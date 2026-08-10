# F22 — Matriz de Tests

**Fecha:** 2026-08-10
**Ejecucion real:** 3 corridas reales (no una sola conveniente):
1. `test_f22_extractor_inventario_mapping.py` (sin DB, `SimpleTestCase`) → **9 passed in 76s**.
2. Corrida completa inicial (integracion F22 + multitenant F22 + regresion F21) →
   **19 passed** (F21, sin cambios, sin regresion) **+ 8 failed** (F22 nuevo) en 1872s.
3. Tras diagnosticar y corregir el bug real (ver §3), re-corrida de los 2 archivos afectados →
   **11 passed in 408s** (0 failed).

**Total F22 (mapping + integracion + multitenant): 9 + 11 = 20 tests, 20/20 pasan.**
**Total combinado con regresion F21 verificada en la misma sesion: 20 + 19 = 39 tests.**

## 1. Mapeo DTO (sin DB) — `test_f22_extractor_inventario_mapping.py`

| # | Escenario | Test | Resultado |
|---|---|---|---|
| 1 | `ENTRADA_COMPRA` -> lineas INVENTARIO_PRODUCTO(DEBE)/PASIVO_COMPRA_INVENTARIO(HABER) | `test_entrada_compra_lineas_inventario_debe_pasivo_haber` | Real |
| 2 | `SALIDA_VENTA` -> COSTO_VENTA_PRODUCTO(DEBE)/INVENTARIO_PRODUCTO(HABER) | `test_salida_venta_lineas_costo_venta_debe_inventario_haber` | Real |
| 3 | `ENTRADA_AJUSTE` -> INVENTARIO_PRODUCTO(DEBE)/INGRESO_AJUSTE_INVENTARIO(HABER) | `test_entrada_ajuste_lineas_inventario_debe_ingreso_ajuste_haber` | Real |
| 4 | `ENTRADA_DEVOLUCION` -> INVENTARIO_PRODUCTO(DEBE)/COSTO_VENTA_DEVOLUCION(HABER) | `test_entrada_devolucion_lineas_inventario_debe_costo_venta_devolucion_haber` | Real |
| 5 | `SALIDA_BAJA` -> GASTO_DETERIORO_INVENTARIO(DEBE)/INVENTARIO_PRODUCTO(HABER) | `test_salida_baja_lineas_gasto_deterioro_debe_inventario_haber` | Real |
| 6 | `SALIDA_CONSUMO` usa concepto distinto de `SALIDA_BAJA` (mismo `tipo_transaccion`) | `test_salida_consumo_usa_concepto_distinto_de_salida_baja_mismo_tipo_transaccion` | Real |
| 7 | Tercero generico cuando no hay proveedor resoluble | `test_tercero_generico_cuando_no_hay_proveedor_resoluble` | Real |
| 8 | `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` fuera de `_TIPOS_CONTABILIZABLES` | `test_traslado_salida_no_esta_en_tipos_contabilizables` | Real |
| 9 | Tipos de `ActivoFijo` fuera de `_TIPOS_CONTABILIZABLES` | `test_tipos_de_activo_fijo_no_estan_en_tipos_contabilizables` | Real |

## 2. Integracion + E2E (DB real) — `test_f22_extractor_inventario_integration.py`

| # | Escenario pedido por el prompt maestro | Test | Resultado |
|---|---|---|---|
| 1 | Entrada por compra (via Compra->Recepcion real) genera asiento balanceado con proveedor real | `test_entrada_compra_genera_asiento_balanceado_con_proveedor_real` | ✅ Real — verifica `debe_total==haber_total`, `documento_origen_modelo='MovimientoInventario'`, `tercero_nit` = NIT real del proveedor via la cadena `RecepcionCompraItem->recepcion->orden_compra->proveedor` |
| 2 | Ejecutar el extractor 2 veces no duplica el asiento | `test_ejecutar_extractor_dos_veces_no_duplica_asiento` | ✅ Real |
| 3 | `ENTRADA_AJUSTE` genera asiento | `test_entrada_ajuste_genera_asiento` | ✅ Real |
| 4 | `SALIDA_BAJA` y `SALIDA_CONSUMO` usan cuentas de gasto distintas | `test_salida_baja_y_salida_consumo_usan_cuentas_de_gasto_distintas` | ✅ Real |
| 5 | Periodo cerrado impide el asiento, aislado en `errores` (no tumba el batch) | `test_periodo_cerrado_impide_asiento_y_queda_en_errores` | ✅ Real |
| 6 | Regla contable faltante aisla el error sin tumbar el batch | `test_regla_contable_faltante_aisla_el_error_sin_tumbar_el_batch` | ✅ Real |
| 7 | Movimiento con `costo_unitario=0` aisla asiento vacio sin tumbar el batch | `test_movimiento_costo_cero_aisla_asiento_vacio_sin_tumbar_el_batch` | ✅ Real |
| 8 | Traslado entre sedes (flujo completo SOLICITADO->RECIBIDO) no genera asiento | `test_traslado_no_genera_asiento` | ✅ Real |
| 9 | **E2E S22.23**: orden 100, recepcion 60 (extraer->1 asiento, reextraer->sigue 1), recepcion 40 restantes (extraer->2 asientos, el primero no se duplica), total debe=1000.00 | `test_e2e_compra_parcial_60_mas_40_no_duplica_primer_asiento` | ✅ Real |
| 10 | **E2E S22.24**: Bogota=100/Barranquilla=20, traslado de 30, 0 asientos generados antes y despues | `test_e2e_traslado_bogota_barranquilla_sin_asiento_economico` | ✅ Real |

