/**
 * inventario.api.js - Wrapper de API Inventario v2.60
 * ⚠️ Aislamiento Gradual: Capa de Datos - Retorna siempre {ok, status, data}
 * ⚠️ Refactorizado para seguir el patrón de empleados.api.js
 * Manejo de peticiones HTTP para el módulo de Inventario.
 * ⚠️ CRÍTICO: Todos los métodos son async para resolver rutas dinámicamente
 */
(function(w) {
  'use strict';

  // ⚠️ v2.40: URL base hardcodeada como fallback
  const API_BASE_FALLBACK = '/api/v1/inventario';

  /**
   * Resuelve la URL base del API usando Routes si está disponible
   * ⚠️ REGLA MANDATORIA: Estándar Asíncrono Estricto - siempre await
   * @returns {Promise<string>} URL base del API
   */
  /**
   * Resuelve la URL base del API usando Routes si está disponible
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica disponibilidad
   * @returns {Promise<string>} URL base del API
   */
  async function getApiBase() {
    if (w.Routes && typeof w.Routes.get === 'function') {
      // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
      const routesRes = await w.Routes.get('inventario');
      
      // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
      if (routesRes && routesRes.ok && routesRes.data) {
        const routes = routesRes.data;
        // Intentar obtener la URL base desde diferentes posibles estructuras
        if (routes.productos && routes.productos.collection) {
          // Extraer la base desde la URL de colección (ej: /api/v1/inventario/productos/ -> /api/v1/inventario)
          const base = routes.productos.collection.replace(/\/productos\/?$/, '');
          if (base) return base;
        }
        if (routes.collection) {
          const base = routes.collection.replace(/\/[^\/]+\/?$/, '');
          if (base) return base;
        }
      } else {
        console.warn('[inventario.api] Error resolviendo rutas, usando fallback');
      }
    }
    return API_BASE_FALLBACK;
  }

  /**
   * Construye URL con query parameters para GET requests
   * ⚠️ v2.40: NUNCA enviar body en GET requests
   */
  function buildUrlWithParams(baseUrl, params = {}) {
    if (!params || Object.keys(params).length === 0) return baseUrl;
    
    const url = new URL(baseUrl, w.location.origin);
    Object.keys(params).forEach(key => {
      const value = params[key];
      if (value !== null && value !== undefined && value !== '') {
        url.searchParams.append(key, String(value));
      }
    });
    return url.pathname + url.search;
  }

  // ⚠️ v2.40: Exposición global explícita (patrón Empleados)
  // ⚠️ CRÍTICO: Todos los métodos son async para resolver rutas dinámicamente
  w.inventarioAPI = {
    // --- PRODUCTOS ---
    productos: {
      list: async (params = {}) => {
        // ⚠️ v2.61.3: Usar Core API Facade directamente como fallback
        const base = await getApiBase();
        // Si el base es el fallback, usar Core API Facade
        if (base === API_BASE_FALLBACK) {
          return w.http('GET', buildUrlWithParams('/api/v1/inventario/productos/', params));
        }
        return w.http('GET', buildUrlWithParams(`${base}/productos/`, params));
      },
      get: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/productos/${id}/`);
      },
      save: async (payload) => {
        const base = await getApiBase();
        return w.http('POST', `${base}/productos/`, payload);
      },
      update: async (id, payload) => {
        const base = await getApiBase();
        return w.http('PATCH', `${base}/productos/${id}/`, payload);
      },
      delete: async (id) => {
        const base = await getApiBase();
        return w.http('DELETE', `${base}/productos/${id}/`);
      },
      stock: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/productos/${id}/stock/`);
      },
      kardex: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/productos/${id}/kardex/`);
      },
      // ⚠️ REGLA MANDATORIA: Endpoint para DataTables CLIENT-SIDE (serverSide: false)
      // Retorna URL resuelta como string (nunca Promise)
      dt: async () => {
        const base = await getApiBase();
        const url = `${base}/productos/dt/`;
        // ⚠️ CRÍTICO: Validar que sea string, no Promise
        if (typeof url !== 'string') {
          console.error('[inventario.api] dt() retornó no-string:', typeof url);
          return API_BASE_FALLBACK + '/productos/dt/';
        }
        return url;
      }
    },

    // --- SERVICIOS ---
    servicios: {
      list: async (params = {}) => {
        const base = await getApiBase();
        return w.http('GET', buildUrlWithParams(`${base}/servicios/`, params));
      },
      get: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/servicios/${id}/`);
      },
      save: async (payload) => {
        const base = await getApiBase();
        return w.http('POST', `${base}/servicios/`, payload);
      },
      update: async (id, payload) => {
        const base = await getApiBase();
        return w.http('PATCH', `${base}/servicios/${id}/`, payload);
      },
      delete: async (id) => {
        const base = await getApiBase();
        return w.http('DELETE', `${base}/servicios/${id}/`);
      },
      dt: async () => {
        const base = await getApiBase();
        const url = `${base}/servicios/dt/`;
        if (typeof url !== 'string') {
          console.error('[inventario.api] dt() retornó no-string:', typeof url);
          return API_BASE_FALLBACK + '/servicios/dt/';
        }
        return url;
      }
    },

    // --- ACTIVOS FIJOS ---
    activos: {
      list: async (params = {}) => {
        const base = await getApiBase();
        return w.http('GET', buildUrlWithParams(`${base}/activos/`, params));
      },
      get: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/activos/${id}/`);
      },
      save: async (payload) => {
        const base = await getApiBase();
        return w.http('POST', `${base}/activos/`, payload);
      },
      update: async (id, payload) => {
        const base = await getApiBase();
        return w.http('PATCH', `${base}/activos/${id}/`, payload);
      },
      delete: async (id) => {
        const base = await getApiBase();
        return w.http('DELETE', `${base}/activos/${id}/`);
      },
      dt: async () => {
        const base = await getApiBase();
        const url = `${base}/activos/dt/`;
        if (typeof url !== 'string') {
          console.error('[inventario.api] dt() retornó no-string:', typeof url);
          return API_BASE_FALLBACK + '/activos/dt/';
        }
        return url;
      },
      // ⚠️ v2.40: Endpoint optimizado para Client-Side DataTables (array JSON simple)
      list_all: async () => {
        const base = await getApiBase();
        const url = `${base}/activos/list-all/`;
        if (typeof url !== 'string') {
          console.error('[inventario.api] list_all() retornó no-string:', typeof url);
          return API_BASE_FALLBACK + '/activos/list-all/';
        }
        return url;
      }
    },

    // --- MOVIMIENTOS (KARDEX) ---
    movimientos: {
      list: async (params = {}) => {
        const base = await getApiBase();
        return w.http('GET', buildUrlWithParams(`${base}/movimientos/`, params));
      },
      get: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/movimientos/${id}/`);
      },
      save: async (payload) => {
        const base = await getApiBase();
        return w.http('POST', `${base}/movimientos/`, payload);
      },
      // ⚠️ v2.40: Endpoint para DataTables SERVER-SIDE
      dt: async () => {
        const base = await getApiBase();
        const url = `${base}/movimientos/dt/`;
        if (typeof url !== 'string') {
          console.error('[inventario.api] dt() retornó no-string:', typeof url);
          return API_BASE_FALLBACK + '/movimientos/dt/';
        }
        return url;
      }
      // No hay update/delete por integridad de Kardex
    },

    // --- HISTORIAL SERVICIOS ---
    historialServicios: {
      list: async (params = {}) => {
        const base = await getApiBase();
        return w.http('GET', buildUrlWithParams(`${base}/historial-servicios/`, params));
      },
      get: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/historial-servicios/${id}/`);
      },
      save: async (payload) => {
        const base = await getApiBase();
        return w.http('POST', `${base}/historial-servicios/`, payload);
      },
      // No hay update/delete por integridad de historial
    },

    // --- CATEGORÍAS (Maestro de Inventario) ---
    categorias: {
      list: async (params = {}) => {
        const base = await getApiBase();
        return w.http('GET', buildUrlWithParams(`${base}/categorias/`, params));
      },
      get: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/categorias/${id}/`);
      },
      save: async (payload) => {
        const base = await getApiBase();
        return w.http('POST', `${base}/categorias/`, payload);
      },
      update: async (id, payload) => {
        const base = await getApiBase();
        return w.http('PATCH', `${base}/categorias/${id}/`, payload);
      },
      delete: async (id) => {
        const base = await getApiBase();
        return w.http('DELETE', `${base}/categorias/${id}/`);
      },
      resumen: async (id) => {
        const base = await getApiBase();
        return w.http('GET', `${base}/categorias/${id}/resumen/`);
      },
      dt: async () => {
        const base = await getApiBase();
        const url = `${base}/categorias/dt/`;
        if (typeof url !== 'string') {
          console.error('[inventario.api] dt() retornó no-string:', typeof url);
          return API_BASE_FALLBACK + '/categorias/dt/';
        }
        return url;
      }
    }
  };
  
})(window);
