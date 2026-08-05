# REPORTE FASE 5-BIS — Reemplazo de Tabulator por django-tables2 + HTMX (`gastos`, `facturas`, `compras`)

**Fecha:** 2026-08-03
**Alcance:** Reemplazo de Tabulator (decisión del usuario, fuera de `AUDITORIA_ENTERPRISE_2026-07-26.md`) — piloto en `gastos`, luego expansión a `facturas` y `compras` en la misma sesión, por decisión explícita del usuario de **no gatear la expansión con la validación en runtime** (esa validación se hace una sola vez, al final, sobre las 3 apps juntas — ver §6). Quedan ~16 apps pendientes (ver tabla de progreso en `PLAN_UNICO_CORRECCIONES.md` §"FASE 5-BIS"). Ver ese mismo documento para el contexto completo de la decisión (tecnología evaluada, alternativas descartadas).
**No se tocó ninguna otra fase del plan** (Fase 5 FE-A/FE-M, Fase 6, etc. siguen pendientes tal como estaban).

---

## 0. Limitación de entorno (misma de todas las fases anteriores)

No hay Docker/venv funcional en este host (ver `REPORTE_FASE_1.md` §0 para el detalle completo del problema). Verificación aplicada en su lugar:
- `python -m py_compile` sobre los 4 archivos `.py` tocados/nuevos → limpio.
- `python -c "ast.parse(...)"` sobre `tables.py`/`views.py` → limpio.
- `node --check` sobre `gasto_list.js` → limpio.
- Lectura completa de cada `Selector`/modelo consumido para que los `accessor`/`order_by` de las columnas `django-tables2` referencien campos reales (no inventados).

**No verificado en este entorno — bloqueante explícito antes de dar el piloto por cerrado:**
1. Que `django-tables2` efectivamente resuelva la plantilla `django_tables2/bootstrap5.html` (depende de la versión exacta instalada; se fijó `>=2.7,<3.0` en `requirements.txt`, que según el registro de cambios de la librería ya la incluye, pero no se pudo confirmar instalando el paquete real).
2. Que las vistas nuevas respondan 200 con datos reales de un tenant (requiere Postgres + `migrate_schemas` con al menos un tenant provisionado).
3. Paridad visual con la versión Tabulator que reemplaza (los `render_*` de `tables.py` reproducen la mayoría de los estilos/badges originales de `gasto_list.js`, pero no se renderizó nunca en un navegador real).
4. Que `pytest apps/tenant/gastos/tests/test_multitenant_isolation.py -v` pase, incluido el test nuevo.

**Recomendación:** ejecutar los 4 puntos anteriores en un entorno Docker/venv funcional antes de considerar el piloto validado y antes de decidir la expansión al resto de apps.

---

## 1. Por qué esta tecnología (resumen de la decisión)

El usuario pidió evitar Tabulator/DataTables por "mucho conflicto con el backend" y pidió investigar la tecnología más apropiada compatible con Django. Se presentaron 3 opciones con trade-offs explícitos y el usuario eligió **`django-tables2` + `django-filter` + HTMX**, alcance **piloto en 1 app** (`gastos`), arranque de código **solo el piloto** (no toda la Fase 5 Frontend en la misma sesión).

**Causa raíz del "conflicto con el backend" que esta tecnología elimina:** Tabulator/DataTables exigen mantener sincronizados dos contratos independientes — el JSON que serializa DRF (`StandardResultsSetPagination`, nombres de campos del serializer) y el formato que la librería JS espera del lado del cliente (parámetros de paginación/orden/filtro, estructura de la respuesta AJAX). `django-tables2` elimina el segundo contrato por completo: el HTML de la tabla se genera en el servidor directamente desde el `QuerySet`, no hay una capa JSON intermedia que pueda desincronizarse.

## 2. Por qué `gastos` como app piloto

