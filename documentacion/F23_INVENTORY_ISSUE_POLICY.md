# F23.5-6 — Politica de Salida de Inventario por Venta

**Fecha:** 2026-08-10

## 1. Evento disparador (F23.5)

**`VentaBusinessService.procesar_y_facturar_venta()`, en el momento exacto en que la venta pasa
de `BORRADOR` a `FACTURADA_DIAN`** (inmediatamente despues de
`VentaCRUDService.vincular_factura()`, dentro del mismo bloque `@transaction.atomic` que ya
envuelve todo el metodo).

**Por que no los otros candidatos del prompt maestro:**
- `VENTA_CONFIRMADA`: no existe ese estado — `Venta.Estado` solo tiene BORRADOR/FACTURADA_DIAN/ANULADA.
- `PEDIDO_DESPACHADO`/`ENTREGA_CONFIRMADA`: no existe ningun modelo de despacho/entrega en el
  codigo real (`F23_VENTAS_BASELINE.md` §2) — inventar uno seria crear infraestructura nueva no
  solicitada, violando la regla de no-duplicacion/no-invencion del prompt maestro.
- `FACTURA_EMITIDA` (evento DIAN real, no la sola creacion del registro `Factura`): es
  efectivamente el mismo momento que "Venta pasa a FACTURADA_DIAN" en el codigo actual — un solo
  metodo atomico hace ambas cosas. No hay una fase intermedia real que distinga "factura generada"
  de "venta facturada".

**Por que NO en `crear_venta_borrador()`:** una venta en BORRADOR es reversible/editable
(`actualizar_venta()` explicitamente lo permite solo en ese estado) y aun no genero ningun
documento fiscal — generar salida de inventario ahi crearia movimientos fantasma para ventas que
el usuario podria editar o nunca facturar.

## 2. Condiciones

- La venta debe estar transicionando realmente a `FACTURADA_DIAN` (no re-ejecutarse sobre una ya
  facturada — ver idempotencia, `F23_SALE_INVENTORY_CONTRACT.md` §3).
- Solo lineas (`ItemVenta`) con `producto_id` no nulo generan movimiento — servicios e items de
  texto libre se excluyen (`F23_VENTAS_BASELINE.md` §5).
- El producto debe existir, pertenecer a la empresa y estar activo (misma validacion que
  `KardexService.registrar_movimiento()` ya aplica — reutilizada, no duplicada).

## 3. Estado requerido

`Venta.estado` debe estar transicionando de `BORRADOR` a `FACTURADA_DIAN` en la misma llamada —
no existe un estado "listo para despachar" intermedio que evaluar.

## 4. Momento de la salida

Sincrono, dentro de la misma transaccion atomica que crea la Venta y la Factura. Si cualquier item
falla (ej. stock insuficiente), la transaccion completa se revierte — no queda una Venta
"facturada" sin su movimiento de inventario correspondiente, ni un movimiento sin su Venta.

## 5. Que sucede si se cancela (anula)

**No aplica un mecanismo nuevo**: `anular_venta()` rechaza estructuralmente cualquier venta ya
`FACTURADA_DIAN` (`F23_VENTAS_BASELINE.md` §2) — no existe ningun escenario real donde una venta
con movimiento de inventario ya generado pueda anularse por este camino. Documentado, no
implementado un reverso que no tiene forma de dispararse.

## 6. Que sucede si se factura

Es el evento mismo (ver §1) — no hay una fase posterior.

## 7. Que sucede si se devuelve

**DEFERRED** — `NotaCredito` no tiene lineas de producto/cantidad (`F23_FACTURAS_BASELINE.md`
§3), por lo que no hay de donde derivar un `ENTRADA_DEVOLUCION` por producto sin crear un modelo
nuevo (`ItemNotaCredito`), fuera del alcance minimo necesario para cerrar la brecha
`Venta->Inventario` que es la mision de F23. El mecanismo de `ENTRADA_DEVOLUCION` en si ya existe
y esta probado (F22) — falta unicamente el disparador real, documentado como brecha separada.

## 8. Politica de stock insuficiente (F23.6/F23.13)

**No se implementa una politica nueva — se reutiliza la existente de `KardexService.
registrar_movimiento()`**: para tipos de salida (`SALIDA_VENTA` incluido),
`producto.stock_actual < cantidad` lanza `ValidationError("Stock insuficiente...")`. Dado que la
generacion de movimientos ocurre dentro del `@transaction.atomic` de
`procesar_y_facturar_venta()`, esa excepcion revierte toda la operacion (venta + factura + XML +
firma + movimientos ya generados de items anteriores) — **rechazo atomico completo**, nunca una
venta facturada con stock negativo accidental. No se implementa "permitir negativo" ni "reservar"
— ninguna de las dos tiene soporte en el modelo actual (`Producto` no tiene campo de stock
reservado) y el prompt maestro prohibe explicitamente introducir ese concepto sin evidencia de
necesidad real.

## 9. Venta parcial / despacho parcial (F23.14/F23.21)

**No existe soporte de despacho parcial en el codigo actual** — `Venta`/`ItemVenta` no tienen
ningun campo de cantidad-despachada-vs-ordenada. Una venta facturada genera la salida de la
cantidad completa del item (`ItemVenta.cantidad`), sin excepcion, porque no hay ningun mecanismo
de entrega parcial que resolver. Documentado como limite del dominio actual, no inventado.
