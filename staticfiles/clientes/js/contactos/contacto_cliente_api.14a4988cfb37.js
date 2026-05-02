/**
 * contacto_cliente_api.js - Wrapper de API Contactos de Clientes v2.61
 * Feature-Sliced: Capa de Datos independiente
 * Consume DRF endpoints:
 * - GET /api/v1/clientes/contactos/ (listar con paginación)
 * - POST /api/v1/clientes/contactos/ (crear contacto)
 * - GET /api/v1/clientes/contactos/{id}/ (detalle)
 * - PATCH /api/v1/clientes/contactos/{id}/ (actualizar)
 * - DELETE /api/v1/clientes/contactos/{id}/ (eliminar)
 * - GET /api/v1/clientes/contactos/render-offcanvas/crear/ (renderizar offcanvas de creación)
 * - GET /api/v1/clientes/contactos/{id}/render-offcanvas/editar/ (renderizar offcanvas de edición)
 * - GET /api/v1/clientes/contactos/render-offcanvas/detalle/?id={id} (renderizar offcanvas de detalle)
 */
(function(w) {
  'use strict';

  w.AppContactoCliente = w.AppContactoCliente || {};
  
  if (typeof w.http !== 'function') {
    console.error('[contacto_cliente_api] http() no está disponible.');
    return;
  }
  
  const CONTACTOS_BASE = '/api/v1/clientes/contactos';

  // Inmutable API
  if (!w.contactosClienteAPI) {
    w.contactosClienteAPI = Object.freeze({
      list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${CONTACTOS_BASE}/?${query}` : `${CONTACTOS_BASE}/`;
        return w.http('GET', url);
      },
      get: (id) => w.http('GET', `${CONTACTOS_BASE}/${id}/`),
      create: (payload) => w.http('POST', `${CONTACTOS_BASE}/`, payload),
      update: (id, payload) => w.http('PATCH', `${CONTACTOS_BASE}/${id}/`, payload),
      delete: (id) => w.http('DELETE', `${CONTACTOS_BASE}/${id}/`),
      
      // HTMX offcanvas rendering
      renderCrear: () => w.http('GET', `${CONTACTOS_BASE}/render-offcanvas/crear/`),
      renderEditar: (id) => w.http('GET', `${CONTACTOS_BASE}/${id}/render-offcanvas/editar/`),
      renderDetalle: (id) => w.http('GET', `${CONTACTOS_BASE}/render-offcanvas/detalle/?id=${id}`)
    });
  }

  w.AppContactoCliente.api = w.contactosClienteAPI;
  
  console.log('[contacto_cliente_api] OK: contactosClienteAPI inicializado');
})(window);
