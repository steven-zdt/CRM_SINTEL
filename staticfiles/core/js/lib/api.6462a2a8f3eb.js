/**
 * api.js - Helpers centralizados para consumo de API REST
 * 
 * ⚠️ v2.37: Unificación de convenciones API-First
 * - Trailing slash consistente
 * - Construcción segura de URLs
 * - Manejo de errores 404/422
 * - Soporte para UUID como identificador
 * - Multitenant: usa window.location.origin para construir API_BASE
 */

(function(window) {
  'use strict';

  // ⚠️ CONFIGURACIÓN: Debe coincidir con DRF DefaultRouter(trailing_slash=True)
  const TRAILING_SLASH = true;

  /**
   * Normalizar trailing slash según configuración
   * @param {string} url - URL a normalizar
   * @returns {string} URL normalizada
   */
  function withTrailingSlash(url) {
    if (!url || typeof url !== 'string') return url;
    if (TRAILING_SLASH) {
      return url.endsWith('/') ? url : url + '/';
    } else {
      return url.endsWith('/') ? url.slice(0, -1) : url;
    }
  }

  /**
   * Base URL de la API derivada del dominio actual (tenant actual)
   * ⚠️ MULTITENANT: window.location.origin resuelve al dominio del tenant actual
   */
  const API_BASE = withTrailingSlash(`${window.location.origin}/api/v1`);

  /**
   * Verificar si un valor es un UUID válido
   * @param {*} v - Valor a verificar
   * @returns {boolean} true si es UUID válido
   */
  function isUuid(v) {
    if (typeof v !== 'string') return false;
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(v);
  }

  /**
   * Construir URL de detalle de forma segura
   * @param {string} baseUrl - URL base de la colección
   * @param {string|number} idOrUuid - ID o UUID del recurso
   * @returns {string} URL de detalle completa
   */
  function buildDetailUrl(baseUrl, idOrUuid) {
    if (!baseUrl) {
      throw new Error('buildDetailUrl: baseUrl es requerido');
    }
    if (idOrUuid === null || idOrUuid === undefined || idOrUuid === '') {
      throw new Error('buildDetailUrl: idOrUuid es requerido');
    }

    const base = withTrailingSlash(String(baseUrl));
    const key = String(idOrUuid).trim().replace(/^\/|\/$/g, ''); // Limpiar slashes del key

    return TRAILING_SLASH ? `${base}${key}/` : `${base}${key}`;
  }

  /**
   * Obtener headers de autenticación
   * @param {Object} additionalHeaders - Headers adicionales
   * @returns {Object} Headers completos
   */
  function authHeaders(additionalHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...additionalHeaders
    };

    // CSRF token para SessionAuthentication
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    return headers;
  }

  /**
   * Helper para obtener cookie por nombre
   * @param {string} name - Nombre de la cookie
   * @returns {string|null} Valor de la cookie o null
   */
  function getCookie(name) {
    if (!document.cookie) return null;
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return null;
  }

  /**
   * Fetch seguro con manejo de errores 404/422
   * @param {string} url - URL a consultar
   * @param {Object} options - Opciones de fetch
   * @returns {Promise<Object>} Respuesta JSON parseada
   * @throws {Error} Error con status, body y fields (si aplica)
   */
  async function safeFetchJson(url, options = {}) {
    const defaultOptions = {
      credentials: 'same-origin',
      headers: authHeaders(options.headers || {})
    };

    // Si hay body, asegurar que sea string JSON
    if (options.body && typeof options.body !== 'string') {
      options.body = JSON.stringify(options.body);
    }

    const finalOptions = { ...defaultOptions, ...options };

    try {
      const res = await fetch(url, finalOptions);
      let body = null;

      try {
        body = await res.json();
      } catch (_) {
        // Ignorar si no hay JSON en la respuesta
      }

      // Manejo específico de errores
      if (res.status === 404) {
        const error = new Error('No encontrado (404). Verifica UUID/ID y tenant actual.');
        error.status = 404;
        error.body = body;
        throw error;
      }

      if (res.status === 422 || res.status === 400) {
        const error = new Error(
          `Datos inválidos (${res.status}): ${body?.message || body?.detail || 'Verifica los campos.'}`
        );
        error.status = res.status;
        error.body = body;
        error.fields = body?.fields || {};
        throw error;
      }

      if (!res.ok) {
        const error = new Error(`HTTP ${res.status}: ${res.statusText}`);
        error.status = res.status;
        error.body = body;
        throw error;
      }

      return body;
    } catch (error) {
      // Re-lanzar errores conocidos
      if (error.status) {
        throw error;
      }
      // Errores de red u otros
      throw new Error(`Error de red: ${error.message}`);
    }
  }

  /**
   * Obtener clave de entidad desde un row (prioriza uuid)
   * @param {Object} row - Fila/objeto de datos
   * @returns {string|number|null} UUID, ID o null
   */
  function getEntityKeyFromRow(row) {
    if (!row) return null;
    return row.uuid || row.id || row.pk || null;
  }

  /**
   * Validar que una clave de entidad sea válida
   * @param {string|number|null} key - Clave a validar
   * @throws {Error} Si la clave no es válida
   */
  function assertValidKey(key) {
    if (!key && key !== 0) {
      throw new Error('Identificador no proporcionado');
    }
  }

  /**
   * Mapear responsabilidades RUT a códigos
   * Convierte selecciones de UI (pueden ser "48 - IVA ..." o objetos {code, label})
   * a un array de códigos string
   * @param {Array} items - Items de responsabilidades
   * @returns {Array<string>} Array de códigos
   */
  function mapResponsabilidadesToCodes(items) {
    if (!Array.isArray(items)) return [];
    
    return items
      .map(x => {
        if (typeof x === 'string') {
          // Formato "48 - IVA como agente de retención"
          const code = x.split(' - ')[0]?.trim();
          return code || null;
        }
        if (x && typeof x === 'object' && 'code' in x) {
          return String(x.code).trim();
        }
        return String(x).trim();
      })
      .filter(Boolean);
  }

  /**
   * URLs base de colecciones por app
   * ⚠️ IMPORTANTE: Estas URLs deben coincidir con las rutas registradas en DRF
   */
  const API = {
    empresas: withTrailingSlash(`${API_BASE}empresas/empresas`),
    facturas: withTrailingSlash(`${API_BASE}facturas`),
    cuentas: withTrailingSlash(`${API_BASE}contabilidad/cuentas-contables`),
    asientos: withTrailingSlash(`${API_BASE}contabilidad/asientos-contables`),
    empleados: withTrailingSlash(`${API_BASE}empleados/empleados`),
    gastos: withTrailingSlash(`${API_BASE}gastos`),
    proveedores: withTrailingSlash(`${API_BASE}proveedores`),
    clientes: withTrailingSlash(`${API_BASE}clientes`),
    perfil: withTrailingSlash(`${API_BASE}perfil`),
    catalogo: withTrailingSlash(`${API_BASE}inventario/catalogo`),
    activos: withTrailingSlash(`${API_BASE}inventario/activos-fijos`),
    movimientos: withTrailingSlash(`${API_BASE}inventario/movimientos`),
  };

  // Exportar al namespace global window
  window.API_HELPERS = {
    API_BASE,
    API,
    TRAILING_SLASH,
    withTrailingSlash,
    isUuid,
    buildDetailUrl,
    authHeaders,
    safeFetchJson,
    getEntityKeyFromRow,
    assertValidKey,
    mapResponsabilidadesToCodes
  };

})(window);
