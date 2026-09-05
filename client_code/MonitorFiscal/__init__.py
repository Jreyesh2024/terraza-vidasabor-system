from ._anvil_designer import MonitorFiscalTemplate
import anvil
import anvil.js

class MonitorFiscal(MonitorFiscalTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      anvil.js.window.anvilAppNav = self.navegar_modulo
    except Exception:
      pass

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
