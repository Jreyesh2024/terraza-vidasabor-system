#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
LA TERRAZA DE VIDA & SABOR (V&S) - ANVIL UPLINK DAEMON (v2)
Conecta PostgreSQL dbterrazavidasabor (schema v2) con Anvil.works.

Este daemon expone endpoints que la app Anvil llama vía RPC.

Cambios v2 respecto a v1:
- Schema v2: sillas.numero_en_mesa (antes numero_silla), sillas.activa (antes activo),
  areas.activa/orden_display (antes activo/orden), sin sillas.estado/comensal_nombre
  (ese estado vive ahora en ocupaciones_silla).
- CUENTAS_TERRAZA se inicializa dinámicamente desde la BD al arranque, en vez de
  estar hardcodeado con QRs viejos (PV-011). Los QRs nuevos son PV-P-01-01, etc.
- uplink_procesar_cobro y uplink_get_kds están STUB hasta que se implementen los
  bloques correspondientes del roadmap (F y E respectivamente).
- Las escrituras a comandas/detalle_comanda/pagos con schema viejo están deshabilitadas.
============================================================================
"""

import os
import random
from decimal import Decimal
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import anvil.server

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ANVIL_UPLINK_KEY = os.getenv("ANVIL_UPLINK_KEY", "server_4V42VWC6OWS6XV7BAV3QVYBV-2OXFFJ3KXFJYJX7J")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jreyes@localhost:5432/dbterrazavidasabor")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ============================================================================
# ITEMS EN MEMORIA (transición Bloque B → Bloque C)
# ============================================================================
# El estado ocupada/disponible ahora vive en la BD (sesiones_mesa +
# ocupaciones_silla). Solo los ITEMS del carrito antes de mandar a cocina viven
# en memoria hasta que el Bloque C los mueva a detalle_comanda.
# Formato: {"<mesaNum>-<sillaNum>": [{item}, {item}, ...]}
# ============================================================================
ITEMS_MEMORIA = {}

# Mesero default (mientras no haya login). Se resuelve al primer uso.
_MESERO_DEFAULT_ID = None


def _get_mesero_default_id(cur):
    """Devuelve el id del mesero de arranque (Atención General V&S)."""
    global _MESERO_DEFAULT_ID
    if _MESERO_DEFAULT_ID is not None:
        return _MESERO_DEFAULT_ID
    cur.execute("SELECT id FROM meseros WHERE codigo_empleado = 'MES-000' LIMIT 1;")
    row = cur.fetchone()
    if row:
        _MESERO_DEFAULT_ID = int(row['id'])
    return _MESERO_DEFAULT_ID


# ============================================================================
# HELPERS: SESIONES DE MESA Y OCUPACIONES DE SILLA
# ============================================================================
# Reglas del modelo v2:
# - Una sesion_mesa se abre cuando la primera silla de una mesa se ocupa.
# - Se cierra automáticamente cuando la última silla se libera.
# - Una ocupacion_silla vive dentro de una sesion_mesa activa.
# - Ocupación es idempotente: si la silla ya está ocupada, no duplica.
# ============================================================================

def _silla_por_qr(cur, codigo_qr):
    """Retorna dict {silla_id, mesa_id, numero_en_mesa, numero_mesa, es_adicional}."""
    cur.execute("""
        SELECT s.id AS silla_id, s.mesa_id, s.numero_en_mesa, s.codigo_qr,
               s.es_adicional, m.numero_mesa
        FROM sillas s LEFT JOIN mesas m ON s.mesa_id = m.id
        WHERE s.codigo_qr = %s AND s.activa = TRUE;
    """, (codigo_qr,))
    return cur.fetchone()


def _silla_por_mesa_y_numero(cur, numero_mesa, numero_en_mesa):
    """Lookup silla por (número de mesa visible, número de silla en la mesa)."""
    cur.execute("""
        SELECT s.id AS silla_id, s.mesa_id, s.numero_en_mesa, s.codigo_qr,
               s.es_adicional, m.numero_mesa
        FROM sillas s JOIN mesas m ON s.mesa_id = m.id
        WHERE m.numero_mesa = %s AND s.numero_en_mesa = %s AND s.activa = TRUE;
    """, (int(numero_mesa), int(numero_en_mesa)))
    return cur.fetchone()


def _abrir_o_reusar_sesion_mesa(cur, mesa_id):
    """Busca sesión activa para esa mesa; si no existe, crea una nueva.
    Retorna el sesion_mesa_id."""
    cur.execute("""
        SELECT id FROM sesiones_mesa
        WHERE mesa_id = %s AND cerrada_at IS NULL
        ORDER BY abierta_at DESC LIMIT 1;
    """, (int(mesa_id),))
    row = cur.fetchone()
    if row:
        return int(row['id'])
    cur.execute("""
        INSERT INTO sesiones_mesa (mesa_id) VALUES (%s) RETURNING id;
    """, (int(mesa_id),))
    return int(cur.fetchone()['id'])


def _abrir_ocupacion_silla(cur, silla_id, mesa_id, origen, cliente_display_name=None):
    """Abre ocupacion en la silla dentro de una sesion_mesa (crea o reusa).
    Idempotente: si la silla ya tiene ocupacion activa, la retorna.
    Retorna (ocupacion_id, sesion_mesa_id, was_new).
    was_new=True si esta llamada CREÓ la ocupación (silla estaba libre).
    was_new=False si ya existía (idempotente, silla ya estaba ocupada)."""
    # ¿Ya hay ocupacion abierta en esta silla?
    cur.execute("""
        SELECT id, sesion_mesa_id FROM ocupaciones_silla
        WHERE silla_id = %s AND cerrada_at IS NULL
        ORDER BY abierta_at DESC LIMIT 1;
    """, (int(silla_id),))
    row = cur.fetchone()
    if row:
        return int(row['id']), int(row['sesion_mesa_id']), False
    # Abrir/reusar sesion de la mesa y crear ocupacion
    sesion_id = _abrir_o_reusar_sesion_mesa(cur, mesa_id)
    cur.execute("""
        INSERT INTO ocupaciones_silla (sesion_mesa_id, silla_id, cliente_display_name, origen)
        VALUES (%s, %s, %s, %s) RETURNING id;
    """, (sesion_id, int(silla_id), cliente_display_name, origen))
    ocup_id = int(cur.fetchone()['id'])
    return ocup_id, sesion_id, True


def _cerrar_ocupacion_silla(cur, silla_id, cerrada_por_mesero_id=None):
    """Cierra la ocupación activa de la silla si existe.
    Retorna el sesion_mesa_id de la ocupación cerrada, o None si no había."""
    cur.execute("""
        SELECT id, sesion_mesa_id FROM ocupaciones_silla
        WHERE silla_id = %s AND cerrada_at IS NULL
        ORDER BY abierta_at DESC LIMIT 1;
    """, (int(silla_id),))
    row = cur.fetchone()
    if not row:
        return None
    cur.execute("""
        UPDATE ocupaciones_silla
        SET cerrada_at = NOW(),
            cerrada_por_mesero_id = %s
        WHERE id = %s;
    """, (cerrada_por_mesero_id, int(row['id'])))
    return int(row['sesion_mesa_id'])


def _cerrar_sesion_si_vacia(cur, sesion_id):
    """Si la sesión no tiene ocupaciones activas, la cierra. Retorna True si cerró."""
    cur.execute("""
        SELECT count(*) AS abiertas FROM ocupaciones_silla
        WHERE sesion_mesa_id = %s AND cerrada_at IS NULL;
    """, (int(sesion_id),))
    if int(cur.fetchone()['abiertas']) == 0:
        cur.execute("""
            UPDATE sesiones_mesa SET cerrada_at = NOW()
            WHERE id = %s AND cerrada_at IS NULL;
        """, (int(sesion_id),))
        return True
    return False


# ============================================================================
# HELPERS: COMANDAS Y DETALLE_COMANDA (Bloque C.1)
# ============================================================================

def _abrir_o_reusar_comanda(cur, sesion_mesa_id, tipo, silla_id=None):
    """Busca comanda activa (estado 'abierta') para esa sesion + tipo + silla,
    o crea una nueva. Retorna comanda_id.
    tipo: 'silla' → silla_id requerido; 'al_centro' → silla_id se ignora."""
    if tipo == 'silla':
        assert silla_id is not None, "silla_id requerido para tipo='silla'"
        cur.execute("""
            SELECT id FROM comandas
            WHERE sesion_mesa_id = %s AND tipo = 'silla'
              AND silla_id = %s AND estado = 'abierta'
            LIMIT 1;
        """, (int(sesion_mesa_id), int(silla_id)))
    else:
        cur.execute("""
            SELECT id FROM comandas
            WHERE sesion_mesa_id = %s AND tipo = 'al_centro'
              AND estado = 'abierta'
            LIMIT 1;
        """, (int(sesion_mesa_id),))
    row = cur.fetchone()
    if row:
        return int(row['id'])
    # Crear nueva
    if tipo == 'silla':
        cur.execute("""
            INSERT INTO comandas (sesion_mesa_id, tipo, silla_id, mesero_id, estado)
            VALUES (%s, 'silla', %s, %s, 'abierta') RETURNING id;
        """, (int(sesion_mesa_id), int(silla_id), _get_mesero_default_id(cur)))
    else:
        cur.execute("""
            INSERT INTO comandas (sesion_mesa_id, tipo, silla_id, mesero_id, estado)
            VALUES (%s, 'al_centro', NULL, %s, 'abierta') RETURNING id;
        """, (int(sesion_mesa_id), _get_mesero_default_id(cur)))
    return int(cur.fetchone()['id'])


def _snapshot_producto(cur, producto_id):
    """Devuelve {precio, nombre, estacion_id} congelados al momento."""
    cur.execute("""
        SELECT precio_unitario, nombre, estacion_id
        FROM productos_menu WHERE id = %s;
    """, (int(producto_id),))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Producto {producto_id} no existe")
    return {
        "precio": float(row['precio_unitario']),
        "nombre": row['nombre'],
        "estacion_id": int(row['estacion_id']) if row['estacion_id'] else None,
    }


def _sesion_activa_de_silla(cur, silla_id):
    """Retorna la sesion_mesa_id activa de la mesa de esta silla, o None."""
    cur.execute("""
        SELECT ses.id AS sesion_id
        FROM sesiones_mesa ses
        JOIN sillas s ON s.mesa_id = ses.mesa_id
        WHERE s.id = %s AND ses.cerrada_at IS NULL
        ORDER BY ses.abierta_at DESC LIMIT 1;
    """, (int(silla_id),))
    row = cur.fetchone()
    return int(row['sesion_id']) if row else None


# ============================================================================
# HELPERS DE SERIALIZACIÓN
# ============================================================================

def serialize_for_anvil(val):
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: serialize_for_anvil(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [serialize_for_anvil(item) for item in val]
    return val


def clean_row(r):
    if not r:
        return {}
    return serialize_for_anvil(dict(r))


# ============================================================================
# CATÁLOGO (sin cambio de schema)
# ============================================================================

@anvil.server.callable
def uplink_get_categorias():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM categorias WHERE activo = TRUE ORDER BY orden_display ASC;")
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_categorias: {e}")
        return []


@anvil.server.callable
def uplink_get_productos():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*,
                       c.nombre        AS categoria_nombre,
                       c.icono         AS categoria_icono,
                       c.orden_display AS categoria_orden,
                       c.es_al_centro  AS categoria_es_al_centro
                FROM productos_menu p
                JOIN categorias c ON p.categoria_id = c.id
                WHERE p.disponible = TRUE AND c.activo = TRUE
                ORDER BY c.orden_display ASC, p.id ASC;
            """)
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_productos: {e}")
        return []


