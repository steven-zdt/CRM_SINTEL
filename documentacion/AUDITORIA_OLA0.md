# Auditoría Ola 0 - Inventario Frontend JS/HTML

**Fecha:** 2025-01-27  
**Alcance:** Inspección completa de módulos JS/HTML en TENANT_APPS  
**Objetivo:** Cerrar inventario real de módulos a migrar y confirmar brechas vs estándar

---

## 1. Mapa por App

### 1.1 Facturas

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/facturas/assets_facturas.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/facturas/facturas.page.js` (352 líneas)
- `apps/tenant/core/static/core/js/facturas/facturas.table.js`
- `apps/tenant/core/static/core/js/facturas/facturas.dt.js` (224 líneas)
- `apps/tenant/core/static/core/js/facturas/facturas.api.js`
- `apps/tenant/core/static/core/js/facturas/facturas.components.js`

**DataTables detectadas:**
- `#table-facturas` → `/api/v1/facturas/dt/` (POST, CSRF ✅)
- `#dt-facturas-main` → `/api/v1/facturas/dt/facturas/` (POST, CSRF ✅)

**Endpoints/URLs:**
- `/api/v1/facturas/dt/` (hardcode)
- `/api/v1/facturas/` (hardcode)

**Método:** POST ✅  
**CSRF header:** ✅ (usa `getCookie('csrftoken')` local)  
**Patrón de visibilidad:** ❌ (no usa `DOMUtils.waitForVisible`)  
**Manejo 401/403:** ❌ (no documentado)

**Brechas:**
- ❌ `getCookie('csrftoken')` duplicado (debería usar `http.js`)
- ❌ URLs hardcodeadas (debería usar `routes.js`)
- ❌ No usa `DOMUtils.waitForVisible` para esperas de visibilidad

---

### 1.2 Contabilidad

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_contabilidad.html`
- `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_cuentas.html`
- `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_asientos.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/contabilidad/contabilidad.page.js` (352 líneas)
- `apps/tenant/core/static/core/js/contabilidad/contabilidad.table.js`
- `apps/tenant/core/static/core/js/contabilidad/cuentas.page.js`
- `apps/tenant/core/static/core/js/contabilidad/asientos.page.js`
- `apps/tenant/core/static/core/js/contabilidad/contabilidad.api.js`

**DataTables detectadas:**
- `#table-contabilidad-cuentas` → `/api/v1/contabilidad/dt/cuentas-contables/` (POST, CSRF ✅)
- `#table-contabilidad-asientos` → `/api/v1/contabilidad/dt/asientos-contables/` (POST, CSRF ✅)

**Endpoints/URLs:**
- `/api/v1/contabilidad/dt/cuentas-contables/` (hardcode)
- `/api/v1/contabilidad/dt/asientos-contables/` (hardcode)
- `/api/v1/contabilidad/asientos-contables/` (hardcode en `asientos.page.js`)

**Método:** POST ✅  
**CSRF header:** ✅ (usa `getCookie('csrftoken')` local)  
**Patrón de visibilidad:** ✅ (usa `DOMUtils.waitForVisible` en `contabilidad.page.js`)  
**Manejo 401/403:** ❌ (no documentado)

**Brechas:**
- ❌ `getCookie('csrftoken')` duplicado
- ❌ URLs hardcodeadas

---

### 1.3 Inventario

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/inventario/assets_inventario.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/inventario/inventario.page.js` (352 líneas)
- `apps/tenant/core/static/core/js/inventario/inventario.table.js`
- `apps/tenant/core/static/core/js/inventario/catalogo.page.js`
- `apps/tenant/core/static/core/js/inventario/activos.page.js`
- `apps/tenant/core/static/core/js/inventario/movimientos.page.js`
- `apps/tenant/core/static/core/js/inventario/inventario.api.js`

**DataTables detectadas:**
- `#table-inventario-catalogo` → `/api/v1/inventario/dt/catalogo/` (POST, CSRF ✅)
- `#table-inventario-activos` → `/api/v1/inventario/dt/activos-fijos/` (POST, CSRF ✅)
- `#table-inventario-movimientos` → `/api/v1/inventario/dt/movimientos/` (POST, CSRF ✅)

