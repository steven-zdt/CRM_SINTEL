# F23.1 — Auditoria Real de Ventas

**Fecha:** 2026-08-10. Metodo: lectura directa de `apps/tenant/ventas/models.py`,
`services/business_service.py`, `services/crud_service.py`, `services/api_mixins.py`.

## 1. Modelos

`Venta(SintelTenantBaseModel)` — **sin `SedeAwareModel`, sin campo `sede` propio.**
`Estado`: `BORRADOR` / `FACTURADA_DIAN` / `ANULADA` (3 estados, sin "CONFIRMADA" ni "DESPACHADA").
`cliente` FK real (`PROTECT`), `factura_asociada` `OneToOneField` a `facturas.Factura`
(`SET_NULL`). Totales: `subtotal`, `impuestos`, `total_neto`.

`ItemVenta(SintelTenantBaseModel)` — `producto`/`servicio` son **FK reales** (no soft-reference
UUID como en `compras.ItemOrdenCompra`), ambos nullable, sin `CheckConstraint` de exclusividad
(pueden venir ambos vacios — item de texto libre). `cantidad`, `precio_unitario`, `subtotal`
(calculado en `save()`).

## 2. Ciclo de vida real (unico camino que muta estado)

```
crear_venta_borrador()          -> Venta(BORRADOR), sin Factura, sin efecto en inventario
procesar_y_facturar_venta()     -> Venta(BORRADOR) -> ... -> Venta(FACTURADA_DIAN)
anular_venta()                  -> Venta(BORRADOR) -> Venta(ANULADA). RECHAZA si ya FACTURADA_DIAN
                                    ("Una venta facturada no puede anularse directamente.
                                    Emita nota credito.") -- ValueError real, no una suposicion.
```

**Hallazgo critico para F23.5:** el UNICO metodo que transiciona `Venta.estado` a
`FACTURADA_DIAN` es `VentaBusinessService.procesar_y_facturar_venta()` — construye el DTO
canonico UBL 2.1, genera CUFE/XML/firma, delega `FacturaBusinessService.crear_factura_desde_venta()`,
y al final (`VentaCRUDService.vincular_factura()`) cambia el estado. No existe ningun concepto de
"despacho" o "entrega" en el modelo — 0 campos, 0 estados, 0 servicio relacionado.

**Hallazgo critico para F23.16 (anulaciones):** dado que `anular_venta()` **rechaza
estructuralmente** cualquier venta ya `FACTURADA_DIAN`, y el movimiento de inventario solo puede
generarse en el momento de facturacion (ver arriba), **no existe ningun escenario real en el
codigo actual donde una venta con `MovimientoInventario` ya generado pueda anularse.** No hay
"movimiento compensatorio por anulacion" que implementar — la maquina de estados ya lo impide.

## 3. Resolucion de sede — confirmado: dato de contexto, no de scoping

`VentaServiceMixin.service_procesar_y_facturar()` resuelve `sede_id =
OrganizationalContext.resolve(self.request).sede_id` (con fallback a `None` si no hay contexto
resoluble) y lo pasa como **parametro explicito** a `procesar_y_facturar_venta(empresa, payload,
sede_id)`. `Venta` no tiene campo `sede` — el `sede_id` viaja como dato plano dentro del DTO hacia
`Factura.sede` (con DSV: solo se asigna si la Sede realmente pertenece a la empresa, si no se
degrada a `None` silenciosamente — ver `crear_factura_desde_venta()`,
`apps/tenant/facturas/services/business_service.py:104-114`). Mismo patron que compras usa para
defaultear un registro nuevo (OCF Fase 9/F10), via `OrganizationalContext` (la sede ACTIVA de
quien opera), no `OrganizationalScope`.

## 4. Multi-item — confirmado, sin agregacion previa

`ItemVenta[]` es una relacion 1:N real (`related_name="items"`). No existe ningun mecanismo de
agregacion por producto — cada `ItemVenta` es una linea independiente, incluso si dos lineas
referencian el mismo `Producto`.

## 5. Productos no inventariables

`ItemVenta.producto_id` es `None` cuando la linea es un `Servicio` o un item de texto libre —
distincion ya disponible sin necesidad de logica nueva: `if item.producto_id:` basta para excluir
servicios/lineas libres de cualquier movimiento de inventario.

## 6. Stock insuficiente — sin politica propia, delega a KardexService existente

`ventas` no tiene ninguna logica de validacion de stock hoy (no genera movimientos). No hay
"reserva" ni concepto de "stock disponible vs fisico" en el modelo.

## 7. Tests existentes

`apps/tenant/ventas/tests/`: `test_multitenant_isolation.py` (patron `tenant1`/`tenant2`, ya
establecido), `test_organizational_context_adoption.py`. `conftest.py` ya expone `tenant1`/
`tenant2` (mismo fixture reutilizable en F23).

## 8. Conclusion

El punto de integracion correcto es **`VentaBusinessService.procesar_y_facturar_venta()`**, justo
despues de `VentaCRUDService.vincular_factura()` (Paso 6 del metodo existente), dentro del mismo
bloque `@transaction.atomic` que ya envuelve todo el metodo — si un item falla por stock
insuficiente, toda la venta+factura+movimientos se revierte atomicamente (comportamiento correcto
gratis, sin logica adicional). No se toca `crear_venta_borrador()` ni `anular_venta()`.
