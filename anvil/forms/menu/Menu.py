from ._anvil_designer import MenuTemplate
import anvil
import anvil.js

class Menu(MenuTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      anvil.js.window.anvilAppNav = self.navegar_modulo
      anvil.js.window.anvilCheckinSilla = self.hacer_checkin_silla
      anvil.js.window.anvilSyncCuenta = self.sincronizar_cuenta_servidor
      anvil.js.window.anvilRecargarCatalogo = self.cargar_catalogo_db
      anvil.js.window.anvilGuardarProducto = self.guardar_producto
      anvil.js.window.anvilCambiarDisponibilidad = self.cambiar_disponibilidad
    except Exception:
      pass

    try:
      url_hash = anvil.get_url_hash()
      mesa_num = 1
      silla_num = 1
      qr_str = ""

        # Extraer mesa, silla y qr desde la URL
        q_idx = url_hash.find('?')
        query_str = url_hash[q_idx+1:] if q_idx != -1 else url_hash
        params = {}
        for part in query_str.split('&'):
          if '=' in part:
            k, v = part.split('=', 1)
            params[k.strip().lower()] = v.strip()

        if 'mesa' in params:
          try: mesa_num = int(params['mesa'])
          except: pass
        if 'silla' in params:
          try: silla_num = int(params['silla'])
          except: pass
        if 'qr' in params:
          qr_str = params['qr']
        else:
          qr_str = f"PV-0{mesa_num}{silla_num}"

      elif isinstance(url_hash, dict) and url_hash:
        try: mesa_num = int(url_hash.get('mesa', 1))
        except: pass
        try: silla_num = int(url_hash.get('silla', 1))
        except: pass
        qr_str = url_hash.get('qr', f"PV-0{mesa_num}{silla_num}")

      # Registrar check-in de inmediato en el servidor
      if mesa_num and silla_num:
        self.hacer_checkin_silla(mesa_num, silla_num, qr_str)

      # Cargar catálogo de platillos y categorías directamente desde PostgreSQL
      self.cargar_catalogo_db()
    except Exception as e:
      print(f"Error procesando check-in en Menu: {e}")

  def cargar_catalogo_db(self):
    try:
      import anvil.server
      import json
      prods = anvil.server.call('get_productos_terraza')
      cats = anvil.server.call('get_categorias_terraza')
      print(f"📦 [MENU] Catálogo cargado de DB: {len(prods) if prods else 0} platillos, {len(cats) if cats else 0} categorías")
      if prods and hasattr(anvil.js.window, 'setMenuDataFromPostgreSQL'):
        anvil.js.window.setMenuDataFromPostgreSQL(json.dumps(prods), json.dumps(cats) if cats else "[]")
      return True
    except Exception as e:
      print(f"Error cargando catálogo desde PostgreSQL: {e}")
      return False

  def guardar_producto(self, prod_dict):
    try:
      import anvil.server
      import json
      if isinstance(prod_dict, str):
        prod_dict = json.loads(prod_dict)
      res = anvil.server.call('guardar_producto_terraza', prod_dict)
      self.cargar_catalogo_db()
      return res
    except Exception as e:
      print(f"Error guardando producto: {e}")
      return {"success": False, "error": str(e)}

  def cambiar_disponibilidad(self, prod_id, disponible):
    try:
      import anvil.server
      res = anvil.server.call('cambiar_disponibilidad_producto_terraza', int(prod_id), bool(disponible))
      self.cargar_catalogo_db()
      return res
    except Exception as e:
      print(f"Error cambiando disponibilidad: {e}")
      return {"success": False, "error": str(e)}

  def hacer_checkin_silla(self, mesa_id, silla_id, qr_id=''):
    try:
      import anvil.server
      res = anvil.server.call('checkin_silla_qr', int(mesa_id), int(silla_id), str(qr_id))
      return res
    except Exception as e:
      print(f"Error en checkin_silla: {e}")
      return None

  def sincronizar_cuenta_servidor(self, mesa_id, silla_id, items, estado='ocupada'):
    try:
      import anvil.server
      import json
      if isinstance(items, str):
        try:
          items_clean = json.loads(items)
        except Exception:
          items_clean = []
      elif isinstance(items, list):
        items_clean = items
      else:
        try:
          # Convertir proxy o iterable de JS
          items_clean = json.loads(json.dumps(items))
        except Exception:
          items_clean = []
      print(f"📡 [MENU.PY] sincronizando con servidor: Mesa {mesa_id} Silla {silla_id} -> {len(items_clean)} items ({estado})")
      res = anvil.server.call('actualizar_cuenta_silla', int(mesa_id), int(silla_id), items_clean, str(estado))
      return res
    except Exception as e:
      print(f"Error en sincronizar_cuenta_servidor: {e}")
      return None

  def navegar_modulo(self, modulo_nombre):
    target_form = 'POSMesero'
    if modulo_nombre in ['pos_mesero', 'croquis', 'palapa']:
      target_form = 'POSMesero'
    elif modulo_nombre in ['menu', 'cliente_qr']:
      target_form = 'Menu'
    elif modulo_nombre in ['monitor_cocina', 'kds']:
      target_form = 'MonitorCocina'
    elif modulo_nombre in ['monitor_fiscal', 'fiscal']:
      target_form = 'MonitorFiscal'
    elif modulo_nombre in ['clientes_lealtad', 'rewards']:
      target_form = 'ClientesLealtad'
    
    anvil.open_form(target_form)
