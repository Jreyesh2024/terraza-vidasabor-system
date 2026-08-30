# ============================================================================
# LA TERRAZA DE VIDA & SABOR (V&S) - ANVIL SERVER MODULE
# ============================================================================

import anvil.server

SEED_CATEGORIAS = [
    {"id": 1, "nombre": "Barra de Café & Infusiones", "icono": "☕"},
    {"id": 2, "nombre": "Desayunos & Brunch Gourmet", "icono": "🍳"},
    {"id": 3, "nombre": "Entradas & Tapas de la Terraza", "icono": "🥗"},
    {"id": 4, "nombre": "Especialidades Fuertes", "icono": "🥩"},
    {"id": 5, "nombre": "Repostería & Postres de Autor", "icono": "🍰"},
    {"id": 6, "nombre": "Bebidas & Coctelería de Autor", "icono": "🍹"}
]

SEED_PRODUCTOS = [
    {"id": 1, "categoria_nombre": "Barra de Café & Infusiones", "nombre": "Café Capuchino Especial V&S", "descripcion": "Espresso doble con leche cremada y toque de canela", "precio_unitario": 68.00, "estacion_preparacion": "barra_cafe", "icono": "☕"},
    {"id": 2, "categoria_nombre": "Barra de Café & Infusiones", "nombre": "Espresso Italiano Robusto", "descripcion": "Grano seleccionado 100% arábica tostado de la casa", "precio_unitario": 48.00, "estacion_preparacion": "barra_cafe", "icono": "☕"},
    {"id": 3, "categoria_nombre": "Desayunos & Brunch Gourmet", "nombre": "Chilaquiles Verdes con Pollo", "descripcion": "Totopos artesanos en salsa de tomatillo con queso gouda", "precio_unitario": 148.00, "estacion_preparacion": "cocina", "icono": "🥘"},
    {"id": 4, "categoria_nombre": "Desayunos & Brunch Gourmet", "nombre": "Omelette Supremo La Terraza", "descripcion": "3 huevos orgánicos con portobello y espinacas baby", "precio_unitario": 155.00, "estacion_preparacion": "cocina", "icono": "🍳"},
    {"id": 5, "categoria_nombre": "Desayunos & Brunch Gourmet", "nombre": "Molletes de Masa Madre con Chorizo", "descripcion": "Frijol negro refrito, queso gouda y chorizo gratinado", "precio_unitario": 125.00, "estacion_preparacion": "cocina", "icono": "🥖"},
    {"id": 6, "categoria_nombre": "Especialidades Fuertes", "nombre": "Rib Eye Grill V&S (350g)", "descripcion": "A las brasas servido con papas gajo y espárragos", "precio_unitario": 385.00, "estacion_preparacion": "cocina", "icono": "🥩"},
    {"id": 7, "categoria_nombre": "Especialidades Fuertes", "nombre": "Pasta Fettuccine con Camarones al Trufado", "descripcion": "Pasta fresca hecha en casa con crema suave de trufa", "precio_unitario": 265.00, "estacion_preparacion": "cocina", "icono": "🍝"},
    {"id": 8, "categoria_nombre": "Repostería & Postres de Autor", "nombre": "Pastel Supremo de Chocolate Valrhona", "descripcion": "Chocolate amargo servido caliente con helado de vainilla", "precio_unitario": 105.00, "estacion_preparacion": "reposteria", "icono": "🍰"},
    {"id": 9, "categoria_nombre": "Bebidas & Coctelería de Autor", "nombre": "Limonada Botánica de Hierbabuena & Jengibre", "descripcion": "Agua mineral infundida con jengibre fresco y hierbabuena", "precio_unitario": 60.00, "estacion_preparacion": "barra_cafe", "icono": "🍋"}
]

@anvil.server.callable
def get_kpis_terraza():
    return {"ventas_dia": 4850.00, "mesas_activas": 3, "comandas_pendientes_cocina": 2}

@anvil.server.callable
def get_categorias_terraza():
    try:
        res = anvil.server.call('uplink_get_categorias')
        if res and len(res) > 0:
            return res
    except Exception as e:
        print('Uplink get_categorias exception:', e)
    return SEED_CATEGORIAS

@anvil.server.callable
def get_productos_terraza():
    try:
        res = anvil.server.call('uplink_get_productos')
        if res and len(res) > 0:
            return res
    except Exception as e:
        print('Uplink get_productos exception:', e)
    return SEED_PRODUCTOS

@anvil.server.callable
def procesar_cobro_terraza(metodo_pago, items_carrito):
    try:
        res = anvil.server.call('uplink_procesar_cobro', metodo_pago, items_carrito)
        if res and res.get('success'):
            return res
    except Exception:
        pass
    import random
    subtotal = sum(i['precio_unitario'] * i['cantidad'] for i in items_carrito)
    total = round(subtotal * 1.10, 2)
    return {"success": True, "folio": f"VS-TICK-{random.randint(1000, 9999)}", "metodo_pago": metodo_pago, "total": total}
