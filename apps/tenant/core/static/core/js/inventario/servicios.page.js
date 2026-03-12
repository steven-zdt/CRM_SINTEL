/**
 * servicios.page.js - Módulo Servicios v2.60 - Tabulator Implementation
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

  const MOD = '[servicios.page]';
  const GRID_ID = '#grid-servicios';
  const SEARCH_ID = '#search-servicio';
  const API_URL = '/api/v1/inventario/servicios/';
  const TAB_ID = '#tab-servicios';
  let table = null;

  // Formateador de moneda
  function formatearMoneda(value) {
    if (value === null || value === undefined || value === '') return '$ 0,00';
    const num = parseFloat(value);
    if (isNaN(num)) return '$ 0,00';
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(num);
  }

  // Definir columnas específicas del módulo
  function getColumns() {
    return [
      {
        title: "Código",
        field: "codigo",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '---';
        },
        width: 120,
        headerFilter: "input"
      },
      {
        title: "Servicio",
        field: "nombre",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '---';
        },
        minWidth: 250,
        headerFilter: "input"
      },
      {
        title: "Categoría",
        field: "categoria_nombre",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '<span class="text-muted">Sin categoría</span>';
        },
        width: 150,
        headerFilter: "input"
      },
      {
        title: "Precio de Venta",
        field: "precio_venta",
        formatter: function(cell) {
          return formatearMoneda(cell.getValue());
        },
        width: 140,
        hozAlign: "right",
        sorter: "number"
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
              <button type="button" class="btn btn-outline-primary btn-edit-servicio" data-id="${id}" title="Editar">
                <i class="bi bi-pencil"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-delete-servicio" data-id="${id}" title="Eliminar">
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
   * Inicializar tabla de servicios
   */
  function initTable() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) {
      console.warn(`${MOD} Contenedor ${GRID_ID} no encontrado`);
      return;
    }

    // ⚠️ Anti-Zombies: Destruir instancia previa si existe
    if (w.SintelInventarioTables && w.SintelInventarioTables.servicios) {
      try {
        w.SintelInventarioTables.servicios.destroy();
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
      placeholder: "No hay servicios registrados",
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
    w.SintelInventarioTables.servicios = table;

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
      if (btn.classList.contains('btn-edit-servicio')) {
        e.preventDefault();
        const id = btn.getAttribute('data-id');
        if (!id) return;

        await htmx.ajax('GET', `/api/v1/inventario/servicios/gestor-offcanvas/?id=${id}`, {
          target: '#offcanvas-container-servicios',
          swap: 'innerHTML'
        });

        const offcanvasEl = d.getElementById('offcanvas-servicios');
        if (offcanvasEl) {
          const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          offcanvas.show();
        }
        return;
      }

      // Botón Eliminar
      if (btn.classList.contains('btn-delete-servicio')) {
        e.preventDefault();
        const id = btn.getAttribute('data-id');
        if (!id) return;

        if (!confirm('¿Está seguro de eliminar este servicio? Esta acción no se puede deshacer.')) {
          return;
        }

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.inventarioAPI || !w.inventarioAPI.servicios || typeof w.inventarioAPI.servicios.delete !== 'function') {
          console.error(`${MOD} inventarioAPI.servicios.delete no está disponible`);
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError({ status: 500, data: { detail: 'API de eliminación no disponible' } }, MOD);
          }
          return;
        }

        const deleteRes = await w.inventarioAPI.servicios.delete(id);

        // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
        if (!deleteRes.ok) {
          if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(deleteRes, MOD, {
              modalSelector: '#offcanvas-servicios',
              errorContainerSelector: '#form-servicio-feedback'
            });
          }
          return;
        }

        // Éxito
        if (w.SintelFeedback) {
          w.SintelFeedback.success('Servicio eliminado correctamente');
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

        await htmx.ajax('GET', `/api/v1/inventario/servicios/gestor-offcanvas/?id=${data.id}`, {
          target: '#offcanvas-container-servicios',
          swap: 'innerHTML'
        });

        const offcanvasEl = d.getElementById('offcanvas-servicios');
        if (offcanvasEl) {
          const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          offcanvas.show();
        }
      });
    }
  }

  /**
   * ⚠️ v2.61.3: DEPRECATED - Esta función ha sido movida a servicios_editor.js
   * La función guardarServicio() ahora está en servicios_editor.js (Feature-Sliced Architecture)
   * Este archivo solo maneja el listado de servicios, no la creación/edición
   */

  /**
   * Recolectar datos del formulario de historial de servicio
   * @returns {Object} Datos del historial
   */
  function recolectarDatosHistorial() {
    const form = d.querySelector('#form-historial-servicio');
    if (!form) {
      console.error(`${MOD} Formulario #form-historial-servicio no encontrado`);
      return null;
    }

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Remover campos vacíos
    Object.keys(data).forEach(key => {
      if (data[key] === '' || data[key] === null) {
        delete data[key];
      }
    });

    // ⚠️ Conversión de tipos numéricos
    if (data.servicio_id) {
      data.servicio = parseInt(data.servicio_id, 10);
      delete data.servicio_id;
    }
    if (data.cantidad) {
      data.cantidad = parseFloat(data.cantidad);
    }
    if (data.valor_cobrado) {
      data.valor_cobrado = parseFloat(data.valor_cobrado);
    }

    return data;
  }

  /**
   * Validar historial antes de enviar
   * @param {Object} data - Datos del historial
   * @returns {Object} {valid: boolean, error: string|null}
   */
  function validarHistorial(data) {
    // Validar que se haya seleccionado un servicio
    if (!data.servicio) {
      return {
        valid: false,
        error: 'Debe seleccionar un servicio'
      };
    }

    // Validar que la cantidad sea positiva
    if (!data.cantidad || data.cantidad <= 0) {
      return {
        valid: false,
        error: 'La cantidad debe ser mayor a cero'
      };
    }

    // Validar que el valor cobrado sea positivo (si se proporciona)
    if (data.valor_cobrado !== undefined && data.valor_cobrado < 0) {
      return {
        valid: false,
        error: 'El valor cobrado no puede ser negativo'
      };
    }

    return { valid: true, error: null };
  }

  /**
   * Procesar historial de servicio (registrar venta/uso)
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function procesarHistorialServicio() {
    const data = recolectarDatosHistorial();
    if (!data) {
      return;
    }

    // ⚠️ Validación frontend antes de enviar
    const validacion = validarHistorial(data);
    if (!validacion.valid) {
      // Mostrar error en el Error Boundary
      const errorContainer = d.querySelector('#form-historial-feedback');
      if (errorContainer) {
        errorContainer.classList.remove('d-none');
        errorContainer.innerHTML = `
          <i class="bi bi-exclamation-triangle me-2"></i>
          <strong>Error de validación:</strong> ${validacion.error}
        `;
      }
      return;
    }

    const offcanvasEl = d.querySelector('#offcanvas-historial-servicio');
    
    // ⚠️ Error Boundary v2.60: Guardar estado original del botón
    const btnGuardar = d.querySelector('#btn-guardar-historial');
    const btnOriginalText = btnGuardar?.innerHTML || '';
    const btnOriginalDisabled = btnGuardar?.disabled || false;
    
    // ⚠️ Error Boundary v2.60: Mostrar estado de loading
    if (btnGuardar) {
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Procesando...';
    }

    // Limpiar errores previos
    const errorContainer = d.querySelector('#form-historial-feedback');
    if (errorContainer) {
      errorContainer.classList.add('d-none');
      errorContainer.innerHTML = '';
    }

    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    if (!w.inventarioAPI || !w.inventarioAPI.historialServicios) {
      console.error(`${MOD} inventarioAPI.historialServicios no está disponible`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API no disponible' } }, MOD);
      }
      // Restaurar botón
      if (btnGuardar) {
        btnGuardar.disabled = btnOriginalDisabled;
        btnGuardar.innerHTML = btnOriginalText;
      }
      return;
    }

    const res = await w.inventarioAPI.historialServicios.save(data);

    // ⚠️ Error Boundary v2.60: Restaurar estado del botón
    if (btnGuardar) {
      btnGuardar.disabled = btnOriginalDisabled;
      btnGuardar.innerHTML = btnOriginalText;
    }

    // ⚠️ v2.60: Aislamiento Gradual - Manejo de errores con UIManager
    if (!res.ok) {
      // ⚠️ Error Boundary: Inyectar errores en el contenedor de feedback
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD, {
          errorContainerSelector: '#form-historial-feedback'
        });
      } else {
        // Fallback: Mostrar error básico
        if (errorContainer) {
          errorContainer.classList.remove('d-none');
          errorContainer.innerHTML = `
            <i class="bi bi-exclamation-triangle me-2"></i>
            <strong>Error:</strong> ${res.data?.detail || 'Error al procesar el historial'}
          `;
        }
      }
      return;
    }

    // ⚠️ Éxito: Cerrar Offcanvas, mostrar feedback y disparar evento
    if (offcanvasEl) {
      const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
      if (offcanvas) {
        offcanvas.hide();
      }
    }

    // Mostrar feedback de éxito
    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
      w.SintelFeedback.success('Historial de servicio registrado correctamente');
    }

    // ⚠️ Disparar evento personalizado para refrescar tabla
    d.dispatchEvent(new Event('serviciosActualizado'));
  }

  /**
   * Cargar servicios disponibles en el select de historial
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function cargarServiciosEnHistorial() {
    const select = d.querySelector('#historial-servicio-select');
    if (!select) {
      return;
    }

    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    if (!w.inventarioAPI || !w.inventarioAPI.servicios || typeof w.inventarioAPI.servicios.list !== 'function') {
      console.warn(`${MOD} inventarioAPI.servicios.list no está disponible`);
      return;
    }

    const res = await w.inventarioAPI.servicios.list({ page_size: 1000 }); // Cargar todos los servicios activos
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok || !res.data) {
      // ⚠️ v2.60: Delegar a UIManager para mostrar error (pero no bloquear)
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(res, MOD);
      }
      return;
    }

    const servicios = Array.isArray(res.data) ? res.data : (res.data.results || []);
    
    // Limpiar opciones existentes (excepto la primera opción vacía)
    select.innerHTML = '<option value="">Seleccionar servicio...</option>';

    // Agregar servicios activos
    servicios
      .filter(serv => serv.activo !== false) // Solo servicios activos
      .forEach(serv => {
        const option = d.createElement('option');
        option.value = serv.id;
        option.setAttribute('data-precio', serv.precio_venta || 0);
        option.textContent = `${serv.codigo} - ${serv.nombre}${serv.precio_venta ? ` ($${parseFloat(serv.precio_venta).toLocaleString('es-CO')})` : ''}`;
        select.appendChild(option);
      });

    // Event listener para actualizar valor cobrado cuando se selecciona un servicio
    select.addEventListener('change', function() {
      const selectedOption = select.options[select.selectedIndex];
      if (selectedOption && selectedOption.value) {
        const precio = parseFloat(selectedOption.getAttribute('data-precio') || '0');
        const valorCobradoInput = d.querySelector('#historial-valor-cobrado');
        if (valorCobradoInput && precio > 0) {
          valorCobradoInput.value = precio;
        }
      }
    });
  }

  /**
   * Configurar eventos del formulario
   * ⚠️ v2.61.3: El formulario de servicios se maneja por servicios_editor.js
   * Este archivo solo maneja el historial de servicios
   */
  function configurarEventosFormulario() {
    // ⚠️ v2.61.3: NO configurar eventos del formulario de servicios aquí
    // El formulario se maneja por servicios_editor.js (Feature-Sliced Architecture)

    // Botón guardar historial
    const btnGuardarHistorial = d.querySelector('#btn-guardar-historial');
    if (btnGuardarHistorial) {
      btnGuardarHistorial.addEventListener('click', procesarHistorialServicio);
    }

    // Formulario de historial (submit)
    const formHistorial = d.querySelector('#form-historial-servicio');
    if (formHistorial) {
      formHistorial.addEventListener('submit', function(e) {
        e.preventDefault();
        procesarHistorialServicio();
      });
    }

    // Cargar servicios cuando se muestra el offcanvas de historial
    const offcanvasHistorial = d.querySelector('#offcanvas-historial-servicio');
    if (offcanvasHistorial) {
      offcanvasHistorial.addEventListener('shown.bs.offcanvas', function() {
        cargarServiciosEnHistorial();
      });
    }
  }

  /**
   * Escuchar evento de actualización para refrescar tabla
   */
  d.addEventListener('serviciosActualizado', function() {
    if (w.SintelInventarioTables && w.SintelInventarioTables.servicios) {
      w.SintelInventarioTables.servicios.replaceData();
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
    if (table && w.SintelInventarioTables && w.SintelInventarioTables.servicios) {
      console.log(`${MOD} Tabla ya inicializada, omitiendo...`);
      return;
    }

    initTable();
  }

  // ⚠️ v2.60: Lazy Loading - Inicializar solo cuando el contenedor sea visible
  if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
    const selectors = [
      GRID_ID,
      '#pane-servicios',
      '#tab-servicios-content',
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

  // ⚠️ Bootstrap Tabs: Inicializar cuando se muestra el tab de servicios
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-bs-target') === '#pane-servicios' || e.target.id === 'tab-servicios')) {
      console.log(`${MOD} Tab de servicios mostrado, verificando inicialización...`);
      if (!table || !w.SintelInventarioTables || !w.SintelInventarioTables.servicios) {
        setTimeout(function() {
          init();
        }, 100);
      }
    }
  });

  // ⚠️ HTMX: Reinicializar cuando se carga contenido vía HTMX
  if (typeof htmx !== 'undefined') {
    d.addEventListener('htmx:afterSwap', function(event) {
      if (event.detail.target.id === 'offcanvas-container-servicios') {
        // Configurar eventos del formulario cuando se carga el offcanvas
        setTimeout(function() {
          configurarEventosFormulario();
        }, 100);
      }
      
      if (event.detail.target.id === 'pane-servicios' || 
          event.detail.target.id === 'tab-servicios-content') {
        setTimeout(function() {
          if (!table || !w.SintelInventarioTables || !w.SintelInventarioTables.servicios) {
            init();
          }
        }, 100);
      }
    });
  }

})(window, document);
