# [PORTAL] Auditoría y SSoT: Módulo Landing (Presentación Estática)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/landing/`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/landing_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/landing_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/landing_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/landing_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-LND). |
| [🗺️ Mapas de Flujo](docs/landing_flow_map.md) | Ciclo de vida de la página de inicio pública y resolución de metadatos de branding. |
| [🧠 Lógica de Negocio](docs/landing_business_logic.md) | SSoT de jerarquía de carga de estilos, gestión de logos y aislamiento de presentación. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Landing** actúa como la fachada pública del inquilino.

1.  **Presentación Corporativa**: Renderizado de la página de inicio pública que muestra la identidad de la empresa.
2.  **SSoT de Branding**: Única fuente de verdad para logos, colores corporativos y metadatos básicos (LandingInfo).
3.  **Aislamiento de Identidad**: Desacoplamiento total de flujos de autenticación y seguridad, delegados a `core`.
4.  **Shell Informativo**: Provisión de información pública sin acceso a datos privados de negocio (Zero-Trust UI).
5.  **Branding Directo**: Consumo de endpoints locales para personalización dinámica según el schema del tenant.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django DRF (LandingViewSet para `/info/`).
- **Service Layer**: `LandingInfoService` para resolución de activos.
- **Frontend**: Vanilla JS estático + CSS Premium.
- **UI**: Templates basados en Partials para modularidad de secciones.
- **Optimización**: Carga mínima de JS para máximo rendimiento SEO.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `LandingInfoService`: Única vía para obtener el payload de branding del tenant.
- `LandingStaticProvider`: (Si aplica) Orquestador de assets de marca.

### Endpoints Estratégicos
- `GET /api/v1/landing/info/`: Punto de entrada para el frontend de la landing page.
- `GET /api/v1/landing/branding/`: Resolución de colores y logos (Consumido por Core para el Header).

---

## 🚀 Próximos Pasos (MT-LND)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/landing_microtasks_architecture.md).

> [!IMPORTANT]
> El aprovisionamiento y onboarding ya no pertenecen a esta app. Cualquier lógica de seguridad debe residir en `apps/tenant/core`.

