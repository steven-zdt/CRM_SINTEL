/**
 * cotizaciones.list.js - Refresh helpers v2.61.8
 * Namespace: window.Sintel.Cotizaciones.list
 */
(function (w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  w.Sintel.Cotizaciones.list = {
    refresh: function () {
      if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.refresh === 'function') {
        w.Sintel.Cotizaciones.table.refresh();
      }
    }
  };

})(window);
