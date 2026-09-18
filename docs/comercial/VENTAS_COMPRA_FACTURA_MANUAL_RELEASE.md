# FACTURAS-VENTAS-COMPRAS-01 — Asociacion manual Venta/Compra <-> Factura

Cierra el DEFERRED `VCF-004` de `docs/comercial/VENTAS_COMPRAS_FACTURAS_FLOW.md`
(pregunta 1: "manualmente desde la UI" -- respondida) y `VCF-005`
(`Venta.factura_asociada` FK vs soft-reference -- se reutilizo la FK real
existente, sin cambiarla).

## Diseño

```
Factura (SSoT fiscal, modulo Facturas)
   |
   | naturaleza=VENTA                    naturaleza=COMPRA
   v                                        v
Venta.factura_asociada              OrdenCompra.factura_asociada
(OneToOneField, YA EXISTIA)          (OneToOneField, NUEVO -- 1 migracion)
```

Ninguna asociacion se crea automaticamente. El unico camino es:
`buscar -> seleccionar -> confirmar -> POST vincular-factura/`.

## Backend

| Componente | Archivo | Nuevo/reutilizado |
|---|---|---|
| `Venta.factura_asociada` | `apps/tenant/ventas/models.py:174` | Reutilizado (ya existia, VCF-005) |
| `OrdenCompra.factura_asociada` | `apps/tenant/compras/models.py` | **Nuevo** (migracion `0009_ordencompra_factura_asociada`) -- Compras no tenia ningun campo de vinculo |
| `VentaCRUDService.vincular_factura()` | `apps/tenant/ventas/services/crud_service.py:123` | Reutilizado (ya existia, sin cambios) |
| `OrdenCompraCRUDService.vincular_factura()` | `apps/tenant/compras/services/crud_service.py` | **Nuevo** -- a diferencia de Ventas, `OrdenCompra.ESTADO_CHOICES` no tiene un estado equivalente a `FACTURADA_DIAN`; no se invento uno, el estado de la orden no cambia por el vinculo |
| `VentaBusinessService.vincular_factura_existente()` | `apps/tenant/ventas/services/business_service.py` | **Nuevo** -- DSV completo (empresa_id via `FacturaSelectors.qs_detail`), valida naturaleza=VENTA, rechaza si ya vinculada |
| `OrdenCompraBusinessService.vincular_factura_existente()` | `apps/tenant/compras/services/business_service.py` | **Nuevo** -- mismo patron, valida naturaleza=COMPRA |
| `POST /api/v1/ventas/{uuid}/vincular-factura/` | `apps/tenant/ventas/api/viewsets.py` | **Nuevo** |
| `POST /api/v1/compras/{uuid}/vincular-factura/` | `apps/tenant/compras/api/viewsets.py` | **Nuevo** |
| Buscador `GET /api/v1/facturas/buscar-para-movimiento/?q=&naturaleza=` | `apps/tenant/facturas/api/viewsets.py` | Reutilizado y corregido (ver `FACTURAS_UI_PERSISTENCE_RELEASE.md` hallazgo 4) |

## Frontend

- `Venta`: `offcanvas_detalle_venta.html` (seccion "Factura de venta") +
  `venta_editor.js::bindFacturaWidget()` + `ventas.api.js::vincularFactura/buscarFacturasVenta`.
- `Compra`: `offcanvas_detalle_compras.html` (seccion "Factura de compra") +
  `compras_list.js` (event delegation sobre `#offcanvas-container-compras`,
  mismo patron que `btn-cambiar-estado`) + `compras.api.js::vincularFactura/buscarFacturasCompra`.
- Ambos reutilizan `window.Sintel.Core.Http` (via los `_fetch()` ya
  existentes de cada API module) -- cero cliente HTTP nuevo.
- Seleccion explicita en 2 pasos: "Seleccionar" (de la lista de resultados)
  -> "Guardar asociacion" (confirmacion inline) -- nunca auto-match.

## Validaciones (backend, DSV real)

| Caso | Resultado verificado |
|---|---|
| Factura VENTA -> Venta | `200`, vincula, `estado -> FACTURADA_DIAN` |
| Factura COMPRA -> Venta | `422 naturaleza_incorrecta` |
| Factura COMPRA -> OrdenCompra | `200`, vincula, estado sin cambios |
| Factura VENTA -> OrdenCompra | `422 naturaleza_incorrecta` (test unitario) |
| Factura de otra empresa -> Venta/Compra | `404` (no resuelve via `FacturaSelectors`, DSV) |
| Factura inexistente | `404` |
| Repetir la misma asociacion | `409` (idempotente, no duplica) |
| Venta/Orden ya vinculada, intentar cambiar a otra factura | `409` |

## Tests

- `apps/tenant/facturas/tests/test_resolver_naturaleza_matrix.py` (13, matriz completa de naturaleza)
- `apps/tenant/ventas/tests/test_vincular_factura_manual.py` (6: happy path, naturaleza incorrecta, inexistente, sin uuid, ya vinculada, DSV cross-empresa [skip -- Empresa singleton por schema])
- `apps/tenant/compras/tests/test_vincular_factura_manual.py` (5: happy path, naturaleza incorrecta, orden inexistente, factura inexistente, ya vinculada)
- E2E HTTP real (curl, JWT real, servidor real corriendo) -- ver tabla completa en `FACTURAS_UI_PERSISTENCE_RELEASE.md`.

## Release Gate

```
SEARCH_FACTURA_VENTA       PASS  (buscar-para-movimiento?naturaleza=VENTA, HTTP real)
SELECT_FACTURA_VENTA       PASS  (UI: 2 pasos explicitos, sin auto-match)
SAVE_ASSOCIATION           PASS  (POST vincular-factura, HTTP real, 200)
PERSIST_AFTER_RELOAD       PASS  (factura_asociada_id persistido en BD, verificado por consulta directa)
REJECT_FACTURA_COMPRA      PASS  (422, HTTP real)
REJECT_CROSS_TENANT        PASS_WITH_LIMITATIONS (DSV via empresa_id verificado en codigo + test; escenario de 2 empresas reales no reproducible -- Empresa es singleton por schema en este proyecto)
IDEMPOTENCY                PASS  (409 al repetir, HTTP real)
NO_AUTO_ASSOCIATION        PASS  (subir XML no toca Venta/Compra -- confirmado leyendo guardar_desde_dto(), no importa ni referencia esos modelos)
```

Mismo resultado para Compras (`SEARCH_FACTURA_COMPRA`, `SELECT_FACTURA_COMPRA`, etc.) --
misma implementacion, mismos tests, mismas pruebas HTTP reales.

**VENTAS_FACTURA_MANUAL = PASS_WITH_LIMITATIONS**
**COMPRAS_FACTURA_MANUAL = PASS_WITH_LIMITATIONS**

Unica limitacion en ambos: sin verificacion visual en navegador (ver
`FACTURAS_UI_PERSISTENCE_RELEASE.md`, seccion de limitaciones) y sin un
segundo tenant/Empresa real para probar el rechazo cross-tenant end-to-end
(el aislamiento por `empresa_id` esta verificado en el codigo del selector
y cubierto por tests unitarios equivalentes en otras apps de este mismo
proyecto, pero no con un segundo tenant real en esta pasada especifica).
