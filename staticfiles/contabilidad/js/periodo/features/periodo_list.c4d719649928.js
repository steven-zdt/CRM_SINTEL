/**
 * periodo_list.js - Feature List para PeriodoContable v2.60
 * ⚠️ Feature-Sliced Design: Encargado exclusivamente de renderizar la tabla Tabulator
 * ⚠️ TabulatorFactory v2.40: Usa obligatoriamente TabulatorFactory, cero inicializaciones manuales
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - PeriodoAPI (definido en periodo.api.js)
 */
(function (w, d) {
  'use strict';

  const MOD = '[periodo.list]';
  const TABLE_SELECTOR = '#grid-periodo';
  const SEARCH_SELECTOR = '#search-periodo';
  const FILTER_ESTADO_SELECTOR = '#filter-estado-periodo';
  const API_URL = '/api/v1/contabilidad/periodos-contables/';
  const TAB_ID = '#subtab-periodos';
  let table = null;

  // Helper: Formatear fecha
  function formatDateTime(isoStr) {
    if (!isoStr) return '-';
    try {
      const dt = new Date(isoStr);
      if (Number.isNaN(dt.getTime())) return '-';
      return dt.toLocaleString('es-CO');
    } catch {
      return '-';
    }
  }

  /**
   * Define las columnas de la tabla Tabulator
   */
  function getColumns() {
    return [
      {
        title: "Periodo",
        field: "periodo",
        headerFilter: "input",
        headerFilterPlaceholder: "Buscar periodo...",
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '---';
        }
      },
      {
        title: "Fecha Inicio",
        field: "fecha_inicio",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '---';
          try {
            return new Date(val).toLocaleDateString('es-CO');
          } catch (e) {
            return val;
          }
        }
      },
      {
        title: "Fecha Fin",
        field: "fecha_fin",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '---';
          try {
            return new Date(val).toLocaleDateString('es-CO');
          } catch (e) {
            return val;
          }
        }
      },
      {
        title: "Estado",
        field: "estado",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '---';
          
          const badges = {
            'ABIERTO': '<span class="badge bg-success">Abierto</span>',
            'CERRADO': '<span class="badge bg-danger">Cerrado</span>'
          };
          
          return badges[val] || `<span class="badge bg-light text-dark">${val}</span>`;
        }
      },
      {
        title: "Cerrado Por",
        field: "cerrado_por",
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '---';
        }
      },
      {
        title: "Fecha Cierre",
        field: "fecha_cierre",
        formatter: function(cell) {
          return formatDateTime(cell.getValue());
        }
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const periodoId = rowData.id || '';
          if (!periodoId) return '-';
          
          const estado = rowData.estado || 'ABIERTO';
          
          let cerrarBtn = '';
          if (estado === 'ABIERTO') {
            cerrarBtn = `<button class="btn btn-sm btn-warning btn-cerrar-periodo" data-id="${periodoId}" title="Cerrar periodo">
              <i class="bi bi-lock"></i>
            </button>`;
          }
          
          return `
            <div class="btn-group">
              <button class="btn btn-sm btn-secondary btn-ver-periodo" data-id="${periodoId}" title="Ver detalle">
                <i class="bi bi-eye"></i>
              </button>
              <button class="btn btn-sm btn-primary btn-editar-periodo" data-id="${periodoId}" title="Editar">
                <i class="bi bi-pencil"></i>
              </button>
              ${cerrarBtn}
              <button class="btn btn-sm btn-danger btn-eliminar-periodo" data-id="${periodoId}" title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        headerSort: false,
        hozAlign: "right",
        width: 200
      }
    ];
  }

  /**
   * Inicializa la tabla Tabulator usando TabulatorFactory v2.40
   * ⚠️ CRÍTICO: Usa TabulatorFactory.create(), cero inicializaciones manuales
   */
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(MOD, 'TabulatorFactory no está disponible');
      return null;
    }

    const tableEl = d.querySelector(TABLE_SELECTOR);
    if (!tableEl) {
      console.error(MOD, 'Tabla no encontrada:', TABLE_SELECTOR);
      return null;
    }

    // ⚠️ v2.60: Usar TabulatorFactory v2.40 obligatoriamente
    table = w.TabulatorFactory.create(
      TABLE_SELECTOR,
      API_URL,
      getColumns(),
      {
        searchInputSelector: SEARCH_SELECTOR,
        paginationSize: 10
      }
    );

    // Aplicar filtros iniciales
    applyFilters();

    return table;
  }

  /**
   * Aplica filtros de estado
   */
  function applyFilters() {
    if (!table) return;

    const estadoFilter = d.querySelector(FILTER_ESTADO_SELECTOR)?.value || '';

    if (estadoFilter) {
      table.setFilter([{ field: 'estado', type: '=', value: estadoFilter }]);
    } else {
      table.clearFilter();
    }
  }

  /**
   * Event delegation para acciones de la tabla
   */
  function attachTableListeners() {
    // Ver detalle
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-ver-periodo');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && typeof htmx !== 'undefined') {
          htmx.ajax('GET', `${API_URL}${id}/render-offcanvas/detalle/`, {
            target: '#offcanvas-container-periodo',
            swap: 'innerHTML'
          }).then(() => {
            const offcanvasEl = d.getElementById('offcanvas-periodo-detalle');
            if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
              w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
            }
          });
        }
      }
    });

    // Editar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-editar-periodo');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && typeof htmx !== 'undefined') {
          htmx.ajax('GET', `${API_URL}${id}/render-offcanvas/editar/`, {
            target: '#offcanvas-container-periodo',
            swap: 'innerHTML'
          }).then(() => {
            const offcanvasEl = d.getElementById('offcanvas-periodo-editar');
            if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
              w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
            }
          });
        }
      }
    });

    // Cerrar periodo
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-cerrar-periodo');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && w.PeriodoEditor && typeof w.PeriodoEditor.cerrar === 'function') {
          w.PeriodoEditor.cerrar(id);
        }
      }
    });

    // Eliminar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-eliminar-periodo');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && confirm('¿Está seguro de que desea eliminar este periodo contable?')) {
          if (w.PeriodoEditor && typeof w.PeriodoEditor.delete === 'function') {
            w.PeriodoEditor.delete(id);
          }
        }
      }
    });

    // Filtro de estado
    const filterEstado = d.querySelector(FILTER_ESTADO_SELECTOR);
    if (filterEstado) {
      filterEstado.addEventListener('change', () => {
        applyFilters();
      });
    }

    // Botón refrescar
    const btnRefresh = d.querySelector('#btn-refrescar-periodo');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        if (table && typeof table.replaceData === 'function') {
          table.replaceData();
        }
      });
    }
  }

  /**
   * Inicialización lazy con DOMUtils.onVisibleOnce
   */
  function init() {
    if (!w.TabulatorFactory) {
      console.error(MOD, 'TabulatorFactory no está disponible');
      return;
    }

    if (!w.DOMUtils || typeof w.DOMUtils.onVisibleOnce !== 'function') {
      console.error(MOD, 'DOMUtils.onVisibleOnce no está disponible');
      return;
    }

    // Inicializar tabla cuando el tab sea visible
    w.DOMUtils.onVisibleOnce(TAB_ID, () => {
      table = initTable();
      attachTableListeners();
    });
  }

  // Inicializar cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Exportar API pública
  if (typeof w !== 'undefined') {
    w.PeriodoList = Object.freeze({
      init,
      reload: () => {
        if (table && typeof table.replaceData === 'function') {
          table.replaceData();
        } else {
          init();
        }
      },
      getTable: () => table
    });
  }
})(window, document);
