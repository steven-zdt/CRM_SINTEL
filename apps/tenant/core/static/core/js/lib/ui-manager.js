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
        handleError: function (htmxDetailOrResponse, moduleName, options = {}) {
            console.warn(`[UIManager][${moduleName}] Procesando error...`);
            
            // ⚠️ v2.61: DEBUG - Log detallado del objeto recibido
            console.log(`[UIManager][${moduleName}] DEBUG - Objeto recibido:`, {
                hasXhr: !!(htmxDetailOrResponse && htmxDetailOrResponse.xhr),
                hasStatus: !!(htmxDetailOrResponse && 'status' in htmxDetailOrResponse),
                status: htmxDetailOrResponse?.status,
                ok: htmxDetailOrResponse?.ok,
                hasData: !!(htmxDetailOrResponse && htmxDetailOrResponse.data),
                dataType: typeof htmxDetailOrResponse?.data,
                dataKeys: htmxDetailOrResponse?.data && typeof htmxDetailOrResponse.data === 'object' ? Object.keys(htmxDetailOrResponse.data) : 'N/A',
                fullObject: htmxDetailOrResponse
            });
            
            let responseData = {};
            
            // ⚠️ v2.61: Soporte para dos formatos:
            // 1. HTMX format: { xhr: XMLHttpRequest }
            // 2. HTTP.js format: { ok: boolean, status: number, data: object }
            if (htmxDetailOrResponse && htmxDetailOrResponse.xhr) {
                // Formato HTMX
                const xhr = htmxDetailOrResponse.xhr;
                try {
                    responseData = JSON.parse(xhr.responseText);
                } catch (e) {
                    responseData = { error: "Ocurrió un error inesperado en el servidor." };
                }
            } else if (htmxDetailOrResponse && typeof htmxDetailOrResponse === 'object' && 'status' in htmxDetailOrResponse) {
                // Formato HTTP.js: { ok: boolean, status: number, data: object }
                responseData = htmxDetailOrResponse.data || {};
                // Si no hay data pero hay detail en el objeto raíz, moverlo
                if (!responseData.detail && htmxDetailOrResponse.detail) {
                    responseData.detail = htmxDetailOrResponse.detail;
                }
                console.log(`[UIManager][${moduleName}] DEBUG - responseData extraído:`, responseData);
            } else {
                console.error(`[UIManager][${moduleName}] Formato de error desconocido:`, htmxDetailOrResponse);
                responseData = { error: "Ocurrió un error inesperado en el servidor." };
            }

            const container = d.querySelector(options.errorContainerSelector);
            
            // ⚠️ v2.61: DEBUG - Log del contenedor
            console.log(`[UIManager][${moduleName}] DEBUG - Contenedor:`, {
                selector: options.errorContainerSelector,
                found: !!container,
                container: container
            });
            
            // 1. Limpiar estados previos (quitar clases is-invalid de los inputs)
            const form = container ? container.closest('form') : null;
            if (form) {
                form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
                form.querySelectorAll('.invalid-feedback.dynamic').forEach(el => el.remove());
            }

            // 2. Renderizar error en el contenedor global del formulario
            if (container) {
                console.log(`[UIManager][${moduleName}] DEBUG - Renderizando error en contenedor:`, {
                    hasError: !!responseData.error,
                    hasDetail: !!responseData.detail,
                    detailType: typeof responseData.detail,
                    isDetailArray: Array.isArray(responseData.detail),
                    detailValue: responseData.detail,
                    responseData: responseData
                });
                
                // ⚠️ v2.61: Limpiar y configurar contenedor
                container.innerHTML = '';
                // Remover todas las clases que puedan ocultar el contenedor
                container.classList.remove('d-none', 'alert-success');
                // Asegurar clases de alerta de error
                container.classList.add('alert', 'alert-danger', 'mb-3');
                // Asegurar que el contenedor sea visible
                container.style.display = 'block';

                // ⚠️ v2.61.3: Manejar diferentes formatos de error de DRF
                // 1. Error con campo "error" y "message" (formato mejorado - PRIORIDAD MÁXIMA)
                if (responseData.error && responseData.message) {
                    // ⚠️ Filtrar tracebacks de Python para mostrar solo el mensaje amigable
                    let errorMessage = responseData.message;
                    // Si el mensaje contiene un traceback, extraer solo la parte útil
                    if (errorMessage.includes('Traceback') || errorMessage.includes('File "/')) {
                        // Buscar el mensaje de error real (última línea del traceback)
                        const lines = errorMessage.split('\n');
                        const lastLine = lines[lines.length - 1];
                        // Si la última línea contiene "DETAIL:" o un mensaje útil, usarla
                        if (lastLine.includes('DETAIL:') || lastLine.includes('already exists') || lastLine.includes('duplicate')) {
                            errorMessage = lastLine.replace('DETAIL:', '').trim();
                        } else {
                            // Usar el mensaje del campo "detail" si está disponible
                            errorMessage = responseData.detail || responseData.message;
                        }
                    }
                    container.innerHTML = `<strong><i class="bi bi-exclamation-triangle me-2"></i>Error:</strong> ${errorMessage}`;
                }
                // 2. Error con campo "error" solamente (formato legacy)
                else if (responseData.error) {
                    container.innerHTML = `<strong><i class="bi bi-exclamation-triangle me-2"></i>Atención:</strong> ${responseData.error}`;
                    if (responseData.detail && typeof responseData.detail === 'string') {
                        container.innerHTML += `<br><small>${responseData.detail}</small>`;
                    }
                } 
                // 2. Error con campo "detail" (formato DRF estándar) - PRIORIDAD ALTA
                else if (responseData.detail) {
                    let detailMessage = '';
                    if (typeof responseData.detail === 'string') {
                        detailMessage = responseData.detail;
                    } else if (Array.isArray(responseData.detail)) {
                        // ⚠️ v2.61: Si detail es un array, unir los mensajes
                        detailMessage = responseData.detail.join(', ');
                        console.log(`[UIManager][${moduleName}] DEBUG - Mensaje de array detail:`, detailMessage);
                    } else if (typeof responseData.detail === 'object') {
                        // Si detail es un objeto, aplanarlo
                        const detailFields = Object.keys(responseData.detail);
                        const detailMessages = detailFields.map(field => {
                            const fieldErrors = Array.isArray(responseData.detail[field]) 
                                ? responseData.detail[field].join(', ')
                                : String(responseData.detail[field]);
                            return `${field}: ${fieldErrors}`;
                        });
                        detailMessage = detailMessages.join(' | ');
                    }
                    
                    // ⚠️ v2.61.3: Filtrar tracebacks de Python
                    if (detailMessage.includes('Traceback') || detailMessage.includes('File "/')) {
                        // Buscar el mensaje de error real (última línea del traceback o mensaje útil)
                        const lines = detailMessage.split('\n');
                        // Buscar líneas con "DETAIL:", "already exists", "duplicate", etc.
                        const usefulLines = lines.filter(line => 
                            line.includes('DETAIL:') || 
                            line.includes('already exists') || 
                            line.includes('duplicate') ||
                            line.includes('IntegrityError') ||
                            line.includes('UniqueViolation')
                        );
                        if (usefulLines.length > 0) {
                            // Extraer el mensaje útil
                            let usefulMsg = usefulLines[usefulLines.length - 1];
                            // Limpiar el mensaje
                            usefulMsg = usefulMsg.replace('DETAIL:', '').replace('IntegrityError:', '').replace('UniqueViolation:', '').trim();
                            // Si contiene "already exists", formatear mejor
                            const codigoMatch = usefulMsg.match(/Key \(codigo\)=\(([^)]+)\)/);
                            if (codigoMatch) {
                                const codigo = codigoMatch[1];
                                detailMessage = `Ya existe un producto con el código '${codigo}'. Por favor, use un código diferente.`;
                            } else {
                                detailMessage = usefulMsg || 'Error de integridad: El producto no puede ser creado. Verifique que los datos sean únicos.';
                            }
                        } else {
                            // Si no hay líneas útiles, usar un mensaje genérico
                            detailMessage = 'Error al procesar la solicitud. Por favor, verifique los datos e intente nuevamente.';
                        }
                    }
                    
                    // ⚠️ v2.61: Asegurar que el mensaje no esté vacío
                    if (!detailMessage) {
                        detailMessage = 'Error desconocido al procesar la solicitud.';
                    }
                    
                    container.innerHTML = `<strong><i class="bi bi-exclamation-triangle me-2"></i>Error:</strong> ${detailMessage}`;
                    console.log(`[UIManager][${moduleName}] DEBUG - HTML renderizado:`, container.innerHTML);
                    console.log(`[UIManager][${moduleName}] DEBUG - Contenedor visible:`, {
                        hasDNone: container.classList.contains('d-none'),
                        display: container.style.display,
                        computedDisplay: window.getComputedStyle(container).display,
                        innerHTML: container.innerHTML.substring(0, 100)
                    });
                }
                // 3. Diccionario de errores de validación de DRF (por campo)
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
        },

        /**
         * ⚠️ DEPRECATED v2.61.3: Usar handleError() en su lugar
         * Notifica un error de forma simple (fallback)
         * @param {Object} response - Respuesta de error
         * @param {String} moduleName - Nombre del módulo para logs
         */
        notifyError: function (response, moduleName) {
            console.warn(`[UIManager][${moduleName}] notifyError() está DEPRECATED. Use handleError() en su lugar.`);
            // Fallback: usar handleError con opciones por defecto
            this.handleError(response, moduleName, {
                errorContainerSelector: '#form-inventario-feedback'
            });
        },

        /**
         * Maneja modales/offcanvas (abrir/cerrar)
         * @param {String} selector - Selector del modal/offcanvas
         * @param {String} action - 'show' o 'hide'
         */
        handleModal: function (selector, action) {
            const el = d.querySelector(selector);
            if (!el) {
                console.warn(`[UIManager] Elemento ${selector} no encontrado`);
                return;
            }

            if (typeof bootstrap === 'undefined' || !bootstrap) {
                console.warn(`[UIManager] Bootstrap no está disponible`);
                return;
            }

            if (selector.includes('offcanvas')) {
                const instance = bootstrap.Offcanvas.getInstance(el) || bootstrap.Offcanvas.getOrCreateInstance(el);
                if (action === 'show') {
                    instance.show();
                } else if (action === 'hide') {
                    instance.hide();
                }
            } else {
                const instance = bootstrap.Modal.getInstance(el) || bootstrap.Modal.getOrCreateInstance(el);
                if (action === 'show') {
                    instance.show();
                } else if (action === 'hide') {
                    instance.hide();
                }
            }
        }
    };
})(window, document);
