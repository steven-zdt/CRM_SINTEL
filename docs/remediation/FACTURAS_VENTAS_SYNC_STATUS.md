# Estado — Sincronización Facturas ↔ Ventas

**Plan ejecutado:** `apps/tenant/ventas/.agent/PLAN_SINCRONIZACION_FACTURAS_VENTAS_FASES.md`
**Baseline:** `docs/remediation/FACTURAS_VENTAS_SYNC_BASELINE.md`
**Fecha:** 2026-09-18

STATUS: PASS

| Fase | Estado | Evidencia |
|---|---|---|
| 0 Baseline | PASS | `FACTURAS_VENTAS_SYNC_BASELINE.md` — inspección real de `factura_asociada`/`venta_origen`, `vincular-factura`, `buscar-para-movimiento`, `venta_editor.js`. |
| 1 Definición | PASS | Sección "Definición" del baseline — sincronizada/pendiente/no-elegible definidos con nombres reales (`naturaleza`, `tipo=FE`, `venta_origen`). |
| 2 Mapeo | PASS | Matriz Factura→Venta en el baseline; reutiliza `VentaCRUDService.crear_venta` (mismo cálculo de totales que creación manual) y `ClienteBusinessService.resolver_o_crear_desde_factura_venta` (ya usado por FST-375). |
| 3 API | PASS | `buscar-para-movimiento` auditado y descartado para este caso de uso (ver baseline) — se creó selector dedicado en vez de forzarlo. |
| 4 Selector | PASS | `FacturaSelectors.qs_pendientes_sincronizacion_venta(empresa_id, search)` — `apps/tenant/facturas/services/selectors.py`. DSV: `empresa_id` obligatorio, sin default `None`. |
| 5 Botón | PASS | `#btn-sincronizar-facturas` en `list_ventas.html`, junto a Nueva Venta/Resoluciones DIAN/Actualizar. |
| 6 Panel | PASS | `offcanvas_sincronizar_facturas.html` (`#offcanvas-sincronizar-facturas`), abierto vía `mostrarOffcanvasSeguro()`. |
| 7 Listado | PASS | Tabla server-rendered con checkbox, Factura, Cliente, NIT, Fecha, Vencimiento, Total (`currency_cop`), CUFE (truncado con `title` completo), acción Vincular. |
| 8 Unitario | PASS | `.btn-vincular-factura` → confirmación → `FacturaVentaSyncService.sincronizar_una()`. Tests: `SincronizarUnaTests` (9 casos). |
| 9 Match Venta | PASS | `_resolver_venta_candidata()` — única señal: `numero_factura` exacto sobre Venta sin `factura_asociada`; >1 candidata → `AMBIGUA`, nunca autovincula. Test: `test_ambigua_si_hay_mas_de_una_venta_candidata`. |
| 10 Masivo | PASS | Checkbox maestro + por fila + contador + botón "Sincronizar seleccionadas" (`sincronizar_facturas.js`). |
| 11 API masiva | PASS | `POST /api/v1/ventas/sincronizar-facturas/` — `{"facturas": [uuid, ...]}`, valida tenant/empresa/lista no vacía server-side. |
| 12 Service | PASS | `FacturaVentaSyncService` (`apps/tenant/ventas/services/business_service.py`) — compone `crear_venta_desde_factura()`/`vincular_factura_existente()` ya existentes, no duplica lógica fiscal. |
| 13 Transacciones | PASS | Cada Factura se procesa en su propia `transaction.atomic()` (`sincronizar_una`, con `select_for_update()`) — un error no revierte el resto del lote (decisión documentada en el docstring de la clase). |
| 14 Resultado | PASS | `sincronizar_masivo()` devuelve `resultados` (por factura) + `resumen` (conteo por estado); UI muestra badges + detalle de no-vinculadas. Test: `SincronizarMasivoTests::test_clasifica_resultados_y_resumen`. |
| 15 Idempotencia | PASS | `test_idempotente_segunda_llamada_reporta_ya_vinculada`, `test_corrida_repetida_no_duplica_ventas` — segunda corrida = 0 Ventas nuevas, `YA_VINCULADA`. |
| 16 Concurrencia | PASS | `test_dos_sincronizaciones_concurrentes_de_la_misma_factura_no_duplican_venta` (threads reales + `transaction=True`, mismo patrón que `test_cartera_concurrencia.py`) — exactamente 1 `VINCULADA` + 1 `YA_VINCULADA`, 1 sola Venta al final. Nota: el teardown de pytest-django (`flush`) falla en TODO test `transaction=True` de este repo bajo django-tenants (confirmado también en `test_cartera_concurrencia.py`, preexistente) — no afecta el resultado de la prueba, solo aparece como error de teardown. |
| 17 Seguridad | PASS | DSV: `test_dsv_no_expone_facturas_de_otra_empresa`, `test_dsv_factura_de_otra_empresa_no_se_puede_sincronizar`, `test_dsv_no_permite_eliminar_venta_de_otra_empresa`. Permisos heredados sin cambios (`IsTenantMember`, `IsTenantAdminOrReadOnly`). UUID inexistente/inválido → `INVALIDA`/404, nunca 500. |
| 18 Integridad fiscal | PASS | Ningún flujo crea/edita `Factura`, XML, CUFE ni autorización. `Venta.factura_asociada` (OneToOneField, `related_name=venta_origen`) sigue siendo la única barrera de vínculo. |
| 19 Regresión Ventas | PASS | Suite completa `apps/tenant/ventas/tests/` (excluyendo el archivo nuevo): **67 passed, 1 skipped**. |
| 20 Regresión Facturas | PASS | Suite XML-pipeline de Facturas (afectada por el fix de escala x100 del parser, ver abajo): **28 passed, 11 skipped**. |
| 21 Datos reales | PASS | FST-375 (`test_fst375_migracion_y_autorrelleno.py`, 9 tests) + casos sintéticos con IVA, crédito, sin items, ambigua (`test_sincronizacion_facturas_ventas.py`). |
| 22 Prueba masiva | PASS | `test_clasifica_resultados_y_resumen`: 3 facturas → 2 `VINCULADA` + 1 `INVALIDA`; `Factura.objects.count()` sin cambios, `Venta.objects.count()` += 2. Además, backfill real (`migrar_facturas_a_ventas`, ejecutado en sesión previa): 30 facturas venta reales detectadas, dry-run sin escritura (aplicar `--apply` queda a criterio del usuario). |
| 23 Documentación | PASS | Este documento + `FACTURAS_VENTAS_SYNC_BASELINE.md`. |

