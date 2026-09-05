  (function () {
    window.catalogProducts = [];
    window.catalogCategories = [];
    window.catalogMesas = [];

    window.setPOSCatalogoFromDB = function (prodsJson, catsJson, mesasJson) {
      try {
        const prods = (typeof prodsJson === 'string') ? JSON.parse(prodsJson) : prodsJson;
        if (Array.isArray(prods) && prods.length > 0) {
          window.catalogProducts = prods.map(function (p) {
            var rawIng = p.ingredientes;
            var parsedIng = [];
            if (Array.isArray(rawIng)) parsedIng = rawIng;
            else if (typeof rawIng === 'string') {
              try { parsedIng = JSON.parse(rawIng); } catch (e) { parsedIng = [rawIng]; }
            }

            var rawPasos = p.pasos;
            var parsedPasos = [];
            if (Array.isArray(rawPasos)) parsedPasos = rawPasos;
            else if (typeof rawPasos === 'string') {
              try { parsedPasos = JSON.parse(rawPasos); } catch (e) { parsedPasos = [rawPasos]; }
            }

            var rawExtras = p.extras_disponibles;
            var parsedExtras = [];
            if (Array.isArray(rawExtras)) {
              parsedExtras = rawExtras.map(function (ex) {
                if (typeof ex === 'object' && ex !== null) return (ex.nombre || '') + ' +$' + (ex.precio || 0);
                return String(ex);
              });
            }

            return {
              id: p.id,
              nombre: p.nombre,
              categoria_id: p.categoria_id,
              categoria_nombre: p.categoria_nombre || (p.categoria ? p.categoria.nombre : ''),
              descripcion: p.descripcion || '',
              precio: (typeof p.precio === 'number') ? p.precio : (parseFloat(p.precio_unitario) || 0),
              icono: p.icono || '🍽️',
              tiempo: p.tiempo_estimado ? (p.tiempo_estimado + ' min') : (p.tiempo || '8–10 min'),
              porciones: p.porciones || '1 persona',
              ingredientes: parsedIng.length > 0 ? parsedIng : ['Ingredientes frescos de temporada'],
              pasos: parsedPasos.length > 0 ? parsedPasos : ['Preparar al momento con ingredientes de calidad.'],
              adicionales: parsedExtras,
              notas: p.notas_receta || p.notas || ''
            };
          });
        }
      } catch (e) {
        console.error('Error parseando productos POS en setPOSCatalogoFromDB:', e);
      }

      try {
        const cats = (typeof catsJson === 'string') ? JSON.parse(catsJson) : catsJson;
        if (Array.isArray(cats) && cats.length > 0) {
          window.catalogCategories = cats;
          renderWaiterCatChips();
        }
      } catch (e) {
        console.error('Error parseando categorias POS en setPOSCatalogoFromDB:', e);
      }

      try {
        const mesas = (typeof mesasJson === 'string') ? JSON.parse(mesasJson) : mesasJson;
        if (Array.isArray(mesas) && mesas.length > 0) {
          window.catalogMesas = mesas;
        }
      } catch (e) {
        console.error('Error parseando mesas POS en setPOSCatalogoFromDB:', e);
      }

      renderWaiterMenuGrid();
    };

    function renderWaiterCatChips() {
      const container = document.getElementById('waiterCatChips');
      if (!container || !window.catalogCategories || window.catalogCategories.length === 0) return;
      container.innerHTML = '';
      const catActual = window.palapaState.categoriaFiltro || window.catalogCategories[0].nombre;

      window.catalogCategories.forEach(function (cat) {
        const btn = document.createElement('button');
        btn.dataset.cat = cat.nombre;
        btn.onclick = function () { window.filtrarCategoria(cat.nombre); };
        const isActive = (cat.nombre === catActual);
        btn.style.cssText = 'padding: 6px 11px !important; font-size: 11px !important; font-weight: 800 !important; border-radius: 10px !important; cursor: pointer !important; white-space: nowrap !important; transition: all 0.2s; ' +
          (isActive ? 'border: 1px solid #34d399 !important; background: #059669 !important; color: #ffffff !important;' : 'border: 1px solid #334155 !important; background: #1e293b !important; color: #cbd5e1 !important;');
        btn.innerHTML = (cat.icono ? (cat.icono + ' ') : '') + cat.nombre;
        container.appendChild(btn);
      });
    }

    var DEFAULT_CUENTAS = {
      // MESA 1: 100% Libre / Disponible (0 comensales)

      // MESA 2: Familia (Cuenta de Mesa al centro + Silla 1 y Silla 3)
      '2-0': {
        estado: 'ocupada',
        qrId: 'MESA-02',
        comensalNombre: '⭐ Cuenta de MESA (Al Centro)',
        items: [
          { id: 301, nombre: 'Entrada al Centro: Paneras & Mantequilla Gourmet', notas: 'Al centro para compartir', precio: 85.00, cantidad: 1, mesaId: 2, sillaNum: 0, es_cuenta_mesa: true, tipo_consumo: 'comida', hora: '09:26 AM', enviadoCocina: true, horaEnvioCocina: '09:26 AM' }
        ],
        historialUbicaciones: [
          { mesaId: 2, sillaNum: 0, hora: '09:25 AM' }
        ]
      },
      '2-1': {
        estado: 'ocupada',
        qrId: 'PV-021',
        comensalNombre: 'Adulto 1 (Papá)',
        items: [
          { id: 402, nombre: 'Combo Chilaquiles V&S', notas: 'Con huevo estrellado y café de olla', precio: 175.00, cantidad: 1, mesaId: 2, sillaNum: 1, es_cuenta_mesa: false, tipo_consumo: 'comida', hora: '09:30 AM', enviadoCocina: true, horaEnvioCocina: '09:30 AM' },
          { id: 501, nombre: 'Jugo de Naranja Natural', notas: 'Sin hielo', precio: 55.00, cantidad: 1, mesaId: 2, sillaNum: 1, es_cuenta_mesa: false, tipo_consumo: 'bebida', hora: '09:31 AM', enviadoCocina: true, horaEnvioCocina: '09:31 AM' }
        ],
        historialUbicaciones: [
          { mesaId: 2, sillaNum: 1, hora: '09:25 AM' }
        ]
      },
      '2-3': {
        estado: 'ocupada',
        qrId: 'PV-023',
        comensalNombre: 'Niño 1',
        items: [
          { id: 601, nombre: 'Hotcakes Infantiles (2 piezas)', notas: 'Con miel y mantequilla', precio: 75.00, cantidad: 1, mesaId: 2, sillaNum: 3, es_cuenta_mesa: false, tipo_consumo: 'comida', hora: '09:32 AM', enviadoCocina: true, horaEnvioCocina: '09:32 AM' },
          { id: 505, nombre: 'Chocolate Caliente Tradicional', notas: 'Tibio', precio: 55.00, cantidad: 1, mesaId: 2, sillaNum: 3, es_cuenta_mesa: false, tipo_consumo: 'bebida', hora: '09:34 AM', enviadoCocina: true, horaEnvioCocina: '09:34 AM' }
        ],
        historialUbicaciones: [
          { mesaId: 2, sillaNum: 3, hora: '09:25 AM' }
        ]
      },

      // MESA 3: 2 comensales (Silla 1 y Silla 2 ocupadas, Silla 3 y 4 libres)
      '3-1': {
        estado: 'ocupada',
        qrId: 'PV-031',
        comensalNombre: 'Comensal Silla 1',
        items: [
          { id: 201, nombre: 'Chilaquiles Verdisimos', notas: 'Con pollo • Salsa verde', precio: 145.00, cantidad: 1, mesaId: 3, sillaNum: 1, hora: '09:15 AM', enviadoCocina: true, horaEnvioCocina: '09:15 AM' }
        ],
        historialUbicaciones: [
          { mesaId: 3, sillaNum: 1, hora: '09:10 AM' }
        ]
      },
      '3-2': {
        estado: 'ocupada',
        qrId: 'PV-032',
        comensalNombre: 'Comensal Silla 2',
        items: [
          { id: 502, nombre: 'Café con Leche / Capuchino', notas: 'Con canela', precio: 68.00, cantidad: 1, mesaId: 3, sillaNum: 2, hora: '09:20 AM', enviadoCocina: true, horaEnvioCocina: '09:20 AM' }
        ],
        historialUbicaciones: [
          { mesaId: 3, sillaNum: 2, hora: '09:20 AM' }
        ]
      }
    };

    function getGlobalCache() {
      try {
        if (typeof window !== 'undefined' && window._palapa_cuentas_v1_cache) {
          return window._palapa_cuentas_v1_cache;
        }
        if (typeof window !== 'undefined' && window.top && window.top._palapa_cuentas_v1_cache) {
          return window.top._palapa_cuentas_v1_cache;
        }
        if (typeof globalThis !== 'undefined' && globalThis._palapa_cuentas_v1_cache) {
          return globalThis._palapa_cuentas_v1_cache;
        }
      } catch (e) { }
      return null;
    }

    function setGlobalCache(val) {
      try {
        if (typeof window !== 'undefined') window._palapa_cuentas_v1_cache = val;
        if (typeof window !== 'undefined' && window.top) window.top._palapa_cuentas_v1_cache = val;
        if (typeof globalThis !== 'undefined') globalThis._palapa_cuentas_v1_cache = val;
      } catch (e) { }
    }

    function saveStateToStorage() {
      if (!window.palapaState || !window.palapaState.cuentas) return;
      var data = window.palapaState.cuentas;
      // 1. In-memory global cache (inmune a restricciones de iframe de Anvil)
      setGlobalCache(JSON.parse(JSON.stringify(data)));

      // 2. SessionStorage
      try {
        sessionStorage.setItem('palapa_cuentas_v1', JSON.stringify(data));
        sessionStorage.setItem('palapa_croquis_state_v1', JSON.stringify({ cuentas: data }));
      } catch (e) { }

      // 3. LocalStorage
      try {
        localStorage.setItem('palapa_cuentas_v1', JSON.stringify(data));
        localStorage.setItem('palapa_croquis_state_v1', JSON.stringify({ cuentas: data }));
      } catch (e) { }
    }

    function loadStateFromStorage() {
      // 1. Intentar desde caché global en memoria
      var cache = getGlobalCache();
      if (cache && typeof cache === 'object' && Object.keys(cache).length > 0) {
        return JSON.parse(JSON.stringify(cache));
      }

      // 2. Intentar desde sessionStorage
      try {
        var sess = sessionStorage.getItem('palapa_cuentas_v1');
        if (sess) {
          var parsedSess = JSON.parse(sess);
          if (parsedSess && typeof parsedSess === 'object' && Object.keys(parsedSess).length > 0) {
            setGlobalCache(parsedSess);
            return parsedSess;
          }
        }
      } catch (e) { }

      // 3. Intentar desde localStorage
      try {
        var saved = localStorage.getItem('palapa_cuentas_v1');
        if (saved) {
          var parsed = JSON.parse(saved);
          if (parsed && typeof parsed === 'object' && Object.keys(parsed).length > 0) {
            setGlobalCache(parsed);
            return parsed;
          }
        }
      } catch (e) { }

      // 4. Fallback a semilla inicial DEFAULT_CUENTAS (solo en el arranque limpio)
      var initial = JSON.parse(JSON.stringify(DEFAULT_CUENTAS));
      setGlobalCache(initial);
      try { localStorage.setItem('palapa_cuentas_v1', JSON.stringify(initial)); } catch (e) { }
      try { sessionStorage.setItem('palapa_cuentas_v1', JSON.stringify(initial)); } catch (e) { }
      return initial;
    }

    window.palapaState = {
      mesaSeleccionadaId: 3,
      sillaSeleccionadaNum: 1,
      modoComandaActiva: false,
      categoriaFiltro: "Bebidas & Jugos",
      modoMoverActivo: false,
      sillaOrigenMover: null,
      cuentas: loadStateFromStorage()
    };

    // Snapshot anterior para detectar items NUEVOS y disparar notificaciones al mesero
    var _prevCuentasSnapshot = {};

    window.aplicarCuentasServidor = function(cuentasServidor) {
      if (!cuentasServidor) return;
      if (typeof cuentasServidor === 'string') {
        try {
          cuentasServidor = JSON.parse(cuentasServidor);
        } catch (e) { return; }
      }
      if (!cuentasServidor || typeof cuentasServidor !== 'object') return;
      if (!window.palapaState || !window.palapaState.cuentas) return;

      var changed = false;
      Object.keys(cuentasServidor).forEach(function(k) {
        var srv = cuentasServidor[k];
        if (!srv) return;
        
        if (!window.palapaState.cuentas[k]) {
          window.palapaState.cuentas[k] = JSON.parse(JSON.stringify(srv));
          changed = true;
        } else {
          var curr = window.palapaState.cuentas[k];
          if (srv.estado === 'ocupada' && curr.estado !== 'ocupada') {
            curr.estado = 'ocupada';
            changed = true;
          }
          if (srv.qrId && !curr.qrId) {
            curr.qrId = srv.qrId;
            changed = true;
          }
          if (srv.comensalNombre && curr.comensalNombre !== srv.comensalNombre) {
            curr.comensalNombre = srv.comensalNombre;
            changed = true;
          }
          if (srv.items && Array.isArray(srv.items)) {
            var localItems = curr.items || [];
            var mergedItems = srv.items.map(function(sItem, sIdx) {
              var lItem = localItems[sIdx] || localItems.find(function(it) {
                return (it.id && it.id === sItem.id) || (it.nombre === sItem.nombre && it.precio === sItem.precio);
              });
              if (lItem && lItem.enviadoCocina && !sItem.enviadoCocina) {
                return Object.assign({}, sItem, {
                  enviadoCocina: true,
                  horaEnvioCocina: lItem.horaEnvioCocina || sItem.horaEnvioCocina
                });
              }
              return sItem;
            });

            if (JSON.stringify(curr.items || []) !== JSON.stringify(mergedItems)) {
              curr.items = mergedItems;
              curr.estado = srv.estado || (curr.items.length > 0 ? 'ocupada' : curr.estado);
              changed = true;
            }
          }
          if (srv.estado && curr.estado !== srv.estado) {
            curr.estado = srv.estado;
            changed = true;
          }
        }
      });

      if (changed) {
        saveStateToStorage();
        renderStateUI();
      }

      // 🔔 Notificar al mesero cuando llegan items nuevos de un cliente QR
      Object.keys(cuentasServidor).forEach(function(k) {
        var srv = cuentasServidor[k];
        if (!srv || !srv.items || !Array.isArray(srv.items) || srv.items.length === 0) return;
        var prev = _prevCuentasSnapshot[k];
        var prevCount = prev && prev.items ? prev.items.length : 0;
        var newCount = srv.items.length;
        if (newCount > prevCount) {
          var newest = srv.items[srv.items.length - 1];
          var nombreProd = newest ? newest.nombre : 'Producto';
          var msg = `🛎️ M${srv.mesaId} Silla ${srv.sillaId || srv.sillaNum}: "${nombreProd}"${newCount > 1 ? ` (+${newCount - prevCount} item${newCount - prevCount > 1 ? 's' : ''})` : ''}`;
          showOrderToast(msg);
        }
        _prevCuentasSnapshot[k] = { items: JSON.parse(JSON.stringify(srv.items)) };
      });
    };

    // Auto-polling en segundo plano para sincronizar check-ins de comensales en tiempo real
    // NOTA: window.anvilGetCuentasServidor() devuelve una Promise (bridge Anvil JS→Python es async)
    var _syncInFlight = false;
    setInterval(function() {
      if (_syncInFlight) return; // evitar solapamiento de requests
      try {
        if (window.anvilGetCuentasServidor) {
          _syncInFlight = true;
          var maybePromise = window.anvilGetCuentasServidor();
          // Manejar tanto Promise como valor síncrono (compatibilidad)
          if (maybePromise && typeof maybePromise.then === 'function') {
            maybePromise.then(function(srvData) {
              _syncInFlight = false;
              if (srvData) { window.aplicarCuentasServidor(srvData); }
            }).catch(function(e) { _syncInFlight = false; });
          } else {
            _syncInFlight = false;
            if (maybePromise) { window.aplicarCuentasServidor(maybePromise); }
          }
        }
      } catch (e) { _syncInFlight = false; }
    }, 2000);

    function resetDemoState() {
      var initial = JSON.parse(JSON.stringify(DEFAULT_CUENTAS));
      window.palapaState.cuentas = initial;
      window.palapaState.mesaSeleccionadaId = 3;
      window.palapaState.sillaSeleccionadaNum = 1;
      window.palapaState.modoComandaActiva = false;
      setGlobalCache(initial);
      try { localStorage.removeItem('palapa_cuentas_v1'); } catch (e) { }
      try { sessionStorage.removeItem('palapa_cuentas_v1'); } catch (e) { }
      saveStateToStorage();
      cancelarModoMover();
      cerrarModalComanda();
      renderStateUI();
      showDragToast('🔄 Estado reiniciado a demo (Mesa 1: Libre, Mesa 2: 2 ocupadas, Mesa 3: 2 ocupadas)', 'ok');
    }

    // ── Toast de notificación (reemplaza alert()) ──
    var _toastTimer = null;
    function showDragToast(msg, tipo) {
      // tipo: 'ok' | 'warn' | 'err' | 'info'
      var t = document.getElementById('dragToast');
      if (!t) return;
      t.textContent = msg;
      t.className = 'show toast-' + (tipo || 'ok');
      if (_toastTimer) clearTimeout(_toastTimer);
      _toastTimer = setTimeout(function () {
        t.className = t.className.replace(' show', '').replace('show', '');
      }, 3200);
    }

    // Toast especial para pedidos nuevos de clientes QR (más tiempo + color naranja)
    function showOrderToast(msg) {
      var t = document.getElementById('dragToast');
      if (!t) return;
      t.textContent = msg;
      t.className = 'show toast-new-order';
      if (_toastTimer) clearTimeout(_toastTimer);
      _toastTimer = setTimeout(function () {
        t.className = t.className.replace(' show', '').replace('show', '');
      }, 5000);
    }

    // ── Mini-modal confirmación (reemplaza confirm()) ──
    var _combineCallback = null;
    function showCombineConfirm(srcMesa, srcSilla, tgtMesa, tgtSilla, onYes) {
      var backdrop = document.getElementById('combineConfirmBackdrop');
      var title = document.getElementById('combineConfirmTitle');
      var msg = document.getElementById('combineConfirmMsg');
      var detail = document.getElementById('combineConfirmDetail');
      if (!backdrop) { onYes(); return; }

      if (title) title.textContent = 'Combinar Cuentas';
      if (msg) msg.textContent = 'Ambas sillas ya tienen consumos.';
      if (detail) detail.innerHTML =
        '<b style="color:#f59e0b;">Origen:</b> Mesa ' + srcMesa + ' Silla ' + srcSilla +
        '<br><b style="color:#38bdf8;">Destino:</b> Mesa ' + tgtMesa + ' Silla ' + tgtSilla +
        '<br><span style="color:#64748b;font-size:11px;">Los consumos del origen se agregarán a la silla destino.</span>';

      _combineCallback = onYes;
      backdrop.classList.add('show');

      document.getElementById('combineConfirmYes').onclick = function () {
        backdrop.classList.remove('show');
        if (_combineCallback) _combineCallback();
        _combineCallback = null;
      };
      document.getElementById('combineConfirmNo').onclick = function () {
        backdrop.classList.remove('show');
        _combineCallback = null;
        cancelarModoMover();
      };
    }

    // ════════════════════════════════════════════════════════════
    //  DRAG DE SILLAS — patrón mousedown/mousemove/mouseup
    //  Igual al resize de VidaSpa: eventos en document para que
    //  z-index y pointer-events de elementos hijos NO interfieran.
    //  document.elementFromPoint() en mouseup detecta la silla destino.
    // ════════════════════════════════════════════════════════════

    var _ms = {
      active: false,   // mousedown activo esperando movimiento
      dragging: false,   // ya pasó el umbral → modo drag visual
      srcMesa: null,
      srcSilla: null,
      startX: 0,
      startY: 0,
      ghost: null
    };
    var _wasDrag = false; // bloquea el click que dispara el browser post-mouseup
    var DRAG_THRESHOLD = 6; // píxeles mínimos para activar drag

    function _limpiarDragVisual() {
      document.querySelectorAll('.chair-btn-fixed').forEach(function (c) {
        c.classList.remove('chair-dragging', 'chair-drag-target-valid', 'chair-drag-target-combine');
      });
      if (_ms.ghost && _ms.ghost.parentNode) {
        _ms.ghost.parentNode.removeChild(_ms.ghost);
      }
      _ms.ghost = null;
    }

    function getClosestChair(mesaId, clientX, clientY, srcM, srcS) {
      var minDist = Infinity;
      var closest = null;
      for (var s = 1; s <= 4; s++) {
        if (mesaId === srcM && s === srcS) continue;
        var el = document.getElementById('chair-' + mesaId + '-' + s);
        if (!el) continue;
        var rect = el.getBoundingClientRect();
        var cx = rect.left + rect.width / 2;
        var cy = rect.top + rect.height / 2;
        var dist = Math.hypot(clientX - cx, clientY - cy);
        if (dist < minDist) { minDist = dist; closest = { mesa: mesaId, silla: s }; }
      }
      return closest;
    }

    function _resolveTargetChair(clientX, clientY, srcM, srcS) {
      var elem = document.elementFromPoint(clientX, clientY);

      // 1. Direct hit on chair
      if (elem) {
        var chairEl = elem.closest ? elem.closest('.chair-btn-fixed') : null;
        if (chairEl && chairEl.id && chairEl.id.indexOf('chair-extra-') === -1) {
          var p = chairEl.id.split('-');
          if (p.length === 3) {
            var tM = parseInt(p[1]);
            var tS = parseInt(p[2]);
            if (!(tM === srcM && tS === srcS)) {
              return { mesaId: tM, sillaNum: tS, el: chairEl };
            }
          }
        }

        // 2. Hit on table box, table circle or mesa container
        var tableBox = elem.closest ? elem.closest('.table-box-220') : null;
        var tableCircle = elem.closest ? elem.closest('.table-circle-fixed') : null;
        var mesaId = null;
        if (tableBox && tableBox.id) {
          mesaId = parseInt(tableBox.id.replace('table-box-', ''));
        } else if (tableCircle && tableCircle.id) {
          mesaId = parseInt(tableCircle.id.replace('table-circle-', ''));
        } else {
          for (var m = 1; m <= 3; m++) {
            var mBox = document.getElementById('table-box-' + m);
            if (mBox) {
              var r = mBox.getBoundingClientRect();
              if (clientX >= r.left - 40 && clientX <= r.right + 40 && clientY >= r.top - 40 && clientY <= r.bottom + 40) {
                mesaId = m;
                break;
              }
            }
          }
        }

        if (mesaId && (srcM === 'extra' || mesaId !== srcM)) {
          // Buscar primero una silla libre estándar (1..4) si no es arrimar forzado
          var freeSilla = null;
          for (var fs = 1; fs <= 4; fs++) {
            var fk = mesaId + '-' + fs;
            var fc = window.palapaState.cuentas[fk];
            if (!fc || (fc.estado !== 'ocupada' && (!fc.items || fc.items.length === 0))) {
              freeSilla = fs;
              break;
            }
          }
          if (freeSilla !== null && srcM !== 'extra') {
            var cel = document.getElementById('chair-' + mesaId + '-' + freeSilla);
            return { mesaId: mesaId, sillaNum: freeSilla, el: cel };
          } else {
            // Mesa llena o arrastre desde reserva extra: arrimar nueva silla
            var celCircle = document.getElementById('table-circle-' + mesaId);
            return { mesaId: mesaId, sillaNum: 'arrimar_nueva', el: celCircle };
          }
        }
      }

      // 3. Proximity fallback: find closest chair within 220px
      var globalMinDist = Infinity;
      var globalClosest = null;
      for (var m = 1; m <= 3; m++) {
        for (var s = 1; s <= 4; s++) {
          if (m === srcM && s === srcS) continue;
          var cel = document.getElementById('chair-' + m + '-' + s);
          if (!cel) continue;
          var rect = cel.getBoundingClientRect();
          var cx = rect.left + rect.width / 2;
          var cy = rect.top + rect.height / 2;
          var dist = Math.hypot(clientX - cx, clientY - cy);
          if (dist < globalMinDist && dist < 220) {
            globalMinDist = dist;
            globalClosest = { mesaId: m, sillaNum: s, el: cel };
          }
        }
      }

      return globalClosest;
    }

    function _chairMousedown(e, mesaId, sillaNum) {
      if (e.button !== 0) return;

      if (mesaId === 'extra') {
        _ms.active = true;
        _ms.dragging = false;
        _ms.srcMesa = 'extra';
        _ms.srcSilla = sillaNum;
        _ms.startX = e.clientX;
        _ms.startY = e.clientY;
        document.addEventListener('mousemove', _chairMousemove);
        document.addEventListener('mouseup', _chairMouseup);
        return;
      }

      var key = mesaId + '-' + sillaNum;
      var cuenta = window.palapaState.cuentas[key];

      _ms.active = true;
      _ms.dragging = false;
      _ms.srcMesa = mesaId;
      _ms.srcSilla = sillaNum;
      _ms.startX = e.clientX;
      _ms.startY = e.clientY;

      document.addEventListener('mousemove', _chairMousemove);
      document.addEventListener('mouseup', _chairMouseup);
    }

    function _chairMousemove(e) {
      if (!_ms.active) return;

      var dx = Math.abs(e.clientX - _ms.startX);
      var dy = Math.abs(e.clientY - _ms.startY);

      // ── Activar modo drag si pasó el umbral ──
      if (!_ms.dragging && (dx > DRAG_THRESHOLD || dy > DRAG_THRESHOLD)) {
        _ms.dragging = true;
        cerrarModalComanda();
        window.palapaState.modoMoverActivo = true;
        window.palapaState.sillaOrigenMover = { mesaId: _ms.srcMesa, sillaNum: _ms.srcSilla };

        // Marcar silla origen
        if (_ms.srcMesa === 'extra') {
          var srcEx = document.getElementById('chair-extra-' + _ms.srcSilla);
          if (srcEx) srcEx.classList.add('chair-dragging');
        } else {
          var srcEl = document.getElementById('chair-' + _ms.srcMesa + '-' + _ms.srcSilla);
          if (srcEl) srcEl.classList.add('chair-dragging');
        }

        // Ghost que sigue al cursor (pointer-events:none → no bloquea elementFromPoint)
        var ghost = document.createElement('div');
        ghost.style.cssText = [
          'position:fixed', 'z-index:99999', 'pointer-events:none',
          'padding:8px 18px', 'background:#1e3a5f', 'color:#ffffff',
          'font-size:13px', 'font-weight:800', 'border-radius:12px',
          'border:2px solid #38bdf8', 'white-space:nowrap',
          'box-shadow:0 8px 28px rgba(0,0,0,0.4)',
          'transform:translate(-50%,-130%)',
          'left:' + e.clientX + 'px', 'top:' + e.clientY + 'px'
        ].join(';') + ';';

        if (_ms.srcMesa === 'extra') {
          ghost.innerHTML = '🪑 <b>+ Arrimar Silla Extra ' + _ms.srcSilla + '</b>';
        } else {
          var key = _ms.srcMesa + '-' + _ms.srcSilla;
          var cuenta = window.palapaState.cuentas[key] || { items: [] };
          var total = 0;
          if (cuenta.items) cuenta.items.forEach(function (i) { total += i.precio * i.cantidad; });
          var isOcc = !!(cuenta && (cuenta.estado === 'ocupada' || (cuenta.items && cuenta.items.length > 0)));
          ghost.innerHTML = '🪑 M' + _ms.srcMesa + ' · S' + _ms.srcSilla + (isOcc ? (' <b>$' + total.toFixed(2) + '</b>') : ' (Libre)');
        }

        document.body.appendChild(ghost);
        _ms.ghost = ghost;

        // Banner
        var bt = document.getElementById('bannerText');
        var bc = document.getElementById('btnCancelMove');
        if (bt) {
          if (_ms.srcMesa === 'extra') {
            bt.innerHTML = '🪑 <b style="color:#0284c7;">ARRIMANDO SILLA EXTRA:</b> Suelta sobre cualquier <b>Mesa</b> (se integrará como 5º lugar o comensal extra).';
          } else {
            bt.innerHTML = '🪑 <b style="color:#0284c7;">ARRASTRANDO</b> Mesa ' + _ms.srcMesa + ' Silla ' + _ms.srcSilla + ' — Suelta sobre otra silla o centro de mesa para moverla o arrimarla.';
          }
        }
        if (bc) bc.style.setProperty('display', 'block', 'important');
      }

      if (!_ms.dragging) return;

      // ── Mover ghost ──
      if (_ms.ghost) {
        _ms.ghost.style.left = e.clientX + 'px';
        _ms.ghost.style.top = e.clientY + 'px';
      }

      // ── Highlight silla destino detectada ──
      document.querySelectorAll('.chair-btn-fixed, .table-circle-fixed').forEach(function (c) {
        c.classList.remove('chair-drag-target-valid', 'chair-drag-target-combine');
      });

      var target = _resolveTargetChair(e.clientX, e.clientY, _ms.srcMesa, _ms.srcSilla);
      if (target && target.el) {
        if (target.sillaNum === 'arrimar_nueva') {
          target.el.classList.add('chair-drag-target-valid');
        } else {
          var tgt = window.palapaState.cuentas[target.mesaId + '-' + target.sillaNum];
          var busy = tgt && tgt.items && tgt.items.length > 0;
          target.el.classList.add(busy ? 'chair-drag-target-combine' : 'chair-drag-target-valid');
        }
      }
    }

    function _chairMouseup(e) {
      document.removeEventListener('mousemove', _chairMousemove);
      document.removeEventListener('mouseup', _chairMouseup);

      var wasRealDrag = _ms.dragging;
      var srcM = _ms.srcMesa;
      var srcS = _ms.srcSilla;

      _limpiarDragVisual();
      _ms.active = false;
      _ms.dragging = false;
      _ms.srcMesa = null;
      _ms.srcSilla = null;

      if (!wasRealDrag) {
        return;
      }

      // ── Es un drag real: bloquear el click post-mouseup para evitar abrir la comanda por accidente ──
      _wasDrag = true;
      setTimeout(function () { _wasDrag = false; }, 350);

      // Resolver la silla destino
      var target = _resolveTargetChair(e.clientX, e.clientY, srcM, srcS);
      if (target) {
        completarMovimiento(target.mesaId, target.sillaNum, srcM, srcS);
      } else {
        cancelarModoMover();
        showDragToast('⚠ Suelta sobre una silla o mesa para mover o arrimar', 'warn');
      }
    }

    function setupDragListeners() {
      // 1. Asignar mousedown a todas las sillas estándar (1..4)
      for (var m = 1; m <= 3; m++) {
        for (var s = 1; s <= 4; s++) {
          (function (mesaId, sillaNum) {
            var el = document.getElementById('chair-' + mesaId + '-' + sillaNum);
            if (!el) return;
            el.addEventListener('mousedown', function (e) {
              _chairMousedown(e, mesaId, sillaNum);
            });
          })(m, s);
        }
      }

      // 2. Asignar mousedown a las sillas de Reserva Extras
      for (var ex = 1; ex <= 3; ex++) {
        (function (extraNum) {
          var exEl = document.getElementById('chair-extra-' + extraNum);
          if (!exEl) return;
          exEl.addEventListener('mousedown', function (e) {
            _chairMousedown(e, 'extra', extraNum);
          });
        })(ex);
      }
    }

    // Global Event Delegation for all Clicks
    document.addEventListener('click', function (e) {
      // Ignorar click que el browser dispara tras un drag con mouse
      if (_wasDrag) return;
      // 1. Chair clicked
      const chairNode = e.target.closest('.chair-btn-fixed');
      if (chairNode) {
        const id = chairNode.id; // e.g. "chair-3-1"
        const parts = id.split('-');
        if (parts.length === 3) {
          const mesaId = parseInt(parts[1]);
          const sillaNum = parseInt(parts[2]);
          handleSillaClick(mesaId, sillaNum);
          return;
        }
      }

      // 2. Table card, table circle or table title clicked -> ABRIR POP-MENU DE MESA
      const tableCircleNode = e.target.closest('.table-circle-fixed, .table-square-fixed, [id^="table-circle-"]');
      const tableCardNode = e.target.closest('[id^="table-card-container-"], [id^="table-box-"], [id^="table-header-title-"], [id^="table-label-"]');
      if (!chairNode && (tableCircleNode || tableCardNode)) {
        let mesaId = 2;
        if (tableCircleNode) {
          const parts = tableCircleNode.id.split('-');
          mesaId = parseInt(parts[parts.length - 1]);
        } else if (tableCardNode) {
          const parts = tableCardNode.id.split('-');
          mesaId = parseInt(parts[parts.length - 1]);
        }
        if (mesaId && !isNaN(mesaId)) {
          handleMesaClick(mesaId);
          return;
        }
      }

      // 3. Category chip clicked
      const chipNode = e.target.closest('[data-cat]');
      if (chipNode) {
        const cat = chipNode.getAttribute('data-cat');
        filtrarCategoria(cat);
        return;
      }

      // 4. Action buttons
      if (e.target.closest('#btnResetDemo')) { resetDemoState(); return; }
      if (e.target.closest('#btnVerComandaActiva')) { abrirModalComandaActual(); return; }
      if (e.target.closest('#btnMoverComensalMain')) { iniciarModoMover(); return; }
      if (e.target.closest('#btnMoverDesdeModal')) { cerrarModalComanda(); iniciarModoMover(); return; }
      if (e.target.closest('#btnCloseModal') || e.target.closest('#btnCerrarModalBottom')) { cerrarModalComanda(); return; }
      if (e.target.closest('#btnCancelMove')) { cancelarModoMover(); return; }
      if (e.target.closest('#btnPrecuenta')) { abrirPrecuenta(); return; }

      // 5. Click outside modal content (on backdrop) closes modal
      if (e.target.id === 'modalComandaBackdrop') {
        cerrarModalComanda();
        return;
      }
      if (e.target.id === 'modalPopMenuMesaBackdrop') {
        window.cerrarPopMenuMesa();
        return;
      }
    });

    // Escape key closes modals and cancels move mode
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        cerrarModalComanda();
        window.cerrarPopMenuMesa();
        cancelarModoMover();
        var cb = document.getElementById('combineConfirmBackdrop');
        if (cb) cb.classList.remove('show');
      }
    });

    function handleSillaClick(mesaId, sillaNum) {
      if (window.palapaState.modoMoverActivo) {
        completarMovimiento(mesaId, sillaNum);
        return;
      }

      const key = `${mesaId}-${sillaNum}`;

      // Si la silla no tiene cuenta, el mesero la registra de inmediato como OCUPADA (comensal presencial ubicado)
      if (!window.palapaState.cuentas[key]) {
        const nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        window.palapaState.cuentas[key] = {
          estado: 'ocupada',
          qrId: 'PV-0' + mesaId + sillaNum,
          comensalNombre: 'Comensal Silla ' + sillaNum,
          items: [],
          historialUbicaciones: [
            { mesaId: mesaId, sillaNum: sillaNum, hora: nowStr }
          ],
          creadoPor: 'mesero_presencial',
          horaLlegada: nowStr
        };
        saveStateToStorage();
        showDragToast('🪑 Comensal ubicado en Mesa ' + mesaId + ' Silla ' + sillaNum + ' (Silla ocupada)', 'ok');
      }

      window.palapaState.mesaSeleccionadaId = mesaId;
      window.palapaState.sillaSeleccionadaNum = sillaNum;
      window.palapaState.modoComandaActiva = true;
      renderStateUI();
    }

    function handleMesaClick(mesaId) {
      if (window.palapaState.modoMoverActivo) {
        var src = window.palapaState.sillaOrigenMover;
        if (!src) {
          showDragToast("Selecciona una silla específica.", "warn");
          return;
        }
        if (src.mesaId === mesaId) {
          showDragToast("El comensal ya se encuentra en esta mesa.", "warn");
          return;
        }

        // Buscar si hay alguna silla libre de las 4 estándar
        var libreSilla = null;
        for (var s = 1; s <= 4; s++) {
          var k = mesaId + '-' + s;
          var c = window.palapaState.cuentas[k];
          if (!c || (c.estado !== 'ocupada' && (!c.items || c.items.length === 0))) {
            libreSilla = s;
            break;
          }
        }

        if (libreSilla !== null) {
          completarMovimiento(mesaId, libreSilla);
        } else {
          // Las 4 sillas estándar están ocupadas -> ¡Arrimar automáticamente una silla extra (S5, S6...)!
          var maxS = 4;
          Object.keys(window.palapaState.cuentas).forEach(function (key) {
            var parts = key.split('-');
            if (parseInt(parts[0]) === mesaId) {
              var sn = parseInt(parts[1]);
              if (sn > maxS) maxS = sn;
            }
          });
          var nuevaSillaNum = maxS + 1;
          completarMovimiento(mesaId, nuevaSillaNum);
          showDragToast(`🪑 Se arrimó la Silla ${nuevaSillaNum} (Extra) en Mesa ${mesaId} para el comensal.`, 'ok');
        }
        return;
      }

      window.palapaState.mesaSeleccionadaId = mesaId;
      if (typeof window.abrirPopMenuMesa === 'function') {
        window.abrirPopMenuMesa(mesaId);
      }
    }

    function abrirPopMenuMesa(mesaId) {
      if (typeof window.abrirPopMenuMesa === 'function') {
        window.abrirPopMenuMesa(mesaId);
      }
    }

    window.handleSillaClick = handleSillaClick;
    window.handleMesaClick = handleMesaClick;
    window.clickSilla = handleSillaClick;
    window.clickMesa = handleMesaClick;

    // PRORRATEAR CUENTA DE MESA (AL CENTRO) ENTRE LAS SILLAS ACTIVAS
    window.prorratearCuentaMesaEntreSillas = function (mesaId) {
      mesaId = mesaId || window.palapaState.mesaSeleccionadaId || 2;
      const keyMesa = `${mesaId}-0`;
      const ctaMesa = window.palapaState.cuentas[keyMesa];

      if (!ctaMesa || !ctaMesa.items || ctaMesa.items.length === 0) {
        showDragToast('ℹ No hay platillos al centro para prorratear.', 'warn');
        return;
      }

      const unpaids = ctaMesa.items.filter(it => !it.pagado);
      if (unpaids.length === 0) {
        showDragToast('ℹ Todos los platillos al centro ya han sido liquidados.', 'info');
        return;
      }

      // Encontrar sillas activas / ocupadas
      const sillasActivas = [];
      for (let s = 1; s <= 10; s++) {
        const k = `${mesaId}-${s}`;
        const c = window.palapaState.cuentas[k];
        if (c && (c.estado === 'ocupada' || (c.items && c.items.length > 0))) {
          sillasActivas.push(s);
        }
      }

      if (sillasActivas.length === 0) {
        showDragToast('⚠ No hay comensales activos en la mesa para prorratear.', 'warn');
        return;
      }

      const totalCentro = unpaids.reduce((sum, it) => sum + (it.precio || 0) * (it.cantidad || 1), 0);
      const cuotaPorSilla = Number((totalCentro / sillasActivas.length).toFixed(2));

      sillasActivas.forEach(sNum => {
        const k = `${mesaId}-${sNum}`;
        if (!window.palapaState.cuentas[k]) {
          window.palapaState.cuentas[k] = {
            estado: 'ocupada',
            qrId: `PV-0${mesaId}${sNum}`,
            comensalNombre: `Comensal Silla ${sNum}`,
            items: [],
            historialUbicaciones: [{ mesaId: mesaId, sillaNum: sNum, hora: (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]
          };
        }
        window.palapaState.cuentas[k].items.push({
          id: Date.now() + Math.floor(Math.random() * 1000),
          nombre: `Cuota Al Centro (1/${sillasActivas.length} de $${totalCentro.toFixed(2)})`,
          precio: cuotaPorSilla,
          cantidad: 1,
          tipo_consumo: 'comida',
          es_cuenta_mesa: false,
          enviadoCocina: true,
          estadoCocina: 'servido',
          notas: 'Prorrateo de Cuenta de Mesa'
        });
      });

      // Limpiar items no pagados de la mesa
      ctaMesa.items = ctaMesa.items.filter(it => it.pagado);
      if (ctaMesa.items.length === 0) {
        ctaMesa.estado = 'disponible';
      }

      saveStateToStorage();
      renderStateUI();
      window.abrirPopMenuMesa(mesaId);
      showDragToast(`⚖️ ¡$${totalCentro.toFixed(2)} de platillos al centro prorrateados entre ${sillasActivas.length} sillas ($${cuotaPorSilla.toFixed(2)} c/u)!`, 'ok');
    };

    // ABRIR POP-MENU CONTEXTUAL DE MESA
    window.abrirPopMenuMesa = function (mesaId) {
      mesaId = mesaId || window.palapaState.mesaSeleccionadaId || 2;
      window.palapaState.mesaSeleccionadaId = mesaId;

      const modal = document.getElementById('modalPopMenuMesaBackdrop');
      const iconEl = document.getElementById('popMenuMesaIcon');
      const tituloEl = document.getElementById('popMenuMesaTitulo');
      const estadoEl = document.getElementById('popMenuMesaEstado');
      const centroTotalEl = document.getElementById('popMenuMesaCentroTotalBadge');
      const centroItemsEl = document.getElementById('popMenuMesaCentroItemsList');

      // 1. Recolectar datos financieros y de comensales
      let totalMesa = 0;
      let sillasOcupadasCount = 0;

      // Platillos al centro (silla 0 / Cuenta de Mesa)
      const ctaMesa = window.palapaState.cuentas[`${mesaId}-0`];
      const itemsCentro = (ctaMesa && ctaMesa.items) ? ctaMesa.items.filter(it => !it.pagado) : [];
      const totalCentro = itemsCentro.reduce((sum, it) => sum + (it.precio || 0) * (it.cantidad || 1), 0);
      totalMesa += totalCentro;

      // Sillas 1..10
      for (let s = 1; s <= 10; s++) {
        const k = `${mesaId}-${s}`;
        const cta = window.palapaState.cuentas[k];
        if (cta && (cta.estado === 'ocupada' || (cta.items && cta.items.length > 0))) {
          sillasOcupadasCount++;
          if (cta.items) {
            cta.items.forEach(it => {
              const itTot = (it.precio || 0) * (it.cantidad || 1);
              totalMesa += itTot;
            });
          }
        }
      }

      // 2. Llenar Encabezado
      if (iconEl) iconEl.innerText = `M${mesaId}`;
      if (tituloEl) tituloEl.innerText = `Mesa ${mesaId} (La Palapa)`;
      if (estadoEl) {
        if (sillasOcupadasCount > 0) {
          estadoEl.innerHTML = `🟡 <b>${sillasOcupadasCount} Comensal(es) Ocupados</b> • Total Mesa: $${totalMesa.toFixed(2)}`;
          estadoEl.style.color = '#fbbf24';
        } else {
          estadoEl.innerHTML = `🟢 <b>Mesa Disponible / Libre</b>`;
          estadoEl.style.color = '#34d399';
        }
      }

      // 3. Renderizar Lista de Platillos al Centro (Mesa)
      if (centroTotalEl) centroTotalEl.innerText = `$${totalCentro.toFixed(2)}`;
      if (centroItemsEl) {
        centroItemsEl.innerHTML = '';
        if (itemsCentro.length === 0) {
          centroItemsEl.innerHTML = `<span style="color: #94a3b8; font-style: italic; font-size: 11px;">Sin platillos al centro registrados en este momento.</span>`;
        } else {
          itemsCentro.forEach(it => {
            const row = document.createElement('div');
            row.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: rgba(0,0,0,0.25); border-radius: 8px; border: 1px dashed rgba(234,179,8,0.25);';
            
            let statusBadge = it.enviadoCocina ? `<span style="color: #34d399; font-size: 9px; font-weight: 800;">🟢 ${it.estadoCocina || 'Recibido'}</span>` : `<span style="color: #f59e0b; font-size: 9px; font-weight: 800;">⏳ Por Enviar</span>`;

            row.innerHTML = `
              <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-weight: 800; color: #fde047; font-size: 12px;">${it.cantidad}x ${it.nombre}</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-weight: 900; color: #34d399; font-size: 12px;">$${((it.precio || 0) * (it.cantidad || 1)).toFixed(2)}</span>
                ${statusBadge}
              </div>
            `;
            centroItemsEl.appendChild(row);
          });
        }
      }

      if (modal) {
        modal.style.display = 'flex';
      }
    };

    window.cerrarPopMenuMesa = function () {
      const modal = document.getElementById('modalPopMenuMesaBackdrop');
      if (modal) modal.style.display = 'none';
    };

    window.popMenuAccionPedirAlCentro = function () {
      const mesaId = window.palapaState.mesaSeleccionadaId || 2;
      window.cerrarPopMenuMesa();

      const key = `${mesaId}-0`;
      if (!window.palapaState.cuentas[key]) {
        const nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        window.palapaState.cuentas[key] = {
          estado: 'ocupada',
          qrId: `MESA-0${mesaId}`,
          comensalNombre: '⭐ Cuenta de MESA (Al Centro)',
          es_cuenta_mesa: true,
          items: [],
          historialUbicaciones: [{ mesaId: mesaId, sillaNum: 0, hora: nowStr }],
          creadoPor: 'mesero_presencial',
          horaLlegada: nowStr
        };
      } else {
        window.palapaState.cuentas[key].estado = 'ocupada';
        window.palapaState.cuentas[key].es_cuenta_mesa = true;
      }

      window.palapaState.sillaSeleccionadaNum = 0;
      window.palapaState.modoComandaActiva = true;
      saveStateToStorage();
      renderStateUI();
      showDragToast(`⭐ Comanda de Mesa ${mesaId} activada para Platillos al Centro (compartidos)`, 'ok');
    };

    window.popMenuAccionChecarCocina = function () {
      const mesaId = window.palapaState.mesaSeleccionadaId || 2;
      window.cerrarPopMenuMesa();
      window.irACocinaMesa(mesaId);
    };

    window.popMenuAccionAbrirComanda = function () {
      const mesaId = window.palapaState.mesaSeleccionadaId || 2;
      window.cerrarPopMenuMesa();

      let targetSilla = 1;
      for (let s = 1; s <= 10; s++) {
        const k = `${mesaId}-${s}`;
        if (window.palapaState.cuentas[k] && (window.palapaState.cuentas[k].estado === 'ocupada' || (window.palapaState.cuentas[k].items && window.palapaState.cuentas[k].items.length > 0))) {
          targetSilla = s;
          break;
        }
      }
      window.palapaState.sillaSeleccionadaNum = targetSilla;
      window.palapaState.modoComandaActiva = true;
      renderStateUI();
    };

    window.popMenuAccionCobrar = function () {
      window.cerrarPopMenuMesa();
      abrirPrecuenta();
    };

    window.arrimarSillaExtraMesaActual = function () {
      const mesaId = window.palapaState.mesaSeleccionadaId || 3;
      let maxS = 4;
      Object.keys(window.palapaState.cuentas).forEach(key => {
        const parts = key.split('-');
        if (parseInt(parts[0]) === mesaId) {
          const sn = parseInt(parts[1]);
          if (sn > maxS) maxS = sn;
        }
      });
      const nuevaSillaNum = maxS + 1;
      const key = `${mesaId}-${nuevaSillaNum}`;
      const nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      window.palapaState.cuentas[key] = {
        estado: 'ocupada',
        esArrimada: true,
        qrId: 'PV-0' + mesaId + nuevaSillaNum,
        comensalNombre: 'Comensal Silla ' + nuevaSillaNum + ' (Arrimada)',
        items: [],
        historialUbicaciones: [{ mesaId: mesaId, sillaNum: nuevaSillaNum, hora: nowStr }],
        creadoPor: 'mesero_presencial',
        horaLlegada: nowStr
      };

      window.palapaState.sillaSeleccionadaNum = nuevaSillaNum;
      window.palapaState.modoComandaActiva = true;
      saveStateToStorage();
      renderStateUI();
      showDragToast(`🪑 Silla ${nuevaSillaNum} (Extra Arrimada) incorporada a Mesa ${mesaId}`, 'ok');
    };

    window.unirMesas = function (tipo) {
      window.palapaState.mesasUnidas = tipo;
      saveStateToStorage();
      renderStateUI();
      if (tipo === '1-2') {
        showDragToast('🔗 Mesas 1 y 2 unidas en un solo grupo modular (8 Lugares)', 'ok');
      } else if (tipo === '2-3') {
        showDragToast('🔗 Mesas 2 y 3 unidas en un solo grupo modular (8 Lugares)', 'ok');
      } else if (tipo === '1-2-3') {
        showDragToast('👑 Mesas 1, 2 y 3 agrupadas en Gran Mesa Imperial (10 a 12 Lugares)', 'ok');
      }
    };

    window.separarMesas = function () {
      window.palapaState.mesasUnidas = null;
      saveStateToStorage();
      renderStateUI();
      showDragToast('✂ Mesas separadas a configuración individual estándar', 'info');
    };

    window.iniciarModoMover = function () {
      const mesaId = window.palapaState.mesaSeleccionadaId;
      const sillaNum = window.palapaState.sillaSeleccionadaNum;

      if (sillaNum === null) {
        showDragToast("Por favor selecciona una silla específica para mover.", "warn");
        return;
      }

      const key = `${mesaId}-${sillaNum}`;
      const cuenta = window.palapaState.cuentas[key];
      const isOccupied = !!(cuenta && (cuenta.estado === 'ocupada' || (cuenta.items && cuenta.items.length > 0)));

      if (!isOccupied) {
        showDragToast(`⚠ La Silla ${sillaNum} de Mesa ${mesaId} está disponible. Selecciona una silla ocupada para mover.`, "warn");
        return;
      }

      window.palapaState.modoMoverActivo = true;
      window.palapaState.sillaOrigenMover = { mesaId, sillaNum };
      window.palapaState.modoComandaActiva = false; // Regresar a la vista de croquis panorámico para ver todas las mesas

      const bannerText = document.getElementById('bannerText');
      const btnCancel = document.getElementById('btnCancelMove');

      if (bannerText && btnCancel) {
        bannerText.innerHTML = `<b style="color: #38bdf8;">MOVIENDO COMENSAL (Mesa ${mesaId} Silla ${sillaNum}):</b> Haz clic en la <b>Silla Destino</b> o en el <b>Centro de la Mesa</b> (si está llena se arrimará una silla extra).`;
        btnCancel.style.display = 'block';
      }

      renderStateUI();
    };

    function iniciarModoMover() {
      window.iniciarModoMover();
    }

    function limpiarDragState() {
      _limpiarDragVisual();
    }

    window.cancelarModoMover = function () {
      window.palapaState.modoMoverActivo = false;
      window.palapaState.sillaOrigenMover = null;
      if (typeof _ms !== 'undefined') {
        _ms.active = false;
        _ms.dragging = false;
        _ms.srcMesa = null;
        _ms.srcSilla = null;
      }
      _limpiarDragVisual();

      const bannerText = document.getElementById('bannerText');
      const btnCancel = document.getElementById('btnCancelMove');

      if (bannerText && btnCancel) {
        bannerText.innerHTML = `Haz clic o <b>arrastra con el mouse</b> cualquier <b>Silla</b> para abrir su comanda o trasladarla a otra silla/mesa.`;
        btnCancel.style.display = 'none';
      }

      renderStateUI();
    };

    function cancelarModoMover() {
      window.cancelarModoMover();
    }

    function completarMovimiento(targetMesaId, targetSillaNum, overrideSrcMesa, overrideSrcSilla) {
      // Soporte dual: modo click (sillaOrigenMover) y drag & drop (override params)
      var srcMesa = overrideSrcMesa !== undefined ? overrideSrcMesa : (window.palapaState.sillaOrigenMover ? window.palapaState.sillaOrigenMover.mesaId : null);
      var srcSilla = overrideSrcSilla !== undefined ? overrideSrcSilla : (window.palapaState.sillaOrigenMover ? window.palapaState.sillaOrigenMover.sillaNum : null);

      if (srcMesa === null || srcSilla === null) return;
      if (srcMesa === targetMesaId && srcSilla === targetSillaNum) {
        cancelarModoMover(); return;
      }

      // Sincronizar estado por si viene de drag (sillaOrigenMover puede ser null)
      if (!window.palapaState.sillaOrigenMover) {
        window.palapaState.sillaOrigenMover = { mesaId: srcMesa, sillaNum: srcSilla };
      }

      // ── CASO A: Arrimar desde la Reserva de Sillas Extras ──
      if (srcMesa === 'extra') {
        let maxS = 4;
        Object.keys(window.palapaState.cuentas).forEach(function (k) {
          var p = k.split('-');
          if (parseInt(p[0]) === targetMesaId) {
            var sn = parseInt(p[1]);
            if (sn > maxS) maxS = sn;
          }
        });

        var nuevaSillaNum = maxS + 1;
        if (targetSillaNum !== 'arrimar_nueva' && typeof targetSillaNum === 'number' && targetSillaNum <= 4) {
          var tk = targetMesaId + '-' + targetSillaNum;
          var tc = window.palapaState.cuentas[tk];
          if (!tc || (tc.estado !== 'ocupada' && (!tc.items || tc.items.length === 0))) {
            nuevaSillaNum = targetSillaNum;
          }
        }

        var key = targetMesaId + '-' + nuevaSillaNum;
        var nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        window.palapaState.cuentas[key] = {
          estado: 'ocupada',
          esArrimada: nuevaSillaNum > 4,
          qrId: 'PV-0' + targetMesaId + nuevaSillaNum,
          comensalNombre: 'Comensal Silla ' + nuevaSillaNum + (nuevaSillaNum > 4 ? ' (Arrimada)' : ''),
          items: [],
          historialUbicaciones: [{ mesaId: targetMesaId, sillaNum: nuevaSillaNum, hora: nowStr }],
          creadoPor: 'mesero_presencial',
          horaLlegada: nowStr
        };

        window.palapaState.mesaSeleccionadaId = targetMesaId;
        window.palapaState.sillaSeleccionadaNum = nuevaSillaNum;
        window.palapaState.modoComandaActiva = false;
        saveStateToStorage();
        cancelarModoMover();
        showDragToast('🪑 Silla Extra arrimada con éxito a Mesa ' + targetMesaId + ' (Silla ' + nuevaSillaNum + ')', 'ok');
        return;
      }

      // ── CASO B: Arrimar a una mesa llena desde otra mesa (o mover cuenta) ──
      if (targetSillaNum === 'arrimar_nueva') {
        let maxS = 4;
        Object.keys(window.palapaState.cuentas).forEach(function (k) {
          var p = k.split('-');
          if (parseInt(p[0]) === targetMesaId) {
            var sn = parseInt(p[1]);
            if (sn > maxS) maxS = sn;
          }
        });
        targetSillaNum = maxS + 1;
      }

      var sourceKey = srcMesa + '-' + srcSilla;
      var targetKey = targetMesaId + '-' + targetSillaNum;
      var sourceCuenta = window.palapaState.cuentas[sourceKey] || {
        estado: 'ocupada',
        items: [],
        comensalNombre: 'Comensal Silla ' + srcSilla
      };
      var targetCuenta = window.palapaState.cuentas[targetKey];
      var isTargetOccupied = !!(targetCuenta && (targetCuenta.estado === 'ocupada' || (targetCuenta.items && targetCuenta.items.length > 0)));

      // ── CASO 1: Si se arrastra a una silla estándar (1..4) que está LIBRE ──
      // El comensal pasa a ocupar la silla estándar y la silla origen (arrimada S5 o de otra mesa) SE ELIMINA
      if (!isTargetOccupied && typeof targetSillaNum === 'number' && targetSillaNum <= 4) {
        sourceCuenta.esArrimada = false;
        delete sourceCuenta.posicionArrimada;
        sourceCuenta.comensalNombre = 'Comensal Silla ' + targetSillaNum;
        sourceCuenta.qrId = 'PV-0' + targetMesaId + targetSillaNum;
        if (sourceCuenta.items) {
          sourceCuenta.items.forEach(function (i) {
            i.mesaId = targetMesaId;
            i.sillaNum = targetSillaNum;
          });
        }
        var nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        sourceCuenta.historialUbicaciones = sourceCuenta.historialUbicaciones || [{ mesaId: srcMesa, sillaNum: srcSilla, hora: nowStr }];
        sourceCuenta.historialUbicaciones.push({ mesaId: targetMesaId, sillaNum: targetSillaNum, hora: nowStr });

        window.palapaState.cuentas[targetKey] = sourceCuenta;
        delete window.palapaState.cuentas[sourceKey];

        window.palapaState.mesaSeleccionadaId = targetMesaId;
        window.palapaState.sillaSeleccionadaNum = targetSillaNum;
        window.palapaState.modoComandaActiva = false;
        saveStateToStorage();
        cancelarModoMover();
        renderStateUI();
        showDragToast('✅ Comensal reubicado a Silla ' + targetSillaNum + ' disponible de Mesa ' + targetMesaId, 'ok');
        return;
      }

      // ── CASO 2: Si es arrimada (S5+) y se arrastra sobre una silla OCUPADA de la misma mesa, reubicar su lado (top/right/bottom/left) ──
      if (srcMesa === targetMesaId && srcSilla > 4 && isTargetOccupied) {
        var lado = targetSillaNum === 1 ? 'top' : targetSillaNum === 2 ? 'right' : targetSillaNum === 3 ? 'bottom' : 'left';
        sourceCuenta.posicionArrimada = lado;
        saveStateToStorage();
        cancelarModoMover();
        renderStateUI();
        showDragToast('🪑 Silla ' + srcSilla + ' (Arrimada) colocada junto a Silla ' + targetSillaNum + ' en Mesa ' + srcMesa, 'ok');
        return;
      }

      var nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      sourceCuenta.historialUbicaciones = sourceCuenta.historialUbicaciones || [{ mesaId: srcMesa, sillaNum: srcSilla, hora: nowStr }];
      sourceCuenta.historialUbicaciones.push({ mesaId: targetMesaId, sillaNum: targetSillaNum, hora: nowStr });

      // Actualizar mesa y silla en los consumos del comensal
      if (sourceCuenta.items) {
        sourceCuenta.items.forEach(function (i) {
          i.mesaId = targetMesaId;
          i.sillaNum = targetSillaNum;
        });
      }
      sourceCuenta.qrId = 'PV-0' + targetMesaId + targetSillaNum;
      if (!sourceCuenta.comensalNombre || sourceCuenta.comensalNombre.indexOf('Comensal Silla') === 0) {
        sourceCuenta.comensalNombre = 'Comensal Silla ' + targetSillaNum + (targetSillaNum > 4 ? ' (Arrimada)' : '');
      }
      if (targetSillaNum > 4) {
        sourceCuenta.esArrimada = true;
      }

      var isTargetOccupied = !!(targetCuenta && (targetCuenta.estado === 'ocupada' || (targetCuenta.items && targetCuenta.items.length > 0)));
      var targetHasItems = targetCuenta && targetCuenta.items && targetCuenta.items.length > 0;
      var sourceHasItems = sourceCuenta.items && sourceCuenta.items.length > 0;

      if (isTargetOccupied && (targetHasItems || sourceHasItems)) {
        // Silla destino ocupada y con consumos — pedir confirmación sin alert()
        showCombineConfirm(srcMesa, srcSilla, targetMesaId, targetSillaNum, function () {
          targetCuenta.items = (targetCuenta.items || []).concat(sourceCuenta.items || []);
          delete window.palapaState.cuentas[sourceKey];
          window.palapaState.mesaSeleccionadaId = targetMesaId;
          window.palapaState.sillaSeleccionadaNum = targetSillaNum;
          window.palapaState.modoComandaActiva = false;
          saveStateToStorage();
          cancelarModoMover();
          showDragToast('✅ Cuentas combinadas en Mesa ' + targetMesaId + ' Silla ' + targetSillaNum, 'ok');
        });
      } else {
        window.palapaState.cuentas[targetKey] = sourceCuenta;
        delete window.palapaState.cuentas[sourceKey];
        window.palapaState.mesaSeleccionadaId = targetMesaId;
        window.palapaState.sillaSeleccionadaNum = targetSillaNum;
        window.palapaState.modoComandaActiva = false;
        saveStateToStorage();
        cancelarModoMover();
        showDragToast('✅ Silla trasladada → Mesa ' + targetMesaId + ' Silla ' + targetSillaNum + (targetSillaNum > 4 ? ' (Arrimada)' : ''), 'ok');
      }
    }

    function abrirModalComandaActual() {
      const mesaId = window.palapaState.mesaSeleccionadaId;
      const sillaNum = window.palapaState.sillaSeleccionadaNum;

      const modal = document.getElementById('modalComandaBackdrop');
      const modalCard = document.getElementById('modalComandaCard');
      const title = document.getElementById('modalTitle');
      const subtitle = document.getElementById('modalSubtitle');
      const header = document.getElementById('modalItemsHeader');
      const container = document.getElementById('modalItemsList');
      const subtotalMontoEl = document.getElementById('modalSubtotalMonto');
      const ivaMontoEl = document.getElementById('modalIvaMonto');
      const propinaMontoEl = document.getElementById('modalPropinaMonto');
      const totalMontoEl = document.getElementById('modalTotalMonto');
      const totalLabelEl = document.getElementById('modalTotalLabel');
      const lblSubtotal = document.getElementById('lblSubtotalModal');
      const btnCobrarDirecto = document.getElementById('btnCobrarModalDirecto');
      const txtBtnCobrar = document.getElementById('txtBtnCobrarModal');
      const btnVerTodaMesa = document.getElementById('btnVerTodaMesaHeader');
      const btnMover = document.getElementById('btnMoverDesdeModal');
      const btnLiberar = document.getElementById('btnLiberarSilla');
      const boxAdicionarSillas = document.getElementById('boxAdicionarSillasAComanda');
      const chipsContainer = document.getElementById('comandaSillasChipsContainer');
      const alertPendientes = document.getElementById('modalPendientesAlert');
      const txtPendientes = document.getElementById('txtPendientesMensaje');

      if (!container || !modal) return;
      container.innerHTML = '';

      // 1. Recopilar todas las sillas ocupadas de la mesa
      var sillasOcupadas = [];
      for (let s = 1; s <= 10; s++) {
        const key = `${mesaId}-${s}`;
        const cuenta = window.palapaState.cuentas[key];
        const isPaid = !!(cuenta && (cuenta.estado === 'pagada' || cuenta.pagado));
        if (cuenta && (cuenta.estado === 'ocupada' || isPaid || (cuenta.items && cuenta.items.length > 0))) {
          var subChair = 0;
          var saldoChair = 0;
          if (cuenta.items) {
            cuenta.items.forEach(it => {
              var itSub = (it.precio * it.cantidad);
              subChair += itSub;
              if (!it.pagado && !isPaid) {
                saldoChair += itSub;
              }
            });
          }
          sillasOcupadas.push({
            sillaNum: s,
            cuenta: cuenta,
            subtotal: subChair,
            saldoPendiente: saldoChair,
            isPaid: isPaid && (saldoChair === 0)
          });
        }
      }

      // 2. Gestionar sillas seleccionadas para cobro
      if (!window.palapaState.sillasSeleccionadasCobro || window.palapaState.sillasSeleccionadasCobroMesa !== mesaId) {
        window.palapaState.sillasSeleccionadasCobroMesa = mesaId;
        if (sillaNum !== null) {
          window.palapaState.sillasSeleccionadasCobro = [sillaNum];
        } else {
          window.palapaState.sillasSeleccionadasCobro = sillasOcupadas.map(o => o.sillaNum);
        }
      }

      // Si estamos en una silla titular, esa silla SIEMPRE es fija e inamovible de su ticket
      if (sillaNum !== null && window.palapaState.sillasSeleccionadasCobro.indexOf(sillaNum) === -1) {
        window.palapaState.sillasSeleccionadasCobro.unshift(sillaNum);
      }

      var seleccionadas = window.palapaState.sillasSeleccionadasCobro || [];

      // 3. Renderizar Header y Selector de Sillas de la Mesa
      if (sillaNum !== null) {
        // MODO COBRO / TICKET POR COMENSAL ESPECÍFICO
        const key = `${mesaId}-${sillaNum}`;
        const cuenta = window.palapaState.cuentas[key] || { items: [] };
        const qrId = cuenta.qrId || ('PV-0' + mesaId + sillaNum);
        if (title) title.innerHTML = `<i class="fa-solid fa-receipt" style="color: #34d399;"></i> Ticket Silla ${sillaNum} <span style="font-size: 11px; background: #1e293b; color: #38bdf8; padding: 2px 8px; border-radius: 6px; border: 1px solid #334155; margin-left: 6px;">🏷️ QR ${qrId}</span>`;
        if (subtitle) subtitle.innerText = `Mesa ${mesaId} • ${cuenta.creadoPor === 'mesero_presencial' ? 'Comensal Ubicado Presencialmente' : 'Registro QR'}`;
        if (btnVerTodaMesa) btnVerTodaMesa.style.display = 'inline-flex';

        // 4. Renderizar Chips de Sillas Faltantes para Anexar (SOLO en modo silla específica)
        if (boxAdicionarSillas && chipsContainer) {
          var sillasDisponiblesParaAnexar = sillasOcupadas.filter(o => o.sillaNum !== sillaNum);

          if (sillasDisponiblesParaAnexar.length > 0) {
            boxAdicionarSillas.style.display = 'flex';
            chipsContainer.innerHTML = '';

            var lblSelector = boxAdicionarSillas.querySelector('span');
            if (lblSelector) {
              lblSelector.innerHTML = `<i class="fa-solid fa-user-plus" style="color: #38bdf8;"></i> ¿Esta cuenta (Silla ${sillaNum}) paga por otras sillas de la mesa?`;
            }

            var btnSoloEsta = document.getElementById('btnComandaSoloEsta');
            if (btnSoloEsta) {
              btnSoloEsta.innerText = `Solo Silla ${sillaNum}`;
            }

            sillasDisponiblesParaAnexar.forEach(obj => {
              var s = obj.sillaNum;
              var isSel = (seleccionadas.indexOf(s) !== -1);

              var chip = document.createElement('button');
              chip.type = 'button';
              chip.onclick = function () { window.toggleSillaAdicional(s); };
              chip.style.cssText = `padding: 6px 12px !important; font-size: 11px !important; font-weight: 800 !important; border-radius: 8px !important; cursor: pointer !important; transition: all 0.2s ease !important; display: flex !important; align-items: center !important; gap: 6px !important; ${isSel
                  ? 'background: #064e3b !important; color: #34d399 !important; border: 2px solid #10b981 !important; box-shadow: 0 0 10px rgba(16, 185, 129, 0.3) !important;'
                  : 'background: #1e293b !important; color: #cbd5e1 !important; border: 1px solid #334155 !important;'
                }`;
              chip.innerHTML = isSel
                ? `<i class="fa-solid fa-check"></i> Silla ${s} • $${obj.subtotal.toFixed(2)} <span style="font-size: 10px; color: #f87171; margin-left: 4px; font-weight: 900;" title="Quitar">✕</span>`
                : `<i class="fa-solid fa-plus" style="color: #38bdf8;"></i> Silla ${s} • $${obj.subtotal.toFixed(2)}`;
              chipsContainer.appendChild(chip);
            });
          } else {
            boxAdicionarSillas.style.display = 'none';
          }
        }
      } else {
        // MODO PANORAMA GENERAL DE LA MESA (SUPERVISIÓN PURAMENTE INFORMATIVA)
        if (title) title.innerHTML = `<i class="fa-solid fa-table-cells" style="color: #38bdf8;"></i> Panorama General • Mesa ${mesaId} (${sillasOcupadas.length} Comensales)`;
        if (subtitle) subtitle.innerText = `Vista informativa de supervisión y consumos por silla (haz clic en una silla para cobrarla)`;
        if (btnVerTodaMesa) btnVerTodaMesa.style.display = 'none';

        // Ocultar caja de anexión en vista general para evitar confusiones
        if (boxAdicionarSillas) boxAdicionarSillas.style.display = 'none';
      }

      if (modalCard) {
        modalCard.style.maxWidth = (seleccionadas.length > 1 || sillaNum === null) ? '960px' : '640px';
      }

      // 5. Renderizar Consumos
      if (header) {
        if (sillaNum === null) {
          header.innerHTML = `<i class="fa-solid fa-list-check" style="color: #38bdf8;"></i> Desglose Individual de Consumos por Silla:`;
        } else {
          header.innerText = (seleccionadas.length > 1)
            ? `Consumos Consolidados (${seleccionadas.length} Sillas: ${seleccionadas.map(s => 'Silla ' + s).join(' + ')}):`
            : `Consumos en Silla ${sillaNum}:`;
        }
      }

      if (sillaNum === null) {
        // PANORAMA GENERAL: Tarjetas informativas de todas las sillas de la mesa
        container.style.cssText = 'display: grid !important; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)) !important; gap: 12px !important; max-height: 340px !important; overflow-y: auto !important;';

        if (sillasOcupadas.length === 0) {
          container.innerHTML = `<div style="text-align: center; grid-column: 1/-1; padding: 25px; color: #64748b; font-size: 12px;">No hay comensales sentados en esta mesa actualmente.</div>`;
        } else {
          sillasOcupadas.forEach(obj => {
            var s = obj.sillaNum;
            var c = obj.cuenta;
            var qrId = c.qrId || ('PV-0' + mesaId + s);
            var sub = obj.subtotal;

            var card = document.createElement('div');
            card.style.cssText = 'background: #0f172a !important; border: 1px solid #334155 !important; border-radius: 12px !important; padding: 12px !important; display: flex !important; flex-direction: column !important; justify-content: space-between !important; gap: 8px !important;';

            var cardHeader = document.createElement('div');
            cardHeader.style.cssText = 'display: flex !important; justify-content: space-between !important; align-items: center !important; padding-bottom: 6px !important; border-bottom: 1px solid #1e293b !important; font-size: 11px !important;';
            cardHeader.innerHTML = `
              <div>
                <span style="font-weight: 900; color: #38bdf8; font-size: 12px; display: block;">
                  <i class="fa-solid fa-user"></i> Silla ${s} (${c.comensalNombre || 'Comensal'})
                </span>
                <span style="font-size: 10px; color: #64748b;">Portavasos #${qrId}</span>
              </div>
              <span style="font-weight: 900; color: #fbbf24; font-size: 13px;">$${sub.toFixed(2)}</span>
            `;
            card.appendChild(cardHeader);

            var itemsWrap = document.createElement('div');
            itemsWrap.style.cssText = 'display: flex !important; flex-direction: column !important; gap: 4px !important; flex: 1 !important; max-height: 140px !important; overflow-y: auto !important;';

            if (!c.items || c.items.length === 0) {
              itemsWrap.innerHTML = `<div style="text-align: center; color: #64748b; font-size: 10px; padding: 10px 0;">Sin consumos registrados</div>`;
            } else {
              c.items.forEach((it) => {
                var itSub = it.precio * it.cantidad;
                var row = document.createElement('div');
                row.style.cssText = 'display: flex !important; justify-content: space-between !important; align-items: center !important; background: #020617 !important; padding: 4px 6px !important; border-radius: 6px !important; font-size: 10px !important;';
                row.innerHTML = `
                  <div style="flex: 1; padding-right: 4px;">
                    <span style="font-weight: 700; color: #ffffff;">${it.cantidad}x ${it.nombre}</span>
                  </div>
                  <span style="font-weight: 900; color: #34d399;">$${itSub.toFixed(2)}</span>
                `;
                itemsWrap.appendChild(row);
              });
            }
            card.appendChild(itemsWrap);
            container.appendChild(card);
          });
        }
      } else if (seleccionadas.length === 1 && seleccionadas[0] === sillaNum) {
        // Vista detallada individual de la silla titular
        container.style.cssText = 'display: flex !important; flex-direction: column !important; gap: 8px !important; max-height: 320px !important; overflow-y: auto !important;';
        const key = `${mesaId}-${sillaNum}`;
        const cuenta = window.palapaState.cuentas[key] || { items: [] };
        const isPaid = !!(cuenta && (cuenta.estado === 'pagada' || cuenta.pagado));
        const saldoChair = (cuenta.items || []).reduce((acc, it) => acc + ((!it.pagado && !isPaid) ? (it.precio * it.cantidad) : 0), 0);
        const totalHistorico = (cuenta.items || []).reduce((acc, it) => acc + (it.precio * it.cantidad), 0);

        if (isPaid && saldoChair === 0) {
          const bannerPaid = document.createElement('div');
          bannerPaid.style.cssText = 'background: rgba(2, 132, 199, 0.18) !important; border: 1.5px solid #0284c7 !important; border-radius: 12px !important; padding: 12px 16px !important; display: flex !important; align-items: center !important; justify-content: space-between !important; margin-bottom: 6px !important;';
          bannerPaid.innerHTML = `
            <div>
              <div style="font-size: 13px !important; font-weight: 800 !important; color: #38bdf8 !important;">
                <i class="fa-solid fa-circle-check"></i> CUENTA PAGADA ($${(cuenta.montoPagado || totalHistorico).toFixed(2)}) • Saldo: $0.00
              </div>
              <div style="font-size: 11px !important; color: #94a3b8 !important; margin-top: 2px !important;">
                ${cuenta.metodoPago ? `Liquidado vía <b>${cuenta.metodoPago}</b> (${cuenta.horaPago || ''}) • ` : ''}Comensal disfrutando de <b>Sobremesa</b>.
              </div>
            </div>
            <button type="button" onclick="window.liberarSillaActual()" style="padding: 6px 14px !important; background: #ef4444 !important; color: #ffffff !important; border: none !important; border-radius: 8px !important; font-size: 11px !important; font-weight: 800 !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 5px !important; white-space: nowrap !important;">
              <i class="fa-solid fa-broom"></i> Desocupar Silla
            </button>
          `;
          container.appendChild(bannerPaid);
        }

        if (!cuenta.items || cuenta.items.length === 0) {
          container.innerHTML = `
            <div style="background: rgba(15, 23, 42, 0.8) !important; border: 1px dashed #059669 !important; border-radius: 14px !important; padding: 18px !important; text-align: center !important; display: flex !important; flex-direction: column !important; align-items: center !important; gap: 8px !important;">
              <div style="width: 42px !important; height: 42px !important; border-radius: 50% !important; background: rgba(16, 185, 129, 0.15) !important; border: 2px solid #10b981 !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 18px !important; color: #34d399 !important;">
                <i class="fa-solid fa-user-check"></i>
              </div>
              <div>
                <div style="font-size: 13px !important; font-weight: 800 !important; color: #ffffff !important;">Comensal Ubicado en Silla ${sillaNum}</div>
                <div style="font-size: 11px !important; color: #94a3b8 !important; margin-top: 3px !important;">La silla está registrada como <b style="color: #fbbf24;">OCUPADA</b> (ubicación presencial).</div>
              </div>
              <div style="display: flex; gap: 8px; justify-content: center; align-items: center; margin-top: 6px; flex-wrap: wrap;">
                <span style="font-size: 11px !important; color: #34d399 !important; font-weight: 700 !important; background: rgba(5, 150, 105, 0.15) !important; padding: 5px 12px !important; border-radius: 20px !important; border: 1px solid rgba(52, 211, 153, 0.3) !important;">
                  👉 Selecciona platillos del catálogo a la derecha
                </span>
                <button type="button" onclick="window.liberarSillaActual()" style="padding: 5px 12px !important; font-size: 11px !important; font-weight: 800 !important; background: rgba(239, 68, 68, 0.2) !important; color: #f87171 !important; border: 1px solid rgba(239, 68, 68, 0.4) !important; border-radius: 20px !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 4px !important;">
                  <i class="fa-solid fa-broom"></i> Desocupar Silla
                </button>
              </div>
            </div>
          `;
        } else {
          cuenta.items.forEach((it, idx) => {
            var itSub = it.precio * it.cantidad;
            var isItPaid = !!(it.pagado || isPaid);
            var row = document.createElement('div');
            row.style.cssText = 'display: flex !important; justify-content: space-between !important; align-items: center !important; background: #0f172a !important; padding: 8px 12px !important; border-radius: 10px !important; border: 1px solid #1e293b !important; font-size: 12px !important;';
            row.innerHTML = `
              <div style="flex: 1; padding-right: 8px;">
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span style="font-weight: 700; color: #ffffff;">${it.cantidad}x ${it.nombre}</span>
                </div>
                <span style="font-size: 10px; color: #94a3b8; font-style: italic;">${it.notas ? it.notas + ' • ' : ''}${it.hora || ''}</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-weight: 900; color: ${isItPaid ? '#94a3b8' : '#34d399'}; font-size: 12px;">$${itSub.toFixed(2)}</span>
                ${isItPaid
                ? `<span style="font-size: 9px; color: #38bdf8; font-weight: 800; background: rgba(2,132,199,0.2) !important; border: 1px solid rgba(56,189,248,0.4) !important; padding: 2px 6px !important; border-radius: 4px !important; display: inline-flex !important; align-items: center !important; gap: 3px !important;"><i class="fa-solid fa-circle-check"></i> Pagado</span>`
                : (it.enviadoCocina
                  ? (it.estadoCocina === 'listo'
                    ? `<span style="font-size: 9px; color: #38bdf8; font-weight: 900; background: rgba(2,132,199,0.25) !important; border: 1px solid #0284c7 !important; padding: 2px 6px !important; border-radius: 4px !important; display: inline-flex !important; align-items: center !important; gap: 3px !important;"><i class="fa-solid fa-circle-check"></i> ¡Listo en Pase!</span>`
                    : (it.estadoCocina === 'preparando'
                      ? (((Date.now() - (it.timestampInicioCocina || it.timestampEnvioCocina || Date.now())) / 60000 >= 14)
                        ? `<span style="font-size: 9px; color: #f87171; font-weight: 900; background: rgba(239,68,68,0.2) !important; border: 1px solid #ef4444 !important; padding: 2px 6px !important; border-radius: 4px !important; display: inline-flex !important; align-items: center !important; gap: 3px !important;"><i class="fa-solid fa-triangle-exclamation"></i> 🔴 Demorado</span>`
                        : `<span style="font-size: 9px; color: #fbbf24; font-weight: 800; background: rgba(245,158,11,0.2) !important; border: 1px solid rgba(245,158,11,0.4) !important; padding: 2px 6px !important; border-radius: 4px !important; display: inline-flex !important; align-items: center !important; gap: 3px !important;"><i class="fa-solid fa-fire"></i> 🟡 En Fuego</span>`)
                      : `<span style="font-size: 9px; color: #34d399; font-weight: 800; background: rgba(16,185,129,0.15) !important; border: 1px solid rgba(16,185,129,0.3) !important; padding: 2px 6px !important; border-radius: 4px !important; display: inline-flex !important; align-items: center !important; gap: 3px !important;"><i class="fa-solid fa-clock"></i> 🟢 Recibido</span>`))
                  : `<button onclick="window.eliminarItemModal('${key}', ${idx})" style="background: transparent; border: none; color: #f87171; cursor: pointer; padding: 2px;" title="Eliminar (No enviado)"><i class="fa-solid fa-trash-can" style="font-size: 11px;"></i></button>`)}
              </div>
            `;
            container.appendChild(row);
          });
        }
      } else {
        // Vista multitarjeta cuando se anexan sillas a la silla titular
        container.style.cssText = 'display: grid !important; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)) !important; gap: 12px !important; max-height: 340px !important; overflow-y: auto !important;';

        seleccionadas.forEach(s => {
          var chairObj = sillasOcupadas.find(o => o.sillaNum === s);
          var c = chairObj ? chairObj.cuenta : (window.palapaState.cuentas[`${mesaId}-${s}`] || { items: [] });
          var sub = chairObj ? chairObj.subtotal : 0;
          var saldo = chairObj ? chairObj.saldoPendiente : 0;
          var qrId = c.qrId || ('PV-0' + mesaId + s);
          var isTitular = (sillaNum !== null && s === sillaNum);
          var isPaidCard = !!(chairObj && chairObj.isPaid);

          var card = document.createElement('div');
          card.style.cssText = 'background: ' + (isTitular ? '#042f2e' : '#0b2921') + ' !important; border: 2px solid ' + (isTitular ? '#059669' : '#10b981') + ' !important; border-radius: 12px !important; padding: 10px 12px !important; display: flex !important; flex-direction: column !important; justify-content: space-between !important; gap: 8px !important; box-shadow: 0 0 12px rgba(16,185,129,0.2) !important;';

          var cardHeader = document.createElement('div');
          cardHeader.style.cssText = 'display: flex !important; justify-content: space-between !important; align-items: center !important; padding-bottom: 6px !important; border-bottom: 1px dashed #10b981 !important; font-size: 11px !important;';
          cardHeader.innerHTML = `
            <div>
              <span style="font-weight: 900; color: ${isTitular ? '#34d399' : '#a7f3d0'}; font-size: 12px; display: block;">
                <i class="fa-solid fa-receipt"></i> Silla ${s} ${isTitular ? '(Titular)' : '(Anexada)'} ${isPaidCard ? '✓' : ''}
              </span>
              <span style="font-size: 10px; color: #94a3b8;">Portavasos #${qrId}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-weight: 900; color: ${isPaidCard ? '#38bdf8' : '#fbbf24'}; font-size: 12px;">${isPaidCard ? 'PAGADO' : '$' + saldo.toFixed(2)}</span>
              ${!isTitular ? `<button onclick="window.toggleSillaAdicional(${s})" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold; cursor: pointer;" title="Quitar de este cobro">✕</button>` : ''}
            </div>
          `;
          card.appendChild(cardHeader);

          var itemsWrap = document.createElement('div');
          itemsWrap.style.cssText = 'display: flex !important; flex-direction: column !important; gap: 4px !important; flex: 1 !important; max-height: 140px !important; overflow-y: auto !important;';

          if (!c.items || c.items.length === 0) {
            itemsWrap.innerHTML = `<div style="text-align: center; color: #64748b; font-size: 10px; padding: 10px 0;">Sin consumos</div>`;
          } else {
            c.items.forEach((it) => {
              var itSub = it.precio * it.cantidad;
              var isItPaid = !!(it.pagado || isPaidCard);
              var row = document.createElement('div');
              row.style.cssText = 'display: flex !important; justify-content: space-between !important; align-items: center !important; background: #020617 !important; padding: 4px 6px !important; border-radius: 6px !important; font-size: 10px !important;';
              row.innerHTML = `
                <div style="flex: 1; padding-right: 4px;">
                  <span style="font-weight: 700; color: #ffffff;">${it.cantidad}x ${it.nombre}</span>
                </div>
                <span style="font-weight: 900; color: ${isItPaid ? '#94a3b8' : '#34d399'};">${isItPaid ? 'Pagado' : '$' + itSub.toFixed(2)}</span>
              `;
              itemsWrap.appendChild(row);
            });
          }
          card.appendChild(itemsWrap);
          container.appendChild(card);
        });
      }

      // 6. Cálculo de Totales Consolidados (SOLO SALDOS PENDIENTES)
      var totalNeto = 0;
      var totalPendiente = 0;
      var sillasPendientes = [];

      if (sillaNum === null) {
        // En panorama general, el total neto es el saldo pendiente acumulado de la mesa
        sillasOcupadas.forEach(obj => {
          totalNeto += obj.saldoPendiente;
        });
      } else {
        sillasOcupadas.forEach(obj => {
          if (seleccionadas.indexOf(obj.sillaNum) !== -1) {
            totalNeto += obj.saldoPendiente;
          } else {
            totalPendiente += obj.saldoPendiente;
            if (obj.saldoPendiente > 0) {
              sillasPendientes.push(`Silla ${obj.sillaNum}`);
            }
          }
        });
      }

      var subtotalBase = totalNeto / 1.16;
      var iva = totalNeto - subtotalBase;
      var propina = totalNeto * 0.10;
      var granTotal = totalNeto;

      if (lblSubtotal) {
        lblSubtotal.innerText = (totalNeto === 0)
          ? `Subtotal (Base s/IVA):`
          : ((sillaNum === null)
            ? `Subtotal Base (Toda la Mesa):`
            : `Subtotal Base (${seleccionadas.length} Silla${seleccionadas.length !== 1 ? 's' : ''}):`);
      }
      if (totalLabelEl) {
        if (totalNeto === 0) {
          totalLabelEl.innerText = `Saldo Pendiente a Cobrar:`;
        } else if (sillaNum === null) {
          totalLabelEl.innerText = `Total Acumulado de la Mesa:`;
        } else if (seleccionadas.length === sillasOcupadas.length && sillasOcupadas.length > 0) {
          totalLabelEl.innerText = `Total a Pagar (Toda la Mesa):`;
        } else {
          totalLabelEl.innerText = `Total a Pagar (Silla${seleccionadas.length > 1 ? 's ' : ' '}${seleccionadas.join(', ')}):`;
        }
      }

      if (subtotalMontoEl) subtotalMontoEl.innerText = `$${subtotalBase.toFixed(2)}`;
      if (ivaMontoEl) ivaMontoEl.innerText = `$${iva.toFixed(2)}`;
      if (propinaMontoEl) propinaMontoEl.innerText = `$${propina.toFixed(2)}`;
      if (totalMontoEl) totalMontoEl.innerText = `$${granTotal.toFixed(2)}`;
      if (txtBtnCobrar) txtBtnCobrar.innerText = `$${granTotal.toFixed(2)}`;

      // 7. Alerta de sillas pendientes no incluidas en este cobro (solo en modo cobro específico)
      if (alertPendientes && txtPendientes) {
        if (sillaNum !== null && sillasPendientes.length > 0 && totalNeto > 0) {
          alertPendientes.style.display = 'block';
          txtPendientes.innerHTML = `<b>Quedará pendiente en la mesa:</b> ${sillasPendientes.join(', ')} por <b>$${totalPendiente.toFixed(2)}</b> (no se cobrará en este ticket).`;
        } else {
          alertPendientes.style.display = 'none';
        }
      }

      // 8. Botones de acción
      const btnEnviarCocina = document.getElementById('btnEnviarCocina');
      const btnPrecuenta = document.getElementById('btnPrecuenta');
      const btnCerrarBottom = document.getElementById('btnCerrarModalBottom');

      if (sillaNum === null) {
        // EN PANORAMA GENERAL (Centro de Mesa): Vista informativa de supervisión
        if (btnCobrarDirecto) btnCobrarDirecto.style.display = 'none';
        if (btnEnviarCocina) btnEnviarCocina.style.display = 'none';
        if (btnMover) btnMover.style.display = 'none';
        if (btnPrecuenta) btnPrecuenta.style.display = 'none';
        if (btnLiberar) {
          btnLiberar.style.display = (sillasOcupadas.length > 0) ? 'inline-flex' : 'none';
          btnLiberar.onclick = function () { window.liberarMesaCompleta(mesaId); };
          btnLiberar.innerHTML = '<i class="fa-solid fa-broom"></i> Desocupar Toda la Mesa';
        }
        if (btnCerrarBottom) {
          btnCerrarBottom.style.flex = '1';
          btnCerrarBottom.innerHTML = '<i class="fa-solid fa-arrow-left"></i> Regresar al Croquis de Mesas';
        }
      } else {
        // EN COBRO POR COMENSAL:
        if (btnPrecuenta) btnPrecuenta.style.display = 'flex';
        if (btnLiberar) {
          btnLiberar.style.display = 'inline-flex';
          btnLiberar.onclick = function () { window.liberarSillaActual(); };
          btnLiberar.innerHTML = '<i class="fa-solid fa-broom"></i> Desocupar Silla';
        }
        if (btnCerrarBottom) {
          btnCerrarBottom.style.flex = '1';
          btnCerrarBottom.innerHTML = '<i class="fa-solid fa-arrow-left"></i> Regresar a Mesas';
        }

        if (btnCobrarDirecto) {
          btnCobrarDirecto.style.display = (totalNeto > 0) ? 'flex' : 'none';
          var labelCobro = (seleccionadas.length > 1) ? `Sillas ${seleccionadas.join(', ')}` : `Silla ${sillaNum}`;
          btnCobrarDirecto.innerHTML = `<i class="fa-solid fa-credit-card"></i> Cobrar ${labelCobro} (<span id="txtBtnCobrarMonto">$${granTotal.toFixed(2)}</span>)`;
        }

        // Control dinámico de Enviar a Cocina (KDS)
        if (btnEnviarCocina) {
          btnEnviarCocina.style.display = 'flex';
          var cuentaActual = window.palapaState.cuentas[`${mesaId}-${sillaNum}`] || { items: [] };
          var pendientes = (cuentaActual.items || []).filter(function (i) { return !i.enviadoCocina; });

          if (pendientes.length > 0) {
            btnEnviarCocina.disabled = false;
            btnEnviarCocina.style.opacity = '1';
            btnEnviarCocina.style.cursor = 'pointer';
            btnEnviarCocina.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
            btnEnviarCocina.style.color = '#0f172a';
            btnEnviarCocina.innerHTML = `<i class="fa-solid fa-fire"></i> Enviar Cocina (${pendientes.length} nuevo${pendientes.length > 1 ? 's' : ''})`;
          } else {
            btnEnviarCocina.disabled = true;
            btnEnviarCocina.style.opacity = '0.45';
            btnEnviarCocina.style.cursor = 'not-allowed';
            btnEnviarCocina.style.background = '#1e293b';
            btnEnviarCocina.style.color = '#64748b';
            btnEnviarCocina.innerHTML = `<i class="fa-solid fa-check-double"></i> Todo en Cocina`;
          }
        }

        if (btnMover) btnMover.style.display = (seleccionadas.length === 1) ? 'flex' : 'none';
        if (btnLiberar) btnLiberar.style.display = (seleccionadas.length === 1) ? 'flex' : 'none';
      }

      if (modal) {
        modal.classList.add('show');
        modal.style.setProperty('display', 'flex', 'important');
      }
    }

    window.toggleSillaAdicional = function (sillaNum) {
      var titular = window.palapaState.sillaSeleccionadaNum;
      // Si la silla es la titular, NUNCA se deselecciona ni se quita de su propia comanda
      if (titular !== null && sillaNum === titular) {
        return;
      }

      var sel = window.palapaState.sillasSeleccionadasCobro || [];
      var idx = sel.indexOf(sillaNum);
      if (idx === -1) {
        sel.push(sillaNum);
      } else {
        sel.splice(idx, 1);
      }

      // Asegurar que la silla titular siempre permanezca en la lista
      if (titular !== null && sel.indexOf(titular) === -1) {
        sel.unshift(titular);
      }

      window.palapaState.sillasSeleccionadasCobro = sel;
      abrirModalComandaActual();
    };

    window.comandaToggleTodaLaMesa = function () {
      var mesaId = window.palapaState.mesaSeleccionadaId;
      var allChairs = [];
      for (var s = 1; s <= 10; s++) {
        if (window.palapaState.cuentas[`${mesaId}-${s}`]) {
          allChairs.push(s);
        }
      }
      window.palapaState.sillasSeleccionadasCobro = allChairs;
      abrirModalComandaActual();
    };

    window.comandaSoloEstaSilla = function () {
      var current = window.palapaState.sillaSeleccionadaNum || 1;
      window.palapaState.sillasSeleccionadasCobro = [current];
      abrirModalComandaActual();
    };

    window.cobrarSeleccionadasDesdeComanda = function () {
      var mesaId = window.palapaState.mesaSeleccionadaId;
      var sillaNum = window.palapaState.sillaSeleccionadaNum;
      var sel = window.palapaState.sillasSeleccionadasCobro || [];

      if (sillaNum === null) {
        var allChairs = [];
        for (var s = 0; s <= 10; s++) {
          if (window.palapaState.cuentas[`${mesaId}-${s}`]) {
            allChairs.push(s);
          }
        }
        if (allChairs.length === 0) {
          showDragToast('⚠ No hay comensales con consumo en esta mesa.', 'warn');
          return;
        }
        window.abrirModalPasarelaCobro(mesaId, allChairs);
        return;
      }

      if (sel.length === 0) {
        sel = [sillaNum];
      }

      window.abrirModalPasarelaCobro(mesaId, sel);
    };

    // ══════════════════════ PASARELA DE COBRO Y LIQUIDACIÓN MULTI-MÉTODO ══════════════════════
    var pasarelaState = {
      mesaId: null,
      sillas: [],
      consumoNeto: 0,
      iva: 0,
      subtotalConIva: 0,
      tipPct: 10,
      tipMonto: 0,
      tipDestino: 'INCLUIDA_TARJETA',
      metodoSeleccionado: 'MERCADOPAGO',
      granTotal: 0,
      mixtoRows: [],
      customTicket: null
    };

    window.abrirModalPasarelaCobro = function (mesaId, sillasArray, customTicket) {
      if (!mesaId) mesaId = window.palapaState.mesaSeleccionadaId;
      if (!sillasArray || sillasArray.length === 0) {
        sillasArray = (window.palapaState.sillasSeleccionadasCobro && window.palapaState.sillasSeleccionadasCobro.length > 0)
          ? window.palapaState.sillasSeleccionadasCobro.slice()
          : (window.palapaState.sillaSeleccionadaNum !== null ? [window.palapaState.sillaSeleccionadaNum] : []);
      }

      if (sillasArray.length === 0 && !customTicket) {
        for (var s = 0; s <= 10; s++) {
          if (window.palapaState.cuentas[mesaId + '-' + s]) {
            sillasArray.push(s);
          }
        }
      }

      var totalVenta = 0;
      var ticketItems = [];

      if (customTicket) {
        totalVenta = customTicket.total || 0;
        ticketItems = customTicket.items || [];
        pasarelaState.customTicket = customTicket;
      } else {
        pasarelaState.customTicket = null;
        sillasArray.forEach(function (s) {
          var c = window.palapaState.cuentas[mesaId + '-' + s];
          if (c && c.items) {
            c.items.forEach(function (it) {
              if (!it.pagado) {
                totalVenta += (it.precio || 0) * (it.cantidad || 1);
                ticketItems.push({
                  sillaNum: s,
                  nombre: it.nombre,
                  cantidad: it.cantidad || 1,
                  precio: it.precio || 0,
                  notas: it.notas || '',
                  es_cuenta_mesa: (s === 0 || it.es_cuenta_mesa)
                });
              }
            });
          }
        });
      }

      if (totalVenta <= 0 && (!ticketItems || ticketItems.length === 0)) {
        showDragToast('⚠ No hay consumo pendiente para cobrar.', 'warn');
        return;
      }

      var subtotalBase = totalVenta / 1.16;
      var iva = totalVenta - subtotalBase;
      var subtotalConIva = totalVenta;

      pasarelaState.mesaId = mesaId;
      pasarelaState.sillas = sillasArray;
      pasarelaState.consumoNeto = totalVenta;
      pasarelaState.subtotalBase = subtotalBase;
      pasarelaState.iva = iva;
      pasarelaState.subtotalConIva = subtotalConIva;
      pasarelaState.tipPct = 10;
      pasarelaState.tipDestino = 'INCLUIDA_TARJETA';
      pasarelaState.metodoSeleccionado = 'MERCADOPAGO';
      pasarelaState.mixtoRows = [
        { id: 'mx_1', metodo: 'CASH', monto: Math.round(subtotalConIva / 2) },
        { id: 'mx_2', metodo: 'TERMINAL_SANTANDER', monto: Number((subtotalConIva - Math.round(subtotalConIva / 2)).toFixed(2)) }
      ];

      // Update Subtitle
      var lblSub = document.getElementById('lblPasarelaSubtitulo');
      if (lblSub) {
        if (customTicket && customTicket.titulo) {
          lblSub.innerText = customTicket.titulo;
        } else {
          var sillasStr = sillasArray.map(function (s) { return s === 0 ? 'Cuenta de Mesa' : ('Silla ' + s); }).join(', ');
          lblSub.innerText = `Mesa ${mesaId} • ${sillasStr}`;
        }
      }

      // Renderizar Desglose del Ticket de Consumo
      var itemsListWrap = document.getElementById('pasarelaTicketItemsList');
      var itemsCountEl = document.getElementById('pasarelaTicketItemsCount');
      if (itemsListWrap) {
        itemsListWrap.innerHTML = '';
        var totalItemsCount = 0;
        ticketItems.forEach(function (it) {
          totalItemsCount += (it.cantidad || 1);
          var itSub = (it.precio || 0) * (it.cantidad || 1);
          var row = document.createElement('div');
          row.style.cssText = 'display: flex !important; justify-content: space-between !important; align-items: center !important; padding: 2px 4px !important; border-bottom: 1px dashed #1e293b !important; color: #e2e8f0 !important; font-size: 11px !important;';
          var originTag = it.es_cuenta_mesa ? '⭐ Mesa:' : (it.sillaNum !== undefined ? (it.sillaNum === 0 ? '⭐ Mesa:' : `Silla ${it.sillaNum}:`) : '');
          row.innerHTML = `
            <div style="flex: 1; padding-right: 6px;">
              <span style="font-weight: 800; color: #38bdf8;">${originTag}</span>
              <span style="color: #ffffff;">${it.cantidad}x ${it.nombre}</span>
              ${it.notas ? `<span style="font-size: 9px; color: #94a3b8; font-style: italic;">(${it.notas})</span>` : ''}
            </div>
            <span style="font-weight: 900; color: #34d399;">$${itSub.toFixed(2)}</span>
          `;
          itemsListWrap.appendChild(row);
        });
        if (itemsCountEl) itemsCountEl.innerText = `${totalItemsCount} producto${totalItemsCount !== 1 ? 's' : ''}`;
      }

      // Update Amounts
      var elConsumo = document.getElementById('pasarelaMontoConsumo');
      var elIva = document.getElementById('pasarelaMontoIva');
      var elSubIva = document.getElementById('pasarelaMontoSubtotalIva');
      if (elConsumo) elConsumo.innerText = `$${subtotalBase.toFixed(2)}`;
      if (elIva) elIva.innerText = `$${iva.toFixed(2)}`;
      if (elSubIva) elSubIva.innerText = `$${subtotalConIva.toFixed(2)}`;

      var lblQr = document.getElementById('lblQrDinamicoCodigo');
      if (lblQr) {
        lblQr.innerText = `QR: #PV-0${mesaId}${sillasArray[0] || '1'}`;
      }

      window.setPasarelaTipPct(10);
      window.selectPasarelaMetodo('MERCADOPAGO');

      // Cerrar otros modales
      cerrarModalComanda();
      if (typeof window.cerrarPrecuenta === 'function') window.cerrarPrecuenta();

      var modalP = document.getElementById('modalPasarelaCobroBackdrop');
      if (modalP) {
        modalP.classList.add('show');
        modalP.style.setProperty('display', 'flex', 'important');
      }
    };

    window.selectPasarelaMetodo = function (metodo) {
      pasarelaState.metodoSeleccionado = metodo;

      var tabs = [
        { id: 'tabMetodoMercadoPago', m: 'MERCADOPAGO', pane: 'paneMetodoMercadoPago' },
        { id: 'tabMetodoSantander', m: 'TERMINAL_SANTANDER', pane: 'paneMetodoSantander' },
        { id: 'tabMetodoCash', m: 'CASH', pane: 'paneMetodoCash' },
        { id: 'tabMetodoQr', m: 'QR_LINK', pane: 'paneMetodoQr' },
        { id: 'tabMetodoMixto', m: 'MIXTO', pane: 'paneMetodoMixto' }
      ];

      tabs.forEach(function (t) {
        var tabBtn = document.getElementById(t.id);
        var pane = document.getElementById(t.pane);
        var isActive = (t.m === metodo);

        if (tabBtn) {
          if (isActive) {
            tabBtn.style.background = 'rgba(56, 189, 248, 0.2)';
            tabBtn.style.color = '#38bdf8';
            tabBtn.style.border = '1px solid #38bdf8';
          } else {
            tabBtn.style.background = '#0f172a';
            tabBtn.style.color = '#94a3b8';
            tabBtn.style.border = '1px solid #1e293b';
          }
        }

        if (pane) {
          pane.style.setProperty('display', isActive ? 'block' : 'none', 'important');
        }
      });

      window.updatePasarelaBalance();
    };

    window.updatePasarelaBalance = function () {
      var subtotal = pasarelaState.subtotalConIva;
      var tip = 0;

      if (pasarelaState.tipPct === 'libre') {
        var inpLibre = document.getElementById('inputTipMontoLibre');
        tip = inpLibre ? (parseFloat(inpLibre.value) || 0) : 0;
      } else {
        tip = (subtotal * pasarelaState.tipPct) / 100;
      }

      pasarelaState.tipMonto = tip;
      var granTotal = Number((subtotal + tip).toFixed(2));
      pasarelaState.granTotal = granTotal;

      // Update Labels
      var elSubtotal = document.getElementById('pasarelaResumenSubtotal');
      var elPropina = document.getElementById('pasarelaResumenPropina');
      var elGranTotal = document.getElementById('pasarelaResumenGranTotal');
      var elBtnMonto = document.getElementById('pasarelaBtnCobrarMonto');

      if (elSubtotal) elSubtotal.innerText = `$${subtotal.toFixed(2)}`;
      if (elPropina) elPropina.innerText = `$${tip.toFixed(2)}`;
      if (elGranTotal) elGranTotal.innerText = `$${granTotal.toFixed(2)}`;
      if (elBtnMonto) elBtnMonto.innerText = `$${granTotal.toFixed(2)}`;

      // Cash calculator
      if (pasarelaState.metodoSeleccionado === 'CASH') {
        var inpCash = document.getElementById('inputCashRecibido');
        var recibido = inpCash ? (parseFloat(inpCash.value) || 0) : 0;
        var cambio = Math.max(0, recibido - granTotal);
        var elCambio = document.getElementById('pasarelaCashCambio');
        if (elCambio) elCambio.innerText = `$${cambio.toFixed(2)}`;
      }

      // Balance status badge & Mixto tracker
      var elBadge = document.getElementById('pasarelaBalanceStatusBadge');
      var btnConfirmar = document.getElementById('btnPasarelaConfirmarCobro');

      if (pasarelaState.metodoSeleccionado === 'MIXTO') {
        var sumaMixto = pasarelaState.mixtoRows.reduce(function (sum, r) { return sum + (r.monto || 0); }, 0);
        var cubiertoEl = document.getElementById('pasarelaMixtoCubierto');
        var restanteEl = document.getElementById('pasarelaMixtoRestante');
        if (cubiertoEl) cubiertoEl.innerText = `$${sumaMixto.toFixed(2)}`;
        if (restanteEl) restanteEl.innerText = `$${Math.max(0, granTotal - sumaMixto).toFixed(2)}`;

        var diff = Math.abs(sumaMixto - granTotal);
        if (diff < 0.05) {
          if (elBadge) {
            elBadge.innerText = '✓ BALANCEADO (100%)';
            elBadge.style.background = 'rgba(16,185,129,0.2)';
            elBadge.style.color = '#34d399';
            elBadge.style.border = '1px solid rgba(16,185,129,0.4)';
          }
          if (btnConfirmar) { btnConfirmar.disabled = false; btnConfirmar.style.opacity = '1'; }
        } else if (sumaMixto < granTotal) {
          if (elBadge) {
            elBadge.innerText = `FALTAN $${(granTotal - sumaMixto).toFixed(2)}`;
            elBadge.style.background = 'rgba(239,68,68,0.2)';
            elBadge.style.color = '#f87171';
            elBadge.style.border = '1px solid rgba(239,68,68,0.4)';
          }
          if (btnConfirmar) { btnConfirmar.disabled = true; btnConfirmar.style.opacity = '0.5'; }
        } else {
          if (elBadge) {
            elBadge.innerText = `EXCEDE POR $${(sumaMixto - granTotal).toFixed(2)}`;
            elBadge.style.background = 'rgba(245,158,11,0.2)';
            elBadge.style.color = '#fbbf24';
            elBadge.style.border = '1px solid rgba(245,158,11,0.4)';
          }
          if (btnConfirmar) { btnConfirmar.disabled = true; btnConfirmar.style.opacity = '0.5'; }
        }
      } else {
        if (elBadge) {
          elBadge.innerText = 'LISTO PARA COBRAR';
          elBadge.style.background = 'rgba(16,185,129,0.2)';
          elBadge.style.color = '#34d399';
          elBadge.style.border = '1px solid rgba(16,185,129,0.4)';
        }
        if (btnConfirmar) { btnConfirmar.disabled = false; btnConfirmar.style.opacity = '1'; }
      }
    };

    window.setCashBillete = function (billete) {
      var inp = document.getElementById('inputCashRecibido');
      if (inp) {
        inp.value = billete;
        window.updatePasarelaBalance();
      }
    };

    var pasarelaMixtoRowIdCounter = 10;
    window.addPasarelaPagoRow = function () {
      var rowId = 'mx_' + (++pasarelaMixtoRowIdCounter);
      var sumaPrevias = pasarelaState.mixtoRows.reduce(function (sum, r) { return sum + (r.monto || 0); }, 0);
      var remanente = Math.max(0, pasarelaState.granTotal - sumaPrevias);

      pasarelaState.mixtoRows.push({ id: rowId, metodo: 'TERMINAL_SANTANDER', monto: Number(remanente.toFixed(2)) });
      window.renderPasarelaMixtoRows();
      window.updatePasarelaBalance();
    };

    window.removePasarelaPagoRow = function (rowId) {
      pasarelaState.mixtoRows = pasarelaState.mixtoRows.filter(function (r) { return r.id !== rowId; });
      window.renderPasarelaMixtoRows();
      window.updatePasarelaBalance();
    };

    window.autoCompletarRemanenteMixto = function () {
      var granTotal = pasarelaState.granTotal;
      var rows = pasarelaState.mixtoRows;
      if (!rows || rows.length === 0) return;

      if (rows.length === 1) {
        rows[0].monto = Number(granTotal.toFixed(2));
      } else {
        var sumaPrevias = 0;
        for (var i = 0; i < rows.length - 1; i++) {
          sumaPrevias += (rows[i].monto || 0);
        }
        var remanente = Math.max(0, granTotal - sumaPrevias);
        rows[rows.length - 1].monto = Number(remanente.toFixed(2));
      }
      window.renderPasarelaMixtoRows();
      window.updatePasarelaBalance();
    };

    window.renderPasarelaMixtoRows = function () {
      var wrap = document.getElementById('pasarelaMixtoRows');
      if (!wrap) return;
      wrap.innerHTML = '';

      pasarelaState.mixtoRows.forEach(function (r, idx) {
        var div = document.createElement('div');
        div.style.cssText = 'display: flex !important; gap: 6px !important; align-items: center !important; background: #0f172a !important; padding: 6px 8px !important; border-radius: 8px !important; border: 1px solid #1e293b !important; font-size: 11px !important;';

        div.innerHTML = `
          <span style="font-weight: bold; color: #94a3b8; width: 16px;">${idx + 1}.</span>
          <select onchange="window.onPasarelaMixtoRowChange('${r.id}', 'metodo', this.value)" style="flex: 1.2; padding: 6px; background: #020617; color: #ffffff; border: 1px solid #334155; border-radius: 6px; font-size: 11px; font-weight: bold;">
            <option value="MERCADOPAGO" ${r.metodo === 'MERCADOPAGO' ? 'selected' : ''}>Terminal MP</option>
            <option value="TERMINAL_SANTANDER" ${r.metodo === 'TERMINAL_SANTANDER' ? 'selected' : ''}>Santander Manual</option>
            <option value="CASH" ${r.metodo === 'CASH' ? 'selected' : ''}>Efectivo</option>
            <option value="QR_LINK" ${r.metodo === 'QR_LINK' ? 'selected' : ''}>QR / Link</option>
          </select>
          <input type="number" step="0.5" min="0" value="${r.monto || 0}" oninput="window.onPasarelaMixtoRowChange('${r.id}', 'monto', parseFloat(this.value) || 0)" style="flex: 1; padding: 6px; background: #020617; color: #34d399; border: 1px solid #334155; border-radius: 6px; font-size: 12px; font-weight: 900; text-align: right;">
          <button type="button" onclick="window.removePasarelaPagoRow('${r.id}')" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; border-radius: 6px; padding: 4px 8px; font-weight: bold; cursor: pointer;">✕</button>
        `;
        wrap.appendChild(div);
      });
    };

    window.onPasarelaMixtoRowChange = function (rowId, field, val) {
      var r = pasarelaState.mixtoRows.find(function (item) { return item.id === rowId; });
      if (r) {
        r[field] = val;
        window.updatePasarelaBalance();
      }
    };

    window.ejecutarLiquidacionPasarela = function () {
      var mesaId = pasarelaState.mesaId;
      var sillas = pasarelaState.sillas;
      var granTotal = pasarelaState.granTotal;
      var metodo = pasarelaState.metodoSeleccionado;

      if (!mesaId || !sillas || sillas.length === 0) return;

      var metodoLabels = {
        'MERCADOPAGO': 'Terminal MP (Point Smart)',
        'TERMINAL_SANTANDER': 'Santander Manual',
        'CASH': 'Efectivo',
        'QR_LINK': 'QR / Link Digital',
        'MIXTO': 'Pago Mixto'
      };
      var metodoNombre = metodoLabels[metodo] || metodo;
      var sillasStr = sillas.map(function (s) { return 'Silla ' + s; }).join(', ');

      // Marcar sillas como pagadas (permanecen en la mesa en sobremesa)
      var nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      sillas.forEach(function (sNum) {
        var k = mesaId + '-' + sNum;
        if (window.palapaState.cuentas[k]) {
          window.palapaState.cuentas[k].estado = 'pagada';
          window.palapaState.cuentas[k].pagado = true;
          window.palapaState.cuentas[k].horaPago = nowStr;
          window.palapaState.cuentas[k].metodoPago = metodoNombre;
          window.palapaState.cuentas[k].montoPagado = granTotal;
          if (window.palapaState.cuentas[k].items) {
            window.palapaState.cuentas[k].items.forEach(function (it) { it.pagado = true; });
          }
        }
      });

      window.palapaState.sillasSeleccionadasCobro = [];
      saveStateToStorage();
      renderStateUI();
      window.cerrarModalPasarelaCobro();

      showDragToast(`💳 ¡Liquidación exitosa de Mesa ${mesaId} (${sillasStr}) por $${granTotal.toFixed(2)} (${metodoNombre})! Cuenta saldada. Comensales continúan en sobremesa.`, 'ok');
    };

    window.enviarCocinaActual = function () {
      var mesaId = window.palapaState.mesaSeleccionadaId;
      var sillaNum = window.palapaState.sillaSeleccionadaNum;
      if (sillaNum === null) return;
      var key = mesaId + '-' + sillaNum;
      var cuenta = window.palapaState.cuentas[key];
      if (!cuenta || !cuenta.items || cuenta.items.length === 0) {
        showDragToast('ℹ Agrega al menos un platillo o bebida antes de enviar a cocina.', 'warn');
        return;
      }

      var pendientes = cuenta.items.filter(function (i) { return !i.enviadoCocina; });
      if (pendientes.length === 0) {
        showDragToast('ℹ Todos los productos de esta comanda ya fueron enviados a Cocina (KDS).', 'info');
        return;
      }

      var nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      pendientes.forEach(function (i) {
        i.enviadoCocina = true;
        if (!i.hora) i.hora = nowStr;
      });

      saveStateToStorage();
      renderStateUI();
      abrirModalComandaActual();
      showDragToast(`🔥 ¡Comanda de Silla ${sillaNum} (${pendientes.length} producto${pendientes.length > 1 ? 's' : ''}) enviada a Cocina (KDS)!`, 'ok');
    };

    window.seleccionarSillaDesdeMesa = function (sillaNum) {
      window.palapaState.sillaSeleccionadaNum = sillaNum;
      window.palapaState.sillasSeleccionadasCobro = [sillaNum];
      renderStateUI();
      abrirModalComandaActual();
    };

    window.verTodaLaMesaEnColumnas = function () {
      window.palapaState.sillaSeleccionadaNum = null;
      window.palapaState.sillasSeleccionadasCobro = [];
      renderStateUI();
      abrirModalComandaActual();
    };

    var _precuentaMesaId = 2;
    var _precuentaModo = 'individual'; // 'individual' | 'anfitrion' | 'split_comida' | 'mesa_completa'
    var _precuentaSillasSeleccionadas = [];
    var _anfitrionSillaNum = 1;

    window.setPrecuentaModo = function (modo) {
      _precuentaModo = modo;

      var tabs = [
        { id: 'btnTabPrecuenta_indiv', m: 'individual' },
        { id: 'btnTabPrecuenta_anfitrion', m: 'anfitrion' },
        { id: 'btnTabPrecuenta_split', m: 'split_comida' },
        { id: 'btnTabPrecuenta_mesa', m: 'mesa_completa' }
      ];

      tabs.forEach(function (t) {
        var el = document.getElementById(t.id);
        if (el) {
          if (t.m === modo) {
            el.style.background = '#059669';
            el.style.color = '#ffffff';
          } else {
            el.style.background = '#1e293b';
            el.style.color = '#94a3b8';
          }
        }
      });

      recalcularPrecuenta();
    };

    window.setAnfitrionSilla = function (sNum) {
      _anfitrionSillaNum = parseInt(sNum);
      recalcularPrecuenta();
    };

    window.trasladarCuentaMesaASilla = function (targetSillaNum) {
      var mesaId = _precuentaMesaId || window.palapaState.mesaSeleccionadaId || 2;
      var mesaKey = `${mesaId}-0`;
      var targetKey = `${mesaId}-${targetSillaNum}`;

      var ctaMesa = window.palapaState.cuentas[mesaKey];
      if (!ctaMesa || !ctaMesa.items || ctaMesa.items.length === 0) {
        showDragToast('ℹ No hay platillos en la Cuenta de Mesa para trasladar.', 'warn');
        return;
      }

      if (!window.palapaState.cuentas[targetKey]) {
        window.palapaState.cuentas[targetKey] = {
          estado: 'ocupada',
          qrId: `PV-0${mesaId}${targetSillaNum}`,
          comensalNombre: `Comensal Silla ${targetSillaNum}`,
          items: [],
          historialUbicaciones: [{ mesaId: mesaId, sillaNum: targetSillaNum, hora: (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]
        };
      }

      var itemsTrasladados = 0;
      ctaMesa.items.forEach(function (it) {
        if (!it.pagado) {
          itemsTrasladados++;
          it.notas = (it.notas ? it.notas + ' • ' : '') + 'Trasladado de Cuenta de Mesa';
          it.sillaNum = parseInt(targetSillaNum);
          it.es_cuenta_mesa = false;
          window.palapaState.cuentas[targetKey].items.push(it);
        }
      });

      // Limpiar items de mesa no pagados
      ctaMesa.items = ctaMesa.items.filter(function (it) { return it.pagado; });
      if (ctaMesa.items.length === 0) {
        ctaMesa.estado = 'disponible';
      }

      saveStateToStorage();
      renderStateUI();
      recalcularPrecuenta();

      const modalPop = document.getElementById('modalPopMenuMesaBackdrop');
      if (modalPop && modalPop.style.display === 'flex') {
        window.abrirPopMenuMesa(mesaId);
      }

      showDragToast(`✨ ¡${itemsTrasladados} platillo(s) al centro trasladados con éxito a la Silla ${targetSillaNum}!`, 'ok');
    };

    function abrirPrecuenta() {
      const mesaId = window.palapaState.mesaSeleccionadaId || 2;
      const sillaNum = window.palapaState.sillaSeleccionadaNum;
      const modalP = document.getElementById('modalPrecuentaBackdrop');
      const fechaEl = document.getElementById('precuentaFecha');

      if (!modalP) return;
      _precuentaMesaId = mesaId;

      if (fechaEl) fechaEl.innerText = 'Fecha: ' + (new Date()).toLocaleDateString() + ' ' + (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      // Encontrar todas las sillas con consumos de esta mesa
      var sillasConConsumo = [];
      for (var s = 0; s <= 10; s++) {
        var k = mesaId + '-' + s;
        var c = window.palapaState.cuentas[k];
        if (c && (c.estado === 'ocupada' || (c.items && c.items.length > 0))) {
          var tot = 0;
          if (c.items) c.items.forEach(function (it) { if (!it.pagado) tot += (it.precio || 0) * (it.cantidad || 1); });
          if (tot > 0 || (c.items && c.items.length > 0)) {
            sillasConConsumo.push(s);
          }
        }
      }

      if (sillasConConsumo.length > 0) {
        _precuentaSillasSeleccionadas = sillasConConsumo.slice();
        var primerComensal = sillasConConsumo.find(function (s) { return s > 0; }) || 1;
        _anfitrionSillaNum = primerComensal;
      } else {
        _precuentaSillasSeleccionadas = [1];
        _anfitrionSillaNum = 1;
      }

      window.setPrecuentaModo('individual');

      modalP.classList.add('show');
      modalP.style.setProperty('display', 'flex', 'important');
    }

    window.togglePrecuentaSilla = function (sillaNum) {
      var idx = _precuentaSillasSeleccionadas.indexOf(sillaNum);
      if (idx === -1) {
        _precuentaSillasSeleccionadas.push(sillaNum);
      } else {
        _precuentaSillasSeleccionadas.splice(idx, 1);
      }
      recalcularPrecuenta();
    };

    window.precuentaSelectPreset = function (preset) {
      var mesaId = _precuentaMesaId;
      if (preset === 'solo_esta') {
        var sSel = window.palapaState.sillaSeleccionadaNum !== null ? window.palapaState.sillaSeleccionadaNum : 1;
        _precuentaSillasSeleccionadas = [sSel];
      } else if (preset === 'todas') {
        _precuentaSillasSeleccionadas = [];
        for (var s = 0; s <= 10; s++) {
          if (window.palapaState.cuentas[mesaId + '-' + s]) {
            _precuentaSillasSeleccionadas.push(s);
          }
        }
      }
      recalcularPrecuenta();
    };

    function recalcularPrecuenta() {
      const mesaId = _precuentaMesaId;
      const controlsBox = document.getElementById('precuentaModoControlsBox');
      const listContainer = document.getElementById('precuentaTramosList');
      const subtotalEl = document.getElementById('precuentaSubtotal');
      const ivaEl = document.getElementById('precuentaIva');
      const propinaEl = document.getElementById('precuentaPropina');
      const totalEl = document.getElementById('precuentaTotal');
      const headerTag = document.getElementById('precuentaHeaderTag');
      const btnCobrarMonto = document.getElementById('btnCobrarMonto');

      if (!listContainer) return;
      listContainer.innerHTML = '';
      if (controlsBox) controlsBox.innerHTML = '';

      // 1. Recolectar datos de toda la mesa
      var mesaCuenta = window.palapaState.cuentas[`${mesaId}-0`];
      var mesaItems = (mesaCuenta && mesaCuenta.items) ? mesaCuenta.items.filter(function (it) { return !it.pagado; }) : [];
      var mesaTotalNeto = mesaItems.reduce(function (sum, it) { return sum + (it.precio || 0) * (it.cantidad || 1); }, 0);

      var sillasActivas = [];
      var totalAlimentosMesa = mesaTotalNeto;
      var totalBebidasMesa = 0;
      var totalGranMesa = mesaTotalNeto;

      for (var s = 1; s <= 10; s++) {
        var k = `${mesaId}-${s}`;
        var c = window.palapaState.cuentas[k];
        if (c && c.items && c.items.length > 0) {
          var unpaids = c.items.filter(function (it) { return !it.pagado; });
          if (unpaids.length > 0) {
            var alimSub = 0;
            var bebSub = 0;
            unpaids.forEach(function (it) {
              var itSub = (it.precio || 0) * (it.cantidad || 1);
              if (it.tipo_consumo === 'comida' || it.es_cuenta_mesa) {
                alimSub += itSub;
              } else {
                bebSub += itSub;
              }
            });
            sillasActivas.push({
              sillaNum: s,
              cuenta: c,
              items: unpaids,
              subtotalAlimentos: alimSub,
              subtotalBebidas: bebSub,
              subtotalTotal: alimSub + bebSub
            });
            totalAlimentosMesa += alimSub;
            totalBebidasMesa += bebSub;
            totalGranMesa += (alimSub + bebSub);
          }
        }
      }

      // ═══════════════════════════════════════════════════════════════════
      // MODALIDAD 1: CUENTAS INDIVIDUALES (POR SILLA & CUENTA DE MESA)
      // ═══════════════════════════════════════════════════════════════════
      if (_precuentaModo === 'individual') {
        if (headerTag) headerTag.innerHTML = `MESA ${mesaId} • ESCENARIO 1: CUENTAS INDIVIDUALES & CENTRO`;

        if (controlsBox) {
          var optionsHtml = sillasActivas.map(function (sa) {
            return `<option value="${sa.sillaNum}">Silla ${sa.sillaNum} (${sa.cuenta.comensalNombre || 'Comensal'})</option>`;
          }).join('');

          controlsBox.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 6px;">
              ${mesaItems.length > 0 ? `
                <div style="background: rgba(234,179,8,0.15); border: 1px solid #ca8a04; border-radius: 8px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center;">
                  <div>
                    <span style="font-weight: 900; color: #b45309; font-size: 11px;">⭐ Cuenta de MESA: $${mesaTotalNeto.toFixed(2)}</span>
                    <span style="display: block; font-size: 9px; color: #64748b;">${mesaItems.length} platillo(s) al centro</span>
                  </div>
                  <div style="display: flex; gap: 4px; align-items: center;">
                    <select id="selTrasladarMesaSilla" style="font-size: 10px; padding: 3px; border-radius: 4px; border: 1px solid #cbd5e1; background: #ffffff;">
                      ${optionsHtml || '<option value="1">Silla 1</option>'}
                    </select>
                    <button type="button" onclick="window.trasladarCuentaMesaASilla(document.getElementById('selTrasladarMesaSilla').value)"
                      style="padding: 3px 8px; font-size: 9px; font-weight: 800; background: #d97706; color: #ffffff; border: none; border-radius: 4px; cursor: pointer;">
                      ➡️ Trasladar
                    </button>
                  </div>
                </div>
              ` : `
                <div style="font-size: 10px; color: #059669; font-weight: 800;"><i class="fa-solid fa-circle-check"></i> Sin platillos al centro pendientes (o ya fueron trasladados).</div>
              `}
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 2px;">
                <span style="font-weight: 800; font-size: 10px; color: #334155;">Seleccionar Cuentas a Incluir en Ticket:</span>
                <div style="display: flex; gap: 4px;">
                  <button type="button" onclick="window.precuentaSelectPreset('solo_esta')" style="padding: 2px 6px; font-size: 9px; background: #e2e8f0; border: none; border-radius: 4px; cursor: pointer;">Solo Actual</button>
                  <button type="button" onclick="window.precuentaSelectPreset('todas')" style="padding: 2px 6px; font-size: 9px; background: #059669; color: #ffffff; border: none; border-radius: 4px; cursor: pointer;">Todas</button>
                </div>
              </div>
            </div>
          `;
        }

        var totalSeleccion = 0;

        // Si Cuenta de Mesa tiene items y está en selección
        if (mesaItems.length > 0 && _precuentaSillasSeleccionadas.indexOf(0) !== -1) {
          totalSeleccion += mesaTotalNeto;
          var mb = document.createElement('div');
          mb.style.cssText = 'background: rgba(234, 179, 8, 0.1) !important; border: 1px solid #eab308 !important; border-radius: 8px !important; padding: 6px 8px !important; margin-bottom: 4px !important;';
          mb.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 900; color: #b45309; font-size: 11px;">
              <span>⭐ CUENTA DE MESA (AL CENTRO)</span>
              <span>$${mesaTotalNeto.toFixed(2)}</span>
            </div>
            <div style="margin-top: 4px; font-size: 10px; color: #334155;">
              ${mesaItems.map(function (i) { return `<div>• ${i.cantidad}x ${i.nombre} <b style="float: right;">$${((i.precio || 0) * (i.cantidad || 1)).toFixed(2)}</b></div>`; }).join('')}
            </div>
            <div style="text-align: right; margin-top: 4px;">
              <button type="button" onclick="window.abrirModalPasarelaCobro(${mesaId}, [0])"
                style="padding: 3px 8px; font-size: 10px; font-weight: 800; background: #d97706; color: #ffffff; border: none; border-radius: 4px; cursor: pointer;">
                💳 Cobrar Cuenta de Mesa
              </button>
            </div>
          `;
          listContainer.appendChild(mb);
        }

        // Renderizar cada silla seleccionada
        sillasActivas.forEach(function (sa) {
          if (_precuentaSillasSeleccionadas.indexOf(sa.sillaNum) !== -1) {
            totalSeleccion += sa.subtotalTotal;
            var sb = document.createElement('div');
            sb.style.cssText = 'border: 1px solid #cbd5e1 !important; border-radius: 8px !important; padding: 6px 8px !important; background: #ffffff !important;';
            sb.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 900; color: #047857; font-size: 11px; border-bottom: 1px dashed #cbd5e1; padding-bottom: 3px;">
                <span>SILLA ${sa.sillaNum} • ${(sa.cuenta.comensalNombre || 'Comensal').toUpperCase()}</span>
                <span style="color: #059669; font-size: 12px;">$${sa.subtotalTotal.toFixed(2)}</span>
              </div>
              <div style="margin-top: 4px; font-size: 10px; color: #334155; display: flex; flex-direction: column; gap: 2px;">
                ${sa.items.map(function (i) {
                  var badge = (i.tipo_consumo === 'comida' || i.es_cuenta_mesa) ? '🥘 Comida' : '🍹 Bebida/Extra';
                  return `<div style="display: flex; justify-content: space-between;"><span>${i.cantidad}x ${i.nombre} <span style="font-size: 8px; color: #64748b;">(${badge})</span></span><b>$${((i.precio || 0) * (i.cantidad || 1)).toFixed(2)}</b></div>`;
                }).join('')}
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; padding-top: 4px; border-top: 1px dotted #e2e8f0;">
                <span style="font-size: 9px; color: #64748b;">Propina voluntaria en cobro</span>
                <button type="button" onclick="window.abrirModalPasarelaCobro(${mesaId}, [${sa.sillaNum}])"
                  style="padding: 4px 10px; font-size: 10px; font-weight: 800; background: #059669; color: #ffffff; border: none; border-radius: 6px; cursor: pointer;">
                  💳 Cobrar Silla ${sa.sillaNum} ($${sa.subtotalTotal.toFixed(2)})
                </button>
              </div>
            `;
            listContainer.appendChild(sb);
          }
        });

        actualizarTotalesPrecuenta(totalSeleccion);
      }

      // ═══════════════════════════════════════════════════════════════════
      // MODALIDAD 2: ANFITRIÓN INVITA COMIDA (BEBIDAS/EXTRAS POR PERSONA)
      // ═══════════════════════════════════════════════════════════════════
      else if (_precuentaModo === 'anfitrion') {
        if (headerTag) headerTag.innerHTML = `MESA ${mesaId} • ESCENARIO 2: ANFITRIÓN INVITA LA COMIDA`;

        if (controlsBox) {
          var optsAnf = sillasActivas.map(function (sa) {
            return `<option value="${sa.sillaNum}" ${_anfitrionSillaNum === sa.sillaNum ? 'selected' : ''}>Silla ${sa.sillaNum} - ${sa.cuenta.comensalNombre || 'Comensal'}</option>`;
          }).join('');

          controlsBox.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <span style="font-weight: 900; font-size: 11px; color: #1e293b;">👑 Selecciona el Anfitrión / Festejado:</span>
              <div style="display: flex; gap: 6px; align-items: center;">
                <select onchange="window.setAnfitrionSilla(this.value)" style="flex: 1; padding: 5px; font-size: 11px; font-weight: bold; border-radius: 6px; border: 1px solid #10b981; background: #ecfdf5; color: #065f46;">
                  ${optsAnf || '<option value="1">Silla 1</option>'}
                </select>
              </div>
              <span style="font-size: 9px; color: #64748b;">El Anfitrión absorbe TODOS los alimentos de la mesa y el centro. Cada invitado paga únicamente sus bebidas y postres personales.</span>
            </div>
          `;
        }

        var anfitrionData = sillasActivas.find(function (sa) { return sa.sillaNum === _anfitrionSillaNum; }) || {
          sillaNum: _anfitrionSillaNum,
          cuenta: window.palapaState.cuentas[`${mesaId}-${_anfitrionSillaNum}`] || {},
          items: [],
          subtotalAlimentos: 0,
          subtotalBebidas: 0
        };

        var totalAnfitrion = totalAlimentosMesa + anfitrionData.subtotalBebidas;

        // 1. TICKET DEL ANFITRIÓN
        var anfitrionBlock = document.createElement('div');
        anfitrionBlock.style.cssText = 'background: rgba(16, 185, 129, 0.12) !important; border: 2px solid #059669 !important; border-radius: 10px !important; padding: 8px 10px !important; margin-bottom: 6px !important;';
        
        var anfitrionItemsDesc = [
          { nombre: `🥘 Total Alimentos de Toda la Mesa (${sillasActivas.length} comensales + centro)`, cantidad: 1, precio: totalAlimentosMesa, notas: 'Cubierto por el anfitrión' }
        ];
        if (anfitrionData.subtotalBebidas > 0) {
          anfitrionData.items.filter(function (it) { return it.tipo_consumo !== 'comida'; }).forEach(function (b) {
            anfitrionItemsDesc.push(b);
          });
        }

        anfitrionBlock.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 900; color: #065f46; font-size: 12px; border-bottom: 1px solid #a7f3d0; padding-bottom: 4px;">
            <span>👑 CUENTA DEL ANFITRIÓN (SILLA ${_anfitrionSillaNum})</span>
            <span style="font-size: 13px; color: #047857;">$${totalAnfitrion.toFixed(2)}</span>
          </div>
          <div style="margin-top: 6px; font-size: 10px; color: #1e293b; display: flex; flex-direction: column; gap: 3px;">
            <div style="display: flex; justify-content: space-between;">
              <span>• Total Alimentos de la Mesa (Invita Anfitrión):</span>
              <b>$${totalAlimentosMesa.toFixed(2)}</b>
            </div>
            ${anfitrionData.subtotalBebidas > 0 ? `
              <div style="display: flex; justify-content: space-between; color: #0284c7;">
                <span>• Bebidas / Extras Propios Silla ${_anfitrionSillaNum}:</span>
                <b>$${anfitrionData.subtotalBebidas.toFixed(2)}</b>
              </div>
            ` : ''}
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; padding-top: 4px; border-top: 1px dashed #a7f3d0;">
            <span style="font-size: 9px; color: #047857; font-weight: bold;">Incluye comida grupal + consumo personal</span>
            <button type="button" id="btnCobrarAnfitrionTicket"
              style="padding: 5px 12px; font-size: 11px; font-weight: 900; background: #059669; color: #ffffff; border: none; border-radius: 6px; cursor: pointer;">
              💳 Cobrar Anfitrión ($${totalAnfitrion.toFixed(2)})
            </button>
          </div>
        `;
        listContainer.appendChild(anfitrionBlock);

        var btnCobrarAnf = anfitrionBlock.querySelector('#btnCobrarAnfitrionTicket');
        if (btnCobrarAnf) {
          btnCobrarAnf.onclick = function () {
            var customTicket = {
              titulo: `Mesa ${mesaId} • 👑 Cuenta Anfitrión (Silla ${_anfitrionSillaNum})`,
              total: totalAnfitrion,
              items: anfitrionItemsDesc,
              sillaNum: _anfitrionSillaNum,
              sillasAfectadas: sillasActivas.map(function (sa) { return sa.sillaNum; }).concat([0]),
              tipoFiltro: 'solo_comida'
            };
            window.abrirModalPasarelaCobro(mesaId, [_anfitrionSillaNum], customTicket);
          };
        }

        // 2. TICKETS DE INVITADOS (SOLO BEBIDAS Y POSTRES EXTRAS)
        sillasActivas.forEach(function (sa) {
          if (sa.sillaNum !== _anfitrionSillaNum) {
            var bebidasItems = sa.items.filter(function (it) { return it.tipo_consumo !== 'comida'; });
            var totalInvitado = sa.subtotalBebidas;

            var invBlock = document.createElement('div');
            invBlock.style.cssText = 'border: 1px solid #cbd5e1 !important; border-radius: 8px !important; padding: 6px 8px !important; background: #ffffff !important;';
            invBlock.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 900; color: #0284c7; font-size: 11px; border-bottom: 1px dashed #cbd5e1; padding-bottom: 3px;">
                <span>SILLA ${sa.sillaNum} (INVITADO) • ${(sa.cuenta.comensalNombre || 'Comensal').toUpperCase()}</span>
                <span style="color: #0369a1; font-size: 12px;">$${totalInvitado.toFixed(2)}</span>
              </div>
              <div style="margin-top: 4px; font-size: 10px; color: #334155; display: flex; flex-direction: column; gap: 2px;">
                <div style="color: #059669; font-size: 9px; font-weight: bold;">✓ Alimentos cubiertos por Anfitrión ($0.00)</div>
                ${bebidasItems.length > 0 ? bebidasItems.map(function (i) {
                  return `<div style="display: flex; justify-content: space-between;"><span>${i.cantidad}x ${i.nombre}</span><b>$${((i.precio || 0) * (i.cantidad || 1)).toFixed(2)}</b></div>`;
                }).join('') : '<div style="color: #94a3b8; font-style: italic;">Sin consumos de bebida/extra registrados</div>'}
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; padding-top: 4px; border-top: 1px dotted #e2e8f0;">
                <span style="font-size: 9px; color: #64748b;">Propina voluntaria por comensal</span>
                <button type="button" id="btnCobrarInv_${sa.sillaNum}" ${totalInvitado === 0 ? 'disabled' : ''}
                  style="padding: 4px 10px; font-size: 10px; font-weight: 800; background: ${totalInvitado > 0 ? '#0284c7' : '#94a3b8'}; color: #ffffff; border: none; border-radius: 6px; cursor: pointer;">
                  💳 Cobrar Silla ${sa.sillaNum} ($${totalInvitado.toFixed(2)})
                </button>
              </div>
            `;
            listContainer.appendChild(invBlock);

            var btnInv = invBlock.querySelector(`#btnCobrarInv_${sa.sillaNum}`);
            if (btnInv && totalInvitado > 0) {
              btnInv.onclick = (function (sNum, tot, bItems) {
                return function () {
                  var customTicket = {
                    titulo: `Mesa ${mesaId} • Silla ${sNum} (Bebidas/Extras)`,
                    total: tot,
                    items: bItems,
                    sillaNum: sNum,
                    sillasAfectadas: [sNum],
                    tipoFiltro: 'solo_bebidas'
                  };
                  window.abrirModalPasarelaCobro(mesaId, [sNum], customTicket);
                };
              })(sa.sillaNum, totalInvitado, bebidasItems);
            }
          }
        });

        actualizarTotalesPrecuenta(totalGranMesa);
      }

      // ═══════════════════════════════════════════════════════════════════
      // MODALIDAD 3: DIVIDIR COMIDA POR PARTES IGUALES (BEBIDAS INDIVIDUALES)
      // ═══════════════════════════════════════════════════════════════════
      else if (_precuentaModo === 'split_comida') {
        var numComensales = Math.max(1, sillasActivas.length);
        var cuotaComida = totalAlimentosMesa / numComensales;

        if (headerTag) headerTag.innerHTML = `MESA ${mesaId} • ESCENARIO 3: COMIDA DIVIDIDA EQUITATIVAMENTE`;

        if (controlsBox) {
          controlsBox.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; text-align: center;">
              <div style="background: #ffffff; padding: 4px; border-radius: 6px; border: 1px solid #cbd5e1;">
                <span style="font-size: 9px; color: #64748b; display: block;">Total Alimentos:</span>
                <span style="font-weight: 900; color: #047857; font-size: 11px;">$${totalAlimentosMesa.toFixed(2)}</span>
              </div>
              <div style="background: #ffffff; padding: 4px; border-radius: 6px; border: 1px solid #cbd5e1;">
                <span style="font-size: 9px; color: #64748b; display: block;">Comensales:</span>
                <span style="font-weight: 900; color: #0f172a; font-size: 11px;">${numComensales}</span>
              </div>
              <div style="background: #ecfdf5; padding: 4px; border-radius: 6px; border: 1px solid #10b981;">
                <span style="font-size: 9px; color: #065f46; display: block;">Cuota Alimentos:</span>
                <span style="font-weight: 900; color: #059669; font-size: 11px;">$${cuotaComida.toFixed(2)}/pers.</span>
              </div>
            </div>
            <div style="font-size: 9px; color: #64748b; margin-top: 4px; text-align: center;">
              Cada comensal paga su parte igual de comida ($${cuotaComida.toFixed(2)}) + sus bebidas y extras personales.
            </div>
          `;
        }

        sillasActivas.forEach(function (sa) {
          var bebidasItems = sa.items.filter(function (it) { return it.tipo_consumo !== 'comida'; });
          var totalPersona = cuotaComida + sa.subtotalBebidas;

          var personaItemsDesc = [
            { nombre: `1/${numComensales} Parte de Alimentos de Mesa & Centro`, cantidad: 1, precio: cuotaComida, notas: 'División equitativa' }
          ];
          bebidasItems.forEach(function (b) { personaItemsDesc.push(b); });

          var card = document.createElement('div');
          card.style.cssText = 'border: 1.5px solid #10b981 !important; border-radius: 8px !important; padding: 6px 8px !important; background: #ffffff !important;';
          card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 900; color: #065f46; font-size: 11px; border-bottom: 1px dashed #cbd5e1; padding-bottom: 3px;">
              <span>SILLA ${sa.sillaNum} • ${(sa.cuenta.comensalNombre || 'Comensal').toUpperCase()}</span>
              <span style="color: #059669; font-size: 12px;">$${totalPersona.toFixed(2)}</span>
            </div>
            <div style="margin-top: 4px; font-size: 10px; color: #334155; display: flex; flex-direction: column; gap: 2px;">
              <div style="display: flex; justify-content: space-between; color: #047857; font-weight: bold;">
                <span>• 1/${numComensales} Cuota Alimentos Mesa:</span>
                <b>$${cuotaComida.toFixed(2)}</b>
              </div>
              ${sa.subtotalBebidas > 0 ? `
                <div style="border-top: 1px dotted #e2e8f0; margin-top: 2px; padding-top: 2px;">
                  <span style="font-size: 9px; color: #0284c7; font-weight: bold;">Consumos personales (Bebidas/Extras):</span>
                  ${bebidasItems.map(function (b) { return `<div style="display: flex; justify-content: space-between; font-size: 9px; color: #475569;"><span>+ ${b.cantidad}x ${b.nombre}</span><span>$${((b.precio || 0) * (b.cantidad || 1)).toFixed(2)}</span></div>`; }).join('')}
                </div>
              ` : '<div style="font-size: 9px; color: #94a3b8; font-style: italic;">Sin bebidas extras registradas</div>'}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; padding-top: 4px; border-top: 1px dotted #e2e8f0;">
              <span style="font-size: 9px; color: #64748b;">Propina voluntaria independiente</span>
              <button type="button" id="btnCobrarSplit_${sa.sillaNum}"
                style="padding: 4px 10px; font-size: 10px; font-weight: 800; background: #059669; color: #ffffff; border: none; border-radius: 6px; cursor: pointer;">
                💳 Cobrar Silla ${sa.sillaNum} ($${totalPersona.toFixed(2)})
              </button>
            </div>
          `;
          listContainer.appendChild(card);

          var btnSplit = card.querySelector(`#btnCobrarSplit_${sa.sillaNum}`);
          if (btnSplit) {
            btnSplit.onclick = (function (sNum, tot, pItems) {
              return function () {
                var customTicket = {
                  titulo: `Mesa ${mesaId} • Silla ${sNum} (Comida Dividida + Bebidas)`,
                  total: tot,
                  items: pItems,
                  sillaNum: sNum,
                  sillasAfectadas: [sNum],
                  esSplit: true
                };
                window.abrirModalPasarelaCobro(mesaId, [sNum], customTicket);
              };
            })(sa.sillaNum, totalPersona, personaItemsDesc);
          }
        });

        actualizarTotalesPrecuenta(totalGranMesa);
      }

      // ═══════════════════════════════════════════════════════════════════
      // MODALIDAD 4: TODA LA MESA (1 SOLO PAGO)
      // ═══════════════════════════════════════════════════════════════════
      else if (_precuentaModo === 'mesa_completa') {
        if (headerTag) headerTag.innerHTML = `MESA ${mesaId} • CUENTA COMPLETA CONSOLIDADA`;

        if (controlsBox) {
          controlsBox.innerHTML = `
            <div style="font-size: 10px; color: #334155; text-align: center;">
              <b>Consolidado de toda la mesa:</b> ${sillasActivas.length} comensales + Cuenta de Mesa al centro. 1 solo pago total.
            </div>
          `;
        }

        var fullBlock = document.createElement('div');
        fullBlock.style.cssText = 'border: 1px solid #cbd5e1 !important; border-radius: 8px !important; padding: 8px !important; background: #ffffff !important;';
        
        fullBlock.innerHTML = `
          <div style="font-size: 11px; font-weight: 900; color: #0f172a; margin-bottom: 6px;">DESGLOSE COMPLETO:</div>
          <div style="display: flex; flex-direction: column; gap: 3px; font-size: 10px; color: #334155;">
            ${mesaItems.length > 0 ? `<div style="display: flex; justify-content: space-between; color: #b45309; font-weight: bold;"><span>⭐ Platillos al Centro:</span><span>$${mesaTotalNeto.toFixed(2)}</span></div>` : ''}
            ${sillasActivas.map(function (sa) {
              return `<div style="display: flex; justify-content: space-between;"><span>• Silla ${sa.sillaNum} (${sa.cuenta.comensalNombre || 'Comensal'} - ${sa.items.length} prod.):</span><b>$${sa.subtotalTotal.toFixed(2)}</b></div>`;
            }).join('')}
          </div>
        `;
        listContainer.appendChild(fullBlock);

        actualizarTotalesPrecuenta(totalGranMesa);
      }
    }

    function actualizarTotalesPrecuenta(montoTotal) {
      const subtotalEl = document.getElementById('precuentaSubtotal');
      const ivaEl = document.getElementById('precuentaIva');
      const propinaEl = document.getElementById('precuentaPropina');
      const totalEl = document.getElementById('precuentaTotal');
      const btnCobrarMonto = document.getElementById('btnCobrarMonto');

      var subtotalBase = montoTotal / 1.16;
      var ivaVal = montoTotal - subtotalBase;
      var propinaVal = montoTotal * 0.10;

      if (subtotalEl) subtotalEl.innerText = `$${subtotalBase.toFixed(2)}`;
      if (ivaEl) ivaEl.innerText = `$${ivaVal.toFixed(2)}`;
      if (propinaEl) propinaEl.innerText = `$${propinaVal.toFixed(2)}`;
      if (totalEl) totalEl.innerText = `$${montoTotal.toFixed(2)}`;
      if (btnCobrarMonto) btnCobrarMonto.innerText = `$${montoTotal.toFixed(2)}`;
    }

    window.cobrarSillasPrecuenta = function () {
      var mesaId = _precuentaMesaId;
      if (_precuentaModo === 'individual') {
        var sillasList = _precuentaSillasSeleccionadas.slice();
        if (sillasList.length === 0) {
          showDragToast('⚠ Selecciona al menos una cuenta para cobrar', 'warn');
          return;
        }
        window.abrirModalPasarelaCobro(mesaId, sillasList);
      } else if (_precuentaModo === 'mesa_completa') {
        var allChairs = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
        window.abrirModalPasarelaCobro(mesaId, allChairs);
      } else {
        showDragToast('ℹ Toca el botón 💳 Cobrar del comensal específico en la lista.', 'info');
      }
    };

    function cerrarPrecuenta() {
      const modalP = document.getElementById('modalPrecuentaBackdrop');
      if (modalP) {
        modalP.classList.remove('show');
        modalP.style.setProperty('display', 'none', 'important');
      }
    }

    window.abrirPrecuenta = function () {
      abrirPrecuenta();
    };
    window.cerrarPrecuenta = function () {
      cerrarPrecuenta();
    };

    function cerrarModalComanda() {
      const modal = document.getElementById('modalComandaBackdrop');
      if (modal) {
        modal.classList.remove('show');
        modal.style.setProperty('display', 'none', 'important');
      }
    }

    window.cerrarModalComanda = function () {
      cerrarModalComanda();
    };
    window.abrirModalComandaActual = function () {
      abrirModalComandaActual();
    };

    window.irACocinaMesaActual = function (mesaId) {
      const m = mesaId || (window.palapaState && window.palapaState.mesaSeleccionadaId) || 2;
      localStorage.setItem('kds_filtro_mesa', m.toString());
      if (typeof window.syncStorageWithGlobal === 'function') {
        window.syncStorageWithGlobal();
      }
      try {
        window.scrollTo(0, 0);
        if (document.documentElement) document.documentElement.scrollTop = 0;
        if (document.body) document.body.scrollTop = 0;
      } catch (e) { }
      if (window.anvilAppNav) {
        window.anvilAppNav('monitor_cocina');
      } else if (typeof window.parent !== 'undefined' && window.parent.anvilAppNav) {
        window.parent.anvilAppNav('monitor_cocina');
      } else {
        window.location.hash = 'monitor_cocina';
      }
    };
    window.irACocinaMesa = window.irACocinaMesaActual;

    window.liberarSillaActual = function () {
      const mesaId = window.palapaState.mesaSeleccionadaId;
      const sillaNum = window.palapaState.sillaSeleccionadaNum;
      if (sillaNum === null) return;
      const key = `${mesaId}-${sillaNum}`;
      const cuenta = window.palapaState.cuentas[key];
      if (cuenta) {
        // Solo pedir confirmación si tiene consumos pendientes no pagados
        if (!cuenta.pagado && cuenta.estado !== 'pagada' && cuenta.items && cuenta.items.length > 0) {
          if (!confirm(`La Silla ${sillaNum} de Mesa ${mesaId} tiene consumos pendientes de cobro. ¿Deseas desocupar la silla de todos modos?`)) {
            return;
          }
        }
        delete window.palapaState.cuentas[key];
        saveStateToStorage();
        renderStateUI();
        cerrarModalComanda();
        showDragToast(`🟢 Silla ${sillaNum} de Mesa ${mesaId} desocupada y disponible`, 'ok');
      }
    };

    window.liberarMesaCompleta = function (mesaId) {
      mesaId = mesaId || window.palapaState.mesaSeleccionadaId;
      if (!mesaId) return;

      var unpaidCount = 0;
      Object.keys(window.palapaState.cuentas).forEach(function (k) {
        var p = k.split('-');
        if (parseInt(p[0]) === mesaId) {
          var c = window.palapaState.cuentas[k];
          if (c && !c.pagado && c.estado !== 'pagada' && c.items && c.items.length > 0) {
            unpaidCount++;
          }
        }
      });

      if (unpaidCount > 0) {
        if (!confirm(`Hay ${unpaidCount} comensal(es) con consumos no pagados en Mesa ${mesaId}. ¿Seguro que deseas desocupar y poner libre toda la mesa?`)) {
          return;
        }
      }

      var count = 0;
      Object.keys(window.palapaState.cuentas).forEach(function (k) {
        var p = k.split('-');
        if (parseInt(p[0]) === mesaId) {
          delete window.palapaState.cuentas[k];
          count++;
        }
      });

      saveStateToStorage();
      renderStateUI();
      cerrarModalComanda();
      showDragToast(`🟢 Mesa ${mesaId} desocupada completamente (${count} sillas liberadas)`, 'ok');
    };

    window.eliminarItemModal = function (key, idx) {
      if (window.palapaState.cuentas[key] && window.palapaState.cuentas[key].items) {
        const it = window.palapaState.cuentas[key].items[idx];
        if (it && it.enviadoCocina) {
          showDragToast('🔒 Este producto ya fue enviado a cocina y no puede eliminarse de la comanda.', 'warn');
          return;
        }
        window.palapaState.cuentas[key].items.splice(idx, 1);
        if (window.palapaState.cuentas[key].items.length === 0) {
          delete window.palapaState.cuentas[key];
        }
        saveStateToStorage();
        renderStateUI();
        abrirModalComandaActual();
      }
    };

    window.volverAlCroquisGeneral = function () {
      window.palapaState.modoComandaActiva = false;
      renderStateUI();
      const bannerText = document.getElementById('bannerText');
      if (bannerText) {
        if (window.palapaState.modoMoverActivo && window.palapaState.sillaOrigenMover) {
          const src = window.palapaState.sillaOrigenMover;
          bannerText.innerHTML = `<b style="color: #38bdf8;">MOVIENDO COMENSAL (Mesa ${src.mesaId} Silla ${src.sillaNum}):</b> Haz clic en la <b>Silla Destino</b> o en el <b>Centro de la Mesa</b>.`;
        } else {
          bannerText.innerHTML = `💡 Haz clic en cualquier <b>Mesa</b> o <b>Silla</b> para tomar su orden y abrir el catálogo de menú ampliado, o <b>arrastra con el mouse</b> para mover comensales.`;
        }
      }
    };

    window.seleccionarSillaSidebar = function (sillaNum) {
      const mesaId = window.palapaState.mesaSeleccionadaId || 3;
      if (window.palapaState.modoMoverActivo) {
        completarMovimiento(mesaId, sillaNum);
        return;
      }

      const esMesa = (sillaNum === 0);
      const key = `${mesaId}-${sillaNum}`;

      if (!window.palapaState.cuentas[key]) {
        const nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        window.palapaState.cuentas[key] = {
          estado: 'ocupada',
          qrId: esMesa ? `MESA-0${mesaId}` : `PV-0${mesaId}${sillaNum}`,
          comensalNombre: esMesa ? '⭐ Cuenta de MESA (Al Centro)' : ('Comensal Silla ' + sillaNum + (sillaNum > 4 ? ' (Arrimada)' : '')),
          items: [],
          historialUbicaciones: [{ mesaId: mesaId, sillaNum: sillaNum, hora: nowStr }],
          creadoPor: 'mesero_presencial',
          horaLlegada: nowStr
        };
        saveStateToStorage();
        showDragToast(esMesa ? `⭐ Cuenta de MESA seleccionada (Mesa ${mesaId})` : `🪑 Comensal ubicado en Mesa ${mesaId} Silla ${sillaNum}`, 'ok');
      }

      window.palapaState.sillaSeleccionadaNum = sillaNum;
      window.palapaState.modoComandaActiva = true;
      renderStateUI();
    };

    window.eliminarItemSidebar = function (idx) {
      const mesaId = window.palapaState.mesaSeleccionadaId;
      const sillaNum = window.palapaState.sillaSeleccionadaNum;
      if (!mesaId || sillaNum === null || sillaNum === undefined) return;

      const key = `${mesaId}-${sillaNum}`;
      if (window.palapaState.cuentas[key] && window.palapaState.cuentas[key].items) {
        const it = window.palapaState.cuentas[key].items[idx];
        if (it && it.enviadoCocina) {
          showDragToast('🔒 Este producto ya fue enviado a cocina y no puede eliminarse de la comanda.', 'warn');
          return;
        }
        window.palapaState.cuentas[key].items.splice(idx, 1);
        saveStateToStorage();
        renderStateUI();
      }
    };

    window.enviarItemIndividualACocina = function (idx) {
      const mesaId = window.palapaState.mesaSeleccionadaId || 1;
      let sillaNum = window.palapaState.sillaSeleccionadaNum;
      if (sillaNum === null || sillaNum === undefined) {
        sillaNum = 0; // Cuenta de mesa al centro
      }

      let key = `${mesaId}-${sillaNum}`;
      let cuenta = window.palapaState.cuentas[key];
      if (!cuenta && (sillaNum === 0 || sillaNum === 'centro')) {
        key = `${mesaId}-centro`;
        cuenta = window.palapaState.cuentas[key];
      }
      if (!cuenta || !cuenta.items || !cuenta.items[idx]) {
        console.warn('No se encontró el item a enviar:', { mesaId, sillaNum, key, idx });
        return;
      }

      const item = cuenta.items[idx];
      const nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      item.enviadoCocina = true;
      item.horaEnvioCocina = nowStr;

      saveStateToStorage();
      renderStateUI();

      // Sincronizar inmediatamente con el servidor persistente
      try {
        if (window.anvilSyncCuenta) {
          const syncSilla = (sillaNum === 'centro') ? 0 : sillaNum;
          window.anvilSyncCuenta(mesaId, syncSilla, JSON.stringify(cuenta.items), cuenta.estado || 'ocupada');
        }
      } catch (err) {
        console.error('Error sincronizando item individual con servidor:', err);
      }

      showDragToast(`🚀 ¡${item.nombre} enviado a Cocina / Barra (${nowStr})!`, 'ok');
    };

    window.enviarACocinaComandaActiva = function () {
      const mesaId = window.palapaState.mesaSeleccionadaId || 1;
      let sillaNum = window.palapaState.sillaSeleccionadaNum;
      if (sillaNum === null || sillaNum === undefined) {
        sillaNum = 0; // Cuenta de mesa al centro
      }

      let key = `${mesaId}-${sillaNum}`;
      let cuenta = window.palapaState.cuentas[key];
      if (!cuenta && (sillaNum === 0 || sillaNum === 'centro')) {
        key = `${mesaId}-centro`;
        cuenta = window.palapaState.cuentas[key];
      }

      if (!cuenta || !cuenta.items || cuenta.items.length === 0) {
        showDragToast('ℹ Agrega al menos un producto a la comanda antes de enviar a cocina.', 'warn');
        return;
      }

      const pendientes = cuenta.items.filter(i => !i.enviadoCocina);
      if (pendientes.length === 0) {
        showDragToast('ℹ Todos los productos de esta orden ya fueron enviados a Cocina / Barra de Café.', 'info');
        return;
      }

      const nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      pendientes.forEach(i => {
        i.enviadoCocina = true;
        i.horaEnvioCocina = nowStr;
      });

      saveStateToStorage();
      renderStateUI();

      // Sincronizar inmediatamente con el servidor persistente
      try {
        if (window.anvilSyncCuenta) {
          const syncSilla = (sillaNum === 'centro') ? 0 : sillaNum;
          window.anvilSyncCuenta(mesaId, syncSilla, JSON.stringify(cuenta.items), cuenta.estado || 'ocupada');
        }
      } catch (err) {
        console.error('Error sincronizando comanda activa con servidor:', err);
      }

      showDragToast(`🚀 ¡${pendientes.length} producto(s) enviados a Cocina / Barra (KDS)! (${nowStr})`, 'ok');
    };

    function renderStateUI() {
      const isMoveMode = window.palapaState.modoMoverActivo;
      const origen = window.palapaState.sillaOrigenMover;
      const isComandaMode = !!window.palapaState.modoComandaActiva;

      // 1. Control del Layout Dual (Panorámico vs Comanda & Menú Ampliado)
      const mainGrid = document.getElementById('mainCanvasGrid');
      const viewCroquis = document.getElementById('viewOverviewCroquis');
      const viewSidebar = document.getElementById('viewSidebarComanda');
      const panelMenu = document.getElementById('panelMenuCatalogo');

      if (mainGrid) mainGrid.className = isComandaMode ? 'mode-comanda' : 'mode-overview';
      if (viewCroquis) viewCroquis.style.setProperty('display', isComandaMode ? 'none' : 'flex', 'important');
      if (viewSidebar) viewSidebar.style.setProperty('display', isComandaMode ? 'flex' : 'none', 'important');
      if (panelMenu) panelMenu.style.setProperty('display', isComandaMode ? 'flex' : 'none', 'important');

      // 2. Renderizar Mesas y Sillas en el Croquis Panorámico
      const unidas = window.palapaState.mesasUnidas;
      const btnSep = document.getElementById('btnSeparateTables');
      const btn12 = document.getElementById('btnJoin12');
      const btn23 = document.getElementById('btnJoin23');
      const btnAll = document.getElementById('btnJoinAll');

      if (btnSep) btnSep.style.setProperty('display', unidas ? 'flex' : 'none', 'important');
      if (btn12) {
        btn12.style.background = unidas === '1-2' ? '#0284c7' : '#ffffff';
        btn12.style.color = unidas === '1-2' ? '#ffffff' : '#0284c7';
      }
      if (btn23) {
        btn23.style.background = unidas === '2-3' ? '#0284c7' : '#ffffff';
        btn23.style.color = unidas === '2-3' ? '#ffffff' : '#0284c7';
      }
      if (btnAll) {
        btnAll.style.background = unidas === '1-2-3' ? '#0369a1' : 'linear-gradient(135deg, #0284c7, #0369a1)';
      }

      const grid = document.getElementById('floorplanTablesGrid');
      const card1 = document.getElementById('table-card-container-1');
      const card2 = document.getElementById('table-card-container-2');
      const card3 = document.getElementById('table-card-container-3');
      const box1 = document.getElementById('table-box-1');
      const box2 = document.getElementById('table-box-2');
      const box3 = document.getElementById('table-box-3');
      const circle1 = document.getElementById('table-circle-1');
      const circle2 = document.getElementById('table-circle-2');
      const circle3 = document.getElementById('table-circle-3');
      const head1 = document.getElementById('table-header-title-1');
      const head2 = document.getElementById('table-header-title-2');
      const head3 = document.getElementById('table-header-title-3');
      const label1 = document.getElementById('table-label-1');
      const label2 = document.getElementById('table-label-2');
      const label3 = document.getElementById('table-label-3');

      // Helper para renderizar una silla interactiva (click y drag)
      function renderChairBadge(m, s, posCss, container, isJoinedMode) {
        const key = `${m}-${s}`;
        const cuenta = window.palapaState.cuentas[key];
        let numItems = 0;
        let saldoPendiente = 0;
        let hasPaidItems = false;

        if (cuenta && cuenta.items) {
          numItems = cuenta.items.length;
          cuenta.items.forEach(it => {
            if (it.pagado) hasPaidItems = true;
            else saldoPendiente += (it.precio * it.cantidad);
          });
        }

        // Si todos los consumos están pagados -> AZUL (Sobremesa)
        // Si hay consumos nuevos/pendientes de cobro -> NARANJA (Ocupada)
        // Si no hay comensal -> VERDE (Disponible)
        const isPaid = (hasPaidItems && saldoPendiente === 0);
        const isOccupied = (saldoPendiente > 0) || (cuenta && (cuenta.estado === 'ocupada' || isPaid || numItems > 0));
        const isSource = isMoveMode && origen && origen.mesaId === m && origen.sillaNum === s;
        const isArrimada = (s >= 5) || (cuenta && cuenta.esArrimada);

        const chairEl = document.createElement('div');
        chairEl.id = `chair-${m}-${s}`;
        chairEl.setAttribute('draggable', 'true');

        let stateClass = isPaid ? 'chair-state-paid' : (isOccupied ? 'chair-state-busy' : 'chair-state-free');
        if (isSource) stateClass = 'chair-moving-source';
        else if (isMoveMode) stateClass = `chair-moving-target ${stateClass}`;

        chairEl.className = `chair-btn-fixed ${stateClass}`;
        chairEl.style.cssText = `position: absolute !important; ${posCss} z-index: 25 !important; cursor: pointer !important; white-space: nowrap !important;`;
        chairEl.onclick = function (e) {
          if (_wasDrag) return;
          if (e) e.stopPropagation();
          window.clickSilla(m, s);
        };

        const paidCheck = isPaid ? ' ✓' : '';

        // Detectar si hay items nuevos del cliente (no enviados a cocina aún)
        const hasNewItems = cuenta && cuenta.items && cuenta.items.some(it => !it.enviadoCocina);
        const newItemsCount = cuenta && cuenta.items ? cuenta.items.filter(it => !it.enviadoCocina).length : 0;
        const totalItems = numItems;

        // Badge de conteo de items
        let itemBadge = '';
        if (totalItems > 0 && !isPaid) {
          const badgeColor = hasNewItems ? '#ef4444' : '#d97706';
          itemBadge = ` <span style="display:inline-block;background:${badgeColor};color:#fff;border-radius:10px;padding:0px 5px;font-size:9px;font-weight:900;vertical-align:middle;min-width:16px;text-align:center;line-height:15px;margin-left:2px;">${totalItems}</span>`;
        }

        // Mini resumen del primer producto
        let miniProd = '';
        if (totalItems > 0 && !isPaid && cuenta && cuenta.items) {
          const primero = cuenta.items[0];
          const nombre = primero.nombre ? primero.nombre.substring(0, 12) + (primero.nombre.length > 12 ? '…' : '') : '';
          miniProd = `<div style="font-size:8px;opacity:0.9;margin-top:1px;line-height:1.1;max-width:64px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${hasNewItems ? '🆕 ' : ''}${nombre}${totalItems > 1 ? ` +${totalItems-1}` : ''}</div>`;
        }

        if (isJoinedMode) {
          chairEl.innerHTML = isArrimada ? `🪑 M${m}-S${s}${paidCheck}${itemBadge}${miniProd}` : `M${m}-S${s}${paidCheck}${itemBadge}${miniProd}`;
        } else {
          chairEl.innerHTML = isArrimada ? `🪑 S${s}${paidCheck}${itemBadge}${miniProd}` : `Silla ${s}${paidCheck}${itemBadge}${miniProd}`;
        }

        // Pulsar si hay pedidos nuevos del cliente aún sin enviar a cocina
        if (hasNewItems) {
          chairEl.classList.add('chair-has-new-order');
        }

        const itemsTooltip = cuenta && cuenta.items && cuenta.items.length > 0
          ? '\n' + cuenta.items.map(it => `  • ${it.nombre} x${it.cantidad || 1}${it.enviadoCocina ? '' : ' 🆕'}`).join('\n')
          : '';

        chairEl.setAttribute('title', isPaid
          ? `Mesa ${m} Silla ${s} (Cuenta Pagada / Sobremesa) • Clic para ver o liberar`
          : (isOccupied
            ? `Mesa ${m} Silla ${s} (Ocupada${saldoPendiente > 0 ? ' · $' + saldoPendiente.toFixed(2) + ' pend.' : ''}) • Arrastra para mover o clic para comanda${itemsTooltip}`
            : `Mesa ${m} Silla ${s} (Disponible) • Arrastra para trasladar o clic para comanda`));

        chairEl.addEventListener('mousedown', function (e) {
          _chairMousedown(e, m, s);
        });

        container.appendChild(chairEl);
        return isOccupied ? 1 : 0;
      }

      // Limpiar sillas existentes de los 3 boxes
      [box1, box2, box3].forEach(box => {
        if (box) {
          box.querySelectorAll('.chair-btn-fixed').forEach(el => el.remove());
        }
      });

      // Helper para renderizar los comensales activos alrededor del conjunto unificado
      function renderJoinedActiveComensales(activeList, container, isImperial) {
        let slots = [];
        if (!isImperial) {
          // Conjunto de 2 Mesas (M1+M2 o M2+M3): 8 posiciones perimetrales óptimas
          slots = [
            'top: 2px; left: 22%; transform: translateX(-50%);',
            'top: 2px; left: 50%; transform: translateX(-50%);',
            'top: 2px; left: 78%; transform: translateX(-50%);',
            'bottom: 2px; left: 22%; transform: translateX(-50%);',
            'bottom: 2px; left: 50%; transform: translateX(-50%);',
            'bottom: 2px; left: 78%; transform: translateX(-50%);',
            'left: 4px; top: 50%; transform: translateY(-50%);',
            'right: 4px; top: 50%; transform: translateY(-50%);'
          ];
        } else {
          // Gran Banquete Imperial (M1+M2+M3): 12 posiciones perimetrales óptimas
          slots = [
            'top: 2px; left: 14%; transform: translateX(-50%);',
            'top: 2px; left: 32%; transform: translateX(-50%);',
            'top: 2px; left: 50%; transform: translateX(-50%);',
            'top: 2px; left: 68%; transform: translateX(-50%);',
            'top: 2px; left: 86%; transform: translateX(-50%);',
            'bottom: 2px; left: 14%; transform: translateX(-50%);',
            'bottom: 2px; left: 32%; transform: translateX(-50%);',
            'bottom: 2px; left: 50%; transform: translateX(-50%);',
            'bottom: 2px; left: 68%; transform: translateX(-50%);',
            'bottom: 2px; left: 86%; transform: translateX(-50%);',
            'left: 4px; top: 50%; transform: translateY(-50%);',
            'right: 4px; top: 50%; transform: translateY(-50%);'
          ];
        }

        activeList.forEach((item, idx) => {
          const posCss = slots[idx] || `top: 2px; left: ${15 + (idx * 12)}%; transform: translateX(-50%);`;
          renderChairBadge(item.mesaId, item.sillaNum, posCss, container, true);
        });
      }

      // MODO 1: GRUPO MODULAR MESA 1 + MESA 2 UNIDAS (MESA LARGA CON 8 SILLAS PERIMETRALES + ARRSTRABLES A CABECERAS)
      if (unidas === '1-2' && grid && card1 && card2 && card3) {
        grid.style.setProperty('grid-template-columns', '2fr 1fr', 'important');
        card1.style.setProperty('display', 'flex', 'important');
        card1.style.setProperty('border', '2.5px solid #0284c7', 'important');
        card1.style.setProperty('background', '#f0f9ff', 'important');
        card1.style.setProperty('box-shadow', '0 8px 25px rgba(2, 132, 199, 0.15)', 'important');
        if (head1) head1.innerHTML = '🔗 CONJUNTO MESA 1 + MESA 2 <span style="font-size:11px;color:#0284c7;">(MESA LARGA 8 PAX CON CABECERAS)</span>';

        if (box1) {
          box1.style.setProperty('width', '580px', 'important');
          box1.style.setProperty('height', '230px', 'important');
          box1.style.setProperty('position', 'relative', 'important');
          box1.style.setProperty('display', 'flex', 'important');
          box1.style.setProperty('align-items', 'center', 'important');
          box1.style.setProperty('justify-content', 'center', 'important');
          box1.innerHTML = `
            <div id="table-circle-1" class="table-square-fixed" onclick="window.clickMesa(1);" style="width: 440px !important; height: 104px !important; border-radius: 18px !important; background: #fffbeb !important; border: 3px solid #f59e0b !important; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.2) !important; display: flex !important; align-items: stretch !important; position: relative !important; cursor: pointer !important; z-index: 10 !important;">
              <div style="flex: 1 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; border-right: 2px dashed #f59e0b !important;">
                <span style="font-size: 18px !important; font-weight: 900 !important; color: #92400e !important; line-height: 1 !important;">M1</span>
                <span style="font-size: 9px !important; font-weight: 800 !important; color: #d97706 !important; text-transform: uppercase !important; margin-top: 2px !important;">Sector 1</span>
              </div>
              <div style="position: absolute !important; left: 50% !important; top: 50% !important; transform: translate(-50%, -50%) !important; background: #1e3a5f !important; color: #ffffff !important; padding: 4px 12px !important; border-radius: 12px !important; font-size: 10px !important; font-weight: 800 !important; white-space: nowrap !important; box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important; z-index: 15 !important;">
                🔗 CONJUNTO M1 + M2 (8 Lugares)
              </div>
              <div style="flex: 1 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important;">
                <span style="font-size: 18px !important; font-weight: 900 !important; color: #92400e !important; line-height: 1 !important;">M2</span>
                <span style="font-size: 9px !important; font-weight: 800 !important; color: #d97706 !important; text-transform: uppercase !important; margin-top: 2px !important;">Sector 2</span>
              </div>
            </div>
          `;

          let busyM1 = 0, busyM2 = 0;

          // 1. Cabecera Izquierda (M1-S4)
          busyM1 += renderChairBadge(1, 4, 'left: 4px; top: 50%; transform: translateY(-50%);', box1, true);

          // 2. Fila Superior (3 sillas)
          busyM1 += renderChairBadge(1, 1, 'top: 2px; left: 24%; transform: translateX(-50%);', box1, true);
          busyM1 += renderChairBadge(1, 2, 'top: 2px; left: 50%; transform: translateX(-50%);', box1, true);
          busyM2 += renderChairBadge(2, 1, 'top: 2px; left: 76%; transform: translateX(-50%);', box1, true);

          // Arrimada M2-S5 (si existe)
          if (window.palapaState.cuentas['2-5']) {
            const pos = window.palapaState.cuentas['2-5'].posicionArrimada || 'top';
            const offCss = pos === 'top'
              ? 'top: 2px; left: calc(76% + 56px);'
              : pos === 'bottom'
                ? 'bottom: 2px; left: calc(76% + 56px);'
                : pos === 'right'
                  ? 'right: 4px; top: calc(50% - 44px);'
                  : 'left: 4px; top: calc(50% - 44px);';
            busyM2 += renderChairBadge(2, 5, offCss, box1, true);
          }

          // 3. Fila Inferior (3 sillas)
          busyM1 += renderChairBadge(1, 3, 'bottom: 2px; left: 24%; transform: translateX(-50%);', box1, true);
          busyM2 += renderChairBadge(2, 4, 'bottom: 2px; left: 50%; transform: translateX(-50%);', box1, true);
          busyM2 += renderChairBadge(2, 3, 'bottom: 2px; left: 76%; transform: translateX(-50%);', box1, true);

          // 4. Cabecera Derecha (M2-S2)
          busyM2 += renderChairBadge(2, 2, 'right: 4px; top: 50%; transform: translateY(-50%);', box1, true);

          const totalBusyJoined = busyM1 + busyM2;
          if (label1) {
            label1.style.color = totalBusyJoined > 0 ? '#d97706' : '#059669';
            label1.innerHTML = totalBusyJoined > 0
              ? `🟡 Ocupada (${totalBusyJoined} Comensales Unidos: ${busyM1} de M1 + ${busyM2} de M2)`
              : `🟢 Conjunto Disponible (8 Lugares)`;
          }
        }

        card2.style.setProperty('display', 'none', 'important');

        // Mesa 3 Individual a la derecha
        card3.style.setProperty('display', 'flex', 'important');
        card3.style.setProperty('border', '1px solid #dce8f5', 'important');
        card3.style.setProperty('background', '#f8fbff', 'important');
        card3.style.setProperty('box-shadow', 'none', 'important');
        if (head3) head3.innerHTML = 'Mesa 3 (Palapa)';
        if (box3) {
          box3.style.setProperty('width', '250px', 'important');
          box3.style.setProperty('height', '230px', 'important');
          box3.style.setProperty('position', 'relative', 'important');
          box3.style.setProperty('display', 'flex', 'important');
          box3.style.setProperty('align-items', 'center', 'important');
          box3.style.setProperty('justify-content', 'center', 'important');
          box3.innerHTML = `
            <div id="table-circle-3" class="table-square-fixed" style="width: 104px !important; height: 104px !important; border-radius: 16px !important; background: #fffbeb !important; border: 3px solid #f59e0b !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; cursor: pointer !important; z-index: 10 !important;">
              <span style="font-size: 18px !important; font-weight: 900 !important; color: #92400e !important; line-height: 1 !important;">M3</span>
              <span id="table-status-3" style="font-size: 9px !important; font-weight: 800 !important; color: #d97706 !important; text-transform: uppercase !important; margin-top: 2px !important;">Ocupada</span>
            </div>
          `;
          let busy3 = 0;
          busy3 += renderChairBadge(3, 1, 'top: 2px; left: 50%; transform: translateX(-50%);', box3, false);
          busy3 += renderChairBadge(3, 2, 'right: 2px; top: 50%; transform: translateY(-50%);', box3, false);
          busy3 += renderChairBadge(3, 3, 'bottom: 2px; left: 50%; transform: translateX(-50%);', box3, false);
          busy3 += renderChairBadge(3, 4, 'left: 2px; top: 50%; transform: translateY(-50%);', box3, false);
          if (label3) {
            label3.style.color = busy3 > 0 ? '#d97706' : '#059669';
            label3.innerHTML = busy3 > 0 ? `🟡 Ocupada (${busy3} Comensal${busy3 > 1 ? 'es' : ''})` : `🟢 Disponible`;
          }
        }

        // MODO 2: GRUPO MODULAR MESA 2 + MESA 3 UNIDAS (MESA LARGA CON 8 SILLAS PERIMETRALES + CABECERAS)
      } else if (unidas === '2-3' && grid && card1 && card2 && card3) {
        grid.style.setProperty('grid-template-columns', '1fr 2fr', 'important');

        // Mesa 1 Individual a la izquierda
        card1.style.setProperty('display', 'flex', 'important');
        card1.style.setProperty('border', '1px solid #dce8f5', 'important');
        card1.style.setProperty('background', '#f8fbff', 'important');
        card1.style.setProperty('box-shadow', 'none', 'important');
        if (head1) head1.innerHTML = 'Mesa 1 (Palapa)';
        if (box1) {
          box1.style.setProperty('width', '250px', 'important');
          box1.style.setProperty('height', '230px', 'important');
          box1.style.setProperty('position', 'relative', 'important');
          box1.style.setProperty('display', 'flex', 'important');
          box1.style.setProperty('align-items', 'center', 'important');
          box1.style.setProperty('justify-content', 'center', 'important');
          box1.innerHTML = `
            <div id="table-circle-1" class="table-square-fixed" style="width: 104px !important; height: 104px !important; border-radius: 16px !important; background: #ecfdf5 !important; border: 3px solid #10b981 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; cursor: pointer !important; z-index: 10 !important;">
              <span style="font-size: 18px !important; font-weight: 900 !important; color: #065f46 !important; line-height: 1 !important;">M1</span>
              <span id="table-status-1" style="font-size: 9px !important; font-weight: 800 !important; color: #059669 !important; text-transform: uppercase !important; margin-top: 2px !important;">Libre</span>
            </div>
          `;
          let busy1 = 0;
          busy1 += renderChairBadge(1, 1, 'top: 2px; left: 50%; transform: translateX(-50%);', box1, false);
          busy1 += renderChairBadge(1, 2, 'right: 2px; top: 50%; transform: translateY(-50%);', box1, false);
          busy1 += renderChairBadge(1, 3, 'bottom: 2px; left: 50%; transform: translateX(-50%);', box1, false);
          busy1 += renderChairBadge(1, 4, 'left: 2px; top: 50%; transform: translateY(-50%);', box1, false);
          if (label1) {
            label1.style.color = busy1 > 0 ? '#d97706' : '#059669';
            label1.innerHTML = busy1 > 0 ? `🟡 Ocupada (${busy1} Comensal${busy1 > 1 ? 'es' : ''})` : `🟢 Disponible`;
          }
        }

        // Mesa 2 + 3 Unidas
        card2.style.setProperty('display', 'flex', 'important');
        card2.style.setProperty('border', '2.5px solid #0284c7', 'important');
        card2.style.setProperty('background', '#f0f9ff', 'important');
        card2.style.setProperty('box-shadow', '0 8px 25px rgba(2, 132, 199, 0.15)', 'important');
        if (head2) head2.innerHTML = '🔗 CONJUNTO MESA 2 + MESA 3 <span style="font-size:11px;color:#0284c7;">(MESA LARGA 8 PAX CON CABECERAS)</span>';

        if (box2) {
          box2.style.setProperty('width', '580px', 'important');
          box2.style.setProperty('height', '230px', 'important');
          box2.style.setProperty('position', 'relative', 'important');
          box2.style.setProperty('display', 'flex', 'important');
          box2.style.setProperty('align-items', 'center', 'important');
          box2.style.setProperty('justify-content', 'center', 'important');
          box2.innerHTML = `
            <div id="table-circle-2" class="table-square-fixed" style="width: 440px !important; height: 104px !important; border-radius: 18px !important; background: #fffbeb !important; border: 3px solid #f59e0b !important; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.2) !important; display: flex !important; align-items: stretch !important; position: relative !important; cursor: pointer !important; z-index: 10 !important;">
              <div style="flex: 1 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; border-right: 2px dashed #f59e0b !important;">
                <span style="font-size: 18px !important; font-weight: 900 !important; color: #92400e !important; line-height: 1 !important;">M2</span>
                <span style="font-size: 9px !important; font-weight: 800 !important; color: #d97706 !important; text-transform: uppercase !important; margin-top: 2px !important;">Sector 1</span>
              </div>
              <div style="position: absolute !important; left: 50% !important; top: 50% !important; transform: translate(-50%, -50%) !important; background: #1e3a5f !important; color: #ffffff !important; padding: 4px 12px !important; border-radius: 12px !important; font-size: 10px !important; font-weight: 800 !important; white-space: nowrap !important; box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important; z-index: 15 !important;">
                🔗 CONJUNTO M2 + M3 (8 Lugares)
              </div>
              <div style="flex: 1 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important;">
                <span style="font-size: 18px !important; font-weight: 900 !important; color: #92400e !important; line-height: 1 !important;">M3</span>
                <span style="font-size: 9px !important; font-weight: 800 !important; color: #d97706 !important; text-transform: uppercase !important; margin-top: 2px !important;">Sector 2</span>
              </div>
            </div>
          `;

          let busyM2 = 0, busyM3 = 0;

          // 1. Cabecera Izquierda (M2-S4)
          busyM2 += renderChairBadge(2, 4, 'left: 4px; top: 50%; transform: translateY(-50%);', box2, true);

          // 2. Fila Superior (3 sillas)
          busyM2 += renderChairBadge(2, 1, 'top: 2px; left: 24%; transform: translateX(-50%);', box2, true);
          busyM2 += renderChairBadge(2, 2, 'top: 2px; left: 50%; transform: translateX(-50%);', box2, true);
          busyM3 += renderChairBadge(3, 1, 'top: 2px; left: 76%; transform: translateX(-50%);', box2, true);

          // Arrimada M2-S5 (si existe)
          if (window.palapaState.cuentas['2-5']) {
            const pos = window.palapaState.cuentas['2-5'].posicionArrimada || 'top';
            const offCss = pos === 'top'
              ? 'top: 2px; left: calc(76% + 56px);'
              : pos === 'bottom'
                ? 'bottom: 2px; left: calc(76% + 56px);'
                : pos === 'right'
                  ? 'right: 4px; top: calc(50% - 44px);'
                  : 'left: 4px; top: calc(50% - 44px);';
            busyM2 += renderChairBadge(2, 5, offCss, box2, true);
          }

          // 3. Fila Inferior (3 sillas)
          busyM2 += renderChairBadge(2, 3, 'bottom: 2px; left: 24%; transform: translateX(-50%);', box2, true);
          busyM3 += renderChairBadge(3, 4, 'bottom: 2px; left: 50%; transform: translateX(-50%);', box2, true);
          busyM3 += renderChairBadge(3, 3, 'bottom: 2px; left: 76%; transform: translateX(-50%);', box2, true);

          // 4. Cabecera Derecha (M3-S2)
          busyM3 += renderChairBadge(3, 2, 'right: 4px; top: 50%; transform: translateY(-50%);', box2, true);

          const totalBusyJoined23 = busyM2 + busyM3;
          if (label2) {
            label2.style.color = totalBusyJoined23 > 0 ? '#d97706' : '#059669';
            label2.innerHTML = totalBusyJoined23 > 0
              ? `🟡 Ocupada (${totalBusyJoined23} Comensales Unidos: ${busyM2} de M2 + ${busyM3} de M3)`
              : `🟢 Conjunto Disponible (8 Lugares)`;
          }
        }

        card3.style.setProperty('display', 'none', 'important');

        // MODO 3: GRAN MESA IMPERIAL (M1 + M2 + M3) — RECTÁNGULO LARGO CON 12-14 SILLAS INCLUYENDO CABECERAS
      } else if (unidas === '1-2-3' && grid && card1 && card2 && card3) {
        grid.style.setProperty('grid-template-columns', '1fr', 'important');
        card1.style.setProperty('display', 'flex', 'important');
        card1.style.setProperty('border', '2.5px solid #0284c7', 'important');
        card1.style.setProperty('background', '#f0f9ff', 'important');
        card1.style.setProperty('box-shadow', '0 10px 30px rgba(2, 132, 199, 0.2)', 'important');
        if (head1) head1.innerHTML = '👑 GRAN CONJUNTO IMPERIAL (M1 + M2 + M3) • 10 A 14 PERSONAS';

        if (box1) {
          box1.style.setProperty('width', '820px', 'important');
          box1.style.setProperty('height', '230px', 'important');
          box1.style.setProperty('position', 'relative', 'important');
          box1.style.setProperty('display', 'flex', 'important');
          box1.style.setProperty('align-items', 'center', 'important');
          box1.style.setProperty('justify-content', 'center', 'important');
          box1.innerHTML = `
            <div id="table-circle-1" class="table-square-fixed" style="width: 660px !important; height: 104px !important; border-radius: 18px !important; background: #fffbeb !important; border: 3px solid #f59e0b !important; box-shadow: 0 4px 16px rgba(245, 158, 11, 0.25) !important; display: flex !important; align-items: stretch !important; position: relative !important; cursor: pointer !important; z-index: 10 !important;">
              <div style="flex: 1 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; border-right: 2px dashed #f59e0b !important;">
                <span style="font-size: 18px !important; font-weight: 900 !important; color: #92400e !important; line-height: 1 !important;">M1</span>
                <span style="font-size: 9px !important; font-weight: 800 !important; color: #d97706 !important; text-transform: uppercase !important; margin-top: 2px !important;">Sector 1</span>
              </div>
              <div style="flex: 1.2 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; border-right: 2px dashed #f59e0b !important;">
                <span style="font-size: 18px !important; font-weight: 900 !important; color: #92400e !important; line-height: 1 !important;">M2</span>
                <span style="font-size: 9px !important; font-weight: 800 !important; color: #d97706 !important; text-transform: uppercase !important; margin-top: 2px !important;">Sector 2</span>
              </div>
              <div style="flex: 1 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important;">
                <span style="font-size: 18px !important; font-weight: 900 !important; color: #92400e !important; line-height: 1 !important;">M3</span>
                <span style="font-size: 9px !important; font-weight: 800 !important; color: #d97706 !important; text-transform: uppercase !important; margin-top: 2px !important;">Sector 3</span>
              </div>
              <div style="position: absolute !important; left: 50% !important; top: 50% !important; transform: translate(-50%, -50%) !important; background: #1e3a5f !important; color: #ffffff !important; padding: 4px 14px !important; border-radius: 12px !important; font-size: 10px !important; font-weight: 800 !important; white-space: nowrap !important; box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important; z-index: 15 !important;">
                👑 GRAN BANQUETE IMPERIAL (12-14 Pax)
              </div>
            </div>
          `;

          let busy1 = 0, busy2 = 0, busy3 = 0;

          // Cabecera Izquierda (M1-S4)
          busy1 += renderChairBadge(1, 4, 'left: 4px; top: 50%; transform: translateY(-50%);', box1, true);

          // Fila Superior (5 sillas)
          busy1 += renderChairBadge(1, 1, 'top: 2px; left: 16%; transform: translateX(-50%);', box1, true);
          busy1 += renderChairBadge(1, 2, 'top: 2px; left: 32%; transform: translateX(-50%);', box1, true);
          busy2 += renderChairBadge(2, 1, 'top: 2px; left: 50%; transform: translateX(-50%);', box1, true);
          busy3 += renderChairBadge(3, 1, 'top: 2px; left: 68%; transform: translateX(-50%);', box1, true);
          busy3 += renderChairBadge(3, 2, 'top: 2px; left: 84%; transform: translateX(-50%);', box1, true);

          // Arrimada M2-S5
          if (window.palapaState.cuentas['2-5']) {
            const pos = window.palapaState.cuentas['2-5'].posicionArrimada || 'top';
            const offCss = pos === 'top'
              ? 'top: 2px; left: calc(50% + 56px);'
              : pos === 'bottom'
                ? 'bottom: 2px; left: calc(50% + 56px);'
                : pos === 'right'
                  ? 'right: 4px; top: calc(50% - 44px);'
                  : 'left: 4px; top: calc(50% - 44px);';
            busy2 += renderChairBadge(2, 5, offCss, box1, true);
          }

          // Fila Inferior (5 sillas)
          busy1 += renderChairBadge(1, 3, 'bottom: 2px; left: 16%; transform: translateX(-50%);', box1, true);
          busy2 += renderChairBadge(2, 4, 'bottom: 2px; left: 32%; transform: translateX(-50%);', box1, true);
          busy2 += renderChairBadge(2, 3, 'bottom: 2px; left: 50%; transform: translateX(-50%);', box1, true);
          busy3 += renderChairBadge(3, 4, 'bottom: 2px; left: 68%; transform: translateX(-50%);', box1, true);
          busy3 += renderChairBadge(3, 3, 'bottom: 2px; left: 84%; transform: translateX(-50%);', box1, true);

          // Cabecera Derecha (M3-S4 o S2)
          busy3 += renderChairBadge(3, 2, 'right: 4px; top: 50%; transform: translateY(-50%);', box1, true);

          const totalBusyImperial = busy1 + busy2 + busy3;
          if (label1) {
            label1.style.color = totalBusyImperial > 0 ? '#d97706' : '#059669';
            label1.innerHTML = totalBusyImperial > 0
              ? `🟡 Ocupada (${totalBusyImperial} Comensales: ${busy1} de M1 + ${busy2} de M2 + ${busy3} de M3)`
              : `🟢 Gran Banquete Imperial Disponible (12-14 Pax)`;
          }
        }

        card2.style.setProperty('display', 'none', 'important');
        card3.style.setProperty('display', 'none', 'important');

        // MODO 4: MESAS INDIVIDUALES ESTÁNDAR (TRES CUADRADOS INDEPENDIENTES)
      } else if (grid && card1 && card2 && card3) {
        grid.style.setProperty('grid-template-columns', 'repeat(3, 1fr)', 'important');

        [card1, card2, card3].forEach(c => {
          c.style.setProperty('display', 'flex', 'important');
          c.style.setProperty('border', '1px solid #dce8f5', 'important');
          c.style.setProperty('background', '#f8fbff', 'important');
          c.style.setProperty('box-shadow', 'none', 'important');
        });

        if (head1) head1.innerHTML = 'Mesa 1 (Palapa)';
        if (head2) head2.innerHTML = 'Mesa 2 (Palapa)';
        if (head3) head3.innerHTML = 'Mesa 3 (Palapa)';

        [box1, box2, box3].forEach(b => {
          if (b) {
            b.style.setProperty('width', '250px', 'important');
            b.style.setProperty('height', '230px', 'important');
            b.style.setProperty('position', 'relative', 'important');
            b.style.setProperty('display', 'flex', 'important');
            b.style.setProperty('align-items', 'center', 'important');
            b.style.setProperty('justify-content', 'center', 'important');
          }
        });

        for (let m = 1; m <= 3; m++) {
          const currentBox = document.getElementById(`table-box-${m}`);
          const currentLabel = document.getElementById(`table-label-${m}`);
          let busyCount = 0;
          let arrimadasCount = 0;

          if (currentBox) {
            currentBox.innerHTML = `
              <div id="table-circle-${m}" class="table-square-fixed" onclick="window.clickMesa(${m});" style="width: 104px !important; height: 104px !important; border-radius: 16px !important; background: #ecfdf5 !important; border: 3px solid #10b981 !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; cursor: pointer !important; z-index: 10 !important;">
                <span style="font-size: 18px !important; font-weight: 900 !important; color: #065f46 !important; line-height: 1 !important;">M${m}</span>
                <span id="table-status-${m}" style="font-size: 9px !important; font-weight: 800 !important; color: #059669 !important; text-transform: uppercase !important; margin-top: 2px !important;">Libre</span>
              </div>
            `;

            // Sillas 1..4
            busyCount += renderChairBadge(m, 1, 'top: 2px; left: 50%; transform: translateX(-50%);', currentBox, false);
            busyCount += renderChairBadge(m, 2, 'right: 2px; top: 50%; transform: translateY(-50%);', currentBox, false);
            busyCount += renderChairBadge(m, 3, 'bottom: 2px; left: 50%; transform: translateX(-50%);', currentBox, false);
            busyCount += renderChairBadge(m, 4, 'left: 2px; top: 50%; transform: translateY(-50%);', currentBox, false);

            // Sillas Arrimadas (S5+) ubicadas según su posicionArrimada
            Object.keys(window.palapaState.cuentas).forEach(k => {
              const parts = k.split('-');
              if (parseInt(parts[0]) === m) {
                const sn = parseInt(parts[1]);
                if (sn >= 5) {
                  arrimadasCount++;
                  const pos = window.palapaState.cuentas[k].posicionArrimada || 'top';
                  const offsetCss = pos === 'top'
                    ? 'top: 2px; left: calc(50% + 56px);'
                    : pos === 'bottom'
                      ? 'bottom: 2px; left: calc(50% + 56px);'
                      : pos === 'right'
                        ? 'right: 2px; top: calc(50% - 44px);'
                        : 'left: 2px; top: calc(50% - 44px);';
                  busyCount += renderChairBadge(m, sn, offsetCss, currentBox, false);
                }
              }
            });

            const currentCircle = document.getElementById(`table-circle-${m}`);
            const currentStatus = document.getElementById(`table-status-${m}`);

            if (currentCircle) {
              if (busyCount > 0) {
                currentCircle.style.background = "#fffbeb";
                currentCircle.style.border = "3px solid #f59e0b";
                currentCircle.style.color = "#92400e";
                currentCircle.style.boxShadow = "0 2px 8px rgba(245, 158, 11, 0.2)";
                if (currentStatus) {
                  currentStatus.innerText = `${busyCount} Ocupada${busyCount > 1 ? 's' : ''}`;
                  currentStatus.style.color = "#d97706";
                }
                if (currentLabel) {
                  currentLabel.style.color = "#d97706";
                  currentLabel.innerText = `🟡 Ocupada (${busyCount} Comensal${busyCount > 1 ? 'es' : ''}${arrimadasCount > 0 ? ' • ' + arrimadasCount + ' Arrimada' : ''})`;
                }
              } else {
                currentCircle.style.background = "#ecfdf5";
                currentCircle.style.border = "3px solid #10b981";
                currentCircle.style.color = "#065f46";
                currentCircle.style.boxShadow = "0 2px 8px rgba(16, 185, 129, 0.2)";
                if (currentStatus) {
                  currentStatus.innerText = `Libre`;
                  currentStatus.style.color = "#059669";
                }
                if (currentLabel) {
                  currentLabel.style.color = "#059669";
                  currentLabel.innerText = `🟢 Disponible`;
                }
              }
            }
          }
        }
      }

      // 3. Renderizar Sidebar de Comanda (si está en modo comanda activa)
      if (isComandaMode) {
        const mesaId = window.palapaState.mesaSeleccionadaId || 2;
        const sillaNum = (window.palapaState.sillaSeleccionadaNum !== null && window.palapaState.sillaSeleccionadaNum !== undefined) ? window.palapaState.sillaSeleccionadaNum : 1;
        const key = `${mesaId}-${sillaNum}`;
        const cuenta = window.palapaState.cuentas[key] || { items: [] };

        const titleEl = document.getElementById('sidebarTableTitle');
        const countEl = document.getElementById('sidebarTableOccupiedCount');
        if (titleEl) titleEl.innerText = `MESA ${mesaId} (PALAPA)`;

        let totalOcupadasMesa = 0;
        let totalArrimadas = 0;
        let sillasDeEstaMesa = [1, 2, 3, 4];
        Object.keys(window.palapaState.cuentas).forEach(k => {
          const parts = k.split('-');
          if (parseInt(parts[0]) === mesaId) {
            const sn = parseInt(parts[1]);
            const c = window.palapaState.cuentas[k];
            if (c && (c.estado === 'ocupada' || (c.items && c.items.length > 0))) {
              totalOcupadasMesa++;
              if (sn > 4) totalArrimadas++;
            }
            if (sn > 4 && sillasDeEstaMesa.indexOf(sn) === -1) {
              sillasDeEstaMesa.push(sn);
            }
          }
        });
        sillasDeEstaMesa.sort((a, b) => a - b);

        if (countEl) {
          if (totalArrimadas > 0) {
            countEl.innerText = `${totalOcupadasMesa} Comensales (${totalOcupadasMesa - totalArrimadas} Estándar + ${totalArrimadas} Arrimada${totalArrimadas > 1 ? 's' : ''})`;
          } else {
            countEl.innerText = `${totalOcupadasMesa} de 4 Sillas Ocupadas`;
          }
        }

        const targetEl = document.getElementById('sidebarTargetMesaSilla');
        const qrBadgeEl = document.getElementById('sidebarQrBadge');
        const comensalEl = document.getElementById('sidebarComensalNombre');
        const activeBadge = document.getElementById('activeTargetBadge');

        if (sillaNum === 0) {
          if (targetEl) targetEl.innerText = `⭐ Comanda de MESA (Al Centro)`;
          if (qrBadgeEl) qrBadgeEl.innerText = `MESA #${mesaId}`;
          if (comensalEl) comensalEl.innerText = `Consumos Compartidos / Platillos al Centro`;
          if (activeBadge) activeBadge.innerText = `Mesa ${mesaId} • Cuenta de Mesa`;
        } else {
          if (targetEl) targetEl.innerText = `🧾 Comanda Silla ${sillaNum}${sillaNum > 4 ? ' (Arrimada)' : ''}`;
          if (qrBadgeEl) qrBadgeEl.innerText = `QR: #${cuenta.qrId || ('PV-0' + mesaId + sillaNum)}`;
          if (comensalEl) comensalEl.innerText = cuenta.comensalNombre || `Comensal Silla ${sillaNum}`;
          if (activeBadge) activeBadge.innerText = `Mesa ${mesaId} • Silla ${sillaNum}`;
        }

        // Selector rápido de sillas de esta mesa (incluyendo Cuenta de Mesa al centro, sillas estándar 1..4 y sillas arrimadas 5+)
        const cardsGrid = document.getElementById('sidebarChairCardsGrid');
        if (cardsGrid) {
          cardsGrid.innerHTML = '';

          // 1. Tarjeta Especial: ⭐ Cuenta de MESA (Al Centro)
          const mesaKey = `${mesaId}-0`;
          const mesaCta = window.palapaState.cuentas[mesaKey];
          const isCurrentMesa = (sillaNum === 0);
          let subMesa = 0;
          let numItemsMesa = 0;
          if (mesaCta && mesaCta.items) {
            mesaCta.items.forEach(i => {
              if (!i.pagado) {
                numItemsMesa += (i.cantidad || 1);
                subMesa += (i.precio * i.cantidad);
              }
            });
          }
          const hasMesaConsumo = (numItemsMesa > 0);

          const mesaCard = document.createElement('div');
          mesaCard.onclick = function () { window.seleccionarSillaSidebar(0); };
          mesaCard.style.cssText = `grid-column: span 2 !important; padding: 8px 12px !important; border-radius: 10px !important; cursor: pointer !important; transition: all 0.2s !important; display: flex !important; justify-content: space-between !important; align-items: center !important; background: ${isCurrentMesa ? 'rgba(234, 179, 8, 0.25)' : (hasMesaConsumo ? 'rgba(234, 179, 8, 0.12)' : 'rgba(30, 41, 59, 0.6)')} !important; border: ${isCurrentMesa ? '2px solid #eab308' : (hasMesaConsumo ? '1.5px solid #ca8a04' : '1px solid #334155')} !important; ${isCurrentMesa ? 'box-shadow: 0 0 14px rgba(234, 179, 8, 0.4) !important;' : ''}`;
          mesaCard.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 14px;">⭐</span>
              <div style="display: flex; flex-direction: column;">
                <span style="font-weight: 900; font-size: 11px; color: ${isCurrentMesa ? '#fef08a' : '#facc15'};">Cuenta de MESA (Al Centro)</span>
                <span style="font-size: 9px; color: #94a3b8;">${hasMesaConsumo ? `${numItemsMesa} platillo(s) al centro` : 'Platillos compartidos'}</span>
              </div>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px; background: ${hasMesaConsumo ? '#ca8a04' : '#1e293b'}; color: #ffffff; display: block;">${hasMesaConsumo ? '🟠 CON CONSUMO' : '⚪ VACÍA'}</span>
              <span style="font-size: 11px; font-weight: 900; color: #facc15; margin-top: 2px; display: block;">$${subMesa.toFixed(2)}</span>
            </div>
          `;
          cardsGrid.appendChild(mesaCard);

          sillasDeEstaMesa.forEach(s => {
            const sKey = `${mesaId}-${s}`;
            const sCta = window.palapaState.cuentas[sKey];
            const isPaidSilla = !!(sCta && (sCta.estado === 'pagada' || sCta.pagado));
            const sOcc = !!(sCta && (sCta.estado === 'ocupada' || isPaidSilla || (sCta.items && sCta.items.length > 0)));
            const isCurrent = (s === sillaNum);
            const isExtra = (s > 4);

            let subSilla = 0;
            let saldoSilla = 0;
            let numItems = 0;
            if (sCta && sCta.items) {
              sCta.items.forEach(i => {
                const itSub = (i.precio * i.cantidad);
                subSilla += itSub;
                if (!i.pagado && !isPaidSilla) {
                  numItems += (i.cantidad || 1);
                  saldoSilla += itSub;
                }
              });
            }

            // Colores temáticos 100% consistentes con el plano de mesas
            let bgCard, borderCard, titleColor, badgeBg, badgeColor, badgeTxt, montoColor, montoTxt;

            if (isPaidSilla) {
              // AZUL: Cuenta Pagada / Sobremesa
              bgCard = isCurrent ? 'rgba(2, 132, 199, 0.28)' : 'rgba(2, 132, 199, 0.15)';
              borderCard = isCurrent ? '2px solid #38bdf8' : '1.5px solid #0284c7';
              titleColor = '#38bdf8';
              badgeBg = '#0284c7';
              badgeColor = '#ffffff';
              badgeTxt = isCurrent ? '● ATENDIENDO (PAGADA)' : '🔵 PAGADA ✓';
              montoColor = '#38bdf8';
              montoTxt = (saldoSilla === 0) ? '$0.00 pend.' : `$${saldoSilla.toFixed(2)}`;
            } else if (sOcc) {
              // NARANJA: Ocupada / Consumiendo
              bgCard = isCurrent ? 'rgba(245, 158, 11, 0.25)' : 'rgba(245, 158, 11, 0.12)';
              borderCard = isCurrent ? '2px solid #fbbf24' : '1.5px solid #f59e0b';
              titleColor = '#fbbf24';
              badgeBg = '#d97706';
              badgeColor = '#ffffff';
              badgeTxt = isCurrent ? '● ATENDIENDO' : '🟠 OCUPADA';
              montoColor = '#fbbf24';
              montoTxt = `$${subSilla.toFixed(2)}`;
            } else {
              // VERDE: Disponible / Libre
              bgCard = isCurrent ? 'rgba(5, 150, 105, 0.25)' : 'rgba(5, 150, 105, 0.12)';
              borderCard = isCurrent ? '2px solid #34d399' : '1.5px solid #10b981';
              titleColor = '#34d399';
              badgeBg = '#059669';
              badgeColor = '#ffffff';
              badgeTxt = isCurrent ? '● ATENDIENDO' : '🟢 LIBRE';
              montoColor = '#64748b';
              montoTxt = '$0.00';
            }

            const card = document.createElement('div');
            card.onclick = (function (sn) { return function () { window.seleccionarSillaSidebar(sn); }; })(s);
            card.style.cssText = `padding: 8px 10px !important; border-radius: 10px !important; cursor: pointer !important; transition: all 0.2s !important; display: flex !important; flex-direction: column !important; gap: 2px !important; background: ${bgCard} !important; border: ${borderCard} !important; ${isCurrent ? 'box-shadow: 0 0 14px rgba(56, 189, 248, 0.35) !important;' : ''}`;

            card.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 900; font-size: 11px; color: ${titleColor};">
                  Silla ${s} ${isExtra ? '<span style="font-size: 9px; color: #38bdf8; font-weight: 800;">(Extra 🪑)</span>' : ''}
                </span>
                <span style="font-size: 9px; font-weight: 900; padding: 2px 6px; border-radius: 4px; background: ${badgeBg}; color: ${badgeColor};">${badgeTxt}</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 2px;">
                <span style="font-size: 9px; color: ${sOcc ? '#fbbf24' : '#94a3b8'};">${isPaidSilla ? 'En Sobremesa' : (sOcc ? (numItems > 0 ? `${numItems} prod.` : 'En Menú (QR)') : 'Disponible')}</span>
                <span style="font-size: 11px; font-weight: 900; color: ${montoColor};">${montoTxt}</span>
              </div>
            `;
            cardsGrid.appendChild(card);
          });
        }

        // Lista de items de la comanda en tiempo real
        const itemsList = document.getElementById('sidebarComandaItemsList');
        let totalConsumos = 0;
        let saldoPendiente = 0;
        let pendientesCount = 0;
        const isPaidAccount = !!(cuenta.pagado || cuenta.estado === 'pagada');

        if (itemsList) {
          itemsList.innerHTML = '';
          if (isPaidAccount) {
            const bannerSobremesa = document.createElement('div');
            bannerSobremesa.style.cssText = 'background: rgba(2, 132, 199, 0.18) !important; border: 1.5px solid #0284c7 !important; border-radius: 10px !important; padding: 10px !important; margin-bottom: 8px !important; text-align: center !important;';
            bannerSobremesa.innerHTML = `
              <div style="font-size: 11px !important; font-weight: 900 !important; color: #38bdf8 !important;"><i class="fa-solid fa-circle-check"></i> Cuenta Pagada • Sobremesa</div>
              <div style="font-size: 10px !important; color: #cbd5e1 !important; margin-top: 2px !important;">Saldo pendiente: <b style="color: #34d399;">$0.00</b></div>
              <button onclick="window.liberarSillaActual();" style="margin-top: 6px !important; padding: 5px 12px !important; background: #ef4444 !important; color: #ffffff !important; border: none !important; border-radius: 6px !important; font-size: 10px !important; font-weight: 800 !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 4px !important;">
                <i class="fa-solid fa-broom"></i> Desocupar Silla (Se retiró)
              </button>
            `;
            itemsList.appendChild(bannerSobremesa);
          }

          if (!cuenta.items || cuenta.items.length === 0) {
            itemsList.innerHTML += `
              <div style="text-align: center; color: #64748b; font-size: 11px; padding: 25px 0;">
                <i class="fa-solid fa-utensils" style="font-size: 20px; display: block; margin-bottom: 6px; opacity: 0.5;"></i>
                No hay consumos en Silla ${sillaNum}.<br>Selecciona platillos del catálogo a la derecha.
              </div>
            `;
          } else {
            cuenta.items.forEach((it, idx) => {
              const itTotal = (it.precio || 0) * (it.cantidad || 1);
              totalConsumos += itTotal;
              const isItPaid = !!(it.pagado || isPaidAccount);
              if (!isItPaid) {
                saldoPendiente += itTotal;
              }
              if (!it.enviadoCocina) pendientesCount++;

              const row = document.createElement('div');
              row.style.cssText = 'display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 6px 8px; border-radius: 8px; border: 1px solid #1e293b; font-size: 11px;';
              row.innerHTML = `
                <div style="flex: 1; padding-right: 6px;">
                  <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="font-weight: 800; color: #ffffff;">${it.cantidad}x ${it.nombre}</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 6px; margin-top: 3px;">
                    <span style="font-size: 11px; font-weight: 900; color: ${isItPaid ? '#94a3b8' : '#34d399'};">$${itTotal.toFixed(2)}</span>
                    ${isItPaid
                  ? `<span style="background: rgba(2,132,199,0.25); border: 1px solid #0284c7; color: #38bdf8; font-size: 9px; font-weight: 800; padding: 1px 5px; border-radius: 4px;"><i class="fa-solid fa-check"></i> Pagado</span>`
                  : (it.enviadoCocina
                    ? (it.estadoCocina === 'listo'
                      ? `<span style="background: rgba(2,132,199,0.25); border: 1px solid #0284c7; color: #38bdf8; font-size: 9px; font-weight: 900; padding: 1px 5px; border-radius: 4px;"><i class="fa-solid fa-circle-check"></i> ¡Listo en Pase!</span>`
                      : (it.estadoCocina === 'preparando'
                        ? (((Date.now() - (it.timestampInicioCocina || it.timestampEnvioCocina || Date.now())) / 60000 >= 14)
                          ? `<span style="background: rgba(239,68,68,0.2); border: 1px solid #ef4444; color: #f87171; font-size: 9px; font-weight: 900; padding: 1px 5px; border-radius: 4px;"><i class="fa-solid fa-triangle-exclamation"></i> 🔴 Demorado</span>`
                          : `<span style="background: rgba(245,158,11,0.2); border: 1px solid #f59e0b; color: #fbbf24; font-size: 9px; font-weight: 800; padding: 1px 5px; border-radius: 4px;"><i class="fa-solid fa-fire"></i> 🟡 En Fuego</span>`)
                        : `<span style="background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.4); color: #34d399; font-size: 9px; font-weight: 800; padding: 1px 5px; border-radius: 4px;"><i class="fa-solid fa-clock"></i> 🟢 Recibido</span>`))
                    : `<div style="display: flex; align-items: center; gap: 4px;">
                            <span style="background: rgba(245,158,11,0.25); border: 1px solid #f59e0b; color: #fbbf24; font-size: 9px; font-weight: 800; padding: 1px 5px; border-radius: 4px;"><i class="fa-solid fa-clock"></i> Pendiente</span>
                            <button onclick="window.enviarItemIndividualACocina(${idx});" style="background: #f59e0b; color: #0f172a; border: none; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 900; cursor: pointer; display: flex; align-items: center; gap: 2px;" title="Enviar este producto a cocina ahora">🚀 Enviar</button>
                          </div>`)}
                  </div>
                </div>
                ${!isItPaid && !it.enviadoCocina
                  ? `<button onclick="window.eliminarItemSidebar(${idx});" style="background: transparent; border: none; color: #f87171; cursor: pointer; padding: 2px 4px; font-size: 12px;" title="Eliminar (Pendiente)">✕</button>`
                  : `<span style="color: #64748b; font-size: 10px; padding: 2px 4px;" title="${isItPaid ? 'Cuenta pagada' : 'En preparación en cocina'}"><i class="fa-solid fa-lock" style="font-size: 10px; opacity: 0.5;"></i></span>`}
              `;
              itemsList.appendChild(row);
            });
          }
        }

        const subtotalBase = saldoPendiente / 1.16;
        const iva = saldoPendiente - subtotalBase;
        const total = saldoPendiente;

        const subtotalEl = document.getElementById('sidebarSubtotal');
        const ivaEl = document.getElementById('sidebarIva');
        const totalEl = document.getElementById('sidebarTotal');
        if (subtotalEl) subtotalEl.innerText = `$${subtotalBase.toFixed(2)}`;
        if (ivaEl) ivaEl.innerText = `$${iva.toFixed(2)}`;
        if (totalEl) totalEl.innerText = `$${total.toFixed(2)}`;

        // Botón de Enviar a Cocina (KDS) por tramos
        const btnSendCocina = document.getElementById('btnSidebarEnviarCocina');
        const btnSendCocinaTxt = document.getElementById('btnSidebarEnviarCocinaTxt');
        if (btnSendCocina && btnSendCocinaTxt) {
          if (pendientesCount > 0) {
            btnSendCocina.disabled = false;
            btnSendCocina.style.opacity = '1';
            btnSendCocina.style.cursor = 'pointer';
            btnSendCocina.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
            btnSendCocina.style.color = '#0f172a';
            btnSendCocinaTxt.innerHTML = `<b>Enviar a Cocina / Barra</b> (${pendientesCount} pendiente${pendientesCount > 1 ? 's' : ''})`;
          } else if (cuenta.items && cuenta.items.length > 0) {
            btnSendCocina.disabled = true;
            btnSendCocina.style.opacity = '0.6';
            btnSendCocina.style.cursor = 'default';
            btnSendCocina.style.background = '#1e293b';
            btnSendCocina.style.color = '#34d399';
            btnSendCocinaTxt.innerHTML = `<i class="fa-solid fa-check-double"></i> Todo enviado a Cocina`;
          } else {
            btnSendCocina.disabled = true;
            btnSendCocina.style.opacity = '0.4';
            btnSendCocina.style.cursor = 'not-allowed';
            btnSendCocina.style.background = '#1e293b';
            btnSendCocina.style.color = '#94a3b8';
            btnSendCocinaTxt.innerHTML = `Enviar a Cocina / Barra`;
          }
        }
      }

      renderWaiterMenuGrid();
    }

    function renderWaiterMenuGrid() {
      const grid = document.getElementById('waiterMenuGrid');
      if (!grid) return;
      grid.innerHTML = '';

      if (!window.catalogProducts || window.catalogProducts.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 30px; color: #94a3b8; font-size: 13px;"><i class="fa-solid fa-circle-notch fa-spin" style="margin-right: 8px; color: #10b981;"></i>Cargando catálogo en tiempo real desde PostgreSQL...</div>';
        return;
      }

      const catFiltro = window.palapaState.categoriaFiltro || (window.catalogCategories && window.catalogCategories[0] ? window.catalogCategories[0].nombre : 'Bebidas & Jugos');
      let filtrados = window.catalogProducts.filter(p => p.categoria_nombre === catFiltro);
      if (filtrados.length === 0 && window.catalogProducts.length > 0) {
        filtrados = window.catalogProducts.filter(p => p.categoria_nombre === window.catalogProducts[0].categoria_nombre);
      }
      const sillaNum = (window.palapaState.sillaSeleccionadaNum !== null && window.palapaState.sillaSeleccionadaNum !== undefined) ? window.palapaState.sillaSeleccionadaNum : 1;

      filtrados.forEach(prod => {
        const card = document.createElement('div');
        card.style.cssText = 'background: #0f172a !important; border: 1px solid #1e293b !important; border-radius: 14px !important; padding: 12px 14px !important; display: flex !important; flex-direction: column !important; justify-content: space-between !important; gap: 10px !important; transition: all 0.2s ease !important; cursor: pointer !important;';

        card.innerHTML = `
          <div style="display: flex; align-items: flex-start; gap: 10px;" onclick="window.agregarPlatilloDirectoById(${prod.id});">
            <span style="font-size: 26px; padding: 4px; background: #020617; border-radius: 10px; border: 1px solid #1e293b;">${prod.icono}</span>
            <div style="flex: 1;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <span style="font-size: 12px; font-weight: 800; color: #ffffff; line-height: 1.2;">${prod.nombre}</span>
              </div>
              <span style="font-size: 10px; color: #94a3b8; display: block; line-height: 1.3; margin-top: 3px;">${prod.descripcion || ''}</span>
              <div style="display: flex; align-items: center; gap: 6px; margin-top: 6px;">
                <span style="font-size: 13px; font-weight: 900; color: #34d399;">$${prod.precio.toFixed(2)}</span>
                <span style="font-size: 9px; color: #38bdf8; font-weight: 700; background: rgba(56,189,248,0.15); padding: 1px 6px; border-radius: 4px;">⏱️ ${prod.tiempo || '8–10 min'}</span>
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 6px; border-top: 1px solid #1e293b; padding-top: 8px;">
            <button onclick="window.agregarPlatilloDirectoById(${prod.id});"
              style="flex: 1; padding: 7px 10px; background: ${sillaNum === 0 ? 'linear-gradient(135deg, #d97706, #b45309)' : '#059669'}; color: #ffffff; font-size: 11px; font-weight: 900; border-radius: 8px; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px; box-shadow: ${sillaNum === 0 ? '0 2px 8px rgba(217,119,6,0.4)' : 'none'};">
              ${sillaNum === 0 ? '<i class="fa-solid fa-plus"></i> ⭐ Al Centro (Mesa)' : ('<i class="fa-solid fa-plus"></i> Silla ' + sillaNum)}
            </button>
            <button onclick="event.stopPropagation(); window.abrirModalReceta(${prod.id});"
              style="padding: 7px 10px; background: #1e293b; color: #38bdf8; font-size: 10px; font-weight: 700; border-radius: 8px; border: 1px solid #334155; cursor: pointer; white-space: nowrap;">
              📖 Receta
            </button>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    window.agregarPlatilloDirectoById = function (prodId) {
      const prod = window.catalogProducts.find(p => p.id === prodId);
      if (prod) agregarPlatilloDirecto(prod);
    };

    window.abrirModalReceta = function (prodId) {
      const prod = window.catalogProducts.find(p => p.id === prodId);
      if (!prod) return;

      document.getElementById('recetaIcono').innerText = prod.icono || '🍳';
      document.getElementById('recetaCategoria').innerText = prod.categoria_nombre || 'Desayuno';
      document.getElementById('recetaTitulo').innerText = prod.nombre;
      document.getElementById('recetaTiempo').innerText = prod.tiempo || '8–10 min';
      document.getElementById('recetaPorcion').innerText = prod.porciones || '1 persona';
      document.getElementById('recetaPrecio').innerText = `$${Number(prod.precio).toFixed(2)}`;

      const listIng = document.getElementById('recetaIngredientesList');
      if (listIng) {
        listIng.innerHTML = '';
        (prod.ingredientes || ['Ingredientes frescos de temporada']).forEach(ing => {
          const li = document.createElement('li');
          li.innerText = ing;
          listIng.appendChild(li);
        });
      }

      const listPasos = document.getElementById('recetaPasosList');
      if (listPasos) {
        listPasos.innerHTML = '';
        (prod.pasos || ['Preparar al momento con ingredientes frescos.']).forEach(paso => {
          const li = document.createElement('li');
          li.innerText = paso;
          listPasos.appendChild(li);
        });
      }

      const boxAdic = document.getElementById('boxRecetaAdicionales');
      const listAdic = document.getElementById('recetaAdicionalesList');
      if (boxAdic && listAdic) {
        if (prod.adicionales && prod.adicionales.length > 0) {
          boxAdic.style.display = 'block';
          listAdic.innerHTML = '';
          prod.adicionales.forEach(adic => {
            const chip = document.createElement('span');
            chip.style.cssText = 'background: #020617; border: 1px solid #0284c7; color: #7dd3fc; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px;';
            chip.innerText = `+ ${adic}`;
            listAdic.appendChild(chip);
          });
        } else {
          boxAdic.style.display = 'none';
        }
      }

      const boxNotas = document.getElementById('boxRecetaNotas');
      const textNotas = document.getElementById('recetaNotasTexto');
      if (boxNotas && textNotas) {
        if (prod.notas) {
          boxNotas.style.display = 'block';
          textNotas.innerText = prod.notas;
        } else {
          boxNotas.style.display = 'none';
        }
      }

      const modal = document.getElementById('modalRecetaBackdrop');
      if (modal) {
        modal.style.display = 'flex';
      }
    };

    window.cerrarModalReceta = function () {
      const modal = document.getElementById('modalRecetaBackdrop');
      if (modal) {
        modal.style.display = 'none';
      }
    };

    function agregarPlatilloDirecto(prod) {
      const mesaId = window.palapaState.mesaSeleccionadaId || 2;
      let sillaNum = window.palapaState.sillaSeleccionadaNum;

      if (sillaNum === null || sillaNum === undefined) {
        sillaNum = 1;
        window.palapaState.sillaSeleccionadaNum = 1;
      }

      const esMesa = (sillaNum === 0);
      const key = `${mesaId}-${sillaNum}`;
      if (!window.palapaState.cuentas[key]) {
        window.palapaState.cuentas[key] = {
          estado: 'ocupada',
          qrId: esMesa ? `MESA-0${mesaId}` : `PV-0${mesaId}${sillaNum}`,
          comensalNombre: esMesa ? '⭐ Cuenta de MESA (Al Centro)' : ('Comensal Silla ' + sillaNum),
          items: [],
          historialUbicaciones: [{ mesaId: mesaId, sillaNum: sillaNum, hora: (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]
        };
      } else {
        // Si estaba pagada en sobremesa, al pedir nuevo consumo pasa a estado ocupada con saldo pendiente
        window.palapaState.cuentas[key].estado = 'ocupada';
        window.palapaState.cuentas[key].pagado = false;
      }

      // Clasificación del producto
      const catNombre = prod.categoria_nombre || '';
      let tipoConsumo = 'comida';
      if (/café|infusión|infusiones|bebida|coctelería|jugo|refresco|cerveza|agua|té|americano|capuchino|chocolate/i.test(catNombre) || /café|jugo|cerveza|refresco|agua|té|capuchino/i.test(prod.nombre || '')) {
        tipoConsumo = 'bebida';
      } else if (/repostería|postre|postres|pastel|dulce|waffles|hotcakes/i.test(catNombre)) {
        tipoConsumo = 'postre_extra';
      }

      const nowStr = (new Date()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const items = window.palapaState.cuentas[key].items;
      const existing = items.find(i => i.id === prod.id && i.mesaId === mesaId && i.sillaNum === sillaNum && !i.enviadoCocina && !i.pagado);
      if (existing) {
        existing.cantidad += 1;
      } else {
        items.push({
          id: prod.id,
          nombre: prod.nombre,
          notas: esMesa ? 'Al centro para compartir' : '',
          precio: prod.precio,
          cantidad: 1,
          mesaId: mesaId,
          sillaNum: sillaNum,
          es_cuenta_mesa: esMesa,
          tipo_consumo: tipoConsumo,
          hora: nowStr,
          enviadoCocina: false,
          pagado: false
        });
      }

      saveStateToStorage();
      renderStateUI();
      try {
        if (typeof window.anvilSyncCuenta === 'function') {
          const syncSilla = (sillaNum === 'centro') ? 0 : (sillaNum || 0);
          window.anvilSyncCuenta(mesaId, syncSilla, JSON.stringify(window.palapaState.cuentas[key].items), 'ocupada');
        }
      } catch (err) {
        console.warn('Error sincronizando con servidor al agregar platillo:', err);
      }
      const modalBackdrop = document.getElementById('modalComandaBackdrop');
      if (modalBackdrop && modalBackdrop.classList.contains('show')) {
        abrirModalComandaActual();
      }
      const destinoTxt = esMesa ? '⭐ Cuenta de MESA (Al Centro)' : `Silla ${sillaNum}`;
      showDragToast(`➕ ${prod.nombre} agregado a ${destinoTxt} (Pendiente de enviar)`, 'ok');
    }

    window.agregarPlatilloDirecto = agregarPlatilloDirecto;

    window.filtrarCategoria = function (catNombre) {
      window.palapaState.categoriaFiltro = catNombre;

      const container = document.getElementById('waiterCatChips');
      if (container) {
        const buttons = container.querySelectorAll('button');
        buttons.forEach(function (btn) {
          if (btn.dataset.cat === catNombre) {
            btn.style.background = "#059669";
            btn.style.color = "#ffffff";
            btn.style.border = "1px solid #34d399";
          } else {
            btn.style.background = "#1e293b";
            btn.style.color = "#cbd5e1";
            btn.style.border = "1px solid #334155";
          }
        });
      }

      renderWaiterMenuGrid();
    };

    function filtrarCategoria(catNombre) {
      window.filtrarCategoria(catNombre);
    }

    // Exponer funciones clave globalmente para que Python y llamadas onclick directas puedan interactuar
    window.renderStateUI = renderStateUI;
    window.setupDragListeners = setupDragListeners;
    window.handleSillaClick = handleSillaClick;
    window.handleMesaClick = handleMesaClick;
    window.clickSilla = handleSillaClick;
    window.clickMesa = handleMesaClick;
    window.agregarPlatilloDirecto = agregarPlatilloDirecto;
    window.initPOSMesero = function() {
      try {
        renderStateUI();
        setupDragListeners();
      } catch (err) {
        console.warn("[initPOSMesero] Error inicializando UI:", err);
      }
    };

    try {
      renderStateUI();
      setupDragListeners();
    } catch (e) {
      console.warn("[POSMesero] renderStateUI inicial:", e);
    }
    setTimeout(function () {
      try { renderStateUI(); setupDragListeners(); } catch (e) {}
    }, 300);
  })();
