/**
 * API Wrapper para Dashboard
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/core/dashboard/ (dashboard completo)
 * - GET /api/v1/core/dashboard/sections/ (secciones)
 */

(function() {
  'use strict';

  if (typeof window.http !== 'function') {
    console.error('[dashboard.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }

  const CORE_API_BASE = '/api/v1/core';

  /**
   * Obtiene dashboard completo
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getDashboard() {
    return await window.http('GET', `${CORE_API_BASE}/dashboard/`);
  }

  /**
   * Obtiene secciones del dashboard
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getDashboardSections() {
    return await window.http('GET', `${CORE_API_BASE}/dashboard/sections/`);
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.dashboardAPI = {
      getDashboard,
      getDashboardSections,
    };
  }
})();
