/**
 * asiento_list.js - Feature List para AsientoContable v2.60
 * ⚠️ Feature-Sliced Design: Encargado exclusivamente de renderizar la tabla Tabulator
 * ⚠️ TabulatorFactory v2.40: Usa obligatoriamente TabulatorFactory, cero inicializaciones manuales
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - AsientoAPI (definido en asiento.api.js)
 */
(function (w, d) {
  'use strict';

  const MOD = '[asiento.list]';
  const TABLE_SELECTOR = '#grid-asiento';
  const SEARCH_SELECTOR = '#search-asiento';
  const FILTER_ESTADO_SELECTOR = '#filter-estado-asiento';
  const FILTER_CUADRATURA_SELECTOR = '#filter-cuadratura-asiento';
  const API_URL = '/api/v1/contabilidad/asientos-contables/';
  const TAB_ID = '#subtab-asientos';
  let table = null;

  // Helper: Formatear dinero
  function fmtMoney(v) {
    if (w.DOMUtils && typeof w.DOMUtils.fmtMoney === 'function') {
      return w.DOMUtils.fmtMoney(v);
    }
    const num = parseFloat(v) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  }

  /**
   * Define las columnas de la tabla Tabulator
   * ⚠️ v2.60: Campos alineados con AsientoContableListSerializer
   */
  function getColumns() {
    return [
      {
        title: "Número",
        field: "numero",
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '---';
        }
      },
      {
        title: "Fecha",
        field: "fecha",
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
        title: "Descripción",
        field: "descripcion",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '---';
          return val.length > 50 ? val.substring(0, 50) + '...' : val;
        }
      },
      {
        title: "Estado",
        field: "estado",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '---';
          
          const badges = {
            'BORRADOR': '<span class="badge bg-secondary">Borrador</span>',
            'APROBADO': '<span class="badge bg-success">Aprobado</span>',
            'CERRADO': '<span class="badge bg-info">Cerrado</span>'
          };
          
          return badges[val] || `<span class="badge bg-light text-dark">${val}</span>`;
        }
      },
      {
        title: "Movimientos",
        field: "movimientos_count",
        formatter: function(cell) {
          const val = cell.getValue();
          const count = parseInt(val) || 0;
          if (count === 0) {
            return '<span class="text-muted">0</span>';
          }
          return `<span class="badge bg-primary">${count}</span>`;
        },
        hozAlign: "center"
      },
      {
        title: "Débito",
        field: "total_debe",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return fmtMoney(val);
        },
        hozAlign: "right"
      },
      {
        title: "Crédito",
        field: "total_haber",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return fmtMoney(val);
        },
        hozAlign: "right"
      },
      {
        title: "Cuadratura",
        field: "cuadratura",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const debe = parseFloat(rowData.total_debe) || 0;
          const haber = parseFloat(rowData.total_haber) || 0;
          const diferencia = Math.abs(debe - haber);
          
          if (diferencia < 0.01) {
            return '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Cuadrado</span>';
          } else {
            return `<span class="badge bg-danger"><i class="bi bi-x-circle"></i> ${fmtMoney(diferencia)}</span>`;
          }
        },
        hozAlign: "center"
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const asientoId = rowData.uuid || '';
          if (!asientoId) return '-';
          
          const estado = rowData.estado || 'BORRADOR';
          const cuadratura = rowData.cuadratura === true;
          
          let aprobarBtn = '';
          if (estado === 'BORRADOR' && cuadratura) {
            aprobarBtn = `<button class="btn btn-sm btn-success btn-aprobar-asiento" data-id="${asientoId}" title="Aprobar">
              <i class="bi bi-check-circle"></i>
            </button>`;
          }
          
          return `
            <div class="btn-group">
              <button class="btn btn-sm btn-secondary btn-ver-asiento" data-id="${asientoId}" title="Ver detalle">
                <i class="bi bi-eye"></i>
              </button>
              <button class="btn btn-sm btn-primary btn-editar-asiento" data-id="${asientoId}" title="Editar">
                <i class="bi bi-pencil"></i>
              </button>
              ${aprobarBtn}
              <button class="btn btn-sm btn-danger btn-eliminar-asiento" data-id="${asientoId}" title="Eliminar">
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
        paginationSize: 10,
        // Pasar filtro estado al servidor — client-side setFilter() no funciona
        // con paginacion remota porque filtra solo la pagina cargada.
        ajaxParams: function() {
          const estado = d.querySelector(FILTER_ESTADO_SELECTOR)?.value || '';
          return estado ? { estado } : {};
        }
      }
    );

    return table;
  }

  /**
   * Recarga la tabla con los filtros actuales como parametros de API.
   * Usa replaceData() para re-ejecutar ajaxURLGenerator con los valores
   * actuales del dropdown, enviandolos al servidor como query params.
   */
  function applyFilters() {
    if (!table || typeof table.replaceData !== 'function') return;
    table.replaceData();
  }

  /**
   * Event delegation para acciones de la tabla
   */
  function attachTableListeners() {
    // Ver detalle
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-ver-asiento');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && typeof htmx !== 'undefined') {
          htmx.ajax('GET', `${API_URL}${id}/render-offcanvas/detalle/`, {
            target: '#offcanvas-container-asiento',
            swap: 'innerHTML'
          }).then(() => {
            const offcanvasEl = d.getElementById('offcanvas-asiento-detalle');
            if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
              w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
            }
          });
        }
      }
    });

    // Editar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-editar-asiento');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && typeof htmx !== 'undefined') {
          htmx.ajax('GET', `${API_URL}${id}/render-offcanvas/editar/`, {
            target: '#offcanvas-container-asiento',
            swap: 'innerHTML'
          }).then(() => {
            const offcanvasEl = d.getElementById('offcanvas-asiento-editar');
            if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
              w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
            }
          });
        }
      }
    });

    // Aprobar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-aprobar-asiento');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && w.AsientoEditor && typeof w.AsientoEditor.aprobar === 'function') {
          w.AsientoEditor.aprobar(id);
        }
      }
    });

    // Eliminar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-eliminar-asiento');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && confirm('¿Está seguro de que desea eliminar este asiento contable?')) {
          if (w.AsientoEditor && typeof w.AsientoEditor.delete === 'function') {
            w.AsientoEditor.delete(id);
          }
        }
      }
    });

    // Filtros
    const filterEstado = d.querySelector(FILTER_ESTADO_SELECTOR);
    const filterCuadratura = d.querySelector(FILTER_CUADRATURA_SELECTOR);
    
    if (filterEstado) {
      filterEstado.addEventListener('change', () => {
        applyFilters();
      });
    }
    
    if (filterCuadratura) {
      filterCuadratura.addEventListener('change', () => {
        applyFilters();
      });
    }

    // Botón refrescar
    const btnRefresh = d.querySelector('#btn-refrescar-asiento');
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
    w.AsientoList = Object.freeze({
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
