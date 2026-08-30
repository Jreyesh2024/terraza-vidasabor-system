#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
LA TERRAZA DE VIDA & SABOR (V&S) - ANVIL UPLINK DAEMON
Conecta la base de datos PostgreSQL independiente (DBterrazavidasabor) en la
Mac Mini con Anvil.works
============================================================================
"""

import os
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import anvil.server

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ANVIL_UPLINK_KEY = os.getenv("ANVIL_UPLINK_KEY", "server_QFB7TIWJGMUD6GH5J6E2AULV-IP5LP3DMNOTWPG7K")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/DBterrazavidasabor")

def get_db_connection():
    """Abre conexión a PostgreSQL DBterrazavidasabor"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ----------------------------------------------------
# FUNCIONES CALLABLE DE ANVIL (UPLINK RPC)
# ----------------------------------------------------

@anvil.server.callable
def uplink_get_categorias():
    """Obtiene categorías del menú V&S desde PostgreSQL"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM categorias WHERE activo = TRUE ORDER BY orden_display ASC;")
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_categorias: {e}")
        return []

@anvil.server.callable
def uplink_get_productos():
    """Obtiene catálogo completo de platillos V&S desde PostgreSQL"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, c.nombre as categoria_nombre 
                FROM productos_menu p
                JOIN categorias c ON p.categoria_id = c.id
                WHERE p.disponible = TRUE
                ORDER BY c.orden_display, p.nombre;
            """)
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_productos: {e}")
        return []

@anvil.server.callable
def uplink_procesar_cobro(metodo_pago, items_carrito):
    """Registra pago de comanda en PostgreSQL DBterrazavidasabor"""
    try:
        conn = get_db_connection()
        folio = f"VS-TICK-{random.randint(1000, 9999)}"
        subtotal = sum(i['precio_unitario'] * i['cantidad'] for i in items_carrito)
        iva = round(subtotal * 0.16, 2)
        propina = round(subtotal * 0.10, 2)
        total = round(subtotal + propina, 2)

        es_bancarizado = (metodo_pago != 'efectivo')

        with conn.cursor() as cur:
            # Crear comanda en DB
            cur.execute("""
                INSERT INTO comandas (mesa_id, folio_ticket, estado, subtotal, iva_monto, propina_monto, total)
                VALUES (1, %s, 'cerrada', %s, %s, %s, %s)
                RETURNING id;
            """, (folio, subtotal, iva, propina, total))
            comanda_id = cur.fetchone()['id']

            # Registrar items en detalle_comanda
            for item in items_carrito:
                cur.execute("""
                    INSERT INTO detalle_comanda (comanda_id, numero_silla, producto_id, producto_nombre, precio_unitario, cantidad, estado_item)
                    VALUES (%s, 1, %s, %s, %s, %s, 'servido');
                """, (comanda_id, item['id'], item['nombre'], item['precio_unitario'], item['cantidad']))

            # Registrar transacción de pago
            cur.execute("""
                INSERT INTO pagos (comanda_id, tipo_cobro, metodo_pago, es_bancarizado, subtotal_cobrado, iva_cobrado, propina_cobrada, total_cobrado, referencia_transaccion)
                VALUES (%s, 'mesa_completa', %s, %s, %s, %s, %s, %s, %s);
            """, (comanda_id, metodo_pago, es_bancarizado, subtotal, iva, propina, total, f"REF-{folio}"))

        conn.commit()
        conn.close()
        return {
            "success": True,
            "folio": folio,
            "metodo_pago": metodo_pago,
            "subtotal": subtotal,
            "iva": iva,
            "total": total
        }
    except Exception as e:
        print(f"Error en uplink_procesar_cobro: {e}")
        return {"success": False, "error": str(e)}

@anvil.server.callable
def uplink_get_kds():
    """Obtiene comandas en preparación para el monitor de cocina (KDS)"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.*, c.folio_ticket, m.nombre as mesa_nombre
                FROM detalle_comanda d
                JOIN comandas c ON d.comanda_id = c.id
                JOIN mesas m ON c.mesa_id = m.id
                WHERE d.estado_item IN ('pendiente', 'en_preparacion')
                ORDER BY d.created_at ASC;
            """)
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_kds: {e}")
        return []

@anvil.server.callable
def uplink_get_mesas():
    """Obtiene el listado de mesas con su estado y capacidad desde PostgreSQL"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM mesas
                ORDER BY area_nombre, numero_mesa;
            """)
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error en uplink_get_mesas: {e}")
        return []


# ----------------------------------------------------
# CONEXIÓN PRINCIPAL UPLINK DE ANVIL
# ----------------------------------------------------

if __name__ == '__main__':
    print("🌿 Conectando 'La Terraza de Vida & Sabor' (V&S) Anvil Uplink a Anvil.works...")
    print(f"🔑 Key: {ANVIL_UPLINK_KEY[:15]}...")
    anvil.server.connect(ANVIL_UPLINK_KEY)
    print("✅ ¡Conexión Anvil Uplink V&S establecida exitosamente con PostgreSQL!")
    anvil.server.wait_forever()
