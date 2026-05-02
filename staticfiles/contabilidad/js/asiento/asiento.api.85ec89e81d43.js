/**
 * asiento.api.js - Módulo API para AsientoContable v2.60
 * ⚠️ Feature-Sliced Design: Encapsula todas las peticiones HTTP hacia endpoints DRF
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API exclusivamente
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en http.js)
 */
(function (w, d) {
  'use strict';

  const MOD = '[asiento.api]';
  const API_BASE = '/api/v1/contabilidad/asientos-contables/';

  /**
   * Namespace del módulo API de AsientoContable
   */
  const AsientoAPI = {
    /**
     * Obtiene la lista de asientos contables (paginada)
     * @param {Object} params - Parámetros de paginación y filtrado
     * @returns {Promise<Object>} Respuesta de la API
     */
    list: async function(params = {}) {
      const url = new URL(API_BASE, w.location.origin);
      if (params.page) url.searchParams.append('page', params.page);
      if (params.page_size) url.searchParams.append('page_size', params.page_size);
      if (params.search) url.searchParams.append('search', params.search);
      if (params.estado) url.searchParams.append('estado', params.estado);
      if (params.fecha) url.searchParams.append('fecha', params.fecha);

      const response = await w.http('GET', url.pathname + url.search);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    },

    /**
     * Obtiene el detalle de un asiento contable por ID
     * @param {number} id - ID del asiento
     * @returns {Promise<Object>} Datos del asiento
     */
    retrieve: async function(id) {
      if (!id) throw new Error('ID de asiento requerido');
      
      const response = await w.http('GET', `${API_BASE}${id}/`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    },

    /**
     * Crea un nuevo asiento contable
     * @param {Object} data - Datos del asiento (debe incluir movimientos)
     * @returns {Promise<Object>} Asiento creado
     * @throws {Object} Error con estructura { ok: false, status: number, data: object }
     */
    create: async function(data) {
      const response = await w.http('POST', API_BASE, data);
      if (!response.ok) {
        // ⚠️ v2.60: Lanzar response completo para que error_injector.js pueda procesarlo
        const error = new Error(response.data?.message || response.data?.detail || 'Error al crear asiento');
        error.status = response.status;
        error.data = response.data;
        error.response = response; // Mantener referencia completa
        throw error;
      }
      return response.data;
    },

    /**
     * Actualiza un asiento contable existente
     * @param {number} id - ID del asiento
     * @param {Object} data - Datos a actualizar (puede incluir movimientos)
     * @returns {Promise<Object>} Asiento actualizado
     * @throws {Object} Error con estructura { ok: false, status: number, data: object }
     */
    update: async function(id, data) {
      if (!id) throw new Error('ID de asiento requerido');
      
      const response = await w.http('PATCH', `${API_BASE}${id}/`, data);
      if (!response.ok) {
        // ⚠️ v2.60: Lanzar response completo para que error_injector.js pueda procesarlo
        const error = new Error(response.data?.message || response.data?.detail || 'Error al actualizar asiento');
        error.status = response.status;
        error.data = response.data;
        error.response = response; // Mantener referencia completa
        throw error;
      }
      return response.data;
    },

    /**
     * Elimina un asiento contable
     * @param {number} id - ID del asiento
     * @returns {Promise<void>}
     */
    delete: async function(id) {
      if (!id) throw new Error('ID de asiento requerido');
      
      const response = await w.http('DELETE', `${API_BASE}${id}/`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
    },

    /**
     * Aprueba un asiento contable
     * @param {number} id - ID del asiento
     * @returns {Promise<Object>} Asiento aprobado
     * @throws {Object} Error con estructura { ok: false, status: number, data: object }
     *                  Si status=422, data contiene detalles de cuadratura para error_injector.js
     */
    aprobar: async function(id) {
      if (!id) throw new Error('ID de asiento requerido');
      
      const response = await w.http('POST', `${API_BASE}${id}/aprobar/`);
      if (!response.ok) {
        // ⚠️ v2.60: Lanzar response completo para que error_injector.js pueda procesarlo
        const error = new Error(response.data?.message || response.data?.detail || 'Error al aprobar asiento');
        error.status = response.status;
        error.data = response.data;
        error.response = response; // Mantener referencia completa
        throw error;
      }
      return response.data;
    },

    /**
     * Obtiene documentos sin asiento (facturas y gastos)
     * @param {string} tipo - 'facturas' o 'gastos' (opcional)
     * @returns {Promise<Object>} Lista de documentos sin asiento
     */
    documentosSinAsiento: async function(tipo = '') {
      const url = new URL(`${API_BASE}documentos-sin-asiento/`, w.location.origin);
      if (tipo) url.searchParams.append('tipo', tipo);

      const response = await w.http('GET', url.pathname + url.search);
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      return response.data;
    },

    /**
     * Crea asientos desde documentos seleccionados
     * @param {Array} facturasIds - IDs de facturas
     * @param {Array} gastosIds - IDs de gastos
     * @returns {Promise<Object>} Resultado de la creación
     * @throws {Object} Error con estructura { ok: false, status: number, data: object }
     */
    crearDesdeDocumentos: async function(facturasIds = [], gastosIds = []) {
      const response = await w.http('POST', `${API_BASE}crear-desde-documentos/`, {
        facturas: facturasIds,
        gastos: gastosIds
      });
      if (!response.ok) {
        // ⚠️ v2.60: Lanzar response completo para que error_injector.js pueda procesarlo
        const error = new Error(response.data?.message || response.data?.detail || 'Error al crear asientos desde documentos');
        error.status = response.status;
        error.data = response.data;
        error.response = response; // Mantener referencia completa
        throw error;
      }
      return response.data;
    }
  };

  // Exportar namespace global
  if (typeof w !== 'undefined') {
    w.AsientoAPI = Object.freeze(AsientoAPI);
  }
})(window, document);
