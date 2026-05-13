# [PORTAL] Auditoría y SSoT: Módulo Core Public (Infraestructura Compartida)

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/public/core/`
**Esquema:** `public`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/core_public_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/core_public_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/core_public_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/core_public_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-COR-PUB). |
| [🗺️ Mapas de Flujo](docs/core_public_flow_map.md) | Flujos de envío de correo, resolución de contexto y bridge JWT. |
| [🧠 Lógica de Negocio](docs/core_public_business_logic.md) | SSoT de envío de emails, gestión de templates globales y utilidades de infraestructura. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Core Public** orquesta los servicios sin modelo de datos propio pero con impacto global.

1.  **Email Service (SSoT)**: Única fuente de verdad para el envío de comunicaciones transaccionales (Invitaciones, Resets).
2.  **Gestión de Templates Globales**: Almacenamiento y renderizado de correos electrónicos con identidad de marca SINTEL.
3.  **Bridge JWT (Verify)**: Endpoint centralizado para la validación de tokens con registro de auditoría de acceso.
4.  **Redirección de Contexto**: Resolución inteligente de la ruta inicial del usuario basada en su estado de autenticación (Landing vs Console).
5.  **Utilidades de Setup**: Comandos de gestión y configuración inicial del esquema público.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django (Esquema Public).
- **Comunicación**: Django Anymail / SMTP para despacho de correos.
- **Service Layer**: `EmailService` (Patrón Singleton/Stateless).
- **API**: Vistas de verificación de tokens y metadatos públicos.
- **Middleware**: Inyección de contextos auxiliares para peticiones de infraestructura.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `EmailService`: Orquestador de envío de correos con soporte para múltiples backends y tracking.
- `PublicContextResolver`: Lógica de determinación de destino inicial (Home/Login).

### Endpoints Estratégicos
- `GET /api/v1/core/token/verify/`: Validación de JWT con log de auditoría.
- `GET /favicon.ico`: Gestión de activos de marca global.
- `GET /workspace/`: Redirección automática según membresía del usuario.

---

## 🚀 Próximos Pasos (MT-COR-PUB)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/core_public_microtasks_architecture.md).

> [!IMPORTANT]
> `EmailService` es crítico para la seguridad (Password Resets); cualquier modificación debe ser probada rigurosamente para evitar fallos en la entrega de tokens sensibles.

