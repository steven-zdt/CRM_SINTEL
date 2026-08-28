# REM-P3-05 — "Cartera pendiente": 2 selectores divergentes

**Estado:** VERIFIED (1 de 2 confirmado muerto y eliminado; el SSoT real
queda sin ambigüedad)
**Prioridad:** P3
**App propietaria:** `clientes`
**Fecha:** 2026-08-28

## Hallazgo

`apps/tenant/clientes/services/selectors.py` tenía 2 métodos calculando
"cartera pendiente" con vocabularios de estado distintos:
`get_cartera_kpis_facturas_venta()` (agrega sobre `Factura.estado_pago`,
`NO_PAGADA`/`PAGO_PARCIAL`/`PAGADA`) y `get_cartera_kpis()` (agrega sobre
el modelo `Cartera`, `SIN_PAGO`/`PARCIAL`/...).

## Investigación

- `get_cartera_kpis_facturas_venta()` — consumidor real confirmado:
  `apps/tenant/clientes/api/viewsets.py:786`. El propio `.agent/
  AUDITORIA_FLUJO_CLIENTES.md:183` ya lo etiqueta "SSoT".
- `get_cartera_kpis()` — **cero consumidores reales** (grep repo-wide,
  solo su propia definición) — `.agent/AUDITORIA_FLUJO_CLIENTES.md:184`
  ya lo etiqueta "Cartera legacy". `DEAD_CONFIRMED`.
- **El modelo `Cartera` en sí NO está muerto** — tiene CRUD real, API,
  frontend (`clientes.cartera.js`, `offcanvas_abono_cartera.html`) y
  tests propios (`test_cartera_crud_api.py`) — es un concepto de negocio
  real (registro manual de abonos), distinto del KPI agregado que sí
  estaba huérfano. No se tocó nada de eso.

## Corrección

Se eliminó únicamente el método muerto `get_cartera_kpis()`. El SSoT del
KPI "cartera pendiente" (el número que se muestra como indicador
agregado) queda sin ambigüedad: `get_cartera_kpis_facturas_venta()`.

## Archivos modificados

- `apps/tenant/clientes/services/selectors.py`

## Modelo afectado

Ninguno. Sin migración (el modelo `Cartera` no se tocó).

## Tests

Ninguno nuevo — es una eliminación de código muerto confirmado sin
consumidores; no hay comportamiento que probar. Se verificó que
`test_cartera_crud_api.py` (existente) no referencia
`get_cartera_kpis()` — sin riesgo de regresión.

## Governance

Pendiente de confirmar en el barrido conjunto de P3.

## Riesgos / deuda pendiente

- **No se resolvió si el modelo `Cartera` (abonos manuales) y
  `Factura.estado_pago` (derivado automático) representan, en la
  práctica, información que podría desincronizarse** para un mismo
  cliente (ej. un abono registrado manualmente en `Cartera` sin que la
  `Factura` correspondiente actualice su `estado_pago`, o viceversa). Esa
  es una pregunta de reconciliación de datos más profunda, no resuelta
  por eliminar un método muerto — requiere decisión de producto sobre si
  `Cartera` debe seguir siendo un registro independiente o derivarse
  también de `Factura`.
