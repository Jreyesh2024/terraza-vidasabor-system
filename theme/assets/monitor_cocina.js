// MONITOR DE COCINA & BARRA (KDS) - LA TERRAZA DE VIDA & SABOR
// Lógica de Producción, Semáforo de Tiempos, Fuego y Despacho en Tiempo Real

(function () {
  'use strict';

  // 1. BASE DE DATOS DE RECETAS ESTANDARIZADAS DESDE POSTGRESQL
  window.recetarioCocinaDB = {};
  window.mesasCocinaDB = {};
  window.areasCocinaDB = [];

  window.setRecetarioFromDB = function (recetasJson) {
    try {
      const list = typeof recetasJson === 'string' ? JSON.parse(recetasJson) : recetasJson;
      if (Array.isArray(list)) {
        list.forEach(function (r) {
          window.recetarioCocinaDB[r.nombre] = r;
          window.recetarioCocinaDB[r.nombre.toLowerCase().trim()] = r;
        });
      }
    } catch (e) {
      console.error('Error cargando recetario desde DB:', e);
    }
  };

  window.setKDSCuentasFromDB = function (cuentasJson) {
    try {
      const cuentas = typeof cuentasJson === 'string' ? JSON.parse(cuentasJson) : cuentasJson;
      if (cuentas && typeof cuentas === 'object') {
        window.kdsCuentasServer = cuentas;
        if (typeof window.cargarKDS === 'function') {
          window.cargarKDS();
        }
      }
    } catch (e) {
      console.error('Error cargando cuentas en KDS desde DB:', e);
    }
  };

  function syncKDSItemToAllStoragesAndServer(keyCuenta, idxInCuenta, newEstado, newTimestamp, itemId) {
    if (!keyCuenta) return;
    var parts = keyCuenta.split('-');
    var mesaId = parseInt(parts[0]) || 1;
    var sillaNum = parseInt(parts[1]) || 0;

    // 1. En window.kdsCuentasServer
    var updatedItems = null;
    if (window.kdsCuentasServer && window.kdsCuentasServer[keyCuenta]) {
      var ctaSrv = window.kdsCuentasServer[keyCuenta];
      if (ctaSrv.items && ctaSrv.items[idxInCuenta]) {
        ctaSrv.items[idxInCuenta].estadoCocina = newEstado;
        ctaSrv.items[idxInCuenta].estado = (newEstado === 'preparando' ? 'en_preparacion' : (newEstado === 'listo' ? 'listo' : (newEstado === 'servido' ? 'servido' : 'enviado_cocina')));
        if (newTimestamp) ctaSrv.items[idxInCuenta].timestampInicioCocina = newTimestamp;
        updatedItems = ctaSrv.items;
        if (!itemId && ctaSrv.items[idxInCuenta].id) itemId = ctaSrv.items[idxInCuenta].id;
      }
    }

    // 2. En palapa_croquis_state_v1
    try {
      var raw = localStorage.getItem('palapa_croquis_state_v1');
      if (raw) {
        var state = JSON.parse(raw);
        if (state && state.cuentas && state.cuentas[keyCuenta] && state.cuentas[keyCuenta].items) {
          if (state.cuentas[keyCuenta].items[idxInCuenta]) {
            state.cuentas[keyCuenta].items[idxInCuenta].estadoCocina = newEstado;
            state.cuentas[keyCuenta].items[idxInCuenta].estado = (newEstado === 'preparando' ? 'en_preparacion' : (newEstado === 'listo' ? 'listo' : (newEstado === 'servido' ? 'servido' : 'enviado_cocina')));
            if (newTimestamp) state.cuentas[keyCuenta].items[idxInCuenta].timestampInicioCocina = newTimestamp;
            localStorage.setItem('palapa_croquis_state_v1', JSON.stringify(state));
            sessionStorage.setItem('palapa_croquis_state_v1', JSON.stringify(state));
            if (!updatedItems) updatedItems = state.cuentas[keyCuenta].items;
            if (!itemId && state.cuentas[keyCuenta].items[idxInCuenta].id) itemId = state.cuentas[keyCuenta].items[idxInCuenta].id;
          }
        }
      }
    } catch (e) { }

    // 3. En palapa_cuentas_v1
    try {
      var rawCuentas = localStorage.getItem('palapa_cuentas_v1');
      if (rawCuentas) {
        var ctas = JSON.parse(rawCuentas);
        if (ctas && ctas[keyCuenta] && ctas[keyCuenta].items) {
          if (ctas[keyCuenta].items[idxInCuenta]) {
            ctas[keyCuenta].items[idxInCuenta].estadoCocina = newEstado;
            ctas[keyCuenta].items[idxInCuenta].estado = (newEstado === 'preparando' ? 'en_preparacion' : (newEstado === 'listo' ? 'listo' : (newEstado === 'servido' ? 'servido' : 'enviado_cocina')));
            if (newTimestamp) ctas[keyCuenta].items[idxInCuenta].timestampInicioCocina = newTimestamp;
            localStorage.setItem('palapa_cuentas_v1', JSON.stringify(ctas));
            sessionStorage.setItem('palapa_cuentas_v1', JSON.stringify(ctas));
            if (!updatedItems) updatedItems = ctas[keyCuenta].items;
            if (!itemId && ctas[keyCuenta].items[idxInCuenta].id) itemId = ctas[keyCuenta].items[idxInCuenta].id;
          }
        }
      }
    } catch (e) { }

    // 4. En window.palapaState si existe
    if (window.palapaState && window.palapaState.cuentas && window.palapaState.cuentas[keyCuenta]) {
      var pItems = window.palapaState.cuentas[keyCuenta].items;
      if (pItems && pItems[idxInCuenta]) {
        pItems[idxInCuenta].estadoCocina = newEstado;
        pItems[idxInCuenta].estado = (newEstado === 'preparando' ? 'en_preparacion' : (newEstado === 'listo' ? 'listo' : (newEstado === 'servido' ? 'servido' : 'enviado_cocina')));
        if (newTimestamp) pItems[idxInCuenta].timestampInicioCocina = newTimestamp;
        if (!updatedItems) updatedItems = pItems;
        if (!itemId && pItems[idxInCuenta].id) itemId = pItems[idxInCuenta].id;
      }
    }

    // 5. Persistir en PostgreSQL directamente
    if (itemId && typeof window.anvilCambiarEstadoItemCocina === 'function') {
      try {
        window.anvilCambiarEstadoItemCocina(itemId, newEstado);
      } catch (err) {
        console.warn('Error llamando anvilCambiarEstadoItemCocina:', err);
      }
    }

    // 6. Enviar actualización al servidor Python / Uplink
    if (updatedItems && typeof window.anvilSyncCuenta === 'function') {
      try {
        window.anvilSyncCuenta(mesaId, sillaNum, JSON.stringify(updatedItems), 'ocupada');
      } catch (err) {
        console.warn('Error sincronizando estado de cocina con servidor:', err);
      }
    }
  }

  window.setMesasCocinaFromDB = function (mesasJson, areasJson) {
    try {
      const mesas = typeof mesasJson === 'string' ? JSON.parse(mesasJson) : mesasJson;
      if (Array.isArray(mesas)) {
        mesas.forEach(function (m) {
          window.mesasCocinaDB[m.id] = m;
          window.mesasCocinaDB[m.numero_mesa] = m;
        });
      }
    } catch (e) {
      console.error('Error cargando mesas en KDS:', e);
    }

    try {
      const areas = typeof areasJson === 'string' ? JSON.parse(areasJson) : areasJson;
      if (Array.isArray(areas) && areas.length > 0) {
        window.areasCocinaDB = areas;
        renderKDSAreaChips();
      }
    } catch (e) {
      console.error('Error cargando areas en KDS:', e);
    }
  };

  function renderKDSAreaChips() {
    const container = document.getElementById('kdsAreaChips');
    if (!container || !window.areasCocinaDB || window.areasCocinaDB.length === 0) return;
    container.innerHTML = '';

    const btnTodas = document.createElement('button');
    btnTodas.id = 'chipArea-TODAS';
    btnTodas.setAttribute('data-area', 'TODAS');
    btnTodas.onclick = function () { window.filtrarAreaKDS('TODAS'); };
    const isTodas = (window.kdsState.areaFiltro === 'TODAS');
    btnTodas.style.cssText = 'padding: 5px 12px; font-size: 11px; font-weight: 800; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 4px; ' +
      (isTodas ? 'border: 1px solid #38bdf8; background: #38bdf8; color: #0f172a;' : 'border: 1px solid #334155; background: #0f172a; color: #cbd5e1;');
    btnTodas.innerHTML = '🏢 Todas las Áreas';
    container.appendChild(btnTodas);

    window.areasCocinaDB.forEach(function (area) {
      const btn = document.createElement('button');
      const areaName = area.nombre;
      btn.id = 'chipArea-' + area.id;
      btn.setAttribute('data-area', areaName);
      btn.onclick = function () { window.filtrarAreaKDS(areaName); };
      const isActive = (window.kdsState.areaFiltro === areaName);
      btn.style.cssText = 'padding: 5px 12px; font-size: 11px; font-weight: 800; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 4px; ' +
        (isActive ? 'border: 1px solid #38bdf8; background: #38bdf8; color: #0f172a;' : 'border: 1px solid #334155; background: #0f172a; color: #cbd5e1;');
      btn.innerHTML = (area.icono ? (area.icono + ' ') : '📍 ') + areaName;
      container.appendChild(btn);
    });
  }

  // 2. ESTADO LOCAL DEL KDS (ÁREAS, MESAS Y ESTACIONES)
  window.kdsState = {
    areaFiltro: 'TODAS', // TODAS, PALAPA, PATIO, CHIMENEA
    mesaFiltro: 'TODAS', // TODAS, '1', '2', '3', etc.
    estacionFiltro: 'TODAS', // TODAS, COCINA, BARRA, REPOSTERIA, INFANTIL
    tickets: []
  };

  // Reloj en tiempo real
  function updateClock() {
    const clockEl = document.getElementById('kdsClock');
    if (clockEl) {
      const now = new Date();
      clockEl.innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
  }
  setInterval(updateClock, 1000);
  updateClock();

  // Mapeo dinámico de Mesas a Áreas desde PostgreSQL
  function getTableArea(mesaId) {
    const m = window.mesasCocinaDB && (window.mesasCocinaDB[mesaId] || window.mesasCocinaDB[parseInt(mesaId)]);
    if (m && m.area_nombre) {
      let idArea = 'PALAPA';
      const an = m.area_nombre.toUpperCase();
      if (an.includes('PATIO')) idArea = 'PATIO';
      else if (an.includes('CHIMENEA')) idArea = 'CHIMENEA';
      else if (an.includes('JARDÍN') || an.includes('JARDIN')) idArea = 'JARDIN';
      else if (an.includes('BARRA') || an.includes('PALAPA')) idArea = 'PALAPA';
      return { id: idArea, nombre: m.area_nombre };
    }
    const id = parseInt(mesaId);
    if (id >= 1 && id <= 3) return { id: 'PALAPA', nombre: 'La Palapa' };
    if (id >= 4 && id <= 6) return { id: 'PATIO', nombre: 'Terraza / Patio' };
    if (id >= 7 && id <= 9) return { id: 'CHIMENEA', nombre: 'La Chimenea' };
    return { id: 'PALAPA', nombre: 'Área General' };
  }

  // Determinar estación/categoría de cada producto dinámicamente desde PostgreSQL
  function getProductStation(nombre) {
    const r = window.recetarioCocinaDB && (window.recetarioCocinaDB[nombre] || window.recetarioCocinaDB[(nombre || '').toLowerCase().trim()]);
    if (r && r.estacion_preparacion) {
      const est = r.estacion_preparacion.toUpperCase();
      if (est.includes('BARRA') || est.includes('CAFÉ') || est.includes('BEBIDA')) return 'BARRA';
      if (est.includes('REPOSTERIA') || est.includes('POSTRE')) return 'REPOSTERIA';
      if (est.includes('INFANTIL') || est.includes('KIDS')) return 'INFANTIL';
      return 'COCINA';
    }
    const n = (nombre || '').toLowerCase();
    if (n.includes('infantil') || n.includes('niño') || n.includes('kids') || n.includes('mini')) {
      return 'INFANTIL';
    } else if (n.includes('café') || n.includes('capuchino') || n.includes('espresso') || n.includes('jugo') || n.includes('limonada') || n.includes('té') || n.includes('refresco') || n.includes('bebida') || n.includes('agua') || n.includes('chocolate')) {
      return 'BARRA';
    } else if (n.includes('waffle') || n.includes('hotcake') || n.includes('crepa') || n.includes('pastel') || n.includes('fruta') || n.includes('dulce')) {
      return 'REPOSTERIA';
    } else {
      return 'COCINA';
    }
  }

  // 3. CARGAR COMANDAS DESDE STORAGE / PALAPA STATE (DESGLOSE POR COMENSAL / COLUMNAS)
  window.cargarKDS = function () {
    if (typeof window.syncStorageWithGlobal === 'function') {
      window.syncStorageWithGlobal();
    }

    var requestedMesa = localStorage.getItem('kds_filtro_mesa');
    if (requestedMesa && requestedMesa !== 'TODAS') {
      window.kdsState.mesaFiltro = requestedMesa;
    }

    var state = null;
    if (window.kdsCuentasServer && typeof window.kdsCuentasServer === 'object' && Object.keys(window.kdsCuentasServer).length > 0) {
      state = { cuentas: window.kdsCuentasServer };
    } else {
      var raw = localStorage.getItem('palapa_cuentas_v1') || localStorage.getItem('palapa_croquis_state_v1');
      if (raw) {
        try {
          var parsed = JSON.parse(raw);
          state = (parsed && parsed.cuentas) ? parsed : { cuentas: parsed };
        } catch (e) { }
      }
      if (!state && window.palapaState && window.palapaState.cuentas) {
        state = window.palapaState;
      }
    }

    var ticketsMap = {};

    if (state && state.cuentas) {
      Object.keys(state.cuentas).forEach(function (key) {
        var cta = state.cuentas[key];
        if (cta && cta.items && cta.items.length > 0) {
          var enviados = cta.items.filter(function (it) {
            return (it.enviadoCocina === true || it.enviadoCocina === 'true') && it.estadoCocina !== 'servido';
          });

          if (enviados.length > 0) {
            var parts = key.split('-');
            var mesaId = parts[0] || '1';
            var sillaNum = parts[1] || '1';
            var isMesaCentro = (sillaNum === '0' || cta.es_cuenta_mesa);
            var areaInfo = getTableArea(mesaId);

            var ticketKey = isMesaCentro ? ('MESA-' + mesaId + '-CENTRO') : ('MESA-' + mesaId + '-S-' + sillaNum);
            if (!ticketsMap[ticketKey]) {
              ticketsMap[ticketKey] = {
                id: isMesaCentro ? ('T-' + mesaId + '-CENTRO') : ('T-' + mesaId + '-' + sillaNum),
                mesaId: mesaId.toString(),
                sillaNum: sillaNum.toString(),
                es_cuenta_mesa: isMesaCentro,
                mesaNombre: isMesaCentro ? ('⭐ Mesa ' + mesaId + ' • AL CENTRO') : ('Mesa ' + mesaId + ' • Silla ' + sillaNum),
                comensalNombre: isMesaCentro ? '⭐ PLATILLOS AL CENTRO' : (cta.comensalNombre || ('Comensal Silla ' + sillaNum)),
                areaId: areaInfo.id,
                areaNombre: areaInfo.nombre,
                horaEnvio: enviados[0].horaEnvioCocina || enviados[0].hora || '09:00 AM',
                timestampEnvio: enviados[0].timestampEnvioCocina || (Date.now() - (6 * 60 * 1000)),
                items: []
              };
            }

            enviados.forEach(function (it, idxInCta) {
              var st = getProductStation(it.nombre);
              ticketsMap[ticketKey].items.push({
                id: it.id,
                nombre: it.nombre,
                cantidad: it.cantidad || 1,
                notas: it.notas || '',
                sillaNum: sillaNum,
                keyCuenta: key,
                idxInCuenta: idxInCta,
                estacion: st,
                horaEnvio: it.horaEnvioCocina || it.hora || '09:00 AM',
                timestampEnvio: it.timestampEnvioCocina || (Date.now() - (6 * 60 * 1000)),
                timestampInicio: it.timestampInicioCocina || null,
                minutosEnAtencion: it.minutosEnAtencion || 0,
                estado: it.estadoCocina || 'recibido'
              });
            });
          }
        }
      });
    }

    var ticketsList = Object.values(ticketsMap);
    window.kdsState.tickets = ticketsList;
    renderKDSUI();
  };

  // 4. RENDERIZAR INTERFAZ DEL KDS CON LOS 3 NIVELES DE FILTRADO
  function renderKDSUI() {
    const container = document.getElementById('kdsTicketsGrid');
    const batchContainer = document.getElementById('kdsBatchContainer');
    const mesaChipsContainer = document.getElementById('kdsMesaChips');
    const focusBanner = document.getElementById('kdsFocusBanner');
    const focusText = document.getElementById('kdsFocusText');

    const currentArea = window.kdsState.areaFiltro;
    const currentMesa = window.kdsState.mesaFiltro;
    const currentStation = window.kdsState.estacionFiltro;

    if (!container) return;
    container.innerHTML = '';

    let countTodas = 0;
    let countCocina = 0;
    let countBarra = 0;
    let countReposteria = 0;
    let countInfantil = 0;
    let batchMap = {};
    let activeTablesSet = {};

    window.kdsState.tickets.forEach(ticket => {
      activeTablesSet[ticket.mesaId] = (activeTablesSet[ticket.mesaId] || 0) + 1;
      ticket.items.forEach(it => {
        if (it.estado !== 'servido') {
          countTodas += it.cantidad;
          if (it.estacion === 'COCINA') countCocina += it.cantidad;
          if (it.estacion === 'BARRA') countBarra += it.cantidad;
          if (it.estacion === 'REPOSTERIA') countReposteria += it.cantidad;
          if (it.estacion === 'INFANTIL') countInfantil += it.cantidad;

          if (it.estado === 'preparando') {
            if (!batchMap[it.nombre]) {
              batchMap[it.nombre] = { qty: it.cantidad, est: it.estacion };
            } else {
              batchMap[it.nombre].qty += it.cantidad;
            }
          }
        }
      });
    });

    const bT = document.getElementById('badgeCountTODAS');
    const bC = document.getElementById('badgeCountCOCINA');
    const bB = document.getElementById('badgeCountBARRA');
    const bR = document.getElementById('badgeCountREPOSTERIA');
    const bI = document.getElementById('badgeCountINFANTIL');
    if (bT) bT.innerText = countTodas;
    if (bC) bC.innerText = countCocina;
    if (bB) bB.innerText = countBarra;
    if (bR) bR.innerText = countReposteria;
    if (bI) bI.innerText = countInfantil;

    // Renderizar Selector Dinámico de Mesas 1 a 9
    if (mesaChipsContainer) {
      mesaChipsContainer.innerHTML = '';

      const isAllSelected = (currentMesa === 'TODAS');
      const btnAll = document.createElement('button');
      btnAll.id = 'chipMesa-TODAS';
      btnAll.onclick = function () { window.filtrarMesaKDS('TODAS'); };
      btnAll.style.cssText = 'padding: 4px 12px; font-size: 11px; font-weight: 800; border-radius: 8px; border: 1px solid ' + (isAllSelected ? '#f59e0b' : '#334155') + '; background: ' + (isAllSelected ? '#f59e0b' : '#0f172a') + '; color: ' + (isAllSelected ? '#0f172a' : '#cbd5e1') + '; cursor: pointer;';
      btnAll.innerHTML = 'Todas las Mesas (' + window.kdsState.tickets.length + ')';
      mesaChipsContainer.appendChild(btnAll);

      for (let m = 1; m <= 9; m++) {
        const mStr = m.toString();
        const isSelected = (currentMesa === mStr);
        const hasOrders = !!activeTablesSet[mStr];
        const areaObj = getTableArea(m);

        if (currentArea !== 'TODAS' && areaObj.id !== currentArea) {
          continue;
        }

        const btnM = document.createElement('button');
        btnM.id = 'chipMesa-' + mStr;
        btnM.onclick = (function (mesaNum) {
          return function () { window.filtrarMesaKDS(mesaNum); };
        })(mStr);

        let btnBg = '#0f172a';
        let btnColor = '#cbd5e1';
        let btnBorder = '#334155';
        if (isSelected) {
          btnBg = '#0284c7';
          btnColor = '#ffffff';
          btnBorder = '#38bdf8';
        } else if (hasOrders) {
          btnBorder = '#f59e0b';
          btnColor = '#fbbf24';
        }

        btnM.style.cssText = 'padding: 4px 10px; font-size: 11px; font-weight: 800; border-radius: 8px; border: 1px solid ' + btnBorder + '; background: ' + btnBg + '; color: ' + btnColor + '; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;';
        btnM.innerHTML = 'Mesa ' + m + (hasOrders ? ' <span style="width: 6px; height: 6px; border-radius: 50%; background: #f59e0b; display: inline-block;"></span>' : '');
        mesaChipsContainer.appendChild(btnM);
      }
    }

    // Actualizar Banner de Enfoque
    if (focusBanner && focusText) {
      if (currentMesa !== 'TODAS') {
        const areaObj = getTableArea(currentMesa);
        const mesaTicketsCount = window.kdsState.tickets.filter(t => t.mesaId === currentMesa).length;
        let estInfo = '';
        if (currentStation === 'BARRA') {
          estInfo = ' • <span style="background:rgba(56,189,248,0.25); color:#38bdf8; padding:2px 8px; border-radius:6px; border:1px solid #0284c7; font-weight:900;"><i class="fa-solid fa-mug-hot"></i> Solo Barra & Bebidas</span>';
        } else if (currentStation === 'COCINA') {
          estInfo = ' • <span style="background:rgba(245,158,11,0.25); color:#fbbf24; padding:2px 8px; border-radius:6px; border:1px solid #f59e0b; font-weight:900;"><i class="fa-solid fa-fire"></i> Solo Cocina Caliente</span>';
        } else if (currentStation === 'REPOSTERIA') {
          estInfo = ' • <span style="background:rgba(192,132,252,0.25); color:#c084fc; padding:2px 8px; border-radius:6px; border:1px solid #9333ea; font-weight:900;"><i class="fa-solid fa-cake-candles"></i> Solo Postres</span>';
        }
        focusText.innerHTML = 'Visualizando comanda: <b>Mesa ' + currentMesa + ' (' + areaObj.nombre + ')</b>' + estInfo + ' • <b>' + mesaTicketsCount + ' Comensal(es)</b>';
        focusBanner.style.display = 'flex';
      } else if (currentArea !== 'TODAS') {
        focusText.innerHTML = 'Visualizando área: <b>' + (currentArea === 'PALAPA' ? 'La Palapa (Mesas 1-3)' : (currentArea === 'PATIO' ? 'Terraza / Patio (Mesas 4-6)' : 'La Chimenea (Mesas 7-9)')) + '</b>';
        focusBanner.style.display = 'flex';
      } else {
        focusBanner.style.display = 'none';
      }
    }

    // Renderizar Lote en Fuego / Preparación (Batch Cooking & Bar Pills)
    if (batchContainer) {
      batchContainer.innerHTML = '';
      const batchKeys = Object.keys(batchMap);
      if (batchKeys.length === 0) {
        batchContainer.innerHTML = '<span style="font-size: 11px; color: #64748b; font-style: italic;">Sin órdenes en preparación activa. Presiona "Iniciar Fuego" / "Preparar Bebida" para comenzar.</span>';
      } else {
        batchKeys.forEach(nombre => {
          const itemInfo = batchMap[nombre];
          const qty = typeof itemInfo === 'object' ? itemInfo.qty : itemInfo;
          const est = typeof itemInfo === 'object' ? itemInfo.est : getProductStation(nombre);

          let pillBg = 'rgba(245, 158, 11, 0.18)';
          let pillBorder = '#f59e0b';
          let pillColor = '#fbbf24';
          let iconTag = '<i class="fa-solid fa-fire"></i>';

          if (est === 'BARRA') {
            pillBg = 'rgba(56, 189, 248, 0.18)';
            pillBorder = '#0284c7';
            pillColor = '#38bdf8';
            iconTag = '<i class="fa-solid fa-mug-hot"></i>';
          } else if (est === 'REPOSTERIA') {
            pillBg = 'rgba(192, 132, 252, 0.18)';
            pillBorder = '#9333ea';
            pillColor = '#c084fc';
            iconTag = '<i class="fa-solid fa-cake-candles"></i>';
          }

          const pill = document.createElement('span');
          pill.style.cssText = 'padding: 4px 10px; background: ' + pillBg + '; border: 1px solid ' + pillBorder + '; color: ' + pillColor + '; border-radius: 20px; font-size: 11px; font-weight: 800; display: inline-flex; align-items: center; gap: 5px;';
          pill.innerHTML = iconTag + ' <b>' + qty + 'x</b> ' + nombre;
          batchContainer.appendChild(pill);
        });
      }
    }

    // Filtrar y renderizar tickets
    let renderedTicketsCount = 0;
    const now = Date.now();

    window.kdsState.tickets.forEach((ticket, tIdx) => {
      if (currentArea !== 'TODAS' && ticket.areaId !== currentArea) return;
      if (currentMesa !== 'TODAS' && ticket.mesaId !== currentMesa) return;

      const visibleItems = ticket.items.filter(it => {
        if (it.estado === 'servido') return false;
        if (currentStation === 'TODAS') return true;
        return it.estacion === currentStation;
      });

      if (visibleItems.length === 0) return;
      renderedTicketsCount++;

      let hasDelayedBarra = false;
      let hasDelayedCocina = false;
      let hasPreparingBarra = false;
      let hasPreparingCocina = false;
      let allItemsReady = true;

      visibleItems.forEach(it => {
        if (it.estado !== 'listo') allItemsReady = false;

        const isBarra = (it.estacion === 'BARRA');
        const threshold = isBarra ? 7 : 14;

        if (it.estado === 'preparando') {
          if (isBarra) hasPreparingBarra = true;
          else hasPreparingCocina = true;

          const startTime = it.timestampInicio || it.timestampEnvio || ticket.timestampEnvio || (now - 5 * 60000);
          const elapsedMins = Math.floor((now - startTime) / 60000);
          if (elapsedMins >= threshold) {
            if (isBarra) hasDelayedBarra = true;
            else hasDelayedCocina = true;
          }
        } else if (it.estado === 'recibido') {
          const startTime = it.timestampEnvio || ticket.timestampEnvio || (now - 5 * 60000);
          const elapsedMins = Math.floor((now - startTime) / 60000);
          if (elapsedMins >= threshold) {
            if (isBarra) hasDelayedBarra = true;
            else hasDelayedCocina = true;
          }
        }
      });

      let semaforoBg = '#10b981';
      let semaforoText = '#34d399';
      let semaforoLabel = '🟢 EN ESPERA';
      let isUrgent = false;

      if (allItemsReady) {
        semaforoBg = '#0284c7';
        semaforoText = '#38bdf8';
        semaforoLabel = '✅ LISTO EN PASE';
      } else if (hasDelayedBarra && hasDelayedCocina) {
        semaforoBg = '#ef4444';
        semaforoText = '#f87171';
        semaforoLabel = '🔴 DEMORA BARRA & COCINA';
        isUrgent = true;
      } else if (hasDelayedBarra) {
        semaforoBg = '#ef4444';
        semaforoText = '#f87171';
        semaforoLabel = '🔴 BARRA DEMORADA (>7m)';
        isUrgent = true;
      } else if (hasDelayedCocina) {
        semaforoBg = '#ef4444';
        semaforoText = '#f87171';
        semaforoLabel = '🔴 COCINA DEMORADA (>14m)';
        isUrgent = true;
      } else if (hasPreparingCocina && hasPreparingBarra) {
        semaforoBg = '#f59e0b';
        semaforoText = '#fbbf24';
        semaforoLabel = '🟡 EN PREPARACIÓN';
      } else if (hasPreparingCocina) {
        semaforoBg = '#f59e0b';
        semaforoText = '#fbbf24';
        semaforoLabel = '🟡 EN FUEGO';
      } else if (hasPreparingBarra) {
        semaforoBg = '#0284c7';
        semaforoText = '#38bdf8';
        semaforoLabel = '🟡 PREPARANDO BEBIDA';
      } else {
        semaforoBg = '#10b981';
        semaforoText = '#34d399';
        semaforoLabel = '🟢 RECIBIDO';
      }

      const totalElapsedMins = Math.floor((now - (ticket.timestampEnvio || (now - 5 * 60000))) / 60000);

      const card = document.createElement('div');
      card.className = 'kds-ticket-card ' + (isUrgent ? 'kds-ticket-urgent' : '');
      card.style.cssText = 'background: #0d1322 !important; border: 2px solid ' + semaforoBg + ' !important; border-radius: 18px !important; padding: 16px !important; display: flex !important; flex-direction: column !important; justify-content: space-between !important; gap: 12px !important; box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important; position: relative !important; overflow: hidden !important;';

      const sideBar = document.createElement('div');
      sideBar.style.cssText = 'position: absolute; top: 0; left: 0; width: 6px; height: 100%; background: ' + semaforoBg + ';';
      card.appendChild(sideBar);

      const header = document.createElement('div');
      header.style.cssText = 'display: flex; justify-content: space-between; align-items: flex-start; padding-left: 6px;';
      header.innerHTML = `
        <div>
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 15px; font-weight: 900; color: #ffffff;">
              ${ticket.mesaNombre}
            </span>
            <span style="font-size: 10px; font-weight: 900; padding: 2px 6px; border-radius: 6px; background: rgba(15,23,42,0.9); color: ${semaforoText}; border: 1px solid ${semaforoBg};">
              ${semaforoLabel}
            </span>
          </div>
          <div style="display: flex; align-items: center; gap: 6px; margin-top: 2px;">
            <span style="font-size: 11px; font-weight: 800; color: #38bdf8;"><i class="fa-solid fa-user"></i> ${ticket.comensalNombre || ('Comensal Silla ' + ticket.sillaNum)}</span>
            <span style="font-size: 11px; color: #94a3b8; font-weight: 700;">
              • <i class="fa-regular fa-clock"></i> ${ticket.horaEnvio} (${totalElapsedMins} min)
            </span>
          </div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
          <span style="font-size: 10px; color: #64748b; font-weight: 800;">Ticket #${ticket.id}</span>
        </div>
      `;
      card.appendChild(header);

      const itemsWrap = document.createElement('div');
      itemsWrap.style.cssText = 'display: flex; flex-direction: column; gap: 8px; padding: 8px 6px; border-top: 1px solid #1e293b; border-bottom: 1px solid #1e293b;';

      visibleItems.forEach((it, iIdx) => {
        let stBadgeBg = '#1e293b';
        let stBadgeColor = '#38bdf8';
        let stLabel = 'Cocina';
        if (it.estacion === 'BARRA') { stBadgeBg = 'rgba(56,189,248,0.15)'; stBadgeColor = '#38bdf8'; stLabel = 'Barra & Café'; }
        if (it.estacion === 'REPOSTERIA') { stBadgeBg = 'rgba(192,132,252,0.15)'; stBadgeColor = '#c084fc'; stLabel = 'Postres'; }
        if (it.estacion === 'INFANTIL') { stBadgeBg = 'rgba(74,222,128,0.15)'; stBadgeColor = '#4ade80'; stLabel = 'Infantil'; }

        let itemStateBadge = '';
        let itemBg = '#070b14';
        let itemBorder = '#1e293b';
        let actionButtonHtml = '';

        const itemElapsedMins = it.timestampInicio ? Math.floor((now - it.timestampInicio) / 60000) : (it.timestampEnvio ? Math.floor((now - it.timestampEnvio) / 60000) : 0);
        const isBarra = (it.estacion === 'BARRA');
        const isRep = (it.estacion === 'REPOSTERIA');
        const threshold = isBarra ? 7 : (isRep ? 10 : 14);

        if (it.estado === 'recibido') {
          let stIcon = 'fa-solid fa-fire';
          let btnText = 'Iniciar Fuego';
          let btnGradient = 'linear-gradient(135deg, #f59e0b, #d97706)';
          let btnTextColor = '#0f172a';

          if (isBarra) {
            stIcon = 'fa-solid fa-mug-hot';
            btnText = 'Preparar Bebida';
            btnGradient = 'linear-gradient(135deg, #0284c7, #0369a1)';
            btnTextColor = '#ffffff';
          } else if (isRep) {
            stIcon = 'fa-solid fa-cake-candles';
            btnText = 'Preparar Postre';
            btnGradient = 'linear-gradient(135deg, #9333ea, #7e22ce)';
            btnTextColor = '#ffffff';
          } else if (it.estacion === 'INFANTIL') {
            stIcon = 'fa-solid fa-child';
            btnText = 'Iniciar Infantil';
            btnGradient = 'linear-gradient(135deg, #16a34a, #15803d)';
            btnTextColor = '#ffffff';
          }

          itemStateBadge = '<span style="font-size: 9px; font-weight: 800; background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.4); padding: 2px 6px; border-radius: 4px;">🟢 En Espera</span>';
          itemBorder = 'rgba(16,185,129,0.3)';
          actionButtonHtml = `
            <button onclick="window.iniciarAtencionItemKDS(${tIdx}, ${iIdx});" style="padding: 4px 10px; font-size: 10px; font-weight: 900; border-radius: 6px; border: none; cursor: pointer; background: ${btnGradient}; color: ${btnTextColor}; display: flex; align-items: center; gap: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.25);">
              <i class="${stIcon}"></i> ${btnText}
            </button>
          `;
        } else if (it.estado === 'preparando') {
          let prepText = '🟡 En Fuego';
          let prepIcon = 'fa-solid fa-fire-burner';
          let prepColor = '#fbbf24';
          let prepBorder = 'rgba(245,158,11,0.4)';
          let prepBg = 'rgba(245,158,11,0.2)';

          if (isBarra) {
            prepText = '🟡 Preparando Bebida';
            prepIcon = 'fa-solid fa-mug-hot';
            prepColor = '#38bdf8';
            prepBorder = 'rgba(56,189,248,0.4)';
            prepBg = 'rgba(56,189,248,0.18)';
          } else if (isRep) {
            prepText = '🟡 Preparando Postre';
            prepIcon = 'fa-solid fa-cake-candles';
            prepColor = '#c084fc';
            prepBorder = 'rgba(192,132,252,0.4)';
            prepBg = 'rgba(192,132,252,0.18)';
          }

          if (itemElapsedMins >= threshold) {
            const delayLabel = isBarra ? '🔴 Barra Demorada' : (isRep ? '🔴 Postre Demorado' : '🔴 Retraso Cocina');
            itemStateBadge = '<span style="font-size: 9px; font-weight: 900; background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid #ef4444; padding: 2px 6px; border-radius: 4px; animation: urgentPulse 1.8s infinite;"><i class="fa-solid fa-triangle-exclamation"></i> ' + delayLabel + ' (' + itemElapsedMins + ' min)</span>';
            itemBorder = '#ef4444';
            itemBg = 'rgba(239,68,68,0.08)';
          } else {
            itemStateBadge = '<span style="font-size: 9px; font-weight: 800; background: ' + prepBg + '; color: ' + prepColor + '; border: 1px solid ' + prepBorder + '; padding: 2px 6px; border-radius: 4px;"><i class="' + prepIcon + '"></i> ' + prepText + ' (' + itemElapsedMins + 'm)</span>';
            itemBorder = isBarra ? '#0284c7' : '#f59e0b';
          }

          actionButtonHtml = `
            <button onclick="window.marcarListoItemKDS(${tIdx}, ${iIdx});" style="padding: 4px 10px; font-size: 10px; font-weight: 900; border-radius: 6px; border: none; cursor: pointer; background: linear-gradient(135deg, #059669, #10b981); color: #ffffff; display: flex; align-items: center; gap: 4px; box-shadow: 0 2px 8px rgba(16,185,129,0.3);">
              <i class="fa-solid fa-check"></i> Marcar Listo
            </button>
          `;
        } else if (it.estado === 'listo') {
          itemStateBadge = '<span style="font-size: 9px; font-weight: 800; background: rgba(2,132,199,0.25); color: #38bdf8; border: 1px solid #0284c7; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-circle-check"></i> Listo en Pase</span>';
          itemBorder = '#0284c7';
          itemBg = 'rgba(2,132,199,0.1)';
          actionButtonHtml = `
            <button onclick="window.iniciarAtencionItemKDS(${tIdx}, ${iIdx});" style="padding: 3px 8px; font-size: 9px; font-weight: 700; border-radius: 6px; border: 1px solid #334155; cursor: pointer; background: #0f172a; color: #94a3b8; display: flex; align-items: center; gap: 3px;">
              <i class="fa-solid fa-rotate-left"></i> Reabrir
            </button>
          `;
        }

        const row = document.createElement('div');
        row.style.cssText = 'background: ' + itemBg + '; border: 1px solid ' + itemBorder + '; border-radius: 10px; padding: 8px 10px; display: flex; flex-direction: column; gap: 4px;';
        row.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-size: 13px; font-weight: 900; color: ${it.estado === 'listo' ? '#38bdf8' : '#ffffff'};">
                ${it.cantidad}x ${it.nombre}
              </span>
              <span style="font-size: 9px; font-weight: 800; background: #0f172a; color: ${(it.sillaNum === '0' || it.sillaNum === 0) ? '#38bdf8' : '#fbbf24'}; border: 1px solid #334155; padding: 1px 5px; border-radius: 4px;">${(it.sillaNum === '0' || it.sillaNum === 0) ? '⭐ Al Centro' : ('Silla ' + it.sillaNum)}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 4px;">
              ${itemStateBadge}
              <span style="font-size: 9px; font-weight: 800; background: ${stBadgeBg}; color: ${stBadgeColor}; padding: 2px 6px; border-radius: 4px; border: 1px solid ${stBadgeColor};">
                ${stLabel}
              </span>
            </div>
          </div>

          ${it.notas ? `<div style="font-size: 11px; color: #fde047; background: rgba(234,179,8,0.1); border: 1px dashed rgba(234,179,8,0.3); border-radius: 6px; padding: 4px 8px; font-style: italic;"><i class="fa-solid fa-note-sticky"></i> ${it.notas}</div>` : ''}

          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
            <button onclick="window.abrirFichaReceta('${it.nombre.replace(/'/g, "\\'")}');" style="background: transparent; border: none; color: #38bdf8; font-size: 10px; font-weight: 800; cursor: pointer; display: flex; align-items: center; gap: 4px; padding: 2px;" title="Ver gramajes exactos e instrucciones de preparación">
              <i class="fa-solid fa-book-open"></i> Ficha Técnica
            </button>
            <div>
              ${actionButtonHtml}
            </div>
          </div>
        `;
        itemsWrap.appendChild(row);
      });
      card.appendChild(itemsWrap);

      // Si todos los items están listos, botón de entrega al mesero
      if (allItemsReady) {
        const footer = document.createElement('div');
        footer.style.cssText = 'padding-left: 6px; display: flex; gap: 8px;';
        footer.innerHTML = `
          <button onclick="window.despacharTicketCompletoKDS(${tIdx});" style="flex: 1; padding: 10px; background: linear-gradient(135deg, #059669, #10b981); color: #ffffff; border: none; border-radius: 12px; font-size: 12px; font-weight: 900; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 4px 12px rgba(16,185,129,0.3);">
            <i class="fa-solid fa-bell-concierge"></i> 🔔 Pase / Entregar a Mesero
          </button>
        `;
        card.appendChild(footer);
      }

      container.appendChild(card);
    });

    if (renderedTicketsCount === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; background: #0d1322; border: 1px dashed #1e293b; border-radius: 20px; padding: 50px 20px; text-align: center;">
          <div style="width: 60px; height: 60px; border-radius: 50%; background: rgba(16,185,129,0.15); color: #34d399; font-size: 26px; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px;">
            <i class="fa-solid fa-check-double"></i>
          </div>
          <h3 style="font-size: 16px; font-weight: 900; color: #ffffff; margin: 0;">¡Cocina y Barra al Día!</h3>
          <p style="font-size: 12px; color: #94a3b8; margin: 4px 0 0 0;">No hay comandas pendientes para el filtro seleccionado (${currentArea !== 'TODAS' ? currentArea + ' • ' : ''}${currentMesa !== 'TODAS' ? 'Mesa ' + currentMesa + ' • ' : ''}${currentStation}).</p>
        </div>
      `;
    }
  }

  // 5. FUNCIONES DE FILTRADO (ÁREAS, MESAS Y ESTACIONES)
  window.filtrarAreaKDS = function (area) {
    window.kdsState.areaFiltro = area;
    if (area !== 'TODAS') {
      localStorage.setItem('kds_filtro_area', area);
    } else {
      localStorage.removeItem('kds_filtro_area');
    }

    const container = document.getElementById('kdsAreaChips');
    if (container) {
      const buttons = container.querySelectorAll('button');
      buttons.forEach(function (btn) {
        const btnArea = btn.getAttribute('data-area') || btn.id.replace('chipArea-', '');
        if (btnArea === area || btn.innerText.includes(area)) {
          btn.style.background = '#38bdf8';
          btn.style.color = '#0f172a';
          btn.style.border = '1px solid #38bdf8';
        } else {
          btn.style.background = '#0f172a';
          btn.style.color = '#cbd5e1';
          btn.style.border = '1px solid #334155';
        }
      });
    }

    renderKDSUI();
  };

  window.filtrarMesaKDS = function (mesaId) {
    window.kdsState.mesaFiltro = mesaId.toString();
    if (mesaId !== 'TODAS') {
      localStorage.setItem('kds_filtro_mesa', mesaId.toString());
    } else {
      localStorage.removeItem('kds_filtro_mesa');
    }
    renderKDSUI();
  };

  window.filtrarEstacionKDS = function (estacion) {
    window.kdsState.estacionFiltro = estacion;

    const chips = ['TODAS', 'COCINA', 'BARRA', 'REPOSTERIA', 'INFANTIL'];
    chips.forEach(c => {
      const btn = document.getElementById('chipKDS-' + c);
      if (btn) {
        if (c === estacion) {
          btn.style.background = '#f59e0b';
          btn.style.color = '#0f172a';
          btn.style.border = '1px solid #f59e0b';
        } else {
          btn.style.background = '#0f172a';
          btn.style.color = '#cbd5e1';
          btn.style.border = '1px solid #334155';
        }
      }
    });

    renderKDSUI();
  };

  // 6. ACCIONES DE COCINA: INICIAR ATENCIÓN / FUEGO (VERDE -> ÁMBAR)
  window.iniciarAtencionItemKDS = function (ticketIdx, itemIdx) {
    const ticket = window.kdsState.tickets[ticketIdx];
    if (!ticket || !ticket.items[itemIdx]) return;

    const it = ticket.items[itemIdx];
    it.estado = 'preparando';
    it.timestampInicio = Date.now();

    syncKDSItemToAllStoragesAndServer(it.keyCuenta, it.idxInCuenta, 'preparando', it.timestampInicio, it.id);
    renderKDSUI();
  };

  // MARCAR PLATILLO LISTO (ÁMBAR/ROJO -> LISTO)
  window.marcarListoItemKDS = function (ticketIdx, itemIdx) {
    const ticket = window.kdsState.tickets[ticketIdx];
    if (!ticket || !ticket.items[itemIdx]) return;

    const it = ticket.items[itemIdx];
    it.estado = 'listo';

    syncKDSItemToAllStoragesAndServer(it.keyCuenta, it.idxInCuenta, 'listo', null, it.id);
    renderKDSUI();
  };

  // 7. DESPACHAR TICKET COMPLETO (PASE / SERVIDO)
  window.despacharTicketCompletoKDS = function (ticketIdx) {
    const ticket = window.kdsState.tickets[ticketIdx];
    if (!ticket) return;

    if (typeof window.anvilDespacharTicketCocina === 'function') {
      window.anvilDespacharTicketCocina(ticket.mesaId, ticket.sillaNum, 'servido');
    }

    ticket.items.forEach(it => {
      it.estado = 'servido';
      syncKDSItemToAllStoragesAndServer(it.keyCuenta, it.idxInCuenta, 'servido', null, it.id);
    });

    playKitchenBell();
    if (typeof window.anvilGetKDSCuentas === 'function') {
      window.anvilGetKDSCuentas();
    } else {
      window.cargarKDS();
    }
  };

  // 8. MODAL DE FICHA TÉCNICA DE RECETA
  window.abrirFichaReceta = function (nombrePlatillo) {
    const modal = document.getElementById('modalFichaRecetaBackdrop');
    const titulo = document.getElementById('fichaRecetaTitulo');
    const categoria = document.getElementById('fichaRecetaCategoria');
    const icon = document.getElementById('fichaRecetaIcon');
    const tiempo = document.getElementById('fichaRecetaTiempo');
    const equipo = document.getElementById('fichaRecetaEquipo');
    const temp = document.getElementById('fichaRecetaTemp');
    const ingredientesContainer = document.getElementById('fichaRecetaIngredientes');
    const pasosContainer = document.getElementById('fichaRecetaPasos');
    const montaje = document.getElementById('fichaRecetaMontaje');

    let rDB = window.recetarioCocinaDB && (window.recetarioCocinaDB[nombrePlatillo] || window.recetarioCocinaDB[(nombrePlatillo || '').toLowerCase().trim()]);
    let receta = null;

    if (rDB) {
      let ingList = [];
      let rawIng = rDB.ingredientes;
      if (typeof rawIng === 'string') {
        try { rawIng = JSON.parse(rawIng); } catch (e) { rawIng = [rawIng]; }
      }
      if (Array.isArray(rawIng)) {
        ingList = rawIng.map(function (ing) {
          if (typeof ing === 'object' && ing !== null) {
            return {
              item: ing.item || ing.nombre || 'Ingrediente',
              cant: ing.cant || ing.cantidad || '',
              dosificador: ing.dosificador || 'Porción estándar'
            };
          }
          return {
            item: String(ing),
            cant: '',
            dosificador: 'Control estándar'
          };
        });
      }

      let pasosList = [];
      let rawPasos = rDB.pasos;
      if (typeof rawPasos === 'string') {
        try { rawPasos = JSON.parse(rawPasos); } catch (e) { rawPasos = [rawPasos]; }
      }
      if (Array.isArray(rawPasos)) {
        pasosList = rawPasos.map(function (p, idx) {
          return (typeof p === 'string' && (p.startsWith('1.') || p.startsWith('2.') || p.startsWith('3.') || p.startsWith('4.'))) ? p : ((idx + 1) + '. ' + p);
        });
      }

      receta = {
        icon: rDB.icono || '🍲',
        categoria: (rDB.categoria_nombre || 'Especialidad') + ' • Estación: ' + (rDB.estacion_preparacion || 'Cocina Caliente'),
        tiempo: (rDB.tiempo_estimado || '6–8') + ' min',
        equipo: 'Estación ' + (rDB.estacion_preparacion || 'Cocina Caliente') + ' / Vajilla estándar',
        temp: 'Caliente (>75°C)',
        ingredientes: ingList.length > 0 ? ingList : [{ item: 'Ingredientes frescos de temporada', cant: '1 porción', dosificador: 'Control estándar' }],
        pasos: pasosList.length > 0 ? pasosList : ['Preparar al momento siguiendo el estándar de calidad de La Terraza.'],
        montaje: rDB.notas_receta || 'Vajilla estándar de La Terraza con guarnición y pase inmediato térmico.'
      };
    } else {
      receta = {
        icon: '🍲',
        categoria: 'Especialidad de la Casa • Cocina Caliente',
        tiempo: '6-8 min',
        equipo: 'Línea de Fuego / Quemador',
        temp: 'Caliente (>75°C)',
        ingredientes: [
          { item: 'Porción base del platillo', cant: '1 porción estándar', dosificador: 'Bolsa dosificada #1' },
          { item: 'Guarnición caliente', cant: '80 g', dosificador: '1 Cucharón' },
          { item: 'Salsas y aderezos', cant: '30 ml', dosificador: 'Dosificador calibrado' }
        ],
        pasos: [
          '1. Tomar los ingredientes porcionados del refrigerador de línea.',
          '2. Saltear o calentar a fuego medio-alto durante el tiempo estándar indicado.',
          '3. Emplatar en vajilla caliente y verificar temperatura antes de enviar a pase.'
        ],
        montaje: 'Vajilla estándar de La Terraza con guarnición y pase inmediato.'
      };
    }

    if (titulo) titulo.innerText = nombrePlatillo;
    if (categoria) categoria.innerText = receta.categoria;
    if (icon) icon.innerText = receta.icon;
    if (tiempo) tiempo.innerText = receta.tiempo;
    if (equipo) equipo.innerText = receta.equipo;
    if (temp) temp.innerText = receta.temp;
    if (montaje) montaje.innerText = receta.montaje;

    if (ingredientesContainer) {
      ingredientesContainer.innerHTML = '';
      receta.ingredientes.forEach(ing => {
        const row = document.createElement('div');
        row.style.cssText = 'display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #1e293b; padding-bottom: 3px;';
        row.innerHTML = `
          <div>
            <span style="color: #ffffff; font-weight: 700;">${ing.item}</span>
            <span style="font-size: 10px; color: #94a3b8; margin-left: 4px;">(${ing.dosificador})</span>
          </div>
          <span style="font-weight: 900; color: #34d399;">${ing.cant}</span>
        `;
        ingredientesContainer.appendChild(row);
      });
    }

    if (pasosContainer) {
      pasosContainer.innerHTML = '';
      receta.pasos.forEach(p => {
        const pEl = document.createElement('div');
        pEl.style.cssText = 'background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 6px 10px;';
        pEl.innerText = p;
        pasosContainer.appendChild(pEl);
      });
    }

    if (modal) {
      modal.style.display = 'flex';
    }
  };

  window.cerrarFichaReceta = function () {
    const modal = document.getElementById('modalFichaRecetaBackdrop');
    if (modal) {
      modal.style.display = 'none';
    }
  };

  // Navegación
  window.navMenu = function (modulo) {
    if (typeof window.anvilAppNav === 'function') {
      window.anvilAppNav(modulo);
    } else if (typeof window.parent !== 'undefined' && typeof window.parent.anvilAppNav === 'function') {
      window.parent.anvilAppNav(modulo);
    } else if (typeof window.top !== 'undefined' && typeof window.top.anvilAppNav === 'function') {
      window.top.anvilAppNav(modulo);
    } else {
      console.log('[navMenu] Navegando a:', modulo);
    }
  };

  // Sonido de Campana de Cocina con Web Audio API (Sin archivos externos)
  function playKitchenBell() {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime); // Nota La (A5)
      osc.frequency.exponentialRampToValueAtTime(1760, ctx.currentTime + 0.1);

      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.8);
    } catch (e) { }
  }

  // Inicializar KDS y configurar polling automático cada 4 segundos
  setTimeout(function () {
    try {
      window.scrollTo(0, 0);
      if (document.documentElement) document.documentElement.scrollTop = 0;
      if (document.body) document.body.scrollTop = 0;
    } catch (e) { }
    if (typeof window.cargarKDS === 'function') {
      window.cargarKDS();
    }
  }, 50);

  setInterval(function () {
    if (typeof window.cargarKDS === 'function') {
      window.cargarKDS();
    }
  }, 4000);

})();
