/**
 * Feature: Listado y Tabulator - Inventario v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Anti-Zombies: Previene instancias fantasma de Tabulator por recargas HTMX
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 */
(function(w, d) {
    'use strict';

    const MOD = '[inventario.list]';

    function mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
    }
    const CORE_API_BASE = '/api/v1/inventario/productos'; // Core API Facade
    let table = null;
    let _eliminandoProducto = false; // ⚠️ v2.61.3: Flag para prevenir rowClick durante eliminación

    // ⚠️ Anti-Zombies v2.60: Singleton global para instancias de Tabulator
    if (window.SintelInventarioTables) {
        Object.values(window.SintelInventarioTables).forEach(tb => {
            if (tb && typeof tb.destroy === 'function') {
                try {
                    tb.destroy();
                } catch (error) {
                    console.warn(`${MOD} Error al destruir instancia zombie:`, error);
                }
            }
        });
    }
    window.SintelInventarioTables = {};

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

    // Formateador de número con decimales
    function formatearNumero(value, decimals = 3) {
        if (value === null || value === undefined || value === '') return '0,00';
        const num = parseFloat(value);
        if (isNaN(num)) return '0,00';
        return new Intl.NumberFormat('es-CO', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(num);
    }

    // Definir columnas específicas del módulo
    function getColumns() {
        return [
            {
                title: "SKU",
                field: "codigo",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
                    return cell.getValue() || '---';
                },
                width: 120,
                headerFilter: "input"
            },
            {
                title: "Producto",
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
                title: "Cantidad Actual",
                field: "stock_actual",
                formatter: function(cell) {
                    const value = cell.getValue();
                    const rowData = cell.getRow().getData();
                    const unidad = rowData.unidad || 'UND';
                    return formatearNumero(value, 3) + ' ' + unidad;
                },
                width: 140,
                hozAlign: "right",
                sorter: "number"
            },
            {
                title: "Stock Mínimo",
                field: "stock_minimo",
                formatter: function(cell) {
                    const value = cell.getValue();
                    const rowData = cell.getRow().getData();
                    const alertaStock = rowData.alerta_stock || false;
                    const unidad = rowData.unidad || 'UND';
                    const valorFormateado = formatearNumero(value, 3) + ' ' + unidad;
                    
                    // ⚠️ Formatter de color si hay alerta
                    if (alertaStock) {
                        return `<span class="badge bg-danger">${valorFormateado}</span>`;
                    }
                    return valorFormateado;
                },
                width: 140,
                hozAlign: "right",
                sorter: "number"
            },
            {
                title: "Precio Venta",
                field: "precio_venta",
                formatter: function(cell) {
                    const value = cell.getValue();
                    if (value === null || value === undefined || value === '') return '$ 0,00';
                    return formatearMoneda(value);
                },
                width: 140,
                hozAlign: "right",
                sorter: "number"
            },
            {
                title: "Precio Promedio",
                field: "costo_promedio",
                formatter: function(cell) {
                    const value = cell.getValue();
                    if (value === null || value === undefined || value === '') return '$ 0,00';
                    return formatearMoneda(value);
                },
                width: 140,
                hozAlign: "right",
                sorter: "number"
            },
            {
                title: "Valor Inventario",
                field: "valor_inventario",
                formatter: function(cell) {
                    const value = cell.getValue();
                    if (value === null || value === undefined || value === '') return '$ 0,00';
                    return formatearMoneda(value);
                },
                width: 150,
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
                            <button type="button" class="btn btn-outline-primary btn-edit-producto" data-id="${id}" title="Editar">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button type="button" class="btn btn-outline-success btn-ajuste-producto" data-id="${id}" title="Ajustar Stock">
                                <i class="bi bi-arrow-left-right"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete-producto" data-id="${id}" title="Eliminar">
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
     * Inicializar tabla de productos
     */
    function initTable() {
        const gridEl = d.querySelector('#grid-productos');
        if (!gridEl) {
            console.warn(`${MOD} Contenedor #grid-productos no encontrado`);
            return;
        }

        // ⚠️ Anti-Zombies: Destruir instancia previa si existe
        if (window.SintelInventarioTables.main) {
            try {
                window.SintelInventarioTables.main.destroy();
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
            searchInputSelector: '#search-producto',
            pagination: true,
            paginationSize: 10,
            paginationSizeSelector: [10, 25, 50, 100],
            layout: "fitDataStretch",
            responsiveLayout: true,
            responsiveLayoutCollapseStartOpen: false,
            placeholder: "No hay productos registrados",
            locale: "es",
            langs: {
                es: {
                    columns: {
                        name: "Nombre",
                        title: "Título"
                    },
                    data: {
                        loading: "Cargando",
                        error: "Error"
                    },
                    pagination: {
                        page_size: "Tamaño de página",
                        page_title: "Mostrar página",
                        first: "Primera",
                        first_title: "Primera página",
                        last: "Última",
                        last_title: "Última página",
                        prev: "Anterior",
                        prev_title: "Página anterior",
                        next: "Siguiente",
                        next_title: "Página siguiente",
                        all: "Todos",
                        counter: {
                            showing: "Mostrando",
                            of: "de",
                            results: "resultados",
                            results: "resultados"
                        }
                    }
                }
            }
        };

        // Crear tabla usando TabulatorFactory
        table = w.TabulatorFactory.create(
            '#grid-productos',
            '/api/v1/inventario/productos/', // ⚠️ v2.61.3: Core API Facade
            getColumns(),
            tableConfig
        );

        // Guardar instancia en singleton global
        window.SintelInventarioTables.main = table;

        // ⚠️ Event Delegation: Manejar clics en botones de acción
        initListEvents();
    }

    /**
     * Inicializar eventos de la lista (Event Delegation)
     */
    function initListEvents() {
        const gridEl = d.querySelector('#grid-productos');
        if (!gridEl) return;

        // Event Delegation para botones de acción
        gridEl.addEventListener('click', async function(e) {
            const btn = e.target.closest('button');
            if (!btn) return;

            // Botón Editar
            if (btn.classList.contains('btn-edit-producto')) {
                e.preventDefault();
                const id = btn.getAttribute('data-id');
                if (!id) return;

                // ⚠️ v2.61.3: Usar Core API Facade para gestor-offcanvas
                await htmx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${id}`, {
                    target: '#offcanvas-container-inventario',
                    swap: 'innerHTML'
                });

                const offcanvasEl = d.getElementById('offcanvas-inventario');
                if (offcanvasEl) {
                    mostrarOffcanvasSeguro(offcanvasEl);
                }
                return;
            }

            // Botón Ajustar Stock
            if (btn.classList.contains('btn-ajuste-producto')) {
                e.preventDefault();
                const id = btn.getAttribute('data-id');
                if (!id) return;

                // ⚠️ v2.61.3: Usar Core API Facade para gestor-offcanvas (ajuste)
                await htmx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${id}&tipo=ajuste`, {
                    target: '#offcanvas-container-inventario',
                    swap: 'innerHTML'
                });

                const offcanvasEl = d.getElementById('offcanvas-inventario');
                if (offcanvasEl) {
                    mostrarOffcanvasSeguro(offcanvasEl);
                }
                return;
            }

            // Botón Eliminar
            if (btn.classList.contains('btn-delete-producto')) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btn.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón eliminar sin data-id`);
                    return;
                }

                // ⚠️ v2.61.3: Validación: Obtener datos del producto para validar estado
                let productoRes;
                if (w.http && typeof w.http === 'function') {
                    productoRes = await w.http('GET', `${CORE_API_BASE}/${id}/`);
                } else if (w.inventarioAPI && w.inventarioAPI.productos && typeof w.inventarioAPI.productos.get === 'function') {
                    productoRes = await w.inventarioAPI.productos.get(id);
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
                const originalHTML = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // ⚠️ v2.61.3: Usar Core API Facade
                    let deleteRes;
                    if (w.http && typeof w.http === 'function') {
                        deleteRes = await w.http('DELETE', `${CORE_API_BASE}/${id}/`);
                    } else if (w.inventarioAPI && w.inventarioAPI.productos && typeof w.inventarioAPI.productos.delete === 'function') {
                        deleteRes = await w.inventarioAPI.productos.delete(id);
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
                    btn.disabled = false;
                    btn.innerHTML = originalHTML;
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

                const data = row.getData();
                if (!data || !data.id) return;

                try {
                    // ⚠️ v2.61.3: Usar Core API Facade para gestor-offcanvas
                    await htmx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${data.id}`, {
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
     * Recargar tabla de productos
     * ⚠️ v2.61.3: Función expuesta para recargar la tabla después de crear/actualizar/eliminar
     */
    function recargar() {
        if (table && typeof table.replaceData === 'function') {
            console.log(`${MOD} Recargando tabla de productos...`);
            table.replaceData();
        } else if (window.SintelInventarioTables.main && typeof window.SintelInventarioTables.main.replaceData === 'function') {
            console.log(`${MOD} Recargando tabla de productos (vía singleton)...`);
            window.SintelInventarioTables.main.replaceData();
        } else {
            console.warn(`${MOD} No se puede recargar: tabla no inicializada`);
            // Intentar inicializar si no está inicializada
            init();
        }
    }

    /**
     * Escuchar evento de actualización para refrescar tabla
     */
    d.addEventListener('inventarioActualizado', function() {
        recargar();
    });

    // ⚠️ v2.61.3: Exponer módulo ProductosList para compatibilidad con productos_editor.js
    if (!w.ProductosList) {
        w.ProductosList = {
            init: init,
            recargar: recargar,
            getTable: () => table || window.SintelInventarioTables.main
        };
    }

    /**
     * ⚠️ v2.60: Inicialización con lazy loading usando DOMUtils.onVisibleOnce
     * Solo se ejecuta cuando el tab/contenedor se vuelve visible
     */
    function init() {
        // Verificar que el contenedor exista
        const container = d.querySelector('#grid-productos');
        if (!container) {
            console.warn(`${MOD} Contenedor #grid-productos no encontrado`);
            return;
        }

        // Verificar que el contenedor esté conectado al DOM
        if (!container.isConnected) {
            console.warn(`${MOD} Contenedor #grid-productos no está conectado al DOM`);
            return;
        }

        // Verificar que no se haya inicializado ya
        if (table && window.SintelInventarioTables.main) {
            console.log(`${MOD} Tabla ya inicializada, omitiendo...`);
            return;
        }

        initTable();
    }

    // ⚠️ v2.60: Lazy Loading - Inicializar solo cuando el contenedor sea visible
    // Usa DOMUtils.onVisibleOnce para esperar a que el tab se active
    if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
        // Intentar múltiples selectores para cubrir diferentes estructuras de tabs
        const selectors = [
            '#grid-productos',
            '#pane-existencias',
            '#tab-inventario-content',
            '#pane-existencias #grid-productos'
        ];
        
        // Usar el primer selector disponible
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
            // Fallback: Inicializar cuando el DOM esté listo (para compatibilidad)
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

    // ⚠️ Bootstrap Tabs: Inicializar cuando se muestra el tab de productos
    d.addEventListener('shown.bs.tab', function(e) {
        const target = e.target.getAttribute('data-bs-target');
        const targetId = e.target.id;
        
        // Verificar si es el tab de productos (existencias)
        if (target === '#pane-existencias' || targetId === 'tab-existencias' || 
            (e.target.classList.contains('nav-link') && targetId && targetId.includes('existencias'))) {
            console.log(`${MOD} Tab de productos mostrado, verificando inicialización...`);
            
            // Verificar si la tabla existe y está inicializada
            const gridEl = d.querySelector('#grid-productos');
            if (!gridEl) {
                console.warn(`${MOD} Contenedor #grid-productos no encontrado`);
                return;
            }
            
            // Si la tabla no está inicializada, inicializarla
            if (!table || !window.SintelInventarioTables.main) {
                console.log(`${MOD} Tabla no inicializada, inicializando...`);
                setTimeout(function() {
                    init();
                }, 100);
            } else {
                // Si ya está inicializada, solo recargar datos
                console.log(`${MOD} Tabla ya inicializada, recargando datos...`);
                setTimeout(function() {
                    recargar();
                }, 50);
            }
        }
    });

    // ⚠️ HTMX: Reinicializar cuando se carga contenido vía HTMX
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', function(event) {
            if (event.detail.target.id === 'pane-existencias' || 
                event.detail.target.id === 'tab-inventario-content') {
                // Pequeño delay para asegurar que el DOM esté completamente renderizado
                setTimeout(function() {
                    // Solo inicializar si no se ha inicializado ya
                    if (!table || !window.SintelInventarioTables.main) {
                        init();
                    }
                }, 100);
            }
        });
    }

})(window, document);
