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
        # Estado del catálogo (Bloque C.3)
        self._menu_productos = []      # array de productos desde vw_menu_cliente
        self._menu_categorias = []     # array de categorías únicas ordenadas
        self._destino_actual = "mi_silla"  # 'mi_silla' | 'al_centro' | 'otra_silla'
        self._silla_destino_num = None      # cuando 'otra_silla'

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
        # ─── C.3: catálogo y comanda ──────────────────────────────
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
            # Regresa a la lista de productos de la última categoría abierta.
            if getattr(self, "_ultima_categoria_id", None):
                self._render_productos_de_categoria(self._ultima_categoria_id)
            else:
                self._render_tab_ordenar(self._destino_actual)
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

    # ─────────────────────── enrutamiento de tabs (C.3) ──────────────────
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
        """Carga get_menu_cliente al primer uso y agrupa por categoría."""
        if self._menu_productos:
            return True
        try:
            productos = anvil.server.call("get_menu_cliente") or []
        except Exception as e:
            print(f"[Menu] Error cargando get_menu_cliente: {e}")
            productos = []
        self._menu_productos = productos
        # Categorías únicas ordenadas por categoria_orden.
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
        # Header contextual según destino
        cabeceras = {
            "mi_silla":  ("🍳 Ordenar a Mi Silla",
                          "Los platillos que elijas se cargan a TU cuenta."),
            "al_centro": ("🍲 Pedir al Centro",
                          "Se comparten con toda la mesa. La cuenta al centro es aparte."),
            "otra_silla": (
                f"👨‍👧 Pedir para Silla {self._silla_destino_num or '?'}",
                f"Los platillos se cargan a la cuenta de la Silla {self._silla_destino_num}, "
                "no a la tuya.",
            ),
        }
        titulo, sub = cabeceras.get(destino, ("Menú", ""))
        # Filtrar categorías: si es 'al_centro' priorizamos las flagged es_al_centro,
        # pero también dejamos ver bebidas y demás (el cliente decide).
        cats_html = ""
        # Excluir categorías Al Centro cuando el destino NO es al_centro (evita duplicar).
        for c in self._menu_categorias:
            es_al_centro = "al centro" in (c.get("nombre", "").lower())
            if destino != "al_centro" and es_al_centro:
                continue
            cats_html += (
                f'<button data-action="abrirCategoria" data-args="{c["id"]}"'
                f' class="rounded-2xl border border-white/5 bg-slate-900/60'
                f' hover:border-emerald-500/40 p-4 flex flex-col items-center'
                f' justify-center gap-2 min-h-[110px] transition text-center">'
                f'  <span style="font-size:36px;line-height:1;">{c["icono"]}</span>'
                f'  <span class="text-[13px] font-bold text-slate-100">{c["nombre"]}</span>'
                f'</button>'
            )
        html = f"""
        {self._header_html()}
        <section class="px-4 mt-4 max-w-md mx-auto">
          <button data-action="volverInicio"
            class="text-xs text-slate-400 flex items-center gap-2 mb-2">
            <i class="fa-solid fa-arrow-left"></i> Inicio
          </button>
          <h2 class="text-lg font-black text-white">{titulo}</h2>
          <p class="text-xs text-slate-400 mt-1">{sub}</p>
        </section>
        <section class="px-4 mt-4 max-w-md mx-auto grid grid-cols-2 gap-3 pb-24">
          {cats_html or '<div class="col-span-2 text-center text-slate-500 py-10">No hay categorías disponibles todavía.</div>'}
        </section>
        """
        self._reemplazar_contenido(html)

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
            items_html += (
                f'<button data-action="abrirProducto" data-args="{p["id"]}"'
                f' class="w-full text-left rounded-2xl bg-slate-900/60 border'
                f' border-white/5 hover:border-emerald-500/40 p-4 flex items-center'
                f' gap-3 transition">'
                f'  <span style="font-size:28px;line-height:1;">{p.get("icono","🍽️")}</span>'
                f'  <div class="flex-1 min-w-0">'
                f'    <div class="text-sm font-black text-white truncate">{p["nombre"]}</div>'
                f'    <div class="text-[11px] text-slate-400 mt-0.5">'
                f'      <span class="text-emerald-400 font-bold">${precio:,.2f}</span>'
                f'      <span class="mx-1 text-slate-600">·</span>'
                f'      <span>{tiempo}</span>'
                f'    </div>'
                f'  </div>'
                f'  <i class="fa-solid fa-plus text-emerald-400 text-lg"></i>'
                f'</button>'
            )
        cat_nombre = (cat or {}).get("nombre", "Menú")
        cat_icono = (cat or {}).get("icono", "🍽️")
        html = f"""
        {self._header_html()}
        <section class="px-4 mt-4 max-w-md mx-auto">
          <button data-action="volverCategorias"
            class="text-xs text-slate-400 flex items-center gap-2 mb-2">
            <i class="fa-solid fa-arrow-left"></i> Volver a categorías
          </button>
          <h2 class="text-lg font-black text-white flex items-center gap-2">
            <span style="font-size:22px;">{cat_icono}</span> {cat_nombre}
          </h2>
        </section>
        <section class="px-4 mt-4 max-w-md mx-auto flex flex-col gap-3 pb-24">
          {items_html}
        </section>
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
            "mi_silla":   "Se carga a TU silla",
            "al_centro":  "Al centro (compartido)",
            "otra_silla": f"Se carga a la Silla {self._silla_destino_num}",
        }.get(self._destino_actual, "")
        html = f"""
        <div id="menuProductoOverlay"
             class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end
                    justify-center p-0 sm:items-center">
          <div class="w-full max-w-md bg-slate-900 border border-white/10
                      rounded-t-3xl sm:rounded-3xl p-5 shadow-2xl">
            <div class="flex items-start justify-between gap-3 mb-3">
              <div>
                <div class="text-[11px] font-bold text-emerald-400 uppercase
                            tracking-wider">{etiqueta_destino}</div>
                <h3 class="text-lg font-black text-white mt-0.5">
                  <span style="font-size:22px;">{p.get('icono','🍽️')}</span>
                  {p['nombre']}
                </h3>
              </div>
              <button data-action="cerrarProducto"
                class="text-slate-400 hover:text-white text-2xl leading-none">✕</button>
            </div>
            {'<p class="text-sm text-slate-300 leading-relaxed mb-3">' + desc + '</p>' if desc else ''}

            <div class="flex items-center justify-between rounded-2xl
                        border border-white/10 bg-slate-950/50 p-3 mt-3">
              <span class="text-sm font-bold text-slate-300">Cantidad</span>
              <div class="flex items-center gap-3">
                <button data-action="cambiarCantidad" data-args="-1"
                  class="w-9 h-9 rounded-xl bg-slate-800 border border-white/10
                         text-white text-xl font-black">−</button>
                <span class="text-lg font-black text-white min-w-[24px] text-center">{cantidad}</span>
                <button data-action="cambiarCantidad" data-args="1"
                  class="w-9 h-9 rounded-xl bg-slate-800 border border-white/10
                         text-white text-xl font-black">+</button>
              </div>
            </div>

            <button data-action="agregarItem" data-args="{p['id']}"
              class="w-full mt-4 rounded-2xl bg-gradient-to-r from-emerald-500
                     to-teal-600 hover:from-emerald-400 hover:to-teal-500
                     text-white font-black text-base py-4 shadow-lg
                     flex items-center justify-center gap-2">
              <i class="fa-solid fa-plus"></i>
              Agregar · ${subtotal:,.2f}
            </button>
          </div>
        </div>
        """
        # Insertar/actualizar el modal como último hijo del root del form.
        # Al ser hijo de self._root, la delegación captura los clics ✓.
        doc = anvil.js.window.document
        existing = doc.getElementById("menuProductoOverlay")
        if existing is not None:
            existing.remove()
        wrapper = doc.createElement("div")
        wrapper.innerHTML = html
        # Buscar el primer hijo real del wrapper y anexarlo al root.
        while wrapper.firstChild:
            self._root.appendChild(wrapper.firstChild)

    def _cambiar_cantidad_modal(self, delta):
        c = getattr(self, "_cantidad_actual", 1) + int(delta)
        self._cantidad_actual = max(1, min(20, c))
        self._pintar_modal_producto()

    def _enviar_agregar_item(self, producto_id):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        silla = info.get("silla_num")
        if not mesa or not silla:
            anvil.alert("No detecté tu silla activa. Escanea el QR de nuevo.")
            return
        para_silla_num = None
        if self._destino_actual == "al_centro":
            para_silla_num = 0
        elif self._destino_actual == "otra_silla":
            para_silla_num = self._silla_destino_num
        try:
            resp = anvil.server.call(
                "agregar_item_a_comanda",
                mesa, silla, int(producto_id),
                cantidad=int(getattr(self, "_cantidad_actual", 1)),
                para_silla_num=para_silla_num,
            )
        except Exception as e:
            print(f"[Menu] Error agregar_item_a_comanda: {e}")
            anvil.alert("No pude agregar el platillo. Intenta de nuevo.")
            return
        if not isinstance(resp, dict) or resp.get("error"):
            anvil.alert("No pude agregar el platillo: " + str((resp or {}).get("error", "")))
            return
        # Cierra el modal y muestra un toast en la vista de productos.
        self._cerrar_modal_producto()
        anvil.alert("Agregado a tu comanda.", title="✓")

    def _cerrar_modal_producto(self):
        doc = anvil.js.window.document
        modal = doc.getElementById("menuProductoOverlay")
        if modal is not None:
            modal.remove()

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
        detalle_ids_borrador = [i["id"] for i in indiv + centro
                                if str(i.get("estado")) == "borrador"]

        def _fila(item, es_al_centro=False, editable=True):
            precio = float(item.get("precio_unitario_snapshot") or 0)
            cantidad = int(item.get("cantidad") or 1)
            subtotal = float(item.get("subtotal") or (precio * cantidad))
            nombre = item.get("producto_nombre_snapshot", "?")
            estado = item.get("estado", "borrador")
            badge = ""
            if estado != "borrador":
                badge = ('<span class="text-[10px] font-bold text-emerald-400 ml-2">'
                         '· en cocina</span>')
            del_btn = ""
            if editable and estado == "borrador":
                del_btn = (f'<button data-action="eliminarItem" data-args="{item["id"]}"'
                           f' class="text-slate-500 hover:text-red-400 text-sm ml-2">'
                           f'<i class="fa-solid fa-trash"></i></button>')
            return (
                f'<div class="flex items-center gap-3 py-2 border-b border-white/5">'
                f'  <div class="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-300'
                f'    text-xs font-black flex items-center justify-center">{cantidad}x</div>'
                f'  <div class="flex-1 min-w-0">'
                f'    <div class="text-sm text-white font-bold truncate">{nombre}{badge}</div>'
                f'    <div class="text-[11px] text-slate-400">${precio:,.2f} c/u</div>'
                f'  </div>'
                f'  <div class="text-sm font-black text-white">${subtotal:,.2f}</div>'
                f'  {del_btn}'
                f'</div>'
            )

        subtotal_indiv = sum(float(i.get("subtotal") or 0) for i in indiv)
        subtotal_centro = sum(float(i.get("subtotal") or 0) for i in centro)

        indiv_html = "".join(_fila(i) for i in indiv) if indiv else (
            '<div class="text-center py-6 text-slate-500 text-xs">'
            'Aún no has agregado platillos a tu silla.</div>'
        )
        centro_html = "".join(_fila(i, es_al_centro=True, editable=False)
                              for i in centro) if centro else (
            '<div class="text-center py-4 text-slate-500 text-xs">'
            'No hay pedidos al centro todavía.</div>'
        )

        enviar_btn = ""
        if detalle_ids_borrador:
            enviar_btn = (
                f'<button data-action="enviarCocina"'
                f' class="w-full mt-4 rounded-2xl bg-gradient-to-r from-emerald-500'
                f' to-teal-600 text-white font-black py-4 shadow-lg flex items-center'
                f' justify-center gap-2">'
                f'  <i class="fa-solid fa-fire"></i>'
                f'  Enviar {len(detalle_ids_borrador)} platillo(s) a cocina'
                f'</button>'
            )

        html = f"""
        {self._header_html()}
        <section class="px-4 mt-4 max-w-md mx-auto pb-32">
          <button data-action="volverInicio"
            class="text-xs text-slate-400 flex items-center gap-2 mb-3">
            <i class="fa-solid fa-arrow-left"></i> Inicio
          </button>
          <h2 class="text-lg font-black text-white">🧾 Mi Comanda</h2>

          <div class="mt-4 rounded-2xl border border-white/10 bg-slate-900/60 p-4">
            <div class="text-xs font-black text-emerald-400 uppercase tracking-wider">
              Mi silla (Silla {silla})
            </div>
            <div class="mt-2">{indiv_html}</div>
            {'<div class="pt-2 mt-2 border-t border-white/10 flex justify-between text-sm">'
             '<span class="text-slate-400">Subtotal mi silla</span>'
             f'<span class="text-white font-black">${subtotal_indiv:,.2f}</span></div>'
              if indiv else ''}
          </div>

          <div class="mt-4 rounded-2xl border border-white/10 bg-slate-900/60 p-4">
            <div class="text-xs font-black text-amber-400 uppercase tracking-wider">
              Al centro de la mesa (compartido)
            </div>
            <div class="mt-2">{centro_html}</div>
            {'<div class="pt-2 mt-2 border-t border-white/10 flex justify-between text-sm">'
             '<span class="text-slate-400">Subtotal al centro</span>'
             f'<span class="text-white font-black">${subtotal_centro:,.2f}</span></div>'
              if centro else ''}
          </div>

          {enviar_btn}
        </section>
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
            anvil.alert("No pude enviar a cocina. Intenta de nuevo.")
            return
        if isinstance(resp, dict) and resp.get("ok"):
            anvil.alert(f"¡Enviado! {resp.get('enviados', 0)} platillo(s) están en cocina.",
                        title="🍳 En cocina")
        self._render_mi_comanda()

    # ─────────────────── selector "Pedir para Otra Silla" (C.3.4) ────────
    def _render_selector_silla_destino(self):
        info = self._sesion_info or {}
        mesa = info.get("mesa_num")
        mi_silla = info.get("silla_num")
        try:
            cuentas = anvil.server.call("get_cuentas_terraza") or {}
        except Exception:
            cuentas = {}
        # Filtrar sillas de la misma mesa, ocupadas, distintas a mí.
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
              {self._header_html()}
              <section class="px-4 mt-6 max-w-md mx-auto text-center">
                <button data-action="volverInicio"
                  class="text-xs text-slate-400 flex items-center gap-2 mb-4 mx-auto">
                  <i class="fa-solid fa-arrow-left"></i> Inicio
                </button>
                <div class="w-16 h-16 mx-auto rounded-full bg-slate-800 flex
                            items-center justify-center text-2xl">👨‍👧</div>
                <h2 class="text-lg font-black text-white mt-3">Pedir para otra silla</h2>
                <p class="text-sm text-slate-400 mt-2">
                  Ninguna otra silla de tu mesa está ocupada aún. Pide al mesero
                  que las registre para poder ayudarles con su pedido.
                </p>
              </section>
            """)
            return
        cards_html = ""
        for s in sillas_disponibles:
            snum = s.get("sillaId")
            nombre = s.get("comensalNombre", f"Silla {snum}")
            cards_html += (
                f'<button data-action="tab" data-args="__setSilla{snum}"'
                f' class="w-full rounded-2xl border border-white/5 bg-slate-900/60'
                f' hover:border-purple-500/40 p-4 flex items-center gap-3 transition">'
                f'  <div class="w-11 h-11 rounded-xl bg-purple-500/15 border'
                f'    border-purple-500/30 flex items-center justify-center text-lg">'
                f'    S{snum}</div>'
                f'  <div class="flex-1 text-left">'
                f'    <div class="text-sm font-black text-white">Silla {snum}</div>'
                f'    <div class="text-[11px] text-slate-400">{nombre}</div>'
                f'  </div>'
                f'  <i class="fa-solid fa-arrow-right text-slate-500"></i>'
                f'</button>'
            )
        html = f"""
        {self._header_html()}
        <section class="px-4 mt-4 max-w-md mx-auto pb-24">
          <button data-action="volverInicio"
            class="text-xs text-slate-400 flex items-center gap-2 mb-2">
            <i class="fa-solid fa-arrow-left"></i> Inicio
          </button>
          <h2 class="text-lg font-black text-white">👨‍👧 Pedir para otra silla</h2>
          <p class="text-xs text-slate-400 mt-1">
            Ayuda a un niño, adulto mayor o compañero de mesa. Elige a quién le vas a ordenar:
          </p>
          <div class="mt-4 flex flex-col gap-3">{cards_html}</div>
        </section>
        """
        self._reemplazar_contenido(html)
        # Interceptar el tab para setear silla destino (dispatcher normal no
        # sabe interpretar el prefijo __setSilla).
        self._pendiente_set_silla = True

    # Override: interpretar el arg especial __setSillaN al elegir destino.
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
        <header class="sticky top-0 z-40 backdrop-blur bg-[#0f172ad9]
                       border-b border-white/10 px-4 py-3 max-w-md mx-auto
                       flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500
                        to-teal-700 flex items-center justify-center text-sm
                        font-black text-white shadow">V&amp;S</div>
            <div>
              <div class="text-[11px] font-black text-white">Mesa {mesa} · Silla {silla}</div>
              <div class="text-[10px] text-emerald-400 font-bold uppercase
                          tracking-wider">La Terraza</div>
            </div>
          </div>
          <div class="flex gap-1.5">
            <button data-action="verComanda"
              class="px-2.5 py-1.5 text-[11px] font-bold rounded-lg
                     bg-sky-500/20 border border-sky-500/50 text-sky-300
                     flex items-center gap-1.5">
              <i class="fa-solid fa-receipt text-xs"></i> Mi cuenta
            </button>
            <button data-action="llamarMesero"
              class="px-2.5 py-1.5 text-[11px] font-bold rounded-lg
                     bg-amber-500/20 border border-amber-500/50 text-amber-300
                     flex items-center gap-1.5">
              <i class="fa-solid fa-bell text-xs"></i> Mesero
            </button>
          </div>
        </header>
        """

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
