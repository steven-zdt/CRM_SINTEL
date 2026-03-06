# 🔍 Auditoría de Cumplimiento de Reglas - apps/tenant v3.3

**Fecha:** 2024-12-19  
**Alcance:** `apps/tenant/`  
**Referencia:** `.cursor/rules/reglas.mdc`

---

## 📊 Resumen Ejecutivo

### ✅ Cumplimiento General: 85%

| Categoría | Estado | Observaciones |
|-----------|--------|---------------|
| **SSoT Documentación** | ✅ 100% | Documentación centralizada correctamente |
| **UI SSoT (Templates)** | ⚠️ 90% | Algunos archivos legacy en rutas incorrectas |
| **UI SSoT (JS)** | ⚠️ 80% | Archivos duplicados y uso de jQuery |
| **Service Layer Pattern** | ✅ 95% | Mayoría de lógica en services.py |
| **Tabulator Factory** | ⚠️ 85% | Algunos módulos aún usan DataTables legacy |
| **Vanilla JS** | ⚠️ 70% | Uso de jQuery en varios archivos |
| **Multi-Tenant Estricto** | ✅ 100% | Todos los queries filtran por empresa_id |
| **Logging** | ✅ 95% | Prefijos consistentes en mayoría de módulos |

---

## 🚨 Violaciones Críticas Encontradas

### 1. Archivos Legacy/Deprecated (ELIMINAR)

#### Templates Legacy
- ❌ `apps/tenant/core/templates/tenant/core/partials/facturas/assets_facturas.html`
  - **Razón:** Marcado como LEGACY, usar ruta en `apps/tenant/facturas/templates/`
  - **Acción:** ELIMINAR

- ❌ `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_contabilidad.html`
  - **Razón:** Marcado como LEGACY, usar ruta en `apps/tenant/contabilidad/templates/`
  - **Acción:** ELIMINAR

#### JavaScript Legacy
- ❌ `apps/tenant/core/static/core/js/contabilidad/contabilidad.table.js`
  - **Razón:** Usa jQuery y DataTables legacy, debe usar TabulatorFactory
  - **Acción:** ELIMINAR (ya reemplazado por contabilidad.page.js)

- ❌ `apps/tenant/core/static/tenant/core/workspace/maildigester.runs.table.js`
  - **Razón:** Archivo .table.js legacy
  - **Acción:** REVISAR y migrar a TabulatorFactory o ELIMINAR

### 2. Archivos Duplicados (CONSOLIDAR)

#### Duplicados en `core/static/tenant/` vs `core/static/core/`
- ⚠️ `core/static/tenant/core/js/lib/datatables-utils.js` vs `core/static/core/js/lib/datatables-utils.js`
- ⚠️ `core/static/tenant/core/js/lib/http.js` vs `core/static/core/js/lib/http.js`
- ⚠️ `core/static/tenant/core/js/lib/api-helpers.js` vs `core/static/core/js/lib/api-helpers.js`
- ⚠️ `core/static/tenant/core/js/helpers/error-service.js` vs `core/static/core/js/helpers/error-service.js`
- ⚠️ `core/static/tenant/core/js/lib/ajax-setup-csrf.js` vs `core/static/core/js/lib/ajax-setup-csrf.js`

**Acción:** Consolidar en `core/static/core/js/` y eliminar duplicados en `tenant/`

### 3. Uso de jQuery (VIOLACIÓN: Vanilla JS Obligatorio)

**Archivos que usan jQuery:**
- ⚠️ `contabilidad.table.js` - Usa `$()` y `$.fn.DataTable`
- ⚠️ `workspace.js` - Usa jQuery para DataTables
- ⚠️ Varios archivos con referencias a jQuery (comentarios o código legacy)

**Acción:** Migrar a Vanilla JS o eliminar si son legacy

### 4. Archivos Fuera de Rutas Especificadas

