# Baseline — Sincronización Facturas ↔ Ventas

**Plan ejecutado:** `apps/tenant/ventas/.agent/PLAN_SINCRONIZACION_FACTURAS_VENTAS_FASES.md`
**Fecha:** 2026-09-18

STATUS: PASS

## FASE 0 — Inspección del código real

| Elemento buscado | Hallazgo real |
|---|---|
| `Venta.factura_asociada` | `OneToOneField(Factura, null=True, blank=True, related_name="venta_origen")` — `apps/tenant/ventas/models.py`. `related_name="venta_origen"` es la barrera estructural anti-duplicado (una Factura solo puede tener UNA Venta). |
| `VentaCRUDService.vincular_factura()` | Existe (`apps/tenant/ventas/services/crud_service.py`) — persiste `venta.factura_asociada` y sincroniza `estado`. Reutilizado sin cambios por `crear_venta_desde_factura()` y `sincronizar_una()`. |
| `vincular-factura` (endpoint manual) | `POST /api/v1/ventas/{uuid}/vincular-factura/` — `VentaViewSet.vincular_factura` (viewsets.py:179). Vinculación manual 1-a-1 desde una Venta ya existente. La nueva funcionalidad NO reemplaza esto, opera en paralelo (descubrimiento masivo). |
| `buscar-para-movimiento` | `GET /api/v1/facturas/buscar-para-movimiento/?naturaleza=VENTA` — buscador libre por texto, SIN exclusión server-side de ya vinculadas ni paginación orientada a "pendientes". Insuficiente para FASE 4 (ver FASE 3 más abajo) — se creó un selector dedicado en vez de forzar este endpoint a un caso de uso distinto. |
| `venta_editor.js` / `venta_list.js` | Ya contienen el autorrelleno FST-375 (`autorrellenarDesdeFactura`) y el refresh de tabla (`venta-updated` en `body`). Reutilizados: el nuevo panel dispara el mismo evento `venta-updated` tras vincular. |
| `list_ventas.html` | Toolbar con `Nueva Venta` / `Resoluciones DIAN` / `Actualizar` — botón nuevo insertado en el mismo grupo. |
| `naturaleza` | `Factura.Naturaleza.VENTA` / `.COMPRA` (choices en `apps/tenant/facturas/models.py`). |
| `tipo` | `Factura.TipoFactura.FE` (factura electrónica) — se exige explícitamente para elegibilidad (excluye notas crédito/débito, que son otro `tipo`). |
| `empresa_id` | Presente y obligatorio en `Factura` y `Venta`; todo el flujo nuevo filtra por él (DSV). |
| `related_name` Factura→Venta | `venta_origen` (ver arriba). `hasattr(factura, "venta_origen")` es el chequeo canónico de "ya vinculada" usado en `sincronizar_una()`. |
| Serializers | `FacturaListSerializer`/`FacturaDetailSerializer` ya exponen `LIST_FIELDS`/`DETAIL_FIELDS` reutilizados tal cual por el selector nuevo (`qs_pendientes_sincronizacion_venta`, `.only(*LIST_FIELDS)`). |
| Permisos | `VentaViewSet.permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]` — se heredan sin cambios en las dos acciones nuevas (no se relajó ni endureció nada). |

## FASE 1 — Definición de "sincronizada"

- **Sincronizada:** `Factura.naturaleza == VENTA` y existe `Venta` tal que `venta.factura_asociada_id == factura.id` (accesible como `factura.venta_origen`).
- **Pendiente (elegible):** `Factura.naturaleza == VENTA` AND `Factura.tipo == FE` AND `venta_origen` no existe AND `empresa_id` coincide con el tenant actual.
- **No elegible:** `naturaleza == COMPRA`; notas crédito/débito (`tipo != FE`); factura de otro `empresa_id` (nunca visible, DSV); factura ya vinculada; factura inexistente/UUID inválido; caso de match ambiguo (más de una Venta candidata) — se reporta pero nunca se autovincula.

## FASE 2 — Mapeo Factura → Venta

| Factura | Venta | Tratamiento |
|---|---|---|
| `cliente_uuid` / `receptor_nit` | `cliente` (FK) | Resuelto por `cliente_uuid` exacto; si no existe, por NIT vía `ClienteBusinessService.resolver_o_crear_desde_factura_venta` (mismo servicio que el autorrelleno de FST-375) |
| `fecha_emision` | `fecha_emision` | Copiado (normalizado a `.date()` si venía con hora) |
| `fecha_vencimiento` | `fecha_vencimiento` | Copiado si existe |
| items (`ItemFactura`) | `items` (`ItemVenta`) | Snapshot 1-a-1: `descripcion`, `cantidad`, `precio_unitario`, `porcentaje_iva` — vía `VentaCRUDService.crear_venta` (mismo constructor usado por creación manual) |
| `numero` | `numero_factura` | Referencia textual (no FK) — es la clave de matching de FASE 9 |
| CUFE | — | NO se duplica; vive solo en `Factura`, accesible desde Venta vía `factura_asociada.cufe` (ya expuesto por `VentaDetailSerializer.factura_cufe`) |
| — | `factura_asociada` | Vínculo real (OneToOneField) — asignado por `VentaCRUDService.vincular_factura()` |
| — | `observaciones` | Autogenerado: `"Migrada automaticamente desde Factura {numero} (uuid=...)."` (solo en creación nueva, nunca sobrescribe una Venta manual existente) |

`subtotal`/`impuestos`/`total_neto` de la Venta se derivan de los items en `VentaCRUDService.crear_venta` (mismo cálculo que la creación manual) — no se copian directamente de la Factura para no duplicar dos fuentes de verdad del cálculo.

## FASE 3 — Auditoría del endpoint existente

`GET /api/v1/facturas/buscar-para-movimiento/?naturaleza=VENTA` es un buscador de texto libre sin exclusión server-side de ya vinculadas, sin paginación orientada al caso "listar pendientes completo", y sin los campos de listado necesarios para la tabla del panel (CUFE, vencimiento, total formateado). **Decisión:** no extenderlo (mezclaría dos casos de uso — buscador puntual para vincular manualmente vs. listado completo de pendientes) ni duplicar lógica de Facturas; se agregó un selector dedicado (`FacturaSelectors.qs_pendientes_sincronizacion_venta`) que reutiliza `LIST_FIELDS` y los mismos filtros DSV.
