#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
LA TERRAZA DE VIDA & SABOR (V&S) - GENERADOR DE QRS INDIVIDUALES POR LUGAR
Genera:
1. Códigos QR PNG de alta resolución por cada silla.
2. Archivos HTML individuales (uno por lugar) para pruebas y ejercicios 1 a 1.
3. Índice visual interactivo en qrs_portavasos/index.html.
============================================================================
"""

import os
import sys
import base64
import io
import qrcode
from PIL import Image

DEFAULT_BASE_URL = "https://impeccable-fruitful-beaver.anvil.app"

# Configuración de las 3 Mesas Palapa (12 Sillas) + 3 Extras Pool
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

def generar_qr_png(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#090d16", back_color="#ffffff")
    return img

def generar_html_individual(item, prev_id, next_id):
    mesa_badge = f"MESA {item['mesa']}" if item['mesa'] > 0 else "POOL EXTRA"
    silla_title = f"Mesa {item['mesa']} · Silla {item['silla']}" if item['mesa'] > 0 else f"Extra #{item['silla']} (Comodín)"
    
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portavasos {item['qr_id']} — {silla_title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      background: #090d16;
      color: #f8fafc;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
    }}
    .nav-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      max-width: 440px;
      margin-bottom: 20px;
      gap: 8px;
    }}
    .nav-btn {{
      background: rgba(30, 41, 59, 0.8);
      color: #cbd5e1;
      text-decoration: none;
      font-size: 13px;
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
    .card {{
      width: 100%;
      max-width: 440px;
      background: #ffffff;
      color: #0f172a;
      border-radius: 28px;
      padding: 28px 24px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
      text-align: center;
      position: relative;
      overflow: hidden;
      border: 3px solid #e2e8f0;
    }}
    .card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 8px;
      background: linear-gradient(90deg, #10b981, #0ea5e9, #f59e0b);
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      text-align: left;
    }}
    .brand-icon {{
      font-size: 28px;
      background: #ecfdf5;
      padding: 6px 8px;
      border-radius: 12px;
      border: 1.5px solid #a7f3d0;
    }}
    .brand-title {{
      font-size: 14px;
      font-weight: 900;
      color: #065f46;
      letter-spacing: 0.5px;
      line-height: 1.1;
    }}
    .brand-sub {{
      font-size: 10px;
      font-weight: 800;
      color: #047857;
      letter-spacing: 1px;
    }}
    .badge {{
      background: #0f172a;
      color: #ffffff;
      font-size: 12px;
      font-weight: 900;
      padding: 6px 14px;
      border-radius: 12px;
      letter-spacing: 0.5px;
    }}
    .qr-box {{
      width: 260px;
      height: 260px;
      margin: 0 auto 20px auto;
      padding: 10px;
      background: #ffffff;
      border: 2px solid #cbd5e1;
      border-radius: 20px;
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .qr-img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
    }}
    .title {{
      font-size: 22px;
      font-weight: 900;
      color: #0f172a;
      margin-bottom: 4px;
    }}
    .subtitle {{
      font-size: 13px;
      font-weight: 800;
      color: #059669;
      font-family: monospace;
      margin-bottom: 8px;
    }}
    .area {{
      font-size: 12px;
      color: #64748b;
      font-weight: 700;
      margin-bottom: 20px;
    }}
    .btn-action {{
      display: block;
      width: 100%;
      padding: 14px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: #ffffff;
      text-decoration: none;
      font-size: 14px;
      font-weight: 900;
      border-radius: 16px;
      box-shadow: 0 8px 20px rgba(16, 185, 129, 0.35);
      transition: all 0.2s;
    }}
    .btn-action:hover {{
      background: linear-gradient(135deg, #059669 0%, #047857 100%);
      transform: translateY(-2px);
    }}
    .url-text {{
      font-size: 10px;
      color: #94a3b8;
      font-family: monospace;
      margin-top: 14px;
      word-break: break-all;
    }}
    @media print {{
      body {{
        background: #ffffff !important;
        padding: 0 !important;
      }}
      .nav-bar, .btn-action {{
        display: none !important;
      }}
      .card {{
        box-shadow: none !important;
        border: 2px solid #000000 !important;
        max-width: 100% !important;
      }}
    }}
  </style>
</head>
<body>

  <div class="nav-bar">
    <a href="{prev_id}.html" class="nav-btn">◀ Anterior</a>
    <a href="index.html" class="nav-btn">📑 Ver Todas</a>
    <a href="{next_id}.html" class="nav-btn">Siguiente ▶</a>
  </div>

  <div class="card">
    <div class="header">
      <div class="brand">
        <span class="brand-icon">🌴</span>
        <div>
          <div class="brand-title">LA TERRAZA</div>
          <div class="brand-sub">VIDA &amp; SABOR</div>
        </div>
      </div>
      <div class="badge">{mesa_badge}</div>
    </div>

    <div class="qr-box">
      <img src="{item['qr_id']}.png" alt="QR {item['qr_id']}" class="qr-img">
    </div>

    <div class="title">{silla_title}</div>
    <div class="subtitle">PORTAVASOS #{item['qr_id']}</div>
    <div class="area">{item['icono']} {item['nombre_area']} · {item['etiqueta']}</div>

    <a href="{item['url']}" target="_blank" class="btn-action">
      🚀 Abrir Menú en Navegador
    </a>

    <div class="url-text">{item['url']}</div>
  </div>

</body>
</html>
"""

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    output_dir = os.path.join(os.path.dirname(__file__), "..", "qrs_portavasos")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🚀 Generando códigos QR individuales por lugar en: {output_dir}")
    print(f"🔗 URL Base configurada: {base_url}\n")

    portavasos_data = []

    for mesa_info in MESAS_CONFIG:
        mesa = mesa_info["mesa"]
        for s in mesa_info["sillas"]:
            silla = s["silla"]
            qr_id = s["qr_id"]
            etiqueta = s["etiqueta"]
            qr_url = build_qr_url(base_url, mesa, silla, qr_id)
            
            img = generar_qr_png(qr_url)
            filename_png = f"{qr_id}.png"
            filepath_png = os.path.join(output_dir, filename_png)
            img.save(filepath_png)

            portavasos_data.append({
                "mesa": mesa,
                "silla": silla,
                "qr_id": qr_id,
                "etiqueta": etiqueta,
                "nombre_area": mesa_info["nombre_area"],
                "icono": mesa_info["icono"],
                "url": qr_url,
                "png": filename_png,
                "html": f"{qr_id}.html"
            })

    # Generar archivos HTML individuales por cada lugar
    total = len(portavasos_data)
    for i, item in enumerate(portavasos_data):
        prev_item = portavasos_data[(i - 1) % total]
        next_item = portavasos_data[(i + 1) % total]
        
        html_content = generar_html_individual(item, prev_item['qr_id'], next_item['qr_id'])
        html_filepath = os.path.join(output_dir, item['html'])
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        mesa_lbl = f"Mesa {item['mesa']}" if item['mesa'] > 0 else "Pool Extra"
        print(f"  📄 Generado: {item['html']} ({mesa_lbl} · Silla {item['silla']})")

    # Generar index.html dentro de qrs_portavasos/
    index_cards = ""
    for item in portavasos_data:
        mesa_badge = f"MESA {item['mesa']}" if item['mesa'] > 0 else "EXTRA"
        silla_lbl = f"Silla {item['silla']}" if item['mesa'] > 0 else f"Extra #{item['silla']}"
        index_cards += f"""
        <a href="{item['html']}" class="grid-card">
          <div class="card-badge">{mesa_badge} · {silla_lbl}</div>
          <img src="{item['png']}" alt="{item['qr_id']}" class="grid-qr">
          <div class="card-code">{item['qr_id']}</div>
          <div class="card-area">{item['icono']} {item['nombre_area']}</div>
        </a>
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
      grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
      gap: 20px;
    }}
    .grid-card {{
      background: #ffffff;
      color: #0f172a;
      border-radius: 20px;
      padding: 20px;
      text-decoration: none;
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
      width: 140px;
      height: 140px;
      object-fit: contain;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      padding: 4px;
      margin-bottom: 10px;
    }}
    .card-code {{
      font-size: 13px;
      font-weight: 900;
      color: #059669;
      font-family: monospace;
    }}
    .card-area {{
      font-size: 11px;
      color: #64748b;
      font-weight: 700;
      margin-top: 2px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div class="title"><span>🌴</span> Portavasos QR Individuales</div>
        <div class="subtitle">Haz clic en cualquier lugar para abrir su portavasos individual de prueba.</div>
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
    print(f"\n📑 Índice generado en: {index_filepath}")
    print(f"🎉 ¡15 portavasos individuales listos para usar 1 a 1!")

if __name__ == "__main__":
    main()
