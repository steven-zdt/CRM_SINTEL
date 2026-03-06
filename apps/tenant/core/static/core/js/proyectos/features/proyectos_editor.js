/**
 * Feature: Editor - Proyectos v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en lib/http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 */
(function(w, d) {
    'use strict';

    const MOD = '[proyectos.editor]';

    /**
     * Recolectar datos del formulario del Offcanvas
     * @returns {Object} Datos del proyecto
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-proyecto');
        if (!form) {
            console.error(`${MOD} Formulario #form-proyecto no encontrado`);
            return null;
        }

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Remover campos vacíos
        Object.keys(data).forEach(key => {
            if (data[key] === '' || data[key] === null) {
                delete data[key];
            }
        });

        // ⚠️ Conversión de tipos numéricos
        if (data.cliente_id) {
            data.cliente_id = parseInt(data.cliente_id);
        }
        if (data.responsable_actual_id) {
            data.responsable_actual_id = parseInt(data.responsable_actual_id);
        }
        if (data.valor_contrato_proyectado) {
            data.valor_contrato_proyectado = parseFloat(data.valor_contrato_proyectado);
        }

        // ⚠️ Manejo del select de cliente (si existe)
        const clienteSelect = form.querySelector('#proyecto-cliente-select');
        if (clienteSelect && clienteSelect.value) {
            data.cliente_id = parseInt(clienteSelect.value);
            // Si hay un cliente seleccionado, obtener su nombre del option
            const selectedOption = clienteSelect.options[clienteSelect.selectedIndex];
            if (selectedOption && selectedOption.text) {
                // Extraer nombre del texto del option (formato: "Nombre (Documento)")
                const match = selectedOption.text.match(/^(.+?)\s*\(/);
                if (match) {
                    data.cliente_nombre = match[1].trim();
                }
            }
        }

        return data;
    }

    /**
     * Guardar proyecto
     * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
     * ⚠️ v2.60: Maneja Offcanvas y Error Boundary
     */
    async function guardarProyecto() {
        const data = recolectarDatosFormulario();
        if (!data) {
            return;
        }

        const id = d.querySelector('#proyecto-id')?.value;
        const offcanvasEl = d.querySelector('#offcanvas-proyecto');
        
        // ⚠️ Error Boundary v2.60: Guardar estado original del botón
        const btnGuardar = d.querySelector('#btn-guardar-proyecto');
        const btnOriginalText = btnGuardar?.innerHTML || '';
        const btnOriginalDisabled = btnGuardar?.disabled || false;
        
        // ⚠️ Error Boundary v2.60: Mostrar estado de loading
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        let res;
        if (id) {
            // Actualizar proyecto existente
            res = await w.http('PATCH', `/api/v1/proyectos/${id}/`, data);
        } else {
            // Crear nuevo proyecto
            res = await w.http('POST', '/api/v1/proyectos/', data);
        }

        // ⚠️ Error Boundary v2.60: Restaurar estado del botón
        if (btnGuardar) {
            btnGuardar.disabled = btnOriginalDisabled;
            btnGuardar.innerHTML = btnOriginalText;
        }

        // ⚠️ v2.60: Aislamiento Gradual - Manejo de errores con UIManager
        if (!res.ok) {
            // ⚠️ Error Boundary: Inyectar errores en el contenedor de feedback
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError(res, MOD, {
                    errorContainerSelector: '#form-proyecto-feedback'
                });
            } else {
                // Fallback: Mostrar error básico
                const errorContainer = d.querySelector('#form-proyecto-feedback');
                if (errorContainer) {
                    errorContainer.classList.remove('d-none');
                    errorContainer.textContent = res.data?.detail || 'Error al guardar el proyecto';
                }
            }
            return;
        }

        // ⚠️ Éxito: Cerrar Offcanvas, mostrar feedback y disparar evento
        if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
            const offcanvasInstance = bootstrap.Offcanvas.getInstance(offcanvasEl);
            if (offcanvasInstance) {
                offcanvasInstance.hide();
            }
        }

        // ⚠️ Feedback visual
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
            w.SintelFeedback.success('Proyecto guardado correctamente');
        }

        // ⚠️ Evento personalizado para recarga reactiva del grid
        d.dispatchEvent(new Event('proyectoGuardado'));

        console.log(`${MOD} Proyecto guardado correctamente`);
    }

    /**
     * Configurar listeners del formulario
     */
    function initEditorEvents() {
        const form = d.querySelector('#form-proyecto');
        if (!form) {
            console.warn(`${MOD} Formulario #form-proyecto no encontrado`);
            return;
        }

        // Listener para el botón de guardar
        const btnGuardar = d.querySelector('#btn-guardar-proyecto');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', (e) => {
                e.preventDefault();
                guardarProyecto();
            });
        }

        // Listener para el submit del formulario (prevenir submit tradicional)
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            guardarProyecto();
        });

        // ⚠️ Sincronización del select de cliente con los campos manuales
        const clienteSelect = form.querySelector('#proyecto-cliente-select');
        const clienteIdInput = form.querySelector('#proyecto-cliente-id');
        const clienteNombreInput = form.querySelector('#proyecto-cliente-nombre');

        if (clienteSelect && clienteIdInput && clienteNombreInput) {
            clienteSelect.addEventListener('change', (e) => {
                if (e.target.value) {
                    // Si se selecciona un cliente del catálogo, sincronizar campos
                    const selectedOption = e.target.options[e.target.selectedIndex];
                    if (selectedOption) {
                        clienteIdInput.value = e.target.value;
                        // Extraer nombre del texto del option
                        const match = selectedOption.text.match(/^(.+?)\s*\(/);
                        if (match) {
                            clienteNombreInput.value = match[1].trim();
                        }
                    }
                } else {
                    // Si se limpia el select, limpiar también los campos manuales
                    clienteIdInput.value = '';
                    clienteNombreInput.value = '';
                }
            });
        }

        // ⚠️ Limpieza: Limpiar formulario cuando se cierre el Offcanvas
        const offcanvasEl = d.querySelector('#offcanvas-proyecto');
        if (offcanvasEl) {
            offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
                // Limpiar contenedor de errores
                const errorContainer = d.querySelector('#form-proyecto-feedback');
                if (errorContainer) {
                    errorContainer.classList.add('d-none');
                    errorContainer.textContent = '';
                }
                
                // Limpiar formulario (opcional, depende de si queremos mantener datos)
                // form.reset();
            });
        }

        console.log(`${MOD} Event listeners del editor configurados`);
    }

    // Inicialización principal
    function init() {
        console.log(`${MOD} Inicializando módulo de editor...`);
        
        // ⚠️ Lazy Loading: Solo inicializar cuando el Offcanvas esté presente
        const offcanvasEl = d.querySelector('#offcanvas-proyecto');
        if (offcanvasEl) {
            initEditorEvents();
        } else {
            // Si no existe, escuchar cuando se cree (HTMX)
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1 && node.id === 'offcanvas-proyecto') {
                            initEditorEvents();
                            observer.disconnect();
                        }
                    });
                });
            });

            const container = d.querySelector('#offcanvas-container-proyectos');
            if (container) {
                observer.observe(container, { childList: true, subtree: true });
            }
        }
    }

    // Auto-inicializar cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ⚠️ HTMX: Reinicializar cuando se cargue el Offcanvas vía HTMX
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', (event) => {
            if (event.detail.target.id === 'offcanvas-container-proyectos') {
                // Pequeño delay para asegurar que el DOM esté completamente renderizado
                setTimeout(() => {
                    initEditorEvents();
                }, 50);
            }
        });
    }

    // ⚠️ API Pública: Exponer funciones para uso externo
    w.ProyectosEditorModule = {
        init,
        guardarProyecto
    };

    // ⚠️ Compatibilidad: Alias para uso legacy
    if (!w.ProyectosModule) {
        w.ProyectosModule = {};
    }
    w.ProyectosModule.guardarProyecto = guardarProyecto;

})(window, document);
