/**
 * ⚠️ DEPRECATED v2.61.3: Este archivo está DEPRECADO
 * 
 * ⚠️ MIGRACIÓN A FEATURE-SLICED ARCHITECTURE:
 * - La lógica CRUD ha sido migrada a módulos independientes en features/:
 *   * productos_list.js (Feature: READ, DELETE, verKardex)
 *   * productos_editor.js (Feature: CREATE, UPDATE)
 * 
 * ⚠️ USO ACTUAL:
 * - Este archivo NO debe ser cargado en nuevos templates
 * - Usar en su lugar: productos_list.js + productos_editor.js
 * - Este archivo se mantiene solo para compatibilidad con código legacy
 * 
 * ⚠️ ELIMINACIÓN DE LÓGICA DUPLICADA:
 * - Funciones CRUD eliminadas (editar, eliminar, verKardex, guardarProducto, abrirModalCrear, cargarCategorias)
 * - Solo se mantiene la estructura básica para evitar errores en código legacy
 * 
 * ⚠️ NOTA: Este archivo será eliminado en una futura versión
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

  /**
   * ⚠️ DEPRECATED v2.61.3: Inicialización de tabla delegada a productos_list.js
   * 
   * La inicialización de la tabla ahora se maneja en:
   * - productos_list.js (Feature: READ - Listado con Tabulator)
   */
  function initTable() {
    console.warn('[productos.page] initTable() está DEPRECADO. Use productos_list.js en su lugar.');
    
    // Intentar usar el nuevo módulo si está disponible
    if (w.ProductosList && typeof w.ProductosList.init === 'function') {
      w.ProductosList.init();
      if (w.ProductosList.getTable && typeof w.ProductosList.getTable === 'function') {
        table = w.ProductosList.getTable();
      }
      return table;
    }
    
    // Fallback legacy solo si el nuevo módulo no está disponible
    if (!w.TabulatorFactory) {
      console.error('[productos.page] TabulatorFactory no está disponible');
      return null;
    }

    const columns = getColumns();
    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, columns, {
      searchInputSelector: SEARCH_SELECTOR
    });

    // ⚠️ v2.61.3: Event delegation delegado a productos_list.js
    // Los eventos ahora se manejan en productos_list.js (initListEvents)

    return table;
  }

  /**
   * ⚠️ DEPRECATED v2.61.3: Funciones CRUD eliminadas
   * 
   * Las siguientes funciones han sido migradas a módulos independientes:
   * - editar() → productos_editor.js (Feature: UPDATE)
   * - eliminar() → productos_list.js (Feature: DELETE)
   * - verKardex() → productos_list.js (Feature: READ detail)
   * - guardarProducto() → productos_editor.js (Feature: CREATE/UPDATE)
   * - abrirModalCrear() → productos_editor.js (Feature: CREATE)
   * - cargarCategorias() → productos_editor.js (Feature: CREATE/UPDATE)
   * 
   * ⚠️ NOTA: Estas funciones se mantienen como stubs para compatibilidad con código legacy
   * que pueda estar llamando a window.InventarioProductosModule
   */
  
  // ⚠️ Stub functions para compatibilidad legacy
  async function editar(id) {
    console.warn('[productos.page] editar() está DEPRECADO. Use productos_editor.js en su lugar.');
    if (w.ProductosEditor && typeof w.ProductosEditor.init === 'function') {
      // Intentar usar el nuevo módulo si está disponible
      const offcanvasContainer = d.getElementById('offcanvas-container-inventario');
      if (offcanvasContainer && typeof htmx !== 'undefined') {
        await htmx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${id}`, {
          target: '#offcanvas-container-inventario',
          swap: 'innerHTML'
        });
        const offcanvasEl = d.getElementById('offcanvas-inventario');
        if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
          const instance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          instance.show();
        }
      }
    }
  }

  async function eliminar(id) {
    console.warn('[productos.page] eliminar() está DEPRECADO. Use productos_list.js en su lugar.');
    if (w.ProductosList && typeof w.ProductosList.eliminar === 'function') {
      await w.ProductosList.eliminar(id);
    }
  }

  async function verKardex(id) {
    console.warn('[productos.page] verKardex() está DEPRECADO. Use productos_list.js en su lugar.');
    if (w.ProductosList && typeof w.ProductosList.verKardex === 'function') {
      await w.ProductosList.verKardex(id);
    }
  }

  function abrirModalCrear() {
    console.warn('[productos.page] abrirModalCrear() está DEPRECADO. Use productos_editor.js en su lugar.');
    if (w.ProductosEditor && typeof w.ProductosEditor.init === 'function') {
      const offcanvasContainer = d.getElementById('offcanvas-container-inventario');
      if (offcanvasContainer && typeof htmx !== 'undefined') {
        htmx.ajax('GET', '/api/v1/inventario/productos/gestor-offcanvas/', {
          target: '#offcanvas-container-inventario',
          swap: 'innerHTML'
        }).then(() => {
          const offcanvasEl = d.getElementById('offcanvas-inventario');
          if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
            const instance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
            instance.show();
          }
        });
      }
    }
  }

  /**
   * ⚠️ DEPRECATED v2.61.3: configurarEventos() eliminado
   * 
   * Los eventos del formulario y botones ahora se manejan en:
   * - productos_editor.js (Feature: CREATE/UPDATE)
   * - productos_list.js (Feature: READ, DELETE)
   */
  function configurarEventos() {
    console.warn('[productos.page] configurarEventos() está DEPRECADO. Los eventos se manejan en productos_editor.js y productos_list.js');
    // Función vacía para compatibilidad legacy
  }

  /**
   * ⚠️ DEPRECATED v2.61.3: Inicialización delegada a módulos nuevos
   * 
   * La inicialización ahora se maneja en:
   * - productos_list.js (Feature: READ - Listado)
   * - productos_editor.js (Feature: CREATE/UPDATE)
   */
  function inicializarModulo() {
    console.warn('[productos.page] inicializarModulo() está DEPRECADO. Use productos_list.js y productos_editor.js en su lugar.');
    
    // Intentar usar el nuevo módulo si está disponible
    if (w.ProductosList && typeof w.ProductosList.init === 'function') {
      w.ProductosList.init();
      if (w.ProductosList.getTable && typeof w.ProductosList.getTable === 'function') {
        table = w.ProductosList.getTable();
      }
    } else {
      // Fallback legacy solo si el nuevo módulo no está disponible
      table = initTable();
    }
    
    // ⚠️ DEPRECATED v2.61.3: Exponer módulo globalmente solo para compatibilidad legacy
    // ⚠️ NOTA: Este módulo está deprecado. Use ProductosList y ProductosEditor en su lugar
    w.InventarioProductosModule = {
      table: table,
      refresh: function() {
        console.warn('[productos.page] refresh() está DEPRECADO. Use ProductosList.recargar() en su lugar.');
        if (w.ProductosList && typeof w.ProductosList.recargar === 'function') {
          w.ProductosList.recargar();
        } else if (table) {
          table.replaceData();
        }
      },
      editar: editar,
      eliminar: eliminar,
      verKardex: verKardex,
      abrirModalCrear: abrirModalCrear
    };
    
    // ⚠️ DEPRECATED: configurarEventos() ya no hace nada
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
