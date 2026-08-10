# F23 — Matriz de Tests

**Fecha:** 2026-08-10
**Ejecucion real:** 3 corridas relevantes:
1. Primera corrida completa: **6 failed, 3 passed** (2 causas raiz reales identificadas, ver §5).
2. Tras corregir el bug de atomicidad + 6 aserciones de test: **8 passed, 1 failed** (1 aserciona
   propia mas con el mismo olvido, ver §5).
3. Tras la ultima correccion: **9/9 pasan** (398s + 235s). Confirmado con una corrida consolidada
   final de F21+F22+F23 juntos (45 tests) para descartar regresion cruzada.

## 1. `test_f23_venta_inventario.py` (8 tests, `SintelTenantTestCase`)

| # | Escenario | Test | Resultado |
|---|---|---|---|
| 1 | Venta facturada genera `MovimientoInventario(SALIDA_VENTA)` con `documento_origen` correcto y sede propagada | `test_venta_facturada_genera_movimiento_salida_venta` | ✅ Real |
| 2 | El costo del movimiento usa `Producto.costo_promedio`, nunca `precio_unitario`/`precio_venta` | `test_costo_del_movimiento_usa_costo_promedio_no_precio_unitario` | ✅ Real |
| 3 | Item de `Servicio` no genera movimiento de inventario | `test_item_servicio_no_genera_movimiento_inventario` | ✅ Real |
| 4 | Stock insuficiente revierte **toda** la operacion (Venta + Factura + movimientos), no solo el item que fallo | `test_stock_insuficiente_revierte_venta_y_factura_completas` | ✅ Real — expuso y confirmo el fix de atomicidad (§5) |
| 5 | Multi-item: 1 movimiento por cada `ItemVenta` con producto real, 0 para servicio | `test_multi_item_genera_un_movimiento_por_cada_producto_y_ninguno_para_servicio` | ✅ Real |
| 6 | Reintentar la generacion de salida sobre la misma Venta no duplica el movimiento | `test_reintentar_generar_salida_no_duplica_movimiento` | ✅ Real |
| 7 | `anular_venta()` rechaza una venta ya `FACTURADA_DIAN`, sin generar ningun movimiento compensatorio (porque no hay mecanismo, ni debe haberlo) | `test_anular_venta_ya_facturada_es_rechazado_estructuralmente` | ✅ Real |
| 8 | **E2E**: Venta -> SALIDA_VENTA -> `ExtractorInventario` (F22, sin cambios) -> `AsientoContable` cuadrado | `test_e2e_venta_facturada_hasta_asiento_contable_via_extractor_f22` | ✅ Real |

## 2. `test_f23_venta_inventario_multitenant.py` (1 test, 2 schemas reales)

| # | Escenario | Test | Resultado |
|---|---|---|---|
| 1 | Una venta de un tenant no afecta stock ni genera movimientos en otro tenant | `test_venta_de_un_tenant_no_afecta_stock_ni_movimientos_de_otro_tenant` | ✅ Real |

## 3. Regresion consolidada (F21 + F22 + F23 en una sola corrida)

`test_f21_recepcion_compra.py` + `test_f21_traslado_inventario.py` (16) +
`test_f22_extractor_inventario_{mapping,integration,multitenant}.py` (20) +
`test_f23_venta_inventario{,_multitenant}.py` (9) = **45/45 pasan**, confirmando que el fix de
atomicidad (§5) y la nueva integracion no regresan ninguna fase anterior.

## 4. Cobertura NO incluida (DEFERRED, declarada — ver `F23_FINAL_REPORT.md`)

| Item | Motivo |
|---|---|
| Devoluciones (`ENTRADA_DEVOLUCION` desde `NotaCredito`) | `NotaCredito` no tiene lineas de producto/cantidad — requeriria crear un modelo nuevo, fuera del alcance minimo de F23 (`F23_FACTURAS_BASELINE.md` §3) |
| Reverso de inventario por anulacion | No aplica — `anular_venta()` rechaza estructuralmente cualquier venta ya facturada, no existe el escenario (test #7 de §1 lo confirma) |
| Despacho/entrega parcial | No existe ese concepto en el modelo `Venta`/`ItemVenta` |
| Tests de API HTTP completos (`POST /ventas/{uuid}/procesar-facturar/`) | Cubierto a nivel de `VentaBusinessService` directamente (mismo criterio que F21/F22) — la capa HTTP es delgada y ya delega integramente |

## 5. Hallazgo real durante el desarrollo — bug de atomicidad preexistente (no de F23)

**Confirmado, no una suposicion:** `VentaBusinessService.procesar_y_facturar_venta()` esta
decorado `@transaction.atomic`, pero su propio `try/except` capturaba toda excepcion y retornaba
una tupla `(False, {...}, codigo)` **sin volver a lanzarla**. Django solo revierte una transaccion
`atomic()` cuando una excepcion escapa del bloque decorado — al capturarla y retornar
normalmente, Django interpreta que el bloque termino sin error y **confirma (commit) todo lo
escrito hasta ese punto**, incluyendo la `Venta` y la `Factura` ya creadas, aunque la funcion
reportara `ok=False` al llamador.

Esto es un bug preexistente a F23 (el patron try/except ya estaba ahi) que **nunca se habia
manifestado en la practica** porque los puntos de fallo anteriores (DSV de cliente/items,
resolucion DIAN) ocurren **antes** de cualquier escritura real. `_generar_salida_inventario()`
(F23) es el primer paso que puede fallar (stock insuficiente) **despues** de que `Venta` y
`Factura` ya existen — expuso el bug en la practica, primero como
`test_stock_insuficiente_revierte_venta_y_factura_completas` fallando con `1 != 0` (una `Venta`
persistida pese a `ok=False`).

**Correccion:** `transaction.set_rollback(True)` agregado en los 3 bloques `except` del metodo
(`ValueError`, `DjangoValidationError`, `Exception` generico) — fuerza el rollback real del
`atomic()` exterior aunque la excepcion se maneje internamente. Verificado por el mismo test:
tras el fix, una venta con stock insuficiente no deja ningun rastro (ni `Venta`, ni `Factura`, ni
`MovimientoInventario`).

## 6. Otros hallazgos durante el desarrollo (bugs de test propios, no de produccion)

7 aserciones en los tests nuevos contaban `MovimientoInventario` sin filtrar por
`tipo=SALIDA_VENTA`, olvidando que `setUp()`/`_preparar_tenant()` ya generan su propio
`ENTRADA_AJUSTE` de stock inicial antes de cada escenario. Corregido filtrando por tipo en cada
asercion afectada — documentado como parte del proceso, no ocultado (mismo criterio que
F21/F22).

## 7. Veredicto

**9/9 tests nuevos de F23 pasan, 45/45 en la regresion consolidada F21+F22+F23.** No se declara
"cobertura 100% del prompt maestro" — §4 documenta explicitamente lo que falta.
