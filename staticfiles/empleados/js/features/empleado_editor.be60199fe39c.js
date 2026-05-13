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
        // Aplicar DOM Shield: remover atributos name de campos visibles
        // y capturar valores desde inputs hidden
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
            e.preventDefault();
            if (window.UIManager) {
                window.UIManager.notifyError('Por favor complete todos los campos requeridos');
            }
            return false;
        }

        return true;
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
        const searchInput = container.querySelector('#cuenta_contable_search');
        const uuidInput = container.querySelector('#cuenta_contable_uuid');
        const suggestions = container.querySelector('#cuenta-contable-resultados');

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
