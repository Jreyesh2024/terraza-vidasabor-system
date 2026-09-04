from ._anvil_designer import POSMeseroTemplate
import anvil
import anvil.js

class POSMesero(POSMeseroTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      anvil.js.window.anvilAppNav = self.navegar_modulo
    except Exception:
      pass

    try:
      url_hash = anvil.get_url_hash()
      abrir_pos = False
      if isinstance(url_hash, str) and url_hash:
        url_lower = url_hash.lower()
        if 'pos_mesero' in url_lower or 'croquis' in url_lower or 'admin' in url_lower:
          abrir_pos = True
      elif isinstance(url_hash, dict) and url_hash.get('form') in ['pos_mesero', 'croquis', 'admin']:
        abrir_pos = True

      # Si NO es mesero/admin explícito, mandar directo a Menu del Comensal
      if not abrir_pos:
        anvil.open_form('Menu')
    except Exception as e:
      print(f"Error procesando enrutamiento QR: {e}")

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
