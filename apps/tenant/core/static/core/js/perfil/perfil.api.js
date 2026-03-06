/**
 * API Wrapper para Perfil v2.40
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/perfil/perfiles/ (lista de perfiles - paginada)
 * - GET /api/v1/perfil/perfiles/{id}/ (detalle de perfil)
 * - GET /api/v1/perfil/perfiles/me/ (perfil del usuario actual)
 * - PATCH /api/v1/perfil/perfiles/me/ (actualizar perfil del usuario)
 * - PATCH /api/v1/perfil/perfiles/me/configuracion/ (configuración)
 * - PATCH /api/v1/perfil/perfiles/me/avatar/ (avatar)
 */

(function() {
  'use strict';

  if (typeof window.http !== 'function') {
    console.error('[perfil.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }

  const API_BASE = '/api/v1/perfil/perfiles';
  const CORE_API_BASE = '/api/v1/core';

  /**
   * Obtiene lista de perfiles (paginada)
   * @param {Object} params - Parámetros de consulta (page, page_size, search, etc.)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function list(params = {}) {
    return await window.http('GET', `${API_BASE}/`, params);
  }

  /**
   * Obtiene detalle de un perfil por ID
   * @param {number} id - ID del perfil
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function get(id) {
    return await window.http('GET', `${API_BASE}/${id}/`);
  }

  /**
   * Obtiene el perfil del usuario actual (me)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getMiPerfil() {
    return await window.http('GET', `${API_BASE}/me/`);
  }

  /**
   * Actualiza el perfil del usuario
   * @param {Object} payload - Datos a actualizar
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function updateMiPerfil(payload) {
    return await window.http('PATCH', `${API_BASE}/me/`, payload);
  }

  /**
   * Actualiza un perfil por ID
   * @param {number} id - ID del perfil
   * @param {Object} payload - Datos a actualizar
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function update(id, payload) {
    return await window.http('PATCH', `${API_BASE}/${id}/`, payload);
  }

  /**
   * Actualiza la configuración del perfil
   * @param {Object} payload - Configuración (JSON)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function updateMiPerfilConfiguracion(payload) {
    return await window.http('PATCH', `${API_BASE}/me/configuracion/`, payload);
  }

  /**
   * Actualiza el avatar del usuario
   * @param {File} file - Archivo de imagen
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function updateMiPerfilAvatar(file) {
    const formData = new FormData();
    formData.append('avatar', file);
    return await window.http('PATCH', `${API_BASE}/me/avatar/`, formData);
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.perfilAPI = {
      list,  // ⚠️ v2.40: Nueva función para lista paginada
      get,   // ⚠️ v2.40: Nueva función para obtener por ID
      getMiPerfil,
      updateMiPerfil,
      update,  // ⚠️ v2.40: Nueva función para actualizar por ID
      updateMiPerfilConfiguracion,
      updateMiPerfilAvatar,
    };
  }
})();
