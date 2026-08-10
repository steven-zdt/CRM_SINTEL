# F22 — Baseline General

**Fecha:** 2026-08-09. Lectura obligatoria completada antes de tocar codigo: `MEMORY.md`,
`AGENTS.md`, `documentacion/arquitectura_general.md`, `F21_FINAL_REPORT.md`, `F21_BASELINE.md`,
`F21_RECEPCION_INVENTARIO.md`, `F21_ORGANIZATIONAL_DECISIONS.md`, `F21_TEST_MATRIX.md`,
`docs/ADR-001/003/004/005`, mas lectura directa de codigo real (`apps/tenant/inventario/`,
`apps/tenant/contabilidad/integracion/`).

Documentos detallados de esta auditoria:
- `documentacion/F22_INVENTARIO_BASELINE.md` — F22.1, superficie real de `MovimientoInventario`.
- `documentacion/F22_EXTRACTOR_INVENTARIO_BASELINE.md` — F22.3, por que `ExtractorInventario`
  retorna `[]` y que infraestructura ya existe y es reutilizable.
- `documentacion/F22_ACCOUNTING_CONTRACT.md` — F22.4-7, matriz de movimientos, reglas contables
  ya seedeadas, resolucion de tercero, documento origen, decision de traslados.

## Resumen ejecutivo

1. **`ExtractorInventario` esta deshabilitado deliberadamente** (`extraer_pendientes()` retorna
   `[]`), no es un bug — es la deuda que F21 documento y F22 cierra.
2. **El contrato ya existe casi completo**: `TipoTransaccion` (`dtos.py`) ya tiene los 5 valores
   de inventario; `seed_reglas_contables.py` ya tiene las `ReglaContable` seedeadas para 4 de los
   5. F22 no inventa un contrato nuevo, lo activa.
3. **`MovimientoInventario` ya tiene todo lo que Contabilidad necesita** (`empresa`, `producto`,
   `tipo`, `cantidad`, `costo_unitario`, `sede`, `id`) — no requiere cambios de modelo en
   `inventario`.
4. **`SALIDA_VENTA` no tiene datos reales hoy** — `ventas`/`facturas` no generan ese tipo de
   movimiento todavia (brecha preexistente, documentada, no resuelta por F22 — resolverla es una
   fase de Ventas, no de Inventario->Contabilidad).
5. **Traslados entre sedes quedan fuera de la contabilizacion** por decision confirmada (no
   representan transaccion economica externa), consistente con que ni `dtos.py` ni
   `seed_reglas_contables.py` los contemplan.
6. **Movimientos de `ActivoFijo`** (asignacion, mantenimiento, baja de activo) quedan fuera de
   alcance de F22 — dominio distinto (activos fijos, no mercancia/Kardex de `Producto`).

No se rehace F21. No se modifica `RecepcionCompra`, `RecepcionCompraItem`, `TrasladoInventario`,
`KardexService`, `StockPorSedeSelector` — F22 vive enteramente en
`apps/tenant/contabilidad/integracion/extractores/inventario.py` y su registro en
`extractores/__init__.py` / `backfill_contabilidad.py`.
