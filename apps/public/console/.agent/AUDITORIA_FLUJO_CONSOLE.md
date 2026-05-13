# [PORTAL] Auditoría y SSoT: Módulo Console (Administración Global)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/public/console/`
**Esquema:** `public`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/console_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/console_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/console_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/console_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-CON). |
| [🗺️ Mapas de Flujo](docs/console_flow_map.md) | Flujos de navegación administrativa, auditoría de acciones y gestión de recursos. |
| [🧠 Lógica de Negocio](docs/console_business_logic.md) | SSoT de permisos de staff, trazabilidad de cambios y seguridad de acceso global. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Console** centraliza la operatividad de la plataforma.

1.  **Gestión de Tenants**: Listado, creación y monitoreo de la salud de los esquemas de los inquilinos.
2.  **Control de Usuarios Globales**: Altas, bajas y gestión de privilegios de acceso al sistema compartido.
3.  **Auditoría Forense (ActionLog)**: Registro detallado de cada acción administrativa ejecutada para trazabilidad y cumplimiento.
4.  **Monitoreo de Infraestructura**: Visualización de estados de migración, tareas Celery pendientes y fallos en el DLQ.
5.  **Administración de Catálogos**: Interfaz para la gestión y actualización del catálogo tributario compartido (Impuestos).

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django (Vistas basadas en clases + Mixins de Staff).
- **Frontend**: HTMX para navegación fluida y reactividad sin recarga de página.
- **UI**: Bootstrap 5 + Tabulator para grillas de datos administrativos.
- **Seguridad**: `StaffRequiredMixin` para bloqueo de acceso no autorizado y `PublicSchemaMixin` para forzar contexto global.
- **Auditoría**: Middleware de captura de acciones en `ConsoleActionLog`.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `ConsoleAuditService`: Única vía para registrar acciones administrativas manuales.
- `StatsProvider`: Generación de métricas globales de la plataforma (Tenants activos, Crecimiento).

### Endpoints Estratégicos
- `GET /console/tenants/`: Vista principal de gestión de inquilinos.
- `GET /api/admin/v1/console/stats/`: Datos para el dashboard administrativo.
- `POST /api/admin/v1/console/action-log/`: Registro de auditoría.

---

## 🚀 Próximos Pasos (MT-CON)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/console_microtasks_architecture.md).

> [!WARNING]
> La consola opera sobre el esquema público y tiene permisos de escritura sobre registros críticos; el uso de `StaffRequiredMixin` es obligatorio en todas sus vistas.

