# Diseño de Dominio v2 — La Terraza de Vida & Sabor

Fecha: 2026-09-06
Estado: propuesto, pendiente de validación
Autor de la síntesis: Claude Opus 4.7 (con base en descripciones de operación del usuario)

## 1. Alcance

Este documento fija el modelo de dominio (entidades, relaciones, casos de uso) y el schema Postgres que soportará la operación del restaurante en su primera área (Palapa) y futuras (2 más). Reemplaza aproximaciones previas donde datos operacionales vivían hardcodeados en HTML.

## 2. Actores y niveles de información

Tres roles con distintos niveles de detalle sobre el catálogo:

| Rol | Ve | No ve |
|---|---|---|
| **Cliente (QR/teléfono)** | Nombre coloquial, descripción amigable, precio (con IVA), imagen, alérgenos, tiempo aproximado. | Costos, receta, ingredientes con cantidades, notas del chef, tiempos exactos. |
| **Mesero (iPad)** | Todo lo del cliente + descripción operativa para explicar, tiempos precisos, extras disponibles, opciones de exclusión, términos. | Receta completa, ingredientes con cantidades, pasos, costos. |
| **Cocina (KDS)** | Todo, incluida ficha técnica: ingredientes con cantidades, pasos, notas del chef, agrupado por estación. | — |

Se enforce en **backend** con 3 vistas SQL: `vw_menu_cliente`, `vw_menu_mesero`, `vw_ficha_cocina`. El front consume la vista de su rol; los campos sensibles nunca viajan al cliente incorrecto.

## 3. Casos de uso capturados

### 3.1 Ocupación de silla
- **Por QR**: cliente escanea código en portavasos → sistema crea `ocupacion_silla` automáticamente. Incluso sin pedir, queda registrado que llegó.
- **Por mesero**: mesero hace clic en silla del croquis (POSMesero) → misma ocupación pero con `origen='mesero'`.
- **Cierre**: solo el mesero marca liberación. El cliente nunca cierra su propia silla.

### 3.2 Sesión de mesa
- Al ocuparse la primera silla de una mesa, se abre `sesion_mesa` (visita).
- La sesión agrupa ocupaciones y comandas.
- Se cierra cuando todas las sillas de la mesa se liberan.

### 3.3 Comanda con cuenta partida
- Cliente A paga y se retira, cliente B se queda.
- Al cerrar la comanda de A, se genera `pago`. La sesión_mesa sigue abierta.
- Si B sigue pidiendo, el sistema **abre una comanda nueva** (nueva `comanda` fila) para su silla dentro de la misma `sesion_mesa`.
- Reporte final de la sesión: N comandas cerradas + M pagos.

### 3.4 Cambio de silla
- Mesero re-ubica cliente de silla 3 → silla 5 dentro de la misma mesa.
- La `ocupacion_silla` se mantiene (mismo `id`, cambia `silla_id`). Los tiempos totales se preservan.
- La comanda asociada refleja el cambio en su siguiente ítem (queda registrado histórico).

### 3.5 Pedido para otra silla ("mamá pide por hijos")
- Cada línea de comanda lleva DOS FK a silla:
  - `para_silla_id` = para quién es (dónde se sirve, quién lo consume por defecto).
  - `pedido_por_silla_id` = quién lo ordenó (mamá).
- UX cliente (mamá): selector arriba del catálogo "estás pidiendo para: [Silla 1 (tú) / Silla 2 / Silla 3 / Al centro]". Al agregar cada ítem se asigna a la silla activa.
- UX resumen: antes de "enviar", vista agrupada por silla para revisar.
- UX mesero (iPad): mismo dropdown al agregar ítem desde su interfaz.

### 3.6 Pedido "al centro" (compartido)
- Comanda paralela a las de silla, `es_cuenta_mesa=true`.
- Cocina la ve como pertenece a mesa (sin silla específica).
- Cobro: se puede prorratear al final entre los comensales activos, o pagarlo un anfitrión completo.

### 3.7 Envío inteligente a cocina
- **Cliente presiona "Enviar"**: el ítem entra al `buffer_pre_envio` (estado `esperando_consolidacion`). UX cliente: **feedback opcional** "esperando pedidos de tu mesa" o silencioso (a validar).
- **Mesero coordina desde POSMesero**: ve buffer agrupado por mesa. Un botón "Enviar tanda" consolida todo lo pendiente de esa mesa/estación en un solo `envio_cocina`.
- **Auto-envío opcional**: si pasan N minutos desde el primer buffer sin acción del mesero, el sistema consolida y envía automáticamente. N configurable por área.
- La cocina siempre recibe **envíos**, nunca ítems sueltos → orden FIFO estricto por `envio_cocina.timestamp`.

