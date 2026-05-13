# 🔧 PLAN DE REFACTOR: Centralización JS - SINTEL v2.37

**Fecha:** 2026-01-29  
**Versión:** v2.37  
**Basado en:** `INFORME_CENTRALIZACION_JS_SINTEL.md`

---

## 📋 Resumen

Este plan detalla los cambios necesarios para centralizar y modularizar el código JavaScript de CRUD (DataTables + POST + CSRF + inicialización) conforme a la arquitectura SINTEL v2.37.

---

## 🎯 Objetivos

1. Eliminar duplicación de código en construcción de URLs, CSRF, y esperas de visibilidad
2. Centralizar descubrimiento de rutas mediante endpoint `GET /api/v1/core/routes/`
3. Unificar inicialización de DataTables server-side POST
4. Reducir `*.page.js` a bootstrap mínimo usando helpers centralizados

---

## 📦 Archivos a Crear/Modificar

### A. Helpers Centralizados (NUEVOS)

#### 1. `apps/tenant/core/static/core/js/helpers/routes.js` ❌ **CREAR**

**Propósito:** Descubrimiento centralizado de rutas API desde endpoint backend.

**Código:**
```javascript
/**
 * Routes Helper - Descubrimiento centralizado de rutas API
 * 
 * ⚠️ v2.37: API-First - Todas las rutas se descubren desde backend
 * - Cache en sessionStorage para evitar requests repetidos
 * - Fallback a construcción manual si endpoint no disponible
 * - URLs siempre relativas (sin dominio)
 */

(function (w) {
  'use strict';

  const CACHE_KEY = 'sintel_routes_cache';
  const CACHE_TTL = 5 * 60 * 1000; // 5 minutos
  const ROUTES_ENDPOINT = '/api/v1/core/routes/';

  let routesCache = null;
  let cacheTimestamp = null;

  /**
   * Obtener rutas desde endpoint o cache
   * @returns {Promise<Object>} Mapa de rutas por módulo
   */
  async function fetchRoutes() {
    // Verificar cache
    if (routesCache && cacheTimestamp) {
      const age = Date.now() - cacheTimestamp;
      if (age < CACHE_TTL) {
        return routesCache;
      }
    }

    // Intentar desde sessionStorage
    try {
      const cached = sessionStorage.getItem(CACHE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached);
        if (parsed.timestamp && (Date.now() - parsed.timestamp < CACHE_TTL)) {
          routesCache = parsed.routes;
          cacheTimestamp = parsed.timestamp;
          return routesCache;
        }
      }
    } catch (e) {
      // Ignorar errores de sessionStorage
    }

    // Fetch desde endpoint
    try {
      const res = await fetch(ROUTES_ENDPOINT, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (res.ok) {
        const routes = await res.json();
        routesCache = routes;
        cacheTimestamp = Date.now();

        // Guardar en sessionStorage
        try {
          sessionStorage.setItem(CACHE_KEY, JSON.stringify({
            routes,
            timestamp: cacheTimestamp
          }));
        } catch (e) {
          // Ignorar errores de sessionStorage
        }

        return routes;
      }
    } catch (e) {
      console.warn('[routes] Error obteniendo rutas desde endpoint:', e);
    }

    // Fallback: retornar objeto vacío (módulos construirán URLs manualmente)
    return {};
  }

  /**
   * Obtener rutas de un módulo específico
   * @param {string} module - Nombre del módulo (ej: 'clientes', 'facturas')
   * @returns {Promise<Object>} Rutas del módulo o null si no existe
   */
  async function get(module) {
    const routes = await fetchRoutes();
    return routes[module] || null;
  }

  /**
   * Construir URL de detalle de forma segura
   * @param {string} module - Nombre del módulo
   * @param {string|number} id - ID del recurso
   * @returns {Promise<string>} URL de detalle
   */
  async function detailUrl(module, id) {
    const modRoutes = await get(module);
    if (modRoutes && modRoutes.detail) {
      return modRoutes.detail.replace('{id}', String(id));
    }
    // Fallback: construcción manual
    return `/api/v1/${module}/${id}/`;
  }

  /**
   * Obtener URL de DataTable para un módulo
   * @param {string} module - Nombre del módulo
   * @returns {Promise<string>} URL de DataTable o null
   */
  async function datatableUrl(module) {
    const modRoutes = await get(module);
    return modRoutes?.datatable || null;
  }

  /**
   * Obtener URL de colección para un módulo
   * @param {string} module - Nombre del módulo
   * @returns {Promise<string>} URL de colección o null
   */
  async function collectionUrl(module) {
    const modRoutes = await get(module);
    return modRoutes?.collection || null;
  }

  /**
   * Invalidar cache (útil después de cambios en backend)
   */
  function invalidateCache() {
    routesCache = null;
    cacheTimestamp = null;
    try {
      sessionStorage.removeItem(CACHE_KEY);
    } catch (e) {
      // Ignorar errores
    }
  }

  w.Routes = Object.freeze({
    get,
    detailUrl,
    datatableUrl,
    collectionUrl,
    invalidateCache
  });
})(window);
```

