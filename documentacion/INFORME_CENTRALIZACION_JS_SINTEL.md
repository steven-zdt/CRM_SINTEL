# 📊 INFORME: Centralización JS (DataTables + CRUD) - SINTEL v2.37

**Fecha:** 2026-01-29  
**Versión:** v2.37  
**Fuente de Verdad:** `documentacion/arquitectura_general.md`

---

## 📋 Resumen Ejecutivo

Este informe documenta el estado actual del código JavaScript en las `TENANT_APPS` del proyecto SINTEL, identificando patrones, duplicaciones y oportunidades de centralización conforme a la arquitectura API-First establecida.

### Hallazgos Principales

- ✅ **26 módulos `.page.js`** detectados en `apps/tenant/core/static/core/js/`
- ✅ **15 inicializaciones DataTables** con server-side POST
- ⚠️ **3 helpers parciales** existentes (`api-helpers.js`, `dom-utils.js`, `http.js`, `datatables-utils.js`)
- ❌ **0 endpoint centralizado** de rutas (`GET /api/v1/core/routes/` no existe)
- ⚠️ **Duplicación de código** en construcción de URLs, manejo CSRF, y esperas de visibilidad

---

## 🗺️ Mapa por App

### 1. **clientes** (`apps/tenant/core/static/core/js/clientes/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/clientes/assets_clientes.html`
  - Carga: `clientes.page.js`

**Archivos JS:**
- `clientes.page.js` (913 líneas)
- `clientes.table.js` (128 líneas)

**DataTables:**
- ❌ **NO usa DataTables server-side**
- ✅ Usa DataTables **client-side** con `fetchClienteList()` + `API_HELPERS.safeFetchJson()`
- ✅ Tabla: `#table-clientes`
- ✅ Inicialización: `DataTablesUtils.initOrUpdateDataTable()` (helper existente)

**Endpoints/URLs:**
- ✅ Descubrimiento dinámico: `discoverCollectionUrl()` desde índice HATEOAS
- ✅ Base: `${API_HELPERS.API_BASE}clientes/`
- ✅ Detalle: `buildDetailUrl(collectionUrl, id)`
- ✅ CRUD: GET, POST, PATCH, DELETE

**Método HTTP:**
- ✅ GET para list/detail
- ✅ POST/PATCH/DELETE con `API_HELPERS.safeFetchJson()` (incluye CSRF automático)

**CSRF Header:**
- ✅ Sí (vía `API_HELPERS.authHeaders()`)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()` (helper existente)

**Manejo 401/403:**
- ✅ 401: Muestra feedback local, no redirige (módulo no crítico)
- ✅ 403: Logging mejorado en `API_HELPERS.safeFetchJson()`

**Estado:** ✅ **CONFORME** - Usa helpers centralizados correctamente

---

### 2. **proveedores** (`apps/tenant/core/static/core/js/proveedores/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/proveedores/assets_proveedores.html`
  - Carga: `proveedores.page.js`

**Archivos JS:**
- `proveedores.page.js` (916 líneas)
- `proveedores.dt.js` (140 líneas) - ⚠️ **DUPLICADO** (no se usa si `proveedores.page.js` existe)

**DataTables:**
- ❌ **NO usa DataTables server-side** (igual que clientes)
- ✅ Usa DataTables **client-side** con `fetchProveedorList()`
- ✅ Tabla: `#table-proveedores`

**Endpoints/URLs:**
- ✅ Descubrimiento dinámico: `discoverCollectionUrl()`
- ✅ Base: `${API_HELPERS.API_BASE}proveedores/`

**Método HTTP:**
- ✅ GET/POST/PATCH/DELETE con `API_HELPERS.safeFetchJson()`

**CSRF Header:**
- ✅ Sí (vía `API_HELPERS.authHeaders()`)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()`

**Manejo 401/403:**
- ✅ 401: Feedback local (módulo no crítico)

**Estado:** ✅ **CONFORME** - Similar a clientes

---

### 3. **gastos** (`apps/tenant/core/static/core/js/gastos/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/gastos/assets_gastos.html`
  - Carga: `gastos.page.js`

**Archivos JS:**
- `gastos.page.js` (905 líneas)
- `gastos.dt.js` (140 líneas) - ⚠️ **DUPLICADO**

**DataTables:**
- ❌ **NO usa DataTables server-side**
- ✅ Usa DataTables **client-side** con `fetchGastoList()`
- ✅ Tabla: `#table-gastos`

