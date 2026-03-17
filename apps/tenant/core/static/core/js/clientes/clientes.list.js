/**
 * Feature: Listado y Tabulator - Clientes v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.clientesAPI (definido en clientes.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 */
(function(w, d) {
    'use strict';

    let table = null;

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
                title: "Documento",
                field: "numero_documento",
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    const badge = data.tipo_documento_display 
                        ? `<span class="badge bg-secondary me-1">${data.tipo_documento_display}</span>` 
                        : '';
                    return `${badge}${data.numero_documento || '-'}`;
                }
            },
            {
                title: "Razón Social",
                field: "razon_social",
                headerFilter: "input",
                headerFilterPlaceholder: "Buscar..."
            },
            {
                title: "Email",
                field: "email",
                formatter: w.TabulatorFactory.formatters.valueOrFallback
            },
            {
                title: "Teléfono",
                field: "telefono",
                formatter: w.TabulatorFactory.formatters.valueOrFallback
            },
            {
                title: "Estado",
                field: "activo",
                formatter: w.TabulatorFactory.formatters.statusBadge,
                headerSort: false
            },
            {
                title: "Acciones",
                field: "acciones",
                hozAlign: "center",
                headerSort: false,
                width: 150,
                formatter: function(cell) {
                    return `
                        <div class="btn-group btn-group-sm" role="group">
                            <button class="btn btn-outline-primary btn-edit-cliente" title="Editar" style="z-index: 10;">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-info btn-view-cliente" title="Ver Detalle" style="z-index: 10;">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-delete-cliente" title="Eliminar" style="z-index: 10;">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>`;
                },
                cellClick: function(e, cell) {
                    const btn = e.target.closest('button');
                    if (!btn) return;
                    
                    const data = cell.getData();
                    console.log("Evento capturado para ID:", data.id);

                    if (btn.classList.contains('btn-edit-cliente')) {
                        abrirClienteOffcanvas(data.id);
                    } else if (btn.classList.contains('btn-delete-cliente')) {
                        eliminarCliente(cell.getRow(), data.id);
                    } else if (btn.classList.contains('btn-view-cliente')) {
                        abrirDetalle(data.id);
                    }
                }
            }
        ];
    }

    /**
     * Abrir offcanvas de edición (Reutilizando lógica HTMX)
     */
    async function abrirClienteOffcanvas(id) {
        const url = `/api/v1/clientes/${id}/render-offcanvas/editar/`;
        await htmx.ajax('GET', url, { target: '#offcanvas-container-clientes', swap: 'innerHTML' });
        const offcanvasEl = d.getElementById('offcanvas-cliente');
        if (offcanvasEl) {
            bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
        }
    }

    /**
     * Ver detalle
     */
    async function abrirDetalle(id) {
        const url = `/api/v1/clientes/render-offcanvas/detalle/?id=${id}`;
        await htmx.ajax('GET', url, { target: '#offcanvas-container-clientes', swap: 'innerHTML' });
        const offcanvasEl = d.getElementById('offcanvas-cliente-detalle');
        if (offcanvasEl) {
            bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
        }
    }

    /**
     * Eliminar Cliente (Atomic Flow)
     */
    async function eliminarCliente(row, id) {
        if (!confirm('¿Está seguro de eliminar este cliente?')) return;
        
        try {
            const res = await w.http('DELETE', `/api/v1/clientes/${id}/`);
            
            if (res.ok) {
                w.SintelFeedback.success('Cliente eliminado correctamente');
                row.delete();
            } else {
                w.UIManager.handleError(res, MOD);
            }
        } catch (err) {
            console.error('[clientes.list] Error en DELETE:', err);
            w.SintelFeedback.error('Error de conexión');
        }
    }

    // Inicializar Tabulator usando Factory (The Engine)
    function initTabulator() {
        if (!w.TabulatorFactory) {
            console.error('[clientes.list] TabulatorFactory no está disponible');
            return;
        }

        // ⚠️ DRY: Solo definimos lo específico, el resto viene del Factory
        table = w.TabulatorFactory.create(
            '#grid-clientes',
            '/api/v1/clientes/',
            getColumns(),
            {
                searchInputSelector: '#search-cliente'
            }
        );

        // ⚠️ v2.61: Procesar HTMX después de cargar datos en Tabulator
        if (table && typeof htmx !== 'undefined') {
            table.on('dataLoaded', function() {
                const tableContainer = d.querySelector('#grid-clientes');
                if (tableContainer) {
                    htmx.process(tableContainer);
                    console.log('[clientes.list] HTMX procesado en tabla después de cargar datos');
                }
            });
        }
    }

    // Eventos del listado
    function initListEvents() {
        // Buscador con debounce (recarga Server-Side)
        const searchInput = d.querySelector('#search-cliente');
        if (searchInput && table) {
            let timeout = null;
            searchInput.addEventListener('keyup', function(e) {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    if (table) {
                        table.setPage(1); // Resetear a primera página
                        table.replaceData(); // Recargar datos (Server-Side)
                    }
                }, 300);
            });
        }

        // ⚠️ Event delegation para botones de acciones en la tabla
        const tableContainer = d.querySelector('#grid-clientes');
        if (tableContainer) {
            tableContainer.addEventListener('click', function(e) {
                const btn = e.target.closest('button');
                if (!btn) return;
                
                const id = parseInt(btn.getAttribute('data-id'), 10);
                if (!id || isNaN(id)) return;
                
                if (btn.classList.contains('btn-edit')) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const btnOriginalText = btn.innerHTML;
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

                            // ⚠️ v2.61: Usar nuevo endpoint RESTful render-offcanvas/editar
                            const url = `/api/v1/clientes/${id}/render-offcanvas/editar/`;
                            try {
                                await htmx.ajax('GET', url, {
                                    target: '#offcanvas-container-clientes',
                                    swap: 'innerHTML'
                                });
                                // El template incluye script de auto-activación del offcanvas
                                console.log('[clientes.list] Offcanvas de edición cargado para cliente ID:', id);
                            } catch (error) {
                                console.error('[clientes.list] Error cargando offcanvas de edición:', error);
                                if (w.SintelFeedback) {
                                    w.SintelFeedback.error('Error al cargar el formulario de edición');
                                }
                            }
                            
                            // El template incluye script de auto-activación del offcanvas
                            // No es necesario activarlo manualmente aquí
                        } catch (error) {
                            console.error('[clientes.list] Error cargando offcanvas de edición:', error);
                            if (w.SintelFeedback) {
                                w.SintelFeedback.error('No se pudo cargar el formulario del cliente.');
                            }
                        } finally {
                            // Restaurar el botón
                            btn.disabled = false;
                            btn.innerHTML = btnOriginalText;
                        }
                    })();
                } else if (btn.classList.contains('btn-contactos')) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const btnOriginal = btn.innerHTML;
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    
                    // ⚠️ v2.60: Usar HTMX para cargar offcanvas de contactos (HTML, no JSON)
                    (async () => {
                        try {
                            await htmx.ajax('GET', `/api/v1/clientes/contactos/gestor-offcanvas/?cliente_id=${id}`, {
                                target: '#offcanvas-container-contactos',
                                swap: 'innerHTML'
                            });
                            
                            // Si HTMX termina con éxito, buscamos el elemento y lo abrimos con Bootstrap
                            const offcanvasEl = d.getElementById('offcanvas-contactos');
                            if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                                bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
                                // Disparar evento para inicializar la lógica de contactos (Fase 4)
                                d.dispatchEvent(new CustomEvent('initContactosEditor', { detail: { cliente_id: id } }));
                            } else {
                                console.warn('[clientes.list] Offcanvas de contactos no encontrado en el DOM o Bootstrap no disponible');
                            }
                        } catch (error) {
                            console.error('[clientes.list] Error cargando offcanvas de contactos:', error);
                            if (w.SintelFeedback) {
                                w.SintelFeedback.error('No se pudo cargar el gestor de contactos.');
                            }
                        } finally {
                            // Restaurar el botón
                            btn.disabled = false;
                            btn.innerHTML = btnOriginal;
                        }
                    })();
                } else if (btn.classList.contains('btn-delete')) {
                    e.preventDefault();
                    e.stopPropagation();
                    // Validar que no esté deshabilitado
                    if (btn.disabled) {
                        if (w.SintelFeedback) {
                            w.SintelFeedback.error('No se puede eliminar un cliente activo. Desactívelo primero.');
                        }
                        return;
                    }
                    // Disparar evento para que el editor lo maneje
                    d.dispatchEvent(new CustomEvent('clienteEliminar', { detail: { id } }));
                }
            });
        }

        // ⚠️ Escuchar evento de cliente guardado para recargar tabla automáticamente
        d.addEventListener('clienteGuardado', function() {
            if (table) {
                table.setPage(1).then(() => {
                    table.replaceData();
                }).catch(err => {
                    console.error('[clientes.list] Error al recargar tabla:', err);
                    // Fallback: intentar recargar directamente
                    if (table) {
                        table.replaceData();
                    }
                });
            }
        });

        // ⚠️ v2.60: Limpieza de DOM - Destruir Offcanvas cuando se cierre para evitar HTML fantasma
        d.addEventListener('hidden.bs.offcanvas', function(e) {
            const offcanvasEl = e.target;
            // Verificar que sea el offcanvas de clientes
            if (offcanvasEl && offcanvasEl.id === 'offcanvas-cliente') {
                const container = d.querySelector('#offcanvas-container-clientes');
                if (container) {
                    // Limpiar el contenedor para evitar acumulación de HTML
                    container.innerHTML = '';
                    console.log('[clientes.list] Offcanvas destruido y contenedor limpiado');
                }
            }
        });
    }

    // Inicialización
    function init() {
        // ⚠️ v2.60: Verificar dependencias con mensajes más informativos
        if (!w.Tabulator) {
            console.error('[clientes.list] Tabulator no está disponible. Asegúrate de que el script de Tabulator se cargue antes de este módulo.');
            // Intentar retry después de un breve delay
            setTimeout(() => {
                if (w.Tabulator && w.TabulatorFactory) {
                    console.info('[clientes.list] Tabulator ahora disponible, reintentando inicialización...');
                    init();
                }
            }, 500);
            return;
        }

        if (!w.TabulatorFactory) {
            console.error('[clientes.list] TabulatorFactory no está disponible. Asegúrate de que tabulator.factory.js se cargue antes de este módulo.');
            return;
        }

        // Verificar dependencias
        if (!w.clientesAPI) {
            console.error('[clientes.list] ❌ CRÍTICO: window.clientesAPI no está disponible.');
            return;
        }
        
        initTabulator();
        initListEvents();
    }

    // Auto-inicialización con lazy loading
    // ⚠️ v2.40: Inicializar solo cuando el contenedor sea visible
    let initialized = false;
    
    function tryInit() {
        if (initialized) return;
        const hasGrid = d.querySelector('#grid-clientes');
        if (hasGrid) {
            init();
            initialized = true;
        }
    }
    
    if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
        // Intentar con múltiples selectores
        w.DOMUtils.onVisibleOnce('#tab-clientes', tryInit);
        w.DOMUtils.onVisibleOnce('#clientes', tryInit);
    }
    
    // Fallback: inicializar en DOMContentLoaded o inmediatamente
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', tryInit);
    } else {
        tryInit();
    }
    
    // También escuchar eventos de tabs de Bootstrap
    d.addEventListener('shown.bs.tab', function(e) {
        if (e.target && (e.target.getAttribute('data-tab') === 'clientes' || 
                         e.target.getAttribute('href') === '#clientes' ||
                         e.target.getAttribute('data-bs-target') === '#clientes')) {
            tryInit();
        }
    });

    // Exponer API pública
    w.ClientesListModule = {
        refresh: function() {
            // ⚠️ CRÍTICO: Recargar tabla con paginación remota
            if (table) {
                // Resetear a la primera página y recargar
                table.setPage(1).then(() => {
                    // replaceData() sin parámetros usa la URL configurada en ajaxURLGenerator
                    table.replaceData();
                }).catch(err => {
                    console.error('[clientes.list] Error al refrescar tabla:', err);
                    // Fallback: intentar recargar directamente
                    try {
                        table.replaceData();
                    } catch (fallbackErr) {
                        console.error('[clientes.list] Error en fallback de refresh:', fallbackErr);
                    }
                });
            }
        },
        getTable: function() {
            return table;
        }
    };

})(window, document);
