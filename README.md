# 🌿 La Terraza de Vida & Sabor (V&S)

Sistema integral de gestión de restaurante, cafetería, menú digital y comandas por mesa para **La Terraza de Vida & Sabor**.

Este proyecto es una aplicación completamente **NUEVA e INDEPENDIENTE** ubicada en la unidad dedicada:
`/Volumes/ORICO ExFAT/terraza-vidasabor-system`

---

## 🎨 Identidad de Marca

* **Nombre Comercial**: La Terraza de Vida & Sabor
* **Siglas / Logotipo**: V&S
* **Estilo Visual**: Dark Glassmorphism con Tailwind CSS, acentos verde esmeralda y ámbar cálido.

---

## 📂 Estructura en Unidad Dedicada ExFAT (`/Volumes/ORICO ExFAT/terraza-vidasabor-system`)

```
/Volumes/ORICO ExFAT/terraza-vidasabor-system/
├── README.md                          # Este documento de referencia
├── .gitignore                         # Control de versiones git sin metadatos macOS
├── .env.example                       # Plantilla de variables de entorno
├── .env                               # Variables de entorno locales
├── database/
│   ├── schema.sql                     # Script DDL inicial PostgreSQL (dbterrazavidasabor)
│   └── seed.sql                       # Datos iniciales de catálogo y áreas V&S
├── anvil/
│   └── forms/
│       └── menu/
│           ├── Menu.html              # Custom HTML Form con Tailwind CSS Dark Mode
│           └── Menu.py                # Lógica del cliente Anvil (JS Bridge)
├── server/
│   └── ServerModule1.py               # Módulo Backend ServerModule (Anvil RPC Callables)
└── uplink/
    ├── terraza_uplink.py              # Script Python Anvil Uplink (Mac Mini / PostgreSQL)
    └── requirements.txt               # Dependencias Python (psycopg2, anvil-uplink, dotenv)
```

---

## 🚀 Inicio Rápido en la Unidad Dedicada

```bash
cd "/Volumes/ORICO ExFAT/terraza-vidasabor-system/uplink"
python3 terraza_uplink.py
```
