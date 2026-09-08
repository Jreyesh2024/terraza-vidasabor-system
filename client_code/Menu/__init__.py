"""
Menu — form del cliente (teléfono / QR) v2.
Arquitectura:
- Estructura HTML declarativa con clases .vs-* y estilos Vanilla CSS directos.
- Python monta UN listener delegado en root.
- Cero dependencia de frameworks CSS externos.
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
        self._sesion_info = None
        self._menu_productos = []
        self._menu_categorias = []
        self._destino_actual = "mi_silla"
        self._silla_destino_num = None
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
                return
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

        if not params and (s.upper().startswith("PV-") or s.upper().startswith("PV")):
            params["qr"] = s

        return self._dict_a_info(params) if params else None

    def _dict_a_info(self, params):
        qr = str(params.get("qr", "")).upper().strip()
        mesa_num = params.get("mesa")
        silla_num = params.get("silla")

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
            self._render_error("Hubo un problema al registrar tu llegada. Solicita ayuda a tu mesero.")
            return

        try:
            anvil.js.window.localStorage.setItem("vs_mi_qr_actual", info["qr"])
        except Exception:
            pass

        self._sesion_info = {**info, **resp}
        self._render_bienvenida()

    def _render_silla_ajena(self, qr):
        html = f"""
        <div class="vs-mobile-wrap" style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:40px 24px;">
          <div style="width:80px;height:80px;border-radius:24px;background:rgba(245,158,11,0.15);border:2px solid rgba(245,158,11,0.5);display:flex;align-items:center;justify-content:center;font-size:36px;margin-bottom:20px;box-shadow:0 10px 30px rgba(245,158,11,0.2);">
            🔒
          </div>
          <span style="font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:1px;color:#fcd34d;background:rgba(245,158,11,0.2);padding:4px 12px;border-radius:99px;border:1px solid rgba(245,158,11,0.4);margin-bottom:12px;">
            Silla en Uso
          </span>
          <h2 style="font-size:24px;font-weight:900;color:#ffffff;margin:0 0 10px 0;">Portavasos Ocupado</h2>
          <p style="font-size:14px;color:#94a3b8;line-height:1.5;max-width:320px;margin:0 0 24px 0;">
            El portavasos <b style="color:#ffffff;font-family:monospace;">{qr}</b> ya está en uso por otro comensal.
          </p>
          <button data-action="reintentarCheckin" class="vs-cta-btn">
            🔄 Reintentar escaneo
          </button>
        </div>
        """
        self._reemplazar_contenido(html)

    def _render_esperando_qr(self):
        html = """
        <div class="vs-mobile-wrap" style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:40px 24px;">
          <div style="width:90px;height:90px;border-radius:26px;background:linear-gradient(135deg,#10b981 0%,#0f766e 100%);display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:900;color:#ffffff;box-shadow:0 12px 35px rgba(16,185,129,0.4);margin-bottom:24px;">
            V&amp;S
          </div>
          <h1 style="font-size:24px;font-weight:900;color:#ffffff;margin:0 0 4px 0;letter-spacing:-0.5px;">La Terraza de Vida &amp; Sabor</h1>
          <p style="font-size:12px;font-weight:800;color:#10b981;text-transform:uppercase;letter-spacing:2px;margin:0 0 32px 0;">Menú Digital Interactivo</p>
          
          <div style="background:rgba(15,23,42,0.85);border:1px solid rgba(255,255,255,0.1);border-radius:24px;padding:24px 20px;box-shadow:0 12px 30px rgba(0,0,0,0.4);backdrop-filter:blur(10px);width:100%;box-sizing:border-box;">
            <div style="font-size:40px;margin-bottom:12px;">📱</div>
            <h3 style="font-size:17px;font-weight:900;color:#ffffff;margin:0 0 8px 0;">Escanea tu Portavasos</h3>
            <p style="font-size:13px;color:#94a3b8;line-height:1.5;margin:0;">
              Apunta la cámara de tu celular al código QR ubicado en tu mesa o portavasos para comenzar a ordenar.
            </p>
          </div>
        </div>
        """
        self._reemplazar_contenido(html)

    def _render_error(self, mensaje):
        html = f"""
        <div class="vs-mobile-wrap" style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:40px 24px;">
          <div style="width:80px;height:80px;border-radius:24px;background:rgba(239,68,68,0.15);border:2px solid rgba(239,68,68,0.5);display:flex;align-items:center;justify-content:center;font-size:36px;margin-bottom:20px;box-shadow:0 10px 30px rgba(239,68,68,0.2);">
            ⚠️
          </div>
          <h2 style="font-size:22px;font-weight:900;color:#ffffff;margin:0 0 10px 0;">No pudimos conectar</h2>
          <p style="font-size:14px;color:#94a3b8;line-height:1.5;max-width:320px;margin:0 0 24px 0;">{mensaje}</p>
          <button data-action="reintentarCheckin" class="vs-cta-btn">
            🔄 Reintentar
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
        <div class="vs-mobile-wrap">
          {self._header_html()}

          <!-- HERO CARD DE BIENVENIDA -->
          <div class="vs-hero-card">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
              <span class="vs-badge-active">
                <span class="vs-pulse-dot"></span>
                Sesión Activa
              </span>
              <span style="font-family:monospace;font-size:11px;font-weight:800;color:#94a3b8;background:rgba(0,0,0,0.3);padding:3px 10px;border-radius:99px;border:1px solid rgba(255,255,255,0.05);">
                {qr}
              </span>
            </div>
            
            <h2 style="font-size:22px;font-weight:900;color:#ffffff;margin:0 0 6px 0;line-height:1.2;">
              ¡Hola! <span style="color:#34d399;">Mesa {mesa}</span> · Silla {silla}
            </h2>
            <p style="font-size:13px;color:#cbd5e1;line-height:1.45;margin:0;">
              {comensal}. Explora nuestro menú y ordena directamente a tu silla o comparte con tu mesa.
            </p>
          </div>

          <!-- 4 TARJETAS PRINCIPALES DE ACCIÓN -->
          <div style="display:flex;flex-direction:column;gap:4px;">
            <!-- 1. ORDENAR A MI SILLA -->
            <div data-action="tab" data-args="silla" class="vs-action-card vs-card-emerald">
              <div class="vs-icon-box" style="background:rgba(16,185,129,0.2);border:1px solid rgba(16,185,129,0.4);">
                🍳
              </div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:15px;font-weight:900;color:#ffffff;display:flex;align-items:center;gap:8px;">
                  Ordenar a Mi Silla
                  <span style="font-size:10px;font-weight:800;color:#6ee7b7;background:rgba(16,185,129,0.25);border:1px solid rgba(16,185,129,0.4);padding:2px 8px;border-radius:99px;">Personal</span>
                </div>
                <div style="font-size:11.5px;color:#94a3b8;margin-top:2px;line-height:1.35;">
                  Bebidas, desayunos y platillos a tu cuenta personal.
                </div>
              </div>
              <div style="color:#34d399;font-size:14px;font-weight:900;">➔</div>
            </div>

            <!-- 2. PEDIR AL CENTRO -->
            <div data-action="tab" data-args="centro" class="vs-action-card vs-card-amber">
              <div class="vs-icon-box" style="background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.4);">
                🍲
              </div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:15px;font-weight:900;color:#ffffff;display:flex;align-items:center;gap:8px;">
                  Pedir al Centro
                  <span style="font-size:10px;font-weight:800;color:#fcd34d;background:rgba(245,158,11,0.25);border:1px solid rgba(245,158,11,0.4);padding:2px 8px;border-radius:99px;">Compartido</span>
                </div>
                <div style="font-size:11.5px;color:#94a3b8;margin-top:2px;line-height:1.35;">
                  Entradas, botanas o jarras para todos en la mesa.
                </div>
              </div>
              <div style="color:#fbbf24;font-size:14px;font-weight:900;">➔</div>
            </div>

            <!-- 3. PEDIR PARA OTRA SILLA -->
            <div data-action="tab" data-args="para_otra" class="vs-action-card vs-card-purple">
              <div class="vs-icon-box" style="background:rgba(168,85,247,0.2);border:1px solid rgba(168,85,247,0.4);">
                👨‍👧
              </div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:15px;font-weight:900;color:#ffffff;display:flex;align-items:center;gap:8px;">
                  Pedir para Otra Silla
                  <span style="font-size:10px;font-weight:800;color:#d8b4fe;background:rgba(168,85,247,0.25);border:1px solid rgba(168,85,247,0.4);padding:2px 8px;border-radius:99px;">Ayuda</span>
                </div>
                <div style="font-size:11.5px;color:#94a3b8;margin-top:2px;line-height:1.35;">
                  Pide a nombre de niños o acompañantes de mesa.
                </div>
              </div>
              <div style="color:#c084fc;font-size:14px;font-weight:900;">➔</div>
            </div>

            <!-- 4. MI COMANDA Y CUENTA -->
            <div data-action="tab" data-args="comanda" class="vs-action-card vs-card-sky">
              <div class="vs-icon-box" style="background:rgba(14,165,233,0.2);border:1px solid rgba(14,165,233,0.4);">
                🧾
              </div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:15px;font-weight:900;color:#ffffff;display:flex;align-items:center;gap:8px;">
                  Mi Comanda &amp; Cuenta
                  <span style="font-size:10px;font-weight:800;color:#7dd3fc;background:rgba(14,165,233,0.25);border:1px solid rgba(14,165,233,0.4);padding:2px 8px;border-radius:99px;">En Vivo</span>
                </div>
                <div style="font-size:11.5px;color:#94a3b8;margin-top:2px;line-height:1.35;">
                  Revisa platillos pedidos, estado de cocina y subtotal.
                </div>
              </div>
              <div style="color:#38bdf8;font-size:14px;font-weight:900;">➔</div>
            </div>
          </div>

          <div style="text-align:center;font-size:11px;color:#64748b;margin-top:28px;">
            La Terraza de Vida &amp; Sabor · Experiencia Digital
          </div>
        </div>
        """
        self._reemplazar_contenido(html)

    def _reemplazar_contenido(self, html):
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
            "mi_silla":  ("🍳", "Ordenar a Mi Silla", "border-color:rgba(16,185,129,0.4);background:linear-gradient(135deg,rgba(16,185,129,0.2) 0%,rgba(15,23,42,0.9) 100%);", "Platillos individuales para tu comanda."),
            "al_centro": ("🍲", "Pedir al Centro", "border-color:rgba(245,158,11,0.4);background:linear-gradient(135deg,rgba(245,158,11,0.2) 0%,rgba(15,23,42,0.9) 100%);", "Platillos para compartir en la mesa."),
            "otra_silla": ("👨‍👧", f"Pedir para Silla {self._silla_destino_num or '?'}", "border-color:rgba(168,85,247,0.4);background:linear-gradient(135deg,rgba(168,85,247,0.2) 0%,rgba(15,23,42,0.9) 100%);", f"Se cargará a la Silla {self._silla_destino_num}."),
        }
        icono, titulo, card_style, sub = cabeceras.get(destino, ("🍽️", "Menú", "", ""))

        resumen_al_centro = ""
        if destino == "al_centro":
            resumen_al_centro = self._resumen_al_centro_html()

        cats_html = ""
        for c in self._menu_categorias:
            es_al_centro_cat = "al centro" in (c.get("nombre", "").lower())
            if destino != "al_centro" and es_al_centro_cat:
                continue
            
            cats_html += f"""
            <div data-action="abrirCategoria" data-args="{c['id']}" class="vs-cat-btn">
              <div style="width:54px;height:54px;border-radius:18px;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.08);display:flex;align-items:center;justify-content:center;font-size:30px;box-shadow:inset 0 2px 5px rgba(0,0,0,0.5);">
                {c['icono']}
              </div>
              <span style="font-size:13px;font-weight:900;color:#ffffff;line-height:1.2;margin-top:4px;">{c['nombre']}</span>
            </div>
            """

        html = f"""
        <div class="vs-mobile-wrap">
          {self._header_html()}
          
          <div style="padding:16px 16px 0 16px;">
            <button data-action="volverInicio" style="background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.1);color:#94a3b8;font-size:12px;font-weight:800;padding:6px 12px;border-radius:12px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;margin-bottom:12px;">
              ⬅ Volver al inicio
            </button>

            <div style="border-radius:24px;border:1px solid rgba(255,255,255,0.1);padding:16px;box-shadow:0 12px 30px rgba(0,0,0,0.4);{card_style}">
              <div style="display:flex;align-items:center;gap:14px;">
                <div style="width:48px;height:48px;border-radius:16px;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;">
                  {icono}
                </div>
                <div>
                  <div style="font-size:16px;font-weight:900;color:#ffffff;line-height:1.2;">{titulo}</div>
                  <div style="font-size:12px;color:#cbd5e1;margin-top:2px;">{sub}</div>
                </div>
              </div>
            </div>
          </div>

          {resumen_al_centro}

          <div style="padding:16px 16px 0 16px;">
            <div style="font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:1px;color:#94a3b8;margin-bottom:8px;">
              Selecciona una categoría
            </div>
            <div class="vs-cats-grid" style="padding:0;margin:0;">
              {cats_html or '<div style="grid-column:span 2;text-align:center;color:#64748b;padding:40px 0;">No hay categorías disponibles.</div>'}
            </div>
          </div>
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
            badge = '<span style="font-size:10px;font-weight:900;color:#34d399;background:rgba(16,185,129,0.2);padding:2px 6px;border-radius:6px;margin-left:6px;">en cocina</span>' if estado != "borrador" else ""
            nombre = it.get("producto_nombre_snapshot", "?")
            filas += f"""
            <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:12.5px;">
              <div style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                <span style="color:#fcd34d;font-weight:900;">{cant}×</span> 
                <span style="color:#ffffff;margin-left:4px;font-weight:600;">{nombre}</span>{badge}
              </div>
              <div style="color:#ffffff;font-weight:900;margin-left:8px;">${subt:,.2f}</div>
            </div>
            """

        return f"""
        <div style="padding:12px 16px 0 16px;">
          <div style="border-radius:22px;border:1px solid rgba(245,158,11,0.35);background:linear-gradient(135deg,rgba(245,158,11,0.15) 0%,rgba(15,23,42,0.9) 100%);padding:14px;box-shadow:0 8px 25px rgba(0,0,0,0.3);">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
              <div style="font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:1px;color:#fbbf24;">
                🍲 Ya pedido al centro
              </div>
              <div style="font-size:13px;font-weight:900;color:#fcd34d;">${total:,.2f}</div>
            </div>
            {filas}
            <div style="margin-top:6px;font-size:10px;color:#94a3b8;text-align:center;">
              Visible para todos los comensales en la mesa.
            </div>
          </div>
        </div>
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
            <div data-action="abrirProducto" data-args="{p['id']}" class="vs-product-card">
              <div style="width:52px;height:52px;border-radius:16px;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.08);display:flex;align-items:center;justify-content:center;font-size:28px;flex-shrink:0;box-shadow:inset 0 2px 4px rgba(0,0,0,0.4);">
                {p.get('icono','🍽️')}
              </div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:14.5px;font-weight:900;color:#ffffff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{p['nombre']}</div>
                {'<div style="font-size:11.5px;color:#94a3b8;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + desc + '</div>' if desc else ''}
                <div style="display:flex;align-items:center;gap:8px;margin-top:6px;">
                  <span style="font-size:12.5px;font-weight:900;color:#34d399;background:rgba(16,185,129,0.18);padding:3px 8px;border-radius:8px;border:1px solid rgba(16,185,129,0.35);">
                    ${precio:,.2f}
                  </span>
                  {('<span style="font-size:10.5px;color:#94a3b8;">⏱ ' + tiempo + '</span>') if tiempo else ''}
                </div>
              </div>
              <div style="width:36px;height:36px;border-radius:12px;background:rgba(16,185,129,0.2);border:1px solid rgba(16,185,129,0.4);color:#34d399;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;flex-shrink:0;">
                +
              </div>
            </div>
            """

        cat_nombre = (cat or {}).get("nombre", "Menú")
        cat_icono = (cat or {}).get("icono", "🍽️")

        html = f"""
        <div class="vs-mobile-wrap">
          {self._header_html()}

          <div style="padding:16px 16px 8px 16px;">
            <button data-action="volverCategorias" style="background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.1);color:#94a3b8;font-size:12px;font-weight:800;padding:6px 12px;border-radius:12px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;margin-bottom:10px;">
              ⬅ Volver a categorías
            </button>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
              <span style="font-size:26px;">{cat_icono}</span>
              <h2 style="font-size:20px;font-weight:900;color:#ffffff;margin:0;">{cat_nombre}</h2>
            </div>
            <p style="font-size:12px;color:#94a3b8;margin:0;">Toca un platillo para ver detalles y agregarlo a tu orden.</p>
          </div>

          <div style="display:flex;flex-direction:column;gap:2px;margin-top:8px;">
            {items_html}
          </div>
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
        <div id="menuProductoOverlay" class="vs-modal-overlay">
          <div class="vs-modal-sheet">
            <div style="width:48px;height:5px;background:#334155;border-radius:99px;margin:0 auto 16px auto;"></div>

            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
              <div style="flex:1;">
                <span style="font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:1px;color:#34d399;background:rgba(16,185,129,0.18);padding:3px 8px;border-radius:8px;border:1px solid rgba(16,185,129,0.35);display:inline-block;margin-bottom:6px;">
                  {etiqueta_destino}
                </span>
                <h3 style="font-size:20px;font-weight:900;color:#ffffff;margin:0;line-height:1.2;display:flex;align-items:center;gap:8px;">
                  <span>{p.get('icono','🍽️')}</span>
                  <span>{p['nombre']}</span>
                </h3>
              </div>
              <button data-action="cerrarProducto" style="width:36px;height:36px;border-radius:12px;background:rgba(255,255,255,0.08);border:none;color:#94a3b8;font-size:18px;font-weight:900;cursor:pointer;display:flex;align-items:center;justify-content:center;">
                ✕
              </button>
            </div>

            {'<p style="font-size:13px;color:#cbd5e1;line-height:1.5;background:rgba(0,0,0,0.3);padding:12px;border-radius:16px;border:1px solid rgba(255,255,255,0.05);margin:12px 0;">' + desc + '</p>' if desc else ''}

            <!-- SELECTOR DE CANTIDAD -->
            <div style="display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.1);padding:12px 16px;border-radius:18px;margin-top:16px;">
              <span style="font-size:13px;font-weight:900;color:#e2e8f0;">Cantidad</span>
              <div style="display:flex;align-items:center;gap:12px;">
                <button data-action="cambiarCantidad" data-args="-1" style="width:40px;height:40px;border-radius:12px;background:#1e293b;border:1px solid rgba(255,255,255,0.1);color:#ffffff;font-size:20px;font-weight:900;cursor:pointer;display:flex;align-items:center;justify-content:center;">
                  −
                </button>
                <span style="font-size:18px;font-weight:900;color:#ffffff;font-family:monospace;min-width:28px;text-align:center;">
                  {cantidad}
                </span>
                <button data-action="cambiarCantidad" data-args="1" style="width:40px;height:40px;border-radius:12px;background:#1e293b;border:1px solid rgba(255,255,255,0.1);color:#ffffff;font-size:20px;font-weight:900;cursor:pointer;display:flex;align-items:center;justify-content:center;">
                  +
                </button>
              </div>
            </div>

            <!-- BOTON AGREGAR CTA -->
            <button data-action="agregarItem" data-args="{p['id']}" class="vs-cta-btn">
              ➕ Agregar a la Orden · ${subtotal:,.2f}
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
            f"z-index: 100000; padding: 12px 24px; "
            f"background: {bg}; color: {color}; "
            f"border-radius: 9999px; font-weight: 800; font-size: 13.5px; font-family: 'Plus Jakarta Sans', system-ui, sans-serif; "
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
                badge = '<span style="font-size:10px;font-weight:900;color:#34d399;background:rgba(16,185,129,0.18);padding:2px 8px;border-radius:6px;border:1px solid rgba(16,185,129,0.35);margin-left:6px;">🍳 En cocina</span>'
            else:
                badge = '<span style="font-size:10px;font-weight:900;color:#fbbf24;background:rgba(245,158,11,0.18);padding:2px 8px;border-radius:6px;border:1px solid rgba(245,158,11,0.35);margin-left:6px;">🟡 Por enviar</span>'

            del_btn = ""
            if editable and estado == "borrador":
                del_btn = f"""
                <button data-action="eliminarItem" data-args="{item['id']}"
                        style="width:32px;height:32px;border-radius:10px;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#f87171;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;margin-left:8px;">
                  🗑️
                </button>
                """

            return f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
              <div style="width:32px;height:32px;border-radius:10px;background:#1e293b;color:#ffffff;font-size:13px;font-weight:900;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-family:monospace;">
                {cantidad}×
              </div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:13px;font-weight:900;color:#ffffff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:flex;align-items:center;">
                  <span>{nombre}</span>
                  {badge}
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-top:2px;">${precio:,.2f} c/u</div>
              </div>
              <div style="font-size:13px;font-weight:900;color:#ffffff;">${subtotal:,.2f}</div>
              {del_btn}
            </div>
            """

        subtotal_indiv = sum(float(i.get("subtotal") or 0) for i in indiv)
        subtotal_centro = sum(float(i.get("subtotal") or 0) for i in centro)
        gran_total = subtotal_indiv + subtotal_centro

        indiv_html = "".join(_fila(i) for i in indiv) if indiv else """
        <div style="text-align:center;padding:24px 0;color:#64748b;font-size:12px;">
          <div style="font-size:28px;margin-bottom:6px;opacity:0.4;">🍽️</div>
          Aún no has agregado platillos a tu silla.
        </div>
        """

        centro_html = "".join(_fila(i, es_al_centro=True, editable=False) for i in centro) if centro else """
        <div style="text-align:center;padding:16px 0;color:#64748b;font-size:12px;">
          No hay pedidos al centro de la mesa.
        </div>
        """

        enviar_btn = ""
        if detalle_ids_borrador:
            enviar_btn = f"""
            <button data-action="enviarCocina" class="vs-cta-btn" style="box-shadow:0 10px 30px rgba(16,185,129,0.4);">
              🔥 Enviar {len(detalle_ids_borrador)} platillo(s) a Cocina
            </button>
            """

        html = f"""
        <div class="vs-mobile-wrap">
          {self._header_html()}

          <div style="padding:16px 16px 0 16px;">
            <button data-action="volverInicio" style="background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.1);color:#94a3b8;font-size:12px;font-weight:800;padding:6px 12px;border-radius:12px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;margin-bottom:12px;">
              ⬅ Volver al inicio
            </button>

            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
              <h2 style="font-size:20px;font-weight:900;color:#ffffff;margin:0;display:flex;align-items:center;gap:8px;">
                <span>🧾</span> Mi Comanda &amp; Cuenta
              </h2>
              <span style="font-size:13px;font-weight:900;color:#34d399;background:rgba(16,185,129,0.18);border:1px solid rgba(16,185,129,0.35);padding:4px 12px;border-radius:99px;">
                Total: ${gran_total:,.2f}
              </span>
            </div>

            <!-- COMANDA PERSONAL -->
            <div style="background:rgba(15,23,42,0.85);border:1px solid rgba(255,255,255,0.1);border-radius:22px;padding:16px;box-shadow:0 8px 24px rgba(0,0,0,0.3);margin-bottom:14px;">
              <div style="font-size:12px;font-weight:900;color:#34d399;text-transform:uppercase;letter-spacing:1px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:8px;">
                <span>🍳 Mi Silla (Silla {silla})</span>
                <span style="color:#ffffff;">${subtotal_indiv:,.2f}</span>
              </div>
              <div style="margin-top:4px;">{indiv_html}</div>
            </div>

            <!-- COMANDA AL CENTRO -->
            <div style="background:rgba(15,23,42,0.85);border:1px solid rgba(255,255,255,0.1);border-radius:22px;padding:16px;box-shadow:0 8px 24px rgba(0,0,0,0.3);margin-bottom:14px;">
              <div style="font-size:12px;font-weight:900;color:#fbbf24;text-transform:uppercase;letter-spacing:1px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:8px;">
                <span>🍲 Al Centro de la Mesa</span>
                <span style="color:#ffffff;">${subtotal_centro:,.2f}</span>
              </div>
              <div style="margin-top:4px;">{centro_html}</div>
            </div>

            {enviar_btn}
          </div>
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
              <div class="vs-mobile-wrap">
                {self._header_html()}
                <div style="padding:40px 24px;text-align:center;">
                  <button data-action="volverInicio" style="background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.1);color:#94a3b8;font-size:12px;font-weight:800;padding:6px 12px;border-radius:12px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;margin-bottom:24px;">
                    ⬅ Volver al inicio
                  </button>
                  <div style="width:72px;height:72px;border-radius:24px;background:rgba(168,85,247,0.2);border:1px solid rgba(168,85,247,0.4);display:flex;align-items:center;justify-content:center;font-size:32px;margin:0 auto 16px auto;">
                    👨‍👧
                  </div>
                  <h2 style="font-size:20px;font-weight:900;color:#ffffff;margin:0 0 8px 0;">Pedir para otra silla</h2>
                  <p style="font-size:13px;color:#94a3b8;line-height:1.5;max-width:300px;margin:0 auto;">
                    No hay otras sillas ocupadas en tu mesa actualmente. Pide a tus acompañantes escanear su portavasos para poder ayudarles.
                  </p>
                </div>
              </div>
            """)
            return

        cards_html = ""
        for s in sillas_disponibles:
            snum = s.get("sillaId")
            nombre = s.get("comensalNombre", f"Silla {snum}")
            cards_html += f"""
            <div data-action="tab" data-args="__setSilla{snum}" class="vs-action-card vs-card-purple">
              <div style="width:48px;height:48px;border-radius:14px;background:rgba(168,85,247,0.25);border:1px solid rgba(168,85,247,0.5);color:#d8b4fe;font-weight:900;font-size:16px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                S{snum}
              </div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:15px;font-weight:900;color:#ffffff;">Silla {snum}</div>
                <div style="font-size:12px;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{nombre}</div>
              </div>
              <div style="color:#c084fc;font-size:14px;font-weight:900;">➔</div>
            </div>
            """

        html = f"""
        <div class="vs-mobile-wrap">
          {self._header_html()}
          <div style="padding:16px 16px 0 16px;">
            <button data-action="volverInicio" style="background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.1);color:#94a3b8;font-size:12px;font-weight:800;padding:6px 12px;border-radius:12px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;margin-bottom:12px;">
              ⬅ Volver al inicio
            </button>
            <h2 style="font-size:20px;font-weight:900;color:#ffffff;margin:0 0 4px 0;display:flex;align-items:center;gap:8px;">
              <span>👨‍👧</span> Pedir para otra silla
            </h2>
            <p style="font-size:12px;color:#94a3b8;margin:0 0 16px 0;">Elige a qué comensal de tu mesa deseas agregarle platillos:</p>
            <div style="display:flex;flex-direction:column;gap:2px;">{cards_html}</div>
          </div>
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
        <div class="vs-header-bar">
          <div style="display:flex;align-items:center;gap:10px;">
            <div class="vs-brand-logo">
              V&amp;S
            </div>
            <div>
              <div style="font-size:13px;font-weight:900;color:#ffffff;line-height:1.2;">Mesa {mesa} · Silla {silla}</div>
              <div style="font-size:10px;font-weight:800;color:#34d399;text-transform:uppercase;letter-spacing:1px;">La Terraza</div>
            </div>
          </div>
          
          <div style="display:flex;align-items:center;gap:8px;">
            <button data-action="llamarMesero" class="vs-btn-amber">
              🔔 Mesero
            </button>
            <button data-action="verComanda" class="vs-btn-sky">
              🧾 Cuenta
            </button>
          </div>
        </div>
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
            "color: #fff; font-weight: 900; font-size: 13.5px; font-family: 'Plus Jakarta Sans', system-ui, sans-serif; "
            "padding: 14px 20px; text-align: center; "
            "box-shadow: 0 -8px 25px rgba(0,0,0,0.6); "
            "display: flex; align-items: center; justify-content: center; gap: 10px;"
        )
        banner.innerHTML = f"""
          <span style="font-size:16px;">🔔</span>
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
