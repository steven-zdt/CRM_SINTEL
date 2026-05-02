/**
 * cotizaciones.api.js - Wrapper de API Cotizaciones v2.60
 * ⚠️ Alineado con arquitectura API-First y endpoints de apps/tenant/cotizaciones/api/
 * ⚠️ Aislamiento Gradual v2.60: Capa de Datos - Retorna siempre {ok, status, data}
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/cotizaciones/ (listar con paginación y búsqueda)
 * - POST /api/v1/cotizaciones/ (crear preforma)
 * - GET /api/v1/cotizaciones/{uuid}/ (detalle completo con items)
 * - PATCH /api/v1/cotizaciones/{uuid}/ (actualizar)
 * - DELETE /api/v1/cotizaciones/{uuid}/ (eliminar)
 * - POST /api/v1/cotizaciones/{uuid}/recalcular/ (recalcular totales)
 * - GET /api/v1/cotizaciones/configuracion/ (listar perfiles de configuración)
 * - GET /api/v1/cotizaciones/items/ (listar items)
 * - POST /api/v1/cotizaciones/items/ (crear item)
 * - PATCH /api/v1/cotizaciones/items/{id}/ (actualizar item)
 * - DELETE /api/v1/cotizaciones/items/{id}/ (eliminar item)
 */
(function(w) {
  'use strict';
  
  // Asegurar que http() esté disponible
  if (typeof w.http !== 'function') {
    console.error('[cotizaciones.api] http() no está disponible. Cargar lib/api.js primero.');
    return;
  }
  
  const API_BASE = '/api/v1/cotizaciones';

  w.cotizacionesAPI = {
    /**
     * Obtiene lista de cotizaciones (paginada, con búsqueda)
     * @param {Object} params - Parámetros de consulta (page, page_size, search)
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      const url = query ? `${API_BASE}/?${query}` : `${API_BASE}/`;
      return w.http('GET', url);
    },
    
    /**
     * Obtiene detalle completo de una cotización (incluye items)
     * @param {string} uuid - UUID de la cotización
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    get: (uuid) => w.http('GET', `${API_BASE}/${uuid}/`),
    
    /**
     * Crea una nueva cotización (preforma)
     * @param {Object} payload - Datos de la cotización
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    create: (payload) => {
      // ⚠️ DEBUG: Verificar payload antes de enviar
      console.log('[cotizaciones.api] create() recibió payload:', payload);
      console.log('[cotizaciones.api] Tipo de cliente:', typeof payload?.cliente, 'Valor:', payload?.cliente);
      if (payload?.cliente !== undefined) {
        if (typeof payload.cliente === 'string' && payload.cliente.includes('(')) {
          console.error('[cotizaciones.api] ⚠️ ERROR CRÍTICO: El payload.cliente parece ser texto descriptivo:', payload.cliente);
        }
      }
      return w.http('POST', `${API_BASE}/`, payload);
    },
    
    /**
     * Actualiza una cotización existente
     * @param {string} uuid - UUID de la cotización
     * @param {Object} payload - Datos a actualizar
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    update: (uuid, payload) => w.http('PATCH', `${API_BASE}/${uuid}/`, payload),
    
    /**
     * Elimina una cotización
     * @param {string} uuid - UUID de la cotización
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    delete: (uuid) => w.http('DELETE', `${API_BASE}/${uuid}/`),
    
    /**
     * Recalcula los totales de una cotización
     * @param {string} uuid - UUID de la cotización
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    recalcular: (uuid) => w.http('POST', `${API_BASE}/${uuid}/recalcular/`),
    
    /**
     * Lista perfiles de configuración disponibles
     * @param {Object} params - Parámetros de consulta (page, page_size, search, es_activo)
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    listConfiguraciones: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      const url = query ? `${API_BASE}/configuracion/?${query}` : `${API_BASE}/configuracion/`;
      return w.http('GET', url);
    },
    
    /**
     * Obtiene un perfil de configuración por ID
     * @param {number} id - ID del perfil
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    getConfiguracion: (id) => w.http('GET', `${API_BASE}/configuracion/${id}/`),
    
    /**
     * Crea un nuevo perfil de configuración
     * @param {Object} payload - Datos del perfil
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    createConfiguracion: (payload) => w.http('POST', `${API_BASE}/configuracion/`, payload),
    
    /**
     * Actualiza un perfil de configuración
     * @param {number} id - ID del perfil
     * @param {Object} payload - Datos a actualizar
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    updateConfiguracion: (id, payload) => w.http('PATCH', `${API_BASE}/configuracion/${id}/`, payload),
    
    /**
     * Elimina un perfil de configuración
     * @param {number} id - ID del perfil
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    deleteConfiguracion: (id) => w.http('DELETE', `${API_BASE}/configuracion/${id}/`),
    
    /**
     * Activa un perfil de configuración
     * @param {number} id - ID del perfil
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    activarConfiguracion: (id) => w.http('POST', `${API_BASE}/configuracion/${id}/activar/`),
    
    // ========= Items de Cotización =========
    
    /**
     * Lista items de cotización
     * @param {Object} params - Parámetros de consulta (cotizacion, page, page_size)
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    listItems: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      const url = query ? `${API_BASE}/items/?${query}` : `${API_BASE}/items/`;
      return w.http('GET', url);
    },
    
    /**
     * Obtiene un item por ID
     * @param {number} id - ID del item
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    getItem: (id) => w.http('GET', `${API_BASE}/items/${id}/`),
    
    /**
     * Crea un nuevo item de cotización
     * ⚠️ AUTO-RECALCULO: El backend recalcula automáticamente los totales
     * @param {Object} payload - Datos del item (debe incluir cotizacion)
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    createItem: (payload) => w.http('POST', `${API_BASE}/items/`, payload),
    
    /**
     * Actualiza un item de cotización
     * ⚠️ AUTO-RECALCULO: El backend recalcula automáticamente los totales
     * @param {number} id - ID del item
     * @param {Object} payload - Datos a actualizar
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    updateItem: (id, payload) => w.http('PATCH', `${API_BASE}/items/${id}/`, payload),
    
    /**
     * Elimina un item de cotización
     * ⚠️ AUTO-RECALCULO: El backend recalcula automáticamente los totales
     * @param {number} id - ID del item
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    deleteItem: (id) => w.http('DELETE', `${API_BASE}/items/${id}/`)
  };
  
  console.log('[cotizaciones.api] ✅ Módulo cotizacionesAPI inicializado correctamente');
})(window);
