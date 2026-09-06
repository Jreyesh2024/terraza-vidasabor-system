"""
POSMesero — form principal del croquis de la terraza.

Arquitectura:
  - HTML declara estructura + `data-action` / `data-args` / `data-backdrop-action`.
  - Python (este archivo) monta UN listener delegado en el nodo raíz del form
    dentro de `form_show`, despacha por `data-action` y llama a la función
    JavaScript correspondiente en `window.*`.
  - JS conserva las implementaciones de negocio existentes en `pos_mesero.js`.
    Migrar handler-por-handler a Python es incremental y no requiere tocar
    esta arquitectura.
  - Sin `onclick` inline. Sin ejecutar `<script>` embebidos. Sin
    MutationObserver global.
"""

from ._anvil_designer import POSMeseroTemplate
import anvil
import anvil.js
import anvil.server
import json


# Acciones que Python maneja directamente (no delegan a window.*).
# Cualquier data-action fuera de este set se busca en window.<action>.
_ACCIONES_NATIVAS = {
    "navAdmin": ("_nav", "AdminMenu"),
    "navPOSMesero": ("_nav", "POSMesero"),
    "navMonitorCocina": ("_nav", "MonitorCocina"),
    "navMonitorFiscal": ("_nav", "MonitorFiscal"),
    "navMenu": ("_nav", "Menu"),
    "navClientesLealtad": ("_nav", "ClientesLealtad"),
    # Composites: reemplazan onclicks compuestos "foo(); bar();" del HTML original.
    "cerrarModalComandaYVolverCroquis": ("_composite_cerrar_y_volver_croquis",),
    "volverAlCroquisYRecargar": ("_composite_volver_y_recargar",),
}