### 3.8 Llamada al mesero
- Cliente pulsa botón en teléfono → `llamadas_mesero` con `silla_id`, `tipo`, `timestamp`, `atendida_por_mesero_id=NULL`.
- Notificación a **todos los meseros del área** (no personal). Puede ser vibración en iPad + badge visual.
- El primer mesero que abre la llamada → sistema pone su ID en `atendida_por_mesero_id`. Los demás iPads limpian la notificación.
- Trazabilidad para reportes: tiempo de respuesta promedio por mesa/silla/mesero.

### 3.9 Cocina FIFO agrupada visualmente por mesa
- Panel KDS: header con AREA-Palapa, sub-header con MESA N, dentro las tarjetas de ítems del envío.
- Un envío = una "tarjeta grande". Al llegar un nuevo envío del mismo N después, aparece como tarjeta nueva abajo (no se fusiona — es un envío separado).
- Botón "listo" por envío completo o por ítem individual.
- Al marcar listo → notificación push a todos los meseros del área. Primero en abrir queda registrado como quien lo recogió.

### 3.10 Cobro modular
- Cobro NO es "sillas" o "mesa" — es asignación libre de ítems a pagos.
- Pantalla de cobro muestra items pendientes agrupados por silla + "al centro".
- Modo de asignación (varias opciones que generan la misma estructura):
  - **Por silla independiente**: cada silla paga sus ítems.
  - **Mesa completa**: un solo pago cubre todos los ítems abiertos.
  - **Anfitrión-comida**: un pago cubre todos los ítems tipo comida; cada silla paga sus bebidas.
  - **Split libre**: mesero (con auxilio) marca qué ítems paga cada quien.
  - **Mixto de métodos**: un mismo pago puede combinar efectivo + tarjeta + Mercado Pago.
- Backend: N filas en `pagos` + M filas en `asignaciones_pago` (relación pago↔ítem).

### 3.11 Modificadores de ítems
- **Extras con costo**: "+ Aguacate ($25)", "+ Tortillas", "+ Pan". Sumandos al precio unitario.
- **Exclusiones**: "Sin cebolla", "Sin cilantro". Sin costo.
- **Términos/opciones**: "Término medio", "Mucho hielo", "2 shots", "Con vainilla". Sin costo.
- **Notas libres**: "Sin picante por favor", "Cortado en 4". Texto libre del cliente.
- Los tres primeros usan JSONB (`extras_disponibles`, `preferencias_exclusion`, `opciones_termino`) definidos por producto. El cuarto es texto libre en la línea de comanda.

## 4. Modelo de datos

### 4.1 Diagrama de entidades

```
AREA (Palapa, futuras 2)
  └── MESA (varias por área)
        └── SILLA (varias por mesa, cada una con codigo_qr único)

SESION_MESA (una visita completa)
  └── OCUPACION_SILLA (una por silla ocupada durante la sesión)
        └── COMANDA (una o varias por sesión, incluye "cuenta partida" y "al centro")
              └── DETALLE_COMANDA (líneas: producto, cantidad, modificadores, para_silla, pedido_por_silla)
                    ├── BUFFER_PRE_ENVIO (si aún no consolidado por el mesero)
                    └── ENVIO_COCINA (ticket agrupador cuando ya salió)

PAGO
  └── ASIGNACION_PAGO (qué detalle_comanda cubre este pago, con monto)

LLAMADA_MESERO (asociada a silla, atendida por el mesero X)

MESERO (asignado por área, o "todos atienden a todos")
ESTACION_COCINA (cocina, barra, postres — por área)

PRODUCTO_MENU
  └── PRECIOS_HISTORICOS (auditoría de cambios de precio)
```

### 4.2 Schema Postgres — tablas nuevas y modificaciones

**Nuevas:**

