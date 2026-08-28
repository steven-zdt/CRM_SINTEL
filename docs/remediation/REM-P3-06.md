# REM-P3-06 — Reporting Hub: 4 de 5 datasets sin pantalla propia

**Estado:** DEFERRED (requiere trabajo de frontend nuevo, no una corrección puntual)
**Prioridad:** P3
**App propietaria:** `core` (frontend del Reporting Hub)
**Fecha:** 2026-08-28

## Hallazgo

El backend del Reporting Hub sirve 5 datasets reales
(`ventas.resumen`, `inventario.movimientos`, `contabilidad.balance_prueba`,
`tax.retenciones`, `gastos.*`), cada uno con su propio provider real y
disciplinado (confirmado por el agente de UX de la auditoría empresarial:
un solo SSoT por dataset, con advertencias documentadas de divergencias
intencionales). El frontend (`reportes_landing.js`) solo tiene pantalla
propia para 1 (`ventas.resumen`) — los otros 4 se muestran como
"Próximamente", ya documentado explícitamente en el propio comentario del
archivo (FASE 39).

## Auditoría de cada dataset (regla explícita: metadata, API, UI, filtros, scope, export — no crear pantallas duplicadas)

| Dataset | Backend (provider real) | UI propia |
|---|---|---|
| `ventas.resumen` | ✅ | ✅ |
| `inventario.movimientos` | ✅ | ❌ "Próximamente" |
| `contabilidad.balance_prueba` | ✅ | ❌ "Próximamente" |
| `tax.retenciones` | ✅ | ❌ "Próximamente" |
| `gastos.*` | ✅ | ❌ "Próximamente" |

## Decisión

**No se implementan las 4 pantallas faltantes en esta sesión.** Cada una
requiere su propio diseño de tabla/filtros/export — 4 piezas de trabajo de
frontend genuinas, no un fix uniforme de 15 minutos. Construirlas
apresuradamente arriesgaría duplicar mal el patrón ya establecido por
`ventas.resumen` en vez de replicarlo correctamente.

## Alcance para una sesión dedicada futura

Para cada uno de los 4 datasets pendientes: replicar el patrón ya usado
por `ventas.resumen` en `reportes_landing.js` (registro en `KNOWN_VIEWS`,
tabla con filtros/scope/período, botón de exportación) — sin inventar un
patrón nuevo, solo repetirlo 4 veces con los campos reales de cada
dataset.

## Governance

N/A — sin cambio de código en esta sesión.
