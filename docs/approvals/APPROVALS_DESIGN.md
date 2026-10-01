# APPROVALS_DESIGN.md — Motor Generico de Solicitudes de Aprobacion

**Mision:** `PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md` (raiz del repo). Pedido explicito del
usuario 2026-09-26, tras detectar que el diseno anterior de "Orden de Compra obligatoria" (FK
unico `OrdenCompra.requisicion` + escape `es_excepcional`, implementado y retirado el mismo dia)
no soportaba consolidar varias Requisiciones en una sola OC. Fases 1-4 (fundamento) y Fase 5
(enganche real de enviar/aprobar/rechazar) completadas el mismo dia -- Centro de Aprobaciones en
Dashboard sigue sin construir (Fase 7/8).

## 1. Alcance de esta entrega

Solo modelos + Service Layer de `apps/tenant/approvals/` (`SolicitudAprobacion`,
`SolicitudAprobacionHistorial`, `ApprovalBusinessService`), la relacion N:N
`OrdenCompraRequisicion` en Compras, y el control financiero
`ProcurementBudgetControlService`. **Sin API ni UI nueva.** El enganche real (Requisicion ->
`enviar_a_aprobacion()` creando una `SolicitudAprobacion`, el Centro de Aprobaciones del
Dashboard, `ApprovalTraceService`/grafo visual) es Fase 5+ del plan original, DEFERRED explicito.

## 2. Por que una app nueva y propia

