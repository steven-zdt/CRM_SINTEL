/**
 * tipo_comprobante.api.js - Módulo API para TipoComprobante v3.5
 * ⚠️ Feature-Sliced Design: Encapsula todas las peticiones HTTP hacia endpoints de comprobantes
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 */
(function (w, d) {
  'use strict';

  const MOD = '[tipo_comprobante.api]';
  const API_BASE = '/api/v1/contabilidad/tipos-comprobante/';

  /**
   * Namespace del módulo API de TipoComprobante
   */
  const TipoComprobanteAPI = {
    /**
     * Obtiene la lista de tipos de comprobante
     */
    list: async function(params = {}) {
      const url = new URL(API_BASE, w.location.origin);
      if (params.activa !== undefined) url.searchParams.append('activa', params.activa);
      
      const response = await w.http('GET', url.pathname + url.search);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    },

    /**
     * Obtiene el detalle de un tipo de comprobante
     */
    retrieve: async function(id) {
      if (!id) throw new Error('ID requerido');
      const response = await w.http('GET', `${API_BASE}${id}/`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    }
  };

  // Exportar namespace global
  w.TipoComprobanteAPI = Object.freeze(TipoComprobanteAPI);

})(window, document);
