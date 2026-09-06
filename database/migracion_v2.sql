-- ============================================================================
-- MIGRACIÓN V2 — La Terraza de Vida & Sabor
-- Fecha: 2026-09-06
-- Diseño: docs/DISENO_DOMINIO_v2.md
--
-- Este script es IDEMPOTENTE: se puede ejecutar múltiples veces sin romper.
-- Usa IF NOT EXISTS / IF EXISTS / CREATE OR REPLACE en todo.
--
-- QR portavasos: formato "PV-<AREA>-<MESA:02>-<SILLA:02>", ej PV-P-01-01.
-- Descarta cualquier QR previo con formato PV-011.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. TABLAS NUEVAS
-- ============================================================================

-- 1.1 Áreas del restaurante (Palapa, Chimenea, Patio)
CREATE TABLE IF NOT EXISTS areas (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) UNIQUE NOT NULL,          -- 'P', 'C', 'Y'
    nombre VARCHAR(100) NOT NULL,                 -- 'Palapa', 'Chimenea', 'Patio'
    descripcion TEXT,
    activa BOOLEAN DEFAULT true,
    orden_display INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.2 Sillas como entidad de primera clase, con QR único
CREATE TABLE IF NOT EXISTS sillas (
    id SERIAL PRIMARY KEY,
    mesa_id INT NOT NULL REFERENCES mesas(id) ON DELETE CASCADE,
    numero INT NOT NULL,                          -- 1..N dentro de la mesa
    codigo_qr VARCHAR(30) UNIQUE NOT NULL,        -- 'PV-P-01-01'
    posicion VARCHAR(10),                          -- 'N', 'E', 'S', 'O'
    capacidad INT DEFAULT 1,
    activa BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (mesa_id, numero)
);

CREATE INDEX IF NOT EXISTS idx_sillas_mesa ON sillas(mesa_id);
CREATE INDEX IF NOT EXISTS idx_sillas_qr ON sillas(codigo_qr);

-- 1.3 Meseros (staff)
CREATE TABLE IF NOT EXISTS meseros (
    id SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    codigo_empleado VARCHAR(20) UNIQUE,
    area_asignada_id INT REFERENCES areas(id),   -- NULL = 'todas las áreas'
    telefono VARCHAR(20),
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.4 Estaciones de cocina por área
CREATE TABLE IF NOT EXISTS estaciones_cocina (
    id SERIAL PRIMARY KEY,
    area_id INT NOT NULL REFERENCES areas(id),
    codigo VARCHAR(30) NOT NULL,                 -- 'cocina_caliente', 'cocina_fria', 'barra', 'postres'
    nombre VARCHAR(100) NOT NULL,
    icono VARCHAR(50) DEFAULT '👨‍🍳',
    activa BOOLEAN DEFAULT true,
    UNIQUE (area_id, codigo)
);

-- 1.5 Sesiones de mesa (una visita completa)
CREATE TABLE IF NOT EXISTS sesiones_mesa (
    id SERIAL PRIMARY KEY,
    mesa_id INT NOT NULL REFERENCES mesas(id),
    abierta_at TIMESTAMPTZ DEFAULT NOW(),
    cerrada_at TIMESTAMPTZ,
    num_comensales_estimado INT,
    notas TEXT
);

CREATE INDEX IF NOT EXISTS idx_sesiones_mesa_abiertas
    ON sesiones_mesa(mesa_id) WHERE cerrada_at IS NULL;

-- 1.6 Ocupaciones de silla (una por silla ocupada durante la sesión)
CREATE TABLE IF NOT EXISTS ocupaciones_silla (
    id SERIAL PRIMARY KEY,
    sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id) ON DELETE CASCADE,
    silla_id INT NOT NULL REFERENCES sillas(id),
    cliente_display_name VARCHAR(80),             -- opcional (ej. "Juan")
    origen VARCHAR(10) NOT NULL CHECK (origen IN ('qr','mesero')),
    abierta_at TIMESTAMPTZ DEFAULT NOW(),
    cerrada_at TIMESTAMPTZ,
    cerrada_por_mesero_id INT REFERENCES meseros(id)
);

