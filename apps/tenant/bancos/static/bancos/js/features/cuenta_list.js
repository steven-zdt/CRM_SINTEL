// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * cuenta_list.js - Controlador de Lista de Cuentas Bancarias
 * Namespace: window.Sintel.Bancos.CuentaList
 * ⚠️ FSD / Vanilla JS
 */
(function (w, d) {
  'use strict';

  const MOD = '[bancos:cuenta_list]';
  const GRID_ID = '#grid-cuentas';
  const SEARCH_ID = '#search-cuenta';
  const API_URL = '/api/v1/bancos/cuentas/';
  let table = null;
  let initialized = false;

  const BANCOS_MAP = {
    'BANCOLOMBIA': 'Bancolombia',
    'BANCO_BOGOTA': 'Banco de Bogotá',
    'DAVIVIENDA': 'Davivienda',
    'BBVA': 'BBVA',
    'OCCIDENTE': 'Banco de Occidente',
    'POPULAR': 'Banco Popular',
    'AV_VILLAS': 'Banco AV Villas'
  };

  const TIPOS_CUENTA_MAP = {
    'AHORROS': 'Ahorros',
    'CORRIENTE': 'Corriente'
  };

  function fmtBanco(cell) {
    const val = cell.getValue();
    return BANCOS_MAP[val] || val || '—';
  }

  function fmtTipo(cell) {
    const val = cell.getValue();
    return TIPOS_CUENTA_MAP[val] || val || '—';
  }

  function getColumns() {
    return [
      {
        title: "Nombre de la Cuenta",
        field: "nombre",
        widthGrow: 2,           // columna flexible — ocupa el espacio disponible
        headerSort: true
      },
      {
        title: "Banco",
        field: "banco",
        formatter: fmtBanco,
        widthGrow: 1,
        minWidth: 130,
        headerSort: true
      },
      {
        title: "Tipo",
        field: "tipo",
        formatter: fmtTipo,
        width: 110,
        hozAlign: "center",
        headerSort: false
      },
      {
        title: "Número",
        field: "numero",
        width: 160,
        headerSort: false
      },
      {
        title: "Acciones",
        field: "acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const identifier = rowData.uuid || rowData.id;
          return `<div class="btn-group btn-group-sm" role="group">
            <button type="button" class="btn btn-outline-primary btn-edit-cuenta" data-id="${identifier}" title="Editar">
              <i class="bi bi-pencil"></i>
            </button>
            <button type="button" class="btn btn-outline-danger btn-delete-cuenta" data-id="${identifier}" title="Eliminar">
              <i class="bi bi-trash"></i>
            </button>
          </div>`;
        },
        width: 95,
        headerSort: false,
        hozAlign: "center"
      }
    ];
  }

  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(`${MOD} TabulatorFactory no disponible`);
      return;
    }

    const spinner = d.querySelector('[data-spinner="cuentas"]');
    const emptyState = d.querySelector('[data-empty-state="cuentas"]');
    const gridEl = d.querySelector(GRID_ID);

    if (spinner) spinner.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (gridEl) gridEl.style.display = 'none';

    table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), {
      searchInputSelector: SEARCH_ID,
      layout: "fitDataFill",    // fitDataFill: columnas ajustan al dato, llenan espacio restante sin desbordar
    });

    if (table) {
      table.on("dataLoaded", function (data) {
        if (spinner) spinner.style.display = 'none';
        if (data.length === 0) {
          if (emptyState) emptyState.style.display = 'block';
          if (gridEl) gridEl.style.display = 'none';
        } else {
          if (emptyState) emptyState.style.display = 'none';
          if (gridEl) gridEl.style.display = 'block';
        }
      });
    }
  }

  function init() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return;

    if (initialized) {
      refresh();
      return;
    }

    console.log(`${MOD} Inicializando tabla de cuentas...`);
    initTable();
    initialized = true;
  }

  function refresh() {
    if (table && typeof table.replaceData === 'function') {
      table.replaceData().catch(err => console.warn(`${MOD} Error al refrescar tabla:`, err));
    }
  }

  // Recalcula dimensiones de columnas — llamar al mostrar el tab (container oculto al inicializar)
  function redraw() {
    if (table && typeof table.redraw === 'function') {
      table.redraw(true);
    }
  }

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.CuentaList = {
    init: init,
    refresh: refresh,
    redraw: redraw
  };

})(window, document);
