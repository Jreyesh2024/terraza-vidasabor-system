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
    # Alertas / llamadas al mesero (Bloque G v1)
    "verAlertas":     ("_ver_alertas",),
    "cerrarAlertas":  ("_cerrar_alertas",),
    "atenderAlerta":  ("_atender_alerta",),
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
        self._instalar_badge_alertas()
        self._iniciar_timer_alertas()
        # Re-instalar el hover tooltip en cada montaje: cuando el usuario
        # vuelve al POSMesero desde otro form, el body puede haber perdido
        # sus listeners. Delay 300ms para que el DOM esté listo.
        anvil.js.window.setTimeout(self._reinstalar_hover_tooltips, 300)
        # Quitar cualquier botón flotante residual del MonitorCocina
        # (por si el hide del otro form no alcanzó a limpiarlo).
        self._limpiar_botones_flotantes_extranos()

    def _reinstalar_hover_tooltips(self, *_):
        try:
            body = anvil.js.window.document.body
            # Forzar re-instalación resetando el guard.
            setattr(body, "_vsHoverInstalled", False)
            install = getattr(anvil.js.window, "installHoverTooltips", None)
            if install is not None:
                install()
        except Exception as e:
            print(f"[POSMesero] Error reinstalando hover tooltips: {e}")

    def _limpiar_botones_flotantes_extranos(self):
        try:
            doc = anvil.js.window.document
            for _id in ("vs-salir-cocina",):
                el = doc.getElementById(_id)
                if el is not None:
                    el.remove()
        except Exception:
            pass

    def form_hide(self, **event_args):
        """Limpieza al salir del form. Evita listeners fantasma y timers colgados."""
        self._unbind_events()
        self._detener_timer_sync()
        self._detener_timer_alertas()
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
        # `async` es palabra reservada en Python, usamos setattr con string.
        setattr(script, "async", False)  # respeta el orden si se añaden más adelante
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

    # ═══════════════════════ ALERTAS AL MESERO (Bloque G v1) ═══════════════
    def _instalar_badge_alertas(self):
        """Inyecta un BANNER horizontal fijo arriba, ancho, muy visible.
        Sólo aparece cuando hay alertas pendientes. Al hacer clic dispara
        data-action='verAlertas' (event delegation Python)."""
        doc = anvil.js.window.document
        if doc.getElementById("vs-alertas-banner") is not None:
            return
        banner = doc.createElement("div")
        banner.id = "vs-alertas-banner"
        banner.setAttribute("data-action", "verAlertas")
        banner.style.cssText = (
            "position: fixed; top: 0; left: 0; right: 0; z-index: 9998; "
            "min-height: 68px; padding: 14px 20px; "
            "display: none; align-items: center; justify-content: center; gap: 14px; "
            "font-weight: 900; font-size: 17px; letter-spacing: 0.3px; "
            "cursor: pointer; user-select: none; "
            "background: linear-gradient(90deg,#dc2626 0%,#b91c1c 50%,#dc2626 100%); "
            "color: #ffffff; border-bottom: 3px solid #7f1d1d; "
            "box-shadow: 0 6px 24px rgba(220,38,38,0.55); "
            "animation: vs-banner-pulse 1.05s ease-in-out infinite; "
            "text-shadow: 0 1px 2px rgba(0,0,0,0.35);"
        )
        banner.innerHTML = (
            '<i class="fa-solid fa-bell" style="font-size:22px;'
            'animation: vs-shake 0.6s ease-in-out infinite;"></i>'
            '<span id="vs-alertas-texto">Llamadas pendientes</span>'
            '<span style="margin-left:8px;padding:4px 12px;background:rgba(0,0,0,0.25);'
            'border-radius:999px;font-size:14px;">Toca para atender</span>'
        )
        doc.body.appendChild(banner)
        # Listener directo (el banner vive en <body>, fuera del root del form,
        # así que la delegación de form_show no lo captura).
        banner.addEventListener("click", lambda ev: self._ver_alertas())
        # Inyecta keyframes una sola vez
        if doc.getElementById("vs-banner-css") is None:
            st = doc.createElement("style")
            st.id = "vs-banner-css"
            st.textContent = (
                "@keyframes vs-banner-pulse {"
                " 0%,100% { filter: brightness(1); box-shadow: 0 6px 24px rgba(220,38,38,0.55); }"
                " 50% { filter: brightness(1.15); box-shadow: 0 10px 34px rgba(220,38,38,0.9); } } "
                "@keyframes vs-shake {"
                " 0%,100% { transform: rotate(-8deg); }"
                " 50% { transform: rotate(8deg); } }"
            )
            doc.head.appendChild(st)

    def _iniciar_timer_alertas(self):
        try:
            self._timer_alertas = anvil.Timer(interval=4)
            self._timer_alertas.set_event_handler("tick", self._tick_alertas)
            self.add_component(self._timer_alertas)
            # Poll inmediato para no esperar 4s en el primer render.
            self._tick_alertas()
        except Exception as e:
            print(f"[POSMesero] Error iniciando timer alertas: {e}")
            self._timer_alertas = None

    def _detener_timer_alertas(self):
        t = getattr(self, "_timer_alertas", None)
        if t is not None:
            try:
                t.interval = 0
            except Exception:
                pass
        self._timer_alertas = None

    def _tick_alertas(self, **event_args):
        try:
            llamadas = anvil.server.call("get_llamadas_pendientes") or []
        except Exception as e:
            print(f"[POSMesero] Error consultando llamadas: {e}")
            return
        self._llamadas_pendientes = llamadas
        self._pintar_badge_alertas(len(llamadas))

    def _pintar_badge_alertas(self, n):
        doc = anvil.js.window.document
        banner = doc.getElementById("vs-alertas-banner")
        texto = doc.getElementById("vs-alertas-texto")
        if banner is None or texto is None:
            return
        if n > 0:
            plural = "llamada pendiente" if n == 1 else "llamadas pendientes"
            texto.innerHTML = f"{n} {plural}"
            banner.style.setProperty("display", "flex", "important")
        else:
            banner.style.setProperty("display", "none", "important")

    def _ver_alertas(self, *_):
        """Modal con dos secciones: Pendientes (arriba) + Atendidas recientes."""
        doc = anvil.js.window.document
        prev = doc.getElementById("vs-alertas-modal")
        if prev is not None:
            prev.remove()
        llamadas = getattr(self, "_llamadas_pendientes", []) or []
        # Cargar atendidas recientes (últimas 10) — se refresca al abrir el modal.
        try:
            atendidas = anvil.server.call("get_llamadas_recientes", 10) or []
        except Exception as e:
            print(f"[POSMesero] Error get_llamadas_recientes: {e}")
            atendidas = []
        etiqueta = {
            "conflicto_silla_ocupada": ("⚠️ Silla ocupada — conflicto",
                                        "linear-gradient(135deg,#dc2626,#991b1b)"),
            "llamar_mesero":           ("🔔 Llamada al mesero", "#0f766e"),
            "solicitar_cuenta":        ("🧾 Pide su cuenta",     "#0369a1"),
            "ayuda_pedido":            ("🤝 Ayuda con pedido",   "#7c3aed"),
        }
        def _card_pendiente(l):
            tipo = l.get("tipo", "?")
            lab, color = etiqueta.get(tipo, (f"🔔 {tipo}", "#334155"))
            mesa = l.get("numero_mesa", "?")
            silla = l.get("numero_en_mesa", "?")
            qr = l.get("codigo_qr", "")
            hora = str(l.get("creada_at", ""))[11:16]
            return (
                f'<div style="background:#0f172a;border:1px solid #334155;'
                f'border-radius:14px;padding:14px 16px;margin-bottom:10px;'
                f'display:flex;flex-direction:column;gap:8px;">'
                f'  <div style="display:flex;align-items:center;justify-content:space-between;">'
                f'    <span style="font-size:12px;font-weight:900;padding:6px 12px;'
                f'      border-radius:999px;background:{color};color:#fff;">{lab}</span>'
                f'    <span style="font-size:11px;color:#94a3b8;font-family:monospace;">{hora}</span>'
                f'  </div>'
                f'  <div style="font-size:15px;font-weight:800;color:#f1f5f9;">'
                f'    Mesa {mesa} · Silla {silla}'
                f'    <span style="font-size:11px;color:#64748b;font-family:monospace;margin-left:8px;">{qr}</span>'
                f'  </div>'
                f'  <button data-action="atenderAlerta" data-args="{l.get("id")}" '
                f'    style="align-self:flex-end;padding:8px 18px;border-radius:10px;'
                f'    background:#059669;color:#fff;font-weight:900;font-size:12px;'
                f'    border:none;cursor:pointer;">Yo la atiendo</button>'
                f'</div>'
            )

        def _card_atendida(l):
            tipo = l.get("tipo", "?")
            lab, color = etiqueta.get(tipo, (f"🔔 {tipo}", "#334155"))
            mesa = l.get("numero_mesa", "?")
            silla = l.get("numero_en_mesa", "?")
            hora_llamada = str(l.get("creada_at", ""))[11:16]
            hora_atendida = str(l.get("atendida_at", ""))[11:16]
            por = l.get("atendida_por") or "Mesero"
            return (
                f'<div style="background:#0a0f1a;border:1px solid #1e293b;'
                f'border-radius:12px;padding:12px 14px;margin-bottom:8px;'
                f'opacity:0.85;">'
                f'  <div style="display:flex;align-items:center;justify-content:space-between;'
                f'    margin-bottom:6px;">'
                f'    <span style="font-size:11px;font-weight:800;padding:4px 10px;'
                f'      border-radius:999px;background:{color};color:#fff;opacity:0.75;">{lab}</span>'
                f'    <span style="font-size:10px;color:#64748b;font-family:monospace;">'
                f'      {hora_llamada} → {hora_atendida}</span>'
                f'  </div>'
                f'  <div style="font-size:13px;color:#cbd5e1;">'
                f'    Mesa {mesa} · Silla {silla}'
                f'    <span style="color:#10b981;margin-left:8px;font-weight:700;">'
                f'      ✓ atendida por {por}</span>'
                f'  </div>'
                f'</div>'
            )

        pendientes_html = ""
        if llamadas:
            pendientes_html = (
                '<div style="font-size:11px;font-weight:900;color:#f87171;text-transform:uppercase;'
                'letter-spacing:0.05em;margin:4px 0 10px 0;">Pendientes'
                f' ({len(llamadas)})</div>'
                + "".join(_card_pendiente(l) for l in llamadas)
            )
        else:
            pendientes_html = (
                '<div style="text-align:center;padding:20px;color:#64748b;">'
                '<i class="fa-solid fa-check-circle" style="font-size:28px;'
                'color:#10b981;margin-bottom:8px;"></i>'
                '<div style="font-weight:700;font-size:13px;">Sin alertas pendientes</div>'
                '</div>'
            )
        atendidas_html = ""
        if atendidas:
            atendidas_html = (
                '<div style="font-size:11px;font-weight:900;color:#94a3b8;text-transform:uppercase;'
                'letter-spacing:0.05em;margin:18px 0 10px 0;'
                'border-top:1px solid #1e293b;padding-top:14px;">'
                f'Historial reciente ({len(atendidas)})</div>'
                + "".join(_card_atendida(l) for l in atendidas)
            )
        cards_html = pendientes_html + atendidas_html
        modal = doc.createElement("div")
        modal.id = "vs-alertas-modal"
        modal.style.cssText = (
            "position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,0.72);"
            "display:flex;align-items:flex-start;justify-content:center;padding:40px 16px;"
            "backdrop-filter:blur(6px);"
        )
        modal.innerHTML = (
            '<div style="width:100%;max-width:520px;background:#020617;'
            'border:1px solid #1e293b;border-radius:20px;padding:20px 20px 24px 20px;'
            'box-shadow:0 20px 60px rgba(0,0,0,0.7);">'
            '  <div style="display:flex;align-items:center;justify-content:space-between;'
            '    margin-bottom:14px;">'
            '    <h2 style="font-size:18px;font-weight:900;color:#f1f5f9;">'
            '      Alertas al Mesero</h2>'
            '    <button id="vs-alertas-close" '
            '      style="background:#1e293b;border:none;color:#cbd5e1;'
            '      width:36px;height:36px;border-radius:10px;cursor:pointer;'
            '      font-size:16px;">✕</button>'
            '  </div>'
            f'  <div>{cards_html}</div>'
            '</div>'
        )
        doc.body.appendChild(modal)
        # Listeners directos (el modal vive en <body>, fuera del form root).
        def _on_backdrop(ev):
            if ev.target.isSameNode(modal):
                self._cerrar_alertas()
        modal.addEventListener("click", _on_backdrop)
        close_btn = doc.getElementById("vs-alertas-close")
        if close_btn is not None:
            close_btn.addEventListener("click", lambda ev: self._cerrar_alertas())
        # Botones "Atender esta llamada" — un listener por cada botón.
        atender_btns = modal.querySelectorAll("[data-action='atenderAlerta']")
        for i in range(int(atender_btns.length)):
            btn = atender_btns.item(i)
            lid = int(btn.dataset.args)
            def _make_handler(llamada_id):
                return lambda ev: self._atender_alerta(llamada_id)
            btn.addEventListener("click", _make_handler(lid))

    def _cerrar_alertas(self, *_):
        doc = anvil.js.window.document
        modal = doc.getElementById("vs-alertas-modal")
        if modal is not None:
            modal.remove()

    def _atender_alerta(self, llamada_id, *_):
        try:
            anvil.server.call("atender_llamada", int(llamada_id))
        except Exception as e:
            print(f"[POSMesero] Error atendiendo llamada {llamada_id}: {e}")
            return
        # Refresco inmediato del badge y del modal
        self._tick_alertas()
        self._ver_alertas()