**Endpoints/URLs:**
- ✅ Descubrimiento dinámico: `discoverCollectionUrl()`
- ✅ Base: `${API_HELPERS.API_BASE}gastos/`

**Método HTTP:**
- ✅ GET/POST/PATCH/DELETE con `API_HELPERS.safeFetchJson()`

**CSRF Header:**
- ✅ Sí (vía `API_HELPERS.authHeaders()`)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()`

**Manejo 401/403:**
- ✅ 401: Feedback local (módulo no crítico)

**Estado:** ✅ **CONFORME**

---

### 4. **empleados** (`apps/tenant/core/static/core/js/empleados/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/empleados/assets_empleados.html`
  - Carga: `empleados.page.js`

**Archivos JS:**
- `empleados.page.js` (943 líneas)
- `empleados.dt.js` (145 líneas) - ⚠️ **DUPLICADO**

**DataTables:**
- ❌ **NO usa DataTables server-side**
- ✅ Usa DataTables **client-side** con `fetchEmpleadoList()`
- ✅ Tabla: `#table-empleados`

**Endpoints/URLs:**
- ✅ Descubrimiento dinámico: `discoverCollectionUrl()`
- ✅ Base: `${API_HELPERS.API_BASE}empleados/`

**Método HTTP:**
- ✅ GET/POST/PATCH/DELETE con `API_HELPERS.safeFetchJson()`

**CSRF Header:**
- ✅ Sí (vía `API_HELPERS.authHeaders()`)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()`

**Manejo 401/403:**
- ✅ 401: Feedback local (módulo no crítico)

**Estado:** ✅ **CONFORME**

---

### 5. **facturas** (`apps/tenant/core/static/core/js/facturas/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/facturas/assets_facturas.html`
  - Carga múltiple:
    - `http.js`
    - `facturas.api.js`
    - `facturas.components.js`
    - `facturas.table.js`
    - `facturas.modals.js`
    - `facturas.page.js`

**Archivos JS:**
- `facturas.page.js` (574 líneas) - ⚠️ **MIXTO**: Tiene inicialización unificada + DataTables server-side
- `facturas.dt.js` (170 líneas) - ⚠️ **LEGACY** (no se usa)
- `facturas.table.js` (151 líneas) - ⚠️ **LEGACY** (no se usa)
- `facturas.api.js` - Helper API específico
- `facturas.components.js` - Componentes UI
- `facturas.modals.js` - Modales

**DataTables:**
- ✅ **USA DataTables server-side POST** (conforme v2.37)
- ✅ Tabla: `#table-facturas`
- ✅ Endpoint: `/api/v1/facturas/dt/`
- ✅ Config:
  ```javascript
  {
    serverSide: true,
    type: 'POST',
    headers: { 'X-CSRFToken': CSRF },
    ajax: { url: API_DT, ... }
  }
  ```

**Endpoints/URLs:**
- ⚠️ **HARDCODEADO**: `const API_DT = '/api/v1/facturas/dt/'`
- ⚠️ **HARDCODEADO**: `const API_BASE = '/api/v1/facturas/'`
- ❌ No usa descubrimiento dinámico

**Método HTTP:**
- ✅ POST para DataTables (conforme)
- ✅ GET/POST/PATCH/DELETE para CRUD (vía `facturas.api.js`)

