/**
 * Feature: Editor - Empresa v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - Sintel.Core.Http (F32.7, core-http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 */
(function(w, d) {
    'use strict';

    const MOD = '[empresa.editor]';

    /**
     * Recolectar datos del formulario del Offcanvas
     * ⚠️ v2.60: Retorna FormData nativo para soportar archivos (multipart/form-data)
     * @returns {FormData|null} FormData con todos los campos del formulario, incluyendo archivos
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-empresa');
        if (!form) {
            console.error(`${MOD} Formulario #form-empresa no encontrado`);
            return null;
        }

        // ⚠️ v2.60: Usar FormData nativo directamente desde el formulario
        // Esto preserva los archivos (File objects) sin convertirlos a objetos JSON vacíos
        const formData = new FormData(form);
        
        // ⚠️ v2.60: Remover campos vacíos del FormData (excepto archivos)
        // Nota: No podemos iterar y eliminar directamente, así que reconstruimos el FormData
        const cleanFormData = new FormData();
        
        // Iterar sobre todos los campos del FormData original
        for (const [key, value] of formData.entries()) {
            // ⚠️ CRÍTICO: Preservar archivos (File objects) siempre
            if (value instanceof File) {
                cleanFormData.append(key, value);
                console.log(`${MOD} Archivo detectado: ${key} = File(${value.name}, ${value.size} bytes, ${value.type})`);
            } 
            // ⚠️ CRÍTICO: Preservar valores no vacíos
            else if (value !== '' && value !== null && value !== undefined) {
                cleanFormData.append(key, value);
            }
            // ⚠️ Campos vacíos se omiten automáticamente
        }

        // ⚠️ v2.60: Verificar si hay un archivo de logo específicamente
        const logoFile = form.querySelector('#empresa-logo')?.files[0];
        if (logoFile) {
            console.log(`${MOD} Logo file detectado y agregado al FormData:`, logoFile.name, logoFile.size, 'bytes');
        }

        return cleanFormData;
    }

    /**
     * Guardar empresa
     * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
     * ⚠️ v2.60: Maneja Offcanvas y Error Boundary
     */
    async function guardarEmpresa() {
        const data = recolectarDatosFormulario();
        if (!data) {
            return;
        }

        const id = d.querySelector('#empresa-id')?.value;
        const offcanvasEl = d.querySelector('#offcanvas-empresa');
        
        // ⚠️ Error Boundary v2.60: Guardar estado original del botón
        const btnGuardar = d.querySelector('#btn-guardar-empresa');
        const btnOriginalText = btnGuardar?.innerHTML || '';
        const btnOriginalDisabled = btnGuardar?.disabled || false;
        
        // ⚠️ Error Boundary v2.60: Mostrar estado de loading
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        // ⚠️ v2.60: Usar Core API (PATCH /api/v1/core/empresa/) para crear/actualizar (singleton)
        // ⚠️ IMPORTANTE: data es FormData nativo, se enviará como multipart/form-data
        let res;
        if (id) {
            // Actualizar empresa existente (Core API)
            res = await w.Sintel.Core.Http.request('PATCH', '/api/v1/core/empresa/', data);
        } else {
            // Crear nueva empresa (Core API - singleton pattern)
            res = await w.Sintel.Core.Http.request('PATCH', '/api/v1/core/empresa/', data);
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
                    errorContainerSelector: '#form-empresa-feedback'
                });
            } else {
                // Fallback: Mostrar error básico
                const errorContainer = d.querySelector('#form-empresa-feedback');
                if (errorContainer) {
                    errorContainer.classList.remove('d-none');
                    errorContainer.textContent = res.data?.detail || 'Error al guardar la empresa';
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
            w.SintelFeedback.success('Empresa guardada correctamente');
        }

        // ⚠️ Evento personalizado para recarga reactiva del grid
        d.dispatchEvent(new Event('empresaGuardada'));

        console.log(`${MOD} Empresa guardada correctamente`);
    }

    /**
     * Configurar listeners del formulario
     */
    function initEditorEvents() {
        const form = d.querySelector('#form-empresa');
        if (!form) {
            console.warn(`${MOD} Formulario #form-empresa no encontrado`);
            return;
        }

        // Guard (FE-A2): init() [MutationObserver/DOMContentLoaded] y el
        // listener htmx:afterSettle pueden llamar initEditorEvents() para el
        // mismo form — sin esto, el submit queda registrado 2 veces.
        if (form.dataset.editorInitialized) return;
        form.dataset.editorInitialized = 'true';

        // Listener para el botón de guardar
        const btnGuardar = d.querySelector('#btn-guardar-empresa');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', (e) => {
                e.preventDefault();
                guardarEmpresa();
            });
        }

        // Listener para el submit del formulario (prevenir submit tradicional)
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            guardarEmpresa();
        });

        // ⚠️ Limpieza: Limpiar formulario cuando se cierre el Offcanvas
        const offcanvasEl = d.querySelector('#offcanvas-empresa');
        if (offcanvasEl) {
            offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
                // Limpiar contenedor de errores
                const errorContainer = d.querySelector('#form-empresa-feedback');
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
        const offcanvasEl = d.querySelector('#offcanvas-empresa');
        if (offcanvasEl) {
            initEditorEvents();
        } else {
            // Si no existe, escuchar cuando se cree (HTMX)
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1 && node.id === 'offcanvas-empresa') {
                            initEditorEvents();
                            observer.disconnect();
                        }
                    });
                });
            });

            const container = d.querySelector('#offcanvas-container-empresa');
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

    // htmx:afterSettle garantiza DOM estable — no usar afterSwap ni setTimeout (race condition)
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSettle', (event) => {
            if (event.detail.target.id === 'offcanvas-container-empresa') {
                initEditorEvents();
            }
        });
    }

    // ⚠️ API Pública: Exponer funciones para uso externo
    w.EmpresaEditorModule = {
        init,
        guardarEmpresa
    };

    // ⚠️ Compatibilidad: Alias para uso legacy
    w.EmpresaModule = w.EmpresaEditorModule;

})(window, document);
