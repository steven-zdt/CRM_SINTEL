/**
 * Feature: Listado y Tabulator - Proyectos v2.60
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
(function (w, d) {
    'use strict';

    const MOD = '[proyectos.list]';
    let table = null;

    // ⚠️ Anti-Zombies v2.60: Singleton global para instancias de Tabulator
    if (window.SintelProyectosTables) {
        Object.values(window.SintelProyectosTables).forEach(tb => {
            if (tb && typeof tb.destroy === 'function') {
                try {
                    tb.destroy();
                } catch (error) {
                    console.warn(`${MOD} Error al destruir instancia zombie:`, error);
                }
            }
        });
    }
    window.SintelProyectosTables = {};

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

    // Formateador de porcentaje
    function formatearPorcentaje(value) {
        if (value === null || value === undefined || value === '') return '0,00%';
        const num = parseFloat(value);
        if (isNaN(num)) return '0,00%';
        return new Intl.NumberFormat('es-CO', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(num / 100);
    }

    // Definir columnas específicas del módulo
    function getColumns() {
        const fmtFecha = (v) => {
            if (!v) return '---';
            try { return new Date(v).toLocaleDateString('es-CO'); } catch { return v; }
        };

        return [
            {
                title: "Proyecto",
                field: "nombre",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function (cell) {
                    return cell.getValue() || '---';
                },
                minWidth: 220,
                frozen: true
            },
            {
                title: "Fase Actual",
                field: "fase_actual_display",
                formatter: function (cell) {
                    const value = cell.getValue() || '---';
                    const fase = cell.getRow().getData().fase_actual;
                    const map = {
                        'BORRADOR':  ['bg-secondary', 'Borrador'],
                        'INICIO':    ['bg-info text-dark', 'Inicio'],
                        'PLANEACION':['bg-primary', 'Planeación'],
                        'EJECUCION': ['bg-warning text-dark', 'Ejecución'],
                        'CIERRE':    ['bg-success', 'Cierre'],
                    };
                    const [cls, label] = map[fase] || ['bg-secondary', value];
                    return `<span class="badge ${cls} px-2">${label}</span>`;
                },
                width: 120,
                hozAlign: "center",
                headerHozAlign: "center"
            },
            {
                title: "Estado",
                field: "estado_display",
                formatter: function (cell) {
                    const estado = cell.getRow().getData().estado_tarea;
                    const map = {
                        'PENDIENTE':  ['bg-secondary', 'Pendiente'],
                        'EN_PROCESO': ['bg-primary',   'En Proceso'],
                        'DETENIDO':   ['bg-danger',    'Detenido'],
                        'COMPLETADO': ['bg-success',   'Completado'],
                    };
                    const [cls, label] = map[estado] || ['bg-secondary', cell.getValue() || '---'];
                    return `<span class="badge ${cls} px-2">${label}</span>`;
                },
                width: 120,
                hozAlign: "center",
                headerHozAlign: "center"
            },
            {
                title: "Cliente",
                field: "cliente_nombre",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function (cell) {
                    return cell.getValue() || '---';
                },
                minWidth: 160
            },
            {
                title: "Factura",
                field: "factura_costo_numero",
                formatter: function (cell) {
                    const factura = cell.getValue();
                    if (!factura) return '<span class="text-muted small">---</span>';
                    return `<span class="badge bg-light text-dark border fw-semibold">${factura}</span>`;
                },
                width: 120,
                hozAlign: "center",
                headerHozAlign: "center"
            },
            {
                title: "Cotización",
                field: "cotizacion_numero",
                formatter: function (cell) {
                    const numero = cell.getValue();
                    if (!numero) return '<span class="text-muted small">---</span>';
                    return `<span class="badge bg-info-subtle text-info-emphasis border border-info fw-semibold">${numero}</span>`;
                },
                width: 120,
                hozAlign: "center",
                headerHozAlign: "center"
            },
            {
                title: "Inicio",
                field: "fecha_inicio",
                formatter: (cell) => fmtFecha(cell.getValue()),
                width: 100,
                hozAlign: "center",
                headerHozAlign: "center"
            },
            {
                title: "Fin Estimado",
                field: "fecha_fin_prevista",
                formatter: (cell) => fmtFecha(cell.getValue()),
                width: 110,
                hozAlign: "center",
                headerHozAlign: "center"
            },
            {
                title: "Valor Contrato",
                field: "valor_contrato_proyectado",
                formatter: (cell) => formatearMoneda(cell.getValue()),
                hozAlign: "right",
                headerHozAlign: "right",
                width: 145
            },
            {
                title: "Utilidad",
                field: "utilidad_planeada",
                formatter: function (cell) {
                    const utilidad = parseFloat(cell.getValue()) || 0;
                    const contrato = parseFloat(cell.getRow().getData().valor_contrato_proyectado) || 0;
                    const pct = contrato > 0 ? ((utilidad / contrato) * 100).toFixed(1) : '0.0';
                    const color = utilidad > 0 ? '#198754' : utilidad < 0 ? '#dc3545' : '#6c757d';
                    const badgeCls = utilidad > 0 ? 'bg-success' : utilidad < 0 ? 'bg-danger' : 'bg-secondary';
                    return `
                        <div style="text-align:right; line-height:1.3;">
                            <span style="font-weight:600; color:${color};">${formatearMoneda(utilidad)}</span><br>
                            <span class="badge ${badgeCls} px-1" style="font-size:0.7rem;">${pct}%</span>
                        </div>`;
                },
                hozAlign: "right",
                headerHozAlign: "right",
                width: 155
            },
            {
                title: "",
                formatter: function (cell) {
                    const uuid = cell.getRow().getData().uuid;
                    return `
                        <div class="btn-group btn-group-sm">
                            <button type="button" class="btn btn-outline-primary btn-edit-proyecto" data-uuid="${uuid}" title="Editar">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete-proyecto" data-uuid="${uuid}" title="Eliminar">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>`;
                },
                headerSort: false,
                hozAlign: "center",
                width: 90,
                frozen: true
            }
        ];
    }

    // Inicializar Tabulator usando Factory (The Engine)
    function initTabulator() {
        if (!w.TabulatorFactory) {
            console.error(`${MOD} TabulatorFactory no está disponible`);
            return;
        }

        const gridElement = d.querySelector('#grid-proyectos');
        if (!gridElement) {
            console.warn(`${MOD} Elemento #grid-proyectos no encontrado`);
            return;
        }

        // ⚠️ Anti-Zombies v2.60: Destruir instancia previa si existe
        if (window.SintelProyectosTables.main) {
            try {
                window.SintelProyectosTables.main.destroy();
                console.log(`${MOD} Instancia zombie de Tabulator destruida`);
            } catch (error) {
                console.warn(`${MOD} Error al destruir instancia previa:`, error);
            }
        }

        // ⚠️ DRY: Solo definimos lo específico, el resto viene del Factory
        table = w.TabulatorFactory.create(
            '#grid-proyectos',
            '/api/v1/proyectos/',
            getColumns(),
            {
                searchInputSelector: '#search-proyecto'
            }
        );

        // ⚠️ Anti-Zombies v2.60: Guardar instancia en singleton global
        if (table) {
            window.SintelProyectosTables.main = table;
            console.log(`${MOD} Tabulator inicializado y guardado en SintelProyectosTables`);
        }

        return table;
    }

    // Event Delegation para acciones del Grid
    function initListEvents() {
        const gridElement = d.querySelector('#grid-proyectos');
        if (!gridElement) {
            console.warn(`${MOD} Elemento #grid-proyectos no encontrado para eventos`);
            return;
        }

        // ⚠️ Event Delegation: Escuchar clics en el contenedor del grid
        gridElement.addEventListener('click', async (e) => {
            // Botón Editar
            const btnEdit = e.target.closest('.btn-edit-proyecto');
            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();

                const uuid = btnEdit.getAttribute('data-uuid');
                if (!uuid) {
                    console.warn(`${MOD} Botón sin data-uuid`);
                    return;
                }

                // Loading state
                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // HTMX: Cargar Offcanvas desde el servidor usando uuid
                    await htmx.ajax('GET', `/api/v1/proyectos/gestor-offcanvas/?uuid=${uuid}`, {
                        target: '#offcanvas-container-proyectos',
                        swap: 'innerHTML'
                    });

                    // ⚠️ v2.62.3: La apertura se delega al htmx:afterSwap en proyectos_editor.js
                    // Esto centraliza la lógica y evita el error de cierre automático.
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al cargar el formulario de proyecto');
                    }
                } finally {
                    // Restaurar estado del botón
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-proyecto');
            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();

                const uuid = btnDelete.getAttribute('data-uuid');
                if (!uuid) {
                    console.warn(`${MOD} Botón eliminar sin data-uuid`);
                    return;
                }

                // Confirmación
                if (!confirm('¿Está seguro de eliminar este proyecto? Esta acción no se puede deshacer.')) {
                    return;
                }

                // Loading state
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    const res = await w.http('DELETE', `/api/v1/proyectos/${uuid}/`);

                    if (res.ok) {
                        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                            w.SintelFeedback.success('Proyecto eliminado correctamente');
                        }
                        // Recargar grid
                        if (table && typeof table.replaceData === 'function') {
                            table.replaceData();
                        }
                    } else {
                        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                            w.UIManager.handleError(res, MOD);
                        } else {
                            alert('Error al eliminar el proyecto');
                        }
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar proyecto:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al eliminar el proyecto');
                    }
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
                return;
            }
        });

        console.log(`${MOD} Event delegation configurado`);
    }

    // ⚠️ Recarga Reactiva: Escuchar evento personalizado
    function initEventListeners() {
        // Escuchar evento de proyecto guardado para refrescar el grid
        d.addEventListener('proyectoGuardado', () => {
            if (table && typeof table.replaceData === 'function') {
                table.replaceData();
                console.log(`${MOD} Grid refrescado tras guardar proyecto`);
            } else {
                console.warn(`${MOD} No se pudo refrescar: tabla no inicializada`);
            }
        });

        console.log(`${MOD} Event listeners configurados`);
    }

    // Inicialización principal
    function init() {
        console.log(`${MOD} Inicializando módulo de listado...`);

        // ⚠️ Lazy Loading: Solo inicializar cuando el tab esté visible
        const tabElement = d.querySelector('#tab-proyectos');
        if (tabElement) {
            // Usar DOMUtils.onVisibleOnce si está disponible
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce(tabElement.id ? '#' + tabElement.id : tabElement, () => {
                    initTabulator();
                    initListEvents();
                    initEventListeners();
                });
            } else {
                // Fallback: Inicializar directamente
                initTabulator();
                initListEvents();
                initEventListeners();
            }
        } else {
            // Si no hay tab, inicializar directamente
            initTabulator();
            initListEvents();
            initEventListeners();
        }
    }

    // ⚠️ HTMX: Limpiar instancias zombie en recargas
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:beforeSwap', (event) => {
            // Si se está recargando el contenedor principal, destruir instancias
            if (event.detail.target.id === 'tab-proyectos-content' ||
                event.detail.target.closest('#tab-proyectos-content')) {
                if (window.SintelProyectosTables.main) {
                    try {
                        window.SintelProyectosTables.main.destroy();
                        delete window.SintelProyectosTables.main;
                        console.log(`${MOD} Instancia destruida por HTMX swap`);
                    } catch (error) {
                        console.warn(`${MOD} Error al destruir instancia en HTMX swap:`, error);
                    }
                }
            }
        });
    }

    // Auto-inicializar cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ⚠️ API Pública: Exponer funciones para uso externo
    w.ProyectosListModule = {
        init,
        refresh: () => {
            if (table && typeof table.replaceData === 'function') {
                table.replaceData();
            }
        },
        getTable: () => table
    };

    // ⚠️ Compatibilidad: Alias para uso legacy
    if (!w.ProyectosModule) {
        w.ProyectosModule = {
            refresh: () => {
                if (table && typeof table.replaceData === 'function') {
                    table.replaceData();
                }
            }
        };
    }

})(window, document);