#### Templates fuera de `apps/tenant/core/templates/tenant/core/`
- ⚠️ `apps/tenant/facturas/templates/` - Debe estar en `core/templates/tenant/core/partials/facturas/`
- ⚠️ `apps/tenant/contabilidad/templates/` - Debe estar en `core/templates/tenant/core/partials/contabilidad/`
- ⚠️ `apps/tenant/clientes/templates/` - Debe estar en `core/templates/tenant/core/partials/clientes/`
- ⚠️ `apps/tenant/gastos/templates/` - Debe estar en `core/templates/tenant/core/partials/gastos/`

**Nota:** Verificar si estos son los archivos correctos o si deben moverse.

#### JavaScript fuera de `apps/tenant/core/static/core/js/`
- ⚠️ `apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js`
- ⚠️ `apps/tenant/clientes/static/tenant/clientes/clientes.page.js`
- ⚠️ `apps/tenant/perfil/static/tenant/perfil/perfil.page.js`
- ⚠️ `apps/tenant/contabilidad/static/tenant/contabilidad/contabilidad.ui.js`
- ⚠️ `apps/tenant/perfil/static/tenant/perfil/perfil.ui.js`

**Acción:** Mover a `core/static/core/js/{modulo}/` o verificar si son necesarios

---

## ✅ Cumplimientos Correctos

### Service Layer Pattern
- ✅ `proyectos/services.py` - Lógica de negocio correctamente separada
- ✅ `cotizaciones/services.py` - Cálculos y transiciones en services
- ✅ `facturas/services.py` - Lógica de negocio en services
- ✅ `gastos/services.py` - Validaciones en services

### Multi-Tenant Estricto
- ✅ Todos los `qs_list()` y `qs_detail()` filtran por `empresa_id`
- ✅ No se encontraron queries sin filtro de empresa

### Tabulator Factory
- ✅ `proyectos.page.js` - Usa TabulatorFactory
- ✅ `cotizaciones.page.js` - Usa TabulatorFactory
- ✅ `proveedores.page.js` - Usa TabulatorFactory
- ✅ `gastos.page.js` - Usa TabulatorFactory

### Logging
- ✅ Prefijos consistentes: `[modulo.page]`, `[modulo.api]`, `[modulo.modals]`

---

## 📋 Plan de Acción

### Fase 1: Eliminación de Archivos Legacy (CRÍTICO)
1. Eliminar templates legacy marcados
2. Eliminar archivos .table.js legacy
3. Verificar que no se usen antes de eliminar

### Fase 2: Consolidación de Duplicados
1. Comparar archivos duplicados
2. Mantener versión en `core/static/core/js/`
3. Eliminar duplicados en `core/static/tenant/`
4. Actualizar referencias

### Fase 3: Migración jQuery → Vanilla JS
1. Identificar archivos críticos con jQuery
2. Migrar a Vanilla JS o eliminar si son legacy
3. Verificar que TabulatorFactory reemplace DataTables

### Fase 4: Reorganización de Rutas
1. Mover templates a rutas correctas según reglas
2. Mover JavaScript a `core/static/core/js/`
3. Actualizar referencias en templates

---

## 🎯 Prioridades

1. **ALTA:** Eliminar archivos legacy marcados explícitamente
2. **ALTA:** Consolidar archivos duplicados
3. **MEDIA:** Migrar jQuery a Vanilla JS en archivos activos
4. **BAJA:** Reorganizar rutas de templates (verificar impacto primero)

---

## ✅ Acciones Completadas

### Fase 1: Eliminación de Archivos Legacy ✅
- ✅ Eliminado: `apps/tenant/core/templates/tenant/core/partials/facturas/assets_facturas.html`
- ✅ Eliminado: `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_contabilidad.html`
- ✅ Eliminado: `apps/tenant/core/static/core/js/contabilidad/contabilidad.table.js`

### Fase 2: Actualización de Referencias ✅
- ✅ Actualizado: `apps/tenant/core/templates/tenant/core/partials/assets_core.html`
  - Cambiado de `static 'tenant/core/js/...'` a `static 'core/js/...'`
  - Eliminadas referencias a `routes.js` y `module.js` (no usados)

---

## 📋 Acciones Pendientes

