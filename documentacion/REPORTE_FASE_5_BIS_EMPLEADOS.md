# REPORTE FASE 5-BIS — Empleados (Tabulator → django-tables2)

**Fecha:** 2026-08-04
**Alcance:** `PLAN_UNICO_CORRECCIONES.md` §"FASE 5-BIS".
**Estado: 5 de 5 grillas migradas.** `empleados`, `contratos`, `resoluciones DIAN` (CRUD planas) y `nominas`/`liquidaciones` (Master-Detail) migradas por completo. Un archivo del plan original (`nomina_historial.js`) queda documentado como código muerto sin tocar — ver §4.

---

## 1. Particularidad de esta app: orquestador con lazy-loading real por sub-tab

A diferencia de `contabilidad`/`ventas`/`bancos` (donde todas las grillas cargaban de inmediato al abrir el módulo, con `hx-trigger="load"`), `empleados.module.js` ya implementaba un lazy-loading genuino: cada sub-tab solo se inicializa la primera vez que el usuario hace click en su pestaña Bootstrap (`shown.bs.tab`), rastreado en `state.subTabsInitialized`. Para no perder ese comportamiento (evitar 3-5 peticiones HTTP innecesarias cada vez que alguien abre el módulo Empleados sin visitar todas sus pestañas), se preservó usando una feature nativa de HTMX en vez de reinventar el mecanismo:

- Tab activo por defecto (**Empleados**): `hx-trigger="load, empleado-updated from:body"` (igual que el resto de apps).
- Tabs no-activos (**Contratos**, **Resoluciones**): `hx-trigger="shown.bs.tab from:#tab-contratos once, contrato-updated from:body"` — HTMX escucha directamente el evento Bootstrap del boton de la pestaña, con `once` para que solo dispare la primera vez.

`empleados.module.js` **no se tocó**: su lógica de `initSubTab()` sigue llamando `XList.init()`/`XList.reload()` exactamente igual, ahora sobre implementaciones que son no-ops (`init`) o disparan el `CustomEvent` que el panel HTMX ya escucha (`reload`) — ambos mecanismos (el trigger nativo de HTMX y el orquestador JS) conviven sin duplicar peticiones: el primero solo dispara una vez (`once`, primera activación), el segundo solo dispara en activaciones posteriores (cuando `subTabsInitialized[tab]` ya es `true`).

## 2. Grillas migradas

| Grilla | Modelo | Archivos nuevos/tocados |
|---|---|---|
| Empleados | `Empleado` | `tables.py::EmpleadoTable`, `views.py::EmpleadoTableView`, `tabla_empleados.html`, `empleados_list.html`, `empleado_list.js` |
| Contratos | `Contrato` | `tables.py::ContratoTable`, `views.py::ContratoTableView`, `tabla_contratos.html`, `empleados_list.html`, `contrato_list.js` |
| Resoluciones DIAN | `ResolucionDIAN` | `tables.py::ResolucionDIANTable`, `views.py::ResolucionDIANTableView`, `tabla_resoluciones.html`, `empleados_list.html`, `resolucion_list.js` |

Patrón idéntico al resto de la expansión: `SingleTableView` + `LoginRequiredMixin` + `SintelDSVMixin.get_empresa_id()`, reutilizando `EmpleadoSelector.get_list()`/`ContratoSelector.get_list()` ya existentes (ambos ya soportaban `search`). `ResolucionDIAN` no tenía un Selector dedicado -- el propio `ResolucionDIANViewSet` arma el queryset inline (`.only(*_RESOLUCION_LIST_FIELDS)`); la vista nueva replica esa misma lógica sin crear un Selector nuevo (no se justifica una abstracción para un solo consumidor adicional).

**Casos especiales:**
- `EmpleadoTable.foto_url`: columna con avatar (foto real si existe, iniciales sobre círculo de color si no) — replica el formatter de Tabulator 1:1, usando `record.foto.url` directo en vez de `request.build_absolute_uri()` (innecesario para un `<img src>` relativo dentro del propio dominio).
- El resumen de estadísticas (`panel-resumen-empleados`, 4 tarjetas arriba de las pestañas) usa un endpoint JSON aparte (`api.empleados.summary`) que **nunca fue una grilla Tabulator** -- se preservó sin cambios, solo se ajustó cuándo se recarga (ahora en `EmpleadoList.init()` al cargar la página, y en `ejecutarEliminar()` tras eliminar un empleado, igual que antes).
- Un `hx-target="#grid-empleados"` colgante se encontró en `offcanvas_crear_devengo.html` (un botón "Guardar Devengo" con `hx-swap="none"`, el target nunca se usaba para renderizar contenido pero SÍ debía apuntar a un elemento existente para no generar un error `htmx:targetError` en consola) -- corregido a `#empleados-panel`.

## 3. Nóminas y Liquidaciones: patrón Master-Detail resuelto con `row_attrs`

