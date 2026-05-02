# Progreso de Propagación DataTables - TODAS las TENANT_APPS

**Fecha**: 2024-12-19  
**Estado**: En Progreso

---

## ✅ Apps Completadas (Backend + Frontend)

### 1. **Facturas** ✅
- [x] `apps/tenant/facturas/api/datatables.py`
- [x] `apps/tenant/facturas/api/urls.py` (ruta `/dt/facturas/`)
- [x] `FacturaListDTSerializer` en serializers.py
- [x] `apps/tenant/core/templates/tenant/core/partials/facturas/list.html`
- [x] `apps/tenant/core/static/core/js/facturas/facturas.table.js`
- [x] `apps/tenant/core/static/core/js/facturas/facturas.page.js` (inicializa DT)

### 2. **Proveedores** ✅ (Backend completo, verificar frontend)
- [x] `apps/tenant/proveedores/api/datatables.py`
- [x] `apps/tenant/proveedores/api/urls.py` (verificar ruta)
- [x] `ProveedorListSerializer` existe
- [ ] `apps/tenant/core/templates/tenant/core/partials/proveedores/list.html` (verificar estructura)
- [ ] `apps/tenant/core/static/core/js/proveedores/proveedores.table.js` (verificar)
- [ ] `apps/tenant/core/static/core/js/proveedores/proveedores.page.js` (verificar inicialización)

### 3. **Gastos** ✅ (Backend completo, verificar frontend)
- [x] `apps/tenant/gastos/api/datatables.py`
- [x] `apps/tenant/gastos/api/urls.py` (verificar ruta)
- [x] `GastoListSerializer` existe
- [ ] `apps/tenant/core/templates/tenant/core/partials/gastos/list.html` (verificar estructura)
- [ ] `apps/tenant/core/static/core/js/gastos/gastos.table.js` (verificar)
- [ ] `apps/tenant/core/static/core/js/gastos/gastos.page.js` (verificar inicialización)

### 4. **Empleados** ✅ (Backend completo, verificar frontend)
- [x] `apps/tenant/empleados/api/datatables.py`
- [x] `apps/tenant/empleados/api/urls.py` (verificar ruta)
- [x] `EmpleadoListSerializer` existe
- [ ] `apps/tenant/core/templates/tenant/core/partials/empleados/list.html` (verificar estructura)
- [ ] `apps/tenant/core/static/core/js/empleados/empleados.table.js` (verificar)
- [ ] `apps/tenant/core/static/core/js/empleados/empleados.page.js` (verificar inicialización)

---

## 🚧 Apps en Progreso (Backend creado, falta Frontend)

### 5. **Contabilidad** ✅
- [x] `apps/tenant/contabilidad/api/datatables.py` (cuentas + asientos)
- [x] `apps/tenant/contabilidad/api/urls.py` (rutas `/dt/cuentas-contables/` y `/dt/asientos-contables/`)
- [x] `CuentaContableListDTSerializer` creado
- [x] `AsientoContableListDTSerializer` creado
- [x] `apps/tenant/core/templates/tenant/core/partials/contabilidad/list_cuentas.html`
- [x] `apps/tenant/core/templates/tenant/core/partials/contabilidad/list_asientos.html`
- [x] `apps/tenant/core/static/core/js/contabilidad/contabilidad.table.js`
- [x] `apps/tenant/core/static/core/js/contabilidad/contabilidad.page.js` (inicializar ambos DTs)
- [x] `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_contabilidad.html` (actualizado)

### 6. **Inventario** ✅
- [x] `apps/tenant/inventario/api/datatables.py` (catálogo + activos + movimientos)
- [x] `apps/tenant/inventario/api/urls.py` (rutas `/dt/catalogo/`, `/dt/activos-fijos/`, `/dt/movimientos/`)
- [x] Serializers existen (`CatalogoItemSerializer`, `ActivoFijoSerializer`, `MovimientoInventarioSerializer`)
- [x] `apps/tenant/core/templates/tenant/core/partials/inventario/list_catalogo.html`
- [x] `apps/tenant/core/templates/tenant/core/partials/inventario/list_activos.html`
- [x] `apps/tenant/core/templates/tenant/core/partials/inventario/list_movimientos.html`
- [x] `apps/tenant/core/static/core/js/inventario/inventario.table.js`
- [x] `apps/tenant/core/static/core/js/inventario/inventario.page.js` (inicializar todos los DTs)
- [x] `apps/tenant/core/templates/tenant/core/partials/inventario/assets_inventario.html` (actualizado)

