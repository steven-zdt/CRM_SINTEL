/**
 * API Wrapper para MailDigester
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/core/maildigester/configs/ (listar configuraciones)
 * - GET /api/v1/core/maildigester/runs/ (listar ejecuciones)
 * - POST /api/v1/core/maildigester/run/ (iniciar ejecución)
 * - POST /api/v1/core/maildigester/run/{run_id}/stop/ (detener ejecución)
 * - GET /api/v1/core/maildigester/run/{run_id}/details/ (detalles de ejecución)
 * - DELETE /api/v1/core/maildigester/run/{run_id}/ (eliminar ejecución)
 * - POST /api/v1/core/maildigester/configs/test/ (probar conexión)
 */

(function() {
  'use strict';

  // Asegurar que http() esté disponible
  if (typeof window.http !== 'function') {
    console.error('[mail.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }

  const API_BASE = '/api/v1/core/maildigester';

  /**
   * Lista configuraciones de buzones activas
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function listConfigs() {
    return await window.http('GET', `${API_BASE}/configs/`);
  }

  /**
   * Lista ejecuciones de ingesta
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function listRuns() {
    return await window.http('GET', `${API_BASE}/runs/`);
  }

  /**
   * Inicia una ejecución de ingesta
   * @param {number} configId - ID de la configuración de buzón
   * @param {number} limitMessages - Límite de mensajes a procesar
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function run(configId, limitMessages = 50) {
    return await window.http('POST', `${API_BASE}/run/`, {
      config_id: configId,
      limit_messages: limitMessages,
    });
  }

  /**
   * Detiene una ejecución
   * @param {number} runId - ID de la ejecución
   * @param {boolean} force - Forzar detención
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function stop(runId, force = false) {
    return await window.http('POST', `${API_BASE}/run/${runId}/stop/`, {
      force: force,
    });
  }

  /**
   * Obtiene detalles de una ejecución
   * @param {number} runId - ID de la ejecución
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getRunDetails(runId) {
    return await window.http('GET', `${API_BASE}/run/${runId}/details/`);
  }

  /**
   * Elimina una ejecución
   * @param {number} runId - ID de la ejecución
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function deleteRun(runId) {
    return await window.http('DELETE', `${API_BASE}/run/${runId}/`);
  }

  /**
   * Prueba conexión a un buzón (sin persistir)
   * @param {Object} config - Configuración del buzón
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function testConfig(config) {
    return await window.http('POST', `${API_BASE}/configs/test/`, config);
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.mailAPI = {
      listConfigs,
      listRuns,
      run,
      stop,
      getRunDetails,
      deleteRun,
      testConfig,
    };
  }
})();