# ============================================================================
# ÁREAS, MESAS, SILLAS (schema v2)
# ============================================================================

@anvil.server.callable
def uplink_get_areas():
    """Áreas activas (schema v2: activa, orden_display)."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM areas WHERE activa = TRUE ORDER BY orden_display ASC, id ASC;")
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_areas: {e}")
        return []


@anvil.server.callable
def uplink_get_mesas():
    """Mesas con su área y sillas. Estado ocupada/disponible se resuelve por
    JOIN a ocupaciones_silla activas (Bloque B: schema v2 persistente)."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.*,
                       a.nombre        AS area_nombre_oficial,
                       a.icono         AS area_icono,
                       a.orden_display AS area_orden,
                       COALESCE(json_agg(
                           json_build_object(
                               'id',              s.id,
                               'numero_silla',    s.numero_en_mesa,
                               'codigo_qr',       s.codigo_qr,
                               'posicion',        s.posicion,
                               'es_adicional',    s.es_adicional,
                               'estado',          CASE WHEN o.id IS NULL
                                                       THEN 'disponible'
                                                       ELSE 'ocupada' END,
                               'comensal_nombre', COALESCE(o.cliente_display_name,
                                                           'Silla ' || s.numero_en_mesa)
                           ) ORDER BY s.numero_en_mesa
                       ) FILTER (WHERE s.id IS NOT NULL), '[]'::json) AS sillas
                FROM mesas m
                LEFT JOIN areas a  ON m.area_id = a.id
                LEFT JOIN sillas s ON m.id = s.mesa_id AND s.activa = TRUE
                LEFT JOIN ocupaciones_silla o
                       ON o.silla_id = s.id AND o.cerrada_at IS NULL
                WHERE m.activa = TRUE
                GROUP BY m.id, a.nombre, a.icono, a.orden_display
                ORDER BY COALESCE(a.orden_display, 99), m.numero_mesa ASC;
            """)
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_mesas: {e}")
        return []


@anvil.server.callable
def uplink_get_sillas(mesa_id=None):
    """Sillas por mesa (schema v2)."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if mesa_id:
                cur.execute(
                    "SELECT * FROM sillas WHERE mesa_id = %s AND activa = TRUE "
                    "ORDER BY numero_en_mesa ASC;",
                    (int(mesa_id),)
                )
            else:
                cur.execute(
                    "SELECT * FROM sillas WHERE activa = TRUE "
                    "ORDER BY mesa_id NULLS LAST, numero_en_mesa NULLS LAST;"
                )
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_sillas: {e}")
        return []


