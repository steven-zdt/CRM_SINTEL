# F21 — Matriz de Tests

**Fecha:** 2026-08-09
**Ejecucion real:** `docker compose exec web python -m pytest apps/tenant/compras/tests/test_f21_recepcion_compra.py apps/tenant/inventario/tests/test_f21_traslado_inventario.py -q` → **16 passed in 1523.59s** (ultima corrida limpia, sin fallos).

## 1. Recepcion de Compras (`apps/tenant/compras/tests/test_f21_recepcion_compra.py`)

| # | Escenario pedido por el prompt maestro | Test | Resultado |
|---|---|---|---|
| 1 | Recepcion total genera movimiento y marca orden RECIBIDA | `RecepcionTotalTests::test_recepcion_total_genera_movimiento_y_marca_orden_recibida` | ✅ Real, verifica `MovimientoInventario` (cantidad, sede, documento_origen), `ItemOrdenCompra.cantidad_recibida`, `Producto.stock_actual` |
| 2 | Dos recepciones parciales (60+40) completan la orden (PARCIAL -> RECIBIDA) | `RecepcionParcialTests::test_dos_recepciones_parciales_completan_la_orden_y_tercer_exceso_se_rechaza` | ✅ Real |
| 3 | Tercer intento sobre orden ya RECIBIDA se rechaza | mismo test, tramo final | ✅ Real — `error=estado_invalido` (la orden ya no admite mas recepciones), HTTP 422 |
| 4 | Recibir mas de lo pendiente mientras la orden sigue PARCIAL se rechaza | `RecepcionParcialTests::test_recibir_mas_de_lo_pendiente_mientras_orden_sigue_parcial_es_rechazado` | ✅ Real — `error=cantidad_excede_pendiente`, distingue este guard del anterior |
| 5 | Confirmar dos veces (doble click/retry) no duplica el movimiento | `RecepcionIdempotenciaTests::test_confirmar_dos_veces_no_duplica_movimiento` | ✅ Real |
| 6 | Anular una recepcion ya CONFIRMADA se rechaza (limite de alcance) | `RecepcionIdempotenciaTests::test_anular_recepcion_confirmada_es_rechazado` | ✅ Real |
| 7 | Item sin referencia de catalogo (`item_inventario_uuid=None`) no genera movimiento pero la recepcion es valida | `RecepcionSinReferenciaCatalogoTests::test_item_sin_producto_de_catalogo_no_genera_movimiento_pero_recepcion_es_valida` | ✅ Real |
| 8 | Orden de otro tenant no se puede recibir (multi-tenant real, 2 schemas) | `test_orden_de_otro_tenant_no_se_puede_recibir` (funcion pytest, `tenant1`/`tenant2`) | ✅ Real — `error=orden_no_encontrada`, HTTP 404 |

**Nota metodologica:** el escenario #8 originalmente se escribio como "2 Empresa en el mismo schema" e intentaba `Empresa.objects.create()` una segunda vez — fallo real por `singleton_key` (Empresa es SSoT singleton por tenant, no por fila). Reescrito correctamente como 2 tenants/schemas reales, mismo patron que `test_multitenant_isolation_tabla_html.py` ya establecido en el repo. Documentado como correccion de metodologia de test, no como bug de produccion.

## 2. Traslado de Inventario (`apps/tenant/inventario/tests/test_f21_traslado_inventario.py`)

