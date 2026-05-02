# Migración Completa de DataTables a Tabulator
## Fecha: 2026-02-20
## Versión: v3.3

## 📋 Estado de Migración

### ✅ Completado
- Archivos eliminados:
  - `datatables-utils.js`
  - `datatables-defaults.js`
  - `datatables-es.js`
- Referencias eliminadas:
  - `assets_core.html` - Scripts de DataTables eliminados
  - `base.html` - CSS y JS de DataTables eliminados
  - `workspace.js` - Función `ajustarDataTablesInventario()` eliminada
  - `dom-utils.js` - Comentarios actualizados

### ⏳ Pendiente de Migración

#### apps/tenant
1. **inventario.page.js** - Usa `DataTablesUtils.initServerSide()`
2. **contabilidad/cuentas.page.js** - Usa `DataTablesUtils.initServerSide()`
3. **contabilidad/asientos.page.js** - Usa `jQuery.fn.DataTable()` directamente
4. **error-service.js** - Tiene referencias a DataTables (verificar si se usa)

#### apps/public
1. **console/tenants_manager.js** - Usa DataTables
2. **console/users_manager.js** - Usa DataTables
3. **Templates HTML** - Referencias a DataTables CSS/JS

## 🔧 Plan de Migración

### Paso 1: Migrar inventario.page.js
- Convertir columnas de DataTables a formato Tabulator
- Reemplazar `DataTablesUtils.initServerSide()` con `TabulatorFactory.create()`
- Cambiar endpoints POST a GET (si es necesario)
- Actualizar eventos de fila (de jQuery a Vanilla JS)

### Paso 2: Migrar contabilidad/cuentas.page.js
- Similar a inventario.page.js
- Usar `TabulatorFactory.create()` con server-side pagination

### Paso 3: Migrar contabilidad/asientos.page.js
- Convertir de client-side DataTables a Tabulator
- Usar `TabulatorFactory.create()` con client-side data

### Paso 4: Actualizar error-service.js
- Eliminar referencias a DataTables si no se usan

### Paso 5: Migrar apps/public
- Migrar tenants_manager.js y users_manager.js a Tabulator
- Actualizar templates HTML

## ⚠️ Notas Importantes

1. **Tabulator usa GET** para server-side, no POST como DataTables
2. **No usar jQuery** - Todo debe ser Vanilla JS
3. **Usar TabulatorFactory.create()** para consistencia
4. **Columnas Tabulator** usan `field` en lugar de `data`
5. **Render functions** tienen sintaxis diferente

## 📝 Formato de Columnas

### DataTables (Antes)
```javascript
{
  data: 'codigo',
  title: 'Código',
  render: (data) => `<span>${data}</span>`
}
```

### Tabulator (Después)
```javascript
{
  title: 'Código',
  field: 'codigo',
  formatter: (cell) => `<span>${cell.getValue()}</span>`
}
```
