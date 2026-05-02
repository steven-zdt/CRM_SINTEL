/**
 * cotizaciones.editor.js - Crear/Editar via HTMX Offcanvas v2.61.8
 * Namespace: window.Sintel.Cotizaciones.editor
 */
(function (w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  w.Sintel.Cotizaciones.editor = {
    showCreate: function () {
      var api = w.Sintel.Cotizaciones.api;
      if (!api) return;
      if (typeof htmx !== 'undefined') {
        htmx.ajax('GET', api.offcanvasCrearUrl, { target: '#offcanvas-container', swap: 'innerHTML' });
      }
    },
    showEdit: function (uuid) {
      var api = w.Sintel.Cotizaciones.api;
      if (!api || !uuid) return;
      var url = typeof api.offcanvasEditarUrl === 'function' ? api.offcanvasEditarUrl(uuid) : api.offcanvasEditarUrl;
      if (typeof htmx !== 'undefined') {
        htmx.ajax('GET', url, { target: '#offcanvas-container', swap: 'innerHTML' });
      }
    }
  };

})(window);
