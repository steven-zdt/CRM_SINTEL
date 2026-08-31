# PRODUCTION_RELEASE_GATE — Fase 65

`PRODUCTION_READY = VERIFIED` solo si TODOS los ítems están en `[x]`.
Estado real, corrida 2026-08-31T15:48:37Z (`python manage.py production_readiness`):

```
[ ] Security            -- 1 BLOCKER activo (APP-02, SECRET_KEY insegura)
[x] Tenant isolation    -- verificado en vivo (TEN-01)
[x] Auth                -- login real, bloqueo real, reactivación real, verificados (misión de lifecycle)
[x] Database            -- sin migraciones pendientes (DB-01)
[x] Migrations          -- ídem
[ ] Backups              -- comandos existen (BAK-01=PASS), pero SIN prueba de restauración (BAK-02=BLOCKER)
[ ] Restore              -- BLOCKER (BAK-02)
[~] Nginx               -- configurado en docker-compose (volumen nginx_certs), no verificable sin entorno real expuesto
[ ] TLS                  -- NOT_APPLICABLE_LOCAL_DEV (INFRA-03) -- no hay certificado real que verificar en este entorno
[ ] DNS                  -- NOT_APPLICABLE_LOCAL_DEV, mismo motivo
[x] Health               -- /health responde 200 (OBS-01)
[~] Monitoring           -- sin infraestructura de alertas real (documentado honestamente en INCIDENT_RUNBOOK.md); no bloqueante para un primer release controlado, sí para operación desatendida a escala
[x] Logs                 -- logging estructurado ya existente (DLQ, ConsoleActionLog parcial)
[x] Celery               -- worker operativo; sin beat (no bloqueante, ver INFRA-02)
[x] Redis                -- operativo (cache + broker)
[~] Storage              -- no auditado exhaustivamente en esta pasada (uploads/XML/PDF -- Fase 18/48, fuera del alcance de esta corrida inicial)
[ ] Critical flows        -- no ejecutados contra un ambiente de staging real (no existe); cubiertos parcialmente por evidencia de sesiones previas (onboarding E2E)
[x] Fiscal readiness classified   -- DIAN y DSPNE explícitamente EXTERNAL_DEPENDENCY, no fingidos como listos
[x] DIAN dependency classified    -- ídem
[x] Nomina dependency classified  -- ídem
[x] Rollback              -- procedimiento documentado (ROLLBACK_RUNBOOK.md), no automatizado (apropiado para la escala actual)
[x] Documentation          -- 7 runbooks + baseline + blockers + este gate, todos con evidencia real
[x] Governance             -- manage.py check PASS, makemigrations --check PASS, git diff --check PASS
[~] EKG                    -- tools.ekg existente y usado en sesiones previas; no se ejecutó un impact-check dedicado sobre el nuevo módulo production_readiness en esta pasada (ver nota abajo)
[x] Smoke tests            -- definidos en PRODUCTION_CHECKLIST.md; ejecutados manualmente contra el entorno de desarrollo (health, login, CRUD) en misiones previas de esta sesión
[ ] No critical blockers    -- FALSO: 2 blockers P0 reales activos (APP-02, BAK-02) más APP-01 (esperado en dev, real si se desplegara hoy)
```

## Nota EKG (Fase 53)

El nuevo módulo `apps/public/core/production_readiness/` es
deliberadamente de bajo acoplamiento: `registry.py`/`checks.py` solo
IMPORTAN de otras apps (para inspeccionar su estado — nunca al revés,
ninguna otra app importa de `production_readiness`). No introduce
ciclos por diseño (dependencia unidireccional, patrón ya usado por
`tools.ekg` mismo). No se ejecutó `tools.ekg.impact` formalmente contra
él en esta pasada por presión de tiempo — recomendado como parte del
cierre de los blockers P0 restantes.

## PRODUCTION_READY = **NOT VERIFIED**

2 blockers P0 reales y activos (`APP-02-secret-key`, `BAK-02-restore-tested`)
más 1 esperado-pero-real-si-se-desplegara-hoy (`APP-01-debug`). Ver
`docs/production/PRODUCTION_READINESS_FINAL.md` para el veredicto
completo y las 3 acciones concretas que cierran el gate.