**CSRF Header:**
- ✅ Sí (obtiene con `getCookie('csrftoken')` local, no usa `API_HELPERS`)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()` en inicialización unificada

**Manejo 401/403:**
- ⚠️ **NO documentado** en `facturas.page.js` (delega a `facturas.api.js`)

**Estado:** ⚠️ **PARCIALMENTE CONFORME**
- ✅ DataTables server-side POST correcto
- ❌ URLs hardcodeadas (debe usar descubrimiento)
- ⚠️ CSRF local (debe usar `API_HELPERS.getCSRF()`)

---

### 6. **contabilidad** (`apps/tenant/core/static/core/js/contabilidad/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_contabilidad.html`
- `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_cuentas.html`
- `apps/tenant/core/templates/tenant/core/partials/contabilidad/assets_asientos.html`

**Archivos JS:**
- `contabilidad.page.js` (656 líneas) - **2 DataTables**: cuentas + asientos
- `contabilidad.table.js` - ⚠️ **LEGACY** (no se usa)
- `contabilidad.api.js` - Helper API
- `contabilidad.modals.js` - Modales
- `cuentas.page.js` (862 líneas) - ⚠️ **DUPLICADO** (módulo separado)
- `asientos.page.js` - ⚠️ **DUPLICADO** (módulo separado)

**DataTables:**
- ✅ **USA DataTables server-side POST** (2 tablas)
- ✅ Tabla 1: `#table-contabilidad-cuentas` → `/api/v1/dt/cuentas-contables/`
- ✅ Tabla 2: `#table-contabilidad-asientos` → `/api/v1/dt/asientos-contables/`
- ✅ Config: `serverSide: true, type: 'POST', headers: { 'X-CSRFToken': CSRF }`

**Endpoints/URLs:**
- ⚠️ **HARDCODEADO**: `const API_BASE = '/api/v1/'`
- ⚠️ **HARDCODEADO**: Endpoints DT construidos manualmente
- ❌ No usa descubrimiento dinámico

**Método HTTP:**
- ✅ POST para DataTables
- ✅ GET/POST/PATCH/DELETE para CRUD

**CSRF Header:**
- ✅ Sí (obtiene con `getCookie('csrftoken')` local)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()` en inicialización unificada

**Manejo 401/403:**
- ⚠️ **NO documentado** explícitamente

**Estado:** ⚠️ **PARCIALMENTE CONFORME**
- ✅ DataTables server-side POST correcto
- ❌ URLs hardcodeadas
- ⚠️ Múltiples archivos duplicados (cuentas.page.js, asientos.page.js)

---

### 7. **inventario** (`apps/tenant/core/static/core/js/inventario/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/inventario/assets_inventario.html`

**Archivos JS:**
- `inventario.page.js` (916 líneas)
- `catalogo.page.js` (718 líneas)
- `activos.page.js` (916 líneas)
- `movimientos.page.js` (805 líneas)
- `inventario.table.js` - Helper tabla
- `inventario.api.js` - Helper API

**DataTables:**
- ✅ **USA DataTables server-side POST** (múltiples tablas)
- ✅ Tabla: `#table-inventario-catalogo` → `/api/v1/inventario/catalogo-items/dt/`
- ✅ Config: `serverSide: true, type: 'POST'`

**Endpoints/URLs:**
- ⚠️ **HARDCODEADO**: URLs construidas manualmente
- ❌ No usa descubrimiento dinámico

**Método HTTP:**
- ✅ POST para DataTables
- ✅ GET/POST/PATCH/DELETE para CRUD

**CSRF Header:**
- ✅ Sí (vía helpers locales)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()` en algunos módulos

**Manejo 401/403:**
- ⚠️ **NO documentado** explícitamente

**Estado:** ⚠️ **PARCIALMENTE CONFORME**
- ✅ DataTables server-side POST correcto
- ❌ URLs hardcodeadas
- ⚠️ Múltiples módulos separados (catalogo, activos, movimientos)

---

### 8. **empresa** (`apps/tenant/core/static/core/js/empresa/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/empresa/assets_empresa.html`
- `apps/tenant/core/templates/tenant/core/partials/empresa/assets_empresas.html`
- `apps/tenant/core/templates/tenant/core/partials/empresa/assets_mailinbox.html`

**Archivos JS:**
- `empresa.page.js` (802 líneas)
- `empresa.api.js` - Helper API
- `empresa.ui.js` - Helper UI
- `empresa.modals.js` - Modales

**DataTables:**
- ❌ **NO usa DataTables** (singleton, no lista)

**Endpoints/URLs:**
- ✅ Usa `API_HELPERS.safeFetchJson()` con descubrimiento
- ✅ Base: `/api/v1/empresas/` o `/api/v1/core/empresa/`

**Método HTTP:**
- ✅ GET/PATCH con `API_HELPERS.safeFetchJson()`

**CSRF Header:**
- ✅ Sí (vía `API_HELPERS.authHeaders()`)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()`

