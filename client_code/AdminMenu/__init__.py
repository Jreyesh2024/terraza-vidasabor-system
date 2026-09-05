from ._anvil_designer import AdminMenuTemplate
import anvil
import anvil.js
import anvil.server
import json

class AdminMenu(AdminMenuTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      # Exponer funciones de navegación y acción directamente en window
      # NOTA: Anvil no ejecuta <script> en HtmlTemplate, por eso se define
      # window.navMenu desde Python para que siempre esté disponible.
      anvil.js.window.navMenu = self.navegar_modulo
      anvil.js.window.anvilAppNav = self.navegar_modulo
      anvil.js.window.anvilGuardarProducto = self.guardar_producto_db
      anvil.js.window.anvilCambiarDisp = self.cambiar_disponibilidad_db
      anvil.js.window.anvilCargarDashboard = self.cargar_dashboard
      # Exponer modales (fallback no-op para que no exploten botones de modal)
      for fn_name in ['abrirModalAdminMenu', 'cerrarModalAdminMenu',
                      'abrirModalPersonal', 'cerrarModalPersonal',
                      'abrirModalInventario', 'cerrarModalInventario',
                      'abrirModalCajaChica', 'cerrarModalCajaChica',
                      'guardarPlatilloDB', 'nuevoPlatilloForm',
                      'filtrarListaPlatillos']:
        if not getattr(anvil.js.window, fn_name, None):
          anvil.js.window[fn_name] = lambda *a, _n=fn_name: print(f"[AdminMenu] {_n} llamado")
    except Exception as e:
      print(f"[AdminMenu] Error exponiendo funciones en window: {e}")

    # Ejecutar scripts de plantilla directamente en el DOM
    self.ejecutar_scripts_template()

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

  def ejecutar_scripts_template(self):
    try:
      dom = anvil.js.get_dom_node(self)
      if not dom:
        return
      doc = anvil.js.window.document
      scripts = dom.querySelectorAll('script')
      count = int(scripts.length) if hasattr(scripts, 'length') else len(scripts)
      for i in range(count):
        s = scripts.item(i) if hasattr(scripts, 'item') else scripts[i]
        if not s.getAttribute('data-executed'):
          s.setAttribute('data-executed', 'true')
          code = str(s.textContent)
          if code and code.strip():
            try:
              anvil.js.window.eval(code)
            except Exception:
              new_script = doc.createElement('script')
              new_script.textContent = code
              doc.head.appendChild(new_script)
              doc.head.removeChild(new_script)
    except Exception as e:
      print(f"[AdminMenu] Error en ejecutar_scripts_template: {e}")
