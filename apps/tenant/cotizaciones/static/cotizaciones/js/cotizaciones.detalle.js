/**
 * cotizaciones.detalle.js - Detalle en Offcanvas via HTMX v2.61.8
 * Namespace: window.Sintel.Cotizaciones.detalle
 */
(function (w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  w.Sintel.Cotizaciones.detalle = {
    show: function (uuid) {
      var api = w.Sintel.Cotizaciones.api;
      if (!api || !uuid) return;
      var url = api.offcanvasDetalleUrl + '?id=' + uuid;
      if (typeof htmx !== 'undefined') {
        htmx.ajax('GET', url, { target: '#offcanvas-container', swap: 'innerHTML' });
      }
    }
  };

})(window);
