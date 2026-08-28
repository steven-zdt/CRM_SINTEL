# REM-P1-04 — Sin validación de fecha de pago vs. fecha del documento

**Estado:** VERIFIED
**Prioridad:** P1
**App propietaria:** `bancos`
**Fecha:** 2026-08-28

## Hallazgo

`TransaccionBancariaConciliarSerializer.validate()` (`apps/tenant/bancos/
api/serializers.py:246-252`) y `TransaccionBancariaCRUDService.
conciliar_transaccion()` (`crud_service.py:129-...`) no validaban que la
fecha de la transacción bancaria (pago) fuera posterior o igual a la fecha
de emisión de la `Factura` vinculada — se podía conciliar un pago con
fecha anterior al documento que paga.

## Corrección

Se agregó la validación en `conciliar_transaccion()` (capa de negocio real
de este flujo, dado que `bancos` no tiene un `business_service.py` dedicado
a `TransaccionBancaria` — se intervino en el punto ya usado para el
disparador cross-app existente `FacturaInterAppAPI.
recalcular_estado_pago_automatico()`, mismo archivo/método, evitando
introducir una capa nueva). Solo se valida cuando se está vinculando/
cambiando `factura_uuid` (no `proveedor_uuid`/`cliente_uuid`, que enlazan a
un tercero completo sin fecha de documento propia). Se resuelve la Factura
vía `FacturaInterAppAPI.get_by_id()` (bridge cross-app ya sancionado y ya
usado en este mismo método) — si no resuelve (soft-reference sin match), no
se bloquea, mismo criterio de tolerancia a datos incompletos ya aplicado en
todo el proyecto (Kardex, Retenciones) para soft-references.

## Archivos modificados

- `apps/tenant/bancos/services/crud_service.py`

## Modelo afectado

Ninguno. Sin migración.

## Tests

`apps/tenant/bancos/tests/test_remediation_p1_04_fecha_pago_vs_documento.py`
(3 tests: fecha posterior permitida, fecha anterior rechazada — y
confirmado que no queda `factura_uuid` parcialmente guardado —, UUID de
factura no resoluble no bloquea). No existía ningún test previo de
`conciliar_transaccion`/`conciliar/` — gap real, no duplicado.

## Evidencia

Corrida local, 2026-08-28: 3/3 PASSED (parte del batch P1 combinado, 17/17
en la corrida final).

**Hallazgo del propio ciclo de validación (paso G/I del plan)**: la
primera corrida falló porque el test esperaba HTTP 400 — la corrección
en sí funcionaba correctamente (el `ValidationError` con el mensaje
exacto se levantaba y bloqueaba la conciliación), pero el código real
responde 422, no 400, para un `ValidationError` levantado desde la capa
de servicio (`conciliar_transaccion()`, en `crud_service.py`, corre
DESPUÉS de que `serializer.is_valid()` ya pasó). Investigado
`SintelServiceMixin.handle_service_error()`
(`apps/tenant/api/mixins.py:74-75`): mapeo **ya establecido y consistente
en todo el proyecto** — `DRFValidationError` desde la capa de servicio →
422; solo los errores de validación del propio `serializer.is_valid()`
(antes de llegar al servicio) producen 400. Bug del test, no del código
ni de la corrección — se corrigió la aserción a 422 con nota explicando
la convención.

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

- No se validó lo mismo para `proveedor_uuid`/`cliente_uuid` — no aplica
  directamente (un tercero no tiene una única "fecha de documento"), y no
  hay evidencia de que el negocio necesite una regla equivalente ahí.