def _parse_arg(raw):
    """Convierte un string de data-args al tipo natural (int, float, bool, None, str)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "null":
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def _split_args(raw):
    if raw is None:
        return []
    s = str(raw).strip()
    if s == "":
        return []
    return [_parse_arg(p) for p in s.split(",")]


class POSMesero(POSMeseroTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self._root = None
        self._click_handler = None
        self._timer_sync = None

        # Enlaces explícitos del ciclo de vida: en HtmlTemplate sin designer,
        # el auto-binding de form_show/form_hide no siempre corre.
        self.set_event_handler("show", self.form_show)
        self.set_event_handler("hide", self.form_hide)

        # Enrutamiento QR (mesa/silla en la URL → módulo cliente).
        try:
            url_hash = anvil.get_url_hash()
            if isinstance(url_hash, str) and url_hash:
                url_lower = url_hash.lower()
                if ("mesa=" in url_lower and "silla=" in url_lower) or "pv-" in url_lower:
                    anvil.open_form("Menu")
                    return
            elif isinstance(url_hash, dict) and url_hash:
                if ("mesa" in url_hash and "silla" in url_hash) or "qr" in url_hash:
                    anvil.open_form("Menu")
                    return
        except Exception as e:
            print(f"[POSMesero] Error enrutando QR: {e}")

    # ─────────────────────────── ciclo de vida ───────────────────────────
    def form_show(self, **event_args):
        """Se dispara cada vez que el form entra en pantalla."""
        self._root = anvil.js.get_dom_node(self)
        self._exponer_puente_python()
        self._bind_events()
        # Anvil v3 ignora los <script> del theme/native_deps en la práctica,
        # así que Python inyecta pos_mesero.js en <head> y encadena el boot
        # cuando el archivo termine de cargar.
        self._asegurar_pos_mesero_js_y_arrancar()
        self._iniciar_timer_sync()

    def form_hide(self, **event_args):
        """Limpieza al salir del form. Evita listeners fantasma y timers colgados."""
        self._unbind_events()
        self._detener_timer_sync()
        self._retirar_puente_python()
        self._desinstalar_mutation_observer()

    def _desinstalar_mutation_observer(self):
        obs = getattr(self, "_mo_observer", None)
        if obs is not None:
            try:
                obs.disconnect()
            except Exception:
                pass
        self._mo_observer = None
        self._mo_installed = False

    # ─────────────────────── binding (event delegation) ──────────────────
    def _bind_events(self):
        if self._root is None:
            return
        self._click_handler = self._on_root_click
        # capture=False, bubble normal. Los descendientes que hagan
        # stopPropagation dejarán de llegar, cosa que aquí no queremos casi
        # nunca; si algún día lo necesitan, ese caso vive en su handler.
        self._root.addEventListener("click", self._click_handler)

    def _unbind_events(self):
        if self._root is not None and self._click_handler is not None:
            try:
                self._root.removeEventListener("click", self._click_handler)
            except Exception:
                pass
        self._click_handler = None

    def _on_root_click(self, event):
        target = event.target
        if target is None:
            return

        # 1) Cierre por clic en fondo (backdrops de modales).
        #    data-backdrop-action="cerrarModalX" se dispara SOLO si el target
        #    es el propio elemento backdrop, no un hijo.
        backdrop = target.closest("[data-backdrop-action]")
        if backdrop is not None and target.isSameNode(backdrop):
            action = getattr(backdrop.dataset, "backdropAction", None)
            if action:
                self._despachar(action, backdrop, event)
            return

        # 2) Acción declarativa normal: data-action + data-args opcional.
        el = target.closest("[data-action]")
        if el is None:
            return
        action = getattr(el.dataset, "action", None)
        if not action:
            return
        self._despachar(action, el, event)

    def _despachar(self, action, el, event):
        """Un único punto que decide qué correr: método Python o función JS."""
        args = _split_args(getattr(el.dataset, "args", None))

        # 2a) Acciones nativas (navegación entre módulos, etc.).
        if action in _ACCIONES_NATIVAS:
            method_name, *fixed_args = _ACCIONES_NATIVAS[action]
            getattr(self, method_name)(*fixed_args, *args)
            return

        # 2b) Delegación a JS: window.<action>(*args). Silencioso si no existe
        #     todavía — evita el TypeError ruidoso; queda registrado en consola.
        js_fn = getattr(anvil.js.window, action, None)
        if js_fn is None:
            print(f"[POSMesero] Acción sin handler: window.{action}")
            return
        try:
            js_fn(*args)
        except Exception as e:
            print(f"[POSMesero] Error ejecutando window.{action}({args}): {e}")
        # Red de contención: refresco visual + persistir estado si aplica.
        self._refrescar_ui()
        self._persistir_estado_si_aplica(action, args)

    # ───────────────────────── navegación entre forms ────────────────────
    def _nav(self, target_form, *_):
        anvil.open_form(target_form)

    # ────────────────────── composites (ex-onclicks compuestos) ──────────
    def _composite_cerrar_y_volver_croquis(self, *_):
        for fn_name in ("cerrarModalComanda", "volverAlCroquisGeneral"):
            fn = getattr(anvil.js.window, fn_name, None)
            if fn is not None:
                try:
                    fn()
                except Exception as e:
                    print(f"[POSMesero] composite: window.{fn_name} falló: {e}")

    def _composite_volver_y_recargar(self, *_):
        fn = getattr(anvil.js.window, "volverAlCroquisGeneral", None)
        if fn is not None:
            try:
                fn()
            except Exception as e:
                print(f"[POSMesero] composite: volverAlCroquisGeneral falló: {e}")
        # Reabrir el propio form es equivalente a "regresar al POSMesero limpio".
        anvil.open_form("POSMesero")

    def _navegar_por_alias(self, modulo):
        """Compatibilidad con llamadas JS antiguas: window.anvilAppNav('kds')."""
        alias = {
            "pos_mesero": "POSMesero", "croquis": "POSMesero", "palapa": "POSMesero",
            "menu": "Menu", "cliente_qr": "Menu",
            "monitor_cocina": "MonitorCocina", "kds": "MonitorCocina",
            "monitor_fiscal": "MonitorFiscal", "fiscal": "MonitorFiscal",
            "clientes_lealtad": "ClientesLealtad", "rewards": "ClientesLealtad",
            "admin": "AdminMenu", "admin_menu": "AdminMenu",
            "inicio": "AdminMenu", "dashboard": "AdminMenu",
        }
        anvil.open_form(alias.get(modulo, "POSMesero"))

    # ─────────────────── puente Python ← JS (solo lo necesario) ─────────
    def _exponer_puente_python(self):
        """
        Expone en window el mínimo indispensable para que el JS existente
        pueda pedir datos al servidor sin duplicar lógica.
        Todo lo demás debe fluir en sentido JS → data-action → Python.
        """
        w = anvil.js.window
        w.anvilAppNav = self._navegar_por_alias
        w.anvilGetCuentasServidor = self._obtener_cuentas_servidor
        w.anvilSyncCuenta = self._sincronizar_cuenta_servidor

    def _retirar_puente_python(self):
        w = anvil.js.window
        for name in ("anvilAppNav", "anvilGetCuentasServidor", "anvilSyncCuenta"):
            try:
                # Asignar None es equivalente a borrar la referencia funcional.
                setattr(w, name, None)
            except Exception:
                pass

    # ─────────────────────────── datos / sync ────────────────────────────
    def _cargar_catalogo_pos_db(self):
        try:
            prods = anvil.server.call("get_productos_terraza") or []
            cats = anvil.server.call("get_categorias_terraza") or []
            mesas = anvil.server.call("get_mesas_terraza") or []
        except Exception as e:
            print(f"[POSMesero] Error cargando catálogo: {e}")
            return
        set_cat = getattr(anvil.js.window, "setPOSCatalogoFromDB", None)
        if set_cat is not None:
            set_cat(json.dumps(prods), json.dumps(cats), json.dumps(mesas))

    def _sincronizar_con_servidor(self):
        try:
            cuentas = anvil.server.call("get_cuentas_terraza")
        except Exception as e:
            print(f"[POSMesero] Error obteniendo cuentas: {e}")
            return
        if not cuentas:
            return
        aplicar = getattr(anvil.js.window, "aplicarCuentasServidor", None)
        if aplicar is not None:
            aplicar(json.dumps(cuentas))
            return
        render = getattr(anvil.js.window, "renderStateUI", None)
        if render is not None:
            render()

    def _obtener_cuentas_servidor(self):
        try:
            res = anvil.server.call("get_cuentas_terraza")
            return json.dumps(res) if res else "{}"
        except Exception as e:
            print(f"[POSMesero] Error obteniendo cuentas: {e}")
            return "{}"

    def _sincronizar_cuenta_servidor(self, mesa_id, silla_id, items, estado="ocupada"):
        # `items` puede llegar como JSON string desde JS, o como lista Python.
        if isinstance(items, str):
            try:
                items_clean = json.loads(items)
            except Exception:
                items_clean = []
        elif isinstance(items, list):
            items_clean = items
        else:
            try:
                items_clean = json.loads(json.dumps(items))
            except Exception:
                items_clean = []
        try:
            return anvil.server.call(
                "actualizar_cuenta_silla",
                int(mesa_id), int(silla_id), items_clean, str(estado)
            )
        except Exception as e:
            print(f"[POSMesero] Error sincronizando cuenta: {e}")
            return None

    # ─────────────────── inyección de pos_mesero.js desde Python ─────────
    def _asegurar_pos_mesero_js_y_arrancar(self):
        """
        Si pos_mesero.js ya está en el <head>, arranca directo.
        Si no, lo inyecta y programa el arranque al terminar de cargar.
        Independiente de anvil.yaml / theme / templates.yaml.
        """
        document = anvil.js.window.document
        existente = document.querySelector('script[src*="pos_mesero"]')
        if existente is not None:
            # Ya cargado en un ciclo previo del form o en una sesión anterior.
            self._cargar_catalogo_pos_db()
            self._sincronizar_con_servidor()
            self._boot_js()
            return
        script = document.createElement("script")
        script.src = "_/theme/pos_mesero.js"
        script.async = False  # respeta el orden si se añaden más adelante
        script.onload = self._on_pos_mesero_js_ready
        script.onerror = self._on_pos_mesero_js_error
        document.head.appendChild(script)

    def _on_pos_mesero_js_ready(self, *_):
        print("[POSMesero] pos_mesero.js cargado, iniciando UI.")
        self._cargar_catalogo_pos_db()
        self._sincronizar_con_servidor()
        self._boot_js()
        self._ajustar_layout_grid()
        # MutationObserver: observa cambios de clase en #mainCanvasGrid.
        # El JS del theme llama renderStateUI() (referencia local del IIFE,
        # NO window.renderStateUI), por lo que envolver window no intercepta
        # nada. Observando el DOM directamente sí capturamos cada cambio.
        self._install_mutation_observer()

    def _install_mutation_observer(self):
        """
        Instala un MutationObserver sobre #mainCanvasGrid que dispara ajust
        del layout + marcar ocupada cada vez que la clase (mode-overview /
        mode-comanda) cambie.
        """
        if getattr(self, "_mo_installed", False):
            return
        w = anvil.js.window
        grid = w.document.getElementById("mainCanvasGrid")
        if grid is None:
            print("[POSMesero] MutationObserver: no encontró mainCanvasGrid")
            return
        MO = getattr(w, "MutationObserver", None)
        if MO is None:
            return
        self_ref = self
        def on_mutation(mutations, observer):
            try:
                self_ref._ajustar_layout_grid()
                self_ref._forzar_ocupada_silla_seleccionada()
            except Exception as e:
                print(f"[POSMesero] callback MutationObserver falló: {e}")
        observer = MO(on_mutation)
        observer.observe(grid, {"attributes": True, "attributeFilter": ["class"]})
        self._mo_observer = observer
        self._mo_installed = True
        print("[POSMesero] MutationObserver instalado en #mainCanvasGrid.")

    def _forzar_ocupada_silla_seleccionada(self):
        """
        Cuando modoComandaActiva=true y hay una silla seleccionada cuyo
        estado no es 'ocupada', la marca ocupada y persiste al servidor.
        Corrige el bug donde handleSillaClick no marca ocupada si la cuenta
        ya existía con estado 'disponible' (venida del servidor).
        """
        w = anvil.js.window
        state = getattr(w, "palapaState", None)
        if state is None:
            return
        try:
            if not state.modoComandaActiva:
                return
            mesa_id = state.mesaSeleccionadaId
            silla_num = state.sillaSeleccionadaNum
        except Exception:
            return
        if not mesa_id or not silla_num:
            return
        try:
            cuenta = state.cuentas[f"{int(mesa_id)}-{int(silla_num)}"]
        except Exception:
            return
        if cuenta is None:
            return
        try:
            estado_actual = str(getattr(cuenta, "estado", "") or "")
        except Exception:
            estado_actual = ""
        if estado_actual == "ocupada":
            return  # ya estaba, no hacer nada
        try:
            cuenta.estado = "ocupada"
        except Exception as e:
            print(f"[POSMesero] Error marcando ocupada localmente: {e}")
            return
        try:
            self._sincronizar_cuenta_servidor(
                int(mesa_id), int(silla_num), [], "ocupada"
            )
        except Exception as e:
            print(f"[POSMesero] Error persistiendo ocupada al servidor: {e}")

    # ─────────────────────── UI: refresh y ajuste de layout ──────────────
    def _refrescar_ui(self):
        """Refresco post-dispatch: re-renderiza JS + fuerza layout inline."""
        render = getattr(anvil.js.window, "renderStateUI", None)
        if render is not None:
            try:
                render()
            except Exception as e:
                print(f"[POSMesero] renderStateUI post-dispatch falló: {e}")
        self._ajustar_layout_grid()

    def _ajustar_layout_grid(self):
        """
        Workaround: el <style> con `grid-template-columns: 420px 1fr !important`
        no siempre se respeta cuando el HtmlTemplate lo inyecta Skulpt.
        Forzamos el valor inline con !important — inline gana sobre stylesheet.
        """
        grid = anvil.js.window.document.getElementById("mainCanvasGrid")
        if grid is None:
            return
        cls = str(getattr(grid, "className", "") or "")
        if "mode-comanda" in cls:
            grid.style.setProperty("grid-template-columns", "420px 1fr", "important")
        else:
            grid.style.setProperty("grid-template-columns", "1fr", "important")

    def _persistir_estado_si_aplica(self, action, args):
        """
        Cuando el mesero abre una silla, marca ocupada en local (handleSillaClick)
        pero NO envía al servidor. El timer sync trae del servidor "disponible"
        cada 2s y pisa la ocupada local. Solución: al despachar clickSilla,
        Python persiste 'ocupada' al servidor de inmediato.
        """
        if action == "clickSilla" and len(args) >= 2:
            try:
                self._sincronizar_cuenta_servidor(args[0], args[1], [], "ocupada")
            except Exception as e:
                print(f"[POSMesero] Error persistiendo ocupada: {e}")

    def _on_pos_mesero_js_error(self, *_):
        print("[POSMesero] ERROR: no se pudo cargar _/theme/pos_mesero.js")

    def _boot_js(self):
        """Dispara el arranque visual del JS (renderiza croquis según estado)."""
        init = getattr(anvil.js.window, "initPOSMesero", None)
        if init is not None:
            try:
                init()
                return
            except Exception as e:
                print(f"[POSMesero] initPOSMesero falló: {e}")
        render = getattr(anvil.js.window, "renderStateUI", None)
        if render is not None:
            try:
                render()
            except Exception as e:
                print(f"[POSMesero] renderStateUI falló: {e}")

    # ─────────────────────────── timer de sync ───────────────────────────
    def _iniciar_timer_sync(self):
        try:
            self._timer_sync = anvil.Timer(interval=2)
            self._timer_sync.set_event_handler("tick", self._tick_sync)
            self.add_component(self._timer_sync)
        except Exception as e:
            print(f"[POSMesero] Error iniciando timer: {e}")

    def _detener_timer_sync(self):
        if self._timer_sync is None:
            return
        try:
            self._timer_sync.interval = 0  # detiene los ticks
        except Exception:
            pass
        self._timer_sync = None

    def _tick_sync(self, **event_args):
        self._sincronizar_con_servidor()
