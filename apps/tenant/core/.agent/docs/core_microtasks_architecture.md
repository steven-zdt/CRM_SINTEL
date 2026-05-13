# CORE — Arquitectura de Microtareas

**Version:** 3.5.0
**App:** `apps/tenant/core/`

---

## 📂 Navegación de Documentación
- [🗺️ Mapa de Flujos y Secuencias](core_flow_map.md)
- [⚖️ Lógica de Negocio y Reglas SSoT](core_business_logic.md)
- [🏠 Portal de Auditoría](../AUDITORIA_FLUJO_CORE.md)

---

## 1. Resumen General

`core` es el **orquestador central** del sistema SINTEL. No contiene lógica de negocio pesada, sino que compone y asegura el entorno de ejecución para todos los demás módulos. Es el responsable de la resolución de tenants, la seguridad transversal, la autenticación y la gestión de la identidad.

## 2. Microtareas: Infraestructura y Resolución (Tenant Lifecycle)

| ID | Tarea | Descripción | Componente |
|---|---|---|---|
| `[MT-COR-101]` | **Normalización de Host** | Eliminar puertos de `HTTP_HOST` para resolución limpia. | `ForceNoPortMiddleware` |
| `[MT-COR-102]` | **Identificación de Tenant** | Resolución de esquema PostgreSQL basada en dominio. | `TenantMainMiddleware` |
| `[MT-COR-103]` | **Selección de URLConf** | Inyección dinámica de `urls_tenant` para dominios privados. | `TenantMainMiddleware` |
| `[MT-COR-104]` | **Bloqueo de Rutas Públicas** | Prevenir acceso a admin/console en subdominios. | `block_public_routes` |
| `[MT-COR-105]` | **Guardia de Membresía** | Validar que el usuario pertenece al tenant actual. | `require_tenant_membership` |

## 3. Microtareas: Seguridad y Autenticación (Dual-Auth)

| ID | Tarea | Descripción | Componente |
|---|---|---|---|
| `[MT-COR-201]` | **Procesamiento Dual-Auth** | Soporte simultáneo JWT + Session Cookies. | `BaseTenantViewSet` |
| `[MT-COR-202]` | **SSoT de Login** | Validación centralizada contra esquema público. | `CoreAuthViewSet` |
| `[MT-COR-203]` | **Inicialización de Perfil** | Asegurar existencia de `TenantProfile` local. | `auth_service.py` |
| `[MT-COR-204]` | **Bridge Session-to-JWT** | Intercambio de sesión activa por token JWT. | `CoreAuthViewSet` |
| `[MT-COR-205]` | **Orquestación de Reset** | Gestión de tokens de recuperación y emails. | `password_reset.py` |

## 4. Microtareas: Orquestación y Facades (Workspace Composer)

| ID | Tarea | Descripción | Componente |
|---|---|---|---|
| `[MT-COR-301]` | **Registro de Enlaces** | SSoT de rutas API/UI para desacoplamiento frontend. | `CoreLinksViewSet` |
| `[MT-COR-302]` | **Composición Dashboard** | Agregación de snapshots de múltiples dominios. | `DashboardSectionsViewSet` |
| `[MT-COR-303]` | **Branding Dinámico** | Resolución de logos y colores por tenant. | `branding.py` |
| `[MT-COR-304]` | **Adapters de Dominio** | Wrappers de servicios externos para la UI Core. | `services/adapters/` |

## 5. Microtareas: Pipeline de Ingesta (Document Router)

| ID | Tarea | Descripción | Componente |
|---|---|---|---|
| `[MT-COR-401]` | **Ingesta Centralizada** | Punto de entrada universal para DTOs externos. | `document_router.py` |
| `[MT-COR-402]` | **Registro de Materializadores** | Sistema de hooks para que las apps procesen DTOs. | `register_materializer` |
| `[MT-COR-403]` | **Normalización de Tipos** | Detección y mapeo de formatos (UBL, JSON, etc). | `document_router.py` |
| `[MT-COR-404]` | **Atomicidad de Ingesta** | Garantía de persistencia íntegra o rollback total. | `materialize_document` |

## 6. Microtareas: Base y Auditoría (Core Models)

| ID | Tarea | Descripción | Componente |
|---|---|---|---|
| `[MT-COR-501]` | **Herencia Obligatoria** | SSoT base para todos los modelos del tenant. | `SintelTenantBaseModel` |
| `[MT-COR-502]` | **Guardia de Empresa** | Validación estricta de `empresa_id` en `save()`. | `core/models.py` |
| `[MT-COR-503]` | **Manejo de Excepciones** | Estandarización de errores API (JSON). | `SintelExceptionMiddleware` |
| `[MT-COR-504]` | **Normalización de Datos** | Conversión transparente QueryDict/JSON. | `coerce_request_data` |

---
**Última actualización:** 2026-05-09
**Status:** In-Sync with SINTEL v3.5.0 DNA
