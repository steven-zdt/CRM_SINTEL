# SPRINT 1 — Desbloquear el CRUD desde la UI

**Proyecto:** CRM Sintel · **Rama destino:** `fix/sprint1-desbloquear-crud` (a crear desde `main`)
**Duración estimada:** 5 días hábiles · **Riesgo:** 🟢 Bajo · **Reversible:** Sí
**Documento creado:** 2026-05-02

---

## 0. Contexto y Objetivo

### Problema raíz verificado en la auditoría previa

Todos los módulos `tenant` consumen un **cliente HTTP que no existe** en su contexto:

1. `apps/public/console/static/js/http.js` exporta `window.http` como **objeto** con métodos `.get/.post/.patch/.delete/.put`.
2. Los 27 archivos `*.api.js` de tenant llaman `w.http('METHOD', url, payload)` esperando una **función** con esa firma.
3. `http.js` **solo se incluye en `apps/public/console/templates/console/base.html`**, no en `apps/tenant/core/templates/tenant/base.html`. En cualquier vista de tenant `window.http` literalmente no existe.
4. Los `*.api.js` con la guarda `if (typeof w.http !== 'function') { return; }` cortocircuitan y `clientesAPI`, `inventarioAPI`, etc. **nunca quedan definidos**, así que cualquier botón "Guardar/Editar/Eliminar" lanza `TypeError: Cannot read property 'create' of undefined` y el handler captura el error sin renderizar feedback.

### Objetivo del sprint

| # | Entregable | Resultado esperado |
|---|---|---|
| 1 | Reescribir `http.js` para que sea **función + objeto** y devuelva `{ok, status, data}` | Compatibilidad total con los 27 `*.api.js` y con `ui-manager.js` |
| 2 | Cargar `http.js` en `apps/tenant/core/templates/tenant/base.html` | `window.http` disponible en todas las vistas de tenant |
| 3 | Implementar `Edit Tenant` (modal + PATCH) en la consola pública | Botón "Editar" funcional en `/console/tenants/` |
| 4 | Definir `showError()` global (en `ui-manager.js`) | Eliminar `ReferenceError: showError is not defined` en módulos tenant |
| 5 | Suite mínima Playwright: login → CRUD de un módulo de referencia | Smoke test reproducible en CI |

### Métrica de éxito

- 0 ocurrencias de `TypeError: Cannot read property 'create' of undefined` en consola del navegador.
- Crear/Editar/Eliminar funciona end-to-end en al menos: **Clientes, Inventario (Productos), Contabilidad (Cuenta), Tenants**.
- Suite Playwright pasa en local (`npx playwright test`).

---

## 1. Inventario de impacto (verificado por grep)

### 1.1 Archivos `*.api.js` que dependen de `w.http(method, url, payload)` — 27 archivos