## 3. Multi-tenant real (2 schemas) — `test_f22_extractor_inventario_multitenant.py`

| # | Escenario | Test | Resultado |
|---|---|---|---|
| 1 | El extractor de un tenant no extrae ni puede contabilizar movimientos de otro tenant (2 schemas reales, `tenant1`/`tenant2`) | `test_extractor_de_un_tenant_no_extrae_movimientos_de_otro_tenant` | ✅ Real |

## 4. Regresion F21 (obligatoria, sin retroceso)

`apps/tenant/compras/tests/test_f21_recepcion_compra.py` +
`apps/tenant/inventario/tests/test_f21_traslado_inventario.py` → **19 passed** en la misma
corrida donde se detectaron las 8 fallas de F22 (nunca se toco codigo de F21 en esta fase) —
confirma que F22 no rompe F21.

## 5. Bug real encontrado y corregido durante el desarrollo (documentado, no ocultado)

La primera corrida completa arrojo **8 fallas** (`0 != 1`/`0 != 2` en todos los asserts de
`contabilizados`). Diagnostico: `KardexService.registrar_movimiento()` estampa
`MovimientoInventario.created_at` con `timezone.now()` real (la fecha real de ejecucion del test,
no una fecha ficticia), pero el `setUp()` de ambos archivos de test creaba un `PeriodoContable`
hardcodeado a `"2026-06"` — `Contabilizador._resolver_periodo()` nunca encontraba un periodo que
cubriera la fecha real, y cada movimiento caia silenciosamente en `resultados['errores']` en vez
de contabilizarse. **No era un bug del extractor** (confirmado independientemente: los 9 tests de
mapeo, que no dependen de periodo/BD, ya pasaban limpio antes de esta corrida). Corregido
calculando el periodo dinamicamente con `django.utils.timezone.localdate()` (rango del año
completo, para no depender de en que dia exacto corre la suite). Re-corrida: 11/11 pasan.

## 6. Cobertura NO incluida (declarada, no oculta)

| Item | Motivo |
|---|---|
| Tests de `SALIDA_VENTA` contra datos reales de una venta | No existen movimientos `SALIDA_VENTA` reales hoy (`ventas`/`facturas` no llaman a `KardexService` — ver `F22_INVENTARIO_BASELINE.md` §4). El mapeo de `SALIDA_VENTA` SI esta probado (test #2 de §1) contra un movimiento sintetico — lo que falta es la integracion Ventas->Inventario en si, fuera de alcance de F22 |
| Movimientos de `ActivoFijo` contabilizados | Fuera de alcance de F22 por decision (dominio distinto) — solo se prueba que estan explicitamente excluidos (test #9 de §1) |
| Tests de API HTTP (`backfill_contabilidad` invocado via HTTP/endpoint) | El comando es de management, no de API — no aplica |
| Tarea Celery periodica para el extractor | No se crea (ver `F22_FINAL_REPORT.md`) — no hay nada que testear ahi |

## 7. Veredicto

**20/20 tests nuevos de F22 pasan por ejecucion real** (9 mapeo + 10 integracion/E2E + 1
multitenant), **19/19 tests de F21 confirmados sin regresion en la misma sesion.** No se declara
"cobertura 100% del prompt maestro" — la tabla §6 documenta explicitamente lo que falta, mismo
criterio de honestidad que `F19_INTEGRATION_TEST_MATRIX.md`/`F21_TEST_MATRIX.md`.
