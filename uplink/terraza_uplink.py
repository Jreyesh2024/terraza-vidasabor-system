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
from datetime import datetime, date, timezone, timedelta
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


def _cerrar_ocupacion_por_qr(cur, qr_codigo):
    """Cierra la ocupación activa asociada al QR dado (silla y sus posibles
    referencias en la sesion). Usado para 'cambio de lugar silencioso' cuando
    el mismo cliente escanea una silla nueva desde su teléfono."""
    silla = _silla_por_qr(cur, qr_codigo)
    if silla is None:
        return None
    sesion_cerrada = _cerrar_ocupacion_silla(
        cur, silla_id=silla['silla_id'], cerrada_por_mesero_id=None
    )
    if sesion_cerrada:
        _cerrar_sesion_si_vacia(cur, sesion_cerrada)
    return sesion_cerrada


def _crear_llamada_conflicto(cur, silla_id, tipo='conflicto_silla_ocupada',
                              notas=None):
    """Registra una llamada al mesero por conflicto en la silla. Deduplica:
    si ya hay una del mismo tipo abierta para esa silla, no crea otra."""
    cur.execute("""
        SELECT id FROM llamadas_mesero
        WHERE silla_id = %s AND tipo = %s AND atendida_at IS NULL
        LIMIT 1;
    """, (int(silla_id), tipo))
    if cur.fetchone():
        return None
    cur.execute("""
        INSERT INTO llamadas_mesero (silla_id, tipo, notas)
        VALUES (%s, %s, %s) RETURNING id;
    """, (int(silla_id), tipo, notas))
    return int(cur.fetchone()['id'])


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
    """Devuelve {precio, nombre, estacion_id, estacion_preparacion} congelados al momento."""
    cur.execute("""
        SELECT precio_unitario, nombre, estacion_id, estacion_preparacion
        FROM productos_menu WHERE id = %s;
    """, (int(producto_id),))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Producto {producto_id} no existe")
    return {
        "precio": float(row['precio_unitario']),
        "nombre": row['nombre'],
        "estacion_id": int(row['estacion_id']) if row['estacion_id'] else None,
        "estacion_preparacion": row.get('estacion_preparacion', 'cocina'),
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
    """Retorna el dict CUENTAS sincronizado en tiempo real desde PostgreSQL:
    - Sillas y ocupaciones desde BD.
    - Items de comanda reales desde detalle_comanda (vinculados a sesiones activas).
    - Cuentas de mesa al centro (f"{mesa}-0") desde detalle_comanda.
    """
    resultado = {}
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Sillas activas y sus ocupaciones vivas
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
                    "items": list(ITEMS_MEMORIA.get(key, [])),
                    "esAdicional": bool(r["es_adicional"]),
                    "ocupacionId": int(r["ocupacion_id"]) if r["ocupacion_id"] else None,
                    "sesionMesaId": int(r["sesion_mesa_id"]) if r["sesion_mesa_id"] else None,
                    "origen": r["origen"],
                    "abiertaAt": r["abierta_at"].isoformat() if r["abierta_at"] else None,
                }

            # 1.1 Procesar automáticamente buffers que hayan cumplido los 5 minutos
            _procesar_todos_los_buffers_vencidos(cur, ventana_segundos=300)

            # 2. Cargar items reales de detalle_comanda para sesiones vivas
            cur.execute("""
                SELECT 
                    d.id,
                    d.comanda_id,
                    d.producto_id,
                    d.para_silla_id,
                    d.pedido_por_silla_id,
                    d.es_al_centro,
                    d.tipo_consumo,
                    d.cantidad,
                    d.precio_unitario_snapshot,
                    d.producto_nombre_snapshot,
                    d.subtotal,
                    d.notas_cliente,
                    d.estado,
                    d.hora_creado,
                    d.hora_enviado_cocina,
                    d.hora_listo,
                    d.hora_servido,
                    d.envio_cocina_id,
                    ec.timestamp_en_preparacion,
                    c.sesion_mesa_id,
                    c.tipo AS comanda_tipo,
                    sm.mesa_id,
                    m.numero_mesa,
                    s_para.numero_en_mesa AS para_silla_num,
                    s_para.codigo_qr      AS para_qr,
                    s_para.es_adicional   AS para_es_adicional
                FROM detalle_comanda d
                JOIN comandas c ON d.comanda_id = c.id
                JOIN sesiones_mesa sm ON c.sesion_mesa_id = sm.id AND sm.cerrada_at IS NULL
                LEFT JOIN mesas m ON sm.mesa_id = m.id
                LEFT JOIN sillas s_para ON d.para_silla_id = s_para.id
                LEFT JOIN envios_cocina ec ON d.envio_cocina_id = ec.id
                WHERE c.estado = 'abierta' AND d.estado <> 'cancelado'
                ORDER BY d.hora_creado ASC;
            """)
            items_rows = cur.fetchall()

            for it in items_rows:
                mesa_num = int(it["numero_mesa"]) if it["numero_mesa"] else 1
                hora_str = it["hora_creado"].strftime("%I:%M %p") if it["hora_creado"] else ""
                hora_envio_str = it["hora_enviado_cocina"].strftime("%I:%M %p") if it["hora_enviado_cocina"] else hora_str
                
                estado_raw = str(it["estado"])
                if estado_raw == "en_preparacion":
                    estado_cocina = "preparando"
                elif estado_raw == "listo":
                    estado_cocina = "listo"
                elif estado_raw == "servido":
                    estado_cocina = "servido"
                elif estado_raw in ("enviado_cocina", "en_buffer"):
                    estado_cocina = "recibido"
                else:
                    estado_cocina = "borrador"

                ts_creado_ms = int(it["hora_creado"].timestamp() * 1000) if it["hora_creado"] else None
                ts_envio_ms = int(it["hora_enviado_cocina"].timestamp() * 1000) if it["hora_enviado_cocina"] else None
                ts_inicio_ms = int(it["timestamp_en_preparacion"].timestamp() * 1000) if it.get("timestamp_en_preparacion") else None

                item_obj = {
                    "id": int(it["id"]),
                    "productoId": int(it["producto_id"]),
                    "nombre": str(it["producto_nombre_snapshot"]),
                    "precio": float(it["precio_unitario_snapshot"]),
                    "cantidad": int(it["cantidad"]),
                    "subtotal": float(it["subtotal"]),
                    "notas": str(it["notas_cliente"] or ""),
                    "estado": estado_raw,
                    "estadoCocina": estado_cocina,
                    "enviadoCocina": (estado_raw not in ("borrador", "en_buffer")),
                    "tipo_consumo": str(it["tipo_consumo"] or "comida"),
                    "hora": hora_str,
                    "horaEnvioCocina": hora_envio_str,
                    "timestampCreado": ts_creado_ms,
                    "timestampEnvioCocina": ts_envio_ms,
                    "timestampInicioCocina": ts_inicio_ms,
                    "envioCocinaId": int(it["envio_cocina_id"]) if it["envio_cocina_id"] else None,
                    "mesaId": mesa_num,
                    "sillaNum": 0 if it["es_al_centro"] else (int(it["para_silla_num"]) if it["para_silla_num"] else 0),
                    "es_cuenta_mesa": bool(it["es_al_centro"]),
                }

                if it["es_al_centro"]:
                    mesa_key_centro = f"{mesa_num}-0"
                    if mesa_key_centro not in resultado:
                        resultado[mesa_key_centro] = {
                            "mesaId": mesa_num,
                            "sillaId": 0,
                            "sillaDbId": 0,
                            "qrId": f"MESA-{mesa_num:02d}",
                            "estado": "ocupada",
                            "comensalNombre": "⭐ Cuenta de MESA (Al Centro)",
                            "items": [],
                            "esAdicional": False,
                            "ocupacionId": None,
                            "sesionMesaId": int(it["sesion_mesa_id"]),
                            "origen": "al_centro",
                            "abiertaAt": None,
                        }
                    if not any(x.get("id") == item_obj["id"] for x in resultado[mesa_key_centro]["items"]):
                        resultado[mesa_key_centro]["items"].append(item_obj)
                else:
                    if it["para_es_adicional"]:
                        pool_num = it["para_qr"].split("-")[-1]
                        chair_key = f"EX-{pool_num}"
                    else:
                        s_num = int(it["para_silla_num"]) if it["para_silla_num"] else 1
                        chair_key = f"{mesa_num}-{s_num}"

                    if chair_key in resultado:
                        if not any(x.get("id") == item_obj["id"] for x in resultado[chair_key]["items"]):
                            resultado[chair_key]["items"].append(item_obj)
                        resultado[chair_key]["estado"] = "ocupada"
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


