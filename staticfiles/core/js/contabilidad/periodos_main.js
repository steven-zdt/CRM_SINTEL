/**
 * periodos_main.js - Orquestador de Periodos Contables v2.61
 * Responsabilidad: Inicializar Tabulator y manejar eventos de la lista.
 */
(function (w, d) {
  'use strict';

  const MOD = '[periodos:main]';
  const TABLE_ID = '#grid-periodos';
  const SEARCH_ID = '#search-periodo';
  const API_URL = '/api/v1/contabilidad/periodos-contables/';
  let table = null;

  function getColumns() {
    return [
      { title: "Periodo", field: "periodo", width: 150 },
      { 
        title: "Fecha Inicio", 
        field: "fecha_inicio", 
        formatter: (cell) => cell.getValue() ? new Date(cell.getValue()).toLocaleDateString('es-CO') : '---' 
      },
      { 
        title: "Fecha Fin", 
        field: "fecha_fin", 
        formatter: (cell) => cell.getValue() ? new Date(cell.getValue()).toLocaleDateString('es-CO') : '---' 
      },
      {
        title: "Estado",
        field: "estado",
        formatter: (cell) => {
          const val = cell.getValue();
          return val === 'ABIERTO' 
            ? '<span class="badge bg-success">Abierto</span>' 
            : '<span class="badge bg-secondary">Cerrado</span>';
        },
        width: 100
      },
      {
        title: "Acciones",
        hozAlign: "center",
        headerSort: false,
        formatter: (cell) => {
          const id = cell.getRow().getData().uuid || cell.getRow().getData().id;
          return `
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-primary btn-ver-periodo" data-id="${id}" title="Ver">
                <i class="bi bi-eye"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-eliminar-periodo" data-id="${id}" title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        }
      }
    ];
  }

  function initTable() {
    if (!w.TabulatorFactory) return console.error(`${MOD} TabulatorFactory no disponible`);

    table = w.TabulatorFactory.create(TABLE_ID, API_URL, getColumns(), {
      searchInputSelector: SEARCH_ID,
      paginationSize: 10
    });

    w.AppPeriodos = w.AppPeriodos || {};
    w.AppPeriodos.table = table;
    
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

      if (btn.classList.contains('btn-ver-periodo')) {
        w.AppPeriodos?.openOffcanvas(id, 'detalle');
      } else if (btn.classList.contains('btn-eliminar-periodo')) {
        w.AppPeriodos?.eliminar(id);
      }
    });
  }

  const init = () => d.querySelector(TABLE_ID) && initTable();

  w.AppPeriodos = w.AppPeriodos || {};
  w.AppPeriodos.init = init;
  w.AppPeriodos.refresh = () => table && table.replaceData();

  if (w.DOMUtils?.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(TABLE_ID, init);
  } else {
    d.addEventListener('DOMContentLoaded', init);
  }

})(window, document);
