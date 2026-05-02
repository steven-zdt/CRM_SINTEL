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

    /**
     * Inicializa el formulario de empleado
     */
    function init(formSelector) {
        const form = document.querySelector(formSelector);
        if (!form) {
            console.error('[EmpleadoEditor] Formulario no encontrado:', formSelector);
            return;
        }

        // Manejar submit del formulario
        form.addEventListener('submit', handleSubmit);

        // Manejar respuesta HTMX
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

    // Exportar módulo
    window.Sintel.Empleados.EmpleadoEditor = {
        init,
        clear,
        handleSubmit
    };

})();
