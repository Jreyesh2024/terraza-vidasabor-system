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
# ESTADO EN MEMORIA (transición)
# ============================================================================
# CUENTAS_TERRAZA vive en memoria del uplink. Al arranque se puebla desde la BD
# leyendo mesas + sillas reales. Al ejecutar clicks/QR se actualiza en memoria.
# En el Bloque B del roadmap se sustituirá por queries a ocupaciones_silla +
# sesiones_mesa + detalle_comanda (persistencia real).
# ============================================================================
CUENTAS_TERRAZA = {}


def _init_cuentas_desde_db():
    """Puebla CUENTAS_TERRAZA con una entrada por silla (regular y del pool)
    en estado 'disponible' e items vacíos. Se llama al arranque del uplink."""
    global CUENTAS_TERRAZA
    CUENTAS_TERRAZA = {}
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.id           AS silla_id,
                       s.mesa_id      AS mesa_id,
                       s.numero_en_mesa,
                       s.codigo_qr,
                       s.es_adicional,
                       m.numero_mesa
                FROM sillas s
                LEFT JOIN mesas m ON s.mesa_id = m.id
                WHERE s.activa = TRUE
                ORDER BY s.es_adicional, m.numero_mesa NULLS LAST, s.numero_en_mesa NULLS LAST;
            """)
            rows = cur.fetchall()
        conn.close()
        for r in rows:
            if r["es_adicional"] or r["mesa_id"] is None:
                # sillas del pool: key = 'EX-01', 'EX-02', ...
                pool_num = r["codigo_qr"].split("-")[-1]
                key = f"EX-{pool_num}"
                mesa_key = 0
                silla_key = 0
            else:
                # sillas regulares: key = '<mesaNum>-<sillaNumEnMesa>'
                mesa_key = int(r["numero_mesa"])
                silla_key = int(r["numero_en_mesa"])
                key = f"{mesa_key}-{silla_key}"
            CUENTAS_TERRAZA[key] = {
                "mesaId": mesa_key,
                "sillaId": silla_key,
                "qrId": r["codigo_qr"],
                "estado": "disponible",
                "comensalNombre": (f"Silla {silla_key}" if silla_key else f"Extra {pool_num}"),
                "items": [],
                "esAdicional": bool(r["es_adicional"]),
            }
        print(f"✅ [UPLINK] CUENTAS_TERRAZA inicializado con {len(CUENTAS_TERRAZA)} sillas desde BD.")
    except Exception as e:
        print(f"⚠️  [UPLINK] No pude inicializar CUENTAS_TERRAZA desde BD: {e}")


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
    """Mesas con su área y sillas (schema v2). El estado 'ocupada/disponible' de
    cada silla se toma de CUENTAS_TERRAZA en memoria (Bloque B lo pasará a BD)."""
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
                               'es_adicional',    s.es_adicional
                           ) ORDER BY s.numero_en_mesa
                       ) FILTER (WHERE s.id IS NOT NULL), '[]'::json) AS sillas
                FROM mesas m
                LEFT JOIN areas a  ON m.area_id = a.id
                LEFT JOIN sillas s ON m.id = s.mesa_id AND s.activa = TRUE
                WHERE m.activa = TRUE
                GROUP BY m.id, a.nombre, a.icono, a.orden_display
                ORDER BY COALESCE(a.orden_display, 99), m.numero_mesa ASC;
            """)
            rows = cur.fetchall()
        conn.close()
        # Enriquecer con estado desde CUENTAS_TERRAZA (memoria)
        result = []
        for r in rows:
            d = clean_row(r)
            for s in d.get("sillas", []):
                key = f"{d['numero_mesa']}-{s['numero_silla']}"
                cta = CUENTAS_TERRAZA.get(key, {})
                s["estado"] = cta.get("estado", "disponible")
                s["comensal_nombre"] = cta.get("comensalNombre", f"Silla {s['numero_silla']}")
            result.append(d)
        return result
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
# COMANDAS EN MEMORIA (transición — Bloque B moverá a BD real)
# ============================================================================

@anvil.server.callable('get_cuentas_terraza')
@anvil.server.callable('uplink_get_cuentas_terraza')
def uplink_get_cuentas_terraza():
    return CUENTAS_TERRAZA


@anvil.server.callable('checkin_silla_qr')
@anvil.server.callable('uplink_checkin_silla_qr')
def uplink_checkin_silla_qr(mesa_id, silla_id, qr_id=''):
    mesa_id = int(mesa_id)
    silla_id = int(silla_id)
    key = f"{mesa_id}-{silla_id}"
    if key not in CUENTAS_TERRAZA:
        CUENTAS_TERRAZA[key] = {
            "mesaId": mesa_id, "sillaId": silla_id,
            "qrId": qr_id or f"PV-P-{mesa_id:02d}-{silla_id:02d}",
            "estado": "ocupada",
            "comensalNombre": f"Comensal Silla {silla_id}",
            "items": [], "esAdicional": False,
        }
    else:
        CUENTAS_TERRAZA[key]["estado"] = "ocupada"
        if qr_id:
            CUENTAS_TERRAZA[key]["qrId"] = qr_id
    print(f"🔔 [UPLINK] Check-in QR: Mesa {mesa_id} Silla {silla_id} ({qr_id}) -> OCUPADA")
    return CUENTAS_TERRAZA[key]


@anvil.server.callable('actualizar_cuenta_silla')
@anvil.server.callable('uplink_actualizar_cuenta_silla')
def uplink_actualizar_cuenta_silla(mesa_id, silla_id, items, estado='ocupada'):
    mesa_id = int(mesa_id)
    silla_id = int(silla_id)
    key = f"{mesa_id}-{silla_id}"
    if key in CUENTAS_TERRAZA:
        CUENTAS_TERRAZA[key]["items"] = items
        CUENTAS_TERRAZA[key]["estado"] = estado
    else:
        CUENTAS_TERRAZA[key] = {
            "mesaId": mesa_id, "sillaId": silla_id,
            "qrId": f"PV-P-{mesa_id:02d}-{silla_id:02d}",
            "estado": estado,
            "comensalNombre": f"Comensal Silla {silla_id}",
            "items": items, "esAdicional": False,
        }
    print(f"📝 [UPLINK] Cuenta actualizada: Mesa {mesa_id} Silla {silla_id} -> {len(items)} items ({estado})")
    return CUENTAS_TERRAZA


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

        ocupadas_count = 0
        comensales_count = 0
        comandas_recientes = []
        for key, cta in CUENTAS_TERRAZA.items():
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
    _init_cuentas_desde_db()
    anvil.server.connect(ANVIL_UPLINK_KEY)
    print("✅ ¡Conexión Anvil Uplink V&S establecida — schema v2!")
    anvil.server.wait_forever()
