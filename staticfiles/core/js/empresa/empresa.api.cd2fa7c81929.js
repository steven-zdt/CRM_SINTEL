/**
 * Legacy copy of empresa.api.js (synchronized from app-level static)
 */
(function() {
  'use strict';

  if (typeof window.http !== 'function') {
    console.error('[empresa.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }

  const API_BASE = '/api/v1';
  const CORE_API_BASE = '/api/v1/core';

  async function getMiEmpresa() {
    return await window.http('GET', `${CORE_API_BASE}/empresa/`);
  }

  async function listEmpresas() {
    return await window.http('GET', `${API_BASE}/empresas/`);
  }

  async function getEmpresa(id) {
    return await window.http('GET', `${API_BASE}/empresas/${id}/`);
  }

  async function createEmpresa(payload) {
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

    return await window.http('POST', `${API_BASE}/empresas/`, formData);
  }

  async function updateEmpresa(id, payload) {
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

  async function deleteEmpresa(id) {
    return await window.http('DELETE', `${API_BASE}/empresas/${id}/`);
  }

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
