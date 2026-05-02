/**
 * Contrato Editor Module - Formulario de Contrato
 * 
 * Namespace: window.Sintel.Empleados.ContratoEditor
 * Versión: v2.61.4
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};

    /**
     * Inicializa el formulario de contrato
     */
    function init(formSelector) {
        const form = document.querySelector(formSelector);
        if (!form) {
            console.error('[ContratoEditor] Formulario no encontrado:', formSelector);
            return;
        }

        // Calcular salario proporcional en tiempo real
        const diasInput = form.querySelector('[name="dias_laborados"]');
        const salarioInput = form.querySelector('[name="salario_mensual"]');
        
        if (diasInput && salarioInput) {
            diasInput.addEventListener('input', calcularProporcional);
        }

        form.addEventListener('submit', handleSubmit);
        document.body.addEventListener('htmx:afterRequest', handleAfterRequest);
    }

    /**
     * Calcular salario proporcional
     */
    function calcularProporcional() {
        const form = document.querySelector('#contrato-form');
        if (!form) return;

        const salarioMensual = parseFloat(form.querySelector('[name="salario_mensual"]')?.value) || 0;
        const diasLaborados = parseFloat(form.querySelector('[name="dias_laborados"]')?.value) || 30;

        // Base: 30 días
        const proporcional = (salarioMensual / 30) * diasLaborados;
        
        // Mostrar cálculo
        const display = form.querySelector('#salario-calculado');
        if (display) {
            display.textContent = `$${proporcional.toFixed(2)}`;
        }
    }

    /**
     * Handler para submit
     */
    function handleSubmit(e) {
        const form = e.target;
        
        // Validar campos
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
            window.UIManager?.notifyError('Complete todos los campos requeridos');
            return false;
        }

        return true;
    }

    /**
     * Handler para respuesta HTMX
     */
    function handleAfterRequest(evt) {
        if (!evt.detail.successful) {
            try {
                const response = JSON.parse(evt.detail.xhr.response);
                window.UIManager?.handleError({
                    error: response.error || 'Error al guardar contrato',
                    detail: response.detail
                });
            } catch (e) {
                window.UIManager?.notifyError('Error inesperado');
            }
            return;
        }

        // Éxito
        const offcanvas = document.querySelector('#contratoOffcanvas');
        if (offcanvas && bootstrap?.Offcanvas) {
            bootstrap.Offcanvas.getInstance(offcanvas)?.hide();
        }

        window.UIManager?.notifySuccess('Contrato guardado correctamente');
        window.Sintel.Empleados.EmpleadoList?.reload();
    }

    // Exportar
    window.Sintel.Empleados.ContratoEditor = {
        init,
        calcularProporcional
    };

})();