```sql
CREATE TABLE areas (
  id SERIAL PRIMARY KEY,
  codigo VARCHAR(10) UNIQUE NOT NULL,  -- 'P' para Palapa
  nombre VARCHAR(100) NOT NULL,
  activa BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sillas (
  id SERIAL PRIMARY KEY,
  mesa_id INT NOT NULL REFERENCES mesas(id) ON DELETE CASCADE,
  numero INT NOT NULL,
  codigo_qr VARCHAR(30) UNIQUE NOT NULL,  -- ej: 'PV-P0101'
  posicion VARCHAR(10),  -- 'N', 'S', 'E', 'O' u otros
  capacidad INT DEFAULT 1,
  activa BOOLEAN DEFAULT true,
  UNIQUE (mesa_id, numero)
);

CREATE TABLE meseros (
  id SERIAL PRIMARY KEY,
  nombre_completo VARCHAR(150) NOT NULL,
  codigo_empleado VARCHAR(20) UNIQUE,
  area_asignada_id INT REFERENCES areas(id),  -- NULL = "todas las áreas"
  activo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE estaciones_cocina (
  id SERIAL PRIMARY KEY,
  area_id INT NOT NULL REFERENCES areas(id),
  codigo VARCHAR(30) NOT NULL,  -- 'cocina_caliente', 'cocina_fria', 'barra', 'postres'
  nombre VARCHAR(100) NOT NULL,
  activa BOOLEAN DEFAULT true,
  UNIQUE (area_id, codigo)
);

CREATE TABLE sesiones_mesa (
  id SERIAL PRIMARY KEY,
  mesa_id INT NOT NULL REFERENCES mesas(id),
  abierta_at TIMESTAMPTZ DEFAULT NOW(),
  cerrada_at TIMESTAMPTZ,
  num_comensales_estimado INT
);

CREATE TABLE ocupaciones_silla (
  id SERIAL PRIMARY KEY,
  sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id) ON DELETE CASCADE,
  silla_id INT NOT NULL REFERENCES sillas(id),
  cliente_display_name VARCHAR(80),  -- opcional
  origen VARCHAR(10) NOT NULL CHECK (origen IN ('qr','mesero')),
  abierta_at TIMESTAMPTZ DEFAULT NOW(),
  cerrada_at TIMESTAMPTZ,
  cerrada_por_mesero_id INT REFERENCES meseros(id)
);

CREATE TABLE envios_cocina (
  id SERIAL PRIMARY KEY,
  sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id),
  estacion_id INT NOT NULL REFERENCES estaciones_cocina(id),
  timestamp_envio TIMESTAMPTZ DEFAULT NOW(),
  timestamp_listo TIMESTAMPTZ,
  timestamp_recogido TIMESTAMPTZ,
  recogido_por_mesero_id INT REFERENCES meseros(id)
);

CREATE TABLE buffer_pre_envio (
  id SERIAL PRIMARY KEY,
  detalle_comanda_id INT NOT NULL REFERENCES detalle_comanda(id) ON DELETE CASCADE,
  creado_at TIMESTAMPTZ DEFAULT NOW(),
  consolidado_en_envio_id INT REFERENCES envios_cocina(id)  -- NULL mientras esté pendiente
);

CREATE TABLE asignaciones_pago (
  id SERIAL PRIMARY KEY,
  pago_id INT NOT NULL REFERENCES pagos(id) ON DELETE CASCADE,
  detalle_comanda_id INT NOT NULL REFERENCES detalle_comanda(id),
  monto_asignado NUMERIC(10,2) NOT NULL CHECK (monto_asignado > 0),
  UNIQUE (pago_id, detalle_comanda_id)
);

CREATE TABLE llamadas_mesero (
  id SERIAL PRIMARY KEY,
  silla_id INT NOT NULL REFERENCES sillas(id),
  ocupacion_silla_id INT REFERENCES ocupaciones_silla(id),
  tipo VARCHAR(30) NOT NULL,  -- 'llamar_mesero','solicitar_cuenta','ayuda_pedido'
  creada_at TIMESTAMPTZ DEFAULT NOW(),
  atendida_at TIMESTAMPTZ,
  atendida_por_mesero_id INT REFERENCES meseros(id)
);

CREATE TABLE precios_historicos (
  id SERIAL PRIMARY KEY,
  producto_id INT NOT NULL REFERENCES productos_menu(id),
  precio_anterior NUMERIC(10,2) NOT NULL,
  precio_nuevo NUMERIC(10,2) NOT NULL,
  cambiado_at TIMESTAMPTZ DEFAULT NOW(),
  cambiado_por VARCHAR(150),  -- FUTURO: FK a usuario admin
  motivo TEXT
);
```

**Modificaciones a tablas existentes:**

