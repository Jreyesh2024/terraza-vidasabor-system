# Estado de Avance — La Terraza de Vida & Sabor

**Fecha del snapshot:** 2026-09-07
**Último commit:** `1d1fef2` — `fix: botón salir cocina en su header + tooltip persistente + no title nativo`
**Rama:** `main` (sincronizada con `anvil` y `origin`)

---

## 1. Bloques del roadmap

| Bloque | Nombre | Estado | Notas |
|---|---|---|---|
| **A** | Datos base (schema v2) | ✅ Completado | 18 tablas + 3 vistas por rol. Palapa activa, Chimenea/Patio inactivas. 12 sillas regulares + 3 pool. 12 categorías + 57 productos preservados. |
| **B** | Ocupación por QR + sesión persistente | ✅ Completado | sesiones_mesa + ocupaciones_silla en BD. Idempotente. get_cuentas_terraza lee de BD. |
| **C.1** | Backend endpoints comanda | ✅ Completado | agregar_item / eliminar_item / get_items_por_silla / enviar_items_a_cocina con snapshot precio. get_menu_cliente / get_menu_mesero. |
| **C.2** | Refactor visual Menu cliente | ✅ Completado | 2622 → 353 líneas. Auto check-in QR. Escenarios A/B/C/D del cambio de silla. Ver [[DISENO_DOMINIO_v2.md]]. |
| **C.3** | Catálogo interactivo cliente | ✅ Completado | Categorías 2-col + productos + modal producto + Mi Comanda + enviar a cocina + Pedir para Otra Silla. Toast in-page. Banner llamada persistente con polling y auto-desaparición al ser atendida. |
| **D** | Buffer inteligente 5 min | ⏳ Pendiente | Buffer 5 min server-side + panel de consolidación del mesero. |
| **E** | MonitorCocina FIFO agrupado por mesa (rediseño) | ⏳ Pendiente | Actualmente es LEGACY con datos JS hardcoded. Estados no persisten. Bebidas se mezclan con cocina. Rediseño completo pendiente. |
| **F** | Cobro modular con asignaciones_pago | ⏳ Pendiente | Motor de asignación libre item ↔ pago. |
| **G** | Llamada al mesero (v1 completada) | 🟡 Parcial | Ya funciona: crear_llamada_mesero, banner rojo POSMesero, atender_llamada, historial atendidas con quién atendió. Falta: notificación al teléfono del mesero (por definir). |
| **H** | Gestión Menú & Recetas gerencial | ⏳ Pendiente | Form para editar productos, precios, recetas desde la app. |

## 2. Módulos y estado

- **POSMesero** — refactor limpio con event delegation. Layout dual funciona. Categorías 3-col cuadros grandes. Vista secundaria por categoría con volver. Startup form actual.
- **Menu** (cliente QR) — reescrito completo C.3. 4 tarjetas: Mi Silla / Al Centro / Otra Silla / Mi Comanda. Toast, banner llamada persistente, resumen al centro visible.
- **MonitorCocina** — legacy. Botón "Volver a Mesa & POS" del header ya funciona (listener directo Python). Estados internos no persisten (Bloque E lo rediseña).
- **AdminMenu** — no es startup. Se accede desde botón "Inicio / Hub" del POSMesero. No es foco por ahora.
- **MonitorFiscal**, **ClientesLealtad** — sin cambios significativos.

## 3. Infraestructura viva

### Postgres
- BD local `dbterrazavidasabor` con schema v2 aplicado.
- Todo persiste: sillas, sesiones, ocupaciones, comandas, detalle_comanda, envios_cocina, pagos, llamadas_mesero.

### Uplink daemon
```bash
python3 "/Volumes/ORICO ExFAT/terraza-vidasabor-system/uplink/terraza_uplink.py"
```
- Conecta a Anvil como SERVER.
- Se debe arrancar manualmente cuando reinicie la Mac.
- Al arrancar imprime `✅ ¡Conexión Anvil Uplink V&S establecida — schema v2 + sesiones persistentes!`.

