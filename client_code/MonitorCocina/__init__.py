from ._anvil_designer import MonitorCocinaTemplate
import anvil
import anvil.js
import anvil.server
import json

class MonitorCocina(MonitorCocinaTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    try:
      anvil.js.window.anvilAppNav = self.navegar_modulo
      anvil.js.window.navMenu = self.navegar_modulo
      anvil.js.window.scrollTo(0, 0)
    except Exception:
      pass

    self.set_event_handler("show", self._form_show)
    self.set_event_handler("hide", self._form_hide)

    # Cargar recetas y mesas dinámicas desde PostgreSQL
    self.cargar_recetario_db()

  def _form_show(self, **event_args):
    # Adjuntar listener directo al botón "Volver a Mesa & POS" del header y
    # a cualquier otro botón dentro del form que quiera navegar a POSMesero.
    # Delay 200ms para que el DOM del form esté completamente inyectado.
    anvil.js.window.setTimeout(self._reforzar_botones_salida, 200)
    # Insurance: reintenta a los 800ms por si el HTML se reinyectó.
    anvil.js.window.setTimeout(self._reforzar_botones_salida, 800)

  def _form_hide(self, **event_args):
    # Limpiar cualquier resto que hayamos podido inyectar en body.
    try:
      doc = anvil.js.window.document
      leftover = doc.getElementById("vs-salir-cocina")
      if leftover is not None:
        leftover.remove()
    except Exception:
      pass

  def _reforzar_botones_salida(self, *_):
    """Enlaza directamente un handler Python al botón 'Volver a Mesa & POS'
    del header del MonitorCocina, sin depender de window.navMenu ni de
    scripts embebidos. Idempotente."""
    try:
      doc = anvil.js.window.document
      # Cualquier botón cuyo texto contenga "Volver a Mesa" o "Volver a Mesas"
      botones = doc.querySelectorAll("button")
      for i in range(int(botones.length)):
        btn = botones.item(i)
        txt = (btn.textContent or "").strip().lower()
        if ("volver a mesa" in txt or "volver a mesas" in txt) \
           and not getattr(btn, "_vsHooked", False):
          setattr(btn, "_vsHooked", True)
          btn.addEventListener("click", lambda ev: self._salir_a_pos())
    except Exception as e:
      print(f"[MonitorCocina] Error reforzando botones salida: {e}")

  def _salir_a_pos(self, *_):
    """Sale a POSMesero limpiando el hash de URL para evitar redirects."""
    try:
      anvil.set_url_hash("", set_in_history=False)
    except Exception:
      pass
    anvil.open_form("POSMesero")

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