def _consultar_estado_horario_db(cur, area_id=None):
    """Consulta en PostgreSQL si el restaurante y la cocina caliente están abiertos según horarios_atencion."""
    try:
        cur.execute("""
            SELECT 
                EXTRACT(DOW FROM NOW())::INT AS dow_num,
                TO_CHAR(NOW(), 'TMDay') AS nombre_dia_actual,
                NOW()::TIME AS hora_actual,
                h.dia_semana,
                h.nombre_dia,
                h.abierto,
                h.hora_apertura,
                h.hora_cierre,
                h.hora_cierre_cocina,
                h.notas
            FROM (SELECT EXTRACT(DOW FROM NOW())::INT AS dow) curr
            LEFT JOIN horarios_atencion h ON h.dia_semana = curr.dow AND (h.area_id = %s OR h.area_id IS NULL)
            ORDER BY h.area_id NULLS LAST
            LIMIT 1;
        """, (area_id,))
        row = cur.fetchone()
        if not row or row['abierto'] is None:
            return {
                "abierto": True,
                "cocina_caliente_abierta": True,
                "dia_nombre": "Servicio",
                "hora_apertura_str": "08:00 AM",
                "hora_cierre_str": "03:00 PM",
                "hora_cierre_cocina_str": "02:00 PM",
                "motivo": None
            }

        abierto_dia = bool(row['abierto'])
        hora_act = row['hora_actual']
        h_aper = row['hora_apertura']
        h_cier = row['hora_cierre']
        h_coc = row['hora_cierre_cocina']

        esta_abierto = abierto_dia and (h_aper <= hora_act < h_cier)
        cocina_abierta = esta_abierto and (hora_act < h_coc)

        h_aper_str = h_aper.strftime("%I:%M %p") if h_aper else "08:00 AM"
        h_cier_str = h_cier.strftime("%I:%M %p") if h_cier else "03:00 PM"
        h_coc_str = h_coc.strftime("%I:%M %p") if h_coc else "02:00 PM"

        motivo = None
        if not abierto_dia:
            motivo = f"Hoy {row['nombre_dia']} es nuestro día de descanso semanal. Abrimos de Martes a Domingo a partir de las 8:00 AM."
        elif hora_act < h_aper:
            motivo = f"Aún no abrimos. Nuestro horario de hoy {row['nombre_dia']} inicia a las {h_aper_str}."
        elif hora_act >= h_cier:
            motivo = f"Servicio cerrado por hoy {row['nombre_dia']}. Nuestro horario es de {h_aper_str} a {h_cier_str}."

        return {
            "abierto": esta_abierto,
            "cocina_caliente_abierta": cocina_abierta,
            "dia_semana": row['dia_semana'],
            "dia_nombre": row['nombre_dia'],
            "hora_apertura_str": h_aper_str,
            "hora_cierre_str": h_cier_str,
            "hora_cierre_cocina_str": h_coc_str,
            "motivo": motivo
        }
    except Exception as e:
        print(f"[UPLINK] Error consultando estado horario: {e}")
        return {
            "abierto": True,
            "cocina_caliente_abierta": True,
            "dia_nombre": "Servicio",
            "hora_apertura_str": "08:00 AM",
            "hora_cierre_str": "03:00 PM",
            "hora_cierre_cocina_str": "02:00 PM",
            "motivo": None
        }


