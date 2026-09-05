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

## 5. Semáforo y Ciclo de Vida Operativo (KDS + Alertas Multirrol)

El sistema opera bajo un modelo de estados interactivos y alertas automáticas por SLA:

1. 🟢 **Verde • Recibida / En Cola (Ingreso)**:
   - La orden/comanda ingresa al KDS en cuanto el mesero o comensal la envía.
   - Indica que el pedido está registrado y en espera de ser tomado por el cocinero.
2. 🟡 **Ámbar • En Preparación Activa (Acción de Cocina)**:
   - El cocinero presiona el botón **`Atender / Iniciar`** en la pantalla del KDS para señalar que ya tiene el platillo en fuego/preparación.
   - El estado cambia inmediatamente a **Ámbar**, reflejando trabajo en progreso tanto en cocina como en la comanda del mesero.
3. 🔴 **Rojo • Tiempo Excedido / Retraso Crítico (Alerta Automática > 14 min)**:
   - Si el platillo permanece en preparación y supera el tiempo estimado de salida (ej. 14 minutos) sin ser despachado, el sistema cambia automáticamente a **Rojo**.
   - **Visibilidad Multirrol en Tiempo Real**: Esta alerta roja se sincroniza de forma inmediata y visible para:
     - 🍳 **Cocina (KDS)**: Pulso visual para priorizar y sacar el platillo de inmediato.
     - 🏃 **Mesero (POS/Tablet/Móvil)**: Para estar al tanto del estatus de su mesa e informar al cliente si es necesario.
     - 👑 **Administrador / Gerente**: Monitor de piso para identificar cuellos de botella y apoyar la estación.
4. 🏁 **Listo / Pase (`✅ Listo`)**:
   - Cocina presiona **`Listo`**; la orden pasa a la mesa de pase y notifica al mesero para entrega inmediata a mesa.

---

## 6. Sincronización con el Croquis y POS del Mesero

1. **Mesero envía comanda**: Presiona **`Enviar a Cocina`**.
2. **KDS recibe (🟢 Verde)**: La comanda aparece en verde en la estación correspondiente.
3. **Cocina inicia preparación (🟡 Ámbar)**: El cocinero toca la orden/platillo para marcar **`Iniciar Fuego`**; el mesero ve en su pantalla que ya está en marcha.
4. **Control de SLA (🔴 Alerta Roja si > 14 min)**: Si se excede el tiempo de cocción, la comanda se tiñe de rojo en KDS, monitor administrativo y tablet del mesero.
5. **Salida (✅ Listo)**: Cocina presiona `Listo`, disparando notificación instantánea al mesero para servicio a mesa.
