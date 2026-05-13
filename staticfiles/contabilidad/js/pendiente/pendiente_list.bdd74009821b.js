/**
 * pendiente_list.js — Documentos pendientes de contabilizar (On-Demand Manual)
 *
 * Dependencias: TabulatorFactory, DOMUtils, window.jwtAuth, htmx
 */
(function (w, d) {
  'use strict';

  const MOD = '[pendiente.list]';
  const TABLE_SELECTOR = '#grid-pendientes';
  const SEARCH_SELECTOR = '#search-pendiente';
  const FILTER_TIPO_SELECTOR = '#filter-tipo-pendiente';
  const API_URL = '/api/v1/contabilidad/pendientes/';
  const TAB_ID = '#subtab-pendientes';
  let table = null;

  const TIPO_BADGE = {
    FACTURA:    { cls: 'info',    label: 'Factura' },
    GASTO:      { cls: 'warning', label: 'Gasto' },
    NOMINA:     { cls: 'primary', label: 'Nomina' },
    INVENTARIO: { cls: 'secondary', label: 'Inventario' },
  };

  function fmtMoneda(val) {
    const n = parseFloat(val);
    if (isNaN(n)) return '—';
    return '$ ' + n.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function getColumns() {
    return [
      {
        title: 'Tipo',
        field: 'tipo_doc',
        width: 115,
        formatter: function (cell) {
          const v = cell.getValue();
          const t = TIPO_BADGE[v] || { cls: 'secondary', label: v };
          return `<span class="badge bg-${t.cls} text-dark">${t.label}</span>`;
        },
      },
      {
        title: 'Número',
        field: 'numero',
        headerFilter: 'input',
        headerFilterPlaceholder: 'Filtrar...',
        formatter: function (cell) {
          return `<strong>${cell.getValue() || '—'}</strong>`;
        },
      },
      { title: 'Fecha', field: 'fecha', width: 110, sorter: 'date' },
      {
        title: 'Tercero',
        field: 'tercero_nombre',
        headerFilter: 'input',
        headerFilterPlaceholder: 'Filtrar...',
        formatter: function (cell) {
          const row = cell.getRow().getData();
          return `<span title="${row.tercero_nit || ''}">${cell.getValue() || '—'}</span>`;
        },
      },
      {
        title: 'Subtotal',
        field: 'subtotal',
        hozAlign: 'right',
        sorter: 'number',
        formatter: function (cell) { return fmtMoneda(cell.getValue()); },
      },
      {
        title: 'Impuestos',
        field: 'impuestos',
        hozAlign: 'right',
        sorter: 'number',
        formatter: function (cell) { return fmtMoneda(cell.getValue()); },
      },
      {
        title: 'Total',
        field: 'total',
        hozAlign: 'right',
        sorter: 'number',
        formatter: function (cell) {
          return `<strong class="text-success">${fmtMoneda(cell.getValue())}</strong>`;
        },
      },
      {
        title: 'Estado',
        field: 'estado',
        width: 110,
        formatter: function (cell) {
          const v = cell.getValue();
          const cls = v === 'ACEPTADA' ? 'success' : v === 'ACTIVO' ? 'primary' : 'secondary';
          return `<span class="badge bg-${cls}">${v}</span>`;
        },
      },
      {
        title: '',
        formatter: function (cell) {
          const row = cell.getRow().getData();
          return `<button class="btn btn-sm btn-success btn-contabilizar"
                    data-app="${row.app_label}"
                    data-modelo="${row.modelo}"
                    data-id="${row.documento_id}"
                    title="Asignar cuentas y contabilizar">
                    <i class="bi bi-journal-plus"></i> Contabilizar
                  </button>`;
        },
        headerSort: false,
        hozAlign: 'center',
        width: 145,
      },
    ];
  }

  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(MOD, 'TabulatorFactory no disponible');
      return null;
    }
    const el = d.querySelector(TABLE_SELECTOR);
    if (!el) {
      console.error(MOD, 'Elemento no encontrado:', TABLE_SELECTOR);
      return null;
    }

    table = w.TabulatorFactory.create(
      TABLE_SELECTOR,
      API_URL,
      getColumns(),
      {
        searchInputSelector: SEARCH_SELECTOR,
        paginationSize: 15,
      }
    );

    table.on('dataLoaded', function (data) {
      const badge = d.getElementById('badge-total-pendientes');
      if (badge) {
        const n = Array.isArray(data) ? data.length : 0;
        badge.textContent = n > 0 ? `${n} pendiente(s)` : '';
      }
    });

    return table;
  }

  function attachListeners() {
    // Filtro por tipo_doc (client-side via Tabulator filter API)
    const filterEl = d.querySelector(FILTER_TIPO_SELECTOR);
    if (filterEl) {
      filterEl.addEventListener('change', function () {
        if (!table) return;
        if (this.value) {
          table.setFilter('tipo_doc', '=', this.value);
        } else {
          // false = preservar header filters de columnas (numero, tercero_nombre)
          table.clearFilter(false);
        }
      });
    }

    // Refrescar
    const btnRefresh = d.querySelector('#btn-refrescar-pendientes');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', function () {
        if (table) table.replaceData();
      });
    }

    // Accion Contabilizar (event delegation)
    d.addEventListener('click', function (ev) {
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
    d.body.addEventListener('pendientes:refresh', function () {
      if (table) table.replaceData();
    });
  }

  function init() {
    if (!w.DOMUtils?.onVisibleOnce) {
      console.error(MOD, 'DOMUtils.onVisibleOnce no disponible');
      return;
    }
    w.DOMUtils.onVisibleOnce(TAB_ID, function () {
      table = initTable();
      attachListeners();
    });
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  w.PendienteList = Object.freeze({
    init,
    reload: function () {
      if (table) table.replaceData();
      else init();
    },
  });
})(window, document);
