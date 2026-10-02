# AUDITORIA DE FLUJO DE TRABAJO - MODULO DE COMPRAS

**Version auditada:** v3.10.5 → corregida 2026-06-18 → sincronizacion CxP 2026-08-26 → Fase 2 remediación 2026-09-12 → Requisiciones de Compra 2026-09-25 → FASE C (Requisicion obligatoria en OrdenCompra) 2026-09-26 → N:N OrdenCompra<->Requisicion + motor de aprobaciones (Fases 1-4) 2026-09-26 → Fase 5: enganche real enviar/aprobar/rechazar 2026-09-26 → Fase 6: ApprovalTraceService 2026-09-26 → Fase 7: API del Centro de Aprobaciones 2026-09-26 → **Fases 8-13: Dashboard completo + Nueva OC multi-select + 2 bugs reales corregidos en crear_orden_compra() 2026-09-26 (PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md COMPLETO)**
**Auditor:** Claude Code. Fase 2 remediación 2026-09-12: Claude Sonnet 5 (Anthropic).
**Estado actual:** 6 bugs criticos/altos corregidos — 3 items de deuda tecnica pendientes. **4 hallazgos ALTO nuevos encontrados y corregidos 2026-09-12** (CO-1..CO-4, ver sección abajo) — **verificado: `pytest apps/tenant/compras/tests/` completo → 43 passed (suite preexistente, sin regresión) + 6 tests nuevos → 6 passed.**

---

## 2026-10-01 — PLAN_OPTIMIZACION_COMPRAS_Y_BASE_NUEVA_REQUISICION_TAREA_1

Plan auditado contra `main`, pero esta rama (`feat/onboarding-cookie`) ya traia sin commitear
el submodulo `requisiciones/`, el motor de aprobaciones (`apps/tenant/approvals/`) y el control
presupuestal (`budget_control_service.py`) -- ninguno contemplado por el plan original. Fase 0
(baseline) confirmo que varias fases ya estaban resueltas por ese trabajo previo; solo se tocaron
las que seguian pendientes contra el codigo real. **Sin pytest en esta sesion (regla explicita del
plan) -- queda para la fase manual del usuario.**

- **Fase 1 (numeración) y Fase 2 (selectors):** YA RESUELTAS, sin cambios. `PlantillaOrdenCompra`
  ya tiene `tipo_documento` (ORDEN_COMPRA/REQUISICION) y `RequisicionCompraBusinessService` ya
  reutiliza el mismo motor (`_dsv_y_asignar_plantilla`, `select_for_update()` + `F()+1`) -- no existe
  un segundo motor de numeracion. Selectors de ambos modulos ya usan `LIST_FIELDS`/`DETAIL_FIELDS`
  + `select_related`/`prefetch_related` completos.
- **Fase 3 (KPIs):** `OrdenCompraKpisView.get_context_data()` (`views.py`) paso de 4 queries
  independientes a un unico `aggregate()` con `Count`/`Sum` condicionados (`filter=Q(...)`).
- **Fase 4 (búsqueda bajo demanda):** `#proveedor`/`#proyecto` en
  `offcanvas_crear_compras.html`/`offcanvas_editar_compras.html` pasaron de `<select>` con el
  catalogo completo precargado a un buscador real (`compras.utils.js::initBuscadorAsync`, 3+
  caracteres, debounce 300ms, `?search=` contra `/api/v1/proveedores/`/`/api/v1/proyectos/`, que ya
  soportaban el parametro). **Hallazgo real:** el `<select>` anterior no descargaba "todo el
  catalogo" como asumia el plan -- al no pasar `?search=`, el backend paginaba 20 resultados por
  defecto (`StandardResultsSetPagination`), asi que el combo silenciosamente solo dejaba elegir
  entre los primeros 20 proveedores/proyectos de la empresa. El fix de Fase 4 corrige ese bug real,
  no solo optimiza.
- **Fase 5 (HTTP único):** `compras.utils.js` (proveedores/proyectos/cotizaciones) y
  `requisiciones_list.js::fetchJson` migrados de `fetch()+getHeaders()` a
  `Sintel.Core.Http.request()` (mismo motor que `compras.api.js::_fetch`). `getHeaders()` retirado
  de `compras.api.js` tras confirmar cero consumidores restantes.
- **Fase 6 (items sin borrado masivo):** `OrdenCompraCRUDService.actualizar_orden()` y
  `RequisicionCompraCRUDService.actualizar_requisicion()` pasaron de `items.all().delete()` +
  `bulk_create()` a sincronizacion diferencial por `uuid` (UPDATE de filas existentes, INSERT de
  nuevas, DELETE solo de las removidas). `requisicion_item_uuid`/`cantidad_aprobada`/
  `cantidad_ordenada`/`cantidad_cancelada` de un item existente ya NO se pierden al editar la
  cabecera (antes se perdian silenciosamente en cada reemplazo total). `ItemOrdenCompraSerializer.
  uuid`/`RequisicionCompraItemSerializer.uuid` pasaron de `read_only` a opcional en escritura para
  que el frontend pueda identificar la fila; `compras_editor.js::recolectarDatos()` y
  `requisiciones_editor.js::recolectarItems()`/`crearFilaItem()` ahora propagan ese uuid.
- **Fase 7 (escrituras redundantes):** `crear_orden()`/`crear_requisicion()` calculan subtotal/IVA/
  total de los items ANTES de instanciar la cabecera -- un solo `save()`, sin el segundo
  `save(update_fields=[...])` posterior. Formula extraida a `_calcular_item()` (un helper por
  modulo, mismo criterio que ya existia en requisiciones).
- **Fase 9 (cálculo JS duplicado):** `actualizarFilaTotal()`/`actualizarTotales()` en
  `compras_editor.js` ahora comparten `calcularItem()` -- antes repetian la misma formula inline.
- **Fase 10 (preview de numeración):** texto cambiado de "Número a asignar" a "Próximo número
  estimado" en `compras_editor.js::actualizarInfoPlantilla()` y
  `requisiciones_editor.js::actualizarInfoPlantillaReq()` -- ninguno de los dos refleja una reserva
  transaccional real (esa ocurre en `_dsv_y_asignar_plantilla()` al guardar).
- **Fase 11 (templates duplicados):** el bloque `<style>` idéntico (~54 líneas, antes bajo dos IDs
  distintos) entre `offcanvas_crear_compras.html`/`offcanvas_editar_compras.html` se extrajo a
  `partials/formulario_estilos.html` (clase compartida `.offcanvas-compra-form`). El resto de
  secciones del formulario (informacion general, items, totales) queda pendiente de una extraccion
  similar en una fase futura -- no se tocaron en esta pasada por tener diferencias reales entre
  crear/editar (ids server-rendered vs placeholders) que requieren mas cuidado.
- **Fase 8 (full_clean en loop):** revisado, SIN CAMBIOS. `ItemOrdenCompra` no tiene un
  `CheckConstraint` de BD equivalente a los `MinValueValidator` de `cantidad`/`valor_unitario` (a
  diferencia de `RequisicionCompraItem`, que si los tiene) -- retirar `full_clean()` del loop
  reduciria integridad real, no solo CPU. Se preserva.
- **Fase 14 (código muerto), retirado con consumidores verificados en cero:** `getHeaders()`
  (`compras.api.js`), `loadProveedoresSelect`/`loadProyectosSelect`/`loadCotizacionesSelect`
  (`compras.utils.js`, sin otro consumidor tras la Fase 4), `OrdenCompraCRUDService.
  _obtener_siguiente_consecutivo()` (`crud_service.py`, sin ningun consumidor en todo el modulo).
  **Se mantiene intencionalmente** `OrdenCompraSelector.get_siguiente_consecutivo()`/
  `RequisicionCompraSelector.get_siguiente_consecutivo()` (selector + mixin + endpoint
  `siguiente-consecutivo/`): confirmado sin consumidor en el frontend real, pero tiene un test
  dedicado (`test_requisicion_compra_selectors.py`) y retirarlo no aporta ninguna reduccion de
  trabajo en runtime (nadie lo llama hoy) -- sin poder correr pytest en esta sesion, no se asumio
  el riesgo de tocar ese test a ciegas.