# ============================================================================
# COMANDAS — Estado persistente en BD (sesiones + ocupaciones)
# Los items del carrito siguen en memoria hasta Bloque C.
# ============================================================================

def _construir_dict_cuentas_desde_db():
    """Retorna el dict CUENTAS con formato compatible con JS legacy:
    keys = "MM-SS" para sillas regulares, "EX-NN" para pool.
    estado se lee de ocupaciones_silla (activa = ocupada).
    items se toma de ITEMS_MEMORIA."""
    resultado = {}
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    s.id           AS silla_id,
                    s.mesa_id,
                    s.numero_en_mesa,
                    s.codigo_qr,
                    s.es_adicional,
                    m.numero_mesa,
                    o.id           AS ocupacion_id,
                    o.sesion_mesa_id,
                    o.cliente_display_name,
                    o.abierta_at,
                    o.origen
                FROM sillas s
                LEFT JOIN mesas m ON s.mesa_id = m.id
                LEFT JOIN ocupaciones_silla o
                       ON o.silla_id = s.id AND o.cerrada_at IS NULL
                WHERE s.activa = TRUE
                ORDER BY s.es_adicional, m.numero_mesa NULLS LAST,
                         s.numero_en_mesa NULLS LAST;
            """)
            rows = cur.fetchall()
        for r in rows:
            if r["es_adicional"] or r["mesa_id"] is None:
                pool_num = r["codigo_qr"].split("-")[-1]
                key = f"EX-{pool_num}"
                mesa_key = 0
                silla_key = 0
                nombre_default = f"Extra {pool_num}"
            else:
                mesa_key = int(r["numero_mesa"])
                silla_key = int(r["numero_en_mesa"])
                key = f"{mesa_key}-{silla_key}"
                nombre_default = f"Silla {silla_key}"
            estado = "ocupada" if r["ocupacion_id"] else "disponible"
            resultado[key] = {
                "mesaId": mesa_key,
                "sillaId": silla_key,
                "sillaDbId": int(r["silla_id"]),
                "qrId": r["codigo_qr"],
                "estado": estado,
                "comensalNombre": r["cliente_display_name"] or nombre_default,
                "items": ITEMS_MEMORIA.get(key, []),
                "esAdicional": bool(r["es_adicional"]),
                "ocupacionId": int(r["ocupacion_id"]) if r["ocupacion_id"] else None,
                "sesionMesaId": int(r["sesion_mesa_id"]) if r["sesion_mesa_id"] else None,
                "origen": r["origen"],
                "abiertaAt": r["abierta_at"].isoformat() if r["abierta_at"] else None,
            }
    finally:
        conn.close()
    return resultado


@anvil.server.callable('get_cuentas_terraza')
@anvil.server.callable('uplink_get_cuentas_terraza')
def uplink_get_cuentas_terraza():
    """Lee estado en tiempo real desde BD (sillas + ocupaciones activas)."""
    try:
        return _construir_dict_cuentas_desde_db()
    except Exception as e:
        print(f"[UPLINK] Error en get_cuentas_terraza: {e}")
        return {}


@anvil.server.callable('checkin_silla_qr')
@anvil.server.callable('uplink_checkin_silla_qr')
def uplink_checkin_silla_qr(mesa_id, silla_id, qr_id=''):
    """Cliente escaneó QR → abre ocupacion en BD (origen='qr'). Idempotente."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Prioridad: si viene qr_id explícito, resolvemos por él (es el más confiable)
            silla_row = None
            if qr_id:
                silla_row = _silla_por_qr(cur, qr_id)
            if silla_row is None:
                silla_row = _silla_por_mesa_y_numero(cur, mesa_id, silla_id)
            if silla_row is None:
                print(f"⚠️  [UPLINK] checkin_qr: silla no encontrada "
                      f"(mesa={mesa_id} silla={silla_id} qr={qr_id})")
                return {"error": "silla no encontrada"}
            _ocup_id, _sesion_id, was_new = _abrir_ocupacion_silla(
                cur,
                silla_id=silla_row['silla_id'],
                mesa_id=silla_row['mesa_id'],
                origen='qr',
            )
        conn.commit()
        estado_txt = "NUEVA OCUPACIÓN" if was_new else "YA ESTABA OCUPADA"
        print(f"🔔 [UPLINK] Check-in QR: silla_id={silla_row['silla_id']} "
              f"(qr={silla_row['codigo_qr']}) → {estado_txt}")
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en checkin_silla_qr: {e}")
        return {"error": str(e)}
    finally:
        conn.close()
    # Retorna el estado actualizado de esa silla en formato legacy + flag ya_ocupada
    all_cuentas = _construir_dict_cuentas_desde_db()
    key = (f"{silla_row['numero_mesa']}-{silla_row['numero_en_mesa']}"
           if not silla_row['es_adicional']
           else f"EX-{silla_row['codigo_qr'].split('-')[-1]}")
    result = dict(all_cuentas.get(key, {}))
    result["ya_ocupada"] = (not was_new)  # True = silla estaba ocupada antes del scan
    return result


