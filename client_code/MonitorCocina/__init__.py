from ._anvil_designer import MonitorCocinaTemplate
import anvil
import anvil.js
import anvil.server
import json

class MonitorCocina(MonitorCocinaTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      # Exponer navegación directamente en window
      anvil.js.window.navMenu = self.navegar_modulo
      anvil.js.window.anvilAppNav = self.navegar_modulo
      anvil.js.window.scrollTo(0, 0)
    except Exception as e:
      print(f"[MonitorCocina] Error exponiendo funciones en window: {e}")

    # Ejecutar scripts de plantilla
    try:
      dom = anvil.js.get_dom_node(self)
      if hasattr(anvil.js.window, 'runFormScripts'):
        anvil.js.window.runFormScripts(dom)
    except Exception:
      pass

    # Cargar recetas y mesas dinámicas desde PostgreSQL
    self.cargar_recetario_db()

  def cargar_recetario_db(self):
    try:
      recetas = anvil.server.call('get_recetas_cocina_terraza')
      mesas = anvil.server.call('get_mesas_terraza')
      areas = anvil.server.call('get_areas_terraza')
      if hasattr(anvil.js.window, 'setRecetarioFromDB'):
        anvil.js.window.setRecetarioFromDB(json.dumps(recetas) if recetas else "[]")
      if hasattr(anvil.js.window, 'setMesasCocinaFromDB'):
        anvil.js.window.setMesasCocinaFromDB(
          json.dumps(mesas) if mesas else "[]",
          json.dumps(areas) if areas else "[]"
        )
    except Exception as e:
      print(f"Error cargando recetario KDS desde DB: {e}")

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
