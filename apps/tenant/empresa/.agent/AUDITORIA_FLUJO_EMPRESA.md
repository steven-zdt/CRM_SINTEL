# [PORTAL] Auditoría y SSoT: Módulo Empresa

**Versión:** 3.5.0
**Estado:** ✅ PRODUCTION READY
**Ubicación:** `apps/tenant/empresa/`
**Última Auditoría:** 2026-05-09

---

## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/empresa_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/empresa_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/empresa_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---
 | :--- |
| [📂 Arquitectura y Microtareas](docs/empresa_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas (MT-EMP). |
| [🗺️ Mapas de Flujo](docs/empresa_flow_map.md) | Diagramas Mermaid de provisión, configuración singleton y test de conexión. |
| [🧠 Lógica de Negocio](docs/empresa_business_logic.md) | SSoT de validaciones de NIT, patrón Singleton y encriptación de MailInbox. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---

## 🎯 Responsabilidades Core

El módulo de **Empresa** centraliza la identidad legal y técnica del inquilino.

1.  **Patrón Singleton**: Garantía de un único registro de identidad por tenant mediante constraints de base de datos (`singleton_key`).
2.  **Identidad Legal (NIT)**: Gestión del Número de Identificación Tributaria y Dígito de Verificación (SSoT para Facturación).
3.  **Configuración de Ingesta (MailInbox)**: Gestión de credenciales IMAP/SMTP para la captura automática de documentos (Facturas de Proveedores).
4.  **SSoT de Emisor**: Provisión de datos maestros a módulos dependientes (Facturas, Nómina, Contabilidad) mediante Selectors optimizados.
5.  **Seguridad de Credenciales**: Encriptación asimétrica de contraseñas de correo y validación de conectividad en tiempo real.

---

## 🛠️ Stack Tecnológico (Alineación v3.5.0)

- **Backend**: Django DRF (ViewSets + Service Layer).
- **Aislamiento**: Multi-tenant estricto (Esquemas PostgreSQL).
- **Frontend**: Vanilla JS (Namespace `window.Sintel.Empresa`).
- **UI**: Bootstrap 5 Offcanvas para edición de configuración.
- **Seguridad**: Validación DSV (Double Semantic Verification) en MailInbox.

---

## 🏗️ Estructura de Servicios y APIs

### Servicios Principales
- `EmpresaSelector`: Única vía para obtener datos del emisor (`get_empresa_emisor_data`).
- `EmpresaBusinessService`: Manejo de lógica de creación/actualización con protección contra duplicados.
- `MailboxProvider`: SSoT para el suministro de credenciales de ingesta.

### Endpoints Estratégicos
- `GET /api/v1/empresas/mi-empresa/`: Acceso rápido al perfil del tenant.
- `POST /api/v1/empresas/mail-inbox-config/{id}/test-connection/`: Validación de IMAP.

---

## 🚀 Próximos Pasos (MT-EMP)

Las tareas de evolución técnica se encuentran en [Arquitectura de Microtareas](docs/empresa_microtasks_architecture.md).

> [!IMPORTANT]
> Los cambios en el NIT o Razón Social tienen impacto directo en la validez jurídica de las facturas emitidas; se recomienda auditoría antes de mutaciones masivas.

