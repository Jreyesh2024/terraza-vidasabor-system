-- ============================================================================
-- SCRIPT DDL INICIAL: LA TERRAZA DE VIDA & SABOR (V&S)
-- Base de Datos PostgreSQL Independiente: DBterrazavidasabor
-- ============================================================================

BEGIN;

-- 1. TABLA DE CATEGORÍAS DEL MENÚ
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    orden_display INT DEFAULT 1,
    icono VARCHAR(50) DEFAULT '🍽️',
    destacado BOOLEAN DEFAULT FALSE,
    es_al_centro BOOLEAN DEFAULT FALSE,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABLA DE PRODUCTOS Y PLATILLOS DEL MENÚ
CREATE TABLE IF NOT EXISTS productos_menu (
    id SERIAL PRIMARY KEY,
    categoria_id INT NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
    codigo_sku VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario >= 0),
    costo_estimado NUMERIC(10,2) DEFAULT 0.00,
    estacion_preparacion VARCHAR(50) DEFAULT 'cocina', -- 'cocina', 'barra_cafe', 'reposteria'
    flags_nutricionales JSONB DEFAULT '{"gluten_free": false, "keto": false, "vegan": false, "lacteos": true}'::jsonb,
    icono VARCHAR(50) DEFAULT '🍲',
    es_al_centro BOOLEAN DEFAULT FALSE,
    disponible BOOLEAN DEFAULT TRUE,
    tiempo_estimado VARCHAR(50) DEFAULT '10-15 min',
    porciones VARCHAR(50) DEFAULT '1 porción',
    opciones_termino JSONB DEFAULT '[]'::jsonb,         -- Términos de cocción o temperatura (ej: Término medio, Mucho hielo, etc.)
    preferencias_exclusion JSONB DEFAULT '[]'::jsonb,   -- Ingredientes que se pueden quitar (ej: Sin cebolla, Sin cilantro)
    extras_disponibles JSONB DEFAULT '[]'::jsonb,       -- Extras con costo adicional (ej: [{"nombre": "+ Tocino", "precio": 35.00}])
    ingredientes JSONB DEFAULT '[]'::jsonb,             -- Lista detallada de ingredientes para la receta
    pasos JSONB DEFAULT '[]'::jsonb,                    -- Pasos de preparación para la cocina / barista
    notas_receta TEXT DEFAULT '',                       -- Notas del chef o indicaciones de servicio
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. TABLA DE MESAS Y ÁREAS DE LA TERRAZA
CREATE TABLE IF NOT EXISTS mesas (
    id SERIAL PRIMARY KEY,
    area_nombre VARCHAR(100) NOT NULL, -- 'Terraza Principal', 'Jardín Exterior', 'Barra de Café'
    numero_mesa INT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    capacidad_sillas INT DEFAULT 4,
    forma VARCHAR(20) DEFAULT 'circular',
    posicion_x NUMERIC(5,2) DEFAULT 0.0,
    posicion_y NUMERIC(5,2) DEFAULT 0.0,
    estado VARCHAR(30) DEFAULT 'disponible', -- 'disponible', 'ocupada', 'precuenta', 'reservada'
    alerta_mesero BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_area_numero_mesa UNIQUE (area_nombre, numero_mesa)
);

-- 4. TABLA DE COMANDAS PRINCIPALES DE MESA
CREATE TABLE IF NOT EXISTS comandas (
    id SERIAL PRIMARY KEY,
    mesa_id INT NOT NULL REFERENCES mesas(id),
    folio_ticket VARCHAR(50) UNIQUE,
    mesero_nombre VARCHAR(100) DEFAULT 'Atención General V&S',
    estado VARCHAR(30) DEFAULT 'abierta', -- 'abierta', 'en_preparacion', 'precuenta', 'cerrada', 'cancelada'
    fecha_apertura TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMP WITH TIME ZONE,
    subtotal NUMERIC(10,2) DEFAULT 0.00,
    iva_monto NUMERIC(10,2) DEFAULT 0.00,
    propina_monto NUMERIC(10,2) DEFAULT 0.00,
    total NUMERIC(10,2) DEFAULT 0.00,
    notas TEXT
);

-- 5. TABLA DE DETALLE DE COMANDA POR SILLA / COMENSAL O CUENTA DE MESA
CREATE TABLE IF NOT EXISTS detalle_comanda (
    id SERIAL PRIMARY KEY,
    comanda_id INT NOT NULL REFERENCES comandas(id) ON DELETE CASCADE,
    numero_silla INT NOT NULL DEFAULT 1, -- 0 o NULL si es Cuenta de Mesa (al centro)
    es_cuenta_mesa BOOLEAN DEFAULT FALSE, -- TRUE si es platillo al centro / cuenta de mesa
    tipo_consumo VARCHAR(30) DEFAULT 'comida', -- 'comida', 'bebida', 'postre_extra'
    producto_id INT NOT NULL REFERENCES productos_menu(id),
    producto_nombre VARCHAR(150) NOT NULL,
    precio_unitario NUMERIC(10,2) NOT NULL,
    cantidad INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    subtotal NUMERIC(10,2) GENERATED ALWAYS AS (precio_unitario * cantidad) STORED,
    estado_item VARCHAR(30) DEFAULT 'pendiente', -- 'pendiente', 'en_preparacion', 'listo', 'servido', 'cancelado'
    notas_preparacion TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. TABLA DE REGISTRO TRANSACCIONAL Y MONITOREO FISCAL DE PAGOS
CREATE TABLE IF NOT EXISTS pagos (
    id SERIAL PRIMARY KEY,
    comanda_id INT NOT NULL REFERENCES comandas(id),
    numero_silla INT, -- NULL si es cobro de mesa completa o cuenta de mesa
    tipo_cobro VARCHAR(40) DEFAULT 'mesa_completa', -- 'mesa_completa', 'por_silla', 'cuenta_mesa', 'anfitrion_comida', 'split_comida'
    metodo_pago VARCHAR(50) NOT NULL, -- 'terminal_santander', 'mercado_pago_point', 'efectivo'
    es_bancarizado BOOLEAN DEFAULT TRUE,
    subtotal_cobrado NUMERIC(10,2) NOT NULL,
    iva_cobrado NUMERIC(10,2) NOT NULL,
    propina_cobrada NUMERIC(10,2) DEFAULT 0.00,
    total_cobrado NUMERIC(10,2) NOT NULL,
    referencia_transaccion VARCHAR(100),
    fecha_pago TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. TABLA DE CLIENTES FRECUENTES / PROGRAMA DE LEALTAD V&S REWARDS
CREATE TABLE IF NOT EXISTS clientes_frecuentes (
    id SERIAL PRIMARY KEY,
    codigo_membresia VARCHAR(50) UNIQUE NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(100),
    nivel_membresia VARCHAR(30) DEFAULT 'Platinium', -- 'Platinium', 'Gold', 'VIP'
    puntos_acumulados INT DEFAULT 0,
    total_visitas INT DEFAULT 0,
    fecha_ultimo_consumo TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ÍNDICES PARA ALTO RENDIMIENTO
CREATE INDEX IF NOT EXISTS idx_comandas_mesa_estado ON comandas(mesa_id, estado);
CREATE INDEX IF NOT EXISTS idx_detalle_comanda_comanda ON detalle_comanda(comanda_id);
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_metodo ON pagos(fecha_pago, metodo_pago);

COMMIT;
