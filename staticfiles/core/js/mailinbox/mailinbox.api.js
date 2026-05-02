/**
 * mailinbox.api.js - Wrapper de API MailInboxConfig v2.60
 * ⚠️ Aislamiento Gradual: Capa de Datos - Retorna {ok, status, data}
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/empresas/mail-inbox-config/ (listar)
 * - POST /api/v1/empresas/mail-inbox-config/ (crear)
 * - GET /api/v1/empresas/mail-inbox-config/{id}/ (detalle)
 * - PUT /api/v1/empresas/mail-inbox-config/{id}/ (actualizar)
 * - DELETE /api/v1/empresas/mail-inbox-config/{id}/ (eliminar)
 * - POST /api/v1/empresas/mail-inbox-config/{id}/test-connection/ (probar conexión)
 */
(function(w) {
  'use strict';
  
  // Asegurar que http() esté disponible
  if (typeof w.http !== 'function') {
    console.error('[mailinbox.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }
  
  const API_BASE = '/api/v1/empresas/mail-inbox-config';

  w.mailinboxAPI = {
    /**
     * Obtiene lista de configuraciones (paginada, con búsqueda)
     * @param {Object} params - Parámetros de consulta (page, page_size, search)
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      const url = query ? `${API_BASE}/?${query}` : `${API_BASE}/`;
      return w.http('GET', url);
    },
    
    /**
     * Obtiene detalle de una configuración
     * @param {number} id - ID de la configuración
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    get: (id) => w.http('GET', `${API_BASE}/${id}/`),
    
    /**
     * Crea una nueva configuración
     * @param {Object} payload - Datos de la configuración
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    create: (payload) => w.http('POST', `${API_BASE}/`, payload),
    
    /**
     * Actualiza una configuración existente
     * @param {number} id - ID de la configuración
     * @param {Object} payload - Datos a actualizar
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    update: (id, payload) => w.http('PUT', `${API_BASE}/${id}/`, payload),
    
    /**
     * Elimina una configuración
     * @param {number} id - ID de la configuración
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    delete: (id) => w.http('DELETE', `${API_BASE}/${id}/`),
    
    /**
     * Prueba la conexión IMAP de una configuración
     * @param {number} id - ID de la configuración
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    testConnection: (id) => w.http('POST', `${API_BASE}/${id}/test-connection/`),
    
    /**
     * Prueba la conexión IMAP con datos proporcionados directamente
     * @param {Object} testData - Datos de prueba (host, port, username, password, etc.)
     * @returns {Promise<{ok: boolean, status: number, data: any}>}
     */
    testConnectionWithData: (testData) => w.http('POST', `${API_BASE}/test-connection/`, testData)
  };
  
  console.log('[mailinbox.api] ✅ Módulo mailinboxAPI inicializado correctamente');
})(window);
