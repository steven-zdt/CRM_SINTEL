# 🗺️ Mapas de Flujo: Módulo Empleados

Este documento detalla los procesos secuenciales y la sincronización de datos en el ciclo de vida del empleado.

---

## 🔄 Ciclo de Vida Laboral (Máquina de Estados)

El flujo es estrictamente secuencial para garantizar la integridad de los datos financieros.

```mermaid
graph TD
    A[Empleado: CREAR] -->|Información Personal| B(Empleado: ACTIVO)
    B --> C{¿Tiene Contrato?}
    C -->|No| D[Contrato: CREAR]
    C -->|Sí| E[Contrato: ACTIVO]
    D --> E
    E --> F{¿Registrar Nómina?}
    F -->|Sí| G[Devengo: PREVIEW]
    G -->|Validar Días/Deducciones| H[Devengo: PERSISTIR]
    H --> I[Historial de Nóminas]
    E -->|Terminar Vinculación| J[Contrato: INACTIVO]
    J --> K[Empleado: RETIRADO]
```

---

## 💸 Flujo de Registro de Nómina (API + HTMX)

Proceso de cálculo en tiempo real sin persistencia hasta la confirmación final.

```mermaid
sequenceDiagram
    participant UI as Browser
    participant JS as devengo_editor.js
    participant API as DevengoViewSet
    participant SVC as NominaCalculationService
    participant DB as PostgreSQL

    UI->>JS: Cambia 'días_laborados' o 'otros_devengos'
    JS->>API: POST /preview-calculo/ (HTMX)
    API->>SVC: calcular_liquidacion(contrato, dias, ...)
    SVC-->>API: Resultado (Salario, Salud, Pensión, Neto)
    API-->>UI: Render 'devengo_calculo_partial.html'
    
    UI->>JS: Click "Guardar Nómina"
    JS->>API: POST /api/v1/empleados/devengos/
    API->>API: Validar Solapamiento (Doble Verificación)
    API->>DB: INSERT Devengo (Atomic Transaction)
    DB-->>API: 201 Created
    API-->>JS: was_updated: false
    JS->>UI: Notificar éxito y cerrar Offcanvas
```

---

## 🛡️ Aislamiento Zero Trust en Empleados

Cada petición valida la identidad del tenant antes de cualquier operación.

- **DSV (Double Semantic Verification)**:
    1.  Verificación de `empresa_id` en el objeto principal (Empleado).
    2.  Verificación de `empresa_id` en todas las entidades relacionadas (Contrato, Empresa).

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/AUDITORIA_FLUJO_EMPLEADOS.md)
- [📂 Arquitectura y Microtareas](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/docs/empleados_microtasks_architecture.md)
- [🧠 Lógica de Negocio](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/empleados/docs/empleados_business_logic.md)
