/**
 * cuentas.page.js - Módulo Contabilidad Cuentas v2.60 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.60: Migración completa de Modales a Offcanvas + HTMX
 * - Eliminado todo código legacy de modales Bootstrap
 * - Uso exclusivo de HTMX para cargar offcanvas
 * - Manejo de errores con error_injector.js/UIManager
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - HTMX (cargado globalmente)
 */
(function (w, d) {
  'use strict';

  const MOD = 'cuentas';
  // ⚠️ v2.61: Selectores corregidos para coincidir con list_cuentas.html (workspace)
  const TABLE_SELECTOR = '#grid-cuentas';  // Plural - usado en workspace.html
  const SEARCH_SELECTOR = '#search-cuenta';  // Singular - correcto
  // ⚠️ v2.61: ROUTES_MODULE eliminado - Routes endpoint no existe, usar URL directa
  const TAB_ID = '#subtab-cuentas';
  const ERROR_CONTAINER_ID = '#error-container-cuentas';  // Plural - usado en list_cuentas.html
  const OFFCANVAS_CONTAINER_ID = '#offcanvas-container-cuentas';  // Plural - usado en list_cuentas.html
  
  // Estado del módulo
  let state = {
    initialized: false,
    listenersAttached: false,
    table: null,
    urls: { collection: null }
  };

  /**
   * Descubrir URL de colección usando URL directa conocida
   * ⚠️ v2.61: Routes endpoint no existe (/api/v1/core/routes/ retorna 404)
   * Usar URL directa conocida para evitar warnings innecesarios
   */
  async function discoverCollectionUrl() {
    if (state.urls.collection) {
      return state.urls.collection;
    }
    
    // ⚠️ v2.61: URL conocida directamente (Routes endpoint no implementado)
    const directUrl = '/api/v1/contabilidad/cuentas-contables/';
    state.urls.collection = window.API_HELPERS?.withTrailingSlash(directUrl) || directUrl;
    console.info(`[${MOD}.page] Usando URL de colección:`, state.urls.collection);
    return state.urls.collection;
  }

  /**
   * Construir URL de detalle para una cuenta
   * @param {string|number} id - ID de la cuenta
   * @returns {string} URL de detalle
   */
  async function cuentaDetailUrl(id) {
    if (!state.urls.collection) {
      await discoverCollectionUrl();
    }
    if (!state.urls.collection) {
      console.warn(`[${MOD}.page] state.urls.collection no descubierta, usando fallback`);
      const fallbackUrl = '/api/v1/contabilidad/cuentas-contables/';
      return window.API_HELPERS?.buildDetailUrl(fallbackUrl, id) || `${fallbackUrl}${id}/`;
    }
    return window.API_HELPERS?.buildDetailUrl(state.urls.collection, id) || `${state.urls.collection}${id}/`;
  }

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

  // ⚠️ v2.60: Definir columnas usando campos del serializer
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
        field: "acciones",  // ⚠️ v2.61: Agregar field para poder identificarlo
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          // ⚠️ v2.61: Validar y normalizar ID - puede venir como número o string
          let cuentaId = rowData.id;
          
          // Validar que el ID exista y sea válido
          if (cuentaId === null || cuentaId === undefined || cuentaId === '') {
            console.warn(`[${MOD}] ⚠️ Fila sin ID válido:`, rowData);
            return '-';
          }
          
          // Normalizar ID a string para asegurar consistencia
          cuentaId = String(cuentaId).trim();
          if (!cuentaId || cuentaId === 'undefined' || cuentaId === 'null') {
            console.warn(`[${MOD}] ⚠️ ID normalizado inválido:`, { original: rowData.id, normalized: cuentaId });
            return '-';
          }
          
          // ⚠️ v2.61: Replicar lógica de cotizaciones.page.js - Usar data-action
          // ⚠️ Editar deshabilitado: La función de editar no es requerida según requerimientos
          return `
            <div class="btn-group">
              <button type="button" class="btn btn-sm btn-secondary" data-action="ver" data-id="${cuentaId}" title="Ver detalle">
                <i class="bi bi-eye"></i>
              </button>
              <button type="button" class="btn btn-sm btn-danger" data-action="eliminar" data-id="${cuentaId}" title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        headerSort: false,
        headerFilter: false,  // ⚠️ v2.61: Columna de acciones no necesita filtro
        hozAlign: "right",
        width: 150
      }
    ];
  }

  // ⚠️ v2.61: Inicializar Tabulator usando TabulatorFactory - Validado y mejorado
  async function initTabulator() {
    if (!w.TabulatorFactory) {
      console.error(`[${MOD}] TabulatorFactory no está disponible`);
      return null;
    }

    const tableEl = d.querySelector(TABLE_SELECTOR);
    if (!tableEl) {
      console.warn(`[${MOD}] Contenedor de tabla no encontrado:`, TABLE_SELECTOR, '- Esto es normal si el módulo no está visible');
      return null;
    }

    // ⚠️ v2.61: Verificar que el contenedor esté visible (no está oculto con display:none)
    if (tableEl.offsetParent === null) {
      console.info(`[${MOD}] Contenedor de tabla existe pero no está visible, omitiendo inicialización`);
      return null;
    }

    // ⚠️ v2.61: Descubrir URL antes de crear tabla y validar
    let apiUrl;
    try {
      apiUrl = await discoverCollectionUrl();
      if (!apiUrl || typeof apiUrl !== 'string') {
        console.error(`[${MOD}] URL de API no válida:`, apiUrl);
        return null;
      }
      console.info(`[${MOD}] Inicializando tabla con URL:`, apiUrl);
    } catch (err) {
      console.error(`[${MOD}] Error descubriendo URL de colección:`, err);
      return null;
    }

    // ⚠️ v2.61: Validar que las columnas estén definidas
    const columns = getColumns();
    if (!columns || !Array.isArray(columns) || columns.length === 0) {
      console.error(`[${MOD}] Columnas no definidas o vacías`);
      return null;
    }
    console.info(`[${MOD}] Columnas definidas:`, columns.length);

    // ⚠️ v2.61: Destruir tabla previa si existe (anti-zombies)
    if (state.table) {
      try {
        state.table.destroy();
        console.info(`[${MOD}] Tabla previa destruida`);
      } catch (err) {
        console.warn(`[${MOD}] Error al destruir tabla previa:`, err);
      }
      state.table = null;
    }

    // ⚠️ v2.61: Usar TabulatorFactory v2.40 con validación
    try {
      state.table = w.TabulatorFactory.create(
        TABLE_SELECTOR,
        apiUrl,
        columns,
        {
          searchInputSelector: SEARCH_SELECTOR,
          paginationSize: 10,
          // ⚠️ v2.61: Callback para validar respuesta de la API
          ajaxResponse: function(url, params, response) {
            console.log(`[${MOD}] Respuesta de API recibida:`, {
              url: url,
              params: params,
              count: response?.count,
              results: response?.results?.length
            });
            
            // Validar estructura de respuesta DRF
            if (!response || typeof response !== 'object') {
              console.error(`[${MOD}] Respuesta de API inválida:`, response);
              return { data: [], last_page: 1 };
            }

            // DRF retorna {count, next, previous, results: [...]}
            if (response.results && Array.isArray(response.results)) {
              return {
                data: response.results,
                last_page: Math.ceil((response.count || 0) / (params.size || 10))
              };
            }

            // Fallback: si es un array directo
            if (Array.isArray(response)) {
              return {
                data: response,
                last_page: 1
              };
            }

            console.warn(`[${MOD}] Formato de respuesta inesperado:`, response);
            return { data: [], last_page: 1 };
          }
        }
      );

      if (!state.table) {
        console.error(`[${MOD}] No se pudo crear la tabla Tabulator`);
        return null;
      }

      console.info(`[${MOD}] Tabla Tabulator inicializada correctamente`);
      
      // ⚠️ v2.61: Agregar listener para errores de carga
      state.table.on('dataLoadError', function(error) {
        console.error(`[${MOD}] Error al cargar datos en Tabulator:`, error);
        const errorContainer = d.querySelector(ERROR_CONTAINER_ID);
        if (errorContainer) {
          errorContainer.classList.remove('d-none');
          errorContainer.innerHTML = `
            <div class="alert alert-danger" role="alert">
              <i class="bi bi-exclamation-triangle me-2"></i>
              <strong>Error al cargar datos:</strong> ${error.message || 'Error desconocido'}
            </div>
          `;
        }
      });

      // ⚠️ v2.61: Agregar listener para datos cargados exitosamente
      state.table.on('dataLoaded', function(data) {
        console.info(`[${MOD}] Datos cargados exitosamente:`, data.length, 'registros');
        // Ocultar mensajes de error si los datos se cargaron correctamente
        const errorContainer = d.querySelector(ERROR_CONTAINER_ID);
        if (errorContainer) {
          errorContainer.classList.add('d-none');
        }
        
        // ⚠️ v2.61: Procesar HTMX después de cargar datos (patrón cotizaciones.page.js)
        if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
          const container = d.querySelector(TABLE_SELECTOR);
          if (container) {
            htmx.process(container);
            console.info(`[${MOD}] HTMX procesado después de cargar datos`);
          }
        }
      });

      // ⚠️ v2.61: Procesar HTMX después de procesar datos (patrón cotizaciones.page.js)
      state.table.on('dataProcessed', function() {
        if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
          const container = d.querySelector(TABLE_SELECTOR);
          if (container) {
            htmx.process(container);
            console.info(`[${MOD}] HTMX procesado después de procesar datos`);
          }
        }
      });

      // ⚠️ v2.61: Event delegation para botones de acciones (patrón cotizaciones.page.js)
      // ⚠️ CRÍTICO: Registrar listener INMEDIATAMENTE después de crear la tabla
      const container = d.querySelector(TABLE_SELECTOR);
      if (container) {
        // ⚠️ v2.61: Registrar listener directamente en el contenedor (event delegation)
        // No clonar el contenedor porque destruiría la tabla de Tabulator
        container.addEventListener('click', function(e) {
          const btn = e.target.closest('button[data-action]');
          if (btn && !btn.disabled) {
            const action = btn.getAttribute('data-action');
            let id = btn.getAttribute('data-id');
            
            // ⚠️ v2.61: Normalizar ID - puede venir como string vacío o null
            if (id) {
              id = String(id).trim();
            }
            
            console.log(`[${MOD}] 🔍 DEBUG: Click detectado en botón:`, {
              action: action,
              id: id,
              idType: typeof id,
              button: btn.className,
              target: e.target.tagName,
              buttonHTML: btn.outerHTML.substring(0, 150),
              dataset: btn.dataset
            });
            
            if (id && id !== 'undefined' && id !== 'null' && id !== '') {
              e.preventDefault();
              e.stopPropagation();
              handleActionClick(action, id, btn);
            } else {
              console.error(`[${MOD}] ❌ Botón ${action} sin ID válido:`, {
                id: id,
                idType: typeof id,
                buttonHTML: btn.outerHTML
              });
            }
          }
        });
        
        console.info(`[${MOD}] ✅ Event listener registrado en contenedor (patrón cotizaciones)`);
      } else {
        console.error(`[${MOD}] ⚠️ Contenedor no encontrado para registrar listener`);
      }

      return state.table;
    } catch (err) {
      console.error(`[${MOD}] Error al crear tabla Tabulator:`, err);
      const errorContainer = d.querySelector(ERROR_CONTAINER_ID);
      if (errorContainer) {
        errorContainer.classList.remove('d-none');
        errorContainer.innerHTML = `
          <div class="alert alert-danger" role="alert">
            <i class="bi bi-exclamation-triangle me-2"></i>
            <strong>Error al inicializar tabla:</strong> ${err.message || 'Error desconocido'}
          </div>
        `;
      }
      return null;
    }
  }

  // ⚠️ v2.61: Manejar apertura de offcanvas después de carga HTMX - Mejorado
  function handleHTMXSwap(event) {
    // Detectar cuando HTMX carga un offcanvas
    const target = event.detail?.target || event.target;
    
    if (!target) return;

    // ⚠️ v2.61: SAFEGUARD - Solo procesar swaps relacionados con el contenedor de cuentas
    // Ignorar swaps de otros módulos (cotizaciones, empleados, etc.)
    const targetId = target.id || '';
    const expectedContainerId = OFFCANVAS_CONTAINER_ID.replace('#', '');
    
    // Si el target NO es el contenedor de cuentas, ignorar este swap
    if (targetId !== expectedContainerId && !targetId.includes('offcanvas-cuenta') && !targetId.includes('cuentas')) {
      // Este swap no es para cuentas, ignorar silenciosamente
      return;
    }

    // Buscar offcanvas dentro del contenedor objetivo
    let offcanvasEl = null;
    
    // Si el target es el contenedor, buscar el offcanvas dentro
    if (targetId === expectedContainerId) {
      offcanvasEl = target.querySelector('[id^="offcanvas-cuenta"]');
    } 
    // Si el target es el offcanvas mismo
    else if (targetId && targetId.includes('offcanvas-cuenta')) {
      offcanvasEl = target;
    }
    // Buscar en el contenedor
    else {
      const container = d.querySelector(OFFCANVAS_CONTAINER_ID);
      if (container) {
        offcanvasEl = container.querySelector('[id^="offcanvas-cuenta"]');
      }
    }

    if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
      // Abrir offcanvas después de que HTMX inyecta el contenido
      requestAnimationFrame(() => {
        try {
          const offcanvas = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          offcanvas.show();
          console.info(`[${MOD}] Offcanvas abierto:`, offcanvasEl.id);
        } catch (err) {
          console.error(`[${MOD}] Error al abrir offcanvas:`, err);
        }
      });
    } else {
      // ⚠️ v2.61: Solo mostrar warning si realmente es un swap de cuentas
      // Si no es un swap de cuentas, ya se retornó antes, así que este warning es válido
      if (targetId === expectedContainerId || targetId.includes('cuentas')) {
        console.warn(`[${MOD}] Offcanvas no encontrado en el contenedor`);
      }
    }
  }

  // ⚠️ v2.61: Handlers para acciones de botones - Replicado de cotizaciones.page.js
  async function handleVerCuenta(id) {
    console.info(`[${MOD}] Ver detalle de cuenta ID:`, id);

    try {
      // Cargar offcanvas de detalle vía HTMX
      if (typeof htmx !== 'undefined') {
        const detailUrl = await cuentaDetailUrl(id);
        const url = `${detailUrl}render-offcanvas/detalle/`;
        
        console.info(`[${MOD}] Cargando offcanvas detalle desde:`, url);
        
        const container = d.querySelector(OFFCANVAS_CONTAINER_ID);
        if (!container) {
          throw new Error('Contenedor de offcanvas no encontrado');
        }
        
        await htmx.ajax('GET', url, {
          target: OFFCANVAS_CONTAINER_ID,
          swap: 'innerHTML'
        });

        // ⚠️ v2.61: Buscar offcanvas después de que HTMX lo carga (patrón cotizaciones)
        // Esperar un momento para que el DOM se actualice
        setTimeout(() => {
          // Buscar el offcanvas dentro del contenedor o el contenedor mismo si es el offcanvas
          let offcanvasEl = container.querySelector('.offcanvas[id^="offcanvas-cuenta"]');
          if (!offcanvasEl) {
            // Si el contenedor mismo es el offcanvas
            if (container.classList.contains('offcanvas')) {
              offcanvasEl = container;
            } else {
              // Buscar cualquier elemento con id que empiece con offcanvas-cuenta
              offcanvasEl = container.querySelector('[id^="offcanvas-cuenta"]');
            }
          }
          
          if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
            try {
              const offcanvas = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
              offcanvas.show();
              console.info(`[${MOD}] ✅ Offcanvas detalle abierto:`, offcanvasEl.id);
            } catch (err) {
              console.error(`[${MOD}] Error al abrir offcanvas:`, err);
            }
          } else {
            console.warn(`[${MOD}] ⚠️ Offcanvas no encontrado en el contenedor. Contenedor HTML:`, container.innerHTML.substring(0, 200));
          }
        }, 100);
      } else {
        throw new Error('HTMX no está disponible');
      }
    } catch (err) {
      console.error(`[${MOD}] Error al cargar detalle de cuenta:`, err);
      if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al cargar el detalle de la cuenta');
      } else {
        alert('Error al cargar el detalle de la cuenta');
      }
    }
  }

  async function handleEditarCuenta(id) {
    console.info(`[${MOD}] Editar cuenta ID:`, id);

    try {
      // Cargar offcanvas de edición vía HTMX
      if (typeof htmx !== 'undefined') {
        const detailUrl = await cuentaDetailUrl(id);
        const url = `${detailUrl}render-offcanvas/editar/`;
        
        console.info(`[${MOD}] Cargando offcanvas editar desde:`, url);
        
        const container = d.querySelector(OFFCANVAS_CONTAINER_ID);
        if (!container) {
          throw new Error('Contenedor de offcanvas no encontrado');
        }
        
        await htmx.ajax('GET', url, {
          target: OFFCANVAS_CONTAINER_ID,
          swap: 'innerHTML'
        });

        // ⚠️ v2.61: Buscar offcanvas después de que HTMX lo carga (patrón cotizaciones)
        // Esperar un momento para que el DOM se actualice
        setTimeout(() => {
          // Buscar el offcanvas dentro del contenedor o el contenedor mismo si es el offcanvas
          let offcanvasEl = container.querySelector('.offcanvas[id^="offcanvas-cuenta"]');
          if (!offcanvasEl) {
            // Si el contenedor mismo es el offcanvas
            if (container.classList.contains('offcanvas')) {
              offcanvasEl = container;
            } else {
              // Buscar cualquier elemento con id que empiece con offcanvas-cuenta
              offcanvasEl = container.querySelector('[id^="offcanvas-cuenta"]');
            }
          }
          
          if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
            try {
              const offcanvas = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
              offcanvas.show();
              console.info(`[${MOD}] ✅ Offcanvas editar abierto:`, offcanvasEl.id);
            } catch (err) {
              console.error(`[${MOD}] Error al abrir offcanvas:`, err);
            }
          } else {
            console.warn(`[${MOD}] ⚠️ Offcanvas no encontrado en el contenedor. Contenedor HTML:`, container.innerHTML.substring(0, 200));
          }
        }, 100);
      } else {
        throw new Error('HTMX no está disponible');
      }
    } catch (err) {
      console.error(`[${MOD}] Error al cargar formulario de edición:`, err);
      if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al cargar el formulario de edición');
      } else {
        alert('Error al cargar el formulario de edición');
      }
    }
  }

  async function handleEliminarCuentaClick(id) {
    // Confirmación
    const confirmacion = confirm('¿Está seguro de que desea eliminar esta cuenta contable?');
    if (!confirmacion) {
      console.info(`[${MOD}] Eliminación cancelada por el usuario`);
      return;
    }

    console.info(`[${MOD}] Eliminar cuenta ID:`, id);

    try {
      await handleEliminarCuenta(id);
    } catch (err) {
      console.error(`[${MOD}] Error al eliminar cuenta:`, err);
    }
  }

  // ⚠️ v2.61: DEPRECATED - Los listeners ahora se registran directamente en initTabulator()
  // Esta función se mantiene por compatibilidad pero ya no se usa
  function attachTableListeners() {
    console.info(`[${MOD}] ⚠️ attachTableListeners() está deprecated. Los listeners se registran en initTabulator().`);
    // Los listeners ya se registran en initTabulator() después de crear la tabla
  }

  // ⚠️ v2.61: Manejar clicks en botones de acciones - Replicado de cotizaciones.page.js
  function handleActionClick(action, id, btn) {
    console.info(`[${MOD}] ✅ Acción solicitada: ${action} - ID:`, id);
    
    // Feedback visual
    if (btn) {
      const originalHTML = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
      
      // Restaurar después de un tiempo si hay error
      setTimeout(() => {
        if (btn.disabled) {
          btn.disabled = false;
          btn.innerHTML = originalHTML;
        }
      }, 5000);
    }
    
    try {
      switch (action) {
        case 'ver':
          handleVerCuenta(id).finally(() => {
            if (btn) {
              btn.disabled = false;
              btn.innerHTML = btn.innerHTML.includes('spinner') ? btn.innerHTML : originalHTML;
            }
          });
          break;
        case 'editar':
          handleEditarCuenta(id).finally(() => {
            if (btn) {
              btn.disabled = false;
              btn.innerHTML = btn.innerHTML.includes('spinner') ? btn.innerHTML : originalHTML;
            }
          });
          break;
        case 'eliminar':
          handleEliminarCuentaClick(id).finally(() => {
            if (btn) {
              btn.disabled = false;
              btn.innerHTML = btn.innerHTML.includes('spinner') ? btn.innerHTML : originalHTML;
            }
          });
          break;
        default:
          console.warn(`[${MOD}] Acción desconocida:`, action);
          if (btn) {
            btn.disabled = false;
            btn.innerHTML = btn.innerHTML.includes('spinner') ? btn.innerHTML : originalHTML;
          }
          break;
      }
    } catch (err) {
      console.error(`[${MOD}] Error en acción ${action}:`, err);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = btn.innerHTML.includes('spinner') ? btn.innerHTML : originalHTML;
      }
      if (w.SintelFeedback) {
        w.SintelFeedback.error(`Error al ejecutar acción ${action}: ${err.message || 'Error desconocido'}`);
      }
    }
  }

  // ⚠️ v2.60: Manejar guardado desde offcanvas (crear/editar)
  function attachOffcanvasListeners() {
    // Guardar crear
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-guardar-cuenta-crear');
      if (btn) {
        ev.preventDefault();
        handleGuardarCuenta('create');
      }
    });

    // Guardar editar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-guardar-cuenta-editar');
      if (btn) {
        ev.preventDefault();
        handleGuardarCuenta('update');
      }
    });
  }

  // ⚠️ v2.61: Guardar cuenta (crear o actualizar) - Mejorado con validaciones y feedback
  async function handleGuardarCuenta(mode) {
    const formId = mode === 'create' ? '#form-cuenta-crear' : '#form-cuenta-editar';
    const form = d.querySelector(formId);
    if (!form) {
      console.error(MOD, 'Formulario no encontrado:', formId);
      if (w.SintelFeedback) {
        w.SintelFeedback.error('Formulario no encontrado. Por favor, recargue la página.');
      }
      return;
    }

    // ⚠️ v2.61: Validar formulario HTML5 antes de enviar
    if (!form.checkValidity()) {
      form.reportValidity();
      // Resaltar campos inválidos
      const invalidFields = form.querySelectorAll(':invalid');
      invalidFields.forEach(field => {
        field.classList.add('is-invalid');
        field.addEventListener('input', function() {
          if (this.checkValidity()) {
            this.classList.remove('is-invalid');
          }
        }, { once: true });
      });
      return;
    }

    // ⚠️ v2.61: Obtener botón de guardar y mostrar estado de loading
    const btnId = mode === 'create' ? '#btn-guardar-cuenta-crear' : '#btn-guardar-cuenta-editar';
    const btnGuardar = d.querySelector(btnId);
    const btnOriginalText = btnGuardar ? btnGuardar.innerHTML : '';
    const btnOriginalDisabled = btnGuardar ? btnGuardar.disabled : false;

    // Mostrar estado de loading
    if (btnGuardar) {
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
    }

    // ⚠️ v2.61: Ocultar mensajes de error previos
    const errorContainer = d.querySelector(ERROR_CONTAINER_ID);
    if (errorContainer) {
      errorContainer.classList.add('d-none');
      errorContainer.innerHTML = '';
    }

    // ⚠️ v2.61: Recolectar datos del formulario con validaciones
    const formData = new FormData(form);
    const payload = {};
    
    // Campos requeridos
    const codigo = formData.get('codigo')?.trim();
    const nombre = formData.get('nombre')?.trim();
    const tipo = formData.get('tipo')?.trim();

    // Validar campos requeridos
    if (!codigo) {
      if (btnGuardar) {
        btnGuardar.disabled = btnOriginalDisabled;
        btnGuardar.innerHTML = btnOriginalText;
      }
      const codigoInput = form.querySelector('#input-codigo');
      if (codigoInput) {
        codigoInput.classList.add('is-invalid');
        codigoInput.focus();
      }
      if (w.SintelFeedback) {
        w.SintelFeedback.error('El campo "Código" es requerido.');
      }
      return;
    }

    if (!nombre) {
      if (btnGuardar) {
        btnGuardar.disabled = btnOriginalDisabled;
        btnGuardar.innerHTML = btnOriginalText;
      }
      const nombreInput = form.querySelector('#input-nombre');
      if (nombreInput) {
        nombreInput.classList.add('is-invalid');
        nombreInput.focus();
      }
      if (w.SintelFeedback) {
        w.SintelFeedback.error('El campo "Nombre" es requerido.');
      }
      return;
    }

    if (!tipo) {
      if (btnGuardar) {
        btnGuardar.disabled = btnOriginalDisabled;
        btnGuardar.innerHTML = btnOriginalText;
      }
      const tipoSelect = form.querySelector('#select-tipo');
      if (tipoSelect) {
        tipoSelect.classList.add('is-invalid');
        tipoSelect.focus();
      }
      if (w.SintelFeedback) {
        w.SintelFeedback.error('El campo "Tipo" es requerido.');
      }
      return;
    }

    // Construir payload
    for (const [key, value] of formData.entries()) {
      if (key === 'activa') {
        payload[key] = value === 'true';
      } else if (key === 'cuenta_padre') {
        payload[key] = value ? parseInt(value) : null;
      } else if (key === 'id' && mode === 'update') {
        payload[key] = value ? parseInt(value) : null;
      } else if (value && value.trim()) {
        payload[key] = value.trim();
      }
    }

    // ⚠️ v2.61: Asegurar que campos requeridos estén en el payload
    payload.codigo = codigo;
    payload.nombre = nombre;
    payload.tipo = tipo;

    // Obtener URL y método
    const collectionUrl = await discoverCollectionUrl();
    const url = mode === 'create' ? collectionUrl : await cuentaDetailUrl(formData.get('id'));
    const method = mode === 'create' ? 'POST' : 'PATCH';

    try {
      // ⚠️ v2.61: Asegurar que url sea una cadena
      const urlString = typeof url === 'string' ? url : String(url || '');
      if (!urlString) {
        throw new Error('URL no válida para la petición');
      }
      
      console.log(`[${MOD}] Enviando ${method} a ${urlString}:`, payload);
      
      // ⚠️ v2.61: w.http() espera (method, url, body) - NO el formato de fetch()
      const response = await w.http(method, urlString, payload);

      // ⚠️ v2.61: Restaurar estado del botón ANTES de procesar respuesta
      if (btnGuardar) {
        btnGuardar.disabled = btnOriginalDisabled;
        btnGuardar.innerHTML = btnOriginalText;
      }

      if (!response.ok) {
        // ⚠️ v2.61: Obtener detalles del error del response
        let errorData = {};
        try {
          errorData = await response.json();
        } catch (e) {
          console.warn(`[${MOD}] No se pudo parsear respuesta de error:`, e);
        }

        // ⚠️ v2.61: Mostrar errores de validación en los campos correspondientes
        if (errorData && typeof errorData === 'object') {
          Object.keys(errorData).forEach(fieldName => {
            const field = form.querySelector(`#input-${fieldName}`) || form.querySelector(`#select-${fieldName}`);
            if (field) {
              field.classList.add('is-invalid');
              const errorMsg = Array.isArray(errorData[fieldName]) 
                ? errorData[fieldName].join(', ') 
                : errorData[fieldName];
              // Agregar mensaje de error debajo del campo
              let feedback = field.parentElement.querySelector('.invalid-feedback');
              if (!feedback) {
                feedback = d.createElement('div');
                feedback.className = 'invalid-feedback';
                field.parentElement.appendChild(feedback);
              }
              feedback.textContent = errorMsg;
            }
          });
        }

        // ⚠️ v2.61: Usar UIManager para manejo de errores con firma correcta
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(response, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
        } else {
          const errorMsg = errorData.detail || errorData.message || `Error ${response.status}: ${response.statusText}`;
          if (w.SintelFeedback) {
            w.SintelFeedback.error(errorMsg);
          } else {
            alert(errorMsg);
          }
        }
        return;
      }

      // ⚠️ v2.61: Éxito - Limpiar formulario y cerrar offcanvas
      form.reset();
      // Remover clases de validación
      form.querySelectorAll('.is-invalid').forEach(field => {
        field.classList.remove('is-invalid');
      });
      form.querySelectorAll('.invalid-feedback').forEach(feedback => {
        feedback.remove();
      });

      // Cerrar offcanvas
      const offcanvasId = mode === 'create' ? '#offcanvas-cuenta-crear' : '#offcanvas-cuenta-editar';
      const offcanvasEl = d.querySelector(offcanvasId);
      if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
        const offcanvas = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (offcanvas) {
          offcanvas.hide();
        }
      }

      // ⚠️ v2.61: Recargar tabla con validación - Solo si el contenedor está disponible y visible
      const tableContainer = d.querySelector(TABLE_SELECTOR);
      if (tableContainer && tableContainer.offsetParent !== null) {
        // El contenedor existe y está visible
        if (state.table && typeof state.table.replaceData === 'function') {
          try {
            await state.table.replaceData();
            console.info(`[${MOD}] Tabla recargada después de ${mode === 'create' ? 'crear' : 'actualizar'} cuenta`);
          } catch (err) {
            console.error(`[${MOD}] Error al recargar tabla:`, err);
          }
        } else {
          // Tabla no inicializada pero contenedor visible - inicializar
          console.info(`[${MOD}] Tabla no inicializada, inicializando...`);
          state.table = await initTabulator();
          if (state.table) {
            attachTableListeners();
            console.info(`[${MOD}] Tabla inicializada correctamente`);
          }
        }
      } else {
        // Contenedor no visible o no existe - no hacer nada (probablemente estamos en otra vista)
        console.info(`[${MOD}] Contenedor de tabla no visible, omitiendo recarga. La tabla se recargará cuando sea visible.`);
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success(mode === 'create' ? 'Cuenta creada correctamente' : 'Cuenta actualizada correctamente');
      }

      console.log(`[${MOD}] Cuenta ${mode === 'create' ? 'creada' : 'actualizada'} exitosamente`);

    } catch (err) {
      // ⚠️ v2.61: Restaurar estado del botón en caso de error
      if (btnGuardar) {
        btnGuardar.disabled = btnOriginalDisabled;
        btnGuardar.innerHTML = btnOriginalText;
      }

      console.error(`[${MOD}] Error guardando cuenta:`, {
        error: err,
        message: err.message,
        stack: err.stack,
        mode: mode,
        formId: formId,
        payload: payload
      });
      
      // ⚠️ v2.61: Manejo mejorado de errores
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        if (err instanceof Response || (err && typeof err === 'object' && 'ok' in err && 'status' in err)) {
          // Es una respuesta de API
          w.UIManager.handleError(err, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
        } else {
          // Mostrar error en el contenedor de errores
          if (errorContainer) {
            errorContainer.classList.remove('d-none');
            errorContainer.innerHTML = `
              <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Error:</strong> ${err.message || 'Error desconocido al guardar la cuenta'}
              </div>
            `;
          }
        }
      } else {
        // Fallback si UIManager no está disponible
        const errorMsg = err.message || 'Error desconocido al guardar la cuenta';
        if (w.SintelFeedback) {
          w.SintelFeedback.error(errorMsg);
        } else {
          alert(`Error al guardar cuenta: ${errorMsg}`);
        }
      }
    }
  }

  // ⚠️ v2.60: Eliminar cuenta
  async function handleEliminarCuenta(id) {
    // ⚠️ v2.61: Validar y normalizar ID
    if (!id) {
      console.error(`[${MOD}] ID de cuenta requerido`);
      return;
    }
    
    // ⚠️ v2.61: Asegurar que el ID sea un número o string válido
    const normalizedId = String(id).trim();
    if (!normalizedId || normalizedId === 'undefined' || normalizedId === 'null') {
      console.error(`[${MOD}] ID de cuenta inválido:`, id);
      return;
    }
    
    console.log(`[${MOD}] Eliminando cuenta con ID normalizado:`, normalizedId);

    try {
      const deleteUrl = await cuentaDetailUrl(normalizedId);
      // ⚠️ v2.61: Asegurar que url sea una cadena válida
      const urlString = typeof deleteUrl === 'string' ? deleteUrl : String(deleteUrl || '');
      if (!urlString || !urlString.includes(normalizedId)) {
        console.error(`[${MOD}] URL no válida o ID no incluido en URL:`, { url: urlString, id: normalizedId });
        throw new Error(`URL no válida para eliminar la cuenta: ${urlString}`);
      }
      
      console.log(`[${MOD}] DELETE URL construida:`, urlString);
      
      // ⚠️ v2.61: w.http() espera (method, url, body) - NO el formato de fetch()
      const response = await w.http('DELETE', urlString);

      if (!response.ok) {
        // ⚠️ v2.61: Usar UIManager para manejo de errores con firma correcta
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(response, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
        } else {
          // Fallback: mostrar error básico
          const errorMsg = response.data?.detail || response.data?.message || `Error ${response.status}: ${response.statusText}`;
          if (w.SintelFeedback) {
            w.SintelFeedback.error(errorMsg);
          } else {
            alert(errorMsg);
          }
        }
        return;
      }

      // ⚠️ v2.61: Recargar tabla con validación - Solo si el contenedor está disponible y visible
      const tableContainer = d.querySelector(TABLE_SELECTOR);
      if (tableContainer && tableContainer.offsetParent !== null) {
        // El contenedor existe y está visible
        if (state.table && typeof state.table.replaceData === 'function') {
          try {
            await state.table.replaceData();
            console.info(`[${MOD}] Tabla recargada después de eliminar cuenta`);
          } catch (err) {
            console.error(`[${MOD}] Error al recargar tabla:`, err);
          }
        } else {
          // Tabla no inicializada pero contenedor visible - inicializar
          console.info(`[${MOD}] Tabla no inicializada, inicializando...`);
          state.table = await initTabulator();
          if (state.table) {
            attachTableListeners();
            console.info(`[${MOD}] Tabla inicializada correctamente`);
          }
        }
      } else {
        // Contenedor no visible o no existe - no hacer nada (probablemente estamos en otra vista)
        console.info(`[${MOD}] Contenedor de tabla no visible, omitiendo recarga. La tabla se recargará cuando sea visible.`);
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Cuenta eliminada correctamente');
      }
    } catch (err) {
      console.error(MOD, 'Error eliminando cuenta:', err);
      // ⚠️ v2.61: Convertir excepción a formato de respuesta para UIManager
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorResponse = {
          ok: false,
          status: err.status || 500,
          statusText: err.statusText || 'Error',
          data: err.data || { detail: err.message || 'Error inesperado al eliminar la cuenta' }
        };
        w.UIManager.handleError(errorResponse, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else {
        // Fallback: mostrar error básico
        const errorMsg = err.message || 'Error inesperado al eliminar la cuenta';
        if (w.SintelFeedback) {
          w.SintelFeedback.error(errorMsg);
        } else {
          alert(errorMsg);
        }
      }
    }
  }

  // ⚠️ v2.61: Botón refrescar - Mejorado con validación y feedback
  function attachRefreshListener() {
    const btnRefresh = d.querySelector('#btn-refrescar-cuentas');  // Plural - usado en list_cuentas.html
    if (btnRefresh) {
      btnRefresh.addEventListener('click', async () => {
        console.info(`[${MOD}] Refrescando tabla...`);
        
        // Mostrar estado de loading
        const originalText = btnRefresh.innerHTML;
        btnRefresh.disabled = true;
        btnRefresh.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Refrescando...';

        try {
          if (state.table && typeof state.table.replaceData === 'function') {
            await state.table.replaceData();
            console.info(`[${MOD}] Tabla refrescada exitosamente`);
            
            // Feedback visual
            if (w.SintelFeedback) {
              w.SintelFeedback.success('Datos actualizados correctamente');
            }
          } else {
            console.warn(`[${MOD}] Tabla no inicializada, reinicializando...`);
            state.table = await initTabulator();
            if (state.table) {
              attachTableListeners();
              if (w.SintelFeedback) {
                w.SintelFeedback.success('Tabla inicializada correctamente');
              }
            } else {
              throw new Error('No se pudo inicializar la tabla');
            }
          }
        } catch (err) {
          console.error(`[${MOD}] Error al refrescar tabla:`, err);
          if (w.SintelFeedback) {
            w.SintelFeedback.error('Error al refrescar los datos');
          }
        } finally {
          // Restaurar estado del botón
          btnRefresh.disabled = false;
          btnRefresh.innerHTML = originalText;
        }
      });
    } else {
      console.warn(`[${MOD}] Botón refrescar no encontrado: #btn-refrescar-cuenta`);
    }
  }

  // ⚠️ v2.61: Inicialización lazy con DOMUtils.onVisibleOnce - Mejorado con validaciones
  function init() {
    console.info(`[${MOD}] Inicializando módulo de cuentas contables...`);
    
    // Validar dependencias críticas
    if (!w.TabulatorFactory) {
      console.error(`[${MOD}] TabulatorFactory no está disponible. Reintentando en 500ms...`);
      setTimeout(init, 500);
      return;
    }

    if (!w.DOMUtils || typeof w.DOMUtils.onVisibleOnce !== 'function') {
      console.error(`[${MOD}] DOMUtils.onVisibleOnce no está disponible. Reintentando en 500ms...`);
      setTimeout(init, 500);
      return;
    }

    // ⚠️ v2.61: Verificar que el tab existe antes de inicializar
    const tabElement = d.querySelector(TAB_ID);
    if (!tabElement) {
      console.warn(`[${MOD}] Tab ${TAB_ID} no encontrado. El módulo se inicializará cuando el tab sea visible.`);
      // Intentar inicializar directamente si el contenedor está disponible
      const tableContainer = d.querySelector(TABLE_SELECTOR);
      if (tableContainer && tableContainer.offsetParent !== null) {
        console.info(`[${MOD}] Contenedor de tabla encontrado, inicializando directamente...`);
        initTabulator().then(table => {
          if (table) {
            state.table = table;
            // ⚠️ v2.61: attachTableListeners() ya no es necesario (listeners en initTabulator)
            attachOffcanvasListeners();
            attachRefreshListener();
            console.info(`[${MOD}] Módulo inicializado correctamente (sin tab)`);
          }
        });
      }
      return;
    }

    console.info(`[${MOD}] Tab ${TAB_ID} encontrado, esperando a que sea visible...`);

    // Inicializar tabla cuando el tab sea visible
    w.DOMUtils.onVisibleOnce(TAB_ID, async () => {
      console.info(`[${MOD}] Tab ${TAB_ID} visible, inicializando tabla...`);
      state.table = await initTabulator();
      if (state.table) {
        // ⚠️ v2.61: attachTableListeners() ya no es necesario (listeners en initTabulator)
        attachOffcanvasListeners();
        attachRefreshListener();
        console.info(`[${MOD}] Módulo inicializado correctamente`);
      } else {
        console.error(`[${MOD}] No se pudo inicializar la tabla`);
      }
    });

    // Escuchar eventos HTMX para abrir offcanvas automáticamente
    if (typeof htmx !== 'undefined') {
      d.body.addEventListener('htmx:afterSwap', handleHTMXSwap);
      console.info(`[${MOD}] Listener HTMX registrado`);
    } else {
      console.warn(`[${MOD}] HTMX no está disponible`);
    }
  }

  // Inicializar cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
    console.info(`[${MOD}] Esperando DOMContentLoaded...`);
  } else {
    console.info(`[${MOD}] DOM ya está listo, inicializando inmediatamente...`);
    init();
  }

  // Exportar API pública
  if (typeof w !== 'undefined') {
    w.AppCuentas = Object.freeze({
      init,
      reload: () => {
        if (state.table && typeof state.table.replaceData === 'function') {
          state.table.replaceData();
        } else {
          init();
        }
      }
    });
  }
})(window, document);
