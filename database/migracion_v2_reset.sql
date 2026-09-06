-- ============================================================================
-- MIGRACIÓN V2 RESET LIMPIO — La Terraza de Vida & Sabor
-- Fecha: 2026-09-06
-- Diseño: docs/DISENO_DOMINIO_v2.md
--
-- ADVERTENCIA: Este script BORRA todas las tablas operativas y de catálogo
-- y las recrea desde cero según el modelo v2. Solo la tabla clientes_frecuentes
-- se recrea también (estaba vacía).
--
-- Después de correr este script, se debe ejecutar seed_catalogo.sql para
-- repoblar categorias y productos_menu (12 categorías + 57 productos ya
-- respaldados con pg_dump previamente).
--
-- QR portavasos: formato "PV-P-MM-SS" para sillas regulares, "PV-P-EX-NN"
-- para sillas del pool extras.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 0. DROP DE TODAS LAS TABLAS OPERATIVAS Y DE CATÁLOGO
-- ============================================================================
DROP TABLE IF EXISTS asignaciones_pago     CASCADE;
DROP TABLE IF EXISTS pagos                 CASCADE;
DROP TABLE IF EXISTS buffer_pre_envio      CASCADE;
DROP TABLE IF EXISTS envios_cocina         CASCADE;
DROP TABLE IF EXISTS detalle_comanda       CASCADE;
DROP TABLE IF EXISTS comandas              CASCADE;
DROP TABLE IF EXISTS llamadas_mesero       CASCADE;
DROP TABLE IF EXISTS ocupaciones_silla     CASCADE;
DROP TABLE IF EXISTS sesiones_mesa         CASCADE;
DROP TABLE IF EXISTS grupos_mesa_miembros  CASCADE;
DROP TABLE IF EXISTS grupos_mesa           CASCADE;
DROP TABLE IF EXISTS sillas                CASCADE;
DROP TABLE IF EXISTS mesas                 CASCADE;
DROP TABLE IF EXISTS meseros               CASCADE;
DROP TABLE IF EXISTS estaciones_cocina     CASCADE;
DROP TABLE IF EXISTS areas                 CASCADE;
DROP TABLE IF EXISTS clientes_frecuentes   CASCADE;
DROP TABLE IF EXISTS productos_menu        CASCADE;
DROP TABLE IF EXISTS categorias            CASCADE;
DROP TABLE IF EXISTS precios_historicos    CASCADE;
DROP VIEW  IF EXISTS vw_menu_cliente       CASCADE;
DROP VIEW  IF EXISTS vw_menu_mesero        CASCADE;
DROP VIEW  IF EXISTS vw_ficha_cocina       CASCADE;

-- ============================================================================
-- 1. TABLAS DE CATÁLOGO (dependencias mínimas)
-- ============================================================================

CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    orden_display INT DEFAULT 1,
    icono VARCHAR(50) DEFAULT '🍽️',
    destacado BOOLEAN DEFAULT false,
    es_al_centro BOOLEAN DEFAULT false,
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE productos_menu (
    id SERIAL PRIMARY KEY,
    categoria_id INT NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
    codigo_sku VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario >= 0),
    costo_estimado NUMERIC(10,2) DEFAULT 0.00,
    estacion_preparacion VARCHAR(50) DEFAULT 'cocina',
    estacion_id INT,                                   -- FK se agrega tras crear estaciones_cocina
    flags_nutricionales JSONB DEFAULT '{"gluten_free": false, "keto": false, "vegan": false, "lacteos": true}'::jsonb,
    icono VARCHAR(50) DEFAULT '🍲',
    es_al_centro BOOLEAN DEFAULT false,
    disponible BOOLEAN DEFAULT true,
    tiempo_estimado VARCHAR(50) DEFAULT '10-15 min',
    porciones VARCHAR(50) DEFAULT '1 porción',
    opciones_termino JSONB DEFAULT '[]'::jsonb,
    preferencias_exclusion JSONB DEFAULT '[]'::jsonb,
    extras_disponibles JSONB DEFAULT '[]'::jsonb,
    ingredientes JSONB DEFAULT '[]'::jsonb,
    pasos JSONB DEFAULT '[]'::jsonb,
    notas_receta TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Historial de precios (auditoría de cambios)
