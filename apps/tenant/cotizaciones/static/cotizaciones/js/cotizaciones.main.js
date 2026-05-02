/**
 * cotizaciones.main.js - Orquestador Principal v2.61.8
 * Namespace: window.Sintel.Cotizaciones
 *
 * Inicializacion diferida via DOMUtils.onVisibleOnce + tab-activated.
 * Delega a submódulos: api, table, ui, list, editor, detalle, utils.
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
      console.log(MOD + ' Inicializando modulo cotizaciones');
      if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.init === 'function') {
        w.Sintel.Cotizaciones.table.init();
      }
      if (w.Sintel.Cotizaciones.ui && typeof w.Sintel.Cotizaciones.ui.bindEvents === 'function') {
        w.Sintel.Cotizaciones.ui.bindEvents();
      }
      initialized = true;
    } else {
      // Tab re-activado: redraw tabla
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

  // tab-activated (Custom Event from workspace.js)
  d.addEventListener('tab-activated', function (event) {
    if (event.detail && event.detail.tabName === 'cotizaciones') {
      init();
    }
  });

})(window, document);
