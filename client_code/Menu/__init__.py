"""
Menu — form del cliente (teléfono / QR) v2.

Arquitectura:
- Estructura HTML declarativa + data-action; Python monta UN listener delegado.
- Al cargar: leer QR de la URL, hacer auto check-in via checkin_silla_qr,
  saludar con datos reales de la sesión.
- Sin onclick inline, sin <script> embebidos, sin shims.

Los endpoints de admin (guardar_producto, etc.) NO viven aquí — pertenecen al
form de Gestión de Menú futuro (Bloque H).

Bloque C.3 agregará: selector "estás pidiendo para", catálogo interactivo,
resumen por silla, botón enviar a cocina.
"""

from ._anvil_designer import MenuTemplate
import anvil
import anvil.js
import anvil.server
import json


class Menu(MenuTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self._root = None
        self._click_handler = None
        self._sesion_info = None  # {mesa_num, silla_num, qr, ocupacionId, ...}

        self.set_event_handler("show", self.form_show)
        self.set_event_handler("hide", self.form_hide)

    # ─────────────────────────── ciclo de vida ───────────────────────────
    def form_show(self, **event_args):
        self._root = anvil.js.get_dom_node(self)
        self._bind_events()
        info_qr = self._parsear_qr_de_url()
        if info_qr is not None:
            self._auto_checkin(info_qr)
        else:
            self._render_esperando_qr()

    def form_hide(self, **event_args):
        self._unbind_events()

    # ─────────────────── event delegation (Python owns) ──────────────────
    def _bind_events(self):
        if self._root is None:
            return
        self._click_handler = self._on_root_click
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
        el = target.closest("[data-action]")
        if el is None:
            return
        action = getattr(el.dataset, "action", None)
        args_raw = getattr(el.dataset, "args", None)
        args = [a.strip() for a in (args_raw or "").split(",") if a.strip()] if args_raw else []
        if action == "navHub":
            anvil.open_form("AdminMenu")
        elif action == "tab":
            self._cambiar_tab(args[0] if args else "silla")
        elif action == "llamarMesero":
            self._llamar_mesero()
        elif action == "solicitarCuenta":
            self._solicitar_cuenta()
        elif action == "reintentarCheckin":
            info = self._parsear_qr_de_url()
            if info:
                self._auto_checkin(info)
            else:
                self._render_esperando_qr()

    # ─────────────────── parsing del hash de URL con QR ──────────────────
    def _parsear_qr_de_url(self):
        """Retorna dict {mesa_num, silla_num, qr} o None."""
        try:
            url_hash = anvil.get_url_hash() or ""
        except Exception:
            return None
        if not url_hash:
            return None
        if isinstance(url_hash, dict):
            return self._dict_a_info(url_hash)
        # Cadena tipo "qr=PV-P-01-01" o "mesa=1&silla=1&qr=..."
        s = str(url_hash).lstrip("#").lstrip("?")
        params = {}
        for part in s.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.strip().lower()] = v.strip()
        # También aceptamos el QR completo pegado directo (sin key=value)
        if not params and s.upper().startswith("PV-"):
            params["qr"] = s
        return self._dict_a_info(params) if params else None

    def _dict_a_info(self, params):
        qr = str(params.get("qr", "")).upper()
        mesa_num = params.get("mesa")
        silla_num = params.get("silla")
        # Decodificar el QR PV-P-MM-SS
        if qr and qr.startswith("PV-P-"):
            partes = qr.split("-")
            # Formatos válidos: PV-P-MM-SS o PV-P-EX-NN
            if len(partes) == 4:
                if partes[2] == "EX":
                    # Extra del pool
                    return {"qr": qr, "mesa_num": 0, "silla_num": int(partes[3]),
                            "es_extra": True}
                try:
                    mesa_num = int(partes[2])
                    silla_num = int(partes[3])
                except ValueError:
                    pass
        try:
            mesa_num = int(mesa_num) if mesa_num is not None else None
            silla_num = int(silla_num) if silla_num is not None else None
        except (ValueError, TypeError):
            return None
        if mesa_num is None or silla_num is None:
            return None
        return {"qr": qr, "mesa_num": mesa_num, "silla_num": silla_num, "es_extra": False}

    # ─────────────────────── auto check-in por QR ────────────────────────
    def _auto_checkin(self, info):
        # qr_previo permite al backend distinguir 3 escenarios:
        # - Silla libre + qr_previo distinto → cambio de lugar silencioso
        #   (cierra la ocupación previa, abre la nueva).
        # - Silla ocupada + qr_previo COINCIDE → misma sesión (idempotente).
        # - Silla ocupada + qr_previo NO coincide → CONFLICTO
        #   (backend crea alerta al mesero, retorna error 'silla_ocupada_por_otro').
        mi_qr_previo = None
        try:
            mi_qr_previo = anvil.js.window.localStorage.getItem("vs_mi_qr_actual")
        except Exception:
            pass
        try:
            resp = anvil.server.call(
                "checkin_silla_qr",
                info["mesa_num"], info["silla_num"], info["qr"],
                qr_previo=mi_qr_previo,
            )
        except Exception as e:
            print(f"[Menu] Error en checkin_silla_qr: {e}")
            self._render_error("No pude registrar tu llegada. Intenta escanear de nuevo.")
            return
        if not isinstance(resp, dict):
            self._render_error("Respuesta inesperada del servidor.")
            return
        err = resp.get("error")
        if err == "silla_ocupada_por_otro":
            # El backend ya creó la alerta al mesero. Le decimos al cliente.
            self._render_silla_ajena(info["qr"])
            return
        if err:
            self._render_error(
                "Hubo un problema al registrar tu llegada. "
                "Por favor llama al mesero para que te ayude."
            )
            return
        # Check-in exitoso: guardar mi QR en localStorage (usado en próximo escaneo).
        try:
            anvil.js.window.localStorage.setItem("vs_mi_qr_actual", info["qr"])
        except Exception:
            pass
        self._sesion_info = {**info, **resp}
        self._render_bienvenida()

    def _render_silla_ajena(self, qr):
        html = f"""
        <div class="max-w-md mx-auto min-h-screen flex flex-col items-center
                    justify-center px-6 text-center bg-[#090d16] text-slate-100">
          <div class="w-16 h-16 rounded-full bg-amber-500/20 border
                      border-amber-500/50 flex items-center justify-center mb-4">
            <i class="fa-solid fa-user-lock text-amber-400 text-2xl"></i>
          </div>
          <h2 class="text-xl font-bold">Silla ocupada</h2>
          <p class="mt-3 text-slate-400 text-sm max-w-xs">
            El portavasos <b class="text-slate-200">{qr}</b> ya está en uso
            por otro comensal.
          </p>
          <p class="mt-4 text-slate-500 text-xs max-w-xs">
            Si te acabas de sentar aquí, por favor llama al mesero para que
            te acomode.
          </p>
        </div>
        """
        self._reemplazar_contenido(html)

    # ─────────────────────── renderers de pantallas ──────────────────────
    def _render_esperando_qr(self):
        """Pantalla mínima si alguien entra sin QR. En el flujo real el cliente
        siempre llega con QR desde su cámara."""
        html = """
        <div class="max-w-md mx-auto min-h-screen flex flex-col items-center
                    justify-center px-6 text-center bg-[#090d16] text-slate-100">
          <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-500
                      to-teal-700 flex items-center justify-center text-xl
                      font-black text-white mb-5 shadow-lg">
            V&amp;S
          </div>
          <h1 class="text-xl font-black">La Terraza de Vida &amp; Sabor</h1>
          <p class="mt-4 text-slate-400 text-sm max-w-xs">
            Escanea el código QR del portavasos de tu silla para comenzar.
          </p>
          <i class="fa-solid fa-qrcode text-4xl text-slate-600 mt-6"></i>
        </div>
        """
        self._reemplazar_contenido(html)

    def _render_error(self, mensaje):
        html = f"""
        <div class="max-w-md mx-auto min-h-screen flex flex-col items-center
                    justify-center px-6 text-center bg-[#090d16] text-slate-100">
          <div class="w-16 h-16 rounded-full bg-red-500/20 border border-red-500/50
                      flex items-center justify-center mb-4">
            <i class="fa-solid fa-triangle-exclamation text-red-400 text-2xl"></i>
          </div>
          <h2 class="text-xl font-bold">Algo no cuadró</h2>
          <p class="mt-2 text-slate-400 text-sm max-w-xs">{mensaje}</p>
          <button data-action="reintentarCheckin"
                  class="mt-8 px-6 py-3 rounded-2xl bg-emerald-600
                         hover:bg-emerald-500 text-white font-bold text-sm">
            Reintentar
          </button>
        </div>
        """
        self._reemplazar_contenido(html)

    def _render_bienvenida(self):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num", "?")
        silla = info.get("sillaId") or info.get("silla_num", "?")
        qr = info.get("qrId") or info.get("qr", "")
        estado = info.get("estado", "ocupada")
        badge_txt = "SILLA OCUPADA" if estado == "ocupada" else "DISPONIBLE"
        badge_bg = "bg-emerald-500/20 border-emerald-500 text-emerald-300"

        html = f"""
        <div class="max-w-md mx-auto min-h-screen bg-[#090d16] text-slate-100
                    font-sans pb-24">
          <header class="sticky top-0 z-40 backdrop-blur bg-[#0f172ad9]
                         border-b border-white/10 px-4 py-3
                         flex items-center justify-between gap-2">
            <div class="flex items-center gap-2.5">
              <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500
                          to-teal-700 flex items-center justify-center
                          text-sm font-black text-white shadow">V&amp;S</div>
              <div>
                <h1 class="text-sm font-black leading-tight">La Terraza de Vida &amp; Sabor</h1>
                <p class="text-[10px] text-emerald-400 font-bold uppercase
                          tracking-wider">Menú Digital</p>
              </div>
            </div>
            <div class="flex gap-1.5">
              <button data-action="llamarMesero"
                      class="px-2.5 py-1.5 text-[11px] font-bold rounded-lg
                             bg-amber-500/20 border border-amber-500/50
                             text-amber-300 flex items-center gap-1.5">
                <i class="fa-solid fa-bell text-xs"></i> Mesero
              </button>
              <button data-action="solicitarCuenta"
                      class="px-2.5 py-1.5 text-[11px] font-bold rounded-lg
                             bg-sky-500/20 border border-sky-500/50
                             text-sky-300 flex items-center gap-1.5">
                <i class="fa-solid fa-receipt text-xs"></i> Cuenta
              </button>
            </div>
          </header>

          <section class="px-4 mt-5">
            <div class="rounded-2xl border border-emerald-500/30
                        bg-gradient-to-br from-emerald-950/60 to-slate-900/60
                        p-5 shadow-xl">
              <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
                <span class="text-[10px] font-black px-2.5 py-1 rounded-full
                             {badge_bg} border tracking-wider">{badge_txt}</span>
                <span class="text-[10px] font-mono text-slate-400
                             bg-slate-800/60 px-2 py-1 rounded-full">
                  Portavasos {qr}
                </span>
              </div>
              <h2 class="text-lg font-black text-white leading-tight">
                ¡Hola! Estás en la <span class="text-emerald-400">Mesa {mesa}</span> ·
                Silla {silla}
              </h2>
              <p class="text-sm text-slate-400 mt-1">
                Ya registramos tu llegada. Desde aquí puedes ordenar cuando gustes.
              </p>
            </div>
          </section>

          <section class="px-4 mt-6 flex flex-col gap-3">
            <button data-action="tab" data-args="silla"
                    class="text-left rounded-2xl bg-slate-900/60 border
                           border-white/5 hover:border-emerald-500/40 p-4
                           transition flex items-center gap-3">
              <div class="w-11 h-11 rounded-xl bg-emerald-500/15 border
                          border-emerald-500/30 flex items-center justify-center
                          text-lg flex-shrink-0">🍳</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-black">Ordenar a Mi Silla</div>
                <div class="text-[11px] text-slate-400">
                  Bebidas, huevos y platillos individuales a tu cuenta.
                </div>
              </div>
              <i class="fa-solid fa-arrow-right text-slate-500 text-sm flex-shrink-0"></i>
            </button>
            <button data-action="tab" data-args="centro"
                    class="text-left rounded-2xl bg-slate-900/60 border
                           border-white/5 hover:border-amber-500/40 p-4
                           transition flex items-center gap-3">
              <div class="w-11 h-11 rounded-xl bg-amber-500/15 border
                          border-amber-500/30 flex items-center justify-center
                          text-lg flex-shrink-0">🍲</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-black">Pedir al Centro</div>
                <div class="text-[11px] text-slate-400">
                  Botanas, chilaquiles o jarras para compartir en tu mesa.
                </div>
              </div>
              <i class="fa-solid fa-arrow-right text-slate-500 text-sm flex-shrink-0"></i>
            </button>
            <button data-action="tab" data-args="para_otra"
                    class="text-left rounded-2xl bg-slate-900/60 border
                           border-white/5 hover:border-purple-500/40 p-4
                           transition flex items-center gap-3">
              <div class="w-11 h-11 rounded-xl bg-purple-500/15 border
                          border-purple-500/30 flex items-center justify-center
                          text-lg flex-shrink-0">👨‍👧</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-black">Pedir para Otra Silla</div>
                <div class="text-[11px] text-slate-400">
                  Ayuda a un niño, adulto mayor o compañero de mesa
                  con su orden.
                </div>
              </div>
              <i class="fa-solid fa-arrow-right text-slate-500 text-sm flex-shrink-0"></i>
            </button>
            <button data-action="tab" data-args="comanda"
                    class="text-left rounded-2xl bg-slate-900/60 border
                           border-white/5 hover:border-sky-500/40 p-4
                           transition flex items-center gap-3">
              <div class="w-11 h-11 rounded-xl bg-sky-500/15 border
                          border-sky-500/30 flex items-center justify-center
                          text-lg flex-shrink-0">🧾</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-black">Mi Comanda</div>
                <div class="text-[11px] text-slate-400">
                  Consulta lo que llevas hasta el momento.
                </div>
              </div>
              <i class="fa-solid fa-arrow-right text-slate-500 text-sm flex-shrink-0"></i>
            </button>
          </section>

          <div id="menuMainPanel" class="px-4 mt-6"></div>

          <div class="text-center mt-10 text-[10px] text-slate-600">
            La Terraza de Vida &amp; Sabor · Menú Cliente v2
          </div>
        </div>
        """
        self._reemplazar_contenido(html)

    def _reemplazar_contenido(self, html):
        """Reemplaza el contenido dentro del root del form con el HTML dado."""
        if self._root is None:
            return
        self._root.innerHTML = html

    # ─────────────────────── acciones (placeholders para C.3) ────────────
    def _cambiar_tab(self, tab_id):
        """Placeholder: Bloque C.3 renderiza aquí el catálogo/resumen."""
        panel = anvil.js.window.document.getElementById("menuMainPanel")
        if panel is None:
            return
        titulos = {
            "silla":     "🍳 Ordenar a Mi Silla",
            "centro":    "🍲 Pedir al Centro",
            "para_otra": "👨‍👧 Pedir para Otra Silla",
            "comanda":   "🧾 Mi Comanda",
        }
        titulo = titulos.get(tab_id, "Sección")
        panel.innerHTML = (
            "<div class='rounded-2xl bg-slate-900/60 border border-white/5 "
            "p-6 text-center'>"
            f"<h3 class='text-base font-black text-white'>{titulo}</h3>"
            "<p class='text-xs text-slate-400 mt-2'>"
            "El catálogo interactivo llega en el siguiente paso (Bloque C.3)."
            "</p></div>"
        )

    def _llamar_mesero(self):
        self._enviar_llamada("llamar_mesero",
                             "Se avisó al mesero. Alguien llegará pronto.")

    def _solicitar_cuenta(self):
        self._enviar_llamada("solicitar_cuenta",
                             "Notificamos tu solicitud. El mesero te traerá la cuenta.")

    def _enviar_llamada(self, tipo, mensaje_ok):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        silla = info.get("silla_num")
        if not mesa or not silla:
            anvil.alert("Primero registra tu llegada escaneando el QR.",
                        title="Sin silla activa")
            return
        try:
            resp = anvil.server.call("crear_llamada_mesero", mesa, silla, tipo)
        except Exception as e:
            print(f"[Menu] Error en crear_llamada_mesero: {e}")
            anvil.alert("No pudimos avisar al mesero. Intenta otra vez.",
                        title="Error")
            return
        if isinstance(resp, dict) and resp.get("ok"):
            anvil.alert(mensaje_ok, title="Aviso enviado")
        else:
            anvil.alert("No pudimos avisar al mesero.", title="Error")
