# Módulos Pendientes de Migración a Tabulator
## Fecha: 2026-02-20
## Versión: v3.3

## ⚠️ Estado Actual

**DataTables ha sido completamente eliminado** de:
- ✅ `assets_core.html` - Referencias eliminadas
- ✅ `base.html` - CSS y JS de DataTables eliminados
- ✅ `workspace.js` - Función `ajustarDataTablesInventario()` eliminada
- ✅ `datatables-utils.js` - Archivo eliminado
- ✅ `datatables-defaults.js` - Archivo eliminado
- ✅ `datatables-es.js` - Archivo eliminado

## 📋 Módulos que AÚN usan DataTables (Pendientes de Migración)

Los siguientes módulos **aún tienen referencias a DataTables** y necesitan ser migrados a Tabulator:

### 1. **Inventario** (`apps/tenant/core/static/core/js/inventario/inventario.page.js`)
- **Estado**: Usa `DataTablesUtils.initServerSide()`
- **Líneas**: 48-126
- **Acción requerida**: Migrar a `TabulatorFactory.create()` con server-side processing
- **Prioridad**: Alta

### 2. **Contabilidad - Cuentas** (`apps/tenant/core/static/core/js/contabilidad/cuentas.page.js`)
- **Estado**: Usa `DataTablesUtils.initServerSide()`
- **Líneas**: 495-519
- **Acción requerida**: Migrar a `TabulatorFactory.create()` con server-side processing
- **Prioridad**: Alta

### 3. **Contabilidad - Asientos** (`apps/tenant/core/static/core/js/contabilidad/asientos.page.js`)
- **Estado**: Usa `jQuery.fn.DataTable()` directamente
- **Líneas**: 747-827
- **Acción requerida**: Migrar a `TabulatorFactory.create()` con client-side processing
- **Prioridad**: Media

## 🔧 Notas Importantes

1. **Estos módulos NO funcionarán** hasta que sean migrados a Tabulator
2. **No se debe usar jQuery** - Tabulator usa Vanilla JS
3. **Usar TabulatorFactory.create()** para consistencia con el resto del proyecto
4. **Server-side processing** debe usar la API REST estándar del proyecto

## ✅ Módulos Ya Migrados a Tabulator

- ✅ Cotizaciones
- ✅ Proyectos
- ✅ Clientes
- ✅ Proveedores
- ✅ Empleados
- ✅ Gastos
- ✅ Empresa
- ✅ Inventario (Productos, Servicios, Activos) - Sub-módulos individuales

## 📝 Plan de Migración

1. **Inventario.page.js**: Migrar tabla principal a TabulatorFactory
2. **Contabilidad/Cuentas.page.js**: Migrar a TabulatorFactory con server-side
3. **Contabilidad/Asientos.page.js**: Migrar a TabulatorFactory con client-side

## ⚠️ Advertencia

**NO usar estos módulos hasta que sean migrados**. Intentar usarlos causará errores porque `DataTablesUtils` ya no existe.