CREATE TABLE precios_historicos (
    id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL REFERENCES productos_menu(id),
    precio_anterior NUMERIC(10,2) NOT NULL,
    precio_nuevo NUMERIC(10,2) NOT NULL,
    cambiado_at TIMESTAMPTZ DEFAULT NOW(),
    cambiado_por VARCHAR(150),
    motivo TEXT
);
CREATE INDEX idx_precios_hist_producto ON precios_historicos(producto_id, cambiado_at DESC);

-- ============================================================================
-- 2. ÁREAS Y ESTACIONES
-- ============================================================================

CREATE TABLE areas (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) UNIQUE NOT NULL,   -- 'P','C','Y'
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    icono VARCHAR(50) DEFAULT '🏡',
    activa BOOLEAN DEFAULT true,
    orden_display INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE estaciones_cocina (
    id SERIAL PRIMARY KEY,
    area_id INT NOT NULL REFERENCES areas(id),
    codigo VARCHAR(30) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    icono VARCHAR(50) DEFAULT '👨‍🍳',
    activa BOOLEAN DEFAULT true,
    UNIQUE (area_id, codigo)
);

-- FK diferida en productos_menu → estaciones_cocina
ALTER TABLE productos_menu
  ADD CONSTRAINT fk_productos_estacion
  FOREIGN KEY (estacion_id) REFERENCES estaciones_cocina(id);

-- ============================================================================
-- 3. MESAS, SILLAS, GRUPOS DE MESAS
-- ============================================================================

CREATE TABLE mesas (
    id SERIAL PRIMARY KEY,
    area_id INT NOT NULL REFERENCES areas(id),
    numero_mesa INT NOT NULL,
    nombre VARCHAR(60) NOT NULL,           -- "Mesa 1", "Mesa 2"…
    capacidad_sillas INT DEFAULT 4,
    forma VARCHAR(20) DEFAULT 'circular',
    posicion_x NUMERIC(5,2) DEFAULT 0.0,
    posicion_y NUMERIC(5,2) DEFAULT 0.0,
    activa BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (area_id, numero_mesa)
);
CREATE INDEX idx_mesas_area ON mesas(area_id);

