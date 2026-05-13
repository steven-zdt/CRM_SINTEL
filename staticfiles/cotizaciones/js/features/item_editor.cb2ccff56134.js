/**
 * item_editor.js - Feature Module para Gestión de Items en Cotización v2.62.0
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};
  w.Sintel.Cotizaciones.features = w.Sintel.Cotizaciones.features || {};

  var ItemEditor = {
    init: function (containerId, cotizacionUuid) {
      var api = w.Sintel.Cotizaciones.api;
      if (!api || !w.Tabulator) return;

      var table = new w.Tabulator('#' + containerId, {
        ajaxURL: api.itemsUrl,
        ajaxParams: { cotizacion_id: cotizacionUuid },
        ajaxConfig: { headers: api.getHeaders() },
        layout: 'fitColumns',
        columns: [
          { title: 'Descripción', field: 'descripcion', editor: 'input' },
          { title: 'Cant', field: 'cantidad', editor: 'number', width: 80 },
          { title: 'Costo', field: 'costo_unitario', editor: 'number' },
          { title: 'Utilidad %', field: 'porcentaje_utilidad', editor: 'number' },
          { title: 'Precio Venta', field: 'precio_unitario_venta', formatter: 'money', bottomCalc: 'sum' },
          { title: 'Subtotal', field: 'subtotal_linea', formatter: 'money', bottomCalc: 'sum' },
          { 
            title: 'Del', 
            formatter: function() { return '<button class="btn btn-sm btn-danger">x</button>'; },
            cellClick: function(e, cell) {
                ItemEditor.deleteItem(cell.getRow().getData().uuid);
            }
          }
        ]
      });
      this.table = table;
    },
    deleteItem: function(uuid) {
        // Lógica de eliminación
    }
  };

  w.Sintel.Cotizaciones.features.itemEditor = ItemEditor;

})(window, document);
