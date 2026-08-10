# F22.1 — Auditoria Real de Inventario (superficie relevante para Contabilidad)

**Fecha:** 2026-08-09. Metodo: lectura directa de codigo (`apps/tenant/inventario/models.py`,
`services/business_service.py`, `services/selectors.py`), no de documentacion previa.

## 1. `MovimientoInventario` — campos relevantes (post-F21)

`apps/tenant/inventario/models.py:237-367`. Hereda `TimeStampedModel(SintelTenantBaseModel)`
(`empresa`, `created_at`, `updated_at`).

| Campo | Tipo | Nota para F22 |
|---|---|---|
| `uuid` | UUID | Identificador publico, no usado como documento_origen (se usa `id`, igual patron que `AsientoContable`) |
| `producto` | FK `Producto`, nullable | Mutuamente excluyente con `activo_fijo` (`CheckConstraint exactly_one_product_or_asset`). **F22 solo contabiliza movimientos con `producto` no nulo** — los de `activo_fijo` (ASIGNACION_RESPONSABLE, TRASLADO_MANTENIMIENTO, RETORNO_MANTENIMIENTO, SALIDA_BAJA_ACTIVO) quedan fuera de alcance (ver `F22_ACCOUNTING_CONTRACT.md` §5) |
| `activo_fijo` | FK `ActivoFijo`, nullable | Fuera de alcance F22 (ver arriba) |
| `tipo` | CharField, `TipoMovimiento.choices` | Ver matriz completa en `F22_ACCOUNTING_CONTRACT.md` §1 |
| `cantidad` | Decimal(14,3) | Siempre positivo (el signo lo da `tipo`, no `cantidad`) |
| `costo_unitario` | Decimal(14,2), default 0 | **Riesgo real de dato**: el default es `0` y `KardexService.registrar_movimiento()` no lo exige — un movimiento historico o uno registrado sin costo produce `monto=0` en la linea contable, lo que dispara `AsientoNoCuadradoError` (asiento vacio) al intentar contabilizarlo. No es un bug de F22: es el estado real de los datos. El extractor debe aislar este caso por documento (no debe tumbar el batch completo) — ver `F22_ACCOUNTING_CONTRACT.md` §6 |
| `sede` | FK `empresa.Sede`, nullable, `SET_NULL` | Informativo (DT-SEDE-05 + F21). **No se propaga a `AsientoContable`** — el modelo contable no tiene campo `sede` (ver decision en `F22_ACCOUNTING_CONTRACT.md` §8) |
| `documento_origen_app` / `_modelo` / `_id` | F21 | Soft-reference al documento que origino el MOVIMIENTO (`compras.RecepcionCompraItem`, `inventario.TrasladoInventario`), NO es el documento origen que Contabilidad debe usar — ver §3 abajo |
| `factura_uuid` / `factura_numero` | Soft-reference pre-F21 | Solo poblado si el movimiento vino de una venta facturada; no usado por SALIDA_VENTA hoy (`ventas`/`facturas` no llaman a `KardexService` — ver hallazgo §4) |
| `origen_referencia` / `cliente_referencia` | CharField libre | Texto libre, no estructurado — no sirve como FK para resolver un tercero real |

## 2. Tipos de movimiento existentes (`TipoMovimiento`, `models.py:238-251`)

```
ENTRADA_COMPRA, ENTRADA_AJUSTE, ENTRADA_DEVOLUCION        (TIPOS_ENTRADA)
SALIDA_VENTA, SALIDA_BAJA, SALIDA_CONSUMO                 (TIPOS_SALIDA)
TRASLADO_SALIDA, TRASLADO_ENTRADA                         (TIPOS_TRASLADO, F21)
ASIGNACION_RESPONSABLE, TRASLADO_MANTENIMIENTO,
RETORNO_MANTENIMIENTO, SALIDA_BAJA_ACTIVO                 (_TIPOS_ACTIVO — ActivoFijo, fuera de alcance)
```

