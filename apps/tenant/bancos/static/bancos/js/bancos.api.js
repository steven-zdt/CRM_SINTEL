// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * bancos.api.js - Wrapper de API Bancos
 * Namespace: window.Sintel.Bancos.API
 * ⚠️ API-First: Consume DRF REST API (v3.9.1)
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 */
(function(w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};

  const API_BASE = '/api/v1/bancos';
  const MOD = 'bancos.api';

  // F32.7: Lazy, verificar Sintel.Core.Http en cada llamada (antes: window.http),
  // no al cargar el modulo -- el modulo puede cargar antes que core-http.js en
  // algunos contextos HTMX.
  function callHttp(method, url, data) {
    if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
      console.error(`[${MOD}] Sintel.Core.Http no disponible al llamar ${method} ${url}`);
      return Promise.resolve({ ok: false, status: 503, data: { detail: 'Sintel.Core.Http no disponible' } });
    }
    return w.Sintel.Core.Http.request(method, url, data);
  }

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

  w.Sintel.Bancos.API = {
    cuentas: {
      list: async (params = {}) => {
        console.log(`[${MOD}] cuentas.list()`, params);
        return callHttp('GET', buildUrlWithParams(`${API_BASE}/cuentas/`, params));
      },
      get: async (uuid) => {
        console.log(`[${MOD}] cuentas.get(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('GET', `${API_BASE}/cuentas/${uuid}/`);
      },
      save: async (payload) => {
        console.log(`[${MOD}] cuentas.save()`, payload);
        return callHttp('POST', `${API_BASE}/cuentas/`, payload);
      },
      update: async (uuid, payload) => {
        console.log(`[${MOD}] cuentas.update(${uuid})`, payload);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('PUT', `${API_BASE}/cuentas/${uuid}/`, payload);
      },
      delete: async (uuid) => {
        console.log(`[${MOD}] cuentas.delete(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('DELETE', `${API_BASE}/cuentas/${uuid}/`);
      }
    },

    extractos: {
      list: async (params = {}) => {
        console.log(`[${MOD}] extractos.list()`, params);
        return callHttp('GET', buildUrlWithParams(`${API_BASE}/extractos/`, params));
      },
      get: async (uuid) => {
        console.log(`[${MOD}] extractos.get(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('GET', `${API_BASE}/extractos/${uuid}/`);
      },
      save: async (formData) => {
        console.log(`[${MOD}] extractos.save() (FormData)`);
        if (!(formData instanceof FormData)) {
          return { ok: false, status: 400, data: { detail: 'Se requiere un objeto FormData' } };
        }
        return callHttp('POST', `${API_BASE}/extractos/`, formData);
      },
      delete: async (uuid) => {
        console.log(`[${MOD}] extractos.delete(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('DELETE', `${API_BASE}/extractos/${uuid}/`);
      },
      procesar: async (uuid, forzar = false) => {
        console.log(`[${MOD}] extractos.procesar(${uuid}, forzar=${forzar})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('POST', `${API_BASE}/extractos/${uuid}/procesar/`, { forzar: !!forzar });
      },
    },

    transacciones: {
      list: async (params = {}) => {
        console.log(`[${MOD}] transacciones.list()`, params);
        return callHttp('GET', buildUrlWithParams(`${API_BASE}/transacciones/`, params));
      },
      get: async (uuid) => {
        console.log(`[${MOD}] transacciones.get(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('GET', `${API_BASE}/transacciones/${uuid}/`);
      },
      conciliar: async (uuid, payload) => {
        console.log(`[${MOD}] transacciones.conciliar(${uuid})`, payload);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('PATCH', `${API_BASE}/transacciones/${uuid}/conciliar/`, payload);
      },
      sugerencias: async (uuid) => {
        console.log(`[${MOD}] transacciones.sugerencias(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('GET', `${API_BASE}/transacciones/${uuid}/sugerencias/`);
      },
      listarAplicaciones: async (uuid) => {
        console.log(`[${MOD}] transacciones.listarAplicaciones(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('GET', `${API_BASE}/transacciones/${uuid}/aplicaciones/`);
      },
      crearAplicacion: async (uuid, payload) => {
        console.log(`[${MOD}] transacciones.crearAplicacion(${uuid})`, payload);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('POST', `${API_BASE}/transacciones/${uuid}/aplicaciones/`, payload);
      },
    },

    aplicaciones: {
      editar: async (uuid, payload) => {
        console.log(`[${MOD}] aplicaciones.editar(${uuid})`, payload);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('PATCH', `${API_BASE}/aplicaciones/${uuid}/`, payload);
      },
      eliminar: async (uuid) => {
        console.log(`[${MOD}] aplicaciones.eliminar(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return callHttp('DELETE', `${API_BASE}/aplicaciones/${uuid}/`);
      },
    },
  };

  // Deprecated fallback for routing
  w.bancosAPI = w.Sintel.Bancos.API;

  console.log(`[${MOD}] API inicializada correctamente.`);
})(window);
