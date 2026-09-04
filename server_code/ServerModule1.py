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

SEED_MESAS = [
  {"id": 1, "area_nombre": "Terraza Principal", "numero_mesa": 1, "nombre": "Mesa 1", "capacidad_sillas": 4, "estado": "disponible"},
  {"id": 2, "area_nombre": "Terraza Principal", "numero_mesa": 2, "nombre": "Mesa 2", "capacidad_sillas": 4, "estado": "disponible"},
  {"id": 3, "area_nombre": "Terraza Principal", "numero_mesa": 3, "nombre": "Mesa 3", "capacidad_sillas": 4, "estado": "ocupada"},
  {"id": 4, "area_nombre": "Jardín Exterior", "numero_mesa": 4, "nombre": "Mesa 4", "capacidad_sillas": 4, "estado": "disponible"},
  {"id": 5, "area_nombre": "Jardín Exterior", "numero_mesa": 5, "nombre": "Mesa 5", "capacidad_sillas": 6, "estado": "disponible"},
  {"id": 6, "area_nombre": "Barra de Café", "numero_mesa": 6, "nombre": "Mesa 6", "capacidad_sillas": 2, "estado": "disponible"}
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
def get_mesas_terraza():
  try:
    res = anvil.server.call('uplink_get_mesas')
    if res and len(res) > 0:
      return res
  except Exception as e:
    print('Uplink get_mesas exception:', e)
  return SEED_MESAS

# Almacenamiento centralizado de cuentas y sillas de La Terraza (sincronizado en tiempo real)
CUENTAS_TERRAZA = {
  "1-1": {"mesaId": 1, "sillaId": 1, "qrId": "PV-011", "estado": "disponible", "comensalNombre": "Silla 1", "items": []},
  "1-2": {"mesaId": 1, "sillaId": 2, "qrId": "PV-012", "estado": "disponible", "comensalNombre": "Silla 2", "items": []},
  "1-3": {"mesaId": 1, "sillaId": 3, "qrId": "PV-013", "estado": "disponible", "comensalNombre": "Silla 3", "items": []},
  "1-4": {"mesaId": 1, "sillaId": 4, "qrId": "PV-014", "estado": "disponible", "comensalNombre": "Silla 4", "items": []},
  "2-1": {"mesaId": 2, "sillaId": 1, "qrId": "PV-021", "estado": "disponible", "comensalNombre": "Silla 1", "items": []},
  "2-2": {"mesaId": 2, "sillaId": 2, "qrId": "PV-022", "estado": "disponible", "comensalNombre": "Silla 2", "items": []},
  "2-3": {"mesaId": 2, "sillaId": 3, "qrId": "PV-023", "estado": "disponible", "comensalNombre": "Silla 3", "items": []},
  "2-4": {"mesaId": 2, "sillaId": 4, "qrId": "PV-024", "estado": "disponible", "comensalNombre": "Silla 4", "items": []},
  "3-1": {"mesaId": 3, "sillaId": 1, "qrId": "PV-031", "estado": "ocupada", "comensalNombre": "Silla 1", "items": [{"id": 501, "nombre": "Omelette de Claras con Champiñones", "notas": "Sin queso", "precio": 155.00, "cantidad": 1, "mesaId": 3, "sillaNum": 1, "hora": "09:15 AM", "enviadoCocina": True, "horaEnvioCocina": "09:15 AM"}]},
  "3-2": {"mesaId": 3, "sillaId": 2, "qrId": "PV-032", "estado": "ocupada", "comensalNombre": "Silla 2", "items": [{"id": 502, "nombre": "Café con Leche / Capuchino", "notas": "Con canela", "precio": 68.00, "cantidad": 1, "mesaId": 3, "sillaNum": 2, "hora": "09:20 AM", "enviadoCocina": True, "horaEnvioCocina": "09:20 AM"}]},
  "3-3": {"mesaId": 3, "sillaId": 3, "qrId": "PV-033", "estado": "ocupada", "comensalNombre": "Silla 3", "items": []},
  "3-4": {"mesaId": 3, "sillaId": 4, "qrId": "PV-034", "estado": "ocupada", "comensalNombre": "Silla 4", "items": []},
}

@anvil.server.callable
def get_cuentas_terraza():
  try:
    res = anvil.server.call('uplink_get_cuentas_terraza')
    if res and isinstance(res, dict):
      return res
  except Exception as e:
    pass
  return CUENTAS_TERRAZA

@anvil.server.callable
def checkin_silla_qr(mesa_id, silla_id, qr_id=''):
  try:
    res = anvil.server.call('uplink_checkin_silla_qr', int(mesa_id), int(silla_id), str(qr_id))
    if res:
      return res
  except Exception:
    pass

  key = f"{mesa_id}-{silla_id}"
  if key not in CUENTAS_TERRAZA:
    CUENTAS_TERRAZA[key] = {
      "mesaId": int(mesa_id),
      "sillaId": int(silla_id),
      "qrId": qr_id or f"PV-0{mesa_id}{silla_id}",
      "estado": "ocupada",
      "comensalNombre": f"Comensal Silla {silla_id}",
      "items": []
    }
  else:
    CUENTAS_TERRAZA[key]["estado"] = "ocupada"
    if qr_id:
      CUENTAS_TERRAZA[key]["qrId"] = qr_id
  return CUENTAS_TERRAZA[key]

@anvil.server.callable
def actualizar_cuenta_silla(mesa_id, silla_id, items, estado='ocupada'):
  try:
    res = anvil.server.call('uplink_actualizar_cuenta_silla', int(mesa_id), int(silla_id), items, str(estado))
    if res:
      return res
  except Exception:
    pass

  key = f"{mesa_id}-{silla_id}"
  if key in CUENTAS_TERRAZA:
    CUENTAS_TERRAZA[key]["items"] = items
    CUENTAS_TERRAZA[key]["estado"] = estado
  else:
    CUENTAS_TERRAZA[key] = {
      "mesaId": int(mesa_id),
      "sillaId": int(silla_id),
      "qrId": f"PV-0{mesa_id}{silla_id}",
      "estado": estado,
      "comensalNombre": f"Comensal Silla {silla_id}",
      "items": items
    }
  return CUENTAS_TERRAZA

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