@anvil.server.callable('get_estado_operativo_restaurante')
@anvil.server.callable('uplink_get_estado_operativo_restaurante')
def uplink_get_estado_operativo_restaurante(area_id=None):
    """Retorna si el restaurante y la cocina caliente están en horario de servicio."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            return _consultar_estado_horario_db(cur, area_id)
    finally:
        conn.close()


@anvil.server.callable('get_horarios_semana')
@anvil.server.callable('uplink_get_horarios_semana')
def uplink_get_horarios_semana():
    """Retorna la tabla completa de horarios de atención para mostrar al cliente."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT dia_semana, nombre_dia, abierto, hora_apertura, hora_cierre, hora_cierre_cocina, notas
                FROM horarios_atencion
                ORDER BY (dia_semana + 6) % 7;
            """)
            rows = cur.fetchall()
            return [clean_row(r) for r in rows]
    finally:
        conn.close()


@anvil.server.callable('checkin_silla_qr')
@anvil.server.callable('uplink_checkin_silla_qr')
def uplink_checkin_silla_qr(mesa_id, silla_id, qr_id='', qr_previo=None):
    """Cliente escaneó QR → valida horarios y abre u adopta ocupacion en BD (origen='qr').
    Políticas amigables:
      - Fuera de horario / Lunes: rechaza amablemente indicando horarios.
      - Silla libre: abre nueva ocupación.
      - Silla ya activada previamente (por mesero o por el mismo comensal):
        se enlaza limpiamente y actualiza origen a 'qr', sin bloquear al cliente.
      - Silla libre + qr_previo distinto: cambio de lugar silencioso (cierra
        la ocupación del qr_previo, abre la nueva).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            silla_row = None
            if qr_id:
                silla_row = _silla_por_qr(cur, qr_id)
            if silla_row is None:
                silla_row = _silla_por_mesa_y_numero(cur, mesa_id, silla_id)
            if silla_row is None:
                print(f"⚠️  [UPLINK] checkin_qr: silla no encontrada "
                      f"(mesa={mesa_id} silla={silla_id} qr={qr_id})")
                return {"error": "silla no encontrada"}

            # 1. Validar horario de servicio del restaurante
            estado_horario = _consultar_estado_horario_db(cur, silla_row.get('area_id'))
            if not estado_horario.get('abierto', True):
                print(f"🌙 [UPLINK] checkin_qr rechazado por fuera de horario: {estado_horario.get('motivo')}")
                return {
                    "error": "restaurante_cerrado",
                    "horario_info": estado_horario,
                    "qr": silla_row['codigo_qr']
                }

            # 2. ¿Esa silla ya tiene ocupación activa?
            cur.execute("""
                SELECT id, origen, sesion_mesa_id FROM ocupaciones_silla
                WHERE silla_id = %s AND cerrada_at IS NULL LIMIT 1;
            """, (int(silla_row['silla_id']),))
            ocup_row = cur.fetchone()

            if ocup_row:
                # Si ya estaba abierta (por mesero o refresco del cliente):
                # La adoptamos de manera transparente y actualizamos el origen a 'qr'
                cur.execute("""
                    UPDATE ocupaciones_silla
                    SET origen = 'qr'
                    WHERE id = %s;
                """, (int(ocup_row['id']),))
                was_new = False
                _ocup_id = int(ocup_row['id'])
                _sesion_id = int(ocup_row['sesion_mesa_id'])
            else:
                # Cambio de lugar silencioso: cierro la ocupación del QR anterior si viene de otra silla
                if qr_previo and qr_previo != silla_row['codigo_qr']:
                    _cerrar_ocupacion_por_qr(cur, qr_previo)

                _ocup_id, _sesion_id, was_new = _abrir_ocupacion_silla(
                    cur,
                    silla_id=silla_row['silla_id'],
                    mesa_id=silla_row['mesa_id'],
                    origen='qr',
                )
        conn.commit()
        estado_txt = "ADOPCIÓN / RECONEXIÓN" if not was_new else ("CAMBIO DE LUGAR" if qr_previo else "NUEVA OCUPACIÓN")
        print(f"🔔 [UPLINK] Check-in QR: silla_id={silla_row['silla_id']} "
              f"(qr={silla_row['codigo_qr']}) → {estado_txt}")
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en checkin_silla_qr: {e}")
        return {"error": str(e)}
    finally:
        conn.close()
    all_cuentas = _construir_dict_cuentas_desde_db()
    key = (f"{silla_row['numero_mesa']}-{silla_row['numero_en_mesa']}"
           if not silla_row['es_adicional']
           else f"EX-{silla_row['codigo_qr'].split('-')[-1]}")
    result = dict(all_cuentas.get(key, {}))
    result["ya_ocupada"] = False  # Para el cliente en móvil, siempre entra directo al menú
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

    # Items en memoria: solo actualizar si se proporcionan items explícitos
    if items is not None and isinstance(items, list) and len(items) > 0:
        ITEMS_MEMORIA[key] = items
    elif items is not None and isinstance(items, list) and len(items) == 0 and estado in ('disponible', 'libre'):
        ITEMS_MEMORIA.pop(key, None)

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


