# [PORTAL] Auditoría y SSoT: Módulo Perfil (Gestión de Usuarios y Roles)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/perfil/`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/perfil_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/perfil_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/perfil_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/perfil_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-PRF). |
| [🗺️ Mapas de Flujo](docs/perfil_flow_map.md) | Ciclo de vida de la invitación, auto-elevación de privilegios y gestión de roles. |
| [🧠 Lógica de Negocio](docs/perfil_business_logic.md) | SSoT de jerarquía de roles, protección de último administrador e integración cross-schema. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Perfil** centraliza el acceso y la identidad dentro del tenant.

1.  **Membresía Tenant**: Vinculación de usuarios globales (`public.User`) con la empresa activa mediante el modelo `TenantProfile`.
2.  **RBAC (Role-Based Access Control)**: Definición y aplicación de roles (`ADMIN`, `OPERADOR`, `VISOR`) que rigen los permisos en todos los ViewSets del tenant.
3.  **Sistema de Invitaciones**: Flujo de creación de usuarios "on-the-fly" para emails no registrados en la plataforma global.
4.  **Auto-Elevación (SSoT Identity)**: Garantía de privilegios administrativos para el propietario legal de la empresa (`owner_email`).
5.  **Seguridad Zero-Trust**: Validación continua de pertenencia al tenant y protección contra degradación accidental de administradores.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django DRF (PerfilViewSet con Dual-Auth JWT/Session).
- **Service Layer**: Estructura modular (`Selectors`, `Business`, `CRUD`).
- **Bridge**: Interacción con el esquema público para validación de membresía primaria.
- **Frontend**: Vanilla JS (Namespace `window.Sintel.Perfil`) con módulos FSD.
- **UI**: Tabulator para gestión de colaboradores y Bootstrap Offcanvas para edición de perfiles.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `PerfilSelector`: Consultas optimizadas con `.only()` de campos de perfil y usuario.
- `PerfilBusinessService`: Orquestador de invitaciones, validación de roles y auto-elevación.
- `PerfilCRUDService`: Persistencia atómica de perfiles y actualización de metadatos.

### Endpoints Estratégicos
- `GET /api/v1/perfil/perfiles/me/`: Resolución del perfil del usuario actual (Fast Path).
- `POST /api/v1/perfil/perfiles/`: Creación de usuario + perfil (Sujeto a rol ADMIN).
- `PATCH /api/v1/perfil/perfiles/{id}/assign-rol/`: Cambio de privilegios con protección de integridad.

---

## 🚀 Próximos Pasos (MT-PRF)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/perfil_microtasks_architecture.md).

> [!CAUTION]
> El sistema no permite que un tenant se quede sin administradores activos. Cualquier intento de degradar al último `ADMIN` resultará en un error de validación de negocio.

