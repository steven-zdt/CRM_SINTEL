// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * cuentas_pagar_list.js - Submodulo Cuentas por Pagar List
 *
 * Tabla "Cuentas por Pagar" (#tabla-cuentas-pagar) es DataTables 3.x, pero
 * poblada via un endpoint MANUAL (POST /api/v1/proveedores/cuentas-pagar/dt/,
 * CuentasPagarViewSet.dt()) que NO pasa por Sintel.Core.DataTablesFactory
 * para su logica server-side -- la fuente (CuentasPagarSelector.
 * qs_list_unificado()) es una lista Python que mezcla Factura(COMPRA) +
 * CuentasPagar, no un QuerySet real (ver docstring del selector), asi que
 * DataTableServer (apps/shared/datatable.py) no aplica sin trabajo aparte.
 * Solo se usa DataTablesFactory.create()/reload() para el lado cliente (la
 * inicializacion de DataTables en si) -- el contrato JSON {draw,
 * recordsTotal, recordsFiltered, data} ya lo arma el ViewSet a mano.
 * CuentasPagarTable/CuentasPagarTableView (django-tables2) retirados.
 *
 * Los chips de estado (Todas/Sin Pago/Pago Parcial/Pagadas/Vencidas) viajan
 * por query string en la URL del ajax (igual que ?naturaleza= en
 * facturas_list.js), no por el body de DataTables -- son filtros top-level,
 * no un filtro por columna.
 *
 * El boton "Abono" (.btn-abono-cuentas-pagar) y las acciones Ver/Eliminar
 * siguen siendo manejadas por cuentas_pagar_editor.js (delegacion global en
 * document, sin cambios necesarios ahi).
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:cuentas-pagar]';
  const TABLA_SELECTOR = '#tabla-cuentas-pagar';
  const DT_URL_BASE = '/api/v1/proveedores/cuentas-pagar/dt/';
  const KPI_URL = '/api/v1/proveedores/cuentas-pagar/dashboard-kpis/';
  let kpiBound = false;
  let _tablaInicializada = false;
  let _filtroActivo = { estado: '', vencidas: false };

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function _fmtCop(v) {
    const n = parseFloat(v) || 0;
    // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
    if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
      return '$' + w.DOMUtils.formatCurrency(Math.round(n), { minimumFractionDigits: 0, maximumFractionDigits: 0, showSymbol: false });
    }
    return '$' + Math.round(n).toLocaleString('en-US');
  }

  // ── DataTables (tabla "Cuentas por Pagar") ──────────────────────────────

  function renderNumeroFactura(value) {
    return '<span class="fw-bold text-primary">' + escapeHtml(value || 'S/N') + '</span>';
  }

  function renderProveedorNombre(data, type, row) {
    if (!row.proveedor_nombre) return '<span class="text-muted small">—</span>';
    var nit = row.proveedor_nit
      ? '<div><small class="text-muted">NIT ' + escapeHtml(row.proveedor_nit) + '</small></div>' : '';
    return '<div class="lh-sm">' + escapeHtml(row.proveedor_nombre) + nit + '</div>';
  }

  function renderFechaVencimiento(data, type, row) {
    if (!row.fecha_vencimiento) return '<span class="text-muted small">—</span>';
    var fecha = escapeHtml(row.fecha_vencimiento);
    var hoy = new Date(); hoy.setHours(0, 0, 0, 0);
    var esVencida = row.estado_pago !== 'PAGADA' && new Date(row.fecha_vencimiento) < hoy;
    if (esVencida) {
      return '<span class="text-danger small fw-semibold"><i class="bi bi-alarm me-1"></i>' + fecha + '</span>';
    }
    return '<span class="small">' + fecha + '</span>';
  }

  function renderSaldo(data, type, row) {
    var monto = _fmtCop(data);
    if (row.estado_pago === 'PAGADA' || parseFloat(data) <= 0) {
      return '<span class="text-muted small">' + monto + '</span>';
    }
    return '<span class="text-danger fw-semibold">' + monto + '</span>';
  }

  function renderEstadoPago(data, type, row) {
    if (row.estado_pago === 'PAGADA') return '<span class="badge bg-success">Pagada</span>';
    if (row.estado_pago === 'PARCIAL') return '<span class="badge bg-warning text-dark">Pago Parcial</span>';
    return '<span class="badge bg-danger">Sin Pago</span>';
  }

  function renderAcciones(data, type, row) {
    var botones = '<button type="button" class="btn btn-outline-secondary btn-ver-cuentas-pagar" ' +
      'data-uuid="' + escapeHtml(row.uuid) + '" title="Ver"><i class="bi bi-eye"></i></button>';
    if (row.estado_pago !== 'PAGADA') {
      botones += '<button type="button" class="btn btn-outline-success btn-abono-cuentas-pagar" ' +
        'data-uuid="' + escapeHtml(row.uuid) + '" title="Registrar Abono"><i class="bi bi-cash-coin"></i> Abono</button>';
    }
    if (row.puede_eliminar) {
      botones += '<button type="button" class="btn btn-outline-danger btn-eliminar-cuentas-pagar" ' +
        'data-uuid="' + escapeHtml(row.uuid) + '" title="Eliminar"><i class="bi bi-trash"></i></button>';
    }
    return '<div class="btn-group btn-group-sm">' + botones + '</div>';
  }

  var COLUMNS = [
    { data: 'numero_factura', title: 'Factura', render: function (v) { return renderNumeroFactura(v); } },
    { data: 'proveedor_nombre', title: 'Proveedor', render: renderProveedorNombre },
    { data: 'valor_total', title: 'Monto Total', render: function (v) { return _fmtCop(v); } },
    { data: 'saldo', title: 'Saldo Pendiente', orderable: false, render: renderSaldo },
    { data: 'fecha_vencimiento', title: 'Vencimiento', render: renderFechaVencimiento },
    { data: null, title: 'Estado', render: renderEstadoPago },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  function _ajaxUrl() {
    var params = new URLSearchParams();
    if (_filtroActivo.estado) params.set('estado_pago', _filtroActivo.estado);
    if (_filtroActivo.vencidas) params.set('vencidas', 'true');
    var qs = params.toString();
    return qs ? DT_URL_BASE + '?' + qs : DT_URL_BASE;
  }

  function initTabla() {
    if (_tablaInicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, _ajaxUrl(), COLUMNS, {
      pageLength: 20,
      order: [[4, 'asc']],
    });
    _tablaInicializada = true;
  }

  function aplicarFiltroChip(filtro) {
    if (filtro === 'vencidas') {
      _filtroActivo = { estado: '', vencidas: true };
    } else {
      _filtroActivo = { estado: filtro || '', vencidas: false };
    }
    var dt = w.Sintel.Core.DataTablesFactory.get(TABLA_SELECTOR);
    if (dt) dt.ajax.url(_ajaxUrl()).load();
  }

  function attachChipListeners() {
    var grupo = d.getElementById('filtros-estado-cuentas-pagar');
    if (!grupo) return;
    grupo.addEventListener('click', function (e) {
      var chip = e.target.closest('[data-filtro-cxp]');
      if (!chip) return;
      aplicarFiltroChip(chip.getAttribute('data-filtro-cxp'));
    });
  }

  function attachRefreshListener() {
    var btn = d.getElementById('btn-refresh-cuentas-pagar');
    if (btn) btn.addEventListener('click', function () { w.refreshCuentasPagarTable(); });
  }

  // Funcion global de refresco: recarga la tabla y dispara el evento que
  // sincroniza los KPIs (cargarKPIs, ver mas abajo).
  w.refreshCuentasPagarTable = function () {
    if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
      w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
    }
    d.body.dispatchEvent(new CustomEvent('cuentas-pagar-updated'));
  };

  // ── KPIs (Pendiente/Vencida/Pagado historico) ────────────────────────────

  async function cargarKPIs() {
    try {
      const resp = await fetch(KPI_URL, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!resp.ok) return;
      const data = await resp.json();
      const el = (id) => d.getElementById(id);
      if (el('cxp-pendiente-monto')) el('cxp-pendiente-monto').textContent = _fmtCop(data.deuda_total_pendiente);
      if (el('cxp-vencida-monto')) el('cxp-vencida-monto').textContent = _fmtCop(data.deuda_vencida);
      if (el('cxp-pagado-monto')) el('cxp-pagado-monto').textContent = _fmtCop(data.total_pagado_historico);
    } catch (err) {
      console.error(`${MOD} Error cargando KPIs:`, err);
    }
  }

  function initKPIRefresh() {
    if (kpiBound) return;
    kpiBound = true;
    cargarKPIs();
    // Mismo evento que recarga la tabla -- se mantienen sincronizados.
    d.body.addEventListener('cuentas-pagar-updated', cargarKPIs);
  }

  function setup() {
    initTabla();
    attachChipListeners();
    attachRefreshListener();
    initKPIRefresh();
  }

  // Exportar al Namespace (mantiene compatibilidad con
  // cuentas_pagar_editor.js, que llama a .refresh() tras registrar un abono)
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.CuentasPagarList = {
    refresh: () => w.refreshCuentasPagarTable()
  };

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }

})(window, document);
