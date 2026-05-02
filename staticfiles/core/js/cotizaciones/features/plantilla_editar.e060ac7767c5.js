/**
 * plantilla_editar.js - Feature-Sliced: Editar Plantilla de Configuración v2.60
 * ⚠️ Feature-Sliced: Módulo dedicado para edición de plantillas
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ UIManager: Manejo de errores centralizado
 */
(function(w, d) {
    'use strict';

    const MOD = 'plantilla_editar';
    const form = d.getElementById('form-plantilla-editar');
    const inputId = d.getElementById('edit-plantilla-id');
    const btnSubmit = d.getElementById('btn-submit-plantilla-editar');
    const feedbackDiv = d.getElementById('form-plantilla-editar-feedback');

    if (!form || !inputId) {
        console.warn(`[${MOD}] Formulario o ID no encontrado. Módulo no inicializado.`);
        return;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const id = inputId.value;
        if (!id) {
            console.error(`[${MOD}] ID de plantilla no encontrado`);
            return;
        }

        const formData = new FormData(form);
        const payload = Object.fromEntries(formData.entries());
        
        // ⚠️ v2.60: User-Driven - Solo convertir valores numéricos esenciales
        if (payload.semilla_inicial) {
            payload.semilla_inicial = parseInt(payload.semilla_inicial, 10);
        }
        if (payload.dias_validez) {
            payload.dias_validez = parseInt(payload.dias_validez, 10);
        }
        
        // Booleanos
        payload.es_activo = d.getElementById('check-es-activo-editar') ? d.getElementById('check-es-activo-editar').checked : true;

        const btnText = btnSubmit.innerHTML;
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Actualizando...';

        // Ocultar feedback anterior
        if (feedbackDiv) {
            feedbackDiv.classList.add('d-none');
        }

        const res = await w.http('PATCH', `/api/v1/cotizaciones/configuracion/${id}/`, payload);
        
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = btnText;

        if (!res.ok) {
            // Mostrar errores en el feedback div
            if (feedbackDiv && res.data) {
                let errorMsg = 'Error al actualizar la plantilla.';
                if (typeof res.data === 'string') {
                    errorMsg = res.data;
                } else if (res.data.detail) {
                    errorMsg = res.data.detail;
                } else if (res.data.non_field_errors) {
                    errorMsg = res.data.non_field_errors.join(', ');
                } else {
                    const errors = Object.values(res.data).flat();
                    errorMsg = errors.join(', ');
                }
                feedbackDiv.textContent = errorMsg;
                feedbackDiv.classList.remove('d-none');
            }
            return w.UIManager?.notifyError(res, 'Editar Plantilla');
        }

        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
            w.SintelFeedback.success('Plantilla actualizada');
        }
        
        // ⚠️ v2.60: Navegación fluida - Volver a la lista de plantillas en lugar de cerrar
        // Cargar la lista de plantillas en el offcanvas
        const listaUrl = '/cotizaciones/partials/configuracion/lista/';
        if (typeof htmx !== 'undefined') {
            htmx.ajax('GET', listaUrl, {
                target: '#offcanvas-container',
                swap: 'innerHTML'
            }).then(() => {
                console.log(`[${MOD}] Lista de plantillas recargada después de editar`);
            }).catch((error) => {
                console.error(`[${MOD}] Error al recargar lista:`, error);
                // Fallback: cerrar offcanvas si falla la recarga
                const offcanvasEl = form.closest('.offcanvas');
                if (w.bootstrap && offcanvasEl) {
                    const instance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
                    if (instance) instance.hide();
                }
            });
        } else {
            // Fallback: cerrar offcanvas si HTMX no está disponible
            const offcanvasEl = form.closest('.offcanvas');
            if (w.bootstrap && offcanvasEl) {
                const instance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (instance) instance.hide();
            }
        }
        
        // Refrescar tabla principal si existe (para el workspace principal)
        if (w.cotizacionesPage && w.cotizacionesPage.configTable && typeof w.cotizacionesPage.configTable.replaceData === 'function') {
            w.cotizacionesPage.configTable.replaceData();
        }
    });
})(window, document);
