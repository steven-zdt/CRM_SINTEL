/**
 * cotizaciones.api.js - SSoT de URLs y consumo de endpoints v2.61.8
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

  w.Sintel.Cotizaciones.api = {
    // URLs
    listUrl:        BASE + '/',
    createUrl:      BASE + '/',
    detailUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    deleteUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    updateUrl:      function (uuid) { return BASE + '/' + uuid + '/'; },
    recalcularUrl:  function (uuid) { return BASE + '/' + uuid + '/recalcular/'; },
    exportarPdfUrl: function (uuid) { return BASE + '/' + uuid + '/exportar-pdf/'; },
    estadisticasUrl: BASE + '/estadisticas/',
    configuracionUrl: BASE + '/configuracion/',

    // HTMX Offcanvas URLs
    offcanvasCrearUrl:   BASE + '/render-offcanvas/crear/',
    offcanvasEditarUrl:  function (uuid) { return BASE + '/' + uuid + '/render-offcanvas/editar/'; },
    offcanvasDetalleUrl: BASE + '/render-offcanvas/detalle/',

    // Headers helper
    getHeaders: getHeaders
  };

})(window);
