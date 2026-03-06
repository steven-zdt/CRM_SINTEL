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
    let table = null;

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
                title: "Precio Promedio",
                field: "costo_promedio",
                formatter: function(cell) {
                    return formatearMoneda(cell.getValue());
                },
                width: 140,
                hozAlign: "right",
                sorter: "number"
            },
            {
                title: "Valor Inventario",
                field: "valor_inventario",
                formatter: function(cell) {
                    return formatearMoneda(cell.getValue());
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
        const gridEl = d.querySelector('#grid-inventario');
        if (!gridEl) {
            console.warn(`${MOD} Contenedor #grid-inventario no encontrado`);
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
            layout: "fitColumns",
            responsiveLayout: "hide",
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
            '#grid-inventario',
            '/api/v1/inventario/productos/',
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
        const gridEl = d.querySelector('#grid-inventario');
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

                await htmx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${id}`, {
                    target: '#offcanvas-container-inventario',
                    swap: 'innerHTML'
                });

                const offcanvasEl = d.getElementById('offcanvas-inventario');
                if (offcanvasEl) {
                    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                    offcanvas.show();
                }
                return;
            }

            // Botón Ajustar Stock
            if (btn.classList.contains('btn-ajuste-producto')) {
                e.preventDefault();
                const id = btn.getAttribute('data-id');
                if (!id) return;

                await htmx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${id}&tipo=ajuste`, {
                    target: '#offcanvas-container-inventario',
                    swap: 'innerHTML'
                });

                const offcanvasEl = d.getElementById('offcanvas-inventario');
                if (offcanvasEl) {
                    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                    offcanvas.show();
                }
                return;
            }

            // Botón Eliminar
            if (btn.classList.contains('btn-delete-producto')) {
                e.preventDefault();
                const id = btn.getAttribute('data-id');
                if (!id) return;

                if (!confirm('¿Está seguro de eliminar este producto? Esta acción no se puede deshacer.')) {
                    return;
                }

                // TODO: Implementar eliminación usando API
                console.warn(`${MOD} Eliminación de producto no implementada aún`);
            }
        });

        // Event Delegation: Clic en fila para editar
        if (table) {
            table.on('rowClick', async function(e, row) {
                const data = row.getData();
                if (!data || !data.id) return;

                await htmx.ajax('GET', `/api/v1/inventario/productos/gestor-offcanvas/?id=${data.id}`, {
                    target: '#offcanvas-container-inventario',
                    swap: 'innerHTML'
                });

                const offcanvasEl = d.getElementById('offcanvas-inventario');
                if (offcanvasEl) {
                    const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                    offcanvas.show();
                }
            });
        }
    }

    /**
     * Escuchar evento de actualización para refrescar tabla
     */
    d.addEventListener('inventarioActualizado', function() {
        if (window.SintelInventarioTables.main) {
            window.SintelInventarioTables.main.replaceData();
        }
    });

    /**
     * ⚠️ v2.60: Inicialización con lazy loading usando DOMUtils.onVisibleOnce
     * Solo se ejecuta cuando el tab/contenedor se vuelve visible
     */
    function init() {
        // Verificar que el contenedor exista
        const container = d.querySelector('#grid-inventario');
        if (!container) {
            console.warn(`${MOD} Contenedor #grid-inventario no encontrado`);
            return;
        }

        // Verificar que el contenedor esté conectado al DOM
        if (!container.isConnected) {
            console.warn(`${MOD} Contenedor #grid-inventario no está conectado al DOM`);
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
            '#grid-inventario',
            '#pane-existencias',
            '#tab-inventario-content',
            '#workspace .tab-pane.show #grid-inventario'
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
        if (e.target && (e.target.getAttribute('data-bs-target') === '#pane-existencias' || e.target.id === 'tab-existencias')) {
            console.log(`${MOD} Tab de productos mostrado, verificando inicialización...`);
            if (!table || !window.SintelInventarioTables.main) {
                setTimeout(function() {
                    init();
                }, 100);
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
