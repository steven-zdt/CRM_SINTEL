# CONSOLE_TENANTS_BASELINE — Fase 0

Auditoría de código real (sin modificar nada en esta fase) de todo lo
relacionado a gestión de tenants desde la consola administrativa.

**Fecha:** 2026-08-31

## Modelos (fuente de verdad real)

`apps/public/tenants/models.py`:

| Modelo | Campos relevantes | Notas |
|---|---|---|
| `Client(TenantMixin)` | `nombre`, `paid_until` (`DateField`, nullable, **sin hora/timezone**), `on_trial` (`bool`, default `True`), `is_active` (`bool`, default `True`), `created_on`, `schema_name` (heredado) | `auto_create_schema=True`, `auto_drop_schema=True`. `delete()` tiene candado anti-borrado del schema `public`. |
| `Domain(DomainMixin)` | `tenant` (FK), `is_primary` | Constraint: un solo `is_primary=True` por tenant (`unique_primary_domain_per_tenant`). |
| `TenantMembership` | `client`, `user`, `rol` (ADMIN/STAFF/USER), `is_primary_admin`, `is_active` | `unique_together=(client,user)`. `clean()` impide 2 `is_primary_admin=True` para el mismo tenant. |
| `FailedTenantTask` | DLQ de Celery — `task_id`, `task_name`, `args`, `kwargs`, `exception`, `tenant_schema`, `status`, `retries` | Ya usado por `apps/public/tenants/tasks.py`. |

`apps/public/console/models.py`:

| Modelo | Campos | Notas |
|---|---|---|
| `ConsoleActionLog` | `action` (choices incluye `TENANT_CREATE/UPDATE/DELETE`, `USER_*`), `actor`, `tenant`, `target_user`, `metadata` (JSON), `created_at` | **Confirmado en la misión anterior (E2E-05): ningún código de producción real escribe `TENANT_CREATE` aquí** — el choice existe desde la migración inicial pero nunca se usa para creación de tenant. |

**NO existen** (confirmado por grep exhaustivo, no asumido):
`trial_start`, `trial_end`, `trial_days`, `subscription_status`,
`expires_at`, `lifecycle_status`. La única fecha de expiración
almacenada hoy es `paid_until` (sin hora).

## Estado real del enforcement de `is_active`/`on_trial`/`paid_until`

**`is_active` SÍ tiene enforcement real**, vía
`apps/public/tenants/middleware.py::TenantSecurityMiddleware`
(registrado en `config/settings.py:216`, después de
`TenantMainMiddleware`): si `tenant.is_active == False`, devuelve 403
para cualquier ruta excepto `/login/`, `/logout/`.

**`on_trial` y `paid_until` NO tienen NINGÚN enforcement** — confirmado
por grep exhaustivo en `middleware.py` y `middleware_urlconf.py`: cero
referencias. Son campos guardados en BD, mostrados potencialmente en
UI/API, pero **sin ninguna consecuencia funcional** hoy. Un tenant con
`paid_until` en el pasado sigue recibiendo tráfico normalmente.

**No existe ninguna tarea Celery ni Celery Beat configurado** para
reconciliar esto — `CELERY_BEAT_SCHEDULE` no existe en `settings.py`
(cero tareas periódicas configuradas en todo el proyecto).

Esto confirma exactamente el objetivo central de esta misión: el "trial"
existe como dato, no como control de acceso.

## ViewSets / API existente (`ClientViewSet`, `apps/public/tenants/api/viewsets.py`)

CRUD completo ya implementado (`ModelViewSet`, `IsAdminUser` +
`SessionAuthentication`):

| Acción | Método/URL | Qué hace |
|---|---|---|
| list/retrieve/create/update/partial_update | estándar DRF | `ClientSerializer` |
| `onboard` | `POST .../onboard/` | Crea tenant completo con owner (ver misión E2E anterior) |
| `toggle-active` | `POST .../{id}/toggle-active/` | Activa/desactiva (`is_active`) |
| `resend-invitation` | `POST .../{id}/resend-invitation/` | Reenvía email de activación |
| `manual-activate` | `POST .../{id}/manual-activate/` | Genera URL de activación sin email (mecanismo legacy — **confirmado roto en la misión anterior, E2E-06**: la página `/activate/` real ya no consume ese token) |
| `admin-set-password` | `POST .../{id}/admin-set-password/` | Setea password directamente (soporte de emergencia) |

