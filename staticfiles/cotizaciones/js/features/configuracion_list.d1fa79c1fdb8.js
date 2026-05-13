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
      if (!api || !w.Tabulator) return;

      var table = new w.Tabulator('#' + containerId, {
        ajaxURL: api.configuracionUrl,
        ajaxConfig: { headers: api.getHeaders() },
        layout: 'fitColumns',
        columns: [
          { title: 'Nombre', field: 'nombre_configuracion' },
          { title: 'Activa', field: 'es_activo', formatter: 'tickCross' },
          { 
            title: 'Acciones', 
            formatter: function() { return '<button class="btn btn-sm btn-primary">Editar</button>'; },
            cellClick: function(e, cell) {
              var data = cell.getRow().getData();
              ConfiguracionList.onEdit(data.id);
            }
          }
        ]
      });
      this.table = table;
    },
    onEdit: function(id) {
        // Disparar HTMX para abrir editor
        var btn = d.createElement('button');
        btn.setAttribute('hx-get', '/cotizaciones/partials/configuracion/editar/' + id + '/');
        btn.setAttribute('hx-target', '#offcanvas-container');
        d.body.appendChild(btn);
        if (w.htmx) w.htmx.process(btn);
        btn.click();
        btn.remove();
    }
  };

  w.Sintel.Cotizaciones.features.configuracionList = ConfiguracionList;

})(window, document);