```sql
ALTER TABLE mesas ADD COLUMN area_id INT REFERENCES areas(id);

ALTER TABLE productos_menu ADD COLUMN estacion_id INT REFERENCES estaciones_cocina(id);
  -- reemplaza el varchar 'estacion_preparacion' cuando esté migrado

ALTER TABLE comandas ADD COLUMN sesion_mesa_id INT REFERENCES sesiones_mesa(id);

ALTER TABLE detalle_comanda
  ADD COLUMN para_silla_id INT REFERENCES sillas(id),
  ADD COLUMN pedido_por_silla_id INT REFERENCES sillas(id),
  ADD COLUMN envio_cocina_id INT REFERENCES envios_cocina(id),
  ADD COLUMN hora_envio_cocina TIMESTAMPTZ,
  ADD COLUMN hora_listo TIMESTAMPTZ,
  ADD COLUMN hora_servido TIMESTAMPTZ,
  ADD COLUMN notas_cliente TEXT;  -- texto libre del comensal
```

### 4.3 Vistas por rol (draft)

```sql
CREATE OR REPLACE VIEW vw_menu_cliente AS
SELECT p.id, p.codigo_sku, p.nombre, p.descripcion, p.precio_unitario,
       p.icono, p.disponible, p.tiempo_estimado, p.flags_nutricionales,
       p.opciones_termino, p.preferencias_exclusion, p.extras_disponibles,
       c.codigo AS categoria_codigo, c.nombre AS categoria_nombre, c.icono AS categoria_icono
FROM productos_menu p
JOIN categorias c ON p.categoria_id = c.id
WHERE p.disponible = true AND c.activo = true;

CREATE OR REPLACE VIEW vw_menu_mesero AS
SELECT p.*, c.codigo AS categoria_codigo, c.nombre AS categoria_nombre
FROM productos_menu p
JOIN categorias c ON p.categoria_id = c.id
WHERE c.activo = true;
-- El mesero ve tiempo preciso, notas de servicio, extras completos.
-- Excluye 'costo_estimado' vía SELECT explícito si se requiere.

CREATE OR REPLACE VIEW vw_ficha_cocina AS
SELECT p.id, p.nombre, p.ingredientes, p.pasos, p.notas_receta,
       p.tiempo_estimado, p.estacion_preparacion, p.porciones
FROM productos_menu p;
```

## 5. Roadmap de implementación

**Bloque A — Datos base** (Postgres schema + migración de prueba)
**Bloque B — Ocupación por QR + sesión de mesa**
**Bloque C — Comanda con selector "para silla" desde teléfono**
**Bloque D — Buffer inteligente + consolidación por mesero**
**Bloque E — MonitorCocina FIFO agrupado por mesa**
**Bloque F — Cobro modular con asignaciones**
**Bloque G — Llamada al mesero + notificación al área**
**Bloque H — Gestión de Menú & Recetas (form gerencial)**

Bloques I+: Fiscal, lealtad, personal, inventarios/compras, reportes (posteriores).

## 6. Convenciones

- **Códigos QR**: formato `PV-<AreaCodigo><MesaNumero:02d><SillaNumero:02d>`. Ej: `PV-P0101` = Palapa Mesa 1 Silla 1.
- **IVA**: precios en `productos_menu.precio_unitario` **incluyen IVA 16%**. El desglose en ticket se calcula: `subtotal_sin_iva = total / 1.16`, `iva = total - subtotal_sin_iva`.
- **Estados de ocupación**: `abierta` (mientras `cerrada_at IS NULL`), `cerrada` (con timestamp).
- **Estados de comanda**: `abierta`, `enviada_parcial`, `enviada_completa`, `cerrada_pago`, `cancelada`.
- **Estados de detalle**: `borrador`, `buffer`, `enviado_cocina`, `preparando`, `listo`, `servido`, `cancelado`.

## 7. Anti-patrones a evitar (herencia de la deuda técnica anterior)

- No hardcodear datos operacionales en HTML — todo desde Postgres.
- No usar `onclick=""` inline — event delegation desde Python (ya establecido en POSMesero).
- No mezclar `<script>` embebidos en HtmlTemplate — inyección desde Python o assets del theme.
- No duplicar shims de compatibilidad — un solo punto de configuración por concepto.
- No mezclar edición desde el IDE web de Anvil con edición local Antigravity/Claude al mismo tiempo (auto-commit de Anvil pisa cambios externos).

## 8. Preguntas pendientes

1. Formato exacto del QR (¿incluye codigo de área o solo mesa-silla?).
2. UX del buffer para el cliente: ¿feedback "esperando pedidos de tu mesa" o silencioso?
3. Cambio de silla: mantener misma `ocupacion_silla` (cambiando FK) vs cerrar+abrir nueva.
