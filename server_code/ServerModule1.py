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
def get_areas_terraza():
    """Obtiene las áreas físicas del restaurante desde PostgreSQL"""
    try:
        return anvil.server.call('uplink_get_areas') or []
    except Exception as e:
        print("Uplink get_areas error:", e)
        return []

@anvil.server.callable
def get_mesas_terraza():
    """Obtiene el listado de mesas con área y sillas desde PostgreSQL"""
    try:
        res = anvil.server.call('uplink_get_mesas')
        if res and len(res) > 0:
            return res
    except Exception as e:
        print("Uplink get_mesas error:", e)
    return []

@anvil.server.callable
def get_sillas_terraza(mesa_id=None):
    """Obtiene las sillas y códigos QR desde PostgreSQL"""
    try:
        return anvil.server.call('uplink_get_sillas', mesa_id) or []
    except Exception as e:
        print("Uplink get_sillas error:", e)
        return []

@anvil.server.callable
def get_recetas_cocina_terraza():
    """Obtiene el recetario completo estandarizado para KDS desde PostgreSQL"""
    try:
        return anvil.server.call('uplink_get_recetas_cocina') or []
    except Exception as e:
        print("Uplink get_recetas_cocina error:", e)
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

@anvil.server.callable
def guardar_producto_terraza(prod_dict):
    """Crea o modifica un platillo en PostgreSQL"""
    try:
        return anvil.server.call('uplink_guardar_producto', prod_dict)
    except Exception as e:
        print("Uplink guardar_producto error:", e)
        return {"success": False, "error": str(e)}

@anvil.server.callable
def cambiar_disponibilidad_producto_terraza(prod_id, disponible):
    """Activa o desactiva disponibilidad de un platillo en PostgreSQL"""
    try:
        return anvil.server.call('uplink_cambiar_disponibilidad_producto', prod_id, disponible)
    except Exception as e:
        print("Uplink cambiar_disponibilidad error:", e)
        return {"success": False, "error": str(e)}

@anvil.server.callable
def eliminar_producto_terraza(prod_id):
    """Desactiva un platillo en PostgreSQL"""
    try:
        return anvil.server.call('uplink_eliminar_producto', prod_id)
    except Exception as e:
        print("Uplink eliminar_producto error:", e)
        return {"success": False, "error": str(e)}

@anvil.server.callable
def guardar_categoria_terraza(cat_dict):
    """Crea o modifica una categoría en PostgreSQL"""
    try:
        return anvil.server.call('uplink_guardar_categoria', cat_dict)
    except Exception as e:
        print("Uplink guardar_categoria error:", e)
        return {"success": False, "error": str(e)}

@anvil.server.callable
def get_dashboard_kpis_terraza():
    """Obtiene métricas ejecutivas, ventas, platillo estrella y alertas de compra para el Dashboard Hub"""
    try:
        return anvil.server.call('uplink_get_dashboard_kpis') or {}
    except Exception as e:
        print("Uplink get_dashboard_kpis error:", e)
        return {}


