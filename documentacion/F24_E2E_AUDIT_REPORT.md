# F24 — Reporte de Auditoria E2E (codigo real, F21-F23)

**Fecha:** 2026-08-10

Este documento cubre F24.2 a F24.5 -- la relectura del codigo real de F21/F22/F23
para confirmar que el circuito sigue intacto, previo a construir los escenarios E2E
nuevos (`F24_E2E_TEST_MATRIX.md`).

## F24.2 — F21: Compras -> Recepcion -> Inventario -> Kardex

Flujo confirmado sin cambios desde el cierre de F21:
`OrdenCompra -> RecepcionCompra -> RecepcionCompraItem -> KardexService.registrar_movimiento()
-> MovimientoInventario -> Producto.stock_actual`.

`KardexService.registrar_movimiento()` sigue siendo la unica implementacion (grep
confirma 0 segundas implementaciones de escritura de stock fuera de
`inventario/services/business_service.py`). `empresa_id`, `sede_id`,
`documento_origen_*` presentes en cada movimiento generado por `confirmar_recepcion()`.

**Hallazgo real durante esta relectura:** el bug de atomicidad de `confirmar_recepcion()`
(F24-001, ver `F24_FINDINGS.md`) -- no estaba presente como regresion, sino que era un
defecto preexistente desde que F21 escribio el metodo, nunca antes ejercitado por un
escenario de fallo-a-mitad-de-loop.

## F24.3 — Traslados entre sedes

`TrasladoInventarioService.solicitar/aprobar/enviar/recibir()` confirmado sin
segunda implementacion. `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` confirmados **fuera**
de `ExtractorInventario._TIPOS_CONTABILIZABLES` (no generan `AsientoContable`),
verificado con test real end-to-end
(`test_f24_traslado_no_genera_asiento_contable_externo`): tras un traslado completo
Bogota->Barranquilla, `contabilizar_pendientes()` solo reporta 1 pendiente (el
`ENTRADA_AJUSTE` inicial), nunca los 2 movimientos de traslado.

## F24.4 — F22: Inventario -> Contabilidad (Pull)

`MovimientoInventario -> ExtractorInventario -> TransaccionEconomica -> Contabilizador
-> AsientoContable` confirmado end-to-end para `ENTRADA_COMPRA` (nuevo en esta
auditoria: F22 solo lo habia probado indirectamente via backfill dry-run, nunca con
un flujo de compra real completo hasta asiento en el mismo test) y `SALIDA_VENTA`
(ya probado por F23, reconfirmado). `_TIPOS_CONTABILIZABLES` y `_LINEAS_POR_TIPO`
revisados: ningun tipo nuevo, ninguna regla contable nueva creada por F24.

**Hallazgo real durante esta relectura:** `validadores.py`'s `validar_periodo_abierto()`
referenciaba `periodo.nombre` (inexistente) (F24-002).

## F24.5 — F23: Ventas -> Inventario -> Kardex -> Costo -> Contabilidad

`procesar_y_facturar_venta() -> _generar_salida_inventario() -> KardexService.registrar_movimiento()`
confirmado sin cambios de comportamiento. Servicios siguen sin generar movimiento
(`items.filter(producto__isnull=False)`). `Producto.costo_promedio` confirmado como
unica fuente de costo (grep: 0 usos de `precio_unitario`/`precio_venta` dentro de
`_generar_salida_inventario`).

## Conclusion

El circuito F21+F22+F23 sigue siendo el descrito en sus respectivos `_FINAL_REPORT.md`.
Los 2 defectos reales encontrados (F24-001, F24-002) eran preexistentes -- ninguno fue
introducido por trabajo posterior a F23 -- y ambos fueron expuestos precisamente por
construir escenarios E2E mas agresivos (multi-item con fallo a mitad de loop, periodo
cerrado real) que las fases anteriores no habian ejercitado.