- 0 hallazgos ALTO en la auditoría (la app "más limpia" del repositorio).
- Ya tiene `test_multitenant_isolation.py` completo (uno de solo 2 apps que lo tenían antes de Fase 1) — mínimo riesgo de introducir una regresión de seguridad sin detectarla.
- 2 grillas de complejidad distinta (Documentos Soporte: 7 columnas con formatters ricos; Resoluciones DIAN: 5 columnas, más simple) — suficiente para validar el patrón contra un caso no trivial sin arriesgar un módulo financiero de alto tráfico como `facturas`/`contabilidad`.

## 3. Cambios aplicados

### 3.1 Dependencias
- `requirements.txt`: `django-tables2>=2.7,<3.0` agregado.
- `config/settings.py`: `"django_tables2"` agregado a `TENANT_APPS` (junto a `django_filters`, mismo bloque); `DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"` agregado como default global (todas las tablas futuras de otras apps heredarán Bootstrap 5 sin tener que declararlo por `Table.Meta`).

### 3.2 Backend nuevo (no se tocó `api/viewsets.py` ni `api/serializers.py`)
- **`apps/tenant/gastos/tables.py` (nuevo):** `DocumentoSoporteTable` (7 columnas: documento, fecha, proveedor, categoría, total, estado, acciones) y `ResolucionDIANTable` (5 columnas). Cada `render_*` reproduce el HTML/badges que antes generaban los `formatter` de Tabulator en `gasto_list.js`, incluyendo los mismos `data-uuid`/clases CSS en los botones de acción para que la delegación de eventos JS existente siga funcionando sin cambios.
- **`apps/tenant/gastos/views.py` (nuevo):** `DocumentoSoporteTableView`/`ResolucionDIANTableView`, ambas `LoginRequiredMixin + SintelDSVMixin + SingleTableView`. Reutilizan `DocumentoSelector.get_list()`/`ResolucionSelector.get_list()` — **cero cambios al Service Layer**, las vistas nuevas son puramente una capa de presentación sobre selectors que ya existían con `.only()` aplicado.
- Aislamiento multi-tenant: `SintelDSVMixin.get_empresa_id()` es la misma fuente de verdad que usa `BaseTenantViewSet` en toda la API DRF — no se reimplementó resolución de tenant ni filtrado por `empresa_id` de ninguna otra forma. Si `get_empresa_id()` lanza `DRFValidationError` (sin perfil de tenant), la vista retorna `queryset.none()` en vez de fallar con 500 o, peor, mostrar datos sin filtrar.
- Paginación: `table_pagination = {"per_page": 20}` — **no** se usó el atributo `paginate_by` de `ListView` (que causaría doble paginación al combinarse con la paginación propia de `django-tables2`, un gotcha documentado de la librería).

### 3.3 Templates
- **2 nuevos parciales** (`templates/tenant/gastos/partials/tabla_gastos.html`, `.../tabla_resoluciones.html`): renderizan `{% render_table table %}` más, en el caso de Documentos, 4 tarjetas KPI recalculadas server-side sobre el queryset completo ya filtrado (total documentos, gastado este mes vía `DocumentoSelector.get_summary()` ya existente, activos, anulados) — **más preciso** que el cálculo anterior en `gasto_list.js`, que dependía de cuántas filas hubiera cargado Tabulator en el cliente en ese momento.
- **`gastos_list.html`:** los contenedores vacíos `#grid-gastos`/`#grid-resoluciones` (poblados históricamente por JS) se reemplazan por `#gastos-panel`/`#resoluciones-panel` con `hx-get` al endpoint nuevo, `hx-trigger="load, gasto-created from:body, gasto-updated from:body"` (reutiliza los mismos eventos custom que ya disparaba `gasto_editor.js` tras crear/editar — cero cambios ahí), y `hx-boost="true"` para que los enlaces de orden/paginación que genera `django-tables2` se vuelvan peticiones AJAX automáticamente sin JS adicional. El campo de búsqueda pasa de filtrar client-side (Tabulator) a `hx-get` con `hx-trigger="keyup changed delay:400ms, search"` contra el mismo endpoint, con `name="q"` (ya soportado por `DocumentoSelector.get_list(search=...)`).
- Se eliminaron los divs de "empty state" separados — `django-tables2` ya maneja `Meta.empty_text` nativamente, evitando la duplicación de lógica que antes vivía en JS.

