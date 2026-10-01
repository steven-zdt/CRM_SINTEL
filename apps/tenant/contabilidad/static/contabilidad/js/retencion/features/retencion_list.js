/**
 * retencion_list.js - Feature List para Retencion
 *
 * DataTables 3.x (mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos/Empleados/Proyectos/Inventario/
 * Contabilidad -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md):
 * la tabla (#tabla-retenciones) se puebla via ajax contra
 * POST /api/v1/contabilidad/retenciones/dt/ (RetencionViewSet.dt()).
 * django-tables2/RetencionTable retirados. Solo lectura -- las retenciones
 * son generadas via Pull Model (RetencionesService), no hay acciones de
 * fila que delegar aqui.
 */
(function (w, d) {
  'use strict';

  var TABLA_SELECTOR = '#tabla-retenciones';
  var DT_URL = '/api/v1/contabilidad/retenciones/dt/';
  var inicializada = false;

  var BADGE_TIPO = {
    RETEFUENTE: ['bg-danger', 'Retefuente'],
    RETEICA: ['bg-warning text-dark', 'ReteICA'],
    RETEIVA: ['bg-info text-dark', 'ReteIVA'],
  };

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderTipo(data, type, row) {
    var cfg = BADGE_TIPO[row.tipo] || ['bg-secondary', row.tipo || '—'];
    return '<span class="badge ' + cfg[0] + '">' + escapeHtml(cfg[1]) + '</span>';
  }

  function renderNaturaleza(value) {
    if (value === 'VENTA') return '<span class="badge bg-success">Venta</span>';
    return '<span class="badge bg-primary">Compra</span>';
  }

  function renderPorcentaje(value) {
    var n = parseFloat(value) || 0;
    return n.toFixed(2) + '%';
  }

  function renderMonto(value) {
    var n = parseFloat(value) || 0;
    return '<span>$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '</span>';
  }

  function renderDocumentoOrigen(data, type, row) {
    if (!row.documento_origen_app) return '<span class="text-muted small">—</span>';
    return '<span class="text-muted small">' + escapeHtml(row.documento_origen_app) + ' / ' +
      escapeHtml(row.documento_origen_modelo || '') + ' #' + escapeHtml(row.documento_origen_id || '') + '</span>';
  }

  function renderReversada(value) {
    if (value) return '<span class="badge bg-secondary">Reversada</span>';
    return '<span class="badge bg-success">Activa</span>';
  }

  var COLUMNS = [
    { data: null, title: 'Tipo', render: renderTipo },
    { data: null, title: 'Naturaleza', render: renderNaturaleza },
    { data: 'porcentaje', title: '%', render: function (v) { return renderPorcentaje(v); } },
    { data: 'monto', title: 'Monto', render: function (v) { return renderMonto(v); } },
    { data: null, title: 'Documento Origen', orderable: false, render: renderDocumentoOrigen },
    { data: 'reversada', title: 'Estado', render: function (v) { return renderReversada(v); } },
    { data: 'created_at', title: 'Fecha' },
  ];

  function initTabla() {
    if (inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 20,
      order: [[6, 'desc']],
    });
    inicializada = true;
  }

  function reload() {
    if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
      w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
    }
  }

  function attachToolbarListeners() {
    var selectTipo = d.getElementById('filter-tipo-retencion');
    if (selectTipo) {
      selectTipo.addEventListener('change', function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 0, selectTipo.value);
        }
      });
    }

    var selectNaturaleza = d.getElementById('filter-naturaleza-retencion');
    if (selectNaturaleza) {
      selectNaturaleza.addEventListener('change', function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 1, selectNaturaleza.value);
        }
      });
    }

    var selectReversada = d.getElementById('filter-reversada-retencion');
    if (selectReversada) {
      selectReversada.addEventListener('change', function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 5, selectReversada.value);
        }
      });
    }

    var btnRefrescar = d.getElementById('btn-refrescar-retencion');
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', reload);
    }
  }

  function init() {
    initTabla();
    attachToolbarListeners();
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Se expone reload() por consistencia con el resto de modulos de
  // contabilidad, por si algun flujo futuro necesita refrescar la tabla.
  w.RetencionList = Object.freeze({
    init,
    reload,
  });
})(window, document);
