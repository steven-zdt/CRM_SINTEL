/**
 * Feature: Listado y Tabulator - Productos v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (CORE_API_BASE)
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Anti-Zombies: Previene instancias fantasma de Tabulator por recargas HTMX
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.ProductosEditor (definido en productos_editor.js) - Feature: Crear/Editar
 * 
 * CRUD:
 * - READ: Lista productos con Tabulator
 * - DELETE: Eliminación con validación de estado activo
 * - READ (detail): Ver Kardex de producto
 */
(function(w, d) {
    'use strict';

    const MOD = '[productos.list]';

    // Abre un offcanvas de forma segura, limpiando backdrops huerfanos primero.
    function mostrarOffcanvasSeguro(el) {
        if (!el || !w.bootstrap?.Offcanvas) return;
        d.querySelectorAll('.offcanvas-backdrop').forEach(function(b) { b.remove(); });
        d.body.classList.remove('overflow-hidden', 'modal-open');
        var prev = bootstrap.Offcanvas.getInstance(el);
        if (prev) prev.dispose();
        new bootstrap.Offcanvas(el).show();
    }
    const GRID_ID = '#grid-productos';
    const SEARCH_ID = '#search-producto';
    const API_URL = '/api/v1/inventario/productos/'; // ⚠️ v2.61.3: Core API Facade para CRUD
    const CORE_API_BASE = '/api/v1/inventario/productos'; // Core API Facade
    let table = null;
    let _eliminandoProducto = false; // Flag para prevenir rowClick durante eliminación

    // ⚠️ Anti-Zombies v3.5: Singleton global para instancias de Tabulator
    w.Sintel = w.Sintel || {};
    w.Sintel.Inventario = w.Sintel.Inventario || {};
    w.Sintel.Inventario.Tables = w.Sintel.Inventario.Tables || {};

    if (w.Sintel.Inventario.Tables.productos) {
        if (w.Sintel.Inventario.Tables.productos && typeof w.Sintel.Inventario.Tables.productos.destroy === 'function') {
            try {
                w.Sintel.Inventario.Tables.productos.destroy();
            } catch (error) {
                console.warn(`${MOD} Error al destruir instancia zombie:`, error);
            }
        }
    }

    /**
     * Formatear moneda usando Intl.NumberFormat
     * @param {number|string} value - Valor a formatear
     * @returns {string} Valor formateado
     */
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

    /**
     * Formatear badge de stock con alerta
     * @param {number} stockActual - Stock actual
     * @param {number} stockMinimo - Stock mínimo
     * @returns {string} HTML del badge
     */
    function formatearStock(stockActual, stockMinimo) {
        const val = parseFloat(stockActual) || 0;
        const min = parseFloat(stockMinimo) || 0;
        const color = val <= min ? 'bg-danger' : 'bg-success';
        return `<span class="badge ${color}">${val.toFixed(2)}</span>`;
    }

    /**
     * Definir columnas específicas del módulo
     * @returns {Array} Configuración de columnas Tabulator
     */
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
                title: "Nombre",
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
                width: 150
            },
            {
                title: "Stock Actual",
                field: "stock_actual",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    return formatearStock(rowData.stock_actual, rowData.stock_minimo);
                },
                width: 120,
                hozAlign: "center"
            },
            {
                title: "Stock Mínimo",
                field: "stock_minimo",
                formatter: function(cell) {
                    const val = parseFloat(cell.getValue()) || 0;
                    return val.toFixed(2);
                },
                width: 120,
                hozAlign: "center"
            },
            {
                title: "Costo",
                field: "costo_promedio",
                formatter: function(cell) {
                    return formatearMoneda(cell.getValue());
                },
                width: 120,
                hozAlign: "right"
            },
            {
                title: "Precio Venta",
                field: "precio_venta",
                formatter: function(cell) {
                    return formatearMoneda(cell.getValue());
                },
                width: 120,
                hozAlign: "right"
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
                            <button type="button" class="btn btn-outline-primary btn-edit-producto" data-id="${id}" title="Editar">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button type="button" class="btn btn-outline-info btn-ver-kardex" data-id="${id}" title="Ver Kardex">
                                <i class="bi bi-list-ul"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete-producto" data-id="${id}" title="Eliminar">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    `;
                },
                width: 180,
                headerSort: false,
                resizable: false,
                hozAlign: "center",
                responsive: 0,
                frozen: true
            }
        ];
    }

    /**
     * Inicializar tabla de productos
     * @returns {Object|null} Instancia de Tabulator o null
     */
    function initTable() {
        const gridEl = d.querySelector(GRID_ID);
        if (!gridEl) {
            console.warn(`${MOD} Contenedor ${GRID_ID} no encontrado`);
            return null;
        }

        // ⚠️ Verificar que TabulatorFactory esté disponible
        if (!w.TabulatorFactory || typeof w.TabulatorFactory.create !== 'function') {
            console.error(`${MOD} TabulatorFactory no está disponible`);
            return null;
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
            placeholder: "No hay productos registrados",
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
        w.Sintel.Inventario.Tables.productos = table;

        // Event Delegation para acciones del Grid
        initListEvents();

        return table;
    }

    /**
     * Ver Kardex de producto
     * ⚠️ CRUD: READ (detail) - Historial de movimientos
     * @param {string|number} productoId - ID del producto
     */
    async function verKardex(productoId) {
        if (!productoId) {
            console.warn(`${MOD} ID de producto no proporcionado`);
            return;
        }

        try {
            // ⚠️ API-First: Obtener información del producto y kardex
            let productoRes, kardexRes;

            if (w.http && typeof w.http === 'function') {
                productoRes = await w.http('GET', `${CORE_API_BASE}/${productoId}/`);
                kardexRes = await w.http('GET', `${CORE_API_BASE}/${productoId}/kardex/`);
            } else if (w.Sintel?.Inventario?.API?.productos) {
                productoRes = await w.Sintel.Inventario.API.productos.get(productoId);
                kardexRes = await w.Sintel.Inventario.API.productos.kardex(productoId);
            } else {
                console.error(`${MOD} API no disponible`);
                return;
            }

            // ⚠️ Aislamiento Gradual - Solo verificar ok
            if (!productoRes.ok || !productoRes.data) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(productoRes, MOD);
                }
                return;
            }

            if (!kardexRes.ok) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(kardexRes, MOD);
                }
                return;
            }

            const producto = productoRes.data;
            const movimientos = Array.isArray(kardexRes.data) ? kardexRes.data : (kardexRes.data.results || []);

            // Mostrar información del producto
            const infoEl = d.querySelector('#kardex-producto-info');
            if (infoEl) {
                const stockActual = parseFloat(producto.stock_actual || 0);
                const stockMinimo = parseFloat(producto.stock_minimo || 0);
                const stockColor = stockActual <= stockMinimo ? 'bg-danger' : 'bg-success';
                
                infoEl.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <strong>Código:</strong> ${producto.codigo || '-'}<br>
                            <strong>Nombre:</strong> ${producto.nombre || '-'}
                        </div>
                        <div class="col-md-6">
                            <strong>Stock Actual:</strong> <span class="badge ${stockColor}">${stockActual.toFixed(2)}</span><br>
                            <strong>Stock Mínimo:</strong> ${stockMinimo.toFixed(2)}
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

            // Abrir modal de kardex
            const modalEl = d.querySelector('#modal-kardex');
            if (modalEl && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            } else {
                console.warn(`${MOD} Modal #modal-kardex no encontrado o Bootstrap no disponible`);
            }

        } catch (error) {
            console.error(`${MOD} Error al obtener kardex:`, error);
            if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                w.SintelFeedback.error('Error al cargar el kardex del producto');
            }
        }
    }

    /**
     * Event Delegation para acciones del Grid
     */
    function initListEvents() {
        const gridElement = d.querySelector(GRID_ID);
        if (!gridElement) {
            console.warn(`${MOD} Elemento ${GRID_ID} no encontrado para eventos`);
            return;
        }

        // ⚠️ Event Delegation: Escuchar clics en el contenedor del grid
        gridElement.addEventListener('click', async (e) => {
            // Botón Editar
            const btnEdit = e.target.closest('.btn-edit-producto');
            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnEdit.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón sin data-id`);
                    return;
                }

                // ⚠️ Loading state
                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // ⚠️ v2.61.3: Usar Core API Facade para HTMX
                    const offcanvasContainer = d.getElementById('offcanvas-container-inventario');
                    if (!offcanvasContainer) {
                        console.warn(`${MOD} Contenedor #offcanvas-container-inventario no encontrado`);
                        return;
                    }

                    await htmx.ajax('GET', `${CORE_API_BASE}/gestor-offcanvas/?id=${id}`, {
                        target: '#offcanvas-container-inventario',
                        swap: 'innerHTML'
                    });

                    await new Promise(resolve => setTimeout(resolve, 100));

                    const offcanvasEl = d.getElementById('offcanvas-inventario');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        mostrarOffcanvasSeguro(offcanvasEl);
                    }
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al cargar el formulario de producto');
                    }
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Ver Kardex
            const btnKardex = e.target.closest('.btn-ver-kardex');
            if (btnKardex) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnKardex.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón kardex sin data-id`);
                    return;
                }

                const originalHTML = btnKardex.innerHTML;
                btnKardex.disabled = true;
                btnKardex.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    await verKardex(id);
                } catch (error) {
                    console.error(`${MOD} Error al ver kardex:`, error);
                } finally {
                    btnKardex.disabled = false;
                    btnKardex.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-producto');
            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnDelete.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón eliminar sin data-id`);
                    return;
                }

                // ⚠️ Validación: Obtener datos del producto para validar estado
                let productoRes;
                if (w.http && typeof w.http === 'function') {
                    productoRes = await w.http('GET', `${CORE_API_BASE}/${id}/`);
                } else if (w.Sintel?.Inventario?.API?.productos && typeof w.Sintel.Inventario.API.productos.get === 'function') {
                    productoRes = await w.Sintel.Inventario.API.productos.get(id);
                } else {
                    console.error(`${MOD} API no disponible`);
                    return;
                }

                if (!productoRes.ok || !productoRes.data) {
                    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                        w.UIManager.handleError(productoRes, MOD);
                    }
                    return;
                }

                const producto = productoRes.data;

                // Validar que el producto no esté activo
                if (producto.activo) {
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('El producto está activo. Desactívelo primero.');
                    }
                    return;
                }

                // Construir mensaje de confirmación
                let mensajeConfirmacion = '¿Está seguro de eliminar este producto?';
                const stock = parseFloat(producto.stock_actual || 0);
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

                // ⚠️ v2.61.3: Activar flag para prevenir rowClick durante eliminación
                _eliminandoProducto = true;

                // ⚠️ Loading state
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // ⚠️ v2.61.3: Usar Core API Facade
                    let deleteRes;
                    if (w.http && typeof w.http === 'function') {
                        deleteRes = await w.http('DELETE', `${CORE_API_BASE}/${id}/`);
                    } else if (w.Sintel?.Inventario?.API?.productos && typeof w.Sintel.Inventario.API.productos.delete === 'function') {
                        deleteRes = await w.Sintel.Inventario.API.productos.delete(id);
                    } else {
                        console.error(`${MOD} API de eliminación no disponible`);
                        return;
                    }

                    // ⚠️ v2.61.3: Aislamiento Gradual - Solo verificar ok
                    if (!deleteRes.ok) {
                        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                            w.UIManager.handleError(deleteRes, MOD);
                        }
                        return;
                    }

                    // ⚠️ v2.61.3: Cerrar cualquier offcanvas abierto
                    const offcanvasProducto = d.getElementById('offcanvas-inventario');
                    if (offcanvasProducto && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const instance = bootstrap.Offcanvas.getInstance(offcanvasProducto);
                        if (instance) {
                            instance.hide();
                        }
                    }

                    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                        w.SintelFeedback.success('Producto eliminado correctamente. Stock y kardex eliminados.');
                    }

                    // Recargar tabla
                    if (table) {
                        table.replaceData();
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar producto:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al eliminar el producto');
                    }
                } finally {
                    // Restaurar estado del botón y flag
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                    _eliminandoProducto = false;
                }
                return;
            }
        });

        // ⚠️ Event Delegation: Clic en fila para editar (solo si no se está eliminando)
        if (table) {
            table.on('rowClick', async function(e, row) {
                // ⚠️ v2.61.3: Prevenir rowClick si se está eliminando un producto
                if (_eliminandoProducto) {
                    console.log(`${MOD} rowClick ignorado: eliminación en proceso`);
                    return;
                }

                // Evitar abrir si se hizo click en un botón
                const target = e.target || e.originalEvent?.target;
                if (target && target.closest && target.closest('button')) {
                    return;
                }

                const rowData = row.getData();
                const id = rowData.id;
                if (!id) return;

                try {
                    // ⚠️ v2.61.3: Usar Core API Facade para HTMX
                    await htmx.ajax('GET', `${CORE_API_BASE}/gestor-offcanvas/?id=${id}`, {
                        target: '#offcanvas-container-inventario',
                        swap: 'innerHTML'
                    });

                    await new Promise(resolve => setTimeout(resolve, 100));

                    const offcanvasEl = d.getElementById('offcanvas-inventario');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        mostrarOffcanvasSeguro(offcanvasEl);
                    }
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas desde rowClick:`, error);
                }
            });
        }
    }

    /**
     * Recargar tabla
     */
    function recargar() {
        if (table) {
            table.replaceData();
        }
    }

    /**
     * Inicializar módulo de listado de productos
     * ⚠️ Lazy Loading: Solo se inicializa cuando el tab está visible
     */
    function init() {
        console.log(`${MOD} Inicializando módulo de listado...`);
        
        const gridEl = d.querySelector(GRID_ID);
        if (!gridEl) {
            console.warn(`${MOD} Contenedor ${GRID_ID} no encontrado. El módulo se inicializará cuando el tab esté visible.`);
            return;
        }

        initTable();
    }

    // ⚠️ Exposición global del módulo v3.5
    w.Sintel.Inventario.Productos = w.Sintel.Inventario.Productos || {};
    w.Sintel.Inventario.Productos.List = {
        init: init,
        recargar: recargar,
        verKardex: verKardex,
        getTable: () => table
    };

    // Deprecated fallbacks
    w.ProductosList = w.Sintel.Inventario.Productos.List;

    // ⚠️ Auto-inicialización si el DOM está listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        // Si el tab de productos está visible, inicializar inmediatamente
        const tabProductos = d.querySelector('#tab-inventario');
        if (tabProductos && tabProductos.classList.contains('active')) {
            init();
        } else {
            // Lazy loading: inicializar cuando el tab se muestre
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce('#pane-existencias', init);
            } else {
                // Fallback: escuchar evento de tab
                const tabButton = d.querySelector('#tab-existencias');
                if (tabButton) {
                    tabButton.addEventListener('shown.bs.tab', function() {
                        if (!table) {
                            init();
                        }
                    });
                }
            }
        }
    }

})(window, document);
