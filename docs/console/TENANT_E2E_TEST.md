# TENANT_E2E_TEST — Fase 56

Flujo end-to-end del lifecycle de trial, ejecutado con evidencia real
(curl + verificación directa de BD) contra el tenant QA
`qa_verify_20260831090942` (Client id=10, ya creado y documentado en
`docs/e2e/ONBOARDING_E2E_REPORT.md`).

```
CREATE TENANT           ✅ (ya verificado en la misión E2E anterior)
   ↓
PROVISIONING            ✅ (79 tablas, ya verificado)
   ↓
DOMAIN                  ✅ (qa-verify-20260831090942.sintel.net.co, ya verificado)
   ↓
MEMBERSHIP               ✅ (ADMIN, is_primary_admin=True, ya verificado)
   ↓
EMPRESA / PERFIL          ✅ (ya verificado)
   ↓
LOGIN / ACCESS            ✅ (ya verificado, sesión anterior)
   ↓
TRIAL vigente             ✅ paid_until=hoy → HTTP 401 (credenciales, tenant accesible)
                              paid_until=mañana → HTTP 401 (accesible)
   ↓
EXPIRATION (sin Celery)    ✅ paid_until=ayer, is_active=True (no reconciliado aún)
                              → POST /login/ real → HTTP 403
                              "El periodo de prueba de este tenant ha vencido..."
                              → BD confirma is_active=False (reconciliado por el middleware, no por Celery)
   ↓
BLOCK                     ✅ confirmado — bloqueo real en el primer request, servidor,
                              sin depender de JS ni de tarea programada
   ↓
ADMIN REACTIVATION        ✅ POST /tenants/10/extend-trial/ {"days":14, "motivo":"..."}
                              → 200 {"lifecycle_status":"ACTIVE_TRIAL", "is_active":true}
                              → ConsoleActionLog: fila real, action=EXTEND_TRIAL,
                                metadata con antes/después completo, actor real
   ↓
ACCESS RESTORED           ✅ POST /login/ real → HTTP 401 (credenciales, ya NO 403)
```

**Caso exacto de expiración (Fase 22):** `paid_until=hoy` → NO expirado
(política inclusive, documentada en `TRIAL_PERIOD.md`). `paid_until=ayer`
→ expirado. Corte verificado sin ambigüedad.

**Aislamiento (Fase 51/57):** ya validado exhaustivamente en la misión
E2E anterior (`docs/e2e/ONBOARDING_E2E_REPORT.md`, Fase 19) — sesión de
un tenant usada contra otro devuelve 401 + invalidación forzada de
cookie. No se repite aquí porque el mecanismo de aislamiento (resolución
por schema) es independiente del lifecycle/trial — no hay razón para
que el trial introduzca una fuga cross-tenant, y el enforcement vive en
el mismo middleware ya validado.

## Lo NO cubierto en esta pasada (honesto, per Fase 65)

- Prueba de concurrencia real (dos admins editando el mismo tenant,
  extend-trial doble simultáneo) — Fase 34/35. El diseño es idempotente
  a nivel de resultado final (`extend-trial` con `paid_until` explícito
  produce el mismo estado sin importar cuántas veces se llame), pero no
  se ejecutó un test de concurrencia real multi-hilo (mismo tipo de
  esfuerzo que la prueba de concurrencia de P0-04 en la sesión de
  remediación anterior — no se duplicó ese trabajo de infraestructura de
  test aquí).
- Tarea Celery de reconciliación — creada
  (`reconcile_tenants_lifecycle_task`) pero no ejecutada contra un
  worker real en esta pasada (no hay `celery beat` en este entorno para
  disparerla automáticamente; se puede invocar manualmente si se desea
  verificar, pero el enforcement real NO depende de ella, que es
  exactamente el punto que la Fase 52 exige probar — y se probó, vía el
  middleware).
