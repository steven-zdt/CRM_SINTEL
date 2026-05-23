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
    var uuid = '';
    try {
      var row = cell.getRow();
      if (row && typeof row.getData === 'function') {
        var data = row.getData();
        uuid = data && data.uuid ? data.uuid : '';
      }
    } catch (e) {
      console.warn(MOD + ' Error obteniendo UUID en formatter:', e);
    }

    if (!uuid) return '<span class="text-muted">Error</span>';

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

    // Validar que el elemento esté visible en el DOM
    if (gridEl.offsetParent === null) {
      console.warn(MOD + ' Elemento grid no es visible, aplazando inicializacion');
      w.requestAnimationFrame(function () { initTable(); });
      return;
    }

    // Destruir instancia previa si existe
    if (_table && typeof _table.destroy === 'function') {
      _table.destroy();
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

      // ⚠️ v2.62: Patrón HTMX para abrir Offcanvas desde Tabulator
      var htmxUrl = null;
      if (btn.classList.contains('btn-edit-cotizacion')) {
        htmxUrl = api.offcanvasEditarUrl(uuid);
      } else if (btn.classList.contains('btn-detail-cotizacion')) {
        htmxUrl = api.offcanvasDetalleUrl(uuid);
      } else if (btn.classList.contains('btn-pdf-cotizacion')) {
        window.open(api.exportarPdfUrl(uuid), '_blank');
        return;
      } else if (btn.classList.contains('btn-delete-cotizacion')) {
        w.Sintel.Cotizaciones.ui.confirmarEliminar(uuid);
        return;
      }

      if (htmxUrl) {
          var trigger = d.createElement('button');
          trigger.setAttribute('hx-get', htmxUrl);
          trigger.setAttribute('hx-target', '#offcanvas-container');
          d.body.appendChild(trigger);
          if (w.htmx) w.htmx.process(trigger);
          trigger.click();
          trigger.remove();
      }
    });
  }

  // Exponer en namespace
  w.Sintel.Cotizaciones.table = {
    init: initTable,
    refresh: function () { if (_table) _table.replaceData(); },
    redraw: function () {
      if (!_table || typeof _table.redraw !== 'function') return;
      var gridEl = _table.element || d.querySelector(GRID_ID);
      if (!gridEl || gridEl.offsetParent === null) return;
      // Validar si la tabla terminó su construcción antes de redibujar
      if (_table.modules && _table.modules.layout && !_table.tableBuilt) return;

      try {
        // requestAnimationFrame asegura que el layout esté completo antes de redraw
        requestAnimationFrame(function () {
          if (_table && typeof _table.redraw === 'function') {
            try {
              _table.redraw(true);
            } catch(e) {
              console.warn(MOD + ' Error interno en redraw:', e);
            }
          }
        });
      } catch (e) {
        console.warn(MOD + ' Error en redraw:', e);
      }
    },
    getInstance: function () { return _table; }
  };

})(window, document);
