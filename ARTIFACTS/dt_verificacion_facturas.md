# Verificación Técnica - Facturas DataTables Server-Side

**Fecha**: 2024-12-19  
**Estado**: ✅ Configuración Completa - Pendiente Pruebas Manuales

---

## ✅ Verificaciones Completadas

### 1. Backend - Endpoint DataTables

#### Archivo: `apps/tenant/facturas/api/datatables.py`
- ✅ Endpoint `facturas_dt` creado
- ✅ Usa `@api_view(['POST'])`
- ✅ Autenticación: `SessionAuthentication`
- ✅ Permisos: `IsAuthenticated`
- ✅ Usa `DataTableSpec` y `DataTableServer` (Arquitectura v2.37)
- ✅ `fields_map` configurado (0-6):
  - 0: `numero`
  - 1: `fecha_emision`
  - 2: `naturaleza`
  - 3: `emisor_razon_social`
  - 4: `receptor_razon_social`
  - 5: `total`
  - 6: `cufe`
- ✅ `search_fields` configurados: `["numero", "emisor_razon_social", "receptor_razon_social", "cufe"]`
- ✅ `base_qs` optimizado con `only()` para campos mínimos
- ✅ Serializer: `FacturaListDTSerializer`

#### Archivo: `apps/tenant/facturas/api/urls.py`
- ✅ Ruta expuesta: `path("dt/facturas/", facturas_dt, name="facturas_dt")`
- ✅ Incluida en `config/api_urls.py` bajo `/api/v1/facturas/`
- ✅ URL completa: `/api/v1/facturas/dt/facturas/`

#### Archivo: `apps/tenant/facturas/api/serializers.py`
- ✅ `FacturaListDTSerializer` existe
- ✅ Campos: `("id", "numero", "fecha_emision", "naturaleza", "emisor", "receptor", "total", "cufe")`
- ✅ `emisor` y `receptor` mapeados desde `emisor_razon_social` y `receptor_razon_social`

### 2. Frontend - HTML y Estructura

#### Archivo: `apps/tenant/core/templates/tenant/core/partials/facturas/list.html`
- ✅ Estructura canónica DataTables:
  - `<thead>` con columnas definidas
  - `<tbody>` vacío (se llena vía AJAX)
  - Sin JavaScript inline
- ✅ Columnas: Número, Emisión, Naturaleza, Emisor, Receptor, Total, CUFE, Acciones
- ✅ Toolbar con botones:
  - `#btn-facturas-refrescar` (Refrescar)
  - `#btn-facturas-importar` (Importar)
- ✅ Feedback container: `#facturas-list-feedback`
- ✅ ID de tabla: `#dt-facturas-main`

#### Archivo: `apps/tenant/core/templates/tenant/core/partials/facturas/assets_facturas.html`
- ✅ Scripts cargados en orden correcto:
  1. `lib/http.js`
  2. `facturas.api.js`
  3. `facturas.components.js`
  4. `facturas.table.js`
  5. `facturas.modals.js`
  6. `facturas.page.js`

### 3. Frontend - JavaScript

#### Archivo: `apps/tenant/core/static/core/js/facturas/facturas.table.js`
- ✅ Función `window.initDataTable_FACTURAS()` exportada
- ✅ Configuración DataTables:
  - `serverSide: true`
  - `processing: true`
  - `responsive: true`
  - `deferRender: true`
  - `pageLength: 10`
  - `order: [[1, 'desc']]` (por Emisión descendente)
- ✅ AJAX configurado:
  - `type: 'POST'`
  - `headers: { 'X-CSRFToken': csrf }`
  - `xhrFields: { withCredentials: true }`
  - URL: `/api/v1/facturas/dt/facturas/`
- ✅ Columnas definidas con `data` y `name`:
  - `numero`
  - `fecha_emision` (con render de fecha)
  - `naturaleza` (con render de badge)
  - `emisor`
  - `receptor`
  - `total` (con render de moneda)
  - `cufe` (con render de truncado)
  - `acciones` (con render de botones)
- ✅ `renderAcciones()` genera botones con `data-action` y `data-id`
- ✅ Botón refrescar vinculado: `$('#btn-facturas-refrescar').on('click', ...)`
- ✅ Función `window.reloadDT_FACTURAS()` exportada

