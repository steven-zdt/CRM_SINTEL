/**
 * features/cotizacion_list.js - DEPRECATED v2.61.8
 *
 * Funcionalidad migrada a modulos FSD en la raiz:
 * - cotizaciones.table.js  (TabulatorFactory + columnas)
 * - cotizaciones.ui.js     (CRUD acciones + offcanvas)
 * - cotizaciones.main.js   (Orquestador + tab-activated)
 *
 * Este archivo se mantiene vacio para compatibilidad de carga.
 */
(function () {
  'use strict';

  window.Sintel = window.Sintel || {};
  window.Sintel.Cotizaciones = window.Sintel.Cotizaciones || {};

  // Alias de compatibilidad (noop)
  window.Sintel.Cotizaciones.CotizacionList = {
    init: function () {
      console.log('[cotizacion_list] DEPRECATED: usar Sintel.Cotizaciones.Main.init()');
      if (window.Sintel.Cotizaciones.Main && typeof window.Sintel.Cotizaciones.Main.init === 'function') {
        window.Sintel.Cotizaciones.Main.init();
      }
    },
    reload: function () {
      if (window.Sintel.Cotizaciones.table && typeof window.Sintel.Cotizaciones.table.refresh === 'function') {
        window.Sintel.Cotizaciones.table.refresh();
      }
    }
  };
})();
