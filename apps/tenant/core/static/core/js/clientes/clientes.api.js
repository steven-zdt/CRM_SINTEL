/**
 * clientes.api.js - Wrapper de API Clientes v2.60
 * ⚠️ Aislamiento Gradual: Capa de Datos - Retorna siempre {ok, status, data}
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/clientes/ (listar con paginación y búsqueda)
 * - POST /api/v1/clientes/ (crear cliente)
 * - GET /api/v1/clientes/{id}/ (detalle completo)
 * - PATCH /api/v1/clientes/{id}/ (actualizar cliente)
 * - DELETE /api/v1/clientes/{id}/ (eliminar cliente)
 */
(function(w) {
  'use strict';
  
  // Asegurar que http() esté disponible
  if (typeof w.http !== 'function') {
    console.error('[clientes.api] http() no está disponible. Cargar lib/api.js primero.');
    return;
  }
  
  const API_BASE = '/api/v1/clientes';

  w.clientesAPI = {
    /**
     * Obtiene lista de clientes (paginada, con búsqueda)
     * @param {Object} params - Parámetros de consulta (page, page_size, search)
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      const url = query ? `${API_BASE}/?${query}` : `${API_BASE}/`;
      return w.http('GET', url);
    },
    
    /**
     * Obtiene detalle completo de un cliente
     * @param {number|string} id - ID del cliente
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    get: (id) => w.http('GET', `${API_BASE}/${id}/`),
    
    /**
     * Crea un nuevo cliente
     * @param {Object} payload - Datos del cliente
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    create: (payload) => w.http('POST', `${API_BASE}/`, payload),
    
    /**
     * Actualiza un cliente existente
     * @param {number|string} id - ID del cliente
     * @param {Object} payload - Datos a actualizar
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    update: (id, payload) => w.http('PATCH', `${API_BASE}/${id}/`, payload),
    
    /**
     * Elimina un cliente
     * @param {number|string} id - ID del cliente
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    delete: (id) => w.http('DELETE', `${API_BASE}/${id}/`)
  };

  const CONTACTOS_API = '/api/v1/clientes/contactos';

  /**
   * ⚠️ v2.61: Integración Maestro-Detalle - Directorio de Contactos
   */
  w.contactosAPI = {
    /**
     * Lista contactos de un cliente
     * @param {number|string} clienteId - ID del cliente
     */
    listByCliente: (clienteId) => w.http('GET', `${CONTACTOS_API}/?cliente=${clienteId}`),

    /**
     * Obtiene detalle de un contacto
     */
    get: (id) => w.http('GET', `${CONTACTOS_API}/${id}/`),

    /**
     * Crea un contacto
     */
    create: (payload) => w.http('POST', `${CONTACTOS_API}/`, payload),

    /**
     * Actualiza un contacto
     */
    update: (id, payload) => w.http('PATCH', `${CONTACTOS_API}/${id}/`, payload),

    /**
     * Elimina un contacto
     */
    delete: (id) => w.http('DELETE', `${CONTACTOS_API}/${id}/`)
  };
  
  console.log('[clientes.api] ✅ Módulo clientesAPI y contactosAPI inicializados');
})(window);