## Hallazgos adicionales corregidos en el camino (fuera del árbol de fases original, pero exigidos por pruebas con datos reales — FASE 21)

1. **Bug de escala x100 en el parser XML universal** (`apps/services/document_parser/normalizers.py` / `xml_parser/parser.py`): valores UBL sin separador de miles (ej. `PriceAmount="582992"`) se dividían por 100. Corregido en ambos niveles (función compartida + bypass dedicado para XML, que nunca necesita heurística de miles). Backfill (`corregir_items_factura_escala_x100.py`) aplicado sobre datos reales: 26 de 29 facturas corruptas corregidas automáticamente (3 no reconciliables, dejadas intactas para revisión manual: FST384/id=26, FST382/id=25, FST376/id=7).
2. **Truncamiento visual de centavos** ("estas omitiendo cifras despues de la coma"): el listado de Facturas (`facturas/tables.py`), el listado de Ventas (`ventas/tables.py`, KPI de monto total) y el preview de totales del formulario Nueva/Editar Venta (`venta_editor.js: fmtMoneda`) forzaban `,.0f`/`maximumFractionDigits:0`, ocultando los centavos aunque el valor real en BD ya era correcto. Unificado con `currency_cop` (2 decimales, formato colombiano punto-miles/coma-decimales) en los tres puntos. Tests: `FormatoNumericoSinTruncarCentavosTests`.
3. **Eliminar Venta sincronizada**: `anular_venta()` rechaza Ventas en `FACTURADA_DIAN` (pensado para una emisión fiscal real, bloqueada estructuralmente por `EMISION_FISCAL_VENTA_AUTORIZADA=False`). Se agregó `VentaBusinessService.eliminar_venta_sincronizada()` — exclusivo para Ventas con `factura_asociada` (nunca hubo emisión DIAN real), hard-delete de la Venta sin tocar la Factura, que vuelve a aparecer como pendiente. Endpoint `DELETE /api/v1/ventas/{uuid}/eliminar-sincronizada/`, botón en el listado de Ventas (solo visible si `factura_asociada` existe). Tests: `EliminarVentaSincronizadaTests` (4 casos, incluye DSV).

## Archivos modificados/creados (resumen)

**Backend:** `facturas/services/selectors.py`, `ventas/services/business_service.py` (`FacturaVentaSyncService`, `eliminar_venta_sincronizada`), `ventas/services/crud_service.py`, `ventas/services/api_mixins.py`, `ventas/api/viewsets.py`, `ventas/tables.py`, `facturas/tables.py`.

**Frontend:** `ventas/templates/tenant/ventas/list_ventas.html`, `offcanvas_sincronizar_facturas.html` (nuevo), `partials/tabla_ventas.html`, `partials/assets_ventas.html`, `ventas/static/ventas/js/ventas.api.js`, `features/sincronizar_facturas.js` (nuevo), `features/venta_list.js`, `features/venta_editor.js`, `facturas/templates/tenant/facturas/offcanvas_crear_factura.html`.

**Tests:** `ventas/tests/test_sincronizacion_facturas_ventas.py` (nuevo, 21 tests).

## Checklist final (FASE 25)

Todos los ítems del checklist del plan quedan satisfechos por lo documentado arriba: botón funcional, filtrado server-side, revisión, vinculación unitaria y masiva, confirmación, estado vacío, manejo de errores, resultado por factura, sin duplicados (Factura/Venta/CUFE/XML), `OneToOne` intacto, SSoT respetado en ambos sentidos, DSV/tenant/permisos verificados, idempotencia y concurrencia probadas, regresión de Ventas y Facturas en verde, documentación alineada con el código real.
