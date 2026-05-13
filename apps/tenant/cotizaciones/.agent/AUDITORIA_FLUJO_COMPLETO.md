# [PORTAL] Auditoría y SSoT: Módulo Cotizaciones

**Versión:** 3.5.0 (Basado en Core v2.62.0)
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/cotizaciones/`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/cotizaciones_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/cotizaciones_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/cotizaciones_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/cotizaciones_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-COT). |
| [🗺️ Mapas de Flujo](docs/cotizaciones_flow_map.md) | Diagramas Mermaid de ciclo de vida, ingesta y pipeline de PDF. |
| [🧠 Lógica de Negocio](docs/cotizaciones_business_logic.md) | SSoT de cálculos, herencia de DNA, snapshot pattern y numeración. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Cotizaciones** es el motor comercial del ERP, encargado de la prospección y formalización de ofertas.

1.  **DNA Dinámico**: Herencia de configuraciones (IVA, Utilidad, AIU) desde plantillas (`ConfiguracionCotizacion`).
2.  **Snapshot Pattern**: Persistencia de datos reales en los items para garantizar integridad histórica (independencia del catálogo).
3.  **Cálculo Centralizado**: Motor SSoT en el Service Layer para gestión de AIU, IVA y Totales.
4.  **Generación Documental**: Pipeline de exportación a PDF profesional vía `xhtml2pdf`.
5.  **Numeración Atómica**: Folios únicos y secuenciales por perfil con bloqueo de base de datos (`select_for_update`).

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django DRF + Service Layer (Business/CRUD/Selectors).
- **Aislamiento**: `SintelTenantBaseModel` (Multi-tenant estricto).
- **Frontend**: Vanilla JS ES6+ (Namespace `window.Sintel.Cotizaciones`).
- **UI**: Tabulator + Bootstrap 5 Offcanvas + HTMX (Server-Driven UI).
- **Comunicación**: Gateway Directo (`/api/v1/cotizaciones/`).

---

## 🏗️ Estructura de Datos y APIs

### Modelos Principales
- `Cotizacion`: Maestro de la oferta comercial.
- `CotizacionItem`: Detalle de productos/servicios con snapshot de costos.
- `ConfiguracionCotizacion`: Plantillas y folios dinámicos.
- `Producto` / `Servicio`: Catálogo de referencia.

### Endpoints Estratégicos
- `GET /api/v1/cotizaciones/`: Listado optimizado con `CotizacionSelector`.
- `POST /api/v1/cotizaciones/`: Creación atómica con herencia de DNA.
- `GET /api/v1/cotizaciones/render-offcanvas/crear/`: UI Shell para creación.
- `POST /api/v1/cotizaciones/{uuid}/recalcular/`: Recálculo forzado de totales.

---

## 🚀 Próximos Pasos (MT-COT)

Las tareas de optimización están documentadas en [Arquitectura de Microtareas](docs/cotizaciones_microtasks_architecture.md).

> [!IMPORTANT]
> Toda modificación debe ser precedida por una revisión de la [Lógica de Negocio](docs/cotizaciones_business_logic.md) para evitar regresiones en los cálculos financieros.

