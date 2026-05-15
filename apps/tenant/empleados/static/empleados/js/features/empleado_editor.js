/**
 * Empleado Editor Module - Formulario de Empleado (Crear/Editar)
 * 
 * Namespace: window.Sintel.Empleados.EmpleadoEditor
 * Versión: v2.61.4
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};

    const MOD = '[EmpleadoEditor]';
    const API_URL = '/api/v1/empleados/';
    const CONTAINER_ID = 'offcanvas-container-empleados';

    /**
     * Abrir offcanvas de empleado (Crear o Editar)
     */
    async function open(id = null) {
        let url = `${API_URL}gestor-offcanvas/?tipo=empleado`;
        if (id) url += `&id=${id}`;

        console.log(`${MOD} Cargando offcanvas: ${url}`);
        
        try {
            await htmx.ajax('GET', url, {
                target: `#${CONTAINER_ID}`,
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al cargar el formulario de empleado');
        }
    }

    /**
     * Listener para activar offcanvas tras inyección HTMX
     */
    function setupOffcanvasLoadListener() {
        document.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail.target;
            if (!target || target.id !== CONTAINER_ID) return;

            const offcanvasEl = target.querySelector('.offcanvas');
            if (offcanvasEl && window.bootstrap) {
                console.log(`${MOD} Activando offcanvas: ${offcanvasEl.id}`);
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                bsOffcanvas.show();

                // Vincular validador al formulario
                const form = offcanvasEl.querySelector('form');
                if (form) {
                    form.addEventListener('submit', handleSubmit);

                    // ── Listeners para botones de guardar ────────────────────
                    const btnGuardar = offcanvasEl.querySelector('[id="btn-guardar-empleado"]');
                    const btnCrear = offcanvasEl.querySelector('[id="btn-crear-empleado"]');

                    if (btnGuardar) {
                        btnGuardar.addEventListener('click', () => {
                            form.dispatchEvent(new Event('submit'));
                        });
                    }
                    if (btnCrear) {
                        btnCrear.addEventListener('click', () => {
                            form.dispatchEvent(new Event('submit'));
                        });
                    }

                    // Inicializar buscador de cuentas contables (v3.5.0)
                    initCuentaContableSearch(offcanvasEl);
                }
            }
        });
    }

    /**
     * Handler global para respuestas exitosas de HTMX en empleados
     */
    function setupHTMXListeners() {
        document.body.addEventListener('htmx:afterRequest', handleAfterRequest);
    }

    /**
     * Handler para submit del formulario
     */
    function handleSubmit(e) {
        e.preventDefault();
        const form = e.target;

        // Validar campos requeridos
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('is-invalid');
            } else {
                field.classList.remove('is-invalid');
            }
        });

        if (!isValid) {
            if (window.UIManager) {
                window.UIManager.notifyError('Por favor complete todos los campos requeridos');
            }
            return false;
        }

        // Recolectar datos del formulario
        submitEmpleado(form);
        return false;
    }

    /**
     * Enviar formulario de empleado (crear o editar)
     */
    async function submitEmpleado(form) {
        // Determinar si es crear o editar
        const offcanvas = form.closest('.offcanvas');
        const empleadoUuid = offcanvas?.dataset.empleadoUuid;

        // Recolectar todos los campos del formulario
        const data = {
            // ── Identificación ──
            tipo_documento: form.querySelector('[name="tipo_documento"]')?.value || '',
            numero_documento: form.querySelector('[name="numero_documento"]')?.value || '',
            primer_nombre: form.querySelector('[name="primer_nombre"]')?.value || '',
            segundo_nombre: form.querySelector('[name="segundo_nombre"]')?.value || null,
            primer_apellido: form.querySelector('[name="primer_apellido"]')?.value || '',
            segundo_apellido: form.querySelector('[name="segundo_apellido"]')?.value || null,

            // ── Contacto ──
            email: form.querySelector('[name="email"]')?.value || '',
            telefono: form.querySelector('[name="telefono"]')?.value || null,

            // ── Seguridad Social (REQUERIDOS) ──
            eps: form.querySelector('[name="eps"]')?.value || '',
            afp: form.querySelector('[name="afp"]')?.value || '',
            arl: form.querySelector('[name="arl"]')?.value || '',
            nivel_riesgo_arl: form.querySelector('[name="nivel_riesgo_arl"]')?.value || 'I',

            // ── Información Laboral ──
            fecha_ingreso: form.querySelector('[name="fecha_ingreso"]')?.value || '',
            estado: form.querySelector('[name="estado"]')?.value || 'ACTIVO',
            fecha_retiro: form.querySelector('[name="fecha_retiro"]')?.value || null,
        };

        // ── Contabilidad (Opcional) ──
        const cuentaUuid = form.querySelector('[name="cuenta_contable_uuid"]')?.value;
        if (cuentaUuid && cuentaUuid.trim()) {
            data.cuenta_contable_uuid = cuentaUuid;
        }

        const submitBtn = form.querySelector('[id="btn-guardar-empleado"]') ||
                          form.querySelector('[id="btn-crear-empleado"]');

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
        }

        try {
            let response;
            const headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]')?.value || ''
            };

            if (empleadoUuid) {
                // PATCH: Editar empleado
                response = await fetch(`${API_URL}${empleadoUuid}/`, {
                    method: 'PATCH',
                    headers,
                    body: JSON.stringify(data)
                });
            } else {
                // POST: Crear empleado
                response = await fetch(API_URL, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify(data)
                });
            }

            if (response.ok) {
                const result = await response.json();

                // Cerrar offcanvas
                const offcanvasEl = form.closest('.offcanvas');
                if (offcanvasEl && window.bootstrap) {
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
                    if (bsOffcanvas) bsOffcanvas.hide();
                }

                // Notificar éxito
                const message = result.message || (empleadoUuid ? 'Empleado actualizado correctamente' : 'Empleado creado correctamente');
                if (window.UIManager) {
                    window.UIManager.notifySuccess(message);
                }

                // Recargar tabla
                if (window.Sintel.Empleados.EmpleadoList) {
                    window.Sintel.Empleados.EmpleadoList.reload();
                }
            } else {
                const errorData = await response.json();
                let errorMsg = 'Error al guardar el empleado';

                console.error(`${MOD} Error response:`, errorData);

                // Parsear errores de validación
                if (typeof errorData === 'object' && errorData !== null) {
                    // Intenta con 'detail' si es string (mensaje del servidor)
                    if (typeof errorData.detail === 'string' && errorData.detail) {
                        errorMsg = errorData.detail
                            // Limpiar formato de Python dict
                            .replace(/'/g, '"')
                            .replace(/ErrorDetail\(string=/g, '')
                            .replace(/, code='[^']*'\)/g, '')
                            .replace(/[\[\]{}]/g, '')
                            .trim();
                    }
                    // Si no, intenta parsear como objeto
                    else if (typeof errorData.detail === 'object') {
                        const fieldErrors = Object.entries(errorData.detail)
                            .map(([field, msgs]) => {
                                const message = Array.isArray(msgs) ? msgs[0] : msgs;
                                return `${field}: ${message}`;
                            })
                            .join('\n');
                        if (fieldErrors) errorMsg = fieldErrors;
                    }
                    // Fallback a 'error' o 'message'
                    else if (errorData.error) {
                        errorMsg = errorData.error;
                    } else if (errorData.message) {
                        errorMsg = errorData.message;
                    }
                    // Última opción: JSON stringify
                    else {
                        errorMsg = JSON.stringify(errorData);
                    }
                }

                if (window.UIManager) {
                    window.UIManager.notifyError(`Error: ${errorMsg}`);
                }
            }
        } catch (error) {
            console.error(`${MOD} Error en submitEmpleado:`, error);
            if (window.UIManager) {
                window.UIManager.notifyError('Error inesperado al guardar el empleado');
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = empleadoUuid ?
                    '<i class="bi bi-check-lg me-1"></i>Actualizar Empleado' :
                    '<i class="bi bi-plus-circle me-1"></i>Crear Empleado';
            }
        }
    }

    /**
     * Handler para respuesta HTMX
     */
    function handleAfterRequest(evt) {
        const target = evt.target;
        const isEmpleadoForm = target && target.id === 'empleado-form';
        
        if (!isEmpleadoForm) return;

        const detail = evt.detail;
        
        // Verificar si es respuesta exitosa
        if (detail.successful) {
            try {
                const response = JSON.parse(detail.xhr.response);
                
                // Cerrar offcanvas
                const offcanvas = document.querySelector('#empleadoOffcanvas');
                if (offcanvas && bootstrap && bootstrap.Offcanvas) {
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvas);
                    if (bsOffcanvas) {
                        bsOffcanvas.hide();
                    }
                }

                // Notificar éxito
                if (window.UIManager) {
                    const message = response.message || 'Empleado guardado correctamente';
                    window.UIManager.notifySuccess(message);
                }

                // Recargar tabla
                if (window.Sintel.Empleados.EmpleadoList) {
                    window.Sintel.Empleados.EmpleadoList.reload();
                }

            } catch (e) {
                console.error('[EmpleadoEditor] Error procesando respuesta:', e);
            }
        } else {
            // Manejar error
            try {
                const response = JSON.parse(detail.xhr.response);
                const errorMsg = response.error || response.detail || 'Error al guardar el empleado';
                
                if (window.UIManager) {
                    window.UIManager.handleError({
                        error: errorMsg,
                        detail: response.detail
                    });
                }
            } catch (e) {
                if (window.UIManager) {
                    window.UIManager.notifyError('Error inesperado al guardar el empleado');
                }
            }
        }
    }

    /**
     * Limpiar formulario
     */
    function clear() {
        const form = document.querySelector('#empleado-form');
        if (form) {
            form.reset();
        }
    }

    /**
     * [v3.5.0] Inicializar buscador asíncrono de cuentas contables
     */
    function initCuentaContableSearch(container) {
        const searchInput = container.querySelector('#empleado-cuenta_contable_label');
        const uuidInput = container.querySelector('#empleado-cuenta_contable_uuid');
        const suggestions = container.querySelector('#empleado-cuenta-resultados');

        if (!searchInput || !uuidInput || !suggestions) return;

        let debounceTimer;

        searchInput.addEventListener('input', () => {
            const query = searchInput.value.trim();
            clearTimeout(debounceTimer);

            if (query.length < 2) {
                suggestions.classList.add('d-none');
                return;
            }

            debounceTimer = setTimeout(async () => {
                try {
                    const api = window.Sintel.Empleados.API;
                    const request = window.Sintel.Empleados.request;
                    if (!api || !request) return;

                    const url = api.contabilidad.search(query);
                    const response = await request(url);

                    if (response && response.ok && response.data) {
                        const results = Array.isArray(response.data) ? response.data : (response.data.results || []);
                        renderSuggestions(results);
                    }
                } catch (err) {
                    console.error(`${MOD} Error en búsqueda de cuentas:`, err);
                }
            }, 300);
        });

        function renderSuggestions(data) {
            suggestions.innerHTML = '';
            if (!data || !data.length) {
                suggestions.classList.add('d-none');
                return;
            }

            data.forEach(cuenta => {
                const item = document.createElement('button');
                item.type = 'button';
                item.className = 'list-group-item list-group-item-action small py-2';
                item.innerHTML = `<div><span class="fw-bold text-primary">${cuenta.codigo}</span> - ${cuenta.nombre}</div>`;
                
                item.addEventListener('click', () => {
                    searchInput.value = `${cuenta.codigo} - ${cuenta.nombre}`;
                    uuidInput.value = cuenta.uuid;
                    suggestions.classList.add('d-none');
                    
                    // Feedback visual
                    searchInput.classList.add('is-valid');
                    setTimeout(() => searchInput.classList.remove('is-valid'), 2000);
                });
                suggestions.appendChild(item);
            });
            suggestions.classList.remove('d-none');
        }

        // Cerrar sugerencias al hacer click fuera
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
                suggestions.classList.add('d-none');
            }
        });

        // Limpiar UUID si el campo de búsqueda se vacía
        searchInput.addEventListener('change', () => {
            if (!searchInput.value.trim()) {
                uuidInput.value = '';
            }
        });
    }

    // Inicializar listeners
    setupHTMXListeners();
    setupOffcanvasLoadListener();

    // Exportar módulo
    window.Sintel.Empleados.EmpleadoEditor = {
        open,
        clear,
        handleSubmit
    };

})();
