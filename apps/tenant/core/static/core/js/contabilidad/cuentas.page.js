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
  const TABLE_SELECTOR = '#grid-cuentas';
  const SEARCH_SELECTOR = '#search-cuenta';
  const ROUTES_MODULE = 'contabilidad.cuentas';  // ⚠️ v2.61: Usar Routes para descubrir URLs
  const TAB_ID = '#subtab-cuentas';
  const ERROR_CONTAINER_ID = '#error-container-cuentas';
  const OFFCANVAS_CONTAINER_ID = '#offcanvas-container-cuentas';
  
  // Estado del módulo
  let state = {
    initialized: false,
    listenersAttached: false,
    table: null,
    urls: { collection: null }
  };

  /**
   * Descubrir URL de colección usando Routes
   * ⚠️ v2.61: Usar Routes helper centralizado (patrón asientos.page.js)
   */
  async function discoverCollectionUrl() {
    if (state.urls.collection) {
      return state.urls.collection;
    }
    
    console.info(`[${MOD}.page] Descubriendo URL de colección usando Routes:`, ROUTES_MODULE);
    
    try {
      // Usar Routes para obtener la URL de colección
      if (window.Routes && typeof window.Routes.collectionUrl === 'function') {
        const collectionUrl = await window.Routes.collectionUrl(ROUTES_MODULE);
        if (collectionUrl) {
          state.urls.collection = collectionUrl;
          console.info(`[${MOD}.page] state.urls.collection descubierta desde Routes:`, state.urls.collection);
          return state.urls.collection;
        }
      }
      
      // Fallback: usar ruta estándar
      const fallbackUrl = '/api/v1/contabilidad/cuentas-contables/';
      state.urls.collection = window.API_HELPERS?.withTrailingSlash(fallbackUrl) || fallbackUrl;
      console.warn(`[${MOD}.page] Routes no disponible, usando fallback:`, state.urls.collection);
      return state.urls.collection;
    } catch (err) {
      console.error(`[${MOD}.page] Error descubriendo URL de colección:`, err);
      // Fallback: usar ruta estándar
      const fallbackUrl = '/api/v1/contabilidad/cuentas-contables/';
      state.urls.collection = window.API_HELPERS?.withTrailingSlash(fallbackUrl) || fallbackUrl;
      return state.urls.collection;
    }
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

  // ⚠️ v2.60: Inicializar Tabulator usando TabulatorFactory
  async function initTabulator() {
    if (!w.TabulatorFactory) {
      console.error(MOD, 'TabulatorFactory no está disponible');
      return null;
    }

    const tableEl = d.querySelector(TABLE_SELECTOR);
    if (!tableEl) {
      console.error(MOD, 'Tabla no encontrada:', TABLE_SELECTOR);
      return null;
    }

    // ⚠️ v2.61: Descubrir URL antes de crear tabla
    const apiUrl = await discoverCollectionUrl();
    
    // ⚠️ v2.60: Usar TabulatorFactory v2.40
    state.table = w.TabulatorFactory.create(
      TABLE_SELECTOR,
      apiUrl,
      getColumns(),
      {
        searchInputSelector: SEARCH_SELECTOR,
        paginationSize: 10
      }
    );

    return state.table;
  }

  // ⚠️ v2.60: Manejar apertura de offcanvas después de carga HTMX
  function handleHTMXSwap(event) {
    // Detectar cuando HTMX carga un offcanvas
    const target = event.detail.target;
    if (target && target.id && target.id.includes('offcanvas-cuenta')) {
      // Abrir offcanvas después de que HTMX inyecta el contenido
      requestAnimationFrame(() => {
        const offcanvasEl = d.getElementById(target.id);
        if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
          const offcanvas = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          offcanvas.show();
        }
      });
    }
  }

  // ⚠️ v2.60: Event delegation para acciones de tabla
  function attachTableListeners() {
    // Ver detalle
    d.addEventListener('click', async (ev) => {
      const btn = ev.target.closest('.btn-ver-cuenta');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id) {
          // Cargar offcanvas de detalle vía HTMX
          if (typeof htmx !== 'undefined') {
            const detailUrl = await cuentaDetailUrl(id);
            htmx.ajax('GET', `${detailUrl}render-offcanvas/detalle/`, {
              target: OFFCANVAS_CONTAINER_ID,
              swap: 'innerHTML'
            }).then(() => {
              handleHTMXSwap({ detail: { target: d.querySelector(OFFCANVAS_CONTAINER_ID) } });
            });
          }
        }
      }
    });

    // Editar
    d.addEventListener('click', async (ev) => {
      const btn = ev.target.closest('.btn-editar-cuenta');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id) {
          // Cargar offcanvas de edición vía HTMX
          if (typeof htmx !== 'undefined') {
            const detailUrl = await cuentaDetailUrl(id);
            htmx.ajax('GET', `${detailUrl}render-offcanvas/editar/`, {
              target: OFFCANVAS_CONTAINER_ID,
              swap: 'innerHTML'
            }).then(() => {
              handleHTMXSwap({ detail: { target: d.querySelector(OFFCANVAS_CONTAINER_ID) } });
            });
          }
        }
      }
    });

    // Eliminar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.btn-eliminar-cuenta');
      if (btn) {
        ev.preventDefault();
        const id = btn.dataset.id;
        if (id) {
          if (confirm('¿Está seguro de que desea eliminar esta cuenta contable?')) {
            handleEliminarCuenta(id);
          }
        }
      }
    });
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

  // ⚠️ v2.60: Guardar cuenta (crear o actualizar)
  async function handleGuardarCuenta(mode) {
    const formId = mode === 'create' ? '#form-cuenta-crear' : '#form-cuenta-editar';
    const form = d.querySelector(formId);
    if (!form) {
      console.error(MOD, 'Formulario no encontrado:', formId);
      return;
    }

    const formData = new FormData(form);
    const payload = {};
    for (const [key, value] of formData.entries()) {
      if (key === 'activa') {
        payload[key] = value === 'true';
      } else if (key === 'cuenta_padre') {
        payload[key] = value ? parseInt(value) : null;
      } else {
        payload[key] = value || null;
      }
    }

    const collectionUrl = await discoverCollectionUrl();
    const url = mode === 'create' ? collectionUrl : await cuentaDetailUrl(formData.get('id'));
    const method = mode === 'create' ? 'POST' : 'PATCH';

    try {
      const response = await w.http(url, {
        method: method,
        body: JSON.stringify(payload),
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        // ⚠️ v2.60: Usar UIManager para manejo de errores
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(response, ERROR_CONTAINER_ID);
        } else {
          throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        return;
      }

      // Recargar tabla
      if (state.table && typeof state.table.replaceData === 'function') {
        state.table.replaceData();
      }

      // Cerrar offcanvas
      const offcanvasId = mode === 'create' ? '#offcanvas-cuenta-crear' : '#offcanvas-cuenta-editar';
      const offcanvasEl = d.querySelector(offcanvasId);
      if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
        const offcanvas = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (offcanvas) {
          offcanvas.hide();
        }
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success(mode === 'create' ? 'Cuenta creada correctamente' : 'Cuenta actualizada correctamente');
      }
    } catch (err) {
      console.error(MOD, 'Error guardando cuenta:', err);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(err, ERROR_CONTAINER_ID);
      }
    }
  }

  // ⚠️ v2.60: Eliminar cuenta
  async function handleEliminarCuenta(id) {
    if (!id) {
      console.error(MOD, 'ID de cuenta requerido');
      return;
    }

    try {
      const deleteUrl = await cuentaDetailUrl(id);
      const response = await w.http(deleteUrl, {
        method: 'DELETE'
      });

      if (!response.ok) {
        // ⚠️ v2.60: Usar UIManager para manejo de errores
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(response, ERROR_CONTAINER_ID);
        } else {
          throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        return;
      }

      // Recargar tabla
      if (state.table && typeof state.table.replaceData === 'function') {
        state.table.replaceData();
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Cuenta eliminada correctamente');
      }
    } catch (err) {
      console.error(MOD, 'Error eliminando cuenta:', err);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(err, ERROR_CONTAINER_ID);
      }
    }
  }

  // ⚠️ v2.60: Botón refrescar
  function attachRefreshListener() {
    const btnRefresh = d.querySelector('#btn-refrescar-cuentas');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        if (state.table && typeof state.table.replaceData === 'function') {
          state.table.replaceData();
        }
      });
    }
  }

  // ⚠️ v2.60: Inicialización lazy con DOMUtils.onVisibleOnce
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
    w.DOMUtils.onVisibleOnce(TAB_ID, async () => {
      state.table = await initTabulator();
      attachTableListeners();
      attachOffcanvasListeners();
      attachRefreshListener();
    });

    // Escuchar eventos HTMX para abrir offcanvas automáticamente
    if (typeof htmx !== 'undefined') {
      d.body.addEventListener('htmx:afterSwap', handleHTMXSwap);
    }
  }

  // Inicializar cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
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