---

#### 2. `apps/tenant/core/static/core/js/helpers/crud.js` ❌ **CREAR**

**Propósito:** Helpers estándar para operaciones CRUD.

**Código:**
```javascript
/**
 * CRUD Helper - Operaciones CRUD estándar
 * 
 * ⚠️ v2.37: API-First - Todas las operaciones CRUD usan este helper
 * - Manejo automático de errores 404/422/401
 * - CSRF automático vía API_HELPERS
 * - URLs desde Routes helper
 */

(function (w) {
  'use strict';

  /**
   * Crear recurso
   * @param {string} module - Nombre del módulo
   * @param {Object} data - Datos del recurso
   * @returns {Promise<Object>} Recurso creado
   */
  async function create(module, data) {
    const collectionUrl = await w.Routes.collectionUrl(module);
    if (!collectionUrl) {
      throw new Error(`No se pudo obtener URL de colección para módulo: ${module}`);
    }

    return await w.API_HELPERS.safeFetchJson(collectionUrl, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  /**
   * Leer recurso
   * @param {string} module - Nombre del módulo
   * @param {string|number} id - ID del recurso
   * @returns {Promise<Object>} Recurso
   */
  async function read(module, id) {
    const detailUrl = await w.Routes.detailUrl(module, id);
    return await w.API_HELPERS.safeFetchJson(detailUrl, {
      method: 'GET'
    });
  }

  /**
   * Actualizar recurso (PATCH parcial)
   * @param {string} module - Nombre del módulo
   * @param {string|number} id - ID del recurso
   * @param {Object} data - Datos a actualizar
   * @returns {Promise<Object>} Recurso actualizado
   */
  async function update(module, id, data) {
    const detailUrl = await w.Routes.detailUrl(module, id);
    return await w.API_HELPERS.safeFetchJson(detailUrl, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  /**
   * Eliminar recurso
   * @param {string} module - Nombre del módulo
   * @param {string|number} id - ID del recurso
   * @returns {Promise<void>}
   */
  async function del(module, id) {
    const detailUrl = await w.Routes.detailUrl(module, id);
    return await w.API_HELPERS.safeFetchJson(detailUrl, {
      method: 'DELETE'
    });
  }

  w.CRUD = Object.freeze({
    create,
    read,
    update,
    delete: del
  });
})(window);
```

---

#### 3. `apps/tenant/core/static/core/js/helpers/datatable.js` ⚠️ **MEJORAR**

**Archivo Existente:** `apps/tenant/core/static/core/js/lib/datatables-utils.js`

