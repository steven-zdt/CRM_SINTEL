/**
 * window.Sintel.Core.Http — Cliente HTTP unico (F32.3/F32.6)
 *
 * Contrato completo: documentacion/F32_3_CORE_HTTP_CONTRACT.md. NO
 * reemplaza a window.http todavia -- se agrega de forma aditiva. La
 * promocion a "el" cliente activo (retirar lib/http.js) es F32.7, y solo
 * despues de que los 6 *.api.js violadores (F31.3) migren a llamar esto
 * directamente (F32.6) con validacion real de navegador (F32.5) en cada
 * paso.
 *
 * Decisiones de diseno tomadas de la evidencia real, no de preferencia:
 * - CSRF via cookie (no meta-tag): es lo que el 100% del trafico tenant
 *   usa hoy (lib/http.js gana en produccion, confirmado en F32.5 spec
 *   00-http-loaded).
 * - upload() es un metodo separado, no deteccion automatica de FormData
 *   en post(): la version "v3.4" que existia antes hacia
 *   JSON.stringify(FormData) -> "{}", corrompiendo archivos en silencio
 *   (hallazgo F32.1 S3).
 * - JWT siempre via getValidAccessToken() (con refresh), nunca
 *   getAccessToken() a secas -- 5 de 6 api.js violadores no refrescaban
 *   (hallazgo F32.1 S5).
 * - Manejo de 401 porta la logica real de lib/http.js (modulos no
 *   criticos vs redirect) -- perderla rompe UX ya validada.
 * - try/catch alrededor de fetch() (la version "v3.4" ya lo hacia bien,
 *   lib/http.js no) -- relevante para ERR_BLOCKED_BY_CLIENT y otros
 *   errores de red, encontrado en la sesion de F32.5.
 */
(function (w) {
  'use strict';

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return decodeURIComponent(parts.pop().split(';').shift());
    }
    return null;
  }

  function csrf() {
    return getCookie('csrftoken');
  }

  // Modulos no-criticos: 401 se retorna como {ok:false,status:401,data}
  // para manejo local, en vez de redirigir a login. Configurable (F32.3
  // S3) -- agregar aqui, no hardcodear en cada consumidor.
  const NON_CRITICAL_401_PREFIXES = [
    '/api/v1/gastos/',
    '/api/v1/clientes/',
    '/api/v1/proveedores/',
    '/api/v1/inventario/',
  ];

  function addNonCritical401Prefix(prefix) {
    if (prefix && NON_CRITICAL_401_PREFIXES.indexOf(prefix) === -1) {
      NON_CRITICAL_401_PREFIXES.push(prefix);
    }
  }

  async function buildHeaders(method, extra) {
    const headers = Object.assign({ Accept: 'application/json' }, extra || {});
    const needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
    if (needsCsrf) {
      const token = csrf();
      if (token) headers['X-CSRFToken'] = token;
    }
    try {
      if (w.jwtAuth && typeof w.jwtAuth.getValidAccessToken === 'function') {
        const jwt = await w.jwtAuth.getValidAccessToken();
        if (jwt) headers['Authorization'] = `Bearer ${jwt}`;
      }
    } catch (_) {
      // jwtAuth es opcional -- SessionAuth sigue funcionando como fallback
      // (BaseTenantViewSet Dual-Auth).
    }
    return headers;
  }

  function normalizeError(status, data) {
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && Array.isArray(data.non_field_errors) && data.non_field_errors[0]) {
      return data.non_field_errors[0];
    }
    if (data && typeof data === 'object') {
      const flat = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join('; ');
      if (flat) return flat;
    }
    return `HTTP ${status}`;
  }

  async function parseBody(res) {
    const text = await res.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch (_) {
      return { detail: text };
    }
  }

  function handle401(url) {
    const isNonCritical = NON_CRITICAL_401_PREFIXES.some((p) => url.includes(p));
    if (isNonCritical) return true;
    const loginUrl = new URL('/login/', w.location.origin);
    loginUrl.searchParams.set('reason', '401');
    loginUrl.searchParams.set('next', w.location.pathname + w.location.hash);
    w.location.assign(loginUrl.toString());
    return false;
  }

  /**
   * Primitiva base. NO lanza en 4xx/5xx -- devuelve {ok,status,data},
   * mismo contrato que window.http hoy (lib/http.js), para que sea un
   * reemplazo drop-in sin cambiar el codigo de cada consumidor.
   */
  async function request(method, url, body, opts) {
    method = String(method || 'GET').toUpperCase();
    const init = Object.assign(
      { method, credentials: 'same-origin' },
      opts || {}
    );
    init.headers = await buildHeaders(method, (opts && opts.headers) || {});

    if (body !== undefined) {
      if (body instanceof FormData) {
        // No usar request() con FormData -- usar upload(). Defensivo: si
        // algun consumidor lo hace de todos modos, no lo corrompemos
        // (a diferencia del bug real de la v3.4 vieja).
        init.body = body;
        delete init.headers['Content-Type'];
        const token = csrf();
        if (token) body.append('csrfmiddlewaretoken', token);
      } else {
        init.headers['Content-Type'] = 'application/json';
        init.body = JSON.stringify(body);
      }
    }

    let res;
    try {
      res = await fetch(url, init);
    } catch (networkErr) {
      // ERR_BLOCKED_BY_CLIENT, DNS, CORS, etc. -- no propagar como
      // excepcion no capturada (bug real de lib/http.js, F32.3 S3).
      return {
        ok: false,
        status: 0,
        data: { detail: (networkErr && networkErr.message) || 'Error de red' },
      };
    }

    if (res.status === 401) {
      const shouldReturnLocally = handle401(url);
      if (!shouldReturnLocally) {
        return { ok: false, status: 401, data: { detail: 'Unauthorized' } };
      }
    }

    const data = await parseBody(res);
    return { ok: res.ok, status: res.status, data };
  }

  /**
   * upload() -- metodo explicito para FormData, nunca inferido. Porta el
   * manejo real de lib/http.js (sin Content-Type explicito, boundary
   * automatico del navegador, csrfmiddlewaretoken en el propio FormData
   * ademas del header).
   */
  async function upload(method, url, formData) {
    return request(method, url, formData);
  }

  const Http = {
    request,
    get: (url, opts) => request('GET', url, undefined, opts),
    post: (url, body, opts) => request('POST', url, body, opts),
    put: (url, body, opts) => request('PUT', url, body, opts),
    patch: (url, body, opts) => request('PATCH', url, body, opts),
    delete: (url, opts) => request('DELETE', url, undefined, opts),
    upload,
    csrf,
    normalizeError,
    addNonCritical401Prefix,
  };

  w.Sintel = w.Sintel || {};
  w.Sintel.Core = w.Sintel.Core || {};
  w.Sintel.Core.Http = Http;
})(window);