@anvil.server.callable('liberar_mesa')
@anvil.server.callable('uplink_liberar_mesa')
def uplink_liberar_mesa(mesa_id):
    """Endpoint explícito para que el mesero o POS libere toda la mesa.
    Cierra todas las ocupaciones activas de sus sillas y la sesión de mesa."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            mesa_id = int(mesa_id)
            cur.execute("""
                UPDATE ocupaciones_silla os
                SET cerrada_at = NOW(),
                    cerrada_por_mesero_id = %s
                FROM sillas s
                WHERE os.silla_id = s.id
                  AND s.mesa_id = %s
                  AND os.cerrada_at IS NULL;
            """, (_get_mesero_default_id(cur), mesa_id))
            
            cur.execute("""
                UPDATE sesiones_mesa
                SET cerrada_at = NOW()
                WHERE mesa_id = %s AND cerrada_at IS NULL;
            """, (mesa_id,))
        conn.commit()
        # Limpiar items en memoria para todas las sillas de esa mesa
        for k in list(ITEMS_MEMORIA.keys()):
            if k.startswith(f"{mesa_id}-"):
                ITEMS_MEMORIA.pop(k, None)
        print(f"🔓 [UPLINK] Mesa {mesa_id} liberada completamente (sesión y sillas cerradas)")
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en liberar_mesa: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('reiniciar_jornada_terraza')
@anvil.server.callable('uplink_reiniciar_jornada_terraza')
def uplink_reiniciar_jornada_terraza():
    """CIERRE DE JORNADA / REINICIO DE TURNO (RESET OPERATIVO COMPLETO):
    - Cierra todas las sesiones de mesa y ocupaciones de sillas activas.
    - Cierra comandas abiertas y marca detalles anteriores como concluidos.
    - Cierra llamadas de mesero pendientes.
    - Limpia la memoria transaccional y buffers.
    - Retorna el tablero 100% libre (verde) para iniciar un nuevo día en blanco.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            mesero_id = _get_mesero_default_id(cur)
            
            # 1. Cerrar todas las ocupaciones de silla activas
            cur.execute("""
                UPDATE ocupaciones_silla
                SET cerrada_at = NOW(),
                    cerrada_por_mesero_id = %s
                WHERE cerrada_at IS NULL;
            """, (mesero_id,))

            # 2. Cerrar todas las sesiones de mesa activas
            cur.execute("""
                UPDATE sesiones_mesa
                SET cerrada_at = NOW()
                WHERE cerrada_at IS NULL;
            """)

            # 3. Cerrar comandas abiertas
            cur.execute("""
                UPDATE comandas
                SET estado = 'cerrada',
                    cerrada_at = NOW()
                WHERE estado = 'abierta';
            """)

            # 4. Cerrar detalles de comanda activos
            cur.execute("""
                UPDATE detalle_comanda
                SET estado = 'servido',
                    hora_servido = COALESCE(hora_servido, NOW())
                WHERE estado IN ('borrador', 'en_buffer', 'enviado_cocina', 'en_preparacion', 'listo');
            """)

            # 5. Cerrar llamadas al mesero pendientes
            cur.execute("""
                UPDATE llamadas_mesero
                SET atendida_at = NOW(),
                    atendida_por_mesero_id = %s
                WHERE atendida_at IS NULL;
            """, (mesero_id,))

            # 6. Limpiar buffer pre-envío si existe la tabla
            try:
                cur.execute("DELETE FROM buffer_pre_envio WHERE consolidado_en_envio_id IS NULL;")
            except Exception:
                pass

        conn.commit()
        # 7. Vaciar memoria de items en tránsito
        ITEMS_MEMORIA.clear()
        print("🌅 [UPLINK] ¡Jornada de La Terraza reiniciada con éxito! Todas las mesas quedaron libres para el nuevo día.")
        return _construir_dict_cuentas_desde_db()
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error reiniciando jornada de la terraza: {e}")
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
            estacion_id = snap.get('estacion_id') or 1
            estacion_prep = snap.get('estacion_preparacion') or 'cocina'

            # Validar si es comida caliente y la cocina ya cerró por horario
            if estacion_prep == 'cocina' or estacion_id != 3:
                estado_horario = _consultar_estado_horario_db(cur, silla_pedido_por_row.get('area_id'))
                if not estado_horario.get('cocina_caliente_abierta', True):
                    return {
                        "ok": False,
                        "error": f"La cocina caliente cerró por hoy a las {estado_horario.get('hora_cierre_cocina_str')}. Aún puedes ordenar bebidas, barra y postres."
                    }

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
                'bebida' if estacion_id == 3 else 'comida',
                cantidad,
                snap['precio'], snap['nombre'],
                Json(extras or []),
                Json(exclusiones or []),
                Json(opciones_termino or []),
                notas_cliente or '',
            ))
            row = cur.fetchone()
            detalle_id = int(row['id'])

            # Registrar en buffer_pre_envio para la ventana de consolidación por mesa
            cur.execute("""
                INSERT INTO buffer_pre_envio (detalle_comanda_id, sesion_mesa_id, estacion_id, creado_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (detalle_comanda_id) DO NOTHING;
            """, (detalle_id, sesion_id, estacion_id))
        conn.commit()
        print(f"➕ [UPLINK] Item agregado al buffer: {snap['nombre']} x{cantidad} "
              f"→ {'AL CENTRO' if es_al_centro else f'Silla {para_silla_num}'} "
              f"(pedido por Silla {silla_num_pedido_por}) [comanda #{comanda_id}]")
        return {
            "ok": True,
            "detalle_id": detalle_id,
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


# ============================================================================
# BUFFER INTELIGENTE & CONSOLIDACIÓN CON MERGE EN FILA (Bloque D)
# ============================================================================

def _consolidar_detalle_ids_con_merge(cur, detalle_ids):
    """Consolida lista de detalle_ids agrupando por (sesion_mesa_id, estacion_id).
    Regla de Merge Inteligente:
    Si la mesa ya tiene un ticket en espera en esa estación (timestamp_en_preparacion IS NULL),
    incorpora los nuevos items a ese ticket existente para que salgan juntos."""
    if not detalle_ids:
        return []
    cur.execute("""
        SELECT d.id, d.comanda_id, c.sesion_mesa_id, COALESCE(p.estacion_id, 1) AS estacion_id
        FROM detalle_comanda d
        JOIN comandas c ON d.comanda_id = c.id
        JOIN productos_menu p ON d.producto_id = p.id
        WHERE d.id = ANY(%s) AND d.estado = 'borrador';
    """, ([int(x) for x in detalle_ids],))
    candidatos = cur.fetchall()
    if not candidatos:
        return []

    grupos = {}
    for c in candidatos:
        key = (int(c['sesion_mesa_id']), int(c['estacion_id']))
        grupos.setdefault(key, []).append(int(c['id']))

    envios_procesados = []
    for (sesion_id, estacion_id), item_ids in grupos.items():
        # 1. ¿Existe ya un ticket en espera para esta mesa en esta estación?
        cur.execute("""
            SELECT id FROM envios_cocina
            WHERE sesion_mesa_id = %s AND estacion_id = %s
              AND timestamp_en_preparacion IS NULL AND timestamp_listo IS NULL
            ORDER BY timestamp_envio DESC LIMIT 1;
        """, (sesion_id, estacion_id))
        envio_existente = cur.fetchone()

        if envio_existente:
            envio_id = int(envio_existente['id'])
            es_merge = True
        else:
            cur.execute("""
                INSERT INTO envios_cocina (sesion_mesa_id, estacion_id, timestamp_envio)
                VALUES (%s, %s, NOW()) RETURNING id;
            """, (sesion_id, estacion_id))
            envio_id = int(cur.fetchone()['id'])
            es_merge = False

        cur.execute("""
            UPDATE detalle_comanda
            SET envio_cocina_id = %s,
                estado = 'enviado_cocina',
                hora_enviado_cocina = NOW()
            WHERE id = ANY(%s);
        """, (envio_id, item_ids))

        cur.execute("""
            UPDATE buffer_pre_envio
            SET consolidado_en_envio_id = %s
            WHERE detalle_comanda_id = ANY(%s);
        """, (envio_id, item_ids))

        envios_procesados.append({
            "envio_id": envio_id,
            "estacion_id": estacion_id,
            "sesion_id": sesion_id,
            "item_ids": item_ids,
            "es_merge": es_merge,
        })
    return envios_procesados


def _procesar_buffer_sesion(cur, sesion_mesa_id, forzar=False, ventana_segundos=300):
    """Revisa y consolida los items en buffer de una sesión de mesa.
    Si forzar=True o han transcurrido ventana_segundos desde el primer item, consolida."""
    cur.execute("""
        SELECT b.detalle_comanda_id, b.creado_at
        FROM buffer_pre_envio b
        JOIN detalle_comanda d ON b.detalle_comanda_id = d.id
        WHERE b.sesion_mesa_id = %s AND b.consolidado_en_envio_id IS NULL AND d.estado = 'borrador'
        ORDER BY b.creado_at ASC;
    """, (int(sesion_mesa_id),))
    rows = cur.fetchall()
    if not rows:
        return {"enviados": 0, "envios": [], "segundos_restantes": 0, "items_en_buffer": 0}

    ahora = datetime.now(timezone.utc)
    primer_creado = rows[0]['creado_at']
    if primer_creado.tzinfo is None:
        primer_creado = primer_creado.replace(tzinfo=timezone.utc)

    transcurridos = (ahora - primer_creado).total_seconds()
    segundos_restantes = max(0, int(ventana_segundos - transcurridos))

    if forzar or transcurridos >= ventana_segundos:
        item_ids = [r['detalle_comanda_id'] for r in rows]
        envios = _consolidar_detalle_ids_con_merge(cur, item_ids)
        return {
            "enviados": len(item_ids),
            "envios": envios,
            "segundos_restantes": 0,
            "consolidado": True,
            "items_en_buffer": 0,
        }

    return {
        "enviados": 0,
        "envios": [],
        "segundos_restantes": segundos_restantes,
        "consolidado": False,
        "items_en_buffer": len(rows),
    }


def _procesar_todos_los_buffers_vencidos(cur, ventana_segundos=300):
    """Busca todas las sesiones con items en buffer que ya superaron los 5 minutos y los consolida."""
    cur.execute("""
        SELECT DISTINCT b.sesion_mesa_id
        FROM buffer_pre_envio b
        JOIN detalle_comanda d ON b.detalle_comanda_id = d.id
        WHERE b.consolidado_en_envio_id IS NULL AND d.estado = 'borrador'
          AND b.creado_at <= (NOW() - (INTERVAL '1 second' * %s));
    """, (int(ventana_segundos),))
    sesiones = cur.fetchall()
    total_enviados = 0
    for s in sesiones:
        res = _procesar_buffer_sesion(cur, s['sesion_mesa_id'], forzar=True, ventana_segundos=ventana_segundos)
        total_enviados += res.get('enviados', 0)
    if total_enviados > 0:
        print(f"⏱️  [BUFFER] Auto-consolidados {total_enviados} items por vencimiento de ventana (5 min).")
    return total_enviados


@anvil.server.callable('enviar_items_a_cocina')
@anvil.server.callable('uplink_enviar_items_a_cocina')
def uplink_enviar_items_a_cocina(detalle_ids):
    """Toma una lista de detalle_comanda_ids en estado 'borrador' y los envía
    a cocina/barra aplicando la consolidación y merge inteligente por estación."""
    if not detalle_ids:
        return {"ok": True, "enviados": 0, "envios": []}
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            envios = _consolidar_detalle_ids_con_merge(cur, detalle_ids)
        conn.commit()
        total = sum(len(e['item_ids']) for e in envios)
        print(f"🍳 [UPLINK] Enviados a cocina/barra: {total} items en {len(envios)} ticket(s).")
        return {"ok": True, "enviados": total, "envios": envios}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en enviar_items_a_cocina: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('liberar_buffer_mesa')
@anvil.server.callable('uplink_liberar_buffer_mesa')
def uplink_liberar_buffer_mesa(mesa_id):
    """Fuerza la liberación y envío inmediato de todos los items en buffer de esa mesa."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM sesiones_mesa
                WHERE mesa_id = %s AND cerrada_at IS NULL
                ORDER BY abierta_at DESC LIMIT 1;
            """, (int(mesa_id),))
            sesion = cur.fetchone()
            if not sesion:
                return {"ok": False, "error": "No hay sesión activa en esta mesa"}
            res = _procesar_buffer_sesion(cur, sesion['id'], forzar=True)
        conn.commit()
        print(f"🚀 [UPLINK] Buffer liberado manualmente para Mesa {mesa_id}: {res.get('enviados', 0)} items.")
        return {"ok": True, **res}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en liberar_buffer_mesa: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('get_estado_buffer_mesa')
