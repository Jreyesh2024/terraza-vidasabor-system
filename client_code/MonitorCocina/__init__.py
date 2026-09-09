from ._anvil_designer import MonitorCocinaTemplate
import anvil
import anvil.js
import anvil.server
import json

class MonitorCocina(MonitorCocinaTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._set_global_nav_hooks()
    self.set_event_handler("show", self._form_show)
    self.set_event_handler("hide", self._form_hide)

    # Cargar recetas y mesas dinámicas desde PostgreSQL
    self.cargar_recetario_db()
    self.cargar_cuentas_kds_db()

  def _set_global_nav_hooks(self):
    try:
      w = anvil.js.window
      w.anvilAppNav = self.navegar_modulo
      w.navMenu = self.navegar_modulo
      w.anvilCambiarEstadoItemCocina = self.cambiar_estado_item_cocina
      w.anvilDespacharTicketCocina = self.despachar_ticket_cocina
      w.anvilGetKDSCuentas = self.cargar_cuentas_kds_db
      if hasattr(w, 'parent') and w.parent:
        w.parent.anvilAppNav = self.navegar_modulo
        w.parent.navMenu = self.navegar_modulo
        w.parent.anvilCambiarEstadoItemCocina = self.cambiar_estado_item_cocina
        w.parent.anvilDespacharTicketCocina = self.despachar_ticket_cocina
        w.parent.anvilGetKDSCuentas = self.cargar_cuentas_kds_db
      if hasattr(w, 'top') and w.top:
        w.top.anvilAppNav = self.navegar_modulo
        w.top.navMenu = self.navegar_modulo
        w.top.anvilCambiarEstadoItemCocina = self.cambiar_estado_item_cocina
        w.top.anvilDespacharTicketCocina = self.despachar_ticket_cocina
        w.top.anvilGetKDSCuentas = self.cargar_cuentas_kds_db
      w.scrollTo(0, 0)
    except Exception as e:
      print(f"[MonitorCocina] Error registrando navMenu y hooks: {e}")

  def _form_show(self, **event_args):
    self._set_global_nav_hooks()
    self.cargar_cuentas_kds_db()
    anvil.js.window.setTimeout(self._set_global_nav_hooks, 300)

  def _form_hide(self, **event_args):
    pass

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

  def cargar_cuentas_kds_db(self):
    try:
      cuentas = anvil.server.call('get_cuentas_terraza')
      if hasattr(anvil.js.window, 'setKDSCuentasFromDB'):
        anvil.js.window.setKDSCuentasFromDB(json.dumps(cuentas) if cuentas else "{}")
      return cuentas
    except Exception as e:
      print(f"[MonitorCocina] Error obteniendo comandas KDS desde DB: {e}")
      return {}

  def cambiar_estado_item_cocina(self, detalle_id, nuevo_estado):
    try:
      res = anvil.server.call('cambiar_estado_item_cocina', int(detalle_id), str(nuevo_estado))
      return res
    except Exception as e:
      print(f"[MonitorCocina] Error cambiando estado de item #{detalle_id}: {e}")
      return {"success": False, "error": str(e)}

  def despachar_ticket_cocina(self, mesa_num, silla_num=None, nuevo_estado='listo'):
    try:
      s_val = int(silla_num) if (silla_num is not None and str(silla_num).isdigit()) else None
      res = anvil.server.call('despachar_ticket_cocina', int(mesa_num), s_val, str(nuevo_estado))
      return res
    except Exception as e:
      print(f"[MonitorCocina] Error despachando ticket mesa {mesa_num}: {e}")
      return {"success": False, "error": str(e)}

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

