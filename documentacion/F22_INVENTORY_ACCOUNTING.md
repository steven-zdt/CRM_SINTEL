# F22 — Integracion Contable de Inventario (Pull)

**Fecha:** 2026-08-09

## 1. Flujo completo

```
Compras -> RecepcionCompra -> MovimientoInventario (ENTRADA_COMPRA)
                                        |
                                        | PULL (Contabilidad lee, Inventario no sabe quien lo lee)
                                        v
                              ExtractorInventario.extraer_pendientes()
                                        |
                                        v
                              TransaccionEconomica (DTO)
                                        |
                                        v
                                 Contabilizador.contabilizar()
                                        |
                                        v
                                  AsientoContable + MovimientoContable
```

`apps/tenant/inventario/` no importa `apps/tenant/contabilidad/` en ningun punto (verificado,
`F22_FINAL_REPORT.md` §Imports). Todo el trabajo nuevo de F22 vive en
`apps/tenant/contabilidad/integracion/extractores/inventario.py`.

## 2. Como ejecutar (produccion / operacion)

```bash
# Ver que se contabilizaria sin persistir nada
python manage.py backfill_contabilidad --extractores=inventario --dry-run

# Contabilizar realmente (idempotente, seguro de re-ejecutar)
python manage.py backfill_contabilidad --extractores=inventario

# Junto con los demas extractores existentes (comportamiento sin cambios, ahora incluye inventario)
python manage.py backfill_contabilidad
```

Prerequisitos por tenant (ver `F22_HISTORICAL_BACKFILL_ANALYSIS.md` §5): `ReglaContable`
seedeadas (`seed_reglas_contables`) y `PeriodoContable` abiertos para las fechas de los
movimientos (`seed_periodos_contables`).

## 3. Que se contabiliza y que no

Ver matriz completa en `F22_ACCOUNTING_CONTRACT.md` §1. Resumen: `ENTRADA_COMPRA`,
`SALIDA_VENTA`, `ENTRADA_AJUSTE`, `SALIDA_BAJA`, `SALIDA_CONSUMO`, `ENTRADA_DEVOLUCION` — todos
movimientos de `Producto` (no `ActivoFijo`). `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` (traslado entre
sedes) **nunca** generan asiento — es una transferencia interna, no una transaccion economica
externa.

## 4. Idempotencia

Cada `MovimientoInventario` (por su PK, `app_label='inventario'`, `modelo='MovimientoInventario'`)
puede generar como maximo 1 `AsientoContable` activo — reforzado por el mismo
`UniqueConstraint` que ya protegia a `AsientoContable` para el resto de extractores
(`gastos`, `facturas`, `nomina`), sin cambios al modelo. Verificado por test real
(`ExtractorInventarioTests::test_ejecutar_extractor_dos_veces_no_duplica_asiento`).

## 5. Limites de alcance (declarados, no ocultos)

- **`SALIDA_VENTA` no tiene datos reales hoy**: `ventas`/`facturas` no generan ese tipo de
  `MovimientoInventario` todavia (brecha preexistente a F22, ver `F22_INVENTARIO_BASELINE.md` §4).
  El mecanismo de extraccion/contabilizacion para `SALIDA_VENTA` esta completo y probado
  (`test_f22_extractor_inventario_mapping.py`), simplemente no tiene datos que procesar hasta que
  esa integracion se construya en una fase de Ventas.
- **Movimientos de `ActivoFijo`** (asignacion de responsable, mantenimiento, baja de activo) no
  se contabilizan — dominio distinto, fuera de alcance de F22.
- **Sin tarea Celery periodica**: la contabilizacion se dispara manualmente
  (`backfill_contabilidad`) o via el mismo mecanismo que ya usan `gastos`/`facturas`/`nomina` —
  no se crea infraestructura de workers nueva (ver `F22_FINAL_REPORT.md` §Celery).
- **`costo_unitario=0`**: un `MovimientoInventario` con costo cero produce un asiento vacio
  (rechazado por `AsientoNoCuadradoError`, aislado en `resultados['errores']`, no tumba el resto
  del batch) — es un problema de calidad de dato en el origen (KardexService lo permite por
  default), no un bug de la integracion contable.
