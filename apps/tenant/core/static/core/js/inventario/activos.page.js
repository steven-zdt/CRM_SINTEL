/**
 * Módulo Activos Fijos v2.60 - Tabulator Implementation (Migrado desde DataTables)
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.inventarioAPI (definido en inventario.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 */
(function(w, d) {
  'use strict';

  const TABLE_SELECTOR = '#grid-activos';
  const SEARCH_SELECTOR = '#search-activo';
  const API_URL = '/api/v1/inventario/activos/';
  let table = null;

  // Helper: Obtener CSRF token
  function getCookie(name) {
    const value = `; ${d.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  // Definir columnas específicas del módulo
  function getColumns() {
    return [
      {
        title: "ID",
        field: "id",
        width: 60,
        headerSort: false
      },
      {
        title: "Placa/Código",
        field: "codigo"
      },
      {
        title: "Nombre",
        field: "nombre"
      },
      {
        title: "Categoría",
        field: "categoria_nombre",
        formatter: w.TabulatorFactory.formatters.valueOrFallback
      },
      {
        title: "Fecha Compra",
        field: "fecha_adquisicion",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '-';
          return new Date(val).toLocaleDateString('es-CO');
        }
      },
      {
        title: "Costo",
        field: "costo_adquisicion",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(val);
        }
      },
      {
        title: "Responsable",
        field: "responsable",
        formatter: w.TabulatorFactory.formatters.valueOrFallback
      },
      {
        title: "Estado",
        field: "estado_display",
        formatter: function(cell) {
          const val = cell.getValue();
          const estado = cell.getData().estado;
          let color = 'bg-secondary';
          if (estado === 'ACTIVO') color = 'bg-success';
          else if (estado === 'MANTENIMIENTO') color = 'bg-warning';
          else if (estado === 'BAJA' || estado === 'VENDIDO') color = 'bg-danger';
          return `<span class="badge ${color}">${val || estado}</span>`;
        },
        headerSort: false
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id = rowData.id;
          
          return `
            <div class="btn-group btn-group-sm" role="group">
              <button type="button" class="btn btn-outline-primary" data-action="editar" data-id="${id}" title="Editar Activo Fijo">
                <i class="fas fa-edit"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" data-action="eliminar" data-id="${id}" title="Eliminar Activo Fijo">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          `;
        },
        headerSort: false,
        hozAlign: "center",
        width: 120
      }
    ];
  }

  // Inicializar tabla
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error('[activos.page] TabulatorFactory no está disponible');
      return null;
    }

    // ⚠️ Anti-Zombies: Destruir instancia anterior si existe
    if (w.SintelInventarioTables && w.SintelInventarioTables.activos) {
      try {
        w.SintelInventarioTables.activos.destroy();
      } catch (error) {
        console.warn('[activos.page] Error al destruir instancia anterior:', error);
      }
    }

    const columns = getColumns();
    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, columns, {
      searchInputSelector: SEARCH_SELECTOR
    });

    // ⚠️ Guardar en singleton global para acceso desde botones de refrescar
    if (!w.SintelInventarioTables) {
      w.SintelInventarioTables = {};
    }
    w.SintelInventarioTables.activos = table;

    // ⚠️ v2.60: Event delegation para botones de acciones (HTMX + Offcanvas)
    if (table) {
      const container = d.querySelector(TABLE_SELECTOR);
      if (container) {
        container.addEventListener('click', async function(e) {
          const btn = e.target.closest('button[data-action]');
          if (!btn) return;
          
          e.preventDefault();
          e.stopPropagation();
          
          const action = btn.getAttribute('data-action');
          const id = parseInt(btn.getAttribute('data-id'), 10);
          
          if (!id || isNaN(id)) {
            console.warn('[activos.page] ID no válido:', id);
            return;
          }
          
          if (action === 'editar') {
            editar(id);
          } else if (action === 'eliminar') {
            eliminar(id);
          }
        });
      }
    }

    return table;
  }

  /**
   * Editar activo (abrir offcanvas con datos del activo)
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function editar(id) {
    if (!id) {
      console.error('[activos.page] ID de activo no proporcionado');
      return;
    }

    // ⚠️ v2.60: Cargar offcanvas vía HTMX
    await htmx.ajax('GET', `/api/v1/inventario/activos/gestor-offcanvas/?id=${id}`, {
      target: '#offcanvas-container-activos',
      swap: 'innerHTML'
    });

    const offcanvasEl = d.getElementById('offcanvas-activos');
    if (offcanvasEl) {
      const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
      offcanvas.show();
      // Configurar eventos del formulario
      setTimeout(function() {
        configurarEventosFormulario();
      }, 100);
    }
  }

  /**
   * Guardar activo (crear o actualizar)
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function guardarActivo(e) {
    e.preventDefault();
    e.stopPropagation();

    const form = d.querySelector('#form-activo');
    if (!form) {
      console.error('[activos.page] Formulario #form-activo no encontrado');
      return;
    }

    const formData = new FormData(form);
    const payload = {
      codigo: formData.get('codigo')?.trim() || '',
      nombre: formData.get('nombre')?.trim() || '',
      categoria: formData.get('categoria') ? parseInt(formData.get('categoria'), 10) : null,
      marca: formData.get('marca')?.trim() || '',
      modelo: formData.get('modelo')?.trim() || '',
      descripcion: formData.get('descripcion')?.trim() || '',
      ubicacion: formData.get('ubicacion')?.trim() || '',
      responsable: formData.get('responsable')?.trim() || '',
      fecha_adquisicion: formData.get('fecha_adquisicion') || null,
      costo_adquisicion: parseFloat(formData.get('costo_adquisicion') || '0') || 0,
      estado: formData.get('estado') || 'ACTIVO'
    };

    // Validación básica
    if (!payload.codigo || !payload.nombre || !payload.estado) {
      const errorContainer = d.querySelector('#form-activo-feedback');
      if (errorContainer) {
        errorContainer.className = 'alert alert-danger';
        errorContainer.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-2"></i>Los campos Código, Nombre y Estado son requeridos.';
        errorContainer.classList.remove('d-none');
      }
      return;
    }

    const activoId = formData.get('id');
    let res;

    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    if (!w.inventarioAPI || !w.inventarioAPI.activos) {
      console.error('[activos.page] inventarioAPI.activos no está disponible');
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API no disponible' } }, '[activos.page]');
      }
      return;
    }

    if (activoId) {
      // Actualizar
      res = await w.inventarioAPI.activos.update(activoId, payload);
    } else {
      // Crear
      res = await w.inventarioAPI.activos.save(payload);
    }

    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[activos.page]', {
          modalSelector: '#offcanvas-activos',
          errorContainerSelector: '#form-activo-feedback'
        });
      }
      return;
    }

    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success(activoId ? 'Activo actualizado correctamente' : 'Activo creado correctamente');
    }

    // Cerrar offcanvas
    const offcanvasEl = d.getElementById('offcanvas-activos');
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
    const btnGuardar = d.querySelector('#btn-guardar-activo');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', guardarActivo);
    }
  }

  /**
   * Eliminar activo
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function eliminar(id) {
    // ⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN: Validar estado activo antes de proceder
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    // Obtener datos del activo para validar estado
    const resGet = await w.inventarioAPI.activos.get(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!resGet.ok || !resGet.data) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(resGet, '[activos.page]');
      }
      return;
    }

    const data = resGet.data;
    
    // Validar que el activo no esté en estado ACTIVO
    if (data.estado === 'ACTIVO') {
      if (w.SintelFeedback) {
        w.SintelFeedback.error('El ítem está activo. Desactívelo primero.');
      }
      return;
    }
    
    // Confirmar eliminación solo si no está activo
    if (!confirm('¿Está seguro de eliminar este activo fijo?')) {
      return;
    }

    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.inventarioAPI.activos.delete(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[activos.page]');
      }
      return;
    }

    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Activo fijo eliminado correctamente');
    }
    
    if (table) {
      table.replaceData();
    }
  }

  /**
   * Cargar categorías
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function cargarCategorias(categoriaSeleccionada = null) {
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.inventarioAPI.categorias.list({ page_size: 200 });
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok || !res.data) {
      // ⚠️ v2.60: Delegar a UIManager para mostrar error (pero no bloquear)
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(res, '[activos.page]');
      }
      return;
    }

    // ⚠️ v2.60: El endpoint retorna formato paginado {count, results, next, previous}
    // Extraer el array de categorías desde results
    const categorias = Array.isArray(res.data) ? res.data : (res.data.results || []);
    
    const select = d.querySelector('#activo-categoria');
    if (!select) {
      return;
    }

    // Limpiar opciones
    select.innerHTML = '<option value="">Seleccione...</option>';

    // Agregar categorías
    if (categorias.length === 0) {
      const option = d.createElement('option');
      option.value = '';
      option.textContent = 'No hay categorías disponibles';
      option.disabled = true;
      select.appendChild(option);
      return;
    }

    categorias.forEach(cat => {
      // Filtrar solo categorías aplicables a ACTIVOS
      if (cat.aplicacion === 'ACTIVO' || cat.aplicacion === 'TODO') {
        const option = d.createElement('option');
        option.value = cat.id;
        option.textContent = cat.nombre;
        if (categoriaSeleccionada && (cat.id === categoriaSeleccionada || cat.id === parseInt(categoriaSeleccionada, 10))) {
          option.selected = true;
        }
        select.appendChild(option);
      }
    });
  }

  /**
   * Abrir offcanvas para crear nuevo activo
   * ⚠️ v2.60: Usa HTMX para cargar el formulario
   */
  async function abrirModalCrear() {
    // ⚠️ v2.60: Cargar offcanvas vía HTMX
    await htmx.ajax('GET', '/api/v1/inventario/activos/gestor-offcanvas/', {
      target: '#offcanvas-container-activos',
      swap: 'innerHTML'
    });

    const offcanvasEl = d.getElementById('offcanvas-activos');
    if (offcanvasEl) {
      const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
      offcanvas.show();
      // Configurar eventos del formulario
      setTimeout(function() {
        configurarEventosFormulario();
      }, 100);
    }
  }

  /**
   * Función legacy (mantener por compatibilidad)
   * @deprecated Usar abrirModalCrear() que ahora usa offcanvas
   */
  function abrirModalCrearLegacy() {
    // Verificar que Bootstrap esté disponible
    if (typeof bootstrap === 'undefined') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Bootstrap no está cargado' } }, '[activos.page]');
      }
      return;
    }
    
    // Buscar modal
    const modalEl = d.querySelector('#modal-activo');
    if (!modalEl) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Modal no encontrado. Verifique que modals.html esté incluido.' } }, '[activos.page]');
      }
      return;
    }
    
    // Limpiar formulario
    const form = d.querySelector('#form-activo');
    if (form) {
      form.reset();
    }
    
    // Limpiar campos específicos
    const idField = d.querySelector('#activo-id');
    if (idField) idField.value = '';
    
    const estadoField = d.querySelector('#activo-estado');
    if (estadoField) estadoField.value = 'ACTIVO';
    
    // ⚠️ v2.60: Ocultar contenedor de error del Error Boundary
    const errorContainer = d.querySelector('#feedback-activo');
    if (errorContainer) {
      errorContainer.classList.add('d-none');
      errorContainer.textContent = '';
    }
    
    // Cargar categorías (async, no bloquea la apertura del modal)
    // ⚠️ v2.60: Aislamiento Gradual - cargarCategorias ya maneja errores internamente
    cargarCategorias();
    
    // Abrir modal usando Bootstrap 5
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    
    // Actualizar título antes de mostrar
    const title = modalEl.querySelector('.modal-title');
    if (title) {
      title.textContent = 'Nuevo Activo Fijo';
    }
    
    modal.show();
  }


  // Función para configurar eventos (reutilizable)
  function configurarEventos() {
    console.log('[activos.page] Configurando eventos...');
    
    // Asegurar que el módulo esté inicializado
    if (!w.InventarioActivosModule) {
      console.warn('[activos.page] InventarioActivosModule no está inicializado aún, inicializando...');
      w.InventarioActivosModule = {
        table: table,
        refresh: function() {
          if (table) {
            table.replaceData();
          }
        },
        editar: editar,
        eliminar: eliminar,
        abrirModalCrear: abrirModalCrear
      };
    }
    
    // Configurar botón "Nuevo" - Intentar múltiples veces si no está disponible
    function configurarBotonNuevo() {
      const btnNuevo = d.querySelector('#btn-nuevo-activo');
      if (btnNuevo) {
        // Remover listeners anteriores si existen (evitar duplicados)
        const nuevoBtn = btnNuevo.cloneNode(true);
        btnNuevo.parentNode.replaceChild(nuevoBtn, btnNuevo);
        
        console.log('[activos.page] Botón "Nuevo Activo" encontrado, agregando event listener');
        nuevoBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          console.log('[activos.page] Click en botón "Nuevo Activo"');
          abrirModalCrear();
        });
        
        // También exponer globalmente para acceso directo (ya está en el módulo, pero por si acaso)
        if (w.InventarioActivosModule) {
          w.InventarioActivosModule.abrirModalCrear = abrirModalCrear;
        }
        
        return true;
      }
      return false;
    }
    
    // Intentar configurar el botón inmediatamente
    if (!configurarBotonNuevo()) {
      // Si no está disponible, intentar después de un delay
      setTimeout(() => {
        if (!configurarBotonNuevo()) {
          console.warn('[activos.page] Botón #btn-nuevo-activo no encontrado después de delay');
        }
      }, 500);
    }
    
    // Configurar formulario
    const form = d.querySelector('#form-activo');
    if (form) {
      // Remover listeners anteriores si existen (evitar duplicados)
      const nuevoForm = form.cloneNode(true);
      form.parentNode.replaceChild(nuevoForm, form);
      
      nuevoForm.addEventListener('submit', function(e) {
        e.preventDefault();
        guardarActivo();
      });
      console.log('[activos.page] Formulario configurado');
    } else {
      console.warn('[activos.page] Formulario #form-activo no encontrado');
    }
  }

  // Función para inicializar el módulo completo
  function inicializarModulo() {
    console.log('[activos.page] Inicializando módulo completo...');
    
    // Inicializar tabla
    table = initTable();
    
    // Exponer módulo globalmente ANTES de configurar eventos
    w.InventarioActivosModule = {
      table: table,
      refresh: function() {
        if (table) {
          table.replaceData();
        }
      },
      editar: editar,
      eliminar: eliminar,
      abrirModalCrear: abrirModalCrear
    };
    
    console.log('[activos.page] Módulo expuesto globalmente:', w.InventarioActivosModule);
    
    // Configurar eventos DESPUÉS de inicializar el módulo
    configurarEventos();
  }

  /**
   * ⚠️ v2.60: Inicialización con lazy loading usando DOMUtils.onVisibleOnce
   * Solo se ejecuta cuando el tab/contenedor se vuelve visible
   */
  function init() {
    // Verificar que el contenedor exista
    const container = d.querySelector(TABLE_SELECTOR);
    if (!container) {
      console.warn('[activos.page] Contenedor ' + TABLE_SELECTOR + ' no encontrado');
      return;
    }

    // Verificar que el contenedor esté conectado al DOM
    if (!container.isConnected) {
      console.warn('[activos.page] Contenedor ' + TABLE_SELECTOR + ' no está conectado al DOM');
      return;
    }

    // Verificar que no se haya inicializado ya
    if (table && w.InventarioActivosModule) {
      console.log('[activos.page] Tabla ya inicializada, omitiendo...');
      return;
    }

    inicializarModulo();
  }

  // ⚠️ v2.60: Lazy Loading - Inicializar solo cuando el contenedor sea visible
  if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
    const selectors = [
      TABLE_SELECTOR,
      '#pane-activos',
      '#tab-activos-content',
      '#subtab-activos',
      '#workspace .tab-pane.show ' + TABLE_SELECTOR
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
        console.log('[activos.page] Contenedor visible, inicializando tabla...');
        inicializarModulo();
      }, { once: true, timeout: 30000 });
    } else {
      // Fallback: Inicializar cuando el DOM esté listo
      console.warn('[activos.page] Selectores de contenedor no encontrados, usando fallback DOMContentLoaded');
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
      } else {
        init();
      }
    }
  } else {
    // Fallback: Si DOMUtils no está disponible, usar DOMContentLoaded
    console.warn('[activos.page] DOMUtils.onVisibleOnce no está disponible, usando fallback DOMContentLoaded');
    if (d.readyState === 'loading') {
      d.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }

  // ⚠️ Bootstrap Tabs: Inicializar cuando se muestra el tab de activos
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-bs-target') === '#pane-activos' || e.target.id === 'tab-activos')) {
      console.log('[activos.page] Tab de activos mostrado, verificando inicialización...');
      if (!table || !w.SintelInventarioTables || !w.SintelInventarioTables.activos) {
        setTimeout(function() {
          inicializarModulo();
        }, 100);
      }
    }
  });

  // ⚠️ HTMX: Reinicializar cuando se carga contenido vía HTMX
  if (typeof htmx !== 'undefined') {
    d.addEventListener('htmx:afterSwap', function(event) {
      if (event.detail.target.id === 'offcanvas-container-activos') {
        // Configurar eventos del formulario cuando se carga el offcanvas
        setTimeout(function() {
          configurarEventosFormulario();
        }, 100);
      }
      
      if (event.detail.target.id === 'pane-activos' || 
          event.detail.target.id === 'tab-activos-content' ||
          event.detail.target.id === 'subtab-activos') {
        setTimeout(function() {
          if (!table || !w.InventarioActivosModule) {
            init();
          }
        }, 100);
      }
    });
  }

})(window, document);
