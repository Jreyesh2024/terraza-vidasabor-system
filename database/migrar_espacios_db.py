#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migración y sembrado de Áreas, Mesas y Sillas en PostgreSQL (dbterrazavidasabor).
Todos los espacios físicos se normalizan y gestionan desde la base de datos.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://jreyes@localhost:5432/dbterrazavidasabor"

AREAS = [
    {
        "codigo": "TERRAZA_PRINCIPAL",
        "nombre": "Terraza Principal",
        "descripcion": "Área techada principal con vista panorámica y ventilación natural",
        "icono": "🏡",
        "orden": 1
    },
    {
        "codigo": "PATIO_CENTRAL",
        "nombre": "Patio Central",
        "descripcion": "Espacio al aire libre rodeado de fuentes y vegetación",
        "icono": "🌿",
        "orden": 2
    },
    {
        "codigo": "CHIMENEA",
        "nombre": "Área Chimenea & Lounge",
        "descripcion": "Zona cálida y confortable junto a la chimenea artesanal",
        "icono": "🔥",
        "orden": 3
    },
    {
        "codigo": "JARDIN_EXTERIOR",
        "nombre": "Jardín Exterior",
        "descripcion": "Mesas bajo sombra natural de árboles para familias y grupos",
        "icono": "🌳",
        "orden": 4
    },
    {
        "codigo": "BARRA_PALAPA",
        "nombre": "Barra de Café & Palapa",
        "descripcion": "Asientos en barra frente a la estación de baristas y coctelería",
        "icono": "☕",
        "orden": 5
    }
]

MESAS = [
    # Terraza Principal
    {"area_codigo": "TERRAZA_PRINCIPAL", "numero_mesa": 1, "nombre": "Mesa Terraza 1", "capacidad": 4, "forma": "circular", "pos_x": 20.0, "pos_y": 30.0},
    {"area_codigo": "TERRAZA_PRINCIPAL", "numero_mesa": 2, "nombre": "Mesa Terraza 2", "capacidad": 4, "forma": "circular", "pos_x": 50.0, "pos_y": 30.0},
    {"area_codigo": "TERRAZA_PRINCIPAL", "numero_mesa": 3, "nombre": "Mesa Terraza 3", "capacidad": 4, "forma": "circular", "pos_x": 80.0, "pos_y": 30.0},
    
    # Patio Central
    {"area_codigo": "PATIO_CENTRAL", "numero_mesa": 4, "nombre": "Mesa Patio 4 (Grande)", "capacidad": 6, "forma": "rectangular", "pos_x": 30.0, "pos_y": 60.0},
    {"area_codigo": "PATIO_CENTRAL", "numero_mesa": 5, "nombre": "Mesa Patio 5", "capacidad": 4, "forma": "cuadrada", "pos_x": 70.0, "pos_y": 60.0},
    
    # Área Chimenea
    {"area_codigo": "CHIMENEA", "numero_mesa": 6, "nombre": "Mesa Chimenea 6", "capacidad": 4, "forma": "circular", "pos_x": 25.0, "pos_y": 85.0},
    {"area_codigo": "CHIMENEA", "numero_mesa": 7, "nombre": "Mesa Chimenea 7 (Lounge)", "capacidad": 6, "forma": "rectangular", "pos_x": 65.0, "pos_y": 85.0},
    
    # Jardín Exterior
    {"area_codigo": "JARDIN_EXTERIOR", "numero_mesa": 8, "nombre": "Mesa Jardín 8", "capacidad": 6, "forma": "rectangular", "pos_x": 85.0, "pos_y": 60.0},
    
    # Barra de Café / Palapa
    {"area_codigo": "BARRA_PALAPA", "numero_mesa": 9, "nombre": "Barra Asiento 1 & 2", "capacidad": 2, "forma": "barra", "pos_x": 50.0, "pos_y": 10.0}
]

def migrar_espacios():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    print("🏡 1. Sembrando Áreas en PostgreSQL...")
    area_id_map = {}
    for a in AREAS:
        cur.execute("""
            INSERT INTO areas (codigo, nombre, descripcion, icono, orden, activo)
            VALUES (%(codigo)s, %(nombre)s, %(descripcion)s, %(icono)s, %(orden)s, TRUE)
            ON CONFLICT (codigo) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                descripcion = EXCLUDED.descripcion,
                icono = EXCLUDED.icono,
                orden = EXCLUDED.orden,
                activo = TRUE
            RETURNING id, codigo;
        """, a)
        row = cur.fetchone()
        area_id_map[row['codigo']] = row['id']
        print(f"   ✓ Área [{row['id']}]: {a['nombre']} ({a['icono']})")

    print("🪑 2. Sembrando Mesas en PostgreSQL...")
    mesa_id_map = {}
    for m in MESAS:
        area_id = area_id_map.get(m["area_codigo"])
        cur.execute("""
            INSERT INTO mesas (area_nombre, area_id, numero_mesa, nombre, capacidad_sillas, forma, posicion_x, posicion_y, estado, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'disponible', TRUE)
            ON CONFLICT (area_nombre, numero_mesa) DO UPDATE SET
                area_id = EXCLUDED.area_id,
                nombre = EXCLUDED.nombre,
                capacidad_sillas = EXCLUDED.capacidad_sillas,
                forma = EXCLUDED.forma,
                posicion_x = EXCLUDED.posicion_x,
                posicion_y = EXCLUDED.posicion_y,
                activo = TRUE
            RETURNING id, numero_mesa, capacidad_sillas;
        """, (
            m["area_codigo"].replace('_', ' ').title(),
            area_id,
            m["numero_mesa"],
            m["nombre"],
            m["capacidad"],
            m["forma"],
            m["pos_x"],
            m["pos_y"]
        ))
        row = cur.fetchone()
        mesa_id_map[row['id']] = row['capacidad_sillas']
        print(f"   ✓ Mesa [{row['id']}]: {m['nombre']} - {row['capacidad_sillas']} sillas")

    print("🔢 3. Sembrando Sillas y QRs normalizados en PostgreSQL...")
    cur.execute("SELECT id, numero_mesa, capacidad_sillas FROM mesas WHERE activo = TRUE;")
    todas_mesas = cur.fetchall()

    for tm in todas_mesas:
        m_id = tm['id']
        num_m = tm['numero_mesa']
        cap = tm['capacidad_sillas'] or 4

        for s_num in range(1, cap + 1):
            qr = f"PV-{num_m:02d}{s_num}"
            cur.execute("""
                INSERT INTO sillas (mesa_id, numero_silla, codigo_qr, estado, activo)
                VALUES (%s, %s, %s, 'disponible', TRUE)
                ON CONFLICT (codigo_qr) DO UPDATE SET
                    mesa_id = EXCLUDED.mesa_id,
                    numero_silla = EXCLUDED.numero_silla,
                    activo = TRUE;
            """, (m_id, s_num, qr))

    conn.commit()
    cur.close()
    conn.close()
    print("✅ ¡Áreas, Mesas y Sillas sembradas exitosamente en PostgreSQL!")

if __name__ == "__main__":
    migrar_espacios()