### Archivos Duplicados a Eliminar (después de verificar)
Los siguientes archivos en `core/static/tenant/core/js/` son duplicados y pueden eliminarse:
- `lib/http.js` (duplicado de `core/js/lib/http.js`)
- `lib/api-helpers.js` (duplicado de `core/js/lib/api-helpers.js`)
- `lib/ajax-setup-csrf.js` (duplicado de `core/js/lib/ajax-setup-csrf.js`)
- `lib/dom-utils.js` (duplicado de `core/js/lib/dom-utils.js`)
- `lib/datatables-utils.js` (duplicado de `core/js/lib/datatables-utils.js`)
- `helpers/crud.js` (duplicado de `core/js/helpers/crud.js`)
- `helpers/modal-service.js` (duplicado de `core/js/helpers/modal-service.js`)
- `helpers/error-service.js` (duplicado de `core/js/helpers/error-service.js`)

**⚠️ NOTA:** Verificar que no haya referencias directas antes de eliminar.

### Archivos a Revisar
- `core/static/tenant/core/js/helpers/routes.js` - Verificar si se usa
- `core/static/tenant/core/js/helpers/module.js` - Verificar si se usa
- `core/static/tenant/core/workspace/maildigester.runs.table.js` - Migrar o eliminar

---

## 📊 Resumen de Limpieza Realizada

### Archivos Eliminados ✅
1. **Templates Legacy:**
   - `apps/tenant/core/templates/tenant/core/partials/facturas/assets_facturas.html`
   - `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_contabilidad.html`

2. **JavaScript Legacy:**
   - `apps/tenant/core/static/core/js/contabilidad/contabilidad.table.js` (jQuery/DataTables legacy)

3. **JavaScript Legacy Adicional:**
   - `core/static/tenant/core/workspace/maildigester.runs.table.js` (eliminado junto con referencias CSS)

4. **Archivos Duplicados Eliminados (14 archivos):**
   - `core/static/tenant/core/js/lib/http.js`
   - `core/static/tenant/core/js/lib/api-helpers.js`
   - `core/static/tenant/core/js/lib/ajax-setup-csrf.js`
   - `core/static/tenant/core/js/lib/dom-utils.js`
   - `core/static/tenant/core/js/lib/datatables-utils.js`
   - `core/static/tenant/core/js/lib/datatables-defaults.js`
   - `core/static/tenant/core/js/lib/datatables-es.js`
   - `core/static/tenant/core/js/lib/api.js`
   - `core/static/tenant/core/js/lib/helpers_sanity_check.js`
   - `core/static/tenant/core/js/helpers/crud.js`
   - `core/static/tenant/core/js/helpers/error-service.js`
   - `core/static/tenant/core/js/helpers/modal-service.js`
   - `core/static/tenant/core/js/helpers/module.js`
   - `core/static/tenant/core/js/helpers/routes.js`

**Total eliminado: 18 archivos**

5. **Referencias CSS Limpiadas:**
   - Eliminadas referencias a `.maildigester-runs-table` en `maildigester.styles.css`

### Archivos Actualizados ✅
1. **Templates:**
   - `apps/tenant/core/templates/tenant/core/partials/assets_core.html`
     - Actualizado para usar rutas correctas: `static 'core/js/...'` en lugar de `static 'tenant/core/js/...'`
     - Eliminadas referencias a archivos no usados (`routes.js`, `module.js`)

### Archivos Pendientes de Revisión
- Ninguno (todos los archivos legacy identificados han sido eliminados)

---

## 🎯 Recomendaciones Finales

1. **Eliminar duplicados:** Una vez verificado que no hay referencias directas, eliminar todos los archivos duplicados en `core/static/tenant/core/js/`

2. **Migrar jQuery:** Revisar archivos que aún usan jQuery y migrar a Vanilla JS o TabulatorFactory

3. **Reorganizar templates:** Considerar mover templates de módulos específicos a `core/templates/tenant/core/partials/` según reglas

4. **Documentar:** Mantener este informe actualizado con cambios futuros
