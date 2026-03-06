/**
 * resoluciones.page.js - v2.40
 * ⚠️ Módulo independiente para gestión de Resoluciones DIAN
 * ⚠️ Migrado a TabulatorFactory - Optimizado para SINTEL v2.40
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API con paginación estándar
 * 
 * ⚠️ INMUTABILIDAD:
 * - Las resoluciones son documentos legales y no deben editarse
 * - Solo se pueden crear nuevas o desactivar/eliminar (si no tienen uso)
 * - Al desactivar/eliminar, DocumentoSoporte conserva su número y prefijo originales (snapshot inalterable)
 * 
 * ⚠️ REGLA CRÍTICA: Solo UNA resolución puede estar vigente por empresa
 */
(function (w, d) {
    'use strict';
  
    const TABLE_SELECTOR = '#grid-resoluciones';
    const SEARCH_SELECTOR = '#search-resolucion';
    const API_URL = '/api/v1/resoluciones-dian/';
    const CONTAINER_ID = '#subtab-resoluciones';
    let table = null;
    let resolucionActiva = null;

    // Helper: Obtener CSRF token
    function getCookie(name) {
        const value = `; ${d.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    // Cargar resolución activa
    async function cargarResolucionActiva() {
        try {
            const res = await w.resolucionesAPI.getActiva();
            if (res.ok && res.data) {
                resolucionActiva = res.data;
            } else {
                resolucionActiva = null;
            }
            actualizarBotonCrear();
        } catch (err) {
            console.error('[resoluciones.page] Error cargando resolución activa:', err);
            resolucionActiva = null;
            actualizarBotonCrear();
        }
    }

    // Ocultar/mostrar botón crear según si hay resolución activa
    function actualizarBotonCrear() {
        const btnCrear = d.querySelector('#btn-crear-resolucion');
        if (btnCrear) {
            if (resolucionActiva) {
                btnCrear.classList.add('d-none');
            } else {
                btnCrear.classList.remove('d-none');
            }
        }
    }

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
                title: "Número Resolución",
                field: "numero_resolucion",
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    return `<span class="fw-bold">${data.numero_resolucion || '-'}</span>`;
                }
            },
            {
                title: "Prefijo",
                field: "prefijo",
                width: 100
            },
            {
                title: "Rango",
                field: "rango_desde",
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    return `${data.rango_desde || '-'} - ${data.rango_hasta || '-'}`;
                }
            },
            {
                title: "Fecha Emisión",
                field: "fecha_resolucion",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '-';
                    try {
                        return new Date(val).toLocaleDateString('es-CO');
                    } catch (e) {
                        return val;
                    }
                }
            },
            {
                title: "Vigencia",
                field: "fecha_fin",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '-';
                    try {
                        return new Date(val).toLocaleDateString('es-CO');
                    } catch (e) {
                        return val;
                    }
                }
            },
            {
                title: "Estado",
                field: "vigente",
                formatter: function(cell) {
                    const data = cell.getValue();
                    if (data === true) {
                        return '<span class="badge bg-success">Vigente</span>';
                    } else {
                        return '<span class="badge bg-secondary">Inactiva</span>';
                    }
                },
                headerSort: false
            },
            {
                title: "Documentos",
                field: "conteo_documentos",
                formatter: function(cell) {
                    const data = cell.getValue();
                    return `<span class="badge bg-info">${data || 0}</span>`;
                },
                headerSort: false
            },
            {
                title: "Acciones",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    const id = rowData.id;
                    const isVigente = rowData.vigente === true;
                    const conteoDocs = rowData.conteo_documentos || 0;
                    const puedeEliminar = !isVigente && conteoDocs === 0;
                    
                    let botones = '';
                    
                    // Si está vigente: solo botón Desactivar
                    if (isVigente) {
                        botones = `
                            <button type="button" class="btn btn-outline-warning btn-desactivar" data-id="${id}" title="Desactivar Resolución">
                                <i class="fas fa-ban"></i> Desactivar
                            </button>
                        `;
                    } else {
                        // Si está inactiva: botón Eliminar (solo si no tiene documentos)
                        if (puedeEliminar) {
                            botones = `
                                <button type="button" class="btn btn-outline-danger btn-delete" data-id="${id}" title="Eliminar Resolución">
                                    <i class="fas fa-trash"></i> Eliminar
                                </button>
                            `;
                        } else {
                            botones = `
                                <button type="button" class="btn btn-outline-secondary" disabled title="No se puede eliminar (tiene ${conteoDocs} documento(s) asociado(s))">
                                    <i class="fas fa-lock"></i> En uso
                                </button>
                            `;
                        }
                    }
                    
                    return `
                        <div class="btn-group btn-group-sm" role="group">
                            ${botones}
                        </div>
                    `;
                },
                headerSort: false,
                hozAlign: "center",
                width: 150
            }
        ];
    }

    // Inicializar tabla con TabulatorFactory
    function initTable() {
        if (!w.TabulatorFactory) {
            console.error('[resoluciones.page] TabulatorFactory no está disponible');
            return null;
        }

        const columns = getColumns();
        table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, columns, {
            searchInputSelector: SEARCH_SELECTOR,
            paginationSize: 10
        });

        // ⚠️ v2.40: Event delegation para botones de acciones
        if (table) {
            const container = d.querySelector(TABLE_SELECTOR);
            if (container) {
                container.addEventListener('click', function(e) {
                    const btn = e.target.closest('button[data-id]');
                    if (!btn) return;
                    
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const id = parseInt(btn.getAttribute('data-id'), 10);
                    if (!id || isNaN(id)) return;
                    
                    if (btn.classList.contains('btn-desactivar')) {
                        desactivarResolucion(id);
                    } else if (btn.classList.contains('btn-delete')) {
                        eliminarResolucion(id);
                    }
                });
            }
        }

        return table;
    }

    // Desactivar resolución
    async function desactivarResolucion(id) {
        if (!confirm('¿Está seguro de desactivar esta resolución? Los documentos ya generados conservarán su número y prefijo originales.')) {
            return;
        }

        try {
            const res = await w.resolucionesAPI.desactivar(id);
            if (res.ok) {
                if (w.notyf) {
                    if (w.SintelFeedback) {
                      w.SintelFeedback.success('Resolución desactivada correctamente');
                }
                await cargarResolucionActiva();
                if (table) {
                    table.replaceData();
                }
            } else {
                const errorMsg = res.data?.message || res.data?.error || 'Error al desactivar resolución';
                if (w.notyf) {
                    if (w.SintelFeedback) {
                      w.SintelFeedback.error(errorMsg);
                } else {
                    if (w.SintelFeedback) {
                      w.SintelFeedback.error(errorMsg);
                }
            }
        } catch (error) {
            console.error('[resoluciones.page] Error desactivando resolución:', error);
            const errorMsg = error.message || 'Error al desactivar resolución';
            if (w.SintelFeedback) {
              w.SintelFeedback.handleAPIError({ status: 500, data: { detail: errorMsg } }, '[resoluciones.page]');
            }
        }
    }

    // Eliminar resolución
    async function eliminarResolucion(id) {
        try {
            // Obtener datos de la resolución para validar
            const resGet = await w.resolucionesAPI.get(id);
            if (!resGet.ok) {
                throw new Error('Error al obtener resolución');
            }

            const data = resGet.data;
            const conteoDocs = data.conteo_documentos || 0;

            if (data.vigente) {
                if (w.SintelFeedback) {
                  w.SintelFeedback.error('No se puede eliminar una resolución vigente. Desactívela primero.');
                }
                return;
            }

            if (conteoDocs > 0) {
                if (w.SintelFeedback) {
                  w.SintelFeedback.error(`No se puede eliminar esta resolución porque tiene ${conteoDocs} documento(s) de soporte asociado(s).`);
                }
                return;
            }

            if (!confirm('¿Está seguro de eliminar esta resolución? Esta acción es irreversible.')) {
                return;
            }

            const res = await w.resolucionesAPI.delete(id);
            if (res.ok || res.status === 204) {
                if (w.notyf) {
                    if (w.SintelFeedback) {
                      w.SintelFeedback.success('Resolución eliminada correctamente');
                }
                await cargarResolucionActiva();
                if (table) {
                    table.replaceData();
                }
            } else {
                const errorMsg = res.data?.message || res.data?.error || 'Error al eliminar resolución';
                if (w.notyf) {
                    if (w.SintelFeedback) {
                      w.SintelFeedback.error(errorMsg);
                } else {
                    if (w.SintelFeedback) {
                      w.SintelFeedback.error(errorMsg);
                }
            }
        } catch (error) {
            console.error('[resoluciones.page] Error eliminando resolución:', error);
            const errorMsg = error.message || 'Error al eliminar resolución';
            if (w.SintelFeedback) {
              w.SintelFeedback.handleAPIError({ status: 500, data: { detail: errorMsg } }, '[resoluciones.page]');
            }
        }
    }

    // Función de refresh
    async function refresh() {
        await cargarResolucionActiva();
        if (table) {
            table.replaceData();
        }
    }

    // Inicializar módulo
    function inicializarModulo() {
        // Cargar resolución activa primero
        cargarResolucionActiva().then(() => {
            // Inicializar tabla con lazy loading
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce(CONTAINER_ID, function() {
                    if (!table) {
                        initTable();
                    }
                });
            } else {
                // Fallback: inicializar inmediatamente
                initTable();
            }
        });
    }

    // Exponer API global
    w.resolucionesPage = {
        refresh: refresh,
        cargarResolucionActiva: cargarResolucionActiva
    };

    // Inicializar cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', inicializarModulo);
    } else {
        inicializarModulo();
    }

    // Re-inicializar cuando se muestre el tab
    const tabElement = d.querySelector('[data-bs-target="' + CONTAINER_ID + '"]');
    if (tabElement) {
        tabElement.addEventListener('shown.bs.tab', function() {
            if (!table) {
                inicializarModulo();
            } else {
                refresh();
            }
        });
    }

})(window, document);