@anvil.server.callable('actualizar_cuenta_silla')
@anvil.server.callable('uplink_actualizar_cuenta_silla')
def uplink_actualizar_cuenta_silla(mesa_id, silla_id, items, estado='ocupada'):
    """Actualiza items en memoria + estado en BD (ocupada abre ocupacion,
    disponible cierra). Sirve como el "clic silla" desde POSMesero.
    Bloque C moverá items también a BD."""
    mesa_id = int(mesa_id)
    silla_id = int(silla_id)
    key = f"{mesa_id}-{silla_id}"

    # Items siempre en memoria (Bloque C los pasa a detalle_comanda)
    ITEMS_MEMORIA[key] = items or []

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            silla_row = _silla_por_mesa_y_numero(cur, mesa_id, silla_id)
            if silla_row is None:
                print(f"⚠️  [UPLINK] actualizar_cuenta: silla no encontrada "
                      f"(mesa={mesa_id} silla={silla_id})")
                return _construir_dict_cuentas_desde_db()
            if estado == 'ocupada':
                _abrir_ocupacion_silla(
                    cur, silla_id=silla_row['silla_id'],
                    mesa_id=silla_row['mesa_id'], origen='mesero'
                )
            elif estado in ('disponible', 'libre'):
                sesion_cerrada = _cerrar_ocupacion_silla(
                    cur, silla_id=silla_row['silla_id'],
                    cerrada_por_mesero_id=_get_mesero_default_id(cur)
                )
                if sesion_cerrada:
                    _cerrar_sesion_si_vacia(cur, sesion_cerrada)
                # Al liberar, olvidar items en memoria
                ITEMS_MEMORIA.pop(key, None)
        conn.commit()
        print(f"📝 [UPLINK] Cuenta actualizada BD: Mesa {mesa_id} Silla {silla_id} "
              f"→ {len(items or [])} items ({estado})")
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en actualizar_cuenta_silla: {e}")
    finally:
        conn.close()
    return _construir_dict_cuentas_desde_db()