CREATE INDEX IF NOT EXISTS idx_ocupaciones_activas
    ON ocupaciones_silla(silla_id) WHERE cerrada_at IS NULL;

-- 1.7 Envíos a cocina (ticket agrupador; 1 envío = varios items)
CREATE TABLE IF NOT EXISTS envios_cocina (
    id SERIAL PRIMARY KEY,
    sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id),
    estacion_id INT NOT NULL REFERENCES estaciones_cocina(id),
    timestamp_envio TIMESTAMPTZ DEFAULT NOW(),
    timestamp_recibido_cocina TIMESTAMPTZ,        -- cocina lo marca "visto"
    timestamp_en_preparacion TIMESTAMPTZ,         -- cocina empezó a cocinar
    timestamp_listo TIMESTAMPTZ,                  -- cocina marca listo
    timestamp_recogido TIMESTAMPTZ,               -- mesero recogió
    recogido_por_mesero_id INT REFERENCES meseros(id),
    notas TEXT
);

CREATE INDEX IF NOT EXISTS idx_envios_cocina_pendientes
    ON envios_cocina(estacion_id, timestamp_envio)
    WHERE timestamp_listo IS NULL;

-- 1.8 Buffer de pre-envío (el "envío inteligente" de 5 min)
CREATE TABLE IF NOT EXISTS buffer_pre_envio (
    id SERIAL PRIMARY KEY,
    detalle_comanda_id INT NOT NULL REFERENCES detalle_comanda(id) ON DELETE CASCADE,
    sesion_mesa_id INT NOT NULL REFERENCES sesiones_mesa(id),
    estacion_id INT NOT NULL REFERENCES estaciones_cocina(id),
    creado_at TIMESTAMPTZ DEFAULT NOW(),
    consolidado_en_envio_id INT REFERENCES envios_cocina(id),  -- NULL mientras pendiente
    UNIQUE (detalle_comanda_id)                                -- un item solo puede estar en un buffer
);

CREATE INDEX IF NOT EXISTS idx_buffer_pendiente
    ON buffer_pre_envio(sesion_mesa_id, estacion_id, creado_at)
    WHERE consolidado_en_envio_id IS NULL;

-- 1.9 Asignaciones de pago (motor de cobro flexible)
CREATE TABLE IF NOT EXISTS asignaciones_pago (
    id SERIAL PRIMARY KEY,
    pago_id INT NOT NULL REFERENCES pagos(id) ON DELETE CASCADE,
    detalle_comanda_id INT NOT NULL REFERENCES detalle_comanda(id),
    monto_asignado NUMERIC(10,2) NOT NULL CHECK (monto_asignado > 0),
    UNIQUE (pago_id, detalle_comanda_id)
);

CREATE INDEX IF NOT EXISTS idx_asig_por_item ON asignaciones_pago(detalle_comanda_id);

-- 1.10 Llamadas al mesero (broadcast a área, primer mesero responde)
CREATE TABLE IF NOT EXISTS llamadas_mesero (
    id SERIAL PRIMARY KEY,
    silla_id INT NOT NULL REFERENCES sillas(id),
    ocupacion_silla_id INT REFERENCES ocupaciones_silla(id),
    tipo VARCHAR(30) NOT NULL,                    -- 'llamar_mesero','solicitar_cuenta','ayuda_pedido'
    creada_at TIMESTAMPTZ DEFAULT NOW(),
    atendida_at TIMESTAMPTZ,
    atendida_por_mesero_id INT REFERENCES meseros(id),
    notas TEXT
);

CREATE INDEX IF NOT EXISTS idx_llamadas_pendientes
    ON llamadas_mesero(silla_id, creada_at)
    WHERE atendida_at IS NULL;

