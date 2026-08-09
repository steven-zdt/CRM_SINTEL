# F21 — Recepcion de Compras -> Inventario

**Fecha:** 2026-08-09

## 1. Flujo implementado

```
OrdenCompra (APROBADA|PARCIAL)
    -> RecepcionCompra (BORRADOR)         [crear_recepcion]
         -> RecepcionCompraItem x N
    -> RecepcionCompra (CONFIRMADA)       [confirmar_recepcion]
         -> ItemOrdenCompra.cantidad_recibida += linea.cantidad_recibida
         -> MovimientoInventario(ENTRADA_COMPRA)  [via KardexService, si el
            item tiene item_inventario_uuid resoluble a un Producto real]
         -> OrdenCompra.estado -> PARCIAL | RECIBIDA
```

Archivos: `apps/tenant/compras/models.py` (`RecepcionCompra`,
`RecepcionCompraItem`, `ItemOrdenCompra.cantidad_recibida`,
`OrdenCompra.ESTADO_CHOICES` +`PARCIAL`), `apps/tenant/compras/services/
{crud_service,business_service,selectors,api_mixins}.py`
(`RecepcionCompra*`), `apps/tenant/compras/api/{serializers,viewsets,urls}.py`.

## 2. Por que OrdenCompra != Recepcion

Una orden puede recibirse en varios eventos (parciales o totales); cada
evento es su propia `RecepcionCompra` con sus propias lineas. El acumulado
vive en `ItemOrdenCompra.cantidad_recibida` (no en la orden ni en la
recepcion), con un `CheckConstraint` de BD
(`item_orden_compra_recibida_lte_cantidad`) como respaldo — nunca puede
quedar `cantidad_recibida > cantidad`.

## 3. Total vs. parcial (validado con test real)

Orden de 100 unidades:
- Recepcion #1 confirma 60 -> `cantidad_recibida=60`, orden `PARCIAL`.
- Recepcion #2 confirma 40 -> `cantidad_recibida=100`, orden `RECIBIDA`.
- Un tercer intento de crear una recepcion de 10 mas es **rechazado** en
  `crear_recepcion()` (antes de llegar a `confirmar`) con
  `error=cantidad_excede_pendiente`, HTTP 422 — no se llega a crear una
  tercera `RecepcionCompra` fantasma.

Ver `apps/tenant/compras/tests/test_f21_recepcion_compra.py::RecepcionParcialTests`.

## 4. Idempotencia (F21 §16)

Dos capas, mismo patron que `AsientoContable`/`Contabilizador`:

1. **Nivel recepcion:** `confirmar_recepcion()` hace
   `select_for_update()` sobre la `RecepcionCompra` y retorna
   inmediatamente (sin reprocesar) si ya esta `CONFIRMADA` — cubre doble
   click / retry HTTP normal.
2. **Nivel movimiento:** `MovimientoInventario` tiene
   `documento_origen_app='compras'`, `documento_origen_modelo=
   'RecepcionCompraItem'`, `documento_origen_id=<id de la linea>`, con
   `UniqueConstraint` condicional (`uniq_movimiento_documento_origen_tipo`,
   incluye `tipo` para permitir que un mismo documento origen genere dos
   tipos de movimiento distintos cuando aplica — ver traslados). Backstop
   real de BD para la condicion de carrera entre dos transacciones
   concurrentes.

`KardexService.registrar_movimiento()` fue extendido (no duplicado) con
`sede_id`/`documento_origen_*` opcionales — los llamadores existentes
(`registrar_entrada`, `registrar_salida`, `ajustar_stock`) no cambian de
comportamiento.

## 5. Item sin referencia a catalogo de inventario

`ItemOrdenCompra.item_inventario_uuid` puede apuntar a un `Producto`, a un
`Servicio`, o quedar vacio (item libre). Solo cuando resuelve a un
`Producto` real de la misma empresa se genera `MovimientoInventario` — en
cualquier otro caso la linea de recepcion sigue siendo valida
(`cantidad_recibida` se actualiza igual), simplemente sin efecto de stock.
Verificado por
`RecepcionSinReferenciaCatalogoTests::test_item_sin_producto_de_catalogo_no_genera_movimiento_pero_recepcion_es_valida`.

## 6. Limites de alcance (declarados, no ocultos)

- **`RecepcionCompra` CONFIRMADA es terminal.** `anular_recepcion()` solo
  opera en `BORRADOR`. Reversar una recepcion confirmada requeriria un
  movimiento compensatorio explicito — fuera de alcance de F21 (ver
  `F21_ORGANIZATIONAL_DECISIONS.md` §6).
- **Sin frontend/HTMX.** `RecepcionCompraViewSet` es API-only
  (`JSONRenderer`), sin `render-offcanvas/*`. Reduccion de alcance
  deliberada dado el volumen ya cubierto en backend+tests dentro de esta
  sesion.
- **Sin edicion de una recepcion BORRADOR** (agregar/quitar lineas despues
  de creada) — solo crear, confirmar, anular. Si se necesita corregir una
  recepcion en borrador, se anula y se crea una nueva.