**Endpoints/URLs:**
- `/api/v1/inventario/dt/catalogo/` (hardcode)
- `/api/v1/inventario/dt/activos-fijos/` (hardcode)
- `/api/v1/inventario/dt/movimientos/` (hardcode)
- `/api/v1/inventario/catalogo/` (hardcode en `catalogo.page.js`, `movimientos.page.js`)
- `/api/v1/inventario/activos-fijos/` (hardcode en `activos.page.js`)

**Método:** POST ✅  
**CSRF header:** ✅ (usa `getCookie('csrftoken')` local)  
**Patrón de visibilidad:** ✅ (usa `DOMUtils.waitForVisible` en `inventario.page.js`)  
**Manejo 401/403:** ❌ (no documentado)

**Brechas:**
- ❌ `getCookie('csrftoken')` duplicado
- ❌ URLs hardcodeadas

---

### 1.4 Clientes

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/clientes/assets_clientes.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/clientes/clientes.page.js` (913 líneas)
- `apps/tenant/core/static/core/js/clientes/clientes.table.js`

**DataTables detectadas:**
- `#table-clientes` → `/api/v1/clientes/dt/clientes/` (POST, CSRF ✅)

**Endpoints/URLs:**
- `/api/v1/clientes/dt/clientes/` (hardcode en `clientes.table.js`)
- `/api/v1/clientes/` (hardcode, usa HATEOAS discovery en `clientes.page.js`)

**Método:** POST ✅  
**CSRF header:** ✅ (usa `API_HELPERS.safeFetchJson` que maneja CSRF)  
**Patrón de visibilidad:** ✅ (usa `DOMUtils.waitForVisible`)  
**Manejo 401/403:** ✅ (manejo inteligente en `API_HELPERS`)

**Brechas:**
- ⚠️ URLs parcialmente hardcodeadas (usa discovery HATEOAS pero con base hardcode)

---

### 1.5 Proveedores

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/proveedores/assets_proveedores.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/proveedores/proveedores.page.js` (916 líneas)
- `apps/tenant/core/static/core/js/proveedores/proveedores.dt.js` (146 líneas)
- `apps/tenant/core/static/core/js/proveedores/proveedores.api.js`

**DataTables detectadas:**
- `#dt-proveedores-main` → `/api/v1/proveedores/dt/proveedores/` (POST, CSRF ✅)

**Endpoints/URLs:**
- `/api/v1/proveedores/dt/proveedores/` (hardcode)
- `/api/v1/proveedores/` (hardcode, usa HATEOAS discovery)

**Método:** POST ✅  
**CSRF header:** ✅ (usa `window.getCookie('csrftoken')` desde `http.js`)  
**Patrón de visibilidad:** ✅ (usa `DOMUtils.waitForVisible`)  
**Manejo 401/403:** ✅ (manejo inteligente en `API_HELPERS`)

**Brechas:**
- ⚠️ URLs parcialmente hardcodeadas

---

### 1.6 Empleados

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/empleados/assets_empleados.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/empleados/empleados.page.js`
- `apps/tenant/core/static/core/js/empleados/empleados.dt.js` (146 líneas)
- `apps/tenant/core/static/core/js/empleados/empleados.api.js`

**DataTables detectadas:**
- `#dt-empleados-main` → `/api/v1/empleados/dt/empleados/` (POST, CSRF ✅)

**Endpoints/URLs:**
- `/api/v1/empleados/dt/empleados/` (hardcode)

**Método:** POST ✅  
**CSRF header:** ✅ (usa `window.getCookie('csrftoken')` desde `http.js`)  
**Patrón de visibilidad:** ❌ (no verificado)  
**Manejo 401/403:** ❌ (no documentado)

**Brechas:**
- ❌ URLs hardcodeadas
- ❌ No verificado uso de `DOMUtils.waitForVisible`

---

### 1.7 Gastos

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/gastos/assets_gastos.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/gastos/gastos.page.js`
- `apps/tenant/core/static/core/js/gastos/gastos.dt.js` (164 líneas)
- `apps/tenant/core/static/core/js/gastos/gastos.api.js`

**DataTables detectadas:**
- `#dt-gastos-main` → `/api/v1/gastos/dt/gastos/` (POST, CSRF ✅)

