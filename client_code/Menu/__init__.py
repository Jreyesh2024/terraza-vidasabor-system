"""
Menu — form del cliente (teléfono / QR) v2.

Arquitectura:
- Estructura HTML declarativa + data-action; Python monta UN listener delegado.
- Al cargar: leer QR de la URL, hacer auto check-in via checkin_silla_qr,
  saludar con datos reales de la sesión.
- Sin onclick inline, sin <script> embebidos, sin shims.

Los endpoints de admin (guardar_producto, etc.) pertenecen al form de
Gestión de Menú futuro (Bloque H).
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
        # Estado del catálogo
        self._menu_productos = []      # array de productos desde vw_menu_cliente
        self._menu_categorias = []     # array de categorías únicas ordenadas
        self._destino_actual = "mi_silla"  # 'mi_silla' | 'al_centro' | 'otra_silla'
        self._silla_destino_num = None      # cuando 'otra_silla'
        self._timer_llamada = None
        self._llamada_id_pollend = None

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
        if self._timer_llamada is not None:
            try:
                self._timer_llamada.interval = 0
            except Exception:
                pass
            self._timer_llamada = None

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
            args_procesados = self._preprocesar_args_tab(args)
            if args_procesados is None:
                return  # ya fue manejado por el prefijo __setSilla
            self._cambiar_tab(args_procesados[0] if args_procesados else "silla")
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
        elif action == "volverInicio":
            self._render_bienvenida()
        elif action == "abrirCategoria":
            cat_id = int(args[0]) if args else 0
            self._render_productos_de_categoria(cat_id)
        elif action == "volverCategorias":
            self._render_tab_ordenar(self._destino_actual)
        elif action == "abrirProducto":
            pid = int(args[0]) if args else 0
            self._render_producto_detalle(pid)
        elif action == "cerrarProducto":
            self._cerrar_modal_producto()
        elif action == "cambiarCantidad":
            self._cambiar_cantidad_modal(int(args[0]) if args else 0)
        elif action == "agregarItem":
            pid = int(args[0]) if args else 0
            self._enviar_agregar_item(pid)
        elif action == "verComanda":
            self._render_mi_comanda()
        elif action == "eliminarItem":
            det_id = int(args[0]) if args else 0
            self._eliminar_item(det_id)
        elif action == "enviarCocina":
            self._enviar_a_cocina()

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

        s = str(url_hash).lstrip("#").lstrip("?")
        if s.startswith("menu?"):
            s = s[5:]
        elif s.startswith("menu"):
            s = s[4:].lstrip("?").lstrip("&")

        params = {}
        for part in s.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.strip().lower()] = v.strip()

        # También aceptamos el QR completo pegado directo (sin key=value)
        if not params and (s.upper().startswith("PV-") or s.upper().startswith("PV")):
            params["qr"] = s

        return self._dict_a_info(params) if params else None

    def _dict_a_info(self, params):
        qr = str(params.get("qr", "")).upper().strip()
        mesa_num = params.get("mesa")
        silla_num = params.get("silla")

        # Formato v2: PV-P-MM-SS (Palapa) o PV-P-EX-NN
        if qr and qr.startswith("PV-P-"):
            partes = qr.split("-")
            if len(partes) == 4:
                if partes[2] == "EX":
                    return {"qr": qr, "mesa_num": 0, "silla_num": int(partes[3]), "es_extra": True}
                try:
                    mesa_num = int(partes[2])
                    silla_num = int(partes[3])
                except ValueError:
                    pass

        # Formato abreviado: PV-011, PV-012, PV-021, etc.
        elif qr and (qr.startswith("PV-0") or qr.startswith("PV-1") or qr.startswith("PV-2") or qr.startswith("PV-3")):
            digitos = qr.replace("PV-", "").replace("PV", "")
            if len(digitos) >= 3:
                try:
                    mesa_num = int(digitos[0:2])
                    silla_num = int(digitos[2:])
                except ValueError:
                    pass

        try:
            mesa_num = int(mesa_num) if mesa_num is not None else None
            silla_num = int(silla_num) if silla_num is not None else None
        except (ValueError, TypeError):
            return None

        if mesa_num is None or silla_num is None:
            return None

        if not qr:
            qr = f"PV-P-{mesa_num:02d}-{silla_num:02d}"

        return {"qr": qr, "mesa_num": mesa_num, "silla_num": silla_num, "es_extra": False}

    # ─────────────────────── auto check-in por QR ────────────────────────
    def _auto_checkin(self, info):
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
            self._render_error("No pudimos registrar tu llegada. Por favor intenta escanear de nuevo.")
            return

        if not isinstance(resp, dict):
            self._render_error("Respuesta inesperada del servidor.")
            return

        err = resp.get("error")
        if err == "silla_ocupada_por_otro":
            self._render_silla_ajena(info["qr"])
            return

        if err:
            self._render_error(
                "Hubo un problema al registrar tu llegada. "
                "Por favor solicita ayuda a tu mesero."
            )
            return

        try:
            anvil.js.window.localStorage.setItem("vs_mi_qr_actual", info["qr"])
        except Exception:
            pass

        self._sesion_info = {**info, **resp}
        self._render_bienvenida()

    def _render_silla_ajena(self, qr):
        html = f"""
        <div class="min-h-screen max-w-md mx-auto px-6 py-12 flex flex-col items-center justify-center text-center bg-[#090d16] text-slate-100 font-sans">
          <div class="w-20 h-20 rounded-3xl bg-amber-500/10 border-2 border-amber-500/40 flex items-center justify-center mb-6 shadow-2xl shadow-amber-500/20">
            <i class="fa-solid fa-chair text-amber-400 text-3xl"></i>
          </div>
          <span class="px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-black uppercase tracking-wider mb-3">
            Silla Ocupada
          </span>
          <h2 class="text-2xl font-black text-white tracking-tight">Portavasos en Uso</h2>
          <p class="mt-3 text-slate-400 text-sm leading-relaxed max-w-xs">
            El código <b class="text-white font-mono">{qr}</b> ya está asignado a otro comensal en esta mesa.
          </p>
          <div class="w-full mt-8 p-4 rounded-2xl bg-slate-900/80 border border-white/10 text-xs text-slate-300">
            <p>Si te acabas de sentar aquí, el mesero ya fue notificado para reasignarte.</p>
          </div>
          <button data-action="reintentarCheckin"
                  class="w-full mt-6 py-3.5 px-6 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-black text-sm shadow-lg active:scale-95 transition">
            <i class="fa-solid fa-rotate-right mr-2"></i> Reintentar escaneo
          </button>
        </div>
        """
        self._reemplazar_contenido(html)

    def _render_esperando_qr(self):
        """Pantalla ilustrada cuando se abre la app sin parámetros de QR."""
        html = """
        <div class="min-h-screen max-w-md mx-auto px-6 py-12 flex flex-col items-center justify-center text-center bg-[#090d16] text-slate-100 font-sans">
          <div class="w-24 h-24 rounded-3xl bg-gradient-to-tr from-emerald-500 via-teal-600 to-emerald-400 p-0.5 shadow-[0_0_40px_rgba(16,185,129,0.35)] mb-6 flex items-center justify-center">
            <div class="w-full h-full bg-[#090d16] rounded-[22px] flex items-center justify-center">
              <span class="text-3xl font-black bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">V&amp;S</span>
            </div>
          </div>
          
          <h1 class="text-2xl font-black text-white tracking-tight leading-tight">La Terraza de Vida &amp; Sabor</h1>
          <p class="text-emerald-400 font-bold text-xs uppercase tracking-widest mt-1 mb-6">Menú Digital Interactivo</p>
          
          <div class="w-full p-5 rounded-3xl bg-slate-900/80 border border-white/10 shadow-xl backdrop-blur-md text-center">
            <div class="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-2xl text-emerald-400 mb-3">
              <i class="fa-solid fa-qrcode"></i>
            </div>
            <h3 class="text-base font-black text-white">Escanea tu Portavasos</h3>
            <p class="mt-2 text-xs text-slate-400 leading-relaxed">
              Abre la cámara de tu celular y apunta al código QR ubicado en el portavasos de tu silla para ordenar al instante.
            </p>
          </div>

          <div class="mt-8 text-center text-[11px] text-slate-500 flex items-center justify-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Sistema activo · Palapa La Terraza
          </div>
        </div>
        """
        self._reemplazar_contenido(html)

    def _render_error(self, mensaje):
        html = f"""
        <div class="min-h-screen max-w-md mx-auto px-6 py-12 flex flex-col items-center justify-center text-center bg-[#090d16] text-slate-100 font-sans">
          <div class="w-20 h-20 rounded-3xl bg-red-500/15 border-2 border-red-500/40 flex items-center justify-center mb-5 shadow-2xl shadow-red-500/20">
            <i class="fa-solid fa-triangle-exclamation text-red-400 text-3xl"></i>
          </div>
          <h2 class="text-xl font-black text-white">No pudimos conectar</h2>
          <p class="mt-2 text-slate-400 text-sm max-w-xs leading-relaxed">{mensaje}</p>
          <button data-action="reintentarCheckin"
                  class="w-full mt-8 py-3.5 px-6 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-sm shadow-lg active:scale-95 transition">
            <i class="fa-solid fa-rotate-right mr-2"></i> Reintentar
          </button>
        </div>
        """
        self._reemplazar_contenido(html)

    def _render_bienvenida(self):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num", "?")
        silla = info.get("sillaId") or info.get("silla_num", "?")
        qr = info.get("qrId") or info.get("qr", "")
        comensal = info.get("comensalNombre") or f"Comensal Silla {silla}"

        html = f"""
        <div class="min-h-screen max-w-md mx-auto bg-[#090d16] text-slate-100 font-sans pb-28">
          {self._header_html()}

          <!-- HERO CARD DE BIENVENIDA -->
          <section class="px-4 mt-4">
            <div class="relative overflow-hidden rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-emerald-950/60 via-slate-900/90 to-teal-950/40 p-5 shadow-[0_15px_35px_-10px_rgba(16,185,129,0.25)]">
              <div class="flex items-center justify-between gap-2 mb-3">
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 text-[10px] font-black uppercase tracking-wider">
                  <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  Sesión Activa
                </span>
                <span class="font-mono text-[11px] text-slate-300 bg-slate-800/80 px-2.5 py-0.5 rounded-full border border-white/5">
                  {qr}
                </span>
              </div>
              
              <h2 class="text-xl font-black text-white leading-tight">
                ¡Hola! <span class="text-emerald-400">Mesa {mesa}</span> · Silla {silla}
              </h2>
              <p class="text-xs text-slate-300 mt-1">
                {comensal}. Explora nuestro menú y ordena directamente a tu silla o comparte con tu mesa.
              </p>
            </div>
          </section>

          <!-- 4 TARJETAS PRINCIPALES DE ACCIÓN -->
          <section class="px-4 mt-5 flex flex-col gap-3">
            <!-- 1. ORDENAR A MI SILLA -->
            <button data-action="tab" data-args="silla"
                    class="w-full text-left rounded-3xl bg-slate-900/80 border border-emerald-500/30 hover:border-emerald-400/80 p-4 transition-all shadow-lg active:scale-[0.98] flex items-center gap-3.5 group">
              <div class="w-13 h-13 w-[52px] h-[52px] rounded-2xl bg-gradient-to-tr from-emerald-500/25 to-teal-500/10 border border-emerald-500/40 flex items-center justify-center text-2xl flex-shrink-0 shadow-inner group-hover:scale-105 transition">
                🍳
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-[15px] font-black text-white flex items-center gap-2">
                  Ordenar a Mi Silla
                  <span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Personal</span>
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5 leading-snug">
                  Bebidas, desayunos y platillos que se cargan a tu cuenta.
                </div>
              </div>
              <div class="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-emerald-400 group-hover:bg-emerald-500/10 transition">
                <i class="fa-solid fa-chevron-right text-xs"></i>
              </div>
            </button>

            <!-- 2. PEDIR AL CENTRO -->
            <button data-action="tab" data-args="centro"
                    class="w-full text-left rounded-3xl bg-slate-900/80 border border-amber-500/30 hover:border-amber-400/80 p-4 transition-all shadow-lg active:scale-[0.98] flex items-center gap-3.5 group">
              <div class="w-[52px] h-[52px] rounded-2xl bg-gradient-to-tr from-amber-500/25 to-orange-500/10 border border-amber-500/40 flex items-center justify-center text-2xl flex-shrink-0 shadow-inner group-hover:scale-105 transition">
                🍲
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-[15px] font-black text-white flex items-center gap-2">
                  Pedir al Centro
                  <span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">Compartido</span>
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5 leading-snug">
                  Entradas, botanas o jarras para todos en la mesa.
                </div>
              </div>
              <div class="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-amber-400 group-hover:bg-amber-500/10 transition">
                <i class="fa-solid fa-chevron-right text-xs"></i>
              </div>
            </button>

            <!-- 3. PEDIR PARA OTRA SILLA -->
            <button data-action="tab" data-args="para_otra"
                    class="w-full text-left rounded-3xl bg-slate-900/80 border border-purple-500/30 hover:border-purple-400/80 p-4 transition-all shadow-lg active:scale-[0.98] flex items-center gap-3.5 group">
              <div class="w-[52px] h-[52px] rounded-2xl bg-gradient-to-tr from-purple-500/25 to-indigo-500/10 border border-purple-500/40 flex items-center justify-center text-2xl flex-shrink-0 shadow-inner group-hover:scale-105 transition">
                👨‍👧
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-[15px] font-black text-white flex items-center gap-2">
                  Pedir para Otra Silla
                  <span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">Ayuda</span>
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5 leading-snug">
                  Pide a nombre de niños, adultos mayores o acompañantes.
                </div>
              </div>
              <div class="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-purple-400 group-hover:bg-purple-500/10 transition">
                <i class="fa-solid fa-chevron-right text-xs"></i>
              </div>
            </button>

            <!-- 4. MI COMANDA Y CUENTA -->
            <button data-action="tab" data-args="comanda"
                    class="w-full text-left rounded-3xl bg-slate-900/80 border border-sky-500/30 hover:border-sky-400/80 p-4 transition-all shadow-lg active:scale-[0.98] flex items-center gap-3.5 group">
              <div class="w-[52px] h-[52px] rounded-2xl bg-gradient-to-tr from-sky-500/25 to-blue-500/10 border border-sky-500/40 flex items-center justify-center text-2xl flex-shrink-0 shadow-inner group-hover:scale-105 transition">
                🧾
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-[15px] font-black text-white flex items-center gap-2">
                  Mi Comanda &amp; Cuenta
                  <span class="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">En Vivo</span>
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5 leading-snug">
                  Revisa platillos pedidos, estado de cocina y subtotal.
                </div>
              </div>
              <div class="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-sky-400 group-hover:bg-sky-500/10 transition">
                <i class="fa-solid fa-chevron-right text-xs"></i>
              </div>
            </button>
          </section>

          <div class="mt-8 text-center text-[11px] text-slate-500">
            La Terraza de Vida &amp; Sabor · Experiencia Digital
          </div>
        </div>
        """
        self._reemplazar_contenido(html)

    def _reemplazar_contenido(self, html):
        """Reemplaza el contenido dentro del root del form con el HTML dado."""
        if self._root is None:
            return
        self._root.innerHTML = html

    # ─────────────────────── enrutamiento de tabs ────────────────────────
    def _cambiar_tab(self, tab_id):
        if tab_id == "silla":
            self._destino_actual = "mi_silla"
            self._silla_destino_num = None
            self._render_tab_ordenar("mi_silla")
        elif tab_id == "centro":
            self._destino_actual = "al_centro"
            self._silla_destino_num = None
            self._render_tab_ordenar("al_centro")
        elif tab_id == "para_otra":
            self._render_selector_silla_destino()
        elif tab_id == "comanda":
            self._render_mi_comanda()

    # ─────────────────────── carga del catálogo ──────────────────────────
    def _asegurar_menu_cargado(self):
        if self._menu_productos:
            return True
        try:
            productos = anvil.server.call("get_menu_cliente") or []
        except Exception as e:
            print(f"[Menu] Error cargando get_menu_cliente: {e}")
            productos = []
        self._menu_productos = productos
        vistas = {}
        for p in productos:
            cid = p.get("categoria_id")
            if cid is None or cid in vistas:
                continue
            vistas[cid] = {
                "id": cid,
                "codigo": p.get("categoria_codigo", ""),
                "nombre": p.get("categoria_nombre", ""),
                "icono": p.get("categoria_icono", "🍽️"),
                "orden": p.get("categoria_orden", 99),
            }
        self._menu_categorias = sorted(vistas.values(), key=lambda c: c["orden"])
        return True

    # ─────────────────── vista TAB ORDENAR (categorías 2 col) ─────────────
    def _render_tab_ordenar(self, destino):
        self._destino_actual = destino
        self._asegurar_menu_cargado()
        cabeceras = {
            "mi_silla":  ("🍳", "Ordenar a Mi Silla", "emerald", "Platillos individuales para tu comanda."),
            "al_centro": ("🍲", "Pedir al Centro", "amber", "Platillos para compartir en la mesa."),
            "otra_silla": ("👨‍👧", f"Pedir para Silla {self._silla_destino_num or '?'}", "purple", f"Se cargará a la Silla {self._silla_destino_num}."),
        }
        icono, titulo, tono, sub = cabeceras.get(destino, ("🍽️", "Menú", "emerald", ""))

        color_styles = {
            "emerald": {
                "bg": "from-emerald-500/20 to-slate-900/80",
                "border": "border-emerald-500/30 hover:border-emerald-400",
                "badge": "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
            },
            "amber": {
                "bg": "from-amber-500/20 to-slate-900/80",
                "border": "border-amber-500/30 hover:border-amber-400",
                "badge": "bg-amber-500/20 text-amber-300 border-amber-500/40",
            },
            "purple": {
                "bg": "from-purple-500/20 to-slate-900/80",
                "border": "border-purple-500/30 hover:border-purple-400",
                "badge": "bg-purple-500/20 text-purple-300 border-purple-500/40",
            }
        }[tono]

        resumen_al_centro = ""
        if destino == "al_centro":
            resumen_al_centro = self._resumen_al_centro_html()

        cats_html = ""
        for c in self._menu_categorias:
            es_al_centro_cat = "al centro" in (c.get("nombre", "").lower())
            if destino != "al_centro" and es_al_centro_cat:
                continue
            
            cats_html += f"""
            <button data-action="abrirCategoria" data-args="{c['id']}"
                    class="rounded-3xl border border-white/10 bg-gradient-to-b from-slate-800/80 to-slate-900/90 hover:border-emerald-400/50 p-4 flex flex-col items-center justify-center gap-2.5 min-h-[135px] transition-all shadow-lg active:scale-95 text-center group">
              <div class="w-14 h-14 rounded-2xl bg-slate-950/70 border border-white/10 flex items-center justify-center text-3xl group-hover:scale-110 transition drop-shadow-md">
                {c['icono']}
              </div>
              <span class="text-xs font-black text-white leading-tight mt-1">{c['nombre']}</span>
            </button>
            """

        html = f"""
        <div class="min-h-screen max-w-md mx-auto bg-[#090d16] text-slate-100 font-sans pb-28">
          {self._header_html()}
          
          <section class="px-4 pt-4">
            <button data-action="volverInicio"
                    class="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white py-1.5 px-3 rounded-xl bg-slate-900/60 border border-white/5 mb-3 transition">
              <i class="fa-solid fa-arrow-left text-[11px]"></i> Volver al inicio
            </button>

            <div class="rounded-3xl border {color_styles['border']} bg-gradient-to-br {color_styles['bg']} p-4 shadow-xl">
              <div class="flex items-center gap-3.5">
                <div class="w-12 h-12 rounded-2xl bg-slate-950/70 border border-white/10 flex items-center justify-center text-2xl flex-shrink-0">
                  {icono}
                </div>
                <div>
                  <div class="text-base font-black text-white leading-tight">{titulo}</div>
                  <div class="text-xs text-slate-300 mt-0.5">{sub}</div>
                </div>
              </div>
            </div>
          </section>

          {resumen_al_centro}

          <section class="px-4 mt-5">
            <div class="text-[11px] font-black uppercase tracking-wider text-slate-400 mb-3 px-1">
              Selecciona una categoría
            </div>
            <div class="grid grid-cols-2 gap-3 pb-8">
              {cats_html or '<div class="col-span-2 text-center text-slate-500 py-10">No hay categorías disponibles.</div>'}
            </div>
          </section>
        </div>
        """
        self._reemplazar_contenido(html)

    def _resumen_al_centro_html(self):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        silla = info.get("silla_num")
        try:
            data = anvil.server.call("get_items_por_silla", mesa, silla) or {}
        except Exception:
            data = {}
        items_centro = data.get("items_al_centro", []) or []
        if not items_centro:
            return ""
        
        filas = ""
        total = 0.0
        for it in items_centro:
            precio = float(it.get("precio_unitario_snapshot") or 0)
            cant = int(it.get("cantidad") or 1)
            subt = float(it.get("subtotal") or (precio * cant))
            total += subt
            estado = it.get("estado", "borrador")
            badge = '<span class="text-[10px] text-emerald-400 font-bold ml-1.5">· en cocina</span>' if estado != "borrador" else ""
            nombre = it.get("producto_nombre_snapshot", "?")
            filas += f"""
            <div class="flex items-center justify-between py-2 border-b border-white/5 text-xs">
              <div class="flex-1 truncate">
                <span class="text-amber-300 font-black">{cant}×</span> 
                <span class="text-white ml-1 font-medium">{nombre}</span>{badge}
              </div>
              <div class="text-white font-black ml-2">${subt:,.2f}</div>
            </div>
            """

        return f"""
        <section class="px-4 mt-3">
          <div class="rounded-3xl border border-amber-500/30 bg-gradient-to-br from-amber-950/40 via-slate-900/90 to-slate-900/60 p-4 shadow-xl">
            <div class="flex items-center justify-between mb-2">
              <div class="text-[11px] font-black uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                <i class="fa-solid fa-users text-xs"></i> Ya pedido al centro de la mesa
              </div>
              <div class="text-xs font-black text-amber-300">${total:,.2f}</div>
            </div>
            {filas}
            <div class="mt-2 text-[10px] text-slate-400 text-center">
              Visible para todos los comensales en esta mesa.
            </div>
          </div>
        </section>
        """

    # ─────────────────── vista PRODUCTOS DE UNA CATEGORÍA ────────────────
    def _render_productos_de_categoria(self, cat_id):
        self._asegurar_menu_cargado()
        self._ultima_categoria_id = cat_id
        cat = next((c for c in self._menu_categorias if c["id"] == cat_id), None)
        productos = [p for p in self._menu_productos if p.get("categoria_id") == cat_id]
        if not productos:
            self._render_tab_ordenar(self._destino_actual)
            return

        items_html = ""
        for p in productos:
            precio = float(p.get("precio_unitario") or 0)
            tiempo = p.get("tiempo_estimado", "")
            desc = (p.get("descripcion") or "").strip()
            
            items_html += f"""
            <button data-action="abrirProducto" data-args="{p['id']}"
                    class="w-full text-left rounded-3xl bg-slate-900/80 border border-white/10 hover:border-emerald-500/50 p-4 flex items-center gap-3.5 transition-all shadow-md active:scale-[0.98] group">
              <div class="w-14 h-14 rounded-2xl bg-slate-950/70 border border-white/10 flex items-center justify-center text-3xl flex-shrink-0 group-hover:scale-105 transition shadow-inner">
                {p.get('icono','🍽️')}
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-black text-white truncate group-hover:text-emerald-300 transition">{p['nombre']}</div>
                {'<div class="text-[11px] text-slate-400 line-clamp-1 mt-0.5">' + desc + '</div>' if desc else ''}
                <div class="flex items-center gap-2 mt-1.5">
                  <span class="text-xs font-black text-emerald-400 bg-emerald-500/15 px-2 py-0.5 rounded-lg border border-emerald-500/30">
                    ${precio:,.2f}
                  </span>
                  {('<span class="text-[10px] text-slate-400"><i class="fa-regular fa-clock mr-1"></i>' + tiempo + '</span>') if tiempo else ''}
                </div>
              </div>
              <div class="w-9 h-9 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition flex-shrink-0">
                <i class="fa-solid fa-plus text-xs"></i>
              </div>
            </button>
            """

        cat_nombre = (cat or {}).get("nombre", "Menú")
        cat_icono = (cat or {}).get("icono", "🍽️")

        html = f"""
        <div class="min-h-screen max-w-md mx-auto bg-[#090d16] text-slate-100 font-sans pb-28">
          {self._header_html()}

          <section class="px-4 pt-4">
            <button data-action="volverCategorias"
                    class="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white py-1.5 px-3 rounded-xl bg-slate-900/60 border border-white/5 mb-3 transition">
              <i class="fa-solid fa-arrow-left text-[11px]"></i> Volver a categorías
            </button>
            <div class="flex items-center gap-2.5 mb-1">
              <span class="text-2xl">{cat_icono}</span>
              <h2 class="text-xl font-black text-white">{cat_nombre}</h2>
            </div>
            <p class="text-xs text-slate-400 px-0.5">Toca un platillo para ver opciones y agregarlo a tu orden.</p>
          </section>

          <section class="px-4 mt-4 flex flex-col gap-3 pb-8">
            {items_html}
          </section>
        </div>
        """
        self._reemplazar_contenido(html)

    # ─────────────────── vista DETALLE DE PRODUCTO (modal) ──────────────
    def _render_producto_detalle(self, producto_id):
        p = next((x for x in self._menu_productos if x.get("id") == producto_id), None)
        if p is None:
            return
        self._producto_actual = p
        self._cantidad_actual = 1
        self._pintar_modal_producto()

    def _pintar_modal_producto(self):
        p = getattr(self, "_producto_actual", None)
        if p is None:
            return
        cantidad = getattr(self, "_cantidad_actual", 1)
        precio = float(p.get("precio_unitario") or 0)
        subtotal = precio * cantidad
        desc = (p.get("descripcion") or "").strip()
        
        etiqueta_destino = {
            "mi_silla":   "🍳 Se cargará a TU silla",
            "al_centro":  "🍲 Al centro (compartido)",
            "otra_silla": f"👨‍👧 Se cargará a la Silla {self._silla_destino_num}",
        }.get(self._destino_actual, "")

        html = f"""
        <div id="menuProductoOverlay"
             class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-end justify-center p-0 font-sans animate-fade-in">
          <div class="w-full max-w-md bg-slate-900 border-t border-x border-white/15 rounded-t-[32px] p-6 shadow-2xl pb-10">
            <!-- PULL BAR -->
            <div class="w-12 h-1.5 bg-slate-700 rounded-full mx-auto mb-4"></div>

            <div class="flex items-start justify-between gap-3 mb-2">
              <div class="flex-1">
                <span class="inline-block text-[10px] font-black text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 rounded-full uppercase tracking-wider mb-1.5">
                  {etiqueta_destino}
                </span>
                <h3 class="text-xl font-black text-white leading-tight flex items-center gap-2">
                  <span>{p.get('icono','🍽️')}</span>
                  <span>{p['nombre']}</span>
                </h3>
              </div>
              <button data-action="cerrarProducto"
                      class="w-9 h-9 rounded-full bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center text-lg active:scale-90 transition">
                ✕
              </button>
            </div>

            {'<p class="text-xs text-slate-300 leading-relaxed mt-2 p-3 rounded-2xl bg-slate-950/60 border border-white/5">' + desc + '</p>' if desc else ''}

            <!-- SELECTOR DE CANTIDAD -->
            <div class="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-950/70 p-3.5 mt-4">
              <span class="text-xs font-black text-slate-300 uppercase tracking-wider">Cantidad</span>
              <div class="flex items-center gap-3">
                <button data-action="cambiarCantidad" data-args="-1"
                        class="w-10 h-10 rounded-xl bg-slate-800 border border-white/10 text-white text-xl font-black active:scale-90 transition flex items-center justify-center">
                  −
                </button>
                <span class="text-lg font-black text-white min-w-[28px] text-center font-mono">
                  {cantidad}
                </span>
                <button data-action="cambiarCantidad" data-args="1"
                        class="w-10 h-10 rounded-xl bg-slate-800 border border-white/10 text-white text-xl font-black active:scale-90 transition flex items-center justify-center">
                  +
                </button>
              </div>
            </div>

            <!-- BOTON AGREGAR CTA -->
            <button data-action="agregarItem" data-args="{p['id']}"
                    class="w-full mt-5 rounded-2xl bg-gradient-to-r from-emerald-500 via-teal-600 to-emerald-500 hover:from-emerald-400 hover:to-teal-500 text-white font-black text-sm py-4 shadow-[0_10px_25px_rgba(16,185,129,0.3)] flex items-center justify-center gap-2 active:scale-95 transition">
              <i class="fa-solid fa-plus text-xs"></i>
              Agregar a la Orden · ${subtotal:,.2f}
            </button>
          </div>
        </div>
        """

        doc = anvil.js.window.document
        existing = doc.getElementById("menuProductoOverlay")
        if existing is not None:
            existing.remove()

        wrapper = doc.createElement("div")
        wrapper.innerHTML = html
        while wrapper.firstChild:
            self._root.appendChild(wrapper.firstChild)

    def _cambiar_cantidad_modal(self, delta):
        c = getattr(self, "_cantidad_actual", 1) + int(delta)
        self._cantidad_actual = max(1, min(20, c))
        self._pintar_modal_producto()

    def _cerrar_modal_producto(self):
        doc = anvil.js.window.document
        modal = doc.getElementById("menuProductoOverlay")
        if modal is not None:
            modal.remove()

    def _enviar_agregar_item(self, producto_id):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        silla = info.get("silla_num")

        if not mesa or not silla:
            self._toast("Escanea el QR de tu silla para poder ordenar.", "warn")
            return

        para_silla_num = None
        if self._destino_actual == "al_centro":
            para_silla_num = 0
        elif self._destino_actual == "otra_silla":
            para_silla_num = self._silla_destino_num

        cant = int(getattr(self, "_cantidad_actual", 1))

        try:
            resp = anvil.server.call(
                "agregar_item_a_comanda",
                mesa, silla, int(producto_id),
                cantidad=cant,
                para_silla_num=para_silla_num,
            )
        except Exception as e:
            print(f"[Menu] Excepción agregar_item_a_comanda: {e}")
            self._toast("No pudimos agregar el platillo. Intenta de nuevo.", "err")
            return

        if not isinstance(resp, dict) or resp.get("error"):
            self._toast("Error: " + str((resp or {}).get("error", "?")), "err")
            return

        p = getattr(self, "_producto_actual", {}) or {}
        self._cerrar_modal_producto()
        self._toast(f"✓ Agregado: {cant}× {p.get('nombre','?')}", "ok")

    def _toast(self, mensaje, tipo="ok"):
        """Toast in-page moderno y no intrusivo."""
        doc = anvil.js.window.document
        prev = doc.getElementById("menuToast")
        if prev is not None:
            prev.remove()

        colores = {
            "ok":   ("linear-gradient(135deg,#10b981,#047857)", "#ffffff"),
            "warn": ("linear-gradient(135deg,#f59e0b,#b45309)", "#ffffff"),
            "err":  ("linear-gradient(135deg,#ef4444,#b91c1c)", "#ffffff"),
            "info": ("linear-gradient(135deg,#0ea5e9,#0369a1)", "#ffffff"),
        }
        bg, color = colores.get(tipo, colores["ok"])

        toast = doc.createElement("div")
        toast.id = "menuToast"
        toast.style.cssText = (
            f"position: fixed; bottom: 30px; left: 50%; "
            f"transform: translateX(-50%) translateY(90px); "
            f"z-index: 100000; padding: 12px 22px; "
            f"background: {bg}; color: {color}; "
            f"border-radius: 9999px; font-weight: 800; font-size: 13px; font-family: 'Plus Jakarta Sans', system-ui, sans-serif; "
            f"box-shadow: 0 14px 35px rgba(0,0,0,0.6); "
            f"max-width: 90vw; opacity: 0; "
            f"transition: transform 0.35s cubic-bezier(.34,1.56,.64,1), opacity 0.3s ease;"
        )
        toast.textContent = mensaje
        doc.body.appendChild(toast)

        anvil.js.window.setTimeout(
            lambda: (
                toast.style.setProperty("transform", "translateX(-50%) translateY(0)"),
                toast.style.setProperty("opacity", "1"),
            ), 20
        )
        anvil.js.window.setTimeout(
            lambda: (
                toast.style.setProperty("transform", "translateX(-50%) translateY(90px)"),
                toast.style.setProperty("opacity", "0"),
            ), 2400
        )
        anvil.js.window.setTimeout(lambda: toast.remove() if toast else None, 2900)

    # ─────────────────── vista MI COMANDA ────────────────────────────────
    def _render_mi_comanda(self):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        silla = info.get("silla_num")

        try:
            data = anvil.server.call("get_items_por_silla", mesa, silla) or {}
        except Exception as e:
            print(f"[Menu] Error get_items_por_silla: {e}")
            data = {"items_individuales": [], "items_al_centro": []}

        indiv = data.get("items_individuales", []) or []
        centro = data.get("items_al_centro", []) or []
        detalle_ids_borrador = [i["id"] for i in indiv + centro if str(i.get("estado")) == "borrador"]

        def _fila(item, es_al_centro=False, editable=True):
            precio = float(item.get("precio_unitario_snapshot") or 0)
            cantidad = int(item.get("cantidad") or 1)
            subtotal = float(item.get("subtotal") or (precio * cantidad))
            nombre = item.get("producto_nombre_snapshot", "?")
            estado = item.get("estado", "borrador")

            badge = ""
            if estado != "borrador":
                badge = '<span class="text-[10px] font-black text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-md ml-2">🍳 En cocina</span>'
            else:
                badge = '<span class="text-[10px] font-black text-amber-400 bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded-md ml-2">🟡 Por enviar</span>'

            del_btn = ""
            if editable and estado == "borrador":
                del_btn = f"""
                <button data-action="eliminarItem" data-args="{item['id']}"
                        class="w-8 h-8 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 flex items-center justify-center text-xs ml-2 active:scale-90 transition">
                  <i class="fa-solid fa-trash"></i>
                </button>
                """

            return f"""
            <div class="flex items-center gap-3 py-3 border-b border-white/5">
              <div class="w-8 h-8 rounded-xl bg-slate-800 text-white text-xs font-black flex items-center justify-center flex-shrink-0 font-mono">
                {cantidad}×
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-xs font-black text-white truncate flex items-center">
                  <span>{nombre}</span>
                  {badge}
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5">${precio:,.2f} c/u</div>
              </div>
              <div class="text-xs font-black text-white">${subtotal:,.2f}</div>
              {del_btn}
            </div>
            """

        subtotal_indiv = sum(float(i.get("subtotal") or 0) for i in indiv)
        subtotal_centro = sum(float(i.get("subtotal") or 0) for i in centro)
        gran_total = subtotal_indiv + subtotal_centro

        indiv_html = "".join(_fila(i) for i in indiv) if indiv else """
        <div class="text-center py-6 text-slate-500 text-xs">
          <i class="fa-solid fa-utensils text-2xl mb-2 opacity-40"></i>
          <p>Aún no has agregado platillos a tu silla.</p>
        </div>
        """

        centro_html = "".join(_fila(i, es_al_centro=True, editable=False) for i in centro) if centro else """
        <div class="text-center py-4 text-slate-500 text-xs">
          <p>No hay pedidos al centro de la mesa.</p>
        </div>
        """

        enviar_btn = ""
        if detalle_ids_borrador:
            enviar_btn = f"""
            <div class="sticky bottom-4 mt-6">
              <button data-action="enviarCocina"
                      class="w-full rounded-2xl bg-gradient-to-r from-emerald-500 via-teal-600 to-emerald-500 hover:from-emerald-400 hover:to-teal-500 text-white font-black text-sm py-4 shadow-[0_10px_30px_rgba(16,185,129,0.4)] flex items-center justify-center gap-2 active:scale-95 transition">
                <i class="fa-solid fa-fire text-amber-300"></i>
                Enviar {len(detalle_ids_borrador)} platillo(s) a Cocina
              </button>
            </div>
            """

        html = f"""
        <div class="min-h-screen max-w-md mx-auto bg-[#090d16] text-slate-100 font-sans pb-28">
          {self._header_html()}

          <section class="px-4 pt-4">
            <button data-action="volverInicio"
                    class="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white py-1.5 px-3 rounded-xl bg-slate-900/60 border border-white/5 mb-3 transition">
              <i class="fa-solid fa-arrow-left text-[11px]"></i> Volver al inicio
            </button>

            <div class="flex items-center justify-between mb-4">
              <h2 class="text-xl font-black text-white flex items-center gap-2">
                <span>🧾</span> Mi Comanda &amp; Cuenta
              </h2>
              <span class="text-xs font-black text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-1 rounded-full">
                Total: ${gran_total:,.2f}
              </span>
            </div>

            <!-- COMANDA PERSONAL -->
            <div class="rounded-3xl border border-white/10 bg-slate-900/80 p-4 shadow-lg mb-4">
              <div class="text-xs font-black text-emerald-400 uppercase tracking-wider flex items-center justify-between">
                <span>🍳 Mi Silla (Silla {silla})</span>
                <span class="text-white">${subtotal_indiv:,.2f}</span>
              </div>
              <div class="mt-2">{indiv_html}</div>
            </div>

            <!-- COMANDA AL CENTRO -->
            <div class="rounded-3xl border border-white/10 bg-slate-900/80 p-4 shadow-lg mb-4">
              <div class="text-xs font-black text-amber-400 uppercase tracking-wider flex items-center justify-between">
                <span>🍲 Al Centro de la Mesa</span>
                <span class="text-white">${subtotal_centro:,.2f}</span>
              </div>
              <div class="mt-2">{centro_html}</div>
            </div>

            {enviar_btn}
          </section>
        </div>
        """
        self._reemplazar_contenido(html)

    def _eliminar_item(self, detalle_id):
        try:
            anvil.server.call("eliminar_item_comanda", int(detalle_id))
        except Exception as e:
            print(f"[Menu] Error eliminar_item_comanda: {e}")
        self._render_mi_comanda()

    def _enviar_a_cocina(self):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        silla = info.get("silla_num")

        try:
            data = anvil.server.call("get_items_por_silla", mesa, silla) or {}
        except Exception:
            data = {}

        indiv = data.get("items_individuales", []) or []
        centro = data.get("items_al_centro", []) or []
        ids = [i["id"] for i in indiv + centro if str(i.get("estado")) == "borrador"]

        if not ids:
            anvil.alert("No hay platillos pendientes de enviar.")
            return

        try:
            resp = anvil.server.call("enviar_items_a_cocina", ids)
        except Exception as e:
            print(f"[Menu] Error enviar_items_a_cocina: {e}")
            anvil.alert("No pudimos enviar a cocina. Intenta de nuevo.")
            return

        if isinstance(resp, dict) and resp.get("ok"):
            self._toast(f"¡Enviado! {resp.get('enviados', 0)} platillo(s) están en preparación.", "ok")

        self._render_mi_comanda()

    # ─────────────────── selector "Pedir para Otra Silla" ───────────────
    def _render_selector_silla_destino(self):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        mi_silla = info.get("silla_num")

        try:
            cuentas = anvil.server.call("get_cuentas_terraza") or {}
        except Exception:
            cuentas = {}

        sillas_disponibles = []
        for key, c in cuentas.items():
            if not isinstance(c, dict):
                continue
            if c.get("mesaId") != mesa:
                continue
            if c.get("estado") != "ocupada":
                continue
            snum = c.get("sillaId")
            if snum == mi_silla or not snum:
                continue
            sillas_disponibles.append(c)

        if not sillas_disponibles:
            self._reemplazar_contenido(f"""
              <div class="min-h-screen max-w-md mx-auto bg-[#090d16] text-slate-100 font-sans pb-28">
                {self._header_html()}
                <section class="px-6 pt-10 text-center">
                  <button data-action="volverInicio"
                          class="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white py-1.5 px-3 rounded-xl bg-slate-900/60 border border-white/5 mb-6 transition">
                    <i class="fa-solid fa-arrow-left text-[11px]"></i> Volver al inicio
                  </button>
                  <div class="w-20 h-20 mx-auto rounded-3xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-3xl mb-4 shadow-xl">
                    👨‍👧
                  </div>
                  <h2 class="text-xl font-black text-white">Pedir para otra silla</h2>
                  <p class="text-xs text-slate-400 mt-2 leading-relaxed max-w-xs mx-auto">
                    No hay otras sillas ocupadas en tu mesa actualmente. Pide a tus acompañantes escanear su QR para poder ayudarles.
                  </p>
                </section>
              </div>
            """)
            return

        cards_html = ""
        for s in sillas_disponibles:
            snum = s.get("sillaId")
            nombre = s.get("comensalNombre", f"Silla {snum}")
            cards_html += f"""
            <button data-action="tab" data-args="__setSilla{snum}"
                    class="w-full rounded-3xl border border-white/10 bg-slate-900/80 hover:border-purple-400/80 p-4 flex items-center gap-3.5 transition-all shadow-md active:scale-[0.98] group">
              <div class="w-12 h-12 rounded-2xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-300 font-black text-sm flex-shrink-0 group-hover:scale-105 transition">
                S{snum}
              </div>
              <div class="flex-1 text-left min-w-0">
                <div class="text-sm font-black text-white">Silla {snum}</div>
                <div class="text-xs text-slate-400 truncate">{nombre}</div>
              </div>
              <div class="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-purple-400 transition">
                <i class="fa-solid fa-chevron-right text-xs"></i>
              </div>
            </button>
            """

        html = f"""
        <div class="min-h-screen max-w-md mx-auto bg-[#090d16] text-slate-100 font-sans pb-28">
          {self._header_html()}
          <section class="px-4 pt-4">
            <button data-action="volverInicio"
                    class="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white py-1.5 px-3 rounded-xl bg-slate-900/60 border border-white/5 mb-3 transition">
              <i class="fa-solid fa-arrow-left text-[11px]"></i> Volver al inicio
            </button>
            <h2 class="text-xl font-black text-white flex items-center gap-2">
              <span>👨‍👧</span> Pedir para otra silla
            </h2>
            <p class="text-xs text-slate-400 mt-1">Elige a qué acompañante de tu mesa deseas agregarle platillos:</p>
            <div class="mt-4 flex flex-col gap-3">{cards_html}</div>
          </section>
        </div>
        """
        self._reemplazar_contenido(html)

    def _preprocesar_args_tab(self, args):
        if not args:
            return args
        v = str(args[0])
        if v.startswith("__setSilla"):
            try:
                self._silla_destino_num = int(v.replace("__setSilla", ""))
                self._destino_actual = "otra_silla"
                self._render_tab_ordenar("otra_silla")
            except ValueError:
                pass
            return None
        return args

    # ─────────────────── header reutilizable ─────────────────────────────
    def _header_html(self):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num", "?")
        silla = info.get("silla_num", "?")
        return f"""
        <header class="sticky top-0 z-40 backdrop-blur-xl bg-[#090d16]/90 border-b border-white/10 px-4 py-3 max-w-md mx-auto flex items-center justify-between gap-2 shadow-lg">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center text-xs font-black text-white shadow-md">
              V&amp;S
            </div>
            <div>
              <div class="text-xs font-black text-white leading-tight">Mesa {mesa} · Silla {silla}</div>
              <div class="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">La Terraza</div>
            </div>
          </div>
          
          <div class="flex items-center gap-2">
            <button data-action="llamarMesero"
                    class="px-3 py-1.5 text-[11px] font-black rounded-xl bg-amber-500/15 border border-amber-500/40 text-amber-300 flex items-center gap-1.5 active:scale-95 transition shadow-sm">
              <i class="fa-solid fa-bell text-xs"></i> Mesero
            </button>
            <button data-action="verComanda"
                    class="px-3 py-1.5 text-[11px] font-black rounded-xl bg-sky-500/15 border border-sky-500/40 text-sky-300 flex items-center gap-1.5 active:scale-95 transition shadow-sm">
              <i class="fa-solid fa-receipt text-xs"></i> Cuenta
            </button>
          </div>
        </header>
        """

    def _llamar_mesero(self):
        self._enviar_llamada("llamar_mesero", "Aviso enviado. Tu mesero llegará enseguida.")

    def _solicitar_cuenta(self):
        self._enviar_llamada("solicitar_cuenta", "Solicitud enviada. Te traeremos la cuenta a tu mesa.")

    def _enviar_llamada(self, tipo, mensaje_ok):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        silla = info.get("silla_num")
        if not mesa or not silla:
            self._toast("Primero escanea el QR de tu silla.", "warn")
            return
        try:
            resp = anvil.server.call("crear_llamada_mesero", mesa, silla, tipo)
        except Exception as e:
            print(f"[Menu] Error en crear_llamada_mesero: {e}")
            self._toast("No pudimos avisar al mesero. Intenta otra vez.", "err")
            return
        if not (isinstance(resp, dict) and resp.get("ok")):
            self._toast("No pudimos avisar al mesero.", "err")
            return

        llamada_id = resp.get("llamada_id")
        self._toast(mensaje_ok, "ok")
        if llamada_id:
            self._mostrar_banner_llamada(llamada_id, tipo)

    def _mostrar_banner_llamada(self, llamada_id, tipo):
        doc = anvil.js.window.document
        prev = doc.getElementById("menuBannerLlamada")
        if prev is not None:
            prev.remove()

        etiqueta = {
            "llamar_mesero":    "Mesero notificado · En camino a tu mesa…",
            "solicitar_cuenta": "Cuenta solicitada · En preparación…",
        }.get(tipo, "Aviso enviado…")

        banner = doc.createElement("div")
        banner.id = "menuBannerLlamada"
        banner.style.cssText = (
            "position: fixed; left: 0; right: 0; bottom: 0; z-index: 9999; "
            "background: linear-gradient(90deg, #d97706, #f59e0b, #d97706); "
            "color: #fff; font-weight: 900; font-size: 13px; font-family: 'Plus Jakarta Sans', system-ui, sans-serif; "
            "padding: 14px 20px; text-align: center; "
            "box-shadow: 0 -8px 25px rgba(0,0,0,0.6); "
            "display: flex; align-items: center; justify-content: center; gap: 10px;"
        )
        banner.innerHTML = f"""
          <i class="fa-solid fa-bell animate-bounce text-sm"></i>
          <span>{etiqueta}</span>
        """
        doc.body.appendChild(banner)
        self._iniciar_polling_llamada(int(llamada_id))

    def _iniciar_polling_llamada(self, llamada_id):
        try:
            t = anvil.Timer(interval=3)
        except Exception:
            return
        self._timer_llamada = t
        self._llamada_id_pollend = int(llamada_id)
        t.set_event_handler("tick", lambda **e: self._chequear_llamada_atendida())
        self.add_component(t)

    def _chequear_llamada_atendida(self):
        lid = getattr(self, "_llamada_id_pollend", None)
        if not lid:
            return
        try:
            resp = anvil.server.call("get_llamada_estado", lid) or {}
        except Exception:
            return
        if resp.get("atendida_at"):
            self._quitar_banner_llamada(resp.get("atendida_por"))

    def _quitar_banner_llamada(self, atendida_por=None):
        nombre = atendida_por or "El mesero"
        self._toast(f"✓ {nombre} atendió tu solicitud.", "ok")
        doc = anvil.js.window.document
        b = doc.getElementById("menuBannerLlamada")
        if b is not None:
            b.remove()
        t = getattr(self, "_timer_llamada", None)
        if t is not None:
            try:
                t.interval = 0
            except Exception:
                pass
        self._timer_llamada = None
        self._llamada_id_pollend = None
