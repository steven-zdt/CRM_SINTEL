# 🗺️ Mapa de Flujo: Módulo Console (SSoT)

Este documento define la secuencia operativa para la gestión administrativa global.

---

## 1. Ciclo de Auditoría de Acciones

```mermaid
 sequenceDiagram
    participant ADM as Staff Admin
    participant UI as Console UI (HTMX)
    participant VIEW as ConsoleView (Mixins)
    participant LOG as ConsoleActionLog
    participant DB as PostgreSQL (Public)

    ADM->>UI: Click "Delete Tenant"
    UI->>VIEW: POST /console/tenants/delete/{id}/
    VIEW->>VIEW: Validar StaffRequiredMixin
    VIEW->>DB: DELETE FROM Client WHERE id={id}
    VIEW->>LOG: Log action(TENANT_DELETE, user, target_id)
    LOG->>DB: INSERT INTO ConsoleActionLog
    VIEW-->>UI: 200 OK (HX-Refresh)
    UI-->>ADM: Tenant Eliminado con Éxito
```

---

## 2. Resolución de Dashboard Administrativo

```mermaid
graph TD
    A[GET /console/] --> B[DashboardView]
    B --> C[StatsProvider.get_summary]
    C --> D[Count Tenants Activos]
    C --> E[Count Usuarios Globales]
    C --> F[Check FailedTasks (DLQ)]
    D & E & F --> G[Render index.html (Bootstrap 5)]
```

---

## 3. Navegación Basada en HTMX (SPA-Lite)

- **Root**: `/console/` sirve el esqueleto de la aplicación.
- **Dynamic Swaps**: Los clics en la barra lateral disparan `hx-get` hacia fragmentos HTML (tenants, usuarios, impuestos).
- **Feedback**: Las operaciones exitosas emiten `HX-Trigger` para actualizar contadores globales en el header.
