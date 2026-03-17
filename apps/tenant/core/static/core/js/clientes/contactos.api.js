/**
 * contactos.api.js - Wrapper de API Contactos v2.61
 * ⚠️ Aislamiento Gradual: Capa de Datos - Retorna siempre {ok, status, data}
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/clientes/contactos/ (listar con paginación y búsqueda)
 * - POST /api/v1/clientes/contactos/ (crear contacto)
 * - GET /api/v1/clientes/contactos/{id}/ (detalle completo)
 * - PATCH /api/v1/clientes/contactos/{id}/ (actualizar contacto)
 * - DELETE /api/v1/clientes/contactos/{id}/ (eliminar contacto)
 */
(function(w) {
  'use strict';
  
  // Asegurar que http() esté disponible
  if (typeof w.http !== 'function') {
    console.error('[contactos.api] http() no está disponible. Cargar lib/api.js primero.');
    return;
  }
  
  const API_BASE = '/api/v1/clientes/contactos';

  w.contactosAPI = {
    /**
     * Obtiene lista de contactos (paginada, con búsqueda)
     * @param {Object} params - Parámetros de consulta (page, page_size, search)
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      const url = query ? `${API_BASE}/?${query}` : `${API_BASE}/`;
      return w.http('GET', url);
    },
    
    /**
     * Obtiene detalle completo de un contacto
     * @param {number|string} id - ID del contacto
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    get: (id) => w.http('GET', `${API_BASE}/${id}/`),
    
    /**
     * Crea un nuevo contacto
     * @param {Object} payload - Datos del contacto
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    create: (payload) => w.http('POST', `${API_BASE}/`, payload),
    
    /**
     * Actualiza un contacto existente
     * @param {number|string} id - ID del contacto
     * @param {Object} payload - Datos a actualizar
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    update: (id, payload) => w.http('PATCH', `${API_BASE}/${id}/`, payload),
    
    /**
     * Elimina un contacto
     * @param {number|string} id - ID del contacto
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    delete: (id) => w.http('DELETE', `${API_BASE}/${id}/`)
  };
  
  console.log('[contactos.api] ✅ Módulo contactosAPI inicializado correctamente');
})(window);
