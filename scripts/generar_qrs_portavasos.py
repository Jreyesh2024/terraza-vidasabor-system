#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
LA TERRAZA DE VIDA & SABOR (V&S) - GENERADOR DE QRS PARA PORTAVASOS
Genera códigos QR de alta resolución (PNG) y un catálogo visual HTML listo
para imprimir y escanear desde teléfonos móviles.
============================================================================
"""

import os
import sys
import base64
import io
import qrcode
from PIL import Image

# URL Base de Anvil oficial
DEFAULT_BASE_URL = "https://impeccable-fruitful-beaver.anvil.app/#menu"

# Configuración de las 3 Mesas y 12 Sillas
MESAS_CONFIG = [
    {
        "mesa": 1,
        "nombre_area": "Terraza Jardín",
        "icono": "🌿",
        "sillas": [
            {"silla": 1, "qr_id": "PV-011", "etiqueta": "Comensal 1"},
            {"silla": 2, "qr_id": "PV-012", "etiqueta": "Comensal 2"},
            {"silla": 3, "qr_id": "PV-013", "etiqueta": "Comensal 3"},
            {"silla": 4, "qr_id": "PV-014", "etiqueta": "Comensal 4"},
        ]
    },
    {
        "mesa": 2,
        "nombre_area": "Terraza Principal (Familia)",
        "icono": "👨‍👩‍👧‍👦",
        "sillas": [
            {"silla": 1, "qr_id": "PV-021", "etiqueta": "Papá / Titular"},
            {"silla": 2, "qr_id": "PV-022", "etiqueta": "Mamá"},
            {"silla": 3, "qr_id": "PV-023", "etiqueta": "Niño 1"},
            {"silla": 4, "qr_id": "PV-024", "etiqueta": "Niño 2"},
        ]
    },
    {
        "mesa": 3,
        "nombre_area": "Palapa Central",
        "icono": "🏖️",
        "sillas": [
            {"silla": 1, "qr_id": "PV-031", "etiqueta": "Comensal 1"},
            {"silla": 2, "qr_id": "PV-032", "etiqueta": "Comensal 2"},
            {"silla": 3, "qr_id": "PV-033", "etiqueta": "Comensal 3"},
            {"silla": 4, "qr_id": "PV-034", "etiqueta": "Comensal 4"},
        ]
    }
]

def build_qr_url(base_url, mesa, silla, qr_id):
    sep = "?" if "?" not in base_url else "&"
    if "#" in base_url:
        return f"{base_url}{sep}mesa={mesa}&silla={silla}&qr={qr_id}"
    else:
        return f"{base_url}#menu?mesa={mesa}&silla={silla}&qr={qr_id}"

def generar_qr_png(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    return img

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    output_dir = os.path.join(os.path.dirname(__file__), "..", "qrs_portavasos")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🚀 Generando códigos QR para La Terraza de Vida & Sabor")
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
            filename = f"qr_mesa_{mesa}_silla_{silla}_{qr_id}.png"
            filepath = os.path.join(output_dir, filename)
            img.save(filepath)

            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            portavasos_data.append({
                "mesa": mesa,
                "silla": silla,
                "qr_id": qr_id,
                "etiqueta": etiqueta,
                "nombre_area": mesa_info["nombre_area"],
                "icono": mesa_info["icono"],
                "url": qr_url,
                "b64": img_b64,
                "filename": filename
            })

            print(f"  ✅ Mesa {mesa} · Silla {silla} ({qr_id}) -> {filename}")

    # Generar archivo HTML interactivo e imprimible
    html_path = os.path.join(os.path.dirname(__file__), "..", "qrs_portavasos_la_terraza.html")
    
    cards_html = ""
    for item in portavasos_data:
        cards_html += f"""
        <div class="pv-card" data-mesa="{item['mesa']}" data-silla="{item['silla']}" data-qr="{item['qr_id']}">
          <div class="pv-header">
            <div class="pv-brand">
              <span class="pv-logo-icon">🌿</span>
              <div>
                <div class="pv-title">LA TERRAZA</div>
                <div class="pv-subtitle">VIDA & SABOR</div>
              </div>
            </div>
            <div class="pv-badge">MESA {item['mesa']}</div>
          </div>
          
          <div class="pv-body">
            <div class="pv-qr-wrapper">
              <img id="img_qr_{item['mesa']}_{item['silla']}" src="data:image/png;base64,{item['b64']}" alt="QR Portavasos {item['qr_id']}" class="pv-qr-img" />
            </div>
            <div class="pv-info">
              <div class="pv-silla">SILLA {item['silla']} <span class="pv-tag">{item['etiqueta']}</span></div>
              <div class="pv-code">PORTAVASOS #{item['qr_id']}</div>
              <div class="pv-area">{item['icono']} {item['nombre_area']}</div>
            </div>
          </div>

          <div class="pv-footer">
            <div class="pv-instruction">
              <i class="fa-solid fa-camera"></i> Escanea con tu celular para abrir Menú Digital y ordenar
            </div>
            <div class="pv-url-preview" id="url_lbl_{item['mesa']}_{item['silla']}">{item['url']}</div>
          </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portavasos QR - La Terraza de Vida & Sabor</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>

  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: #090d16;
      color: #f8fafc;
      padding: 24px;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    .toolbar {{
      background: rgba(30, 41, 59, 0.85);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 20px;
      padding: 20px 24px;
      margin-bottom: 28px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }}
    .toolbar h1 {{
      font-size: 20px;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .toolbar p {{
      font-size: 12px;
      color: #94a3b8;
      margin-top: 4px;
    }}
    .url-config-box {{
      display: flex;
      gap: 8px;
      width: 100%;
      max-width: 600px;
    }}
    .url-config-box input {{
      flex: 1;
      background: #0f172a;
      border: 1px solid #334155;
      color: #38bdf8;
      font-size: 13px;
      font-family: monospace;
      padding: 10px 14px;
      border-radius: 12px;
      outline: none;
    }}
    .url-config-box input:focus {{
      border-color: #10b981;
      box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }}
    .btn {{
      padding: 10px 18px;
      border-radius: 12px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }}
    .btn-primary {{
      background: linear-gradient(135deg, #10b981, #059669);
      color: #ffffff;
    }}
    .btn-primary:hover {{
      background: linear-gradient(135deg, #059669, #047857);
      transform: translateY(-1px);
    }}
    .btn-print {{
      background: #334155;
      color: #f1f5f9;
    }}
    .btn-print:hover {{
      background: #475569;
    }}

    .filter-tabs {{
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
    }}
    .filter-btn {{
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid #334155;
      padding: 8px 16px;
      border-radius: 10px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }}
    .filter-btn.active {{
      background: #10b981;
      color: #fff;
      border-color: #10b981;
    }}

    /* GRID DE PORTAVASOS */
    .pv-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
      gap: 24px;
    }}

    /* TARJETA PORTAVASOS */
    .pv-card {{
      background: #ffffff;
      color: #0f172a;
      border-radius: 20px;
      padding: 18px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border: 2px solid #e2e8f0;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .pv-card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 15px 30px -5px rgba(0, 0, 0, 0.6);
      border-color: #10b981;
    }}
    .pv-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 6px;
      background: linear-gradient(90deg, #10b981, #0284c7, #f59e0b);
    }}

    .pv-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }}
    .pv-brand {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .pv-logo-icon {{
      font-size: 22px;
      background: #ecfdf5;
      padding: 4px 6px;
      border-radius: 8px;
      border: 1px solid #a7f3d0;
    }}
    .pv-title {{
      font-size: 11px;
      font-weight: 900;
      color: #065f46;
      letter-spacing: 0.5px;
    }}
    .pv-subtitle {{
      font-size: 9px;
      font-weight: 700;
      color: #047857;
      letter-spacing: 1px;
    }}
    .pv-badge {{
      background: #0f172a;
      color: #f8fafc;
      font-size: 11px;
      font-weight: 800;
      padding: 4px 10px;
      border-radius: 8px;
      letter-spacing: 0.5px;
    }}

    .pv-body {{
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 14px;
    }}
    .pv-qr-wrapper {{
      width: 110px;
      height: 110px;
      background: #ffffff;
      padding: 4px;
      border-radius: 12px;
      border: 1px solid #cbd5e1;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
    .pv-qr-img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
    }}
    .pv-info {{
      flex: 1;
      min-width: 0;
    }}
    .pv-silla {{
      font-size: 15px;
      font-weight: 900;
      color: #0f172a;
      line-height: 1.2;
    }}
    .pv-tag {{
      display: inline-block;
      font-size: 10px;
      font-weight: 700;
      background: #e0f2fe;
      color: #0369a1;
      padding: 2px 6px;
      border-radius: 4px;
      margin-top: 2px;
    }}
    .pv-code {{
      font-size: 11px;
      font-weight: 800;
      color: #059669;
      margin-top: 6px;
      font-family: monospace;
    }}
    .pv-area {{
      font-size: 10px;
      color: #64748b;
      margin-top: 2px;
      font-weight: 600;
    }}

    .pv-footer {{
      background: #f8fafc;
      border: 1px dashed #cbd5e1;
      border-radius: 10px;
      padding: 8px 10px;
      text-align: center;
    }}
    .pv-instruction {{
      font-size: 9.5px;
      font-weight: 700;
      color: #334155;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
    }}
    .pv-url-preview {{
      font-size: 8px;
      color: #94a3b8;
      font-family: monospace;
      margin-top: 4px;
      word-break: break-all;
      display: none;
    }}

    /* MODO IMPRESIÓN */
    @media print {{
      body {{
        background: #ffffff !important;
        color: #000000 !important;
        padding: 0 !important;
      }}
      .toolbar, .filter-tabs {{
        display: none !important;
      }}
      .pv-grid {{
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 16px !important;
      }}
      .pv-card {{
        box-shadow: none !important;
        border: 1.5px solid #64748b !important;
        page-break-inside: avoid;
        margin-bottom: 12px;
      }}
    }}
  </style>
</head>
<body>

<div class="container">
  <!-- TOOLBAR INTERACTIVA -->
  <div class="toolbar">
    <div>
      <h1><span>☕</span> Portavasos QR - La Terraza de Vida & Sabor</h1>
      <p>Códigos QR físicos para ordenar directo a cada comensal y silla.</p>
    </div>
    
    <div class="url-config-box">
      <input type="text" id="inputBaseUrl" value="{base_url}" placeholder="Ingresa la URL de la App en Anvil" />
      <button class="btn btn-primary" onclick="actualizarTodosQRs()">
        <i class="fa-solid fa-rotate"></i> Actualizar QRs
      </button>
      <button class="btn btn-print" onclick="window.print()">
        <i class="fa-solid fa-print"></i> Imprimir
      </button>
    </div>
  </div>

  <!-- FILTROS POR MESA -->
  <div class="filter-tabs">
    <button class="filter-btn active" onclick="filtrarMesa('all', this)">Todas las Mesas (12 Sillas)</button>
    <button class="filter-btn" onclick="filtrarMesa('1', this)">🌿 Mesa 1 (4)</button>
    <button class="filter-btn" onclick="filtrarMesa('2', this)">👨‍👩‍👧‍👦 Mesa 2 (4)</button>
    <button class="filter-btn" onclick="filtrarMesa('3', this)">🏖️ Mesa 3 (4)</button>
  </div>

  <!-- GRID DE TARJETAS PORTAVASOS -->
  <div class="pv-grid" id="pvGrid">
    {cards_html}
  </div>
</div>

<script>
  function buildUrl(baseUrl, mesa, silla, qrId) {{
    var sep = baseUrl.includes('?') ? '&' : '?';
    if (baseUrl.includes('#')) {{
      return baseUrl + sep + 'mesa=' + mesa + '&silla=' + silla + '&qr=' + qrId;
    }} else {{
      return baseUrl + '#menu?mesa=' + mesa + '&silla=' + silla + '&qr=' + qrId;
    }}
  }}

  function actualizarTodosQRs() {{
    var baseUrl = document.getElementById('inputBaseUrl').value.trim();
    if (!baseUrl) {{
      alert('Por favor ingresa una URL válida de Anvil');
      return;
    }}

    var cards = document.querySelectorAll('.pv-card');
    cards.forEach(function(card) {{
      var mesa = card.getAttribute('data-mesa');
      var silla = card.getAttribute('data-silla');
      var qrId = card.getAttribute('data-qr');
      var newUrl = buildUrl(baseUrl, mesa, silla, qrId);

      var urlLbl = document.getElementById('url_lbl_' + mesa + '_' + silla);
      if (urlLbl) urlLbl.innerText = newUrl;

      // Generar nuevo QR dinámicamente con QRCode.js
      var qrWrapper = card.querySelector('.pv-qr-wrapper');
      qrWrapper.innerHTML = '';
      new QRCode(qrWrapper, {{
        text: newUrl,
        width: 102,
        height: 102,
        colorDark: "#0f172a",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
      }});
    }});
  }}

  function filtrarMesa(mesaNum, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    var cards = document.querySelectorAll('.pv-card');
    cards.forEach(card => {{
      if (mesaNum === 'all' || card.getAttribute('data-mesa') === mesaNum) {{
        card.style.display = 'flex';
      }} else {{
        card.style.display = 'none';
      }}
    }});
  }}
</script>

</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n🎉 ¡Proceso completado exitosamente!")
    print(f"📄 Catálogo HTML interactivo e imprimible: {html_path}")
    print(f"📂 Archivos PNG guardados en: {output_dir}")

if __name__ == "__main__":
    main()
