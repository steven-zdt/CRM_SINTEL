/**
 * cotizaciones.table.js - Tabulator Grid via TabulatorFactory v2.61.8
 * Namespace: window.Sintel.Cotizaciones.table
 *
 * Columnas alineadas con CotizacionListSerializer:
 *   id, uuid, numero_cotizacion, estado, estado_display,
 *   fecha_emision, fecha_vencimiento, total_con_impuestos,
 *   cliente, cliente_nombre, cliente_razon_social, empresa, created_at
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  var MOD = '[cotizaciones.table]';
  var GRID_ID = '#tabla-cotizaciones-principal';
  var SEARCH_ID = '#search-cotizacion';
  var API_URL = '/api/v1/cotizaciones/';
  var _table = null;

  /**
   * Badge de estado con colores Bootstrap
   */
  function badgeEstado(cell) {
    var val = cell.getValue();
    var map = {
      'BORRADOR':  'bg-secondary',
      'ENVIADA':   'bg-primary',
      'ACEPTADA':  'bg-success',
      'CANCELADA': 'bg-danger'
    };
    var cls = map[val] || 'bg-secondary';
    var display = cell.getRow().getData().estado_display || val || 'N/A';
    return '<span class="badge ' + cls + '">' + display + '</span>';
  }

  /**
   * Formateo moneda COP
   */
  function fmtMoney(cell) {
    var v = parseFloat(cell.getValue()) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(v);
  }

  /**
   * Columna de acciones CRUD
   */
  function accionesFormatter(cell) {
    var data = cell.getRow().getData();
    var uuid = data.uuid || '';
    return '<div class="btn-group btn-group-sm" role="group">' +
      '<button class="btn btn-outline-primary btn-edit-cotizacion" data-uuid="' + uuid + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
      '<button class="btn btn-outline-info btn-detail-cotizacion" data-uuid="' + uuid + '" title="Detalle"><i class="bi bi-eye"></i></button>' +
      '<button class="btn btn-outline-secondary btn-pdf-cotizacion" data-uuid="' + uuid + '" title="PDF"><i class="bi bi-file-pdf"></i></button>' +
      '<button class="btn btn-outline-danger btn-delete-cotizacion" data-uuid="' + uuid + '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  function getColumns() {
    return [
      { title: 'No. Cotizacion', field: 'numero_cotizacion', headerFilter: true, width: 140 },
      { title: 'Cliente', field: 'cliente_razon_social', headerFilter: true },
      { title: 'Fecha Emision', field: 'fecha_emision', width: 120, sorter: 'date' },
      { title: 'Vencimiento', field: 'fecha_vencimiento', width: 120, sorter: 'date' },
      { title: 'Estado', field: 'estado', width: 120, formatter: badgeEstado, hozAlign: 'center' },
      { title: 'Total', field: 'total_con_impuestos', width: 150, formatter: fmtMoney, hozAlign: 'right' },
      { title: 'Acciones', width: 180, formatter: accionesFormatter, headerSort: false, hozAlign: 'center' }
    ];
  }

  /**
   * Inicializar tabla con TabulatorFactory
   */
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(MOD + ' TabulatorFactory no disponible');
      return;
    }
    var gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return;

    // Destruir instancia previa si existe
    if (_table && typeof _table.destroy === 'function') {
      try { _table.destroy(); } catch (e) { /* ignore */ }
      _table = null;
    }

    _table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), {
      searchInputSelector: SEARCH_ID,
      layout: 'fitColumns'
    });

    if (_table) {
      initGridEvents();
      console.log(MOD + ' Tabla inicializada con TabulatorFactory');
    }
  }

  /**
   * Delegacion de eventos en la tabla (click en botones de accion)
   */
  function initGridEvents() {
    var gridEl = d.querySelector(GRID_ID);
    if (!gridEl || gridEl.dataset.eventsBound === 'true') return;
    gridEl.dataset.eventsBound = 'true';

    gridEl.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-uuid]');
      if (!btn) return;
      e.stopPropagation();
      var uuid = btn.getAttribute('data-uuid');
      if (!uuid) return;

      var api = w.Sintel.Cotizaciones.api;
      if (!api) return;

      if (btn.classList.contains('btn-edit-cotizacion')) {
        w.Sintel.Cotizaciones.editor.showEdit(uuid);
      } else if (btn.classList.contains('btn-detail-cotizacion')) {
        w.Sintel.Cotizaciones.detalle.show(uuid);
      } else if (btn.classList.contains('btn-pdf-cotizacion')) {
        window.open(api.exportarPdfUrl(uuid), '_blank');
      } else if (btn.classList.contains('btn-delete-cotizacion')) {
        w.Sintel.Cotizaciones.ui.confirmarEliminar(uuid);
      }
    });
  }

  // Exponer en namespace
  w.Sintel.Cotizaciones.table = {
    init: initTable,
    refresh: function () { if (_table) _table.replaceData(); },
    redraw: function () { if (_table && typeof _table.redraw === 'function') _table.redraw(true); },
    getInstance: function () { return _table; }
  };

})(window, document);
