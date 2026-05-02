# Reporte de Pruebas (Smoke Tests) - DataTables Server-Side

## Apps Implementadas

### ✅ Facturas
- **Endpoint**: `POST /api/v1/facturas/dt/facturas/`
- **Tabla**: `#dt-facturas-main`
- **JS**: `facturas.dt.js`
- **Estado**: ✅ Implementado
- **Pruebas**:
  - [ ] Abrir `/workspace/#facturas` → Tabla renderiza con loader y luego datos
  - [ ] Ordenar por columna "Emisión" → Backend recibe POST con order
  - [ ] Buscar término → Backend recibe POST con search[value]
  - [ ] Paginación (siguiente/anterior) → Llamadas POST con start/length
  - [ ] Filtros (naturaleza, NIT, fechas) → Viajan en ajax.data
  - [ ] Acciones (Ver/XML/Eliminar) → Abren modales y recargan tabla
  - [ ] Inspeccionar red → Solo POST (no GET) para carga principal

### ✅ Gastos
- **Endpoint**: `POST /api/v1/gastos/dt/gastos/`
- **Tabla**: `#dt-gastos-main`
- **JS**: `gastos.dt.js`
- **Estado**: ✅ Implementado
- **Pruebas**:
  - [ ] Abrir `/workspace/#gastos` → Tabla renderiza correctamente
  - [ ] Ordenar por "Monto" → Funciona
  - [ ] Buscar → Funciona
  - [ ] Filtros (categoría, fechas) → Funcionan
  - [ ] Acciones (Ver/Editar/Eliminar) → Funcionan
  - [ ] Inspeccionar red → Solo POST

### ✅ Proveedores
- **Endpoint**: `POST /api/v1/proveedores/dt/proveedores/`
- **Tabla**: `#dt-proveedores-main`
- **JS**: `proveedores.dt.js`
- **Estado**: ✅ Implementado
- **Pruebas**:
  - [ ] Abrir `/workspace/#proveedores` → Tabla renderiza correctamente
  - [ ] Ordenar por "Razón Social" → Funciona
  - [ ] Buscar → Funciona
  - [ ] Acciones (Ver/Editar/Eliminar) → Funcionan
  - [ ] Inspeccionar red → Solo POST

### ✅ Empleados
- **Endpoint**: `POST /api/v1/empleados/dt/empleados/`
- **Tabla**: `#dt-empleados-main`
- **JS**: `empleados.dt.js`
- **Estado**: ✅ Implementado
- **Pruebas**:
  - [ ] Abrir `/workspace/#empleados` → Tabla renderiza correctamente
  - [ ] Ordenar por "Nombre Completo" → Funciona
  - [ ] Buscar → Funciona
  - [ ] Acciones (Ver/Editar/Eliminar) → Funcionan
  - [ ] Inspeccionar red → Solo POST

---

## Checklist de Validación

### Frontend
- [x] `list.html` actualizado con estructura DataTables (thead limpio, sin scripts inline)
- [x] `<app>.dt.js` creado con inicialización POST server-side
- [x] CSRF token incluido en headers (`X-CSRFToken`)
- [x] `credentials: "same-origin"` configurado
- [x] Columnas definidas en `columns` coinciden con thead
- [x] Filtros integrados en `ajax.data`
- [x] `window.<app>DT.reload()` expuesto para refrescos
- [x] Assets actualizados (`assets_<app>.html` incluye `<app>.dt.js`)
- [x] `page.js` inicializa DataTables y bindea eventos

### Backend
- [x] Endpoints `/dt/<resource>/` creados con `@api_view(['POST'])`
- [x] `DataTableSpec` configurado con `fields_map` y `search_fields`
- [x] QuerySet optimizado con `only()` y `select_related()`/`prefetch_related()`
- [x] Serializer mínimo (`*ListSerializer`) con solo campos visibles
- [x] `extra_filter` implementado para filtros adicionales
- [x] Respuesta con contrato DataTables: `{draw, recordsTotal, recordsFiltered, data}`
- [x] URLs registradas en `urls.py`

### Integración
- [x] `workspace.html` extiende `tenant/base.html` (hereda DataTables CSS/JS)
- [x] Router (`router.js`) tiene todas las rutas configuradas
- [x] `window.init<App>Page()` inyecta `list.html` y `modals.html`
- [x] Modales funcionan y recargan tabla tras acciones

---

## Errores Comunes a Verificar

1. **CSRF 403**: Verificar que `X-CSRFToken` esté en headers y cookie presente
2. **404 en /dt/**: Verificar que URLs estén registradas en `urls.py`
3. **Columnas no coinciden**: Verificar `fields_map` vs `columns` en JS
4. **GET en lugar de POST**: Verificar `type: 'POST'` en `ajax` config
5. **Tabla no inicializa**: Verificar que jQuery y DataTables estén cargados antes de `<app>.dt.js`

---

**Última actualización**: 2024-12-19  
**Versión**: 1.0
