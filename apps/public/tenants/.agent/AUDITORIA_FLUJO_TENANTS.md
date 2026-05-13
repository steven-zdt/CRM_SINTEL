# [PORTAL] Auditoría y SSoT: Módulo Tenants (Provisionamiento y Esquemas)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/public/tenants/`
**Esquema:** `public`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/tenants_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/tenants_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/tenants_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/tenants_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-TNS). |
| [🗺️ Mapas de Flujo](docs/tenants_flow_map.md) | Pipeline de onboarding, migración de esquemas y resolución de dominios. |
| [🧠 Lógica de Negocio](docs/tenants_business_logic.md) | SSoT de nombres de esquema, gestión de membresías y políticas de eliminación masiva. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Tenants** orquesta la infraestructura lógica por inquilino.

1.  **Provisionamiento (Onboarding)**: Flujo atómico de creación de empresa, esquema, dominio y administrador primario.
2.  **Gestión de Esquemas**: Control del ciclo de vida de los esquemas PostgreSQL (`migrate_schemas`) y aislamiento de datos.
3.  **Resolución de Dominios**: Asociación de subdominios o dominios personalizados con inquilinos específicos.
4.  **Membresía Cross-Schema**: Gestión del modelo `TenantMembership` que vincula usuarios globales con acceso a esquemas específicos.
5.  **Observabilidad de Errores (DLQ)**: Registro y reintento de tareas de infraestructura fallidas mediante `FailedTenantTask`.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django-Tenants (Esquema Public).
- **Procesamiento**: Celery para migraciones de esquemas en segundo plano.
- **Service Layer**: `OnboardingService`, `DeletionService`, `InvitationService`.
- **Middleware**: Orquestación de `TenantMiddleware` para resolución de contexto por URL.
- **API**: Endpoints de onboarding idempotentes y gestión administrativa.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `OnboardingService`: Única fuente de verdad para la creación de nuevos tenants.
- `InvitationService`: Gestión de invitaciones OTT (One-Time-Token) para activación de cuentas.
- `TenantDeletionService`: Borrado físico de esquemas y limpieza de metadatos.

### Endpoints Estratégicos
- `POST /api/public/v1/tenants/onboard/`: Creación completa de un nuevo entorno SINTEL.
- `GET /api/public/v1/tenants/`: Inventario global de inquilinos activos.
- `POST /api/public/v1/tenants/{id}/reset-password/`: Orquestación de reset de contraseñas.

---

## 🚀 Próximos Pasos (MT-TNS)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/tenants_microtasks_architecture.md).

> [!CAUTION]
> La eliminación de un tenant destruye físicamente el esquema PostgreSQL correspondiente. Este proceso es irreversible y borra todos los datos del inquilino.

