/**
 * proveedores.api.js - Capa de Datos Proveedores v2.61
 * [INFO] Auditor ACE: Retorna siempre {ok, status, data} compatible con UIManager.
 */
(function (w) {
  'use strict';

  const API_URL = '/api/v1/proveedores/';

  /**
   * Normalización Zero Trust de Payloads
   */
  function normalizePayload(data) {
    const p = Object.assign({}, data || {});
    
    // Normalización de Identificación (SSoT: numero_documento)
    p.numero_documento = String(p.numero_documento || '').trim();
    
    // Normalización de booleanos
    ['responsable_iva', 'gran_contribuyente', 'autoretenedor', 'activo'].forEach(f => {
      if (p[f] !== undefined) {
        p[f] = (p[f] === true || p[f] === 'true' || p[f] === 'on' || p[f] === 1);
      }
    });

    return p;
  }

  const proveedoresAPI = {
    list: (params) => w.http('GET', API_URL, params),
    get: (id) => w.http('GET', `${API_URL}${id}/`),
    create: (data) => w.http('POST', API_URL, normalizePayload(data)),
    update: (id, data) => w.http('PATCH', `${API_URL}${id}/`, normalizePayload(data)),
    delete: (id) => w.http('DELETE', `${API_URL}${id}/`),
    searchCuentas: (q) => w.http('GET', `/api/v1/contabilidad/cuentas-contables/?search=${encodeURIComponent(q)}&app_origen=proveedores&activa=true`),
    getCuentaByUuid: (uuid) => w.http('GET', `/api/v1/contabilidad/cuentas-contables/?uuid=${encodeURIComponent(uuid)}&app_origen=proveedores`)
  };

  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.API = proveedoresAPI;

})(window);