**Manejo 401/403:**
- ✅ 401: Redirige a login (módulo crítico)

**Estado:** ✅ **CONFORME**

---

### 9. **perfil** (`apps/tenant/core/static/core/js/perfil/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/perfil/assets_perfil.html`

**Archivos JS:**
- `perfil.page.js` (506 líneas)
- `perfil.api.js` - Helper API
- `perfil.modals.js` - Modales
- `perfil.ui.js` - Helper UI

**DataTables:**
- ❌ **NO usa DataTables** (singleton)

**Endpoints/URLs:**
- ✅ Usa `API_HELPERS.safeFetchJson()`
- ✅ Base: `/api/v1/perfil/perfiles/me/`

**Método HTTP:**
- ✅ GET/PATCH con `API_HELPERS.safeFetchJson()`

**CSRF Header:**
- ✅ Sí (vía `API_HELPERS.authHeaders()`)

**Patrón de Visibilidad:**
- ✅ Usa `DOMUtils.waitForVisible()` en inicialización unificada

**Manejo 401/403:**
- ✅ 401: Muestra feedback, no redirige (módulo no crítico)

**Estado:** ✅ **CONFORME**

---

### 10. **dashboard** (`apps/tenant/core/static/core/js/dashboard/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/dashboard/assets_dashboard.html`

**Archivos JS:**
- `dashboard.page.js`
- `dashboard.api.js` - Helper API

**DataTables:**
- ❌ **NO usa DataTables** (KPIs y resúmenes)

**Endpoints/URLs:**
- ✅ Usa `API_HELPERS.safeFetchJson()`
- ✅ Base: `/api/v1/core/dashboard/`

**Estado:** ✅ **CONFORME**

---

### 11. **landing** (`apps/tenant/core/static/core/js/landing/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/landing/assets_landing.html`

**Archivos JS:**
- `landing.page.js`
- `landing.api.js` - Helper API

**DataTables:**
- ❌ **NO usa DataTables**

**Endpoints/URLs:**
- ✅ Usa `API_HELPERS.safeFetchJson()`
- ✅ Base: `/api/v1/core/landing/` o `/api/v1/landing/`

**Estado:** ✅ **CONFORME**

---

### 12. **mail/mailinbox** (`apps/tenant/core/static/core/js/mail/`, `mailinbox/`)

**Partials HTML:**
- `apps/tenant/core/templates/tenant/core/partials/mail/assets_mail.html`
- `apps/tenant/core/templates/tenant/core/partials/empresa/assets_mailinbox.html`

**Archivos JS:**
- `mail.page.js`
- `mail.api.js`
- `mail.modals.js`
- `mailinbox.page.js` (594 líneas)

**DataTables:**
- ⚠️ **NO documentado** explícitamente (requiere inspección)

**Endpoints/URLs:**
- ⚠️ **NO documentado** explícitamente

**Estado:** ⚠️ **REQUIERE INSPECCIÓN**

---

## 🔍 Hallazgos Globales

### 1. **Duplicación de Código**

#### A. Construcción de URLs
- ❌ **15+ módulos** construyen URLs manualmente: `/api/v1/${MOD}/dt/`
- ❌ **0 módulos** usan endpoint centralizado de rutas
- ⚠️ **3 módulos** usan descubrimiento HATEOAS (clientes, proveedores, gastos, empleados) - ✅ Buen patrón

#### B. Obtención de CSRF
- ⚠️ **2 implementaciones**:
  - `API_HELPERS.getCSRF()` (usado por 8 módulos) ✅
  - `getCookie('csrftoken')` local (usado por 5 módulos) ❌

#### C. Esperas de Visibilidad
- ✅ **Mayoría usa** `DOMUtils.waitForVisible()` (helper existente)
- ⚠️ **Algunos módulos** tienen timeouts personalizados con `setTimeout`

