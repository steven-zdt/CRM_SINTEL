# TRIAL_PERIOD — Período de prueba real y efectivo

**Fecha:** 2026-08-31

## SSoT (Fase 10-11)

Ningún campo nuevo. Se reutilizan los ya existentes en `Client`:

- `on_trial` (bool) — si el tenant está en régimen de prueba.
- `paid_until` (`DateField`, sin hora) — fecha hasta la cual el tenant
  tiene acceso. **Único campo de fecha** — no existen `trial_start`,
  `trial_end`, `expires_at` duplicados.
- `is_active` (bool) — **ya tenía enforcement real** vía
  `TenantSecurityMiddleware` (confirmado en el baseline). El trial se
  integra a este mecanismo YA EXISTENTE, no crea uno paralelo.

## Inicio del trial (Fase 12)

El evento elegido: **creación del tenant** — `on_trial=True` por
`default` del modelo, y `paid_until` se captura en el propio formulario
de creación (ya existía este campo en `new.html`/`tenants_manager.js`
antes de esta misión). No se modificó el punto de inicio — ya era
correcto.

## Cálculo (Fase 13) y zona horaria (Fase 14) — política explícita, sin ambigüedad

- El negocio NO definió un N de días fijo obligatorio en esta misión —
  el admin ingresa `paid_until` directamente al crear, o usa
  `extend-trial` con `days` (que SÍ calcula `paid_until = hoy + N días`)
  o con `paid_until` explícito.
- **Zona horaria:** `settings.TIME_ZONE = America/Bogota` (sin horario
  de verano — GMT-5 fijo, sin ambigüedad de transición). Se usa
  `django.utils.timezone.localdate()` (fecha local, no UTC) para toda
  comparación.
- **Momento exacto de expiración, sin ambigüedad de `>` vs `>=`:** el
  tenant permanece activo durante **todo el día calendario
  `paid_until`**, en zona horaria local. Expira al iniciar el día
  siguiente. Implementación: `timezone.localdate() > client.paid_until`
  (estrictamente mayor). Ejemplo: `paid_until = 2026-09-15` → el tenant
  sigue teniendo acceso durante el 15 de septiembre completo; el 16 de
  septiembre a las 00:00:00 (hora Bogotá) ya está `EXPIRED`.
  **Validado en vivo:** `paid_until=hoy` → acceso permitido;
  `paid_until=ayer` → `403` inmediato.

## Estado visible (Fase 15) y regla de expiración (Fase 16)

Ver `docs/console/TENANT_LIFECYCLE_MATRIX.md` para los 5 estados
derivados y la matriz completa. Regla dura implementada exactamente
como la pide el plan:

```python
# apps/public/tenants/services/lifecycle.py::is_trial_expired
return timezone.localdate() > client.paid_until
```

Nunca se desactiva por eventos de UI ("usuario abrió página") — solo por
esta comparación de fecha, evaluada en cada request real.

## Desactivación real (Fase 17) — no depende de JavaScript ni exclusivamente de Celery

`apps/public/tenants/middleware.py::TenantSecurityMiddleware` llama
`reconcile_tenant_lifecycle(tenant)` **en cada request**, antes de
evaluar `is_active`. Costo: cero queries adicionales en el caso común
(comparación en memoria sobre el objeto `tenant` ya resuelto); un solo
`UPDATE` la primera vez que se detecta la expiración.

**Validado en vivo, sin ejecutar ninguna tarea de Celery (Fase 20,
caso obligatorio del plan):**

```
paid_until = ayer, is_active = True (no reconciliado aún)
POST /api/v1/core/auth/login/ (Host: tenant real)
→ HTTP 403 "El periodo de prueba de este tenant ha vencido..."
→ BD confirma is_active pasó a False automáticamente
```

## Reconciliación (Fase 18) y Celery (Fase 19)

`reconcile_tenant_lifecycle()` es la ÚNICA implementación de la regla —
la llaman tanto el middleware (runtime) como
`apps/public/tenants/tasks.py::reconcile_tenants_lifecycle_task`
(nueva, patrón `@shared_task` + DLQ ya establecido en el archivo).

**Estado honesto:** este proyecto **no tiene `celery beat` corriendo**
en ningún entorno (confirmado: `docker-compose.yaml` define un `worker`,
cero servicio `beat`; `CELERY_BEAT_SCHEDULE` no existe en
`settings.py`). Por eso el diseño NUNCA dependió de Celery para el
enforcement real — la tarea es un complemento opcional (refleja el
estado en el admin para tenants sin tráfico entrante) que puede
invocarse manualmente o activarse el día que exista un scheduler, sin
cambiar ni una línea de la regla de negocio (vive en un solo lugar).

## Extensión (Fase 25) y reactivación (Fase 26) — auditadas

`POST /api/public/v1/tenants/{id}/extend-trial/` — nueva acción:

- Body: `{"days": N}` o `{"paid_until": "YYYY-MM-DD"}`, `"motivo"` opcional.
- Rechaza fechas no futuras (400).
- Reactiva (`is_active=True`) si el tenant estaba `EXPIRED`/`SUSPENDED`.
- **Auditada siempre** en `ConsoleActionLog` (`action=EXTEND_TRIAL`,
  `metadata` con `paid_until_antes/después`, `estado_lifecycle_antes/después`,
  `motivo`, actor y timestamp automáticos del modelo).
- **Validado en vivo:** tenant `EXPIRED` real → `extend-trial(days=14)` →
  200, `lifecycle_status: ACTIVE_TRIAL` → acceso HTTP real restaurado
  (401 por credenciales, ya no 403 por bloqueo) → fila real en
  `ConsoleActionLog` confirmada por consulta SQL directa.

`toggle-active` reactivando un tenant `EXPIRED`: per Fase 26 ("no debe
simplemente `is_active=true` sin resolver el modelo"), esta acción
**retira al tenant del régimen de trial** (`on_trial=False`) en vez de
dejarlo con una fecha vencida que el middleware volvería a desactivar en
el siguiente request — es una "activación administrativa" explícita,
sin inventar facturación. Si se prefiere mantenerlo en trial, usar
`extend-trial`.

## Diferenciación EXPIRED vs SUSPENDED_BY_ADMIN (Fase 27)

Derivada, no un campo nuevo: `EXPIRED` si `on_trial=True` y `paid_until`
vencido (sin importar `is_active`); `SUSPENDED_BY_ADMIN` si
`is_active=False` sin que corresponda a un trial vencido. Ver
`compute_lifecycle_status()`.

## Provisioning y estados ACTIVE falsos (Fase 28-30)

No se auditaron exhaustivamente inconsistencias `Client ACTIVE pero
schema/domain/membership/Empresa inexistente` en esta pasada — el motor
de creación (`crear_tenant_con_owner()`) ya está envuelto en
`@transaction.atomic` (con el riesgo de schema huérfano ya documentado
y delegado a `task_6ea17ebf` en la misión de auditoría de onboarding
anterior — no se duplica ese trabajo aquí). El campo `is_active` se
setea `True` únicamente en la creación exitosa del `Client` en BD; no
hay un estado "PROVISIONING_ERROR" separado porque el fallo de
`create_schema()` ya aborta la creación completa del `Client` (ver
`TenantMixin.save()`, `docs/e2e/ONBOARDING_E2E_REPORT.md`).
