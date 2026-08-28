# REM-P1-02 — Delete de Gastos con bypass en DEBUG

**Estado:** VERIFIED
**Prioridad:** P1
**App propietaria:** `gastos`
**Fecha:** 2026-08-28

## Hallazgo

`GastoViewSet.destroy()` (`apps/tenant/gastos/api/viewsets.py:124-134`)
solo aplicaba el guard *"el gasto debe estar anulado antes de eliminar"*
cuando `settings.DEBUG` era `False`. Con `DEBUG=True` (que es, además, el
valor real usado en este entorno de tests — `.env: DJANGO_DEBUG=True`),
cualquier gasto se podía eliminar físicamente sin haber sido anulado
primero.

## Causa raíz

Atajo de desarrollo dejado en código de producción — la integridad del
dato terminaba dependiendo de una variable de entorno, mismo patrón de
bug ya encontrado y corregido en `inventario` en esta misma sesión
(commit `399f1c8`, guard de `ActivoFijo.destroy()`).

## Impacto

En cualquier entorno con `DEBUG=True` (desarrollo, y potencialmente
staging/QA mal configurados), se podía eliminar un `DocumentoSoporte` sin
pasar por la anulación trazable (`motivo_anulacion`/`usuario_anulacion`/
`fecha_anulacion`), perdiendo esa evidencia de auditoría.

## Corrección

Guard aplicado siempre, sin condicional a `settings.DEBUG`. Import de
`settings` removido del archivo (quedó sin otros usos).

## Archivos modificados

- `apps/tenant/gastos/api/viewsets.py`

## Modelo afectado

Ninguno. Sin migración.

## Tests

`apps/tenant/gastos/tests/test_remediation_p1_02_delete_debug_bypass.py`
(2 tests, ejecutados bajo `DEBUG=True` real del entorno de test —
confirmado con `self.assertTrue(settings.DEBUG, ...)` explícito para que
el test no dé un falso positivo si el entorno cambiara). No existía ningún
test previo de `GastoViewSet.destroy()` — gap real de cobertura, no
duplicado.

## Evidencia

Corrida local, 2026-08-28: 2/2 PASSED (parte del batch P1 combinado, 17/17
en la corrida final).

**Hallazgo del propio ciclo de validación (paso G/I del plan)**: la
primera corrida falló — el test asumía que el entorno de test corre con
`settings.DEBUG=True` (como el `.env` del proyecto declara), pero el
entorno de test real usa `DEBUG=False`. Bug del test, no del código: se
corrigió para forzar `DEBUG=True` explícitamente con
`@override_settings(DEBUG=True)` en vez de depender del ambiente —
determinístico y prueba el escenario exacto donde el bug original era
invisible, sin importar qué `DEBUG` tenga el entorno real.

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

Ninguno.
