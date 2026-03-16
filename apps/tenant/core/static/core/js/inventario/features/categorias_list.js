/**
 * Feature: Listado y Tabulator - Categorías v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (CORE_API_BASE)
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Anti-Zombies: Previene instancias fantasma de Tabulator por recargas HTMX
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.CategoriasEditor (definido en categorias_editor.js) - Feature: Crear/Editar
 */
(function(w, d) {
    'use strict';

    const MOD = '[categorias.list]';
    const GRID_ID = '#grid-categorias';
    const SEARCH_ID = '#search-categoria';
    const API_URL = '/api/v1/core/v1/inventario/categorias/'; // ⚠️ v2.61.3: Core API Facade para CRUD
    const CORE_API_BASE = '/api/v1/core/v1/inventario/categorias'; // Core API Facade
    let table = null;
    let _eliminandoCategoria = false; // Flag para prevenir rowClick durante eliminación

    // ⚠️ Anti-Zombies v2.61.3: Singleton global para instancias de Tabulator
    if (window.SintelInventarioTables && window.SintelInventarioTables.categorias) {
        if (window.SintelInventarioTables.categorias && typeof window.SintelInventarioTables.categorias.destroy === 'function') {
            try {
                window.SintelInventarioTables.categorias.destroy();
            } catch (error) {
                console.warn(`${MOD} Error al destruir instancia zombie:`, error);
            }
        }
    }
    if (!window.SintelInventarioTables) {
        window.SintelInventarioTables = {};
    }

    /**
     * Formatear badge de aplicación
     * @param {string} aplicacion - Tipo de aplicación
     * @returns {string} HTML del badge
     */
    function formatearAplicacion(aplicacion) {
        const badges = {
            'TODO': '<span class="badge bg-primary">Todos</span>',
            'PRODUCTO': '<span class="badge bg-info">Productos</span>',
            'SERVICIO': '<span class="badge bg-warning">Servicios</span>',
            'ACTIVO': '<span class="badge bg-secondary">Activos</span>'
        };
        return badges[aplicacion] || `<span class="badge bg-secondary">${aplicacion || '-'}</span>`;
    }

    /**
     * Definir columnas específicas del módulo
     * @returns {Array} Configuración de columnas Tabulator
     */
    /**
     * Formatter seguro para valores con fallback
     * ⚠️ v2.61.3: Previene error "Formatter has returned a type of object"
     * @param {CellComponent} cell - Celda de Tabulator
     * @param {string} fallback - Valor por defecto
     * @returns {string} Valor o fallback
     */
    function safeValueOrFallback(cell, fallback = '-') {
        const value = cell.getValue();
        // ⚠️ Asegurar que siempre retorne string, nunca objeto
        if (value === null || value === undefined || value === '') {
            return fallback;
        }
        return String(value);
    }

    function getColumns() {
        return [
            {
                title: "Nombre",
                field: "nombre",
                formatter: function(cell) {
                    return safeValueOrFallback(cell, '---');
                },
                minWidth: 200,
                headerFilter: "input"
            },
            {
                title: "Descripción",
                field: "descripcion",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val || val === '') {
                        return '<span class="text-muted">Sin descripción</span>';
                    }
                    return String(val);
                },
                minWidth: 250
            },
            {
                title: "Aplicación",
                field: "aplicacion",
                formatter: function(cell) {
                    return formatearAplicacion(cell.getValue());
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
            layout: "fitDataStretch",
            responsiveLayout: true,
            responsiveLayoutCollapseStartOpen: false,
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
        window.SintelInventarioTables.categorias = table;

        // Event Delegation para acciones del Grid
        initListEvents();

        return table;
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
            const btnEdit = e.target.closest('.btn-edit-categoria');
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
                    const offcanvasContainer = d.getElementById('offcanvas-container-categorias');
                    if (!offcanvasContainer) {
                        console.warn(`${MOD} Contenedor #offcanvas-container-categorias no encontrado`);
                        return;
                    }

                    await htmx.ajax('GET', `${CORE_API_BASE}/gestor-offcanvas/?id=${id}`, {
                        target: '#offcanvas-container-categorias',
                        swap: 'innerHTML'
                    });

                    // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
                    await new Promise(resolve => setTimeout(resolve, 100));

                    const offcanvasEl = d.getElementById('offcanvas-categorias');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                        offcanvasInstance.show();
                    } else {
                        console.warn(`${MOD} No se pudo abrir el Offcanvas: elemento no encontrado o Bootstrap no disponible`);
                    }
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al cargar el formulario de categoría');
                    }
                } finally {
                    // Restaurar estado del botón
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-categoria');
            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnDelete.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón eliminar sin data-id`);
                    return;
                }

                // Confirmación
                if (!confirm('¿Está seguro de eliminar esta categoría? Los ítems asociados quedarán sin categoría.')) {
                    return;
                }

                // ⚠️ v2.61.3: Activar flag para prevenir rowClick durante eliminación
                _eliminandoCategoria = true;

                // ⚠️ Loading state
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // ⚠️ v2.61.3: Usar Core API Facade
                    let deleteRes;
                    if (w.http && typeof w.http === 'function') {
                        deleteRes = await w.http('DELETE', `${CORE_API_BASE}/${id}/`);
                    } else if (w.inventarioAPI && w.inventarioAPI.categorias && typeof w.inventarioAPI.categorias.delete === 'function') {
                        deleteRes = await w.inventarioAPI.categorias.delete(id);
                    } else {
                        console.error(`${MOD} API de eliminación no disponible`);
                        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                            w.UIManager.notifyError({ status: 500, data: { detail: 'API de eliminación no disponible' } }, MOD);
                        }
                        return;
                    }

                    // ⚠️ v2.61.3: Aislamiento Gradual - Solo verificar ok
                    if (!deleteRes.ok) {
                        // ⚠️ v2.61.3: Manejo genérico de errores (ya no hay validación de categoría activa)
                        let errorMensaje = 'Error al eliminar la categoría';
                        if (deleteRes.data) {
                            if (deleteRes.data.detail) {
                                errorMensaje = typeof deleteRes.data.detail === 'string' 
                                    ? deleteRes.data.detail 
                                    : JSON.stringify(deleteRes.data.detail);
                            } else if (deleteRes.data.message) {
                                errorMensaje = deleteRes.data.message;
                            }
                        }
                        
                        if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                            w.SintelFeedback.error(errorMensaje);
                        } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                            w.UIManager.handleError(deleteRes, MOD, {
                                modalSelector: '#offcanvas-categorias',
                                errorContainerSelector: '#form-categoria-feedback'
                            });
                        } else {
                            alert(errorMensaje);
                        }
                        
                        // Restaurar estado del botón
                        btnDelete.disabled = false;
                        btnDelete.innerHTML = originalHTML;
                        _eliminandoCategoria = false;
                        return;
                    }

                    // ⚠️ v2.61.3: Cerrar cualquier offcanvas abierto
                    const offcanvasCategoria = d.getElementById('offcanvas-categorias');
                    if (offcanvasCategoria && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const instance = bootstrap.Offcanvas.getInstance(offcanvasCategoria);
                        if (instance) {
                            instance.hide();
                        }
                    }

                    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                        w.SintelFeedback.success('Categoría eliminada correctamente');
                    }

                    // Recargar tabla
                    if (table) {
                        table.replaceData();
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar categoría:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al eliminar la categoría');
                    }
                } finally {
                    // Restaurar estado del botón y flag
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                    _eliminandoCategoria = false;
                }
                return;
            }
        });

        // ⚠️ Event Delegation: Clic en fila para editar (solo si no se está eliminando)
        if (table) {
            table.on('rowClick', async function(e, row) {
                // ⚠️ v2.61.3: Prevenir rowClick si se está eliminando una categoría
                if (_eliminandoCategoria) {
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
                        target: '#offcanvas-container-categorias',
                        swap: 'innerHTML'
                    });

                    await new Promise(resolve => setTimeout(resolve, 100));

                    const offcanvasEl = d.getElementById('offcanvas-categorias');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                        offcanvasInstance.show();
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
     * Inicializar módulo de listado de categorías
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

    // ⚠️ Exposición global del módulo
    if (!w.CategoriasList) {
        w.CategoriasList = {
            init: init,
            recargar: recargar,
            getTable: () => table
        };
    }

    // ⚠️ Auto-inicialización si el DOM está listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        // Si el tab de categorías está visible, inicializar inmediatamente
        const tabCategorias = d.querySelector('#tab-categorias');
        if (tabCategorias && tabCategorias.classList.contains('active')) {
            init();
        } else {
            // Lazy loading: inicializar cuando el tab se muestre
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce('#pane-categorias', init);
            } else {
                // Fallback: escuchar evento de tab
                const tabButton = d.querySelector('#tab-categorias');
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
