/**
 * categorias.page.js - Módulo Categorías v2.60 - Tabulator Implementation
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Lazy Loading: Usa DOMUtils.onVisibleOnce() para inicialización diferida
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.inventarioAPI (definido en inventario.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 */
(function (w, d) {
  'use strict';

  const MOD = '[categorias.page]';
  const GRID_ID = '#grid-categorias';
  const SEARCH_ID = '#search-categoria';
  const API_URL = '/api/v1/inventario/categorias/';
  const TAB_ID = '#tab-categorias';
  let table = null;

  // Definir columnas específicas del módulo
  function getColumns() {
    return [
      {
        title: "Nombre",
        field: "nombre",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '---';
        },
        minWidth: 200,
        headerFilter: "input"
      },
      {
        title: "Descripción",
        field: "descripcion",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '<span class="text-muted">Sin descripción</span>';
        },
        minWidth: 250
      },
      {
        title: "Aplicación",
        field: "aplicacion",
        formatter: function(cell) {
          const aplicacion = cell.getValue();
          const badges = {
            'TODO': '<span class="badge bg-primary">Todos</span>',
            'PRODUCTO': '<span class="badge bg-info">Productos</span>',
            'SERVICIO': '<span class="badge bg-warning">Servicios</span>',
            'ACTIVO': '<span class="badge bg-secondary">Activos</span>'
          };
          return badges[aplicacion] || `<span class="badge bg-secondary">${aplicacion || '-'}</span>`;
        },
        width: 120
      },
      {
        title: "Estado",
        field: "activo",
        formatter: function(cell) {
          const activo = cell.getValue();
          if (activo) {
            return '<span class="badge bg-success">Activo</span>';
          }
          return '<span class="badge bg-secondary">Inactivo</span>';
        },
        width: 100,
        hozAlign: "center"
      },
      {
        title: "Acciones",
        field: "acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id = rowData.id;
          return `
            <div class="btn-group btn-group-sm" role="group">
              <button type="button" class="btn btn-outline-primary btn-edit-categoria" data-id="${id}" title="Editar">
                <i class="bi bi-pencil"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-delete-categoria" data-id="${id}" title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        width: 150,
        headerSort: false,
        resizable: false
      }
    ];
  }

  /**
   * Inicializar tabla de categorías
   */
  function initTable() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) {
      console.warn(`${MOD} Contenedor ${GRID_ID} no encontrado`);
      return;
    }

    // ⚠️ Anti-Zombies: Destruir instancia previa si existe
    if (w.SintelInventarioTables && w.SintelInventarioTables.categorias) {
      try {
        w.SintelInventarioTables.categorias.destroy();
      } catch (error) {
        console.warn(`${MOD} Error al destruir tabla previa:`, error);
      }
    }

    // ⚠️ Verificar que TabulatorFactory esté disponible
    if (!w.TabulatorFactory || typeof w.TabulatorFactory.create !== 'function') {
      console.error(`${MOD} TabulatorFactory no está disponible`);
      return;
    }

    // Configuración de la tabla
    const tableConfig = {
      searchInputSelector: SEARCH_ID,
      pagination: true,
      paginationMode: "remote",
      paginationSize: 10,
      paginationSizeSelector: [10, 25, 50, 100],
      layout: "fitColumns",
      responsiveLayout: "hide",
      placeholder: "No hay categorías registradas",
      locale: "es"
    };

    // Crear tabla usando TabulatorFactory
    table = w.TabulatorFactory.create(
      GRID_ID,
      API_URL,
      getColumns(),
      tableConfig
    );

    // Guardar instancia en singleton global
    if (!w.SintelInventarioTables) {
      w.SintelInventarioTables = {};
    }
    w.SintelInventarioTables.categorias = table;

    // ⚠️ Event Delegation: Manejar clics en botones de acción
    initListEvents();
  }

  /**
   * Inicializar eventos de la lista (Event Delegation)
   */
  function initListEvents() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return;

    // Event Delegation para botones de acción
    gridEl.addEventListener('click', async function(e) {
      const btn = e.target.closest('button');
      if (!btn) return;

      // Botón Editar
      if (btn.classList.contains('btn-edit-categoria')) {
        e.preventDefault();
        const id = btn.getAttribute('data-id');
        if (!id) return;

        await htmx.ajax('GET', `/api/v1/inventario/categorias/gestor-offcanvas/?id=${id}`, {
          target: '#offcanvas-container-categorias',
          swap: 'innerHTML'
        });

        const offcanvasEl = d.getElementById('offcanvas-categorias');
        if (offcanvasEl) {
          const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          offcanvas.show();
        }
        return;
      }

      // Botón Eliminar
      if (btn.classList.contains('btn-delete-categoria')) {
        e.preventDefault();
        const id = btn.getAttribute('data-id');
        if (!id) return;

        if (!confirm('¿Está seguro de eliminar esta categoría? Los ítems asociados quedarán sin categoría.')) {
          return;
        }

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.inventarioAPI || !w.inventarioAPI.categorias || typeof w.inventarioAPI.categorias.delete !== 'function') {
          console.error(`${MOD} inventarioAPI.categorias.delete no está disponible`);
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError({ status: 500, data: { detail: 'API de eliminación no disponible' } }, MOD);
          }
          return;
        }

        const deleteRes = await w.inventarioAPI.categorias.delete(id);

        // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
        if (!deleteRes.ok) {
          if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(deleteRes, MOD, {
              modalSelector: '#offcanvas-categorias',
              errorContainerSelector: '#form-categoria-feedback'
            });
          }
          return;
        }

        // Éxito
        if (w.SintelFeedback) {
          w.SintelFeedback.success('Categoría eliminada correctamente');
        }
        if (table) {
          table.replaceData();
        }
      }
    });

    // Event Delegation: Clic en fila para editar
    if (table) {
      table.on('rowClick', async function(e, row) {
        const data = row.getData();
        if (!data || !data.id) return;

        await htmx.ajax('GET', `/api/v1/inventario/categorias/gestor-offcanvas/?id=${data.id}`, {
          target: '#offcanvas-container-categorias',
          swap: 'innerHTML'
        });

        const offcanvasEl = d.getElementById('offcanvas-categorias');
        if (offcanvasEl) {
          const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          offcanvas.show();
        }
      });
    }
  }

  /**
   * Guardar categoría (crear o actualizar)
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function guardarCategoria(e) {
    e.preventDefault();
    e.stopPropagation();

    const form = d.querySelector('#form-categoria');
    if (!form) {
      console.error(`${MOD} Formulario #form-categoria no encontrado`);
      return;
    }

    const formData = new FormData(form);
    const payload = {
      nombre: formData.get('nombre')?.trim() || '',
      aplicacion: formData.get('aplicacion') || 'TODO',
      descripcion: formData.get('descripcion')?.trim() || '',
      activo: formData.get('activo') === 'on' || formData.get('activo') === 'true'
    };

    // Validación básica
    if (!payload.nombre || !payload.aplicacion) {
      const errorContainer = d.querySelector('#form-categoria-feedback');
      if (errorContainer) {
        errorContainer.className = 'alert alert-danger';
        errorContainer.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-2"></i>Los campos Nombre y Aplicación son requeridos.';
        errorContainer.classList.remove('d-none');
      }
      return;
    }

    const categoriaId = formData.get('id');
    let res;

    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    if (!w.inventarioAPI || !w.inventarioAPI.categorias) {
      console.error(`${MOD} inventarioAPI.categorias no está disponible`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API no disponible' } }, MOD);
      }
      return;
    }

    if (categoriaId) {
      // Actualizar
      res = await w.inventarioAPI.categorias.update(categoriaId, payload);
    } else {
      // Crear
      res = await w.inventarioAPI.categorias.save(payload);
    }

    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD, {
          modalSelector: '#offcanvas-categorias',
          errorContainerSelector: '#form-categoria-feedback'
        });
      }
      return;
    }

    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success(categoriaId ? 'Categoría actualizada correctamente' : 'Categoría creada correctamente');
    }

    // Cerrar offcanvas
    const offcanvasEl = d.getElementById('offcanvas-categorias');
    if (offcanvasEl) {
      const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
      if (offcanvas) {
        offcanvas.hide();
      }
    }

    // Refrescar tabla
    if (table) {
      table.replaceData();
    }
  }

  /**
   * Configurar eventos del formulario
   */
  function configurarEventosFormulario() {
    // Botón guardar
    const btnGuardar = d.querySelector('#btn-guardar-categoria');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', guardarCategoria);
    }
  }

  /**
   * Escuchar evento de actualización para refrescar tabla
   */
  d.addEventListener('categoriasActualizado', function() {
    if (w.SintelInventarioTables && w.SintelInventarioTables.categorias) {
      w.SintelInventarioTables.categorias.replaceData();
    }
  });

  /**
   * ⚠️ v2.60: Inicialización con lazy loading usando DOMUtils.onVisibleOnce
   * Solo se ejecuta cuando el tab/contenedor se vuelve visible
   */
  function init() {
    // Verificar que el contenedor exista
    const container = d.querySelector(GRID_ID);
    if (!container) {
      console.warn(`${MOD} Contenedor ${GRID_ID} no encontrado`);
      return;
    }

    // Verificar que el contenedor esté conectado al DOM
    if (!container.isConnected) {
      console.warn(`${MOD} Contenedor ${GRID_ID} no está conectado al DOM`);
      return;
    }

    // Verificar que no se haya inicializado ya
    if (table && w.SintelInventarioTables && w.SintelInventarioTables.categorias) {
      console.log(`${MOD} Tabla ya inicializada, omitiendo...`);
      return;
    }

    initTable();
  }

  // ⚠️ v2.60: Lazy Loading - Inicializar solo cuando el contenedor sea visible
  if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
    const selectors = [
      GRID_ID,
      '#pane-categorias',
      '#tab-categorias-content',
      '#workspace .tab-pane.show ' + GRID_ID
    ];
    
    let targetSelector = null;
    for (const selector of selectors) {
      const el = d.querySelector(selector);
      if (el) {
        targetSelector = selector;
        break;
      }
    }
    
    if (targetSelector) {
      w.DOMUtils.onVisibleOnce(targetSelector, function(el) {
        console.log(`${MOD} Contenedor visible, inicializando tabla...`);
        init();
      }, { once: true, timeout: 30000 });
    } else {
      // Fallback: Inicializar cuando el DOM esté listo
      console.warn(`${MOD} Selectores de contenedor no encontrados, usando fallback DOMContentLoaded`);
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
      } else {
        init();
      }
    }
  } else {
    // Fallback: Si DOMUtils no está disponible, usar DOMContentLoaded
    console.warn(`${MOD} DOMUtils.onVisibleOnce no está disponible, usando fallback DOMContentLoaded`);
    if (d.readyState === 'loading') {
      d.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }

  // ⚠️ Bootstrap Tabs: Inicializar cuando se muestra el tab de categorías
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-bs-target') === '#pane-categorias' || e.target.id === 'tab-categorias')) {
      console.log(`${MOD} Tab de categorías mostrado, verificando inicialización...`);
      if (!table || !w.SintelInventarioTables || !w.SintelInventarioTables.categorias) {
        setTimeout(function() {
          init();
        }, 100);
      }
    }
  });

  // ⚠️ HTMX: Reinicializar cuando se carga contenido vía HTMX
  if (typeof htmx !== 'undefined') {
    d.addEventListener('htmx:afterSwap', function(event) {
      if (event.detail.target.id === 'offcanvas-container-categorias') {
        // Configurar eventos del formulario cuando se carga el offcanvas
        setTimeout(function() {
          configurarEventosFormulario();
        }, 100);
      }
      
      if (event.detail.target.id === 'pane-categorias' || 
          event.detail.target.id === 'tab-categorias-content') {
        setTimeout(function() {
          if (!table || !w.SintelInventarioTables || !w.SintelInventarioTables.categorias) {
            init();
          }
        }, 100);
      }
    });
  }

})(window, document);
