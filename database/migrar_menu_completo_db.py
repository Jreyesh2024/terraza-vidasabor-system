#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migración integral: Poblar catálogo completo de categorías, platillos,
términos, preferencias y extras directamente en PostgreSQL (dbterrazavidasabor).
"""

import psycopg2
from psycopg2.extras import Json
import json

DATABASE_URL = "postgresql://jreyes@localhost:5432/dbterrazavidasabor"

CATEGORIAS = [
    {
        "id": 1,
        "codigo": "AL_CENTRO",
        "nombre": "Al Centro (Para Compartir)",
        "descripcion": "Platillos y botanas al centro para compartir entre todos los comensales",
        "orden_display": 0,
        "icono": "🍲",
        "destacado": True,
        "es_al_centro": True
    },
    {
        "id": 2,
        "codigo": "BEBIDAS",
        "nombre": "Bebidas & Jugos",
        "descripcion": "Cafetería de altura, jugos naturales prensados al momento y bebidas tradicionales",
        "orden_display": 1,
        "icono": "☕",
        "destacado": False,
        "es_al_centro": False
    },
    {
        "id": 3,
        "codigo": "HUEVOS",
        "nombre": "Huevos & Omelettes",
        "descripcion": "Huevos orgánicos al gusto, rancheros, a la mexicana y omelettes gourmet",
        "orden_display": 2,
        "icono": "🍳",
        "destacado": False,
        "es_al_centro": False
    },
    {
        "id": 4,
        "codigo": "ESPECIALIDADES",
        "nombre": "Especialidades Mexicanas",
        "descripcion": "Chilaquiles artesanales verdes y rojos, enchiladas, molletes y tacos de guisado",
        "orden_display": 3,
        "icono": "🥘",
        "destacado": False,
        "es_al_centro": False
    },
    {
        "id": 5,
        "codigo": "DULCES",
        "nombre": "Dulces & Americanos",
        "descripcion": "Hot cakes esponjosos, waffles belgas y fruta de temporada fresca",
        "orden_display": 4,
        "icono": "🥞",
        "destacado": False,
        "es_al_centro": False
    },
    {
        "id": 6,
        "codigo": "COMBOS",
        "nombre": "Combos Recomendados",
        "descripcion": "Combinaciones completas con platillo fuerte, jugo natural y café caliente",
        "orden_display": 5,
        "icono": "⭐",
        "destacado": False,
        "es_al_centro": False
    },
    {
        "id": 7,
        "codigo": "KIDS",
        "nombre": "Menú Infantil (Kids)",
        "descripcion": "Porciones adaptadas y recetas suaves y nutritivas pensadas para niños",
        "orden_display": 6,
        "icono": "👶",
        "destacado": False,
        "es_al_centro": False
    }
]

PRODUCTOS = [
    # -------------------------------------------------------------
    # 1. AL CENTRO (PARA COMPARTIR)
    # -------------------------------------------------------------
    {
        "categoria_codigo": "AL_CENTRO",
        "sku": "CEN-001",
        "nombre": "Guacamole de la Casa con Chicharrón",
        "descripcion": "Aguacate hass fresco machacado al momento con pico de gallo, limón colima, queso de rancho y crujiente chicharrón de cerdo con totopos artesanales",
        "precio": 145.00,
        "estacion": "cocina",
        "icono": "🥑",
        "es_al_centro": True,
        "tiempo": "6–8 min",
        "porciones": "Para 2 a 4 personas",
        "opciones_termino": ["🥑 Chicharrón crujiente montado", "🥑 Chicharrón aparte en tazón", "🥑 Con totopos calientitos"],
        "preferencias": ["🚫 Sin cebolla", "🚫 Sin cilantro", "🌶️ Sin picante (sin serrano)", "🧂 Poca sal"],
        "extras": [
            {"nombre": "+ Chicharrón de cerdo extra", "precio": 35.00},
            {"nombre": "+ Queso de rancho desmoronado", "precio": 20.00},
            {"nombre": "+ Porción extra de totopos", "precio": 15.00}
        ],
        "ingredientes": ["2 aguacates Hass maduros", "50g pico de gallo fresco", "15ml jugo de limón colima", "60g chicharrón de cerdo crujiente", "30g queso fresco", "Totopos de maíz nixtamal"],
        "pasos": ["Machacar aguacate en molcajete con sal y limón.", "Incorporar pico de gallo.", "Coronar con trozos de chicharrón crujiente y queso fresco.", "Acompañar con totopos calientitos."],
        "notas": "Ideal para botanear al centro."
    },
    {
        "categoria_codigo": "AL_CENTRO",
        "sku": "CEN-002",
        "nombre": "Trilogía de Taquitos de Camarón al Ajillo (Orden de 3)",
        "descripcion": "Tres tacos en tortilla de maíz con costra de queso gouda, camarón salteado al ajillo y chile guajillo, col morada encurtida y aderezo chipotle",
        "precio": 165.00,
        "estacion": "cocina",
        "icono": "🦐",
        "es_al_centro": True,
        "tiempo": "10–12 min",
        "porciones": "Orden de 3 tacos",
        "opciones_termino": ["🌮 Tortilla de maíz nixtamal", "🌮 Tortilla de harina"],
        "preferencias": ["🚫 Sin cebolla", "🚫 Sin cilantro", "🌶️ Aderezo chipotle aparte", "🌶️ Salsa aparte"],
        "extras": [
            {"nombre": "+ Taco adicional (1 pza)", "precio": 55.00},
            {"nombre": "+ Aguacate fresco rebanado", "precio": 25.00},
            {"nombre": "+ Costra de queso adicional", "precio": 20.00}
        ],
        "ingredientes": ["150g camarón pacotilla limpio", "3 tortillas de maíz recién hechas", "60g queso gouda para costra", "Ajo dorado y chile guajillo en aros", "Col morada encurtida", "Aderezo chipotle artesanal"],
        "pasos": ["Formar costras de queso en plancha sobre tortillas.", "Saltear camarón al ajillo con aceite de oliva y mantequilla.", "Montar sobre las costras y decorar con col morada y aderezo."],
        "notas": "Servir con limones y salsa habanera aparte."
    },
    {
        "categoria_codigo": "AL_CENTRO",
        "sku": "CEN-003",
        "nombre": "Orden de Taquitos de Arrachera Marinada (Orden de 3)",
        "descripcion": "Tres tacos de arrachera Angus asada a la plancha con cebollitas caramelizadas, cilantro fresco, chiles toreados y salsa verde molcajeteada",
        "precio": 155.00,
        "estacion": "cocina",
        "icono": "🥩",
        "es_al_centro": True,
        "tiempo": "8–10 min",
        "porciones": "Orden de 3 tacos",
        "opciones_termino": ["🥩 Término 3/4 jugoso", "🥩 Término Medio", "🥩 Bien cocido", "🌮 Tortilla de maíz", "🌮 Tortilla de harina"],
        "preferencias": ["🚫 Sin cebolla", "🚫 Sin cilantro", "🌶️ Chile toreado aparte", "🧂 Poca sal"],
        "extras": [
            {"nombre": "+ Taco adicional (1 pza)", "precio": 50.00},
            {"nombre": "+ Aguacate fresco rebanado", "precio": 25.00},
            {"nombre": "+ Costra de queso adicional", "precio": 20.00},
            {"nombre": "+ Cebollitas cambray asadas", "precio": 20.00}
        ],
        "ingredientes": ["160g arrachera marinada en tiras", "3 tortillas de maíz calientitas", "40g cebollitas cambray asadas", "Cilantro y cebolla picada", "1 chile toreado"],
        "pasos": ["Sellar arrachera a fuego vivo en plancha al término deseado.", "Picar en cubos jugosos.", "Servir en doble tortilla con cebollita asada, cilantro y chile toreado."],
        "notas": "Acompañar con salsa verde molcajeteada."
    },
    {
        "categoria_codigo": "AL_CENTRO",
        "sku": "CEN-004",
        "nombre": "Queso Fundido Tradicional con Chistorra",
        "descripcion": "Cazuelita de barro con mezcla de quesos Oaxaca y Gouda fundidos, doradita chistorra artesanal y rajas poblanas con tortillas de harina y maíz",
        "precio": 135.00,
        "estacion": "cocina",
        "icono": "🧀",
        "es_al_centro": True,
        "tiempo": "8–10 min",
        "porciones": "Para compartir (2-3 personas)",
        "opciones_termino": ["🫓 Con tortillas de maíz calientitas", "🫓 Con tortillas de harina", "🫓 Mixtas (harina y maíz)"],
        "preferencias": ["🚫 Sin rajas poblanas", "🚫 Sin chistorra (solo queso puro)", "🧂 Poca sal"],
        "extras": [
            {"nombre": "+ Chistorra artesanal extra", "precio": 35.00},
            {"nombre": "+ Champiñones al ajillo", "precio": 25.00},
            {"nombre": "+ Tortillas adicionales", "precio": 10.00}
        ],
        "ingredientes": ["150g mezcla de queso Oaxaca y Gouda", "60g chistorra artesanal dorada", "30g rajas de chile poblano", "Tortillas de maíz y harina"],
        "pasos": ["Dorar chistorra.", "Fundir quesos en cazuela a fuego medio hasta gratinar.", "Coronar con la chistorra y rajas.", "Servir burbujeante."],
        "notas": "Servir inmediatamente caliente."
    },
    {
        "categoria_codigo": "AL_CENTRO",
        "sku": "CEN-005",
        "nombre": "Jarra de Agua Fresca Artesanal (1.5 Litros)",
        "descripcion": "Jarra grande para compartir en la mesa. Sabores del día: Horchata con canela de varita, Jamaica fresca o Maracuyá cítrico",
        "precio": 95.00,
        "estacion": "barra_cafe",
        "icono": "🫖",
        "es_al_centro": True,
        "tiempo": "3–4 min",
        "porciones": "1.5 Litros (4 a 5 vasos)",
        "opciones_termino": ["🧊 Mucho hielo", "🧊 Hielo moderado", "🧊 Sin hielo / Al tiempo"],
        "preferencias": ["🍯 Sin azúcar añadida (100% natural)", "🍋 Sin rodajas de cítricos"],
        "extras": [
            {"nombre": "+ Jarabe natural extra", "precio": 10.00},
            {"nombre": "+ Rodajas de naranja / limón", "precio": 10.00},
            {"nombre": "+ Escarchado con chamoy y miguelito", "precio": 15.00}
        ],
        "ingredientes": ["Concentrado artesanal de fruta/grano", "1.2L agua purificada", "Hielos", "Rodajas de cítricos o canela decorativa"],
        "pasos": ["Mezclar en jarra de vidrio con abundante hielo.", "Revolver con cuchara bailarina.", "Servir con vasos escarchados o limpios para la mesa."],
        "notas": "Preguntar sabor preferido."
    },
    {
        "categoria_codigo": "AL_CENTRO",
        "sku": "CEN-006",
        "nombre": "Jarra de Clericot Frutal de la Casa (1.5 Litros)",
        "descripcion": "Jarra refrescante de vino tinto joven con manzana, fresas frescas, toque de cítricos y agua mineral para brindar en grupo",
        "precio": 220.00,
        "estacion": "barra_cafe",
        "icono": "🍷",
        "es_al_centro": True,
        "tiempo": "5 min",
        "porciones": "1.5 Litros (4 a 5 copas)",
        "opciones_termino": ["🍷 Bien frío con hielo", "🍷 Hielo moderado", "🍷 Sin hielo"],
        "preferencias": ["🍎 Sin fruta en la copa", "🍯 Poco dulce"],
        "extras": [
            {"nombre": "+ Porción extra de fruta picada", "precio": 25.00},
            {"nombre": "+ Copa adicional para la mesa", "precio": 0.00}
        ],
        "ingredientes": ["750ml vino tinto de la casa", "Fruta picada (manzana, fresa, naranja)", "Refresco de limón y agua mineral", "Jarabe natural y hielo"],
        "pasos": ["Colocar fruta macerada en la base de la jarra con hielo.", "Agregar vino tinto y espumantes.", "Mezclar suavemente."],
        "notas": "Bebida estrella de la terraza."
    },
    {
        "categoria_codigo": "AL_CENTRO",
        "sku": "CEN-007",
        "nombre": "Papas Rústicas Botaneras al Romero",
        "descripcion": "Gajos de papa doradita con piel aromatizados con romero y paprika ahumada, acompañadas de alioli de ajo asado y dip de queso",
        "precio": 95.00,
        "estacion": "cocina",
        "icono": "🍟",
        "es_al_centro": True,
        "tiempo": "7–9 min",
        "porciones": "Para 2 a 3 personas",
        "opciones_termino": ["🍟 Extra doraditas crujientes", "🍟 Término suave"],
        "preferencias": ["🚫 Sin romero", "🚫 Sin paprika", "🧂 Poca sal"],
        "extras": [
            {"nombre": "+ Dip de queso cheddar fundido", "precio": 20.00},
            {"nombre": "+ Alioli de ajo rostizado extra", "precio": 15.00}
        ],
        "ingredientes": ["220g papas rústicas en gajos", "Romero fresco y paprika", "50ml aderezo alioli de ajo rostizado"],
        "pasos": ["Freír a 180°C hasta obtener textura crujiente dorada.", "Sazonar en tazón con sal, romero y paprika.", "Servir en canastilla con aderezo."],
        "notas": "Excelente botana al centro."
    },

    # -------------------------------------------------------------
    # 2. BEBIDAS & JUGOS
    # -------------------------------------------------------------
    {
        "categoria_codigo": "BEBIDAS",
        "sku": "BEB-501",
        "nombre": "Café Americano / de Olla",
        "descripcion": "Café de altura recién tostado o receta tradicional con canela y piloncillo",
        "precio": 45.00,
        "estacion": "barra_cafe",
        "icono": "☕",
        "es_al_centro": False,
        "tiempo": "3–5 min",
        "porciones": "1 taza (240ml)",
        "opciones_termino": ["☕ Caliente tradicional", "🧊 Frío con hielo", "🍯 Con piloncillo (De Olla)"],
        "preferencias": ["🚫 Sin endulzante", "☕ Descafeinado"],
        "extras": [
            {"nombre": "+ Shot extra de espresso", "precio": 20.00},
            {"nombre": "+ Canela extra de varita", "precio": 0.00}
        ],
        "ingredientes": ["15g café de grano arábica molido", "240ml agua purificada a 90°C", "Opción de olla: piloncillo y canela"],
        "pasos": ["Extraer en cafetera de goteo o hervir infusión de canela y piloncillo.", "Servir bien caliente en taza precalentada."],
        "notas": "Mantener café fresco en contenedor hermético."
    },
    {
        "categoria_codigo": "BEBIDAS",
        "sku": "BEB-502",
        "nombre": "Café con Leche / Capuchino",
        "descripcion": "Espresso doble con leche cremada artesanal al vapor",
        "precio": 68.00,
        "estacion": "barra_cafe",
        "icono": "☕",
        "es_al_centro": False,
        "tiempo": "4–6 min",
        "porciones": "1 taza (240ml)",
        "opciones_termino": ["☕ Caliente tradicional", "🧊 Frappé / Frío (+ $10)", "🥛 Leche entera", "🥛 Leche deslactosada", "🥥 Leche de almendra (+ $15)"],
        "preferencias": ["🍯 Sin azúcar", "☕ Descafeinado"],
        "extras": [
            {"nombre": "+ Shot extra de espresso", "precio": 20.00},
            {"nombre": "+ Jarabe de vainilla / caramelo", "precio": 15.00},
            {"nombre": "+ Canela extra", "precio": 0.00}
        ],
        "ingredientes": ["18g café espresso molido", "60ml espresso doble", "180ml leche cremada al vapor", "Canela"],
        "pasos": ["Extraer espresso doble en taza.", "Cremar leche con textura aterciopelada a 65°C.", "Verter sobre espresso y decorar con canela."],
        "notas": "Textura microespuma sedosa."
    },
    {
        "categoria_codigo": "BEBIDAS",
        "sku": "BEB-503",
        "nombre": "Jugo de Naranja Natural",
        "descripcion": "100% natural recién exprimido al momento",
        "precio": 55.00,
        "estacion": "barra_cafe",
        "icono": "🍊",
        "es_al_centro": False,
        "tiempo": "3–5 min",
        "porciones": "1 vaso (300ml)",
        "opciones_termino": ["🥤 Con hielo", "🥤 Sin hielo / Al tiempo", "🥤 Sin colar"],
        "preferencias": ["🍯 Sin azúcar añadida (100% puro)", "🧊 Poco hielo"],
        "extras": [
            {"nombre": "+ Shot de jengibre fresco", "precio": 15.00},
            {"nombre": "+ Semillas de chía orgánica", "precio": 15.00}
        ],
        "ingredientes": ["4–5 naranjas de jugo frescas (300ml)"],
        "pasos": ["Lavar naranjas, cortar y exprimir en extractor al momento.", "Servir en vaso alto con hielo."],
        "notas": "Exprimir al momento para evitar oxidación."
    },
    {
        "categoria_codigo": "BEBIDAS",
        "sku": "BEB-504",
        "nombre": "Jugo Verde Energético",
        "descripcion": "Nopal, apio, piña, perejil y jugo de naranja fresco",
        "precio": 60.00,
        "estacion": "barra_cafe",
        "icono": "🥬",
        "es_al_centro": False,
        "tiempo": "4–6 min",
        "porciones": "1 vaso (350ml)",
        "opciones_termino": ["🥤 Con hielo", "🥤 Sin hielo / Al tiempo"],
        "preferencias": ["🚫 Sin apio", "🚫 Sin nopal", "🚫 Sin perejil", "🍯 Sin endulzante"],
        "extras": [
            {"nombre": "+ Shot de jengibre", "precio": 15.00},
            {"nombre": "+ Chía orgánica", "precio": 15.00}
        ],
        "ingredientes": ["1/2 nopal tierno limpio", "1 vara de apio fresco", "60g piña en cubos", "Ramita de perejil", "180ml jugo de naranja natural"],
        "pasos": ["Licuar todos los ingredientes a alta velocidad durante 45s.", "Servir de inmediato sin colar."],
        "notas": "Bebida detox de alto valor nutricional."
    },
    {
        "categoria_codigo": "BEBIDAS",
        "sku": "BEB-505",
        "nombre": "Chocolate Caliente Tradicional",
        "descripcion": "Preparado con cacao criollo, canela y leche caliente",
        "precio": 55.00,
        "estacion": "barra_cafe",
        "icono": "🍫",
        "es_al_centro": False,
        "tiempo": "5–7 min",
        "porciones": "1 taza (240ml)",
        "opciones_termino": ["☕ Con leche entera", "🥛 Con leche deslactosada", "🥥 Con leche de almendra (+ $15)", "💧 Con agua tradicional"],
        "preferencias": ["🍯 Poco dulce", "🚫 Sin canela"],
        "extras": [
            {"nombre": "+ Malvaviscos flameados", "precio": 15.00},
            {"nombre": "+ Toque de menta", "precio": 10.00}
        ],
        "ingredientes": ["40g tableta de chocolate de mesa con canela", "240ml leche entera caliente"],
        "pasos": ["Disolver chocolate en leche caliente a fuego bajo.", "Batir con molinillo tradicional hasta espuma espesa."],
        "notas": "Tradición artesanal mexicana."
    },
    {
        "categoria_codigo": "BEBIDAS",
        "sku": "BEB-506",
        "nombre": "Agua Fresca de Fruta del Día",
        "descripcion": "Agua de fruta natural de temporada (500 ml)",
        "precio": 40.00,
        "estacion": "barra_cafe",
        "icono": "🍉",
        "es_al_centro": False,
        "tiempo": "2–3 min",
        "porciones": "1 vaso (500ml)",
        "opciones_termino": ["🧊 Mucho hielo", "🧊 Hielo moderado", "🧊 Sin hielo / Al tiempo"],
        "preferencias": ["🍯 Sin azúcar añadida", "🍋 Con limón"],
        "extras": [
            {"nombre": "+ Chía orgánica", "precio": 15.00},
            {"nombre": "+ Escarchado chamoy y miguelito", "precio": 15.00}
        ],
        "ingredientes": ["500ml agua de fruta natural fresca (Jamaica, Horchata, Limón Chía)", "Hielo al gusto"],
        "pasos": ["Servir en vaso con cubos de hielo."],
        "notas": "Preparada diariamente."
    },
    {
        "categoria_codigo": "BEBIDAS",
        "sku": "BEB-507",
        "nombre": "Refresco de Lata (355ml)",
        "descripcion": "Variedad de refrescos fríos de lata",
        "precio": 38.00,
        "estacion": "barra_cafe",
        "icono": "🥤",
        "es_al_centro": False,
        "tiempo": "1–2 min",
        "porciones": "1 lata (355ml)",
        "opciones_termino": ["🥤 Con vaso y hielo", "🥤 Solo lata fría", "🍋 Con limón y sal"],
        "preferencias": [],
        "extras": [
            {"nombre": "+ Vaso escarchado con chamoy", "precio": 15.00}
        ],
        "ingredientes": ["1 lata 355ml surtida fría", "Vaso con hielo y limón"],
        "pasos": ["Entregar lata cerrada con vaso de hielo."],
        "notas": "Refrigerador a 3°C."
    },

    # -------------------------------------------------------------
    # 3. HUEVOS Y OMELETTES
    # -------------------------------------------------------------
    {
        "categoria_codigo": "HUEVOS",
        "sku": "HUE-101",
        "nombre": "Huevos al Gusto",
        "descripcion": "2 huevos (fritos, revueltos o estrellados) + frijoles + tortillas o pan",
        "precio": 90.00,
        "estacion": "cocina",
        "icono": "🍳",
        "es_al_centro": False,
        "tiempo": "8–10 min",
        "porciones": "1 persona",
        "opciones_termino": ["🍳 Revueltos", "🍳 Estrellados tiernos (yema líquida)", "🍳 Estrellados bien cocidos", "🍳 Fritos volteados"],
        "preferencias": ["🚫 Sin frijoles", "🧂 Poca sal", "🫓 Con tortillas de maíz", "🍞 Con pan tostado"],
        "extras": [
            {"nombre": "+ Tocino crocante dorado", "precio": 35.00},
            {"nombre": "+ Jamón de pavo", "precio": 25.00},
            {"nombre": "+ Aguacate fresco", "precio": 25.00},
            {"nombre": "+ Queso Gouda gratinado", "precio": 25.00}
        ],
        "ingredientes": ["2 huevos frescos", "1 cda aceite o mantequilla", "80g frijoles refritos", "Tortillas o pan"],
        "pasos": ["Cocinar al término solicitado.", "Acompañar con frijoles calientes y tortillas o pan."],
        "notas": "Preguntar siempre término de yema."
    },
    {
        "categoria_codigo": "HUEVOS",
        "sku": "HUE-102",
        "nombre": "Huevos a la Mexicana",
        "descripcion": "Huevos revueltos con jitomate, cebolla y chile + frijoles refritos",
        "precio": 95.00,
        "estacion": "cocina",
        "icono": "🍳",
        "es_al_centro": False,
        "tiempo": "8–10 min",
        "porciones": "1 persona",
        "opciones_termino": ["🍳 Revuelto suave", "🍳 Bien doradito"],
        "preferencias": ["🚫 Sin cebolla", "🌶️ Sin picante (sin chile)", "🚫 Sin cilantro", "🧂 Poca sal"],
        "extras": [
            {"nombre": "+ Tocino crocante", "precio": 35.00},
            {"nombre": "+ Queso fresco de rancho", "precio": 20.00},
            {"nombre": "+ Aguacate rebanado", "precio": 25.00}
        ],
        "ingredientes": ["2 huevos", "40g jitomate picado", "25g cebolla picada", "10–15g chile serrano picado", "10g cilantro", "80g frijoles + tortillas"],
        "pasos": ["Sofríe verdura 2-3 min.", "Agrega huevos batidos.", "Ajusta sal y cilantro."],
        "notas": "Ajustar picante al gusto."
    },
    {
        "categoria_codigo": "HUEVOS",
        "sku": "HUE-103",
        "nombre": "Huevos Rancheros",
        "descripcion": "Huevos estrellados sobre tortilla con salsa roja o verde + frijoles",
        "precio": 105.00,
        "estacion": "cocina",
        "icono": "🍳",
        "es_al_centro": False,
        "tiempo": "10–12 min",
        "porciones": "1 persona",
        "opciones_termino": ["🌿 Salsa Verde clásica", "🍅 Salsa Roja tatemada", "🌶️ Salsa Divorciada (mitad y mitad)"],
        "preferencias": ["🚫 Sin cebolla", "🚫 Sin cilantro", "🥛 Sin crema", "🧀 Sin queso", "🍳 Yema bien cocida"],
        "extras": [
            {"nombre": "+ Porción de bistec (80g)", "precio": 45.00},
            {"nombre": "+ Aguacate fresco", "precio": 25.00},
            {"nombre": "+ Queso gratinado extra", "precio": 25.00}
        ],
        "ingredientes": ["2 huevos", "2 tortillas de maíz pasadas por aceite", "120ml salsa roja o verde caliente", "80g frijoles refritos", "Queso y crema"],
        "pasos": ["Calienta tortillas.", "Fríe huevos estrellados tiernos.", "Coloca sobre tortillas, baña con salsa caliente y corona con queso y crema."],
        "notas": "Salsa hirviendo al servir."
    },
    {
        "categoria_codigo": "HUEVOS",
        "sku": "HUE-104",
        "nombre": "Huevos con Jamón / Tocino / Chorizo",
        "descripcion": "Huevos al gusto + proteína a elegir + frijoles de la olla",
        "precio": 115.00,
        "estacion": "cocina",
        "icono": "🥓",
        "es_al_centro": False,
        "tiempo": "8–10 min",
        "porciones": "1 persona",
        "opciones_termino": ["🥓 Con Tocino dorado", "🥩 Con Jamón de pavo", "🌭 Con Chorizo artesanal"],
        "preferencias": ["🚫 Sin frijoles", "🧂 Poca sal", "🍳 Huevo bien cocido"],
        "extras": [
            {"nombre": "+ Proteína adicional", "precio": 35.00},
            {"nombre": "+ Aguacate fresco", "precio": 25.00},
            {"nombre": "+ Queso Gouda gratinado", "precio": 25.00}
        ],
        "ingredientes": ["2 huevos", "40–50g jamón, tocino o chorizo", "80g frijoles + tortillas"],
        "pasos": ["Dorar proteína elegida, verter huevos batidos y cocinar al punto.", "Servir con frijoles y tortillas."],
        "notas": "Escurrir exceso de grasa."
    },
    {
        "categoria_codigo": "HUEVOS",
        "sku": "HUE-105",
        "nombre": "Omelette de Jamón y Queso",
        "descripcion": "Omelette relleno con queso gouda y jamón + ensalada o frijoles",
        "precio": 125.00,
        "estacion": "cocina",
        "icono": "🧀",
        "es_al_centro": False,
        "tiempo": "7–9 min",
        "porciones": "1 persona",
        "opciones_termino": ["🥗 Con ensalada fresca", "🫘 Con frijoles refritos", "🍞 Con pan tostado", "🫓 Con tortillas"],
        "preferencias": ["🧂 Poca sal", "🥛 Sin mantequilla (con aceite de oliva)"],
        "extras": [
            {"nombre": "+ Champiñones salteados", "precio": 20.00},
            {"nombre": "+ Aguacate fresco", "precio": 25.00},
            {"nombre": "+ Tocino crocante", "precio": 35.00}
        ],
        "ingredientes": ["3 huevos", "40g jamón picado", "40g queso manchego o Oaxaca", "1 cda mantequilla"],
        "pasos": ["Batir huevos con sal y pimienta.", "Cocinar en sartén con mantequilla a fuego medio.", "Agregar jamón y queso, doblar y terminar 1–2 min."],
        "notas": "Consistencia cremosa interior."
    },
    {
        "categoria_codigo": "HUEVOS",
        "sku": "HUE-106",
        "nombre": "Omelette Champiñones y Espinaca",
        "descripcion": "Opción ligera con espinacas baby, champiñón fresco y queso panela",
        "precio": 130.00,
        "estacion": "cocina",
        "icono": "🍄",
        "es_al_centro": False,
        "tiempo": "8–10 min",
        "porciones": "1 persona",
        "opciones_termino": ["🥗 Con ensalada fresca", "🫘 Con frijoles de la olla"],
        "preferencias": ["🧀 Sin queso", "🧂 Poca sal"],
        "extras": [
            {"nombre": "+ Queso de cabra cenizo", "precio": 30.00},
            {"nombre": "+ Aguacate fresco", "precio": 25.00}
        ],
        "ingredientes": ["3 huevos orgánicos", "50g champiñones frescos", "30g espinaca baby", "30g queso panela"],
        "pasos": ["Saltear champiñones y espinaca 2 min.", "Verter huevos batidos, rellenar con salteado y queso, doblar y servir."],
        "notas": "Opción vegetariana."
    },
    {
        "categoria_codigo": "HUEVOS",
        "sku": "HUE-107",
        "nombre": "Machaca con Huevo Norteña",
        "descripcion": "Clásico norteño de carne seca con huevo + frijoles y tortillas de harina",
        "precio": 135.00,
        "estacion": "cocina",
        "icono": "🥩",
        "es_al_centro": False,
        "tiempo": "10–12 min",
        "porciones": "1 persona",
        "opciones_termino": ["🫓 Con tortillas de harina", "🫓 Con tortillas de maíz", "🌶️ Picante suave", "🔥 Picante bravo"],
        "preferencias": ["🚫 Sin cebolla", "🚫 Sin chile", "🧂 Poca sal"],
        "extras": [
            {"nombre": "+ Porción extra de machaca", "precio": 45.00},
            {"nombre": "+ Aguacate fresco", "precio": 25.00},
            {"nombre": "+ Queso asadero fundido", "precio": 25.00}
        ],
        "ingredientes": ["50g machaca de res sonorense", "2 huevos", "Jitomate y cebolla", "80g frijoles + tortillas de harina"],
        "pasos": ["Sofríe verdura, añade machaca para hidratar.", "Incorpora huevos batidos y revuelve bien.", "Servir con frijoles y tortillas de harina."],
        "notas": "Carne seca norteña artesanal."
    },

    # -------------------------------------------------------------
    # 4. ESPECIALIDADES MEXICANAS
    # -------------------------------------------------------------
    {
        "categoria_codigo": "ESPECIALIDADES",
        "sku": "ESP-201",
        "nombre": "Chilaquiles Verdes o Rojos",
        "descripcion": "Con crema, queso y cebolla. Acompañados con huevo o pollo",
        "precio": 145.00,
        "estacion": "cocina",
        "icono": "🥘",
        "es_al_centro": False,
        "tiempo": "15–18 min",
        "porciones": "1 persona",
        "opciones_termino": ["🌿 Salsa Verde clásica", "🍅 Salsa Roja tatemada", "🌶️ Salsa Pasilla suave", "🔥 Salsa Habanero extra", "🍗 Con Pollo deshebrado", "🍳 Con Huevo estrellado"],
        "preferencias": ["🚫 Sin cebolla", "🚫 Sin cilantro", "🥛 Sin crema", "🧀 Sin queso", "🫘 Sin frijoles"],
        "extras": [
            {"nombre": "+ Bistec de Res Asado (100g)", "precio": 45.00},
            {"nombre": "+ Porción Extra de Pollo (50g)", "precio": 35.00},
            {"nombre": "+ Huevo Extra al Gusto", "precio": 20.00},
            {"nombre": "+ Aguacate fresco en rebanadas", "precio": 25.00},
            {"nombre": "+ Queso Gratinado Extra", "precio": 25.00}
        ],
        "ingredientes": ["80–90g totopos artesanos de maíz", "180ml salsa verde o roja casera", "50g pollo deshebrado o 1 huevo", "30g crema mexicana", "25g queso fresco desmoronado", "15g cebolla en pluma", "Cilantro fresco"],
        "pasos": ["Calentar salsa en sartén hondo (3–4 min).", "Agregar totopos y mezclar solo hasta hidratar (1–2 min).", "Servir en plato, coronar con pollo o huevo, crema, queso, cebolla y cilantro."],
        "notas": "Totopos crujientes previamente fritos en hermético."
    },
    {
        "categoria_codigo": "ESPECIALIDADES",
        "sku": "ESP-202",
        "nombre": "Chilaquiles con Bistec o Chorizo",
        "descripcion": "Versión fuerte con bistec a la plancha o chorizo artesanal",
        "precio": 165.00,
        "estacion": "cocina",
        "icono": "🥩",
        "es_al_centro": False,
        "tiempo": "15–18 min",
        "porciones": "1 persona",
        "opciones_termino": ["🥩 Con Bistec de res (Término 3/4)", "🥩 Con Bistec de res (Bien cocido)", "🌭 Con Chorizo artesanal dorado", "🌿 Salsa Verde", "🍅 Salsa Roja"],
        "preferencias": ["🚫 Sin cebolla", "🚫 Sin cilantro", "🥛 Sin crema", "🧀 Sin queso"],
        "extras": [
            {"nombre": "+ Huevo Estrellado Extra", "precio": 20.00},
            {"nombre": "+ Aguacate en Rebanadas", "precio": 25.00},
            {"nombre": "+ Queso Gratinado Extra", "precio": 25.00}
        ],
        "ingredientes": ["90g totopos artesanos de maíz", "180ml salsa verde o roja", "120g bistec plancha o 60g chorizo", "30g crema", "25g queso fresco", "15g cebolla"],
        "pasos": ["Asar bistec al término.", "Preparar chilaquiles en salsa hirviendo 1–2 min.", "Montar chilaquiles con carne en tiras."],
        "notas": "Platillo insignia fuerte."
    },
    {
        "categoria_codigo": "ESPECIALIDADES",
        "sku": "ESP-203",
        "nombre": "Enchiladas de Desayuno",
        "descripcion": "Rojas o verdes, rellenas de pollo o queso + huevo estrellado encima",
        "precio": 145.00,
        "estacion": "cocina",
        "icono": "🌶️",
        "es_al_centro": False,
        "tiempo": "12–15 min",
        "porciones": "1 persona (3 piezas)",
        "opciones_termino": ["🌿 Salsa Verde", "🍅 Salsa Roja", "🍗 Rellenas de Pollo", "🧀 Rellenas de Queso"],
        "preferencias": ["🚫 Sin cebolla", "🥛 Sin crema", "🧀 Sin queso encima"],
        "extras": [
            {"nombre": "+ Porción Extra de Pollo", "precio": 35.00},
            {"nombre": "+ Aguacate en Rebanadas", "precio": 25.00},
            {"nombre": "+ Huevo extra estrellado", "precio": 20.00}
        ],
        "ingredientes": ["3 tortillas maíz pasadas por aceite", "100g pollo o queso", "180ml salsa verde/roja caliente", "1 huevo estrellado", "30g crema", "25g queso fresco"],
        "pasos": ["Rellenar tortillas con pollo/queso y enrollar.", "Bañar con salsa caliente.", "Coronar con huevo estrellado, crema y queso fresco."],
        "notas": "Servir muy caliente."
    },
    {
        "categoria_codigo": "ESPECIALIDADES",
        "sku": "ESP-204",
        "nombre": "Molletes Tradicionales",
        "descripcion": "Bolillo con frijoles refritos, queso gratinado y pico de gallo",
        "precio": 105.00,
        "estacion": "cocina",
        "icono": "🥖",
        "es_al_centro": False,
        "tiempo": "8–10 min",
        "porciones": "1 persona (2 mitades)",
        "opciones_termino": ["🥖 Bolillo crujiente tradicional", "🥖 Suave"],
        "preferencias": ["🚫 Sin pico de gallo", "🌶️ Pico de gallo sin chile", "🚫 Sin cebolla"],
        "extras": [
            {"nombre": "+ Porción de Chorizo Artesanal (40g)", "precio": 30.00},
            {"nombre": "+ Porción de Tocino Dorado (30g)", "precio": 30.00},
            {"nombre": "+ Huevo Estrellado encima", "precio": 20.00},
            {"nombre": "+ Aguacate en Rebanadas", "precio": 25.00}
        ],
        "ingredientes": ["1 bolillo artesano partido a la mitad", "80g frijoles refritos", "50–60g queso manchego o Oaxaca rallado", "40g pico de gallo fresco"],
        "pasos": ["Abrir bolillo y tostar base.", "Untar frijoles, cubrir con queso rallado.", "Gratinar 3–4 min en horno.", "Servir con pico de gallo."],
        "notas": "Pan crujiente por fuera y suave por dentro."
    },
    {
        "categoria_codigo": "ESPECIALIDADES",
        "sku": "ESP-205",
        "nombre": "Tacos de Huevo al Gusto (3 pzas)",
        "descripcion": "3 tacos de huevo con salsa a elegir y frijoles",
        "precio": 85.00,
        "estacion": "cocina",
        "icono": "🌮",
        "es_al_centro": False,
        "tiempo": "8–10 min",
        "porciones": "1 persona (3 tacos)",
        "opciones_termino": ["🌮 Tortilla de maíz", "🌮 Tortilla de harina", "🍳 Huevo con jamón", "🍳 Huevo a la mexicana"],
        "preferencias": ["🚫 Sin cebolla", "🚫 Sin picante"],
        "extras": [
            {"nombre": "+ Aguacate en rebanadas", "precio": 25.00},
            {"nombre": "+ Queso fundido", "precio": 20.00}
        ],
        "ingredientes": ["3 tortillas calientes", "2 huevos revueltos al gusto", "Frijoles y salsas"],
        "pasos": ["Preparar huevo revuelto.", "Montar en 3 tortillas con frijoles y salsa."],
        "notas": "Rápido y económico."
    },
    {
        "categoria_codigo": "ESPECIALIDADES",
        "sku": "ESP-206",
        "nombre": "Tacos de Chorizo con Huevo (3 pzas)",
        "descripcion": "Guisado tradicional en tortillas recién hechas",
        "precio": 95.00,
        "estacion": "cocina",
        "icono": "🌮",
        "es_al_centro": False,
        "tiempo": "8–10 min",
        "porciones": "1 persona (3 tacos)",
        "opciones_termino": ["🌮 Tortilla de maíz", "🌮 Tortilla de harina"],
        "preferencias": ["🚫 Sin cilantro", "🚫 Sin cebolla"],
        "extras": [
            {"nombre": "+ Costra de queso", "precio": 20.00},
            {"nombre": "+ Aguacate", "precio": 25.00}
        ],
        "ingredientes": ["3 tortillas", "50g chorizo artesanal", "2 huevos", "Cebolla y cilantro"],
        "pasos": ["Dorar chorizo 3 min, incorporar huevos y revolver.", "Repartir en 3 tacos con cebolla y cilantro."],
        "notas": "Sabor casero."
    },

    # -------------------------------------------------------------
    # 5. DULCES / AMERICANOS
    # -------------------------------------------------------------
    {
        "categoria_codigo": "DULCES",
        "sku": "DUL-301",
        "nombre": "Hotcakes Clásicos (3 pzas)",
        "descripcion": "Con mantequilla de rancho y miel de maple o cajeta",
        "precio": 110.00,
        "estacion": "cocina",
        "icono": "🥞",
        "es_al_centro": False,
        "tiempo": "12–15 min",
        "porciones": "1 persona (3 piezas)",
        "opciones_termino": ["🥞 Con miel de maple", "🥞 Con cajeta artesanal", "🥞 Con mermelada de frutos rojos"],
        "preferencias": ["🍯 Poca miel", "🧈 Sin mantequilla"],
        "extras": [
            {"nombre": "+ Tocino dorado crocante", "precio": 35.00},
            {"nombre": "+ Frutos rojos frescos", "precio": 30.00},
            {"nombre": "+ Nutella extra", "precio": 25.00}
        ],
        "ingredientes": ["120g harina hotcakes", "1 huevo", "150ml leche", "15g azúcar", "10g mantequilla derretida", "Pizca sal", "Miel y mantequilla"],
        "pasos": ["Mezclar ingredientes hasta masa uniforme.", "Cocinar en sartén antiadherente a fuego medio (2 min por lado).", "Servir torre de 3 con mantequilla y miel o cajeta."],
        "notas": "Fuego medio parejo."
    },
    {
        "categoria_codigo": "DULCES",
        "sku": "DUL-302",
        "nombre": "Hotcakes con Fruta Fresca",
        "descripcion": "Acompañados de plátano, fresas de temporada o mixtas",
        "precio": 130.00,
        "estacion": "cocina",
        "icono": "🍓",
        "es_al_centro": False,
        "tiempo": "12–15 min",
        "porciones": "1 persona (3 piezas)",
        "opciones_termino": ["🥞 Con miel de maple", "🥞 Con miel de abeja", "🥞 Con cajeta artesanal"],
        "preferencias": ["🚫 Sin plátano", "🚫 Sin fresas", "🧈 Sin mantequilla"],
        "extras": [
            {"nombre": "+ Porción extra de fresas", "precio": 25.00},
            {"nombre": "+ Nutella", "precio": 25.00},
            {"nombre": "+ Nuez picada", "precio": 15.00}
        ],
        "ingredientes": ["3 hotcakes", "40g plátano", "40g fresas", "Miel maple"],
        "pasos": ["Cocinar 3 hotcakes.", "Montar intercalando fruta fresca y bañar con miel."],
        "notas": "Favorito familiar."
    },
    {
        "categoria_codigo": "DULCES",
        "sku": "DUL-303",
        "nombre": "Waffles Belgas con Frutas",
        "descripcion": "Waffles dorados con fruta fresca y miel de abeja",
        "precio": 135.00,
        "estacion": "cocina",
        "icono": "🧇",
        "es_al_centro": False,
        "tiempo": "10–12 min",
        "porciones": "1 persona",
        "opciones_termino": ["🧇 Doradito crujiente", "🧇 Término suave"],
        "preferencias": ["🍯 Poca miel", "🧈 Sin mantequilla"],
        "extras": [
            {"nombre": "+ Bola de helado de vainilla", "precio": 25.00},
            {"nombre": "+ Nutella caliente", "precio": 25.00},
            {"nombre": "+ Tocino crocante", "precio": 35.00}
        ],
        "ingredientes": ["1 waffle belga dorado", "Fresas, plátano y moras", "Miel de abeja", "Azúcar glass"],
        "pasos": ["Hornear en waflera 4 min.", "Decorar con fruta fresca, azúcar glass y miel."],
        "notas": "Exterior crujiente."
    },
    {
        "categoria_codigo": "DULCES",
        "sku": "DUL-304",
        "nombre": "Orden de Fruta de Temporada",
        "descripcion": "Papaya, melón y piña con yogurt natural o granola",
        "precio": 95.00,
        "estacion": "cocina",
        "icono": "🍍",
        "es_al_centro": False,
        "tiempo": "4–6 min",
        "porciones": "1 persona",
        "opciones_termino": ["🥣 Con yogurt natural", "🥣 Con miel de abeja", "🥣 Con queso cottage"],
        "preferencias": ["🚫 Sin melón", "🚫 Sin papaya", "🚫 Sin piña"],
        "extras": [
            {"nombre": "+ Granola artesanal extra", "precio": 15.00},
            {"nombre": "+ Queso cottage extra", "precio": 25.00}
        ],
        "ingredientes": ["80g papaya", "80g melón", "80g piña", "Yogurt o granola"],
        "pasos": ["Cortar fruta en cubos uniformes.", "Servir con ramequín de yogurt o granola."],
        "notas": "Fruta fresca del día."
    },
    {
        "categoria_codigo": "DULCES",
        "sku": "DUL-305",
        "nombre": "Yogurt con Granola y Fruta",
        "descripcion": "Bowl fresco con yogurt natural, granola artesanal y fruta",
        "precio": 90.00,
        "estacion": "cocina",
        "icono": "🥣",
        "es_al_centro": False,
        "tiempo": "4–6 min",
        "porciones": "1 persona",
        "opciones_termino": ["🥣 Yogurt natural griego", "🥣 Yogurt sabor fresa"],
        "preferencias": ["🍯 Sin miel añadida"],
        "extras": [
            {"nombre": "+ Semillas de chía orgánica", "precio": 15.00},
            {"nombre": "+ Nuez picada", "precio": 15.00}
        ],
        "ingredientes": ["150g yogurt griego", "40g granola artesanal", "Fresas, plátano y miel"],
        "pasos": ["Cama de yogurt en bowl.", "Decorar con granola y frutas, bañar con miel."],
        "notas": "Opción ligera."
    },

    # -------------------------------------------------------------
    # 6. COMBOS RECOMENDADOS
    # -------------------------------------------------------------
    {
        "categoria_codigo": "COMBOS",
        "sku": "COM-401",
        "nombre": "Combo Clásico Desayuno",
        "descripcion": "Huevos al gusto + frijoles + jugo de naranja + café",
        "precio": 145.00,
        "estacion": "cocina",
        "icono": "⭐",
        "es_al_centro": False,
        "tiempo": "12–15 min",
        "porciones": "1 persona",
        "opciones_termino": ["🍳 Huevos revueltos", "🍳 Huevos estrellados tiernos", "☕ Café americano", "☕ Café de olla"],
        "preferencias": ["🚫 Sin frijoles", "🧂 Poca sal"],
        "extras": [
            {"nombre": "+ Tocino crocante", "precio": 35.00},
            {"nombre": "+ Aguacate en rebanadas", "precio": 25.00}
        ],
        "ingredientes": ["Huevos al gusto con frijoles y tortillas", "Jugo naranja (240ml)", "Café americano o de olla (240ml)"],
        "pasos": ["Servir café y jugo de inmediato.", "Cocinar huevos y servir con guarnición."],
        "notas": "Bebidas al inicio."
    },
    {
        "categoria_codigo": "COMBOS",
        "sku": "COM-402",
        "nombre": "Combo Chilaquiles V&S",
        "descripcion": "Chilaquiles con huevo/pollo + jugo natural + café",
        "precio": 175.00,
        "estacion": "cocina",
        "icono": "⭐",
        "es_al_centro": False,
        "tiempo": "15–18 min",
        "porciones": "1 persona",
        "opciones_termino": ["🌿 Salsa Verde", "🍅 Salsa Roja", "🍗 Con Pollo", "🍳 Con Huevo estrellado"],
        "preferencias": ["🚫 Sin cebolla", "🥛 Sin crema", "🧀 Sin queso"],
        "extras": [
            {"nombre": "+ Bistec asado extra", "precio": 45.00},
            {"nombre": "+ Aguacate fresco", "precio": 25.00}
        ],
        "ingredientes": ["Chilaquiles verdes/rojos con huevo o pollo", "Jugo naranja", "Café americano o de olla"],
        "pasos": ["Entregar café y jugo.", "Preparar chilaquiles y servir calientes."],
        "notas": "Combo estrella matutino."
    },
    {
        "categoria_codigo": "COMBOS",
        "sku": "COM-403",
        "nombre": "Combo Dulce Mañana",
        "descripcion": "Hotcakes + jugo de naranja natural + café americano",
        "precio": 155.00,
        "estacion": "cocina",
        "icono": "⭐",
        "es_al_centro": False,
        "tiempo": "12–15 min",
        "porciones": "1 persona",
        "opciones_termino": ["🥞 Con miel maple", "🥞 Con cajeta", "☕ Café americano", "☕ Café con leche (+ $15)"],
        "preferencias": ["🧈 Sin mantequilla"],
        "extras": [
            {"nombre": "+ Tocino crocante", "precio": 35.00},
            {"nombre": "+ Fruta fresca picada", "precio": 25.00}
        ],
        "ingredientes": ["3 Hotcakes clásicos con mantequilla y miel", "Jugo naranja", "Café americano"],
        "pasos": ["Servir café y jugo.", "Cocinar hotcakes y servir con miel."],
        "notas": "Desayuno dulce."
    },

    # -------------------------------------------------------------
    # 7. MENÚ INFANTIL (KIDS)
    # -------------------------------------------------------------
    {
        "categoria_codigo": "KIDS",
        "sku": "KID-601",
        "nombre": "Hotcakes Infantiles (2 piezas)",
        "descripcion": "2 hotcakes suaves y esponjosos con mantequilla y miel o cajeta",
        "precio": 75.00,
        "estacion": "cocina",
        "icono": "🥞",
        "es_al_centro": False,
        "tiempo": "10–12 min",
        "porciones": "1 niño (2 piezas)",
        "opciones_termino": ["🥞 Con miel maple", "🥞 Con cajeta artesanal"],
        "preferencias": ["🧈 Sin mantequilla"],
        "extras": [
            {"nombre": "+ Fresas o Plátano Rebanado", "precio": 20.00},
            {"nombre": "+ Chispas de Chocolate", "precio": 15.00}
        ],
        "ingredientes": ["80g harina para hotcakes", "1 huevo chico", "100ml leche", "10g azúcar", "8g mantequilla derretida", "Pizca de sal", "Miel o cajeta"],
        "pasos": ["Mezclar ingredientes hasta masa suave.", "Cocinar a fuego medio (1.5–2 min por lado).", "Servir con mantequilla y miel o cajeta."],
        "notas": "Porción infantil suave y esponjosa."
    },
    {
        "categoria_codigo": "KIDS",
        "sku": "KID-602",
        "nombre": "Huevito Feliz con Jamón",
        "descripcion": "Huevo al gusto decorado con jamón en tiras, frijolitos y pan o tortilla",
        "precio": 65.00,
        "estacion": "cocina",
        "icono": "🍳",
        "es_al_centro": False,
        "tiempo": "7–8 min",
        "porciones": "1 niño",
        "opciones_termino": ["🍳 Revuelto suave", "🍳 Estrellado carita feliz"],
        "preferencias": ["🚫 Sin frijoles", "🍞 Con pan tostado", "🫓 Con tortilla"],
        "extras": [
            {"nombre": "+ Queso Oaxaca fundido", "precio": 15.00}
        ],
        "ingredientes": ["1 huevo fresco", "25g jamón en tiras", "50g frijoles refritos suaves", "1 tortilla de maíz o 1/2 bolillo", "1 cdita mantequilla"],
        "pasos": ["Calentar jamón en sartén.", "Cocinar huevo en forma de carita feliz.", "Servir con frijoles y tortilla o pan."],
        "notas": "Montaje divertido para niños."
    },
    {
        "categoria_codigo": "KIDS",
        "sku": "KID-604",
        "nombre": "Mollete Pequeño",
        "descripcion": "1/2 bolillo con frijolitos, queso gratinado y pico de gallo suave",
        "precio": 55.00,
        "estacion": "cocina",
        "icono": "🥖",
        "es_al_centro": False,
        "tiempo": "7–9 min",
        "porciones": "1 niño (1 mitad)",
        "opciones_termino": ["🥖 Bolillo suave", "🥖 Tostado"],
        "preferencias": ["🚫 Sin pico de gallo", "🚫 Sin cebolla"],
        "extras": [
            {"nombre": "+ Porción de Chorizo Infantil (20g)", "precio": 15.00},
            {"nombre": "+ Porción de Tocino", "precio": 15.00}
        ],
        "ingredientes": ["1/2 bolillo artesano", "50g frijoles refritos", "30g queso manchego o Oaxaca rallado", "25g pico de gallo suave (sin picante)"],
        "pasos": ["Abre medio bolillo y calienta.", "Unta frijoles, agrega queso y gratina 3–4 min.", "Sirve con pico de gallo suave."],
        "notas": "Pico de gallo 100% sin chile para niños."
    },
    {
        "categoria_codigo": "KIDS",
        "sku": "KID-605",
        "nombre": "Quesadilla de Queso con Frijolitos",
        "descripcion": "Quesadilla doradita con queso manchego o Oaxaca fundido",
        "precio": 45.00,
        "estacion": "cocina",
        "icono": "🧀",
        "es_al_centro": False,
        "tiempo": "5–6 min",
        "porciones": "1 niño",
        "opciones_termino": ["🌮 En tortilla de harina", "🌮 En tortilla de maíz"],
        "preferencias": ["🚫 Sin frijoles"],
        "extras": [
            {"nombre": "+ Jamón en Cubitos", "precio": 15.00}
        ],
        "ingredientes": ["1 tortilla de harina o maíz", "40g queso Oaxaca o manchego", "40g frijoles refritos para acompañar"],
        "pasos": ["Coloca queso en tortilla y dobla.", "Calienta en comal hasta fundir.", "Sirve con frijoles."],
        "notas": "Queso bien fundido."
    },
    {
        "categoria_codigo": "KIDS",
        "sku": "KID-608",
        "nombre": "Mini Chilaquiles Suaves (Kids)",
        "descripcion": "Totopitos con salsa suave de tomate sin picante, crema y queso fresco",
        "precio": 85.00,
        "estacion": "cocina",
        "icono": "🥘",
        "es_al_centro": False,
        "tiempo": "10–12 min",
        "porciones": "1 niño",
        "opciones_termino": ["🍅 Salsa roja suave sin picante"],
        "preferencias": ["🚫 Sin cebolla", "🥛 Sin crema", "🧀 Sin queso"],
        "extras": [
            {"nombre": "+ Pollo Deshebrado (30g)", "precio": 20.00},
            {"nombre": "+ Huevo Revuelto", "precio": 15.00}
        ],
        "ingredientes": ["50–55g totopos", "100ml salsa roja suave de tomate (sin picante)", "20g crema", "20g queso fresco", "10g cebolla suave"],
        "pasos": ["Calienta salsa suave.", "Agrega totopos y mezcla 1 min hasta hidratar.", "Sirve con crema y queso fresco."],
        "notas": "Salsa 100% sin chile para niños."
    },
    {
        "categoria_codigo": "KIDS",
        "sku": "KID-609",
        "nombre": "Chocolate con Pan Tostado",
        "descripcion": "Chocolate caliente espumoso con pan tostado con mantequilla",
        "precio": 45.00,
        "estacion": "barra_cafe",
        "icono": "🍫",
        "es_al_centro": False,
        "tiempo": "5–6 min",
        "porciones": "1 niño",
        "opciones_termino": ["🥛 Tibio agradable", "🥛 Calientito"],
        "preferencias": ["🧈 Sin mantequilla en el pan"],
        "extras": [
            {"nombre": "+ Malvaviscos", "precio": 15.00}
        ],
        "ingredientes": ["200ml leche tibia", "20–25g chocolate de mesa", "1/2 bolillo o 1 rebanada de pan tostado", "5g mantequilla"],
        "pasos": ["Calienta leche con chocolate hasta disolver.", "Tuesta pan y unta mantequilla.", "Sirve juntos a temperatura tibia."],
        "notas": "Temperatura tibia agradable."
    }
]

def migrar():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    print("🚀 1. Creando columnas en PostgreSQL si no existen...")
    cur.execute("""
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS opciones_termino JSONB DEFAULT '[]'::jsonb;
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS preferencias_exclusion JSONB DEFAULT '[]'::jsonb;
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS extras_disponibles JSONB DEFAULT '[]'::jsonb;
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS tiempo_estimado VARCHAR(50) DEFAULT '10-15 min';
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS porciones VARCHAR(50) DEFAULT '1 porción';
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS ingredientes JSONB DEFAULT '[]'::jsonb;
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS pasos JSONB DEFAULT '[]'::jsonb;
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS notas_receta TEXT DEFAULT '';
        ALTER TABLE productos_menu ADD COLUMN IF NOT EXISTS es_al_centro BOOLEAN DEFAULT FALSE;

        ALTER TABLE categorias ADD COLUMN IF NOT EXISTS es_al_centro BOOLEAN DEFAULT FALSE;
        ALTER TABLE categorias ADD COLUMN IF NOT EXISTS destacado BOOLEAN DEFAULT FALSE;
    """)

    print("📁 2. Insertando/Actualizando Categorías oficiales en PostgreSQL...")
    cat_id_map = {}
    for cat in CATEGORIAS:
        cur.execute("""
            INSERT INTO categorias (codigo, nombre, descripcion, orden_display, icono, destacado, es_al_centro, activo)
            VALUES (%(codigo)s, %(nombre)s, %(descripcion)s, %(orden_display)s, %(icono)s, %(destacado)s, %(es_al_centro)s, TRUE)
            ON CONFLICT (codigo) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                descripcion = EXCLUDED.descripcion,
                orden_display = EXCLUDED.orden_display,
                icono = EXCLUDED.icono,
                destacado = EXCLUDED.destacado,
                es_al_centro = EXCLUDED.es_al_centro,
                activo = TRUE
            RETURNING id, codigo;
        """, cat)
        row = cur.fetchone()
        cat_id_map[row[1]] = row[0]
        print(f"   ✓ Categoría: [{row[0]}] {cat['nombre']} ({cat['icono']})")

    print("🍳 3. Insertando/Actualizando Catálogo Completo de Platillos y Personalizaciones en PostgreSQL...")
    for prod in PRODUCTOS:
        cat_id = cat_id_map.get(prod["categoria_codigo"])
        if not cat_id:
            print(f"   ⚠️ Categoría no encontrada para {prod['sku']}")
            continue

        cur.execute("""
            INSERT INTO productos_menu (
                categoria_id, codigo_sku, nombre, descripcion, precio_unitario,
                estacion_preparacion, icono, es_al_centro, disponible,
                tiempo_estimado, porciones, opciones_termino, preferencias_exclusion,
                extras_disponibles, ingredientes, pasos, notas_receta
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, TRUE,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (codigo_sku) DO UPDATE SET
                categoria_id = EXCLUDED.categoria_id,
                nombre = EXCLUDED.nombre,
                descripcion = EXCLUDED.descripcion,
                precio_unitario = EXCLUDED.precio_unitario,
                estacion_preparacion = EXCLUDED.estacion_preparacion,
                icono = EXCLUDED.icono,
                es_al_centro = EXCLUDED.es_al_centro,
                disponible = TRUE,
                tiempo_estimado = EXCLUDED.tiempo_estimado,
                porciones = EXCLUDED.porciones,
                opciones_termino = EXCLUDED.opciones_termino,
                preferencias_exclusion = EXCLUDED.preferencias_exclusion,
                extras_disponibles = EXCLUDED.extras_disponibles,
                ingredientes = EXCLUDED.ingredientes,
                pasos = EXCLUDED.pasos,
                notas_receta = EXCLUDED.notas_receta;
        """, (
            cat_id, prod["sku"], prod["nombre"], prod["descripcion"], prod["precio"],
            prod["estacion"], prod["icono"], prod["es_al_centro"],
            prod["tiempo"], prod["porciones"],
            Json(prod["opciones_termino"]), Json(prod["preferencias"]),
            Json(prod["extras"]), Json(prod["ingredientes"]),
            Json(prod["pasos"]), prod["notas"]
        ))
        print(f"   ✓ Platillo: [{prod['sku']}] {prod['nombre']} - ${prod['precio']:.2f}")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ ¡Migración de menú completa en PostgreSQL exitosa!")

if __name__ == "__main__":
    migrar()