- **Fase 4 (extensión) / Fase 11 (extensión), mismo día, continuación a pedido del usuario:**
  - El mismo bug real de Fase 4 (combo que solo mostraba los primeros 20 resultados por paginación
    silenciosa) existía en TRES lugares más de `requisiciones/`, todos corregidos al mismo patrón
    `?search=` bajo demanda (confirmado que `/api/v1/proyectos/`, `/api/v1/proveedores/` y
    `/api/v1/cotizaciones/` ya soportan el parámetro vía `CotizacionServiceMixin.get_qs_list()`):
    1. Buscador de Proyecto en `requisiciones_editor.js::renderResultadosProyecto` (precargaba
       `fetchProyectos()` una vez y filtraba client-side).
    2. `<select>` de Proveedor del panel "Generar Orden de Compra" (`offcanvas_detalle_requisicion.
       html` / `requisiciones_list.js::poblarSelectProveedores`, retirada).
    3. `<select>` de Cotización del panel "Vincular Cotización" (mismo archivo/template,
       `poblarSelectCotizaciones`, retirada) -- el filtro de "ya vinculadas" se preserva aplicándose
       sobre cada página de resultados de búsqueda (`_cotizacionVincYaVinculadas`), no sobre un
       catálogo completo cacheado.

    El widget de Cotizaciones de "Nueva Requisición" (modal 0..N, `renderResultadosCotizacion`) se
    revisó y se dejó intacto a propósito: ya usa un endpoint dedicado pre-filtrado por el backend
    (`cotizacionesDisponibles()`, excluye vinculadas) con un conjunto acotado, no el catálogo
    completo -- no es el mismo patrón defectuoso.
  - Fase 11 extendida: `offcanvas_crear_compras.html`/`offcanvas_editar_compras.html` ahora
    comparten además `partials/buscador_proveedor_proyecto.html`, `partials/items_table_head.html`,
    `partials/totales_observaciones.html` y `partials/acciones_footer.html` (antes solo el `<style>`
    se había extraído). La sección "Información General" se dejó sin tocar a propósito: sus campos
    son genuinamente distintos entre crear (Plantilla + preview) y editar (Consecutivo readonly),
    forzar un partial ahí habría sido una abstracción prematura sin reducir duplicación real.
  - Nota de diseño conocida, no resuelta: `initBuscadorAsync()` agrega un listener de `click` sobre
    `document` cada vez que se inicializa un formulario/panel -- en una sesión larga con muchas
    aperturas del mismo offcanvas (HTMX re-renderiza el DOM cada vez) esos listeners se acumulan
    sin limpiarse (cada uno referencia un nodo ya desmontado, por lo que es inofensivo en
    comportamiento, solo un crecimiento lento de memoria). Mismo tipo de tradeoff que ya existía en
    otros bindings de esta base de código; no se resolvió en esta pasada por no formar parte del
    alcance de Fase 4/5/11.

- **Drift de documentación preexistente (no corregido en esta pasada):** las secciones 5.1/5.2 mas
  abajo en este mismo archivo todavia describen un grid Tabulator -- ya reemplazado por DataTables
  3.x (ver docstring de `OrdenCompraKpisView` en `views.py` y `docs/remediation/
  DATATABLES_PILOT_VENTAS_STATUS.md`). Reescribir esas secciones es un trabajo aparte, fuera del
  alcance quirúrgico de esta Tarea 1 -- se deja señalado para no repetir el hallazgo.

---

## 2026-09-28 — PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS: cierre de brechas sobre `OrdenCompra.factura_asociada` (no reconstruido desde cero)

Auditoria Fase 0 del plan encontro que el vinculo manual Factura(COMPRA)<->OrdenCompra (FACTURAS-UI-CRONO-01, ver mas abajo/`docs`) ya existia casi completo: modelo `factura_asociada` (OneToOne), `vincular_factura_existente()`, accion `POST .../vincular-factura/`, buscador reutilizando `GET /api/v1/facturas/buscar-para-movimiento/` (`naturaleza=COMPRA`), y el widget completo en `offcanvas_detalle_compras.html` + `compras_list.js`. `RequisicionFactura` (submodulo Requisiciones) es un vinculo de **trazabilidad/evidencia** distinto y ya documentado como tal -- no se toco, no compite con `factura_asociada` como SSoT operacional. Brechas reales encontradas y cerradas en esta sesion (mismo hallazgo tambien existe hoy en el equivalente de Ventas -- `Venta.factura_asociada` -- pero quedo fuera de alcance de este plan, que es especifico de Compras):

1. **Sin validacion de proveedor** (Fase 10 del plan): `vincular_factura_existente()` ahora compara `Factura.emisor_nit` contra `OrdenCompra.proveedor.numero_documento` via `same_nit()` (SSoT ya existente en `facturas.services.business_service`) -- 422 `proveedor_incompatible` si no coincide.
2. **Sin proteccion de concurrencia** (Fase 22): `select_for_update()` sobre la Orden en `vincular_factura_existente()` y `desvincular_factura_existente()`.
3. **"Cambiar factura" roto**: el boton ya existia en el template/JS pero el backend siempre devolvia 409 `orden_ya_vinculada` al reintentar vincular sobre una Orden que ya tenia factura -- no existia forma de desvincular. Nuevo: `OrdenCompraCRUDService.desvincular_factura()`, `OrdenCompraBusinessService.desvincular_factura_existente()` (bloquea con 409 `vinculo_bloqueado_pagos` si la CxP de esa Factura ya tiene `valor_pagado>0`), `POST .../desvincular-factura/`, `Sintel.Compras.API.desvincularFactura()`. `compras_list.js`: el boton "Cambiar factura" ahora desvincula primero (con confirmacion) y solo abre el buscador si el backend lo permite.
4. **Buscador no excluia facturas ya vinculadas** (Fase 9): `buscar-para-movimiento` gano un parametro opt-in `excluir_vinculadas=compra|venta` (no cambia el comportamiento por defecto de Inventario, su otro consumidor real) -- Compras lo pasa siempre.
5. **CxP sin trazabilidad a la Factura real** (Fase 20): `CuentasPagar.factura_uuid` nunca se completaba al vincular una Factura despues de que la Orden ya hubiera generado su CxP al Aprobarse (o viceversa). Ahora `vincular_factura_existente()` completa el `factura_uuid` de la CxP existente (si estaba vacio, nunca crea una segunda), y `_sincronizar_cuenta_por_pagar()` (Aprobar) la incluye desde el nacimiento si la Factura ya estaba vinculada antes.
6. **Diferencia de valor Factura vs Orden** (Fase 32): nueva `@property OrdenCompra.factura_diferencia`, badge informativo en el detalle (nunca bloquea ni corrige automaticamente).

Deliberadamente fuera de alcance (evaluado y descartado en la Fase 0, no es una omision): endpoint de busqueda dedicado (Fase 24 -- el existente ya evita duplicar contrato, se reuso); vinculo en el momento de creacion de la Orden (Fase 28 -- sin evidencia de necesidad real, el flujo post-creacion ya cubre el caso); conciliacion de items Factura<->OC (Fase 33 -- sin mapping confiable por referencia/UUID/codigo, el plan mismo pide no inventar heuristica); permisos granulares ver/vincular/desvincular (Fase 35 -- no existe esa infraestructura en ningun otro modulo del proyecto, se reutilizan los permisos de rol ya existentes del ViewSet); auditoria formal usuario/fecha/accion (Fase 36 -- no existe infraestructura de AuditLog en el proyecto para este tipo de accion, mismo gap preexistente en Ventas); "Ver factura" (abrir el documento real, Fase 39) -- Ventas (el patron de referencia) tampoco lo tiene, se mantuvo paridad UX exacta con Ventas en vez de agregar una feature que ni la referencia tiene.

