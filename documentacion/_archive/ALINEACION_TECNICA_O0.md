# Alineación técnica — Fase 0

**Fecha:** 2024-12-19  
**Versión:** v2.37  
**Objetivo:** Verificar y corregir orden de carga Core → App, normalizar assets_core.html, agregar `style="width:100%"` a tablas DataTables, y crear sanity-check de helpers.

---

## 1) Partials corregidos (orden de carga)

Todos los partials de apps verificados y confirmados con orden correcto: **Core → App**

### Partials verificados (todos OK):

- ✅ `apps/tenant/facturas/templates/tenant/facturas/partials/assets_facturas.html` → OK
- ✅ `apps/tenant/clientes/templates/tenant/clientes/partials/assets_clientes.html` → OK
- ✅ `apps/tenant/gastos/templates/tenant/gastos/partials/assets_gastos.html` → OK
- ✅ `apps/tenant/empleados/templates/tenant/empleados/partials/assets_empleados.html` → OK
- ✅ `apps/tenant/proveedores/templates/tenant/proveedores/partials/assets_proveedores.html` → OK
- ✅ `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/assets_cuentas.html` → OK
- ✅ `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/assets_asientos.html` → OK
- ✅ `apps/tenant/inventario/templates/tenant/inventario/partials/assets_inventario.html` → OK
- ✅ `apps/tenant/empresa/templates/tenant/empresa/partials/assets_empresa.html` → OK
- ✅ `apps/tenant/perfil/templates/tenant/perfil/partials/assets_perfil.html` → OK

**Patrón verificado:**
```html
{% include 'tenant/core/partials/assets_core.html' %}
<script src="{% static 'core/js/{app}/{app}.page.js' %}"></script>
```

---

## 2) Tablas actualizadas con `style="width:100%"`

Todas las tablas DataTables ahora incluyen `style="width:100%"` explícito según mejores prácticas de DataTables para tablas en Bootstrap tabs.

### Tablas actualizadas:

- ✅ `apps/tenant/facturas/templates/tenant/facturas/partials/list.html` → `#table-facturas`
- ✅ `apps/tenant/clientes/templates/tenant/clientes/partials/list.html` → `#table-clientes`
- ✅ `apps/tenant/gastos/templates/tenant/gastos/partials/list.html` → `#table-gastos`
- ✅ `apps/tenant/empleados/templates/tenant/empleados/partials/list.html` → `#table-empleados`
- ✅ `apps/tenant/proveedores/templates/tenant/proveedores/partials/list.html` → `#table-proveedores`
- ✅ `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_cuentas.html` → `#table-contabilidad-cuentas`
- ✅ `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_asientos.html` → `#table-contabilidad-asientos`
- ✅ `apps/tenant/inventario/templates/tenant/inventario/partials/list_catalogo.html` → `#table-inventario-catalogo`
- ✅ `apps/tenant/inventario/templates/tenant/inventario/partials/list_activos.html` → `#table-inventario-activos`
- ✅ `apps/tenant/inventario/templates/tenant/inventario/partials/list_movimientos.html` → `#table-inventario-movimientos`
- ✅ `apps/tenant/empresa/templates/tenant/empresa/partials/list.html` → `#table-empresa`
- ✅ `apps/tenant/empresa/templates/tenant/empresa/partials/mailinbox_list.html` → `#table-mailinbox`

### Tablas en partials Core (también actualizadas):

- ✅ `apps/tenant/core/templates/tenant/core/partials/facturas/list.html` → `#table-facturas`
- ✅ `apps/tenant/core/templates/tenant/core/partials/clientes/list.html` → `#table-clientes`
- ✅ `apps/tenant/core/templates/tenant/core/partials/gastos/list.html` → `#table-gastos`
- ✅ `apps/tenant/core/templates/tenant/core/partials/empleados/list.html` → `#table-empleados`
- ✅ `apps/tenant/core/templates/tenant/core/partials/proveedores/list.html` → `#table-proveedores`
- ✅ `apps/tenant/core/templates/tenant/core/partials/contabilidad/list_cuentas.html` → `#table-contabilidad-cuentas`
- ✅ `apps/tenant/core/templates/tenant/core/partials/contabilidad/list_asientos.html` → `#table-contabilidad-asientos`
- ✅ `apps/tenant/core/templates/tenant/core/partials/inventario/list_catalogo.html` → `#table-inventario-catalogo`
- ✅ `apps/tenant/core/templates/tenant/core/partials/inventario/list_activos.html` → `#table-inventario-activos`
- ✅ `apps/tenant/core/templates/tenant/core/partials/inventario/list_movimientos.html` → `#table-inventario-movimientos`
- ✅ `apps/tenant/core/templates/tenant/core/partials/empresa/empresa_list.html` → `#table-empresa`
- ✅ `apps/tenant/core/templates/tenant/core/partials/mailinbox/list.html` → `#table-mailinbox`

**Total:** 24 tablas actualizadas

