# REM-P3-09 — OrdenCompra.ANULADA: la transición ya es alcanzable (corrección de la auditoría)

**Estado:** VERIFIED (hallazgo original impreciso — ya resuelto además
por REM-P1-01)
**Prioridad:** P3
**App involucrada:** `compras`
**Fecha:** 2026-08-28

## Hallazgo original (impreciso)

`BUSINESS_GAP_MATRIX.md` reportaba: *"`OrdenCompra.ESTADO_CHOICES` incluye
`'ANULADA'` pero ningún método de servicio transiciona a ese estado —
código inalcanzable."*

## Investigación

`OrdenCompraBusinessService.cambiar_estado_orden_compra()`
(`apps/tenant/compras/services/business_service.py:339-...`) es un método
de servicio real, expuesto vía endpoint HTTP (`cambiar-estado`), que
acepta **cualquier** valor válido de `ESTADO_CHOICES` como destino —
incluido `'ANULADA'` — desde antes de esta sesión. El estado siempre fue
técnicamente alcanzable por esta vía genérica; no existía (y sigue sin
existir) un endpoint *dedicado* `anular/` como el que sí tiene
`GastoViewSet`, pero eso es una diferencia de conveniencia de API, no un
estado inalcanzable.

**Confirmado con evidencia directa**: `REM-P1-01` (misma sesión) agregó
`OrdenCompraBusinessService.TRANSICIONES_VALIDAS` y su test
`test_anular_orden_aprobada_sigue_permitido`
(`apps/tenant/compras/tests/test_remediation_p1_01_estados_orden_compra.py`)
prueba exactamente `APROBADA → ANULADA` con éxito.

## Decisión

**No se crea ningún método/endpoint nuevo.** El hallazgo original estaba
equivocado — el estado siempre fue alcanzable por el endpoint genérico
`cambiar-estado`, y ahora además está correctamente validado por la
máquina de estados de `REM-P1-01` (que sí permite `APROBADA → ANULADA`,
pero ya no permite anular una orden `RECIBIDA`/`PARCIAL`, un endurecimiento
real y deliberado, no relacionado con este hallazgo). Se corrige la
clasificación en `BUSINESS_GAP_MATRIX.md`.

## Archivos modificados

Ninguno nuevo — cubierto por `REM-P1-01`. Se corrige la clasificación en
`documentacion/auditoria_empresarial/BUSINESS_GAP_MATRIX.md`.

## Governance

N/A — sin cambio de código adicional.
