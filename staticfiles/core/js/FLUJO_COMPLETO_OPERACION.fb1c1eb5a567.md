# Flujo Completo y Operación Actual - Core JS v2.37

**Ubicación:** `apps/tenant/core/static/core/js/`  
**Versión:** 2.37  
**Fecha:** 2024

---

## 📋 Tabla de Contenidos

1. [Estructura de Directorios](#estructura-de-directorios)
2. [Orden de Carga y Dependencias](#orden-de-carga-y-dependencias)
3. [Helpers Core - Librerías Base](#helpers-core---librerías-base)
4. [Helpers Core - Utilidades Transversales](#helpers-core---utilidades-transversales)
5. [Flujo de Inicialización de Módulos](#flujo-de-inicialización-de-módulos)
6. [Patrones Estándar por Tipo de Módulo](#patrones-estándar-por-tipo-de-módulo)
7. [Ejemplos de Uso Completo](#ejemplos-de-uso-completo)
8. [Mejores Prácticas](#mejores-prácticas)
9. [Troubleshooting](#troubleshooting)

---

## 1. Estructura de Directorios

```
apps/tenant/core/static/core/js/
├── lib/                          # Librerías base (cargadas primero)
│   ├── http.js                   # Cliente HTTP básico + getCookie
│   ├── api-helpers.js            # Helpers API (safeFetchJson, withTrailingSlash, etc.)
│   ├── dom-utils.js              # Utilidades DOM (isVisible, waitForVisible, awaitVisibleAny)
│   ├── datatables-utils.js       # Utilidades DataTables (initServerSide, safeDestroy)
│   ├── datatables-es.js          # Traducción DataTables ES
│   └── api.js                    # (Legacy, si existe)
│
├── helpers/                      # Helpers transversales (cargados después de lib/)
│   ├── routes.js                 # Descubrimiento de rutas API (HATEOAS)
│   ├── crud.js                   # Operaciones CRUD estándar
│   ├── module.js                 # Bootstrap estándar para módulos
│   └── README.md                 # Documentación de helpers
│
├── {modulo}/                     # Módulos por app (cargados después de helpers/)
│   ├── {modulo}.page.js          # Script principal del módulo
│   ├── {modulo}.api.js           # (Opcional) Lógica API específica
│   ├── {modulo}.ui.js            # (Opcional) Lógica UI específica
│   ├── {modulo}.modals.js        # (Opcional) Manejo de modales
│   └── {modulo}.dt.js            # (Legacy) Configuración DataTables
│
├── workspace.js                  # Navegación del workspace
├── router.js                     # Router de navegación (si existe)
└── tests/                        # Tests (UX Smoke Runner)
    └── workspace_ux_smoke.js
```

**Módulos actuales:**
- `clientes/` - Gestión de clientes
- `proveedores/` - Gestión de proveedores
- `empleados/` - Gestión de empleados
- `gastos/` - Gestión de gastos
- `facturas/` - Gestión de facturas
- `contabilidad/` - Contabilidad (cuentas, asientos)
- `inventario/` - Inventario (catálogo, activos, movimientos)
- `empresa/` - Configuración de empresa (singleton)
- `perfil/` - Perfil de usuario (singleton)
- `mailinbox/` - Configuración de buzones de correo
- `dashboard/` - Dashboard
- `landing/` - Landing page
- `mail/` - Gestión de correo

---

## 2. Orden de Carga y Dependencias

### 2.1 Orden Obligatorio de Carga

El orden de carga es **CRÍTICO** y está definido en `assets_core.html`:

```html
<!-- PASO 1: Librerías base (HTTP, DOM, DataTables) -->
<script src="{% static 'core/js/lib/http.js' %}"></script>
<script src="{% static 'core/js/lib/api-helpers.js' %}"></script>
<script src="{% static 'core/js/lib/dom-utils.js' %}"></script>
<script src="{% static 'core/js/lib/datatables-utils.js' %}"></script>

<!-- PASO 2: Helpers transversales -->
<script src="{% static 'core/js/helpers/routes.js' %}"></script>
<script src="{% static 'core/js/helpers/crud.js' %}"></script>
<script src="{% static 'core/js/helpers/module.js' %}"></script>

<!-- PASO 3: Shim de depuración -->
<script>
  window.__DEBUG__ = (typeof window.__DEBUG__ === 'boolean') ? window.__DEBUG__ : false;
  if (window.API_HELPERS) {
    window.API_HELPERS.DEBUG = window.__DEBUG__;
  }
</script>
```

### 2.2 Dependencias entre Helpers

```
http.js
  └─> (sin dependencias)
      └─> Expone: window.http, window.getCookie

api-helpers.js
  └─> Depende de: window (usa window.location)
      └─> Expone: window.API_HELPERS (idempotente, no muta read-only)

dom-utils.js
  └─> Depende de: window, document
      └─> Expone: window.DOMUtils (isVisible, waitForVisible, awaitVisibleAny, onVisibleOnce)

datatables-utils.js
  └─> Depende de: window.jQuery, window.DOMUtils, window.API_HELPERS
      └─> Expone: window.DataTablesUtils (initServerSide, safeDestroy, isDataTableInitialized)

routes.js
  └─> Depende de: window.API_HELPERS (o window.http)
      └─> Expone: window.Routes (get, collectionUrl, detailUrl, datatableUrl, singletonUrl)

crud.js
  └─> Depende de: window.Routes, window.API_HELPERS (o window.http)
      └─> Expone: window.CRUD (create, read, update, delete, readSingleton, updateSingleton)

module.js
  └─> Depende de: window.DOMUtils, window.Routes, window.DataTablesUtils
      └─> Expone: window.Module (init)
```

### 2.3 Carga en Partials de Apps

Cada app debe incluir `assets_core.html` **ANTES** de sus propios scripts:

```html
<!-- En apps/tenant/{app}/templates/tenant/{app}/partials/assets_{app}.html -->
{% load static %}

<!-- ⚠️ OBLIGATORIO: Core helpers primero -->
{% include 'tenant/core/partials/assets_core.html' %}

<!-- Scripts de la app -->
<script src="{% static 'tenant/{app}/js/{app}.api.js' %}"></script>
<script src="{% static 'tenant/{app}/js/{app}.page.js' %}"></script>
```

---

## 3. Helpers Core - Librerías Base

### 3.1 `lib/http.js`

**Propósito:** Cliente HTTP básico con manejo de CSRF y SessionAuth.

**API:**
```javascript
// Función principal
const result = await http('GET', '/api/v1/clientes/', undefined);
// Retorna: { ok: boolean, status: number, data: any }

// Helper de cookies
const csrf = getCookie('csrftoken');
```

**Características:**
- URLs siempre relativas (sin dominio absoluto)
- CSRF automático para métodos que modifican estado (POST, PUT, PATCH, DELETE)
- Manejo de 401 con redirección inteligente (módulos críticos vs no críticos)
- SessionAuth vía `credentials: 'same-origin'`

**Exporta:**
- `window.http` - Función HTTP principal
- `window.getCookie` - Helper de cookies

---

### 3.2 `lib/api-helpers.js`

**Propósito:** Helpers API unificados (construcción de URLs, CSRF, fetch seguro).

**API:**
```javascript
// Construcción de URLs
const url = API_HELPERS.withTrailingSlash('/api/v1/clientes');
const detailUrl = API_HELPERS.buildDetailUrl('/api/v1/clientes/', id);

// Fetch seguro con manejo de errores
const data = await API_HELPERS.safeFetchJson(url, {
  method: 'GET',
  headers: { ... }
});
// Retorna: body directamente (no {ok, status, data})

// CSRF
const csrf = API_HELPERS.getCSRF();
const headers = API_HELPERS.authHeaders();
```

**Características:**
- **Idempotente:** No muta propiedades read-only (`TRAILING_SLASH`)
- Manejo de errores 404, 422, 401 con excepciones descriptivas
- Normalización de datos (responsabilidades_rut_codigos)
- `DEBUG` sincronizado con `window.__DEBUG__`

**Exporta:**
- `window.API_HELPERS` - Objeto con todas las funciones (idempotente)

**Propiedades:**
- `TRAILING_SLASH` - Constante (read-only)
- `API_BASE` - Base URL de la API
- `withTrailingSlash(s)` - Normaliza trailing slash
- `buildDetailUrl(base, id)` - Construye URL de detalle
- `mapResponsabilidadesToCodes(items)` - Normaliza responsabilidades
- `getCSRF()` - Obtiene token CSRF
- `authHeaders()` - Headers con CSRF
- `safeFetchJson(url, options)` - Fetch seguro
- `DEBUG` - Flag de depuración

---

### 3.3 `lib/dom-utils.js`

**Propósito:** Utilidades DOM para verificación de elementos y visibilidad.

**API:**
```javascript
// Obtener elemento
const el = DOMUtils.getEl('#table-clientes');

// Verificar visibilidad
const visible = DOMUtils.isVisible(el);

// Esperar visibilidad (un selector)
const tableEl = await DOMUtils.waitForVisible('#table-clientes', {
  timeout: 10000,
  interval: 120
});

// Esperar visibilidad (cualquiera de varios selectores) - ⚠️ RECOMENDADO para tabs
const visibleEl = await DOMUtils.awaitVisibleAny([
  '#table-clientes',
  '#tab-clientes.active',
  '#pane-clientes.show',
  '#clientes-container',
  '#workspace .tab-pane.show'
], { timeout: 6000 });

// Ejecutar callback cuando elemento se vuelve visible
DOMUtils.onVisibleOnce('#table-clientes', (el) => {
  console.log('Tabla visible, inicializando...');
  initDataTable();
});
```

**Características:**
- `isVisible()` robusto: verifica `offsetParent`, `display`, `visibility`, `opacity`, dimensiones
- `awaitVisibleAny()` optimizado para tablas en tabs/accordions
- `onVisibleOnce()` escucha eventos Bootstrap (`shown.bs.tab`, `shown.bs.collapse`) y MutationObserver

**Exporta:**
- `window.DOMUtils` - Objeto con todas las funciones

---

### 3.4 `lib/datatables-utils.js`

**Propósito:** Utilidades para inicialización segura de DataTables server-side.

**API:**
```javascript
// Verificar si DataTable está inicializada
const isInit = DataTablesUtils.isDataTableInitialized('#table-clientes');

// Destruir DataTable de forma segura (evita parentNode null)
DataTablesUtils.safeDestroy('#table-clientes');

// Inicializar DataTable server-side (POST + CSRF automático)
const dtInstance = await DataTablesUtils.initServerSide({
  table: '#table-clientes',
  endpoint: '/api/v1/clientes/dt/clientes/',
  columns: COLUMNS,
  options: {
    order: [[2, 'desc']],
    pageLength: 25
  }
});
```

**Características:**
- **Visibilidad robusta:** Usa `awaitVisibleAny` para manejar tabs/accordions
- **Mismatch automático:** Ajusta columnas si hay discrepancia entre `<th>` y `columns`
- **Destrucción segura:** Verifica `parentNode` antes de destruir
- **POST obligatorio:** Fuerza `serverSide: true` y `ajax.type: 'POST'`
- **CSRF automático:** Incluye `X-CSRFToken` en headers

**Exporta:**
- `window.DataTablesUtils` - Objeto con todas las funciones

**Funciones:**
- `canUseDataTables()` - Verifica dependencias
- `isDataTableInitialized(selector)` - Verifica si está inicializada
- `safeDestroy(selector)` - Destruye de forma segura
- `initOrUpdateDataTable(tableEl, options)` - Inicializa o actualiza (client-side)
- `initServerSide(config)` - Inicializa server-side (POST + CSRF)

---

## 4. Helpers Core - Utilidades Transversales

### 4.1 `helpers/routes.js`

**Propósito:** Descubrimiento dinámico de rutas API desde el backend (HATEOAS).

**API:**
```javascript
// Obtener bloque de rutas del módulo
const routes = await Routes.get('facturas');
// Retorna: { collection, detail, datatable, singleton, ... }

// URLs específicas
const collectionUrl = await Routes.collectionUrl('facturas');
const detailUrl = await Routes.detailUrl('facturas', 123);
const datatableUrl = await Routes.datatableUrl('facturas');
const singletonUrl = await Routes.singletonUrl('empresa');

// Subclaves (módulos anidados)
const routes = await Routes.get('inventario.catalogo');
const routes = await Routes.get('contabilidad.asientos');

// Invalidar cache
Routes.invalidateCache();
```

**Características:**
- **Cache en sessionStorage:** TTL de 5 minutos
- **Fallback:** Si el endpoint no responde, retorna `{}` y permite construcción manual
- **Subclaves:** Soporta módulos anidados (`inventario.catalogo`, `contabilidad.asientos`)
- **Idempotente:** Puede llamarse múltiples veces sin problemas

**Flujo:**
1. Verifica cache en `sessionStorage`
2. Si expirado o no existe, hace `GET /api/v1/core/routes/`
3. Extrae bloque del módulo desde la respuesta
4. Guarda en cache con timestamp
5. Retorna bloque de rutas

**Exporta:**
- `window.Routes` - Objeto con todas las funciones

---

### 4.2 `helpers/crud.js`

**Propósito:** Operaciones CRUD estándar con CSRF y manejo de errores uniforme.

**API:**
```javascript
// Crear recurso
const result = await CRUD.create('clientes', {
  nombre: 'Cliente 1',
  nit: '123456789'
});
// Retorna: { ok: boolean, status: number, data: any }

// Leer recurso
const result = await CRUD.read('clientes', 123);

// Actualizar recurso (PATCH)
const result = await CRUD.update('clientes', 123, {
  nombre: 'Cliente Actualizado'
});

// Eliminar recurso
const result = await CRUD.delete('clientes', 123);

// Singleton: Leer
const result = await CRUD.readSingleton('empresa');

// Singleton: Actualizar
const result = await CRUD.updateSingleton('empresa', {
  razon_social: 'Nueva Razón Social'
});
```

**Características:**
- Usa `Routes` para descubrir URLs automáticamente
- Transport: `API_HELPERS.safeFetchJson` o `http.js` (fallback)
- Manejo uniforme de errores 4xx/5xx
- Retorna siempre `{ok, status, data}`

**Exporta:**
- `window.CRUD` - Objeto con todas las funciones

---

### 4.3 `helpers/module.js`

**Propósito:** Bootstrap estándar para inicialización de módulos.

**API:**
```javascript
const state = await Module.init({
  module: 'facturas',
  container: '#facturas-main',
  table: '#table-facturas',
  columns: COLUMNS,
  datatableOptions: {
    order: [[2, 'desc']],
    pageLength: 25
  },
  onInit: (state) => {
    console.log('Módulo inicializado:', state);
    // state.routes, state.dtInstance disponibles
  },
  onBindEvents: (state) => {
    // Bindear eventos personalizados
    document.getElementById('btn-refrescar').addEventListener('click', () => {
      state.dtInstance.ajax.reload();
    });
  }
});
```

**Flujo de inicialización:**
1. Espera visibilidad del contenedor (`DOMUtils.waitForVisible`)
2. Carga rutas del módulo (`Routes.get(module)`)
3. Inicializa DataTable si hay tabla y columnas (`DataTablesUtils.initServerSide`)
4. Ejecuta callback `onInit(state)`
5. Ejecuta callback `onBindEvents(state)`
6. Retorna `{ ok, module, container, routes, dtInstance }`

**Exporta:**
- `window.Module` - Objeto con función `init`

---

## 5. Flujo de Inicialización de Módulos

### 5.1 Flujo Estándar (usando Module.init)

```javascript
// En {modulo}.page.js
(function (w, d) {
  'use strict';

  const MOD = 'facturas';
  const TABLE_ID = '#table-facturas';
  const CONTAINER_ID = '#facturas-main';

  // Columnas DataTable
  const COLUMNS = [ /* ... */ ];

  // Estado del módulo
  let state = {
    initialized: false,
    table: null,
    routes: null
  };

  // Inicialización
  async function init() {
    if (state.initialized) return;

    const result = await Module.init({
      module: MOD,
      container: CONTAINER_ID,
      table: TABLE_ID,
      columns: COLUMNS,
      onInit: (state) => {
        // Callback después de inicialización
        state.table = state.dtInstance;
        state.routes = state.routes;
      },
      onBindEvents: (state) => {
        // Bindear eventos
        attachListeners(state);
      }
    });

    if (result.ok) {
      state.initialized = true;
    }
  }

  // Inicializar cuando DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
```

### 5.2 Flujo Manual (sin Module.init)

Algunos módulos no usan `Module.init` y hacen la inicialización manualmente:

```javascript
async function init() {
  // 1. Esperar visibilidad (usar awaitVisibleAny para tabs)
  await DOMUtils.awaitVisibleAny([
    TABLE_ID,
    '#tab-{modulo}.active',
    '#workspace .tab-pane.show'
  ], { timeout: 6000 });

  // 2. Cargar rutas
  if (Routes) {
    state.routes = await Routes.get(MOD);
  }

  // 3. Inicializar DataTable
  if (DataTablesUtils) {
    state.table = await DataTablesUtils.initServerSide({
      table: TABLE_ID,
      endpoint: state.routes?.datatable || '/api/v1/{modulo}/dt/',
      columns: COLUMNS
    });
  }

  // 4. Bindear eventos
  attachListeners();

  state.initialized = true;
}
```

### 5.3 Flujo para Tablas en Tabs/Accordions

**Problema:** Las tablas en tabs/accordions están ocultas inicialmente, causando timeouts.

**Solución:** Usar `awaitVisibleAny` con múltiples candidatos:

```javascript
// ❌ INCORRECTO (causa timeout)
await DOMUtils.waitForVisible('#table-inventario-catalogo', { timeout: 10000 });

// ✅ CORRECTO (maneja tabs/accordions)
await DOMUtils.awaitVisibleAny([
  '#table-inventario-catalogo',
  '#tab-inventario-catalogo.active',
  '#pane-inventario-catalogo.show',
  '#inventario-catalogo-container',
  '#workspace .tab-pane.show'
], { timeout: 6000 });
```

---

## 6. Patrones Estándar por Tipo de Módulo

### 6.1 Módulo con DataTable Server-Side (Colección)

**Ejemplo:** `facturas.page.js`, `clientes.page.js`

```javascript
// 1. Definir columnas
const COLUMNS = [
  { data: 'id', visible: false },
  { data: 'numero', title: 'Número' },
  { data: 'fecha', title: 'Fecha' },
  // ...
];

// 2. Inicializar con Module.init o manualmente
const state = await Module.init({
  module: 'facturas',
  container: '#facturas-main',
  table: '#table-facturas',
  columns: COLUMNS,
  onInit: (state) => {
    // Guardar instancia
    window.facturasDT = state.dtInstance;
  }
});

// 3. Operaciones CRUD
const result = await CRUD.create('facturas', payload);
if (result.ok) {
  state.dtInstance.ajax.reload();
}
```

### 6.2 Módulo Singleton (0 o 1 registro)

**Ejemplo:** `empresa.page.js`, `perfil.page.js`

```javascript
// 1. Leer singleton
const result = await CRUD.readSingleton('empresa');
if (result.ok) {
  renderEmpresaData(result.data);
}

// 2. Actualizar singleton
const result = await CRUD.updateSingleton('empresa', {
  razon_social: 'Nueva Razón Social'
});
```

### 6.3 Módulo con DataTable Client-Side

**Ejemplo:** `mailinbox.page.js`, `empresa.page.js` (lista)

```javascript
// 1. Cargar datos
const rows = await fetchMailInboxList();

// 2. Inicializar DataTable client-side
state.table = DataTablesUtils.initOrUpdateDataTable(tableEl, {
  data: rows,
  columns: COLUMNS,
  paging: true,
  searching: true
});
```

### 6.4 Módulo con Múltiples Tablas (Tabs)

**Ejemplo:** `contabilidad.page.js` (cuentas + asientos), `inventario.page.js` (catálogo + activos + movimientos)

```javascript
// Inicializar cada tabla cuando su tab se muestre
async function initDataTableCuentas() {
  await DOMUtils.awaitVisibleAny([
    '#table-contabilidad-cuentas',
    '#contabilidad-cuentas-pane.show',
    '#workspace .tab-pane.show'
  ], { timeout: 6000 });

  const dtInstance = await DataTablesUtils.initServerSide({
    table: '#table-contabilidad-cuentas',
    endpoint: await Routes.datatableUrl('contabilidad.cuentas'),
    columns: CUENTAS_COLUMNS
  });
}

// Usar onVisibleOnce para inicializar cuando el tab se muestra
DOMUtils.onVisibleOnce('#table-contabilidad-asientos', () => {
  initDataTableAsientos();
});
```

---

## 7. Ejemplos de Uso Completo

### 7.1 Ejemplo: Módulo Completo con CRUD

```javascript
/**
 * facturas.page.js - Módulo Facturas v2.37
 */
(function (w, d) {
  'use strict';

  const MOD = 'facturas';
  const TABLE_ID = '#table-facturas';
  const CONTAINER_ID = '#facturas-main';

  // Columnas DataTable
  const COLUMNS = [
    { data: 'id', visible: false },
    { data: 'numero', title: 'Número' },
    { data: 'fecha', title: 'Fecha' },
    { data: 'cliente', title: 'Cliente' },
    { data: 'total', title: 'Total' },
    {
      data: null,
      title: 'Acciones',
      orderable: false,
      render: (data, type, row) => {
        return `
          <button class="btn btn-sm btn-primary btn-editar" data-id="${row.id}">Editar</button>
          <button class="btn btn-sm btn-danger btn-eliminar" data-id="${row.id}">Eliminar</button>
        `;
      }
    }
  ];

  // Estado
  let state = {
    initialized: false,
    table: null,
    routes: null
  };

  // Logger seguro
  const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
  function log(...args) {
    if (DEBUG) console.debug(`[${MOD}.page]`, ...args);
  }

  // Bindear eventos
  function attachListeners() {
    // Botón Crear
    d.getElementById('btn-facturas-crear')?.addEventListener('click', async () => {
      const result = await CRUD.create(MOD, {
        numero: 'FAC-001',
        fecha: new Date().toISOString().split('T')[0],
        // ...
      });
      if (result.ok) {
        state.table.ajax.reload();
      }
    });

    // Botón Editar (delegación)
    d.addEventListener('click', async (ev) => {
      const btn = ev.target.closest('.btn-editar');
      if (btn) {
        const id = btn.dataset.id;
        const result = await CRUD.read(MOD, id);
        if (result.ok) {
          // Abrir modal de edición
          openEditModal(result.data);
        }
      }
    });

    // Botón Eliminar (delegación)
    d.addEventListener('click', async (ev) => {
      const btn = ev.target.closest('.btn-eliminar');
      if (btn) {
        const id = btn.dataset.id;
        if (confirm('¿Eliminar factura?')) {
          const result = await CRUD.delete(MOD, id);
          if (result.ok) {
            state.table.ajax.reload();
          }
        }
      }
    });
  }

  // Inicialización
  async function init() {
    if (state.initialized) return;

    log('Inicializando módulo Facturas...');

    const result = await Module.init({
      module: MOD,
      container: CONTAINER_ID,
      table: TABLE_ID,
      columns: COLUMNS,
      onInit: (state) => {
        state.table = state.dtInstance;
        state.routes = state.routes;
      },
      onBindEvents: (state) => {
        attachListeners();
      }
    });

    if (result.ok) {
      state.initialized = true;
      log('Módulo Facturas inicializado');
    }
  }

  // Inicializar cuando DOM esté listo
  if (typeof d !== 'undefined' && d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
```

### 7.2 Ejemplo: Módulo Singleton

```javascript
/**
 * empresa.page.js - Módulo Empresa v2.37 (Singleton)
 */
(async function() {
  'use strict';

  const MOD = 'empresa';

  // Leer datos de empresa
  const result = await CRUD.readSingleton(MOD);
  if (result.ok) {
    renderEmpresaData(result.data);
  }

  // Botón Guardar
  document.getElementById('btn-empresa-guardar')?.addEventListener('click', async () => {
    const payload = {
      razon_social: document.getElementById('empresa-razon_social').value,
      nit: document.getElementById('empresa-nit').value,
      // ...
    };

    const result = await CRUD.updateSingleton(MOD, payload);
    if (result.ok) {
      showFeedback('Empresa actualizada correctamente', 'success');
    }
  });
})();
```

### 7.3 Ejemplo: Módulo con Tabla en Tab

```javascript
/**
 * inventario/catalogo.page.js - Módulo Inventario Catálogo v2.37
 */
async function initDataTableCatalogo() {
  // ⚠️ IMPORTANTE: Usar awaitVisibleAny para tabs
  await DOMUtils.awaitVisibleAny([
    '#table-inventario-catalogo',
    '#tab-inventario-catalogo.active',
    '#pane-inventario-catalogo.show',
    '#inventario-catalogo-container',
    '#workspace .tab-pane.show'
  ], { timeout: 6000 });

  const tableEl = document.querySelector('#table-inventario-catalogo');
  if (!tableEl || !tableEl.parentNode) {
    console.warn('Tabla no disponible en DOM');
    return null;
  }

  // Verificar mismatch columnas
  const thCount = tableEl.querySelectorAll('thead tr th').length;
  let finalColumns = Array.from(COLUMNS);
  if (finalColumns.length !== thCount) {
    console.warn(`Mismatch: <th>(${thCount}) vs columns(${finalColumns.length})`);
    if (finalColumns.length > thCount) {
      finalColumns = finalColumns.slice(0, thCount);
    } else {
      while (finalColumns.length < thCount) {
        finalColumns.push({ data: null, defaultContent: '' });
      }
    }
  }

  // Inicializar DataTable
  const dtInstance = await DataTablesUtils.initServerSide({
    table: '#table-inventario-catalogo',
    endpoint: await Routes.datatableUrl('inventario.catalogo'),
    columns: finalColumns
  });

  return dtInstance;
}
```

---

## 8. Mejores Prácticas

### 8.1 Orden de Carga

✅ **CORRECTO:**
```html
{% include 'tenant/core/partials/assets_core.html' %}
<script src="{% static 'tenant/{app}/js/{app}.page.js' %}"></script>
```

❌ **INCORRECTO:**
```html
<script src="{% static 'tenant/{app}/js/{app}.page.js' %}"></script>
{% include 'tenant/core/partials/assets_core.html' %}
```

### 8.2 Visibilidad en Tabs

✅ **CORRECTO (awaitVisibleAny):**
```javascript
await DOMUtils.awaitVisibleAny([
  '#table-{modulo}',
  '#tab-{modulo}.active',
  '#pane-{modulo}.show',
  '#{modulo}-container',
  '#workspace .tab-pane.show'
], { timeout: 6000 });
```

❌ **INCORRECTO (waitForVisible):**
```javascript
await DOMUtils.waitForVisible('#table-{modulo}', { timeout: 10000 });
// Causa timeout si la tabla está en un tab oculto
```

### 8.3 Destrucción de DataTables

✅ **CORRECTO (safeDestroy):**
```javascript
DataTablesUtils.safeDestroy('#table-{modulo}');
```

❌ **INCORRECTO (destroy manual):**
```javascript
$('#table-{modulo}').DataTable().destroy();
// Puede fallar si el nodo no está en el DOM
```

### 8.4 Logger Seguro

✅ **CORRECTO:**
```javascript
const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
function log(...args) {
  if (DEBUG) console.debug(`[${MOD}.page]`, ...args);
}
```

❌ **INCORRECTO:**
```javascript
function log(...args) {
  if (w.__DEBUG__) console.debug(...args);
  // Puede fallar si __DEBUG__ no está definido
}
```

### 8.5 Manejo de Mismatch Columnas

✅ **CORRECTO:**
```javascript
let finalColumns = Array.from(columns);
if (finalColumns.length !== thCount) {
  console.warn(`Mismatch: <th>(${thCount}) vs columns(${finalColumns.length})`);
  if (finalColumns.length > thCount) {
    finalColumns = finalColumns.slice(0, thCount);
  } else {
    while (finalColumns.length < thCount) {
      finalColumns.push({ data: null, defaultContent: '' });
    }
  }
}
// Usar finalColumns en DataTable
```

❌ **INCORRECTO:**
```javascript
// Usar columns directamente sin verificar
DataTablesUtils.initServerSide({
  table: '#table-{modulo}',
  columns: columns  // Puede causar error si hay mismatch
});
```

### 8.6 Verificación de Helpers

✅ **CORRECTO:**
```javascript
if (w.API_HELPERS && typeof w.API_HELPERS.safeFetchJson === 'function') {
  const data = await w.API_HELPERS.safeFetchJson(url);
}
```

❌ **INCORRECTO:**
```javascript
const data = await w.API_HELPERS.safeFetchJson(url);
// Puede fallar si API_HELPERS no está cargado
```

---

## 9. Troubleshooting

### 9.1 Error: `Cannot read properties of undefined (reading 'API_HELPERS')`

**Causa:** `assets_core.html` no se cargó antes del script del módulo.

**Solución:**
1. Verificar que `{% include 'tenant/core/partials/assets_core.html' %}` esté **ANTES** de los scripts del módulo
2. Verificar que `api-helpers.js` esté en `assets_core.html`

### 9.2 Error: `Cannot read properties of null (reading 'parentNode')`

**Causa:** Intentando destruir DataTable cuando el nodo no está en el DOM.

**Solución:**
```javascript
// Usar safeDestroy
DataTablesUtils.safeDestroy('#table-{modulo}');

// O verificar antes de destruir
const tableEl = document.querySelector('#table-{modulo}');
if (tableEl && tableEl.parentNode) {
  $(tableEl).DataTable().destroy();
}
```

### 9.3 Error: `Timeout esperando visibilidad: #table-{modulo}`

**Causa:** La tabla está en un tab/accordion oculto.

**Solución:**
```javascript
// Usar awaitVisibleAny en lugar de waitForVisible
await DOMUtils.awaitVisibleAny([
  '#table-{modulo}',
  '#tab-{modulo}.active',
  '#workspace .tab-pane.show'
], { timeout: 6000 });
```

### 9.4 Error: `Mismatch entre <th> (7) y columnas (8)`

**Causa:** El número de `<th>` en el template no coincide con `columns.length`.

**Solución:**
1. **Temporal:** El helper ajusta automáticamente, pero deja un warning
2. **Definitivo:** Alinear el template (`<th>`) con el array `columns` en el JS

### 9.5 Error: `Cannot assign to read only property 'TRAILING_SLASH'`

**Causa:** `api-helpers.js` intenta mutar una propiedad read-only.

**Solución:** Ya corregido en v2.37 - `api-helpers.js` es idempotente y no muta propiedades read-only.

### 9.6 Error: `finalColumns is not defined`

**Causa:** Variable `finalColumns` no está definida antes de usarse.

**Solución:**
```javascript
// Definir finalColumns antes de usarlo
let finalColumns = Array.from(columns);
// ... ajustar si hay mismatch ...
// Usar finalColumns en DataTable
```

---

## 10. Checklist de Migración

Al migrar un módulo a v2.37, verificar:

- [ ] `assets_core.html` incluido **ANTES** de scripts del módulo
- [ ] URLs hardcodeadas reemplazadas por `Routes.collectionUrl()`, `Routes.detailUrl()`, etc.
- [ ] `getCookie('csrftoken')` reemplazado por `API_HELPERS.getCSRF()` o `API_HELPERS.safeFetchJson()`
- [ ] `setTimeout` para visibilidad reemplazado por `DOMUtils.waitForVisible()` o `DOMUtils.awaitVisibleAny()`
- [ ] DataTables inicializadas con `DataTablesUtils.initServerSide()` (POST + CSRF automático)
- [ ] Logger seguro: `const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true)`
- [ ] Verificación de `parentNode` antes de destruir DataTables
- [ ] Manejo de mismatch columnas si aplica
- [ ] `awaitVisibleAny` para tablas en tabs/accordions

---

## 11. Referencias

- **Documentación Helpers:** `apps/tenant/core/static/core/js/helpers/README.md`
- **Arquitectura General:** `documentacion/arquitectura_general.md`
- **Resumen Operativo:** `documentacion/RESUMEN_OPERATIVO_FRONTEND.md`
- **Plan de Refactor:** `PLAN_REFACTOR_JS_SINTEL.md`

---

**Última actualización:** 2024  
**Versión:** 2.37  
**Mantenedor:** Equipo SINTEL
