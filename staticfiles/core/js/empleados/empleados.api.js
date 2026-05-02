/**
 * empleados.api.js - Wrapper de API Empleados v2.60
 * ⚠️ Aislamiento Gradual: Capa de Datos - Retorna siempre {ok, status, data}
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * 
 * Dependencias:
 * - window.http (definido en lib/http.js)
 */
(function(w) {
  'use strict';

  const API_BASE = '/api/v1/empleados';

  // Verificar que window.http esté disponible
  if (typeof w.http !== 'function') {
    console.error('[empleados.api] window.http no está disponible. Cargar lib/http.js primero.');
    w.empleadosAPI = {
      error: 'window.http no está disponible'
    };
    return;
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

  w.empleadosAPI = {
      // --- Empleados ---
      list: (params = {}) => w.http('GET', buildUrlWithParams(`${API_BASE}/`, params)),
      get: (id) => w.http('GET', `${API_BASE}/${id}/`),
      save: (payload) => w.http('POST', `${API_BASE}/`, payload),
      update: (id, payload) => w.http('PATCH', `${API_BASE}/${id}/`, payload),
      delete: (id) => w.http('DELETE', `${API_BASE}/${id}/`),
      getSummary: () => w.http('GET', `${API_BASE}/summary/`),

      // --- Contratos ---
      listContratos: (params = {}) => w.http('GET', buildUrlWithParams(`${API_BASE}/contratos/`, params)),
      getContrato: (id) => w.http('GET', `${API_BASE}/contratos/${id}/`),
      saveContrato: (payload) => {
        // ⚠️ v2.95: Si payload es FormData, pasarlo directamente; si es objeto, convertir a FormData
        if (payload instanceof FormData) {
          return w.http('POST', `${API_BASE}/contratos/`, payload);
        }
        // Convertir objeto a FormData si tiene archivo
        const formData = new FormData();
        Object.keys(payload).forEach(key => {
          if (payload[key] !== null && payload[key] !== undefined) {
            formData.append(key, payload[key]);
          }
        });
        return w.http('POST', `${API_BASE}/contratos/`, formData);
      },
      updateContrato: (id, payload) => {
        if (payload instanceof FormData) {
          return w.http('PATCH', `${API_BASE}/contratos/${id}/`, payload);
        }
        const formData = new FormData();
        Object.keys(payload).forEach(key => {
          if (payload[key] !== null && payload[key] !== undefined) {
            formData.append(key, payload[key]);
          }
        });
        return w.http('PATCH', `${API_BASE}/contratos/${id}/`, formData);
      },
      getContratoActivo: (empleadoId) => w.http('GET', buildUrlWithParams(`${API_BASE}/contratos/`, { empleado: empleadoId, activo: true })),
      
      // --- Nómina (Devengos) ---
      // v2.95: Permite pasar filtros de fecha_inicio y fecha_fin
      listDevengos: (params = {}) => w.http('GET', buildUrlWithParams(`${API_BASE}/devengos/`, params)),
      getDevengosByEmpleado: (empleadoId, params = {}) => {
          const query = { ...params, empleado: empleadoId };
          return w.http('GET', buildUrlWithParams(`${API_BASE}/devengos/`, query));
      },
      getDevengo: (id) => w.http('GET', `${API_BASE}/devengos/${id}/`),
      previsualizarDevengo: (payload) => w.http('POST', `${API_BASE}/devengos/previsualizar/`, payload),
      saveDevengo: (payload) => {
        // ⚠️ v2.95: Si payload es FormData, pasarlo directamente; si es objeto, convertir a FormData
        if (payload instanceof FormData) {
          return w.http('POST', `${API_BASE}/devengos/`, payload);
        }
        // Convertir objeto a FormData
        const formData = new FormData();
        Object.keys(payload).forEach(key => {
          if (payload[key] !== null && payload[key] !== undefined) {
            formData.append(key, payload[key]);
          }
        });
        return w.http('POST', `${API_BASE}/devengos/`, formData);
      },
      anularDevengo: (id) => w.http('POST', `${API_BASE}/devengos/${id}/anular/`)
  };
})(window);