Tests nuevos en `apps/tenant/compras/tests/test_vincular_factura_manual.py` (proveedor incompatible, desvincular exitoso, desvincular sin vinculo, desvincular bloqueado por pagos, sync de `factura_uuid` en CxP existente) -- **pytest NO ejecutado en esta sesion, queda para la fase manual del usuario** (decision explicita del plan, seccion 46/47).

## 2026-09-25 — Submodulo Requisiciones de Compra (nuevo)

Nuevo submodulo `apps.tenant.compras.requisiciones` (app Django propia, `app_label='tenant_compras_requisiciones'`, registrada en `TENANT_APPS`), UI integrada como tercera sub-pestaña de `workspace/#compras`. `OrdenCompra` gano `requisicion`/`es_excepcional`/`motivo_excepcion` (nullable, FASE A de una migracion por fases). Documentacion completa: `docs/compras/REQUISICIONES_ARCHITECTURE.md`, `_FLOW.md`, `_SSOT.md`, `_RELEASE_GATE.md`, `_PRE_TEST_AUDIT.md`, `REQUISITION_BASELINE.md`, `REQUISICIONES_DESIGN.md`. Verificado end-to-end en vivo contra el tenant `admin` (Playwright): crear -> enviar a aprobacion -> aprobar -> generar Orden de Compra -> ATENDIDA automatica, 0 errores. Datos de prueba limpiados tras verificar. **Fase 11 autorizada por el usuario 2026-09-25** ("si, por ahora ejecuta"); Fase 12 en curso: `apps/tenant/compras/requisiciones/tests/` 50 passed (suite nueva), `apps/tenant/compras/tests/` completo 84 passed (sin regresión en Ordenes/Plantillas/Recepciones), `apps/tenant/cotizaciones/tests/` 26/26 en los 2 archivos afectados tras corregir 2 bugs reales encontrados durante esta Fase (ver `docs/compras/REQUISICIONES_PRE_TEST_AUDIT.md` §5-BIS); regresión cruzada de `proveedores`/`clientes`/`proyectos`/`inventario`/`contabilidad` + `manage.py check`/`makemigrations --check --dry-run` pendientes de ejecutar — este modulo de Compras (Ordenes/Plantillas/Recepciones) NO se modifico en su logica, solo se le agrego la FK opcional y el nuevo tab de UI.

## 2026-09-26 — FASE C: Requisicion pasa de opcional a OBLIGATORIA en OrdenCompra

Pedido explicito del usuario. La logica del modulo Compras (Ordenes/Plantillas/Recepciones) SI se modifico esta vez, a diferencia de la mision de Requisiciones del dia anterior: `crear_orden_compra()` ahora exige `requisicion` o (`es_excepcional=True` + `motivo_excepcion`), 422 (`requisicion_requerida`) si ninguna de las dos esta presente. Hallazgo real: `OrdenCompraCreateUpdateSerializer` nunca habia declarado `requisicion`/`es_excepcional`/`motivo_excepcion` -- la API real jamas pudo asociar una Requisicion a una Orden creada desde "Nueva Orden de Compra" (solo el camino `crear_orden_desde_requisicion()`, que llama al Business Service en Python directo, lo lograba). **Superado el mismo dia -- ver entrada siguiente.**

## 2026-09-26 — N:N OrdenCompra<->RequisicionCompra + motor de aprobaciones (Fases 1-4 de PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md)

El FK unico + escape `es_excepcional` de la entrada anterior se retiraron el mismo dia: el usuario proveyo un plan nuevo y definitivo que exige N:N real ("no resolver esto con un FK unico") y elimina la excepcion ("no debe seguir funcionando para nuevas OC"). Cambios: modelo `OrdenCompraRequisicion` (junction, `monto_asignado` por fila) reemplaza el FK; `ItemOrdenCompra.requisicion_item_uuid` nuevo (trazabilidad por linea); `crear_orden_compra()` ahora recibe `requisiciones` (lista, >=1 sin excepcion posible) y reparte el monto proporcional via el nuevo `ProcurementBudgetControlService` (`apps/tenant/compras/services/budget_control_service.py`), que tambien valida que ninguna Requisicion exceda su saldo disponible (rollback completo si excede). Nueva app `apps/tenant/approvals/` (motor generico `SolicitudAprobacion`/`ApprovalBusinessService`, registry explicito, sin API/UI todavia -- Fases 1-4 son fundamento, el enganche real con Requisiciones y el Centro de Aprobaciones del Dashboard son Fase 5+, DEFERRED). 0 filas reales usaban el FK retirado (1 sola `OrdenCompra` real en el tenant `admin`) -- migracion sin backfill. Detalle completo: `docs/approvals/APPROVALS_DESIGN.md`, `docs/compras/REQUISICIONES_RELEASE_GATE.md` §"[2026-09-26] N:N + Aprobaciones". Tests actualizados (compras + core), sin ejecutar pytest en esta sesion.

---

## 2026-09-26 — Fase 5: enganche real enviar/aprobar/rechazar de Requisiciones con el motor de Aprobaciones

