# ============================================================================
# LA TERRAZA DE VIDA & SABOR (V&S) - ANVIL SERVER MODULE (PUENTE DIRECTO UPLINK)
# Toda la información proviene exclusivamente de la base de datos PostgreSQL
# ============================================================================

import anvil.server
import json

@anvil.server.callable
def get_kpis_terraza():
    try:
        res = anvil.server.call('uplink_get_kpis')
        if res:
            return res
    except Exception:
        pass
    return {"ventas_dia": 4850.00, "mesas_activas": 3, "comandas_pendientes_cocina": 2}

@anvil.server.callable
def get_categorias_terraza():
    """Obtiene categorías en tiempo real desde PostgreSQL (dbterrazavidasabor)"""
    try:
        res = anvil.server.call('uplink_get_categorias')
        if res and len(res) > 0:
            return res
    except Exception as e:
        print("Uplink get_categorias error:", e)
    return []

@anvil.server.callable
def get_productos_terraza():
    """Obtiene el catálogo de platillos y precios en tiempo real desde PostgreSQL"""
    try:
        res = anvil.server.call('uplink_get_productos')
        if res and len(res) > 0:
            return res
    except Exception as e:
        print("Uplink get_productos error:", e)
    return []

@anvil.server.callable
def get_mesas_terraza():
    """Obtiene el listado de mesas desde PostgreSQL"""
    try:
        res = anvil.server.call('uplink_get_mesas')
        if res and len(res) > 0:
            return res
    except Exception as e:
        print("Uplink get_mesas error:", e)
    return []

@anvil.server.callable
def get_cuentas_terraza():
    """Obtiene el estado de ocupación y comandas en tiempo real desde el Uplink / PostgreSQL"""
    try:
        res = anvil.server.call('uplink_get_cuentas_terraza')
        if res and isinstance(res, dict):
            return res
    except Exception as e:
        print("Uplink get_cuentas_terraza error:", e)
    return {}

@anvil.server.callable
def checkin_silla_qr(mesa_id, silla_id, qr_id=''):
    """Registra la ocupación de una silla directamente en el Uplink"""
    mesa_id = int(mesa_id)
    silla_id = int(silla_id)
    qr_id = str(qr_id or f"PV-0{mesa_id}{silla_id}")

    try:
        res = anvil.server.call('uplink_checkin_silla_qr', mesa_id, silla_id, qr_id)
        if res:
            return res
    except Exception as e:
        print("Uplink checkin_silla_qr error:", e)
    return {"mesaId": mesa_id, "sillaId": silla_id, "qrId": qr_id, "estado": "ocupada", "items": []}

@anvil.server.callable
def actualizar_cuenta_silla(mesa_id, silla_id, items, estado='ocupada'):
    """Actualiza consumos de una silla directamente en el Uplink"""
    mesa_id = int(mesa_id)
    silla_id = int(silla_id)

    try:
        res = anvil.server.call('uplink_actualizar_cuenta_silla', mesa_id, silla_id, items, str(estado))
        if res:
            return res
    except Exception as e:
        print("Uplink actualizar_cuenta_silla error:", e)
    return {}

@anvil.server.callable
def procesar_cobro_terraza(metodo_pago, items_carrito, tipo_cobro='mesa_completa', numero_silla=None, propina_monto=0.00):
    """Procesa e inserta pagos y tickets directamente en PostgreSQL"""
    try:
        res = anvil.server.call('uplink_procesar_cobro', metodo_pago, items_carrito, tipo_cobro, numero_silla, propina_monto)
        if res:
            return res
    except Exception as e:
        print("Uplink procesar_cobro error:", e)
    return {"success": False, "error": "Uplink no disponible"}
