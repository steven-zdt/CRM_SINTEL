/**
 * cuenta_list.js - Feature List para CuentaContable v2.60
 * ⚠️ Feature-Sliced Design: Encargado exclusivamente de renderizar la tabla Tabulator
 * ⚠️ TabulatorFactory v2.40: Usa obligatoriamente TabulatorFactory, cero inicializaciones manuales
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - CuentaAPI (definido en cuenta.api.js)
 */
(function (w, d) {
  'use strict';

  const MOD = '[cuenta.list]';
  const TABLE_SELECTOR = '#grid-cuenta';
  const SEARCH_SELECTOR = '#search-cuenta';
  const API_URL = '/api/v1/contabilidad/cuentas-contables/';
  const TAB_ID = '#subtab-cuentas';
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
   * ⚠️ v2.60: Campos alineados con CuentaContableListSerializer
   */
  function getColumns() {
    return [
      {
        title: "Código",
        field: "codigo",
        headerFilter: "input",
        headerFilterPlaceholder: "Buscar código...",
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '---';
        }
      },
      {
        title: "Nombre",
        field: "nombre",
        headerFilter: "input",
        headerFilterPlaceholder: "Buscar nombre...",
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '---';
        }
      },
      {
        title: "Tipo",
        field: "tipo",
        formatter: function(cell) {
          const data = cell.getValue();
          if (!data) return '-';
          const badges = {
            'ACTIVO': 'primary',
            'PASIVO': 'danger',
            'PATRIMONIO': 'success',
            'INGRESO': 'info',
            'GASTO': 'warning'
          };
          const badge = badges[data] || 'secondary';
          return `<span class="badge bg-${badge}">${data}</span>`;
        }
      },
      {
        title: "Estado",
        field: "activa",
        formatter: function(cell) {
          const data = cell.getValue();
          if (data === true || data === 'true') {
            return '<span class="badge bg-success">Activa</span>';
          } else {
            return '<span class="badge bg-secondary">Inactiva</span>';
          }
        },
        headerSort: false
      },
      {
        title: "Creado",
        field: "created_at",
        formatter: function(cell) {
          return formatDateTime(cell.getValue());
        }
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const cuentaId = rowData.id || '';
          if (!cuentaId) return '-';
          return `
            <div class="btn-group">
              <button class="btn btn-sm btn-secondary btn-ver-cuenta" data-id="${cuentaId}" title="Ver detalle">
                <i class="bi bi-eye"></i>
              </button>
              <button class="btn btn-sm btn-primary btn-editar-cuenta" data-id="${cuentaId}" title="Editar">
                <i class="bi bi-pencil"></i>
              </button>
              <button class="btn btn-sm btn-danger btn-eliminar-cuenta" data-id="${cuentaId}" title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        headerSort: false,
        hozAlign: "right",
        width: 150
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

    return table;
  }

  /**
   * Event delegation para acciones de la tabla
   */
  function attachTableListeners() {
    // Ver detalle
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-ver-cuenta');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && typeof htmx !== 'undefined') {
          htmx.ajax('GET', `${API_URL}${id}/render-offcanvas/detalle/`, {
            target: '#offcanvas-container-cuenta',
            swap: 'innerHTML'
          }).then(() => {
            const offcanvasEl = d.getElementById('offcanvas-cuenta-detalle');
            if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
              w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
            }
          });
        }
      }
    });

    // Editar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-editar-cuenta');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && typeof htmx !== 'undefined') {
          htmx.ajax('GET', `${API_URL}${id}/render-offcanvas/editar/`, {
            target: '#offcanvas-container-cuenta',
            swap: 'innerHTML'
          }).then(() => {
            const offcanvasEl = d.getElementById('offcanvas-cuenta-editar');
            if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
              w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
            }
          });
        }
      }
    });

    // Eliminar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-eliminar-cuenta');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id && confirm('¿Está seguro de que desea eliminar esta cuenta contable?')) {
          if (w.CuentaEditor && typeof w.CuentaEditor.delete === 'function') {
            w.CuentaEditor.delete(id);
          }
        }
      }
    });

    // Botón refrescar
    const btnRefresh = d.querySelector('#btn-refrescar-cuenta');
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
    w.CuentaList = Object.freeze({
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
