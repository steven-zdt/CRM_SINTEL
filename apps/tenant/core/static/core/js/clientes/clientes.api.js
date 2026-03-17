/**
 * clientes.api.js - Wrapper de API Clientes v2.60
 * ⚠️ Aislamiento Gradual: Capa de Datos - Retorna siempre {ok, status, data}
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/clientes/ (listar con paginación y búsqueda)
 * - POST /api/v1/clientes/ (crear cliente)
 * - GET /api/v1/clientes/{id}/ (detalle completo)
 * - PATCH /api/v1/clientes/{id}/ (actualizar cliente)
 * - DELETE /api/v1/clientes/{id}/ (eliminar cliente)
 */
(function(w) {
  'use strict';
  
  if (typeof w.http !== 'function') {
    console.error('[clientes.api] http() no está disponible.');
    return;
  }
  
  const CLIENTES_BASE = '/api/v1/clientes';
  const CONTACTOS_BASE = '/api/v1/clientes/contactos';

  // ⚠️ Inmutable APIs
  if (!w.clientesAPI) {
    w.clientesAPI = Object.freeze({
      list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${CLIENTES_BASE}/?${query}` : `${CLIENTES_BASE}/`;
        return w.http('GET', url);
      },
      get: (id) => w.http('GET', `${CLIENTES_BASE}/${id}/`),
      create: (payload) => w.http('POST', `${CLIENTES_BASE}/`, payload),
      update: (id, payload) => w.http('PATCH', `${CLIENTES_BASE}/${id}/`, payload),
      delete: (id) => w.http('DELETE', `${CLIENTES_BASE}/${id}/`)
    });
  }

  if (!w.contactosAPI) {
    w.contactosAPI = Object.freeze({
      // Listado global
      list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${CONTACTOS_BASE}/?${query}` : `${CONTACTOS_BASE}/`;
        return w.http('GET', url);
      },
      // Listado por cliente
      listByCliente: (clienteId) => w.http('GET', `${CONTACTOS_BASE}/?cliente=${clienteId}`),
      
      get: (id) => w.http('GET', `${CONTACTOS_BASE}/${id}/`),
      create: (payload) => w.http('POST', `${CONTACTOS_BASE}/`, payload),
      update: (id, payload) => w.http('PATCH', `${CONTACTOS_BASE}/${id}/`, payload),
      delete: (id) => w.http('DELETE', `${CONTACTOS_BASE}/${id}/`)
    });
  }
  
  console.log('[clientes.api] ✅ clientesAPI y contactosAPI inmutables inicializados');
})(window);
