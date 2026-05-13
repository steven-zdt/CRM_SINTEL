# [PORTAL] Auditoría y SSoT: Módulo Dashboard

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/dashboard/`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/dashboard_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/dashboard_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/dashboard_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/dashboard_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-DSH). |
| [🗺️ Mapas de Flujo](docs/dashboard_flow_map.md) | Diagramas Mermaid del ciclo de vida de hidratación de datos. |
| [🧠 Lógica de Negocio](docs/dashboard_business_logic.md) | SSoT de KPIs, agregación de datos y roles de usuario. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Dashboard** actúa como el centro de mando del inquilino (tenant), consolidando información de múltiples dominios.

1.  **Agregación Multi-Dominio**: Consumo de métricas de Facturas, Clientes, Cotizaciones y Contabilidad.
2.  **Orquestación API-First**: Provisión de un payload único (`DashboardPayload`) para una hidratación reactiva del frontend.
3.  **Seguridad por Rol**: Filtrado dinámico de widgets y acciones rápidas según el perfil operativo del usuario.
4.  **Optimización Zero Waste**: Consultas optimizadas mediante Selectors para minimizar la carga en la base de datos PostgreSQL.
5.  **Aislamiento de Interfaz**: Independencia visual que permite actualizaciones de métricas sin recargar el Shell de la aplicación.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django DRF (APIViews + Selectors).
- **Aislamiento**: Multi-tenant estricto basado en `request.tenant`.
- **Frontend**: Vanilla JS (Namespace `window.Sintel.Dashboard`).
- **UI**: Integración con `core` Shell para visualización de KPIs y gráficas.
- **Comunicación**: Gateway Directo (`/api/v1/dashboard/data/`).

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `DashboardSelector`: Consultas de agregación optimizadas.
- `DashboardBusinessService`: Lógica de roles y ruteo de bienvenida.

### Endpoints Estratégicos
- `GET /api/v1/dashboard/data/`: Endpoint principal de hidratación.
- `GET /api/v1/dashboard/kpis/`: Acceso directo a métricas específicas.

---

## 🚀 Próximos Pasos (MT-DSH)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/dashboard_microtasks_architecture.md).

> [!IMPORTANT]
> El Dashboard no posee modelos propios; cualquier cambio en la estructura de datos de módulos externos (ej. Facturas) debe reflejarse en los Selectors de este módulo.