@anvil.server.callable('liberar_silla')
@anvil.server.callable('uplink_liberar_silla')
def uplink_liberar_silla(mesa_id, silla_id):
    """Endpoint explícito para que el mesero libere una silla.
    Cierra ocupacion + sesion si es la última."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            silla_row = _silla_por_mesa_y_numero(cur, int(mesa_id), int(silla_id))
            if silla_row is None:
                return {"error": "silla no encontrada"}
            sesion_cerrada = _cerrar_ocupacion_silla(
                cur, silla_id=silla_row['silla_id'],
                cerrada_por_mesero_id=_get_mesero_default_id(cur)
            )
            sesion_tambien_cerrada = False
            if sesion_cerrada:
                sesion_tambien_cerrada = _cerrar_sesion_si_vacia(cur, sesion_cerrada)
        conn.commit()
        key = f"{int(mesa_id)}-{int(silla_id)}"
        ITEMS_MEMORIA.pop(key, None)
        print(f"🔓 [UPLINK] Silla liberada: Mesa {mesa_id} Silla {silla_id} "
              f"{'(sesion cerrada)' if sesion_tambien_cerrada else ''}")
        return {"ok": True, "sesion_cerrada": sesion_tambien_cerrada}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en liberar_silla: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


# ============================================================================
# GESTIÓN DE MENÚ (sin cambio de schema — productos_menu igual estructura)
# ============================================================================

@anvil.server.callable
def uplink_guardar_producto(prod_dict):
    try:
        conn = get_db_connection()
        sku = prod_dict.get('codigo_sku') or f"SKU-{random.randint(1000, 9999)}"
        nombre = prod_dict.get('nombre', 'Nuevo Platillo')
        cat_id = int(prod_dict.get('categoria_id', 1))
        precio = float(prod_dict.get('precio_unitario', 0.00))
        desc = prod_dict.get('descripcion', '')
        estacion = prod_dict.get('estacion_preparacion', 'cocina')
        icono = prod_dict.get('icono', '🍲')
        es_al_centro = bool(prod_dict.get('es_al_centro', False))
        disponible = bool(prod_dict.get('disponible', True))
        tiempo = prod_dict.get('tiempo_estimado', '10-15 min')
        porciones = prod_dict.get('porciones', '1 persona')
        opciones_termino = prod_dict.get('opciones_termino', [])
        prefs = prod_dict.get('preferencias_exclusion', [])
        extras = prod_dict.get('extras_disponibles', [])
        ingredientes = prod_dict.get('ingredientes', [])
        pasos = prod_dict.get('pasos', [])
        notas = prod_dict.get('notas_receta', '')

        prod_id = prod_dict.get('id')
        with conn.cursor() as cur:
            if prod_id:
                cur.execute("""
                    UPDATE productos_menu SET
                        categoria_id = %s, nombre = %s, descripcion = %s,
                        precio_unitario = %s, estacion_preparacion = %s,
                        icono = %s, es_al_centro = %s, disponible = %s,
                        tiempo_estimado = %s, porciones = %s,
                        opciones_termino = %s, preferencias_exclusion = %s,
                        extras_disponibles = %s, ingredientes = %s,
                        pasos = %s, notas_receta = %s
                    WHERE id = %s RETURNING *;
                """, (cat_id, nombre, desc, precio, estacion, icono, es_al_centro,
                      disponible, tiempo, porciones, Json(opciones_termino),
                      Json(prefs), Json(extras), Json(ingredientes), Json(pasos),
                      notas, prod_id))
            else:
                cur.execute("""
                    INSERT INTO productos_menu (
                        categoria_id, codigo_sku, nombre, descripcion, precio_unitario,
                        estacion_preparacion, icono, es_al_centro, disponible,
                        tiempo_estimado, porciones, opciones_termino, preferencias_exclusion,
                        extras_disponibles, ingredientes, pasos, notas_receta
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                """, (cat_id, sku, nombre, desc, precio, estacion, icono, es_al_centro,
                      disponible, tiempo, porciones, Json(opciones_termino), Json(prefs),
                      Json(extras), Json(ingredientes), Json(pasos), notas))
            row = cur.fetchone()
            conn.commit()
        conn.close()
        print(f"✅ [UPLINK] Platillo guardado: {nombre} (${precio:.2f})")
        return {"success": True, "producto": clean_row(row)}
    except Exception as e:
        print(f"Error en uplink_guardar_producto: {e}")
        return {"success": False, "error": str(e)}


@anvil.server.callable
def uplink_cambiar_disponibilidad_producto(prod_id, disponible):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE productos_menu SET disponible = %s WHERE id = %s "
                "RETURNING id, disponible;",
                (bool(disponible), int(prod_id))
            )
            row = cur.fetchone()
            conn.commit()
        conn.close()
        print(f"✅ [UPLINK] Disponibilidad: Producto {prod_id} -> {disponible}")
        return {"success": True, "id": row['id'], "disponible": row['disponible']}
    except Exception as e:
        print(f"Error en uplink_cambiar_disponibilidad_producto: {e}")
        return {"success": False, "error": str(e)}


@anvil.server.callable
def uplink_eliminar_producto(prod_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE productos_menu SET disponible = FALSE WHERE id = %s RETURNING id;",
                (int(prod_id),)
            )
            conn.commit()
        conn.close()
        print(f"✅ [UPLINK] Producto desactivado: {prod_id}")
        return {"success": True, "id": prod_id}
    except Exception as e:
        print(f"Error en uplink_eliminar_producto: {e}")
        return {"success": False, "error": str(e)}


@anvil.server.callable
def uplink_guardar_categoria(cat_dict):
    try:
        conn = get_db_connection()
        nombre = cat_dict.get('nombre', 'Nueva Categoría')
        codigo = cat_dict.get('codigo') or nombre.upper().replace(' ', '_')[:25]
        icono = cat_dict.get('icono', '🍽️')
        orden = int(cat_dict.get('orden_display', 10))
        destacado = bool(cat_dict.get('destacado', False))
        es_al_centro = bool(cat_dict.get('es_al_centro', False))
        cat_id = cat_dict.get('id')
        with conn.cursor() as cur:
            if cat_id:
                cur.execute("""
                    UPDATE categorias SET nombre = %s, icono = %s, orden_display = %s,
                        destacado = %s, es_al_centro = %s, activo = TRUE
                    WHERE id = %s RETURNING *;
                """, (nombre, icono, orden, destacado, es_al_centro, cat_id))
            else:
                cur.execute("""
                    INSERT INTO categorias (codigo, nombre, icono, orden_display,
                        destacado, es_al_centro, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (codigo) DO UPDATE SET
                        nombre = EXCLUDED.nombre, icono = EXCLUDED.icono,
                        orden_display = EXCLUDED.orden_display
                    RETURNING *;
                """, (codigo, nombre, icono, orden, destacado, es_al_centro))
            row = cur.fetchone()
            conn.commit()
        conn.close()
        return {"success": True, "categoria": clean_row(row)}
    except Exception as e:
        print(f"Error en uplink_guardar_categoria: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# MENÚS POR ROL (Bloque C.1) — vistas SQL: vw_menu_cliente / vw_menu_mesero
# ============================================================================

@anvil.server.callable('get_menu_cliente')
@anvil.server.callable('uplink_get_menu_cliente')
def uplink_get_menu_cliente():
    """Menú visible al cliente (teléfono/QR). Sin recetas ni costos."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM vw_menu_cliente ORDER BY categoria_orden, id;")
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"Error en get_menu_cliente: {e}")
        return []


