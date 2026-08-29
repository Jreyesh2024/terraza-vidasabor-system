# 🌿 La Terraza de Vida & Sabor (V&S)

Sistema integral de gestión de restaurante, cafetería, menú digital y comandas por mesa para **La Terraza de Vida & Sabor**.

Este proyecto es una aplicación completamente **NUEVA e INDEPENDIENTE** desarrollada para **Anvil.works**, **Python** y **PostgreSQL**, adoptando el estándar técnico de Formularios Custom HTML con Tailwind CSS en modo oscuro, llamadas RPC y total aislamiento de datos.

---

## 🎨 Identidad de Marca

* **Nombre Comercial**: La Terraza de Vida & Sabor
* **Siglas / Logotipo**: V&S
* **Estilo Visual**: Dark Glassmorphism con Tailwind CSS, acentos verde esmeralda y ámbar cálido.

---

## 📂 Estructura del Repositorio (`terraza-vidasabor-system`)

```
terraza-vidasabor-system/
├── README.md                          # Este documento de referencia
├── .env.example                       # Plantilla de variables de entorno
├── .env                               # Variables de entorno locales
├── database/
│   ├── schema.sql                     # Script DDL inicial PostgreSQL (DBterrazavidasabor)
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

## 🚀 Pasos para la Configuración Inicial

### 1. Base de Datos en PostgreSQL (pgAdmin)

1. Abre **pgAdmin** o tu cliente PostgreSQL preferido.
2. Crea una nueva base de datos independiente llamada: `DBterrazavidasabor`.
3. Ejecuta el script DDL inicial: [`database/schema.sql`](file:///Volumes/ORICO_APFS/desarrollo/restaurant-pos/terraza-vidasabor-system/database/schema.sql).
4. Ejecuta el script de sembrado de catálogo: [`database/seed.sql`](file:///Volumes/ORICO_APFS/desarrollo/restaurant-pos/terraza-vidasabor-system/database/seed.sql).

### 2. Nuevo Repositorio en GitHub

1. En GitHub, crea un nuevo repositorio público o privado llamado **`terraza-vidasabor-system`** (en blanco, sin README inicial).
2. Inicializa este directorio local como el nuevo repo y haz tu primer commit:

```bash
cd /Volumes/ORICO_APFS/desarrollo/restaurant-pos/terraza-vidasabor-system
git init
git add .
git commit -m "Initial commit: La Terraza de Vida & Sabor (V&S) base setup"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/terraza-vidasabor-system.git
git push -u origin main
```

### 3. Nueva Aplicación en Anvil (anvil.works)

1. Ingresa a tu panel en **Anvil.works**.
2. Haz clic en **New App** > Selecciona **Custom HTML / Blank App**.
3. Vincula el nuevo repositorio de GitHub `terraza-vidasabor-system`.
4. Habilita el servicio **Anvil Uplink** en la configuración de la app de Anvil (*App Settings > Services > Uplink*) para obtener tu `ANVIL_UPLINK_KEY`.
5. Copia tu llave en el archivo `.env`:

```env
ANVIL_UPLINK_KEY=server_TU_LLAVE_DE_ANVIL_AQUI
DATABASE_URL=postgresql://postgres:password@localhost:5432/DBterrazavidasabor
```

### 4. Ejecución del Demonio Anvil Uplink en Mac Mini

```bash
cd /Volumes/ORICO_APFS/desarrollo/restaurant-pos/terraza-vidasabor-system/uplink
pip install -r requirements.txt
python3 terraza_uplink.py
```

---

## 📊 Módulos Operativos Incluidos

1. 🍽️ **Menú Digital & Comandas por Mesa**: Vista de comensales y meseros con modificadores e ítems granulares.
2. 💳 **Cobro Multicanal**: Integración de cobros vía Terminal Santander, Mercado Pago Point y Efectivo.
3. 🍳 **Monitor de Cocina & Barra (KDS)**: Despliegue de ordenes en tiempo real categorizadas por estación.
4. 📈 **Monitor Fiscal & Financiero**: Desglose de ingresos bancarizados vs. efectivo e IVA (16%).
5. 🎁 **Programa de Lealtad (V&S Rewards)**: Registro de clientes frecuentes y acumulación de puntos.