**No existe** ninguna acción para: extender trial, ver estado de trial
derivado, reactivar con lógica de lifecycle (solo el toggle binario
`is_active`), ni `DELETE` real expuesto vía consola UI (el modelo lo
soporta con candados, pero no hay endpoint/UI que lo dispare).

## Frontend actual

- `apps/public/console/templates/console/pages/tenants/list.html` +
  `apps/public/console/static/js/tenants_manager.js`: listado con
  búsqueda/paginación, botón "Nuevo Tenant", toggle activo/inactivo por
  fila (según lo visto en la sesión E2E anterior).
- `apps/public/console/templates/console/pages/tenants/new.html`:
  formulario de un solo paso (nombre, schema_name opcional, dominio
  opcional, email del propietario, fecha de vencimiento opcional,
  checkbox "período de prueba").
- **`paid_until` y `on_trial` SÍ se capturan en el formulario de
  creación** (confirmado por el grep de Fase 0) — pero como ya
  establecido, sin ningún efecto funcional posterior.

## Reglas de esta misión ya confirmadas contra el código real

- No existe `TenantService`/`TenantLifecycleService`/`TrialService`/
  `DomainService`/`MembershipService` en ningún lado del código —
  **no hay nada que duplicar**; crear `apps/public/tenants/services/lifecycle.py`
  es una adición legítima, no una duplicación.
- El motor de creación (`empresa_service.py`) y el `ClientViewSet` son
  los "owners" reales de identidad/dominio/membresía/lifecycle público
  — se respeta la regla de capa propietaria.
- `apps/public/tenants/tasks.py` ya tiene el patrón establecido
  (`@shared_task(bind=True, ...)` + `_registrar_dlq()` en
  `FailedTenantTask`) — se reutiliza ese patrón para la tarea de
  reconciliación, no se inventa uno nuevo.

## Decisión de diseño para el SSoT del trial (Fase 10-14, resuelto aquí per regla "no crear múltiples fechas")

**SSoT: `paid_until` (ya existente) + `on_trial` (ya existente) +
`is_active` (ya existente, ya enforced).** No se agrega ningún campo
nuevo — no hay migración de datos que hacer.

- `paid_until IS NULL` → sin fecha de expiración definida (tenant sin
  límite de trial explícito — comportamiento actual preservado para no
  romper tenants existentes que ya tienen `paid_until=NULL`).
- `on_trial=True` y `paid_until` en el pasado → trial expirado →
  `is_active` debe reconciliarse a `False`.
- `on_trial=False` → no está en trial (suscripción activa u otro
  régimen) → `paid_until` no bloquea nada (reservado para uso futuro de
  facturación real, fuera de alcance de esta misión — no se inventa un
  sistema de suscripción/facturación que no existe).
- Zona horaria: `paid_until` es un `DateField` sin hora. Política
  elegida (documentada explícitamente, sin ambigüedad, per Fase 14):
  **el trial vence al final del día `paid_until` en
  `settings.TIME_ZONE`**, es decir, expira al llegar
  `paid_until + 1 día, 00:00:00` (equivalente a "el tenant sigue activo
  durante todo el día calendario indicado"). Esto se implementa
  comparando `timezone.now().date() > paid_until` (estrictamente mayor
  al DÍA, no a la medianoche exacta) — evita ambigüedad de hora exacta
  dado que el campo nunca tuvo hora en primer lugar.
- `MANUALLY_SUSPENDED` vs `TRIAL_EXPIRED` (Fase 27): se distinguen
  mediante un campo derivado/lógico, no un campo nuevo en BD — ver
  `docs/console/TENANT_LIFECYCLE.md` para la matriz de estados
  derivados.

Ningún código fue modificado en esta fase — solo lectura.
