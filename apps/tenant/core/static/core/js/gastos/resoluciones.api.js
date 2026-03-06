/**
 * resoluciones.api.js - Wrapper de API Resoluciones DIAN v2.40
 * 
 * ⚠️ v2.40: ViewSet independiente para Resoluciones DIAN
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/resoluciones-dian/ (listar)
 * - POST /api/v1/resoluciones-dian/ (crear)
 * - GET /api/v1/resoluciones-dian/{id}/ (detalle)
 * - DELETE /api/v1/resoluciones-dian/{id}/ (eliminar - solo si no tiene Documentos de Soporte)
 * - POST /api/v1/resoluciones-dian/{id}/desactivar/ (desactivar)
 * - GET /api/v1/resoluciones-dian/activa/ (resolución vigente)
 */
(function(w) {
  'use strict';
  
  // Asegurar que http() esté disponible
  if (typeof w.http !== 'function') {
    console.error('[resoluciones.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }
  
  const API_BASE = '/api/v1/resoluciones-dian';

  w.resolucionesAPI = {
    // Obtiene lista completa para Tabulator (v2.40)
    list: () => w.http('GET', `${API_BASE}/`),
    
    // Detalle completo
    get: (id) => w.http('GET', `${API_BASE}/${id}/`),
    
    // Crear nueva resolución
    create: (payload) => w.http('POST', `${API_BASE}/`, payload),
    
    // Desactivar resolución
    desactivar: (id) => w.http('POST', `${API_BASE}/${id}/desactivar/`),
    
    // Eliminar resolución (solo si no tiene Documentos de Soporte)
    delete: (id) => w.http('DELETE', `${API_BASE}/${id}/`),
    
    // Obtiene la resolución activa (SSoT - solo una vigente)
    getActiva: () => w.http('GET', `${API_BASE}/activa/`)
  };
})(window);