### 7. **Clientes** ✅
- [x] `apps/tenant/clientes/api/datatables.py`
- [x] `apps/tenant/clientes/api/urls.py` (ruta `/dt/clientes/`)
- [x] `ClienteListSerializer` existe
- [x] `apps/tenant/core/templates/tenant/core/partials/clientes/list.html`
- [x] `apps/tenant/core/static/core/js/clientes/clientes.table.js`
- [x] `apps/tenant/core/static/core/js/clientes/clientes.page.js` (inicializar DT)
- [x] `apps/tenant/core/templates/tenant/core/partials/clientes/assets_clientes.html`

---

## ⏭️ Apps que NO requieren DataTables

### 8. **Empresa** ⏭️
- ⚠️ Singleton: Solo hay una empresa por tenant
- No requiere listado DataTables (solo formulario de edición)

### 9. **Landing** ⏭️
- Panel informativo, no requiere DataTables

### 10. **Dashboard** ⏭️
- Panel de indicadores, no requiere DataTables

### 11. **Perfil** ⏭️
- Formulario de perfil, no requiere DataTables

---

## 📋 Checklist de Implementación por App

Para cada app que requiere DataTables:

### Backend
- [ ] `apps/tenant/<app>/api/datatables.py` con función `*_dt()`
- [ ] `apps/tenant/<app>/api/urls.py` con ruta `path("dt/<resource>/", ...)`
- [ ] Serializer DT mínimo en `serializers.py` (ej: `*ListDTSerializer`)

### Frontend HTML
- [ ] `apps/tenant/core/templates/tenant/core/partials/<app>/list.html` con estructura canónica:
  - `<thead>` con columnas
  - `<tbody>` vacío
  - Sin JS inline
  - ID de tabla: `#dt-<app>-main`
  - Feedback container: `#<app>-list-feedback`
  - Toolbar con botón refrescar

### Frontend JavaScript
- [ ] `apps/tenant/core/static/core/js/<app>/<app>.table.js` con:
  - `window.initDataTable_<APP>()` exportado
  - `window.reloadDT_<APP>()` exportado
  - Configuración: `serverSide: true`, `processing: true`, POST + CSRF
  - Columnas con `data` y `name` alineadas con backend
- [ ] `apps/tenant/core/static/core/js/<app>/<app>.page.js` que:
  - Inyecta `list.html`
  - Llama a `window.initDataTable_<APP>()` tras montar vista
  - Usa `window.reloadDT_<APP>()` tras acciones

### Integración
- [ ] `apps/tenant/core/templates/tenant/core/partials/<app>/assets_<app>.html` incluye `<app>.table.js`
- [ ] `apps/tenant/core/static/core/js/router.js` tiene ruta `#<app>` → `init<App>Page`
- [ ] `apps/tenant/core/templates/tenant/core/workspace.html` incluye `assets_<app>.html`

---

## 🎯 Próximos Pasos

1. **Verificar apps existentes** (proveedores, gastos, empleados):
   - Revisar `list.html` si tienen estructura canónica
   - Revisar `.table.js` si usan DataTables server-side
   - Actualizar si es necesario

2. **Completar apps en progreso** (contabilidad, inventario, clientes):
   - Crear `list.html` para cada recurso
   - Crear `.table.js` con inicialización DataTables
   - Actualizar `.page.js` para inicializar DTs

3. **Validación final**:
   - Verificar que todas las rutas `/dt/` estén expuestas
   - Verificar que todos los serializers DT existan
   - Verificar que todos los `list.html` tengan estructura canónica
   - Verificar que todos los `.table.js` usen POST + CSRF
   - Ejecutar smoke tests

---

**Última actualización**: 2024-12-19