@anvil.server.callable('get_menu_mesero')
@anvil.server.callable('uplink_get_menu_mesero')
def uplink_get_menu_mesero():
    """Menú operativo para el mesero (iPad). Sin receta técnica ni costos."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM vw_menu_mesero ORDER BY categoria_orden, id;")
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"Error en get_menu_mesero: {e}")
        return []


# ============================================================================
# ITEMS DE COMANDA (Bloque C.1) — agregar / eliminar / leer
# ============================================================================

@anvil.server.callable('agregar_item_a_comanda')
@anvil.server.callable('uplink_agregar_item_a_comanda')
def uplink_agregar_item_a_comanda(
    mesa_num, silla_num_pedido_por, producto_id, cantidad=1,
    para_silla_num=None,           # None = mismo que silla_num_pedido_por; 0 = al centro
    extras=None, exclusiones=None, opciones_termino=None, notas_cliente=''
):
    """Cliente/mesero agrega un item a una comanda.
    - para_silla_num=0 → item al centro (tipo comanda 'al_centro').
    - para_silla_num=None → default: para la misma silla que ordena.
    - pedido_por_silla_num identifica quién físicamente ordenó (mamá pide por hijo).
    Guarda snapshot de precio + nombre. NO envía a cocina (queda estado 'borrador')."""
    mesa_num = int(mesa_num)
    silla_num_pedido_por = int(silla_num_pedido_por)
    cantidad = max(1, int(cantidad or 1))
    if para_silla_num is None:
        para_silla_num = silla_num_pedido_por
    para_silla_num = int(para_silla_num)  # 0 = al centro
    es_al_centro = (para_silla_num == 0)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Resolver sillas
            silla_pedido_por_row = _silla_por_mesa_y_numero(cur, mesa_num, silla_num_pedido_por)
            if silla_pedido_por_row is None:
                return {"error": f"Silla {mesa_num}-{silla_num_pedido_por} no encontrada"}
            silla_para_row = None
            if not es_al_centro:
                silla_para_row = _silla_por_mesa_y_numero(cur, mesa_num, para_silla_num)
                if silla_para_row is None:
                    return {"error": f"Silla destino {mesa_num}-{para_silla_num} no encontrada"}

            # Asegurar sesión + ocupación de quien ordena
            _abrir_ocupacion_silla(
                cur, silla_id=silla_pedido_por_row['silla_id'],
                mesa_id=silla_pedido_por_row['mesa_id'], origen='qr',
            )
            sesion_id = _sesion_activa_de_silla(cur, silla_pedido_por_row['silla_id'])

            # Si es individual, también aseguramos ocupación de la silla destino
            if not es_al_centro:
                _abrir_ocupacion_silla(
                    cur, silla_id=silla_para_row['silla_id'],
                    mesa_id=silla_para_row['mesa_id'], origen='mesero',
                )

            # Abrir o reusar la comanda apropiada
            if es_al_centro:
                comanda_id = _abrir_o_reusar_comanda(cur, sesion_id, tipo='al_centro')
            else:
                comanda_id = _abrir_o_reusar_comanda(
                    cur, sesion_id, tipo='silla',
                    silla_id=silla_para_row['silla_id']
                )

            # Snapshot del producto
            snap = _snapshot_producto(cur, producto_id)

            cur.execute("""
                INSERT INTO detalle_comanda (
                    comanda_id, producto_id,
                    para_silla_id, pedido_por_silla_id, es_al_centro,
                    tipo_consumo, cantidad,
                    precio_unitario_snapshot, producto_nombre_snapshot,
                    extras_seleccionados, exclusiones,
                    opciones_termino_seleccionadas, notas_cliente,
                    estado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'borrador')
                RETURNING id, precio_unitario_snapshot, subtotal;
            """, (
                comanda_id, int(producto_id),
                None if es_al_centro else silla_para_row['silla_id'],
                silla_pedido_por_row['silla_id'],
                es_al_centro,
                'comida',  # tipo_consumo — Bloque D lo puede refinar según categoría
                cantidad,
                snap['precio'], snap['nombre'],
                Json(extras or []),
                Json(exclusiones or []),
                Json(opciones_termino or []),
                notas_cliente or '',
            ))
            row = cur.fetchone()
        conn.commit()
        print(f"➕ [UPLINK] Item agregado: {snap['nombre']} x{cantidad} "
              f"→ {'AL CENTRO' if es_al_centro else f'Silla {para_silla_num}'} "
              f"(pedido por Silla {silla_num_pedido_por}) [comanda #{comanda_id}]")
        return {
            "ok": True,
            "detalle_id": int(row['id']),
            "comanda_id": comanda_id,
            "precio_unitario": float(row['precio_unitario_snapshot']),
            "subtotal": float(row['subtotal']),
            "estado": "borrador",
        }
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en agregar_item_a_comanda: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('eliminar_item_comanda')
@anvil.server.callable('uplink_eliminar_item_comanda')
def uplink_eliminar_item_comanda(detalle_id):
    """Elimina item si está en 'borrador'. Si ya fue enviado a cocina, lo marca
    'cancelado' (para trazabilidad)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT estado FROM detalle_comanda WHERE id = %s;",
                        (int(detalle_id),))
            row = cur.fetchone()
            if row is None:
                return {"error": "detalle no encontrado"}
            if row['estado'] == 'borrador':
                cur.execute("DELETE FROM detalle_comanda WHERE id = %s;", (int(detalle_id),))
                accion = 'eliminado'
            else:
                cur.execute("""
                    UPDATE detalle_comanda SET estado = 'cancelado' WHERE id = %s;
                """, (int(detalle_id),))
                accion = 'cancelado'
        conn.commit()
        print(f"🗑️  [UPLINK] Item #{detalle_id} {accion}.")
        return {"ok": True, "accion": accion}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en eliminar_item_comanda: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('get_items_por_silla')
