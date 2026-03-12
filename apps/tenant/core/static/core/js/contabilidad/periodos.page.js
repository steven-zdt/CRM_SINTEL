/**
 * periodos.page.js - Módulo Principal de Periodos Contables v2.61 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.61: Migración a TabulatorFactory v2.40
 * - Inicialización de Tabulator Factory
 * - Event delegation para acciones de tabla
 * - Integración con offcanvas de creación/detalle/edición
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - HTMX (cargado globalmente)
 */
(function (w, d) {
  'use strict';

  const MOD = '[periodos.page]';
  const TABLE_SELECTOR = '#grid-periodos';
  const SEARCH_SELECTOR = '#search-periodo';
  const FILTER_ESTADO_SELECTOR = '#filter-estado-periodo';
  const API_URL = '/api/v1/contabilidad/periodos-contables/';
  const TAB_ID = '#subtab-periodos';
  const ERROR_CONTAINER_ID = '#error-container-periodos';
  const OFFCANVAS_CONTAINER_ID = '#offcanvas-container-periodo';
  let table = null;
  let tableInitialized = false; // ⚠️ v2.61: Protección contra inicialización múltiple

  // ⚠️ v2.61: Definir columnas usando campos de PERIODO_LIST_FIELDS
  function getColumns() {
    return [
      {
        title: "Periodo",
        field: "periodo",
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
            'CERRADO': '<span class="badge bg-secondary">Cerrado</span>'
          };
          
          return badges[val] || `<span class="badge bg-light text-dark">${val}</span>`;
        }
      },
      {
        title: "Empresa",
        field: "empresa_nombre",
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '---';
        }
      },
      {
        title: "Acciones",
        field: "actions",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const uuid = rowData.uuid || rowData.id;
          if (!uuid) return '-';
          
          return `
            <div class="btn-group btn-group-sm" role="group">
              <button type="button" class="btn btn-outline-primary btn-ver-periodo" data-uuid="${uuid}" title="Ver Detalle">
                <i class="bi bi-eye"></i>
              </button>
              <button type="button" class="btn btn-outline-secondary btn-editar-periodo" data-uuid="${uuid}" title="Editar">
                <i class="bi bi-pencil"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-eliminar-periodo" data-uuid="${uuid}" title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        hozAlign: "center",
        headerSort: false
      }
    ];
  }

    /**
     * Inicializar tabla Tabulator
   * ⚠️ v2.61: Aislamiento Gradual - Sin try/catch, solo verifica disponibilidad
   * ⚠️ v2.61: Protección contra inicialización múltiple
   */
  function initTable() {
    // ⚠️ v2.61: Evitar inicialización múltiple
    if (tableInitialized && table) {
      console.log(`${MOD} Tabla ya inicializada, omitiendo...`);
      return;
    }
    
    if (!w.TabulatorFactory) {
      console.warn(`${MOD} TabulatorFactory no está disponible. Reintentando...`);
      setTimeout(initTable, 500);
      return;
    }

    const container = d.querySelector(TABLE_SELECTOR);
    if (!container) {
      console.warn(`${MOD} Contenedor ${TABLE_SELECTOR} no encontrado`);
        return;
      }

    // ⚠️ v2.61: Verificar que el contenedor esté visible (no está oculto con display:none)
    if (container.offsetParent === null) {
      console.info(`${MOD} Contenedor existe pero no está visible, omitiendo inicialización`);
      return;
    }

    // ⚠️ v2.61: Usar TabulatorFactory para crear tabla
    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, getColumns(), {
          paginationSize: 10,
      searchInputSelector: SEARCH_SELECTOR,
      ajaxParams: function(params) {
        // ⚠️ v2.61: Asegurar que params existe antes de asignar propiedades
        if (!params) {
          params = {};
        }
        
        // Filtrar por estado si está seleccionado
        const filterEstado = d.querySelector(FILTER_ESTADO_SELECTOR);
        const estado = filterEstado ? filterEstado.value : '';
        
        if (estado) {
          params.estado = estado;
        }
        
        return params;
      },
      // ⚠️ v2.61: Transformar respuesta DRF a formato Tabulator
      ajaxResponse: function(url, params, response) {
        console.log(`${MOD} Respuesta de API recibida:`, {
          url: url,
          params: params,
          count: response?.count,
          results: response?.results?.length
        });
        
        // Validar estructura de respuesta DRF
        if (!response || typeof response !== 'object') {
          console.error(`${MOD} Respuesta de API inválida:`, response);
          return { data: [], last_page: 1 };
        }

        // DRF retorna {count, next, previous, results: [...]}
        if (response.results && Array.isArray(response.results)) {
          const pageSize = params?.size || 10;
          const count = parseInt(response.count) || 0;
          const lastPage = count > 0 && pageSize > 0 ? Math.ceil(count / pageSize) : 1;
          
          console.log(`${MOD} Transformando respuesta DRF:`, {
            count: count,
            resultsCount: response.results.length,
            lastPage: lastPage
          });
          
          return {
            data: response.results,
            last_page: lastPage
          };
      }

        // Fallback: si es un array directo
        if (Array.isArray(response)) {
          return {
            data: response,
            last_page: 1
          };
      }

        console.warn(`${MOD} Formato de respuesta inesperado:`, response);
        return { data: [], last_page: 1 };
      }
    });

    if (!table) {
      console.error(`${MOD} No se pudo crear la tabla Tabulator`);
      return;
      }

    // ⚠️ v2.61: Marcar como inicializada
    tableInitialized = true;

    // ⚠️ v2.61: Event delegation para acciones de tabla
    container.addEventListener('click', function(evt) {
      const btnVer = evt.target.closest('.btn-ver-periodo');
      if (btnVer) {
        const uuid = btnVer.dataset.uuid;
        if (uuid) {
          handleVer(uuid);
        }
        return;
      }
      
      const btnEditar = evt.target.closest('.btn-editar-periodo');
      if (btnEditar) {
        const uuid = btnEditar.dataset.uuid;
        if (uuid) {
          handleEditar(uuid);
        }
        return;
      }
      
      const btnEliminar = evt.target.closest('.btn-eliminar-periodo');
      if (btnEliminar) {
        const uuid = btnEliminar.dataset.uuid;
        if (uuid) {
          handleEliminar(uuid);
        }
        return;
      }
    });
    
    // ⚠️ v2.61: Filtros de Estado
    setupFilters();

    console.log(`${MOD} Tabla Tabulator inicializada`);
  }

  /**
   * Refrescar tabla
   * ⚠️ v2.61: Aislamiento Gradual - Sin try/catch
   */
  function refreshTable() {
    if (table && typeof table.replaceData === 'function') {
      table.replaceData();
      console.log(`${MOD} Tabla refrescada`);
    } else {
      console.warn(`${MOD} Tabla no disponible para refrescar`);
    }
  }
  
  /**
   * ⚠️ v2.61: Configurar filtros de Estado
   */
  function setupFilters() {
    const filterEstado = d.querySelector(FILTER_ESTADO_SELECTOR);
    const btnRefrescar = d.querySelector('#btn-refrescar-periodos');
    
    if (filterEstado) {
      filterEstado.addEventListener('change', function() {
        aplicarFiltros();
      });
    }
    
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', function() {
        refreshTable();
      });
    }
  }
  
  /**
   * ⚠️ v2.61: Aplicar filtros de Estado
   */
  function aplicarFiltros() {
    if (!table) return;
    
    const filterEstado = d.querySelector(FILTER_ESTADO_SELECTOR);
    const estado = filterEstado ? filterEstado.value : '';
    
    // Construir filtro
    let filtro = [];
    
    if (estado) {
      filtro.push({field: 'estado', type: '=', value: estado});
    }
    
    // Aplicar filtros a la tabla
    if (filtro.length > 0) {
      table.setFilter(filtro);
    } else {
      table.clearFilter();
    }
  }

  /**
   * Manejar visualización de detalle de período
   */
  function handleVer(uuid) {
    console.log(`${MOD} Viendo detalle de período:`, uuid);
      
    const container = d.querySelector(OFFCANVAS_CONTAINER_ID);
    if (!container) {
      console.error(`${MOD} Contenedor ${OFFCANVAS_CONTAINER_ID} no encontrado`);
      return;
    }

    // HTMX cargará el offcanvas de detalle
    htmx.ajax('GET', `${API_URL}${uuid}/render-offcanvas/detalle/`, {
      target: container,
      swap: 'innerHTML',
      onAfterSwap: () => {
        const offcanvasEl = d.querySelector('#offcanvas-periodo-detalle');
        if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
          w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
        }
      }
    });
  }

    /**
     * Manejar edición de período
     */
  function handleEditar(uuid) {
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
  }

    /**
     * Manejar eliminación de período
     */
  function handleEliminar(uuid) {
      console.log(`${MOD} Eliminando período:`, uuid);
      
      if (!confirm('¿Está seguro de que desea eliminar este período?')) {
        return;
      }

    const csrftoken = d.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                      d.cookie.match(/csrftoken=([^;]+)/)?.[1];
    
    fetch(`${API_URL}${uuid}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': csrftoken
      },
      credentials: 'same-origin'
    })
    .then(response => {
      if (response.ok || response.status === 204) {
            console.log(`${MOD} Período eliminado correctamente`);
        refreshTable();
            
            // Mostrar feedback
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
              w.SintelFeedback.success('Período eliminado correctamente');
            }
          } else {
        throw new Error(`HTTP ${response.status}`);
      }
    })
    .catch(error => {
      console.error(`${MOD} Error al eliminar período:`, error);
            
            // Mostrar error
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al eliminar el período' } }, MOD);
        }
      });
  }

    /**
   * Inicializar módulo cuando el tab esté visible
   * ⚠️ v2.61: Usa DOMUtils.onVisibleOnce para lazy loading
   */
  function init() {
    if (!w.DOMUtils || !w.DOMUtils.onVisibleOnce) {
      console.warn(`${MOD} DOMUtils.onVisibleOnce no disponible. Inicializando directamente...`);
      initTable();
      return;
    }

    // ⚠️ v2.61: Lazy loading - Solo inicializar cuando el tab esté visible
    w.DOMUtils.onVisibleOnce(TAB_ID, function() {
      console.log(`${MOD} Tab visible, inicializando tabla...`);
      initTable();
    });
  }

  // ⚠️ CRÍTICO v2.61: Exponer PeriodosPage INMEDIATAMENTE
  if (!w.PeriodosPage) {
    w.PeriodosPage = {};
    }

  // Exponer funciones públicas
  w.PeriodosPage.refreshGrid = refreshTable;
  w.PeriodosPage.init = init;

  // Auto-inicializar cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ⚠️ v2.61: Listener adicional para evento Bootstrap tab (cuando se muestra el tab)
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-bs-target') === TAB_ID || e.target.id === 'contabilidad-periodos-tab')) {
      console.log(`${MOD} Tab de periodos mostrado, verificando inicialización...`);
      const container = d.querySelector(TABLE_SELECTOR);
      if (container && !tableInitialized) {
        console.log(`${MOD} Tabla no inicializada, inicializando desde evento shown.bs.tab...`);
        initTable();
      } else if (table && typeof table.replaceData === 'function') {
        // Si la tabla ya existe, refrescar datos
        console.log(`${MOD} Tabla ya inicializada, refrescando datos...`);
        table.replaceData();
    }
    }
  });

  console.log(`${MOD} Módulo cargado`);

})(window, document);