**Mejoras Necesarias:**
```javascript
/**
 * DataTable Helper - Inicialización estándar server-side POST
 * 
 * ⚠️ v2.37: Todas las DataTables server-side usan este helper
 */

(function (w) {
  'use strict';

  // ... código existente ...

  /**
   * Inicializar DataTable server-side POST estándar
   * @param {Object} config - Configuración
   * @param {string} config.table - Selector de tabla (ej: '#table-clientes')
   * @param {string} config.endpoint - URL del endpoint DataTable
   * @param {Array} config.columns - Definición de columnas
   * @param {Object} config.options - Opciones adicionales (order, pageLength, etc.)
   * @returns {Promise<DataTable>} Instancia de DataTable
   */
  async function initServerSide({ table, endpoint, columns, options = {} }) {
    if (!canUseDataTables()) {
      throw new Error('jQuery/DataTables no disponibles');
    }

    const $ = w.jQuery;
    const $table = $(table);

    if (!$table.length) {
      throw new Error(`Tabla ${table} no encontrada`);
    }

    // Esperar visibilidad
    if (w.DOMUtils && w.DOMUtils.waitForVisible) {
      await w.DOMUtils.waitForVisible(table, { timeout: 5000 });
    }

    // Verificar estructura
    if (!$table.find('thead').length || !$table.find('thead tr th').length) {
      throw new Error(`Tabla ${table} no tiene estructura correcta (thead/tr/th)`);
    }

    // Obtener CSRF
    const csrf = w.API_HELPERS?.getCSRF() || '';
    if (!csrf) {
      console.warn('[datatable] CSRF token no encontrado');
    }

    // Configuración estándar
    const defaults = {
      processing: true,
      serverSide: true,
      autoWidth: false,
      searching: false,
      ordering: true,
      lengthChange: true,
      pageLength: 10,
      language: w.DATATABLES_ES_CONFIG || {
        url: 'https://cdn.datatables.net/plug-ins/1.13.8/i18n/es-ES.json'
      },
      ajax: {
        url: endpoint,
        type: 'POST',
        headers: {
          'X-CSRFToken': csrf
        },
        data: function (d) {
          // Añadir búsqueda desde toolbar si existe
          const searchInput = document.querySelector(`#txt-buscar-${table.replace('#table-', '')}`);
          if (searchInput) {
            d.search = { value: searchInput.value || '' };
          }
          return d;
        },
        error: function (xhr, error, thrown) {
          console.error('[datatable] Error en ajax:', error, thrown);
          const feedback = document.getElementById(`feedback-${table.replace('#table-', '')}-list`);
          if (feedback) {
            feedback.className = 'alert alert-danger';
            feedback.textContent = `Error cargando datos: ${error || 'Error desconocido'}`;
            feedback.classList.remove('d-none');
          }
        }
      },
      columns: columns,
      order: options.order || [[0, 'asc']]
    };

    // Merge con opciones personalizadas
    const config = { ...defaults, ...options };
    if (options.ajax) {
      config.ajax = { ...defaults.ajax, ...options.ajax };
    }

    // Inicializar
    try {
      return $table.DataTable(config);
    } catch (err) {
      console.error('[datatable] Error inicializando:', err);
      throw err;
    }
  }

  // Exportar función nueva
  w.DataTablesUtils = Object.freeze({
    ...w.DataTablesUtils, // Mantener funciones existentes
    initServerSide
  });
})(window);
```

---

#### 4. `apps/tenant/core/static/core/js/helpers/module.js` ❌ **CREAR**

**Propósito:** Bootstrap estándar para módulos.

**Código:**
```javascript
/**
 * Module Helper - Bootstrap estándar para módulos
 * 
 * ⚠️ v2.37: Todos los módulos usan este helper para inicialización
 * - Espera de visibilidad
 * - Descubrimiento de rutas
 * - Inicialización de DataTables (si aplica)
 * - Bind de eventos
 */

