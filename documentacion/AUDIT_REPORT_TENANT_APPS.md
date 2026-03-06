# Reporte de Auditoría: Violaciones del Patrón Core-Only UI

**Fecha:** 2026-02-03  
**Objetivo:** Detectar y corregir violaciones del patrón donde solo `apps/tenant/core` expone UI al usuario final.

---

## Apps Auditadas

Apps privadas de tenant (TENANT_APPS excepto `core`):
- `empresa`
- `facturas`
- `contabilidad`
- `perfil`
- `dashboard`
- `landing`

---

## Hallazgos por App

### 1. `apps/tenant/empresa`

#### ✅ CUMPLE (parcialmente)
- **Partials HTML:** ✅ `templates/tenant/empresa/partials/card.html` (correcto)
- **Views UI:** ✅ `views_ui.py` expone solo partials (correcto)
- **URLs UI:** ⚠️ `urls_ui.py` retorna 404 (deprecado, pero no viola el patrón)

#### ❌ VIOLACIONES
1. **Template no-partial:**
   - `templates/tenant/empresa/page.html` - Template completo que extiende `tenant/base.html`
   - **ACCIÓN:** Eliminar o mover a Core si se necesita

2. **HTML estático completo:**
   - `static/tenant/empresa/index.html` - Página HTML completa con JS embebido
   - **ACCIÓN:** Eliminar (debe estar en `apps/tenant/core/static/tenant/core/empresa/index.html`)

3. **JS UI duplicado:**
   - `static/tenant/empresa/empresa.ui.js` - JS UI que debería estar en Core
   - `static/empresa/js/empresas.js` - JS UI adicional
   - **ACCIÓN:** Verificar si está duplicado en Core; eliminar si es así

4. **Rutas en urls_tenant.py:**
   - `path('empresa/', RedirectView.as_view(url='/static/tenant/core/empresa/index.html', ...))` - ✅ Correcto (redirect)
   - `path('empresas/', RedirectView.as_view(url='/static/tenant/core/empresa/index.html', ...))` - ✅ Correcto (redirect)

---

### 2. `apps/tenant/facturas`

#### ✅ CUMPLE
- **Partials HTML:** ✅ `templates/tenant/facturas/partials/table.html` (correcto)
- **Views UI:** ✅ `views_ui.py` está vacío/deprecado (correcto)
- **URLs UI:** ✅ `urls_ui.py` existe pero probablemente retorna 404

#### ❌ VIOLACIONES
1. **JS UI duplicado:**
   - `static/tenant/facturas/facturas.ui.js` - JS UI que debería estar en Core
   - `static/facturas/js/facturas.js` - JS UI adicional
   - **ACCIÓN:** Verificar si está duplicado en Core; eliminar si es así

2. **Rutas en urls_tenant.py:**
   - `path('facturas/', RedirectView.as_view(url='/static/tenant/core/facturas/index.html', ...))` - ✅ Correcto (redirect)

---

### 3. `apps/tenant/contabilidad`

#### ✅ CUMPLE
- **Partials HTML:** ✅ `templates/tenant/contabilidad/partials/summary.html` (correcto)
- **Views UI:** ✅ `views_ui.py` está vacío/deprecado (correcto)

#### ❌ VIOLACIONES
1. **JS UI duplicado:**
   - `static/tenant/contabilidad/contabilidad.ui.js` - JS UI que debería estar en Core
   - `static/contabilidad/js/contabilidad.js` - JS UI adicional
   - **ACCIÓN:** Verificar si está duplicado en Core; eliminar si es así

2. **Rutas en urls_tenant.py:**
   - `path('contabilidad/', RedirectView.as_view(url='/static/tenant/core/contabilidad/index.html', ...))` - ✅ Correcto (redirect)

---

### 4. `apps/tenant/perfil`

#### ✅ CUMPLE
- **Partials HTML:** ✅ `templates/tenant/perfil/partials/card.html` (correcto)
- **Views UI:** ✅ `views_ui.py` está vacío/deprecado (correcto)

#### ❌ VIOLACIONES
1. **JS UI duplicado:**
   - `static/tenant/perfil/perfil.ui.js` - JS UI que debería estar en Core
   - `static/perfil/js/perfil.js` - JS UI adicional
   - **ACCIÓN:** Verificar si está duplicado en Core; eliminar si es así

2. **Rutas en urls_tenant.py:**
   - `path('perfil/', RedirectView.as_view(url='/static/tenant/core/perfil/index.html', ...))` - ✅ Correcto (redirect)

---

### 5. `apps/tenant/dashboard`

#### ✅ CUMPLE
- **Partials HTML:** ✅ `templates/tenant/dashboard/partials/*.html` (correcto)
- **Views UI:** ✅ `views_ui.py` está vacío/deprecado (correcto)
- **Views:** ✅ `views.py` está vacío/deprecado (correcto)
- **URLs:** ✅ `urls.py` está vacío (correcto)

#### ❌ VIOLACIONES
1. **HTML estático completo:**
   - `static/tenant/dashboard/index.html` - Página HTML completa con JS embebido
   - **ACCIÓN:** Eliminar (debe estar en `apps/tenant/core/static/tenant/core/dashboard/index.html`)