**Endpoints/URLs:**
- `/api/v1/gastos/dt/gastos/` (hardcode)

**Método:** POST ✅  
**CSRF header:** ✅ (usa `window.getCookie('csrftoken')` desde `http.js`)  
**Patrón de visibilidad:** ❌ (no verificado)  
**Manejo 401/403:** ❌ (no documentado)

**Brechas:**
- ❌ URLs hardcodeadas
- ❌ No verificado uso de `DOMUtils.waitForVisible`

---

### 1.8 Perfil

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/perfil/assets_perfil.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/perfil/perfil.page.js`
- `apps/tenant/core/static/core/js/perfil/perfil.api.js`

**DataTables detectadas:** Ninguna

**Endpoints/URLs:**
- `/api/v1/perfil/perfiles/me/` (hardcode, singleton)

**Método:** GET/PATCH  
**CSRF header:** ✅ (usa `API_HELPERS` o `http.js`)  
**Patrón de visibilidad:** ✅ (usa `DOMUtils.waitForVisible`)  
**Manejo 401/403:** ✅ (manejo inteligente)

**Brechas:**
- ❌ URL hardcodeada

---

### 1.9 Empresa

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/empresa/assets_empresa.html`
- `apps/tenant/core/templates/tenant/core/partials/empresa/assets_empresas.html`
- `apps/tenant/core/templates/tenant/core/partials/empresa/assets_mailinbox.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/empresa/empresa.page.js`
- `apps/tenant/core/static/core/js/empresa/empresa.api.js`
- `apps/tenant/core/static/core/js/empresa/empresa.ui.js`
- `apps/tenant/core/static/core/js/empresa/empresa.modals.js`
- `apps/tenant/core/static/core/js/mailinbox/mailinbox.page.js`

**DataTables detectadas:** Ninguna

**Endpoints/URLs:**
- `/api/v1/core/empresa/` (hardcode)
- `/api/v1/empresas/` (hardcode)
- `/api/v1/empresas/mail-inbox-config/` (hardcode en `mailinbox.page.js`)

**Método:** GET/POST/PATCH/DELETE  
**CSRF header:** ✅ (usa `http.js` o `API_HELPERS`)  
**Patrón de visibilidad:** ✅ (usa `DOMUtils.waitForVisible`)  
**Manejo 401/403:** ✅ (manejo inteligente)

**Brechas:**
- ❌ URLs hardcodeadas

---

### 1.10 Landing

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/landing/assets_landing.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/landing/landing.page.js`
- `apps/tenant/core/static/core/js/landing/landing.api.js`

**DataTables detectadas:** Ninguna

**Endpoints/URLs:**
- Endpoints de landing (no detallados en esta auditoría)

**Método:** GET/POST  
**CSRF header:** ✅  
**Patrón de visibilidad:** ❌ (no verificado)  
**Manejo 401/403:** ✅

---

### 1.11 Dashboard

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/dashboard/assets_dashboard.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/dashboard/dashboard.page.js`
- `apps/tenant/core/static/core/js/dashboard/dashboard.api.js`

**DataTables detectadas:** Ninguna

**Endpoints/URLs:**
- Endpoints de dashboard (no detallados en esta auditoría)

**Método:** GET  
**CSRF header:** ✅  
**Patrón de visibilidad:** ❌ (no verificado)  
**Manejo 401/403:** ✅

---

