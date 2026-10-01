/**
 * pendiente_list.js — Documentos pendientes de contabilizar (On-Demand Manual)
 *
 * DataTables 3.x (mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos/Empleados/Proyectos/Inventario/
 * Contabilidad -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md),
 * pero contra un endpoint MANUAL (POST /api/v1/contabilidad/pendientes/dt/,
 * DocumentosPendientesViewSet.dt()) que NO pasa por
 * Sintel.Core.DataTablesFactory para su logica server-side -- la fuente
 * mezcla 4 modelos de 4 apps (Factura/DocumentoSoporte/Devengo/movimientos
 * de Inventario) en una lista Python, no un QuerySet real. Reemplaza el
 * Tabulator client-side anterior (traia TODOS los pendientes en un solo
 * GET sin paginacion/busqueda server-side).
 *
 * Dependencias: DOMUtils, htmx
 */
(function (w, d) {
  'use strict';

  const MOD = '[pendiente.list]';
  const TABLA_SELECTOR = '#tabla-pendientes';
  const DT_URL = '/api/v1/contabilidad/pendientes/dt/';
  let inicializada = false;

  const TIPO_BADGE = {
    FACTURA:    { cls: 'info',    label: 'Factura' },
    GASTO:      { cls: 'warning', label: 'Gasto' },
    NOMINA:     { cls: 'primary', label: 'Nomina' },
    INVENTARIO: { cls: 'secondary', label: 'Inventario' },
  };

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function fmtMoneda(val) {
    const n = parseFloat(val);
    if (isNaN(n)) return '—';
    // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
    if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
      return '$ ' + w.DOMUtils.formatCurrency(n, { minimumFractionDigits: 2, maximumFractionDigits: 2, showSymbol: false });
    }
    return '$ ' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function renderTipo(value) {
    var t = TIPO_BADGE[value] || { cls: 'secondary', label: value };
    return '<span class="badge bg-' + t.cls + ' text-dark">' + escapeHtml(t.label) + '</span>';
  }

  function renderNumero(value) {
    return '<strong>' + escapeHtml(value || '—') + '</strong>';
  }

  function renderTercero(data, type, row) {
    return '<span title="' + escapeHtml(row.tercero_nit || '') + '">' + escapeHtml(row.tercero_nombre || '—') + '</span>';
  }

  function renderEstado(value) {
    var cls = value === 'ACEPTADA' ? 'success' : value === 'ACTIVO' ? 'primary' : 'secondary';
    return '<span class="badge bg-' + cls + '">' + escapeHtml(value || '') + '</span>';
  }

  function renderAcciones(data, type, row) {
    return '<button class="btn btn-sm btn-success btn-contabilizar" ' +
      'data-app="' + escapeHtml(row.app_label) + '" data-modelo="' + escapeHtml(row.modelo) + '" data-id="' + escapeHtml(row.documento_id) + '" ' +
      'title="Asignar cuentas y contabilizar"><i class="bi bi-journal-plus"></i> Contabilizar</button>';
  }

  var COLUMNS = [
    { data: 'tipo_doc', title: 'Tipo', render: function (v) { return renderTipo(v); } },
    { data: 'numero', title: 'Número', render: function (v) { return renderNumero(v); } },
    { data: 'fecha', title: 'Fecha' },
    { data: null, title: 'Tercero', orderable: false, render: renderTercero },
    { data: 'subtotal', title: 'Subtotal', className: 'text-end', render: function (v) { return fmtMoneda(v); } },
    { data: 'impuestos', title: 'Impuestos', className: 'text-end', render: function (v) { return fmtMoneda(v); } },
    { data: 'total', title: 'Total', className: 'text-end', render: function (v) { return '<strong class="text-success">' + fmtMoneda(v) + '</strong>'; } },
    { data: 'estado', title: 'Estado', orderable: false, render: function (v) { return renderEstado(v); } },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  function actualizarBadgeTotal(dt) {
    const badge = d.getElementById('badge-total-pendientes');
    if (!badge) return;
    const info = dt.page.info();
    const n = info.recordsDisplay || 0;
    badge.textContent = n > 0 ? `${n} pendiente(s)` : '';
  }

  function initTabla() {
    if (inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 15,
      order: [],
      onDraw: actualizarBadgeTotal,
    });
    inicializada = true;
  }

  function reload() {
    if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
      w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
    }
  }

  function attachListeners() {
    // Filtro por tipo_doc (columna 0, server-side via ColumnFilter manual)
    const filterEl = d.querySelector('#filter-tipo-pendiente');
    if (filterEl) {
      filterEl.addEventListener('change', function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 0, this.value);
        }
      });
    }

    // Refrescar
    const btnRefresh = d.querySelector('#btn-refrescar-pendientes');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', reload);
    }

    // Accion Contabilizar (event delegation, sobre document.body -- la
    // tabla se recrea via ajax.reload(), nunca via innerHTML swap)
    d.body.addEventListener('click', function (ev) {
      if (!ev.target.closest(TABLA_SELECTOR)) return;
      const btn = ev.target.closest('.btn-contabilizar');
      if (!btn) return;
      ev.preventDefault();
      const app = btn.dataset.app;
      const modelo = btn.dataset.modelo;
      const id = btn.dataset.id;
      const url = `/api/v1/contabilidad/pendientes/render-offcanvas/?app=${app}&modelo=${modelo}&id=${id}`;
      if (typeof htmx !== 'undefined') {
        htmx.ajax('GET', url, {
          target: '#offcanvas-container-pendientes',
          swap: 'innerHTML',
        });
      }
    });

    // Refresca tabla tras contabilizar exitoso
    d.body.addEventListener('pendientes:refresh', reload);
  }

  function init() {
    initTabla();
    attachListeners();
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  w.PendienteList = Object.freeze({
    init,
    reload,
  });
})(window, document);
