#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de códigos QR v2 para La Terraza de Vida & Sabor.

Consulta la BD (dbterrazavidasabor) las sillas activas y genera 1 PNG por
silla con el QR que apunta a:
  https://<app-url>/#qr=<codigo_qr>

Los códigos siguen el formato v2: PV-P-MM-SS (regulares) y PV-P-EX-NN (pool).
Los PNGs se guardan en qrs_portavasos_v2/ como archivos listos para imprimir
en el portavasos correspondiente.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import qrcode
from PIL import Image, ImageDraw, ImageFont

APP_URL = os.getenv("VS_APP_URL", "https://impeccable-fruitful-beaver.anvil.app")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jreyes@localhost:5432/dbterrazavidasabor")
OUT_DIR = "/Volumes/ORICO ExFAT/terraza-vidasabor-system/qrs_portavasos_v2"

QR_SIZE_PX = 640          # tamaño interno del QR sin margen
CANVAS_W, CANVAS_H = 720, 900
MARGIN_TOP = 40


def _load_fonts():
    """Intenta cargar Inter/Helvetica; cae a default si no está."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return {
                "title":    ImageFont.truetype(path, 42),
                "subtitle": ImageFont.truetype(path, 26),
                "code":     ImageFont.truetype(path, 30),
                "footer":   ImageFont.truetype(path, 18),
            }
    d = ImageFont.load_default()
    return {"title": d, "subtitle": d, "code": d, "footer": d}


def _leer_sillas_activas():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT s.codigo_qr, s.mesa_id, s.numero_en_mesa,
                   s.es_adicional, m.numero_mesa, a.nombre AS area_nombre
            FROM sillas s
            LEFT JOIN mesas m ON s.mesa_id = m.id
            LEFT JOIN areas a ON m.area_id = a.id
            WHERE s.activa = TRUE
            ORDER BY s.es_adicional, m.numero_mesa NULLS LAST, s.numero_en_mesa NULLS LAST;
        """)
        rows = cur.fetchall()
    conn.close()
    return rows


def _componer_qr(codigo_qr, mesa_num, silla_num, es_adicional, area_nombre):
    """Devuelve una imagen PIL 720x900 con el QR + etiqueta legible."""
    url = f"{APP_URL}/#qr={codigo_qr}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10, border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0f172a", back_color="white").convert("RGB")
    qr_img = qr_img.resize((QR_SIZE_PX, QR_SIZE_PX), Image.NEAREST)

    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    draw = ImageDraw.Draw(canvas)
    fonts = _load_fonts()

    # Título
    titulo = "La Terraza de Vida & Sabor"
    subtitulo = (
        f"Mesa {mesa_num} · Silla {silla_num}" if not es_adicional
        else f"Silla Extra #{codigo_qr.split('-')[-1]}"
    )

    _draw_centered(draw, (CANVAS_W // 2, MARGIN_TOP),
                   titulo, fonts["title"], "#0f172a")
    _draw_centered(draw, (CANVAS_W // 2, MARGIN_TOP + 55),
                   subtitulo, fonts["subtitle"], "#059669")

    # QR centrado
    qr_x = (CANVAS_W - QR_SIZE_PX) // 2
    qr_y = MARGIN_TOP + 120
    canvas.paste(qr_img, (qr_x, qr_y))

    # Código legible debajo del QR
    _draw_centered(draw, (CANVAS_W // 2, qr_y + QR_SIZE_PX + 30),
                   codigo_qr, fonts["code"], "#0f172a")

    # Instrucción
    _draw_centered(draw, (CANVAS_W // 2, qr_y + QR_SIZE_PX + 75),
                   "Escanea con tu cámara para ordenar",
                   fonts["footer"], "#64748b")

    # Área (footer discreto)
    if area_nombre:
        _draw_centered(draw, (CANVAS_W // 2, CANVAS_H - 30),
                       f"Área: {area_nombre}",
                       fonts["footer"], "#94a3b8")

    return canvas


def _draw_centered(draw, xy, text, font, fill):
    x, y = xy
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
    except AttributeError:
        w, _ = draw.textsize(text, font=font)
    draw.text((x - w // 2, y), text, font=font, fill=fill)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sillas = _leer_sillas_activas()
    print(f"Generando {len(sillas)} QR PNGs → {OUT_DIR}")
    for s in sillas:
        codigo = s["codigo_qr"]
        mesa_num = s["numero_mesa"] or 0
        silla_num = s["numero_en_mesa"] or 0
        area = s["area_nombre"] or "Palapa"
        img = _componer_qr(
            codigo, mesa_num, silla_num, s["es_adicional"], area
        )
        filename = f"{codigo}.png"
        img.save(os.path.join(OUT_DIR, filename), format="PNG", optimize=True)
        print(f"  ✓ {filename}")
    print("Listo. URL usada:", APP_URL)


if __name__ == "__main__":
    main()