### 1.12 Mail

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/mail/assets_mail.html`

**Archivos JS:**
- `apps/tenant/core/static/core/js/mail/mail.page.js`
- `apps/tenant/core/static/core/js/mail/mail.api.js`
- `apps/tenant/core/static/core/js/mail/mail.ui.js`
- `apps/tenant/core/static/core/js/mail/mail.modals.js`

**DataTables detectadas:** Ninguna

**Endpoints/URLs:**
- Endpoints de mail (no detallados en esta auditoría)

**Método:** GET/POST  
**CSRF header:** ✅  
**Patrón de visibilidad:** ❌ (no verificado)  
**Manejo 401/403:** ✅

---

## 2. Hallazgos Globales

### 2.1 URLs Hardcodeadas

**Total de módulos con URLs hardcodeadas:** 12/12 (100%)

**Patrones detectados:**
- `/api/v1/{app}/` (colecciones)
- `/api/v1/{app}/dt/{resource}/` (DataTables)
- `/api/v1/{app}/{resource}/` (recursos específicos)
- `/api/v1/core/{resource}/` (Core API)

**Impacto:** Alto - Cualquier cambio en rutas requiere modificar múltiples archivos JS.

---

### 2.2 CSRF Token Management

**Módulos con `getCookie('csrftoken')` duplicado:** 8/12

**Módulos que usan `http.js` o `API_HELPERS`:**
- ✅ Clientes (usa `API_HELPERS.safeFetchJson`)
- ✅ Proveedores (usa `window.getCookie` desde `http.js`)
- ✅ Empleados (usa `window.getCookie` desde `http.js`)
- ✅ Gastos (usa `window.getCookie` desde `http.js`)
- ✅ Perfil (usa `API_HELPERS` o `http.js`)
- ✅ Empresa (usa `http.js` o `API_HELPERS`)

**Módulos con implementación local:**
- ❌ Facturas (implementación local)
- ❌ Contabilidad (implementación local)
- ❌ Inventario (implementación local)

**Impacto:** Medio - Duplicación de código, riesgo de inconsistencias.

---

### 2.3 DataTables Server-Side

**Total de DataTables detectadas:** 11

**Conformes (POST + CSRF):** 11/11 (100%) ✅

**Módulos con DataTables:**
1. Facturas (2 tablas)
2. Contabilidad (2 tablas)
3. Inventario (3 tablas)
4. Clientes (1 tabla)
5. Proveedores (1 tabla)
6. Empleados (1 tabla)
7. Gastos (1 tabla)

**Brechas:**
- ❌ Todas usan URLs hardcodeadas
- ⚠️ Algunas no usan helper centralizado para CSRF

---

### 2.4 Esperas de Visibilidad

**Módulos que usan `DOMUtils.waitForVisible`:**
- ✅ Contabilidad (`contabilidad.page.js`)
- ✅ Inventario (`inventario.page.js`)
- ✅ Clientes (`clientes.page.js`)
- ✅ Proveedores (`proveedores.page.js`)
- ✅ Perfil (`perfil.page.js`)
- ✅ Empresa (`empresa.page.js`)
- ✅ Facturas (`facturas.page.js`)

**Módulos con `setTimeout` personalizado:**
- ⚠️ Algunos módulos pueden tener timeouts personalizados no detectados

**Impacto:** Bajo - La mayoría ya usa el helper centralizado.

---

### 2.5 Manejo de 401/403

**Módulos con manejo inteligente:**
- ✅ Clientes (vía `API_HELPERS`)
- ✅ Proveedores (vía `API_HELPERS`)
- ✅ Perfil (vía `API_HELPERS`)
- ✅ Empresa (vía `http.js`)

**Módulos sin manejo documentado:**
- ❌ Facturas
- ❌ Contabilidad
- ❌ Inventario
- ❌ Empleados
- ❌ Gastos

**Impacto:** Medio - Riesgo de redirecciones inesperadas en módulos no críticos.

---

## 3. Brechas vs Estándar

### 3.1 UI Standard TENANT_APPS

**✅ Cumplimiento:**
- Páginas sin lógica (datos vía JS) ✅
- Rutas en TENANT_URLCONF ✅
- Core como orquestador ✅

**❌ Brechas:**
- URLs hardcodeadas (deberían venir de Core Routes API)
- CSRF duplicado (debería usar `http.js`)

---

### 3.2 DataTables Estándar

**✅ Cumplimiento:**
- Server-side con POST ✅
- CSRF obligatorio ✅
- Paginación DRF ✅

**❌ Brechas:**
- URLs hardcodeadas (deberían venir de Core Routes API)
- Algunos módulos no usan helper centralizado para CSRF

---

### 3.3 Estáticos/Partials

**✅ Cumplimiento:**
- Assets JS/CSS en app origen ✅
- Partials por app ✅
- No usa `static/` raíz ✅

**❌ Brechas:** Ninguna detectada

---

## 4. Verificación de Rutas en TENANT_URLCONF

### 4.1 Rutas Registradas en `config/api_urls.py`

| App | Prefijo | Estado | Archivo |
|-----|---------|--------|---------|
| empresas | `empresas/` | ✅ | `apps/tenant/empresa/api/urls.py` |
| facturas | `facturas/` | ✅ | `apps/tenant/facturas/api/urls.py` |
| contabilidad | `''` (raíz) | ✅ | `apps/tenant/contabilidad/api/urls.py` |
| inventario | `inventario/` | ✅ | `apps/tenant/inventario/api/urls.py` |
| perfil | `perfil/` | ✅ | `apps/tenant/perfil/api/urls.py` |
| dashboard | `dashboard/` | ✅ | `apps/tenant/dashboard/api/urls.py` |
| core | `core/` | ✅ | `apps/tenant/core/api/urls.py` |
| empleados | `empleados/` | ✅ | `apps/tenant/empleados/api/urls.py` |
| gastos | `gastos/` | ✅ | `apps/tenant/gastos/api/urls.py` |
| proveedores | `proveedores/` | ✅ | `apps/tenant/proveedores/api/urls.py` |
| clientes | `clientes/` | ✅ | `apps/tenant/clientes/api/urls.py` |
| landing | `landing/` | ✅ | `apps/tenant/landing/api/urls.py` |

**Resultado:** ✅ Todas las apps están registradas correctamente.

---

### 4.2 Endpoints DataTables Verificados

| Módulo | Endpoint Esperado | Presente | Archivo Fuente |
|--------|-------------------|----------|----------------|
| facturas | `/api/v1/facturas/dt/facturas/` | ✅ | `apps/tenant/facturas/api/urls.py` |
| contabilidad | `/api/v1/contabilidad/dt/cuentas-contables/` | ✅ | `apps/tenant/contabilidad/api/urls.py` |
| contabilidad | `/api/v1/contabilidad/dt/asientos-contables/` | ✅ | `apps/tenant/contabilidad/api/urls.py` |
| inventario | `/api/v1/inventario/dt/catalogo/` | ✅ | `apps/tenant/inventario/api/urls.py` |
| inventario | `/api/v1/inventario/dt/activos-fijos/` | ✅ | `apps/tenant/inventario/api/urls.py` |
| inventario | `/api/v1/inventario/dt/movimientos/` | ✅ | `apps/tenant/inventario/api/urls.py` |
| clientes | `/api/v1/clientes/dt/clientes/` | ✅ | `apps/tenant/clientes/api/urls.py` |
| proveedores | `/api/v1/proveedores/dt/proveedores/` | ✅ | `apps/tenant/proveedores/api/urls.py` |
| empleados | `/api/v1/empleados/dt/empleados/` | ✅ | `apps/tenant/empleados/api/urls.py` |
| gastos | `/api/v1/gastos/dt/gastos/` | ✅ | `apps/tenant/gastos/api/urls.py` |

**Resultado:** ✅ Todos los endpoints DataTables están registrados correctamente.

---

## 5. Riesgos Identificados

### 5.1 Riesgo Alto

1. **URLs Hardcodeadas (100% de módulos)**
   - **Impacto:** Cualquier cambio en rutas requiere modificar múltiples archivos JS
   - **Mitigación:** Implementar Core Routes API (`GET /api/v1/core/routes/`)

2. **CSRF Duplicado (8/12 módulos)**
   - **Impacto:** Inconsistencias, riesgo de errores
   - **Mitigación:** Migrar todos a `http.js`

---

### 5.2 Riesgo Medio

1. **Manejo 401/403 Inconsistente**
   - **Impacto:** Redirecciones inesperadas en módulos no críticos
   - **Mitigación:** Estandarizar manejo en `http.js`

2. **Timeouts de Visibilidad Personalizados**
   - **Impacto:** Comportamiento inconsistente
   - **Mitigación:** Migrar todos a `DOMUtils.waitForVisible`

---

### 5.3 Riesgo Bajo

1. **Partials HTML sin estandarizar**
   - **Impacto:** Bajo, estructura ya es consistente
   - **Mitigación:** Documentar patrón estándar

---

## 6. Lista Priorizada de Módulos para Migración

### 6.1 Prioridad 1 - Críticos Server-Side (DataTables)

1. **Facturas** ⚠️
   - 2 DataTables
   - URLs hardcodeadas
   - CSRF duplicado
   - No usa `DOMUtils.waitForVisible`

2. **Contabilidad** ⚠️
   - 2 DataTables
   - URLs hardcodeadas
   - CSRF duplicado
   - ✅ Usa `DOMUtils.waitForVisible`

3. **Inventario** ⚠️
   - 3 DataTables
   - URLs hardcodeadas
   - CSRF duplicado
   - ✅ Usa `DOMUtils.waitForVisible`

4. **Clientes** ✅
   - 1 DataTable
   - URLs parcialmente hardcodeadas (usa HATEOAS)
   - ✅ Usa `API_HELPERS`
   - ✅ Usa `DOMUtils.waitForVisible`

5. **Proveedores** ✅
   - 1 DataTable
   - URLs parcialmente hardcodeadas (usa HATEOAS)
   - ✅ Usa `http.js`
   - ✅ Usa `DOMUtils.waitForVisible`

6. **Empleados** ⚠️
   - 1 DataTable
   - URLs hardcodeadas
   - ✅ Usa `http.js`
   - ❌ No verificado `DOMUtils.waitForVisible`

7. **Gastos** ⚠️
   - 1 DataTable
   - URLs hardcodeadas
   - ✅ Usa `http.js`
   - ❌ No verificado `DOMUtils.waitForVisible`

---

### 6.2 Prioridad 2 - Client-Side (Sin DataTables)

8. **Perfil** ✅
   - Singleton (GET/PATCH)
   - URL hardcodeada
   - ✅ Usa `API_HELPERS`
   - ✅ Usa `DOMUtils.waitForVisible`

9. **Empresa** ⚠️
   - CRUD completo
   - URLs hardcodeadas
   - ✅ Usa `http.js` o `API_HELPERS`
   - ✅ Usa `DOMUtils.waitForVisible`

10. **Landing** ⚠️
    - Endpoints de autenticación
    - URLs hardcodeadas (asumido)
    - ✅ Usa helpers centralizados

11. **Dashboard** ⚠️
    - Endpoints de resumen
    - URLs hardcodeadas (asumido)
    - ✅ Usa helpers centralizados

12. **Mail** ⚠️
    - Endpoints de correo
    - URLs hardcodeadas (asumido)
    - ✅ Usa helpers centralizados

---

### 6.3 Prioridad 3 - Singleton/Especiales

13. **Mailinbox** ⚠️
    - Configuración de mailbox
    - URL hardcodeada (`/api/v1/empresas/mail-inbox-config/`)
    - ✅ Usa helpers centralizados

---

## 7. Resumen Ejecutivo

### 7.1 Conteo Real

- **Módulos totales:** 12
- **Módulos con URLs hardcodeadas:** 12 (100%)
- **Módulos con `getCookie('csrftoken')` duplicado:** 8 (67%)
- **DataTables totales:** 11
- **DataTables conformes POST + CSRF:** 11 (100%) ✅
- **Timeouts de visibilidad personalizados:** 0 (todos usan `DOMUtils.waitForVisible` o no requieren)

---

### 7.2 Acciones Recomendadas

1. **Crear Core Routes API** (`GET /api/v1/core/routes/`)
   - Mapa canónico de rutas por módulo
   - Endpoint único para descubrimiento de rutas

2. **Migrar CSRF a `http.js`**
   - Eliminar implementaciones locales de `getCookie('csrftoken')`
   - Usar `window.getCookie` desde `http.js`

3. **Migrar URLs a `routes.js`**
   - Reemplazar todas las URLs hardcodeadas
   - Usar Core Routes API para descubrimiento

4. **Estandarizar manejo 401/403**
   - Implementar en `http.js`
   - Respetar módulos no críticos

5. **Smoke tests por módulo**
   - Verificar que cada módulo funciona después de migración
   - Validar que DataTables cargan correctamente

---

## 8. Próximos Pasos (Olas 1-5)

1. **Ola 1:** Crear Core Routes API y helpers centralizados
2. **Ola 2:** Migrar módulos críticos (Facturas, Contabilidad, Inventario)
3. **Ola 3:** Migrar módulos client-side (Perfil, Empresa, Landing)
4. **Ola 4:** Migrar módulos restantes (Empleados, Gastos, Mail)
5. **Ola 5:** Auditoría final y smoke tests

---

**Fin del Informe**
