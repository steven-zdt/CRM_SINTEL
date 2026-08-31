# PRODUCTION_READINESS_FINAL — Fase 67

**Versión evaluada:** rama `feat/onboarding-cookie`, commit base `8377edc`
(este módulo se commitea sobre ese estado).
**Fecha de la corrida:** 2026-08-31T15:48:37Z
**Herramienta:** `python manage.py production_readiness` (nueva,
implementada en esta misión — `apps/public/core/production_readiness/`)

## Estado (Fase 66 — nunca "certificado")

## **NOT_READY**

No `READY`, no `READY_WITH_EXTERNAL_DEPENDENCIES` — hay blockers `P0`
reales que no son dependencias externas y que sí están al alcance de
corregirse (a diferencia de DIAN/DSPNE, que sí son
`EXTERNAL_DEPENDENCY` correctamente clasificados y no cuentan como la
razón del `NOT_READY`).

## Los 3 blockers reales, en orden de esfuerzo para cerrarlos

1. **`APP-02-secret-key` (trivial — minutos):** generar
   `DJANGO_SECRET_KEY` real y definirla en el `.env` del entorno de
   destino. No requiere cambio de código — el código ya lee
   correctamente de la variable de entorno
   (`config/settings.py:17`); falta que el entorno de destino la
   provea.
2. **`APP-01-debug` (trivial — minutos):** `DEBUG=False` en el `.env`
   del entorno de destino. Mismo patrón — no es un bug de código, es
   configuración de despliegue pendiente.
3. **`BAK-02-restore-tested` (real — requiere una ventana dedicada):**
   ejecutar el drill de `BACKUP_RESTORE_RUNBOOK.md` contra un tenant de
   prueba real y documentar el resultado con evidencia (RPO/RTO
   medidos). Es el único de los 3 que requiere trabajo real más allá de
   configuración.

## Dependencias externas (correctamente BLOCKED, no fingidas)

- Transmisión real DIAN (`docs/remediation/REM-EXT-01.md`).
- Transmisión real DSPNE (`docs/remediation/REM-EXT-02.md`).

Ninguna de las dos bloquea un primer despliegue de SINTEL como ERP
interno/operativo (facturación/contabilidad/inventario funcionan sin
transmisión electrónica real) — SÍ bloquean declarar "facturación
electrónica production-ready ante la DIAN", que es una afirmación
distinta y más específica.

## Checks ejecutados — resumen

19 checks reales, 9 categorías (`APPLICATION`, `SECURITY`, `DATABASE`,
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

## Lo que NO se verificó en esta pasada (honesto, no inferido)

- TLS/DNS reales — no existe ambiente expuesto para verificar.
- Restauración real de backup — comando existe, drill no ejecutado.
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

Cerrar los 3 blockers `P0` (2 triviales de configuración, 1 que
requiere un drill real de backup/restore) y volver a correr `manage.py
production_readiness`. Con esos 3 en `PASS`, el estado pasaría a
`READY_WITH_EXTERNAL_DEPENDENCIES` (por DIAN/DSPNE) — suficiente para un
primer despliegue de SINTEL como ERP operativo sin transmisión
electrónica real, nunca para declarar "facturación electrónica DIAN
production ready" sin los insumos externos correspondientes.

## Continuidad (Fase 70)

`python manage.py production_readiness` queda como el mecanismo
recurrente — se recomienda ejecutarlo como parte del
`DEPLOYMENT_RUNBOOK.md` (paso 1, obligatorio) de cada release futuro,
no solo en esta auditoría inicial.