-- 1.11 Grupos de mesas unidas (mesa 1 + mesa 2, o 1+2+3)
-- Modelo: los QR de silla NO cambian; cada silla mantiene su código.
-- El grupo agrega un metadato "estas mesas están físicamente juntas ahora".
CREATE TABLE IF NOT EXISTS grupos_mesa (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(60),                           -- auto: "Mesas 1+2" o libre
    area_id INT NOT NULL REFERENCES areas(id),
    abierto_at TIMESTAMPTZ DEFAULT NOW(),
    cerrado_at TIMESTAMPTZ,
    notas TEXT
);

CREATE INDEX IF NOT EXISTS idx_grupos_mesa_activos
    ON grupos_mesa(area_id) WHERE cerrado_at IS NULL;

CREATE TABLE IF NOT EXISTS grupos_mesa_miembros (
    id SERIAL PRIMARY KEY,
    grupo_mesa_id INT NOT NULL REFERENCES grupos_mesa(id) ON DELETE CASCADE,
    mesa_id INT NOT NULL REFERENCES mesas(id),
    es_maestra BOOLEAN DEFAULT false,             -- la mesa "cabeza" del grupo
    agregada_at TIMESTAMPTZ DEFAULT NOW(),
    removida_at TIMESTAMPTZ,                      -- si una mesa se saca del grupo mid-sesión
    UNIQUE (grupo_mesa_id, mesa_id)
);

CREATE INDEX IF NOT EXISTS idx_grupos_mesa_miembros_mesa
    ON grupos_mesa_miembros(mesa_id) WHERE removida_at IS NULL;

-- 1.12 Historial de cambios de precio
CREATE TABLE IF NOT EXISTS precios_historicos (
    id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL REFERENCES productos_menu(id),
    precio_anterior NUMERIC(10,2) NOT NULL,
    precio_nuevo NUMERIC(10,2) NOT NULL,
    cambiado_at TIMESTAMPTZ DEFAULT NOW(),
    cambiado_por VARCHAR(150),                    -- FUTURO: FK a usuario admin
    motivo TEXT
);

CREATE INDEX IF NOT EXISTS idx_precios_hist_producto
    ON precios_historicos(producto_id, cambiado_at DESC);

-- ============================================================================
-- 2. MODIFICACIONES A TABLAS EXISTENTES
-- ============================================================================

-- 2.1 mesas: agregar area_id
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS area_id INT REFERENCES areas(id);

-- 2.2 productos_menu: agregar estacion_id (FK). El varchar estacion_preparacion
-- se mantiene por retrocompatibilidad hasta que se termine de migrar el JS.
ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS estacion_id INT REFERENCES estaciones_cocina(id);

-- 2.3 comandas: agregar sesion_mesa_id (permite cuentas partidas en una sesión)
ALTER TABLE comandas ADD COLUMN IF NOT EXISTS sesion_mesa_id INT REFERENCES sesiones_mesa(id);

-- 2.3b sesiones_mesa: agregar grupo_mesa_id (si la sesión es de un grupo unido)
ALTER TABLE sesiones_mesa ADD COLUMN IF NOT EXISTS grupo_mesa_id INT REFERENCES grupos_mesa(id);

-- 2.4 detalle_comanda: agregar para_silla_id, pedido_por_silla_id,
-- envio_cocina_id, hora_envio_cocina, hora_listo, hora_servido, notas_cliente
ALTER TABLE detalle_comanda ADD COLUMN IF NOT EXISTS para_silla_id INT REFERENCES sillas(id);
ALTER TABLE detalle_comanda ADD COLUMN IF NOT EXISTS pedido_por_silla_id INT REFERENCES sillas(id);
ALTER TABLE detalle_comanda ADD COLUMN IF NOT EXISTS envio_cocina_id INT REFERENCES envios_cocina(id);
ALTER TABLE detalle_comanda ADD COLUMN IF NOT EXISTS hora_envio_cocina TIMESTAMPTZ;
ALTER TABLE detalle_comanda ADD COLUMN IF NOT EXISTS hora_listo TIMESTAMPTZ;
ALTER TABLE detalle_comanda ADD COLUMN IF NOT EXISTS hora_servido TIMESTAMPTZ;
ALTER TABLE detalle_comanda ADD COLUMN IF NOT EXISTS notas_cliente TEXT;