`SolicitudAprobacion` es su propio dominio (`#37` del plan: "Approval SSoT = workflow de
aprobacion"), no una tabla mas de Compras ni de Requisiciones -- debe poder aprobar Cotizaciones u
Ordenes de Compra en el futuro sin reestructurar nada. Vive en `apps/tenant/approvals/`
(`app_label='tenant_approvals'`), FSD completo (models/services), registrada en `TENANT_APPS`.

## 3. Registry explicito, no GenericForeignKey

`#9` del plan es explicito: "Preferir un registry explicito" -- nunca `GenericForeignKey` (riesgo
de fuga cross-tenant si el resolver no filtra por `empresa_id`, ver auditoria previa de este
mismo riesgo en otras partes del proyecto). `TIPO_DOCUMENTO_REGISTRY`
(`apps/tenant/approvals/services/business_service.py`) mapea `'REQUISICION'` a 3 funciones
(`resolver`/`aprobar`/`rechazar`) que hacen DSV real contra el modelo correspondiente. Agregar
`'COTIZACION'`/`'ORDEN_COMPRA'` en el futuro es una entrada nueva en ese dict, sin tocar
`SolicitudAprobacion` ni el resto del Service Layer.

`objeto_uuid` es una soft-reference simple (`UUIDField`, sin FK) -- mismo patron que el resto del
proyecto ya usa para referencias cross-dominio (`RequisicionDocumento.documento_uuid`,
`Factura.cotizacion_uuid`, `ItemOrdenCompra.item_inventario_uuid`/`requisicion_item_uuid`).

## 4. Nunca escribir el estado del dominio directamente (`#26`)

`ApprovalBusinessService.aprobar()`/`rechazar()` **delegan** la transicion real al
BusinessService del dominio resuelto via el registry (`RequisicionCompraBusinessService.
aprobar_requisicion()`/`rechazar_requisicion()`, ya existentes) -- nunca
`objeto.estado = "APROBADA"` desde este servicio. Esto significa que toda la validacion de
transiciones/permisos/DSV que ya vive en Requisiciones se reutiliza sin duplicarse.

## 5. Idempotencia

- **Crear:** `crear_solicitud()` reutiliza una `SolicitudAprobacion` `PENDIENTE` existente para el
  mismo `(tipo_documento, objeto_uuid)` en vez de duplicar -- reforzado con un
  `UniqueConstraint` condicional a nivel de BD (`unique_solicitud_pendiente_por_documento`,
  `condition=Q(estado='PENDIENTE')`).
- **Decidir (`#28`):** `aprobar()`/`rechazar()` usan `select_for_update()` sobre la solicitud; si
  ya no esta `PENDIENTE`, devuelven la solicitud tal cual (sin re-ejecutar la transicion del
  dominio ni duplicar el historial) -- doble clic o carrera de concurrencia nunca duplica efectos.

## 6. N:N OrdenCompra <-> RequisicionCompra

Reemplaza el FK unico + escape `es_excepcional` (`#3` del plan: "No resolver esto con un FK
unico", "la excepcion no debe seguir funcionando para nuevas OC"). `OrdenCompraRequisicion`
(`apps/tenant/compras/models.py`) con `monto_asignado` por fila -- una OC puede consolidar varias
Requisiciones, y una Requisicion puede consumirse en varias OC mientras tenga saldo.
`crear_orden_compra()` exige `len(requisiciones) >= 1` sin excepcion posible, valida cada una via
DSV + estado disponible para compra, y reparte el total de la orden proporcional al
`total_estimado` de cada requisicion (salvo montos explicitos) via
`ProcurementBudgetControlService.repartir_monto_proporcional()`.

Trazabilidad por linea (`#4` del plan): `ItemOrdenCompra.requisicion_item_uuid` (soft-reference,
igual patron que `item_inventario_uuid`) -- el flujo `crear_orden_desde_requisicion()` ya recibia
este dato por linea, solo faltaba persistirlo.

**Migracion de esquema:** `apps/tenant/compras/migrations/0012_ordencomprarequisicion_and_more.py`
quita `requisicion`/`es_excepcional`/`motivo_excepcion` de `OrdenCompra` sin backfill -- 0 filas
reales los usaban al momento del cambio (verificado, tenant `admin`, 1 sola `OrdenCompra` real sin
ninguno de esos 3 campos poblado).

## 7. Control financiero (`ProcurementBudgetControlService`)

`apps/tenant/compras/services/budget_control_service.py` -- "una regla, una implementacion,
muchos consumidores" (`#20`). `obtener_saldo_cotizacion()`/`obtener_saldo_requisicion()` calculan
saldo real contra la BD (nunca cacheado); `validar_consolidacion_oc()` bloquea si algun monto
asignado excede el saldo de su Requisicion (`#23`/`#24`) -- unico consumidor real por ahora:
`crear_orden_compra()`, dentro de la misma `transaction.atomic()` (rollback completo si el
presupuesto no alcanza, incluida la `OrdenCompra` ya insertada).
`validar_requisicion_contra_cotizacion()` existe y esta listo para el enganche real en la
aprobacion de Requisicion -- Fase 5, DEFERRED, sin caller todavia.

Estados considerados "activos" para efectos de saldo (`#19`, verificado contra el codigo real, no
una hipotesis sin validar): Requisicion -- todos menos `RECHAZADA`/`CANCELADA`/`BORRADOR`; Orden
de Compra -- todos menos `ANULADA`.

## 8. Fase 5 (2026-09-26) — Enganche real: enviar / aprobar / rechazar / snapshot / revalidacion

`RequisicionCompraBusinessService.enviar_a_aprobacion()` ahora crea la `SolicitudAprobacion` real
(dentro de la misma `transaction.atomic()` que la transicion de estado -- nunca queda una
requisicion en `PENDIENTE_APROBACION` sin su solicitud) via `ApprovalBusinessService.
crear_solicitud()`, que calcula el snapshot automaticamente (`entry['snapshot'](objeto)` del
registry, `_snapshot_requisicion()`: valor, numero, tipo, cotizacion de origen, proyecto, cantidad
de lineas -- #13 del plan).

**Quien cierra la solicitud, y por que sin duplicar historial:** el camino real HOY (boton
"Aprobar"/"Rechazar" de la UI de Requisiciones) sigue llamando a
`RequisicionCompraBusinessService.aprobar_requisicion()`/`rechazar_requisicion()` DIRECTO -- no
hay Centro de Aprobaciones todavia que pase por `ApprovalBusinessService`. Para que la
`SolicitudAprobacion` nunca quede huerfana en `PENDIENTE` sin importar el camino, `aprobar_
requisicion()`/`rechazar_requisicion()` cierran ellos mismos su propia solicitud (si existe) como
ultimo paso de la transaccion (`_cerrar_solicitud_aprobacion_si_existe()`, best-effort: un fallo
ahi nunca bloquea la transicion real del dominio). Cuando el futuro Centro de Aprobaciones llame
`ApprovalBusinessService.aprobar()`/`rechazar()` en su lugar, este metodo:
1. Revalida el snapshot contra el estado actual del documento (bloquea con 409
   `documento_modificado` si cambio desde el envio).
2. Delega al BusinessService del dominio (que cierra su propia solicitud, ver arriba).
3. Vuelve a leer la solicitud de la BD -- si el dominio ya la cerro, NO vuelve a escribir
   (evita duplicar el historial); si por algun motivo no la cerro (dominio antiguo sin este
   side-effect), la cierra el mismo como fallback.

Verificado end-to-end contra el tenant `admin` real (datos desechables, limpiados despues): crear
-> enviar (solicitud PENDIENTE con snapshot real) -> aprobar directo (domain) -> solicitud
APROBADA, 2 eventos de historial (CREADA + APROBADA, sin duplicar); mismo flujo via
`ApprovalBusinessService.aprobar()` -- identico resultado, sin duplicar; snapshot corrompido a
proposito -> aprobacion bloqueada 409, requisicion permanece en `PENDIENTE_APROBACION`.

## 9. Fase 6 (2026-09-26) — ApprovalTraceService (trazabilidad, solo lectura)

`apps/tenant/approvals/services/trace_service.py::ApprovalTraceService.construir_trazabilidad()`
implementa el contrato exacto de `#16` del plan: `Solicitud -> resolver documentos relacionados ->
construir nodos -> construir relaciones -> calcular resumen -> retornar DTO`. Nunca escribe en
dominios ajenos -- solo `select_related`/queries de lectura.

DTO (`dict` plano, JSON-serializable): `{request, origin, nodes, relations, timeline,
financial_summary, alerts}`, tal como especifica `#16`. Para `tipo_documento='REQUISICION'`
(unico soportado hoy):
- **nodes/relations**: REQUISICION (origen del grafo) + COTIZACION (via `RequisicionCotizacion`
  `tipo_relacion='ORIGEN'`) + PROYECTO (si tiene) + ORDEN_COMPRA por cada
  `OrdenCompraRequisicion` vinculada (N:N de Fase 3).
- **timeline**: merge de `SolicitudAprobacionHistorial` + `RequisicionHistorialEstado` (las 2
  unicas fuentes reales de historial append-only involucradas -- no se invento un tercer modelo
  de eventos), ordenado por fecha.
- **financial_summary/alerts**: unica fuente de calculo es `ProcurementBudgetControlService`
  (Fase 4) -- nunca reimplementado aqui. Alerta `ROJO` si el saldo de la requisicion o de su
  cotizacion de origen queda negativo.

Agregar `COTIZACION`/`ORDEN_COMPRA` como `tipo_documento` propio en el futuro es una rama nueva en
`construir_trazabilidad()`, sin tocar el contrato del DTO ni el resto del servicio.

Verificado end-to-end contra el tenant `admin` real (datos desechables, limpiados despues): DTO
completo con 3 nodos (Requisicion/Cotizacion/Proyecto), 2 relaciones, timeline de 2 fuentes
correctamente ordenado, resumen financiero con saldos exactos, sin alertas (dentro de
presupuesto). Tests nuevos en `apps/tenant/approvals/tests/test_approval_trace_service.py`
(incluye caso con Orden de Compra generada y caso de alerta por exceso de saldo).

## 10. DEFERRED explicito -- unico item real que queda fuera de esta mision

- `validar_requisicion_contra_cotizacion()` sin caller (bloqueo real al aprobar una Requisicion
  si excede el saldo de su Cotizacion -- el metodo existe desde Fase 4, listo para engancharse en
  `aprobar_requisicion()`). Decision explicita: el control real de esta mision se hace en el punto
  de CONSOLIDACION (crear una OC no puede exceder el saldo de la Requisicion/Cotizacion, Fase 3/4,
  verificado en Fase 11), que es donde el dinero realmente se compromete; bloquear tambien en el
  momento de APROBAR la Requisicion es una capa adicional de alerta temprana, no un requisito de
  integridad financiera -- se deja fuera para no inventar una segunda regla de bloqueo no pedida
  explicitamente. Notificaciones (`#35` del plan) y alertas visuales configurables en UI (mas alla
  de los 3 niveles fijos ya implementados en Fase 8) tambien quedan fuera por el mismo criterio:
  no pedidas explicitamente, sin infraestructura de notificaciones transversal existente en el
  proyecto para reutilizar (habria que inventarla, fuera de alcance).

Todo lo demas del plan original (Fases 0-13, incluida la UI completa del Centro de Aprobaciones)
esta implementado -- ver `#12` en adelante.

## 11. Fase 7 (2026-09-26) — API del Centro de Aprobaciones

`apps/tenant/approvals/api/` (`SolicitudAprobacionViewSet`) expone en solo lectura + acciones de
workflow -- nunca create/update/destroy directo (`#26`: la solicitud solo nace como side-effect de
`enviar_a_aprobacion()`, Fase 5). Montado en `/api/v1/dashboard/aprobaciones/`
(`config/api_urls.py`) -- path conceptual de `#31` del plan aunque el codigo vive en
`apps.tenant.approvals` (dueno real del dominio, `#37`: Dashboard es solo presentacion/control).

**Orden de registro en `config/api_urls.py`:** `dashboard/aprobaciones/` se registra ANTES de
`dashboard/` -- mismo motivo, y mismo bug real encontrado y corregido en vivo, que ya documentaba
el comentario de `compras/requisiciones/` vs `compras/`: el router de `DashboardViewSet` tiene un
patron de detalle (`lookup_field='uuid'`, sin restriccion de formato) que capturaba
`/dashboard/aprobaciones/` como si `"aprobaciones"` fuera un `uuid` de dashboard, devolviendo
`dashboard-detail` en vez de nunca llegar a `SolicitudAprobacionViewSet`. Verificado con
`get_resolver('config.urls_tenant').resolve(path)` antes y despues del fix.

**Permisos (`#29`):** `[IsTenantMember, IsTenantAdmin, HasOrganizationalScope]` -- mismo patron ya
usado en `DashboardViewSet.invalidar_cache`, solo ADMIN accede al Centro de Aprobaciones.

**Endpoints:**
- `GET /api/v1/dashboard/aprobaciones/?estado=&tipo_documento=` -- bandeja (lista todas por
  defecto, no solo `PENDIENTE`; el filtro de "vista por defecto" es responsabilidad del futuro
  consumidor de UI, Fase 8).
- `GET /api/v1/dashboard/aprobaciones/{uuid}/` -- detalle + historial embebido.
- `GET /api/v1/dashboard/aprobaciones/{uuid}/trazabilidad/` -- DTO completo de
  `ApprovalTraceService` (Fase 6).
- `POST /api/v1/dashboard/aprobaciones/{uuid}/aprobar/` (`{observacion}`) -- delega a
  `ApprovalBusinessService.aprobar()`.
- `POST /api/v1/dashboard/aprobaciones/{uuid}/rechazar/` (`{motivo}`, requerido, 422 si falta) --
  delega a `ApprovalBusinessService.rechazar()`.

**Segundo endpoint de esta fase (`#32` del plan):**
`GET /api/v1/compras/requisiciones/disponibles-para-orden/` -- nuevo `@action` en el
`RequisicionCompraViewSet` ya existente (no una app nueva: el dato pertenece a Requisiciones).
Reutiliza `RequisicionCompraSelector.get_available_for_purchase()` (ya existia, Fase 0) +
`ProcurementBudgetControlService.obtener_saldo_requisicion()` (Fase 4, unico calculo de saldo,
`#20`) por fila. Devuelve `uuid/numero_documento/cotizacion/proyecto/valor_total/
valor_comprometido/saldo/estado` -- el contrato exacto de `#32`.

Verificado end-to-end contra el tenant `admin` real (datos desechables, limpiados despues, via
`APIRequestFactory` + `force_authenticate` -- ejercita el ViewSet/serializers reales, no solo el
Service Layer): crear Requisicion+Cotizacion -> enviar a aprobacion -> `GET lista` (aparece
PENDIENTE) -> `GET trazabilidad` (DTO completo) -> `POST create` (bloqueado, 405) -> `POST
aprobar` (200, requisicion y solicitud pasan a APROBADA, historial exacto `CREADA`+`APROBADA` sin
duplicar) -> `GET disponibles-para-orden` (aparece con `saldo == valor_total`, `valor_comprometido
== 0`). Sin residuo en el tenant real al terminar.

## 12. Fase 8 (2026-09-26) — Dashboard: banner, KPIs, bandeja, filtros

**Prioridad/riesgo real, calculado y congelado al enviar (nunca en JS, `#34` del plan):**
`ApprovalBusinessService._calcular_riesgo_requisicion()` calcula `% de la Cotizacion de origen ya
comprometido por TODAS sus Requisiciones activas` (incluyendo la que se esta enviando) en el
momento de `enviar_a_aprobacion()` -- una Requisicion que satura el presupuesto de su Cotizacion es
mas critica que una con margen amplio, independientemente de su propio valor absoluto. Umbrales
documentados como constantes de backend (`RIESGO_UMBRAL_ALTO=0.90`, `RIESGO_UMBRAL_MEDIO=0.60`),
mapeados 1:1 a `SolicitudAprobacion.Prioridad` (ALTA/MEDIA/BAJA = 🔴/🟠/🟢 del banner, `#6`). El
`riesgo_pct` se agrega al `snapshot_financiero` (ya existente desde Fase 5, `#13`) -- la bandeja lee
ese valor congelado, sin recalcular saldos en vivo por fila (evita N+1 real en un listado que puede
crecer). Consecuencia documentada de esta decision: el riesgo mostrado en la bandeja refleja el
presupuesto AL MOMENTO DEL ENVIO, no el saldo actual -- la vista de detalle (`trazabilidad`, Fase 6)
si es 100% en vivo, por eso el usuario siempre revisa el detalle antes de decidir.

**Backend nuevo:**
- `SolicitudAprobacionSelector.get_resumen(empresa_id)` -- unica fuente de los numeros del banner/
  KPIs (`#6`/`#7` del plan: "Todos los numeros deben provenir del backend"): pendientes, criticas/
  riesgo/normales (por prioridad, solo PENDIENTE), aprobadas hoy, rechazadas, valor pendiente (suma
  de `snapshot_financiero.valor`), antiguedad promedio/maxima en horas.
- `GET /api/v1/dashboard/aprobaciones/resumen/` -- expone lo anterior.
- `POST /api/v1/dashboard/aprobaciones/dt/` -- bandeja server-side (DataTables 3.x, mismo patron
  que `RequisicionCompraViewSet.dt()`, `#7`/`#8` del plan: "No cargar todo al navegador"). Columnas:
  Prioridad/Tipo/Documento/Solicitante/Proyecto/Origen/Valor/Riesgo/Tiempo Pendiente/Estado/Accion.
  Filtros por columna (Prioridad/Tipo/Estado, EXACT) + busqueda global sobre `snapshot_financiero`
  (numero/cotizacion/proyecto, JSONField key lookup nativo de Django, verificado en vivo).
  `SolicitudAprobacionListSerializer` ahora expone `snapshot_financiero` completo y
  `tiempo_pendiente_horas` (calculado, solo si PENDIENTE) -- sin una segunda consulta por fila.

**Frontend nuevo** (`apps/tenant/approvals/static/approvals/js/{approvals.api,features/
centro_aprobaciones}.js`, `apps/tenant/dashboard/templates/tenant/dashboard/partials/
centro_aprobaciones.html`): banner con pills 🔴/🟠/🟢, 6 tarjetas KPI, bandeja DataTables 3.x
(reutiliza `w.Sintel.Core.DataTablesFactory`, mismo factory que Requisiciones/Ordenes de Compra),
2 filtros (`estado`, `prioridad`) wireados a `DataTablesFactory.columnSearch()`. La seccion completa
queda oculta (`hidden`) si el backend responde 403 (usuario no-ADMIN, `#29`) -- nunca se asume el rol
en el frontend. Incluida en `list_dashboard.html` (Dashboard sigue sin modelos/logica propia, ver
`apps/tenant/dashboard/.agent/AUDITORIA_FLUJO_DASHBOARD.md`).

Verificado end-to-end contra el tenant `admin` real (datos desechables, limpiados despues): una
Requisicion que consume 95% del saldo de su Cotizacion se envia a aprobacion -> `prioridad=ALTA`
calculada correctamente, `riesgo_pct=0.95` en el snapshot; `GET resumen` cuenta 1 critica; `POST dt`
con busqueda global por numero de cotizacion y con filtro de columna `prioridad=ALTA` devuelven
exactamente esa fila. `manage.py check`/`makemigrations --check --dry-run` limpios (sin modelos
nuevos). Render real de `/workspace/` (HTTP, con sesion real) confirma que el HTML/JS/CSS nuevos se
sirven sin error de plantilla.

## 13. Fase 9 (2026-09-26) — Detalle interactivo (offcanvas de revision + ruta visual)

`apps/tenant/dashboard/templates/tenant/dashboard/partials/offcanvas_revisar_solicitud.html` --
mismo esqueleto del mockup `#14` del plan (estado/solicitante/fecha, "RUTA DEL PROCESO", "RESUMEN
FINANCIERO", `[RECHAZAR]`/`[APROBAR]`), poblado 100% via JS contra el DTO de `ApprovalTraceService`
(Fase 6, ya construido, ya expuesto via API en Fase 7 -- Fase 9 no agrega backend nuevo, solo lo
consume). Abierto con `w.Sintel.Core.mostrarOffcanvasSeguro()` (nunca `getOrCreateInstance().show()`,
regla de `CLAUDE.md`).

**Ruta visual (`#15` del plan) -- decision de diseno documentada:** se implementa como una lista de
nodos conectados verticalmente (timeline con marcador + linea, exactamente el layout de `#14`), NO
como un grafo canvas/SVG interactivo con ramificaciones. Motivo: ninguna libreria de grafos esta en
el stack aprobado del proyecto (`CLAUDE.md` "Frontend": Bootstrap/HTMX/Bootstrap Icons/Font Awesome,
Alpine explicitamente NO aprobado) -- introducir una nueva dependencia solo para el grafo violaria
"No build step" y el criterio de simplicidad ("Minimum code. No especulative abstractions"). Cada
nodo SI es interactivo (`#15`: "cada nodo debe ser interactivo") via un link `Ver` que navega al tab
del workspace del dominio correspondiente (Cotizacion/Proyecto/Requisicion/Orden de Compra) --
apertura del propio SSoT de cada documento, no una vista inventada aqui.

El boton `[APROBAR]`/`[RECHAZAR]` solo se muestra si `estado == PENDIENTE` (nunca se ofrece decidir
sobre una solicitud ya cerrada). Rechazar exige motivo (validacion cliente + servidor, `#27`). Tras
decidir, se cierra el offcanvas y se refresca banner+bandeja (`refrescarTodo()`).

Verificado end-to-end (backend ya cubierto en Fase 7; Fase 9 es capa de presentacion pura) -- sin
backend nuevo que verificar aqui mas alla de lo ya probado.

## 14. Fase 10 (2026-09-26) — Nueva Orden de Compra: seleccion multiple con saldos en vivo

Reemplaza el `<select>` de seleccion unica (interino desde Fase 1-4) por un checklist real (`#21`/
`#33` del plan: "seleccion multiple", "ver saldos", "Total disponible seleccionado").

- `apps/tenant/compras/static/compras/js/compras.utils.js`: `fetchRequisicionesDisponibles()` ahora
  llama al endpoint real `disponibles-para-orden` (Fase 7, con saldo) en vez de traer TODAS las
  Requisiciones y filtrar por estado en el cliente (el comportamiento anterior, interino desde antes
  de que existiera el endpoint dedicado). Nuevo `loadRequisicionesDisponiblesChecklist()` +
  `getRequisicionesSeleccionadas()` + `recalcularTotalDisponibleSeleccionado()` (suma el SALDO de
  las filas marcadas, no el valor total -- consistente con lo que realmente se puede consolidar).
- `compras_editor.js`: `payload.requisiciones` ahora es la lista real de UUIDs marcados (antes
  siempre `[uuid]` de 0 o 1 elemento). El backend (Fase 3) ya soportaba N:N desde el primer dia --
  esta fase completa la UX correspondiente, no cambia ninguna regla de negocio.
- `offcanvas_crear_compras.html`: el `<select id="requisicion">` se reemplaza por un contenedor
  `#requisiciones-disponibles-checklist` (checkboxes con numero/origen/total/saldo por fila) +
  `#requisiciones-total-disponible` (suma en vivo).

El backend sigue siendo la autoridad final (`ProcurementBudgetControlService.
validar_consolidacion_oc()`, Fase 4) -- si el usuario arma una OC que excede el saldo de alguna
Requisicion seleccionada, el submit falla con el mensaje real del backend (`showError`, patron ya
existente en el formulario). No se duplico esa validacion en JS (`#34`: "No duplicar logica de
calculo en JS").

Verificacion: backend cubierto por el smoke test de Fase 11 (consolidacion real de 2 Requisiciones
en 1 OC via `OrdenCompraBusinessService.crear_orden_compra()`). Prueba de navegador interactiva
(click real en checkboxes) NO se realizo en esta sesion -- fuera del alcance verificable sin un
navegador real disponible; queda como parte de los comandos manuales entregados al usuario.

## 15. Fase 11 (2026-09-26) — Integraciones verificadas + 2 bugs reales encontrados y corregidos

Verificacion end-to-end de la cadena completa (Cotizacion -> 2 Requisiciones -> enviar -> aprobar ->
1 Orden de Compra consolidando ambas) contra el tenant `admin` real, ejercitando el codigo real
(`OrdenCompraBusinessService.crear_orden_compra()`), no solo selectors/serializers. Esta verificacion
encontro 2 bugs reales que NINGUNA prueba anterior de esta mision habia ejercitado (las pruebas
previas de Fases 3/4/7 no habian llamado a `crear_orden_compra()` con >= 2 Requisiciones reales via
el Business Service completo):

1. **`AttributeError` real, bloqueaba el 100% de las creaciones de OC:**
   `OrdenCompraBusinessService.crear_orden_compra()` referenciaba
   `RequisicionCompraSelector.ESTADOS_DISPONIBLES_PARA_COMPRA` como si fuera un atributo de clase --
   es una constante a nivel de MODULO en `apps/tenant/compras/requisiciones/services/selectors.py`
   (`ESTADOS_DISPONIBLES_PARA_COMPRA = (...)`, fuera de la clase). Cualquier intento real de crear
   una Orden de Compra (con 1 o mas Requisiciones) fallaba con `AttributeError` -- acceptance
   criteria `#7`/`#8` del plan estaban rotos en produccion desde que se introdujo en Fase 3.
   Corregido: `from ...selectors import ESTADOS_DISPONIBLES_PARA_COMPRA` (import directo del
   simbolo del modulo, no un atributo de la clase).
2. **Hueco de concurrencia real (`#25` del plan, nunca cerrado):** el comentario en el codigo
   afirmaba "select_for_update() implicito via `_obtener_entidad_por_id_o_uuid`" -- FALSO:
   `_obtener_entidad_por_id_o_uuid()` es un `.filter().first()` simple, sin lock. Dos creaciones de
   OC concurrentes contra la misma Requisicion podian leer el mismo saldo "libre" y sobre-consumirlo
   (exactamente el escenario prohibido que `#25` describe: "Usuario A consume $10M, Usuario B
   consume $10M, RESULTADO PROHIBIDO = $110M"). Corregido: re-fetch explicito de las Requisiciones
   resueltas con `RequisicionCompra.objects.select_for_update().filter(id__in=...)` (dentro del
   mismo `@transaction.atomic` que ya envolvia el metodo) ANTES de calcular montos/validar saldo.

Verificado tras ambos fixes: consolidacion real de 2 Requisiciones ($40.000/$30.000) en 1 OC,
`OrdenCompraRequisicion` con `monto_asignado` correcto por fila, `ItemOrdenCompra.
requisicion_item_uuid` poblado en el 100% de las lineas (`#4` del plan, trazabilidad por linea),
saldo de ambas Requisiciones en `$0.00` tras consolidar, saldo de la Cotizacion en `$30.000`
(100.000 - 70.000, exacto). Sin residuo en el tenant real al terminar.

Integraciones preservadas (`#11` del plan) -- no se toco ninguna de estas, se confirma que siguen
intactas: sincronizacion Cotizacion<->Venta<->Factura (verificada y corregida en una fase anterior
de esta misma sesion, sin relacion con Approvals), Recepcion de Compras -> Inventario (F21, codigo
no tocado), CxP (no tocado).

## 16. Fase 13 (2026-09-26) — Autoauditoria

Revision sistematica contra la lista de `#13` del plan:

- **Bypass de aprobacion:** grep de todo `apps/tenant/approvals`+`apps/tenant/compras`+
  `apps/tenant/dashboard` -- el UNICO lugar que escribe `SolicitudAprobacion.estado` es
  `SolicitudAprobacionCRUDService.cambiar_estado()` (la capa que corresponde); ningun Business
  Service de Approvals ni el Dashboard escriben `RequisicionCompra.estado`/`OrdenCompra.estado`
  directo -- siempre delegado (`#26`, ya documentado en `#4`).
- **Bypass de limites:** `OrdenCompraRequisicion` solo se crea en un unico sitio
  (`OrdenCompraBusinessService.crear_orden_compra()`, `bulk_create` verificado por grep), siempre
  precedido por `validar_consolidacion_oc()` -- sin via alterna.
- **Carreras de concurrencia:** hueco real encontrado y corregido en Fase 11 (arriba, item 2).
- **Fuga cross-tenant:** todo endpoint nuevo de Fase 7/8 usa `_get_empresa_id_seguro()` (DSV
  estandar del proyecto); `ApprovalBusinessService` resuelve todo objeto via el registry, siempre
  filtrando por `empresa_id`.
- **Duplicacion de logica:** riesgo/prioridad se calcula UNA vez (`_calcular_riesgo_requisicion()`)
  y se consume desde el snapshot -- el frontend nunca recalcula porcentajes ni saldos.
- **Inconsistencias de estados:** los valores de estado usados en JS (`PENDIENTE`/`APROBADA`/
  `RECHAZADA`/`CANCELADA`) son un calco exacto de `SolicitudAprobacion.Estado` -- ningun estado
  inventado en frontend.
- **Errores de migracion:** `makemigrations --check --dry-run` limpio en cada fase de esta mision,
  incluida esta (Fases 8-13 no agregan modelos).
- **Inconsistencias frontend/backend:** contrastados uno a uno los campos que consume cada JS nuevo
  contra la respuesta real de su endpoint (via los smoke tests de Fase 8/11) -- sin discrepancias.
- **Rutas API duplicadas:** unico riesgo real (`dashboard/aprobaciones/` vs `dashboard/`) ya
  encontrado y corregido en Fase 7; no se introdujo ninguna ruta nueva en Fases 8-10 (reutilizan las
  ya existentes).
- **Dashboard como SSoT de Compras:** el Dashboard (`apps/tenant/dashboard/`) no gano ningun modelo,
  selector ni Business Service en esta mision -- toda la logica nueva vive en `apps/tenant/
  approvals` o `apps/tenant/compras`, el Dashboard solo aporta plantillas/assets.

Con esto, `PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md` queda completo (Fases 0-13). Unico item
DEFERRED explicito: `#10` de este documento.
