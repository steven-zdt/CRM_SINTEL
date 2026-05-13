# Snippets Mínimos — DataTables (Orientativos)

**Objetivo:** Snippets listos para producción que implementan mejores prácticas de DataTables según documentación oficial.

---

## 1) Adapter DT en tabs — Ajustar columnas al mostrar la pestaña

**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/assets_core.html`

**Snippet:**
```html
<script>
  // Cuando un tab de Bootstrap se hace visible, recalcular columnas y responsive
  document.addEventListener('shown.bs.tab', function () {
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.dataTable) {
      window.jQuery
        .fn
        .dataTable
        .tables({ visible: true, api: true })
        .columns.adjust().responsive.recalc();
    }
  });
  
  // También para accordions
  document.addEventListener('shown.bs.collapse', function () {
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.dataTable) {
      window.jQuery
        .fn
        .dataTable
        .tables({ visible: true, api: true })
        .columns.adjust().responsive.recalc();
    }
  });
</script>
```

**Por qué:** DataTables recomienda recalcular tamaños cuando una tabla pasa de oculta a visible (`columns.adjust()` y, si usas la extensión Responsive, `responsive.recalc()`), especialmente en tabs/accordions. [stackoverflow.com](https://stackoverflow.com/questions/70101412/how-to-make-datatable-responsive-in-bootstrap-tabs), [xjavascript.com](https://www.xjavascript.com/blog/datatables-setting-column-width/)

**Estado:** ✅ Implementado en `assets_core.html` (PASO 5)

---

## 2) Inyección CSRF por tabla — Para DataTables server-side

**Ubicación:** `apps/tenant/core/static/core/js/lib/datatables-utils.js` (función `initServerSide`)

**Snippet:**
```javascript
$('#table-x').DataTable({
  serverSide: true,
  processing: true,
  ajax: {
    url: '/api/v1/x/dt/',
    type: 'POST',
    // Token fresco en cada request (reload/draw)
    beforeSend: function (xhr) {
      xhr.setRequestHeader('X-CSRFToken', API_HELPERS.getCSRF());
    },
    // Parámetros dinámicos por draw (filtros adicionales)
    data: function (d) {
      d.extra = $('#filter-x').val();  // ejemplo de filtro
      return d;
    }
  }
});
```

**Por qué:** Inyectar CSRF por request con `beforeSend` y usar `ajax.data` (función) para recalcular parámetros en cada draw es el patrón recomendado con DataTables. [stackoverflow.com](https://stackoverflow.com/questions/28417781/jquery-add-csrf-token-to-all-post-requests-data), [poligran-m...epoint.com]

**Estado:** ✅ Implementado en `datatables-utils.js` (Fase 2)

**Uso en módulos:**
```javascript
// Ya está integrado en initServerSide, solo necesitas:
const dt = await DataTablesUtils.initServerSide({
  table: '#table-x',
  endpoint: '/api/v1/x/dt/',
  columns: COLUMNS,
  options: {
    ajax: {
      data: function (d) {
        d.extra = $('#filter-x').val(); // Parámetros dinámicos
        return d;
      }
    }
  }
});
```

---

## 3) Error handling global — Sin alertas, con logging controlado

**Ubicación:** `apps/tenant/core/static/core/js/helpers/error-service.js`

**Snippet:**
```javascript
// Silenciar los alerts por defecto y manejar el evento de error de DataTables
$.fn.dataTable.ext.errMode = 'none';
$(document.body).on('dt-error.dt', function (_e, _settings, techNote, message) {
  console.error('DT error', techNote, message);
  // TODO: Mostrar toast/log centralizado, telemetría, etc.
});
```

**Por qué:** `DataTable.ext.errMode='none'` evita alertas intrusivas y permite gestionar errores con el evento `dt-error` (antes `error`), recomendado para integrar con tu logger/UX. [dtdocs.com](https://dtdocs.com/), [stackoverflow.com](https://stackoverflow.com/questions/74244263/how-do-i-make-deferrender-work-for-datatables-on-a-page-client-side-processing)

**Estado:** ✅ Implementado en `error-service.js` (Fase 1)

**Implementación actual:**
- `errMode='none'` configurado globalmente
- Listener `dt-error.dt` captura errores
- Logging en consola + feedback visual en tabla afectada

---

## 4) StateSave — Persistir búsqueda/orden/paginación

**Ubicación:** `apps/tenant/core/static/core/js/lib/datatables-defaults.js`

**Snippet mínimo (API moderna) para una tabla concreta:**
```javascript
new DataTable('#myTable', {
  stateSave: true,
  stateDuration: 7200 // segundos (2h) en localStorage; usa -1 para sessionStorage
});
```

**Por qué:** `stateSave` guarda y restaura orden, filtro y paginación; `stateDuration` define dónde y cuánto tiempo persiste (localStorage/sessionStorage). [jqueryscript.net](https://www.jqueryscript.net/demo/DataTables-Jquery-Table-Plugin/examples/basic_init/state_save.html), [stackoverflow.com](https://stackoverflow.com/questions/74244263/how-do-i-make-deferrender-work-for-datatables-on-a-page-client-side-processing)

**Estado:** ✅ Implementado globalmente en `datatables-defaults.js` (Fase 3)

**Configuración global:**
```javascript
// En datatables-defaults.js
$.extend(true, $.fn.dataTable.defaults, {
  stateSave: true,
  stateDuration: 7200, // 2 horas en localStorage
  // ...
});
```

**Uso en módulos:**
```javascript
// Ya está activo por defecto, pero puedes sobrescribir:
const dt = await DataTablesUtils.initServerSide({
  table: '#table-x',
  endpoint: '/api/v1/x/dt/',
  columns: COLUMNS,
  options: {
    stateSave: true,        // Opcional: ya está en defaults
    stateDuration: 7200     // Opcional: ya está en defaults
  }
});
```

---

## 5) Recarga sin perder estado — refreshSafe()

**Ubicación:** `apps/tenant/core/static/core/js/lib/datatables-utils.js` (función `initServerSide`)

**Snippet:**
```javascript
// Después de CRUD, recargar sin perder paginación/orden/búsqueda
const dt = $('#table-x').DataTable();