Ambas pestañas usan un layout **Master-Detail**: una grilla maestra de empleados (columna izquierda) + una grilla de detalle (columna derecha, vacía hasta seleccionar un empleado) que muestra el histórico de nóminas/liquidaciones de ESE empleado. A diferencia de los 3 casos de `contabilidad` (`pendientes`/`libro-diario`/`reportes`, vistas agregadas cross-app sin encaje natural en `django_tables2.Table`), este patrón **sí encajaba**: ambas son tablas planas de un solo modelo (`Devengo`, `LiquidacionPrestacion`), solo que la del detail se filtra por el empleado seleccionado en el master.

**Solución implementada — sin JS de terceros, sin reimplementar nada del lado del cliente:**
- `NominaEmpleadoMasterTable`/`LiquidacionEmpleadoMasterTable` (`tables.py`) usan `Meta.row_attrs` (feature nativa de `django-tables2`) para inyectar `hx-get`/`hx-target`/`hx-swap` en cada `<tr>` renderizado, con la URL calculada por fila via `lambda record: reverse(...) + f"?empleado_uuid={record.uuid}"`. El click en una fila del master ya dispara la carga del detail sin ningún listener JS adicional -- HTMX intercepta el click porque el propio `<tr>` lleva los atributos.
- `NominaDetailTableView`/`LiquidacionDetailTableView` resuelven el `Empleado` desde `?empleado_uuid=` (filtrado por `empresa_id` del tenant actual -- si el uuid pertenece a otro tenant, `first()` retorna `None` y la vista cae al estado "sin empleado seleccionado", cerrando el mismo vector de IDOR que ya cubre `SintelDSVMixin` en el resto de vistas). Ambas retornan el **panel completo** (header con nombre/contador/botón "Nueva Nómina o Nueva Liquidación" + tabla), no solo la tabla, porque el header depende de qué empleado está seleccionado -- se recarga todo junto en cada click, evitando desincronización entre header y tabla.
- `LiquidacionDetailTableView` además soporta `?tipo_liquidacion=`: los filtros por tipo (antes pills siempre visibles pero funcionalmente inertes sin empleado seleccionado) se movieron **dentro** del panel de detail -- solo existen cuando ya hay un empleado activo, y cada pill dispara un `hx-get` con `empleado_uuid` + `tipo_liquidacion`, recargando el panel completo (mantiene el header consistente con el filtro aplicado).
- JS resultante (`nomina_list.js`, `liquidacion_list.js`): sin Tabulator, sin lógica de fetch manual. Solo: (a) resaltado visual de la fila activa en el master (`table-active`/`fw-bold`, delegado por click), guardando el `empleado_uuid` activo en una variable de módulo; (b) acciones del detail (nueva nómina/liquidación, anular, ver, eliminar) delegadas sobre el panel persistente; (c) `reload()` dispara el evento HTMX del master **y**, si hay un empleado activo, vuelve a pedir su detail (para que anular una nómina, por ejemplo, refresque ambos paneles a la vez).

## 4. Código muerto encontrado, no tocado: `nomina_historial.js`

Un cuarto archivo del inventario original de esta app (`nomina_historial.js`, offcanvas "Historial de Nóminas" con su propia tabla Tabulator) resultó estar **cargado pero inerte**: se referencia en `assets_empleados.html` y el endpoint backend (`/api/v1/empleados/{id}/historial-nominas/`) funciona, pero **ningún botón en el HTML actual invoca `NominaHistorial.open()`**. Es plausible que haya sido el patrón anterior a la introducción del Master-Detail de `nomina_list.js` (que muestra exactamente el mismo historial, pero integrado), nunca limpiado tras el reemplazo. No se tocó (ni se migró ni se borró) -- mismo criterio que `resolucion_list.js` de `bancos`: queda documentado para una pasada de limpieza dedicada, no es parte del alcance de "reemplazar grillas Tabulator activas".

## 5. Verificación

Sin Docker/venv funcional en este host (misma limitación de toda la sesión). Verificado con `python -m py_compile` (`tables.py`, `views.py`, `urls.py`, `conftest.py`, `test_multitenant_isolation_tablas_html.py` -- todos OK) y `node --check` (`empleado_list.js`, `contrato_list.js`, `resolucion_list.js` -- OK). Grep de `grid-empleados`/`grid-contratos`/`grid-resoluciones` en toda la app confirma cero referencias colgantes tras el reemplazo (y la corrección del `hx-target` huérfano en `offcanvas_crear_devengo.html`). `apps/tenant/empleados/tests/conftest.py` ya existía (con fixture `tenant`/`admin_user`/`tenant_factory` propios) -- se le agregaron las fixtures canónicas `tenant1`/`tenant2` (AGENTS.md §24.5) sin tocar las existentes.

