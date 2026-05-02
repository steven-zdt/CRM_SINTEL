// Compatibility wrapper for facturas UI helpers
(function (w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Facturas = w.Sintel.Facturas || {};

  w.Sintel.Facturas.ui = w.Sintel.Facturas.ui || {
    abrirDetalle: function (id) { console.log('[facturas.ui] abrirDetalle', id); },
    abrirCrear: function () { console.log('[facturas.ui] abrirCrear'); },
    cerrar: function () { console.log('[facturas.ui] cerrar'); },
    initHTMX: function () {},
    initEventosOffcanvas: function () {}
  };

})(window);
