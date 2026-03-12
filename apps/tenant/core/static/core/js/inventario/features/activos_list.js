/**
 * Feature: Listado y Tabulator - Activos Fijos v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (CORE_API_BASE)
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Anti-Zombies: Previene instancias fantasma de Tabulator por recargas HTMX
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.ActivosEditor (definido en activos_editor.js) - Feature: Crear/Editar
 * 
 * CRUD:
 * - READ: Lista activos fijos con Tabulator
 * - DELETE: Eliminación con validación de estado activo
 */
(function(w, d) {
    'use strict';

    const MOD = '[activos.list]';
    const GRID_ID = '#grid-activos';
    const SEARCH_ID = '#search-activo';
    const API_URL = '/api/v1/core/v1/inventario/activos/'; // ⚠️ v2.61.3: Core API Facade para CRUD
    const CORE_API_BASE = '/api/v1/core/v1/inventario/activos'; // Core API Facade
    let table = null;
    let _eliminandoActivo = false; // Flag para prevenir rowClick durante eliminación

    // ⚠️ Anti-Zombies v2.61.3: Singleton global para instancias de Tabulator
    if (window.SintelInventarioTables && window.SintelInventarioTables.activos) {
        if (window.SintelInventarioTables.activos && typeof window.SintelInventarioTables.activos.destroy === 'function') {
            try {
                window.SintelInventarioTables.activos.destroy();
            } catch (error) {
                console.warn(`${MOD} Error al destruir instancia zombie:`, error);
            }
        }
    }
    if (!window.SintelInventarioTables) {
        window.SintelInventarioTables = {};
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
     * Formatear fecha
     * @param {string} value - Fecha en formato ISO
     * @returns {string} Fecha formateada
     */
    function formatearFecha(value) {
        if (!value) return '-';
        try {
            const date = new Date(value);
            return date.toLocaleDateString('es-CO');
        } catch (error) {
            return value;
        }
    }

    /**
     * Formatear badge de estado
     * @param {string} estado - Estado del activo
     * @param {string} estadoDisplay - Texto de estado para mostrar
     * @returns {string} HTML del badge
     */
    function formatearEstado(estado, estadoDisplay) {
        let color = 'bg-secondary';
        if (estado === 'ACTIVO') color = 'bg-success';
        else if (estado === 'MANTENIMIENTO') color = 'bg-warning';
        else if (estado === 'BAJA' || estado === 'VENDIDO') color = 'bg-danger';
        
        const texto = estadoDisplay || estado || 'N/A';
        return `<span class="badge ${color}">${texto}</span>`;
    }

    /**
     * Definir columnas específicas del módulo
     * @returns {Array} Configuración de columnas Tabulator
     */
    function getColumns() {
        return [
            {
                title: "Placa/Código",
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
                width: 150,
                headerFilter: "input"
            },
            {
                title: "Fecha Compra",
                field: "fecha_adquisicion",
                formatter: function(cell) {
                    return formatearFecha(cell.getValue());
                },
                width: 120
            },
            {
                title: "Costo",
                field: "costo_adquisicion",
                formatter: function(cell) {
                    return formatearMoneda(cell.getValue());
                },
                width: 120,
                hozAlign: "right"
            },
            {
                title: "Responsable",
                field: "responsable",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
                    return cell.getValue() || '<span class="text-muted">-</span>';
                },
                width: 150
            },
            {
                title: "Estado",
                field: "estado",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    return formatearEstado(rowData.estado, rowData.estado_display);
                },
                width: 140,
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
                            <button type="button" class="btn btn-outline-primary btn-edit-activo" data-id="${id}" title="Editar">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete-activo" data-id="${id}" title="Eliminar">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    `;
                },
                width: 120,
                headerSort: false,
                resizable: false,
                hozAlign: "center"
            }
        ];
    }

    /**
     * Inicializar tabla de activos
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
            placeholder: "No hay activos fijos registrados",
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
        window.SintelInventarioTables.activos = table;

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
            const btnEdit = e.target.closest('.btn-edit-activo');
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
                    const offcanvasContainer = d.getElementById('offcanvas-container-activos');
                    if (!offcanvasContainer) {
                        console.warn(`${MOD} Contenedor #offcanvas-container-activos no encontrado`);
                        return;
                    }

                    await htmx.ajax('GET', `${CORE_API_BASE}/gestor-offcanvas/?id=${id}`, {
                        target: '#offcanvas-container-activos',
                        swap: 'innerHTML'
                    });

                    // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
                    await new Promise(resolve => setTimeout(resolve, 100));

                    const offcanvasEl = d.getElementById('offcanvas-activos');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                        offcanvasInstance.show();
                    } else {
                        console.warn(`${MOD} No se pudo abrir el Offcanvas: elemento no encontrado o Bootstrap no disponible`);
                    }
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al cargar el formulario de activo');
                    }
                } finally {
                    // Restaurar estado del botón
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-activo');
            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnDelete.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón eliminar sin data-id`);
                    return;
                }

                // ⚠️ Validación: Obtener datos del activo para validar estado
                let activoRes;
                if (w.http && typeof w.http === 'function') {
                    activoRes = await w.http('GET', `${CORE_API_BASE}/${id}/`);
                } else if (w.inventarioAPI && w.inventarioAPI.activos && typeof w.inventarioAPI.activos.get === 'function') {
                    activoRes = await w.inventarioAPI.activos.get(id);
                } else {
                    console.error(`${MOD} API no disponible`);
                    return;
                }

                if (!activoRes.ok || !activoRes.data) {
                    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                        w.UIManager.handleError(activoRes, MOD);
                    }
                    return;
                }

                const activo = activoRes.data;

                // Validar que el activo no esté en estado ACTIVO
                if (activo.estado === 'ACTIVO') {
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('El activo está activo. Desactívelo primero.');
                    }
                    return;
                }

                // Confirmación
                if (!confirm('¿Está seguro de eliminar este activo fijo?')) {
                    return;
                }

                // ⚠️ v2.61.3: Activar flag para prevenir rowClick durante eliminación
                _eliminandoActivo = true;

                // ⚠️ Loading state
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // ⚠️ v2.61.3: Usar Core API Facade
                    let deleteRes;
                    if (w.http && typeof w.http === 'function') {
                        deleteRes = await w.http('DELETE', `${CORE_API_BASE}/${id}/`);
                    } else if (w.inventarioAPI && w.inventarioAPI.activos && typeof w.inventarioAPI.activos.delete === 'function') {
                        deleteRes = await w.inventarioAPI.activos.delete(id);
                    } else {
                        console.error(`${MOD} API de eliminación no disponible`);
                        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                            w.UIManager.notifyError({ status: 500, data: { detail: 'API de eliminación no disponible' } }, MOD);
                        }
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
                    const offcanvasActivo = d.getElementById('offcanvas-activos');
                    if (offcanvasActivo && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const instance = bootstrap.Offcanvas.getInstance(offcanvasActivo);
                        if (instance) {
                            instance.hide();
                        }
                    }

                    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                        w.SintelFeedback.success('Activo fijo eliminado correctamente');
                    }

                    // Recargar tabla
                    if (table) {
                        table.replaceData();
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar activo:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al eliminar el activo');
                    }
                } finally {
                    // Restaurar estado del botón y flag
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                    _eliminandoActivo = false;
                }
                return;
            }
        });

        // ⚠️ Event Delegation: Clic en fila para editar (solo si no se está eliminando)
        if (table) {
            table.on('rowClick', async function(e, row) {
                // ⚠️ v2.61.3: Prevenir rowClick si se está eliminando un activo
                if (_eliminandoActivo) {
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
                        target: '#offcanvas-container-activos',
                        swap: 'innerHTML'
                    });

                    await new Promise(resolve => setTimeout(resolve, 100));

                    const offcanvasEl = d.getElementById('offcanvas-activos');
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
     * Inicializar módulo de listado de activos
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
    if (!w.ActivosList) {
        w.ActivosList = {
            init: init,
            recargar: recargar,
            getTable: () => table
        };
    }

    // ⚠️ Auto-inicialización si el DOM está listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        // Si el tab de activos está visible, inicializar inmediatamente
        const tabActivos = d.querySelector('#tab-activos');
        if (tabActivos && tabActivos.classList.contains('active')) {
            init();
        } else {
            // Lazy loading: inicializar cuando el tab se muestre
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce('#pane-activos', init);
            } else {
                // Fallback: escuchar evento de tab
                const tabButton = d.querySelector('#tab-activos');
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
