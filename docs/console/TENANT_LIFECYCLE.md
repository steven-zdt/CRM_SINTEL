# TENANT_LIFECYCLE

Documento índice — el detalle vive en 2 archivos dedicados para no
duplicar contenido:

- **Matriz de estados y transiciones:** `docs/console/TENANT_LIFECYCLE_MATRIX.md`
- **Trial (SSoT, zona horaria, enforcement, reconciliación, extensión, reactivación):** `docs/console/TRIAL_PERIOD.md`

## Resumen de la arquitectura de lifecycle

```
Client.is_active (bool, YA con enforcement real — TenantSecurityMiddleware)
Client.on_trial (bool)
Client.paid_until (date)
        │
        ▼
apps/public/tenants/services/lifecycle.py
        │
        ├─ is_trial_expired(client)          -- pura, sin efectos secundarios
        ├─ compute_lifecycle_status(client)   -- deriva 1 de 5 estados
        ├─ trial_days_remaining(client)       -- para UI
        └─ reconcile_tenant_lifecycle(client) -- ÚNICA función que escribe
                                                  is_active=False (nunca reactiva)
        │
        ├── llamada desde TenantSecurityMiddleware (runtime, cada request)
        └── llamada desde reconcile_tenants_lifecycle_task (Celery, opcional)
```

**Ningún campo nuevo en el modelo. Ninguna migración necesaria** (Fase
46-47 del plan quedan sin trabajo — se reutilizó exactamente lo que ya
existía, per la regla de no duplicación).

**Auditoría:** toda acción administrativa relevante
(`TENANT_CREATE`, `TENANT_UPDATE` vía toggle-active, `EXTEND_TRIAL`)
ahora escribe a `ConsoleActionLog` — cierra el gap E2E-05 documentado en
la misión de auditoría de onboarding anterior (`documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md`).
