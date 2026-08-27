/**
 * configuracion_list.js - Feature Module para Listado de Plantillas v2.62.0
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};
  w.Sintel.Cotizaciones.features = w.Sintel.Cotizaciones.features || {};

  var ConfiguracionList = {
    init: function (containerId) {
      var api = w.Sintel.Cotizaciones.api;
      if (!api || !w.TabulatorFactory) return;

      // Antes: new w.Tabulator(...) crudo con ajaxURL directo, sin adaptar
      // la forma paginada de DRF ({count, next, previous, results}) --
      // Tabulator esperaba un array y recibia un objeto ("Data Loading
      // Error - Expecting: array, Received: object"). Bug real reportado
      // en vivo, 2026-08-27. Fix: usar TabulatorFactory (SSoT ya usado por
      // cotizaciones.table.js), que si sabe traducir la respuesta de DRF.
      var table = w.TabulatorFactory.create('#' + containerId, api.configuracionUrl, [
        { title: 'Nombre', field: 'nombre_configuracion' },
        { title: 'Activa', field: 'es_activo', formatter: 'tickCross' },
        {
          title: 'Acciones',
          formatter: function() { return '<button class="btn btn-sm btn-primary">Editar</button>'; },
          cellClick: function(e, cell) {
            var data = cell.getRow().getData();
            ConfiguracionList.onEdit(data.uuid);
          }
        }
      ], { layout: 'fitColumns' });
      this.table = table;
    },
    onEdit: function(uuid) {
        // Disparar HTMX para abrir editor
        var btn = d.createElement('button');
        btn.setAttribute('hx-get', '/cotizaciones/partials/configuracion/editar/' + uuid + '/');
        btn.setAttribute('hx-target', '#offcanvas-container');
        d.body.appendChild(btn);
        if (w.htmx) w.htmx.process(btn);
        btn.click();
        btn.remove();
    },
    reload: function () {
        // Antes: configuracion_editor.js llamaba a este metodo tras
        // crear/editar, pero no existia -- la lista de Plantillas nunca se
        // refrescaba sola (hallazgo real, auditoria de modernizacion,
        // 2026-08-27).
        if (this.table && typeof this.table.replaceData === 'function') {
            this.table.replaceData();
        }
    }
  };

  w.Sintel.Cotizaciones.features.configuracionList = ConfiguracionList;

})(window, document);
