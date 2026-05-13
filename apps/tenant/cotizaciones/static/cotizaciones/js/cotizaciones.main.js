/**
 * cotizaciones.main.js - Orquestador Principal v2.62.0 - SINTEL FSD
 * Namespace: window.Sintel.Cotizaciones
 */
(function (w, d) {
  'use strict';

  var MOD = '[cotizaciones.main]';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  var TAB_ID = '#tab-cotizaciones';
  var initialized = false;

  function init() {
    var tabEl = d.querySelector(TAB_ID);
    if (!tabEl) return;

    if (!initialized) {
      console.log(MOD + ' Inicializando modulo cotizaciones v2.62.0');
      
      // Inicialización de componentes CORE
      if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.init === 'function') {
        w.Sintel.Cotizaciones.table.init();
      }
      if (w.Sintel.Cotizaciones.ui && typeof w.Sintel.Cotizaciones.ui.bindEvents === 'function') {
        w.Sintel.Cotizaciones.ui.bindEvents();
      }

      // Inicialización de FEATURES (Lazy-like check)
      var features = w.Sintel.Cotizaciones.features;
      if (features) {
          // Si hay listado de productos en el DOM
          if (features.productoList && d.getElementById('table-productos')) {
              features.productoList.init('table-productos');
          }
          // Si hay listado de servicios en el DOM
          if (features.servicioList && d.getElementById('table-servicios')) {
              features.servicioList.init('table-servicios');
          }
      }

      initialized = true;
    } else {
      // Tab re-activado: redraw tabla principal
      if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.redraw === 'function') {
        w.Sintel.Cotizaciones.table.redraw();
      }
    }
  }

  // Exponer init y refresh en namespace
  w.Sintel.Cotizaciones.Main = {
    init: init,
    refresh: function () {
      if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.refresh === 'function') {
        w.Sintel.Cotizaciones.table.refresh();
      }
    }
  };

  // Lazy Load via DOMUtils o fallback DOMContentLoaded
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(TAB_ID, init);
  } else {
    d.addEventListener('DOMContentLoaded', init);
  }

  // Evento tab-activated (Sintel Standard)
  d.addEventListener('tab-activated', function (event) {
    if (event.detail && event.detail.tabName === 'cotizaciones') {
      init();
    }
  });

})(window, document);