Confirmado por lectura directa de `KardexService` (`services/business_service.py:48-65`) — no hay
tipos adicionales sin usar en el enum.

## 3. Documento origen real para Contabilidad — NO es el `documento_origen_*` de F21

Hallazgo de diseno (no un bug): los campos `documento_origen_app/modelo/id` que F21 agrego a
`MovimientoInventario` identifican de DONDE VINO el movimiento (para la idempotencia interna de
Inventario — ej. que una `RecepcionCompraItem` no genere dos `ENTRADA_COMPRA`). Para Contabilidad,
el "documento origen" del asiento debe ser el **propio `MovimientoInventario`**
(`app_label='inventario'`, `modelo='MovimientoInventario'`, `id=<pk>`) — exactamente el mismo
patron que `ExtractorGastos` usa `DocumentoSoporte` (no lo que origino el `DocumentoSoporte`) y
`ExtractorNomina` usa `Devengo` (no lo que origino el `Devengo`). Ver `F22_ACCOUNTING_CONTRACT.md`
§4 para el contrato completo.

## 4. Hallazgo real: `SALIDA_VENTA` no se genera hoy en ningun flujo real

Grep de `KardexService.registrar_salida\|TipoMovimiento.SALIDA_VENTA` fuera de
`apps/tenant/inventario/` = **0 resultados** en `ventas`/`facturas`. Ni `ventas.Venta` ni
`facturas.Factura` llaman a `KardexService` para descargar stock ni generar `MovimientoInventario`.
Esto significa: **hoy no existen movimientos `SALIDA_VENTA` reales en produccion** — el extractor
que F22 implementa para este tipo es correcto y funcional, pero no tiene datos que consumir hasta
que `ventas`/`facturas` generen la salida real (brecha ya documentada en
`F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.6/§F18.11 y en `F15_F20_FINAL_REPORT.md` §12 — no es nueva
de F22, ni se resuelve aqui: implementar esa integracion es una fase de Ventas/Facturas, fuera del
alcance de F22, que es especificamente Inventario->Contabilidad).

## 5. Movimientos generados por F21 (los unicos con datos reales garantizados)

- `ENTRADA_COMPRA` — via `RecepcionCompraBusinessService.confirmar_recepcion()`, con
  `costo_unitario=item_oc.valor_unitario` (siempre > 0, viene de `ItemOrdenCompra`), `sede_id`
  poblado, `documento_origen_modelo='RecepcionCompraItem'`.
- `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` — via `TrasladoInventarioService`, sin `costo_unitario`
  (no se pasa, queda en default `0`) — irrelevante para Contabilidad porque estos 2 tipos quedan
  fuera de extraccion (ver `F22_ACCOUNTING_CONTRACT.md` §5).
- `ENTRADA_AJUSTE`/`SALIDA_BAJA` — via `KardexService.ajustar_stock()`, sin `costo_unitario`
  explicito (usa el default `0` salvo que el llamador lo pase) — mismo riesgo de dato que §1.

## 6. Selectors/API relevantes

`MovimientoInventarioSelector.get_list()`/`get_detail()` — read-only, ya usados por el ViewSet;
F22 no los reutiliza (el extractor consulta el modelo directamente, mismo patron que
`ExtractorGastos`, que tampoco pasa por los selectors de `gastos`).

## 7. Conclusion

No hay nada que modificar en `apps/tenant/inventario/` para F22 — los campos que Contabilidad
necesita (`empresa`, `producto`, `tipo`, `cantidad`, `costo_unitario`, `sede`, `created_at`, `id`)
ya existen, todos poblados por el flujo real de F21 para `ENTRADA_COMPRA`. La totalidad de F22 vive
en `apps/tenant/contabilidad/integracion/extractores/inventario.py` (Pull), consistente con la
regla arquitectonica: Inventario no sabe quien consume sus movimientos.
