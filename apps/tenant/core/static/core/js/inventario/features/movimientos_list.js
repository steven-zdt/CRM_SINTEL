/**
 * Feature: Listado y Tabulator - Movimientos de Inventario (Kardex) v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (CORE_API_BASE)
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Anti-Zombies: Previene instancias fantasma de Tabulator por recargas HTMX
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.MovimientosEditor (definido en movimientos_editor.js) - Feature: Crear
 * 
 * CRUD:
 * - READ: Lista movimientos de inventario con Tabulator
 * - READ (detail): Ver detalles de un movimiento
 * ⚠️ NOTA: No hay UPDATE/DELETE por integridad del Kardex (movimientos históricos)
 */
(function(w, d) {
    'use strict';

    const MOD = '[movimientos.list]';
    const GRID_ID = '#grid-movimientos';
    const SEARCH_ID = '#search-movimiento';
    const API_URL = '/api/v1/core/v1/inventario/movimientos/'; // ⚠️ v2.61.3: Core API Facade para CRUD
    const CORE_API_BASE = '/api/v1/core/v1/inventario/movimientos'; // Core API Facade
    let table = null;

    // ⚠️ Anti-Zombies v2.61.3: Singleton global para instancias de Tabulator
    if (window.SintelInventarioTables && window.SintelInventarioTables.movimientos) {
        if (window.SintelInventarioTables.movimientos && typeof window.SintelInventarioTables.movimientos.destroy === 'function') {
            try {
                window.SintelInventarioTables.movimientos.destroy();
            } catch (error) {
                console.warn(`${MOD} Error al destruir instancia zombie:`, error);
            }
        }
    }
    if (!window.SintelInventarioTables) {
        window.SintelInventarioTables = {};
    }

    /**
     * Formatear fecha y hora
     * @param {string} value - Fecha en formato ISO
     * @returns {string} Fecha formateada
     */
    function formatearFechaHora(value) {
        if (!value) return '-';
        try {
            const date = new Date(value);
            return date.toLocaleString('es-CO');
        } catch (error) {
            return value;
        }
    }

    /**
     * Formatear badge de tipo de movimiento
     * @param {string} tipo - Tipo de movimiento
     * @param {string} tipoDisplay - Texto de tipo para mostrar
     * @returns {string} HTML del badge
     */
    function formatearTipoMovimiento(tipo, tipoDisplay) {
        let color = 'bg-secondary';
        // Entradas
        if (tipo && tipo.includes('ENTRADA')) {
            color = 'bg-success';
        }
        // Salidas
        else if (tipo && tipo.includes('SALIDA')) {
            color = 'bg-danger';
        }
        
        const texto = tipoDisplay || tipo || 'N/A';
        return `<span class="badge ${color}">${texto}</span>`;
    }

    /**
     * Definir columnas específicas del módulo
     * @returns {Array} Configuración de columnas Tabulator
     */
    function getColumns() {
        return [
            {
                title: "Fecha",
                field: "created_at",
                formatter: function(cell) {
                    return formatearFechaHora(cell.getValue());
                },
                width: 160
            },
            {
                title: "Tipo Movimiento",
                field: "tipo",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    return formatearTipoMovimiento(rowData.tipo, rowData.tipo_display);
                },
                width: 150
            },
            {
                title: "Producto",
                field: "producto_nombre",
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    const codigo = data.producto_codigo || '';
                    const nombre = data.producto_nombre || '-';
                    return `<strong>${codigo}</strong> - ${nombre}`;
                },
                minWidth: 250,
                headerFilter: "input"
            },
            {
                title: "Cantidad",
                field: "cantidad",
                formatter: function(cell) {
                    const val = parseFloat(cell.getValue()) || 0;
                    return val.toFixed(3);
                },
                width: 100,
                hozAlign: "right"
            },
            {
                title: "Origen",
                field: "origen_referencia",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
                    return cell.getValue() || '<span class="text-muted">-</span>';
                },
                width: 150
            },
            {
                title: "Destino",
                field: "cliente_referencia",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
                    return cell.getValue() || '<span class="text-muted">-</span>';
                },
                width: 150
            },
            {
                title: "Observaciones",
                field: "observaciones",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
                    return cell.getValue() || '<span class="text-muted">-</span>';
                },
                width: 200
            },
            {
                title: "Acciones",
                field: "acciones",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    const id = rowData.id;
                    // ⚠️ Solo botón de ver detalles (movimientos históricos no se editan/eliminan)
                    return `
                        <button type="button" class="btn btn-outline-info btn-sm btn-ver-detalle-movimiento" data-id="${id}" title="Ver Detalles">
                            <i class="bi bi-eye"></i>
                        </button>
                    `;
                },
                width: 80,
                headerSort: false,
                resizable: false,
                hozAlign: "center"
            }
        ];
    }

    /**
     * Inicializar tabla de movimientos
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
            placeholder: "No hay movimientos registrados",
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
        window.SintelInventarioTables.movimientos = table;

        // Event Delegation para acciones del Grid
        initListEvents();

        return table;
    }

    /**
     * Ver detalles de un movimiento
     * ⚠️ CRUD: READ (detail)
     * @param {string|number} movimientoId - ID del movimiento
     */
    async function verDetalle(movimientoId) {
        if (!movimientoId) {
            console.warn(`${MOD} ID de movimiento no proporcionado`);
            return;
        }

        try {
            // ⚠️ API-First: Obtener información del movimiento
            let movimientoRes;
            if (w.http && typeof w.http === 'function') {
                movimientoRes = await w.http('GET', `${CORE_API_BASE}/${movimientoId}/`);
            } else if (w.inventarioAPI && w.inventarioAPI.movimientos && typeof w.inventarioAPI.movimientos.get === 'function') {
                movimientoRes = await w.inventarioAPI.movimientos.get(movimientoId);
            } else {
                console.error(`${MOD} API no disponible`);
                return;
            }

            // ⚠️ Aislamiento Gradual - Solo verificar ok
            if (!movimientoRes.ok || !movimientoRes.data) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(movimientoRes, MOD);
                }
                return;
            }

            const movimiento = movimientoRes.data;

            // Construir información del movimiento
            const info = `
                <strong>Fecha:</strong> ${movimiento.created_at ? formatearFechaHora(movimiento.created_at) : '-'}<br>
                <strong>Tipo:</strong> ${movimiento.tipo_display || movimiento.tipo || '-'}<br>
                <strong>Producto:</strong> ${movimiento.producto_nombre || movimiento.producto_codigo || '-'}<br>
                <strong>Cantidad:</strong> ${parseFloat(movimiento.cantidad || 0).toFixed(3)}<br>
                <strong>Origen:</strong> ${movimiento.origen_referencia || '-'}<br>
                <strong>Destino:</strong> ${movimiento.cliente_referencia || '-'}<br>
                <strong>Observaciones:</strong> ${movimiento.observaciones || '-'}
            `;

            // Mostrar información usando SintelFeedback
            if (w.SintelFeedback && typeof w.SintelFeedback.info === 'function') {
                w.SintelFeedback.info(info);
            } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                // Fallback: usar UIManager si SintelFeedback no está disponible
                w.UIManager.notifyError({ status: 200, data: { detail: info } }, MOD);
            }

        } catch (error) {
            console.error(`${MOD} Error al obtener detalles:`, error);
            if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                w.SintelFeedback.error('Error al cargar los detalles del movimiento');
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
            // Botón Ver Detalle
            const btnVerDetalle = e.target.closest('.btn-ver-detalle-movimiento');
            if (btnVerDetalle) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnVerDetalle.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón sin data-id`);
                    return;
                }

                // ⚠️ Loading state
                const originalHTML = btnVerDetalle.innerHTML;
                btnVerDetalle.disabled = true;
                btnVerDetalle.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    await verDetalle(id);
                } catch (error) {
                    console.error(`${MOD} Error al ver detalle:`, error);
                } finally {
                    // Restaurar estado del botón
                    btnVerDetalle.disabled = false;
                    btnVerDetalle.innerHTML = originalHTML;
                }
                return;
            }
        });
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
     * Inicializar módulo de listado de movimientos
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
    if (!w.MovimientosList) {
        w.MovimientosList = {
            init: init,
            recargar: recargar,
            verDetalle: verDetalle,
            getTable: () => table
        };
    }

    // ⚠️ Auto-inicialización si el DOM está listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        // Si el tab de movimientos está visible, inicializar inmediatamente
        const tabMovimientos = d.querySelector('#tab-movimientos');
        if (tabMovimientos && tabMovimientos.classList.contains('active')) {
            init();
        } else {
            // Lazy loading: inicializar cuando el tab se muestre
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce('#pane-movimientos', init);
            } else {
                // Fallback: escuchar evento de tab
                const tabButton = d.querySelector('#tab-movimientos');
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