-- ============================================================================
-- 3. SEED INICIAL
-- ============================================================================

-- 3.1 Áreas (Palapa activa; Chimenea y Patio inactivas por ahora)
INSERT INTO areas (codigo, nombre, descripcion, activa, orden_display) VALUES
    ('P', 'Palapa',   'Área principal bajo palapa (6.00m x 4.00m)', true,  1),
    ('C', 'Chimenea', 'Área con chimenea (futura apertura)',        false, 2),
    ('Y', 'Patio',    'Área de patio exterior (futura apertura)',   false, 3)
ON CONFLICT (codigo) DO NOTHING;

-- 3.2 Backfill: todas las mesas actuales pertenecen a Palapa
UPDATE mesas
SET area_id = (SELECT id FROM areas WHERE codigo = 'P')
WHERE area_id IS NULL;

-- 3.3 Estaciones de cocina de la Palapa
INSERT INTO estaciones_cocina (area_id, codigo, nombre, icono) VALUES
    ((SELECT id FROM areas WHERE codigo = 'P'), 'cocina_caliente', 'Cocina Caliente', '🔥'),
    ((SELECT id FROM areas WHERE codigo = 'P'), 'cocina_fria',     'Cocina Fría',     '🥗'),
    ((SELECT id FROM areas WHERE codigo = 'P'), 'barra',           'Barra & Bebidas', '☕'),
    ((SELECT id FROM areas WHERE codigo = 'P'), 'postres',         'Repostería',      '🍰')
ON CONFLICT (area_id, codigo) DO NOTHING;

-- 3.4 Backfill de productos_menu.estacion_id a partir del varchar estacion_preparacion
UPDATE productos_menu p
SET estacion_id = ec.id
FROM estaciones_cocina ec
JOIN areas a ON ec.area_id = a.id
WHERE a.codigo = 'P'
  AND p.estacion_id IS NULL
  AND (
      (p.estacion_preparacion = 'cocina'      AND ec.codigo = 'cocina_caliente') OR
      (p.estacion_preparacion = 'barra_cafe'  AND ec.codigo = 'barra') OR
      (p.estacion_preparacion = 'reposteria'  AND ec.codigo = 'postres')
  );

-- 3.5 Poblar tabla sillas para todas las mesas de Palapa
-- QR: 'PV-<AreaCodigo>-<MesaNumero:02>-<SillaNumero:02>'
-- Posiciones N/E/S/O para las 4 primeras sillas (para 4-sillas por mesa)
INSERT INTO sillas (mesa_id, numero, codigo_qr, posicion)
SELECT
    m.id                                                    AS mesa_id,
    s.numero                                                AS numero,
    'PV-' || a.codigo || '-' ||
        LPAD(m.numero_mesa::text, 2, '0') || '-' ||
        LPAD(s.numero::text,      2, '0')                   AS codigo_qr,
    CASE s.numero
        WHEN 1 THEN 'N'
        WHEN 2 THEN 'E'
        WHEN 3 THEN 'S'
        WHEN 4 THEN 'O'
        ELSE NULL
    END                                                     AS posicion
FROM mesas m
JOIN areas a ON m.area_id = a.id
CROSS JOIN LATERAL generate_series(1, COALESCE(m.capacidad_sillas, 4)) AS s(numero)
WHERE a.codigo = 'P'
ON CONFLICT (mesa_id, numero) DO NOTHING;

-- ============================================================================
-- 4. VISTAS POR ROL
-- ============================================================================

