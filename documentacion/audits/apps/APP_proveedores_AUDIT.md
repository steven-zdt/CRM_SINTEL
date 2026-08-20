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

Ver tabla completa en `APP_proveedores_NORMATIVE_MATRIX.md`. Resumen:

| # | Item | Prioridad |
|---|---|---|
| 1 | SSoT de retenciones (`obtener_configuracion_retenciones`) documentada como integrada con `gastos` pero sin consumidor real -- verificar con evidencia completa al auditar `gastos` | **P1** |
| 2 | Tarifa Retefuente deberia parametrizarse por concepto (no 4% plano) + validar cuantia minima UVT -- condicionado a resolver #1 primero | P2 |
| 3 | Tarifa ReteICA deberia parametrizarse por municipio/actividad -- condicionado a resolver #1 primero | P2 |

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, sin codigo muerto para eliminar (FASE C/D/K)
- [x] Matriz normativa colombiana completa, con hallazgo P1 real (FASE M)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 18 passed, 0 failed
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**COMPLETED_WITH_DEFERRED** -- 18/18 tests pasan, 0 regresiones. Se
usa `_WITH_DEFERRED` por el hallazgo P1 (CONTRACT_DRIFT de retenciones
vs `gastos`), que no bloquea el cierre de esta app individual pero
queda registrado como prioridad alta para cuando se audite `gastos`.
