# TENANT_LIFECYCLE_MATRIX — Fase 8

Estados REALES (derivados, nunca almacenados como campo nuevo — ver
`apps/public/tenants/services/lifecycle.py::LifecycleStatus`).

| Estado | Condición | Puede acceder | Puede login | Puede administrar | Puede crear datos | Recibe requests | Puede reactivarse | Puede cambiar trial |
|---|---|---|---|---|---|---|---|---|
| `ACTIVE_TRIAL` | `on_trial=True`, `paid_until` vigente o sin definir, `is_active=True` | Sí | Sí | Sí (según rol) | Sí | Sí | N/A (ya activo) | Sí (extender) |
| `ACTIVE_SUBSCRIPTION` | `on_trial=False`, `paid_until` definido y vigente*, `is_active=True` | Sí | Sí | Sí | Sí | Sí | N/A | Reservado (sin sistema de facturación real aún) |
| `NO_EXPIRATION` | `on_trial=False`, `paid_until=NULL`, `is_active=True` | Sí | Sí | Sí | Sí | Sí | N/A | Sí (se le puede asignar un `paid_until` vía `extend-trial`, quedando en `ACTIVE_SUBSCRIPTION`) |
| `EXPIRED` | `on_trial=True`, `paid_until` en el pasado (independiente de `is_active`, la fecha es determinante) | **No** | **No** (403) | **No** | **No** | Bloqueado excepto `/login/`, `/logout/` | Sí — vía `extend-trial` (nueva fecha futura) o `toggle-active` (retira del régimen de trial) | Sí (extender es la única forma de reactivar sin admin manual) |
| `SUSPENDED_BY_ADMIN` | `is_active=False`, sin trial vencido correspondiente | **No** | **No** (403) | **No** | **No** | Bloqueado excepto `/login/`, `/logout/` | Sí — vía `toggle-active` | Sí |

*`ACTIVE_SUBSCRIPTION` no tiene enforcement de expiración por diseño —
`on_trial=False` significa "fuera del régimen de trial", y este sistema
no implementa facturación/suscripción real todavía (per instrucción
explícita del plan: "No inventar facturación/subscription si todavía no
existe"). Si se necesita expiración real fuera de trial en el futuro,
es una extensión separada y deliberada, no algo que esta misión debía
inventar.

## Transiciones válidas

```
ACTIVE_TRIAL
   │
   ├─ (paid_until vence, sin intervención) ──────────► EXPIRED
   ├─ (admin: toggle-active, desactivar) ─────────────► SUSPENDED_BY_ADMIN
   └─ (admin: extend-trial) ──────────────────────────► ACTIVE_TRIAL (nueva fecha)

EXPIRED
   ├─ (admin: extend-trial, fecha futura) ────────────► ACTIVE_TRIAL
   └─ (admin: toggle-active, "reactivar") ─────────────► NO_EXPIRATION (retira de trial, activación administrativa)

SUSPENDED_BY_ADMIN
   ├─ (admin: toggle-active, "reactivar") ─────────────► estado previo a la suspensión (is_active=True, on_trial/paid_until sin tocar)
   └─ (admin: extend-trial) ───────────────────────────► ACTIVE_TRIAL (nueva fecha, is_active=True)
```

**Regla dura (Fase 26, ya implementada):** `reconcile_tenant_lifecycle()`
JAMÁS reactiva — solo desactiva por trial vencido. Toda reactivación es
una acción administrativa explícita y auditada.
