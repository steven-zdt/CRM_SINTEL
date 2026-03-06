/**
 * Feature: Listado y Tabulator - Contactos v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator para Contactos
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Notificaciones
 */
(function(w, d) {
    'use strict';

    let table = null;
    let initialized = false;

    // Definir columnas específicas del módulo de contactos
    function getColumnsContactos() {
        return [
            {
                title: "ID",
                field: "id",
                width: 60,
                headerSort: false
            },
            {
                title: "Cliente",
                field: "cliente_nombre",
                headerFilter: "input",
                headerFilterPlaceholder: "Buscar cliente...",
                formatter: w.TabulatorFactory.formatters.valueOrFallback
            },
            {
                title: "Nombre",
                field: "nombre_completo",
                headerFilter: "input",
                headerFilterPlaceholder: "Buscar nombre...",
                formatter: w.TabulatorFactory.formatters.valueOrFallback
            },
            {
                title: "Cargo",
                field: "cargo",
                headerFilter: "input",
                headerFilterPlaceholder: "Buscar cargo...",
                formatter: w.TabulatorFactory.formatters.valueOrFallback
            },
            {
                title: "Email",
                field: "email",
                headerFilter: "input",
                headerFilterPlaceholder: "Buscar email...",
                formatter: w.TabulatorFactory.formatters.valueOrFallback
            },
            {
                title: "Teléfono",
                field: "telefono",
                formatter: w.TabulatorFactory.formatters.valueOrFallback
            },
            {
                title: "Principal",
                field: "is_principal",
                formatter: function(cell) {
                    const value = cell.getValue();
                    if (value === true) {
                        return '<span class="badge bg-primary">Principal</span>';
                    }
                    return '<span class="text-muted">-</span>';
                },
                headerSort: false,
                hozAlign: "center",
                width: 100
            },
            {
                title: "Estado",
                field: "activo",
                formatter: w.TabulatorFactory.formatters.statusBadge,
                headerSort: false,
                hozAlign: "center",
                width: 100
            },
            {
                title: "Acciones",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    const id = rowData.id;
                    
                    return `
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-primary btn-edit-contacto" data-id="${id}" title="Editar Contacto">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete-contacto" data-id="${id}" title="Eliminar Contacto">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    `;
                },
                headerSort: false,
                hozAlign: "center",
                width: 120
            }
        ];
    }

    // Inicializar Tabulator usando Factory (The Engine)
    function initTabulator() {
        if (!w.TabulatorFactory) {
            console.error('[contactos.list] TabulatorFactory no está disponible');
            return;
        }

        const gridElement = d.querySelector('#grid-contactos');
        if (!gridElement) {
            console.warn('[contactos.list] Contenedor #grid-contactos no encontrado');
            return;
        }

        // ⚠️ DRY: Solo definimos lo específico, el resto viene del Factory
        table = w.TabulatorFactory.create(
            '#grid-contactos',
            '/api/v1/clientes/contactos/',
            getColumnsContactos(),
            {
                searchInputSelector: '#search-contacto'
            }
        );
    }

    // Eventos del listado
    function initListEvents() {
        // Buscador con debounce (recarga Server-Side)
        const searchInput = d.querySelector('#search-contacto');
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
        const tableContainer = d.querySelector('#grid-contactos');
        if (tableContainer) {
            tableContainer.addEventListener('click', async function(e) {
                const btn = e.target.closest('button');
                if (!btn) return;
                
                const id = parseInt(btn.getAttribute('data-id'), 10);
                if (!id || isNaN(id)) return;

                if (btn.classList.contains('btn-edit-contacto')) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const btnOriginalText = btn.innerHTML;
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

                    // ⚠️ v2.60: Usar HTMX para cargar offcanvas de edición (HTML, no JSON)
                    try {
                        // Obtener el contacto para saber el cliente_id
                        const contactoRes = await w.http('GET', `/api/v1/clientes/contactos/${id}/`);
                        if (!contactoRes.ok || !contactoRes.data) {
                            throw new Error('No se pudo cargar el contacto');
                        }

                        const contacto = contactoRes.data;
                        const clienteId = contacto.cliente;

                        // Llamado HTMX al offcanvas con cliente_id
                        await htmx.ajax('GET', `/api/v1/clientes/contactos/gestor-offcanvas/?cliente_id=${clienteId}`, {
                            target: '#offcanvas-container-contactos',
                            swap: 'innerHTML'
                        });
                        
                        const offcanvasEl = d.getElementById('offcanvas-contactos');
                        if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                            bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
                            // Disparar evento para inicializar la lógica de contactos y cargar el contacto para editar
                            d.dispatchEvent(new CustomEvent('initContactosEditor', { 
                                detail: { 
                                    cliente_id: clienteId,
                                    contacto_id: id 
                                } 
                            }));
                        } else {
                            console.warn('[contactos.list] Offcanvas no encontrado en el DOM o Bootstrap no disponible');
                        }
                    } catch (error) {
                        console.error('[contactos.list] Error cargando offcanvas de edición:', error);
                        if (w.SintelFeedback) {
                            w.SintelFeedback.error('No se pudo cargar el formulario del contacto.');
                        }
                    } finally {
                        // Restaurar el botón
                        btn.disabled = false;
                        btn.innerHTML = btnOriginalText;
                    }
                } else if (btn.classList.contains('btn-delete-contacto')) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Confirmación estándar
                    if (!confirm('¿Está seguro de que desea eliminar este contacto?')) {
                        return;
                    }

                    const btnOriginalText = btn.innerHTML;
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

                    // Disparar evento para que el editor lo maneje
                    d.dispatchEvent(new CustomEvent('contactoEliminar', { detail: { id } }));
                    
                    // Restaurar el botón después de un breve delay
                    setTimeout(() => {
                        btn.disabled = false;
                        btn.innerHTML = btnOriginalText;
                    }, 1000);
                }
            });
        }

        // ⚠️ Escuchar evento de contacto guardado para recargar tabla automáticamente
        d.addEventListener('contactoGuardado', function() {
            if (table) {
                table.setPage(1).then(() => {
                    table.replaceData();
                }).catch(err => {
                    console.error('[contactos.list] Error al recargar tabla:', err);
                    // Fallback: intentar recargar directamente
                    if (table) {
                        table.replaceData();
                    }
                });
            }
        });

        // ⚠️ Escuchar evento de contacto eliminado para recargar tabla
        d.addEventListener('contactoEliminado', function() {
            if (table) {
                table.setPage(1).then(() => {
                    table.replaceData();
                }).catch(err => {
                    console.error('[contactos.list] Error al recargar tabla:', err);
                    if (table) {
                        table.replaceData();
                    }
                });
            }
        });

        // ⚠️ v2.60: Limpieza de DOM - Destruir Offcanvas cuando se cierre para evitar HTML fantasma
        d.addEventListener('hidden.bs.offcanvas', function(e) {
            const offcanvasEl = e.target;
            // Verificar que sea el offcanvas de contactos
            if (offcanvasEl && offcanvasEl.id === 'offcanvas-contactos') {
                const container = d.querySelector('#offcanvas-container-contactos');
                if (container) {
                    // Limpiar el contenedor para evitar acumulación de HTML
                    container.innerHTML = '';
                    console.log('[contactos.list] Offcanvas destruido y contenedor limpiado');
                }
            }
        });
    }

    // Inicialización
    function init() {
        if (initialized) {
            // Si ya está inicializado, solo recargar datos
            if (table) {
                table.replaceData();
            }
            return;
        }

        if (!w.Tabulator) {
            console.error('[contactos.list] Tabulator no está disponible');
            return;
        }

        if (!w.TabulatorFactory) {
            console.error('[contactos.list] TabulatorFactory no está disponible');
            return;
        }

        const gridElement = d.querySelector('#grid-contactos');
        if (!gridElement) {
            console.warn('[contactos.list] Contenedor #grid-contactos no encontrado');
            return;
        }

        // ⚠️ CRÍTICO: Verificar que el tab esté visible antes de inicializar
        const tabPane = d.querySelector('#tab-pane-contactos');
        if (tabPane && tabPane.classList.contains('active')) {
            // Tab está visible, inicializar inmediatamente
            initTabulator();
            initListEvents();
            initialized = true;
        } else {
            // Tab está oculto, inicializar pero Tabulator puede fallar
            // Esperaremos al evento shown.bs.tab para inicializar correctamente
            console.log('[contactos.list] Tab de contactos no está visible, esperando evento shown.bs.tab');
        }
    }

    // ⚠️ v2.60: Lazy Loading para Tabs de Bootstrap
    // Tabulator falla si se inicializa en un Tab oculto, así que esperamos al evento shown.bs.tab
    d.addEventListener('shown.bs.tab', function(e) {
        // Verificar que sea el tab de contactos
        const target = e.target;
        const tabId = target.getAttribute('id');
        const tabTarget = target.getAttribute('data-bs-target');
        
        if (tabId === 'tab-contactos' || tabTarget === '#tab-pane-contactos') {
            console.log('[contactos.list] Tab de contactos activado, inicializando Tabulator...');
            
            if (!initialized) {
                // Primera vez que se muestra el tab, inicializar
                init();
            } else if (table) {
                // Ya está inicializado, pero recargar datos para asegurar que las columnas se dibujen correctamente
                setTimeout(() => {
                    if (table) {
                        table.redraw(true); // Forzar redibujado completo
                        table.replaceData(); // Recargar datos
                    }
                }, 100);
            }
        }
    });

    // Auto-inicialización con lazy loading
    // ⚠️ v2.60: Inicializar solo cuando el contenedor sea visible (tab activo)
    function tryInit() {
        if (initialized) return;
        
        const gridElement = d.querySelector('#grid-contactos');
        if (!gridElement) return;

        // Verificar si el tab está visible
        const tabPane = d.querySelector('#tab-pane-contactos');
        if (tabPane && tabPane.classList.contains('active') && tabPane.classList.contains('show')) {
            init();
        }
    }
    
    if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
        w.DOMUtils.onVisibleOnce('#tab-pane-contactos', tryInit);
    }
    
    // Fallback: inicializar en DOMContentLoaded o inmediatamente
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', tryInit);
    } else {
        tryInit();
    }

    // Exponer API pública
    w.ContactosListModule = {
        refresh: function() {
            // ⚠️ CRÍTICO: Recargar tabla con paginación remota
            if (table) {
                // Resetear a la primera página y recargar
                table.setPage(1).then(() => {
                    // replaceData() sin parámetros usa la URL configurada en ajaxURLGenerator
                    table.replaceData();
                }).catch(err => {
                    console.error('[contactos.list] Error al refrescar tabla:', err);
                    // Fallback: intentar recargar directamente
                    try {
                        table.replaceData();
                    } catch (fallbackErr) {
                        console.error('[contactos.list] Error en fallback de refresh:', fallbackErr);
                    }
                });
            }
        },
        getTable: function() {
            return table;
        },
        init: function() {
            if (!initialized) {
                init();
            }
        }
    };

})(window, document);
