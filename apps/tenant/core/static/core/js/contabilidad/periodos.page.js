/**
 * periodos.page.js - Página Principal de Períodos Contables v2.61
 * ⚠️ Feature-Sliced Design: Script dedicado exclusivamente para PeriodoContable
 * ⚠️ Namespace: window.PeriodosPage
 * 
 * Funcionalidades:
 * 1. Inicialización de tabla Tabulator (#grid-periodos)
 * 2. Event delegation para crear, editar, eliminar períodos
 * 3. Sincronización con HTMX para offcanvas
 * 4. Manejo de errores con UIManager
 */

(function (w, d) {
  'use strict';

  const MOD = '[periodos.page]';
  const API_URL = '/api/v1/contabilidad/periodos-contables/';
  const GRID_ID = '#grid-periodos';
  const OFFCANVAS_CONTAINER_ID = '#offcanvas-container-periodo';
  const ERROR_CONTAINER_ID = '#error-container-periodos';
  const SEARCH_INPUT_ID = '#search-periodo';
  const FILTER_ESTADO_ID = '#filter-estado-periodo';
  const BTN_CREAR_ID = '#btn-crear-periodo';
  const BTN_REFRESCAR_ID = '#btn-refrescar-periodo';

  console.log(`%c${MOD} ✅ Módulo cargado`, 'color: #51cf66; font-weight: bold; font-size: 12px;');

  /**
   * Objeto PeriodosPage - Namespace principal
   */
  const PeriodosPage = {
    table: null,
    searchTimeout: null,

    /**
     * Inicializar módulo
     */
    init: function () {
      console.log(`${MOD} Inicializando...`);
      
      this.initTabulator();
      this.bindEvents();
      this.bindHTMXListeners();
      
      console.log(`${MOD} ✅ Inicialización completada`);
    },

    /**
     * Inicializar tabla Tabulator
     */
    initTabulator: function () {
      const gridElement = d.querySelector(GRID_ID);
      if (!gridElement) {
        console.warn(`${MOD} Elemento ${GRID_ID} no encontrado`);
        return;
      }

      try {
        this.table = new Tabulator(GRID_ID, {
          ajaxURL: API_URL,
          ajaxParams: {
            search: d.querySelector(SEARCH_INPUT_ID)?.value || '',
            estado: d.querySelector(FILTER_ESTADO_ID)?.value || ''
          },
          layout: 'fitColumns',
          responsiveLayout: 'collapse',
          pagination: 'remote',
          paginationSize: 10,
          columns: [
            { title: 'Nombre', field: 'nombre', width: 150 },
            { title: 'Inicio', field: 'fecha_inicio', width: 120 },
            { title: 'Fin', field: 'fecha_fin', width: 120 },
            { title: 'Estado', field: 'estado', width: 100 },
            {
              title: 'Acciones',
              width: 150,
              formatter: (cell) => {
                const uuid = cell.getRow().getData().uuid;
                return `
                  <button class="btn btn-sm btn-outline-primary btn-editar-periodo" data-uuid="${uuid}" title="Editar">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger btn-eliminar-periodo" data-uuid="${uuid}" title="Eliminar">
                    <i class="bi bi-trash"></i>
                  </button>
                `;
              }
            }
          ]
        });

        console.log(`${MOD} Tabulator inicializado correctamente`);
      } catch (error) {
        console.error(`${MOD} Error al inicializar Tabulator:`, error);
      }
    },

    /**
     * Vincular eventos de delegación
     */
    bindEvents: function () {
      // Búsqueda
      const searchInput = d.querySelector(SEARCH_INPUT_ID);
      if (searchInput) {
        searchInput.addEventListener('keyup', (e) => {
          clearTimeout(this.searchTimeout);
          this.searchTimeout = setTimeout(() => {
            this.reloadTable();
          }, 500);
        });
      }

      // Filtro de estado
      const filterEstado = d.querySelector(FILTER_ESTADO_ID);
      if (filterEstado) {
        filterEstado.addEventListener('change', () => {
          this.reloadTable();
        });
      }

      // Botón refrescar
      const btnRefrescar = d.querySelector(BTN_REFRESCAR_ID);
      if (btnRefrescar) {
        btnRefrescar.addEventListener('click', () => {
          this.reloadTable();
        });
      }

      // Delegación: Editar período
      d.addEventListener('click', (e) => {
        if (e.target.closest('.btn-editar-periodo')) {
          const uuid = e.target.closest('.btn-editar-periodo').dataset.uuid;
          this.handleEditar(uuid);
        }
      });

      // Delegación: Eliminar período
      d.addEventListener('click', (e) => {
        if (e.target.closest('.btn-eliminar-periodo')) {
          const uuid = e.target.closest('.btn-eliminar-periodo').dataset.uuid;
          this.handleEliminar(uuid);
        }
      });

      console.log(`${MOD} Eventos vinculados`);
    },

    /**
     * Vincular listeners HTMX
     */
    bindHTMXListeners: function () {
      const container = d.querySelector(OFFCANVAS_CONTAINER_ID);
      if (!container) {
        console.warn(`${MOD} Contenedor HTMX ${OFFCANVAS_CONTAINER_ID} no encontrado`);
        return;
      }

      // Después de cargar offcanvas
      container.addEventListener('htmx:afterSwap', (e) => {
        console.log(`${MOD} htmx:afterSwap disparado`);
        // Reinicializar si es necesario
      });

      // Después de completar la carga
      container.addEventListener('htmx:afterOnLoad', (e) => {
        console.log(`${MOD} htmx:afterOnLoad disparado`);
      });

      console.log(`${MOD} Listeners HTMX vinculados`);
    },

    /**
     * Recargar tabla
     */
    reloadTable: function () {
      if (!this.table) return;
      
      const search = d.querySelector(SEARCH_INPUT_ID)?.value || '';
      const estado = d.querySelector(FILTER_ESTADO_ID)?.value || '';
      
      this.table.setData(API_URL, {
        search: search,
        estado: estado
      });
      
      console.log(`${MOD} Tabla recargada`);
    },

    /**
     * Manejar edición de período
     */
    handleEditar: function (uuid) {
      console.log(`${MOD} Editando período:`, uuid);
      
      const container = d.querySelector(OFFCANVAS_CONTAINER_ID);
      if (!container) {
        console.error(`${MOD} Contenedor ${OFFCANVAS_CONTAINER_ID} no encontrado`);
        return;
      }

      // HTMX cargará el offcanvas
      htmx.ajax('GET', `${API_URL}${uuid}/render-offcanvas/editar/`, {
        target: container,
        swap: 'innerHTML',
        onAfterSwap: () => {
          const offcanvasEl = d.querySelector('#offcanvas-periodo-editar');
          if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
            w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
          }
        }
      });
    },

    /**
     * Manejar eliminación de período
     */
    handleEliminar: function (uuid) {
      console.log(`${MOD} Eliminando período:`, uuid);
      
      if (!confirm('¿Está seguro de que desea eliminar este período?')) {
        return;
      }

      htmx.ajax('DELETE', `${API_URL}${uuid}/`, {
        onAfterRequest: (xhr) => {
          if (xhr.status === 204) {
            console.log(`${MOD} Período eliminado correctamente`);
            this.reloadTable();
            
            // Mostrar feedback
            if (w.SintelFeedback) {
              w.SintelFeedback.success('Período eliminado correctamente');
            }
          } else {
            console.error(`${MOD} Error al eliminar período:`, xhr);
            
            // Mostrar error
            if (w.UIManager) {
              w.UIManager.handleError(xhr, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
            }
          }
        }
      });
    },

    /**
     * Debug - Ver estado actual
     */
    debug: function () {
      console.log(`${MOD} Estado actual:`, {
        table: this.table ? 'Inicializada' : 'No inicializada',
        gridElement: d.querySelector(GRID_ID) ? 'Encontrado' : 'No encontrado',
        offcanvasContainer: d.querySelector(OFFCANVAS_CONTAINER_ID) ? 'Encontrado' : 'No encontrado'
      });
    }
  };

  /**
   * Exponer en window
   */
  w.PeriodosPage = PeriodosPage;

  /**
   * Inicializar cuando el DOM esté listo
   */
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', () => {
      PeriodosPage.init();
    });
  } else {
    PeriodosPage.init();
  }

  /**
   * Re-inicializar con HTMX
   */
  d.addEventListener('htmx:afterSwap', () => {
    if (d.querySelector(GRID_ID)) {
      PeriodosPage.init();
    }
  });

})(window, document);