### 3.4 Frontend JS
- **`gasto_list.js` reducido de ~750 a ~260 líneas.** Se eliminó: inicialización de Tabulator, las 2 listas de columnas/formatters (~250 líneas), el cálculo de KPIs client-side (`actualizarKPIs`), el manejo de reintentos de `TabulatorFactory`, y el listener de `shown.bs.tab` que forzaba la inicialización lazy por pestaña (ya no aplica: los paneles HTMX cargan con `hx-trigger="load"` apenas el DOM los inserta).
- **Se conservó intacto:** la delegación de eventos de los botones de acción (`btn-view-gasto`, `btn-edit-gasto`, `btn-cancel-gasto`, `btn-delete-gasto`, `btn-edit-resolucion`, `btn-deactivate-resolucion`) — ahora anclada a `#gastos-panel`/`#resoluciones-panel` (el contenedor persistente, no reemplazado por los swaps `hx-swap="innerHTML"`) en vez de a `#grid-gastos`/`#grid-resoluciones`; el manejo de offcanvas (`loadAndShowOffcanvas`, los listeners `htmx:afterSettle`/`htmx:beforeCleanupElement`); `refresh()`/`reload()`, que ahora despachan el mismo `CustomEvent` que ya escuchaba `gasto_editor.js`, en vez de llamar `tabla.replaceData()`.
- **No se agregó ningún guard `data-editor-initialized` (FE-A1)** porque no aplica aquí: a diferencia de los `*_editor.js` que motivaron ese hallazgo, este script no tiene múltiples mecanismos (`MutationObserver`+`DOMContentLoaded`+`htmx:afterSettle`) que puedan disparar el mismo `addEventListener` más de una vez — se documentó explícitamente en el código por qué no hace falta, para que una futura pasada de Fase 5 no lo agregue "por consistencia" sin revisar si aplica.

### 3.5 Test nuevo
- `test_multitenant_isolation_gastos_tabla_html` agregado a `apps/tenant/gastos/tests/test_multitenant_isolation.py` (mismo archivo, mismo patrón `tenant1`/`tenant2` que el test DRF ya existente). Cubre: (1) el listado HTML de Documentos no filtra datos de otro tenant, (2) idem para Resoluciones, (3) un cliente sin sesión recibe redirect a login en vez de datos. Se agregó porque las vistas nuevas **no son ViewSets DRF** — no heredan automáticamente la cobertura de aislamiento que ya validaba `/api/v1/gastos/`.

---

## Expansión — `facturas`

**Por qué esta app fue la siguiente:** primera en la priorización "apps que tocan dinero primero" del criterio de expansión, y es el caso más complejo del lote (2 grillas Ventas/Compras sobre el mismo modelo `Factura` filtrado por `naturaleza`, filtros rápidos de estado de pago, resumen de KPIs independiente). Se migró completa (no solo una de las 2 pestañas) para que la validación final cubra el caso más exigente.

