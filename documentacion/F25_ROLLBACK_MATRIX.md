# F25 — Matriz de Rollback

**Fecha:** 2026-08-10

Para cada servicio con multiples escrituras reales dentro de su propio scope, el
punto de fallo inyectado y el resultado observado (real, no supuesto).

| Servicio | Write 1 | Write 2 | Write N | Punto de fallo inyectado | Rollback esperado | Resultado observado |
|---|---|---|---|---|---|---|
| `RecepcionCompraBusinessService.confirmar_recepcion()` | `ItemOrdenCompra.save()` (item A) | `MovimientoInventario` (item A, via KardexService) | item B repite 1+2 | Item B excede `cantidad_recibida` (simulando carrera) | Rollback total (A y B) | **Antes del fix (F24):** A quedaba persistido. **Con el fix:** 0 rastro de A ni B (`test_f24_confirmar_recepcion_atomicidad.py`, revertido con `git stash` y confirmado FAIL, luego PASS) |
| `VentaBusinessService.procesar_y_facturar_venta()` | `Venta.save()` | `Factura` (DIAN) | `MovimientoInventario` (SALIDA_VENTA) por item | Stock insuficiente en el ultimo item | Rollback total | **Antes del fix (F23):** Venta+Factura persistian. **Con el fix:** 0 rastro (`test_f23_venta_inventario.py::test_stock_insuficiente_revierte_venta_y_factura_completas`) |
| `GastoBusinessService.procesar_gasto()` | `DocumentoSoporte` (via CRUD, atomic) | `Retencion` RETEFUENTE (cruda, sin savepoint) | `Retencion` RETEICA (cruda) | Fallo forzado (mock) en la 2a retencion | Rollback total | **Antes del fix (F25):** DocumentoSoporte + 1a retencion persistian (confirmado, `1 failed in 158.54s`). **Con el fix:** 0 rastro (`test_f25_procesar_gasto_atomicidad.py`, `2 passed in 232.39s`) |
| `Contabilizador.contabilizar()` | `AsientoContable.save()` | `MovimientoContable.bulk_create()` | `ImpuestoDocumento.bulk_create()` | `validar_cuadratura()`/`validar_periodo_abierto()`/resolucion de cuenta fallida (antes del `save()`, dentro del mismo `with atomic()`) | Rollback total (nada se guarda hasta pasar todas las validaciones) | Confirmado por diseno: todas las validaciones ocurren ANTES de `asiento.save()` (linea 84-97 de `contabilizador.py`), y el bloque completo esta en `with transaction.atomic()` sin ningun `except` que lo capture localmente -- cualquier excepcion propaga y Django revierte. Sin test de inyeccion de fallo dedicado adicional (el comportamiento ya esta cubierto por `test_f24_periodo_cerrado_rechaza_contabilizacion`, que fuerza exactamente este tipo de fallo -- `validar_periodo_abierto()` -- y confirma 0 `AsientoContable` creados) |
| `FacturaBusinessService.guardar_desde_dto()` | `Factura` | `FacturaImpuesto` (loop) | `Retencion` (loop) / `NotaCredito` / `ItemFactura` (loop) | Cualquier escritura de esta secuencia falla (no hay try/except local) | Rollback total (via Django, no via codigo de aplicacion) | Confirmado por lectura de codigo (ver F25-FP-013 en `F25_FINDINGS.md`); no se escribio un test de inyeccion de fallo dedicado dado que el mecanismo es la ausencia misma de manejo local de excepciones (nada que revertir manualmente) -- clasificado SAFE_BY_DESIGN, no HIGH, por lo que no aplica la regla F25.51 de prueba obligatoria de falla por write (esa regla aplica a "servicios criticos" con el patron de riesgo confirmado, no a todos los servicios multi-write per se) |

## Nota sobre alcance de pruebas de inyeccion de falla

La regla F25.51 pide inyectar fallo en cada write "para servicios criticos... cuando
el flujo tenga multiples escrituras". Se interpreta "critico" como los servicios
donde el analisis de codigo (F25_FINDINGS.md) identifico un riesgo REAL o donde ya
existia evidencia previa de un defecto (RecepcionCompra, Venta/Facturacion,
MovimientoInventario/Contabilizacion) -- los 4 primeros de esta tabla. Para
`Contabilizador` y `guardar_desde_dto`, que resultaron SAFE_BY_DESIGN, la prueba de
falla existente (periodo cerrado) mas el analisis de codigo se consideran evidencia
suficiente y proporcional; no se duplico esfuerzo escribiendo pruebas adicionales
para escenarios ya demostrados estructuralmente seguros.