| App | Archivo | Endpoints CRUD afectados |
|---|---|---|
| `tenant.clientes` | [clientes.api.js](apps/tenant/clientes/static/clientes/js/clientes.api.js) | clientes, contactos |
| `tenant.clientes` | [contactos/contacto_cliente_api.js](apps/tenant/clientes/static/clientes/js/contactos/contacto_cliente_api.js) | contactos (renderOffcanvas) |
| `tenant.clientes` | [clientes.list.js:418](apps/tenant/clientes/static/clientes/js/clientes.list.js#L418), [clientes.contactos.js:97](apps/tenant/clientes/static/clientes/js/clientes.contactos.js#L97) | inline (DELETE) |
| `tenant.inventario` | [inventario.api.js](apps/tenant/inventario/static/inventario/js/inventario.api.js) | productos, servicios, activos, movimientos, categorías, historial-servicios |
| `tenant.inventario` | features/`productos_*.js`, `servicios_*.js`, `activos_*.js`, `movimientos_*.js`, `categorias_*.js`, `inventario_*.js` | inline en editores y listas |
| `tenant.inventario` | [inventario.utils.js:39](apps/tenant/inventario/static/inventario/js/inventario.utils.js#L39) | categorías (load) |
| `tenant.contabilidad` | [asiento/asiento.api.js](apps/tenant/contabilidad/static/contabilidad/js/asiento/asiento.api.js) | asientos |
| `tenant.contabilidad` | [cuenta/cuenta.api.js](apps/tenant/contabilidad/static/contabilidad/js/cuenta/cuenta.api.js) | plan de cuentas |
| `tenant.contabilidad` | [periodo/periodo.api.js](apps/tenant/contabilidad/static/contabilidad/js/periodo/periodo.api.js) | periodos contables |
| `tenant.empresa` | empresa.api.js (varias copias — consolidar es deuda separada) | datos de empresa |
| `tenant.empleados` | empleados.api.js | empleados |
| `tenant.gastos` | gastos.api.js | gastos |
| `tenant.proveedores` | proveedores.api.js | proveedores |
| `tenant.cotizaciones` | cotizaciones.api.js | cotizaciones |
| `tenant.facturas` | facturas.api.js | facturas |
| `tenant.proyectos` | proyectos.api.js | proyectos |
| `tenant.perfil` | perfil.api.js | perfil |
| `tenant.dashboard` | dashboard.api.js | dashboard |
| `tenant.core` | mail.api.js, mailinbox.api.js, landing.api.js | mailinbox, landing |

> **Nota:** existen duplicados (ej. `tenant/empresa/static/empresa/js/empresa.api.js`, `tenant/empresa/static/js/empresa/empresa.api.js`, `tenant/core/static/core/js/empresa/empresa.api.js`). **No los consolides en este sprint** — solo verifica que todos consuman el `w.http(method, url, payload)` armonizado. La consolidación queda para Sprint 2.

### 1.2 Consumidor del lado de la consola pública

| Archivo | Uso |
|---|---|
| [http.js](apps/public/console/static/js/http.js) | objeto con métodos (`.get/.post/...`) |
| [tenants_manager.js](apps/public/console/static/js/tenants_manager.js) | usa `fetch()` directo (no `http`) |
| [users_manager.js](apps/public/console/static/js/users_manager.js) | usa `fetch()` directo |
| [console.js](apps/public/console/static/js/console.js) | usa `fetchAPI()` interno + `jwtAuth` |
| [console/templates/console/base.html](apps/public/console/templates/console/base.html) | **único** template que carga `http.js` hoy |

### 1.3 `showError(...)` invocado pero indefinido en algunos contextos

| Definido en | Invocado en (sin import/define) |
|---|---|
| `clientes.list.js:615` (local) | `inventario/features/*.js` (varios), `cotizaciones/cotizaciones.page.js` |
| `tenants/templates/public/activate_password.html:213` (inline) | — |
| `landing/.../facturas.page.js:188` (local) | — |
| `core/static/core/js/error_injector.js:125` (interna) | — |

**Conclusión:** la función está reimplementada localmente 4 veces y **falta global**. La centralizamos en `ui-manager.js`.

---

## 2. Fase 1 (Día 1, mañana) — Reescribir `http.js`

### 2.1 Contrato nuevo

```text
// Forma función (la que usan TODOS los *.api.js de tenant)
const res = await window.http('POST', '/api/v1/clientes/', payload);
// res = { ok: true, status: 201, data: { id: 42, ... } }
// res = { ok: false, status: 400, data: { campo: ['error'] } }   ← NO lanza
// res = { ok: false, status: 0, data: { detail: 'Error de red' } } ← NO lanza

// Forma objeto (la que usa la consola pública: tenants/users/impuestos)
const data = await window.http.get('/api/public/v1/tenants/');   // throw on error
await window.http.post('/api/public/v1/tenants/', payload);      // throw on error
```

**Regla clave:** la **forma función** **no lanza** en errores HTTP (4xx/5xx) — devuelve `{ok:false, status, data}` para que `clientes.editor.js`, `productos_editor.js`, etc. puedan hacer `if (response.ok) { ... } else { ... }` exactamente como ya hacen. La **forma objeto** sí lanza, para conservar el contrato actual de `console.js` / `impuestos.api.js`.

### 2.2 Código completo (reemplaza `apps/public/console/static/js/http.js`)

```javascript
/**
 * http.js — Cliente HTTP unificado (v3.4)
 *
 * Doble contrato:
 *   1. Función (compatibilidad tenant *.api.js):
 *        const res = await window.http(method, url, payload?);
 *        // res = { ok, status, data }   NO lanza en 4xx/5xx
 *
 *   2. Objeto (compatibilidad consola pública):
 *        await window.http.get(url, params?);
 *        await window.http.post(url, body?);
 *        // lanza Error en 4xx/5xx
 *
 * Inyecta automáticamente:
 *   - X-CSRFToken (desde meta[name="csrf-token"])
 *   - Authorization: Bearer <token> si window.jwtAuth.getValidAccessToken() existe
 *   - credentials: 'include' (cookies HttpOnly OTT)
 */
(function (w) {
  'use strict';

  function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  async function buildHeaders(extra = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
      'Accept': 'application/json',
      ...extra,
    };
    // Inyectar JWT si está disponible (no romper si no lo está)
    try {
      if (w.jwtAuth && typeof w.jwtAuth.getValidAccessToken === 'function') {
        const token = await w.jwtAuth.getValidAccessToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;
      }
    } catch (_) { /* silencioso: jwtAuth opcional */ }
    return headers;
  }

  async function parseBody(response) {
    const ct = response.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      try { return await response.json(); } catch (_) { return null; }
    }
    try { return await response.text(); } catch (_) { return null; }
  }

  /**
   * Forma función: no lanza, devuelve {ok, status, data}
   */
  async function httpFn(method, url, payload) {
    const opts = {
      method: String(method || 'GET').toUpperCase(),
      credentials: 'include',
      headers: await buildHeaders(),
    };
    if (payload !== undefined && opts.method !== 'GET' && opts.method !== 'HEAD') {
      opts.body = JSON.stringify(payload);
    }

    let response;
    try {
      response = await fetch(url, opts);
    } catch (networkErr) {
      // Error de red, DNS, CORS, etc.
      return {
        ok: false,
        status: 0,
        data: { detail: networkErr && networkErr.message ? networkErr.message : 'Error de red' },
      };
    }

    const data = await parseBody(response);
    return { ok: response.ok, status: response.status, data };
  }

  /**
   * Forma objeto: lanza Error en 4xx/5xx (contrato pre-existente)
   */
  function buildError(response, data) {
    if (data && data.detail) return new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
    if (data && data.non_field_errors && data.non_field_errors[0]) return new Error(data.non_field_errors[0]);
    if (data && typeof data === 'object') {
      const flat = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join('; ');
      return new Error(flat || `HTTP ${response.status}`);
    }
    return new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  async function request(url, options = {}) {
    const opts = {
      credentials: 'include',
      ...options,
      headers: { ...(await buildHeaders()), ...(options.headers || {}) },
    };
    const response = await fetch(url, opts);
    const data = await parseBody(response);
    if (!response.ok) throw buildError(response, data);
    return data;
  }

  const methods = {
    async get(url, params = {}) {
      const qs = new URLSearchParams(params).toString();
      return request(qs ? `${url}?${qs}` : url, { method: 'GET' });
    },
    async post(url, body = {}) {
      return request(url, { method: 'POST', body: JSON.stringify(body) });
    },
    async patch(url, body = {}) {
      return request(url, { method: 'PATCH', body: JSON.stringify(body) });
    },
    async put(url, body = {}) {
      return request(url, { method: 'PUT', body: JSON.stringify(body) });
    },
    async delete(url) {
      return request(url, { method: 'DELETE' });
    },
  };

  // Fusionar: la función httpFn ES la API pública, y le pegamos los métodos encima
  Object.assign(httpFn, methods);

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { http: httpFn };
  }
  w.http = httpFn;

  // Marcador para detectar versión cargada (útil en tests y debugging)
  w.http.__version__ = '3.4';
})(window);
```

### 2.3 Smoke test manual inmediato (DevTools console)

```javascript
// Forma función
await window.http('GET', '/api/v1/clientes/?page_size=1')
  // → { ok: true, status: 200, data: { count: ..., results: [...] } }

// Forma objeto
await window.http.get('/api/public/v1/impuestos/contribuyentes-tipos/')
  // → [...]   (lanza si 4xx/5xx)

// Verificar versión
console.log(window.http.__version__);   // → "3.4"
```

### 2.4 Compatibilidad regresiva — qué romper / qué no

| Llamada existente | Antes | Después | ¿Funciona? |
|---|---|---|---|
| `w.http('GET', url)` (tenant `*.api.js`) | TypeError | `{ok, status, data}` | ✅ Funciona |
| `await w.http.get(url)` (consola) | data directa o throw | data directa o throw | ✅ Idéntico |
| `await w.http.post(url, body)` (consola) | data directa o throw | data directa o throw | ✅ Idéntico |

---

## 3. Fase 2 (Día 1, tarde) — Cargar `http.js` en `tenant/base.html`

### 3.1 Decisión: dónde colocar el `<script>`

Debe cargarse **antes** que cualquier `*.api.js` y **después** de `jwt-auth.js` (porque inyecta JWT si está disponible). El template `tenant/base.html` ya carga `jwt-auth.js` en línea 125. Nuevo script va inmediatamente después.

### 3.2 Diff a aplicar en [apps/tenant/core/templates/tenant/base.html](apps/tenant/core/templates/tenant/base.html)

```diff
     <!-- JWT helper: proporciona window.jwtAuth para inyección Authorization -->
     <script src="{% static 'js/jwt-auth.js' %}"></script>
+
+    <!-- Cliente HTTP unificado v3.4 (función + objeto, devuelve {ok,status,data}) -->
+    <!-- Debe cargarse DESPUÉS de jwt-auth.js y ANTES de cualquier *.api.js -->
+    <script src="{% static 'js/http.js' %}"></script>

     <!-- Hook de scripts por-página -->
     {% block page_assets_body %}{% endblock page_assets_body %}
```

### 3.3 Rutas de `static/`

Verificar que `apps/public/console/static/js/http.js` queda accesible vía `{% static 'js/http.js' %}`. En este proyecto la consola pública ya lo expone con esa misma ruta (línea 125 carga `js/jwt-auth.js`). Si por configuración de `STATICFILES_DIRS` no estuviera, la alternativa es:

```diff
-    <script src="{% static 'js/http.js' %}"></script>
+    <script src="{% static 'console/static/js/http.js' %}"></script>
```

**Acción concreta:**
1. Ejecutar `python manage.py collectstatic --noinput --dry-run | grep http.js` para confirmar la ruta colectada.
2. Si no aparece, copiar `http.js` también a `apps/tenant/core/static/js/http.js` (es el patrón ya usado para `jwt-auth.js`).

### 3.4 Validación post-cambio

```bash
# 1. Recolectar staticfiles
python manage.py collectstatic --noinput

# 2. Reiniciar runserver
python manage.py runserver 0.0.0.0:8000

# 3. En el navegador, en cualquier subdominio de tenant (ej. demo.sintel.com:8000):
#    Abrir DevTools → Console → typeof window.http
#    → "function"
#    → window.http.__version__ === "3.4"
```

---

## 4. Fase 3 (Días 2 y 3) — Verificación y desbloqueo POR MÓDULO

> **Estrategia:** no tocar la lógica de los `*.api.js` ni de los editores. Solo **verificar** que la corrección de `http.js` los desbloquea. El plan por módulo es: (a) cargar la página, (b) reproducir el CRUD, (c) confirmar smoke en DevTools.

### Plantilla de verificación (a aplicar en cada módulo)

```text
[ ] Cargar /<modulo>/  →  ningún error rojo en consola
[ ] Tabla Tabulator se popula  →  GET responde 200 y Tabulator muestra filas
[ ] Botón "Nuevo"  →  offcanvas abre  →  guardar form mínimo  →  201
[ ] Botón "Editar" en una fila  →  offcanvas con datos  →  PATCH 200
[ ] Botón "Eliminar"  →  confirma  →  DELETE 204
[ ] En DevTools: Network → ningún request 4xx/5xx no esperado
[ ] En DevTools: Console → ningún ReferenceError ni TypeError
```

### 4.1 Módulo `clientes`

**Archivos clave:**
- [clientes.api.js](apps/tenant/clientes/static/clientes/js/clientes.api.js) — CLIENTES_BASE=`/api/v1/clientes`, CONTACTOS_BASE=`/api/v1/clientes/contactos`
- [clientes.list.js](apps/tenant/clientes/static/clientes/js/clientes.list.js) — Tabulator + acciones
- [clientes.editor.js](apps/tenant/clientes/static/clientes/js/clientes.editor.js) — form

**Pasos:**
1. Subdominio: `demo.sintel.com:8000/clientes/`.
2. Verificar en consola: `window.clientesAPI` debe existir (`Object.freeze` con `list/get/create/update/delete`).
3. CRUD:
   - **Crear:** "Nuevo Cliente" → llenar campos requeridos (`tipo_persona`, `tipo_documento`, `numero_documento`, `razon_social`, `regimen_tributario`) → Guardar.
   - **Editar:** click "Editar" en una fila → cambiar razón social → Guardar.
   - **Eliminar:** click "Eliminar" → confirmar.
4. **Sub-módulo Contactos:**
   - Tab "Contactos" en detalle de cliente → repetir crear/editar/eliminar.
5. Bug específico a confirmar resuelto: [clientes.list.js:418](apps/tenant/clientes/static/clientes/js/clientes.list.js#L418) (DELETE inline).

**Resultado esperado:** los 3 botones funcionan **sin tocar más código**. Si falla algún campo de validación, es problema de serializer (deuda separada).

### 4.2 Módulo `inventario`

**Archivos clave (todos consumen `w.http`):**
- [inventario.api.js](apps/tenant/inventario/static/inventario/js/inventario.api.js) — productos, servicios, activos, movimientos, categorías, historial-servicios
- features: [productos_editor.js](apps/tenant/inventario/static/inventario/js/features/productos_editor.js), [productos_list.js](apps/tenant/inventario/static/inventario/js/features/productos_list.js), `servicios_*`, `activos_*`, `movimientos_*`, `categorias_*`, `inventario_*`
- [inventario.utils.js:39](apps/tenant/inventario/static/inventario/js/inventario.utils.js#L39) — preload de categorías (200 items)

**Sub-módulos a probar uno por uno** (cada uno tiene editor + list propios):

| Sub-módulo | Endpoint base | Crear | Editar | Eliminar |
|---|---|---|---|---|
| Productos | `/api/v1/inventario/productos/` | ✅ | ✅ | ✅ |
| Servicios | `/api/v1/inventario/servicios/` | ✅ | ✅ | ✅ |
| Activos | `/api/v1/inventario/activos/` | ✅ | ✅ | ✅ |
| Movimientos | `/api/v1/inventario/movimientos/` | ✅ | — | — |
| Categorías | `/api/v1/inventario/categorias/` | ✅ | ✅ | ✅ |
| Historial-Servicios | `/api/v1/inventario/historial-servicios/` | ✅ | — | — |

**Pasos:**
1. `demo.sintel.com:8000/inventario/`
2. Verificar `typeof window.inventarioAPI === 'object'`.
3. Para cada sub-módulo de la tabla, ejecutar el smoke `[Crear → Editar → Eliminar]`.
4. **Atención particular** a [inventario_editor.js:200](apps/tenant/inventario/static/inventario/js/features/inventario_editor.js#L200) (`w.http(method, endpoint, data)` con method dinámico) — el contrato lo soporta sin cambios.

### 4.3 Módulo `contabilidad`

**Sub-módulos:**

| Sub-módulo | Archivo API | Endpoint |
|---|---|---|
| Asientos | [asiento/asiento.api.js](apps/tenant/contabilidad/static/contabilidad/js/asiento/asiento.api.js) | `/api/v1/contabilidad/asientos/` |
| Cuentas | [cuenta/cuenta.api.js](apps/tenant/contabilidad/static/contabilidad/js/cuenta/cuenta.api.js) | `/api/v1/contabilidad/cuentas/` |
| Periodos | [periodo/periodo.api.js](apps/tenant/contabilidad/static/contabilidad/js/periodo/periodo.api.js) | `/api/v1/contabilidad/periodos/` |

**Pasos:**
1. `/contabilidad/cuentas/` → CRUD cuenta del plan.
2. `/contabilidad/periodos/` → crear periodo (mensual), abrir, cerrar.
3. `/contabilidad/asientos/` → CRUD asiento con líneas (cuidado con balance débito=crédito).
4. Smoke especial: [features/asiento_cargar_desde_docs.js](apps/tenant/contabilidad/static/contabilidad/js/asiento/features/asiento_cargar_desde_docs.js) (ingesta XML/UBL).

### 4.4 Módulo `empresa` (incluye 3 ubicaciones duplicadas)

**Archivos** (todos hacen lo mismo, **no consolidar en este sprint**):
- `apps/tenant/empresa/static/empresa/js/empresa.api.js`
- `apps/tenant/empresa/static/js/empresa/empresa.api.js`
- `apps/tenant/core/static/core/js/empresa/empresa.api.js`

**Acción:** verificar **cuál** es el que se carga efectivamente (`assets_empresa.html` lo dirá). Probar CRUD desde la página actual `/empresa/`. Anotar cuál se cargó (para Sprint 2 — consolidación).

### 4.5 Módulo `empleados`

- [empleados/empleados.api.js](apps/tenant/empleados/static/empleados/js/empleados.api.js)
- También existe duplicado en `apps/tenant/core/static/core/js/empleados/empleados.api.js`.

**Pasos:** `/empleados/` → CRUD empleado.

### 4.6 Módulo `gastos`

- [gastos/gastos.api.js](apps/tenant/gastos/static/gastos/js/gastos.api.js)
- Duplicado en `core/static/core/js/gastos/gastos.api.js`.

**Pasos:** `/gastos/` → CRUD gasto.

### 4.7 Módulo `proveedores`

- [proveedores/proveedores.api.js](apps/tenant/proveedores/static/proveedores/js/proveedores.api.js)
- Duplicado en `core/static/core/js/proveedores/proveedores.api.js`.

**Pasos:** `/proveedores/` → CRUD proveedor.

### 4.8 Módulo `cotizaciones`

- [cotizaciones/cotizaciones.api.js](apps/tenant/cotizaciones/static/cotizaciones/js/cotizaciones.api.js)

**Pasos:**
1. `/cotizaciones/` → crear cotización.
2. **Limitación conocida:** TODO en backend de "convertir a factura" — fuera de alcance de este sprint.

### 4.9 Módulo `facturas`

- [facturas/facturas.api.js](apps/tenant/facturas/static/js/facturas/facturas.api.js)

**Pasos:**
1. `/facturas/` → upload XML/UBL → verificar parsing.
2. CRUD básico de factura.
3. **No probar** workflows de envío DIAN en este sprint.

### 4.10 Módulo `proyectos`

- [proyectos/proyectos.api.js](apps/tenant/proyectos/static/proyectos/js/proyectos.api.js)

**Pasos:** `/proyectos/` → CRUD proyecto.

### 4.11 Módulo `perfil`

- [perfil/perfil.api.js](apps/tenant/perfil/static/perfil/js/perfil.api.js)

**Pasos:** `/perfil/` → editar campos de perfil de colaborador.

### 4.12 Módulo `dashboard`

- [dashboard/dashboard.api.js](apps/tenant/dashboard/static/dashboard/js/dashboard.api.js)

**Pasos:** `/dashboard/` → verificar que widgets cargan datos (sólo lectura).

### 4.13 Módulos auxiliares `mail` / `mailinbox` / `landing`

- [core/static/core/js/mail/mail.api.js](apps/tenant/core/static/core/js/mail/mail.api.js)
- [core/static/core/js/mailinbox/mailinbox.api.js](apps/tenant/core/static/core/js/mailinbox/mailinbox.api.js)
- [core/static/core/js/landing/landing.api.js](apps/tenant/core/static/core/js/landing/landing.api.js)

**Pasos:** verificar que cargan sin error en consola. CRUD profundo es opcional en este sprint.

### 4.14 Tabla resumen del Día 2 + Día 3

Llenar al cerrar cada módulo:

| Módulo | List ✅ | Create ✅ | Update ✅ | Delete ✅ | Notas |
|---|---|---|---|---|---|
| clientes | | | | | |
| clientes.contactos | | | | | |
| inventario.productos | | | | | |
| inventario.servicios | | | | | |
| inventario.activos | | | | | |
| inventario.movimientos | | | — | — | sólo registro |
| inventario.categorías | | | | | |
| contabilidad.cuentas | | | | | |
| contabilidad.periodos | | | | | |
| contabilidad.asientos | | | | | |
| empresa | | | | | qué archivo se cargó: |
| empleados | | | | | |
| gastos | | | | | |
| proveedores | | | | | |
| cotizaciones | | | | — | |
| facturas | | | | | |
| proyectos | | | | | |
| perfil | — | — | | — | sólo edit |
| dashboard | — | — | — | — | read-only |

---

## 5. Fase 4 (Día 4, mañana) — `showError()` global en `ui-manager.js`

### 5.1 Estado actual

`ui-manager.js` **ya tiene** `handleError(response, context, options)` (verificado en líneas 32-100). Lo que falta es exponer un atajo `showError(message)` y `showSuccess(message)` globales que sustituyan a las definiciones locales en `clientes.list.js:615`, `landing/.../facturas.page.js:188` y los usos sin definición en `inventario`.

### 5.2 Cambio en [apps/tenant/core/static/core/js/common/ui-manager.js](apps/tenant/core/static/core/js/common/ui-manager.js)

Agregar al final del IIFE existente (justo antes del cierre `})(window, document)`):

```javascript
  // ============================================
  // v3.4 — Atajos globales: showError / showSuccess / showInfo
  // Centralizan los `showError(...)` que estaban definidos localmente
  // en clientes.list.js, facturas.page.js, etc.
  // ============================================

  function _toast(level, msg) {
    const text = (msg && typeof msg === 'object') ? JSON.stringify(msg) : String(msg ?? '');
    if (w.SintelFeedback && typeof w.SintelFeedback[level] === 'function') {
      w.SintelFeedback[level](text);
      return;
    }
    if (w.Notyf) {
      try {
        const n = w._notyfInstance || (w._notyfInstance = new w.Notyf({ duration: 4000, dismissible: true }));
        n[level === 'success' ? 'success' : 'error'](text);
        return;
      } catch (_) { /* fallthrough */ }
    }
    // Fallback final: console (no romper UX)
    (console[level] || console.log)(`[ui] ${level}: ${text}`);
  }

  w.showError   = function (msg) { _toast('error',   msg); };
  w.showSuccess = function (msg) { _toast('success', msg); };
  w.showInfo    = function (msg) { _toast('info',    msg); };

  // Idempotente: exponer también en UIManager para uso explícito
  w.UIManager = w.UIManager || {};
  w.UIManager.showError   = w.showError;
  w.UIManager.showSuccess = w.showSuccess;
  w.UIManager.showInfo    = w.showInfo;
```

### 5.3 Limpieza opcional (recomendada pero NO bloqueante)

Eliminar las definiciones locales que ahora están duplicadas:
- [clientes.list.js:615-622](apps/tenant/clientes/static/clientes/js/clientes.list.js#L615) — eliminar `function showError(msg) { ... }`
- [landing/.../facturas.page.js:188](apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js#L188) — idem

> Si quitas las locales, los **call sites** ya funcionan porque `window.showError` ahora existe global. Si prefieres minimizar diff en este sprint, **déjalas** (las locales sombrean a la global, pero no rompen nada).

### 5.4 Verificación

```javascript
// DevTools en cualquier vista de tenant
typeof window.showError;     // → "function"
window.showError('test');    // → toast rojo
window.showSuccess('ok');    // → toast verde
```

---

## 6. Fase 5 (Día 4, tarde) — Implementar `Edit Tenant`

### 6.1 Estado actual del código

[apps/public/console/static/js/tenants_manager.js:436-440](apps/public/console/static/js/tenants_manager.js#L436-L440):

```javascript
jQuery('#dt-tenants').on('click', '.btn-edit', function() {
    const tenantId = jQuery(this).data('id');
    // TODO: Implementar edición
    showNotification('Funcionalidad de edición en desarrollo', 'info');
});
```

Backend **ya existe**: `PATCH /api/public/v1/tenants/{id}/` (verificado en `apps/public/tenants/api/viewsets.py`, ClientViewSet hereda de ModelViewSet).

### 6.2 Diseño mínimo

- Reutilizar el mismo modal/offcanvas del formulario "Crear" (ya existe `#tenant-form` en la página `/console/tenants/`).
- Modo edición: precarga campos vía `GET /api/public/v1/tenants/{id}/`, cambia `submit` para hacer `PATCH` en vez de `POST`.
- Campos editables: `nombre`, `paid_until`, `on_trial`, `is_active`. **No** editar `schema_name` ni `domain` (rompería el tenant).

### 6.3 Patch a aplicar en `tenants_manager.js`

Reemplazar el handler entre líneas 436-440:

```javascript
jQuery('#dt-tenants').on('click', '.btn-edit', async function () {
    const tenantId = jQuery(this).data('id');
    if (!tenantId) return;
    try {
        const tenant = await window.http.get(`/api/public/v1/tenants/${tenantId}/`);
        openEditTenantModal(tenant);
    } catch (err) {
        showNotification(err.message || 'No se pudo cargar el tenant', 'error');
    }
});

function openEditTenantModal(tenant) {
    const form = document.getElementById('tenant-form');
    if (!form) {
        showNotification('Formulario de tenant no encontrado en la página', 'error');
        return;
    }

    // Precargar campos editables
    const setVal = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.value = value ?? '';
    };
    setVal('nombre', tenant.nombre);
    setVal('paid_until', tenant.paid_until || '');
    const onTrial = document.getElementById('on_trial');
    if (onTrial) onTrial.checked = !!tenant.on_trial;
    const isActive = document.getElementById('is_active');
    if (isActive) isActive.checked = !!tenant.is_active;

    // Bloquear inmutables
    ['schema_name', 'dominio_fqdn', 'owner_email'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) { el.value = id === 'schema_name' ? tenant.schema_name : (tenant[id] || ''); el.readOnly = true; el.disabled = true; }
    });

    form.dataset.mode = 'edit';
    form.dataset.tenantId = tenant.id;

    // Cambiar título y botón submit
    const title = document.querySelector('#tenant-modal-title, #tenant-form-title');
    if (title) title.textContent = `Editar tenant: ${tenant.nombre}`;
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = 'Guardar cambios';

    // Mostrar el modal/offcanvas existente
    const modalEl = document.getElementById('tenant-modal') || document.getElementById('tenant-offcanvas');
    if (modalEl) {
        const inst = bootstrap.Modal.getOrCreateInstance(modalEl) || bootstrap.Offcanvas.getOrCreateInstance(modalEl);
        inst.show();
    }
}
```

Y dentro del listener `submit` actual (cerca de [tenants_manager.js:518](apps/public/console/static/js/tenants_manager.js#L518)), bifurcar por `form.dataset.mode`:

```javascript
form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const mode = form.dataset.mode || 'create';
    const tenantId = form.dataset.tenantId;
    const payload = collectFormPayload(form);   // helper ya existente

    try {
        let result;
        if (mode === 'edit' && tenantId) {
            result = await window.http.patch(`/api/public/v1/tenants/${tenantId}/`, payload);
            showNotification(`Tenant "${result.nombre}" actualizado`, 'success');
        } else {
            result = await window.http.post('/api/public/v1/tenants/onboard/', payload);
            showNotification(`Tenant "${result.nombre}" creado`, 'success');
        }
        // Recargar DataTable
        const dt = jQuery('#dt-tenants').DataTable();
        if (dt) dt.ajax.reload(null, false);
        // Reset form
        form.reset();
        delete form.dataset.mode;
        delete form.dataset.tenantId;
    } catch (err) {
        showFormErrors(form, err);   // helper ya existente o definir si no
    }
});
```

> **Nota:** `tenants_manager.js` usa `window.http.get/patch/post` (forma objeto) — **no** la forma función — porque está en la **consola pública** y necesita el contrato pre-existente que lanza en errores.

### 6.4 Tests

- Crear tenant nuevo → debe seguir funcionando como antes.
- Editar tenant existente → cambiar `nombre`, `paid_until`, `on_trial` → guardar → refrescar tabla → cambios persistidos.
- Intentar editar `schema_name` → campo readonly, no enviado.

---

## 7. Fase 6 (Día 5) — Smoke tests E2E con Playwright

### 7.1 Setup mínimo (sin tocar `requirements.txt` Python)

```bash
# Desde la raíz del repo
mkdir -p tests/e2e
cd tests/e2e
npm init -y
npm install -D @playwright/test@^1.45
npx playwright install chromium
```

Crear `tests/e2e/playwright.config.js`:

```javascript
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './specs',
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://demo.sintel.com:8000',
    headless: true,
    ignoreHTTPSErrors: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});
```

### 7.2 `tests/e2e/specs/_helpers.js`

```javascript
const { expect } = require('@playwright/test');

async function login(page, { username, password }) {
  await page.goto('/login/');
  await page.fill('input[name="username"], #username, [data-test="username"]', username);
  await page.fill('input[name="password"], #password, [data-test="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|workspace|console)\/?/);
}

async function expectNoConsoleErrors(page, context = '') {
  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`[${context}] ${msg.text()}`);
  });
  page.on('pageerror', (err) => errors.push(`[${context}] ${err.message}`));
  return () => expect(errors, errors.join('\n')).toHaveLength(0);
}

module.exports = { login, expectNoConsoleErrors };
```

### 7.3 `tests/e2e/specs/00-http-loaded.spec.js`

```javascript
const { test, expect } = require('@playwright/test');
const { login } = require('./_helpers');

test('window.http está disponible como función con métodos', async ({ page }) => {
  await login(page, { username: process.env.E2E_USER, password: process.env.E2E_PASS });
  await page.goto('/dashboard/');
  const info = await page.evaluate(() => ({
    type: typeof window.http,
    version: window.http && window.http.__version__,
    hasGet: typeof window.http?.get,
    hasPost: typeof window.http?.post,
    hasPatch: typeof window.http?.patch,
    hasDelete: typeof window.http?.delete,
  }));
  expect(info.type).toBe('function');
  expect(info.version).toBe('3.4');
  expect(info.hasGet).toBe('function');
  expect(info.hasPost).toBe('function');
  expect(info.hasPatch).toBe('function');
  expect(info.hasDelete).toBe('function');
});
```

### 7.4 `tests/e2e/specs/10-clientes-crud.spec.js`

```javascript
const { test, expect } = require('@playwright/test');
const { login, expectNoConsoleErrors } = require('./_helpers');

test('Clientes: crear → editar → eliminar', async ({ page }) => {
  const checkErrors = await expectNoConsoleErrors(page, 'clientes');
  await login(page, { username: process.env.E2E_USER, password: process.env.E2E_PASS });

  await page.goto('/clientes/');
  await expect(page.locator('#tabla-clientes, [data-test="tabla-clientes"]').first()).toBeVisible();

  // Crear
  await page.click('button:has-text("Nuevo"), [data-test="btn-nuevo-cliente"]');
  const ts = Date.now();
  await page.selectOption('#cliente-tipo_persona, [name="tipo_persona"]', 'PJ');
  await page.selectOption('#cliente-tipo_documento, [name="tipo_documento"]', 'NIT');
  await page.fill('#cliente-numero_documento, [name="numero_documento"]', `9001${ts.toString().slice(-6)}`);
  await page.fill('#cliente-razon_social, [name="razon_social"]', `E2E Test ${ts}`);
  await page.selectOption('#cliente-regimen_tributario, [name="regimen_tributario"]', { index: 1 });
  await page.click('#btn-guardar-cliente, button:has-text("Guardar")');
  await expect(page.locator(`text=E2E Test ${ts}`)).toBeVisible({ timeout: 5000 });

  // Editar
  await page.locator(`tr:has-text("E2E Test ${ts}") .btn-edit, [data-test="edit-cliente"]`).first().click();
  await page.fill('#cliente-razon_social, [name="razon_social"]', `E2E Test ${ts} EDITED`);
  await page.click('#btn-guardar-cliente, button:has-text("Guardar")');
  await expect(page.locator(`text=E2E Test ${ts} EDITED`)).toBeVisible({ timeout: 5000 });

  // Eliminar
  page.once('dialog', (d) => d.accept());
  await page.locator(`tr:has-text("E2E Test ${ts} EDITED") .btn-delete, [data-test="delete-cliente"]`).first().click();
  await expect(page.locator(`text=E2E Test ${ts} EDITED`)).toBeHidden({ timeout: 5000 });

  checkErrors();
});
```

### 7.5 `tests/e2e/specs/20-inventario-productos-crud.spec.js`

Mismo patrón aplicado a Productos: ir a `/inventario/`, crear producto con SKU `E2E-${ts}`, editar nombre, eliminar.

### 7.6 `tests/e2e/specs/30-contabilidad-cuenta-crud.spec.js`

Mismo patrón aplicado a `/contabilidad/cuentas/`.

### 7.7 `tests/e2e/specs/40-tenant-edit.spec.js`

```javascript
const { test, expect } = require('@playwright/test');

test('Edit Tenant funciona desde la consola pública', async ({ page }) => {
  await page.goto(`${process.env.E2E_PUBLIC_URL || 'http://sintel.com:8000'}/console/tenants/`);
  // login admin público (ajustar según flujo real)
  await page.fill('[name="username"]', process.env.E2E_ADMIN_USER);
  await page.fill('[name="password"]', process.env.E2E_ADMIN_PASS);
  await page.click('button[type="submit"]');

  await page.waitForSelector('#dt-tenants');
  await page.locator('#dt-tenants tbody tr').first().locator('.btn-edit').click();
  await page.waitForSelector('#tenant-form[data-mode="edit"]');

  const newName = `Editado E2E ${Date.now()}`;
  await page.fill('#nombre', newName);
  await page.click('#tenant-form button[type="submit"]');

  await expect(page.locator(`#dt-tenants:has-text("${newName}")`)).toBeVisible({ timeout: 5000 });
});
```

### 7.8 Ejecución

```bash
cd tests/e2e
E2E_BASE_URL=http://demo.sintel.com:8000 \
E2E_USER=test_user \
E2E_PASS=test_pass \
E2E_PUBLIC_URL=http://sintel.com:8000 \
E2E_ADMIN_USER=admin \
E2E_ADMIN_PASS=admin_pass \
npx playwright test
```

### 7.9 Fixture de datos (recomendado)

Antes de correr la suite, asegurar tenants y usuarios de prueba:

```bash
python manage.py generar_tenants_prueba --cantidad 1
# crear usuario test del tenant via management command o admin
```

---

## 8. Checklist global de cierre

### Día 1
- [ ] Crear rama `fix/sprint1-desbloquear-crud`.
- [ ] Reescribir `apps/public/console/static/js/http.js` con el contrato dual.
- [ ] `python manage.py collectstatic --noinput`.
- [ ] DevTools en `/console/` y en `/dashboard/` → `window.http.__version__ === '3.4'`.
- [ ] Insertar `<script src="{% static 'js/http.js' %}">` en `apps/tenant/core/templates/tenant/base.html` después de `jwt-auth.js`.

### Días 2-3
- [ ] Verificar CRUD en cada uno de los 13 módulos de la tabla §4.14.
- [ ] Documentar en esa misma tabla los issues no resueltos por el desbloqueo (van a backlog Sprint 2).

### Día 4
- [ ] Añadir `showError/showSuccess/showInfo` globales a `ui-manager.js`.
- [ ] Implementar Edit Tenant (handler + branch en submit).
- [ ] Smoke manual en `/console/tenants/`: editar nombre, on_trial, paid_until.

### Día 5
- [ ] Setup Playwright en `tests/e2e/`.
- [ ] 5 specs: http loaded, clientes CRUD, inventario productos CRUD, contabilidad cuenta CRUD, edit tenant.
- [ ] `npx playwright test` pasa local.
- [ ] PR a `main` con descripción que cite este documento y la tabla §4.14 llenada.

---

## 9. Riesgos y plan de rollback

| Riesgo | Mitigación |
|---|---|
| `http.js` cargado dos veces (consola y tenant) ⇒ doble registro | Idempotencia: `httpFn` se reasigna pero el resultado es idéntico. Marcador `__version__` permite detectar |
| Algún `*.api.js` esperaba que `w.http` lance en error (no `{ok:false}`) | El grep mostró que **todos** los `*.api.js` de tenant siguen el patrón `if (response.ok) { ... } else { ... data ... }`. Revisión cruzada en Día 2. |
| Endpoint `/api/public/v1/tenants/{id}/` con PATCH no soporta `paid_until` o `on_trial` | Verificar con `python manage.py shell`: `from apps.public.tenants.models import Client; Client._meta.get_fields()`. Ajustar `editable_fields` si necesario. |
| Playwright no encuentra los selectores reales | Los selectores del spec usan fallbacks `, [data-test="..."]`. Si fallan, ajustar al markup real del módulo y, en Sprint 2, agregar `data-test` para estabilidad. |

### Rollback

```bash
git checkout main
git branch -D fix/sprint1-desbloquear-crud
python manage.py collectstatic --noinput
```

Como la única dependencia añadida (Playwright) vive en `tests/e2e/node_modules/`, eliminar la carpeta deja el repo idéntico al estado previo.

---

## 10. Lo que NO entra en este sprint (backlog Sprint 2)

- Consolidar las 3 ubicaciones duplicadas de `empresa.api.js`, `empleados.api.js`, `gastos.api.js`, `proveedores.api.js`.
- Unificar los 3 templates `offcanvas_crear/editar/detalle` por módulo en un único template parametrizado.
- Añadir `primary_domain` al `ClientSerializer` (ver auditoría previa).
- Validación cruzada FE↔BE de campos requeridos (hoy duplicada en JS y serializer).
- Debounce de 300 ms en búsqueda de Tabulator (`tabulator.factory.js`).
- Archivar 60+ markdowns históricos en `documentacion/_archive/` y publicar `FRONTEND.md` canónico.
- Hardening de seguridad pre-prod (SECRET_KEY ≥ 50 + assert, JWT refresh TTL 1-3 días, etc.).

---

**Final del documento.**
Cualquier desviación durante la ejecución debe registrarse en el PR como comentario y, si afecta a otros módulos, reflejarse en la tabla §4.14.


