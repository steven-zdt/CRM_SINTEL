// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * extracto_list.js - Controlador de Lista de Extractos Bancarios
 * Namespace: window.Sintel.Bancos.ExtractoList
 *
 * DataTables 3.x (mismo patron ya validado en Ventas/Bancos-Cuentas/
 * Facturas/Clientes/Proveedores/Compras/Gastos/Empleados/Proyectos/
 * Inventario -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md): la
 * tabla (#tabla-extractos-bancarios) se puebla via ajax contra
 * POST /api/v1/bancos/extractos/dt/ usando Sintel.Core.DataTablesFactory.
 * django-tables2/ExtractoBancarioTable retirados. Los KPIs de conciliacion
 * (BAN-09) siguen server-rendered via HTMX (kpis_extractos.html).
 *
 * Las acciones de fila (ver/conciliar/procesar/eliminar) las maneja
 * bancos.main.js via delegacion global sobre document.body -- no se
 * tocan aqui.
 *
 * init()/redraw() hacen trabajo real (mismo patron ya usado en
 * cuenta_list.js): bancos.main.js los invoca en varios momentos
 * (activacion de sub-tab, activacion del tab del workspace) porque
 * #tab-pane-extractos puede estar oculto (display:none) cuando el
 * DataTable se crea -- init() es idempotente (guardia `inicializada`),
 * redraw() solo recalcula anchos de columna (dt.columns().adjust()),
 * nunca reconsulta ni reconstruye la tabla.
 */
(function (w, d) {
  'use strict';

  const MOD = '[bancos:extracto_list]';
  var TABLA_SELECTOR = '#tabla-extractos-bancarios';
  var DT_URL = '/api/v1/bancos/extractos/dt/';
  var inicializada = false;

  var MESES_MAP = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
  };

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderCuenta(data, type, row) {
    var numero = row.cuenta_numero
      ? '<span class="text-muted small d-block">' + escapeHtml(row.cuenta_numero) + '</span>' : '';
    return '<div class="py-1"><span class="fw-semibold">' + escapeHtml(row.cuenta_nombre || '—') + '</span>' + numero + '</div>';
  }

  function renderPeriodo(data, type, row) {
    var mes = MESES_MAP[row.mes] || '—';
    return mes + ' / ' + (row.anio || '—');
  }

  function renderArchivo(value) {
    if (!value) return '—';
    var nombre = String(value).split('/').pop().split('?')[0];
    return '<a href="' + escapeHtml(value) + '" target="_blank" class="text-decoration-none small text-truncate d-inline-block" ' +
      'style="max-width:150px;" title="' + escapeHtml(nombre) + '"><i class="bi bi-file-earmark-excel text-success me-1"></i>' + escapeHtml(nombre) + '</a>';
  }

  function renderProcesado(value) {
    if (value) return '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Procesado</span>';
    return '<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle me-1"></i>Pendiente</span>';
  }

  function renderConciliacion(data, type, row) {
    var total = row.total_transacciones || 0;
    var conc = row.tx_conciliadas || 0;
    var pend = row.tx_pendientes != null ? row.tx_pendientes : (total - conc);

    if (!row.procesado || total === 0) {
      return '<span class="text-muted small">Sin transacciones</span>';
    }

    var pct = total > 0 ? Math.round((conc / total) * 100) : 0;
    var color = pct === 100 ? 'bg-success' : pct > 0 ? 'bg-warning' : 'bg-danger';
    var txtColor = pct >= 50 ? 'text-success' : 'text-danger';
    var pendBadge = pend > 0
      ? '<span class="badge bg-danger" style="font-size:.6rem;">' + pend + ' pendiente' + (pend > 1 ? 's' : '') + '</span>'
      : '<span class="badge bg-success" style="font-size:.6rem;"><i class="bi bi-check2-all"></i></span>';
    return '<div style="font-size:.72rem;line-height:1.2;">' +
      '<div class="d-flex justify-content-between mb-1"><span class="fw-semibold ' + txtColor + '">' + conc + '/' + total + '</span>' + pendBadge + '</div>' +
      '<div class="progress" style="height:4px;border-radius:2px;"><div class="progress-bar ' + color + '" style="width:' + pct + '%;transition:width .3s;"></div></div>' +
      '</div>';
  }

  function renderAcciones(data, type, row) {
    var total = row.total_transacciones || 0;
    var conc = row.tx_conciliadas || 0;
    var pend = row.tx_pendientes != null ? row.tx_pendientes : (total - conc);

    var btns = '<button type="button" class="btn btn-outline-info btn-view-extracto" data-id="' + escapeHtml(row.uuid) +
      '" title="Ver Detalle / Conciliar"><i class="bi bi-eye"></i></button>';
    if (row.procesado && pend > 0) {
      btns += '<button type="button" class="btn btn-outline-primary btn-conciliar-extracto" data-id="' + escapeHtml(row.uuid) +
        '" title="Conciliar Transacciones (' + pend + ' pendientes)"><i class="bi bi-link-45deg"></i></button>';
    }
    if (!row.procesado) {
      btns += '<button type="button" class="btn btn-outline-warning btn-procesar-extracto" data-id="' + escapeHtml(row.uuid) +
        '" title="Procesar Transacciones"><i class="bi bi-cpu"></i></button>';
    }
    if (row.procesado && total > 0) {
      // BAN-12: descarga directa (GET simple), no requiere JS.
      btns += '<a class="btn btn-outline-success" href="/api/v1/bancos/extractos/' + escapeHtml(row.uuid) +
        '/exportar/" title="Exportar reporte de conciliacion (CSV)"><i class="bi bi-file-earmark-spreadsheet"></i></a>';
    }
    btns += '<button type="button" class="btn btn-outline-danger btn-delete-extracto" data-id="' + escapeHtml(row.uuid) +
      '" title="Eliminar"><i class="bi bi-trash"></i></button>';
    return '<div class="btn-group btn-group-sm">' + btns + '</div>';
  }

  var COLUMNS = [
    { data: null, title: 'Cuenta Bancaria', render: renderCuenta },
    { data: null, title: 'Periodo', orderable: false, render: renderPeriodo },
    { data: 'archivo_s3', title: 'Archivo', orderable: false, render: function (v) { return renderArchivo(v); } },
    { data: 'procesado', title: 'Estado', render: function (v) { return renderProcesado(v); } },
    { data: null, title: 'Conciliación', orderable: false, render: renderConciliacion },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  function init() {
    if (inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 20,
      order: [],
    });
    inicializada = true;
  }

  function refresh() {
    if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
      w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
    }
    // Los KPIs siguen server-rendered via HTMX (kpis_extractos.html).
    d.body.dispatchEvent(new CustomEvent('extracto-updated'));
  }

  function redraw() {
    var dt = w.Sintel.Core.DataTablesFactory.get(TABLA_SELECTOR);
    if (dt) dt.columns.adjust();
  }

  async function procesarExtracto(uuid) {
    if (!uuid) return;

    if (w.UIManager?.showLoading) {
      w.UIManager.showLoading('Procesando extracto bancario...');
    }

    const api = w.Sintel.Bancos.API;
    if (!api || !api.extractos) return;

    let res = await api.extractos.procesar(uuid);

    // Fase 24 (importacion no destructiva): el backend rechaza reprocesar un
    // extracto con conciliaciones/aplicaciones salvo forzar=true -- se ofrece
    // confirmar y reintentar en vez de dejar al usuario sin salida.
    if (!res.ok && res.status === 422 && /forzar=true/i.test(_detalle(res))) {
      if (w.UIManager?.hideLoading) w.UIManager.hideLoading();
      if (w.confirm(_detalle(res))) {
        if (w.UIManager?.showLoading) w.UIManager.showLoading('Reprocesando extracto bancario...');
        res = await api.extractos.procesar(uuid, true);
      }
    }

    if (w.UIManager?.hideLoading) {
      w.UIManager.hideLoading();
    }

    if (!res.ok) {
      return w.UIManager?.handleError(res, MOD);
    }

    if (w.UIManager?.showSuccess) {
      w.UIManager.showSuccess('Extracto procesado exitosamente.');
    }

    refresh();
  }

  function _detalle(res) {
    const detail = res?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.join(', ');
    return 'No se pudo procesar el extracto.';
  }

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.ExtractoList = {
    init: init,
    refresh: refresh,
    redraw: redraw,
    procesarExtracto: procesarExtracto
  };

})(window, document);
