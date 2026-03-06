/**
 * Módulo Productos v2.60 - Tabulator Implementation (Migrado desde DataTables)
 * ⚠️ STANDALONE MODULE: Módulo completamente independiente
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ ARQUITECTURA STANDALONE:
 * - Este módulo NO depende de otros módulos del inventario (categorías, servicios, activos)
 * - Otros módulos pueden usar este módulo, pero este NO los usa
 * - Solo expone su API global: window.InventarioProductosModule
 * - Al eliminar un producto, se eliminan automáticamente:
 *   * Todo el stock asociado (es parte del registro)
 *   * Todos los movimientos de inventario (Kardex) - CASCADE
 */
(function(w, d) {
  'use strict';

  const TABLE_SELECTOR = '#grid-productos';
  const SEARCH_SELECTOR = '#search-producto';
  const API_URL = '/api/v1/inventario/productos/';
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
        title: "Código",
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
        title: "Stock Actual",
        field: "stock_actual",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          const data = cell.getRow().getData();
          const min = parseFloat(data.stock_minimo) || 0;
          const color = val <= min ? "bg-danger" : "bg-success";
          return `<span class="badge ${color}">${val.toFixed(2)}</span>`;
        }
      },
      {
        title: "Stock Mínimo",
        field: "stock_minimo",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return val.toFixed(2);
        }
      },
      {
        title: "Costo",
        field: "costo_promedio",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(val);
        }
      },
      {
        title: "Precio Venta",
        field: "precio_venta",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(val);
        }
      },
      {
        title: "Estado",
        field: "activo",
        formatter: w.TabulatorFactory.formatters.statusBadge,
        headerSort: false
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id = rowData.id;
          
          return `
            <div class="btn-group btn-group-sm" role="group">
              <button type="button" class="btn btn-outline-primary" data-action="editar" data-id="${id}" title="Editar Producto">
                <i class="fas fa-edit"></i>
              </button>
              <button type="button" class="btn btn-outline-info" data-action="ver-kardex" data-id="${id}" title="Ver Kardex">
                <i class="fas fa-list-alt"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" data-action="eliminar" data-id="${id}" title="Eliminar Producto">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          `;
        },
        headerSort: false,
        hozAlign: "center",
        width: 180
      }
    ];
  }

  // Inicializar tabla
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error('[productos.page] TabulatorFactory no está disponible');
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
            console.warn('[productos.page] ID no válido:', id);
            return;
          }
          
          if (!w.InventarioProductosModule) {
            console.error('[productos.page] InventarioProductosModule no está disponible');
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
              w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Módulo no disponible' } }, '[productos.page]');
            }
            return;
          }
          
          switch (action) {
            case 'editar':
              w.InventarioProductosModule.editar(id);
              break;
            case 'eliminar':
              w.InventarioProductosModule.eliminar(id);
              break;
            case 'ver-kardex':
              w.InventarioProductosModule.verKardex(id);
              break;
            default:
              console.warn('[productos.page] Acción no reconocida:', action);
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
  async function editar(id) {
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.inventarioAPI.productos.get(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok || !res.data) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[productos.page]');
      }
      return;
    }
    
    const data = res.data;
    
    // Llenar formulario
    d.querySelector('#producto-id').value = data.id || '';
    d.querySelector('#producto-codigo').value = data.codigo || '';
    d.querySelector('#producto-nombre').value = data.nombre || '';
    d.querySelector('#producto-precio').value = data.precio_venta || '';
    d.querySelector('#producto-stock-min').value = data.stock_minimo || 0;
    d.querySelector('#producto-activo').checked = data.activo !== false;
    
    // Cargar categorías y seleccionar la del producto
    await cargarCategorias(data.categoria);
    
    // Abrir modal
    const modalEl = d.querySelector('#modal-producto');
    if (modalEl) {
      // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
      if (w.bootstrap && w.bootstrap.Modal) {
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
        w.UIManager.handleModal('#modal-producto', 'show');
      }
      
      // Actualizar título
      const title = modalEl.querySelector('.modal-title');
      if (title) title.textContent = 'Editar Producto';
    }
  }

  /**
   * Eliminar producto
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function eliminar(id) {
    // ⚠️ REGLA DE SEGURIDAD DE ELIMINACIÓN: Validar estado activo antes de proceder
    // ⚠️ STANDALONE MODULE: Este módulo es independiente
    // ⚠️ NOTA: Al eliminar un producto, se eliminan automáticamente su stock y todos sus movimientos de kardex
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    // Obtener datos del producto para validar estado y mostrar información
    const resGet = await w.inventarioAPI.productos.get(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!resGet.ok || !resGet.data) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(resGet, '[productos.page]');
      }
      return;
    }
    
    const data = resGet.data;
    
    // Validar que el producto no esté activo
    if (data.activo) {
      if (w.SintelFeedback) {
        w.SintelFeedback.error('El ítem está activo. Desactívelo primero.');
      }
      return;
    }
    
    // Construir mensaje de confirmación con información del stock
    let mensajeConfirmacion = '¿Está seguro de eliminar este producto?';
    const stock = parseFloat(data.stock_actual || 0);
    if (stock > 0) {
      mensajeConfirmacion += `\n\nEste producto tiene ${stock} unidades en stock.`;
    }
    mensajeConfirmacion += '\n\n⚠️ ADVERTENCIA: Esta acción eliminará:';
    mensajeConfirmacion += '\n- El producto';
    mensajeConfirmacion += '\n- Todo el stock asociado';
    mensajeConfirmacion += '\n- Todo el historial de movimientos (Kardex)';
    mensajeConfirmacion += '\n\nEsta acción es irreversible.';
    
    if (!confirm(mensajeConfirmacion)) {
      return;
    }

    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.inventarioAPI.productos.delete(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[productos.page]');
      }
      return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Producto eliminado correctamente. Stock y kardex eliminados.');
    }
    
    if (table) {
      table.replaceData();
    }
  }

  /**
   * Ver kardex de producto
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function verKardex(id) {
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    // Obtener información del producto
    const productoRes = await w.inventarioAPI.productos.get(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!productoRes.ok || !productoRes.data) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(productoRes, '[productos.page]');
      }
      return;
    }
    
    const producto = productoRes.data;
    
    // Obtener kardex
    const kardexRes = await w.inventarioAPI.productos.kardex(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!kardexRes.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(kardexRes, '[productos.page]');
      }
      return;
    }
    
    const movimientos = Array.isArray(kardexRes.data) ? kardexRes.data : (kardexRes.data.results || []);
    
    // Mostrar información del producto
    const infoEl = d.querySelector('#kardex-producto-info');
    if (infoEl) {
      infoEl.innerHTML = `
        <div class="row">
          <div class="col-md-6">
            <strong>Código:</strong> ${producto.codigo || '-'}<br>
            <strong>Nombre:</strong> ${producto.nombre || '-'}
          </div>
          <div class="col-md-6">
            <strong>Stock Actual:</strong> <span class="badge ${parseFloat(producto.stock_actual || 0) <= parseFloat(producto.stock_minimo || 0) ? 'bg-danger' : 'bg-success'}">${parseFloat(producto.stock_actual || 0).toFixed(2)}</span><br>
            <strong>Stock Mínimo:</strong> ${parseFloat(producto.stock_minimo || 0).toFixed(2)}
          </div>
        </div>
      `;
    }
    
    // Llenar tabla de movimientos
    const tbody = d.querySelector('#table-kardex tbody');
    if (tbody) {
      if (movimientos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No hay movimientos registrados</td></tr>';
      } else {
        tbody.innerHTML = movimientos.map(mov => {
          const fecha = mov.created_at ? new Date(mov.created_at).toLocaleString('es-CO') : '-';
          const tipo = mov.tipo_display || mov.tipo || '-';
          const cantidad = parseFloat(mov.cantidad || 0).toFixed(3);
          const referencia = mov.origen_referencia || mov.cliente_referencia || '-';
          const observaciones = mov.observaciones || '-';
          const tipoColor = (tipo.includes('ENTRADA') || tipo.includes('entrada')) ? 'success' : 'danger';
          
          return `
            <tr>
              <td>${fecha}</td>
              <td><span class="badge bg-${tipoColor}">${tipo}</span></td>
              <td class="text-end">${cantidad}</td>
              <td>${referencia}</td>
              <td>${observaciones}</td>
            </tr>
          `;
        }).join('');
      }
    }
    
    // Abrir modal
    const modalEl = d.querySelector('#modal-kardex');
    if (modalEl) {
      // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
      if (w.bootstrap && w.bootstrap.Modal) {
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
        w.UIManager.handleModal('#modal-producto', 'show');
      }
    }
  }

  /**
   * Cargar categorías
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function cargarCategorias(categoriaSeleccionada = null) {
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.inventarioAPI.categorias.list();
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok || !res.data) {
      // ⚠️ v2.60: Delegar a UIManager para mostrar error (pero no bloquear)
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(res, '[productos.page]');
      }
      return;
    }
    
    const categorias = Array.isArray(res.data) ? res.data : (res.data.results || []);
    const select = d.querySelector('#producto-categoria');
    if (!select) return;
    
    // Limpiar opciones
    select.innerHTML = '<option value="">Seleccione...</option>';
    
    // Agregar categorías
    categorias.forEach(cat => {
      if (cat.aplicacion === 'PRODUCTO' || cat.aplicacion === 'TODO') {
        const option = d.createElement('option');
        option.value = cat.id;
        option.textContent = cat.nombre;
        if (categoriaSeleccionada && cat.id === categoriaSeleccionada) {
          option.selected = true;
        }
        select.appendChild(option);
      }
    });
  }

  /**
   * Guardar producto
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function guardarProducto() {
    const form = d.querySelector('#form-producto');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = {
      codigo: formData.get('codigo'),
      nombre: formData.get('nombre'),
      categoria: parseInt(formData.get('categoria')) || null,
      precio_venta: parseFloat(formData.get('precio_venta')) || 0,
      stock_minimo: parseFloat(formData.get('stock_minimo')) || 0,
      activo: d.querySelector('#producto-activo').checked
    };
    
    const id = d.querySelector('#producto-id').value;
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    let res;
    if (id) {
      res = await w.inventarioAPI.productos.update(id, data);
    } else {
      res = await w.inventarioAPI.productos.save(data);
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok y delegar a UIManager
    if (!res.ok) {
      // ⚠️ Error Boundary: Delegar completamente a UIManager (aislamiento de presentación)
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[productos.page]', {
          modalSelector: '#modal-producto',
          errorContainerSelector: '#feedback-producto'
        });
      } else {
        // Fallback crítico: Si UIManager no está disponible, usar notifyError
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(res, '[productos.page]');
        }
      }
      // ⚠️ Error Boundary: Modal permanece abierto para errores 400 (UIManager lo maneja)
      return;
    }
    
    // Éxito: cerrar modal y mostrar notificación
    if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
      w.UIManager.handleModal('#modal-producto', 'hide');
    } else {
      const modalEl = d.querySelector('#modal-producto');
      if (modalEl) {
        // ⚠️ v2.60: Usar UIManager para cerrar modal
        if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
          w.UIManager.handleModal('#modal-producto', 'hide');
        }
      }
    }
    
    if (w.SintelFeedback) {
      w.SintelFeedback.success(id ? 'Producto actualizado correctamente' : 'Producto creado correctamente');
    }
    
    // Recargar tabla
    if (table) {
      table.replaceData();
    }
  }

  function abrirModalCrear() {
    // Verificar que Bootstrap esté disponible
    if (typeof bootstrap === 'undefined') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Bootstrap no está cargado' } }, '[productos.page]');
      }
      return;
    }
    
    // Buscar modal
    const modalEl = d.querySelector('#modal-producto');
    if (!modalEl) {
      console.error('[productos.page] Modal #modal-producto no encontrado en el DOM');
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Modal no encontrado. Verifique que modals_productos.html esté incluido.' } }, '[productos.page]');
      }
      return;
    }
    
    // Limpiar formulario
    const form = d.querySelector('#form-producto');
    if (form) {
      form.reset();
    }
    
    // Limpiar campos específicos
    const idField = d.querySelector('#producto-id');
    if (idField) idField.value = '';
    
    const activoField = d.querySelector('#producto-activo');
    if (activoField) activoField.checked = true;
    
    // Cargar categorías (async, no bloquea la apertura del modal)
    cargarCategorias().catch(err => {
      console.error('[productos.page] Error al cargar categorías:', err);
    });
    
    // Abrir modal usando Bootstrap 5
    // ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verificar disponibilidad
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    
    // Actualizar título antes de mostrar
    const title = modalEl.querySelector('.modal-title');
    if (title) {
      title.textContent = 'Nuevo Producto';
    }
    
    modal.show();
      if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al abrir el modal: ' + error.message);
      }
    }
  }

  // Función para configurar eventos (reutilizable)
  function configurarEventos() {
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de operación
    
    // Configurar botón "Nuevo"
    const btnNuevo = d.querySelector('#btn-nuevo-producto');
    if (btnNuevo) {
      // Remover listeners anteriores si existen (evitar duplicados)
      const nuevoBtn = btnNuevo.cloneNode(true);
      btnNuevo.parentNode.replaceChild(nuevoBtn, btnNuevo);
      
      nuevoBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        abrirModalCrear();
      });
    }
    
    // Configurar formulario
    const form = d.querySelector('#form-producto');
    if (form) {
      // Remover listeners anteriores si existen (evitar duplicados)
      const nuevoForm = form.cloneNode(true);
      form.parentNode.replaceChild(nuevoForm, form);
      
      nuevoForm.addEventListener('submit', function(e) {
        e.preventDefault();
        guardarProducto();
      });
    }
  }

  // Función para inicializar el módulo completo
  function inicializarModulo() {
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de operación
    
    // Inicializar tabla
    table = initTable();
    
    // Exponer módulo globalmente ANTES de configurar eventos
    w.InventarioProductosModule = {
      table: table,
      refresh: function() {
        if (table) {
          table.replaceData();
        }
      },
      editar: editar,
      eliminar: eliminar,
      verKardex: verKardex,
      abrirModalCrear: abrirModalCrear
    };
    
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de éxito
    
    // Configurar eventos DESPUÉS de inicializar el módulo
    configurarEventos();
  }

  // Lazy Loading: Inicializar solo cuando el tab sea visible
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce('#subtab-productos', function() {
      inicializarModulo();
    });
  } else {
    // Fallback si DOMUtils no está disponible
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      
      inicializarModulo();
    }
    initFallback();
  }
  
  // También configurar eventos cuando el tab de productos se muestre (Bootstrap event)
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && e.target.getAttribute('data-bs-target') === '#subtab-productos') {
      // Asegurar que el módulo esté inicializado
      if (!w.InventarioProductosModule) {
        inicializarModulo();
      } else {
        setTimeout(configurarEventos, 100);
      }
    }
  });

})(window, document);