@anvil.server.callable('uplink_get_estado_buffer_mesa')
def uplink_get_estado_buffer_mesa(mesa_id):
    """Consulta el estado del buffer (ítems acumulados y segundos restantes) de la mesa."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM sesiones_mesa
                WHERE mesa_id = %s AND cerrada_at IS NULL
                ORDER BY abierta_at DESC LIMIT 1;
            """, (int(mesa_id),))
            sesion = cur.fetchone()
            if not sesion:
                return {"items_en_buffer": 0, "segundos_restantes": 0}
            res = _procesar_buffer_sesion(cur, sesion['id'], forzar=False)
            return res
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


# ============================================================================
# LLAMADAS AL MESERO (Bloque G — versión mínima para P2)
# ============================================================================

@anvil.server.callable('get_llamadas_pendientes')
@anvil.server.callable('uplink_get_llamadas_pendientes')
def uplink_get_llamadas_pendientes(area_codigo=None):
    """Lista las llamadas no atendidas. Si area_codigo se pasa, filtra por
    esa área (para meseros que atienden solo una)."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT l.id, l.tipo, l.creada_at, l.notas,
                       s.id AS silla_id, s.codigo_qr, s.numero_en_mesa,
                       s.es_adicional,
                       m.numero_mesa,
                       a.codigo AS area_codigo, a.nombre AS area_nombre
                FROM llamadas_mesero l
                JOIN sillas s ON l.silla_id = s.id
                LEFT JOIN mesas m ON s.mesa_id = m.id
                LEFT JOIN areas a ON m.area_id = a.id
                WHERE l.atendida_at IS NULL
                  AND (%s::text IS NULL OR a.codigo = %s::text)
                ORDER BY l.creada_at ASC;
            """, (area_codigo, area_codigo))
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"[UPLINK] Error en get_llamadas_pendientes: {e}")
        return []


