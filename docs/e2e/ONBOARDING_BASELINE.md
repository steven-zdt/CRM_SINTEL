# ONBOARDING_BASELINE — Fase 0

Mapa del flujo REAL de creación de tenant vía consola administrativa
(Vía A — la que este E2E ejercita), consolidando lo ya verificado en
`documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md` (código real,
no documentación histórica) más lo confirmado adicionalmente hoy.

**Fecha:** 2026-08-31

## Flujo end-to-end (Console)

```
Browser: /console/tenants/new/  (apps/public/console/views.py)
   ↓ (form submit, JS: apps/public/console/static/js/tenants_manager.js:1107)
POST /api/public/v1/tenants/onboard/
   ↓ (ClientViewSet.onboard, apps/public/tenants/api/viewsets.py:77-175)
   [SessionAuthentication + IsAdminUser]
   ↓ OnboardTenantWithOwnerSerializer valida payload
crear_tenant_con_owner()  (apps/services/onboarding/empresa_service.py:208)
   [@transaction.atomic — ver riesgo confirmado en auditoría, Hallazgo #4]
   ├─ 1. User.objects.get_or_create(email=owner_email) — set_unusable_password()
   ├─ 2. validate_schema_name(schema_name)
   ├─ 3. Client(schema_name=...).save() → auto_create_schema=True
   │       → django-tenants: CREATE SCHEMA + migrate_schemas TENANT_APPS
   ├─ 4. Domain.objects.get_or_create(domain=FQDN, is_primary=True)
   ├─ 5. TenantMembership.objects.get_or_create(rol=ADMIN, is_primary_admin=True)
   ├─ 6. schema_context(schema):
   │       Empresa.objects.get_or_create(singleton_key=1)
   │       asegurar_estructura_organizacional_inicial(empresa)
   │       TenantProfile.objects.get_or_create(user, empresa, rol=ADMIN)
   └─ 7. transaction.on_commit(): encola email de activación (token 48h)
                                   + provisión de certificados (Celery)
   ↓
Response 201: {client_id, domain, membership_id, login_url}
```

## Owners por componente (capa propietaria)

| Componente | Modelo/Servicio | App propietaria |
|---|---|---|
| Cliente/Tenant | `Client` (`TenantMixin`) | `apps.public.tenants` |
| Dominio | `Domain` (`DomainMixin`) | `apps.public.tenants` |
| Membresía | `TenantMembership` | `apps.public.tenants` |
| Motor de creación | `crear_tenant_con_owner()`, `onboard_tenant()`, `crear_empresa()` | `apps.services.onboarding.empresa_service` (compartido, NO en `apps.public.tenants` — cross-app intencional, es el Service Layer de onboarding) |
| Usuario global | `User` (`AUTH_USER_MODEL`) | `apps.public.accounts` (público, nunca en schema de tenant) |
| Empresa (dentro del tenant) | `Empresa` | `apps.tenant.empresa` |
| Perfil (dentro del tenant) | `TenantProfile` | `apps.tenant.perfil` |
| Resolución de tenant por hostname | Middleware | `apps.public.tenants.middleware_urlconf` (`TenantSecurityAndURLConfMiddleware`) |
| Auditoría de acciones admin | `ConsoleActionLog` | `apps.public.console` |
| Emails transaccionales | `EmailService` | `apps.public.core.services.email_service` |
| Certificados del tenant | `provision_tenant_certificates_task` | `apps.public.tenants.tasks` (Celery) |

## Tablas involucradas

- `public.tenants_client`, `public.tenants_domain`, `public.tenants_tenantmembership`
- `public.console_consoleactionlog` — **no se confirmó en la auditoría anterior si `ClientViewSet.onboard()` escribe aquí** — a verificar en Fase 16-17 de este E2E (posible gap, no asumir que existe).
- Dentro del schema del tenant: `empresa_empresa`, `perfil_tenantprofile`, más todas las tablas de `TENANT_APPS` (migradas automáticamente).

## Tareas asíncronas (Celery)

- `send_activation_email_task` (email de activación, 48h token) — encolada via `transaction.on_commit()`.
- `provision_tenant_certificates_task` — encolada via `transaction.on_commit()`, siempre (no depende de si el owner es nuevo).
- `FailedTenantTask` — modelo de dead-letter-queue para tareas fallidas (confirmado en auditoría previa, `.agent/AUDITORIA_FLUJO_CORE_PUBLIC.md` §2.2).

## Autenticación posterior al alta

El owner recién creado tiene `set_unusable_password()` — **no puede autenticarse directamente** hasta activar vía el email (token firmado 48h) o vía OTT (Vía B, no aplica aquí). Para este E2E, esto significa: **el login real del owner requiere completar la activación primero** (Fase 23-24 de este documento evalúan si eso bloquea la Fase 11 del plan maestro, o si se resuelve con `manage.py owner_activation_reset_and_token` / activación directa vía servicio).

## DOCUMENTATION_DRIFT ya registrado (no repetir investigación)

Ver `documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md` — Hallazgo #3
(`.agent/AUDITORIA_FLUJO_CORE_PUBLIC.md` describía una función
`crear_tenant_con_owner()` inalcanzable, ya remediado eliminando el código
muerto) y Hallazgo #4 (riesgo de schema huérfano si el seed de paso 6
falla, confirmado con evidencia de `django_tenants/models.py`, tarea
dedicada `task_6ea17ebf` en curso al momento de escribir esto).

## No modificado en esta fase

Confirmado — solo lectura. La creación real del tenant QA ocurre en la
Fase 2 de este mismo documento maestro, vía el endpoint de consola real,
no invocando el modelo directamente.
