# Auditoría Partials Core — PASO 1 (identificación)

**Ruta auditada:** `apps/tenant/core/templates/tenant/core/partials/`  
**Fecha:** 2025-01-17

## Resumen

- **Total partials:** 50
- **CORE_VALIDO:** 1
- **CORE_INVALIDO_APP_SPECIFIC:** 48
- **CORE_LEGACY_DUPLICADO:** 1

## Detalle por archivo

### 1) assets_common.html

- **Clasificación:** CORE_VALIDO
- **Motivo:** Archivo vacío con solo comentarios, destinado a assets comunes transversales. No contiene referencias a apps específicas.
- **Hallazgos:**
  - Paths core: Ninguno (archivo vacío)
  - Paths de app: Ninguno
  - Legacy: Ninguno
- **Recomendación:** Mantener en Core. Puede usarse para incluir helpers Core comunes (http.js, api-helpers.js, dom-utils.js, datatables-utils.js, helpers/routes.js, helpers/crud.js, helpers/module.js) que todas las apps necesitan.

---

### 2) clientes/assets_clientes.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (clientes)
- **Motivo:** Incluye scripts específicos del módulo clientes: `core/js/clientes/clientes.table.js`, `core/js/clientes/clientes.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/clientes/clientes.table.js`, `core/js/clientes/clientes.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/clientes/templates/tenant/clientes/partials/assets_clientes.html` (si existe app clientes) o mantener estructura pero mover solo los scripts de app fuera de Core.

---

### 3) clientes/list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (clientes)
- **Motivo:** Template HTML específico del módulo clientes con IDs y estructura específica (`#ui-clientes-list`, `#table-clientes`, `#btn-clientes-crear`)
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/clientes/templates/tenant/clientes/partials/list.html`

---

### 4) clientes/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (clientes)
- **Motivo:** Modales específicos del módulo clientes
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/clientes/templates/tenant/clientes/partials/modals.html`

---

### 5) contabilidad/assets_contabilidad.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (contabilidad)
- **Motivo:** Incluye scripts específicos del módulo contabilidad: `core/js/contabilidad/contabilidad.api.js`, `core/js/contabilidad/contabilidad.ui.js`, `core/js/contabilidad/contabilidad.table.js`, `core/js/contabilidad/contabilidad.modals.js`, `core/js/contabilidad/contabilidad.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/contabilidad/contabilidad.api.js`, `core/js/contabilidad/contabilidad.ui.js`, `core/js/contabilidad/contabilidad.table.js`, `core/js/contabilidad/contabilidad.modals.js`, `core/js/contabilidad/contabilidad.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/assets_contabilidad.html`

---

### 6) contabilidad/assets_cuentas.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (contabilidad)
- **Motivo:** Incluye script específico de cuentas contables: `core/js/contabilidad/cuentas.page.js`
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: `core/js/contabilidad/cuentas.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/assets_cuentas.html`

---

### 7) contabilidad/assets_asientos.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (contabilidad)
- **Motivo:** Incluye script específico de asientos contables: `core/js/contabilidad/asientos.page.js`
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: `core/js/contabilidad/asientos.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/assets_asientos.html`

---

### 8) contabilidad/list_cuentas.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (contabilidad)
- **Motivo:** Template HTML específico de cuentas contables
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_cuentas.html`

---

### 9) contabilidad/list_asientos.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (contabilidad)
- **Motivo:** Template HTML específico de asientos contables
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_asientos.html`

---

### 10) contabilidad/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (contabilidad)
- **Motivo:** Modales específicos del módulo contabilidad
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/modals.html`

---

### 11) contabilidad/modals_cuentas.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (contabilidad)
- **Motivo:** Modales específicos de cuentas contables
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/modals_cuentas.html`

---

### 12) contabilidad/modals_asientos.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (contabilidad)
- **Motivo:** Modales específicos de asientos contables
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/modals_asientos.html`

---

### 13) dashboard/assets_dashboard.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (dashboard)
- **Motivo:** Incluye scripts específicos del módulo dashboard: `core/js/dashboard/dashboard.api.js`, `core/js/dashboard/dashboard.ui.js`, `core/js/dashboard/dashboard.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`
  - Paths de app: `core/js/dashboard/dashboard.api.js`, `core/js/dashboard/dashboard.ui.js`, `core/js/dashboard/dashboard.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/dashboard/templates/tenant/dashboard/partials/assets_dashboard.html` (si existe app dashboard) o mantener estructura pero mover solo los scripts de app fuera de Core.

---

### 14) empleados/assets_empleados.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (empleados)
- **Motivo:** Incluye scripts específicos del módulo empleados: `core/js/empleados/empleados.api.js`, `core/js/empleados/empleados.dt.js`, `core/js/empleados/empleados.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/empleados/empleados.api.js`, `core/js/empleados/empleados.dt.js`, `core/js/empleados/empleados.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/empleados/templates/tenant/empleados/partials/assets_empleados.html` (si existe app empleados) o mantener estructura pero mover solo los scripts de app fuera de Core.

---

### 15) empleados/list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (empleados)
- **Motivo:** Template HTML específico del módulo empleados
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/empleados/templates/tenant/empleados/partials/list.html`