CREATE TABLE sillas (
    id SERIAL PRIMARY KEY,
    mesa_id INT REFERENCES mesas(id),      -- NULL = está en el pool (extras sin asignar)
    numero_en_mesa INT,                    -- 1..N cuando está asignada a mesa; NULL en pool
    codigo_qr VARCHAR(30) UNIQUE NOT NULL, -- 'PV-P-01-01' regulares, 'PV-P-EX-01' extras
    posicion VARCHAR(10),                  -- 'N','E','S','O' para regulares
    capacidad INT DEFAULT 1,
    es_adicional BOOLEAN DEFAULT false,    -- true = viene del pool de extras
    activa BOOLEAN DEFAULT true,
    asignada_at TIMESTAMPTZ,               -- cuando el extra fue asignado a la mesa actual
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sillas_mesa ON sillas(mesa_id) WHERE mesa_id IS NOT NULL;
CREATE INDEX idx_sillas_qr   ON sillas(codigo_qr);
CREATE INDEX idx_sillas_pool ON sillas(activa) WHERE mesa_id IS NULL;

-- Grupos de mesas unidas (mesa 1+2, o 1+2+3)
CREATE TABLE grupos_mesa (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(60),
    area_id INT NOT NULL REFERENCES areas(id),
    abierto_at TIMESTAMPTZ DEFAULT NOW(),
    cerrado_at TIMESTAMPTZ,
    notas TEXT
);
CREATE INDEX idx_grupos_mesa_activos ON grupos_mesa(area_id) WHERE cerrado_at IS NULL;

CREATE TABLE grupos_mesa_miembros (
    id SERIAL PRIMARY KEY,
    grupo_mesa_id INT NOT NULL REFERENCES grupos_mesa(id) ON DELETE CASCADE,
    mesa_id INT NOT NULL REFERENCES mesas(id),
    es_maestra BOOLEAN DEFAULT false,
    agregada_at TIMESTAMPTZ DEFAULT NOW(),
    removida_at TIMESTAMPTZ,
    UNIQUE (grupo_mesa_id, mesa_id)
);
CREATE INDEX idx_grupos_miembros_mesa ON grupos_mesa_miembros(mesa_id)
  WHERE removida_at IS NULL;

-- ============================================================================
-- 4. PERSONAL (MESEROS)
-- ============================================================================

CREATE TABLE meseros (
    id SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    codigo_empleado VARCHAR(20) UNIQUE,
    area_asignada_id INT REFERENCES areas(id),  -- NULL = todas
    telefono VARCHAR(20),
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 5. SESIONES, OCUPACIONES, LLAMADAS
-- ============================================================================

CREATE TABLE sesiones_mesa (
    id SERIAL PRIMARY KEY,
    mesa_id INT NOT NULL REFERENCES mesas(id),
    grupo_mesa_id INT REFERENCES grupos_mesa(id),    -- NULL = mesa sola
    abierta_at TIMESTAMPTZ DEFAULT NOW(),
    cerrada_at TIMESTAMPTZ,
    num_comensales_estimado INT,
    notas TEXT
);
CREATE INDEX idx_sesiones_activas ON sesiones_mesa(mesa_id) WHERE cerrada_at IS NULL;

CREATE TABLE ocupaciones_silla (
    id SERIAL PRIMARY KEY,
    sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id) ON DELETE CASCADE,
    silla_id INT NOT NULL REFERENCES sillas(id),
    cliente_display_name VARCHAR(80),
    origen VARCHAR(10) NOT NULL CHECK (origen IN ('qr','mesero')),
    abierta_at TIMESTAMPTZ DEFAULT NOW(),
    cerrada_at TIMESTAMPTZ,
    cerrada_por_mesero_id INT REFERENCES meseros(id)
);
CREATE INDEX idx_ocupaciones_activas ON ocupaciones_silla(silla_id) WHERE cerrada_at IS NULL;
CREATE INDEX idx_ocupaciones_sesion  ON ocupaciones_silla(sesion_mesa_id);

CREATE TABLE llamadas_mesero (
    id SERIAL PRIMARY KEY,
    silla_id INT NOT NULL REFERENCES sillas(id),
    ocupacion_silla_id INT REFERENCES ocupaciones_silla(id),
    tipo VARCHAR(30) NOT NULL,      -- 'llamar_mesero','solicitar_cuenta','ayuda_pedido'
    creada_at TIMESTAMPTZ DEFAULT NOW(),
    atendida_at TIMESTAMPTZ,
    atendida_por_mesero_id INT REFERENCES meseros(id),
    notas TEXT
);
CREATE INDEX idx_llamadas_pendientes ON llamadas_mesero(silla_id, creada_at)
  WHERE atendida_at IS NULL;

-- ============================================================================
-- 6. COMANDAS Y DETALLE
-- ============================================================================

CREATE TABLE comandas (
    id SERIAL PRIMARY KEY,
    sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id),
    folio_ticket VARCHAR(50) UNIQUE,
    tipo VARCHAR(20) NOT NULL DEFAULT 'silla' CHECK (tipo IN ('silla','al_centro')),
    silla_id INT REFERENCES sillas(id),          -- NULL cuando tipo='al_centro'
    mesero_id INT REFERENCES meseros(id),
    estado VARCHAR(30) DEFAULT 'abierta',        -- abierta/enviada_parcial/enviada_completa/cerrada_pago/cancelada
    abierta_at TIMESTAMPTZ DEFAULT NOW(),
    cerrada_at TIMESTAMPTZ,
    subtotal NUMERIC(10,2) DEFAULT 0.00,
    iva_monto NUMERIC(10,2) DEFAULT 0.00,
    propina_monto NUMERIC(10,2) DEFAULT 0.00,
    total NUMERIC(10,2) DEFAULT 0.00,
    notas TEXT
);
CREATE INDEX idx_comandas_sesion ON comandas(sesion_mesa_id);
CREATE INDEX idx_comandas_estado ON comandas(estado);

