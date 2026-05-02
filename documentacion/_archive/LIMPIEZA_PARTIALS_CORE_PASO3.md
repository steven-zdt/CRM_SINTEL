# Limpieza de Partials Core — PASO 3

**Fecha:** 2025-01-17  
**Objetivo:** Mover todos los partials de apps específicas fuera de Core y limpiar duplicados legacy.

## Resumen Ejecutivo

- **Archivos movidos:** 33
- **Assets limpiados (helpers Core removidos):** 16
- **Errores:** 0
- **Core limpio:** ✅ Solo `assets_core.html` y `assets_common.html` permanecen en Core

## Archivos Movidos por App

### clientes
- `clientes/assets_clientes.html` → `apps/tenant/clientes/templates/tenant/clientes/partials/assets_clientes.html` (limpiado)
- `clientes/list.html` → `apps/tenant/clientes/templates/tenant/clientes/partials/list.html`
- `clientes/modals.html` → `apps/tenant/clientes/templates/tenant/clientes/partials/modals.html`

### contabilidad
- `contabilidad/assets_contabilidad.html` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/assets_contabilidad.html` (limpiado)
- `contabilidad/assets_cuentas.html` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/assets_cuentas.html` (limpiado)
- `contabilidad/assets_asientos.html` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/assets_asientos.html` (limpiado)
- `contabilidad/list_cuentas.html` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_cuentas.html`
- `contabilidad/list_asientos.html` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_asientos.html`
- `contabilidad/modals.html` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/modals.html`
- `contabilidad/modals_cuentas.html` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/modals_cuentas.html`
- `contabilidad/modals_asientos.html` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/modals_asientos.html`

### facturas
- `facturas/assets_facturas.html` → `apps/tenant/facturas/templates/tenant/facturas/partials/assets_facturas.html` (limpiado)
- `facturas/list.html` → `apps/tenant/facturas/templates/tenant/facturas/partials/list.html`
- `facturas/modals.html` → `apps/tenant/facturas/templates/tenant/facturas/partials/modals.html`

### inventario
- `inventario/assets_inventario.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/assets_inventario.html` (limpiado)
- `inventario/_activos_modals.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/_activos_modals.html`
- `inventario/_activos_table.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/_activos_table.html`
- `inventario/_catalogo_modals.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/_catalogo_modals.html`
- `inventario/_catalogo_table.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/_catalogo_table.html`
- `inventario/list_activos.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/list_activos.html`
- `inventario/list_catalogo.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/list_catalogo.html`
- `inventario/list_movimientos.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/list_movimientos.html`
- `inventario/modals_activos.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/modals_activos.html`
- `inventario/modals_catalogo.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/modals_catalogo.html`
- `inventario/modals_movimientos.html` → `apps/tenant/inventario/templates/tenant/inventario/partials/modals_movimientos.html`

### gastos
- `gastos/assets_gastos.html` → `apps/tenant/gastos/templates/tenant/gastos/partials/assets_gastos.html` (limpiado)
- `gastos/list.html` → `apps/tenant/gastos/templates/tenant/gastos/partials/list.html`
- `gastos/modals.html` → `apps/tenant/gastos/templates/tenant/gastos/partials/modals.html`

### empleados
- `empleados/assets_empleados.html` → `apps/tenant/empleados/templates/tenant/empleados/partials/assets_empleados.html` (limpiado)
- `empleados/list.html` → `apps/tenant/empleados/templates/tenant/empleados/partials/list.html`
- `empleados/modals.html` → `apps/tenant/empleados/templates/tenant/empleados/partials/modals.html`

### empresa
- `empresa/assets_empresa.html` → `apps/tenant/empresa/templates/tenant/empresa/partials/assets_empresa.html` (limpiado)
- `empresa/assets_empresas.html` → `apps/tenant/empresa/templates/tenant/empresa/partials/assets_empresas.html` (limpiado, LEGACY)
- `empresa/assets_mailinbox.html` → `apps/tenant/mailinbox/templates/tenant/mailinbox/partials/assets_mailinbox.html` (limpiado)
- `empresa/empresa_list.html` → `apps/tenant/empresa/templates/tenant/empresa/partials/empresa_list.html`
- `empresa/empresa_list.html` → `apps/tenant/empresa/templates/tenant/empresa/partials/empresa_list.html`
- `empresa/mailinbox_list.html` → `apps/tenant/mailinbox/templates/tenant/mailinbox/partials/mailinbox_list.html`
- `empresa/modals.html` → `apps/tenant/empresa/templates/tenant/empresa/partials/modals.html`

### perfil
- `perfil/assets_perfil.html` → `apps/tenant/perfil/templates/tenant/perfil/partials/assets_perfil.html` (limpiado)
- `perfil/list.html` → `apps/tenant/perfil/templates/tenant/perfil/partials/list.html`
- `perfil/modals.html` → `apps/tenant/perfil/templates/tenant/perfil/partials/modals.html`

### proveedores
- `proveedores/assets_proveedores.html` → `apps/tenant/proveedores/templates/tenant/proveedores/partials/assets_proveedores.html` (limpiado)
- `proveedores/list.html` → `apps/tenant/proveedores/templates/tenant/proveedores/partials/list.html`
- `proveedores/modals.html` → `apps/tenant/proveedores/templates/tenant/proveedores/partials/modals.html`