**Backend nuevo:**
- `apps/tenant/facturas/tables.py` (nuevo): `FacturaTable`, una sola clase parametrizada por `naturaleza="VENTA"|"COMPRA"` (constructor acepta el kwarg), igual que el `getColumnsNaturaleza(naturaleza)` que reemplaza. La columna "Cot." (cotización asociada) se excluye vía `Table(..., exclude=("cotizacion_numero",))` cuando `naturaleza=COMPRA`, en vez de duplicar la clase.
- `apps/tenant/facturas/views.py` (nuevo): `FacturaTableView`, con `naturaleza` como parámetro de URL (`/ui/facturas/tabla/venta/`, `/ui/facturas/tabla/compra/`). Reutiliza `FacturaSelectors.qs_list()` (ya trae `select_related`/`.only()`) y agrega el filtro `estado_pago` sobre ese queryset — no se tocó el selector.
- Los **filtros rápidos de "Pago"** (antes botones JS con estado en el cliente) ahora se renderizan **dentro** del fragmento HTMX (no en el shell estático), con la clase `active` calculada server-side desde `request.GET.get('estado_pago')` — necesario porque, a diferencia de `gastos`, aquí el estado del filtro debe sobrevivir a cada recarga del panel.

**Simplificaciones conscientes respecto a la versión Tabulator (documentadas para que la validación final las tenga en cuenta, no son bugs):**
1. **Se retiró el click-en-fila para abrir el detalle.** La versión Tabulator abría el offcanvas de detalle tanto al hacer clic en cualquier parte de la fila como al hacer clic en el botón "Ver". Se conservó solo el botón "Ver" (funcionalmente equivalente, un clic más específico) para no tener que replicar el manejo de `e.composedPath()`/exclusión de botones sobre filas `<tr>` generadas por `django-tables2`.
2. **El pin "vinculado" (icono de enlace junto al nombre de cliente/proveedor) ahora solo verifica que `cliente_uuid`/`proveedor_uuid` no sea nulo**, no que ese UUID resuelva a un registro `Cliente`/`Proveedor` existente (esa verificación vivía en un método del serializer viejo que hacía una consulta adicional por fila — replicarla habría reintroducido la clase de N+1 que `PERF-A1`/Fase 4 ya cerró). Es un pin puramente decorativo en la UI, no una verificación de seguridad.
3. **Carga elegida (`hx-trigger="load"`) en vez de lazy-init por pestaña:** igual que en `gastos`, ambos paneles (Ventas y Compras) se piden al servidor apenas se renderiza la página, no solo cuando el usuario hace clic en la pestaña "Compras". Antes, `initTabulatorCompras()` esperaba a `shown.bs.tab`.
4. **El filtro `tipo_impuesto`** que el JS viejo intentaba leer de un `<select id="filter-tipo-impuesto">` **nunca existió en el template** (confirmado por grep) — no se migró porque no había nada real que migrar, era código defensivo sobre un elemento inexistente.

**Frontend JS:** `facturas_list.js` bajó de ~805 a ~290 líneas. Se eliminó: inicialización de ambos Tabulator, `getColumnsNaturaleza()` (~110 líneas), `getVentasUrl()`/`getComprasUrl()`/`initFiltrosPago()`/`initFiltroImpuesto()` (filtrado ahora server-side), y el listener `shown.bs.tab` de lazy-init. Se conservó intacto: la delegación de eventos de editar/ver/eliminar (mismas clases/`data-id`), toda la lógica de apertura del offcanvas de detalle (`gestor-offcanvas`), y `loadSummary()`/`_doLoadSummary()` (independiente de Tabulator, sigue golpeando `/api/v1/facturas/summary/`).

**Detalle importante de integración:** el evento `facturaGuardada` que dispara la recarga de ambos paneles se despacha sobre `document` (`d.dispatchEvent`, confirmado leyendo `facturas_editor.js:385`), **no** sobre `document.body` como en `gastos` — por eso el `hx-trigger` de `list_factura.html` usa `facturaGuardada from:document` y no `from:body`. Detalle que habría roto la recarga reactiva silenciosamente si se hubiera copiado el patrón de `gastos` sin verificar el target real de cada `dispatchEvent`.

**Test nuevo:** `apps/tenant/facturas/tests/conftest.py` (nuevo — `facturas` no tenía la infraestructura de fixtures `tenant1`/`tenant2`, se copió el patrón canónico) + `test_multitenant_isolation_tabla_html.py` (nuevo). Cubre solo la superficie nueva (la vista HTML); **no es** el backfill completo de `test_multitenant_isolation.py` de 3 niveles que `facturas` sigue sin tener (eso es Fase 7, TEST-C2).