CREATE TABLE envios_cocina (
    id SERIAL PRIMARY KEY,
    sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id),
    estacion_id INT NOT NULL REFERENCES estaciones_cocina(id),
    timestamp_envio TIMESTAMPTZ DEFAULT NOW(),
    timestamp_recibido_cocina TIMESTAMPTZ,
    timestamp_en_preparacion TIMESTAMPTZ,
    timestamp_listo TIMESTAMPTZ,
    timestamp_recogido TIMESTAMPTZ,
    recogido_por_mesero_id INT REFERENCES meseros(id),
    notas TEXT
);
CREATE INDEX idx_envios_pendientes ON envios_cocina(estacion_id, timestamp_envio)
  WHERE timestamp_listo IS NULL;

CREATE TABLE detalle_comanda (
    id SERIAL PRIMARY KEY,
    comanda_id INT NOT NULL REFERENCES comandas(id) ON DELETE CASCADE,
    producto_id INT NOT NULL REFERENCES productos_menu(id),
    para_silla_id INT REFERENCES sillas(id),                  -- NULL = "al centro"
    pedido_por_silla_id INT REFERENCES sillas(id),            -- NULL = pedido por mesero
    es_al_centro BOOLEAN DEFAULT false,
    tipo_consumo VARCHAR(30) DEFAULT 'comida',                -- comida/bebida/postre_extra
    cantidad INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario_snapshot NUMERIC(10,2) NOT NULL,          -- captura precio al momento
    producto_nombre_snapshot VARCHAR(150) NOT NULL,           -- captura nombre para reportes
    subtotal NUMERIC(10,2) GENERATED ALWAYS AS (precio_unitario_snapshot * cantidad) STORED,
    -- Modificadores aplicados por el cliente en este ítem:
    extras_seleccionados JSONB DEFAULT '[]'::jsonb,           -- [{nombre, precio}, ...]
    exclusiones JSONB DEFAULT '[]'::jsonb,                    -- ["sin cebolla",...]
    opciones_termino_seleccionadas JSONB DEFAULT '[]'::jsonb, -- ["término medio",...]
    notas_cliente TEXT,                                       -- texto libre del comensal
    -- Estado y trazabilidad:
    estado VARCHAR(30) DEFAULT 'borrador',                    -- borrador/buffer/enviado_cocina/preparando/listo/servido/cancelado
    envio_cocina_id INT REFERENCES envios_cocina(id),
    hora_creado TIMESTAMPTZ DEFAULT NOW(),
    hora_enviado_cocina TIMESTAMPTZ,
    hora_listo TIMESTAMPTZ,
    hora_servido TIMESTAMPTZ
);
CREATE INDEX idx_detalle_comanda    ON detalle_comanda(comanda_id);
CREATE INDEX idx_detalle_producto    ON detalle_comanda(producto_id);
CREATE INDEX idx_detalle_para_silla  ON detalle_comanda(para_silla_id);
CREATE INDEX idx_detalle_envio       ON detalle_comanda(envio_cocina_id);

CREATE TABLE buffer_pre_envio (
    id SERIAL PRIMARY KEY,
    detalle_comanda_id INT NOT NULL UNIQUE REFERENCES detalle_comanda(id) ON DELETE CASCADE,
    sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id),
    estacion_id INT NOT NULL REFERENCES estaciones_cocina(id),
    creado_at TIMESTAMPTZ DEFAULT NOW(),
    consolidado_en_envio_id INT REFERENCES envios_cocina(id)  -- NULL mientras esté pendiente
);
CREATE INDEX idx_buffer_pendientes ON buffer_pre_envio(sesion_mesa_id, estacion_id, creado_at)
  WHERE consolidado_en_envio_id IS NULL;

-- ============================================================================
-- 7. PAGOS Y ASIGNACIONES
-- ============================================================================