### App publicada
- URL: `https://impeccable-fruitful-beaver.anvil.app`
- Requiere Publish manual desde Anvil.works IDE tras cada push git.
- Último commit publicado en el momento de dejar el proyecto: **ver historial de Publish en el IDE** — el usuario debe confirmarlo. Los commits sin publicar quedan en git pero la app viva sigue en la versión publicada anterior.

## 4. Pendientes menores anotados

1. **Flash de arranque** ("flashazo" con AdminMenu sin estilos por milisegundos): probado con CSS puro `body::before` + splash + estilos inline en `native_deps`. Sigue apareciendo brevemente. Considerar límite del runner de Anvil.
2. **Scroll AdminMenu con header cortado**: `overflow-y: auto` global aplicado; requiere verificar con la versión publicada más reciente.
3. **Botón "Salir/Cerrar sesión" en POSMesero**: pendiente diseñarlo (para el mesero).
4. **Meseros entran directo a POSMesero sin ver Hub**: cumplido temporalmente con `startup: POSMesero`. Considerar roles cuando gerente/mesero tengan credenciales distintas.
5. **Notificación al teléfono del mesero** (llamadas cliente): por analizar. El banner rojo del POSMesero ya lo alerta.
6. **Bebidas separadas de cocina caliente** en el KDS: parte de Bloque E, la BD ya tiene `estacion_id`.
7. **Popup hover con estados coincidentes con la comanda**: implementado; el mapeo lee tanto v2 (`estado`) como flags legacy (`enviadoCocina`, `enFuego`, `listo`, `servido`).

## 5. Convenciones establecidas

- **Arquitectura**: Python dueño de eventos vía delegación desde `get_dom_node(self)` en `form_show`; JS es DOM tonto; datos en Postgres; sin `onclick` inline; sin `<script>` embebidos que dependan del parseo del innerHTML.
- **Snapshots** en `detalle_comanda`: `precio_unitario_snapshot` y `producto_nombre_snapshot` congelados al momento de la comanda.
- **QR**: formato `PV-<AREA>-<MESA:02>-<SILLA:02>` para regulares y `PV-P-EX-NN` para extras del pool. Ejemplo: `PV-P-01-01` = Palapa Mesa 1 Silla 1.
- **Ciclo de trabajo**: Claude edita archivos locales → commit + push → user publica en Anvil IDE (Publish → Choose a version → seleccionar commit más nuevo → cerrar IDE).
- **Nunca abrir el IDE de Anvil mientras editamos local** — hace auto-commits que pisan el trabajo.

## 6. Commits importantes por bloque

- Bloque A + reset: `9f29f0b` (auto-commit Anvil que pisó primer refactor), `c1003aa` (re-aplicado)
- Bloque B: `b9900c6`
- Bloque C.1: `917e1ae`
- Bloque C.2: `75fa2e7`
- Bloque C.3 completo: `912ffc1` + `1b3e267` + `bb2a294`
- Bloque G v1 (llamadas): `aaccf74`
- Fixes finales navegación cocina + hover: `1d1fef2` (último al momento del snapshot)

## 7. Cómo retomar

1. **Verificar uplink corriendo**: `ps aux | grep terraza_uplink`. Si no está: `python3 uplink/terraza_uplink.py &`.
2. **Verificar rama**: `git -C "/Volumes/ORICO ExFAT/terraza-vidasabor-system" status` — debe estar clean en main.
3. **Publish en Anvil** del último commit local si no coincide con la publicada.
4. **Leer**: este documento + `docs/DISENO_DOMINIO_v2.md`.
5. **Elegir siguiente bloque** de la tabla en §1.

## 8. Rutas de referencia del disco

- Repo: `/Volumes/ORICO ExFAT/terraza-vidasabor-system`
- Uplink: `uplink/terraza_uplink.py`
- QRs para imprimir: `qrs_portavasos/*.png` (15 archivos, formato PV-P-*)
- Schema BD: `database/migracion_v2_reset.sql` + `database/seed_catalogo.sql`
- Diseño: `docs/DISENO_DOMINIO_v2.md`
- Snapshot (este archivo): `docs/ESTADO_AVANCE_2026-09-07.md`
