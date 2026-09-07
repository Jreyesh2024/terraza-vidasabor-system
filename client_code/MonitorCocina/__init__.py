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

    # Botón flotante SIEMPRE visible para salir a POSMesero,
    # independiente del HTML embebido del form (defensivo).
    self.set_event_handler("show", self._form_show)

    # Cargar recetas y mesas dinámicas desde PostgreSQL
    self.cargar_recetario_db()

  def _form_show(self, **event_args):
    self._instalar_boton_salida()

  def _instalar_boton_salida(self):
    try:
      doc = anvil.js.window.document
      prev = doc.getElementById("vs-salir-cocina")
      if prev is not None:
        prev.remove()
      btn = doc.createElement("button")
      btn.id = "vs-salir-cocina"
      btn.innerHTML = ('<i class="fa-solid fa-arrow-left"></i>'
                      ' <span>Volver a Mesas</span>')
      btn.style.cssText = (
        "position: fixed; top: 12px; left: 16px; z-index: 99998; "
        "padding: 10px 18px; "
        "background: linear-gradient(135deg,#059669,#0f766e); color:#fff; "
        "border: 2px solid #34d399; border-radius: 999px; "
        "font-weight: 900; font-size: 13px; "
        "cursor: pointer; user-select: none; "
        "box-shadow: 0 6px 20px rgba(16,185,129,0.5); "
        "display: flex; align-items: center; gap: 8px;"
      )
      btn.addEventListener("click", lambda ev: anvil.open_form("POSMesero"))
      doc.body.appendChild(btn)
    except Exception as e:
      print(f"[MonitorCocina] Error instalando botón salida: {e}")

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