CREATE TABLE pagos (
    id SERIAL PRIMARY KEY,
    sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id),
    metodo_pago VARCHAR(50) NOT NULL,       -- terminal_santander, mercado_pago_point, efectivo, qr_link
    es_bancarizado BOOLEAN DEFAULT true,
    subtotal_cobrado NUMERIC(10,2) NOT NULL,
    iva_cobrado NUMERIC(10,2) NOT NULL,
    propina_cobrada NUMERIC(10,2) DEFAULT 0.00,
    total_cobrado NUMERIC(10,2) NOT NULL,
    referencia_transaccion VARCHAR(100),
    procesado_por_mesero_id INT REFERENCES meseros(id),
    fecha_pago TIMESTAMPTZ DEFAULT NOW(),
    notas TEXT
);
CREATE INDEX idx_pagos_fecha  ON pagos(fecha_pago);
CREATE INDEX idx_pagos_sesion ON pagos(sesion_mesa_id);

CREATE TABLE asignaciones_pago (
    id SERIAL PRIMARY KEY,
    pago_id INT NOT NULL REFERENCES pagos(id) ON DELETE CASCADE,
    detalle_comanda_id INT NOT NULL REFERENCES detalle_comanda(id),
    monto_asignado NUMERIC(10,2) NOT NULL CHECK (monto_asignado > 0),
    UNIQUE (pago_id, detalle_comanda_id)
);
CREATE INDEX idx_asig_por_item ON asignaciones_pago(detalle_comanda_id);

-- ============================================================================
-- 8. CLIENTES FRECUENTES (recreado para consistencia)
-- ============================================================================

