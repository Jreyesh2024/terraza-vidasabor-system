from ._anvil_designer import MenuTemplate
import anvil
import anvil.js

class Menu(MenuTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      anvil.js.window.anvilAppNav = self.navegar_modulo
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