---

### 16) empleados/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (empleados)
- **Motivo:** Modales específicos del módulo empleados
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/empleados/templates/tenant/empleados/partials/modals.html`

---

### 17) empresa/assets_empresa.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (empresa)
- **Motivo:** Incluye scripts específicos del módulo empresa: `core/js/empresa/empresa.api.js`, `core/js/empresa/empresa.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/empresa/empresa.api.js`, `core/js/empresa/empresa.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/empresa/templates/tenant/empresa/partials/assets_empresa.html`

---

### 18) empresa/assets_empresas.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (empresa)
- **Motivo:** Incluye scripts específicos del módulo empresa: `core/js/empresa/empresa.api.js`, `core/js/empresa/empresa.ui.js`, `core/js/empresa/empresa.modals.js`, `core/js/empresa/empresa.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`
  - Paths de app: `core/js/empresa/empresa.api.js`, `core/js/empresa/empresa.ui.js`, `core/js/empresa/empresa.modals.js`, `core/js/empresa/empresa.page.js`
  - Legacy: Posible duplicación con `assets_empresa.html`
- **Recomendación:** Mover a `apps/tenant/empresa/templates/tenant/empresa/partials/assets_empresas.html` y consolidar con `assets_empresa.html` si son duplicados.

---

### 19) empresa/assets_mailinbox.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (mailinbox)
- **Motivo:** Incluye script específico de mailinbox: `core/js/mailinbox/mailinbox.page.js`
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: `core/js/mailinbox/mailinbox.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/mailinbox/templates/tenant/mailinbox/partials/assets_mailinbox.html` (si existe app mailinbox) o a la app correspondiente.

---

### 20) empresa/empresa_list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (empresa)
- **Motivo:** Template HTML específico del módulo empresa
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/empresa/templates/tenant/empresa/partials/empresa_list.html`

---

### 21) empresa/list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (empresa)
- **Motivo:** Template HTML específico del módulo empresa
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/empresa/templates/tenant/empresa/partials/list.html`

---

### 22) empresa/mailinbox_list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (mailinbox)
- **Motivo:** Template HTML específico del módulo mailinbox
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/mailinbox/templates/tenant/mailinbox/partials/list.html` (si existe app mailinbox) o a la app correspondiente.

---

### 23) empresa/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (empresa)
- **Motivo:** Modales específicos del módulo empresa
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/empresa/templates/tenant/empresa/partials/modals.html`

---

### 24) facturas/assets_facturas.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (facturas)
- **Motivo:** Incluye scripts específicos del módulo facturas: `core/js/facturas/facturas.api.js`, `core/js/facturas/facturas.components.js`, `core/js/facturas/facturas.table.js`, `core/js/facturas/facturas.modals.js`, `core/js/facturas/facturas.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/facturas/facturas.api.js`, `core/js/facturas/facturas.components.js`, `core/js/facturas/facturas.table.js`, `core/js/facturas/facturas.modals.js`, `core/js/facturas/facturas.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/facturas/templates/tenant/facturas/partials/assets_facturas.html`

---

### 25) facturas/list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (facturas)
- **Motivo:** Template HTML específico del módulo facturas
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/facturas/templates/tenant/facturas/partials/list.html`

---

### 26) facturas/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (facturas)
- **Motivo:** Modales específicos del módulo facturas
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/facturas/templates/tenant/facturas/partials/modals.html`

---

### 27) gastos/assets_gastos.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (gastos)
- **Motivo:** Incluye scripts específicos del módulo gastos: `core/js/gastos/gastos.api.js`, `core/js/gastos/gastos.dt.js`, `core/js/gastos/gastos.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/gastos/gastos.api.js`, `core/js/gastos/gastos.dt.js`, `core/js/gastos/gastos.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/gastos/templates/tenant/gastos/partials/assets_gastos.html` (si existe app gastos) o mantener estructura pero mover solo los scripts de app fuera de Core.

---

### 28) gastos/list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (gastos)
- **Motivo:** Template HTML específico del módulo gastos
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/gastos/templates/tenant/gastos/partials/list.html`

---