@anvil.server.callable('get_llamada_estado')
@anvil.server.callable('uplink_get_llamada_estado')
def uplink_get_llamada_estado(llamada_id):
    """Devuelve el estado de una llamada (para que el cliente sepa cuando
    su solicitud fue atendida y quitar el aviso de su pantalla)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT l.id, l.tipo, l.creada_at, l.atendida_at,
                       m.nombre_completo AS atendida_por
                FROM llamadas_mesero l
                LEFT JOIN meseros m ON l.atendida_por_mesero_id = m.id
                WHERE l.id = %s;
            """, (int(llamada_id),))
            row = cur.fetchone()
        if row is None:
            return {"error": "llamada no encontrada"}
        return clean_row(row)
    finally:
        conn.close()


@anvil.server.callable('get_llamadas_recientes')
@anvil.server.callable('uplink_get_llamadas_recientes')
def uplink_get_llamadas_recientes(limit=25):
    """Lista las últimas llamadas atendidas (para el historial de meseros)."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT l.id, l.tipo, l.creada_at, l.atendida_at, l.notas,
                       s.codigo_qr, s.numero_en_mesa,
                       m.numero_mesa,
                       mes.nombre_completo AS atendida_por
                FROM llamadas_mesero l
                JOIN sillas s ON l.silla_id = s.id
                LEFT JOIN mesas m ON s.mesa_id = m.id
                LEFT JOIN meseros mes ON l.atendida_por_mesero_id = mes.id
                WHERE l.atendida_at IS NOT NULL
                ORDER BY l.atendida_at DESC LIMIT %s;
            """, (int(limit),))
            rows = cur.fetchall()
        conn.close()
        return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"[UPLINK] Error en get_llamadas_recientes: {e}")
        return []


