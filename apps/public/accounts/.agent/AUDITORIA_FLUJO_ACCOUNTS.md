# [PORTAL] Auditoría y SSoT: Módulo Accounts (Usuarios Globales)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/public/accounts/`
**Esquema:** `public`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/accounts_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/accounts_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/accounts_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/accounts_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-ACC). |
| [🗺️ Mapas de Flujo](docs/accounts_flow_map.md) | Ciclo de vida del usuario global, flujos de eliminación y limpieza cross-schema. |
| [🧠 Lógica de Negocio](docs/accounts_business_logic.md) | SSoT de identidad única, normalización de credenciales y auditoría de borrado. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Accounts** centraliza la identidad en el esquema compartido.

1.  **Identidad Global**: Modelo `User` (AbstractUser) como única fuente de verdad para credenciales y datos básicos.
2.  **Unidireccionalidad**: El usuario global desconoce los tenants. La relación es siempre `TenantProfile` (Tenant) -> `User` (Public).
3.  **Normalización de Credenciales**: Generación de usernames consistentes a partir de correos electrónicos y normalización a minúsculas.
4.  **Limpieza Cross-Schema**: Orquestación de la eliminación de usuarios garantizando el borrado de perfiles vinculados en todos los esquemas de inquilinos.
5.  **Auditoría de Borrado**: Registro persistente en `DeletionAudit` para trazabilidad de usuarios eliminados y cumplimiento de normativas de datos.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django (Esquema Public).
- **Autenticación**: JWT (SimpleJWT) + Session (Bridge).
- **Manejo de Usuarios**: `UserManager` personalizado para gestión de identidades basadas en email.
- **Service Layer**: `DeleteUserService` para operaciones de limpieza transaccional.
- **API**: ViewSets administrativos protegidos para gestión global.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `UserManager`: Gestión de creación y validación de unicidad.
- `DeleteUserService`: Única vía autorizada para eliminar un usuario y sus dependencias cross-schema.

### Endpoints Estratégicos
- `GET /api/admin/v1/accounts/users/`: Listado administrativo global.
- `POST /api/admin/v1/accounts/users/`: Registro administrativo de nuevos colaboradores.
- `DELETE /api/admin/v1/accounts/users/{id}/`: Baja de usuario con orquestación de limpieza.

---

## 🚀 Próximos Pasos (MT-ACC)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/accounts_microtasks_architecture.md).

> [!WARNING]
> Cualquier modificación en el modelo `User` requiere una migración en el esquema público (`python manage.py migrate_schemas --schema=public`).