### 29) gastos/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (gastos)
- **Motivo:** Modales específicos del módulo gastos
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/gastos/templates/tenant/gastos/partials/modals.html`

---

### 30) inventario/assets_inventario.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Incluye scripts específicos del módulo inventario: `core/js/inventario/inventario.api.js`, `core/js/inventario/inventario.table.js`, `core/js/inventario/catalogo.page.js`, `core/js/inventario/activos.page.js`, `core/js/inventario/movimientos.page.js`, `core/js/inventario/inventario.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/inventario/inventario.api.js`, `core/js/inventario/inventario.table.js`, `core/js/inventario/catalogo.page.js`, `core/js/inventario/activos.page.js`, `core/js/inventario/movimientos.page.js`, `core/js/inventario/inventario.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/assets_inventario.html`

---

### 31) inventario/_activos_modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Modales específicos de activos fijos
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/_activos_modals.html`

---

### 32) inventario/_activos_table.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Template HTML específico de activos fijos
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/_activos_table.html`

---

### 33) inventario/_catalogo_modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Modales específicos de catálogo
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/_catalogo_modals.html`

---

### 34) inventario/_catalogo_table.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Template HTML específico de catálogo
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/_catalogo_table.html`

---

### 35) inventario/list_activos.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Template HTML específico de activos fijos
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/list_activos.html`

---

### 36) inventario/list_catalogo.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Template HTML específico de catálogo
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/list_catalogo.html`

---

### 37) inventario/list_movimientos.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Template HTML específico de movimientos de inventario
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/list_movimientos.html`

---

### 38) inventario/modals_activos.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Modales específicos de activos fijos
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/modals_activos.html`

---

### 39) inventario/modals_catalogo.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Modales específicos de catálogo
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/modals_catalogo.html`

---

### 40) inventario/modals_movimientos.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (inventario)
- **Motivo:** Modales específicos de movimientos de inventario
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/inventario/templates/tenant/inventario/partials/modals_movimientos.html`

---

### 41) landing/assets_landing.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (landing)
- **Motivo:** Incluye scripts específicos del módulo landing: `core/js/landing/landing.api.js`, `core/js/landing/landing.ui.js`, `core/js/landing/landing.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`
  - Paths de app: `core/js/landing/landing.api.js`, `core/js/landing/landing.ui.js`, `core/js/landing/landing.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/landing/templates/tenant/landing/partials/assets_landing.html` (si existe app landing) o mantener estructura pero mover solo los scripts de app fuera de Core.

---

### 42) mail/assets_mail.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (mail)
- **Motivo:** Incluye scripts específicos del módulo mail: `core/js/mail/mail.api.js`, `core/js/mail/mail.ui.js`, `core/js/mail/mail.modals.js`, `core/js/mail/mail.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`
  - Paths de app: `core/js/mail/mail.api.js`, `core/js/mail/mail.ui.js`, `core/js/mail/mail.modals.js`, `core/js/mail/mail.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/mail/templates/tenant/mail/partials/assets_mail.html` (si existe app mail) o mantener estructura pero mover solo los scripts de app fuera de Core.

---

### 43) mail/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (mail)
- **Motivo:** Modales específicos del módulo mail
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/mail/templates/tenant/mail/partials/modals.html`

---

### 44) mailinbox/list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (mailinbox)
- **Motivo:** Template HTML específico del módulo mailinbox
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/mailinbox/templates/tenant/mailinbox/partials/list.html` (si existe app mailinbox) o a la app correspondiente.

---

### 45) perfil/assets_perfil.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (perfil)
- **Motivo:** Incluye scripts específicos del módulo perfil: `core/js/perfil/perfil.api.js`, `core/js/perfil/perfil.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/perfil/perfil.api.js`, `core/js/perfil/perfil.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/perfil/templates/tenant/perfil/partials/assets_perfil.html` (si existe app perfil) o mantener estructura pero mover solo los scripts de app fuera de Core.

---

### 46) perfil/list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (perfil)
- **Motivo:** Template HTML específico del módulo perfil
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/perfil/templates/tenant/perfil/partials/list.html`

---

### 47) perfil/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (perfil)
- **Motivo:** Modales específicos del módulo perfil
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/perfil/templates/tenant/perfil/partials/modals.html`

---

### 48) proveedores/assets_proveedores.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (proveedores)
- **Motivo:** Incluye scripts específicos del módulo proveedores: `core/js/proveedores/proveedores.api.js`, `core/js/proveedores/proveedores.dt.js`, `core/js/proveedores/proveedores.page.js`
- **Hallazgos:**
  - Paths core: `core/js/lib/http.js`, `core/js/lib/api-helpers.js`, `core/js/lib/dom-utils.js`, `core/js/lib/datatables-utils.js`, `core/js/helpers/routes.js`, `core/js/helpers/crud.js`, `core/js/helpers/module.js`
  - Paths de app: `core/js/proveedores/proveedores.api.js`, `core/js/proveedores/proveedores.dt.js`, `core/js/proveedores/proveedores.page.js`
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/proveedores/templates/tenant/proveedores/partials/assets_proveedores.html` (si existe app proveedores) o mantener estructura pero mover solo los scripts de app fuera de Core.

