/**
 * API Wrapper para Landing
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/core/landing/info/ (información pública)
 * - GET /api/v1/core/landing/resumen/ (resumen)
 */

(function() {
  'use strict';

  if (typeof window.http !== 'function') {
    console.error('[landing.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }

  const CORE_API_BASE = '/api/v1/core';

  async function getLandingInfo() {
    return await window.http('GET', `${CORE_API_BASE}/landing/info/`);
  }

  async function getLandingResumen() {
    return await window.http('GET', `${CORE_API_BASE}/landing/resumen/`);
  }

  if (typeof window !== 'undefined') {
    window.landingAPI = {
      getLandingInfo,
      getLandingResumen,
    };
  }
})();