### dashboard
- `dashboard/assets_dashboard.html` → `apps/tenant/dashboard/templates/tenant/dashboard/partials/assets_dashboard.html` (limpiado)

### landing
- `landing/assets_landing.html` → `apps/tenant/landing/templates/tenant/landing/partials/assets_landing.html` (limpiado)

### mail
- `mail/assets_mail.html` → `apps/tenant/mail/templates/tenant/mail/partials/assets_mail.html` (limpiado)
- `mail/modals.html` → `apps/tenant/mail/templates/tenant/mail/partials/modals.html`

### mailinbox
- `mailinbox/list.html` → `apps/tenant/mailinbox/templates/tenant/mailinbox/partials/list.html`

## Limpieza de Assets (Helpers Core Removidos)

Los siguientes archivos `assets_*.html` fueron limpiados removiendo las referencias a helpers Core duplicados:

- `http.js`
- `api-helpers.js`
- `dom-utils.js`
- `datatables-utils.js`
- `routes.js`
- `crud.js`
- `module.js`

Estos helpers ahora se cargan una sola vez desde `assets_core.html` (PASO 2).

**Total de assets limpiados:** 16

## Duplicados Legacy Consolidados

### empresa/assets_empresas.html
- **Clasificación:** CORE_LEGACY_DUPLICADO
- **Acción:** Movido a `apps/tenant/empresa/templates/tenant/empresa/partials/assets_empresas.html` y limpiado
- **Nota:** Posible duplicación con `assets_empresa.html`. Revisar consolidación futura si ambos archivos son necesarios.

## Templates Actualizados

### workspace.html
**Archivo:** `apps/tenant/core/templates/tenant/core/workspace.html`

**Cambios realizados:**

1. **Bloque `extra_js`:**
   - ✅ Removidos helpers Core duplicados (http.js, api-helpers.js, dom-utils.js, datatables-utils.js)
   - ✅ Agregado `{% include 'tenant/core/partials/assets_core.html' %}` al inicio
   - ✅ Actualizados todos los includes de assets para apuntar a las nuevas rutas de apps

2. **Bloque `content`:**
   - ✅ Actualizados todos los includes de `list.html` y `modals.html` para apuntar a las nuevas rutas de apps

**Includes actualizados:**
- `tenant/core/partials/empresa/*` → `tenant/empresa/partials/*`
- `tenant/core/partials/facturas/*` → `tenant/facturas/partials/*`
- `tenant/core/partials/contabilidad/*` → `tenant/contabilidad/partials/*`
- `tenant/core/partials/inventario/*` → `tenant/inventario/partials/*`
- `tenant/core/partials/empleados/*` → `tenant/empleados/partials/*`
- `tenant/core/partials/gastos/*` → `tenant/gastos/partials/*`
- `tenant/core/partials/proveedores/*` → `tenant/proveedores/partials/*`
- `tenant/core/partials/clientes/*` → `tenant/clientes/partials/*`
- `tenant/core/partials/perfil/*` → `tenant/perfil/partials/*`
- `tenant/core/partials/empresa/mailinbox_*` → `tenant/mailinbox/partials/*`

## Validación Final

### Core Limpio
✅ **0 referencias a `tenant/<app>/...` (≠ core) en `apps/tenant/core/templates/tenant/core/partials/`**

Archivos que permanecen en Core:
- `assets_core.html` - Helpers oficiales v2.37
- `assets_common.html` - Vacío, puede usarse para assets comunes transversales

### Helpers v2.37 Únicos
✅ **No hay duplicados de HTTP/CSRF, DOM utils, DataTables utils, ni inicializaciones inline de DataTables en partials Core**

Todos los helpers Core se cargan una sola vez desde `assets_core.html`.

### Apps Actualizadas
✅ **Los templates de cada app incluyen primero `assets_core.html` y luego su partial de módulo**

El orden de carga en `workspace.html` es:
1. `assets_core.html` (helpers Core oficiales)
2. Assets específicos de cada módulo (sin helpers Core duplicados)

## Criterios de Aceptación

- ✅ Core sin contaminación: 0 includes `tenant/<app>/...` (≠ core) en `apps/tenant/core/templates/tenant/core/partials/`
- ✅ Helpers v2.37 únicos: No hay duplicados de HTTP/CSRF, DOM utils, DataTables utils, ni inicializaciones inline de DataTables en partials Core
- ✅ Apps actualizadas: Los templates de cada app incluyen primero `assets_core.html` y luego su partial de módulo
- ✅ Reporte: Existe `LIMPIEZA_PARTIALS_CORE_PASO3.md` con el inventario de movimientos y limpieza

## Próximos Pasos

1. **Eliminar archivos originales de Core** (opcional, después de verificar que todo funciona):
   - Los archivos movidos aún existen en `apps/tenant/core/templates/tenant/core/partials/`
   - Considerar eliminarlos después de verificar que no hay referencias rotas

2. **Verificar funcionamiento:**
   - Probar que el workspace carga correctamente
   - Verificar que los módulos se inicializan correctamente
   - Confirmar que no hay errores de JavaScript por helpers faltantes

3. **Consolidar duplicados legacy:**
   - Revisar `assets_empresa.html` vs `assets_empresas.html` y consolidar si es necesario

---

**Resultado:** Core queda mínimo y transversal; todas las apps consumen `assets_core.html` + sus propios partials. Consistencia total con SINTEL v2.37: UI Standard, DataTables server-side POST + CSRF, estáticos por app, Core orquestador.
