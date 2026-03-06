/**
 * ui-manager.js - Gestor global de Interfaz y Errores (Error Boundary)
 * Procesa respuestas de HTMX y fetch para pintar feedback visual.
 */
(function (w, d) {
    'use strict';

    w.UIManager = {
        /**
         * Maneja errores provenientes de htmx:response-error
         * @param {Object} htmxDetail - event.detail de HTMX
         * @param {String} moduleName - Nombre del módulo para logs
         * @param {Object} options - { errorContainerSelector: '#id-del-div' }
         */
        handleError: function (htmxDetail, moduleName, options = {}) {
            console.warn(`[UIManager][${moduleName}] Procesando error...`);
            
            const xhr = htmxDetail.xhr;
            let responseData = {};
            
            try {
                responseData = JSON.parse(xhr.responseText);
            } catch (e) {
                responseData = { error: "Ocurrió un error inesperado en el servidor." };
            }

            const container = d.querySelector(options.errorContainerSelector);
            
            // 1. Limpiar estados previos (quitar clases is-invalid de los inputs)
            const form = container ? container.closest('form') : null;
            if (form) {
                form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
                form.querySelectorAll('.invalid-feedback.dynamic').forEach(el => el.remove());
            }

            // 2. Renderizar error en el contenedor global del formulario
            if (container) {
                container.innerHTML = '';
                container.classList.remove('d-none', 'alert-success');
                container.classList.add('alert', 'alert-danger', 'mt-3');

                // Si es un error general de negocio (ej: "Ya existe un empleado...")
                if (responseData.error) {
                    container.innerHTML = `<strong><i class="fas fa-exclamation-triangle"></i> Atención:</strong> ${responseData.error}`;
                    if (responseData.detail && typeof responseData.detail === 'string') {
                        container.innerHTML += `<br><small>${responseData.detail}</small>`;
                    }
                } 
                // Si es un diccionario de errores de validación de DRF
                else {
                    let errorHtml = '<ul class="mb-0">';
                    for (const [field, messages] of Object.entries(responseData)) {
                        const msgText = Array.isArray(messages) ? messages.join(', ') : messages;
                        errorHtml += `<li><strong>${field.toUpperCase()}:</strong> ${msgText}</li>`;
                        
                        // Opcional: Pintar de rojo el input específico
                        if (form) {
                            const input = form.querySelector(`[name="${field}"]`);
                            if (input) {
                                input.classList.add('is-invalid');
                            }
                        }
                    }
                    errorHtml += '</ul>';
                    container.innerHTML = errorHtml;
                }
            } else {
                // Fallback si no hay contenedor definido (ej: usar Toast o Alert)
                alert(responseData.error || "Ocurrió un error de validación. Revise los datos.");
            }
        },

        /**
         * Limpia el contenedor de errores (útil para inyectar en hx-on::before-request)
         */
        clearErrors: function (selector) {
            const container = d.querySelector(selector);
            if (container) {
                container.classList.add('d-none');
                container.innerHTML = '';
            }
            const form = container ? container.closest('form') : null;
            if (form) {
                form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            }
        }
    };
})(window, document);