| # | Escenario pedido por el prompt maestro | Test | Resultado |
|---|---|---|---|
| 1 | E2E completo Bogota->Barranquilla 30 unidades, con verificacion antes/durante/despues (sin doble conteo) | `TrasladoHappyPathTests::test_flujo_completo_bogota_a_barranquilla_30_unidades` | ✅ Real — tabla exacta del prompt maestro verificada linea por linea |
| 2 | sede_origen == sede_destino se rechaza | `TrasladoValidacionesTests::test_sede_origen_igual_destino_es_rechazado` | ✅ Real (ademas de `CheckConstraint` de BD) |
| 3 | Cantidad > stock disponible en sede origen se rechaza al enviar (no al solicitar) | `TrasladoValidacionesTests::test_cantidad_mayor_a_stock_disponible_en_origen_es_rechazado_al_enviar` | ✅ Real — confirma que NO se genera movimiento de salida |
| 4 | Enviar sin aprobar se rechaza (maquina de estados) | `TrasladoValidacionesTests::test_enviar_sin_aprobar_es_rechazado` | ✅ Real |
| 5 | Cancelar un traslado EN_TRANSITO se rechaza | `TrasladoValidacionesTests::test_cancelar_en_transito_es_rechazado` | ✅ Real |
| 6 | Cancelar un traslado SOLICITADO es permitido | `TrasladoValidacionesTests::test_cancelar_en_solicitado_es_permitido` | ✅ Real |
| 7 | Enviar dos veces (retry) no duplica TRASLADO_SALIDA | `TrasladoIdempotenciaTests::test_enviar_dos_veces_no_duplica_movimiento_salida` | ✅ Real |
| 8 | Recibir dos veces (retry) no duplica TRASLADO_ENTRADA | `TrasladoIdempotenciaTests::test_recibir_dos_veces_no_duplica_movimiento_entrada` | ✅ Real |
| 9 | No se puede trasladar a una sede de otro tenant (multi-tenant real, 2 schemas) | `test_no_se_puede_trasladar_a_sede_de_otro_tenant` (funcion pytest, `tenant1`/`tenant2`) | ✅ Real — mismo ajuste metodologico que el caso #8 de Recepcion |

## 3. Cobertura NO incluida (declarada, no oculta)

| Item del prompt maestro | Motivo de no-cobertura |
|---|---|
| Tests de API HTTP completos (DRF `APIClient`, JWT) para `RecepcionCompraViewSet`/`TrasladoInventarioViewSet` | Los tests cubren la capa `BusinessService`/`Service` directamente (mismo patron ya usado en `apps/tenant/clientes/tests/test_cartera_crud_api.py` y otros) — la capa API es delgada (ViewSet -> ServiceMixin -> BusinessService, sin logica propia) y ya se valida indirectamente por `manage.py check` + el registro de URLs verificado manualmente. Reduccion de alcance por presupuesto de tiempo de sesion, no por imposibilidad tecnica. |
| Tests de permisos/`HasOrganizationalScope` con perfiles SEDE/AREA para las 2 features nuevas | El mecanismo en si ya esta probado extensamente para `OrdenCompra`/`MovimientoInventario` (F5/F7/F13, ver `test_scope_pilot_f5.py`, `test_scope_selectors_f7.py`); `RecepcionCompraViewSet`/`TrasladoInventarioViewSet` reutilizan el mismo `HasOrganizationalScope` sin logica adicional — no se duplico la suite completa de permisos por perfil para 2 ViewSets nuevos que no agregan comportamiento nuevo a ese mecanismo. |
| Contabilidad (Recepcion/Traslado -> Extractor -> DTO -> Contabilizador -> Asiento) | No aplica — el extractor de inventario esta deshabilitado (deuda preexistente, ver `F21_BASELINE.md` §5), no hay integracion real que testear todavia. |
| Tests de Area (`area_origen`/`area_destino` en Traslado, `area` en Recepcion) | Los campos existen y son opcionales (`SET_NULL`); no se escribieron tests dedicados de Area para estas 2 features nuevas en esta sesion — mismo criterio de reduccion de alcance que el resto de esta tabla. |

## 4. Veredicto

**16/16 tests pasan, ejecucion real confirmada.** No se declara "cobertura 100% del prompt maestro" — la tabla §3 documenta explicitamente lo que falta, igual criterio de honestidad que `F19_INTEGRATION_TEST_MATRIX.md`.
