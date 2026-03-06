/**
 * Módulo Movimientos de Inventario (Kardex) v2.60 - Tabulator Implementation
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

  const TABLE_SELECTOR = '#grid-movimientos';
  const SEARCH_SELECTOR = '#search-movimiento';
  const API_URL = '/api/v1/inventario/movimientos/';
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
        title: "Fecha",
        field: "created_at",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '-';
          return new Date(val).toLocaleString('es-CO');
        }
      },
      {
        title: "Tipo Movimiento",
        field: "tipo_display",
        formatter: function(cell) {
          const val = cell.getValue();
          const tipo = cell.getData().tipo;
          let color = 'bg-secondary';
          // Entradas
          if (tipo && tipo.includes('ENTRADA')) {
            color = 'bg-success';
          }
          // Salidas
          else if (tipo && tipo.includes('SALIDA')) {
            color = 'bg-danger';
          }
          return `<span class="badge ${color}">${val || tipo}</span>`;
        }
      },
      {
        title: "Producto",
        field: "producto_nombre",
        formatter: function(cell) {
          const data = cell.getRow().getData();
          const codigo = data.producto_codigo || '';
          const nombre = data.producto_nombre || '-';
          return `<strong>${codigo}</strong> - ${nombre}`;
        }
      },
      {
        title: "Cantidad",
        field: "cantidad",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return val.toFixed(3);
        },
        hozAlign: "right"
      },
      {
        title: "Origen",
        field: "origen_referencia",
        formatter: w.TabulatorFactory.formatters.valueOrFallback
      },
      {
        title: "Destino",
        field: "cliente_referencia",
        formatter: w.TabulatorFactory.formatters.valueOrFallback
      },
      {
        title: "Observaciones",
        field: "observaciones",
        formatter: w.TabulatorFactory.formatters.valueOrFallback,
        width: 200
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id = rowData.id;
          
          // ⚠️ v2.95: Solo botón de ver detalles (movimientos históricos no se editan/eliminan)
          return `
            <button type="button" class="btn btn-outline-info btn-sm" data-action="ver-detalle" data-id="${id}" title="Ver Detalles">
              <i class="fas fa-eye"></i>
            </button>
          `;
        },
        headerSort: false,
        hozAlign: "center",
        width: 80
      }
    ];
  }

  // Inicializar tabla
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error('[movimientos.page] TabulatorFactory no está disponible');
      return null;
    }

    const columns = getColumns();
    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, columns, {
      searchInputSelector: SEARCH_SELECTOR
    });

    // ⚠️ v2.95: Event delegation para botones de acciones
    if (table) {
      const container = d.querySelector(TABLE_SELECTOR);
      if (container) {
        container.addEventListener('click', function(e) {
          const btn = e.target.closest('button[data-action]');
          if (!btn) return;
          
          e.preventDefault();
          e.stopPropagation();
          
          const action = btn.getAttribute('data-action');
          const id = parseInt(btn.getAttribute('data-id'), 10);
          
          if (!id || isNaN(id)) {
            console.warn('[movimientos.page] ID no válido:', id);
            return;
          }
          
          if (!w.InventarioMovimientosModule) {
            console.error('[movimientos.page] InventarioMovimientosModule no está disponible');
            if (w.notyf) {
              if (w.SintelFeedback) {
                w.SintelFeedback.error('Error: Módulo no disponible');
              }
            }
            return;
          }
          
          switch (action) {
            case 'ver-detalle':
              w.InventarioMovimientosModule.verDetalle(id);
              break;
            default:
              console.warn('[movimientos.page] Acción no reconocida:', action);
          }
        });
      }
    }

    return table;
  }

  /**
   * Funciones CRUD
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function verDetalle(id) {
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.inventarioAPI.movimientos.get(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok || !res.data) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[movimientos.page]');
      }
      return;
    }
    
    const movimiento = res.data;
    
    // Mostrar información en un alert o modal (simple por ahora)
    const info = `
      <strong>Fecha:</strong> ${movimiento.created_at ? new Date(movimiento.created_at).toLocaleString('es-CO') : '-'}<br>
      <strong>Tipo:</strong> ${movimiento.tipo_display || movimiento.tipo || '-'}<br>
      <strong>Producto:</strong> ${movimiento.producto_nombre || movimiento.producto_codigo || '-'}<br>
      <strong>Cantidad:</strong> ${parseFloat(movimiento.cantidad || 0).toFixed(3)}<br>
      <strong>Origen:</strong> ${movimiento.origen_referencia || '-'}<br>
      <strong>Destino:</strong> ${movimiento.cliente_referencia || '-'}<br>
      <strong>Observaciones:</strong> ${movimiento.observaciones || '-'}
    `;
    
    // Usar alert simple o crear un modal más elaborado
      // ⚠️ v2.60: Usar SintelFeedback para mostrar información (utilidad centralizada)
      if (w.SintelFeedback) {
        w.SintelFeedback.info(info);
      } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        // Fallback: usar UIManager si SintelFeedback no está disponible
        w.UIManager.notifyError({ status: 200, data: { detail: info } }, '[movimientos.page]');
      }
    
    // TODO: Implementar modal de detalles más elaborado si es necesario
  }

  /**
   * Cargar productos
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function cargarProductos() {
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.inventarioAPI.productos.list();
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok || !res.data) {
      // ⚠️ v2.60: Delegar a UIManager para mostrar error (pero no bloquear)
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(res, '[movimientos.page]');
      }
      return;
    }

    const productos = Array.isArray(res.data) ? res.data : (res.data.results || []);
    const select = d.querySelector('#movimiento-producto');
    if (!select) return;

    // Limpiar opciones
    select.innerHTML = '<option value="">Seleccione...</option>';

    // Agregar productos
    productos.forEach(prod => {
      const option = d.createElement('option');
      option.value = prod.id;
      option.textContent = `${prod.codigo} - ${prod.nombre}`;
      select.appendChild(option);
    });
  }

  function abrirModalCrear() {
    // Verificar que Bootstrap esté disponible
    if (typeof bootstrap === 'undefined') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Bootstrap no está cargado' } }, '[movimientos.page]');
      }
      return;
    }
    
    // Buscar modal
    const modalEl = d.querySelector('#modal-movimiento');
    if (!modalEl) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Modal no encontrado. Verifique que modals.html esté incluido.' } }, '[movimientos.page]');
      }
      return;
    }
    
    // Limpiar formulario
    const form = d.querySelector('#form-movimiento');
    if (form) {
      form.reset();
    }
    
    // ⚠️ v2.60: Ocultar contenedor de error del Error Boundary
    const errorContainer = d.querySelector('#feedback-movimiento');
    if (errorContainer) {
      errorContainer.classList.add('d-none');
      errorContainer.textContent = '';
    }
    
    // Cargar productos (async, no bloquea la apertura del modal)
    // ⚠️ v2.60: Aislamiento Gradual - cargarProductos ya maneja errores internamente
    cargarProductos();
    
    // Abrir modal usando Bootstrap 5
    // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
    const modalEl = d.querySelector('#modal-movimiento');
    if (modalEl && w.bootstrap && w.bootstrap.Modal) {
      const modal = w.bootstrap.Modal.getOrCreateInstance(modalEl);
      modalEl.addEventListener('shown.bs.modal', function focusFirstInput() {
        const firstInput = modalEl.querySelector('input:not([type="hidden"]), select, textarea');
        if (firstInput) {
          firstInput.focus();
        }
        modalEl.removeEventListener('shown.bs.modal', focusFirstInput);
      }, { once: true });
      modal.show();
    } else if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
      // Fallback: usar UIManager si Bootstrap no está disponible
      w.UIManager.handleModal('#modal-movimiento', 'show');
    }
  }

  /**
   * Guardar movimiento
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function guardarMovimiento() {
    const form = d.querySelector('#form-movimiento');
    if (!form) return;

    const formData = new FormData(form);
    const data = {
      producto: parseInt(formData.get('producto')) || null,
      tipo: formData.get('tipo'),
      cantidad: parseFloat(formData.get('cantidad')) || 0,
      origen_referencia: formData.get('origen_referencia') || '',
      observaciones: formData.get('observaciones') || ''
    };

    const modalEl = d.querySelector('#modal-movimiento');
    
    // ⚠️ Error Boundary v2.60: Guardar estado original del botón
    const btnGuardar = d.querySelector('#btn-guardar-movimiento');
    const btnOriginalText = btnGuardar?.innerHTML || '';
    const btnOriginalDisabled = btnGuardar?.disabled || false;
    
    // ⚠️ Error Boundary v2.60: Mostrar estado de loading
    if (btnGuardar) {
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    }

    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.inventarioAPI.movimientos.save(data);
    
    // ⚠️ Error Boundary v2.60: Restaurar estado del botón ANTES de procesar respuesta
    if (btnGuardar) {
      btnGuardar.disabled = btnOriginalDisabled;
      btnGuardar.innerHTML = btnOriginalText;
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok y delegar a UIManager
    if (!res.ok) {
      // ⚠️ Error Boundary: Delegar completamente a UIManager (aislamiento de presentación)
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[movimientos.page]', {
          modalSelector: '#modal-movimiento',
          errorContainerSelector: '#feedback-movimiento'
        });
      } else {
        // Fallback crítico: Si UIManager no está disponible, usar notifyError
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(res, '[movimientos.page]');
        }
      }
      // ⚠️ Error Boundary: Modal permanece abierto para errores 400 (UIManager lo maneja)
      return;
    }

    // ⚠️ Éxito: Solo cerrar modal si res.ok es true
    if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
      w.UIManager.handleModal('#modal-movimiento', 'hide');
    } else {
      if (modalEl) {
        // ⚠️ v2.60: Usar UIManager para cerrar modal
        if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          w.UIManager.handleModal('#modal-movimiento', 'hide');
        }
      }
    }

    if (w.SintelFeedback) {
      w.SintelFeedback.success('Movimiento registrado correctamente');
    }

    if (table) {
      table.replaceData();
    }
  }

  // Función para configurar eventos (reutilizable)
  function configurarEventos() {
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de operación
    
    // Asegurar que el módulo esté inicializado
    if (!w.InventarioMovimientosModule) {
      console.warn('[movimientos.page] InventarioMovimientosModule no está inicializado aún, inicializando...');
      w.InventarioMovimientosModule = {
        table: table,
        refresh: function() {
          if (table) {
            table.replaceData();
          }
        },
        abrirModalCrear: abrirModalCrear
      };
    }
    
    // Configurar botón "Nuevo Movimiento" - Intentar múltiples veces si no está disponible
    function configurarBotonNuevo() {
      const btnNuevo = d.querySelector('#btn-nuevo-movimiento');
      if (btnNuevo) {
        // Remover listeners anteriores si existen (evitar duplicados)
        const nuevoBtn = btnNuevo.cloneNode(true);
        btnNuevo.parentNode.replaceChild(nuevoBtn, btnNuevo);
        
        console.log('[movimientos.page] Botón "Registrar Movimiento" encontrado, agregando event listener');
        nuevoBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          console.log('[movimientos.page] Click en botón "Registrar Movimiento"');
          abrirModalCrear();
        });
        
        // También exponer globalmente para acceso directo (ya está en el módulo, pero por si acaso)
        if (w.InventarioMovimientosModule) {
          w.InventarioMovimientosModule.abrirModalCrear = abrirModalCrear;
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
          console.warn('[movimientos.page] Botón #btn-nuevo-movimiento no encontrado después de delay');
        }
      }, 500);
    }
    
    // Configurar formulario
    const form = d.querySelector('#form-movimiento');
    if (form) {
      // Remover listeners anteriores si existen (evitar duplicados)
      const nuevoForm = form.cloneNode(true);
      form.parentNode.replaceChild(nuevoForm, form);
      
      nuevoForm.addEventListener('submit', function(e) {
        e.preventDefault();
        guardarMovimiento();
      });
      console.log('[movimientos.page] Formulario configurado');
    } else {
      console.warn('[movimientos.page] Formulario #form-movimiento no encontrado');
    }
  }

  // Función para inicializar el módulo completo
  function inicializarModulo() {
    console.log('[movimientos.page] Inicializando módulo completo...');
    
    // Inicializar tabla
    table = initTable();
    
    // Exponer módulo globalmente ANTES de configurar eventos
    w.InventarioMovimientosModule = {
      table: table,
      refresh: function() {
        if (table) {
          table.replaceData();
        }
      },
      abrirModalCrear: abrirModalCrear,
      verDetalle: verDetalle
    };
    
    console.log('[movimientos.page] Módulo expuesto globalmente:', w.InventarioMovimientosModule);
    
    // Configurar eventos DESPUÉS de inicializar el módulo
    configurarEventos();
  }

  // Lazy Loading: Inicializar solo cuando el tab sea visible
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    const selectors = [
      TABLE_SELECTOR,
      '#pane-movimientos',
      '#tab-movimientos-content',
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
        console.log('[movimientos.page] Contenedor visible, inicializando tabla...');
        inicializarModulo();
      }, { once: true, timeout: 30000 });
    } else {
      console.warn('[movimientos.page] Selectores de contenedor no encontrados, usando fallback');
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', inicializarModulo);
      } else {
        inicializarModulo();
      }
    }
  } else {
    // Fallback si DOMUtils no está disponible
    console.warn('[movimientos.page] DOMUtils no disponible, inicializando inmediatamente');
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      
      inicializarModulo();
    }
    initFallback();
  }
  
  // También configurar eventos cuando el tab de movimientos se muestre (Bootstrap event)
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-bs-target') === '#pane-movimientos' || e.target.id === 'tab-movimientos')) {
      console.log('[movimientos.page] Tab de movimientos mostrado, verificando eventos...');
      // Asegurar que el módulo esté inicializado
      if (!w.InventarioMovimientosModule || !w.SintelInventarioTables || !w.SintelInventarioTables.movimientos) {
        console.log('[movimientos.page] Módulo no inicializado, inicializando desde evento shown.bs.tab...');
        inicializarModulo();
      } else {
        setTimeout(configurarEventos, 100);
      }
    }
  });

})(window, document);