(function (w) {
  'use strict';

  /**
   * Inicializar módulo estándar
   * @param {Object} config - Configuración del módulo
   * @param {string} config.module - Nombre del módulo (ej: 'clientes')
   * @param {string} config.table - Selector de tabla (opcional)
   * @param {Array} config.columns - Columnas DataTable (opcional)
   * @param {Function} config.onInit - Callback después de inicialización
   * @param {Function} config.onBindEvents - Callback para bind de eventos
   * @returns {Promise<void>}
   */
  async function init(config) {
    const { module, table, columns, onInit, onBindEvents } = config;

    console.debug(`[${module}] Inicializando módulo...`);

    try {
      // 1. Esperar visibilidad del contenedor principal
      const containerSelector = `#${module}-container, #${module}-info-container, #table-${module}`;
      if (w.DOMUtils && w.DOMUtils.waitForVisible) {
        try {
          await w.DOMUtils.waitForVisible(containerSelector, { timeout: 5000 });
        } catch (err) {
          console.warn(`[${module}] Contenedor no visible, continuando...`);
        }
      }

      // 2. Descubrir rutas (si Routes está disponible)
      let routes = null;
      if (w.Routes) {
        try {
          routes = await w.Routes.get(module);
          if (routes) {
            console.debug(`[${module}] Rutas descubiertas:`, routes);
          }
        } catch (err) {
          console.warn(`[${module}] Error descubriendo rutas:`, err);
        }
      }

      // 3. Inicializar DataTable (si aplica)
      let dtInstance = null;
      if (table && columns && w.DataTablesUtils && w.DataTablesUtils.initServerSide) {
        try {
          const endpoint = routes?.datatable || `/api/v1/${module}/dt/`;
          dtInstance = await w.DataTablesUtils.initServerSide({
            table,
            endpoint,
            columns
          });
          console.debug(`[${module}] DataTable inicializada`);
        } catch (err) {
          console.error(`[${module}] Error inicializando DataTable:`, err);
        }
      }

      // 4. Callback de inicialización personalizada
      if (onInit) {
        await onInit({ routes, dtInstance });
      }

      // 5. Bind de eventos
      if (onBindEvents) {
        onBindEvents({ routes, dtInstance });
      }

      console.debug(`[${module}] Módulo inicializado correctamente`);
    } catch (err) {
      console.error(`[${module}] Error inicializando módulo:`, err);
      throw err;
    }
  }

  w.Module = Object.freeze({
    init
  });
})(window);
```

---

### B. Backend: Endpoint de Rutas

#### 1. Vista: `apps/tenant/core/api/views.py` ⚠️ **AGREGAR**

**Código:**
```python
class CoreRoutesView(APIView):
    """
    Endpoint centralizado de rutas API para descubrimiento dinámico.
    
    GET /api/v1/core/routes/
    
    Retorna un mapa canónico de rutas por módulo:
    {
      "clientes": {
        "collection": "/api/v1/clientes/",
        "detail": "/api/v1/clientes/{id}/",
        "datatable": "/api/v1/clientes/dt/"
      },
      "facturas": {
        "collection": "/api/v1/facturas/",
        "detail": "/api/v1/facturas/{id}/",
        "datatable": "/api/v1/facturas/dt/"
      },
      ...
    }
    
    ⚠️ POLÍTICA:
    - URLs siempre relativas (sin dominio)
    - Centralizado en Core API para fácil mantenimiento
    - Cache en frontend (sessionStorage) para evitar requests repetidos
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    
    def get(self, request):
        """
        Retorna el mapa de rutas para todas las TENANT_APPS.
        """
        routes = {
            "clientes": {
                "collection": "/api/v1/clientes/",
                "detail": "/api/v1/clientes/{id}/",
                "datatable": "/api/v1/clientes/dt/" if self._has_datatable_endpoint('clientes') else None
            },
            "proveedores": {
                "collection": "/api/v1/proveedores/",
                "detail": "/api/v1/proveedores/{id}/",
                "datatable": "/api/v1/proveedores/dt/" if self._has_datatable_endpoint('proveedores') else None
            },
            "gastos": {
                "collection": "/api/v1/gastos/",
                "detail": "/api/v1/gastos/{id}/",
                "datatable": "/api/v1/gastos/dt/" if self._has_datatable_endpoint('gastos') else None
            },
            "empleados": {
                "collection": "/api/v1/empleados/",
                "detail": "/api/v1/empleados/{id}/",
                "datatable": "/api/v1/empleados/dt/" if self._has_datatable_endpoint('empleados') else None
            },
            "facturas": {
                "collection": "/api/v1/facturas/",
                "detail": "/api/v1/facturas/{id}/",
                "datatable": "/api/v1/facturas/dt/"
            },
            "contabilidad": {
                "cuentas": {
                    "collection": "/api/v1/cuentas-contables/",
                    "detail": "/api/v1/cuentas-contables/{id}/",
                    "datatable": "/api/v1/dt/cuentas-contables/"
                },
                "asientos": {
                    "collection": "/api/v1/asientos-contables/",
                    "detail": "/api/v1/asientos-contables/{id}/",
                    "datatable": "/api/v1/dt/asientos-contables/"
                }
            },
            "inventario": {
                "catalogo": {
                    "collection": "/api/v1/inventario/catalogo-items/",
                    "detail": "/api/v1/inventario/catalogo-items/{id}/",
                    "datatable": "/api/v1/inventario/catalogo-items/dt/"
                },
                "activos": {
                    "collection": "/api/v1/inventario/activos-fijos/",
                    "detail": "/api/v1/inventario/activos-fijos/{id}/",
                    "datatable": "/api/v1/inventario/activos-fijos/dt/"
                }
            },
            "empresa": {
                "collection": "/api/v1/empresas/",
                "detail": "/api/v1/empresas/{id}/",
                "singleton": "/api/v1/core/empresa/"  # Endpoint singleton
            },
            "perfil": {
                "singleton": "/api/v1/perfil/perfiles/me/"
            }
        }
        
        return Response(routes, status=status.HTTP_200_OK)
    
    def _has_datatable_endpoint(self, module):
        """
        Verificar si un módulo tiene endpoint DataTable.
        TODO: Implementar verificación dinámica desde routers
        """
        # Por ahora, retornar True para módulos conocidos
        return module in ['clientes', 'proveedores', 'gastos', 'empleados', 'facturas']
```

#### 2. URL: `apps/tenant/core/api/urls.py` ⚠️ **AGREGAR**

**Código:**
```python
from apps.tenant.core.api.views import CoreRoutesView

urlpatterns = [
    # ... rutas existentes ...
    
    # Endpoint centralizado de rutas
    path('routes/', CoreRoutesView.as_view(), name='core-routes'),
]
```

#### 3. Registrar en Router: `config/api_urls.py` ✅ **YA ESTÁ** (Core API ya registrado)

---

### C. Migración de Módulos

#### Prioridad 1: Módulos con DataTables Server-Side

##### 1. `facturas.page.js`

**Archivo:** `apps/tenant/core/static/core/js/facturas/facturas.page.js`

**Cambios:**
```diff
--- a/apps/tenant/core/static/core/js/facturas/facturas.page.js
+++ b/apps/tenant/core/static/core/js/facturas/facturas.page.js
@@ -14,9 +14,6 @@
   const MOD = 'facturas';
-  const API_DT = `/api/v1/${MOD}/dt/`; // Endpoint DataTables
-  const API_BASE = `/api/v1/${MOD}/`;
   
   // Helper para obtener CSRF token
-  function getCookie(name) {
-    let cookieValue = null;
-    if (document.cookie && document.cookie !== '') {
-      const cookies = document.cookie.split(';');
-      for (let i = 0; i < cookies.length; i++) {
-        const cookie = cookies[i].trim();
-        if (cookie.substring(0, name.length + 1) === (name + '=')) {
-          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
-          break;
-        }
-      }
-    }
-    return cookieValue;
-  }
-
-  const CSRF = getCookie('csrftoken');
+  // ⚠️ Usar API_HELPERS.getCSRF() en lugar de getCookie local
   
   // Columnas según LIST_FIELDS del service
@@ -116,50 +113,20 @@
   /**
    * Inicializa DataTable para Facturas
    */
-  function initDataTable() {
+  async function initDataTable() {
     // Verificar que jQuery y DataTables estén disponibles
     if (typeof $ === 'undefined' || !$.fn || !$.fn.DataTable) {
       console.error(`[${MOD}.page] jQuery/DataTables no están disponibles`);
       return;
     }
 
-    const tableId = `#table-${MOD}`;
-    const $table = $(tableId);
+    // Descubrir ruta DataTable
+    const routes = await window.Routes.get(MOD);
+    const endpoint = routes?.datatable || `/api/v1/${MOD}/dt/`;
     
-    if (!$table.length) {
-      console.warn(`[${MOD}.page] Tabla ${tableId} no encontrada`);
-      return;
-    }
-
-    // ... verificaciones de estructura ...
-
-    // Inicializar DataTable con server-side POST (con try-catch para capturar errores)
-    try {
-      dtInstance = $table.DataTable({
-      processing: true,
-      serverSide: true,
-      autoWidth: false,
-      searching: false,
-      ordering: true,
-      lengthChange: true,
-      pageLength: 10,
-      language: window.DATATABLES_ES_CONFIG || {
-        url: 'https://cdn.datatables.net/plug-ins/1.13.8/i18n/es-ES.json',
-      },
-      ajax: {
-        url: API_DT,
-        type: 'POST', // OBLIGATORIO v2.37
-        headers: { 
-          'X-CSRFToken': CSRF 
-        },
+    // Usar helper centralizado
+    try {
+      dtInstance = await window.DataTablesUtils.initServerSide({
+        table: `#table-${MOD}`,
+        endpoint: endpoint,
+        columns: COLUMNS,
+        options: {
+          order: [[2, 'desc']]
+        }
+      });
     } catch (error) {
       console.error(`[${MOD}.page] Error al inicializar DataTable:`, error);
-      // ... manejo de errores ...
+      throw error;
     }
   }
```

---

##### 2. `contabilidad.page.js`

**Archivo:** `apps/tenant/core/static/core/js/contabilidad/contabilidad.page.js`

**Cambios:**
```diff
--- a/apps/tenant/core/static/core/js/contabilidad/contabilidad.page.js
+++ b/apps/tenant/core/static/core/js/contabilidad/contabilidad.page.js
@@ -30,8 +30,6 @@
   const CSRF = getCookie('csrftoken');
-  // ⚠️ IMPORTANTE: Contabilidad está en path('', ...) en config/api_urls.py
-  // Las rutas están directamente en /api/v1/ sin prefijo "contabilidad"
-  const API_BASE = '/api/v1/';
+  // ⚠️ Usar Routes.get('contabilidad') para descubrir rutas
 
   const MOD = 'contabilidad';
   let dtInstanceCuentas = null;
@@ -42,50 +40,20 @@
   /**
    * Inicializa DataTable para Cuentas Contables
    */
-  function initDataTableCuentas() {
-    // ... verificaciones ...
+  async function initDataTableCuentas() {
+    const routes = await window.Routes.get('contabilidad');
+    const cuentasRoutes = routes?.cuentas;
+    const endpoint = cuentasRoutes?.datatable || '/api/v1/dt/cuentas-contables/';
     
-    // Inicializar DataTable con server-side POST
-    try {
-      dtInstanceCuentas = $table.DataTable({
-        processing: true,
-        serverSide: true,
-        // ... configuración ...
-        ajax: {
-          url: `${API_BASE}dt/cuentas-contables/`,
-          type: 'POST',
-          headers: { 'X-CSRFToken': CSRF },
-          // ...
-        },
-        // ...
-      });
+    try {
+      dtInstanceCuentas = await window.DataTablesUtils.initServerSide({
+        table: '#table-contabilidad-cuentas',
+        endpoint: endpoint,
+        columns: COLUMNS_CUENTAS,
+        options: {
+          order: [[1, 'asc']]
+        }
+      });
     } catch (error) {
-      // ... manejo de errores ...
+      throw error;
     }
   }
   
   // Similar para initDataTableAsientos()
```

---

#### Prioridad 2: Módulos con DataTables Client-Side

##### 3. `clientes.page.js` (Ya usa helpers parcialmente)

**Archivo:** `apps/tenant/core/static/core/js/clientes/clientes.page.js`

**Cambios Mínimos:**
```diff
--- a/apps/tenant/core/static/core/js/clientes/clientes.page.js
+++ b/apps/tenant/core/static/core/js/clientes/clientes.page.js
@@ -19,7 +19,6 @@
   const NS = '[clientes.page]';
   const MOD = 'clientes';
-  const API_INDEX = `${w.API_HELPERS?.API_BASE || '/api/v1'}${MOD}/`;
+  // ⚠️ Usar Routes.collectionUrl(MOD) en lugar de construcción manual
   const TABLE_ID = '#table-clientes';
   
   /**
    * Descubrir URL de colección desde el índice HATEOAS
    */
   async function discoverCollectionUrl() {
-    if (state.urls.collection) {
-      return state.urls.collection;
-    }
-    
-    log('Descubriendo URL de colección desde índice:', API_INDEX);
-    
-    try {
-      const idxPayload = await w.API_HELPERS.safeFetchJson(API_INDEX, {
-        method: 'GET'
-      });
-      
-      // Caso A: índice HATEOAS -> extraer URL de colección
-      if (idxPayload && typeof idxPayload === 'object' && idxPayload.clientes) {
-        state.urls.collection = w.API_HELPERS.withTrailingSlash(idxPayload.clientes);
-        log('CLIENTE_COLLECTION_URL descubierta:', state.urls.collection);
-        return state.urls.collection;
-      }
-      
-      // Caso B: ya es colección (array o objeto con results)
-      state.urls.collection = w.API_HELPERS.withTrailingSlash(API_INDEX);
-      log('CLIENTE_COLLECTION_URL (índice = colección):', state.urls.collection);
-      return state.urls.collection;
-    } catch (err) {
-      error('Error descubriendo URL de colección:', err);
-      // Fallback: usar el índice como colección
-      state.urls.collection = w.API_HELPERS.withTrailingSlash(API_INDEX);
-      return state.urls.collection;
-    }
+    // ⚠️ Usar Routes.collectionUrl(MOD) directamente
+    const url = await w.Routes.collectionUrl(MOD);
+    state.urls.collection = url || `${w.API_HELPERS.API_BASE}${MOD}/`;
+    return state.urls.collection;
   }
```

---

#### Prioridad 3: Módulos Singleton

##### 4. `empresa.page.js` (Ya usa helpers)

**Cambios Mínimos:**
- Reemplazar construcción manual de URLs por `Routes.detailUrl('empresa', id)`
- Ya usa `API_HELPERS.safeFetchJson()` ✅

---

### D. Actualizar Partials HTML

#### Ejemplo: `assets_facturas.html`

**Antes:**
```html
{% load static %}
<script src="{% static 'core/js/lib/http.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.api.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.components.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.table.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.modals.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.page.js' %}"></script>
```

**Después:**
```html
{% load static %}
<!-- Helpers centralizados (cargar primero) -->
<script src="{% static 'core/js/lib/api-helpers.js' %}"></script>
<script src="{% static 'core/js/lib/dom-utils.js' %}"></script>
<script src="{% static 'core/js/lib/datatables-utils.js' %}"></script>
<script src="{% static 'core/js/helpers/routes.js' %}"></script>
<script src="{% static 'core/js/helpers/crud.js' %}"></script>
<script src="{% static 'core/js/helpers/module.js' %}"></script>

<!-- Módulo específico -->
<script src="{% static 'core/js/facturas/facturas.api.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.components.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.modals.js' %}"></script>
<script src="{% static 'core/js/facturas/facturas.page.js' %}"></script>
```

---

## 📝 Checklist de Migración por Módulo

### Para cada `*.page.js`:

- [ ] Reemplazar `getCookie('csrftoken')` por `API_HELPERS.getCSRF()`
- [ ] Reemplazar construcción manual de URLs por `Routes.get(module)`
- [ ] Reemplazar inicialización DataTables manual por `DataTablesUtils.initServerSide()`
- [ ] Reemplazar `setTimeout` para visibilidad por `DOMUtils.waitForVisible()`
- [ ] Reemplazar fetch directo por `API_HELPERS.safeFetchJson()` o `CRUD.*()`
- [ ] Usar `Module.init()` para bootstrap estándar
- [ ] Eliminar código duplicado (helpers locales)
- [ ] Actualizar partial HTML para cargar helpers centralizados

---

## 🧪 Smoke Tests Sugeridos

### Test por Módulo:

```javascript
// Ejemplo: test_clientes.js
describe('Módulo Clientes', () => {
  it('debe descubrir rutas desde endpoint', async () => {
    const routes = await window.Routes.get('clientes');
    expect(routes).toHaveProperty('collection');
    expect(routes.collection).toBe('/api/v1/clientes/');
  });

  it('debe inicializar DataTable correctamente', async () => {
    const dt = await window.DataTablesUtils.initServerSide({
      table: '#table-clientes',
      endpoint: '/api/v1/clientes/dt/',
      columns: []
    });
    expect(dt).toBeDefined();
  });

  it('debe incluir CSRF en requests', async () => {
    const csrf = window.API_HELPERS.getCSRF();
    expect(csrf).toBeTruthy();
  });
});
```

---

## 📊 Métricas de Éxito

### Antes del Refactor:
- ❌ 10+ módulos con URLs hardcodeadas
- ❌ 5+ módulos con `getCookie()` local
- ❌ 3+ módulos con `setTimeout` para visibilidad
- ❌ 0 endpoint centralizado de rutas

### Después del Refactor:
- ✅ 0 módulos con URLs hardcodeadas (todas desde `Routes`)
- ✅ 0 módulos con `getCookie()` local (todos usan `API_HELPERS.getCSRF()`)
- ✅ 0 módulos con `setTimeout` para visibilidad (todos usan `DOMUtils.waitForVisible()`)
- ✅ 1 endpoint centralizado de rutas (`GET /api/v1/core/routes/`)

---

## 🚀 Orden de Ejecución

1. **Crear helpers centralizados** (`routes.js`, `crud.js`, `module.js`)
2. **Mejorar helpers existentes** (`datatables-utils.js`)
3. **Crear endpoint backend** (`CoreRoutesView`)
4. **Migrar módulo piloto** (`clientes.page.js` o `proveedores.page.js`)
5. **Validar con smoke tests**
6. **Migrar módulos restantes** (prioridad: server-side → client-side → singleton)
7. **Eliminar archivos duplicados** (`.dt.js`, `.table.js` legacy)
8. **Actualizar documentación**

---

**Fin del Plan**
