/**
 * cuentas_main.js - Orquestador de Cuentas Contables v2.61
 * Responsabilidad: Inicializar Tabulator y manejar eventos de la lista.
 */
(function (w, d) {
  'use strict';

  const MOD = '[cuentas:main]';
  const TABLE_ID = '#grid-cuentas';
  const SEARCH_ID = '#search-cuenta';
  const API_URL = '/api/v1/contabilidad/cuentas-contables/';
  let table = null;

  function getColumns() {
    return [
      { title: "Código", field: "codigo", headerFilter: "input", width: 150 },
      { title: "Nombre", field: "nombre", headerFilter: "input", minWidth: 250 },
      {
        title: "Tipo",
        field: "tipo",
        formatter: (cell) => {
          const val = cell.getValue();
          const colors = { 'ACTIVO': 'primary', 'PASIVO': 'danger', 'PATRIMONIO': 'success', 'INGRESO': 'info', 'GASTO': 'warning' };
          return `<span class="badge bg-${colors[val] || 'secondary'}">${val}</span>`;
        },
        width: 120
      },
      {
        title: "Estado",
        field: "activa",
        formatter: (cell) => cell.getValue() ? '<span class="badge bg-success">Activa</span>' : '<span class="badge bg-secondary">Inactiva</span>',
        width: 100,
        hozAlign: "center"
      },
      {
        title: "Acciones",
        hozAlign: "right",
        headerSort: false,
        formatter: (cell) => {
          const id = cell.getRow().getData().id;
          return `
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-secondary btn-ver-cuenta" data-id="${id}" title="Ver">
                <i class="bi bi-eye"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-eliminar-cuenta" data-id="${id}" title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        width: 120
      }
    ];
  }

  function initTable() {
    if (!w.TabulatorFactory) return console.error(`${MOD} TabulatorFactory no disponible`);

    table = w.TabulatorFactory.create(TABLE_ID, API_URL, getColumns(), {
      searchInputSelector: SEARCH_ID,
      paginationSize: 10
    });

    w.AppCuentas = w.AppCuentas || {};
    w.AppCuentas.table = table;
    
    initEvents();
  }

  function initEvents() {
    const grid = d.querySelector(TABLE_ID);
    if (!grid) return;

    grid.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      const id = btn.dataset.id;
      if (!id) return;

      if (btn.classList.contains('btn-ver-cuenta')) {
        w.AppCuentas?.openOffcanvas(id, 'detalle');
      } else if (btn.classList.contains('btn-eliminar-cuenta')) {
        w.AppCuentas?.eliminar(id);
      }
    });
  }

  const init = () => d.querySelector(TABLE_ID) && initTable();

  w.AppCuentas = w.AppCuentas || {};
  w.AppCuentas.init = init;
  w.AppCuentas.refresh = () => table && table.replaceData();

  if (w.DOMUtils?.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(TABLE_ID, init);
  } else {
    d.addEventListener('DOMContentLoaded', init);
  }

})(window, document);
