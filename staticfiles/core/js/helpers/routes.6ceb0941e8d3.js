/**
 * Routes Helper - Descubrimiento y cacheo de rutas del backend
 * 
 * ⚠️ OLA 1: Helper centralizado para eliminar URLs hardcodeadas
 * - Descubre rutas desde GET /api/v1/core/routes/
 * - Cache en sessionStorage con TTL (5 minutos)
 * - Soporta subclaves (inventario.catalogo, contabilidad.asientos)
 * - Fallback: retorna {} si el endpoint no responde
 */

(function (w) {
  'use strict';

  const CACHE_KEY = 'sintel_routes_cache';
  const CACHE_TTL = 5 * 60 * 1000; // 5 minutos
  const ROUTES_ENDPOINT = '/api/v1/core/routes/';

  let cache = null;
  let cacheTimestamp = null;

  /**
   * Obtiene el valor de una cookie por nombre
   */
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return decodeURIComponent(parts.pop().split(";").shift());
    }
    return null;
  }

  /**
   * Carga rutas desde el backend
   */
  async function fetchRoutes() {
    try {
      const csrf = getCookie('csrftoken');
      const headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      };
      if (csrf) {
        headers['X-CSRFToken'] = csrf;
      }

      const res = await fetch(ROUTES_ENDPOINT, {
        method: 'GET',
        headers: headers,
        credentials: 'same-origin'
      });

      if (!res.ok) {
        console.warn('[Routes] Error cargando rutas:', res.status, res.statusText);
        return {};
      }

      const data = await res.json();
      return data || {};
    } catch (err) {
      console.warn('[Routes] Error en fetch de rutas:', err);
      return {};
    }
  }

  /**
   * Carga rutas desde cache o backend
   */
  async function loadRoutes() {
    // Intentar desde sessionStorage
    try {
      const cached = sessionStorage.getItem(CACHE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached);
        const age = Date.now() - parsed.timestamp;
        if (age < CACHE_TTL) {
          cache = parsed.data;
          cacheTimestamp = parsed.timestamp;
          return cache;
        }
      }
    } catch (err) {
      // Ignorar errores de sessionStorage
    }

    // Cargar desde backend
    cache = await fetchRoutes();
    cacheTimestamp = Date.now();

    // Guardar en sessionStorage
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({
        timestamp: cacheTimestamp,
        data: cache
      }));
    } catch (err) {
      // Ignorar errores de sessionStorage
    }

    return cache;
  }

  /**
   * Obtiene el bloque de rutas de un módulo
   * @param {string} module - Nombre del módulo (ej: 'facturas', 'inventario.catalogo')
   * @returns {Object|null} Bloque de rutas o null si no existe
   */
  async function get(module) {
    if (!cache) {
      await loadRoutes();
    }

    if (!cache || !module) {
      return null;
    }

    // Soporte para subclaves (inventario.catalogo, contabilidad.asientos)
    const parts = module.split('.');
    let current = cache;

    for (const part of parts) {
      if (!current || typeof current !== 'object') {
        return null;
      }
      current = current[part];
    }

    return current || null;
  }

  /**
   * Construye URL de colección
   * @param {string} module - Nombre del módulo
   * @returns {string|null} URL de colección o null
   */
  async function collectionUrl(module) {
    const routes = await get(module);
    return routes?.collection || null;
  }

  /**
   * Construye URL de detalle
   * @param {string} module - Nombre del módulo
   * @param {string|number} id - ID del recurso
   * @returns {string|null} URL de detalle o null
   */
  async function detailUrl(module, id) {
    const routes = await get(module);
    if (!routes?.detail) {
      return null;
    }
    return routes.detail.replace('{id}', String(id));
  }

  /**
   * Construye URL de DataTable
   * @param {string} module - Nombre del módulo
   * @returns {string|null} URL de DataTable o null
   */
  async function datatableUrl(module) {
    const routes = await get(module);
    return routes?.datatable || null;
  }

  /**
   * Construye URL de singleton
   * @param {string} module - Nombre del módulo
   * @returns {string|null} URL de singleton o null
   */
  async function singletonUrl(module) {
    const routes = await get(module);
    return routes?.singleton || null;
  }

  /**
   * Invalida el cache y fuerza recarga
   */
  async function invalidateCache() {
    cache = null;
    cacheTimestamp = null;
    try {
      sessionStorage.removeItem(CACHE_KEY);
    } catch (err) {
      // Ignorar errores
    }
    return await loadRoutes();
  }

  // Exportar API pública
  w.Routes = Object.freeze({
    get,
    collectionUrl,
    detailUrl,
    datatableUrl,
    singletonUrl,
    invalidateCache
  });
})(window);
