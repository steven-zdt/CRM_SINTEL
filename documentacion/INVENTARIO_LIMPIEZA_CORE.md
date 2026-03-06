# Inventario y Clasificación - Limpieza apps/tenant/core

## A) Inventario Completo

### Templates (apps/tenant/core/templates/tenant/core/)

| STATUS | PATH | REASON |
|--------|------|--------|
| KEEP | `workspace.html` | Shell principal del workspace (a actualizar a mínimo) |
| KEEP | `partials/empresa/assets_empresas.html` | Asset modular de empresa |
| KEEP | `partials/facturas/assets_facturas.html` | Asset modular de facturas |
| KEEP | `partials/facturas/list.html` | Partial modular de facturas |
| KEEP | `partials/facturas/modals.html` | Partial modular de facturas |
| KEEP | `partials/inventario/assets_inventario.html` | Asset modular de inventario |
| KEEP | `partials/gastos/assets_gastos.html` | Asset modular de gastos |
| KEEP | `partials/landing/assets_landing.html` | Asset modular de landing |
| KEEP | `partials/perfil/assets_perfil.html` | Asset modular de perfil |
| KEEP | `partials/proveedores/assets_proveedores.html` | Asset modular de proveedores |
| KEEP | `partials/empleados/assets_empleados.html` | Asset modular de empleados |
| KEEP | `partials/dashboard/assets_dashboard.html` | Asset modular de dashboard |
| KEEP | `partials/contabilidad/assets_contabilidad.html` | Asset modular de contabilidad |
| KEEP | `partials/mail/assets_mail.html` | Asset modular de MailDigester |
| DELETE_CANDIDATE | `partials/assets_common.html` | Vacío, solo comentario, no usado |
| DELETE_CANDIDATE | `partials/assets_facturas_refresh.html` | Referencia archivo inexistente (facturas.refresh.js) |
| DELETE_CANDIDATE | `partials/assets_facturas.html` | Duplicado (ya existe en partials/facturas/) |
| DELETE_CANDIDATE | `partials/assets_perfil.html` | Duplicado (ya existe en partials/perfil/) |
| DELETE_CANDIDATE | `partials/assets_maildigester.html` | Duplicado (ya existe en partials/mail/) |
| REVIEW | `partials/inventario/_catalogo_table.html` | Usado en workspace.html, migrar a módulo modular |
| REVIEW | `partials/inventario/_catalogo_modals.html` | Usado en workspace.html, migrar a módulo modular |
| REVIEW | `partials/inventario/_activos_table.html` | Usado en workspace.html, migrar a módulo modular |
| REVIEW | `partials/inventario/_activos_modals.html` | Usado en workspace.html, migrar a módulo modular |

### Static JS (apps/tenant/core/static/core/js/)

| STATUS | PATH | REASON |
|--------|------|--------|
| KEEP | `router.js` | Router central por hash |
| KEEP | `lib/http.js` | Helper HTTP compartido (IIFE, usado por todos) |
| KEEP | `empresa/empresa.api.js` | Módulo modular empresa |
| KEEP | `empresa/empresa.ui.js` | Módulo modular empresa |
| KEEP | `empresa/empresa.page.js` | Módulo modular empresa |
| KEEP | `facturas/facturas.api.js` | Módulo modular facturas |
| KEEP | `facturas/facturas.components.js` | Módulo modular facturas |
| KEEP | `facturas/facturas.table.js` | Módulo modular facturas |
| KEEP | `facturas/facturas.modals.js` | Módulo modular facturas |
| KEEP | `facturas/facturas.page.js` | Módulo modular facturas |
| KEEP | `inventario/inventario.api.js` | Módulo modular inventario |
| KEEP | `inventario/inventario.ui.js` | Módulo modular inventario |
| KEEP | `inventario/inventario.page.js` | Módulo modular inventario |
| KEEP | `gastos/gastos.api.js` | Módulo modular gastos |
| KEEP | `gastos/gastos.ui.js` | Módulo modular gastos |
| KEEP | `gastos/gastos.page.js` | Módulo modular gastos |
| KEEP | `landing/landing.api.js` | Módulo modular landing |
| KEEP | `landing/landing.ui.js` | Módulo modular landing |
| KEEP | `landing/landing.page.js` | Módulo modular landing |
| KEEP | `perfil/perfil.api.js` | Módulo modular perfil |
| KEEP | `perfil/perfil.ui.js` | Módulo modular perfil |
| KEEP | `perfil/perfil.page.js` | Módulo modular perfil |
| KEEP | `proveedores/proveedores.api.js` | Módulo modular proveedores |
| KEEP | `proveedores/proveedores.ui.js` | Módulo modular proveedores |
| KEEP | `proveedores/proveedores.page.js` | Módulo modular proveedores |
| KEEP | `empleados/empleados.api.js` | Módulo modular empleados |
| KEEP | `empleados/empleados.ui.js` | Módulo modular empleados |
| KEEP | `empleados/empleados.page.js` | Módulo modular empleados |
| KEEP | `dashboard/dashboard.api.js` | Módulo modular dashboard |
| KEEP | `dashboard/dashboard.ui.js` | Módulo modular dashboard |
| KEEP | `dashboard/dashboard.page.js` | Módulo modular dashboard |
| KEEP | `contabilidad/contabilidad.api.js` | Módulo modular contabilidad |
| KEEP | `contabilidad/contabilidad.ui.js` | Módulo modular contabilidad |
| KEEP | `contabilidad/contabilidad.page.js` | Módulo modular contabilidad |
| KEEP | `mail/mail.api.js` | Módulo modular MailDigester |
| KEEP | `mail/mail.ui.js` | Módulo modular MailDigester |
| KEEP | `mail/mail.page.js` | Módulo modular MailDigester |
| DELETE_CANDIDATE | `facturas.ui.js` | Legacy, duplicado (ya existe modular en facturas/) |
| DELETE_CANDIDATE | `empresa.ui.js` | Legacy, duplicado (ya existe modular en empresa/) |
| DELETE_CANDIDATE | `perfil.ui.js` | Legacy, duplicado (ya existe modular en perfil/) |
| DELETE_CANDIDATE | `contabilidad.ui.js` | Legacy, duplicado (ya existe modular en contabilidad/) |
| DELETE_CANDIDATE | `dashboard.ui.js` | Legacy, duplicado (ya existe modular en dashboard/) |
| DELETE_CANDIDATE | `landing.ui.js` | Legacy, duplicado (ya existe modular en landing/) |
| DELETE_CANDIDATE | `landing.reset.ui.js` | Legacy, usa _csrf.js obsoleto |
| DELETE_CANDIDATE | `http.js` | Duplicado (ES6 modules), usar lib/http.js (IIFE) |
| DELETE_CANDIDATE | `_csrf.js` | Obsoleto, funcionalidad migrada a lib/http.js |

