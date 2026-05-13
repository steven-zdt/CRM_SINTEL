/**
 * producto_list.js - Feature Module para Listado de Productos v2.62.0
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};
  w.Sintel.Cotizaciones.features = w.Sintel.Cotizaciones.features || {};

  var ProductoList = {
    init: function (containerId) {
      var api = w.Sintel.Cotizaciones.api;
      if (!api || !w.Tabulator) return;

      var table = new w.Tabulator('#' + containerId, {
        ajaxURL: api.productosUrl,
        ajaxConfig: { headers: api.getHeaders() },
        layout: 'fitColumns',
        pagination: 'remote',
        paginationSize: 10,
        columns: [
          { title: 'Código', field: 'codigo' },
          { title: 'Nombre', field: 'nombre' },
          { title: 'Precio', field: 'precio_venta', formatter: 'money' },
          { 
            title: 'Acciones', 
            formatter: function() { return '<button class="btn btn-sm btn-primary btn-edit-prod">Editar</button>'; },
            cellClick: function(e, cell) {
              var data = cell.getRow().getData();
              ProductoList.onEdit(data.uuid);
            }
          }
        ]
      });
      this.table = table;
    },
    onEdit: function(uuid) {
        // Lógica para mostrar editor de producto
        console.log('Editando producto:', uuid);
    }
  };

  w.Sintel.Cotizaciones.features.productoList = ProductoList;

})(window, document);
