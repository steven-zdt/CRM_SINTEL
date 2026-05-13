# 🗺️ Mapas de Flujo: Módulo Dashboard

Este documento visualiza los procesos de agregación y entrega de datos del dashboard.

---

## 🔄 Ciclo de Vida de la Petición (API-First)

El dashboard opera bajo un modelo de hidratación reactiva. El frontend solicita el estado completo del negocio mediante un único punto de entrada.

```mermaid
sequenceDiagram
    participant UI as Browser (Core Shell)
    participant JS as dashboard_main.js
    participant API as DashboardDataAPIView
    participant SVC as DashboardBusinessService
    participant SEL as DashboardSelector
    participant DB as PostgreSQL (Tenant Schema)

    UI->>JS: Carga de página Dashboard
    JS->>API: GET /api/v1/dashboard/data/
    API->>API: Autenticación (Session) & Throttle
    API->>SVC: get_dashboard_context(user, tenant)
    SVC->>SEL: Consultar Métricas (Facturas, Clientes, etc.)
    SEL->>DB: SELECT ... (Zero Waste con .only())
    DB-->>SEL: Datos Crudos
    SEL-->>SVC: Objetos de Dominio / Agregados
    SVC-->>API: Diccionario de Contexto Unificado
    API->>API: Serialización (DashboardPayload)
    API-->>JS: 200 OK (JSON)
    JS->>UI: Hidratar Widgets (KPIs, Gráficas, Tablas)
```

---

## 🏗️ Desglose Funcional

### 1. Puente de Autenticación
- La página del dashboard es servida como un asset estático por el módulo `core`.
- Al cargar, utiliza `window.jwtAuth` o `SessionAuthentication` para autorizar las llamadas a la API de datos.

### 2. Enrutamiento por Rol
- `get_dashboard_redirect_url` determina si el usuario debe aterrizar en una vista de Administrador, Staff o Visor.
- El frontend ajusta dinámicamente las "Acciones Rápidas" visibles basadas en el atributo `user_role` del payload.

### 3. Integridad de Datos
- Todas las consultas están estrictamente aisladas por `empresa_id` (Tenant isolation).
- Se proporcionan valores por defecto (0 o vacíos) si los módulos de dominio (ej. `facturas`) aún no contienen datos.

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/AUDITORIA_FLUJO_DASHBOARD.md)
- [📂 Arquitectura y Microtareas](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/docs/dashboard_microtasks_architecture.md)
- [🧠 Lógica de Negocio](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/docs/dashboard_business_logic.md)
