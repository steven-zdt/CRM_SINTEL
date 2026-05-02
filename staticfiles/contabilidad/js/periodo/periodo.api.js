/**
 * periodo.api.js - Módulo API para PeriodoContable v2.60
 * ⚠️ Feature-Sliced Design: Encapsula todas las peticiones HTTP hacia endpoints DRF
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API exclusivamente
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en http.js)
 */
(function (w, d) {
  'use strict';

  const MOD = '[periodo.api]';
  const API_BASE = '/api/v1/contabilidad/periodos-contables/';

  /**
   * Namespace del módulo API de PeriodoContable
   */
  const PeriodoAPI = {
    /**
     * Obtiene la lista de periodos contables (paginada)
     * @param {Object} params - Parámetros de paginación y filtrado
     * @returns {Promise<Object>} Respuesta de la API
     */
    list: async function(params = {}) {
      const url = new URL(API_BASE, w.location.origin);
      if (params.page) url.searchParams.append('page', params.page);
      if (params.page_size) url.searchParams.append('page_size', params.page_size);
      if (params.search) url.searchParams.append('search', params.search);
      if (params.estado) url.searchParams.append('estado', params.estado);

      const response = await w.http('GET', url.pathname + url.search);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    },

    /**
     * Obtiene el detalle de un periodo contable por ID
     * @param {number} id - ID del periodo
     * @returns {Promise<Object>} Datos del periodo
     */
    retrieve: async function(id) {
      if (!id) throw new Error('ID de periodo requerido');
      
      const response = await w.http('GET', `${API_BASE}${id}/`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    },

    /**
     * Crea un nuevo periodo contable
     * @param {Object} data - Datos del periodo
     * @returns {Promise<Object>} Periodo creado
     */
    create: async function(data) {
      const response = await w.http('POST', API_BASE, data);
      if (!response.ok) {
        throw response; // Lanzar response completo para manejo de errores
      }
      return response.data;
    },

    /**
     * Actualiza un periodo contable existente
     * @param {number} id - ID del periodo
     * @param {Object} data - Datos a actualizar
     * @returns {Promise<Object>} Periodo actualizado
     */
    update: async function(id, data) {
      if (!id) throw new Error('ID de periodo requerido');
      
      const response = await w.http('PATCH', `${API_BASE}${id}/`, data);
      if (!response.ok) {
        throw response; // Lanzar response completo para manejo de errores
      }
      return response.data;
    },

    /**
     * Elimina un periodo contable
     * @param {number} id - ID del periodo
     * @returns {Promise<void>}
     */
    delete: async function(id) {
      if (!id) throw new Error('ID de periodo requerido');
      
      const response = await w.http('DELETE', `${API_BASE}${id}/`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
    },

    /**
     * Cierra un periodo contable
     * @param {number} id - ID del periodo
     * @param {Object} data - Datos adicionales (observaciones, etc.)
     * @returns {Promise<Object>} Periodo cerrado
     */
    cerrar: async function(id, data = {}) {
      if (!id) throw new Error('ID de periodo requerido');
      
      const response = await w.http('POST', `${API_BASE}${id}/cerrar/`, data);
      if (!response.ok) {
        throw response; // Lanzar response completo para manejo de errores
      }
      return response.data;
    }
  };

  // Exportar namespace global
  if (typeof w !== 'undefined') {
    w.PeriodoAPI = Object.freeze(PeriodoAPI);
  }
})(window, document);