@anvil.server.callable('uplink_get_items_por_silla')
def uplink_get_items_por_silla(mesa_num, silla_num):
    """Retorna los items abiertos de una silla dentro de la sesión activa.
    Separa en items_individuales (comanda de silla) y items_al_centro
    (comanda al_centro donde esta silla es parte de la mesa)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            silla_row = _silla_por_mesa_y_numero(cur, int(mesa_num), int(silla_num))
            if silla_row is None:
                return {"items_individuales": [], "items_al_centro": []}
            sesion_id = _sesion_activa_de_silla(cur, silla_row['silla_id'])
            if sesion_id is None:
                return {"items_individuales": [], "items_al_centro": []}
            # Items individuales de esta silla
            cur.execute("""
                SELECT d.id, d.producto_id, d.cantidad,
                       d.precio_unitario_snapshot, d.producto_nombre_snapshot,
                       d.subtotal, d.extras_seleccionados, d.exclusiones,
                       d.opciones_termino_seleccionadas, d.notas_cliente,
                       d.estado, d.hora_creado
                FROM detalle_comanda d
                JOIN comandas c ON d.comanda_id = c.id
                WHERE c.sesion_mesa_id = %s AND c.tipo = 'silla'
                  AND c.silla_id = %s AND c.estado = 'abierta'
                  AND d.estado <> 'cancelado'
                ORDER BY d.hora_creado ASC;
            """, (sesion_id, silla_row['silla_id']))
            items_indiv = [clean_row(r) for r in cur.fetchall()]
            # Items al centro de la mesa (visibles a todas las sillas de la sesión)
            cur.execute("""
                SELECT d.id, d.producto_id, d.cantidad,
                       d.precio_unitario_snapshot, d.producto_nombre_snapshot,
                       d.subtotal, d.extras_seleccionados, d.exclusiones,
                       d.opciones_termino_seleccionadas, d.notas_cliente,
                       d.estado, d.hora_creado, d.pedido_por_silla_id
                FROM detalle_comanda d
                JOIN comandas c ON d.comanda_id = c.id
                WHERE c.sesion_mesa_id = %s AND c.tipo = 'al_centro'
                  AND c.estado = 'abierta'
                  AND d.estado <> 'cancelado'
                ORDER BY d.hora_creado ASC;
            """, (sesion_id,))
            items_centro = [clean_row(r) for r in cur.fetchall()]
        return {
            "items_individuales": items_indiv,
            "items_al_centro": items_centro,
            "sesion_id": sesion_id,
        }
    except Exception as e:
        print(f"[UPLINK] Error en get_items_por_silla: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('enviar_items_a_cocina')
@anvil.server.callable('uplink_enviar_items_a_cocina')
def uplink_enviar_items_a_cocina(detalle_ids):
    """Toma una lista de detalle_comanda_ids en estado 'borrador' y los envía
    a cocina. Agrupa por estación → crea 1 envio_cocina por estación → asigna.
    Versión simple SIN buffer inteligente (eso es Bloque D)."""
    if not detalle_ids:
        return {"ok": True, "enviados": 0, "envios": []}
    ids_list = [int(x) for x in detalle_ids]
    conn = get_db_connection()
    envios_creados = []
    try:
        with conn.cursor() as cur:
            # Obtener items válidos (estado borrador) + su estacion via producto
            cur.execute("""
                SELECT d.id, d.comanda_id, c.sesion_mesa_id, p.estacion_id
                FROM detalle_comanda d
                JOIN comandas c ON d.comanda_id = c.id
                JOIN productos_menu p ON d.producto_id = p.id
                WHERE d.id = ANY(%s) AND d.estado = 'borrador';
            """, (ids_list,))
            candidatos = cur.fetchall()
            if not candidatos:
                return {"ok": True, "enviados": 0, "envios": [],
                        "aviso": "ningún item en estado borrador"}
            # Agrupar por (sesion_id, estacion_id)
            grupos = {}
            for c in candidatos:
                if c['estacion_id'] is None:
                    continue  # skip items sin estación asignada
                key = (int(c['sesion_mesa_id']), int(c['estacion_id']))
                grupos.setdefault(key, []).append(int(c['id']))
            # Por cada grupo, crear envio_cocina y marcar items
            for (sesion_id, estacion_id), item_ids in grupos.items():
                cur.execute("""
                    INSERT INTO envios_cocina (sesion_mesa_id, estacion_id)
                    VALUES (%s, %s) RETURNING id;
                """, (sesion_id, estacion_id))
                envio_id = int(cur.fetchone()['id'])
                cur.execute("""
                    UPDATE detalle_comanda
                    SET envio_cocina_id = %s,
                        estado = 'enviado_cocina',
                        hora_enviado_cocina = NOW()
                    WHERE id = ANY(%s);
                """, (envio_id, item_ids))
                envios_creados.append({
                    "envio_id": envio_id,
                    "estacion_id": estacion_id,
                    "item_ids": item_ids,
                })
        conn.commit()
        total = sum(len(e['item_ids']) for e in envios_creados)
        print(f"🍳 [UPLINK] Enviados a cocina: {total} items en "
              f"{len(envios_creados)} envío(s).")
        return {"ok": True, "enviados": total, "envios": envios_creados}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en enviar_items_a_cocina: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


# ============================================================================
# COCINA / KDS (STUB — se implementa en Bloque E del roadmap)
# ============================================================================

@anvil.server.callable
def uplink_get_recetas_cocina():
    """Ficha técnica de recetas. Usa la vista vw_ficha_cocina del schema v2."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.codigo_sku, p.nombre, p.descripcion, p.icono,
                       p.estacion_preparacion, p.tiempo_estimado, p.porciones,
                       p.ingredientes, p.pasos, p.notas_receta,
                       c.nombre AS categoria_nombre, c.icono AS categoria_icono
                FROM productos_menu p
                JOIN categorias c ON p.categoria_id = c.id
                WHERE p.disponible = TRUE AND c.activo = TRUE
                ORDER BY c.orden_display ASC, p.nombre ASC;
            """)
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_recetas_cocina: {e}")
        return []


@anvil.server.callable
def uplink_get_kds():
    """STUB. En el Bloque E se implementará consumiendo envios_cocina + detalle_comanda."""
    print("⏸️  [UPLINK] uplink_get_kds llamado (stub — pendiente Bloque E).")
    return []


# ============================================================================
# COBROS (STUB — se implementa en Bloque F del roadmap)
# ============================================================================

@anvil.server.callable
def uplink_procesar_cobro(metodo_pago, items_carrito, tipo_cobro='mesa_completa',
                          numero_silla=None, propina_monto=0.00):
    """STUB. En el Bloque F se implementará con sesiones_mesa + asignaciones_pago."""
    print(f"⏸️  [UPLINK] uplink_procesar_cobro llamado (stub — pendiente Bloque F). "
          f"metodo={metodo_pago} tipo={tipo_cobro}")
    subtotal = sum(
        i.get('precio_unitario', i.get('precio', 0.00)) * i.get('cantidad', 1)
        for i in (items_carrito or [])
    )
    iva = round(subtotal * 0.16 / 1.16, 2)  # IVA incluido en el precio
    propina = round(float(propina_monto or 0), 2)
    total = round(subtotal + propina, 2)
    return {
        "success": True,
        "stub": True,
        "aviso": "Cobro simulado — persistencia real pendiente del Bloque F.",
        "folio": f"VS-STUB-{random.randint(1000, 9999)}",
        "metodo_pago": metodo_pago,
        "tipo_cobro": tipo_cobro,
        "subtotal": subtotal,
        "iva": iva,
        "propina": propina,
        "total": total,
    }


# ============================================================================
# DASHBOARD KPIs (usa memoria y conteos simples — sigue funcional)
# ============================================================================

@anvil.server.callable
def uplink_get_dashboard_kpis():
    try:
        conn = get_db_connection()
        total_prods = 0
        total_mesas = 0
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM productos_menu WHERE disponible = TRUE;")
            total_prods = cur.fetchone()['count']
            cur.execute("SELECT count(*) FROM mesas WHERE activa = TRUE;")
            total_mesas = cur.fetchone()['count']
        conn.close()

        # Estado en tiempo real desde BD (v2)
        cuentas = _construir_dict_cuentas_desde_db()
        ocupadas_count = 0
        comensales_count = 0
        comandas_recientes = []
        for key, cta in cuentas.items():
            if cta and cta.get('estado') == 'ocupada' and cta.get('items'):
                ocupadas_count += 1
                items_count = len(cta.get('items', []))
                total_cta = sum(
                    float(it.get('precio', 0)) * int(it.get('cantidad', 1))
                    for it in cta.get('items', [])
                )
                comensales_count += 1
                parts = key.split('-')
                mesa_num = parts[0]
                silla_num = parts[1] if len(parts) > 1 else '1'
                comandas_recientes.append({
                    'folio': f"CMD-{key}",
                    'mesa': f"Mesa {mesa_num}" if silla_num != '0' else f"Mesa {mesa_num} (Al Centro)",
                    'comensal': cta.get('comensalNombre', f"Silla {silla_num}"),
                    'hora': cta.get('items', [{}])[0].get('hora', '09:30 AM'),
                    'monto': round(total_cta, 2),
                    'items_count': items_count,
                    'estado': 'En servicio',
                })

        return {
            'ventas': {
                'total_semana': 14850.00, 'comandas_semana': 38,
                'total_hoy': 4850.00, 'comandas_hoy': 14, 'promedio_ticket': 346.40,
            },
            'platillo_estrella': {
                'nombre': 'Chilaquiles Rojos con Huevo',
                'categoria': 'Especialidades Mexicanas',
                'ordenes_semana': 42, 'icono': '🍳', 'porcentaje_ventas': '28% del volumen',
            },
            'flujo_caja': {
                'efectivo': 5400.00, 'bancarizado': 9450.00,
                'propinas': 850.00, 'iva_trasladado': 2048.27,
            },
            'mesas': {
                'total': total_mesas,
                'ocupadas': ocupadas_count,
                'libres': max(0, total_mesas - ocupadas_count),
                'comensales_activos': comensales_count,
            },
            'comandas_recientes': comandas_recientes,
            'alertas_insumos': [
                {'insumo': 'Huevos frescos de rancho', 'cant_actual': '3 rejas (90 pzas)',
                 'urgencia': 'URGENTE', 'dias_restantes': '1 día',
                 'consumo_semanal': '15 rejas', 'color': '#ef4444'},
                {'insumo': 'Totopos horneados de maíz', 'cant_actual': '4 kg',
                 'urgencia': 'PRÓXIMO', 'dias_restantes': '2 días',
                 'consumo_semanal': '25 kg', 'color': '#f59e0b'},
                {'insumo': 'Queso fresco artesanal', 'cant_actual': '2.5 kg',
                 'urgencia': 'PRÓXIMO', 'dias_restantes': '3 días',
                 'consumo_semanal': '12 kg', 'color': '#f59e0b'},
                {'insumo': 'Aguacate Hass seleccionado', 'cant_actual': '5 kg',
                 'urgencia': 'NORMAL', 'dias_restantes': '4 días',
                 'consumo_semanal': '18 kg', 'color': '#10b981'},
                {'insumo': 'Café de altura molido arábica', 'cant_actual': '6 kg',
                 'urgencia': 'NORMAL', 'dias_restantes': '5 días',
                 'consumo_semanal': '10 kg', 'color': '#10b981'},
            ],
            'total_platillos_catalogo': total_prods,
        }
    except Exception as e:
        print(f"Error en uplink_get_dashboard_kpis: {e}")
        return {}


# ============================================================================
# ALIASES REQUERIDOS POR AdminMenu (nombres _terraza)
# ============================================================================

@anvil.server.callable('get_dashboard_kpis_terraza')
def alias_get_dashboard_kpis_terraza():
    return uplink_get_dashboard_kpis()


@anvil.server.callable('get_productos_terraza')
def alias_get_productos_terraza():
    return uplink_get_productos()


@anvil.server.callable('get_categorias_terraza')
def alias_get_categorias_terraza():
    return uplink_get_categorias()


@anvil.server.callable('get_mesas_terraza')
def alias_get_mesas_terraza():
    return uplink_get_mesas()


@anvil.server.callable('guardar_producto_terraza')
def alias_guardar_producto_terraza(prod_dict):
    return uplink_guardar_producto(prod_dict)


@anvil.server.callable('cambiar_disponibilidad_producto_terraza')
def alias_cambiar_disponibilidad_terraza(prod_id, disponible):
    return uplink_cambiar_disponibilidad_producto(prod_id, disponible)


@anvil.server.callable('get_recetas_cocina_terraza')
def alias_get_recetas_cocina_terraza():
    return uplink_get_recetas_cocina()


@anvil.server.callable('get_areas_terraza')
def alias_get_areas_terraza():
    return uplink_get_areas()


# ============================================================================
# CONEXIÓN PRINCIPAL UPLINK DE ANVIL
# ============================================================================

if __name__ == '__main__':
    print("🌿 Conectando 'La Terraza de Vida & Sabor' (V&S) Anvil Uplink a Anvil.works...")
    print(f"🔑 Key: {ANVIL_UPLINK_KEY[:15]}...")
    anvil.server.connect(ANVIL_UPLINK_KEY)
    print("✅ ¡Conexión Anvil Uplink V&S establecida — schema v2 + sesiones persistentes!")
    anvil.server.wait_forever()
