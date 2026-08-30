# P0-02 — Períodos contables cerrados no bloqueaban Facturas/Gastos

**Estado:** VERIFIED
**Apps:** `facturas`, `gastos` (consumidores) / `contabilidad` (owner de `verificar_periodo_cerrado()`)
**Fecha:** 2026-08-28

## Hallazgo

`PeriodoContable.__doc__` afirma explícitamente: *"Bloquea
edición/anulación de Facturas y Gastos en periodos cerrados."* La función
real (`verificar_periodo_cerrado()`) solo se invocaba desde dentro de
`contabilidad` (`AsientoContable`) — cero usos en `facturas`/`gastos`
confirmados por grep exhaustivo antes de corregir.

## Causa raíz

Integración incompleta: la función se implementó para el ciclo de vida
de `AsientoContable` pero nunca se conectó a los 2 consumidores
adicionales que el propio docstring promete cubrir. Sin evidencia de que
fuera una decisión deliberada.

## Corrección (reutilización, sin duplicar lógica)

Ver matriz completa en `P0_02_PERIOD_CLOSURE_MATRIX.md`. Se invoca la
función YA EXISTENTE de `contabilidad` desde 4 puntos reales de mutación
(2 en Facturas, 2 en Gastos) — no se creó ninguna función paralela
(`check_period_closed_new()` o similar).

## Tests

`test_remediation_p0_02_periodo_cerrado.py` (facturas, 4 tests) +
`test_remediation_p0_02_periodo_cerrado.py` (gastos, 4 tests) — período
abierto/cerrado × PATCH/anulación, para ambas apps. 8/8 PASS (parte del
batch combinado de 26 tests, 607.33s, ver `REM-P0-02.md`).

## Antes / Después

| | Antes | Después |
|---|---|---|
| PATCH factura con `fecha_emision` en período cerrado | 200, editado sin restricción | 400 |
| Anular factura con `fecha_emision` en período cerrado | 200, anulado sin restricción | 400 |
| PATCH/anular gasto con fecha en período cerrado | Sin restricción | 400 |

## Riesgos / deuda pendiente

- No se bloqueó `CREATE` — decisión documentada, no gap (ver matriz).
- Transiciones administrativas de Factura (`ENVIADA→ACEPTADA`, etc.) no
  se validan contra el período — decisión deliberada (reflejan una
  respuesta externa ya ocurrida, no una edición retroactiva).