@anvil.server.callable('atender_llamada')
@anvil.server.callable('uplink_atender_llamada')
def uplink_atender_llamada(llamada_id, mesero_id=None):
    """Marca la llamada como atendida por el mesero (primero que responde)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            mid = int(mesero_id) if mesero_id else _get_mesero_default_id(cur)
            cur.execute("""
                UPDATE llamadas_mesero
                SET atendida_at = NOW(), atendida_por_mesero_id = %s
                WHERE id = %s AND atendida_at IS NULL
                RETURNING id;
            """, (mid, int(llamada_id)))
            row = cur.fetchone()
        conn.commit()
        atendida = row is not None
        print(f"✅ [UPLINK] Llamada #{llamada_id} atendida por mesero_id={mid}"
              if atendida else
              f"⚠️  [UPLINK] Llamada #{llamada_id} ya estaba atendida")
        return {"ok": True, "atendida": atendida}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en atender_llamada: {e}")
        return {"error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('get_meseros_activos')
@anvil.server.callable('uplink_get_meseros_activos')
def uplink_get_meseros_activos(area_id=None):
    """Lista todos los meseros activos para asignación de atención y turnos."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if area_id:
                cur.execute("""
                    SELECT id, nombre_completo, codigo_empleado, area_asignada_id
                    FROM meseros
                    WHERE activo = TRUE AND (area_asignada_id = %s OR area_asignada_id IS NULL)
                    ORDER BY id ASC;
                """, (int(area_id),))
            else:
                cur.execute("""
                    SELECT id, nombre_completo, codigo_empleado, area_asignada_id
                    FROM meseros
                    WHERE activo = TRUE
                    ORDER BY id ASC;
                """)
            rows = cur.fetchall()
            return [clean_row(r) for r in rows]
    except Exception as e:
        print(f"[UPLINK] Error en get_meseros_activos: {e}")
        return []
    finally:
        conn.close()