**Antes de dar esta migración por validada en runtime**, incluir en el batch de validación final ya definido para el resto de Fase 5-BIS:
```
pytest apps/tenant/empleados/tests/test_multitenant_isolation_tablas_html.py -v
```
y abrir manualmente el módulo Empleados: las 5 pestañas migradas. Para Empleados/Contratos/Resoluciones: confirmar que Contratos/Resoluciones solo cargan datos al hacer click en su pestaña (no antes), buscar, paginar, ordenar, crear/editar/eliminar empleado, crear/cancelar contrato, crear/eliminar resolución. Para Nóminas/Liquidaciones: click en una fila del master carga el detail correcto, resaltado visual de la fila activa, crear/anular nómina refresca ambos paneles, crear/eliminar liquidación igual, filtros por tipo de liquidación funcionan con el empleado activo.

Agregado también `test_multitenant_isolation_empleados_master_detail_html`, que ademas de aislamiento verifica el caso IDOR especifico de estas 2 vistas: pasar un `empleado_uuid` que pertenece a OTRO tenant no debe filtrar ningun dato -- la vista cae al estado "sin empleado seleccionado" porque el filtro `empresa_id + uuid` no lo encuentra.

## 6. Archivos nuevos/tocados (resumen)

```
NUEVO  apps/tenant/empleados/tables.py
NUEVO  apps/tenant/empleados/views.py
NUEVO  apps/tenant/empleados/templates/tenant/empleados/partials/tabla_empleados.html
NUEVO  apps/tenant/empleados/templates/tenant/empleados/partials/tabla_contratos.html
NUEVO  apps/tenant/empleados/templates/tenant/empleados/partials/tabla_resoluciones.html
NUEVO  apps/tenant/empleados/templates/tenant/empleados/partials/tabla_nomina_master.html
NUEVO  apps/tenant/empleados/templates/tenant/empleados/partials/tabla_nomina_detalle.html
NUEVO  apps/tenant/empleados/templates/tenant/empleados/partials/tabla_liquidacion_master.html
NUEVO  apps/tenant/empleados/templates/tenant/empleados/partials/tabla_liquidacion_detalle.html
NUEVO  apps/tenant/empleados/tests/test_multitenant_isolation_tablas_html.py
M      apps/tenant/empleados/urls.py (8 rutas *-tabla/ agregadas)
M      apps/tenant/empleados/tests/conftest.py (fixtures tenant1/tenant2 agregadas)
M      apps/tenant/empleados/templates/tenant/empleados/empleados_list.html (las 5 pestañas)
M      apps/tenant/empleados/templates/tenant/empleados/offcanvas_crear_devengo.html (hx-target huerfano corregido)
M      apps/tenant/empleados/static/empleados/js/features/empleado_list.js
M      apps/tenant/empleados/static/empleados/js/features/contrato_list.js
M      apps/tenant/empleados/static/empleados/js/features/resolucion_list.js
M      apps/tenant/empleados/static/empleados/js/features/nomina_list.js
M      apps/tenant/empleados/static/empleados/js/features/liquidacion_list.js
```

No se tocaron `empleados.module.js` (el orquestador sigue funcionando sin cambios, ver §1), ningún `*_editor.js`, ni `nomina_historial.js` (código muerto documentado en §4, no en alcance).

**Nota menor:** `empleados.module.js::conectarBotonesCreacion()` sigue buscando `document.getElementById('btn-nueva-liquidacion')`, un botón que existía en el toolbar fijo del tab Liquidaciones y que ahora vive dentro del panel de detail (`.btn-nueva-liquidacion-header`, inyectado por HTMX, manejado directamente por `liquidacion_list.js`). La búsqueda en `empleados.module.js` queda inerte (el guard `if (btnLiquidacion && ...)` evita cualquier error), no rompe nada -- se documenta por transparencia, no se limpió `empleados.module.js` para mantener el diff de esta migración acotado a lo estrictamente necesario.

## 7. Progreso de la expansión Fase 5-BIS (actualizado)

| App | Estado |
|---|---|
| `gastos` | Migrado (piloto) |
| `facturas` | Migrado |
| `compras` | Migrado |
| `contabilidad` | Migrado 5/8 grillas (3 fuera de alcance deliberado) |
| `ventas` | Migrado 1/1 grilla real (2 archivos del plan resultaron ser código no conectado, en progreso) |
| `bancos` | Migrado 2/2 grillas reales (1 archivo del plan nunca existió) |
| `empleados` | **Migrado 5/5 grillas** (incluye Master-Detail de Nóminas y Liquidaciones -- ver §3). 1 archivo del plan (`nomina_historial.js`) es código muerto no tocado -- ver §4 |
| resto (~11 apps) | Pendiente: `inventario`, `cotizaciones`, `proveedores`, `empresa`, `proyectos`, `clientes`, `dashboard`, `perfil`, `core` |