**Ejemplo de cambio:**
```html
<!-- Antes -->
<table id="table-facturas" class="table table-striped table-hover w-100">

<!-- Después -->
<table id="table-facturas" class="table table-striped table-hover w-100" style="width:100%">
```

---

## 3) Normalización de assets_core.html

### Orden verificado y corregido:

**PASO 1: Librerías base**
- ✅ `lib/http.js`
- ✅ `lib/api-helpers.js`
- ✅ `lib/dom-utils.js`
- ✅ `lib/datatables-utils.js`

**PASO 2: Helpers transversales**
- ✅ `helpers/routes.js`
- ✅ `helpers/crud.js`
- ✅ `helpers/module.js`

**PASO 3: Shim de depuración**
- ✅ Inicialización segura de `window.__DEBUG__`
- ✅ Sincronización con `API_HELPERS.DEBUG`

**PASO 4: Sanity check de helpers** (NUEVO)
- ✅ `lib/helpers_sanity_check.js` - Verificación automática de disponibilidad de helpers

**PASO 5: Hook global para ajuste de columnas DataTables** (NUEVO)
- ✅ Listener para `shown.bs.tab` (Bootstrap tabs)
- ✅ Listener para `shown.bs.collapse` (Bootstrap accordions)
- ✅ `columns.adjust()` y `responsive.recalc()` automáticos

---

## 4) Sanity-check de helpers (DOM Ready)

### Script creado:

**Archivo:** `apps/tenant/core/static/core/js/lib/helpers_sanity_check.js`

**Funcionalidad:**
- Verifica disponibilidad de todos los helpers Core antes de que los módulos los usen
- Verifica funciones críticas de cada helper
- Expone resultados en `window.__HELPERS_SANITY_CHECK`
- Logs en consola si hay errores (solo en modo DEBUG)

### Helpers verificados:

- ✅ **API_HELPERS** → OK
  - `safeFetchJson` → OK
  - `getCSRF` → OK
  - `withTrailingSlash` → OK

- ✅ **DOMUtils** → OK
  - `waitForVisible` → OK
  - `awaitVisibleAny` → OK

- ✅ **DataTablesUtils** → OK
  - `initServerSide` → OK
  - `safeDestroy` → OK

- ✅ **Routes** → OK
  - `get` → OK
  - `collectionUrl` → OK

- ✅ **CRUD** → OK
  - `create` → OK

- ✅ **Module** → OK
  - `init` → OK

---

## 5) Cambios en assets_core.html

### Agregado:

1. **Sanity check de helpers:**
```html
<!-- PASO 4: Sanity check de helpers (verificación de disponibilidad) -->
<script src="{% static 'core/js/lib/helpers_sanity_check.js' %}"></script>
```

2. **Hook global para ajuste de columnas:**
```html
<!-- PASO 5: Hook global para ajuste de columnas DataTables en tabs -->
<script>
  document.addEventListener('shown.bs.tab', function () {
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.dataTable) {
      window.jQuery.fn.dataTable.tables({ visible: true, api: true })
        .columns.adjust().responsive.recalc();
    }
  });
  
  document.addEventListener('shown.bs.collapse', function () {
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.dataTable) {
      window.jQuery.fn.dataTable.tables({ visible: true, api: true })
        .columns.adjust().responsive.recalc();
    }
  });
</script>
```

---

## 6) Criterios de aceptación (Fase 0)

### ✅ Todos cumplidos:

- [x] Todos los partials por app cargan primero `assets_core.html` y después los scripts de app
- [x] Todas las tablas con `id="table-..."` definen `style="width:100%"`
- [x] `helpers_sanity_check.js` creado y cargado en `assets_core.html`
- [x] `assets_core.html` normalizado con orden correcto y hooks de DataTables
- [x] Reportes `ALINEACION_TECNICA_O0.md` y `alineacion_tecnica_o0.json` generados

---

## 7) Resumen de cambios

### Archivos modificados:

1. **assets_core.html** - Normalizado con orden correcto, sanity check y hooks DataTables
2. **24 archivos de templates** - Tablas actualizadas con `style="width:100%"`
3. **helpers_sanity_check.js** - Creado (nuevo archivo)

### Archivos creados:

- `apps/tenant/core/static/core/js/lib/helpers_sanity_check.js`
- `ALINEACION_TECNICA_O0.md` (este archivo)
- `alineacion_tecnica_o0.json`

---

## 8) Próximos pasos

La Fase 0 está completa. Los módulos ahora tienen:

- ✅ Orden de carga garantizado (Core → App)
- ✅ Tablas con ancho 100% explícito (mejores prácticas DataTables)
- ✅ Sanity check automático de helpers
- ✅ Ajuste automático de columnas en tabs/accordions

**Listo para continuar con las siguientes fases del refactor.**

---

**Última actualización:** 2024-12-19  
**Versión:** v2.37  
**Mantenedor:** Equipo SINTEL
