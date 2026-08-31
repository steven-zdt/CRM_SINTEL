# PRODUCTION_READINESS_FINAL — Fase 67

**Versión evaluada:** rama `feat/onboarding-cookie`, commit base `8377edc`
(este módulo se commitea sobre ese estado).
**Fecha de la corrida inicial:** 2026-08-31T15:48:37Z. **Actualizada**
tras cerrar `BAK-02` (drill de restore real) y agregar `BAK-04`
(check de version pg_dump/pg_restore), corrida dentro del contenedor
`web` el mismo día.
**Herramienta:** `python manage.py production_readiness` (nueva,
implementada en esta misión — `apps/public/core/production_readiness/`)

## Estado (Fase 66 — nunca "certificado")

## **NOT_READY**

No `READY`, no `READY_WITH_EXTERNAL_DEPENDENCIES` — hay blockers `P0`
reales que no son dependencias externas y que sí están al alcance de
corregirse (a diferencia de DIAN/DSPNE, que sí son
`EXTERNAL_DEPENDENCY` correctamente clasificados y no cuentan como la
razón del `NOT_READY`).

## Los 2 blockers reales restantes (ambos triviales, config de entorno)

1. **`APP-02-secret-key` (trivial — minutos):** generar
   `DJANGO_SECRET_KEY` real y definirla en el `.env` del entorno de
   destino. No requiere cambio de código — el código ya lee
   correctamente de la variable de entorno
   (`config/settings.py:17`); falta que el entorno de destino la
   provea.
2. **`APP-01-debug` (trivial — minutos):** `DEBUG=False` en el `.env`
   del entorno de destino. Mismo patrón — no es un bug de código, es
   configuración de despliegue pendiente.

## `BAK-02-restore-tested` — CERRADO (2026-08-31)

Drill end-to-end ejecutado y verificado (backup real → dato corrompido
deliberadamente → restore → verificación de datos e integridad, RTO
medido). Ver `docs/production/BACKUP_RESTORE_RUNBOOK.md` para la
evidencia completa.

**Hallazgo real encontrado y corregido durante el drill:** el cliente
`pg_restore` de la imagen `web` (v17, Debian trixie sin versión fijada)
era incompatible con el servidor `postgres:16-alpine` — cualquier
restauración real habría fallado con
`unrecognized configuration parameter "transaction_timeout"`. Corregido
fijando `postgresql-client-16` en el `Dockerfile` (repo oficial PGDG).
Se agregó `BAK-04-pg-client-server-version-match` al Production Check
Registry para detectar esta clase de regresión automáticamente en el
futuro, sin depender de que alguien vuelva a correr el drill manual.

## Dependencias externas (correctamente BLOCKED, no fingidas)

- Transmisión real DIAN (`docs/remediation/REM-EXT-01.md`).
- Transmisión real DSPNE (`docs/remediation/REM-EXT-02.md`).

Ninguna de las dos bloquea un primer despliegue de SINTEL como ERP
interno/operativo (facturación/contabilidad/inventario funcionan sin
transmisión electrónica real) — SÍ bloquean declarar "facturación
electrónica production-ready ante la DIAN", que es una afirmación
distinta y más específica.

## Checks ejecutados — resumen

20 checks reales, 9 categorías (`APPLICATION`, `SECURITY`, `DATABASE`,
`TENANT`, `INFRA`, `BACKUP`, `OBSERVABILITY`, `DOCUMENTATION`,
`FISCAL`). Detalle completo, reproducible en cualquier momento futuro
(Fase 70 — proceso recurrente, no auditoría de una sola vez):

```bash
python manage.py production_readiness
python manage.py production_readiness --json reporte.json  # para CI/histórico
```

Ver `docs/production/PRODUCTION_BLOCKERS.md` para la tabla completa
por severidad, y `docs/production/PRODUCTION_RELEASE_GATE.md` para el
checklist ítem-por-ítem contra las 24 áreas del gate final del plan.

## Lo que SÍ está confirmado y verificado en vivo (no solo por código)

- **Aislamiento cross-tenant** — sesión de un tenant rechazada
  explícitamente contra otro, con invalidación forzada de cookie.
- **Escalación de privilegios crítica encontrada y corregida** —
  owners de tenant ya no reciben `is_staff=True` global (regresión
  cubierta por check automatizado `TEN-02`).
- **Período de prueba con bloqueo real** — verificado sin depender de
  Celery (que ni siquiera tiene scheduler configurado en ningún
  entorno).
- **Sin secretos hardcodeados** en código fuente (`apps`/`config`).
- **Sin migraciones pendientes** de generar.
- **`/health` operativo.**
- **Mock de transporte DIAN deshabilitado por defecto**, no activable
  por el cliente.
- **Restauración real de backup** — drill completo ejecutado (backup →
  dato corrompido → restore → verificación), incluyendo un hallazgo real
  de incompatibilidad de versión cliente/servidor encontrado y corregido
  en el proceso (ver `BACKUP_RESTORE_RUNBOOK.md`).

## Lo que NO se verificó en esta pasada (honesto, no inferido)

- TLS/DNS reales — no existe ambiente expuesto para verificar.
- Carga/concurrencia real (Fase 27, 34-35).
- Flujos críticos de negocio contra un ambiente de staging real (no
  existe staging desplegado — sí hay evidencia extensa contra el
  entorno de desarrollo, documentada en `docs/e2e/` y `docs/console/`).
- Clasificación exhaustiva de las 65 ocurrencias de `localhost`/`127.0.0.1`
  detectadas (Fase 44 — marcado como P2, no bloqueante, pendiente de
  revisión dedicada).
- Auditoría exhaustiva de uploads/storage (Fase 18/48) y privacidad de
  datos personales (Fase 51) — fuera del alcance que esta primera
  corrida pudo cubrir con evidencia real; **no se declara cumplimiento
  ni se afirma protección de datos personal certificada** —
  `PROFESSIONAL_REVIEW_REQUIRED` si se necesita esa certificación.

## Recomendación

Cerrar los 2 blockers `P0` restantes (ambos triviales, config de `.env`
del entorno de destino: `APP-01-debug`, `APP-02-secret-key`) y volver a
correr `manage.py production_readiness`. Con esos 2 en `PASS`, el estado
pasaría a `READY_WITH_EXTERNAL_DEPENDENCIES` (por DIAN/DSPNE) —
suficiente para un primer despliegue de SINTEL como ERP operativo sin
transmisión electrónica real, nunca para declarar "facturación
electrónica DIAN production ready" sin los insumos externos
correspondientes.

## Continuidad (Fase 70)

`python manage.py production_readiness` queda como el mecanismo
recurrente — se recomienda ejecutarlo como parte del
`DEPLOYMENT_RUNBOOK.md` (paso 1, obligatorio) de cada release futuro,
no solo en esta auditoría inicial.
