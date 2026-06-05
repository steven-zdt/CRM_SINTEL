// @ts-nocheck
/**
 * cotizaciones.table.js v3.10 — Tabulator Grid + KPIs + Filtros por Estado
 * Namespace: window.Sintel.Cotizaciones.table
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

  // ── Formatters ──────────────────────────────────────────────────────────────

  function fmtMoneda(v) {
    var n = parseFloat(v);
    if (isNaN(n)) return '—';
    return new Intl.NumberFormat('es-CO', {
      style: 'currency', currency: 'COP',
      minimumFractionDigits: 0, maximumFractionDigits: 0
    }).format(n);
  }

  function fmtFecha(v) {
    if (!v) return '<span class="text-muted">—</span>';
    try {
      var d = new Date(v + 'T00:00:00');
      return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch (_) { return v; }
  }

  function badgeEstado(cell) {
    var val = cell.getValue();
    var MAP = {
      'BORRADOR':  ['bg-secondary', 'Borrador'],
      'ENVIADA':   ['bg-primary',   'Enviada'],
      'ACEPTADA':  ['bg-success',   'Aceptada'],
      'CANCELADA': ['bg-danger',    'Cancelada']
    };
    var pair = MAP[val] || ['bg-light text-dark', val || '—'];
    var display = cell.getRow().getData().estado_display || pair[1];
    return '<span class="badge ' + pair[0] + ' px-2 py-1">' + display + '</span>';
  }

  function fmtNumero(cell) {
    var row = cell.getRow().getData();
    var num = row.numero_cotizacion || '—';
    var cod = row.codigo_unico || '';
    var tipo = row.tipo_cotizacion || '';
    var tipoMap = { 'PRODUCTOS': 'Productos', 'SERVICIOS': 'Servicios', 'MIXTO': 'Mixto' };
    var tipoLabel = tipoMap[tipo] || tipo;
    var tipoHtml = tipoLabel
      ? '<span class="badge bg-light text-secondary border fw-normal" style="font-size:0.65rem;">' + tipoLabel + '</span> '
      : '';
    return '<div style="line-height:1.35;">' +
      '<div class="fw-semibold">' + num + '</div>' +
      '<div class="mt-1">' + tipoHtml + (cod ? '<code class="text-muted" style="font-size:0.7rem;">' + cod + '</code>' : '') + '</div>' +
      '</div>';
  }

  function fmtCliente(cell) {
    var row = cell.getRow().getData();
    var nombre = row.cliente_razon_social || row.cliente_nombre || '—';
    return '<span class="text-truncate d-block small" style="max-width:160px;" title="' + nombre + '">' + nombre + '</span>';
  }

  function fmtVencimiento(cell) {
    var v = cell.getValue();
    if (!v) return '<span class="text-muted">—</span>';
    var hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    var fecha = new Date(v + 'T00:00:00');
    var row = cell.getRow().getData();
    var abierto = row.estado === 'BORRADOR' || row.estado === 'ENVIADA';
    var vencida = abierto && fecha < hoy;
    var label = fmtFecha(v);
    if (vencida) {
      return '<span class="text-danger fw-semibold" title="Vencida"><i class="bi bi-exclamation-triangle-fill me-1"></i>' + label + '</span>';
    }
    return '<span>' + label + '</span>';
  }

  function fmtTotal(cell) {
    var v = parseFloat(cell.getValue()) || 0;
    return '<span class="fw-semibold">' + fmtMoneda(v) + '</span>';
  }

  function accionesFormatter(cell) {
    var uuid = '';
    try {
      var data = cell.getRow().getData();
      uuid = data && data.uuid ? data.uuid : '';
    } catch (e) {
      console.warn(MOD + ' Error obteniendo UUID:', e);
    }
    if (!uuid) return '<span class="text-muted small">—</span>';
    return '<div class="btn-group btn-group-sm" role="group">' +
      '<button class="btn btn-outline-primary btn-edit-cotizacion" data-uuid="' + uuid + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
      '<button class="btn btn-outline-info btn-detail-cotizacion" data-uuid="' + uuid + '" title="Detalle"><i class="bi bi-eye"></i></button>' +
      '<button class="btn btn-outline-secondary btn-pdf-cotizacion" data-uuid="' + uuid + '" title="PDF"><i class="bi bi-file-pdf"></i></button>' +
      '<button class="btn btn-outline-danger btn-delete-cotizacion" data-uuid="' + uuid + '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  // ── KPIs ────────────────────────────────────────────────────────────────────

  function actualizarKPIs(rows) {
    var hoy = new Date();
    hoy.setHours(0, 0, 0, 0);

    var total     = rows.length;
    var borrador  = 0, enviada = 0, aceptada = 0, vencidas = 0;
    var monto     = 0;

    rows.forEach(function (r) {
      if (r.estado === 'BORRADOR')  borrador++;
      if (r.estado === 'ENVIADA')   enviada++;
      if (r.estado === 'ACEPTADA')  aceptada++;
      monto += parseFloat(r.total_con_impuestos) || 0;
      if ((r.estado === 'BORRADOR' || r.estado === 'ENVIADA') && r.fecha_vencimiento) {
        var fv = new Date(r.fecha_vencimiento + 'T00:00:00');
        if (fv < hoy) vencidas++;
      }
    });

    function set(id, v) { var el = d.getElementById(id); if (el) el.textContent = v; }
    set('kpi-cot-total',    total);
    set('kpi-cot-borrador', borrador);
    set('kpi-cot-enviada',  enviada);
    set('kpi-cot-aceptada', aceptada);
    set('kpi-cot-vencidas', vencidas);
    set('kpi-cot-monto',    fmtMoneda(monto));
  }

  // ── Columnas ─────────────────────────────────────────────────────────────────

  function getColumns() {
    return [
      {
        title: 'Cotizacion',
        field: 'numero_cotizacion',
        minWidth: 160,
        formatter: fmtNumero
      },
      {
        title: 'Cliente',
        field: 'cliente_razon_social',
        minWidth: 180,
        formatter: fmtCliente
      },
      {
        title: 'Emision',
        field: 'fecha_emision',
        width: 115,
        hozAlign: 'center',
        headerHozAlign: 'center',
        formatter: function (cell) { return fmtFecha(cell.getValue()); },
        sorter: 'date'
      },
      {
        title: 'Vencimiento',
        field: 'fecha_vencimiento',
        width: 135,
        hozAlign: 'center',
        headerHozAlign: 'center',
        formatter: fmtVencimiento,
        sorter: 'date'
      },
      {
        title: 'Estado',
        field: 'estado',
        width: 110,
        hozAlign: 'center',
        headerHozAlign: 'center',
        formatter: badgeEstado
      },
      {
        title: 'Total',
        field: 'total_con_impuestos',
        width: 155,
        hozAlign: 'right',
        headerHozAlign: 'right',
        formatter: fmtTotal,
        sorter: 'number'
      },
      {
        title: '',
        field: 'uuid',
        width: 170,
        headerSort: false,
        hozAlign: 'center',
        formatter: accionesFormatter
      }
    ];
  }

  // ── Filtros por Estado ────────────────────────────────────────────────────────

  function initFiltrosEstado() {
    var contenedor = d.getElementById('filtros-estado-cotizaciones');
    if (!contenedor) return;
    contenedor.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-estado]');
      if (!btn) return;
      contenedor.querySelectorAll('[data-estado]').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var estado = btn.getAttribute('data-estado');
      if (!_table) return;
      _table.clearFilter(true);
      if (estado) _table.setFilter('estado', '=', estado);
    });
  }

  // ── Inicializar Tabla ─────────────────────────────────────────────────────────

  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(MOD + ' TabulatorFactory no disponible');
      return;
    }
    var gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return;

    if (gridEl.offsetParent === null) {
      w.requestAnimationFrame(function () { initTable(); });
      return;
    }

    if (_table && typeof _table.destroy === 'function') {
      _table.destroy();
      _table = null;
    }

    _table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), {
      searchInputSelector: SEARCH_ID,
      layout: 'fitColumns'
    });

    if (_table) {
      _table.on('dataLoaded', function (data) {
        actualizarKPIs(data);
      });
      _table.on('dataFiltered', function (_f, rows) {
        actualizarKPIs(rows.map(function (r) { return r.getData(); }));
      });
      initGridEvents();
      initFiltrosEstado();
      console.log(MOD + ' Tabla inicializada');
    }
  }

  // ── Event Delegation ─────────────────────────────────────────────────────────

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

  // ── Export ───────────────────────────────────────────────────────────────────

  w.Sintel.Cotizaciones.table = {
    init: initTable,
    refresh: function () { if (_table) _table.replaceData(); },
    redraw: function () {
      if (!_table || typeof _table.redraw !== 'function') return;
      var gridEl = _table.element || d.querySelector(GRID_ID);
      if (!gridEl || gridEl.offsetParent === null) return;
      if (_table.modules && _table.modules.layout && !_table.tableBuilt) return;
      requestAnimationFrame(function () {
        try { _table.redraw(true); } catch (e) { console.warn(MOD + ' redraw error:', e); }
      });
    },
    getInstance: function () { return _table; }
  };

})(window, document);
