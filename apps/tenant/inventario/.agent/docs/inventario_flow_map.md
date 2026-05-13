# 🗺️ Mapa de Flujo: Módulo Inventario (SSoT)

Este documento define la secuencia operativa para la gestión de ítems y control de existencias.

---

## 1. Ciclo de Vida: Registro y Movimiento de Producto

```mermaid
sequenceDiagram
    participant UI as Browser (productos_editor.js)
    participant API as ProductoViewSet (/api/v1/inventario/productos/)
    participant SRV as KardexService (services.py)
    participant DB as PostgreSQL

    UI->>API: POST Data (Código, Nombre, Precio)
    API->>SRV: crear_producto(empresa, data)
    SRV->>DB: INSERT Producto (stock_actual=0)
    DB-->>SRV: Success
    API-->>UI: 201 Created
    
    Note over UI, DB: Registro de entrada inicial (Kardex)
    
    UI->>API: POST /movimientos/ (Entrada, Cantidad: 100)
    API->>SRV: registrar_entrada(producto, cantidad)
    SRV->>DB: INSERT MovimientoInventario
    SRV->>SRV: recalcular_stock_producto(id) [select_for_update]
    SRV->>DB: UPDATE Producto SET stock_actual=100
    DB-->>SRV: Success
    API-->>UI: 201 Created (HX-Trigger)
```

---

## 2. Validación de Stock en Salidas

```mermaid
graph TD
    A[POST /movimientos/ SALIDA] --> B{¿DSV: Producto de Empresa?}
    B -- NO --> C[Error 404/403]
    B -- SI --> D{¿stock_actual >= cantidad?}
    D -- NO --> E[Error 422: Stock Insuficiente]
    D -- SI --> F[INSERT MovimientoInventario]
    F --> G[Recalcular stock_actual]
    G --> H[Success 201]
```

---

## 3. Proceso de Carga Masiva (Excel)

```mermaid
graph LR
    EXC[Archivo Excel] --> PAR[DocumentParser]
    PAR --> DTO[Lista de ProductoDTO]
    DTO --> MAT[MaterializarCargaMasiva]
    MAT --> CAT{¿Existe Categoría?}
    CAT -- NO --> CREA[Crear Categoría Auto]
    CAT -- SI --> UPD[Update or Create Producto]
    CREA --> UPD
    UPD --> STK{¿Stock Inicial > 0?}
    STK -- SI --> MOV[Insert Movimiento Inicial]
    MOV --> FIN[Reporte de Carga]
    STK -- NO --> FIN
```

---

## 4. Estructura de Navegación UI (FSD)

- **Inventario Dashboard**: Pestañas para Productos, Servicios, Activos y Movimientos.
- **Grilla Tabulator**: Carga bajo demanda de ítems con alertas visuales de stock bajo.
- **Editores Offcanvas**: Formularios específicos para cada tipo de ítem.
- **Kardex Modal**: Vista cronológica del historial de un producto específico.
