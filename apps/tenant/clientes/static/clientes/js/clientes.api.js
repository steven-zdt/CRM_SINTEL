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

  w.AppCliente = w.AppCliente || {};
  
  if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
    console.error('[clientes.api] Sintel.Core.Http no está disponible.');
    return;
  }
  
  const CLIENTES_BASE = '/api/v1/clientes';
  const CONTACTOS_BASE = '/api/v1/clientes/contactos';
  const CARTERA_BASE = '/api/v1/clientes/cartera';

  // ⚠️ Inmutable APIs
  if (!w.clientesAPI) {
    w.clientesAPI = Object.freeze({
      list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${CLIENTES_BASE}/?${query}` : `${CLIENTES_BASE}/`;
        return w.Sintel.Core.Http.request('GET', url);
      },
      get: (id) => w.Sintel.Core.Http.request('GET', `${CLIENTES_BASE}/${id}/`),
      create: (payload) => w.Sintel.Core.Http.request('POST', `${CLIENTES_BASE}/`, payload),
      update: (id, payload) => w.Sintel.Core.Http.request('PATCH', `${CLIENTES_BASE}/${id}/`, payload),
      delete: (id) => w.Sintel.Core.Http.request('DELETE', `${CLIENTES_BASE}/${id}/`),
      
      // [v3.5.0] Buscador de cuentas PUC por texto (autocompletar)
      searchCuentas: (search = '') => {
        const url = `/api/v1/contabilidad/cuentas-contables/?search=${encodeURIComponent(search)}&app_origen=clientes&solo_auxiliares=true`;
        return w.Sintel.Core.Http.request('GET', url);
      },
      // [v3.6.1] Resolver nombre de cuenta por UUID — §18: consumo HTTP, no import Python
      getCuentaByUuid: (uuid = '') => {
        const url = `/api/v1/contabilidad/cuentas-contables/?uuid=${encodeURIComponent(uuid)}&app_origen=clientes`;
        return w.Sintel.Core.Http.request('GET', url);
      }
    });
  }

  if (!w.contactosAPI) {
    w.contactosAPI = Object.freeze({
      // Listado global
      list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${CONTACTOS_BASE}/?${query}` : `${CONTACTOS_BASE}/`;
        return w.Sintel.Core.Http.request('GET', url);
      },
      // Listado por cliente
      listByCliente: (clienteId) => w.Sintel.Core.Http.request('GET', `${CONTACTOS_BASE}/?cliente=${clienteId}`),
      
      get: (id) => w.Sintel.Core.Http.request('GET', `${CONTACTOS_BASE}/${id}/`),
      create: (payload) => w.Sintel.Core.Http.request('POST', `${CONTACTOS_BASE}/`, payload),
      update: (id, payload) => w.Sintel.Core.Http.request('PATCH', `${CONTACTOS_BASE}/${id}/`, payload),
      delete: (id) => w.Sintel.Core.Http.request('DELETE', `${CONTACTOS_BASE}/${id}/`)
    });
  }

  if (!w.carteraAPI) {
    w.carteraAPI = Object.freeze({
      list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${CARTERA_BASE}/?${query}` : `${CARTERA_BASE}/`;
        return w.Sintel.Core.Http.request('GET', url);
      },
      get: (id) => w.Sintel.Core.Http.request('GET', `${CARTERA_BASE}/${id}/`),
      kpis: () => w.Sintel.Core.Http.request('GET', `${CARTERA_BASE}/kpis/`),
      registrarAbono: (id, payload) => w.Sintel.Core.Http.request('POST', `${CARTERA_BASE}/${id}/registrar-abono/`, payload)
    });
  }

  w.AppCliente.api = w.clientesAPI;
  w.AppCliente.contactosApi = w.contactosAPI;
  w.AppCliente.carteraApi = w.carteraAPI;
  
  console.log('[clientes.api] ✅ clientesAPI, contactosAPI y carteraAPI inmutables inicializados');
})(window);
