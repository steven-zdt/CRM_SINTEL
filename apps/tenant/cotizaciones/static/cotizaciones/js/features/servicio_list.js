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
      if (!api || !w.TabulatorFactory) return;

      // Antes: new w.Tabulator(...) crudo -- mismo bug real que
      // producto_list.js/configuracion_list.js (2026-08-27). Fix: usar
      // TabulatorFactory (SSoT).
      var table = w.TabulatorFactory.create('#' + containerId, api.serviciosUrl, [
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
      ], { layout: 'fitColumns', paginationSize: 10 });
      this.table = table;
    },
    onEdit: function(uuid) {
        console.log('Editando servicio:', uuid);
    }
  };

  w.Sintel.Cotizaciones.features.servicioList = ServicioList;

})(window, document);
