/**
 * retencion_list.js - Feature List para Retencion v3.16.1
 *
 * Solo lectura — las retenciones son generadas via Pull Model (RetencionesService).
 * Dependencias: TabulatorFactory, DOMUtils.onVisibleOnce
 */
(function (w, d) {
  'use strict';

  const MOD = '[retencion.list]';
  const TABLE_SELECTOR = '#grid-retencion';
  const SEARCH_SELECTOR = '#search-retencion';
  const FILTER_TIPO_SELECTOR = '#filter-tipo-retencion';
  const FILTER_NATURALEZA_SELECTOR = '#filter-naturaleza-retencion';
  const FILTER_REVERSADA_SELECTOR = '#filter-reversada-retencion';
  const API_URL = '/api/v1/contabilidad/retenciones/';
  const TAB_ID = '#subtab-retenciones';
  let table = null;

  function fmtMoney(v) {
    const num = parseFloat(v) || 0;
    const sign = num < 0 ? '-' : '';
    return sign + '$' + Math.abs(num).toLocaleString('es-CO', { minimumFractionDigits: 0 });
  }

  function getColumns() {
    return [
      {
        title: 'Tipo',
        field: 'tipo',
        width: 130,
        hozAlign: 'center',
        formatter: function (cell) {
          const v = cell.getValue();
          const map = {
            RETEFUENTE: '<span class="badge bg-danger">Retefuente</span>',
            RETEICA:    '<span class="badge bg-warning text-dark">ReteICA</span>',
            RETEIVA:    '<span class="badge bg-info text-dark">ReteIVA</span>',
          };
          return map[v] || `<span class="badge bg-secondary">${v || '—'}</span>`;
        }
      },
      {
        title: 'Naturaleza',
        field: 'naturaleza',
        width: 115,
        hozAlign: 'center',
        formatter: function (cell) {
          const v = cell.getValue();
          return v === 'VENTA'
            ? '<span class="badge bg-success">Venta</span>'
            : '<span class="badge bg-primary">Compra</span>';
        }
      },
      {
        title: '%',
        field: 'porcentaje',
        width: 80,
        hozAlign: 'right',
        formatter: function (cell) {
          const v = parseFloat(cell.getValue());
          return isNaN(v) ? '—' : v.toFixed(2) + '%';
        }
      },
      {
        title: 'Monto',
        field: 'monto',
        widthGrow: 1,
        hozAlign: 'right',
        formatter: function (cell) {
          return fmtMoney(cell.getValue());
        }
      },
      {
        title: 'Documento Origen',
        field: 'documento_origen_app',
        widthGrow: 2,
        formatter: function (cell) {
          const row = cell.getRow().getData();
          const app    = row.documento_origen_app    || '';
          const modelo = row.documento_origen_modelo || '';
          const id     = row.documento_origen_id     || '';
          if (!app) return '<span class="text-muted small">—</span>';
          return `<span class="text-muted small">${app} / ${modelo} #${id}</span>`;
        }
      },
      {
        title: 'Estado',
        field: 'reversada',
        width: 110,
        hozAlign: 'center',
        formatter: function (cell) {
          return cell.getValue()
            ? '<span class="badge bg-secondary">Reversada</span>'
            : '<span class="badge bg-success">Activa</span>';
        }
      },
      {
        title: 'Fecha',
        field: 'created_at',
        width: 130,
        formatter: function (cell) {
          const v = cell.getValue();
          if (!v) return '—';
          return new Date(v).toLocaleDateString('es-CO', {
            day: '2-digit', month: 'short', year: 'numeric'
          });
        }
      },
    ];
  }

  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(MOD, 'TabulatorFactory no disponible');
      return null;
    }
    if (!d.querySelector(TABLE_SELECTOR)) {
      console.error(MOD, 'Container no encontrado:', TABLE_SELECTOR);
      return null;
    }

    table = w.TabulatorFactory.create(
      TABLE_SELECTOR,
      API_URL,
      getColumns(),
      {
        searchInputSelector: SEARCH_SELECTOR,
        paginationSize: 20,
        ajaxParams: function () {
          const tipo       = d.querySelector(FILTER_TIPO_SELECTOR)?.value       || '';
          const naturaleza = d.querySelector(FILTER_NATURALEZA_SELECTOR)?.value || '';
          const reversada  = d.querySelector(FILTER_REVERSADA_SELECTOR)?.value  || '';
          const params = {};
          if (tipo)       params.tipo       = tipo;
          if (naturaleza) params.naturaleza = naturaleza;
          if (reversada)  params.reversada  = reversada;
          return params;
        }
      }
    );
    return table;
  }

  function applyFilters() {
    if (table && typeof table.replaceData === 'function') {
      table.replaceData();
    }
  }

  function attachListeners() {
    d.querySelector(FILTER_TIPO_SELECTOR)?.addEventListener('change', applyFilters);
    d.querySelector(FILTER_NATURALEZA_SELECTOR)?.addEventListener('change', applyFilters);
    d.querySelector(FILTER_REVERSADA_SELECTOR)?.addEventListener('change', applyFilters);

    d.querySelector('#btn-refrescar-retencion')?.addEventListener('click', applyFilters);
  }

  function init() {
    if (!w.TabulatorFactory) {
      console.error(MOD, 'TabulatorFactory no disponible');
      return;
    }
    if (!w.DOMUtils || typeof w.DOMUtils.onVisibleOnce !== 'function') {
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

  if (typeof w !== 'undefined') {
    w.RetencionList = Object.freeze({
      init,
      reload: function () {
        if (table && typeof table.replaceData === 'function') {
          table.replaceData();
        } else {
          init();
        }
      },
      getTable: function () { return table; }
    });
  }
})(window, document);
