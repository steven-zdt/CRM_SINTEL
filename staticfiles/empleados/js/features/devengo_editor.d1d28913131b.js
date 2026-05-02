/**
 * Devengo (Nómina) Editor Module - Formulario de Nómina
 * 
 * Namespace: window.Sintel.Empleados.DevengoEditor
 * Versión: v2.61.4
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};

    /**
     * Inicializa el formulario de devengo
     */
    function init(formSelector) {
        const form = document.querySelector(formSelector);
        if (!form) {
            console.error('[DevengoEditor] Formulario no encontrado:', formSelector);
            return;
        }

        // Calcular nómina en tiempo real
        const inputs = form.querySelectorAll('[name="dias_laborados"], [name="otros_devengos"], [name="prestamos"]');
        inputs.forEach(input => {
            input.addEventListener('input', calcularNomina);
        });

        form.addEventListener('submit', handleSubmit);
        document.body.addEventListener('htmx:afterRequest', handleAfterRequest);
    }

    /**
     * Calcular nómina colombiana
     */
    function calcularNomina() {
        const form = document.querySelector('#devengo-form');
        if (!form) return;

        const salarioBase = parseFloat(form.dataset.salarioBase) || 0;
        const auxilioTransporte = parseFloat(form.dataset.auxilioTransporte) || 0;
        const diasLaborados = parseFloat(form.querySelector('[name="dias_laborados"]')?.value) || 30;
        const otrosDevengos = parseFloat(form.querySelector('[name="otros_devengos"]')?.value) || 0;
        const prestamos = parseFloat(form.querySelector('[name="prestamos"]')?.value) || 0;

        // Cálculos proporcionales
        const factor = diasLaborados / 30;
        const salarioProporcional = salarioBase * factor;
        const auxilioProporcional = auxilioTransporte * factor;

        // Deducciones (4% salud + 4% pensión sobre IBC)
        const ibc = salarioProporcional;
        const salud = ibc * 0.04;
        const pension = ibc * 0.04;

        // Neto
        const devengos = salarioProporcional + auxilioProporcional + otrosDevengos;
        const deducciones = salud + pension + prestamos;
        const neto = devengos - deducciones;

        // Mostrar resultados
        const display = form.querySelector('#nomina-calculada');
        if (display) {
            display.innerHTML = `
                <div class="alert alert-info">
                    <strong>Resumen:</strong><br>
                    Salario proporcional: $${salarioProporcional.toFixed(2)}<br>
                    Auxilio transporte: $${auxilioProporcional.toFixed(2)}<br>
                    Salud (4%): $${salud.toFixed(2)}<br>
                    Pensión (4%): $${pension.toFixed(2)}<br>
                    <strong>Neto a pagar: $${neto.toFixed(2)}</strong>
                </div>
            `;
        }
    }

    /**
     * Handler para submit
     */
    function handleSubmit(e) {
        const form = e.target;
        
        // Validar límite de días
        const diasInput = form.querySelector('[name="dias_laborados"]');
        const dias = parseFloat(diasInput?.value) || 0;
        
        if (dias <= 0 || dias > 31) {
            e.preventDefault();
            window.UIManager?.notifyError('Los días laborados deben estar entre 0.5 y 31');
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
                    error: response.error || 'Error al registrar nómina',
                    detail: response.detail
                });
            } catch (e) {
                window.UIManager?.notifyError('Error inesperado');
            }
            return;
        }

        // Éxito
        const offcanvas = document.querySelector('#devengoOffcanvas');
        if (offcanvas && bootstrap?.Offcanvas) {
            bootstrap.Offcanvas.getInstance(offcanvas)?.hide();
        }

        window.UIManager?.notifySuccess('Nómina registrada correctamente');
        window.Sintel.Empleados.EmpleadoList?.reload();
    }

    // Exportar
    window.Sintel.Empleados.DevengoEditor = {
        init,
        calcularNomina
    };

})();
