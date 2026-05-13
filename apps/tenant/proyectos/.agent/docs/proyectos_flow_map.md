# Mapa de Flujo: Módulo Proyectos v3.5.0

Este documento describe cómo fluyen los datos y las acciones en el módulo de **Proyectos**, desde el frontend hasta la persistencia en la base de datos.

## 1. Flujo de Listado (Data Grid)

```mermaid
sequenceDiagram
    participant Browser as Usuario / Tabulator
    participant JS as proyectos.list.js
    participant API as ProyectoViewSet (list)
    participant Selector as ProyectoSelector (qs_list)
    participant DB as PostgreSQL (Tenant Schema)

    Browser->>JS: Carga página / Filtra búsqueda
    JS->>API: GET /api/v1/proyectos/?search=...
    API->>Selector: qs_list(empresa_id, search)
    Selector->>DB: Query SELECT .only(LIST_FIELDS)
    DB-->>Selector: ResultSet (Proyectos)
    Selector-->>API: QuerySet
    API-->>JS: JSON (count, results)
    JS-->>Browser: Render Tabulator Grid
```

## 2. Flujo de Creación / Edición (Offcanvas + DSV)

```mermaid
sequenceDiagram
    participant UI as Offcanvas Form
    participant JS as proyectos_editor.js
    participant API as ProyectoViewSet (create/update)
    participant Service as ProyectoBusinessService
    participant CRUD as ProyectoCRUDService
    participant DB as PostgreSQL (Transaction)

    UI->>JS: Submit Form Data (JSON)
    JS->>API: POST/PATCH /api/v1/proyectos/ (with JWT)
    API->>Service: orchestrate_create_proyecto(empresa, data)
    Note over Service: DSV: Valida cliente_id y responsable_id
    Service->>Service: Genera Código SSoT (si aplica)
    Service->>CRUD: save_proyecto(proyecto)
    CRUD->>DB: INSERT / UPDATE
    Service->>Service: calcular_indicadores_financieros()
    Service-->>API: Instancia Proyecto
    API-->>JS: 201 Created / 200 OK
    JS->>UI: Close Offcanvas & Refresh Table
```

## 3. Flujo de Gestión Financiera (Async/Internal)

```mermaid
graph TD
    A[Cambio en Asignación Personal] --> B(Trigger: ProyectoBusinessService)
    C[Cambio en Pedido de Materiales] --> B
    B --> D{Recalcular Indicadores}
    D --> E[Costo Mano de Obra Real]
    D --> F[Costo Materiales Real]
    E & F --> G[Utilidad Estimada]
    G --> H[Margen de Rentabilidad]
    H --> I[Update Proyecto via CRUDService]
```

## 4. Patrón de Desacoplamiento (Snapshots)

| Acción | Origen (Módulo) | Destino (Proyectos) | Mecanismo |
| :--- | :--- | :--- | :--- |
| Selección de Cliente | Clientes | `cliente_id`, `cliente_nombre` | API Fetch + Snapshot |
| Asignación de Responsable | Empleados | `responsable_id`, `responsable_nombre` | API Fetch + Snapshot |
| Gasto de Materiales | Inventario | `material_ref`, `precio_unitario` | Snapshot en Pedido |
