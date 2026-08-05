/**
 * Feature: Listado y Tabulator - Empresa v2.60
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

    const MOD = '[empresa.list]';
    let table = null;

    if (!w.SintelEmpresaTables) {
        w.SintelEmpresaTables = {};
    }

    // Helper anti-backdrop-acumulado (patron inventario v3.9.0)
    function mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(el);
    }

    // Definir columnas específicas del módulo
    function getColumns() {
        return [
            {
                title: "NIT",
                field: "nit",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    const nit = rowData.nit ? String(rowData.nit).trim() : '';
                    const dv = rowData.dv ? String(rowData.dv).trim() : '';
                    if (!nit) return '<span class="text-muted">—</span>';
                    const nitFull = dv ? `${nit}-${dv}` : nit;
                    return `<code class="text-muted">${nitFull}</code>`;
                },
                width: 150
            },
            {
                title: "Razón Social",
                field: "razon_social",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<span class="fw-semibold text-dark">${val}</span>`;
                },
                minWidth: 250
            },
            {
                title: "Dirección",
                field: "direccion",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-geo-alt text-primary me-1"></i><span class="small">${val}</span>`;
                },
                minWidth: 200
            },
            {
                title: "Teléfono",
                field: "telefono",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-telephone text-success me-1"></i><span>${val}</span>`;
                },
                width: 140,
                hozAlign: "center"
            },
            {
                title: "Email",
                field: "email_contacto",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-envelope text-info me-1"></i><span class="small">${val}</span>`;
                },
                minWidth: 180
            },
            {
                title: "Acciones",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    const id = rowData.id;

                    return `
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-primary btn-edit-empresa" data-id="${id}" title="Editar Empresa">
                                <i class="bi bi-pencil"></i>
                            </button>
                        </div>
                    `;
                },
                headerSort: false,
                hozAlign: "center",
                width: 100
            }
        ];
    }

    // Inicializar Tabulator usando Factory (The Engine)
    function initTabulator() {
        if (!w.TabulatorFactory) {
            console.error(`${MOD} TabulatorFactory no está disponible`);
            return;
        }

        const gridElement = d.querySelector('#grid-empresa');
        if (!gridElement) {
            console.warn(`${MOD} Elemento #grid-empresa no encontrado`);
            return;
        }

        // ⚠️ Anti-Zombies v2.60: Destruir instancia previa si existe
        if (w.SintelEmpresaTables['empresa']) {
            try {
                w.SintelEmpresaTables['empresa'].destroy();
                console.log(`${MOD} Instancia zombie de Tabulator destruida`);
            } catch (error) {
                console.warn(`${MOD} Error al destruir instancia previa:`, error);
            }
        }

        // ⚠️ DRY: Solo definimos lo específico, el resto viene del Factory
        table = w.TabulatorFactory.create(
            '#grid-empresa',
            '/api/v1/empresas/',
            getColumns(),
            {
                searchInputSelector: '#search-empresa'
            }
        );

        // ⚠️ Anti-Zombies v2.60: Guardar instancia en singleton global
        if (table) {
            w.SintelEmpresaTables['empresa'] = table;
            console.log(`${MOD} Tabulator inicializado y guardado en SintelEmpresaTables`);

            // ⚠️ v3.10.0: Actualizar resumen cuando carguen datos
            if (typeof table.on === 'function') {
                table.on('dataLoaded', function() {
                    console.log(`${MOD} Datos cargados, actualizando resumen...`);
                    actualizarResumenEmpresa();
                });
            }
        }

        return table;
    }

    // Actualizar panel de resumen de empresa
    function actualizarResumenEmpresa() {
        try {
            // Cargar datos de Sedes y Áreas
            const sedesTable = w.SintelEmpresaTables && w.SintelEmpresaTables['sede'];
            const areasTable = w.SintelEmpresaTables && w.SintelEmpresaTables['area'];

            let totalSedes = 0;
            let totalAreas = 0;

            if (sedesTable && typeof sedesTable.getData === 'function') {
                totalSedes = sedesTable.getData().length;
            }

            if (areasTable && typeof areasTable.getData === 'function') {
                totalAreas = areasTable.getData().length;
            }

            // Actualizar elementos del DOM
            const sedesEl = d.getElementById('total-sedes');
            const areasEl = d.getElementById('total-areas');

            if (sedesEl) sedesEl.textContent = totalSedes;
            if (areasEl) areasEl.textContent = totalAreas;
        } catch (err) {
            console.warn(`${MOD} Error actualizando resumen:`, err);
        }
    }

    // Event Delegation para acciones del Grid
    function initListEvents() {
        const gridElement = d.querySelector('#grid-empresa');
        if (!gridElement) {
            console.warn(`${MOD} Elemento #grid-empresa no encontrado para eventos`);
            return;
        }

        // ⚠️ Event Delegation: Escuchar clics en el contenedor del grid
        gridElement.addEventListener('click', async (e) => {
            const btn = e.target.closest('.btn-edit-empresa');
            if (!btn) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            const id = btn.getAttribute('data-id');
            if (!id) {
                console.warn(`${MOD} Botón sin data-id`);
                return;
            }

            // ⚠️ Loading state
            const originalHTML = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

            try {
                // ⚠️ HTMX: Cargar Offcanvas desde el servidor
                await htmx.ajax('GET', `/api/v1/empresas/gestor-offcanvas/?id=${id}`, {
                    target: '#offcanvas-container-empresa',
                    swap: 'innerHTML'
                });

                // ⚠️ Safeguard: Verificar que el elemento existe antes de abrir
                const offcanvasEl = d.getElementById('offcanvas-empresa');
                if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                    mostrarOffcanvasSeguro(offcanvasEl);
                } else {
                    console.warn(`${MOD} No se pudo abrir el Offcanvas: elemento no encontrado o Bootstrap no disponible`);
                }
            } catch (error) {
                console.error(`${MOD} Error al cargar Offcanvas:`, error);
                if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                    w.SintelFeedback.error('Error al cargar el formulario de empresa');
                }
            } finally {
                // Restaurar estado del botón
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            }
        });

        console.log(`${MOD} Event delegation configurado`);
    }

    // ⚠️ Recarga Reactiva: Escuchar evento personalizado
    function initEventListeners() {
        // Escuchar evento de empresa guardada para refrescar el grid
        d.addEventListener('empresaGuardada', () => {
            if (table && typeof table.replaceData === 'function') {
                table.replaceData();
                console.log(`${MOD} Grid refrescado tras guardar empresa`);
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
        const tabElement = d.querySelector('#tab-empresa');
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
            if (event.detail.target.id === 'ui-empresa-list' || 
                event.detail.target.closest('#ui-empresa-list')) {
                if (w.SintelEmpresaTables['empresa']) {
                    try {
                        w.SintelEmpresaTables['empresa'].destroy();
                        delete w.SintelEmpresaTables['empresa'];
                        console.log(`${MOD} Instancia destruida por HTMX swap`);
                    } catch (error) {
                        console.warn(`${MOD} Error al destruir instancia en HTMX swap:`, error);
                    }
                }
            }
        });
    }

    // ⚠️ HTMX: Escuchar después de que el swap termine y el DOM esté estable
    if (typeof htmx !== 'undefined') {
        d.body.addEventListener('htmx:afterSettle', (event) => {
            const target = event.detail.target;
            
            // 1. Refrescar Tabulator si el contenedor principal fue recargado
            if (target && (target.id === 'ui-empresa-list' || target.closest('#ui-empresa-list'))) {
                if (w.EmpresaListModule && typeof w.EmpresaListModule.refresh === 'function') {
                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            w.EmpresaListModule.refresh();
                            console.log('[empresa.list] Tabulator refrescado tras recarga HTMX');
                        });
                    });
                }
            }

            // 2. Mostrar Offcanvas si fue inyectado
            if (target && target.id === 'offcanvas-container-empresa') {
                console.log('[empresa.list] Offcanvas de empresa cargado, inicializando...');
                
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        const offcanvasEl = d.getElementById('offcanvas-empresa');
                        if (offcanvasEl && typeof bootstrap !== 'undefined') {
                            mostrarOffcanvasSeguro(offcanvasEl);
                            console.log('[empresa.list] Offcanvas de empresa mostrado');
                        }
                    });
                });
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
    w.EmpresaListModule = {
        init,
        refresh: () => {
            if (table && typeof table.replaceData === 'function') {
                table.replaceData();
            }
        },
        getTable: () => table
    };

})(window, document);
