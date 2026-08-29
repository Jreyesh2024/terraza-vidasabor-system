-- ============================================================================
-- SCRIPT DE SEMBRADO INICIAL: LA TERRAZA DE VIDA & SABOR (V&S)
-- Base de Datos PostgreSQL: DBterrazavidasabor
-- ============================================================================

BEGIN;

-- 1. CATEGORÍAS DEL MENÚ V&S
INSERT INTO categorias (id, codigo, nombre, descripcion, orden_display, icono) VALUES
(1, 'CAFETERIA', 'Barra de Café & Infusiones', 'Espressos de grano 100% arábica, lattes de especialidad y tés herbales', 1, '☕'),
(2, 'DESAYUNOS', 'Desayunos & Brunch Gourmet', 'Chilaquiles artesanales, omelettes especiales y pancakes de masa madre', 2, '🍳'),
(3, 'ENTRADAS', 'Entradas & Tapas de la Terraza', 'Tabla de quesos artesanales, carpaccios, guacamole especial y croquetas', 3, '🥗'),
(4, 'PLATOS_FUERTES', 'Especialidades Fuertes', 'Cortes seleccionados, pastas artesanales, ensaladas gourmet y hamburguesas V&S', 4, '🥩'),
(5, 'POSTRES', 'Repostería & Postres de Autor', 'Pastel supremo de chocolate, flan artesanal y tarta de frutos del bosque', 5, '🍰'),
(6, 'BEBIDAS', 'Bebidas & Coctelería de Autor', 'Jugos naturales, limonadas botánicas, mimosas y cocteles artesanales', 6, '🍹')
ON CONFLICT (codigo) DO NOTHING;

-- 2. PRODUCTOS Y PLATILLOS DE MENÚ
INSERT INTO productos_menu (categoria_id, codigo_sku, nombre, descripcion, precio_unitario, costo_estimado, estacion_preparacion, icono) VALUES
(1, 'CAF-001', 'Café Capuchino Especial V&S', 'Espresso doble con leche cremada artesanal y toque de canela o cacao', 68.00, 18.00, 'barra_cafe', '☕'),
(1, 'CAF-002', 'Espresso Italiano Robusto', 'Grano seleccionado 100% arábica tostado de la casa (30ml)', 48.00, 12.00, 'barra_cafe', '☕'),
(1, 'CAF-003', 'Latte Machiatto Vainilla Bourbon', 'Espresso con leche de almendra y jarabe natural de vainilla bourbon', 75.00, 22.00, 'barra_cafe', '🥛'),
(1, 'CAF-004', 'Té Matcha Ceremonial Frappé', 'Grado ceremonial de Uji con leche deslactosada y toque de miel de agave', 88.00, 25.00, 'barra_cafe', '🍵'),

(2, 'DES-001', 'Chilaquiles Verdes con Pollo y Queso Gouda', 'Totopos artesanos en salsa de tomatillo a la parrilla con pollo deshebrado y gouda', 148.00, 42.00, 'cocina', '🥘'),
(2, 'DES-002', 'Omelette Supremo La Terraza', '3 huevos orgánicos rellenos de portobello, espinacas baby y queso asadero', 155.00, 45.00, 'cocina', '🍳'),
(2, 'DES-003', 'Molletes de Masa Madre con Chorizo', 'Pan artesano de masa madre con frijol negro refrito, queso gouda y gratinado con chorizo', 125.00, 35.00, 'cocina', '🥖'),
(2, 'DES-004', 'Stack Pancakes de Frutos Rojos', 'Tres pancakes esponjosos servidos con compota de frutos del bosque y miel maple', 135.00, 38.00, 'cocina', '🥞'),

(3, 'ENT-001', 'Tabla de Quesos & Jamón Serrano V&S', 'Queso brie, manchego curado, prosciutto, uvas verdes, nueces y tostadas gourmet', 240.00, 85.00, 'cocina', '🧀'),
(3, 'ENT-002', 'Guacamole Rústico con Rib Eye Chicharrón', 'Aguacate criollo preparado al momento con crujiente chicharrón de Rib Eye', 175.00, 55.00, 'cocina', '🥑'),

(4, 'PF-001', 'Rib Eye Grill V&S (350g)', 'Corte de alta calidad a las brasas servido con papas gajo sazonadas y espárragos', 385.00, 140.00, 'cocina', '🥩'),
(4, 'PF-002', 'Pasta Fettuccine con Camarones al Trufado', 'Pasta fresca hecha en casa con camarones u-15 y crema suave de trufa negra', 265.00, 90.00, 'cocina', '🍝'),

(5, 'POS-001', 'Pastel Supremo de Chocolate Valrhona', 'Rebanada caliente de pastel de chocolate amargo servido con helado de vainilla', 105.00, 30.00, 'reposteria', '🍰'),
(5, 'POS-002', 'Tarta Vasca de Queso con Frutos del Bosque', 'Textura cremosa con cubierta horneada caramelizada y mermelada artesanal', 98.00, 28.00, 'reposteria', '🥧'),

(6, 'BEB-001', 'Limonada Botánica de Hierbabuena & Jengibre', 'Agua mineral infucionada con jengibre fresco, limón eufrata y hierbabuena', 60.00, 14.00, 'barra_cafe', '🍋'),
(6, 'BEB-002', 'Mimosa Sparkling V&S', 'Vino espumoso prosecco combinado con jugo natural de naranja recién exprimido', 110.00, 32.00, 'barra_cafe', '🥂')
ON CONFLICT (codigo_sku) DO NOTHING;

-- 3. MESAS Y ÁREAS DE LA TERRAZA
INSERT INTO mesas (id, area_nombre, numero_mesa, nombre, capacidad_sillas, forma, posicion_x, posicion_y) VALUES
(1, 'Terraza Principal', 1, 'Mesa Terraza 1', 4, 'circular', 25.0, 50.0),
(2, 'Terraza Principal', 2, 'Mesa Terraza 2', 4, 'circular', 50.0, 50.0),
(3, 'Terraza Principal', 3, 'Mesa Terraza 3', 4, 'circular', 75.0, 50.0),
(4, 'Jardín Exterior', 1, 'Mesa Jardín 1', 6, 'rectangular', 35.0, 40.0),
(5, 'Jardín Exterior', 2, 'Mesa Jardín 2', 6, 'rectangular', 65.0, 40.0),
(6, 'Barra de Café', 1, 'Barra V&S Asiento 1', 2, 'circular', 50.0, 20.0)
ON CONFLICT (area_nombre, numero_mesa) DO NOTHING;

-- 4. CLIENTE FRECUENTE DE PRUEBA
INSERT INTO clientes_frecuentes (codigo_membresia, nombre_completo, telefono, email, nivel_membresia, puntos_acumulados, total_visitas) VALUES
('VS-VIP-001', 'Carlos Mendoza', '5551234567', 'carlos.mendoza@email.com', 'VIP', 450, 12)
ON CONFLICT (codigo_membresia) DO NOTHING;

COMMIT;