---

## Expansión — `compras`

**Backend nuevo:**
- `apps/tenant/compras/tables.py` (nuevo): `OrdenCompraTable`, 8 columnas (consecutivo, fechas, proveedor, proyecto, total, estado, acciones).
- `apps/tenant/compras/views.py` (nuevo): `OrdenCompraTableView`. `OrdenCompraSelector.get_list()` ya aceptaba `estado` como filtro — no hubo que tocar el Service Layer en absoluto, el único cambio fue empezar a pasarle ese parámetro desde `request.GET`.
- KPIs (Total Órdenes, Monto Total, Aprobadas, Pendientes) recalculados server-side sobre `self.object_list` (el queryset completo ya filtrado, antes de paginar) — mismo patrón que `gastos`, más preciso que el cálculo anterior basado en las filas que Tabulator tuviera cargadas.

**Frontend JS:** `compras_list.js` bajó de ~632 a ~330 líneas. Se eliminó: inicialización de Tabulator, `getColumnas()` (~145 líneas), `actualizarKPIs()`, y el listener de `tab-activated` que inicializaba la tabla la primera vez que se activaba el módulo (ya no aplica: `hx-trigger="load"` carga el panel apenas se inserta el HTML). Se conservó intacto: la delegación de eventos de ver/editar/eliminar/cambiar-estado, el formulario completo de "Nueva Plantilla" (`initPlantillaForm`, sin relación con Tabulator), y el manejo de offcanvas.

**Hallazgo nuevo, no corregido (fuera de alcance de esta fase):** `compras` no tenía **ningún** archivo de test en `apps/tenant/compras/tests/` — ni siquiera el directorio existía (el único test de la app vive en `tests/tenant/compras/test_compras_plantillas.py`, con un patrón de test distinto — `SintelTenantTestCase`, no fixtures `tenant1`/`tenant2`). Se creó `apps/tenant/compras/tests/__init__.py` + `conftest.py` (mismo patrón canónico) + `test_multitenant_isolation_tabla_html.py`, cubriendo solo la vista nueva. El backfill completo (TEST-A1: "compras tiene 0/1 tests para un módulo financiero con DSV") sigue pendiente en Fase 7.

## 4. Decisiones de diseño relevantes

- **La API DRF no se tocó ni se eliminó.** `GastoViewSet`/`ResolucionDIANViewSet` siguen existiendo intactos — las vistas nuevas son un camino de renderizado paralelo (HTML) para el grid del workspace, no un reemplazo del backend API-first. Esto evita cualquier riesgo de regresión en los tests IDOR ya existentes (`test_multitenant_isolation_gastos`) y mantiene la API disponible para consumidores externos.
- **`django-tables2` como `TENANT_APPS`, no `SHARED_APPS`:** la librería no tiene modelos ni necesita tabla propia; se agregó solo donde se usa (vistas tenant). Si en Fase 5-BIS (expansión) se detecta que el Console público (`apps/public/`) también la necesita, se deberá agregar a `SHARED_APPS` en ese momento — no se hizo preventivamente para no ampliar el alcance de este piloto.
- **No se migró la pestaña "Resoluciones DIAN" a una app distinta ni se dejó a medias:** se decidió migrar ambas grillas del módulo `gastos` en el mismo piloto (no solo una), para que la validación cubra un caso "app completa", no "media app con dos tecnologías mezcladas".

## 5. Archivos tocados (las 3 apps de esta sesión)

