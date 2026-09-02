# 🍳 Manual de Arquitectura Operativa: KDS & Producción de Cocina
## La Terraza de Vida & Sabor • Sistema de Alto Rendimiento

---

## 1. Mapeo de Flujo y Enrutamiento por Estaciones

```mermaid
flowchart TD
    POS[📱 POS Mesero / Comensal QR] -->|🚀 Envío de Comanda| KDS[🖥️ KDS Central: Enrutador Inteligente]
    
    KDS -->|Categoría: Bebidas & Cafetería| EST1[☕ Estación 1: Barra de Café & Jugos]
    KDS -->|Categoría: Huevos, Omelettes, Mexicanas, Carnes| EST2[🍳 Estación 2: Cocina Caliente / Desayunos]
    KDS -->|Categoría: Dulces, Waffles, Postres| EST3[🍰 Estación 3: Repostería & Fríos]

    EST1 -->|✅ Bebida Lista (2-4 min)| PASE[🛎️ Mesa de Pase / Expeditor]
    EST2 -->|✅ Platillo Listo (6-12 min)| PASE
    EST3 -->|✅ Postre Listo (5-8 min)| PASE

    PASE -->|🔔 Notificación de Entrega| MESERO[🏃 Servicio a Mesa]
```

---

## 2. Descripción de las 3 Estaciones Operativas

| Estación | Equipamiento Clave | Productos Asignados | Meta de Tiempo (*SLA*) |
| :--- | :--- | :--- | :--- |
| **☕ Estación 1: Barra de Café** | Cafetera espresso, molinos, licuadoras, extractor de jugos | Espresso, Capuchino, Americano, Jugo Verde, Naranjada, Refrescos | **2 a 4 minutos** |
| **🍳 Estación 2: Cocina Caliente** | Estufa de 4-6 quemadores, plancha de cromo duro, sartenes | Chilaquiles, Omelettes, Huevos Rancheros, Cortes, Enchiladas | **6 a 12 minutos** |
| **🍰 Estación 3: Repostería & Fríos** | Wafflera, crepera, salamandra, mesa refrigerada | Waffles Belgas, Crepas Dulces, Fruta de Temporada, Pasteles | **5 a 8 minutos** |
| **👑 Expeditor (Pase Central)** | Mesa de pase con lámpara térmica, monitor maestro | Supervisión integral de la orden por mesa | Sincronización y salida simultánea |

---

## 3. Matriz de Cocción por Lotes (*Batch Cooking*)

Cuando una mesa o varias mesas solicitan platillos idénticos al mismo tiempo:
* **Cocción Individual vs. Cocción por Lote**:
  - Preparar 4 órdenes de chilaquiles una por una toma $4 \times 6\text{ min} = 24\text{ min}$ y satura 4 sartenes.
  - El sistema activa el **Consolidado de Fuego**: el cocinero usa un sartén hondo o cacerola para calentar salsa para 4 porciones en **7 minutos totales**.

---

## 4. Estandarización de Fichas Técnicas (Gramajes Exactos)

### Ejemplo 1: Chilaquiles Verdes con Pollo (Especialidad de la Casa)
* **Totopo horneado**: 120 g (bolsa precortada y pesada).
* **Salsa verde tatemada**: 150 ml (1 cucharón medidor rojo estándar).
* **Pechuga de pollo deshebrada**: 80 g (bolsita dosificada).
* **Queso fresco de rancho**: 30 g (1 cucharada medidora).
* **Crema de rancho**: 20 ml (biberón dosificador).
* **Cebolla morada encurtida**: 15 g.
* **Tiempo objetivo**: 6 minutos.

### Ejemplo 2: Omelette Especial Vida & Sabor
* **Huevo líquido pasteurizado / fresco batido**: 3 piezas (150 ml).
* **Queso Gouda rallado**: 40 g.
* **Champiñón salteado**: 30 g.
* **Espinaca baby**: 20 g.
* **Guarnición (Frijol refrito)**: 80 g.
* **Tiempo objetivo**: 5 minutos.

---

## 5. Semáforo de Control de Tiempos en Pantalla KDS

* 🟢 **Verde (0 a 8 min)**: Tiempo normal y controlado.
* 🟡 **Ámbar (9 a 14 min)**: Tiempo en desarrollo; el cocinero debe tener el plato en fuego activo.
* 🔴 **Rojo (≥ 15 min)**: Retraso crítico; el KDS emite pulso visual para priorizar la mesa.

---

## 6. Sincronización con el Croquis y POS del Mesero

1. El mesero presiona **`Enviar a Cocina`** en su comanda.
2. El ítem cambia de `🟡 Pendiente` a `🔥 En Cocina (09:05 AM)` y queda bloqueado contra borrado involuntario.
3. El KDS recibe la orden en su estación correspondiente.
4. Al salir del fuego, cocina presiona `✅ Listo`.
5. El mesero recibe aviso inmediato en su dispositivo para recoger la comanda y llevarla a la mesa.
