#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
LA TERRAZA DE VIDA & SABOR (V&S) - GENERADOR DE TARJETAS DE IMAGEN Y QRS
Genera:
1. Tarjetas de imagen completas en formato PNG (alta resolución con diseño,
   logo, mesa, silla, portavasos y código QR incrustado).
2. Códigos QR individuales en PNG.
3. Archivos HTML individuales con QR incrustado en Base64 (100% autónomos).
============================================================================
"""

import os
import sys
import base64
import io
import qrcode
from PIL import Image, ImageDraw, ImageFont

DEFAULT_BASE_URL = "https://impeccable-fruitful-beaver.anvil.app"

MESAS_CONFIG = [
    {
        "mesa": 1,
        "nombre_area": "Palapa Principal",
        "icono": "🌴",
        "sillas": [
            {"silla": 1, "qr_id": "PV-P-01-01", "etiqueta": "Silla 1"},
            {"silla": 2, "qr_id": "PV-P-01-02", "etiqueta": "Silla 2"},
            {"silla": 3, "qr_id": "PV-P-01-03", "etiqueta": "Silla 3"},
            {"silla": 4, "qr_id": "PV-P-01-04", "etiqueta": "Silla 4"},
        ]
    },
    {
        "mesa": 2,
        "nombre_area": "Palapa Central (Familia)",
        "icono": "👨‍👩‍👧‍👦",
        "sillas": [
            {"silla": 1, "qr_id": "PV-P-02-01", "etiqueta": "Silla 1"},
            {"silla": 2, "qr_id": "PV-P-02-02", "etiqueta": "Silla 2"},
            {"silla": 3, "qr_id": "PV-P-02-03", "etiqueta": "Silla 3"},
            {"silla": 4, "qr_id": "PV-P-02-04", "etiqueta": "Silla 4"},
        ]
    },
    {
        "mesa": 3,
        "nombre_area": "Palapa Jardín",
        "icono": "🌿",
        "sillas": [
            {"silla": 1, "qr_id": "PV-P-03-01", "etiqueta": "Silla 1"},
            {"silla": 2, "qr_id": "PV-P-03-02", "etiqueta": "Silla 2"},
            {"silla": 3, "qr_id": "PV-P-03-03", "etiqueta": "Silla 3"},
            {"silla": 4, "qr_id": "PV-P-03-04", "etiqueta": "Silla 4"},
        ]
    },
    {
        "mesa": 0,
        "nombre_area": "Pool Extras / Comodines",
        "icono": "⭐",
        "sillas": [
            {"silla": 1, "qr_id": "PV-P-EX-01", "etiqueta": "Extra 1"},
            {"silla": 2, "qr_id": "PV-P-EX-02", "etiqueta": "Extra 2"},
            {"silla": 3, "qr_id": "PV-P-EX-03", "etiqueta": "Extra 3"},
        ]
    }
]

def build_qr_url(base_url, mesa, silla, qr_id):
    clean_base = base_url.rstrip("/")
    if mesa == 0:
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
    """Genera una imagen PNG completa de alta resolución (800x1000 px) de la tarjeta portavasos."""
    W, H = 800, 1020
    card = Image.new("RGB", (W, H), "#090d16")
    draw = ImageDraw.Draw(card)

    # Intentar cargar fuentes del sistema o usar default
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        font_subtitle = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        font_silla = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
        font_code = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 26)
        font_area = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_inst = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font_title = ImageFont.load_default()
        font_subtitle = font_title
        font_silla = font_title
        font_code = font_title
        font_area = font_title
        font_inst = font_title

    # Fondo de la tarjeta blanca central (con borde)
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

    # Franja superior verde/esmeralda
    draw.rounded_rectangle(
        [margin_x, top_y, margin_x + card_w, top_y + 16],
        radius=0,
        fill="#10b981"
    )

    # Header: Logo y Marca
    header_y = top_y + 40
    # Cuadrado logo V&S
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
    mesa_lbl = f"MESA {item['mesa']}" if item['mesa'] > 0 else "EXTRA POOL"
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

    # Marco del QR
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
    silla_title = f"MESA {item['mesa']} · SILLA {item['silla']}" if item['mesa'] > 0 else f"EXTRA #{item['silla']} (POOL)"
    
    # Silla
    draw.text((W // 2, info_y), silla_title, fill="#0f172a", font=font_title, anchor="mm")
    
    # Código Portavasos
    code_lbl = f"PORTAVASOS #{item['qr_id']}"
    draw.text((W // 2, info_y + 40), code_lbl, fill="#059669", font=font_code, anchor="mm")

    # Área
    area_lbl = f"{item['nombre_area']} · {item['etiqueta']}"
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

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    output_dir = os.path.join(os.path.dirname(__file__), "..", "qrs_portavasos")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🚀 Generando tarjetas de imagen PNG y códigos QR en: {output_dir}")
    print(f"🔗 URL Base: {base_url}\n")

    portavasos_data = []

    for mesa_info in MESAS_CONFIG:
        mesa = mesa_info["mesa"]
        for s in mesa_info["sillas"]:
            silla = s["silla"]
            qr_id = s["qr_id"]
            etiqueta = s["etiqueta"]
            qr_url = build_qr_url(base_url, mesa, silla, qr_id)
            
            # QR individual
            qr_img = generar_qr_pil(qr_url, box_size=12)
            
            # Tarjeta completa como PNG
            card_img = crear_tarjeta_imagen_completa({
                "mesa": mesa,
                "silla": silla,
                "qr_id": qr_id,
                "etiqueta": etiqueta,
                "nombre_area": mesa_info["nombre_area"],
            }, qr_img)

            # Guardar tarjeta completa como imagen PNG principal
            card_filename = f"{qr_id}.png"
            card_filepath = os.path.join(output_dir, card_filename)
            card_img.save(card_filepath, "PNG")

            # Guardar QR puro también
            qr_filename = f"qr_{qr_id}.png"
            qr_filepath = os.path.join(output_dir, qr_filename)
            qr_img.save(qr_filepath, "PNG")

            # Convertir a base64 para el HTML autónomo
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
                "etiqueta": etiqueta,
                "nombre_area": mesa_info["nombre_area"],
                "icono": mesa_info["icono"],
                "url": qr_url,
                "card_png": card_filename,
                "qr_png": qr_filename,
                "card_b64": card_b64,
                "qr_b64": qr_b64,
                "html": f"{qr_id}.html"
            })

            mesa_lbl = f"Mesa {mesa}" if mesa > 0 else "Pool Extra"
            print(f"  🖼️  Imagen generada: {card_filename} ({mesa_lbl} · Silla {silla})")

    # Generar HTMLs individuales 100% autónomos con Base64 incrustado
    total = len(portavasos_data)
    for i, item in enumerate(portavasos_data):
        prev_item = portavasos_data[(i - 1) % total]
        next_item = portavasos_data[(i + 1) % total]
        mesa_badge = f"MESA {item['mesa']}" if item['mesa'] > 0 else "EXTRA"
        silla_title = f"Mesa {item['mesa']} · Silla {item['silla']}" if item['mesa'] > 0 else f"Extra #{item['silla']}"

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
        mesa_badge = f"MESA {item['mesa']}" if item['mesa'] > 0 else "EXTRA"
        silla_lbl = f"Silla {item['silla']}" if item['mesa'] > 0 else f"Extra #{item['silla']}"
        index_cards += f"""
        <div class="grid-card">
          <div class="card-badge">{mesa_badge} · {silla_lbl}</div>
          <a href="{item['html']}">
            <img src="data:image/png;base64,{item['qr_b64']}" alt="{item['qr_id']}" class="grid-qr">
          </a>
          <div class="card-code">{item['qr_id']}</div>
          <div class="card-area">{item['icono']} {item['nombre_area']}</div>
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
        <div class="title"><span>🌴</span> Portavasos QR Individuales</div>
        <div class="subtitle">15 lugares disponibles (Palapa 12 sillas + 3 Pool Extras). Abre cualquier tarjeta para tus ejercicios.</div>
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

    print(f"\n🎉 ¡Proceso finalizado con éxito!")
    print(f"📂 Archivos PNG generados directamente en: {output_dir}")

if __name__ == "__main__":
    main()