#### Archivo: `apps/tenant/core/static/core/js/facturas/facturas.page.js`
- ✅ Función `window.initFacturasPage()` exportada
- ✅ Carga HTML inline de `list.html` (sin filtros, columnas simplificadas)
- ✅ Inicializa `window.initDataTable_FACTURAS()` tras montar vista
- ✅ Event delegation para acciones:
  - `data-action="view"` → `showFacturaDetail()`
  - `data-action="xml"` → `showFacturaXML()`
  - `data-action="delete"` → `confirmDeleteFactura()`
- ✅ Usa `window.reloadDT_FACTURAS()` tras acciones (eliminar, importar)
- ✅ Modal de importar configurado

### 4. Integración - Router y Workspace

#### Archivo: `apps/tenant/core/static/core/js/router.js`
- ✅ Ruta `#facturas` configurada
- ✅ Inicializa `window.initFacturasPage()`

#### Archivo: `apps/tenant/core/templates/tenant/core/workspace.html`
- ✅ Incluye `assets_facturas.html`
- ✅ Link de navegación: `<a href="#facturas" data-view="facturas">`
- ✅ Router outlet: `#workspace-router-outlet`

### 5. Verificaciones de Sintaxis

- ✅ `python manage.py check --deploy` ejecutado (solo warnings de seguridad esperados)
- ✅ Importaciones verificadas: `DataTableSpec`, `DataTableServer`, `facturas_dt`
- ✅ Sin errores de linter en archivos modificados

---

## ⏳ Pruebas Pendientes (Manuales)

### Pruebas Funcionales
1. **Carga Inicial**: Verificar que la tabla se carga al navegar a `#facturas`
2. **Paginación**: Probar cambio de página (10, 25, 50 registros)
3. **Ordenamiento**: Probar ordenar por columnas (Número, Emisión, Total)
4. **Búsqueda Global**: Probar búsqueda en campo de DataTables
5. **Botón Refrescar**: Verificar que recarga sin cambiar de página
6. **Acciones - Ver**: Probar botón "Ver" abre modal de detalle
7. **Acciones - XML**: Probar botón "Ver XML" muestra XML
8. **Acciones - Eliminar**: Probar eliminación y recarga automática
9. **Importar Factura**: Probar modal de importar (preview y guardar)

### Pruebas de Red (DevTools)
1. **Método POST**: Verificar que todas las peticiones a `/dt/facturas/` son POST
2. **CSRF Token**: Verificar header `X-CSRFToken` en todas las peticiones
3. **Contrato DataTables**: Verificar respuesta JSON con `draw`, `recordsTotal`, `recordsFiltered`, `data`
4. **Sin GET**: Verificar que no hay peticiones GET para cargar la tabla

### Pruebas de Errores
1. **Error de Red**: Simular desconexión y verificar feedback
2. **Error 400/422**: Verificar manejo de errores de validación
3. **Error 403**: Verificar manejo de permisos

---

## 📋 Checklist de Aceptación (DoD)

- [x] `list.html` usa canon DataTables (thead limpio, tbody vacío, sin JS inline)
- [x] `facturas.table.js` con `serverSide:true`, `processing:true`, POST + CSRF
- [x] Backend `/dt/facturas/` devuelve contrato DataTables estándar
- [x] `urls.py` expone `/api/v1/facturas/dt/facturas/` (POST)
- [x] `facturas.page.js` inicializa la tabla al montar la vista
- [ ] **Pendiente**: Todas las pruebas manuales pasan
- [ ] **Pendiente**: Sin errores en consola del navegador
- [ ] **Pendiente**: Sin errores en logs del servidor

---

## 🔗 Referencias

- **Arquitectura v2.37**: DataTables server-side con POST + CSRF
- **DataTableSpec/DataTableServer**: Helper en `apps/shared/datatable.py`
- **Documentación DataTables**: https://datatables.net/manual/server-side
- **Smoke Tests**: Ver `ARTIFACTS/dt_smoke_report_facturas.md`

---

## 📝 Notas

- El endpoint está configurado y listo para pruebas
- Todas las importaciones y configuraciones están correctas
- La estructura HTML y JavaScript está alineada con el estándar
- Las pruebas manuales deben ejecutarse en un entorno con datos de prueba
- Verificar que el usuario tenga permisos para acceder a `/workspace/#facturas`

---

**Última actualización**: 2024-12-19
