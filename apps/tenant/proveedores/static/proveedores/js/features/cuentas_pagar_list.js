// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * cuentas_pagar_list.js - Submodulo Cuentas por Pagar List v3.16.1
 * Feature-Sliced Design: Responsable de la Lista y Filtrado de Cuentas por Pagar.
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:cuentas-pagar]';
  const GRID_ID = '#grid-cuentas-pagar';
  const SEARCH_ID = '#search-cuentas-pagar';
  const SELECT_ESTADO_ID = '#filtro-estado-cuentas-pagar';
  const API_URL = '/api/v1/proveedores/cuentas-pagar/';
  let table = null;
  let initialized = false;

  /**
   * Formateador de moneda COP
   */
  function fmtMoneda(cell) {
    const val = parseFloat(cell.getValue() || 0);
    return val.toLocaleString('es-CO', {
      style: 'currency', currency: 'COP', maximumFractionDigits: 0
    });
  }

  /**
   * Formateador del estado de pago
   */
  function fmtEstado(cell) {
    const estado = cell.getValue();
    if (estado === 'PAGADA') {
      return '<span class="badge bg-success">Pagada</span>';
    } else if (estado === 'PARCIAL') {
      return '<span class="badge bg-warning text-dark">Pago Parcial</span>';
    } else {
      return '<span class="badge bg-danger">Sin Pago</span>';
    }
  }

  /**
   * Columnas de la tabla Cuentas por Pagar
   */
  function getColumns() {
    return [
      {
        title: "Factura",
        field: "numero_factura",
        formatter: function(cell) {
          const val = cell.getValue() || 'S/N';
          return `<span class="fw-bold text-primary">${val}</span>`;
        },
        width: 140
      },
      {
        title: "Proveedor",
        field: "proveedor_nombre",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback,
        minWidth: 180
      },
      {
        title: "Monto Total",
        field: "valor_total",
        formatter: fmtMoneda,
        width: 130,
        hozAlign: "right"
      },
      {
        title: "Saldo Pendiente",
        field: "saldo",
        formatter: fmtMoneda,
        width: 130,
        hozAlign: "right"
      },
      {
        title: "Vencimiento",
        field: "fecha_vencimiento",
        width: 120,
        hozAlign: "center"
      },
      {
        title: "Estado",
        field: "estado_pago",
        formatter: fmtEstado,
        width: 110,
        hozAlign: "center"
      },
      {
        title: "Acciones",
        field: "acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const uuid = rowData.uuid;
          const esPagada = rowData.estado_pago === 'PAGADA';
          const btnDisabled = esPagada ? 'disabled' : '';
          const btnClass = esPagada ? 'opacity-50' : '';

          return `
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-success btn-abono-cuentas-pagar ${btnClass}" data-uuid="${uuid}" ${btnDisabled} title="Registrar Abono">
                <i class="bi bi-cash-coin"></i> Abono
              </button>
            </div>
          `;
        },
        width: 110,
        headerSort: false,
        hozAlign: "center"
      }
    ];
  }

  /**
   * Inicializar tabla Tabulator
   */
  function initTable() {
    if (!w.TabulatorFactory) return console.error(`${MOD} TabulatorFactory no disponible`);

    if (w.SintelProveedoresTables?.cuentas_pagar) {
      w.SintelProveedoresTables.cuentas_pagar.destroy();
    }

    const spinner = d.querySelector('[data-spinner="cuentas-pagar"]');
    const grid = d.querySelector('[data-grid="cuentas-pagar"]');
    const empty = d.querySelector('[data-empty-state="cuentas-pagar"]');

    function updateUI(loading, loaded, count) {
      if (spinner) spinner.style.display = (!loaded && loading) ? 'block' : 'none';
      if (grid) grid.style.display = loaded ? 'block' : 'none';
      if (empty) empty.style.display = (!loading && loaded && count === 0) ? 'block' : 'none';
    }

    // Set initial loading state
    updateUI(true, false, 0);

    table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), {
      searchInputSelector: SEARCH_ID,
      initialSort: [{ field: "fecha_vencimiento", dir: "asc" }],
      ajaxParams: function() {
        const select = d.querySelector(SELECT_ESTADO_ID);
        const estado = select ? select.value : '';
        const params = {};
        if (estado) {
          params.estado_pago = estado;
        }
        return params;
      }
    });

    if (!table) return;

    table.on("dataLoaded", function(data) {
      updateUI(false, true, data.length);
    });

    if (!w.SintelProveedoresTables) w.SintelProveedoresTables = {};
    w.SintelProveedoresTables.cuentas_pagar = table;

    // Escuchar el cambio en el selector de estado
    const select = d.querySelector(SELECT_ESTADO_ID);
    if (select) {
      select.addEventListener('change', function() {
        if (table) {
          updateUI(true, false, 0);
          table.replaceData().catch(err => console.warn(`${MOD} Error al aplicar filtro de estado:`, err));
        }
      });
    }
  }

  /**
   * Inicializacion
   */
  function init() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return;

    if (initialized) {
      if (table) w.Sintel.Proveedores.CuentasPagarList.refresh();
      return;
    }

    initTable();
    initialized = true;
    console.log(`${MOD} Submodulo Cuentas por Pagar List inicializado.`);
  }

  // Exportar al Namespace
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.CuentasPagarList = {
    init: init,
    refresh: () => {
      if (table && typeof table.replaceData === 'function') {
        table.replaceData().catch(err => console.warn(`${MOD} Error al refrescar Cuentas por Pagar:`, err));
      }
    },
    redraw: () => {
      if (table && typeof table.redraw === 'function') {
        table.redraw(true);
      }
    }
  };

  // NO auto-init en page-load — container oculto en tab inactivo.
  // init() se llama desde proveedores_main.js en shown.bs.tab (skill: tabulator.md §6)

})(window, document);
