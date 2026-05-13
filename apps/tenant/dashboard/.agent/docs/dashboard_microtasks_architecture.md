# 📂 Arquitectura y Microtareas: Módulo Dashboard

Este documento desglosa el módulo en tareas atómicas (Microtareas) para asegurar trazabilidad y cumplimiento de estándares SINTEL v3.5.0.

---

## 🏗️ Mapa de Microtareas (MT-DSH)

### 🧩 [MT-DSH-INF] Infraestructura y Base
- `[x]` Crear estructura de carpetas `services/` y `docs/`.
- `[x]` Definir Portal de Auditoría SSoT.
- `[ ]` Implementar Selector base `DashboardSelector` con métodos de agregación.

### 🔌 [MT-DSH-API] Capa de Datos (API-First)
- `[x]` Implementar `DashboardDataAPIView` (GET).
- `[ ]` Estandarizar serialización del payload en `DashboardBusinessService`.
- `[ ]` Añadir soporte para filtros de fecha (`startDate`, `endDate`) en el endpoint de datos.

### 🧠 [MT-DSH-BUS] Lógica de Negocio y Servicios
- `[x]` Implementar lógica de redirección por rol (`get_dashboard_redirect_url`).
- `[ ]` Integrar Selectors de `Facturas` y `Contabilidad` para KPIs reales.
- `[ ]` Implementar cacheo de 5-15 min para métricas pesadas (usando `django-redis` si aplica).

### 🎨 [MT-DSH-UI] Interfaz de Usuario y JS
- `[x]` Definir namespace `window.Sintel.Dashboard`.
- `[ ]` Implementar `dashboard.main.js` para orquestación de hidratación.
- `[ ]` Crear componentes de widget reutilizables en `dashboard.ui.js`.

---

## 🏛️ Decisiones Arquitectónicas

1.  **Estado: Sin Modelos**: El módulo no persiste datos. Si requiere persistir preferencias de usuario (ej. orden de widgets), se usarán metadatos en `TenantProfile`.
2.  **Agregación Lazy**: Los KPIs se calculan al vuelo mediante SQL optimizado. Para volúmenes masivos de datos, se migrará a una tabla de materialización (`DashboardStats`).
3.  **Independencia de Interfaz**: Los widgets del dashboard se comunican vía eventos de JS, permitiendo que un widget falle sin afectar al resto de la aplicación.

---

## 🔗 Navegación
- [⬅️ Volver al Portal](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/AUDITORIA_FLUJO_DASHBOARD.md)
- [🗺️ Mapas de Flujo](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/docs/dashboard_flow_map.md)
- [🧠 Lógica de Negocio](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/dashboard/docs/dashboard_business_logic.md)
