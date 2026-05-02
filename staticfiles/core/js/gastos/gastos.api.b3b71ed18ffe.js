/**
 * gastos.api.js - Wrapper de API Gastos v2.60
 * ⚠️ Aislamiento Gradual: Capa de Datos - Retorna siempre {ok, status, data}
 * Alineado con inmutabilidad estricta (no PUT/PATCH).
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/gastos/ (listar con filtros)
 * - POST /api/v1/gastos/ (crear - usa automáticamente resolución vigente)
 * - GET /api/v1/gastos/{id}/ (detalle)
 * - DELETE /api/v1/gastos/{id}/ (eliminar - rollback técnico)
 * - GET /api/v1/gastos/summary/ (resumen financiero neto)
 * - GET /api/v1/gastos/resoluciones/ (resoluciones DIAN vigentes - legacy)
 * - GET /api/v1/gastos/resolucion-activa/ (resolución vigente - v2.40)
 * - POST /api/v1/gastos/configurar-resolucion/ (configurar resolución - v2.40)
 * - POST /api/v1/gastos/{id}/anular/ (anulación legal)
 */
(function(w) {
  'use strict';
  
  // Asegurar que http() esté disponible
  if (typeof w.http !== 'function') {
    console.error('[gastos.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }
  
  const API_BASE = '/api/v1/gastos';
  const RESOLUCIONES_API_BASE = '/api/v1/resoluciones-dian';

  w.gastosAPI = {
    // Obtiene lista completa para Tabulator (v2.40)
    list: () => w.http('GET', `${API_BASE}/`),
    
    // Detalle completo (evidencia legal)
    get: (id) => w.http('GET', `${API_BASE}/${id}/`),
    
    // Resumen financiero neto (excluye anulados)
    summary: () => w.http('GET', `${API_BASE}/summary/`),
    
    // Resoluciones vigentes para el formulario (legacy, mantener compatibilidad)
    resoluciones: () => w.http('GET', `${API_BASE}/resoluciones/`),
    
    // ⚠️ v2.40: Obtiene la resolución activa (SSoT - solo una vigente)
    getResolucionActiva: () => w.http('GET', `${API_BASE}/resolucion-activa/`),
    
    // ⚠️ v2.40: Configura una nueva resolución DIAN
    setConfigResolucion: (payload) => w.http('POST', `${API_BASE}/configurar-resolucion/`, payload),

    // Creación inmutable
    create: (payload) => w.http('POST', `${API_BASE}/`, payload),

    // ⚠️ v2.40: Desactivar documento (paso previo obligatorio antes de anular)
    desactivar: (id) => w.http('POST', `${API_BASE}/${id}/desactivar/`),

    // Anulación legal (v2.40) - Solo si está desactivado
    anular: (id) => w.http('POST', `${API_BASE}/${id}/anular/`),

    // Rollback técnico
    delete: (id) => w.http('DELETE', `${API_BASE}/${id}/`)
  };

  // API dedicada para resolución DIAN (usada por módulos de resolución y gasto).
  w.resolucionesAPI = {
    list: () => w.http('GET', `${RESOLUCIONES_API_BASE}/`),
    get: (id) => w.http('GET', `${RESOLUCIONES_API_BASE}/${id}/`),
    create: (payload) => w.http('POST', `${RESOLUCIONES_API_BASE}/`, payload),
    delete: (id) => w.http('DELETE', `${RESOLUCIONES_API_BASE}/${id}/`),
    desactivar: (id) => w.http('POST', `${RESOLUCIONES_API_BASE}/${id}/desactivar/`),
    activa: () => w.http('GET', `${RESOLUCIONES_API_BASE}/activa/`)
  };
})(window);