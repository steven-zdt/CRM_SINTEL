/**
 * ⚠️ DEPRECATED v2.40: Este archivo NO se carga y NO debe usarse.
 * ⚠️ ENFORCED MODE: La UI debe usar SOLO PATCH /api/v1/core/empresa/ (Core Orchestrator).
 * 
 * LEGACY: no se carga en assets. Mantener solo como referencia histórica.
 * Módulo reemplazado por empresa.page.js + helpers globales (api-helpers.js).
 * 
 * API Wrapper para Empresa (SSoT) 
 * 
 * ⚠️ DEPRECATED ENDPOINTS (NO USAR DESDE UI):
 * - POST /api/v1/empresas/ (crear) → Usar PATCH /api/v1/core/empresa/
 * - PATCH /api/v1/empresas/{id}/ (actualizar) → Usar PATCH /api/v1/core/empresa/
 * - DELETE /api/v1/empresas/{id}/ (eliminar) → Solo STAFF/ADMIN
 * 
 * Endpoints permitidos (solo lectura):
 * - GET /api/v1/core/empresa/ (mi empresa)
 * - GET /api/v1/empresas/ (listar - singleton)
 */

(function() {
  'use strict';

  // Asegurar que http() esté disponible
  if (typeof window.http !== 'function') {
    console.error('[empresa.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }

  const API_BASE = '/api/v1';
  const CORE_API_BASE = '/api/v1/core';

  /**
   * Obtiene la empresa del tenant actual (mi empresa)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getMiEmpresa() {
    return await window.http('GET', `${CORE_API_BASE}/empresa/`);
  }

  /**
   * Lista empresas (singleton: retorna 0-1 elementos)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function listEmpresas() {
    return await window.http('GET', `${API_BASE}/empresas/`);
  }

  /**
   * Obtiene una empresa por ID
   * @param {number} id - ID de la empresa
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getEmpresa(id) {
    return await window.http('GET', `${API_BASE}/empresas/${id}/`);
  }

  /**
   * Crea una nueva empresa
   * ⚠️ DEPRECATED v2.40: Usa PATCH /api/v1/core/empresa/ en su lugar (Core Orchestrator).
   * Esta función retornará 405 para usuarios no-staff (ENFORCED MODE).
   * @param {Object} payload - Datos de la empresa
   * @param {File} [payload.logo] - Archivo de logo (opcional)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function createEmpresa(payload) {
    const formData = new FormData();
    
    // Agregar campos al FormData
    Object.keys(payload).forEach(key => {
      if (key === 'logo' && payload[key] instanceof File) {
        formData.append('logo', payload[key]);
      } else if (key === 'responsabilidades_rut_codigos' && Array.isArray(payload[key])) {
        formData.append(key, JSON.stringify(payload[key]));
      } else if (payload[key] !== null && payload[key] !== undefined) {
        formData.append(key, payload[key]);
      }
    });

    return await window.http('POST', `${API_BASE}/empresas/`, formData);
  }

  /**
   * Actualiza una empresa
   * @param {number} id - ID de la empresa
   * @param {Object} payload - Datos a actualizar
   * @param {File} [payload.logo] - Archivo de logo (opcional)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function updateEmpresa(id, payload) {
    // Usar Core API para actualización (más simple)
    const formData = new FormData();
    
    Object.keys(payload).forEach(key => {
      if (key === 'logo' && payload[key] instanceof File) {
        formData.append('logo', payload[key]);
      } else if (key === 'responsabilidades_rut_codigos' && Array.isArray(payload[key])) {
        formData.append(key, JSON.stringify(payload[key]));
      } else if (payload[key] !== null && payload[key] !== undefined) {
        formData.append(key, payload[key]);
      }
    });

    return await window.http('PATCH', `${CORE_API_BASE}/empresa/`, formData);
  }

  /**
   * Elimina una empresa
   * @param {number} id - ID de la empresa
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function deleteEmpresa(id) {
    return await window.http('DELETE', `${API_BASE}/empresas/${id}/`);
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.empresaAPI = {
      getMiEmpresa,
      listEmpresas,
      getEmpresa,
      createEmpresa,
      updateEmpresa,
      deleteEmpresa,
    };
  }
})();
