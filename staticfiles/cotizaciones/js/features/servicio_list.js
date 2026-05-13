/**
 * servicio_list.js - Feature Module para Listado de Servicios v2.62.0
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};
  w.Sintel.Cotizaciones.features = w.Sintel.Cotizaciones.features || {};

  var ServicioList = {
    init: function (containerId) {
      var api = w.Sintel.Cotizaciones.api;
      if (!api || !w.Tabulator) return;

      var table = new w.Tabulator('#' + containerId, {
        ajaxURL: api.serviciosUrl,
        ajaxConfig: { headers: api.getHeaders() },
        layout: 'fitColumns',
        pagination: 'remote',
        paginationSize: 10,
        columns: [
          { title: 'Nombre', field: 'nombre' },
          { title: 'Precio', field: 'precio_venta', formatter: 'money' },
          { 
            title: 'Acciones', 
            formatter: function() { return '<button class="btn btn-sm btn-primary btn-edit-serv">Editar</button>'; },
            cellClick: function(e, cell) {
              var data = cell.getRow().getData();
              ServicioList.onEdit(data.uuid);
            }
          }
        ]
      });
      this.table = table;
    },
    onEdit: function(uuid) {
        console.log('Editando servicio:', uuid);
    }
  };

  w.Sintel.Cotizaciones.features.servicioList = ServicioList;

})(window, document);