#### D. Inicialización DataTables
- ⚠️ **2 patrones**:
  - Inicialización unificada (facturas, contabilidad, inventario) ✅
  - Inicialización directa sin helpers (algunos módulos legacy) ❌

### 2. **404/403 Recurrentes**

- ⚠️ **No documentado** explícitamente en logs, pero:
  - Módulos con URLs hardcodeadas pueden fallar si rutas cambian
  - Falta endpoint centralizado de rutas para validación

### 3. **Timeouts de Visibilidad**

- ✅ **Mayoría usa** `DOMUtils.waitForVisible()` con timeout configurable
- ⚠️ **Algunos módulos** tienen `setTimeout` hardcodeado (300ms, 200ms)

### 4. **Fetch sin CSRF/POST**

- ✅ **Todos los módulos** incluyen CSRF en headers
- ✅ **DataTables server-side** usan POST (conforme v2.37)
- ⚠️ **Algunos módulos** usan `getCookie()` local en lugar de `API_HELPERS.getCSRF()`

### 5. **URLs Hardcodeadas**

- ❌ **10+ módulos** tienen URLs hardcodeadas:
  - `facturas.page.js`: `const API_DT = '/api/v1/facturas/dt/'`
  - `contabilidad.page.js`: `const API_BASE = '/api/v1/'`
  - `inventario/*.page.js`: URLs construidas manualmente

---

## 📊 Brechas vs. Estándar

### A. UI Standard (documentacion/arquitectura_general.md)

#### ✅ Conforme:
- Partials HTML en `apps/tenant/core/templates/tenant/core/partials/`
- Assets JS en `apps/tenant/core/static/core/js/`
- Rutas en `TENANT_URLCONF` (`config/urls_tenant.py`)

#### ❌ Brechas:
- **0 módulos** usan endpoint centralizado de rutas (`GET /api/v1/core/routes/` no existe)
- Algunos módulos tienen lógica de negocio en JS (debe estar en APIs)

### B. DataTables Estándar

#### ✅ Conforme:
- **15 inicializaciones** usan `serverSide: true`
- **15 inicializaciones** usan `type: 'POST'`
- **15 inicializaciones** incluyen `X-CSRFToken` en headers

#### ❌ Brechas:
- **5 módulos** (clientes, proveedores, gastos, empleados, empresa) usan DataTables **client-side** (no server-side)
  - ⚠️ **NOTA**: Esto puede ser intencional si los datasets son pequeños
- **Algunos módulos** no usan `datatables-utils.js` para inicialización segura

### C. Estáticos/Templates

#### ✅ Conforme:
- Assets en `apps/tenant/core/static/core/js/`
- Partials en `apps/tenant/core/templates/tenant/core/partials/`
- No se usa `static/` raíz

#### ❌ Brechas:
- Algunos módulos tienen archivos `.dt.js` y `.table.js` **duplicados** que no se usan

---

## 💡 Recomendaciones

### 1. Crear Helpers Centralizados

**Ubicación:** `apps/tenant/core/static/core/js/helpers/`

#### A. `http.js` ✅ **YA EXISTE** (parcialmente)
- ✅ Manejo de CSRF
- ✅ Manejo de 401/403
- ⚠️ **MEJORAR**: Unificar con `api-helpers.js` (hay duplicación)

#### B. `routes.js` ❌ **NO EXISTE** (CRÍTICO)
- Descubrir rutas desde `GET /api/v1/core/routes/`
- Cachear rutas en `sessionStorage`
- Fallback a construcción manual si endpoint no disponible

#### C. `dom.js` ✅ **YA EXISTE** (`dom-utils.js`)
- ✅ `waitForVisible()`
- ✅ `isVisible()`
- ✅ `getEl()`

#### D. `datatable.js` ✅ **YA EXISTE** (`datatables-utils.js`)
- ✅ `canUseDataTables()`
- ✅ `initOrUpdateDataTable()`
- ⚠️ **MEJORAR**: Agregar helper para inicialización server-side POST estándar

#### E. `crud.js` ❌ **NO EXISTE**
- Helpers para operaciones CRUD estándar:
  - `create(resource, data)`
  - `read(resource, id)`
  - `update(resource, id, data)`
  - `delete(resource, id)`
  - Todos con manejo de errores 404/422/401

