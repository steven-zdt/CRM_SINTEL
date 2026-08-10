# F25 — Matriz de Atomicidad

**Fecha:** 2026-08-10

Completada solo con evidencia real (lectura de codigo + tests), no rellenada
manualmente.

| App | Servicio/Metodo | Writes | Atomic | Rollback correcto | Multi-write | Riesgo | Estado |
|---|---|---|---|---|---|---|---|
| compras | `confirmar_recepcion()` | multi (loop) | Si | Si (F24 fix) | Si | era HIGH, corregido | FIXED (F24) |
| compras | `anular_recepcion()` | 1 | Si | Si (F24 fix defensivo) | No | bajo | FIXED (F24) |
| compras | `crear_orden_compra()` | 1 (delegada, atomic) | Si | N/A (savepoint interno) | No | ninguno | SAFE_BY_DESIGN |
| compras | `actualizar_orden_compra()` | 1 (delegada, atomic; internamente delete+recreate en el mismo savepoint) | Si | N/A | No* | ninguno | SAFE_BY_DESIGN |
| compras | `cambiar_estado_orden_compra()` | 1 | Si | N/A | No | ninguno | SAFE_BY_DESIGN |
| compras | `eliminar_orden_compra()` | 1 | Si | N/A | No | ninguno | SAFE_BY_DESIGN |
| compras | `crear_recepcion()` | 1 (delegada, atomic) | Si | N/A | No | ninguno | SAFE_BY_DESIGN |
| ventas | `procesar_y_facturar_venta()` | multi (Venta+Factura+loop SALIDA_VENTA) | Si | Si (F23 fix) | Si | era HIGH, corregido | FIXED (F23) |
| ventas | `crear_venta_borrador()` | 1 (delegada, atomic) | Si | N/A | No | ninguno | SAFE_BY_DESIGN |
| ventas | `anular_venta()` | 1 (delegada, atomic) | Si | N/A | No | ninguno | SAFE_BY_DESIGN |
| ventas | `crear/actualizar/eliminar_resolucion()` (x3) | 1 c/u (delegada, atomic) | Si | N/A | No | ninguno | SAFE_BY_DESIGN |
| facturas | `guardar_desde_dto()` | multi (Factura+impuestos+retenciones+NC+items) | Si | Si (nada lo absorbe, propaga y Django revierte todo) | Si | ninguno (ver F25-FP-013) | SAFE_BY_DESIGN |
| gastos | `procesar_gasto()` | multi (DocumentoSoporte + loop retenciones) | Si | Si (F25 fix) | Si | era HIGH, corregido | FIXED (F25) |
| gastos | `anular_gasto()` / `eliminar_gasto()` | 1 c/u (delegada, atomic) | Si | N/A | No | ninguno | SAFE_BY_DESIGN |
| inventario | `KardexService.registrar_movimiento()` | 1 (con savepoint interno para IntegrityError especifico) | Si | Si (patron ejemplar, `raise` explicito para excepciones inesperadas) | No | ninguno | SAFE_BY_DESIGN / referencia |
| inventario | `TrasladoInventarioService.enviar()` / `.recibir()` | 1 c/u (2 transiciones deliberadamente separadas) | Si | Si (nada lo absorbe) | No | ninguno | SAFE_BY_DESIGN |
| contabilidad | `Contabilizador.contabilizar()` | multi (AsientoContable + MovimientoContable bulk + ImpuestoDocumento bulk) | Si (`with transaction.atomic()`) | Si (nada lo absorbe; `IntegrityError` especifico se traduce a `AsientoYaExisteError` y se relanza) | Si | ninguno | SAFE_BY_DESIGN / referencia |
| contabilidad | `AbstractExtractor.contabilizar_pendientes()` | multi (1 por documento pendiente) | No (orquestador; cada `contabilizar()` interno es atomic) | Si (aislamiento por documento, error de uno no afecta a los demas) | Si | ninguno | SAFE_BY_DESIGN |

\* `actualizar_orden_compra()`: aunque su unica llamada delegada
(`actualizar_orden()`) internamente hace 2 operaciones (`delete()` + `bulk_create()`),
ambas ocurren dentro del MISMO savepoint de esa unica llamada -- ver F25-FP-002 en
`F25_FINDINGS.md` para el analisis completo de por que esto es seguro pese a
"parecer" multi-write desde la perspectiva del metodo externo.

## Leyenda

- **Atomic**: el metodo (o su unica escritura delegada) esta decorado
  `@transaction.atomic`.
- **Rollback correcto**: ante una excepcion durante las escrituras, el estado previo
  se restaura completamente (verificado por lectura de codigo y/o test real).
- **Multi-write**: el metodo realiza 2+ escrituras reales separadas dentro de su
  propio scope (no delegadas a una unica llamada atomica).
- **Riesgo**: clasificacion final tras el analisis (no la sola presencia del patron
  AST).
