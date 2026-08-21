# APP_proveedores_AUDIT — Auditoria integral (app 6/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> clientes
-> **proveedores** -> inventario -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/proveedores` tiene `.agent/AUDITORIA_FLUJO_PROVEEDORES.md`
(v3.17.1, 2026-06-10, 725 lineas, "PRODUCTION READY") mas 2 docs
secundarios (`docs/proveedores_flow_map.md`,
`docs/proveedores_microtasks_architecture.md`) -- usados como fuente
primaria, verificados contra codigo actual.

**Verificado 1:1:** 3 modelos (`Proveedor`, `CuentasPagar`,
`Representante`), coincide con `APP_AUDIT_MATRIX.md`. `CuentasPagar`
es el resultado de una unificacion historica (`CuentaPorPagar` +
`Cartera` -> `CuentasPagar`, migraciones 0009-0015, ya cerrada, sin
restos duplicados encontrados).

Resumen de negocio: directorio de acreedores con conformidad fiscal
(NIT, regimen, CIIU), cuentas por pagar con `registrar_abono()`
(`select_for_update()` anti-race, igual patron que `clientes.Cartera`),
directorio de representantes/contactos autorizados por proveedor.

## FASE C/D/K — Service Layer y codigo muerto

**A diferencia de `clientes`, NO se encontro codigo muerto real en
`services/services.py`.** Este archivo tambien es un "backward-
compatibility layer" (mismo patron arquitectonico que `clientes`),
pero aqui las 3 funciones que contiene (`crear_proveedor`,
`actualizar_proveedor`, `qs_list`) **SI estan re-exportadas y
consumidas activamente**: `services/__init__.py` las envuelve
explicitamente ("Legacy wrappers for test_proveedores_api_and_
service") y 2 tests las importan (`test_proveedores_api_and_service.py`
via el paquete, `test_idempotence_v2614.py` via el submodulo
directo). Sin clases sombra sin consumidores (a diferencia de
`clientes`, que si tenia 4 clases muertas en su equivalente).

**Sin root `permissions.py` propio** (a diferencia de `empresa`, que
tenia un shim huerfano) -- confirma que no todas las apps replican el
mismo patron de deuda tecnica.

**Conclusion FASE K: 0 lineas de codigo muerto confirmado para
eliminar.**

**Hallazgo real (no es codigo muerto, es CONTRACT_DRIFT):**
`ProveedorBusinessService.obtener_configuracion_retenciones()` y
`calcular_componentes_retencion()` (`business_service.py:164-208`)
estan documentadas en los docs `.agent/` propios de la app como el
flujo SSoT para calcular retenciones al crear un gasto, marcadas
`[COMPLETED]` -- pero **no tienen NINGUN consumidor real en todo el
repo** (confirmado con grep de nombre de funcion, incluyendo
`apps/tenant/gastos`, que es el consumidor documentado). Ver FASE M
para el detalle completo -- este hallazgo es primariamente normativo
(afecta si las retenciones a proveedores se calculan correctamente),
no de limpieza de codigo, por eso se documenta ahi y no se resuelve
en esta pasada (requiere auditar `gastos`, app 12/16, primero).

## FASE M — Normativa colombiana

`proveedores` esta en la lista explicita de apps que requieren matriz
normativa. Ver **`documentacion/audits/apps/
APP_proveedores_NORMATIVE_MATRIX.md`** -- a diferencia de `clientes`
(solo configuracion), `proveedores` **SI contiene calculo real** de
Retefuente (4% fijo si no autorretenedor) y ReteICA (0.966% fijo si
persona NATURAL). Hallazgos principales:

1. **CONTRACT_DRIFT (P1):** la funcion que calcula estas tarifas nunca
   se invoca en ningun flujo real -- desconectada de `gastos`, pese a
   estar documentada como integrada.
2. Las tarifas en si (4% Retefuente plano, 0.966% ReteICA solo para
   NATURAL) son una simplificacion que no reflejaria correctamente la
   variacion real por concepto (Retefuente) ni por municipio/actividad
   (ReteICA) si llegaran a activarse -- marcado `REQUIERE_VALIDACION`,
   condicionado a resolver primero el hallazgo #1.

## FASE Q — Tests / Regresion

18 tests coleccionados (`apps/tenant/proveedores/tests/`). Regresion
ejecutada: **18 passed, 0 failed, 2 warnings preexistentes (min_value
DRF) en 1655.60s (0:27:35)**. Sin cambios de codigo en esta app, la
regresion confirma el baseline.

## Deferred

**ACTUALIZACION 2026-08-20 (post-auditoria de `gastos`, app 12/16):**
el item #1 (P1) fue **resuelto con evidencia directa**. Se confirmo
que `gastos.GastoBusinessService.procesar_gasto()` calcula
retenciones via `contabilidad.RetencionesService.obtener_retenciones_
desde_tercero()` -- una tercera implementacion, independiente y
correctamente centralizada, NO las funciones de esta app. El
mecanismo real funciona correctamente (Pull Model, sin gap
funcional); `obtener_configuracion_retenciones()`/
`calcular_componentes_retencion()` de `proveedores` son
**DEAD_CONFIRMED** (superseded, nunca conectadas). Ver
`documentacion/audits/apps/APP_gastos_NORMATIVE_MATRIX.md` para el
detalle completo. **Reclasificado de P1 a P3** -- limpieza de codigo
muerto pendiente (no se ejecuta en esta sesion para no reabrir una
app ya cerrada con regresion confirmada; queda para una sesion de
limpieza dedicada o para la FASE FINAL de esta mision).

Ver tabla completa (items #2/#3, sin cambios) en
`APP_proveedores_NORMATIVE_MATRIX.md`. Resumen actualizado:

| # | Item | Prioridad |
|---|---|---|
| 1 | ~~SSoT de retenciones desconectada de `gastos`~~ -- **RESUELTO**: `gastos` usa `contabilidad.RetencionesService` (mecanismo real, correcto). Las funciones de `proveedores` son codigo muerto confirmado, pendiente de eliminar en limpieza futura. | ~~P1~~ -> **P3** |
| 2 | Tarifa Retefuente deberia parametrizarse por concepto (no 4% plano) + validar cuantia minima UVT -- aplica solo si se decide reactivar/eliminar el codigo muerto del item #1 | P3 (informativo, codigo no se ejecuta) |
| 3 | Tarifa ReteICA deberia parametrizarse por municipio/actividad -- mismo condicionamiento que #2 | P3 (informativo, codigo no se ejecuta) |

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, sin codigo muerto para eliminar (FASE C/D/K)
- [x] Matriz normativa colombiana completa, con hallazgo P1 real (FASE M)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 18 passed, 0 failed
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**COMPLETED_WITH_DEFERRED** -- 18/18 tests pasan, 0 regresiones. El
hallazgo original (P1, CONTRACT_DRIFT de retenciones) fue **resuelto**
al auditar `gastos` (app 12/16): el mecanismo real es correcto, vive
en `contabilidad`. Se mantiene `_WITH_DEFERRED` por 3 items P3
(limpieza de codigo muerto confirmado, informativos, sin riesgo
funcional) en vez de `COMPLETED` puro.
