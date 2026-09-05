from ._anvil_designer import AdminMenuTemplate
import anvil
import anvil.js
import anvil.server
import json

class AdminMenu(AdminMenuTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      anvil.js.window.anvilAppNav = self.navegar_modulo
      anvil.js.window.anvilGuardarProducto = self.guardar_producto_db
      anvil.js.window.anvilCambiarDisp = self.cambiar_disponibilidad_db
      anvil.js.window.anvilCargarDashboard = self.cargar_dashboard
    except Exception:
      pass

    # Cargar datos iniciales del Dashboard
    self.cargar_dashboard()

  def cargar_dashboard(self):
    try:
      kpis = anvil.server.call('get_dashboard_kpis_terraza')
      prods = anvil.server.call('get_productos_terraza')
      cats = anvil.server.call('get_categorias_terraza')
      mesas = anvil.server.call('get_mesas_terraza')
      if hasattr(anvil.js.window, 'renderAdminDashboard'):
        anvil.js.window.renderAdminDashboard(
          json.dumps(kpis) if kpis else "{}",
          json.dumps(prods) if prods else "[]",
          json.dumps(cats) if cats else "[]",
          json.dumps(mesas) if mesas else "[]"
        )
    except Exception as e:
      print(f"Error cargando datos en AdminMenu: {e}")

  def guardar_producto_db(self, prod_json):
    try:
      prod_dict = json.loads(prod_json) if isinstance(prod_json, str) else prod_json
      res = anvil.server.call('guardar_producto_terraza', prod_dict)
      # Recargar catálogo tras guardar
      self.cargar_dashboard()
      return json.dumps(res) if res else "{}"
    except Exception as e:
      print(f"Error guardando producto desde AdminMenu: {e}")
      return json.dumps({"success": False, "error": str(e)})

  def cambiar_disponibilidad_db(self, prod_id, disponible):
    try:
      res = anvil.server.call('cambiar_disponibilidad_producto_terraza', int(prod_id), bool(disponible))
      self.cargar_dashboard()
      return json.dumps(res) if res else "{}"
    except Exception as e:
      print(f"Error cambiando disponibilidad: {e}")
      return json.dumps({"success": False, "error": str(e)})

  def navegar_modulo(self, modulo_nombre):
    target_form = 'AdminMenu'
    if modulo_nombre in ['pos_mesero', 'pos', 'palapa', 'croquis']:
      target_form = 'POSMesero'
    elif modulo_nombre in ['monitor_cocina', 'kds', 'cocina']:
      target_form = 'MonitorCocina'
    elif modulo_nombre in ['menu', 'cliente_qr', 'comensal']:
      target_form = 'Menu'
    elif modulo_nombre in ['monitor_fiscal', 'fiscal']:
      target_form = 'MonitorFiscal'
    elif modulo_nombre in ['clientes_lealtad', 'rewards']:
      target_form = 'ClientesLealtad'
    elif modulo_nombre in ['admin', 'admin_menu', 'dashboard', 'inicio']:
      target_form = 'AdminMenu'

    anvil.open_form(target_form)
