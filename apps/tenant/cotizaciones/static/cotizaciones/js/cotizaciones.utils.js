/**
 * cotizaciones.utils.js - Funciones puras de formateo y validacion v2.61.8
 * Namespace: window.Sintel.Cotizaciones.utils
 */
(function (w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  w.Sintel.Cotizaciones.utils = {
    parseFloatSafe: function (val) {
      var f = parseFloat(val);
      return isNaN(f) ? 0 : f;
    },
    fmtMoney: function (v) {
      var num = parseFloat(v) || 0;
      return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(num);
    },
    formatDate: function (dateStr) {
      if (!dateStr) return '-';
      try {
        var d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('es-CO', { year: 'numeric', month: '2-digit', day: '2-digit' });
      } catch (e) {
        return dateStr;
      }
    }
  };

})(window);
