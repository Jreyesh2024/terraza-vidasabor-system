#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
LA TERRAZA DE VIDA & SABOR (V&S) - GENERADOR DINÁMICO DE QRS DESDE POSTGRESQL
Fuente única de verdad: Base de datos PostgreSQL (`dbterrazavidasabor`).
Lee la tabla `sillas` + `mesas` + `areas` (sillas activas).
Cualquier nueva silla o mesa agregada en la BD se reflejará automáticamente
sin necesidad de modificar código.
============================================================================
"""

import os
import sys
import base64
import io
import qrcode
import psycopg2
from psycopg2.extras import RealDictCursor
from PIL import Image, ImageDraw, ImageFont

DEFAULT_BASE_URL = os.environ.get("ANVIL_BASE_URL", "https://impeccable-fruitful-beaver.anvil.app")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/dbterrazavidasabor")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def obtener_sillas_desde_db():
    """Consulta PostgreSQL para obtener todas las sillas activas con sus mesas y áreas."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    s.id           AS silla_id,
                    s.codigo_qr,
                    s.numero_en_mesa,
                    s.es_adicional,
                    s.activa,
                    m.numero_mesa,
                    COALESCE(a.nombre, 'Palapa') AS area_nombre,
                    COALESCE(a.codigo, 'P')      AS area_codigo
                FROM sillas s
                LEFT JOIN mesas m ON s.mesa_id = m.id
                LEFT JOIN areas a ON m.area_id = a.id
                WHERE s.activa = TRUE
                ORDER BY s.es_adicional ASC, m.numero_mesa ASC NULLS LAST, s.numero_en_mesa ASC NULLS LAST;
            """)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()

def build_qr_url(base_url, mesa, silla, qr_id):
    clean_base = base_url.rstrip("/")
    if not mesa or mesa == 0:
        return f"{clean_base}#qr={qr_id}"
    return f"{clean_base}#mesa={mesa}&silla={silla}&qr={qr_id}"

def generar_qr_pil(url, box_size=12):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#090d16", back_color="#ffffff").convert("RGB")
    return img

def crear_tarjeta_imagen_completa(item, qr_img):
    """Genera una imagen PNG completa de alta resolución (800x1020 px) de la tarjeta portavasos."""
    W, H = 800, 1020
    card = Image.new("RGB", (W, H), "#090d16")
    draw = ImageDraw.Draw(card)

    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        font_subtitle = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        font_code = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 26)
        font_area = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_inst = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font_title = ImageFont.load_default()
        font_subtitle = font_title
        font_code = font_title
        font_area = font_title
        font_inst = font_title

    margin_x = 40
    top_y = 40
    card_w = W - 2 * margin_x
    card_h = H - 2 * top_y

    # Fondo blanco de la tarjeta
    draw.rounded_rectangle(
        [margin_x, top_y, margin_x + card_w, top_y + card_h],
        radius=36,
        fill="#ffffff",
        outline="#10b981",
        width=4
    )

    # Franja superior verde esmeralda
    draw.rounded_rectangle(
        [margin_x, top_y, margin_x + card_w, top_y + 16],
        radius=0,
        fill="#10b981"
    )

    # Header: Logo y Marca
    header_y = top_y + 40
    draw.rounded_rectangle(
        [margin_x + 30, header_y, margin_x + 90, header_y + 60],
        radius=14,
        fill="#10b981"
    )
    draw.text((margin_x + 40, header_y + 15), "V&S", fill="#ffffff", font=font_subtitle)

    # Textos de marca
    draw.text((margin_x + 105, header_y + 5), "LA TERRAZA", fill="#065f46", font=font_subtitle)
    draw.text((margin_x + 105, header_y + 32), "VIDA & SABOR", fill="#047857", font=font_inst)

    # Badge de Mesa
    mesa_val = item.get('numero_mesa')
    mesa_lbl = f"MESA {mesa_val}" if mesa_val else "EXTRA POOL"
    draw.rounded_rectangle(
        [margin_x + card_w - 180, header_y + 8, margin_x + card_w - 30, header_y + 52],
        radius=14,
        fill="#0f172a"
    )
    draw.text((margin_x + card_w - 165, header_y + 18), mesa_lbl, fill="#ffffff", font=font_inst)

    # Línea divisoria
    draw.line([margin_x + 30, header_y + 80, margin_x + card_w - 30, header_y + 80], fill="#e2e8f0", width=2)

    # QR Centrado
    qr_size = 460
    qr_resized = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    qr_x = margin_x + (card_w - qr_size) // 2
    qr_y = header_y + 105

    draw.rounded_rectangle(
        [qr_x - 12, qr_y - 12, qr_x + qr_size + 12, qr_y + qr_size + 12],
        radius=20,
        fill="#ffffff",
        outline="#cbd5e1",
        width=3
    )
    card.paste(qr_resized, (qr_x, qr_y))

    # Textos inferiores
    info_y = qr_y + qr_size + 30
    silla_num = item.get('numero_en_mesa')
    if mesa_val:
        silla_title = f"MESA {mesa_val} · SILLA {silla_num}"
    else:
        extra_num = item['codigo_qr'].split("-")[-1]
        silla_title = f"EXTRA #{extra_num} (POOL)"
    
    draw.text((W // 2, info_y), silla_title, fill="#0f172a", font=font_title, anchor="mm")
    
    code_lbl = f"PORTAVASOS #{item['codigo_qr']}"
    draw.text((W // 2, info_y + 40), code_lbl, fill="#059669", font=font_code, anchor="mm")

    area_lbl = f"Área: {item['area_nombre']}"
    draw.text((W // 2, info_y + 75), area_lbl, fill="#64748b", font=font_area, anchor="mm")

    # Footer con instrucción
    draw.rounded_rectangle(
        [margin_x + 30, info_y + 105, margin_x + card_w - 30, info_y + 155],
        radius=14,
        fill="#f8fafc",
        outline="#cbd5e1",
        width=2
    )
    draw.text((W // 2, info_y + 130), "📷 Escanea con tu celular para abrir el Menú Digital", fill="#334155", font=font_inst, anchor="mm")

    return card

def generar_catalogo_completo(base_url=None, output_dir=None):
    base_url = base_url or DEFAULT_BASE_URL
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "qrs_portavasos")
    os.makedirs(output_dir, exist_ok=True)

    print(f"📡 Conectando a PostgreSQL ({DATABASE_URL}) para leer sillas...")
    sillas_db = obtener_sillas_desde_db()
    print(f"✅ Se encontraron {len(sillas_db)} sillas activas en la base de datos.\n")

    portavasos_data = []

    for s in sillas_db:
        mesa = s.get("numero_mesa")
        silla = s.get("numero_en_mesa")
        qr_id = s["codigo_qr"]
        qr_url = build_qr_url(base_url, mesa, silla, qr_id)
        
        qr_img = generar_qr_pil(qr_url, box_size=12)
        
        card_img = crear_tarjeta_imagen_completa(s, qr_img)

        card_filename = f"{qr_id}.png"
        card_filepath = os.path.join(output_dir, card_filename)
        card_img.save(card_filepath, "PNG")

        qr_filename = f"qr_{qr_id}.png"
        qr_filepath = os.path.join(output_dir, qr_filename)
        qr_img.save(qr_filepath, "PNG")

        buffered = io.BytesIO()
        card_img.save(buffered, format="PNG")
        card_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        buffered_qr = io.BytesIO()
        qr_img.save(buffered_qr, format="PNG")
        qr_b64 = base64.b64encode(buffered_qr.getvalue()).decode("utf-8")

        portavasos_data.append({
            "mesa": mesa,
            "silla": silla,
            "qr_id": qr_id,
            "area_nombre": s["area_nombre"],
            "url": qr_url,
            "card_png": card_filename,
            "qr_png": qr_filename,
            "card_b64": card_b64,
            "qr_b64": qr_b64,
            "html": f"{qr_id}.html"
        })

        mesa_lbl = f"Mesa {mesa} · Silla {silla}" if mesa else f"Pool Extra #{qr_id}"
        print(f"  🖼️  Generado desde BD: {card_filename} ({mesa_lbl})")

    # Generar HTMLs individuales
    total = len(portavasos_data)
    for i, item in enumerate(portavasos_data):
        prev_item = portavasos_data[(i - 1) % total]
        next_item = portavasos_data[(i + 1) % total]
        silla_title = f"Mesa {item['mesa']} · Silla {item['silla']}" if item['mesa'] else f"Extra #{item['qr_id']}"

        html_code = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portavasos {item['qr_id']} — {silla_title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      background: #090d16;
      color: #f8fafc;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px 16px;
    }}
    .nav-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      max-width: 440px;
      margin-bottom: 16px;
      gap: 8px;
    }}
    .nav-btn {{
      background: rgba(30, 41, 59, 0.85);
      color: #cbd5e1;
      text-decoration: none;
      font-size: 12.5px;
      font-weight: 800;
      padding: 8px 14px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all 0.2s;
    }}
    .nav-btn:hover {{
      background: #10b981;
      color: #ffffff;
      border-color: #10b981;
    }}
    .card-wrap {{
      width: 100%;
      max-width: 440px;
      text-align: center;
    }}
    .card-img {{
      width: 100%;
      height: auto;
      border-radius: 28px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);
      display: block;
    }}
    .btn-action {{
      display: block;
      width: 100%;
      padding: 15px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: #ffffff;
      text-decoration: none;
      font-size: 14px;
      font-weight: 900;
      border-radius: 16px;
      box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
      margin-top: 16px;
      transition: all 0.2s;
    }}
    .btn-action:hover {{
      background: linear-gradient(135deg, #059669 0%, #047857 100%);
      transform: translateY(-2px);
    }}
    .url-preview {{
      font-size: 10.5px;
      color: #64748b;
      font-family: monospace;
      margin-top: 12px;
      word-break: break-all;
    }}
  </style>
</head>
<body>
  <div class="nav-bar">
    <a href="{prev_item['qr_id']}.html" class="nav-btn">◀ Anterior</a>
    <a href="index.html" class="nav-btn">📑 Ver Todas</a>
    <a href="{next_item['qr_id']}.html" class="nav-btn">Siguiente ▶</a>
  </div>

  <div class="card-wrap">
    <img src="data:image/png;base64,{item['card_b64']}" alt="Portavasos {item['qr_id']}" class="card-img">
    <a href="{item['url']}" target="_blank" class="btn-action">
      🚀 Abrir Menú Digital de esta Silla
    </a>
    <div class="url-preview">{item['url']}</div>
  </div>
</body>
</html>
"""
        html_filepath = os.path.join(output_dir, item['html'])
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(html_code)

    # Actualizar index.html
    index_cards = ""
    for item in portavasos_data:
        mesa_badge = f"MESA {item['mesa']}" if item['mesa'] else "EXTRA"
        silla_lbl = f"Silla {item['silla']}" if item['mesa'] else f"Extra #{item['qr_id']}"
        index_cards += f"""
        <div class="grid-card">
          <div class="card-badge">{mesa_badge} · {silla_lbl}</div>
          <a href="{item['html']}">
            <img src="data:image/png;base64,{item['qr_b64']}" alt="{item['qr_id']}" class="grid-qr">
          </a>
          <div class="card-code">{item['qr_id']}</div>
          <div class="card-area">{item['area_nombre']}</div>
          <div class="card-actions">
            <a href="{item['html']}" class="btn-sm">Ver Tarjeta</a>
            <a href="{item['card_png']}" download class="btn-sm btn-green">Descargar PNG</a>
          </div>
        </div>
        """

    index_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Índice de Portavasos QR — La Terraza</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      background: #090d16;
      color: #f8fafc;
      padding: 32px 20px;
    }}
    .container {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    .header {{
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 24px;
      padding: 24px 28px;
      margin-bottom: 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .title {{
      font-size: 24px;
      font-weight: 900;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .subtitle {{
      font-size: 13px;
      color: #94a3b8;
      margin-top: 4px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
      gap: 20px;
    }}
    .grid-card {{
      background: #ffffff;
      color: #0f172a;
      border-radius: 24px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
      border: 2px solid #e2e8f0;
      transition: all 0.2s;
    }}
    .grid-card:hover {{
      transform: translateY(-5px);
      border-color: #10b981;
      box-shadow: 0 15px 35px rgba(16, 185, 129, 0.3);
    }}
    .card-badge {{
      background: #0f172a;
      color: #ffffff;
      font-size: 11px;
      font-weight: 900;
      padding: 4px 10px;
      border-radius: 8px;
      margin-bottom: 12px;
    }}
    .grid-qr {{
      width: 150px;
      height: 150px;
      object-fit: contain;
      border: 1px solid #cbd5e1;
      border-radius: 14px;
      padding: 4px;
      margin-bottom: 10px;
      cursor: pointer;
    }}
    .card-code {{
      font-size: 13px;
      font-weight: 900;
      color: #059669;
      font-family: monospace;
    }}
    .card-area {{
      font-size: 11.5px;
      color: #64748b;
      font-weight: 700;
      margin-top: 2px;
      margin-bottom: 12px;
    }}
    .card-actions {{
      display: flex;
      gap: 6px;
      width: 100%;
    }}
    .btn-sm {{
      flex: 1;
      text-decoration: none;
      background: #0f172a;
      color: #ffffff;
      font-size: 11px;
      font-weight: 800;
      padding: 8px 6px;
      border-radius: 10px;
      text-align: center;
      transition: all 0.2s;
    }}
    .btn-green {{
      background: #10b981;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div class="title"><span>🌴</span> Portavasos QR Generados desde PostgreSQL</div>
        <div class="subtitle">Sincronizado con la tabla `sillas`. Total: {len(portavasos_data)} sillas activas.</div>
      </div>
    </div>
    <div class="grid">
      {index_cards}
    </div>
  </div>
</body>
</html>
"""
    index_filepath = os.path.join(output_dir, "index.html")
    with open(index_filepath, "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"\n🎉 ¡Catálogo regenerado con éxito directamente desde la base de datos PostgreSQL!")
    return len(portavasos_data)

if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generar_catalogo_completo(base_url=url_arg)
