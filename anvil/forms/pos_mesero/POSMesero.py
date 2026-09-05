from ._anvil_designer import POSMeseroTemplate
import anvil
import anvil.js
import anvil.server

import json

class POSMesero(POSMeseroTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      anvil.js.window.anvilAppNav = self.navegar_modulo
      anvil.js.window.navMenu = self.navegar_modulo
      anvil.js.window.anvilGetCuentasServidor = self.obtener_cuentas_servidor
      anvil.js.window.anvilSyncCuenta = self.sincronizar_cuenta_servidor
    except Exception:
      pass

    try:
      url_hash = anvil.get_url_hash()
      # Solo redirigir a Menu si la URL trae explícitamente parámetros de comensal/QR/mesa
      if isinstance(url_hash, str) and url_hash:
        url_lower = url_hash.lower()
        if 'menu' in url_lower or 'qr' in url_lower or 'mesa=' in url_lower or 'silla=' in url_lower or 'pv-' in url_lower or 'cliente' in url_lower:
          anvil.open_form('Menu')
          return
        elif 'monitor_cocina' in url_lower or 'kds' in url_lower:
          anvil.open_form('MonitorCocina')
          return
        elif 'monitor_fiscal' in url_lower or 'fiscal' in url_lower:
          anvil.open_form('MonitorFiscal')
          return
        elif 'clientes_lealtad' in url_lower or 'rewards' in url_lower:
          anvil.open_form('ClientesLealtad')
          return
      elif isinstance(url_hash, dict) and url_hash:
        if url_hash.get('form') in ['menu', 'cliente_qr'] or 'mesa' in url_hash or 'qr' in url_hash:
          anvil.open_form('Menu')
          return
    except Exception as e:
      print(f"Error procesando enrutamiento QR: {e}")

    # Sincronización inicial con el servidor
    self.sincronizar_con_servidor()

    # Cargar catálogo dinámico de productos, categorías y mesas desde PostgreSQL
    self.cargar_catalogo_pos_db()

    # Timer nativo de Anvil en segundo plano para sincronizar cada 2 segundos
    try:
      self.timer_sync = anvil.Timer(interval=2)
      self.timer_sync.set_event_handler('tick', self.timer_tick_sync)
      self.add_component(self.timer_sync)
    except Exception as e:
      print(f"Error iniciando timer sync en POSMesero: {e}")

  def timer_tick_sync(self, **event_args):
    self.sincronizar_con_servidor()

  def obtener_cuentas_servidor(self):
    try:
      res = anvil.server.call('get_cuentas_terraza')
      return json.dumps(res) if res else "{}"
    except Exception as e:
      print(f"Error obteniendo cuentas de servidor: {e}")
      return "{}"

  def sincronizar_con_servidor(self):
    try:
      cuentas = anvil.server.call('get_cuentas_terraza')
      if cuentas:
        try:
          if hasattr(anvil.js.window, 'aplicarCuentasServidor'):
            anvil.js.window.aplicarCuentasServidor(json.dumps(cuentas))
        except Exception:
          pass
    except Exception as e:
      print(f"Error sincronizando servidor en POSMesero: {e}")

  def cargar_catalogo_pos_db(self):
    try:
      prods = anvil.server.call('get_productos_terraza')
      cats = anvil.server.call('get_categorias_terraza')
      mesas = anvil.server.call('get_mesas_terraza')
      if hasattr(anvil.js.window, 'setPOSCatalogoFromDB'):
        anvil.js.window.setPOSCatalogoFromDB(
          json.dumps(prods) if prods else "[]",
          json.dumps(cats) if cats else "[]",
          json.dumps(mesas) if mesas else "[]"
        )
    except Exception as e:
      print(f"Error cargando catalogo POS desde servidor: {e}")

  def sincronizar_cuenta_servidor(self, mesa_id, silla_id, items, estado='ocupada'):
    try:
      if isinstance(items, str):
        try:
          items_clean = json.loads(items)
        except Exception:
          items_clean = []
      elif isinstance(items, list):
        items_clean = items
      else:
        try:
          items_clean = json.loads(json.dumps(items))
        except Exception:
          items_clean = []
      print(f"📡 [POSMESERO] sincronizando con servidor: Mesa {mesa_id} Silla {silla_id} -> {len(items_clean)} items ({estado})")
      res = anvil.server.call('actualizar_cuenta_silla', int(mesa_id), int(silla_id), items_clean, str(estado))
      return res
    except Exception as e:
      print(f"Error en sincronizar_cuenta_servidor desde POSMesero: {e}")
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
    elif modulo_nombre in ['admin', 'admin_menu', 'inicio', 'dashboard']:
      target_form = 'AdminMenu'
    
    anvil.open_form(target_form)
