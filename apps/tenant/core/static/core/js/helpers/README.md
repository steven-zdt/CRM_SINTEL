# Helpers Core — SINTEL v2.37

## lib/

- **http.js / api-helpers.js**: transporte HTTP + CSRF (mutaciones con header), `safeFetchJson`.
- **dom-utils.js**: visibilidad real (tabs/accordions) con `awaitVisibleAny` / `onVisibleOnce`.
- **datatables-utils.js**: `initServerSide({ table, endpoint, columns, options })` (POST + CSRF, deferRender, safeDestroy, ajuste en tabs).
  > Ajustar columnas en tabs: `columns.adjust()` + `responsive.recalc()` cuando el tab se muestra. [stackoverflow.com](https://stackoverflow.com/questions/70101412/how-to-make-datatable-responsive-in-bootstrap-tabs), [xjavascript.com](https://www.xjavascript.com/blog/datatables-setting-column-width/)

## helpers/

- **routes.js**: discovery (soporta subclaves `inventario.catalogo`, `contabilidad.asientos`).
- **crud.js**: `create/read/update/delete/readSingleton/updateSingleton` (devuelve `{ok,status,data}`).
- **module.js**: bootstrap estándar con `onInit/onBindEvents`.
- **error-service.js**: `DataTable.ext.errMode='none'` + listener `dt-error`. [dtdocs.com](https://dtdocs.com/), [stackoverflow.com](https://stackoverflow.com/questions/74244263/how-do-i-make-deferrender-work-for-datatables-on-a-page-client-side-processing)

## Convenciones

- **Server-side** en tablas grandes; evita re‑init. [datatables.net](https://datatables.net/examples/data_sources/server_side), [datatables.net](https://datatables.net/reference/option/stateSave)
- **stateSave** + `ajax.reload(null,false)` para no pisar estado al refrescar. [jqueryscript.net](https://www.jqueryscript.net/demo/DataTables-Jquery-Table-Plugin/examples/basic_init/state_save.html), [dev.to](https://dev.to/markpelf/aspnet8-using-datatablesnet-part3-state-saving-5gai)
- **CSRF** en todas las mutaciones; para DataTables usa `ajax.beforeSend`. [stackoverflow.com](https://stackoverflow.com/questions/28417781/jquery-add-csrf-token-to-all-post-requests-data)

## Ejemplo: Antes → Después

### Antes
```javascript
// ❌ URLs hardcodeadas
const API_DT = '/api/v1/facturas/dt/';
const CSRF = getCookie('csrftoken');

// ❌ setTimeout para visibilidad
setTimeout(() => {
  if ($('#table-facturas').is(':visible')) {
    initDataTable();
  }
}, 300);

// ❌ Inicialización manual
$('#table-facturas').DataTable({
  serverSide: true,
  ajax: { url: API_DT, type: 'POST', headers: { 'X-CSRFToken': CSRF } },
  columns: COLUMNS
});
```

### Después
```javascript
// ✅ Routes para discovery
const routes = await Routes.get('facturas');
const endpoint = routes?.datatable || '/api/v1/facturas/dt/';

// ✅ DOMUtils para visibilidad
await DOMUtils.awaitVisibleAny(['#table-facturas', '#tab-facturas.active'], { timeout: 6000 });

// ✅ DataTablesUtils.initServerSide (CSRF automático)
const dt = await DataTablesUtils.initServerSide({
  table: '#table-facturas',
  endpoint: endpoint,
  columns: COLUMNS,
  options: { rowId: 'id', order: [[2, 'desc']] }
});

// ✅ CRUD helper
const result = await CRUD.create('facturas', payload);
if (result.ok) {
  dt.refreshSafe(); // o dt.ajax.reload(null, false)
}
```
