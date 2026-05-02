/**
 * API Wrapper para Contabilidad
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/core/contabilidad/cuentas/ (listar cuentas)
 * - POST /api/v1/core/contabilidad/cuentas/ (crear cuenta)
 * - GET /api/v1/core/contabilidad/cuentas/{id}/ (detalle cuenta)
 * - PATCH /api/v1/core/contabilidad/cuentas/{id}/ (actualizar cuenta)
 * - DELETE /api/v1/core/contabilidad/cuentas/{id}/ (eliminar cuenta)
 * - GET /api/v1/core/contabilidad/asientos/ (listar asientos)
 * - POST /api/v1/core/contabilidad/asientos/ (crear asiento)
 * - GET /api/v1/core/contabilidad/asientos/{id}/ (detalle asiento)
 * - PATCH /api/v1/core/contabilidad/asientos/{id}/ (actualizar asiento)
 * - POST /api/v1/core/contabilidad/asientos/{id}/aprobar/ (aprobar asiento)
 * - GET /api/v1/core/contabilidad/movimientos/ (listar movimientos)
 */

(function() {
  'use strict';

  if (typeof window.http !== 'function') {
    console.error('[contabilidad.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }

  const CORE_API_BASE = '/api/v1/core/contabilidad';

  // Cuentas
  async function listCuentas(params = {}) {
    const queryParams = new URLSearchParams();
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key]);
      }
    });
    const url = queryParams.toString() ? `${CORE_API_BASE}/cuentas/?${queryParams.toString()}` : `${CORE_API_BASE}/cuentas/`;
    return await window.http('GET', url);
  }

  async function getCuenta(id) {
    return await window.http('GET', `${CORE_API_BASE}/cuentas/${id}/`);
  }

  async function createCuenta(payload) {
    return await window.http('POST', `${CORE_API_BASE}/cuentas/`, payload);
  }

  async function updateCuenta(id, payload) {
    return await window.http('PATCH', `${CORE_API_BASE}/cuentas/${id}/`, payload);
  }

  async function deleteCuenta(id) {
    return await window.http('DELETE', `${CORE_API_BASE}/cuentas/${id}/`);
  }

  // Asientos
  async function listAsientos(params = {}) {
    const queryParams = new URLSearchParams();
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key]);
      }
    });
    const url = queryParams.toString() ? `${CORE_API_BASE}/asientos/?${queryParams.toString()}` : `${CORE_API_BASE}/asientos/`;
    return await window.http('GET', url);
  }

  async function getAsiento(id) {
    return await window.http('GET', `${CORE_API_BASE}/asientos/${id}/`);
  }

  async function createAsiento(payload) {
    return await window.http('POST', `${CORE_API_BASE}/asientos/`, payload);
  }

  async function updateAsiento(id, payload) {
    return await window.http('PATCH', `${CORE_API_BASE}/asientos/${id}/`, payload);
  }

  async function aprobarAsiento(id) {
    return await window.http('POST', `${CORE_API_BASE}/asientos/${id}/aprobar/`);
  }

  // Movimientos
  async function listMovimientos(params = {}) {
    const queryParams = new URLSearchParams();
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key]);
      }
    });
    const url = queryParams.toString() ? `${CORE_API_BASE}/movimientos/?${queryParams.toString()}` : `${CORE_API_BASE}/movimientos/`;
    return await window.http('GET', url);
  }

  if (typeof window !== 'undefined') {
    window.contabilidadAPI = {
      listCuentas,
      getCuenta,
      createCuenta,
      updateCuenta,
      deleteCuenta,
      listAsientos,
      getAsiento,
      createAsiento,
      updateAsiento,
      aprobarAsiento,
      listMovimientos,
    };
  }
})();