-- 4.1 Menú Cliente (teléfono QR): info amigable + precio con IVA + alérgenos.
-- Excluye recetas, costos, ingredientes con cantidades, pasos, notas del chef.
CREATE OR REPLACE VIEW vw_menu_cliente AS
SELECT
    p.id,
    p.codigo_sku,
    p.nombre,
    p.descripcion,
    p.precio_unitario,
    p.icono,
    p.disponible,
    p.tiempo_estimado,
    p.porciones,
    p.flags_nutricionales,
    p.opciones_termino,           -- ej: "término medio", "mucho hielo"
    p.preferencias_exclusion,     -- ej: "sin cebolla"
    p.extras_disponibles,         -- ej: [{nombre:"+ Aguacate", precio:25}]
    p.es_al_centro,
    c.id     AS categoria_id,
    c.codigo AS categoria_codigo,
    c.nombre AS categoria_nombre,
    c.icono  AS categoria_icono,
    c.orden_display AS categoria_orden
FROM productos_menu p
JOIN categorias c ON p.categoria_id = c.id
WHERE p.disponible = true AND c.activo = true;

-- 4.2 Menú Mesero (iPad): todo lo del cliente + info operativa para explicar
-- al comensal. Excluye receta técnica y costo interno.
CREATE OR REPLACE VIEW vw_menu_mesero AS
SELECT
    p.id,
    p.codigo_sku,
    p.nombre,
    p.descripcion,
    p.precio_unitario,
    p.icono,
    p.disponible,
    p.tiempo_estimado,
    p.porciones,
    p.flags_nutricionales,
    p.opciones_termino,
    p.preferencias_exclusion,
    p.extras_disponibles,
    p.es_al_centro,
    p.notas_receta,               -- notas de servicio útiles para explicar
    ec.codigo AS estacion_codigo,
    ec.nombre AS estacion_nombre,
    c.id     AS categoria_id,
    c.codigo AS categoria_codigo,
    c.nombre AS categoria_nombre,
    c.icono  AS categoria_icono,
    c.orden_display AS categoria_orden
FROM productos_menu p
JOIN categorias c ON p.categoria_id = c.id
LEFT JOIN estaciones_cocina ec ON p.estacion_id = ec.id
WHERE c.activo = true;
-- NOTA: costo_estimado, ingredientes y pasos NO se exponen en esta vista.

-- 4.3 Ficha Cocina (KDS): ficha técnica completa incluyendo receta.
CREATE OR REPLACE VIEW vw_ficha_cocina AS
SELECT
    p.id,
    p.codigo_sku,
    p.nombre,
    p.descripcion,
    p.tiempo_estimado,
    p.porciones,
    p.ingredientes,               -- lista detallada con cantidades
    p.pasos,                       -- pasos de preparación
    p.notas_receta,               -- notas del chef
    p.opciones_termino,
    p.extras_disponibles,
    ec.codigo AS estacion_codigo,
    ec.nombre AS estacion_nombre,
    a.codigo  AS area_codigo,
    a.nombre  AS area_nombre
FROM productos_menu p
LEFT JOIN estaciones_cocina ec ON p.estacion_id = ec.id
LEFT JOIN areas a ON ec.area_id = a.id;

COMMIT;

-- ============================================================================
-- FIN DE MIGRACIÓN V2
--
-- Verificación post-migración (queries de comprobación, no destructivas):
--
--   SELECT codigo, nombre, activa FROM areas ORDER BY orden_display;
--   SELECT area_id, count(*) FROM mesas GROUP BY area_id;
--   SELECT count(*) FROM sillas;                    -- esperado: 12 mesas * 4 sillas = 48
--   SELECT codigo, nombre FROM estaciones_cocina;
--   SELECT count(*) FROM productos_menu WHERE estacion_id IS NULL;  -- idealmente 0
--   SELECT * FROM vw_menu_cliente  LIMIT 3;
--   SELECT * FROM vw_menu_mesero   LIMIT 3;
--   SELECT * FROM vw_ficha_cocina  LIMIT 3;
-- ============================================================================
