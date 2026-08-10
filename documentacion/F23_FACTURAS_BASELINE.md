# F23.2 — Auditoria Real de Facturas (superficie relevante para F23)

**Fecha:** 2026-08-10. Metodo: lectura directa de `apps/tenant/facturas/models.py` y
`apps/tenant/facturas/services/business_service.py`.

## 1. `crear_factura_desde_venta(empresa, dto)` — confirmado, no se modifica

Recibe el DTO canonico UBL 2.1 construido por `VentaBusinessService._construir_dto_factura()`,
genera un numero provisional `BORR-VTA-{uuid8}` (hasta que la DIAN asigne el numero definitivo),
resuelve `Factura.sede` desde `dto["sede_id"]` con DSV (Sede debe pertenecer a la empresa, si no
se degrada a `None`). Este mecanismo es correcto y **no se toca en F23** — la mision del prompt
maestro es exclusivamente `Venta -> Inventario`, no `Venta -> Factura` (ya resuelto).

## 2. `ItemFactura` — soft-reference, NO se usa como fuente de F23

`ItemFactura.item_inventario_uuid` (UUID nullable, `help_text`: "Referencia soft, sin FK") — a
diferencia de `ItemVenta.producto`/`.servicio` (FK reales). Usar `ItemFactura` como fuente para
generar `MovimientoInventario` habria requerido resolver el UUID de vuelta a un `Producto` real
(un salto extra, mas fragil). **Decision: la fuente de verdad para F23 es `ItemVenta` (FK directa,
ya validada por `_dsv_items()` antes de llegar a Factura), no `ItemFactura`.** Consistente con la
regla arquitectonica del prompt maestro (§5): `Venta -> Inventario`, no `Factura -> Inventario`.

## 3. `NotaCredito` — hallazgo real que reduce el alcance de F23 (devoluciones)

`apps/tenant/facturas/models.py:683` — `NotaCredito` es **1:1 con `Factura`** (una nota credito
por factura) y es un **documento de solo cabecera**: `subtotal`/`impuestos`/`total`/`retefuente`/
`reteica`/`reteiva` a nivel de documento completo, `motivo` (texto libre),
`ref_factura_numero`/`ref_factura_cufe` (soft-reference a la factura original). **No existe
`ItemNotaCredito` ni ningun modelo de linea** — confirmado por grep (`class Item` en
`facturas/models.py` solo encuentra `ItemFactura`).

**Consecuencia real para F23.15/F23.28 (devoluciones):** no hay informacion de que producto ni
cuanta cantidad se devuelve — solo un monto total y un motivo en texto libre. Generar
`ENTRADA_DEVOLUCION` por producto requeriria **crear un modelo nuevo** (`ItemNotaCredito` o
equivalente) para capturar esa granularidad, lo cual el prompt maestro exige evitar salvo que sea
"imprescindible para cerrar la brecha" (§21) — la brecha que F23 debe cerrar es
`Venta->Inventario` (`SALIDA_VENTA`), no devoluciones. **Decision: devoluciones
(`ENTRADA_DEVOLUCION` desde `NotaCredito`) quedan `DEFERRED`**, documentadas explicitamente, no
implementadas — ver `F23_FINAL_REPORT.md` §Reducciones de alcance. El mecanismo de
`ENTRADA_DEVOLUCION` en si ya existe y esta probado desde F22 (mapeo DTO), solo falta el
disparador real desde Facturas/Ventas, igual que `SALIDA_VENTA` estaba antes de F23.

## 4. Estados de `Factura` — sin cambios, no se tocan

`BORRADOR` / `ENVIADA` / `ACEPTADA` / `RECHAZADA` / `ANULADA` (mas `EstadoPago` independiente) —
confirmado en sesiones anteriores (`F15_F20_FINAL_REPORT.md` §8), re-verificado sin cambios. F23
no modifica ningun estado de `Factura`.

## 5. Conclusion

F23 no requiere ningun cambio en `apps/tenant/facturas/` — ni en modelos, ni en
`crear_factura_desde_venta()`, ni en `ItemFactura`. Toda la implementacion vive en
`apps/tenant/ventas/services/business_service.py` (el disparo del movimiento) y
`apps/tenant/inventario/services/business_service.py` (reutilizando `KardexService`, sin
duplicar).