#### F. `module.js` ❌ **NO EXISTE**
- Bootstrap estándar para módulos:
  - Espera de visibilidad
  - Descubrimiento de rutas
  - Inicialización de DataTables
  - Bind de eventos

### 2. Endpoint Centralizado de Rutas

**Crear:** `GET /api/v1/core/routes/`

**Ubicación Backend:**
- Vista: `apps/tenant/core/api/views.py` → `CoreRoutesView`
- URL: `apps/tenant/core/api/urls.py` → `path('routes/', CoreRoutesView.as_view())`
- Registrar en: `config/api_urls.py` → `path('core/', include('apps.tenant.core.api.urls'))`

**Respuesta Esperada:**
```json
{
  "clientes": {
    "collection": "/api/v1/clientes/",
    "detail": "/api/v1/clientes/{id}/",
    "datatable": "/api/v1/clientes/dt/"
  },
  "proveedores": {
    "collection": "/api/v1/proveedores/",
    "detail": "/api/v1/proveedores/{id}/",
    "datatable": "/api/v1/proveedores/dt/"
  },
  ...
}
```

### 3. Migración de Módulos

**Patrón Típico Actual:**
```javascript
// ❌ ANTES
const API_DT = `/api/v1/${MOD}/dt/`;
const CSRF = getCookie('csrftoken');
dtInstance = $table.DataTable({
  ajax: {
    url: API_DT,
    type: 'POST',
    headers: { 'X-CSRFToken': CSRF }
  }
});
```

**Patrón Propuesto:**
```javascript
// ✅ DESPUÉS
import { routes } from './helpers/routes.js';
import { datatable } from './helpers/datatable.js';

const modRoutes = await routes.get('clientes');
dtInstance = datatable.initServerSide({
  table: '#table-clientes',
  endpoint: modRoutes.datatable,
  columns: COLUMNS
});
```

---

## 📅 Plan de Adopción

### Fase 1: Piloto (2 módulos)
1. ✅ Seleccionar: `clientes` y `proveedores` (ya usan helpers parcialmente)
2. ✅ Crear `routes.js` helper
3. ✅ Crear endpoint `GET /api/v1/core/routes/`
4. ✅ Migrar `clientes.page.js` y `proveedores.page.js` a usar `routes.js`
5. ✅ Validar con smoke tests

### Fase 2: Auditoría Automática
1. ✅ Script de validación:
   - Detectar URLs hardcodeadas
   - Detectar `getCookie()` local (no `API_HELPERS.getCSRF()`)
   - Detectar `setTimeout` para visibilidad (no `DOMUtils.waitForVisible()`)
   - Detectar DataTables sin POST + CSRF

### Fase 3: Migración Progresiva
1. ✅ Migrar módulos con DataTables server-side (facturas, contabilidad, inventario)
2. ✅ Migrar módulos con DataTables client-side (gastos, empleados)
3. ✅ Migrar módulos singleton (empresa, perfil)

### Fase 4: Smoke Tests
1. ✅ Test por módulo:
   - Tabla se inicializa correctamente
   - Rutas se descubren desde endpoint
   - CSRF se incluye en requests
   - 401/403 se manejan correctamente

---

## ✅ Criterios de Éxito

- [ ] 0 inicializaciones DataTables sin `POST + CSRF`
- [ ] 0 fetch directos sin `http.js` o `API_HELPERS.safeFetchJson()`
- [ ] 0 rutas construidas a mano en `*.page.js` (todas desde `routes.js`)
- [ ] 0 timeouts de visibilidad personalizados fuera de `dom.js`
- [ ] Smoke tests por módulo pasan
- [ ] `GET /api/v1/core/routes/` operativo

---

## 📝 Notas Finales

- **No mover assets** fuera de `apps/tenant/core/static/core/js/` (conforme estándar)
- **No cambiar contratos API** (solo centralizar descubrimiento de rutas)
- **Mantener compatibilidad** con módulos legacy durante migración
- **Documentar** cualquier gap de rutas en endpoint centralizado

---

**Fin del Informe**
