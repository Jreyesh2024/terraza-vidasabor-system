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
    except Exception:
      pass

    try:
      url_hash = anvil.get_url_hash()
      if isinstance(url_hash, str) and url_hash:
        url_lower = url_hash.lower()
        if 'pos_mesero' in url_lower or 'croquis' in url_lower:
          anvil.open_form('POSMesero')
        elif 'monitor_cocina' in url_lower or 'kds' in url_lower:
          anvil.open_form('MonitorCocina')
        elif 'monitor_fiscal' in url_lower or 'fiscal' in url_lower:
          anvil.open_form('MonitorFiscal')
        elif 'clientes_lealtad' in url_lower or 'rewards' in url_lower:
          anvil.open_form('ClientesLealtad')
    except Exception as e:
      print(f"Error procesando routing en Menu: {e}")

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
      res = anvil.server.call('actualizar_cuenta_silla', int(mesa_id), int(silla_id), items, str(estado))
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
