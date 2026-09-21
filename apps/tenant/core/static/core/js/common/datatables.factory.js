/**
 * datatables.factory.js — Factory vanilla para DataTables 3.x + ColumnControl.
 *
 * Piloto (Ventas): docs/ux/TABLES_FORMS_RELEASE_GATE.md. NO reutilizar/tocar
 * tabulator.factory.js -- sigue acoplado a Tabulator para otros modulos
 * (sub-grids de Clientes/Proveedores/Inventario/Empleados, listado de
 * Cotizaciones). Este factory es independiente y solo lo cargan los modulos
 * que ya migraron a DataTables (via su propio assets_<app>_datatables.html).
 *
 * Contrato de red: mismo patron ya usado por apps/public/console contra
 * apps/shared/datatable.py (DataTableServer) -- POST JSON + header
 * X-CSRFToken, respuesta {draw, recordsTotal, recordsFiltered, data}.
 *
 * Rango en columnas fecha/numero: el protocolo DataTables no define un
 * formato nativo de rango (columns[i][search][value] es siempre un string
 * simple). Este factory codifica rangos como "min~max" (cualquier lado
 * opcional) -- el mismo formato que apps/shared/datatable.py::_apply_range_filter
 * espera. No depende de ningun widget nativo de ColumnControl para rangos.
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Core = w.Sintel.Core || {};

  var RANGE_SEPARATOR = '~';
  var instances = {};

  function csrfToken() {
    if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http && typeof w.Sintel.Core.Http.csrf === 'function') {
      return w.Sintel.Core.Http.csrf();
    }
    return '';
  }

  /**
   * Crea (o re-crea) una instancia de DataTable server-side sobre `selector`.
   *
   * @param {string} selector   Selector CSS de la tabla (ej. '#tabla-ventas')
   * @param {string} apiUrl     Endpoint DataTables (POST), ej. '/api/v1/ventas/dt/'
   * @param {Array}  columns    Config nativa de columnas DataTables: [{data, title, orderable, searchable, className, render}]
   * @param {Object} [options]
   * @param {number} [options.pageLength=20]
   * @param {Array}  [options.order]              Orden inicial DataTables (ej. [[1, 'desc']])
   * @param {Function} [options.onDraw]           Callback tras cada draw (para re-bindear acciones de fila si hace falta)
   * @returns {Object} instancia de DataTable
   */
  function create(selector, apiUrl, columns, options) {
    options = options || {};

    if (typeof DataTable === 'undefined') {
      console.error('[DataTablesFactory] DataTables no esta cargado -- revisar assets_ventas_datatables.html');
      return null;
    }

    var existing = DataTable.isDataTable(selector);
    if (existing) {
      instances[selector].destroy();
    }

    var dt = new DataTable(selector, {
      serverSide: true,
      processing: true,
      pageLength: options.pageLength || 20,
      order: options.order || [],
      columns: columns,
      // `layout` hace merge parcial sobre el default de DataTables
      // ({topStart:'pageLength', topEnd:'search', bottomStart:'info',
      // bottomEnd:'paging'}) -- cualquier slot no mencionado aqui conserva
      // su contenido por defecto en vez de quedar vacio. topEnd debe
      // anularse explicitamente o el buscador por defecto de ese slot
      // queda activo ADEMAS del nuestro en topStart (2 cajas "Buscar...",
      // confirmado en navegador real).
      layout: {
        topStart: 'search',
        topEnd: null,
        bottomStart: 'info',
        bottomEnd: 'paging',
      },
      language: {
        search: '',
        searchPlaceholder: 'Buscar...',
        emptyTable: 'No se encontraron registros',
        zeroRecords: 'No encontramos resultados con los filtros actuales',
        info: 'Mostrando _START_-_END_ de _TOTAL_',
        infoEmpty: 'Sin registros',
        infoFiltered: '(filtrado de _MAX_ totales)',
        paginate: { previous: '‹', next: '›' },
        processing: 'Cargando...',
      },
      ajax: {
        url: apiUrl,
        type: 'POST',
        contentType: 'application/json',
        headers: { 'X-CSRFToken': csrfToken() },
        data: function (d) { return JSON.stringify(d); },
        dataSrc: 'data',
        error: function (xhr) {
          console.error('[DataTablesFactory] Error cargando ' + apiUrl, xhr && xhr.status);
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError({ data: { detail: 'No fue posible cargar los datos.' } });
          }
        },
      },
      drawCallback: function () {
        if (typeof options.onDraw === 'function') options.onDraw(dt);
      },
    });

    instances[selector] = dt;
    return dt;
  }

  function get(selector) {
    return instances[selector] || null;
  }

  /**
   * Recarga sin perder la pagina actual (2do arg `false` de ajax.reload).
   */
  function reload(selector) {
    var dt = get(selector);
    if (dt) dt.ajax.reload(null, false);
  }

  /**
   * Aplica busqueda global (debounced por el llamador).
   */
  function search(selector, value) {
    var dt = get(selector);
    if (dt) dt.search(value || '').draw();
  }

  /**
   * Aplica un filtro exacto/contains a una columna por indice.
   */
  function columnSearch(selector, columnIndex, value) {
    var dt = get(selector);
    if (dt) dt.column(columnIndex).search(value || '').draw();
  }

  /**
   * Aplica un filtro de rango "min~max" a una columna (fecha/numero).
   * min/max vacios se omiten (filtro parcial: solo "desde" o solo "hasta").
   */
  function columnRangeSearch(selector, columnIndex, min, max) {
    var value = (min || '') + RANGE_SEPARATOR + (max || '');
    if (value === RANGE_SEPARATOR) value = '';
    columnSearch(selector, columnIndex, value);
  }

  w.Sintel.Core.DataTablesFactory = {
    create: create,
    get: get,
    reload: reload,
    search: search,
    columnSearch: columnSearch,
    columnRangeSearch: columnRangeSearch,
  };

})(window, document);