Mismo dia, misma mision. `RequisicionCompraBusinessService.enviar_a_aprobacion()` ahora crea la `SolicitudAprobacion` real (misma transaccion que la transicion de estado) via `ApprovalBusinessService.crear_solicitud()`, con snapshot automatico (valor/numero/tipo/cotizacion/proyecto/cantidad de lineas). `aprobar_requisicion()`/`rechazar_requisicion()` cierran su propia solicitud `PENDIENTE` (si existe) como ultimo paso -- funciona igual sin importar si la dispara el endpoint directo de Requisiciones (camino real hoy, sin Centro de Aprobaciones todavia) o el futuro `ApprovalBusinessService.aprobar()`/`rechazar()` (que revalida el snapshot antes de delegar, y no duplica el cierre si el dominio ya lo hizo). Revalidacion de snapshot (#13 del plan): si el documento cambio desde el envio, bloquea la aprobacion con 409 en vez de aprobar "a ciegas". **Verificado end-to-end contra el tenant `admin` real** con datos desechables (creados y limpiados en la misma sesion): crear->enviar->aprobar directo (2 eventos de historial, sin duplicar); mismo flujo via `ApprovalBusinessService.aprobar()` (identico, sin duplicar); snapshot corrompido a proposito -> aprobacion bloqueada, requisicion permanece `PENDIENTE_APROBACION`. Detalle completo: `docs/approvals/APPROVALS_DESIGN.md` §8, `docs/compras/REQUISICIONES_RELEASE_GATE.md` §"[2026-09-26] Fase 5". 2 tests nuevos en `apps/tenant/approvals/tests/`, sin ejecutar pytest en esta sesion.

---

## 2026-09-26 — Fase 6: ApprovalTraceService (trazabilidad, solo lectura)

Mismo dia, misma mision. `apps/tenant/approvals/services/trace_service.py::ApprovalTraceService.construir_trazabilidad()` construye el DTO `{request, origin, nodes, relations, timeline, financial_summary, alerts}` de una `SolicitudAprobacion` -- para Requisicion: nodos Requisicion/Cotizacion-origen/Proyecto/Ordenes-de-Compra-generadas (N:N de Fase 3), timeline mezclando `SolicitudAprobacionHistorial` + `RequisicionHistorialEstado` (ordenado por fecha), resumen financiero y alertas via `ProcurementBudgetControlService` (Fase 4, sin reimplementar el calculo). Solo lectura -- no escribe en ningun dominio. **Verificado end-to-end contra el tenant `admin` real** con datos desechables: DTO completo con 3 nodos, 2 relaciones, timeline correctamente ordenado, resumen financiero exacto, sin alertas (dentro de presupuesto). 5 tests nuevos en `apps/tenant/approvals/tests/test_approval_trace_service.py`. Detalle completo: `docs/approvals/APPROVALS_DESIGN.md` §9. Sin ejecutar pytest en esta sesion.

## 2026-09-26 — Fase 7: API del Centro de Aprobaciones + disponibles-para-orden

Mismo dia, misma mision. `apps/tenant/approvals/api/` (`SolicitudAprobacionViewSet`) montado en `/api/v1/dashboard/aprobaciones/` -- solo lectura + acciones `trazabilidad`/`aprobar`/`rechazar`, `create` bloqueado (405, la solicitud solo nace como side-effect de `enviar_a_aprobacion()`), permisos ADMIN-only. Segundo endpoint: `GET /api/v1/compras/requisiciones/disponibles-para-orden/` (nuevo `@action` en el `RequisicionCompraViewSet` ya existente), reutiliza `RequisicionCompraSelector.get_available_for_purchase()` + `ProcurementBudgetControlService.obtener_saldo_requisicion()`.

**2 bugs reales encontrados y corregidos en la misma sesion, antes de dar la fase por cerrada:**
1. `apps/tenant/approvals/services/__init__.py` no exportaba `SolicitudAprobacionServiceMixin` -- el import fallaba silenciosamente dentro del try/except de `config/api_urls.py` (patron de resiliencia del propio archivo) y la ruta nunca se registraba, sin ningun error visible salvo un `WARNING` en el log.
2. `dashboard/aprobaciones/` quedaba capturado por el catch-all de `DashboardViewSet` (`dashboard-detail`) al registrarse despues de `dashboard/` en `config/api_urls.py` -- mismo mecanismo ya conocido y documentado para `compras/requisiciones/` vs `compras/`. Corregido registrando `dashboard/aprobaciones/` ANTES.

Ambos detectados con `get_resolver('config.urls_tenant').resolve(path)` contra el path real -- no se asumio que la ruta funcionaba solo porque el archivo compilaba. **Verificado end-to-end contra el tenant `admin` real** (datos desechables, limpiados despues) via `APIRequestFactory` + `force_authenticate` (ejercita el ViewSet/serializers reales, no solo el Service Layer): LIST, trazabilidad, create bloqueado, aprobar (sin duplicar historial), disponibles-para-orden con saldo correcto. `manage.py check` limpio, `makemigrations --check --dry-run` sin cambios. Detalle completo: `docs/approvals/APPROVALS_DESIGN.md` §11. Sin ejecutar pytest en esta sesion.

## 2026-09-26 — Fases 8-13: Dashboard completo, Nueva OC multi-select, 2 BUGS REALES en crear_orden_compra()

Mismo dia, misma mision -- cierra `PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md` completo. Fase 8
(banner/KPIs/bandeja del Centro de Aprobaciones en Dashboard) y Fase 9 (offcanvas de revision con
ruta del proceso) no tocan `apps/tenant/compras/` -- viven en `apps/tenant/approvals/` +
`apps/tenant/dashboard/`. Fase 10 SI toca compras: el formulario "Nueva Orden de Compra" reemplaza
su `<select>` de Requisicion unica por un checklist real de seleccion multiple con saldo en vivo
(`compras.utils.js::loadRequisicionesDisponiblesChecklist`, `compras.api.js::requisiciones.
disponiblesParaOrden`), consumiendo el endpoint `disponibles-para-orden` de Fase 7 en vez de listar
todas las Requisiciones y filtrar por estado en el cliente.

**Fase 11 (verificacion de integracion) encontro 2 bugs reales en `OrdenCompraBusinessService.
crear_orden_compra()` que NINGUNA prueba anterior de esta mision (Fases 3/4/7) habia detectado,
porque ninguna habia llamado a este metodo con >= 2 Requisiciones reales de punta a punta:**

1. **`AttributeError` real -- bloqueaba el 100% de las creaciones de OC reales:**
   `if requisicion.estado not in RequisicionCompraSelector.ESTADOS_DISPONIBLES_PARA_COMPRA:`
   referenciaba una constante de MODULO (`ESTADOS_DISPONIBLES_PARA_COMPRA`, definida fuera de la
   clase en `requisiciones/services/selectors.py`) como si fuera un atributo de clase. Cualquier
   llamada real a `crear_orden_compra()` con al menos 1 requisicion fallaba con `AttributeError`
   envuelto como error 500 -- es decir, el acceptance criteria "toda OC nueva exige >= 1
   Requisicion" (`#7`/`#8` del plan) estaba roto en produccion desde que se introdujo en Fase 3, sin
   que ningun test previo de esta sesion lo hubiera ejercitado con datos reales de extremo a
   extremo. Corregido: `from apps.tenant.compras.requisiciones.services.selectors import
   ESTADOS_DISPONIBLES_PARA_COMPRA` (import directo del simbolo del modulo).
2. **Hueco de concurrencia real, nunca cerrado (`#25` del plan):** un comentario en el codigo
   afirmaba "select_for_update() implicito via `_obtener_entidad_por_id_o_uuid`" -- verificado que
   es FALSO (ese helper es un `.filter().first()` sin lock). Corregido con un re-fetch explicito de
   las Requisiciones ya resueltas usando `RequisicionCompra.objects.select_for_update().filter(
   id__in=...)`, dentro de la misma `@transaction.atomic` que ya envolvia el metodo, ANTES de
   calcular montos/validar saldo -- cierra el escenario de doble-consumo que `#25` describe
   explicitamente.

**Verificado tras ambos fixes, contra el tenant `admin` real (datos desechables, limpiados
despues):** 2 Requisiciones APROBADAS ($40.000/$30.000) consolidadas en 1 sola Orden de Compra via
`crear_orden_compra()` real -- `OrdenCompraRequisicion` con `monto_asignado` correcto por fila,
`ItemOrdenCompra.requisicion_item_uuid` poblado en el 100% de las lineas (trazabilidad por linea,
`#4` del plan), saldo de ambas Requisiciones en `$0.00`, saldo de la Cotizacion en `$30.000`
(exacto). Sin residuo en el tenant real.

**Fase 13 (autoauditoria):** revision sistematica (bypass de aprobacion/limites, concurrencia, fuga
cross-tenant, duplicacion de logica, inconsistencias de estado, rutas duplicadas, Dashboard-como-
SSoT) -- sin hallazgos adicionales a los 2 ya corregidos arriba. Detalle completo:
`docs/approvals/APPROVALS_DESIGN.md` §12-16. `manage.py check`/`makemigrations --check --dry-run`
limpios.

## 2026-09-26/27 -- Pytest real ejecutado por el usuario: 4 bugs reales adicionales encontrados y corregidos

El usuario corrio la suite real (`apps/tenant/compras/tests`, `apps/tenant/compras/requisiciones/
tests`, `apps/tenant/approvals/tests`, `apps/tenant/dashboard/tests`, `apps/tenant/cotizaciones/
tests`) por primera vez desde que arranco esta mision -- expuso 4 bugs reales que ninguna
verificacion manual anterior (siempre con datos desechables ad-hoc) habia detectado:

1. **`_hoy()` con zona horaria incorrecta** (`apps/tenant/compras/requisiciones/models.py`):
   usaba `timezone.now().date()` (fecha calendario de UTC) en vez de `timezone.localdate()`. Con
   `TIME_ZONE='America/Bogota'` (UTC-5), entre las 19:00 y las 23:59 hora local esto adelantaba
   `fecha_solicitud` un dia completo, violando el check constraint
   `requisicion_compra_fecha_necesidad_gte_solicitud` para cualquier Requisicion con
   `fecha_necesidad=hoy`. Verificado en vivo: `date.today()`=26, `timezone.now().date()`=27,
   `timezone.localdate()`=26, exactamente durante esa ventana horaria.
2. **`crear_orden_compra()` no revertia la `OrdenCompra` ya insertada al rechazar por presupuesto**
   (`apps/tenant/compras/services/business_service.py`): Django NO revierte automaticamente una
   `transaction.atomic()` cuando la excepcion se captura DENTRO del mismo metodo decorado -- solo
   revierte si la excepcion escapa del bloque. El `except ValidationError as e: return False, ...`
   dejaba la `OrdenCompra` COMMITEADA huerfana pese a devolver `ok=False`. Corregido con
   `transaction.set_rollback(True)` explicito en ambos handlers (`ValidationError` y `Exception`)
   antes de retornar. Verificado: `OrdenCompra.objects.count()` volvio a dar 0 tras un rechazo por
   presupuesto.
3. **Related name obsoleto `ordenes_compra` en 4 lugares** tras el N:N de Fase 3 (el related_name
   real es `ordenes_compra_vinculadas`, definido en `OrdenCompraRequisicion.requisicion`):
   `RequisicionCompraCRUDService.eliminar_requisicion()` (rompia CUALQUIER intento de eliminar una
   Requisicion BORRADOR con `AttributeError`), `RequisicionCompraDetailSerializer.
   get_ordenes_compra_uuids()`, el `prefetch_related` de `RequisicionCompraSelector.get_detail()` y
   de `render_offcanvas_detalle` en el ViewSet, y el template `offcanvas_detalle_requisicion.html`.
   Todos corregidos a `ordenes_compra_vinculadas` (navegando `.orden_compra` donde corresponde).
4. **Tests con supuestos obsoletos** (nunca actualizados tras cambios de fases anteriores de esta
   misma mision, detectados solo al ejecutarlos): `test_orden_compra_requisicion_integracion.py`
   (una Requisicion BORRADOR ya no puede ni vincularse a una OC nueva -- rechazo temprano, no en
   la aprobacion posterior), `test_requisicion_compra_service.py` (2 asserts usaban el FK singular
   retirado `OrdenCompra.requisicion`/`orden.requisicion_id`, migrados a la traversal N:N
   `requisiciones_vinculadas__requisicion`), `test_approval_business_service.py` (un test de
   "creacion fresca" invocaba antes `enviar_a_aprobacion()`, que desde Fase 5 ya crea la solicitud
   como side-effect -- probaba idempotencia sin querer).

**Resultado final verificado por el usuario** (todo ejecutado, nada simulado): `apps/tenant/
compras/tests` 57 passed, `apps/tenant/compras/requisiciones/tests` 57 passed, `apps/tenant/
approvals/tests` 17 passed, `apps/tenant/dashboard/tests` 36 passed, `apps/tenant/cotizaciones/
tests` 70 passed. Los `SystemExit: 2`/`connection is closed` que aparecieron en la primera corrida
completa de `compras/tests` (38 min) no se repitieron corriendo los mismos archivos en lotes mas
pequenos ni en la corrida final completa (57 passed, sin errores) -- confirmado como contencion de
recursos/conexiones Postgres por el volumen de schemas `TenantTestCase` creados en una sola corrida
larga, no un defecto de codigo.

---

## 2026-09-12 — Fase 2 de remediación: CO-1, CO-2, CO-3, CO-4 (ALTO, `docs/remediation/AUDIT_BASELINE_20260912.md`)

**✅ Verificado.** `pytest apps/tenant/compras/tests/` completo → **43 passed** (suite preexistente, cero regresión) + `test_co1_plantillas_visibles.py` (1 caso) + `test_co3_co4_estado_endpoint.py` (3 casos) → **4 passed**. Detalle fila por fila en `docs/remediation/RELEASE_GATE_20260912.md`.

- **CO-1 — Plantillas con `vigente=False` invisibles en toda la UI.** No era un bug de API (`PlantillaOrdenCompraViewSet`/`PlantillaOrdenCompraSelector` ya filtraban correctamente por `empresa_id`) sino de UI: cero consumidores reales de `API.plantillas.list` — el único punto de acceso era el dropdown de "Nueva Orden", que fuerza `vigente_only=True`. **Fix**: pantalla de gestión nueva — `PlantillaOrdenCompraTable`/`PlantillaOrdenCompraTableView` (`tables.py`/`views.py`, mismo patrón django-tables2+HTMX ya usado por `OrdenCompraTable`), ruta `compras:plantillas-tabla`, panel nuevo en `compras_list.html`. Acciones por fila: Editar (nueva acción `render_offcanvas_editar` en `PlantillaOrdenCompraViewSet`, reutiliza `offcanvas_crear_plantilla.html` en modo edición) y Activar/Desactivar (`PATCH {vigente: bool}` sobre el endpoint ya existente, sin cambio de backend). El evento `plantilla-created` (antes sin ningún listener, hallazgo CO-8 del baseline) se unificó en `plantilla-changed`, ahora con listener real (refresca el panel).
- **CO-2 — Botón "Marcar Recibida" siempre devolvía 400.** `TRANSICIONES_VALIDAS['APROBADA']` (`business_service.py`) no incluye `RECIBIDA` desde que se introdujo el flujo de Recepciones (`RecepcionCompraBusinessService.confirmar_recepcion()`, sin UI propia por decisión documentada). El botón viejo nunca se limpió tras ese cambio. **Fix**: botón removido de `offcanvas_detalle_compras.html`, con comentario explicando cuándo reintroducirlo (cuando exista UI de Recepciones).
- **CO-3 — `estado` escribible en el serializer genérico bypaseaba la máquina de estados.** `OrdenCompraCreateUpdateSerializer` no marcaba `estado` como `read_only`; tanto `crear_orden()` como `actualizar_orden()` (`crud_service.py`) usan el valor de `data` tal cual sin pasar por `TRANSICIONES_VALIDAS` ni disparar `_sincronizar_cuenta_por_pagar()` — un `POST`/`PATCH` directo con `estado="APROBADA"` podía crear/dejar una orden "aprobada" sin Cuenta por Pagar generada. **Fix**: `estado` en `read_only_fields` (el modelo ya tiene `default='BORRADOR'`, la creación normal no cambia).
- **CO-4 — Transiciones (Aprobar/Anular) no actualizaban `updated_at`.** `OrdenCompraCRUDService.cambiar_estado()` hacía `orden.save(update_fields=['estado'])` — Django solo refresca un campo `auto_now=True` si está listado en `update_fields`. **Fix**: `update_fields=['estado', 'updated_at']`.

---

## 1. Descripcion General

El modulo de Compras gestiona el ciclo de vida de las Ordenes de Compra en un esquema SaaS multi-tenant estricto. Permite registrar solicitudes de compra de bienes/servicios a proveedores, con aprobacion, recepcion e integracion con Documentos Soporte o Gastos.

**Modelos:** `PlantillaOrdenCompra`, `OrdenCompra`, `ItemOrdenCompra`  
**URL base:** `/api/v1/compras/`  
**Tab workspace:** `#tab-compras` (`section#tab-compras` en workspace.html:110)

---

## 2. Modelos de Datos

### PlantillaOrdenCompra (`SintelTenantBaseModel`)
| Campo | Tipo | Notas |
|---|---|---|
| `uuid` | UUIDField | PK publica en API/URLs |
| `nombre` | CharField(100) | |
| `prefijo` | CharField(10) | Ej: OC, COM. Opcional. |
| `rango_desde` | IntegerField | Min 1 |
| `rango_hasta` | IntegerField | Min 1 |
| `consecutivo_actual` | IntegerField | Proximo numero a asignar |
| `vigente` | BooleanField | Filtro en selector de formulario |

**Metodos:** `formar_numero()`, `esta_en_rango()`  
**Validacion Python:** `clean()` verifica `rango_hasta >= rango_desde`  
**DT-COMPRAS-02:** Sin CheckConstraint DB — solo validacion Python.

**Indice:** `['empresa', 'vigente']`

### OrdenCompra (`SintelTenantBaseModel`)
| Campo | Tipo | Notas |
|---|---|---|
| `uuid` | UUIDField | PK publica |
| `plantilla` | FK PlantillaOrdenCompra | PROTECT, opcional |
| `consecutivo` | IntegerField | Autoasignado por plantilla |
| `numero_documento` | CharField(50) | Formado por plantilla: `prefijo-consecutivo` |
| `proveedor` | FK Proveedor | PROTECT, obligatorio |
| `proyecto` | FK Proyecto | SET_NULL, opcional |
| `documento_soporte` | FK DocumentoSoporte | SET_NULL, opcional |
| `fecha` | DateField | Emision |
| `fecha_entrega` | DateField | Opcional |
| `estado` | CharField | BORRADOR/PENDIENTE/APROBADA/RECIBIDA/ANULADA |
| `subtotal`, `impuestos`, `total` | DecimalField | Calculados desde items |
| `observaciones` | TextField | |

**Constraint:** `UniqueConstraint(['empresa', 'numero_documento'])` — unicidad por tenant  
**DT-COMPRAS-02:** Sin CheckConstraint para `fecha_entrega >= fecha`.  
**Indices:** `['empresa', 'fecha']`, `['empresa', 'estado']`

### ItemOrdenCompra (`SintelTenantBaseModel`)
| Campo | Tipo | Notas |
|---|---|---|
| `orden_compra` | FK OrdenCompra | CASCADE |
| `descripcion` | CharField(255) | |
| `item_inventario_uuid` | UUIDField | Soft ref a catalogo inventario, opcional |
| `cantidad`, `valor_unitario`, `porcentaje_iva` | DecimalField | Entradas del usuario |
| `valor_iva`, `subtotal`, `total` | DecimalField | Calculados en CRUDService |

---

## 3. Flujo de Estados

```
BORRADOR → PENDIENTE → APROBADA → RECIBIDA
    ↓           ↓          ↓
 ANULADA     ANULADA    ANULADA
```

| Estado | Edicion cabecera | Edicion items | Asociar DocSoporte |
|---|---|---|---|
| BORRADOR | Si | Si | No |
| PENDIENTE | Solo admin | No (bloqueado en CRUDService) | No |
| APROBADA | No | No | Si |
| RECIBIDA | No | No | No |
| ANULADA | No | No | No |

`CRUDService.actualizar_orden()` lanza `ValidationError` si `estado not in ['BORRADOR', 'PENDIENTE']`.

---

## 4. Arquitectura de Codigo (Service Layer FSD)

### 4.1 Selectors (`services/selectors.py`)

**`PlantillaOrdenCompraSelector`**
- `get_list(empresa_id, vigente_only=False)` → `.only(*PLANTILLA_LIST_FIELDS)`
- `get_detail(empresa_id, plantilla_uuid)` → `.only(*PLANTILLA_DETAIL_FIELDS)`
- `get_vigentes(empresa_id)` → solo plantillas con `vigente=True`

**`OrdenCompraSelector`**
- `get_list(empresa_id, search=None, estado=None)` → optimizado con:
  - `select_related('proveedor', 'proyecto', 'documento_soporte', 'plantilla')`
  - `.only(*ORDEN_COMPRA_LIST_FIELDS, *_PLANTILLA_TRAVERSALS, *_PROVEEDOR_TRAVERSALS, *_PROYECTO_TRAVERSALS, *_DOCUMENTO_SOPORTE_TRAVERSALS)`
  - **CORREGIDO 2026-06-18:** Se agregaron traversals de proveedor/proyecto/documento_soporte (antes causaban N+1 queries)
- `get_detail(empresa_id, orden_uuid)` → `select_related` + `prefetch_related('items')`
- `get_siguiente_consecutivo(empresa_id)` → `Max('consecutivo')` + 1

**Constantes SSoT (Zero-Collision):**
```python
ORDEN_COMPRA_LIST_FIELDS = ('id', 'uuid', 'consecutivo', 'numero_documento', 'plantilla_id',
    'fecha', 'fecha_entrega', 'estado', 'subtotal', 'impuestos', 'total',
    'empresa_id', 'proveedor_id', 'proyecto_id', 'documento_soporte_id')

_PLANTILLA_TRAVERSALS   = ('plantilla__uuid', 'plantilla__nombre', 'plantilla__prefijo')
_PROVEEDOR_TRAVERSALS   = ('proveedor__razon_social', 'proveedor__numero_documento')
_PROYECTO_TRAVERSALS    = ('proyecto__nombre',)
_DOCUMENTO_SOPORTE_TRAVERSALS = ('documento_soporte__numero_documento',)
```

### 4.2 CRUD Service (`services/crud_service.py`)

**`PlantillaOrdenCompraCRUDService`**
- `crear_plantilla(empresa, data)` — `full_clean()` + `save()`
- `actualizar_plantilla(plantilla, data)` — campos: nombre/prefijo/rango_desde/rango_hasta/consecutivo_actual/vigente
- `eliminar_plantilla(plantilla)` — bloquea si tiene ordenes asociadas

**`OrdenCompraCRUDService`**
- `crear_orden(data, items_data, empresa)` — crea cabecera, crea items con `bulk_create`, actualiza totales
- `actualizar_orden(orden, data, items_data)` — solo si estado BORRADOR/PENDIENTE; reemplaza items si se envian
- `cambiar_estado(orden, nuevo_estado)` — valida contra `ESTADO_CHOICES`
- `eliminar_orden(orden)` — solo si estado BORRADOR

### 4.3 Business Service (`services/business_service.py`)

**`_obtener_entidad_por_id_o_uuid(model_class, lookup_value, empresa_id)`**  
Helper DSV anti-IDOR. Soporta instancias del modelo (con verificacion `empresa_id`), objetos `uuid.UUID`, strings UUID, e integers.

**`_dsv_y_asignar_plantilla(empresa_id, plantilla_raw)`**  
- `select_for_update()` en PlantillaOrdenCompra para prevenir race conditions
- Valida: vigente=True, `esta_en_rango()`
- Asigna consecutivo y llama `formar_numero()`
- **DT-COMPRAS-01:** `consecutivo_actual += 1; save()` — seguro con `select_for_update`, pero patron no canonico (deberia usar `F('consecutivo_actual') + 1`)

**`crear_orden_compra(data, items_data, empresa)`**  
Flujo DSV 4 pasos:
1. DSV Plantilla (obligatorio) → asigna consecutivo
2. DSV Proveedor (obligatorio)
3. DSV Proyecto (opcional)
4. DSV DocumentoSoporte (opcional)
5. Delega a `OrdenCompraCRUDService.crear_orden()`

### 4.4 API Mixins (`services/api_mixins.py`)

- `PlantillaOrdenCompraServiceMixin` — CRUD simple sin business logic
- `OrdenCompraServiceMixin` — delega a `OrdenCompraBusinessService`; expone `service_crear_orden_compra`, `service_actualizar_orden_compra`, `service_cambiar_estado`, `service_eliminar_orden_compra`, `service_get_siguiente_consecutivo`

### 4.5 ViewSets (`api/viewsets.py`)

**`OrdenCompraViewSet`** (hereda `OrdenCompraServiceMixin`, `SintelDSVMixin`, `BaseTenantViewSet`)
- `lookup_field = "uuid"` (heredado de `BaseTenantViewSet`)
- `get_permissions()` → `[IsTenantMember(), IsTenantAdminOrReadOnly()]`  
  **CORREGIDO 2026-06-18:** Eliminado `if settings.DEBUG: return []` que bypasseaba toda autenticacion
- Acciones HTMX: `render_offcanvas/crear`, `render_offcanvas/editar`, `render_offcanvas/detalle`
- Accion extra: `cambiar-estado` (POST), `siguiente-consecutivo` (GET)

**`PlantillaOrdenCompraViewSet`** (hereda `PlantillaOrdenCompraServiceMixin`, `SintelDSVMixin`, `BaseTenantViewSet`)
- `get_permissions()` → `[IsTenantMember(), IsTenantAdminOrReadOnly()]`  
  **CORREGIDO 2026-06-18:** Mismo DEBUG bypass eliminado
- `get_object()` filtrado por `empresa_id` (anti-IDOR)

### 4.6 Serializers (`api/serializers.py`)

**`PlantillaOrdenCompraSerializer`** — fields: id, uuid, nombre, prefijo, `rango_desde`, `rango_hasta`, consecutivo_actual, vigente  
**`ItemOrdenCompraSerializer`** — fields: id, uuid, descripcion, item_inventario_uuid, cantidad, valor_unitario, porcentaje_iva, valor_iva, subtotal, total  
**`OrdenCompraListSerializer`** — fields aplanados: proveedor_nombre/nit, proyecto_nombre, plantilla_nombre, documento_soporte_numero  
**`OrdenCompraDetailSerializer`** — incluye items (many) + plantilla_uuid  
**`OrdenCompraCreateUpdateSerializer`** — `UUIDOrPKRelatedField` para plantilla/proveedor/proyecto/documento_soporte; valida `items` no vacio  
**`UUIDOrPKRelatedField`** — acepta UUID string o PK entero; DSV via `empresa_id` en context; retorna instancia del modelo

**DT-COMPRAS-03:** Sin validacion `fecha_entrega >= fecha` en `validate()` del serializer.

### 4.7 URLs (`api/urls.py`)

```python
router.register(r'plantillas', PlantillaOrdenCompraViewSet, basename='plantilla-orden-compra')
router.register(r'', OrdenCompraViewSet, basename='ordenes-compra')
```

Montado en `config/api_urls.py` bajo `compras/`.

---

## 5. UI y JavaScript

### 5.1 Template principal (`templates/tenant/compras/compras_list.html`)

Incluido en `workspace.html` bajo `<section id="tab-compras">`. Contiene:
- Toolbar con buscador (`#search-compra`) y boton "Nueva Orden" (HTMX GET)
- KPIs: `#kpi-total-ordenes`, `#kpi-monto-total`, `#kpi-aprobadas`, `#kpi-pendientes`
- Spinner: `[data-spinner="compras"]` (inicia oculto)
- Grid: `#grid-compras` (inicia oculto, revelado por JS)
- Container offcanvas: `#offcanvas-container-compras`
- Modal confirmacion eliminar: `#confirmarEliminarModalCompras`

**CORREGIDO 2026-06-18:** Eliminada doble inclusion de `assets_compras.html` que causaba ejecucion doble de los 4 scripts JS. Los assets se cargan solo desde `workspace.html extra_js` (linea 304).

### 5.2 Assets (`templates/tenant/compras/assets_compras.html`)

Cargado UNICAMENTE desde `workspace.html extra_js`:
1. `compras.api.js` — SSoT endpoints + `getHeaders()`
2. `compras.utils.js` — cache de proveedores/proyectos (5 min TTL)
3. `features/compras_list.js` — Tabulator grid + KPIs + event delegation
4. `features/compras_editor.js` — formulario dinamico de items

### 5.3 compras.api.js (`static/compras/js/compras.api.js`)

Namespace: `window.Sintel.Compras.API`

**Endpoints:**
```javascript
API.compras.list          // '/api/v1/compras/'
API.compras.detail(uuid)  // '/api/v1/compras/{uuid}/'
API.compras.cambiarEstado(uuid)  // '/api/v1/compras/{uuid}/cambiar-estado/'
API.compras.create(data)  // POST
API.compras.update(uuid, data)  // PATCH
API.cambiarEstado(uuid, estado) // POST con confirmacion
API.eliminar(uuid)        // DELETE
API.endpoints.renderCrear()
API.endpoints.renderEditar(uuid)
API.endpoints.renderDetalle(uuid)
```

`getHeaders()` — JWT via `window.jwtAuth.getValidAccessToken()`  
**CORREGIDO 2026-06-18:** CSRF ahora leido desde cookie (`getCookie('csrftoken')`) en lugar de `document.querySelector('[name=csrfmiddlewaretoken]')` que retornaba `null` antes de abrir el offcanvas.

### 5.4 compras.utils.js (`static/compras/js/compras.utils.js`)

Namespace: `window.Sintel.Compras.Utils`

- `loadProveedoresSelect(selector, selectedValue, placeholder)` — carga `/api/v1/proveedores/` con cache 5 min
- `loadProyectosSelect(selector, selectedValue, placeholder)` — carga `/api/v1/proyectos/` con cache 5 min
- `invalidateCache(which)` — limpia cache selectiva o total

### 5.5 compras_list.js (`static/compras/js/features/compras_list.js`)

Namespace: `window.Sintel.Compras.ComprasList` (alias: `window.Sintel.Compras.List`)

**Anti-zombie:** Destruye `w.SintelComprasTables` al inicio del modulo.

**`ComprasList.init(retryCount=0)`**
- Guarda: `_initializing = true` (previene doble init)
- 5 reintentos si TabulatorFactory no disponible (500ms cada uno)
- TabulatorFactory.create con `ajaxParams` NO es funcion (no hay filtro por estado, carga todo)
- `searchInputSelector: '#search-compra'` — debounce 300ms integrado en factory

**KPIs:** Calculados en `dataLoaded` y `dataFiltered` desde los datos del grid.

**Event delegation en `#grid-compras`:**
- `.btn-view-compra` → `ComprasList.verDetalle(uuid)` → HTMX GET `render-offcanvas/detalle/`
- `.btn-edit-compra` → `ComprasList.editarCompra(uuid)` → HTMX GET `render-offcanvas/editar/`
- `.btn-delete-compra` → `ComprasList.eliminarCompra(uuid)` → DELETE con confirmacion

**Event delegation en `#offcanvas-container-compras`:**
- `.btn-cambiar-estado` → `cambiarEstado(uuid, estado)` → cierra offcanvas + refresh

**HTMX hooks:**
- `htmx:afterSettle` en `document.body` → abre Bootstrap Offcanvas sobre el nuevo elemento HTML
- `htmx:beforeCleanupElement` → **CORREGIDO 2026-06-18:** `instance.dispose()` (eliminacion inmediata de backdrop) en lugar de `instance.hide()` (animacion que no completaba → backdrops acumulados)

**CORREGIDO 2026-06-18:** Agregado listener `tab-activated` para `redraw(true)` al volver al tab, o `init()` si la tabla aun no existe.

**Eventos reactivos:** Escucha `compra-created` y `compra-updated` en `document.body` → `refresh()`.

### 5.6 compras_editor.js (`static/compras/js/features/compras_editor.js`)

Inicializado via evento `compra-editor-init` disparado desde `htmx:afterSettle` (compras_list.js) o desde `loadAndShowOffcanvas()`.

**Ciclo de vida:**
1. `initializeEditor(form)` — lee `data-mode` y `data-uuid` del `<form>`
2. Carga proveedores y proyectos via `compras.utils.js` (con cache)
3. Bindea filas existentes (modo edicion) o agrega primera fila vacia (modo crear)
4. Configura selector de plantilla con info de rango disponible
5. `handleFormSubmit(e, form)` → `recolectarDatos(form)` → POST o PATCH

**Payload enviado al crear:**
```javascript
{
  plantilla: uuid,  // solo en create
  fecha, fecha_entrega, proveedor, proyecto, observaciones,
  items: [{ descripcion, item_inventario_uuid, cantidad, valor_unitario, porcentaje_iva }]
}
```

**Validacion frontend:** Al menos 1 item con descripcion; verificacion visual si plantilla agotada.

---

## 6. Flujo de Carga workspace/#compras

```
DOMContentLoaded
  ├─► workspace.js: showTab('compras') si hash=#compras
  │     → dispatchEvent('tab-activated', {tabName:'compras'})
  │         → compras_list.js: tab-activated handler
  │               → ComprasList.init() si tabla no existe
  │               → tabla.redraw(true) si ya existe [CORREGIDO]
  │
  ├─► compras_list.js DOMContentLoaded listener
  │     → setup() → ComprasList.init() [guard _initializing previene doble]
  │
  └─► Usuario click "Nueva Orden"
        → HTMX GET /api/v1/compras/render-offcanvas/crear/
        → hx-swap="innerHTML" en #offcanvas-container-compras
        → htmx:beforeCleanupElement → instance.dispose() [CORREGIDO]
        → htmx:afterSettle → new Offcanvas(el).show()
        → dispatchEvent('compra-editor-init', {form})
        → compras_editor.js: initializeEditor(form)
```

---

## 7. Migraciones

| Migracion | Contenido |
|---|---|
| `0001_init_compras.py` | OrdenCompra + ItemOrdenCompra inicial |
| `0002_plantillaordencompra_and_more.py` | PlantillaOrdenCompra + FK plantilla en OrdenCompra |

---

## 8. Registro de Correcciones (2026-06-18)

| ID | Severidad | Archivo | Descripcion | Estado |
|---|---|---|---|---|
| BUG-01 | CRITICO | `compras_list.html:122` | Doble carga de `assets_compras.html` — scripts ejecutaban 2 veces | CORREGIDO |
| BUG-02 | CRITICO | `compras.api.js:117` | CSRF leido de DOM (null antes de abrir offcanvas) → headers invalidos en DELETE/cambiar-estado | CORREGIDO |
| BUG-03 | CRITICO | `compras_list.js:491` | `instance.hide()` en `htmx:beforeCleanupElement` → backdrop no se limpiaba → pantalla negra en 2do open | CORREGIDO |
| BUG-04 | CRITICO | `viewsets.py:51,248` | `if settings.DEBUG: return []` bypasseaba toda autenticacion y aislamiento de tenant | CORREGIDO |
| BUG-05 | ALTO | `selectors.py:82-85` | `select_related` sin traversals en `.only()` → N+1 queries para proveedor/proyecto/documento_soporte | CORREGIDO |
| BUG-06 | ALTO | `compras_list.js` | Sin listener `tab-activated` → Tabulator no redibujaba al volver al tab | CORREGIDO |

---

## 9. Deuda Tecnica — RESUELTA 2026-06-18

| ID | Severidad | Descripcion | Archivo | Estado |
|---|---|---|---|---|
| DT-COMPRAS-01 | MEDIA | `plantilla.consecutivo_actual += 1; save()` → cambiado a `F('consecutivo_actual') + 1` con `.update()` | `business_service.py:121` | RESUELTO |
| DT-COMPRAS-02 | MEDIA | `CheckConstraint` DB agregado en `PlantillaOrdenCompra` (`rango_hasta >= rango_desde`, `consecutivo_actual >= rango_desde`) y en `OrdenCompra` (`fecha_entrega >= fecha`). Migracion `0003_add_check_constraints_compras.py` aplicada. | `models.py` | RESUELTO |
| DT-COMPRAS-03 | BAJA | `validate()` agregado a `OrdenCompraCreateUpdateSerializer` validando `fecha_entrega >= fecha` | `serializers.py` | RESUELTO |

---

## 10. Bridge Compras -> Proveedores: sincronizacion de Cuentas por Pagar (2026-08-26)

**Hallazgo real:** reportado en vivo por el usuario — una compra creada en el
tenant `home` (`OC-QA-1`) no aparecia en `workspace/#proveedores` > Cuentas
por Pagar. Auditoria confirmo `CuentasPagar` con 0 registros en toda la
historia del tenant: el unico llamador de
`CuentasPagarBusinessService.registrar_cuenta_pagar()` era el endpoint
manual `POST /api/v1/proveedores/cuentas-pagar/`. Ningun flujo de Compras
lo disparaba (mismo patron confirmado, simetricamente, en
`clientes.Cartera` — tampoco tiene trigger automatico desde Ventas).

**Fix:** `OrdenCompraBusinessService.cambiar_estado_orden_compra()`
(`services/business_service.py:339`) ahora llama a
`_sincronizar_cuenta_por_pagar(orden)` cuando `nuevo_estado == 'APROBADA'`.
Decision explicita del usuario: el punto de reconocimiento de la obligacion
es la aprobacion de la orden, no la recepcion ni la existencia de una
Factura DIAN (la mayoria de compras de este ERP no generan factura
electronica).

```python
orden = OrdenCompraCRUDService.cambiar_estado(orden, nuevo_estado)
if nuevo_estado == 'APROBADA':
    OrdenCompraBusinessService._sincronizar_cuenta_por_pagar(orden)
```

`_sincronizar_cuenta_por_pagar()` importa `CuentasPagarBusinessService`
localmente dentro del metodo (mismo patron de bridge cross-app que
`RecepcionCompraBusinessService.confirmar_recepcion()` usa para Inventario).
Construye `numero_factura = orden.numero_documento or f"OC-{consecutivo}"`,
`fecha_vencimiento = orden.fecha + proveedor.plazo_pago_dias`, y pasa
`orden_compra_uuid=orden.uuid` (campo nuevo en `CuentasPagar`, migracion
`proveedores/0019`, soft reference sin FK — mismo patron que `factura_uuid`).

**Idempotente:** `registrar_cuenta_pagar()` hace `get_or_create()` sobre
`(empresa, proveedor, numero_factura)` — reaprobar o reintentar no duplica.

**Fuera de alcance deliberado:** si la orden se anula despues de aprobada,
la CxP ya generada no se reversa automaticamente (mismo criterio que
`anular_recepcion()`, que tampoco reversa `MovimientoInventario` de una
recepcion CONFIRMADA — ver `services/business_service.py`,
`RecepcionCompraBusinessService.anular_recepcion()`).

Tests: `apps/tenant/compras/tests/test_sincronizacion_cuentas_pagar.py`.

---

## 12. Vista dinámica por menú (2026-09-15)

`compras_list.html` pasó de mostrar "Órdenes de Compra" y "Plantillas de Numeración" como 2 cards
siempre visibles y apiladas, a un menú de pestañas (`nav-pills`, mismo patrón que
Clientes/Proveedores) — clic en cada pestaña muestra solo esa lista. Cambio de solo-template,
sin tocar `views.py`/`urls.py`/`tables.py` ni backend: cada tab conserva su propio panel HTMX
(`#compras-panel` / `#plantillas-panel`) con los mismos `hx-get`/`hx-trigger` de antes. Sin
verificación visual en navegador real en esta pasada (sin acceso a browser interactivo).

## 11. Reglas de Mantenimiento

1. **Agregar traversal al selector** cuando se agregue un campo `source='fk__campo'` en un serializer list.
2. **Nunca `new bootstrap.Offcanvas(el)` mas de una vez** por elemento — el `htmx:beforeCleanupElement` llama `dispose()` antes de cada swap.
3. **No usar `if settings.DEBUG: return []`** en `get_permissions()` — rompe el aislamiento multi-tenant en desarrollo.
4. **Assets** cargados UNICAMENTE en `workspace.html extra_js` — no incluir `assets_compras.html` en templates de listado.
5. **`ajaxParams` como funcion** si se agrega filtro por estado al grid (ver patron en ventas: `function() { return _filtroEstado ? {estado: _filtroEstado} : {}; }`).

## 13. Integracion con Proyectos (2026-10-02)

`PLAN_INTEGRACION_PROYECTOS_ORDENES_COMPRA_VENTA_OPCIONAL.md`: `OrdenCompra.proyecto`
(FK ya existente, ver `models.py`) ahora se asigna EXCLUSIVAMENTE via
`ProjectOrderAssignmentService.asociar_orden_a_proyecto()`
(`services/project_assignment_service.py`) cuando el flujo viene desde el
bloque "Ordenes de Compra" del detalle de Proyecto. Reglas: Orden debe estar
`APROBADA`, Proyecto debe estar en fase `BORRADOR`, idempotente si ya esta
asociada al mismo Proyecto, rechazada (nunca sobrescrita) si ya pertenece a
otro Proyecto. Direccion de dependencia: compras -> proyectos (el servicio
vive aqui, Proyecto solo consulta via import local — nunca al reves).

La edicion directa del campo `proyecto` en `OrdenCompraBusinessService.
crear_orden_compra()`/`actualizar_orden_compra()` (DSV de solo
empresa_id, sin las reglas de estado/fase arriba) se mantiene intacta para no
romper el flujo existente de asignacion manual desde el formulario de
Compras — es una via distinta y mas permisiva, deliberadamente no unificada
en esta fase (el plan la señala como mejora futura opcional, Paso 12.2).

Selectores nuevos en `OrdenCompraSelector`: `get_disponibles_para_proyecto()`
(APROBADA + sin proyecto + alcance organizacional), `get_by_proyecto()`
(anota `valor_recibido` via SQL) y `get_resumen_proyecto()` (agregacion
cantidad/comprometido/recibido/pendiente). Consumidos desde
`apps/tenant/proyectos/api/viewsets.py::ProyectoViewSet` (`ordenes_compra`,
`ordenes_compra_disponibles`, `ordenes_compra_asociar`).