@anvil.server.callable('crear_llamada_mesero')
@anvil.server.callable('uplink_crear_llamada_mesero')
def uplink_crear_llamada_mesero(mesa_num, silla_num, tipo='llamar_mesero',
                                 notas=None):
    """Cliente pulsa botón 'llamar mesero' / 'solicitar cuenta' en el Menu."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            silla = _silla_por_mesa_y_numero(cur, int(mesa_num), int(silla_num))
            if silla is None:
                return {"error": "silla no encontrada"}
            cur.execute("""
                INSERT INTO llamadas_mesero (silla_id, tipo, notas)
                VALUES (%s, %s, %s) RETURNING id;
            """, (silla['silla_id'], str(tipo), notas))
            llamada_id = int(cur.fetchone()['id'])
        conn.commit()
        print(f"🔔 [UPLINK] Llamada tipo={tipo} creada #{llamada_id} "
              f"Mesa {mesa_num} Silla {silla_num}")
        return {"ok": True, "llamada_id": llamada_id}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en crear_llamada_mesero: {e}")
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


@anvil.server.callable('cambiar_estado_item_cocina')
@anvil.server.callable('uplink_cambiar_estado_item_cocina')
def uplink_cambiar_estado_item_cocina(detalle_id, nuevo_estado):
    """Actualiza el estado de preparación de un platillo individual en cocina/barra en PostgreSQL.
    nuevo_estado: 'preparando'/'en_preparacion' (fuego), 'listo' (pase), 'servido' (entregado), 'recibido'/'enviado_cocina' (reabrir)."""
    detalle_id = int(detalle_id)
    if nuevo_estado in ('preparando', 'en_preparacion', 'fuego'):
        db_estado = 'en_preparacion'
    elif nuevo_estado in ('listo', 'pase'):
        db_estado = 'listo'
    elif nuevo_estado in ('servido', 'entregado'):
        db_estado = 'servido'
    else:
        db_estado = 'enviado_cocina'

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if db_estado == 'en_preparacion':
                cur.execute("""
                    UPDATE detalle_comanda
                    SET estado = 'en_preparacion'
                    WHERE id = %s
                    RETURNING envio_cocina_id;
                """, (detalle_id,))
                row = cur.fetchone()
                if row and row['envio_cocina_id']:
                    cur.execute("""
                        UPDATE envios_cocina
                        SET timestamp_en_preparacion = COALESCE(timestamp_en_preparacion, NOW())
                        WHERE id = %s;
                    """, (row['envio_cocina_id'],))
            elif db_estado == 'listo':
                cur.execute("""
                    UPDATE detalle_comanda
                    SET estado = 'listo', hora_listo = NOW()
                    WHERE id = %s
                    RETURNING envio_cocina_id;
                """, (detalle_id,))
                row = cur.fetchone()
                if row and row['envio_cocina_id']:
                    cur.execute("""
                        SELECT COUNT(*) AS pend
                        FROM detalle_comanda
                        WHERE envio_cocina_id = %s AND estado NOT IN ('listo', 'servido', 'cancelado');
                    """, (row['envio_cocina_id'],))
                    cnt = cur.fetchone()
                    if cnt and cnt['pend'] == 0:
                        cur.execute("""
                            UPDATE envios_cocina
                            SET timestamp_listo = NOW()
                            WHERE id = %s;
                        """, (row['envio_cocina_id'],))
            elif db_estado == 'servido':
                cur.execute("""
                    UPDATE detalle_comanda
                    SET estado = 'servido', hora_servido = NOW()
                    WHERE id = %s
                    RETURNING envio_cocina_id;
                """, (detalle_id,))
                row = cur.fetchone()
                if row and row['envio_cocina_id']:
                    cur.execute("""
                        UPDATE envios_cocina
                        SET timestamp_recogido = NOW()
                        WHERE id = %s;
                    """, (row['envio_cocina_id'],))
            elif db_estado == 'enviado_cocina':
                cur.execute("""
                    UPDATE detalle_comanda
                    SET estado = 'enviado_cocina', hora_listo = NULL, hora_servido = NULL
                    WHERE id = %s;
                """, (detalle_id,))
        conn.commit()
        print(f"🍳 [UPLINK] Item #{detalle_id} actualizado en BD → estado='{db_estado}'")
        return {"success": True, "detalle_id": detalle_id, "estado": db_estado}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en uplink_cambiar_estado_item_cocina: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('despachar_ticket_cocina')
@anvil.server.callable('uplink_despachar_ticket_cocina')
def uplink_despachar_ticket_cocina(mesa_num, silla_num=None, nuevo_estado='listo'):
    """Marca todos los platillos activos de una comanda/ticket como 'listo' o 'servido'."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            mesa_num = int(mesa_num)
            if silla_num is not None and str(silla_num) not in ('TODAS', '', 'None'):
                s_int = int(silla_num)
                if s_int == 0:
                    cur.execute("""
                        UPDATE detalle_comanda d
                        SET estado = %s,
                            hora_listo = CASE WHEN %s = 'listo' THEN NOW() ELSE d.hora_listo END,
                            hora_servido = CASE WHEN %s = 'servido' THEN NOW() ELSE d.hora_servido END
                        FROM comandas c
                        JOIN sesiones_mesa sm ON c.sesion_mesa_id = sm.id AND sm.cerrada_at IS NULL
                        WHERE d.comanda_id = c.id
                          AND sm.mesa_id = (SELECT id FROM mesas WHERE numero_mesa = %s)
                          AND d.es_al_centro = TRUE
                          AND d.estado IN ('enviado_cocina', 'en_preparacion', 'listo');
                    """, (nuevo_estado, nuevo_estado, nuevo_estado, mesa_num))
                else:
                    cur.execute("""
                        UPDATE detalle_comanda d
                        SET estado = %s,
                            hora_listo = CASE WHEN %s = 'listo' THEN NOW() ELSE d.hora_listo END,
                            hora_servido = CASE WHEN %s = 'servido' THEN NOW() ELSE d.hora_servido END
                        FROM comandas c
                        JOIN sesiones_mesa sm ON c.sesion_mesa_id = sm.id AND sm.cerrada_at IS NULL
                        JOIN sillas s ON d.para_silla_id = s.id
                        WHERE d.comanda_id = c.id
                          AND sm.mesa_id = (SELECT id FROM mesas WHERE numero_mesa = %s)
                          AND s.numero_en_mesa = %s
                          AND d.estado IN ('enviado_cocina', 'en_preparacion', 'listo');
                    """, (nuevo_estado, nuevo_estado, nuevo_estado, mesa_num, s_int))
            else:
                cur.execute("""
                    UPDATE detalle_comanda d
                    SET estado = %s,
                        hora_listo = CASE WHEN %s = 'listo' THEN NOW() ELSE d.hora_listo END,
                        hora_servido = CASE WHEN %s = 'servido' THEN NOW() ELSE d.hora_servido END
                    FROM comandas c
                    JOIN sesiones_mesa sm ON c.sesion_mesa_id = sm.id AND sm.cerrada_at IS NULL
                    WHERE d.comanda_id = c.id
                      AND sm.mesa_id = (SELECT id FROM mesas WHERE numero_mesa = %s)
                      AND d.estado IN ('enviado_cocina', 'en_preparacion', 'listo');
                """, (nuevo_estado, nuevo_estado, nuevo_estado, mesa_num))
        conn.commit()
        print(f"🔔 [UPLINK] Ticket Mesa {mesa_num} Silla {silla_num} despachado → '{nuevo_estado}'")
        return {"success": True}
    except Exception as e:
        conn.rollback()
        print(f"[UPLINK] Error en despachar_ticket_cocina: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@anvil.server.callable('get_kds_comandas')
@anvil.server.callable('uplink_get_kds')
def uplink_get_kds():
    """Retorna las cuentas de la terraza con estado vivo para el monitor KDS."""
    return uplink_get_cuentas_terraza()


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
