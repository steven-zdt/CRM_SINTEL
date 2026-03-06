/**
 * plantillas_list.js - Lista de Plantillas v2.60
 * ⚠️ Arquitectura: Tabulator Nativo con decodificador DRF manual para evitar bugs del Factory.
 */
(function(w, d) {
    'use strict';

    const selector = '#grid-plantillas-offcanvas';

    function accionesFormatter(cell) {
        const data = cell.getRow().getData();
        if (!data || !data.id) return '';
        const id = data.id;
        
        // ⚠️ v2.60: Detectar si estamos en el contexto del editor (para mostrar botón "Seleccionar")
        const isEditorContext = d.querySelector('#editor-select-perfil') !== null;
        
        let botonSeleccionar = '';
        if (isEditorContext) {
            botonSeleccionar = `
                <button class="btn btn-sm btn-outline-success p-1" onclick="window.SintelPlantillas.seleccionar(${id})" title="Seleccionar Plantilla">
                    <i class="bi bi-check-lg"></i>
                </button>
            `;
        }
        
        return `
            <div class="d-flex justify-content-center gap-1">
                ${botonSeleccionar}
                <button class="btn btn-sm btn-outline-info p-1" onclick="window.SintelPlantillas.ver(${id})" title="Ver Detalles">
                    <i class="bi bi-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-warning p-1" onclick="window.SintelPlantillas.editar(${id})" title="Editar Plantilla">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger p-1" onclick="window.SintelPlantillas.eliminar(${id})" title="Eliminar Plantilla">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
    }

    const PlantillasListModule = {
        table: null,
        init() {
            const container = d.querySelector(selector);
            if (!container) return;

            const tableConfig = {
                ajaxURL: "/api/v1/cotizaciones/configuracion/", // ⚠️ Endpoint correcto según logs
                layout: "fitColumns",
                pagination: true,
                paginationMode: "remote",
                paginationSize: 10,
                placeholder: "No se encontraron plantillas en la base de datos",
                // ⚠️ v2.60: Parámetros fijos para filtrar solo activos
                ajaxParams: {
                    es_activo: true
                },
                // ⚠️ Decodificador DRF manual integrado (API-First)
                ajaxResponse: function(url, params, response) {
                    console.log('[plantillas_list] Respuesta de API:', { url, params, response });
                    return {
                        data: response.results || response.data || response || [],
                        last_page: response.count ? Math.ceil(response.count / 10) : 1
                    };
                },
                columns: [
                    { title: "Nombre", field: "nombre_configuracion", headerFilter: "input", minWidth: 150 },
                    { 
                        title: "Secuencia", 
                        field: "secuencia_display",
                        width: 180,
                        formatter: function(cell) {
                            const row = cell.getRow().getData();
                            const prefijo = row.prefijo_secuencia || '';
                            const sufijo = row.sufijo_secuencia || '';
                            const semilla = row.semilla_inicial || 1;
                            // Mostrar formato: "Prefijo Semilla Sufijo" (ej: "STS. 0001-2026")
                            const numeroFormateado = String(semilla).padStart(4, '0');
                            return `${prefijo}${numeroFormateado}${sufijo}` || '--';
                        }
                    },
                    { 
                        title: "Días Validez", 
                        field: "dias_validez", 
                        width: 120, 
                        hozAlign: "center",
                        formatter: function(cell) {
                            const dias = cell.getValue();
                            return dias ? `${dias} días` : '--';
                        }
                    },
                    { title: "Activa", field: "es_activo", formatter: "tickCross", width: 80, hozAlign: "center" },
                    { title: "Acciones", formatter: accionesFormatter, width: 130, headerSort: false, hozAlign: "center" }
                ]
            };

            // ⚠️ Inicialización nativa forzada para evitar corrupción de configuración del Factory
            this.table = new w.Tabulator(selector, tableConfig);
            w.cotizacionesConfigPage = { table: this.table };
        }
    };

    /**
     * Detecta el contenedor correcto según el contexto (principal o secundario)
     * @returns {string} ID del contenedor offcanvas a usar
     */
    function detectarContenedor() {
        // Si el grid está dentro de un offcanvas secundario, usar ese contenedor
        const gridElement = d.querySelector(selector);
        if (gridElement) {
            const offcanvasSecundario = gridElement.closest('#offcanvas-container-secundario');
            if (offcanvasSecundario) {
                return '#offcanvas-container-secundario';
            }
        }
        // Por defecto, usar el contenedor principal
        return '#offcanvas-container';
    }

    // ⚠️ Exposición explícita en window para acceso desde onclick
    w.SintelPlantillas = {
        seleccionar: function(id) {
            // ⚠️ v2.60: Seleccionar plantilla en el editor
            const selectPerfil = d.getElementById('editor-select-perfil');
            if (selectPerfil) {
                selectPerfil.value = String(id);
                
                // Disparar evento change para activar el renderizado dinámico
                const changeEvent = new Event('change', { bubbles: true });
                selectPerfil.dispatchEvent(changeEvent);
                
                // Cerrar offcanvas secundario
                const offcanvasSecundario = d.getElementById('offcanvas-container-secundario');
                if (offcanvasSecundario && window.bootstrap) {
                    const instance = window.bootstrap.Offcanvas.getInstance(offcanvasSecundario);
                    if (instance) {
                        instance.hide();
                    }
                }
                
                if (window.SintelFeedback && typeof window.SintelFeedback.success === 'function') {
                    window.SintelFeedback.success('Plantilla seleccionada correctamente');
                }
            } else {
                console.warn('[plantillas_list] No se encontró el select de perfil en el editor');
            }
        },
        ver: function(id) {
            // ⚠️ Guardar el ID globalmente para que el script del partial lo lea
            window.lastViewedPlantillaId = id;
            
            const targetContainer = detectarContenedor();
            const url = `/cotizaciones/partials/configuracion/ver/${id}/`;
            if (typeof htmx !== 'undefined') {
                htmx.ajax('GET', url, {
                    target: targetContainer,
                    swap: 'innerHTML'
                });
            } else {
                console.error('[plantillas_list] HTMX no está disponible');
                if (window.UIManager) {
                    window.UIManager.notifyError({ status: 500, data: { detail: 'HTMX no está disponible' } }, 'Ver Plantilla');
                }
            }
        },
        editar: function(id) {
            const targetContainer = detectarContenedor();
            const url = `/cotizaciones/partials/configuracion/editar/${id}/`;
            if (typeof htmx !== 'undefined') {
                htmx.ajax('GET', url, { target: targetContainer, swap: 'innerHTML' });
            }
        },
        eliminar: async function(id) {
            // 🛡️ Blindaje v2.60: Verificar existencia de la función antes de invocarla
            let confirmar = false;
            const mensajeHeader = '¿Eliminar plantilla?';
            const mensajeBody = 'Esta acción no se puede deshacer y podría afectar cotizaciones futuras.';

            if (window.SintelFeedback && typeof window.SintelFeedback.confirm === 'function') {
                // Usar la librería personalizada si está disponible
                confirmar = await window.SintelFeedback.confirm(mensajeHeader, mensajeBody);
            } else if (window.Swal) {
                // Fallback a SweetAlert2 si está disponible directamente
                const result = await window.Swal.fire({
                    title: mensajeHeader,
                    text: mensajeBody,
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonText: 'Sí, eliminar',
                    cancelButtonText: 'Cancelar'
                });
                confirmar = result.isConfirmed;
            } else {
                // Fallback final: Confirmación nativa del navegador
                confirmar = confirm(`${mensajeHeader}\n\n${mensajeBody}`);
            }

            if (!confirmar) return;

            // Ejecutar la eliminación
            const res = await window.http('DELETE', `/api/v1/cotizaciones/configuracion/${id}/`);
            if (!res.ok) return window.UIManager?.notifyError(res, 'Plantillas');
            
            if (window.SintelFeedback && typeof window.SintelFeedback.success === 'function') {
                window.SintelFeedback.success('Plantilla eliminada exitosamente');
            } else {
                console.log('[plantillas_list] Plantilla eliminada (feedback nativo)');
            }

            // Refrescar tabla
            if (window.cotizacionesConfigPage?.table) window.cotizacionesConfigPage.table.replaceData();
        }
    };
    
    // ⚠️ Asegurar exposición global explícita (w ya es window, pero por claridad)
    window.SintelPlantillas = w.SintelPlantillas;

    function safeInit() {
        if (!PlantillasListModule.table) PlantillasListModule.init();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', safeInit);
    } else {
        safeInit();
    }

    d.body.addEventListener('htmx:afterSwap', function(event) {
        if (event.detail.target.id === 'offcanvas-container' || event.detail.target.querySelector(selector)) {
            setTimeout(safeInit, 50);
        }
    });

})(window, document);
