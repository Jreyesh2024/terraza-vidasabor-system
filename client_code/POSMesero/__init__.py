from ._anvil_designer import POSMeseroTemplate
import anvil
import anvil.js
import anvil.server

class POSMesero(POSMeseroTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      anvil.js.window.anvilAppNav = self.navegar_modulo
      anvil.js.window.anvilGetCuentasServidor = self.obtener_cuentas_servidor
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

    # Sincronización inicial
    self.sincronizar_con_servidor()

  def obtener_cuentas_servidor(self):
    try:
      return anvil.server.call('get_cuentas_terraza')
    except Exception as e:
      print(f"Error obteniendo cuentas de servidor: {e}")
      return {}

  def sincronizar_con_servidor(self):
    try:
      cuentas = anvil.server.call('get_cuentas_terraza')
      if cuentas:
        try:
          if hasattr(anvil.js.window, 'aplicarCuentasServidor'):
            anvil.js.window.aplicarCuentasServidor(cuentas)
        except Exception:
          pass
    except Exception as e:
      print(f"Error sincronizando servidor en POSMesero: {e}")

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
