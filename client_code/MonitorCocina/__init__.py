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

    # Ejecutar scripts de plantilla directamente en el DOM
    self.ejecutar_scripts_template()

    # Exponer función de sincronización de cuenta para que KDS actualice el servidor
    try:
      anvil.js.window.anvilSyncCuenta = self.sincronizar_cuenta_servidor
    except Exception:
      pass

    # Cargar recetas y mesas dinámicas desde PostgreSQL
    self.cargar_recetario_db()
    self.sincronizar_con_servidor()

    # Timer nativo de Anvil en segundo plano para sincronizar KDS cada 2.5 segundos
    try:
      self.timer_sync = anvil.Timer(interval=2.5)
      self.timer_sync.set_event_handler('tick', self.timer_tick_sync)
      self.add_component(self.timer_sync)
    except Exception as e:
      print(f"Error iniciando timer sync en MonitorCocina: {e}")

  def timer_tick_sync(self, **event_args):
    self.sincronizar_con_servidor()

  def sincronizar_con_servidor(self):
    try:
      cuentas = anvil.server.call('get_cuentas_terraza')
      if cuentas:
        if hasattr(anvil.js.window, 'setKDSCuentasFromDB'):
          anvil.js.window.setKDSCuentasFromDB(json.dumps(cuentas))
        elif hasattr(anvil.js.window, 'cargarKDS'):
          anvil.js.window.cargarKDS()
    except Exception as e:
      print(f"Error sincronizando servidor en MonitorCocina: {e}")

  def sincronizar_cuenta_servidor(self, mesa_id, silla_id, items, estado='ocupada'):
    try:
      if isinstance(items, str):
        try: items_clean = json.loads(items)
        except Exception: items_clean = []
      elif isinstance(items, list):
        items_clean = items
      else:
        try: items_clean = json.loads(json.dumps(items))
        except Exception: items_clean = []
      res = anvil.server.call('actualizar_cuenta_silla', int(mesa_id), int(silla_id), items_clean, str(estado))
      return res
    except Exception as e:
      print(f"Error en sincronizar_cuenta_servidor desde MonitorCocina: {e}")
      return None

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

  def ejecutar_scripts_template(self):
    try:
      dom = anvil.js.get_dom_node(self)
      if not dom:
        return
      doc = anvil.js.window.document
      scripts = dom.querySelectorAll('script')
      for s in scripts:
        if not s.getAttribute('data-executed'):
          s.setAttribute('data-executed', 'true')
          code = s.textContent
          if code and code.strip():
            new_script = doc.createElement('script')
            for attr in s.attributes:
              try:
                new_script.setAttribute(attr.name, attr.value)
              except Exception:
                pass
            new_script.textContent = code
            doc.head.appendChild(new_script)
            doc.head.removeChild(new_script)
    except Exception as e:
      print(f"[MonitorCocina] Error en ejecutar_scripts_template: {e}")
