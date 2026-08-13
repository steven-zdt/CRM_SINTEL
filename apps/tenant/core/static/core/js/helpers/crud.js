/**
 * CRUD Helper - Operaciones CRUD estándar con CSRF y manejo de errores uniforme
 * 
 * ⚠️ OLA 1: Helper centralizado para operaciones CRUD
 * - Usa Routes para descubrir URLs
 * - Transport: usa API_HELPERS.safeFetchJson o http.js
 * - Manejo uniforme de errores 4xx/5xx
 * - Retorna {ok, status, data}
 */

(function (w) {
  'use strict';

  /**
   * Wrapper para safeFetchJson que retorna {ok, status, data}
   * @param {string} url - URL a llamar
   * @param {Object} options - Opciones de fetch
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function fetcher(url, options = {}) {
    // Usar API_HELPERS.safeFetchJson si está disponible
    if (w.API_HELPERS && typeof w.API_HELPERS.safeFetchJson === 'function') {
      try {
        // safeFetchJson retorna directamente el body en caso de éxito
        const data = await w.API_HELPERS.safeFetchJson(url, {
          ...options,
          // Asegurar que body sea JSON string si es objeto
          body: typeof options.body === 'object' && !(options.body instanceof FormData)
            ? JSON.stringify(options.body)
            : options.body
        });
        return { ok: true, status: 200, data };
      } catch (err) {
        // safeFetchJson lanza excepciones con err.status y err.body
        return {
          ok: false,
          status: err.status || 500,
          data: err.body || { detail: err.message || 'Error desconocido' }
        };
      }
    }

    // Fallback: usar Sintel.Core.Http si está disponible (F32.7, antes http.js)
    if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http) {
      const method = (options.method || 'GET').toUpperCase();
      return await w.Sintel.Core.Http.request(method, url, options.body);
    }

    // Fallback: fetch básico con CSRF
    try {
      const method = (options.method || 'GET').toUpperCase();
      const headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...(options.headers || {})
      };
      
      // ⚠️ FASE 2: Inyectar CSRF en mutaciones
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const csrf = (w.API_HELPERS && typeof w.API_HELPERS.getCSRF === 'function')
          ? w.API_HELPERS.getCSRF()
          : null;
        if (csrf) {
          headers['X-CSRFToken'] = csrf;
        }
      }
      
      const res = await fetch(url, {
        ...options,
        method: method,
        credentials: 'same-origin',
        headers: headers,
        body: typeof options.body === 'object' && !(options.body instanceof FormData)
          ? JSON.stringify(options.body)
          : options.body
      });

      let data = null;
      try {
        data = await res.json();
      } catch (_) {
        data = { detail: res.statusText };
      }
      
      // 🔍 FORENSIS: Log detallado de respuestas con error
      if (!res.ok && (w.__DEBUG__ === true || (w.API_HELPERS && w.API_HELPERS.DEBUG === true))) {
        console.error('[CRUD.fetcher] 🔍 FORENSIS - Error HTTP:', {
          url: url,
          method: options.method || 'GET',
          status: res.status,
          statusText: res.statusText,
          data: data,
          headers: Object.fromEntries(res.headers.entries())
        });
      }

      return {
        ok: res.ok,
        status: res.status,
        data
      };
    } catch (err) {
      return {
        ok: false,
        status: 500,
        data: { detail: err.message || 'Error de red' }
      };
    }
  }

  /**
   * Crea un recurso
   * @param {string} module - Nombre del módulo
   * @param {Object} payload - Datos del recurso
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function create(module, payload) {
    if (!w.Routes) {
      return { ok: false, status: 500, data: { detail: 'Routes helper no disponible' } };
    }

    const url = await w.Routes.collectionUrl(module);
    if (!url) {
      return { ok: false, status: 500, data: { detail: `URL de colección no encontrada para módulo: ${module}` } };
    }

    return await fetcher(url, {
      method: 'POST',
      body: payload
    });
  }

  /**
   * Lee un recurso
   * @param {string} module - Nombre del módulo
   * @param {string|number} id - ID del recurso
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function read(module, id) {
    if (!w.Routes) {
      return { ok: false, status: 500, data: { detail: 'Routes helper no disponible' } };
    }

    const url = await w.Routes.detailUrl(module, id);
    if (!url) {
      return { ok: false, status: 500, data: { detail: `URL de detalle no encontrada para módulo: ${module}` } };
    }

    return await fetcher(url, {
      method: 'GET'
    });
  }

  /**
   * Actualiza un recurso (PATCH)
   * @param {string} module - Nombre del módulo
   * @param {string|number} id - ID del recurso
   * @param {Object} payload - Datos a actualizar
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function update(module, id, payload) {
    if (!w.Routes) {
      return { ok: false, status: 500, data: { detail: 'Routes helper no disponible' } };
    }

    const url = await w.Routes.detailUrl(module, id);
    if (!url) {
      return { ok: false, status: 500, data: { detail: `URL de detalle no encontrada para módulo: ${module}` } };
    }

    return await fetcher(url, {
      method: 'PATCH',
      body: payload
    });
  }

  /**
   * Elimina un recurso
   * @param {string} module - Nombre del módulo
   * @param {string|number} id - ID del recurso
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function remove(module, id) {
    if (!w.Routes) {
      return { ok: false, status: 500, data: { detail: 'Routes helper no disponible' } };
    }

    const url = await w.Routes.detailUrl(module, id);
    if (!url) {
      return { ok: false, status: 500, data: { detail: `URL de detalle no encontrada para módulo: ${module}` } };
    }

    return await fetcher(url, {
      method: 'DELETE'
    });
  }

  /**
   * Lee un recurso singleton
   * @param {string} module - Nombre del módulo
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function readSingleton(module) {
    if (!w.Routes) {
      return { ok: false, status: 500, data: { detail: 'Routes helper no disponible' } };
    }

    const routes = await w.Routes.get(module);
    const url = routes?.singleton || await w.Routes.collectionUrl(module);
    
    if (!url) {
      return { ok: false, status: 500, data: { detail: `URL de singleton no encontrada para módulo: ${module}` } };
    }

    return await fetcher(url, {
      method: 'GET'
    });
  }

  /**
   * Actualiza un recurso singleton (PATCH)
   * @param {string} module - Nombre del módulo
   * @param {Object} payload - Datos a actualizar
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function updateSingleton(module, payload) {
    if (!w.Routes) {
      return { ok: false, status: 500, data: { detail: 'Routes helper no disponible' } };
    }

    const routes = await w.Routes.get(module);
    const url = routes?.singleton || await w.Routes.collectionUrl(module);
    
    if (!url) {
      return { ok: false, status: 500, data: { detail: `URL de singleton no encontrada para módulo: ${module}` } };
    }

    return await fetcher(url, {
      method: 'PATCH',
      body: payload
    });
  }

  // Exportar API pública
  w.CRUD = Object.freeze({
    create,
    read,
    update,
    delete: remove,
    readSingleton,
    updateSingleton
  });
})(window);
