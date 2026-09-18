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
