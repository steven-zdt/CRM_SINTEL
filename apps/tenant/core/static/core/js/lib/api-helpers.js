/**
 * API Helpers - Helpers centralizados para operaciones API
 * 
 * ⚠️ v2.40: ENFORCED MODE - Manejo mejorado de errores de permisos
 * ⚠️ v2.37: API-First - Helpers compartidos para todas las páginas
 * - Construcción de URLs con trailing slash consistente
 * - Manejo de CSRF token automático en mutaciones
 * - Normalización de datos (responsabilidades_rut_codigos)
 * - Fetch seguro con manejo de errores estandarizado
 * - Soporte para errores 405 (Method Not Allowed - ENFORCED MODE)
 * - Soporte para errores 403 (Forbidden), 409 (Conflict), 422 (Validation)
 */

(function (w) {
  'use strict';

  const TRAILING_SLASH = true;
  
  const withTrailingSlash = (s) => {
    if (!s) return '';
    return TRAILING_SLASH 
      ? (s.endsWith('/') ? s : s + '/')
      : (s.endsWith('/') ? s.slice(0, -1) : s);
  };

  const API_BASE = withTrailingSlash(`${w.location.origin}/api/v1`);

  function buildDetailUrl(base, idOrUuid) {
    const b = withTrailingSlash(base);
    const u = String(idOrUuid ?? '').trim().replace(/^\/|\/$/g, '');
    return TRAILING_SLASH ? `${b}${u}/` : `${b}${u}`;
  }

  function mapResponsabilidadesToCodes(items) {
    return (items || [])
      .map(x => {
        if (typeof x === 'string') {
          return x.split(' - ')[0].trim();
        }
        if (x && typeof x === 'object' && 'code' in x) {
          return String(x.code).trim();
        }
        return String(x || '').trim();
      })
      .filter(Boolean);
  }

  /**
   * Obtiene el token CSRF desde meta tag o cookie
   * ⚠️ FASE 2: Función idempotente que siempre lee el token fresco
   * @returns {string} Token CSRF o cadena vacía
   */
  function getCSRF() {
    // Prioridad 1: meta tag
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta?.content) return meta.content.trim();
    
    // Prioridad 2: cookie (fallback)
    const m = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[2]) : '';
  }

  /**
   * Genera headers de autenticación con CSRF
   * ⚠️ FASE 2: Siempre incluye X-CSRFToken si está disponible
   * @param {Object} extra - Headers adicionales
   * @returns {Object} Headers con CSRF
   */
  function authHeaders(extra = {}) {
    const csrf = getCSRF();
    const headers = { 'Content-Type': 'application/json', ...extra };
    if (csrf) {
      headers['X-CSRFToken'] = csrf;
    }
    return headers;
  }

  /**
   * Fetch seguro con manejo de errores y CSRF automático
   * ⚠️ v2.40: ENFORCED MODE - Manejo mejorado de errores 405/403/409
   * ⚠️ FASE 2: SIEMPRE incluye CSRF en mutaciones (POST, PUT, PATCH, DELETE)
   * 
   * @param {string} url - URL a llamar
   * @param {Object} init - Opciones de fetch
   * @param {string} [init.method] - Método HTTP (GET, POST, PUT, PATCH, DELETE)
   * @param {Object|FormData|string} [init.body] - Body de la petición
   * @param {Object} [init.headers] - Headers adicionales
   * @returns {Promise<any>} Body de la respuesta parseado como JSON
   * @throws {Error} Error con propiedades: status, body, detail
   * 
   * Errores manejados:
   * - 401: Sesión expirada
   * - 403: Acceso denegado (permisos insuficientes)
   * - 404: Recurso no encontrado
   * - 405: Método no permitido (ENFORCED MODE - requiere ADMIN/STAFF)
   * - 409: Conflicto (recurso duplicado o estado inválido)
   * - 422: Validación fallida (campos inválidos)
   */
  async function safeFetchJson(url, init = {}) {
    const method = (init.method || 'GET').toUpperCase();
    
    // Preparar opciones base
    const opts = {
      credentials: 'same-origin',
      ...init,
      headers: {
        'Accept': 'application/json',
        ...(init.headers || {})
      }
    };

    // Manejo inteligente de Content-Type y body
    const isFormData = (v) => typeof FormData !== "undefined" && v instanceof FormData;
    
    if (isFormData(init.body)) {
      // FormData: el navegador establecerá Content-Type automáticamente
    } else if (init.body != null && method !== 'GET' && method !== 'HEAD') {
      opts.headers['Content-Type'] = 'application/json';
      // Stringify solo si es objeto (no string ni FormData)
      if (typeof opts.body === 'object' && !(opts.body instanceof String)) {
        opts.body = JSON.stringify(opts.body);
      }
    }

    // ⚠️ FASE 2: Inyectar CSRF en mutaciones (POST, PUT, PATCH, DELETE)
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const csrf = getCSRF();
      if (csrf) {
        opts.headers['X-CSRFToken'] = csrf;
      }
    }

    const res = await fetch(url, opts);
    
    let body = null;
    let bodyText = null;
    
    // Intentar obtener el body como texto primero para diagnóstico
    try {
      bodyText = await res.text();
    } catch (_) {
      // Si no se puede obtener como texto, continuar
    }
    
    // Intentar parsear como JSON solo si hay contenido y parece JSON
    if (bodyText && bodyText.trim().length > 0) {
      const contentType = res.headers.get('content-type') || '';
      const isJson = contentType.includes('application/json') || 
                     (bodyText.trim().startsWith('{') || bodyText.trim().startsWith('['));
      
      if (isJson) {
        try {
          body = JSON.parse(bodyText);
        } catch (parseErr) {
          // Si falla el parse JSON, usar el texto como body
          // Esto permite que el código de manejo de errores acceda al contenido
          body = { 
            _raw: bodyText,
            _parseError: parseErr.message,
            detail: 'Error parseando respuesta del servidor'
          };
        }
      } else {
        // No es JSON, usar el texto como body
        body = { _raw: bodyText, detail: bodyText };
      }
    }

    // Manejo específico de códigos de estado HTTP
    if (res.status === 404) {
      const e = new Error('No encontrado (404). Verifica UUID/ID y tenant actual.');
      e.status = 404;
      e.body = body;
      throw e;
    }
    
    if (res.status === 401) {
      const e = new Error('No autorizado (401). Sesión expirada.');
      e.status = 401;
      e.body = body;
      throw e;
    }
    
    // ⚠️ v2.40: ENFORCED MODE - 405 Method Not Allowed
    // Indica que el usuario no tiene permisos ADMIN/STAFF para esta operación
    if (res.status === 405) {
      const detail = body?.detail || body?.message || 'Método no permitido. Solo usuarios ADMIN/STAFF pueden realizar esta operación.';
      const e = new Error(`HTTP 405: Method Not Allowed. ${detail}`);
      e.status = 405;
      e.body = body;
      e.detail = detail;
      throw e;
    }
    
    if (res.status === 403) {
      const detail = body?.detail || body?.message || 'Acceso denegado. No tienes permisos para realizar esta operación.';
      const e = new Error(`HTTP 403: Forbidden. ${detail}`);
      e.status = 403;
      e.body = body;
      e.detail = detail;
      throw e;
    }
    
    if (res.status === 409) {
      const detail = body?.detail || body?.message || 'Conflicto. El recurso ya existe o hay un conflicto de estado.';
      const e = new Error(`HTTP 409: Conflict. ${detail}`);
      e.status = 409;
      e.body = body;
      e.detail = detail;
      throw e;
    }
    
    if (res.status === 422) {
      const e = new Error(body?.message || body?.detail || 'Datos inválidos (422). Verifica los campos.');
      e.status = 422;
      e.body = body;
      e.fields = body?.fields || {};
      e.detail = body?.detail || body?.message;
      throw e;
    }
    
    if (!res.ok) {
      // Extraer mensaje de error del body si está disponible
      const errorMessage = body?.detail || body?.message || body?.error || `HTTP ${res.status}: ${res.statusText}`;
      const e = new Error(errorMessage);
      e.status = res.status;
      e.body = body;
      e.detail = body?.detail || body?.message;
      throw e;
    }
    
    return body;
  }

  // ⚠️ Inicialización idempotente: NO mutar propiedades read-only
  // Crear/usar namespace sin romper si ya existe/fue congelado
  const AH = w.API_HELPERS || {};

  // Define TRAILING_SLASH solo si NO existe (evita TypeError en propiedades read-only)
  if (!Object.prototype.hasOwnProperty.call(AH, 'TRAILING_SLASH')) {
    try {
      Object.defineProperty(AH, 'TRAILING_SLASH', {
        value: TRAILING_SLASH,
        writable: false,
        configurable: false,
        enumerable: true
      });
    } catch (_) {
      // Si ya estaba como no configurable, no lo tocamos
    }
  }

  // Asignar funciones SOLO si no existen (evita sobrescribir en recargas)
  if (!AH.withTrailingSlash) AH.withTrailingSlash = withTrailingSlash;
  if (!AH.API_BASE) AH.API_BASE = API_BASE;
  if (!AH.buildDetailUrl) AH.buildDetailUrl = buildDetailUrl;
  if (!AH.mapResponsabilidadesToCodes) AH.mapResponsabilidadesToCodes = mapResponsabilidadesToCodes;
  if (!AH.getCSRF) AH.getCSRF = getCSRF;
  if (!AH.authHeaders) AH.authHeaders = authHeaders;
  if (!AH.safeFetchJson) AH.safeFetchJson = safeFetchJson;

  // Propagar flag de depuración si existe (siempre actualizable)
  try {
    AH.DEBUG = (typeof w.__DEBUG__ === 'boolean') ? w.__DEBUG__ : (AH.DEBUG === true);
  } catch (_) {
    // Si DEBUG es read-only, intentar definir
    try {
      Object.defineProperty(AH, 'DEBUG', {
        value: (typeof w.__DEBUG__ === 'boolean') ? w.__DEBUG__ : (AH.DEBUG === true),
        writable: true,
        configurable: true,
        enumerable: true
      });
    } catch (__) {
      // Si no se puede, ignorar
    }
  }

  // Exponer el namespace final (solo si no existía)
  if (!w.API_HELPERS) {
    w.API_HELPERS = Object.freeze(AH);
  }
})(window);
