/**
 * cuenta.api.js - Módulo API para CuentaContable v2.60
 * ⚠️ Feature-Sliced Design: Encapsula todas las peticiones HTTP hacia endpoints DRF
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API exclusivamente
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en http.js)
 */
(function (w, d) {
  'use strict';

  const MOD = '[cuenta.api]';
  const API_BASE = '/api/v1/contabilidad/cuentas-contables/';

  /**
   * Namespace del módulo API de CuentaContable
   */
  const CuentaAPI = {
    /**
     * Obtiene la lista de cuentas contables (paginada)
     * @param {Object} params - Parámetros de paginación y filtrado
     * @returns {Promise<Object>} Respuesta de la API
     */
    list: async function(params = {}) {
      const url = new URL(API_BASE, w.location.origin);
      if (params.page) url.searchParams.append('page', params.page);
      if (params.page_size) url.searchParams.append('page_size', params.page_size);
      if (params.search) url.searchParams.append('search', params.search);
      if (params.tipo) url.searchParams.append('tipo', params.tipo);
      if (params.activa !== undefined) url.searchParams.append('activa', params.activa);

      const response = await w.http('GET', url.pathname + url.search);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    },

    /**
     * Obtiene el detalle de una cuenta contable por ID
     * @param {number} id - ID de la cuenta
     * @returns {Promise<Object>} Datos de la cuenta
     */
    retrieve: async function(id) {
      if (!id) throw new Error('ID de cuenta requerido');
      
      const response = await w.http('GET', `${API_BASE}${id}/`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    },

    /**
     * Crea una nueva cuenta contable
     * @param {Object} data - Datos de la cuenta
     * @returns {Promise<Object>} Cuenta creada
     * @throws {Object} Error con estructura { ok: false, status: number, data: object }
     */
    create: async function(data) {
      const response = await w.http('POST', API_BASE, data);
      if (!response.ok) {
        // ⚠️ v2.60: Lanzar response completo para que error_injector.js pueda procesarlo
        const error = new Error(response.data?.message || response.data?.detail || 'Error al crear cuenta');
        error.status = response.status;
        error.data = response.data;
        error.response = response; // Mantener referencia completa
        throw error;
      }
      return response.data;
    },

    /**
     * Actualiza una cuenta contable existente
     * @param {number} id - ID de la cuenta
     * @param {Object} data - Datos a actualizar
     * @returns {Promise<Object>} Cuenta actualizada
     * @throws {Object} Error con estructura { ok: false, status: number, data: object }
     */
    update: async function(id, data) {
      if (!id) throw new Error('ID de cuenta requerido');
      
      const response = await w.http('PATCH', `${API_BASE}${id}/`, data);
      if (!response.ok) {
        // ⚠️ v2.60: Lanzar response completo para que error_injector.js pueda procesarlo
        const error = new Error(response.data?.message || response.data?.detail || 'Error al actualizar cuenta');
        error.status = response.status;
        error.data = response.data;
        error.response = response; // Mantener referencia completa
        throw error;
      }
      return response.data;
    },

    /**
     * Elimina una cuenta contable
     * @param {number} id - ID de la cuenta
     * @returns {Promise<void>}
     */
    delete: async function(id) {
      if (!id) throw new Error('ID de cuenta requerido');
      
      const response = await w.http('DELETE', `${API_BASE}${id}/`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
    },

    /**
     * Obtiene la lista de cuentas para select (lookup)
     * @returns {Promise<Array>} Lista de cuentas para select
     */
    lookup: async function() {
      const response = await w.http('GET', API_BASE);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data.results || response.data;
    }
  };

  // Exportar namespace global
  if (typeof w !== 'undefined') {
    w.CuentaAPI = Object.freeze(CuentaAPI);
  }
})(window, document);
