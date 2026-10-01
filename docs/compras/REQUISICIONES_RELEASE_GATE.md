# REQUISICIONES_RELEASE_GATE.md

**Mision:** `PLAN_IMPLEMENTACION_REQUISICIONES_COMPRAS.md`. Estado a la fecha: **Fases 1-11 completadas (autorizacion de tests recibida del usuario 2026-09-25, "si, por ahora ejecuta"). Fase 12 (testing) EN CURSO — ver `REQUISICIONES_PRE_TEST_AUDIT.md` §5-BIS para resultados parciales; pendiente: regresion cruzada de `proveedores`/`clientes`/`proyectos`/`inventario`/`contabilidad` + `manage.py check`/`makemigrations --check --dry-run` (comandos entregados al usuario para ejecucion manual).**

**[2026-09-26] Cambio de regla de negocio -- Cotizacion de origen OBLIGATORIA (item #21 abajo):** los 50 tests de `apps/tenant/compras/requisiciones/tests/` reportados como passing en `REQUISICIONES_PRE_TEST_AUDIT.md` §5-BIS corren ANTES de este cambio. Se actualizaron los fixtures de los 4 archivos que llaman a `crear_requisicion()` directamente (`test_requisicion_compra_service.py`, `test_requisicion_compra_selectors.py`, `test_requisicion_compra_documentos_vinculos.py`, `apps/tenant/compras/tests/test_orden_compra_requisicion_integracion.py`) para pasar una `Cotizacion` real, mas 2 tests nuevos de la validacion (`test_crear_sin_cotizacion_es_rechazado`, `test_crear_con_cotizacion_inexistente_es_rechazado`). Un bug propio se encontro y corrigio despues (`test_requisicion_compra_api.py` habia quedado sin actualizar -- ver siguiente entrada). Bug NO relacionado con este cambio: la avalancha de `IntegrityError`/`SystemExit: 2` que reporto el usuario en 2 corridas fue causada por conexiones huerfanas a `test_sintel` de corridas anteriores no cerradas limpiamente -- diagnosticado y limpiado (`pg_terminate_backend`), no requirio cambios de codigo.

**[2026-09-26] Re-auditoria "evita redundancias" -- 2 gaps reales encontrados contra el checklist original del plan (§44/§45), sin duplicar cobertura ya existente:**
- `test_requisicion_compra_api.py::_payload_valido()` no incluia `cotizacion` -- se me habia pasado en la primera pasada. Corregido (fixture + campo), afectaba 6 tests de ese archivo en cascada (`KeyError: 'uuid'`).
- §45 ("casos de rechazo obligatorios") no tenia test para "editar requisicion ya aprobada" ni "eliminar requisicion con orden generada" -- el codigo YA los rechazaba (`RequisicionCompraCRUDService.actualizar_requisicion()`/`eliminar_requisicion()`), simplemente no estaban verificados. Agregados 3 tests nuevos a `test_requisicion_compra_service.py`: `test_actualizar_requisicion_aprobada_es_rechazada`, `test_eliminar_requisicion_con_orden_generada_es_rechazada`, `test_eliminar_requisicion_borrador_sin_ordenes_permitido` (caso positivo de control). No se agrego cobertura DSV adicional por campo (proyecto/factura de otro tenant) -- el helper `_obtener_entidad_por_id_o_uuid()` es compartido y ya esta probado geneericamente via `test_crear_con_cotizacion_inexistente_es_rechazado`; duplicarlo por cada FK seria la redundancia que se pidio evitar. **Ninguno de estos tests nuevos se ha ejecutado todavia (sin pytest en esta sesion, solo `py_compile`).**

**[2026-09-26] §39 del plan ("Proteccion contra borrado") -- gap real cerrado:** `RequisicionCompraCRUDService.eliminar_requisicion()` tenia un docstring que afirmaba bloquear DELETE con "ordenes/documentos/vinculos", pero el codigo solo verificaba `ordenes_compra` (Recepcion queda cubierta transitivamente -- nunca existe sin una OrdenCompra). Agregados los 2 checks que faltaban: `cotizaciones_vinculadas.exclude(tipo_relacion='ORIGEN')` y `facturas_vinculadas` -- ambos bloquean el DELETE si existen. La Cotizacion de ORIGEN (obligatoria desde el cambio de regla de negocio del mismo dia) se excluye a proposito: toda requisicion BORRADOR la tiene desde que nace, bloquearla por eso volveria indeletable cualquier borrador recien creado -- contradiria la instruccion explicita del usuario de no dejar que esa obligatoriedad limite el CRUD normal. Solo bloquea trazabilidad ADICIONAL (vinculada despues via `vincular_cotizacion`/`vincular_factura`/sincronizacion desde Proyecto). 3 tests nuevos: `test_eliminar_requisicion_con_cotizacion_adicional_es_rechazada`, `test_eliminar_requisicion_con_factura_vinculada_es_rechazada`, mas el caso positivo ya agregado (`test_eliminar_requisicion_borrador_sin_ordenes_permitido`). Sin cambios de UI -- el manejo de error ya existente en `requisiciones_list.js::eliminar()` muestra el mensaje del backend tal cual.

**Accion pendiente del usuario:** re-correr `apps/tenant/compras/requisiciones/tests/`, `apps/tenant/compras/tests/` y `apps/tenant/ventas/tests/test_sincronizacion_facturas_ventas.py` para confirmar que todo lo anterior efectivamente pasa.

## Matriz de aceptacion

| # | Requisito | Estado | Evidencia |
|---|---|---|---|
| 1 | Auditoria previa sin modificar codigo | PASS | `REQUISITION_BASELINE.md` |
| 2 | Diseño documentado antes de codigo | PASS | `REQUISICIONES_DESIGN.md` (con auto-correccion documentada: se elimino `RequisicionOrdenCompra`) |
| 3 | Modelos con `SedeAwareModel`/`SintelTenantBaseModel`, constraints reales | PASS | `apps/tenant/compras/requisiciones/models.py`, migracion `0001_requisiciones_compra` aplicada en 3 schemas (home/admin/aipoc) |
| 4 | Sin `centro_costo` inventado | PASS | Documentado DEFERRED, `proyecto` como agrupador |
| 5 | `OrdenCompra.requisicion` nullable (FASE A), sin backfill inventado | PASS | migraciones `0010`/`0011` de `tenant_compras` |
| 6 | Service Layer completo (selectors/crud/business/api_mixins) | PASS | `apps/tenant/compras/requisiciones/services/` |
| 7 | DSV anti-IDOR en todo lookup cross-entidad | PASS | `_obtener_entidad_por_id_o_uuid()`, verificado por grep (`REQUISICIONES_PRE_TEST_AUDIT.md`) |
| 8 | `estado` nunca editable via PATCH generico | PASS | `read_only_fields` en `RequisicionCompraCreateUpdateSerializer`; unica via son las acciones explicitas |
| 9 | Maquina de estados con historial append-only | PASS | `RequisicionHistorialEstado`, `TRANSICIONES_VALIDAS` |
| 10 | `crear_orden_desde_requisicion` reutiliza `OrdenCompraBusinessService`, no duplica DSV | PASS | `business_service.py::crear_orden_desde_requisicion` |
| 11 | API montada correctamente, sin colisión de rutas | PASS (tras fix) | ver hallazgo #9 de `REQUISICIONES_ARCHITECTURE.md` — orden de registro en `config/api_urls.py` |
| 12 | Frontend integrado como sub-pestaña de `workspace/#compras` | PASS | `compras_list.html` + `requisiciones_list.js`/`requisiciones_editor.js` |
| 13 | Verificacion visual real (no simulada) | PASS | Playwright contra tenant `admin` real, flujo completo crear->aprobar->generar orden->ATENDIDA, 0 errores, evidencia en `REQUISICIONES_FLOW.md` |
| 14 | Datos de prueba limpiados tras verificar | PASS | `RequisicionCompra`/`OrdenCompra` de smoke test eliminados; sesion QA temporal eliminada |
| 15 | `manage.py check` / `makemigrations --check` limpios | PASS | 0 issues, "No changes detected" |
| 16 | `ruff check` sin hallazgos reales nuevos (mas alla del estilo `Tuple` ya preexistente en el proyecto) | PASS | 2 imports sin usar corregidos (`api_mixins.py`, `business_service.py`) |
| 17 | Documentacion (`_ARCHITECTURE`, `_FLOW`, `_SSOT`, `_RELEASE_GATE`, `.agent` actualizado) | PASS | este set de documentos |
| 18 | NO se ejecuto pytest/test suite durante Fases 1-10 | PASS | unicos comandos ejecutados: `check`, `makemigrations`, `migrate_schemas`, `collectstatic`, `ruff check`, mas verificacion Playwright manual (no es la suite pytest) |
| 19 | Autorizacion explicita de tests antes de Fase 12 | PASS | recibida 2026-09-25, ver Fase 11 mas abajo |
| 20 | Fase 12 (testing final) completa | **EN CURSO** | `REQUISICIONES_PRE_TEST_AUDIT.md` §5-BIS — requisiciones/compras/cotizaciones ya verdes; proveedores/clientes/proyectos/inventario/contabilidad + checks pendientes de ejecucion manual |
| 21 | Cotizacion de origen OBLIGATORIA al crear (pedido explicito del usuario, 2026-09-26) | **PENDIENTE DE RE-TEST** | `RequisicionCompraBusinessService.crear_requisicion()` valida y vincula (`RequisicionCotizacion`, `tipo_relacion='ORIGEN'`, `es_principal=True`) en la misma transaccion; serializer (`cotizacion` required) + UI (`#req-cotizacion` en el formulario de creacion, oculto en edicion); fixtures de tests actualizados pero no re-ejecutados en esta sesion (ver nota arriba) |
| 22 | FASE C activada -- Requisicion OBLIGATORIA al crear OrdenCompra, salvo excepcion auditada (pedido explicito del usuario, 2026-09-26) | **SUPERADO** | Reemplazado el mismo dia por el item #23 (N:N sin excepcion) -- ver `PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md` |
| 23 | N:N OrdenCompra<->RequisicionCompra + motor de aprobaciones (Fases 1-4 de `PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md`, pedido explicito del usuario, 2026-09-26) | **PENDIENTE DE RE-TEST** | Ver entrada `[2026-09-26] N:N + Aprobaciones` mas abajo y `docs/approvals/APPROVALS_DESIGN.md` |
| 24 | Fase 5 -- enganche real enviar/aprobar/rechazar + snapshot + revalidacion (pedido explicito del usuario, 2026-09-26) | **PENDIENTE DE RE-TEST** (verificado manualmente end-to-end con datos desechables, ver §"[2026-09-26] Fase 5" mas abajo) | `docs/approvals/APPROVALS_DESIGN.md` §8 |
| 25 | Fase 6 -- `ApprovalTraceService` (nodos/relaciones/timeline/resumen financiero/alertas, solo lectura) | **PENDIENTE DE RE-TEST** (verificado manualmente end-to-end con datos desechables) | `docs/approvals/APPROVALS_DESIGN.md` §9 |

## DEFERRED (documentado, no inventado, no marcado como completado)

- `centro_costo` como entidad real.
- Backfill retroactivo de `OrdenCompra.requisicion` en ordenes historicas (las ordenes creadas antes de FASE C quedan con `requisicion=NULL`, `es_excepcional=False` -- no se reescribe historial).
- `NOT NULL` en `OrdenCompra.requisicion` (FASE D) — la columna sigue siendo nullable a nivel de BD; la obligatoriedad ahora vive en el Service Layer (`crear_orden_compra()`), no en la base de datos. Activar FASE D exigiria antes decidir que valor poner en las ordenes historicas sin requisicion (no se puede inventar una).
- `RequisicionProyecto` como junction N:N (se uso FK directa 0..1, cubre el caso comun).
- Nuevo AI tool `buscar_requisiciones` (no pedido explicitamente).
- UI dedicada para vincular MANUALMENTE una Factura arbitraria (el API `vincular-factura` existe y funciona; la UI de detalle solo muestra lo ya vinculado + el boton "Sincronizar desde Proyecto"; vincular una factura NO derivada del Proyecto queda sin UI dedicada).

**[2026-09-26] Cerrado parcialmente:** UI dedicada para vincular manualmente una Cotizacion arbitraria (no derivada del Proyecto) -- pedido explicito del usuario. Boton "Vincular Cotización" en `offcanvas_detalle_requisicion.html` (seccion Trazabilidad, siempre visible, no depende de tener Proyecto asignado) abre un panel inline con un `<select>` poblado desde `/api/v1/cotizaciones/` (excluye las ya vinculadas via `data-cotizacion-vinculada-uuid`), y confirma contra `POST .../vincular-cotizacion/` (`Sintel.Compras.API.requisiciones.vincularCotizacion()`, nuevo en `compras.api.js`) -- mismo endpoint/DSV que ya usaba la sincronizacion automatica, sin tocar Service Layer. Tras vincular, refresca el detalle (`RequisicionesList.verDetalle`). Sin verificacion en navegador real en esta sesion (sin acceso a browser interactivo) -- pendiente de smoke visual.

## Fase 11 — Autorizacion de Tests

Conforme a la regla explicita del plan (`PLAN_IMPLEMENTACION_REQUISICIONES_COMPRAS.md` §0.2/§57): la implementacion, integracion, hardening y documentacion de Requisiciones de Compra estan **COMPLETADAS** y verificadas end-to-end en un navegador real contra datos reales, sin haber ejecutado pytest/unittest/E2E automatizado en ningun momento de las Fases 1-10.

**Autorizacion recibida del usuario 2026-09-25** ("si, por ahora ejecuta"). Fase 12 iniciada -- ver §5-BIS en `REQUISICIONES_PRE_TEST_AUDIT.md` para resultados.

## Fase 12 — Testing Final (estado a la fecha)

Ejecutado: `apps/tenant/compras/requisiciones/tests/` (50 passed), `apps/tenant/compras/tests/` completo (84 passed), `apps/tenant/cotizaciones/tests/` (26/26 en los 2 archivos afectados, tras corregir 2 bugs reales encontrados durante esta fase — ver `REQUISICIONES_PRE_TEST_AUDIT.md` §5-BIS).

**Pendiente de ejecucion manual** (el usuario pidio no correr mas tests desde esta sesion; comandos entregados para que el mismo los corra):

```bash
docker compose exec web python -m pytest apps/tenant/proveedores/tests/ -q
docker compose exec web python -m pytest apps/tenant/clientes/tests/ -q
docker compose exec web python -m pytest apps/tenant/proyectos/tests/ -q
docker compose exec web python -m pytest apps/tenant/inventario/tests/ -q
docker compose exec web python -m pytest apps/tenant/contabilidad/tests/ -q
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
```

Cuando esos resultados esten disponibles, actualizar este documento y `REQUISICIONES_PRE_TEST_AUDIT.md` §5-BIS con el resultado real antes de marcar la Fase 12 como `COMPLETED`.

## [2026-09-26] FASE C activada -- Requisicion OBLIGATORIA al crear OrdenCompra

Pedido explicito del usuario: "al crear una orden de compra siempre y obligatoriamente debe estar asociada a una requisicion". Esto es exactamente FASE C del plan original (§4), que quedaba DEFERRED desde la implementacion inicial de Requisiciones -- ver `docs/compras/REQUISICIONES_DESIGN.md`.

**Hallazgo real antes de implementar:** `OrdenCompraCreateUpdateSerializer` (`apps/tenant/compras/api/serializers.py`) nunca declaraba los campos `requisicion`/`es_excepcional`/`motivo_excepcion`, pese a que `OrdenCompraBusinessService.crear_orden_compra()` ya tenia logica DSV completa para `requisicion` desde la mision de Requisiciones. Un `POST` real a `/api/v1/compras/` desde la UI **nunca podia asociar una Requisicion** -- DRF descartaba el campo de `validated_data` antes de que llegara al Service Layer (mismo patron de bug ya documentado para `area`, hallazgo OSF Fase F5). Solo el camino directo `RequisicionCompraBusinessService.crear_orden_desde_requisicion()` (el boton "Generar Orden de Compra" dentro del detalle de una Requisicion) funcionaba, porque llama a `crear_orden_compra()` en Python directo, sin pasar por el serializer.

**Cambios:**
- `OrdenCompraCreateUpdateSerializer`: agregados `requisicion` (opcional a nivel de campo -- la regla "A o B" no la puede expresar DRF), `es_excepcional`, `motivo_excepcion`. `OrdenCompraDetailSerializer` gano `requisicion_uuid`/`requisicion_numero`/`es_excepcional`/`motivo_excepcion` para lectura.
- `OrdenCompraBusinessService.crear_orden_compra()`: si no se envia `requisicion`, ahora exige `es_excepcional=True` + `motivo_excepcion` no vacio (`error: requisicion_requerida`, 422) -- nunca un bypass silencioso, misma filosofia que el plan original pedia. La validacion de que la Requisicion (si se envia) este `APROBADA` sigue viviendo en `cambiar_estado_orden_compra()`, sin cambios.
- Frontend (`offcanvas_crear_compras.html` + `compras_editor.js` + `compras.utils.js`): nuevo select "Requisición de Origen \*" (poblado con `RequisicionCompraSelector`-equivalente client-side: estados APROBADA/EN_PROCESO_COMPRA/PARCIALMENTE_ATENDIDA) + checkbox "Compra Excepcional" que alterna a un textarea de motivo obligatorio. Validacion client-side espejo de la del backend (nunca la unica linea de defensa). Solo en creacion -- edicion no toca este campo (mismo criterio que la Cotizacion obligatoria de Requisiciones).
- Tests existentes que creaban ordenes sin requisicion (`test_compras_crud_workspace.py`, `test_organizational_isolation_empresa_a.py`, `test_organizational_service_layer.py`) actualizados con `es_excepcional=True` -- no son tests especificos de Requisiciones, se usa la via de excepcion en vez de fabricar Requisicion+Cotizacion completas. `test_orden_compra_requisicion_integracion.py::test_crear_orden_sin_requisicion_sigue_funcionando_igual` (probaba explicitamente que NO exigir requisicion era el comportamiento correcto) se reemplazo por `test_crear_orden_sin_requisicion_ni_excepcion_es_rechazada` (prueba el rechazo 422) -- su premisa quedo obsoleta por este mismo cambio de regla de negocio. `test_orden_excepcional_sin_requisicion_puede_aprobarse_sin_restriccion` ya cubria "cero regresion del camino de excepcion" sin necesitar cambios.
- Verificado en el dominio real (`admin.sintel.net.co`) que el JS actualizado ya esta servido (`collectstatic` corrido, contenido confirmado via `curl`).
- **Superado el mismo dia por la entrada siguiente** (N:N real, sin excepcion) -- el usuario proveyo `PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md` como diseno nuevo y definitivo antes de que este FASE C se pudiera verificar con tests.

## [2026-09-26] N:N + Aprobaciones (Fases 1-4 de PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md)

Reemplaza la entrada anterior de FASE C. Detalle de diseno completo en `docs/approvals/APPROVALS_DESIGN.md` -- resumen aqui:

- **Nueva app** `apps/tenant/approvals/` (`app_label='tenant_approvals'`): `SolicitudAprobacion`/`SolicitudAprobacionHistorial` + `ApprovalBusinessService` (registry explicito, nunca GenericForeignKey; delega la transicion real al BusinessService del dominio, nunca escribe `objeto.estado` directo). Sin API/UI todavia -- Fase 5+ del plan original.
- **N:N real**: `OrdenCompraRequisicion` (`apps/tenant/compras/models.py`) reemplaza el FK unico `OrdenCompra.requisicion` + `es_excepcional`/`motivo_excepcion` (retirados, migracion `0012_ordencomprarequisicion_and_more`, sin backfill -- 0 filas reales los usaban, verificado antes de migrar). `ItemOrdenCompra.requisicion_item_uuid` nuevo para trazabilidad por linea.
- **`crear_orden_compra()`**: ahora recibe `requisiciones` (lista, `len >= 1`, sin excepcion posible -- `requisicion_requerida`/422 si vacia). Reparte el total de la orden proporcional al `total_estimado` de cada requisicion (`ProcurementBudgetControlService.repartir_monto_proporcional`, salvo montos explicitos) y valida que ninguna exceda su saldo disponible antes de persistir el vinculo -- rollback completo (incluida la `OrdenCompra` ya insertada) si excede.
- **Control financiero**: `apps/tenant/compras/services/budget_control_service.py` -- `ProcurementBudgetControlService`, unico punto de calculo de saldos Cotizacion/Requisicion (`#20` del plan: "una regla, una implementacion"). `validar_requisicion_contra_cotizacion()` existe pero sin caller todavia (el bloqueo real al aprobar una Requisicion es Fase 5).
- **Serializer**: `requisiciones` (lista, `allow_empty=False`) reemplaza `requisicion`/`es_excepcional`/`motivo_excepcion`. Detalle expone `requisiciones_vinculadas` (numero + monto_asignado por cada una).
- **Frontend**: mismo select unico de antes (`offcanvas_crear_compras.html`/`compras_editor.js`), ahora envia `requisiciones: [uuid]`; se quito el checkbox "Compra Excepcional" y su textarea (ya no existe esa via). La seleccion multiple con saldos en vivo (`#21`/`#33` del plan) queda para Fase 10.
- **Migraciones aplicadas** en los 3 tenants reales (`home`/`admin`/`adk_diag_test`) -- verificado: 1 `OrdenCompra` real y 28 `RequisicionCompra` reales intactas tras migrar, `SolicitudAprobacion`/`OrdenCompraRequisicion` en 0 filas (tablas nuevas). `manage.py check`/`makemigrations --check --dry-run` limpios.
- **Tests**: reescritos `test_orden_compra_requisicion_integracion.py` (rechazo sin requisicion, N:N con 2 requisiciones consolidadas + reparto proporcional, rechazo por exceso de saldo) y los 3 archivos genericos que antes usaban `es_excepcional` (`test_compras_crud_workspace.py`, `test_organizational_isolation_empresa_a.py`, `test_organizational_service_layer.py`) -- ahora fabrican una Requisicion real aprobada en vez de usar la excepcion retirada. Nuevo `apps/tenant/approvals/tests/test_approval_business_service.py` (crear/idempotencia/DSV/aprobar/rechazar, delegacion al dominio). **Sin ejecutar pytest en esta sesion** (instruccion explicita del plan §41 + el usuario pidio no correr mas tests el mismo).

**Accion pendiente del usuario:**
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations tenant_compras tenant_approvals
pytest apps/tenant/compras/tests -q
pytest apps/tenant/compras/requisiciones/tests -q
pytest apps/tenant/approvals/tests -q
pytest apps/tenant/core/tests/test_organizational_service_layer.py -q
```

## [2026-09-26] Fase 5 -- enganche real enviar/aprobar/rechazar + snapshot + revalidacion

Detalle completo de diseno en `docs/approvals/APPROVALS_DESIGN.md` §8 -- resumen aqui:

- `RequisicionCompraBusinessService.enviar_a_aprobacion()` crea la `SolicitudAprobacion` real
  (misma transaccion que la transicion de estado) via `ApprovalBusinessService.crear_solicitud()`,
  que calcula el snapshot automaticamente (`_snapshot_requisicion()`: valor, numero, tipo,
  cotizacion de origen, proyecto, cantidad de lineas).
- `aprobar_requisicion()`/`rechazar_requisicion()` cierran su propia `SolicitudAprobacion`
  `PENDIENTE` (si existe) como ultimo paso -- funciona sin importar si la llama el endpoint
  directo de Requisiciones (camino real hoy) o el futuro `ApprovalBusinessService.aprobar()`/
  `rechazar()` (Centro de Aprobaciones, Fase 7/8). `ApprovalBusinessService.aprobar()`/`rechazar()`
  revalidan primero (ver siguiente punto), delegan al dominio, y solo re-escriben el cierre de la
  solicitud si el dominio no lo hizo ya (nunca duplica historial).
- Revalidacion de snapshot (#13 del plan): al aprobar, se recalcula el snapshot del documento
  actual y se compara contra el guardado al enviar -- si difieren, bloquea con 409
  `documento_modificado` ("El documento cambio despues de ser enviado a aprobacion. Debe
  revisarse y reenviarse.") sin tocar el estado real.
- **Verificado end-to-end contra el tenant `admin` real** (datos desechables, creados y limpiados
  en la misma sesion, sin tocar las 28 Requisiciones/28 Ventas/28 Facturas reales existentes):
  1. Crear -> enviar -> solicitud `PENDIENTE` con snapshot real -> aprobar via
     `aprobar_requisicion()` directo -> solicitud `APROBADA`, exactamente 2 eventos de historial
     (`CREADA`, `APROBADA`), requisicion `APROBADA`.
  2. Mismo flujo pero aprobando via `ApprovalBusinessService.aprobar()` (el camino que usara el
     futuro Centro de Aprobaciones) -- identico resultado, sin duplicar historial.
  3. Snapshot corrompido a proposito tras el envio -> `ApprovalBusinessService.aprobar()` rechaza
     con 409, la requisicion permanece en `PENDIENTE_APROBACION` (no se aprueba "a ciegas").
- Nuevos tests en `apps/tenant/approvals/tests/test_approval_business_service.py`:
  `test_aprobar_requisicion_directo_cierra_la_solicitud_sin_pasar_por_approvals`,
  `test_aprobar_bloqueado_si_el_documento_cambio_desde_el_envio`. **Sin ejecutar pytest en esta
  sesion** -- verificacion funcional hecha con datos desechables via shell, no via la suite.

## [2026-09-26] Fase 6 -- ApprovalTraceService (trazabilidad, solo lectura)

Detalle completo en `docs/approvals/APPROVALS_DESIGN.md` §9. `apps/tenant/approvals/services/
trace_service.py::ApprovalTraceService.construir_trazabilidad()` implementa el contrato exacto
del plan (`#16`): DTO `{request, origin, nodes, relations, timeline, financial_summary, alerts}`.
Para Requisicion: nodos Requisicion/Cotizacion-origen/Proyecto/Ordenes-de-Compra-generadas (N:N),
timeline mezclando `SolicitudAprobacionHistorial` + `RequisicionHistorialEstado` (ordenado por
fecha), resumen financiero y alertas via `ProcurementBudgetControlService` (Fase 4, sin
reimplementar el calculo). Solo lectura -- no escribe en ningun dominio.

**Verificado end-to-end contra el tenant `admin` real** (datos desechables, limpiados despues):
DTO completo con 3 nodos, 2 relaciones, timeline de 2 fuentes correctamente ordenado (la
transicion real de la Requisicion antes que la creacion de la Solicitud, reflejando el orden real
de escritura dentro de la misma transaccion), resumen financiero con saldos exactos, sin alertas
(dentro de presupuesto). Nuevo `apps/tenant/approvals/tests/test_approval_trace_service.py` (5
tests: nodos/relaciones basicos, timeline ordenado, ordenes de compra generadas, alerta por
exceso de saldo, tipo de documento no soportado). **Sin ejecutar pytest en esta sesion.**

## [2026-09-26] Fase 7 -- API del Centro de Aprobaciones + disponibles-para-orden

Detalle completo en `docs/approvals/APPROVALS_DESIGN.md` §11.

- `apps/tenant/approvals/api/` -- `SolicitudAprobacionViewSet` (`api_mixins.py`,
  `serializers.py`, `viewsets.py`, `urls.py`), montado en
  `/api/v1/dashboard/aprobaciones/`. Solo lectura + `trazabilidad`/`aprobar`/`rechazar`; `create`
  devuelve 405 explicito (la solicitud solo nace como side-effect de `enviar_a_aprobacion()`).
  Permisos ADMIN-only (`#29`): `[IsTenantMember, IsTenantAdmin, HasOrganizationalScope]`.
- `GET /api/v1/compras/requisiciones/disponibles-para-orden/` -- nuevo `@action` en
  `RequisicionCompraViewSet` (`#32` del plan), reutiliza `RequisicionCompraSelector.
  get_available_for_purchase()` + `ProcurementBudgetControlService.obtener_saldo_requisicion()`.
- **Bug real encontrado y corregido en la misma sesion:** `apps/tenant/approvals/services/
  __init__.py` no exportaba `SolicitudAprobacionServiceMixin` (solo `ApprovalBusinessService`/
  `ApprovalTraceService`) -- el import fallaba silenciosamente dentro del try/except de
  `config/api_urls.py` y la URL nunca se registraba. Detectado al resolver la URL con
  `get_resolver(...).resolve(path)` y ver el `WARNING` real en el log; corregido agregando el
  export faltante.
- **Segundo bug real encontrado y corregido:** `dashboard/aprobaciones/` quedaba capturado por el
  catch-all de `DashboardViewSet` (`dashboard-detail`) si se registraba despues de `dashboard/` en
  `config/api_urls.py` -- mismo mecanismo ya documentado para `compras/requisiciones/` vs
  `compras/`. Corregido registrando `dashboard/aprobaciones/` ANTES; verificado con
  `get_resolver('config.urls_tenant').resolve('/api/v1/dashboard/aprobaciones/')` devolviendo
  `SolicitudAprobacionViewSet` (no `DashboardViewSet`) tras el fix.
- **Verificado end-to-end contra el tenant `admin` real** (datos desechables, limpiados despues)
  via `rest_framework.test.APIRequestFactory` + `force_authenticate` -- ejercita el ViewSet real
  (permisos, serializers, acciones), no solo el Service Layer: crear Requisicion+Cotizacion ->
  enviar a aprobacion -> `GET /aprobaciones/?estado=PENDIENTE` (200, aparece) -> `GET
  .../trazabilidad/` (200, DTO completo) -> `POST /aprobaciones/` directo (405, bloqueado) ->
  `POST .../aprobar/` (200, requisicion y solicitud pasan a `APROBADA`, historial exacto
  `CREADA`+`APROBADA` sin duplicar) -> `GET disponibles-para-orden/` (200, la requisicion aparece
  con `saldo == valor_total`, `valor_comprometido == 0`). Sin residuo en el tenant real al
  terminar. `manage.py check` limpio, `makemigrations --check --dry-run` sin cambios (fase
  puramente de API, sin modelos nuevos).
- **Accion pendiente del usuario:**
```bash
python manage.py check
pytest apps/tenant/approvals/tests -q
pytest apps/tenant/compras/requisiciones/tests -q
```

## [2026-09-26] Fases 8-13 -- Dashboard completo, Nueva OC multi-select, integracion, autoauditoria

Detalle completo en `docs/approvals/APPROVALS_DESIGN.md` §12-16. Cierra
`PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md` (Fases 0-13, completo salvo 1 item DEFERRED
explicito documentado en §10).

- **Fase 8 (Dashboard):** banner + 6 KPIs + bandeja server-side DataTables 3.x + 2 filtros, todo
  en `apps/tenant/approvals/static/approvals/` + `apps/tenant/dashboard/templates/.../partials/
  centro_aprobaciones.html`. Prioridad/riesgo real calculado y congelado en el snapshot al enviar
  (nunca en JS) -- `ApprovalBusinessService._calcular_riesgo_requisicion()`.
- **Fase 9 (detalle interactivo):** offcanvas de revision con ruta del proceso (lista de nodos
  conectados, decision documentada de no introducir una libreria de grafos fuera del stack
  aprobado), resumen financiero, historial, aprobar/rechazar.
- **Fase 10 (Nueva OC):** el `<select>` de Requisicion unica se reemplaza por un checklist real de
  seleccion multiple con saldo en vivo por fila y total seleccionado -- consume el endpoint
  `disponibles-para-orden` de Fase 7.
- **Fase 11 (integracion) -- 2 BUGS REALES ENCONTRADOS Y CORREGIDOS**, ninguno detectado por las
  fases anteriores porque ninguna habia ejercitado `crear_orden_compra()` con >= 2 Requisiciones
  reales via el Business Service completo:
  1. `AttributeError` real: `RequisicionCompraSelector.ESTADOS_DISPONIBLES_PARA_COMPRA` no existe
     como atributo de clase (es una constante de MODULO) -- **bloqueaba el 100% de las creaciones
     de Orden de Compra**, acceptance criteria `#7`/`#8` del plan rotos desde Fase 3. Corregido con
     el import correcto del simbolo del modulo.
  2. Hueco de concurrencia real (`#25` del plan): el codigo afirmaba tener `select_for_update()`
     implicito pero no lo tenia -- 2 OC creadas en paralelo contra la misma Requisicion podian
     sobre-consumir su saldo. Corregido con `select_for_update()` explicito sobre las Requisiciones
     resueltas, dentro de la misma transaccion.
  Verificado tras el fix: consolidacion real de 2 Requisiciones en 1 OC, `monto_asignado` correcto,
  `ItemOrdenCompra.requisicion_item_uuid` poblado en el 100% de las lineas, saldos exactos en $0.00
  (Requisiciones) y $30.000 (Cotizacion). Sin residuo en el tenant real.
- **Fase 13 (autoauditoria):** revision sistematica de bypass de aprobacion/limites, carreras de
  concurrencia, fuga cross-tenant, duplicacion de logica, inconsistencias de estado/frontend-
  backend, rutas duplicadas, y Dashboard-como-SSoT -- sin hallazgos adicionales a los ya corregidos
  en Fase 11.

**Verificacion realizada esta fase (sin pytest, siempre datos desechables en el tenant `admin`
real):** `manage.py check` limpio, `makemigrations --check --dry-run` sin cambios (Fases 8-13 no
agregan modelos), render real de `/workspace/` via `django.test.Client` con sesion real confirma
que las plantillas/JS nuevos se sirven sin error, `collectstatic` ejecutado tras cada cambio de
JS/template.

**No verificado en esta sesion (fuera de alcance sin navegador real disponible):** interaccion real
de click en la bandeja/offcanvas/checklist de "Nueva OC" en un navegador. El backend que esos flujos
consumen esta 100% verificado via `APIRequestFactory`/Business Service directo.

**Accion pendiente del usuario:**
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
pytest apps/tenant/approvals/tests -q
pytest apps/tenant/compras/tests -q
pytest apps/tenant/compras/requisiciones/tests -q
pytest apps/tenant/dashboard/tests -q
pytest apps/tenant/cotizaciones/tests -q
```
Y, si es posible, una pasada manual en navegador de: Dashboard -> Centro de Aprobaciones (banner/
KPIs/bandeja/filtros), abrir una solicitud pendiente real (REVISAR -> ruta/resumen/historial ->
Aprobar o Rechazar), y Compras -> Nueva Orden de Compra -> seleccionar 2+ Requisiciones del
checklist y confirmar que el total seleccionado se actualiza en vivo.
