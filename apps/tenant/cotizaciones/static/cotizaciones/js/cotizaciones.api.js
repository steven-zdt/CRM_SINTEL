/**
 * cotizaciones.api.js - SSoT de URLs y consumo de endpoints v2.62.0
 * Namespace: window.Sintel.Cotizaciones.api
 *
 * Gateway Directo: /api/v1/cotizaciones/
 */
(function (w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  var BASE = '/api/v1/cotizaciones';

  /**
   * Construye headers con JWT Bearer + CSRF.
   */
  function getHeaders() {
    var headers = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };
    var token = w.jwtAuth && typeof w.jwtAuth.getAccessToken === 'function'
      ? w.jwtAuth.getAccessToken()
      : null;
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    // CSRF cookie
    var csrfToken = (function () {
      var match = document.cookie.match(/csrftoken=([^;]+)/);
      return match ? match[1] : null;
    })();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
    return headers;
  }

  /**
   * Helper para peticiones asíncronas con manejo de errores estandarizado
   */
  async function request(url, options = {}) {
    options.headers = Object.assign(getHeaders(), options.headers || {});
    
    try {
      const response = await fetch(url, options);
      const data = await response.json();
      
      if (!response.ok) {
        throw { ok: false, status: response.status, data: data };
      }
      
      return data;
    } catch (error) {
      if (error.status) throw error;
      throw { ok: false, status: 500, data: { detail: error.message || 'Error de conexión' } };
    }
  }

  w.Sintel.Cotizaciones.api = {
    // URLs Cotizaciones
    listUrl:        BASE + '/',
    createUrl:      BASE + '/',
    detailUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    deleteUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    updateUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    recalcularUrl:  function (uuid) { return BASE + '/' + uuid + '/recalcular/'; },
    exportarPdfUrl: function (uuid) { return BASE + '/' + uuid + '/exportar-pdf/'; },
    estadisticasUrl: BASE + '/estadisticas/',
    
    // URLs Configuracion
    configuracionUrl: BASE + '/configuracion/',
    configuracionDetailUrl: function (uuid) { return BASE + '/configuracion/' + uuid + '/'; },
    
    // Métodos Configuracion
    createConfiguracion: function (data) {
      return request(this.configuracionUrl, {
        method: 'POST',
        body: JSON.stringify(data)
      });
    },
    updateConfiguracion: function (uuid, data) {
      return request(this.configuracionDetailUrl(uuid), {
        method: 'PATCH',
        body: JSON.stringify(data)
      });
    },
    deleteConfiguracion: function (uuid) {
      return request(this.configuracionDetailUrl(uuid), {
        method: 'DELETE'
      });
    },
    
    // URLs Productos
    productosUrl:     BASE + '/productos/',
    productoDetailUrl: function (uuid) { return BASE + '/productos/' + uuid + '/'; },
    
    // URLs Servicios
    serviciosUrl:     BASE + '/servicios/',
    servicioDetailUrl: function (uuid) { return BASE + '/servicios/' + uuid + '/'; },
    
    // URLs Items
    itemsUrl:         BASE + '/items/',
    itemDetailUrl:    function (uuid) { return BASE + '/items/' + uuid + '/'; },

    // HTMX Offcanvas URLs (Partials)
    offcanvasCrearUrl:   '/cotizaciones/editor/draft/',
    offcanvasEditarUrl:  function (uuid) { return '/cotizaciones/editor/' + uuid + '/'; },
    offcanvasDetalleUrl: function (uuid) { return '/cotizaciones/partials/ver/' + uuid + '/'; },

    // Headers helper
    getHeaders: getHeaders
  };

})(window);
