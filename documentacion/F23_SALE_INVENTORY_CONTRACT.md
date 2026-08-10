# F23 — Contrato Venta -> Inventario

**Fecha:** 2026-08-10

## 1. Flujo

```
VentaBusinessService.procesar_y_facturar_venta()
    -> VentaCRUDService.crear_venta()               (BORRADOR, existente, sin cambios)
    -> FacturaBusinessService.crear_factura_desde_venta()  (existente, sin cambios)
    -> VentaCRUDService.vincular_factura()           (BORRADOR -> FACTURADA_DIAN, existente)
    -> [NUEVO] generar_salida_inventario_por_venta(venta, empresa_id, sede_id)
           -> por cada ItemVenta con producto_id:
                KardexService.registrar_movimiento(
                    tipo=SALIDA_VENTA, sede_id=sede_id,
                    documento_origen_app='ventas', documento_origen_modelo='ItemVenta',
                    documento_origen_id=item.id,
                )
    -> return (True, venta, 201)
```

Todo dentro del mismo `@transaction.atomic` que ya envuelve `procesar_y_facturar_venta()` — no se
agrega una segunda transaccion ni un `try/except` que oculte fallos: si un item falla (stock
insuficiente, producto inactivo), la excepcion se propaga y toda la operacion se revierte
(comportamiento correcto: no debe existir una Venta `FACTURADA_DIAN` sin su salida de inventario
real).

## 2. Donde vive el codigo nuevo (Service Layer, sin excepciones)

- `apps/tenant/ventas/services/business_service.py` — nuevo metodo estatico
  `VentaBusinessService._generar_salida_inventario(venta, items_data_resueltos, empresa_id,
  sede_id)`, llamado desde `procesar_y_facturar_venta()` antes del `return`. Import local de
  `KardexService` (cross-app read/write hacia `inventario`, mismo patron de import local ya
  establecido en todo el proyecto para evitar acoplamiento a nivel de modulo).
- **No se crea** `VentaInventoryService`, `SaleInventoryService`, `InventarioBridge`,
  `KardexVentaService` ni ningun servicio nuevo — se reutiliza `KardexService.
  registrar_movimiento()` directamente, igual patron que F21 uso desde `compras` (
  `RecepcionCompraBusinessService.confirmar_recepcion()` llama a `KardexService.
  registrar_movimiento()` directamente, sin un bridge intermedio).

## 3. Idempotencia

`documento_origen_app='ventas'`, `documento_origen_modelo='ItemVenta'`,
`documento_origen_id=item.id` — un `ItemVenta` no puede generar mas de 1 `MovimientoInventario`
activo (mismo `UniqueConstraint` de `MovimientoInventario` que F21 ya establecio,
`uniq_movimiento_documento_origen_tipo`, sin cambios de modelo). Se eligio `ItemVenta` (no
`Venta`) como documento origen porque la granularidad real es por linea (F23.11/multi-item) —
mismo criterio que F21 uso `RecepcionCompraItem`, no `RecepcionCompra`, como documento origen de
cada `MovimientoInventario`.

`procesar_y_facturar_venta()` en si ya es una operacion de creacion (no de re-ejecucion sobre una
Venta existente) — no hay un escenario real de "volver a facturar la misma Venta dos veces" en el
codigo actual (no existe un endpoint que reintente sobre una Venta ya `FACTURADA_DIAN`). La
proteccion de idempotencia real y verificada por test es a nivel de `KardexService.
registrar_movimiento()` (retry/doble-click a nivel de infraestructura HTTP/Celery), no a nivel de
"volver a facturar".

## 4. Multi-item

Un `MovimientoInventario` por cada `ItemVenta` con `producto_id` no nulo — sin agregacion (si dos
lineas referencian el mismo `Producto`, se generan 2 movimientos independientes, cada uno
trazable a su propio `ItemVenta.id`). Items con `servicio_id` (o ninguno de los dos FK) se
excluyen sin generar movimiento ni error.

## 5. Sede

`sede_id` — el mismo parametro que `procesar_y_facturar_venta(empresa, payload, sede_id)` ya
recibe (resuelto por el caller via `OrganizationalContext.resolve(request).sede_id`, ver
`F23_VENTAS_BASELINE.md` §3) — no se re-deriva, no se acepta del payload del cliente. Puede ser
`None` (sin contexto organizacional resoluble); `MovimientoInventario.sede` ya es nullable
(`SET_NULL`) para exactamente este caso, sin cambios de modelo.

## 6. Costo del movimiento (F23.19/F23.20)

**`producto.costo_promedio`** (campo ya existente en `Producto`, `apps/tenant/inventario/models.py:160`)
— **nunca** `ItemVenta.precio_unitario` (precio de venta al cliente, no costo de inventario).
Hallazgo real verificado: `costo_promedio` es un campo estatico, poblado manualmente o por
ingesta CSV (`ingesta_service.py`), **nunca recalculado automaticamente** por `ENTRADA_COMPRA` ni
ningun otro movimiento — no es un costo promedio ponderado real, es el mejor costo de referencia
disponible en el modelo actual. Implementar costeo FIFO/promedio-ponderado-real seria un metodo
contable nuevo sin evidencia de que el prompt maestro lo exija — no se hace (F23.19 lo prohibe
explicitamente sin esa evidencia).

## 7. Contabilidad (Pull, sin cambios)

`SALIDA_VENTA` ya esta contemplado por `TipoTransaccion.SALIDA_INVENTARIO_VENTA` y por las
`ReglaContable` seedeadas en F22 (`COSTO_VENTA_PRODUCTO`/`INVENTARIO_PRODUCTO`) y por
`ExtractorInventario._TIPOS_CONTABILIZABLES` (ya incluye `SALIDA_VENTA` desde F22, sin datos
reales hasta ahora). **F23 no modifica `apps/tenant/contabilidad/` en absoluto** — el
`ExtractorInventario` ya construido en F22 detectara estos movimientos nuevos automaticamente
la proxima vez que se ejecute `backfill_contabilidad`, sin ningun cambio de codigo.

## 8. Limites de alcance (DEFERRED, documentados)

- Devoluciones (`ENTRADA_DEVOLUCION` desde `NotaCredito`) — `NotaCredito` no tiene lineas de
  producto (`F23_FACTURAS_BASELINE.md` §3).
- Anulacion con reverso de inventario — no aplica, la maquina de estados ya lo impide
  (`F23_INVENTORY_ISSUE_POLICY.md` §5).
- Despacho/entrega parcial — no existe ese concepto en el modelo (`F23_INVENTORY_ISSUE_POLICY.md` §9).
- Reserva de stock — no existe ese concepto en el modelo, no se introduce.