---

### 49) proveedores/list.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (proveedores)
- **Motivo:** Template HTML específico del módulo proveedores
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/proveedores/templates/tenant/proveedores/partials/list.html`

---

### 50) proveedores/modals.html

- **Clasificación:** CORE_INVALIDO_APP_SPECIFIC (proveedores)
- **Motivo:** Modales específicos del módulo proveedores
- **Hallazgos:**
  - Paths core: Ninguno
  - Paths de app: Ninguno (solo HTML)
  - Legacy: Ninguno
- **Recomendación:** Mover a `apps/tenant/proveedores/templates/tenant/proveedores/partials/modals.html`

---

## Resumen de Hallazgos

### Paths Core Válidos Encontrados (en archivos INVÁLIDOS)

Los siguientes paths Core aparecen en archivos que deberían estar en apps específicas, pero son válidos como dependencias:

- `core/js/lib/http.js`
- `core/js/lib/api-helpers.js`
- `core/js/lib/dom-utils.js`
- `core/js/lib/datatables-utils.js`
- `core/js/helpers/routes.js`
- `core/js/helpers/crud.js`
- `core/js/helpers/module.js`

**Recomendación:** Estos paths Core son correctos como dependencias, pero los archivos que los incluyen deben moverse a sus apps correspondientes.

### Paths de App Encontrados (INVÁLIDOS en Core)

- `core/js/clientes/*`
- `core/js/contabilidad/*`
- `core/js/facturas/*`
- `core/js/inventario/*`
- `core/js/gastos/*`
- `core/js/empleados/*`
- `core/js/empresa/*`
- `core/js/perfil/*`
- `core/js/proveedores/*`
- `core/js/dashboard/*`
- `core/js/landing/*`
- `core/js/mail/*`
- `core/js/mailinbox/*`

**Recomendación:** Todos estos paths indican que los partials deben moverse a sus apps correspondientes.

### Legacy

- **empresa/assets_empresas.html:** Posible duplicación con `assets_empresa.html` (ambos incluyen scripts de empresa pero con diferentes estructuras).

---

## Recomendaciones Generales

1. **Mantener en Core:** Solo `assets_common.html` (aunque está vacío, puede usarse para helpers Core comunes).

2. **Mover a Apps:** Todos los demás partials deben moverse a sus apps correspondientes:
   - `clientes/*` → `apps/tenant/clientes/templates/tenant/clientes/partials/`
   - `contabilidad/*` → `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/`
   - `facturas/*` → `apps/tenant/facturas/templates/tenant/facturas/partials/`
   - `inventario/*` → `apps/tenant/inventario/templates/tenant/inventario/partials/`
   - `gastos/*` → `apps/tenant/gastos/templates/tenant/gastos/partials/`
   - `empleados/*` → `apps/tenant/empleados/templates/tenant/empleados/partials/`
   - `empresa/*` → `apps/tenant/empresa/templates/tenant/empresa/partials/`
   - `perfil/*` → `apps/tenant/perfil/templates/tenant/perfil/partials/`
   - `proveedores/*` → `apps/tenant/proveedores/templates/tenant/proveedores/partials/`
   - `dashboard/*` → `apps/tenant/dashboard/templates/tenant/dashboard/partials/` (si existe)
   - `landing/*` → `apps/tenant/landing/templates/tenant/landing/partials/` (si existe)
   - `mail/*` → `apps/tenant/mail/templates/tenant/mail/partials/` (si existe)
   - `mailinbox/*` → `apps/tenant/mailinbox/templates/tenant/mailinbox/partials/` (si existe)

3. **Consolidar Duplicados:** Revisar `empresa/assets_empresa.html` y `empresa/assets_empresas.html` para consolidar si son duplicados.

4. **Crear Partial Core Único:** Considerar crear un `assets_core_helpers.html` que incluya solo los helpers Core comunes (http.js, api-helpers.js, dom-utils.js, datatables-utils.js, helpers/routes.js, helpers/crud.js, helpers/module.js) para que las apps lo incluyan desde Core.

---

**Nota:** Esta auditoría es solo identificación. El movimiento de archivos se realizará en una ola separada.