```
M  requirements.txt
M  config/settings.py
M  documentacion/PLAN_UNICO_CORRECCIONES.md

# gastos (piloto)
M  apps/tenant/gastos/urls.py
M  apps/tenant/gastos/templates/tenant/gastos/gastos_list.html
M  apps/tenant/gastos/static/gastos/js/features/gasto_list.js
M  apps/tenant/gastos/tests/test_multitenant_isolation.py
?? apps/tenant/gastos/tables.py
?? apps/tenant/gastos/views.py
?? apps/tenant/gastos/templates/tenant/gastos/partials/tabla_gastos.html
?? apps/tenant/gastos/templates/tenant/gastos/partials/tabla_resoluciones.html

# facturas
M  apps/tenant/facturas/urls.py
M  apps/tenant/facturas/templates/tenant/facturas/list_factura.html
M  apps/tenant/facturas/static/js/facturas/features/facturas_list.js
?? apps/tenant/facturas/tables.py
?? apps/tenant/facturas/views.py
?? apps/tenant/facturas/templates/tenant/facturas/partials/tabla_facturas.html
?? apps/tenant/facturas/tests/conftest.py
?? apps/tenant/facturas/tests/test_multitenant_isolation_tabla_html.py

# compras
M  apps/tenant/compras/urls.py
M  apps/tenant/compras/templates/tenant/compras/compras_list.html
M  apps/tenant/compras/static/compras/js/features/compras_list.js
?? apps/tenant/compras/tables.py
?? apps/tenant/compras/views.py
?? apps/tenant/compras/templates/tenant/compras/partials/tabla_compras.html
?? apps/tenant/compras/tests/__init__.py
?? apps/tenant/compras/tests/conftest.py
?? apps/tenant/compras/tests/test_multitenant_isolation_tabla_html.py

?? documentacion/REPORTE_FASE_5_PILOTO_TABLAS.md
```

No se ejecutó ningún `git add`/`git commit`.

## 6. Checklist de cierre (piloto + expansión facturas/compras)

- [x] 0 `SyntaxError` en los 14 archivos `.py` tocados/nuevos de las 3 apps (`py_compile` limpio, barrido completo).
- [x] 0 `SyntaxError` en los 3 archivos `.js` tocados (`node --check` limpio: `gasto_list.js`, `facturas_list.js`, `compras_list.js`).
- [x] La API DRF existente no fue modificada en ninguna de las 3 apps.
- [x] Los `accessor`/`order_by` de cada columna de cada `tables.py` referencian campos reales del modelo (verificado leyendo `models.py` de cada app línea por línea, no asumidos desde nombres de serializer).
- [x] Test de aislamiento multi-tenant nuevo por app (3 archivos), siguiendo el mismo patrón `tenant1`/`tenant2` ya validado.
- [x] `facturas`/`compras` no tenían la infraestructura de fixtures `tenant1`/`tenant2` — se creó (`conftest.py` copiado del patrón canónico) en vez de omitir el test por falta de infraestructura.
- [x] Simplificaciones respecto a la versión Tabulator documentadas explícitamente por app (§"Expansión — facturas" punto 1-4; KPIs recalculados server-side en `gastos`/`compras`), no dejadas implícitas.
- [ ] **Pendiente (bloqueado por entorno, diferido a propósito al final de toda la expansión — decisión del usuario):** ejecución real de `pytest` de las 3 apps, render en navegador de las 4 grillas (Documentos Soporte, Resoluciones DIAN, Facturas Ventas, Facturas Compras, Órdenes de Compra), confirmación de que `django_tables2/bootstrap5.html` existe en la versión instalada.

## 7. Siguiente paso

Continuar la expansión al resto de apps pendientes (tabla de progreso en `PLAN_UNICO_CORRECCIONES.md` §"FASE 5-BIS"), priorizando `ventas` y `contabilidad` (siguientes en el criterio "apps que tocan dinero primero"). La validación real en un entorno Docker/venv funcional (pytest + navegador) se ejecuta una sola vez al cerrar la tabla completa, no después de cada app — si esa validación final encuentra un defecto sistémico en el patrón (no específico de una app), se corrige una vez y se reaplica a todas las apps ya migradas.
