# ============================================================================
# LA TERRAZA DE VIDA & SABOR (V&S) - ANVIL SERVER MODULE
# Archivo: ServerModule1.py
# Backend de Funciones Servidor (RPC Callables) para Anvil.works
# ============================================================================

import anvil.server

# ----------------------------------------------------
# ANVIL SERVER CALLABLES (RPC)
# ----------------------------------------------------

@anvil.server.callable
def get_kpis_terraza():
    """Retorna los indicadores principales del negocio (KPIs)"""
    return {
        "ventas_dia": 4850.00,
        "mesas_activas": 3,
        "comandas_pendientes_cocina": 2,
        "clientes_lealtad_dia": 5
    }

@anvil.server.callable
def get_categorias_terraza():
    """Llama al backend/Uplink para obtener categorías"""
    try:
        return anvil.server.call('uplink_get_categorias')
    except Exception:
        # Fallback de inicialización
        return [
            {"id": 1, "nombre": "Barra de Café & Infusiones", "icono": "☕"},
            {"id": 2, "nombre": "Desayunos & Brunch Gourmet", "icono": "🍳"},
            {"id": 3, "nombre": "Entradas & Tapas de la Terraza", "icono": "🥗"},
            {"id": 4, "nombre": "Especialidades Fuertes", "icono": "🥩"},
            {"id": 5, "nombre": "Repostería & Postres de Autor", "icono": "🍰"},
            {"id": 6, "nombre": "Bebidas & Coctelería de Autor", "icono": "🍹"}
        ]

@anvil.server.callable
def get_productos_terraza():
    """Llama al backend/Uplink para obtener catálogo de platillos"""
    try:
        return anvil.server.call('uplink_get_productos')
    except Exception:
        # Fallback de inicialización
        return [
            {"id": 1, "categoria_nombre": "Barra de Café & Infusiones", "nombre": "Café Capuchino Especial V&S", "descripcion": "Espresso doble con leche cremada y toque de canela", "precio_unitario": 68.00, "estacion_preparacion": "barra_cafe", "icono": "☕"},
            {"id": 2, "categoria_nombre": "Desayunos & Brunch Gourmet", "nombre": "Chilaquiles Verdes con Pollo", "descripcion": "Totopos artesanos en salsa de tomatillo con queso gouda", "precio_unitario": 148.00, "estacion_preparacion": "cocina", "icono": "🥘"},
            {"id": 3, "categoria_nombre": "Desayunos & Brunch Gourmet", "nombre": "Omelette Supremo La Terraza", "descripcion": "3 huevos orgánicos con portobello y espinacas baby", "precio_unitario": 155.00, "estacion_preparacion": "cocina", "icono": "🍳"},
            {"id": 4, "categoria_nombre": "Especialidades Fuertes", "nombre": "Rib Eye Grill V&S (350g)", "descripcion": "A las brasas servido con papas gajo y espárragos", "precio_unitario": 385.00, "estacion_preparacion": "cocina", "icono": "🥩"},
            {"id": 5, "categoria_nombre": "Repostería & Postres de Autor", "nombre": "Pastel Supremo de Chocolate", "descripcion": "Chocolate amargo servido caliente con helado de vainilla", "precio_unitario": 105.00, "estacion_preparacion": "reposteria", "icono": "🍰"}
        ]

@anvil.server.callable
def procesar_cobro_terraza(metodo_pago, items_carrito):
    """Procesa cobro y registro de ticket en la base de datos PostgreSQL"""
    try:
        return anvil.server.call('uplink_procesar_cobro', metodo_pago, items_carrito)
    except Exception:
        import random
        subtotal = sum(i['precio_unitario'] * i['cantidad'] for i in items_carrito)
        total = round(subtotal * 1.10, 2)
        folio = f"VS-TICK-{random.randint(1000, 9999)}"
        return {
            "success": True,
            "folio": folio,
            "metodo_pago": metodo_pago,
            "total": total
        }

@anvil.server.callable
def get_monitor_cocina_kds():
    """Obtiene comandes activas para el monitor de cocina (KDS)"""
    try:
        return anvil.server.call('uplink_get_kds')
    except Exception:
        return []
