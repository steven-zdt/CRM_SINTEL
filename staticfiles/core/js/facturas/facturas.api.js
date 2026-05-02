// Compatibility wrapper for facturas API
(function (w) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Facturas = w.Sintel.Facturas || {};

  w.Sintel.Facturas.api = w.Sintel.Facturas.api || {
    crear: async function (payload) {
      console.warn('[facturas.api] stub crear called');
      return { ok: false };
    },
    actualizar: async function (id, payload) {
      console.warn('[facturas.api] stub actualizar called');
      return { ok: false };
    },
    eliminar: async function (id) {
      console.warn('[facturas.api] stub eliminar called');
      return { ok: false };
    },
    obtenerResumen: async function () {
      console.warn('[facturas.api] stub obtenerResumen called');
      return { ok: true, data: {} };
    }
  };

})(window);