CREATE TABLE clientes_frecuentes (
    id SERIAL PRIMARY KEY,
    codigo_membresia VARCHAR(50) UNIQUE NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(100),
    nivel_membresia VARCHAR(30) DEFAULT 'Platinium',
    puntos_acumulados INT DEFAULT 0,
    total_visitas INT DEFAULT 0,
    fecha_ultimo_consumo TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 9. SEED INICIAL
-- ============================================================================

-- 9.1 Áreas
INSERT INTO areas (codigo, nombre, descripcion, icono, activa, orden_display) VALUES
  ('P', 'Palapa',   'Área principal bajo palapa (6.00m x 4.00m)',   '🏡', true,  1),
  ('C', 'Chimenea', 'Área con chimenea (futura apertura)',          '🔥', false, 2),
  ('Y', 'Patio',    'Área de patio exterior (futura apertura)',     '🌳', false, 3);

-- 9.2 Estaciones de cocina para Palapa
INSERT INTO estaciones_cocina (area_id, codigo, nombre, icono)
SELECT a.id, x.codigo, x.nombre, x.icono
FROM areas a
CROSS JOIN (VALUES
  ('cocina_caliente', 'Cocina Caliente', '🔥'),
  ('cocina_fria',     'Cocina Fría',     '🥗'),
  ('barra',           'Barra & Bebidas', '☕'),
  ('postres',         'Repostería',      '🍰')
) AS x(codigo, nombre, icono)
WHERE a.codigo = 'P';

-- 9.3 Mesas de Palapa: 3 mesas de capacidad 4
INSERT INTO mesas (area_id, numero_mesa, nombre, capacidad_sillas, forma, posicion_x, posicion_y)
SELECT a.id, m.num, 'Mesa ' || m.num, 4, 'cuadrada', m.px, m.py
FROM areas a
CROSS JOIN (VALUES
  (1, 1.50, 2.00),
  (2, 3.00, 2.00),
  (3, 4.50, 2.00)
) AS m(num, px, py)
WHERE a.codigo = 'P';

-- 9.4 Sillas regulares: 4 por mesa (12 total), QR 'PV-P-MM-SS'
INSERT INTO sillas (mesa_id, numero_en_mesa, codigo_qr, posicion, es_adicional)
SELECT
    m.id,
    s.numero,
    'PV-' || a.codigo || '-' ||
        LPAD(m.numero_mesa::text, 2, '0') || '-' ||
        LPAD(s.numero::text, 2, '0')             AS codigo_qr,
    CASE s.numero WHEN 1 THEN 'N' WHEN 2 THEN 'E' WHEN 3 THEN 'S' WHEN 4 THEN 'O' END,
    false
FROM mesas m
JOIN areas a ON m.area_id = a.id
CROSS JOIN LATERAL generate_series(1, m.capacidad_sillas) AS s(numero)
WHERE a.codigo = 'P';

-- 9.5 Sillas del pool extras: 3 sillas sin mesa asignada (mesa_id NULL)
INSERT INTO sillas (mesa_id, numero_en_mesa, codigo_qr, posicion, es_adicional)
SELECT NULL, NULL,
       'PV-P-EX-' || LPAD(n::text, 2, '0'),
       NULL,
       true
FROM generate_series(1, 3) AS n;

-- 9.6 Meseros: uno de arranque, sin área específica (todos atienden a todos)
INSERT INTO meseros (nombre_completo, codigo_empleado, area_asignada_id, activo)
VALUES ('Atención General V&S', 'MES-000', NULL, true);

-- ============================================================================
-- 10. VISTAS POR ROL
-- ============================================================================

CREATE OR REPLACE VIEW vw_menu_cliente AS
SELECT
    p.id, p.codigo_sku, p.nombre, p.descripcion, p.precio_unitario,
    p.icono, p.disponible, p.tiempo_estimado, p.porciones,
    p.flags_nutricionales, p.opciones_termino,
    p.preferencias_exclusion, p.extras_disponibles, p.es_al_centro,
    c.id AS categoria_id, c.codigo AS categoria_codigo,
    c.nombre AS categoria_nombre, c.icono AS categoria_icono,
    c.orden_display AS categoria_orden
FROM productos_menu p
JOIN categorias c ON p.categoria_id = c.id
WHERE p.disponible = true AND c.activo = true;

CREATE OR REPLACE VIEW vw_menu_mesero AS
SELECT
    p.id, p.codigo_sku, p.nombre, p.descripcion, p.precio_unitario,
    p.icono, p.disponible, p.tiempo_estimado, p.porciones,
    p.flags_nutricionales, p.opciones_termino,
    p.preferencias_exclusion, p.extras_disponibles, p.es_al_centro,
    p.notas_receta,
    ec.codigo AS estacion_codigo, ec.nombre AS estacion_nombre,
    c.id AS categoria_id, c.codigo AS categoria_codigo,
    c.nombre AS categoria_nombre, c.icono AS categoria_icono,
    c.orden_display AS categoria_orden
FROM productos_menu p
JOIN categorias c ON p.categoria_id = c.id
LEFT JOIN estaciones_cocina ec ON p.estacion_id = ec.id
WHERE c.activo = true;

CREATE OR REPLACE VIEW vw_ficha_cocina AS
SELECT
    p.id, p.codigo_sku, p.nombre, p.descripcion,
    p.tiempo_estimado, p.porciones,
    p.ingredientes, p.pasos, p.notas_receta,
    p.opciones_termino, p.extras_disponibles,
    ec.codigo AS estacion_codigo, ec.nombre AS estacion_nombre,
    a.codigo AS area_codigo, a.nombre AS area_nombre
FROM productos_menu p
LEFT JOIN estaciones_cocina ec ON p.estacion_id = ec.id
LEFT JOIN areas a ON ec.area_id = a.id;

COMMIT;

-- ============================================================================
-- FIN. Después de este script, ejecutar:
--   psql -U jreyes -d dbterrazavidasabor -f database/seed_catalogo.sql
--
-- Y luego el backfill de estacion_id en productos_menu:
--   UPDATE productos_menu p SET estacion_id = ec.id
--   FROM estaciones_cocina ec JOIN areas a ON ec.area_id = a.id
--   WHERE a.codigo = 'P' AND p.estacion_id IS NULL
--     AND (
--       (p.estacion_preparacion = 'cocina'      AND ec.codigo = 'cocina_caliente') OR
--       (p.estacion_preparacion = 'barra_cafe'  AND ec.codigo = 'barra') OR
--       (p.estacion_preparacion = 'reposteria'  AND ec.codigo = 'postres')
--     );
-- ============================================================================