## B) Verificación de Referencias

### Archivos Legacy Referenciados

1. **facturas.ui.js**:
   - Referenciado en: `apps/tenant/core/static/tenant/core/facturas/index.html` (shell estático legacy)
   - Acción: Verificar si el shell estático se usa; si no, eliminar ambos

2. **empresa.ui.js, perfil.ui.js, contabilidad.ui.js, dashboard.ui.js**:
   - Referenciados en: `apps/tenant/core/static/tenant/core/*/index.html` (shells estáticos legacy)
   - Acción: Verificar si se usan; si no, eliminar

3. **landing.reset.ui.js**:
   - Usa `_csrf.js` obsoleto
   - Acción: Eliminar ambos si no se usan

4. **http.js** (raíz):
   - ES6 modules, usado por facturas.ui.js legacy
   - Acción: Eliminar si facturas.ui.js se elimina

5. **assets_facturas_refresh.html**:
   - Referencia `facturas.refresh.js` inexistente
   - Incluido en workspace.html
   - Acción: Eliminar

6. **assets_common.html**:
   - Vacío, no usado
   - Acción: Eliminar

## C) Archivos a Revisar (REVIEW)

Los partials de inventario con guiones bajos están siendo usados en workspace.html:
- `_catalogo_table.html`
- `_catalogo_modals.html`
- `_activos_table.html`
- `_activos_modals.html`

**Acción**: Migrar a módulo modular de inventario o mantener si son parte de la UI legacy que se migrará después.

## D) Resumen de Eliminaciones Propuestas

### Templates a Eliminar:
1. `partials/assets_common.html` (vacío)
2. `partials/assets_facturas_refresh.html` (archivo inexistente)
3. `partials/assets_facturas.html` (duplicado)
4. `partials/assets_perfil.html` (duplicado)
5. `partials/assets_maildigester.html` (duplicado)

### JS a Eliminar:
1. `facturas.ui.js` (legacy, duplicado)
2. `empresa.ui.js` (legacy, duplicado)
3. `perfil.ui.js` (legacy, duplicado)
4. `contabilidad.ui.js` (legacy, duplicado)
5. `dashboard.ui.js` (legacy, duplicado)
6. `landing.ui.js` (legacy, duplicado)
7. `landing.reset.ui.js` (legacy, obsoleto)
8. `http.js` (duplicado, usar lib/http.js)
9. `_csrf.js` (obsoleto)

### Shells Estáticos a Verificar:
- `apps/tenant/core/static/tenant/core/facturas/index.html`
- `apps/tenant/core/static/tenant/core/empresa/index.html`
- `apps/tenant/core/static/tenant/core/perfil/index.html`
- `apps/tenant/core/static/tenant/core/contabilidad/index.html`
- `apps/tenant/core/static/tenant/core/dashboard/index.html`

Si no se usan, eliminar también.
