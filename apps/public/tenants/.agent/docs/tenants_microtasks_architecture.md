# 🏗️ Arquitectura de Microtareas (MT-TNS): Módulo Tenants

Sistema de trazabilidad técnica para la evolución de la infraestructura multi-inquilino.

---

## 🛠️ Fase 1: Infraestructura y Datos (Data Layer)

- `[ ]` **MT-TNS-001**: Implementar `lookup_field='uuid'` en `ClientViewSet` (si el modelo lo permite).
- `[ ]` **MT-TNS-002**: Refactorizar `FailedTenantTask` para incluir metadatos de contexto de la petición original.
- `[ ]` **MT-TNS-003**: Implementar soporte para dominios personalizados con validación de registros CNAME/A.
- `[ ]` **MT-TNS-004**: Auditoría de integridad de `schema_name` en la creación masiva de tenants.

---

## 🧠 Fase 2: Lógica de Onboarding (Service Layer)

- `[ ]` **MT-TNS-010**: Desarrollar `OnboardingService.validate_availability` (Email y Subdominio) como paso previo atómico.
- `[ ]` **MT-TNS-011**: Implementar el "Self-Healing" en el pipeline de migración de esquemas.
- `[ ]` **MT-TNS-012**: Crear `InvitationService` para centralizar la lógica de expiración de tokens OTT.
- `[ ]` **MT-TNS-013**: Refactorizar `TenantMembership` para soportar roles heredados desde el esquema público.

---

## 🌐 Fase 3: API y Middleware (API Layer)

- `[ ]` **MT-TNS-020**: Optimizar `TenantMiddleware` para reducir latencia en la resolución de esquema mediante caché (Redis).
- `[ ]` **MT-TNS-021**: Implementar Rate Limiting en el endpoint `/onboard/` para prevenir ataques de denegación de servicio.
- `[ ]` **MT-TNS-022**: Documentación OpenAPI detallada para el ciclo de vida del tenant.

---

## 🎨 Fase 4: Consola de Gestión (UI Layer)

- `[ ]` **MT-TNS-030**: Crear panel de monitoreo de esquemas en la Consola Global (Status: Migrating/Ready/Error).
- `[ ]` **MT-TNS-031**: UI para la gestión de dominios adicionales por cliente.
- `[ ]` **MT-TNS-032**: Implementar asistente de migración manual para tenants con versiones de esquema desactualizadas.
