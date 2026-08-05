// @ts-nocheck
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

    // Guard against double submission. Each open() call (HTMX swap) re-adds submit/click
    // listeners without removing old ones; without this flag, opening the form N times
    // produces N simultaneous API calls on submit: first creates the employee, subsequent
    // ones hit the uniqueness check and show the spurious "ya existe" error.
    let _submitting = false;

    /**
     * Abrir offcanvas de empleado (Crear o Editar)
     */
    async function open(uuid = null) {
        let url = `${API_URL}gestor-offcanvas/?tipo=empleado`;
        if (uuid) url += `&uuid=${uuid}`;

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

    function _mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return window.Sintel?.Core?.mostrarOffcanvasSeguro(el);
    }

    /**
     * Configurar lógica en cascada para Sede y Área
     */
    function setupCascadingSelects(offcanvasEl) {
        const sedeSelect = offcanvasEl.querySelector('#empleado-sede');
        const areaSelect = offcanvasEl.querySelector('#empleado-area');

        if (!sedeSelect || !areaSelect) return;

        function updateAreas() {
            const selectedSedeUuid = sedeSelect.value;
            let currentSelectedStillValid = false;

            Array.from(areaSelect.options).forEach(opt => {
                if (!opt.value) {
                    opt.style.display = '';
                    return;
                }

                const optSedeUuid = opt.getAttribute('data-sede-uuid');
                if (!selectedSedeUuid) {
                    opt.style.display = 'none';
                } else if (optSedeUuid === selectedSedeUuid) {
                    opt.style.display = '';
                    if (opt.value === areaSelect.value) {
                        currentSelectedStillValid = true;
                    }
                } else {
                    opt.style.display = 'none';
                    if (opt.value === areaSelect.value) {
                        opt.selected = false;
                    }
                }
            });

            if (!currentSelectedStillValid && areaSelect.value !== '') {
                areaSelect.value = '';
            }
        }

        sedeSelect.addEventListener('change', updateAreas);
        updateAreas();
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
                _mostrarOffcanvasSeguro(offcanvasEl);

                // Configurar lógica en cascada para Sede y Área
                setupCascadingSelects(offcanvasEl);

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

                }
            }
        });
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
     * Enviar formulario de empleado (crear o editar).
     * Usa FormData para soportar upload de foto (multipart/form-data).
     */
    async function submitEmpleado(form) {
        if (_submitting) return;
        _submitting = true;

        const offcanvas = form.closest('.offcanvas');
        const empleadoUuid = offcanvas?.dataset.empleadoUuid;

        // Construir FormData con todos los campos del formulario
        const fd = new FormData();
        const campos = [
            'tipo_documento', 'numero_documento',
            'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
            'email', 'telefono',
            'eps', 'afp', 'arl', 'nivel_riesgo_arl',
            'fecha_ingreso', 'estado', 'fecha_retiro',
            'sede', 'area',
        ];
        campos.forEach(c => {
            const el = form.querySelector(`[name="${c}"]`);
            if (el && el.value !== '' && el.value !== null) fd.append(c, el.value);
        });

        // Foto: solo adjuntar si el usuario seleccionó un archivo
        const fotoInput = form.querySelector('[name="foto"]');
        if (fotoInput && fotoInput.files && fotoInput.files.length > 0) {
            fd.append('foto', fotoInput.files[0]);
        }

        const submitBtn = offcanvas?.querySelector('[id="btn-guardar-empleado"]') ||
                          offcanvas?.querySelector('[id="btn-crear-empleado"]') ||
                          document.getElementById('btn-guardar-empleado') ||
                          document.getElementById('btn-crear-empleado');

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
        }

        // Sin Content-Type: el browser lo establece automáticamente con el boundary correcto
        const headers = {
            'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]')?.value || ''
        };

        try {
            let response;
            if (empleadoUuid) {
                response = await fetch(`${API_URL}${empleadoUuid}/`, {
                    method: 'PATCH', headers, body: fd
                });
            } else {
                response = await fetch(API_URL, {
                    method: 'POST', headers, body: fd
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
            _submitting = false;
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = empleadoUuid ?
                    '<i class="bi bi-check-lg me-1"></i>Actualizar Empleado' :
                    '<i class="bi bi-plus-circle me-1"></i>Crear Empleado';
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

    // Inicializar listeners
    // Guard: setupOffcanvasLoadListener() registra en `document.body` (persiste
    // entre recargas HTMX del modulo "empleados") — sin este guard, cada
    // recarga del script duplica el flujo de guardado (FE-A1/A2).
    if (!document.body.dataset.empleadoEditorInitialized) {
        document.body.dataset.empleadoEditorInitialized = 'true';
        setupOffcanvasLoadListener();
    }

    // Exportar módulo
    window.Sintel.Empleados.EmpleadoEditor = {
        open,
        clear,
        handleSubmit
    };

})();