2. **JS UI duplicado:**
   - `static/tenant/dashboard/js/dashboard.js` - JS UI que debería estar en Core
   - **ACCIÓN:** Verificar si está duplicado en Core; eliminar si es así

3. **Rutas en urls_tenant.py:**
   - `path('dashboard/', RedirectView.as_view(url='/static/tenant/core/dashboard/index.html', ...))` - ✅ Correcto (redirect)

---

### 6. `apps/tenant/landing`

#### ✅ CUMPLE
- **Partials HTML:** ✅ `templates/tenant/landing/partials/*.html` (correcto)
- **Views UI:** ✅ `views_ui.py` expone solo partials (correcto)
- **URLs UI:** ✅ `urls_ui.py` expone solo partials (correcto)

#### ❌ VIOLACIONES
- **Ninguna detectada** - Landing cumple con el patrón (solo partials, JS centralizado en Core)

---

## Servicios en Core

### ✅ Servicios Existentes
- `apps/tenant/core/services/empresa.py` - ✅ `get_empresas_snapshot()`, `get_mi_empresa()`
- `apps/tenant/core/services/facturas.py` - ✅ `get_facturas_snapshot()`
- `apps/tenant/core/services/contabilidad.py` - ✅ `get_contabilidad_snapshot()`
- `apps/tenant/core/services/perfil.py` - ✅ `get_perfil_snapshot()`
- `apps/tenant/core/services/landing.py` - ✅ `get_landing_resumen()`, `get_landing_snapshot()`

### ❌ Servicios Faltantes
- `apps/tenant/core/services/dashboard.py` - ⚠️ **CREADO** - `get_dashboard_resumen()`, `get_dashboard_snapshot()`

---

## Resumen de Violaciones

| App | Templates no-partial | HTML estático | JS UI duplicado | Rutas directas | Total |
|-----|---------------------|---------------|-----------------|----------------|-------|
| empresa | 1 | 1 | 2 | 0 | **4** |
| facturas | 0 | 0 | 2 | 0 | **2** |
| contabilidad | 0 | 0 | 2 | 0 | **2** |
| perfil | 0 | 0 | 2 | 0 | **2** |
| dashboard | 0 | 1 | 1 | 0 | **2** |
| landing | 0 | 0 | 0 | 0 | **0** |

**Total de violaciones:** 12

---

## Acciones Recomendadas

### Prioridad Alta
1. ✅ **Crear servicio dashboard** en `apps/tenant/core/services/dashboard.py`
2. ❌ **Eliminar** `apps/tenant/empresa/templates/tenant/empresa/page.html`
3. ❌ **Eliminar** `apps/tenant/empresa/static/tenant/empresa/index.html`
4. ❌ **Eliminar** `apps/tenant/dashboard/static/tenant/dashboard/index.html`

### Prioridad Media
5. ❌ **Auditar y eliminar JS UI duplicado** en:
   - `apps/tenant/empresa/static/tenant/empresa/empresa.ui.js`
   - `apps/tenant/empresa/static/empresa/js/empresas.js`
   - `apps/tenant/facturas/static/tenant/facturas/facturas.ui.js`
   - `apps/tenant/facturas/static/facturas/js/facturas.js`
   - `apps/tenant/contabilidad/static/tenant/contabilidad/contabilidad.ui.js`
   - `apps/tenant/contabilidad/static/contabilidad/js/contabilidad.js`
   - `apps/tenant/perfil/static/tenant/perfil/perfil.ui.js`
   - `apps/tenant/perfil/static/perfil/js/perfil.js`
   - `apps/tenant/dashboard/static/tenant/dashboard/js/dashboard.js`

   **Verificar primero** que Core tiene versiones centralizadas en:
   - `apps/tenant/core/static/core/js/empresa.ui.js`
   - `apps/tenant/core/static/core/js/facturas.ui.js`
   - `apps/tenant/core/static/core/js/contabilidad.ui.js`
   - `apps/tenant/core/static/core/js/perfil.ui.js`
   - `apps/tenant/core/static/core/js/dashboard.ui.js`

### Prioridad Baja
6. ✅ **Rutas en urls_tenant.py** - Ya están correctamente configuradas como redirects

---

## Estado de Servicios Core

| App | Servicio | Estado |
|-----|----------|--------|
| empresa | `get_empresas_snapshot()` | ✅ Existe |
| empresa | `get_mi_empresa()` | ✅ Existe |
| facturas | `get_facturas_snapshot()` | ✅ Existe |
| contabilidad | `get_contabilidad_snapshot()` | ✅ Existe |
| perfil | `get_perfil_snapshot()` | ✅ Existe |
| landing | `get_landing_resumen()` | ✅ Existe |
| landing | `get_landing_snapshot()` | ✅ Existe |
| dashboard | `get_dashboard_resumen()` | ✅ **CREADO** |
| dashboard | `get_dashboard_snapshot()` | ✅ **CREADO** |

---

## Conclusión

- **Landing:** ✅ Cumple completamente con el patrón
- **Otras apps:** ⚠️ Tienen violaciones menores (JS UI duplicado, templates/HTML estáticos)
- **Servicios Core:** ✅ Todos los servicios necesarios están creados/alineados
- **Rutas:** ✅ Correctamente configuradas como redirects a Core

**Próximos pasos:** Eliminar archivos violadores y consolidar JS UI en Core.