// Opción 1: Usar refreshSafe() (recomendado)
dt.refreshSafe?.() ?? dt.ajax.reload(null, false);

// Opción 2: Directamente
dt.ajax.reload(null, false); // null = mantener parámetros, false = no resetear paginación
```

**Por qué:** `ajax.reload(null, false)` y `draw(false)` son las formas seguras de no reiniciar paginación/orden/búsqueda al refrescar. [dev.to](https://dev.to/markpelf/aspnet8-using-datatablesnet-part3-state-saving-5gai)

**Estado:** ✅ Implementado en `datatables-utils.js` (Fase 3)

**Utilidad agregada:**
```javascript
// refreshSafe() está disponible en todas las instancias creadas con initServerSide
dt.refreshSafe(); // Equivalente a dt.ajax.reload(null, false)
```

---

## 6) Visibilidad robusta — awaitVisibleAny / onVisibleOnce

**Ubicación:** `apps/tenant/core/static/core/js/lib/dom-utils.js`

**Snippet:**
```javascript
// Esperar a que cualquiera de los selectores esté visible
await DOMUtils.awaitVisibleAny([
  '#table-x',
  '#tab-x.active',
  '#pane-x.show',
  '#x-container',
  '#workspace .tab-pane.show'
], { timeout: 6000 });

// Ejecutar callback cuando un elemento se vuelve visible (tabs/accordions)
DOMUtils.onVisibleOnce('#table-x', () => {
  initDataTable();
});
```

**Por qué:** Evita timeouts cuando las tablas están en tabs/accordions ocultos. [stackoverflow.com](https://stackoverflow.com/questions/70101412/how-to-make-datatable-responsive-in-bootstrap-tabs)

**Estado:** ✅ Implementado en `dom-utils.js` (Fase 0-1)

---

## 7) IDs estables — rowId

**Ubicación:** En opciones de `initServerSide`

**Snippet:**
```javascript
const dt = await DataTablesUtils.initServerSide({
  table: '#table-x',
  endpoint: '/api/v1/x/dt/',
  columns: COLUMNS,
  options: {
    rowId: 'id'  // o el campo único de tu recurso
  }
});
```

**Por qué:** IDs estables permiten selección/edición confiables. [rdrr.io](https://rdrr.io/cran/data.table/man/rowid.html), [quantargo.com](https://www.quantargo.com/help/r/latest/packages/data.table/as.data.table.html/rowid)

**Estado:** ✅ Implementado en módulos migrados (Fase 4)

---

## Resumen de Implementación

| Snippet | Ubicación | Estado |
|---------|-----------|--------|
| Ajuste columnas en tabs | `assets_core.html` (PASO 5) | ✅ |
| CSRF por request | `datatables-utils.js` (beforeSend) | ✅ |
| Error handling global | `error-service.js` | ✅ |
| StateSave global | `datatables-defaults.js` | ✅ |
| refreshSafe() | `datatables-utils.js` | ✅ |
| Visibilidad robusta | `dom-utils.js` | ✅ |
| rowId estable | Opciones de initServerSide | ✅ |

---

## Convenciones Aplicadas

- **Centraliza en Core:** transporte/CSRF, discovery de rutas, CRUD, adapter DataTables, manejo de errores y modales base.
- **Modulariza por app:** columnas/formatos/reglas UI y flujo propio.
- **Aplica sistemáticamente:** prácticas de DataTables para tabs ocultos, estado, rendimiento (server-side + deferRender) y errores, tal como recomiendan sus manuales.

---

## Referencias

- [DataTables - Responsive en Tabs](https://stackoverflow.com/questions/70101412/how-to-make-datatable-responsive-in-bootstrap-tabs)
- [DataTables - Ajuste de Columnas](https://www.xjavascript.com/blog/datatables-setting-column-width/)
- [DataTables - CSRF en AJAX](https://stackoverflow.com/questions/28417781/jquery-add-csrf-token-to-all-post-requests-data)
- [DataTables - Error Handling](https://dtdocs.com/)
- [DataTables - State Save](https://www.jqueryscript.net/demo/DataTables-Jquery-Table-Plugin/examples/basic_init/state_save.html)
- [DataTables - State Saving Best Practices](https://dev.to/markpelf/aspnet8-using-datatablesnet-part3-state-saving-5gai)
