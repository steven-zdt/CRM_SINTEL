/**
 * retencion.api.js - SSoT de endpoints para Retencion v3.16.1
 *
 * Dependencias: window.http (http.js)
 */
(function (w) {
  'use strict';

  const MOD = '[retencion.api]';
  const API_BASE = '/api/v1/contabilidad/retenciones/';

  const RetencionAPI = {
    /**
     * Lista retenciones con filtros opcionales.
     * @param {Object} params
     * @param {string} [params.tipo]              - RETEFUENTE | RETEICA | RETEIVA
     * @param {string} [params.naturaleza]        - VENTA | COMPRA
     * @param {string} [params.reversada]         - 'true' | 'false'
     * @param {string} [params.documento_origen_app]
     * @param {string} [params.search]
     * @returns {Promise<Object>} Respuesta paginada DRF
     */
    list: async function (params) {
      const url = new URL(API_BASE, w.location.origin);
      if (params) {
        if (params.tipo)                url.searchParams.append('tipo',                params.tipo);
        if (params.naturaleza)          url.searchParams.append('naturaleza',          params.naturaleza);
        if (params.reversada !== undefined && params.reversada !== '')
                                        url.searchParams.append('reversada',           params.reversada);
        if (params.documento_origen_app) url.searchParams.append('documento_origen_app', params.documento_origen_app);
        if (params.search)              url.searchParams.append('search',              params.search);
      }
      const response = await w.http('GET', url.pathname + url.search);
      if (!response.ok) {
        const msg = response.data?.detail || `HTTP ${response.status}`;
        const err = new Error(msg);
        err.status = response.status;
        err.data = response.data;
        throw err;
      }
      return response.data;
    }
  };

  if (typeof w !== 'undefined') {
    w.RetencionAPI = Object.freeze(RetencionAPI);
  }
})(window);
