#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación para el Bloque D:
1. Check-in seamless cuando la silla fue activada por el mesero.
2. Buffer de acumulación de ítems por mesa (buffer_pre_envio).
3. Enrutamiento automático por estación (Cocina vs Barra).
4. Merge inteligente en cola (anexar ítems a ticket en espera).
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Importar funciones de uplink
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "uplink"))
from terraza_uplink import (
    uplink_checkin_silla_qr,
    uplink_actualizar_cuenta_silla,
    uplink_agregar_item_a_comanda,
    uplink_liberar_buffer_mesa,
    uplink_get_estado_buffer_mesa,
    uplink_liberar_silla,
    get_db_connection
)

def run_tests():
    print("🧪 ============================================================")
    print("   INICIANDO PRUEBAS AUTOMATIZADAS: BLOQUE D")
    print("============================================================\n")

    # Limpiar estado de Mesa 1 para pruebas limpias
    uplink_liberar_silla(1, 1)
    uplink_liberar_silla(1, 2)

    # -------------------------------------------------------------------------
    # TEST 1: Check-in Seamless (Mesero activa primero -> Cliente escanea QR)
    # -------------------------------------------------------------------------
    print("▶️ TEST 1: Activación por mesero y escaneo posterior del cliente...")
    # Mesero activa silla 1
    uplink_actualizar_cuenta_silla(1, 1, [], estado='ocupada')
    
    # Cliente escanea su QR
    resp_qr = uplink_checkin_silla_qr(1, 1, qr_id='PV-P-01-01')
    
    assert "error" not in resp_qr or resp_qr.get("error") is None, f"Fallo checkin: {resp_qr}"
    assert resp_qr.get("ya_ocupada") is False, "ya_ocupada no debe bloquear al cliente"
    print("   ✅ Test 1 PASÓ: El cliente entró directo al menú sin pantalla de bloqueo.\n")

    # -------------------------------------------------------------------------
    # TEST 2: Buffer de acumulación y enrutamiento por estación (Barra vs Cocina)
    # -------------------------------------------------------------------------
    print("▶️ TEST 2: Agregar bebida (Barra) y comida (Cocina) al buffer...")
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Obtener un producto de barra y uno de cocina
        cur.execute("SELECT id, nombre, estacion_id FROM productos_menu WHERE estacion_id = 3 LIMIT 1;")
        prod_barra = cur.fetchone()
        cur.execute("SELECT id, nombre, estacion_id FROM productos_menu WHERE estacion_id = 1 LIMIT 1;")
        prod_cocina = cur.fetchone()
    conn.close()

    assert prod_barra and prod_cocina, "Deben existir productos asignados a barra y cocina"

    # Silla 1 pide bebida
    item_b = uplink_agregar_item_a_comanda(1, 1, prod_barra['id'], cantidad=1)
    assert item_b.get("ok"), f"Fallo agregar bebida: {item_b}"

    # Silla 2 pide comida
    item_c = uplink_agregar_item_a_comanda(1, 2, prod_cocina['id'], cantidad=2)
    assert item_c.get("ok"), f"Fallo agregar comida: {item_c}"

    # Consultar estado del buffer
    buf_estado = uplink_get_estado_buffer_mesa(1)
    print(f"   ℹ️ Estado del Buffer Mesa 1: {buf_estado}")
    assert buf_estado.get("items_en_buffer") == 2, f"Esperaba 2 items en buffer, obtuvo: {buf_estado}"
    print("   ✅ Test 2 PASÓ: Los ítems se acumularon correctamente en buffer_pre_envio.\n")

    # -------------------------------------------------------------------------
    # TEST 3: Consolidación por mesa hacia múltiples estaciones (Barra y Cocina)
    # -------------------------------------------------------------------------
    print("▶️ TEST 3: Liberación de buffer y despacho a Barra y Cocina...")
    liberacion = uplink_liberar_buffer_mesa(1)
    print(f"   ℹ️ Resultado liberación: {liberacion}")
    assert liberacion.get("ok"), f"Fallo liberación: {liberacion}"
    assert liberacion.get("enviados") == 2, f"Esperaba 2 items enviados, obtuvo {liberacion.get('enviados')}"
    assert len(liberacion.get("envios", [])) == 2, f"Esperaba 2 envíos (Barra y Cocina), obtuvo {len(liberacion.get('envios', []))}"
    
    envio_cocina_1 = [e for e in liberacion["envios"] if e["estacion_id"] == 1][0]
    print(f"   ✅ Test 3 PASÓ: Se generaron 2 envíos separados por estación (Envío Cocina #{envio_cocina_1['envio_id']}).\n")

    # -------------------------------------------------------------------------
    # TEST 4: Merge inteligente en cola (Incorporación a ticket en espera)
    # -------------------------------------------------------------------------
    print("▶️ TEST 4: Cliente 1 pide otro platillo mientras el ticket sigue en espera en cocina...")
    item_c2 = uplink_agregar_item_a_comanda(1, 1, prod_cocina['id'], cantidad=1)
    liberacion_merge = uplink_liberar_buffer_mesa(1)
    print(f"   ℹ️ Resultado liberación posterior: {liberacion_merge}")

    envio_merge = liberacion_merge["envios"][0]
    assert envio_merge["es_merge"] is True, "Debe haber detectado el ticket existente en espera y hacer merge"
    assert envio_merge["envio_id"] == envio_cocina_1["envio_id"], f"Debió reutilizar el envío #{envio_cocina_1['envio_id']}, pero creó #{envio_merge['envio_id']}"
    print(f"   ✅ Test 4 PASÓ: El nuevo platillo se incorporó inteligentemente al ticket #{envio_merge['envio_id']} de la mesa.\n")

    print("🎉 ============================================================")
    print("   ¡TODAS LAS PRUEBAS DEL BLOQUE D PASARON EXITOSAMENTE (100%)!")
    print("============================================================\n")

if __name__ == '__main__':
    run_tests()
