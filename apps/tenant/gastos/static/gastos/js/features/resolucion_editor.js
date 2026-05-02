/**
 * Resolucion DIAN Editor Module - Formulario de Resolución
 * 
 * Namespace: window.Sintel.Gastos.ResolucionEditor
 * Versión: v2.61.4
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Gastos = window.Sintel.Gastos || {};

    function init(formSelector) {
        const form = document.querySelector(formSelector);
        if (!form) {
            console.error('[ResolucionEditor] Formulario no encontrado:', formSelector);
            return;
        }

        // Validar fechas
        const fechaInicio = form.querySelector('[name="fecha_inicio"]');
        const fechaFin = form.querySelector('[name="fecha_fin"]');
        
        if (fechaInicio && fechaFin) {
            fechaInicio.addEventListener('change', () => validarFechas(form));
            fechaFin.addEventListener('change', () => validarFechas(form));
        }

        // Validar rangos
        const rangoDesde = form.querySelector('[name="rango_desde"]');
        const rangoHasta = form.querySelector('[name="rango_hasta"]');
        
        if (rangoDesde && rangoHasta) {
            rangoDesde.addEventListener('change', () => validarRangos(form));
            rangoHasta.addEventListener('change', () => validarRangos(form));
        }

        form.addEventListener('submit', handleSubmit);
        document.body.addEventListener('htmx:afterRequest', handleAfterRequest);
    }

    function validarFechas(form) {
        const inicio = form.querySelector('[name="fecha_inicio"]')?.value;
        const fin = form.querySelector('[name="fecha_fin"]')?.value;
        
        if (inicio && fin && new Date(inicio) > new Date(fin)) {
            window.UIManager?.notifyError('La fecha de inicio no puede ser mayor a la fecha final');
            return false;
        }
        return true;
    }

    function validarRangos(form) {
        const desde = parseInt(form.querySelector('[name="rango_desde"]')?.value) || 0;
        const hasta = parseInt(form.querySelector('[name="rango_hasta"]')?.value) || 0;
        
        if (desde && hasta && desde >= hasta) {
            window.UIManager?.notifyError('El rango inicial debe ser menor al rango final');
            return false;
        }
        return true;
    }

    function handleSubmit(e) {
        const form = e.target;
        
        if (!validarFechas(form) || !validarRangos(form)) {
            e.preventDefault();
            return false;
        }

        // Validar campos requeridos
        const required = ['numero_resolucion', 'prefijo', 'rango_desde', 'rango_hasta', 'fecha_resolucion'];
        let isValid = true;
        
        required.forEach(field => {
            const input = form.querySelector(`[name="${field}"]`);
            if (!input?.value?.trim()) {
                isValid = false;
                input?.classList.add('is-invalid');
            } else {
                input?.classList.remove('is-invalid');
            }
        });

        if (!isValid) {
            e.preventDefault();
            window.UIManager?.notifyError('Complete todos los campos requeridos');
            return false;
        }

        return true;
    }

    function handleAfterRequest(evt) {
        if (!evt.detail.successful) {
            try {
                const response = JSON.parse(evt.detail.xhr.response);
                window.UIManager?.handleError({
                    error: response.error || 'Error al guardar resolución',
                    detail: response.detail
                });
            } catch (e) {
                window.UIManager?.notifyError('Error inesperado');
            }
            return;
        }

        try {
            const response = JSON.parse(evt.detail.xhr.response);
            
            const offcanvas = document.querySelector('#resolucionOffcanvas');
            if (offcanvas && bootstrap?.Offcanvas) {
                bootstrap.Offcanvas.getInstance(offcanvas)?.hide();
            }

            window.UIManager?.notifySuccess(response.message || 'Resolución guardada correctamente');
            
            // Recargar lista de resoluciones si existe
            if (window.Sintel.Gastos.ResolucionList) {
                window.Sintel.Gastos.ResolucionList.reload();
            }
        } catch (e) {
            console.error('[ResolucionEditor] Error procesando respuesta:', e);
        }
    }

    window.Sintel.Gastos.ResolucionEditor = {
        init,
        validarFechas,
        validarRangos
    };

})();
