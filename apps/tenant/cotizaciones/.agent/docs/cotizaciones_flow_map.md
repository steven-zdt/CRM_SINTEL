# 🗺️ Mapas de Flujo: Módulo Cotizaciones

Este documento visualiza los procesos críticos del módulo de cotizaciones, desde la interacción del usuario hasta la persistencia y exportación.

---

## 🔄 Ciclo de Vida de una Cotización

El siguiente diagrama detalla el flujo de creación de una cotización, destacando la herencia de DNA desde la plantilla.

```mermaid
sequenceDiagram
    participant U as Usuario (Workspace)
    participant F as Frontend (Cotizaciones.editor)
    participant A as API (CotizacionViewSet)
    participant B as Business Service (CotizacionService)
    participant C as CRUD Service (CotizacionCRUDService)
    participant D as Database (PostgreSQL)

    U->>F: Selecciona Plantilla y Cliente
    F->>A: POST /api/v1/cotizaciones/ (payload)
    A->>B: crear_preforma(empresa, datos)
    B->>D: select_for_update (Configuracion)
    D-->>B: Perfil Actual
    B->>B: Heredar DNA (IVA, AIU, Totales)
    B->>B: generar_codigo_unico()
    B->>C: create_instance()
    C->>D: INSERT Cotizacion
    D-->>C: ID / UUID
    C-->>B: Instancia
    B-->>A: Instancia Creada
    A-->>F: 201 Created (JSON)
    F-->>U: Notificación Éxito + Redraw Table
```

---

## 📥 Ingesta de Items y Recálculo de Totales

El recálculo de totales es una operación SSoT que se dispara automáticamente ante cualquier mutación de items.

```mermaid
graph TD
    A[Mutación de Item: Crear/Editar/Borrar] --> B{¿Es exitoso?}
    B -- Sí --> C[Perform Recalculate Hook]
    C --> D[Business Service: calcular_totales]
    D --> E[Obtener todos los items]
    E --> F[Sumar Subtotal Línea]
    F --> G{¿Usa AIU?}
    G -- Sí --> H[Calcular Admin, Imprevistos, Utilidad]
    G -- No --> I[AIU = 0]
    H --> J[Calcular IVA sobre Subtotal + AIU]
    I --> J[Calcular IVA sobre Subtotal]
    J --> K[Total Final = Subtotal + AIU + IVA]
    K --> L[Update Cotizacion.total_con_impuestos]
    L --> M[Retornar Totales Actualizados]
```

---

## 📄 Pipeline de Generación de PDF

Proceso sincrónico de exportación de documentos comerciales.

```mermaid
graph LR
    A[Usuario: Clic PDF] --> B[API: CotizacionPDFViewSet]
    B --> C[Service: get_pdf_content]
    C --> D[Selector: get_detail_with_items]
    D --> E[Template: cotizacion_pdf.html]
    E --> F[xhtml2pdf Engine]
    F --> G[HttpResponse: application/pdf]
    G --> H[Navegador: Visualización/Descarga]
```

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/AUDITORIA_FLUJO_COMPLETO.md)
- [📂 Arquitectura y Microtareas](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/docs/cotizaciones_microtasks_architecture.md)
- [🧠 Lógica de Negocio](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/cotizaciones/docs/cotizaciones_business_logic.md)
