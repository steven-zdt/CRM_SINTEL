# Fase 4 - Migración por App - Progreso

## ✅ Módulos Completados

### 1. Proveedores (`proveedores.page.js`)
- ✅ Migrado a server-side con `DataTablesUtils.initServerSide`
- ✅ `rowId:'id'` agregado para IDs estables
- ✅ `refreshSafe()` implementado en todos los refrescos (4 ocurrencias)
- ✅ `awaitVisibleAny` para visibilidad robusta en tabs
- ✅ Endpoint: `/api/v1/proveedores/dt/proveedores/`

### 2. Gastos (`gastos.page.js`)
- ✅ Migrado a server-side con `DataTablesUtils.initServerSide`
- ✅ `rowId:'id'` agregado para IDs estables
- ✅ `refreshSafe()` implementado en todos los refrescos (5 ocurrencias)
- ✅ `awaitVisibleAny` para visibilidad robusta en tabs
- ✅ Endpoint: `/api/v1/gastos/dt/gastos/`

## 🔄 Módulos Pendientes

### 3. Empleados (`empleados.page.js`)
- [ ] Migrar a server-side con `initServerSide`
- [ ] Agregar `rowId:'id'`
- [ ] Reemplazar todos los `state.table.clear()` + `rows.add()` + `draw()` por `refreshSafe()`
- [ ] Endpoint: `/api/v1/empleados/dt/empleados/`

### 4. Facturas (`facturas.page.js`)
- [ ] Ya usa server-side, pero necesita:
  - [ ] Agregar `rowId:'id'` en opciones
  - [ ] Verificar que todos los refrescos usen `refreshSafe()`
  - [ ] Migrar a `Module.init` (opcional, patrón manual también válido)

### 5. Contabilidad (múltiples tablas)
- [ ] `cuentas.page.js`:
  - [ ] Migrar a server-side con `initServerSide`
  - [ ] Agregar `rowId:'id'`
  - [ ] Endpoint: `Routes.get('contabilidad').cuentas.datatable`
- [ ] `asientos.page.js`:
  - [ ] Migrar a server-side con `initServerSide`
  - [ ] Agregar `rowId:'id'`
  - [ ] Endpoint: `Routes.get('contabilidad').asientos.datatable`
- [ ] Asegurar `awaitVisibleAny` separado para cada tabla
- [ ] Handler global para `shown.bs.tab` que ajuste columnas

### 6. Inventario (subclaves)
- [ ] `catalogo.page.js`:
  - [ ] Migrar a server-side con `initServerSide`
  - [ ] Agregar `rowId:'id'`
  - [ ] Endpoint: `Routes.get('inventario.catalogo').datatable`
- [ ] `activos.page.js`:
  - [ ] Migrar a server-side con `initServerSide`
  - [ ] Agregar `rowId:'id'`
  - [ ] Endpoint: `Routes.get('inventario.activos').datatable`
- [ ] `movimientos.page.js` (si aplica):
  - [ ] Migrar a server-side con `initServerSide`
  - [ ] Agregar `rowId:'id'`
  - [ ] Endpoint: `Routes.get('inventario.movimientos').datatable`

### 7. Clientes (`clientes.page.js`)
- [ ] Verificar si ya usa `Module.init` o necesita migración
- [ ] Agregar `rowId:'id'` si falta
- [ ] Verificar que todos los refrescos usen `refreshSafe()` o `replaceDataSafe()`

### 8. Empresa y Perfil (singletons)
- [ ] Verificar que usen `CRUD.readSingleton` y `CRUD.updateSingleton`
- [ ] No requieren DataTables (a menos que tengan listas auxiliares)

## 📋 Patrón de Migración Aplicado

Para cada módulo:

1. **Cambiar `initDataTable*()` a server-side:**
```javascript
// Antes (client-side):
const rows = await fetchList();
state.table = w.DataTablesUtils.initOrUpdateDataTable(tableEl, {
  data: rows,
  columns: columns,
  // ...
});

// Después (server-side):
const routes = state.routes || await w.Routes?.get(MOD);
const endpoint = routes?.datatable || '/api/v1/{modulo}/dt/{modulo}/';
state.table = await w.DataTablesUtils.initServerSide({
  table: TABLE_ID,
  endpoint: endpoint,
  columns: columns,
  options: {
    rowId: 'id',  // ⚠️ FASE 4: IDs estables
    // stateSave ya viene de defaults (Fase 3)
  }
});
```

2. **Reemplazar todos los refrescos:**
```javascript
// Antes:
state.table.clear();
const rows = await fetchList();
state.table.rows.add(rows).draw();

// Después:
if (state.table.refreshSafe && typeof state.table.refreshSafe === 'function') {
  await state.table.refreshSafe();
} else if (state.table.ajax && typeof state.table.ajax.reload === 'function') {
  state.table.ajax.reload(null, false);
} else {
  await initDataTable();
}
```

3. **Asegurar visibilidad robusta:**
```javascript
await w.DOMUtils.awaitVisibleAny([
  TABLE_ID,
  `#tab-${MOD}.active`,
  `#pane-${MOD}.show`,
  `#${MOD}-container`,
  '#workspace .tab-pane.show'
], { timeout: 6000 });
```

## ✅ Criterios de Aceptación

- [x] 0 warnings/errores de re-init (usar `retrieve:true`/`destroy:true` en `initServerSide`)
- [x] Al cambiar de tab, la tabla se ve correcta (hook global en `assets_core.html` ajusta columnas)
- [x] CRUD funciona con CSRF (headers por request en `beforeSend`)
- [x] IDs estables (`rowId:'id'` o `DT_RowId` desde backend)
- [x] Refrescos sin pisar estado (`refreshSafe()` o `ajax.reload(null, false)`)

## 📝 Notas

- Los endpoints `/dt/` ya existen para todos los módulos según `apps/tenant/core/api/views.py`
- `Module.init` es opcional; el patrón manual también es válido
- El hook global para ajuste de columnas en tabs ya está en `assets_core.html` (Fase 0)
- `stateSave` y `stateDuration` ya están configurados globalmente (Fase 3)
