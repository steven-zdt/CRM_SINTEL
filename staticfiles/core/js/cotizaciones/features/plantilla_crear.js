/**
 * plantilla_crear.js - Feature-Sliced: Crear Plantilla de Configuración v2.60
 * ⚠️ Feature-Sliced: Módulo dedicado para creación de plantillas
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ UIManager: Manejo de errores centralizado
 */
(function(w, d) {
    'use strict';

    const MOD = 'plantilla_crear';
    const form = d.getElementById('form-plantilla-crear');
    const btnSubmit = d.getElementById('btn-submit-plantilla-crear');
    const feedbackDiv = d.getElementById('form-plantilla-crear-feedback');

    if (!form) {
        console.warn(`[${MOD}] Formulario no encontrado. Módulo no inicializado.`);
        return;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!form.checkValidity()) {
            form.reportValidity();
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
        payload.es_activo = d.getElementById('check-es-activo-crear') ? d.getElementById('check-es-activo-crear').checked : true;

        const btnText = btnSubmit.innerHTML;
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Guardando...';

        // Ocultar feedback anterior
        if (feedbackDiv) {
            feedbackDiv.classList.add('d-none');
        }

        const res = await w.http('POST', '/api/v1/cotizaciones/configuracion/', payload);
        
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = btnText;

        if (!res.ok) {
            // Mostrar errores en el feedback div
            if (feedbackDiv && res.data) {
                let errorMsg = 'Error al crear la plantilla.';
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
            return w.UIManager?.notifyError(res, 'Crear Plantilla');
        }

        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
            w.SintelFeedback.success('Plantilla creada con éxito');
        }
        
        // ⚠️ v2.60: Navegación fluida - Volver a la lista de plantillas en lugar de cerrar
        // Cargar la lista de plantillas en el offcanvas secundario
        const listaUrl = '/cotizaciones/partials/configuracion/lista/';
        if (typeof htmx !== 'undefined') {
            // Cerrar offcanvas actual primero
            const offcanvasActual = form.closest('.offcanvas');
            if (w.bootstrap && offcanvasActual) {
                try {
                    const instanceActual = w.bootstrap.Offcanvas.getInstance(offcanvasActual);
                    if (instanceActual) instanceActual.hide();
                } catch (error) {
                    console.warn(`[${MOD}] Error al cerrar offcanvas actual:`, error);
                }
            }
            
            // Cargar lista en el contenedor principal
            htmx.ajax('GET', listaUrl, {
                target: '#offcanvas-container-secundario',
                swap: 'innerHTML'
            }).then(() => {
                console.log(`[${MOD}] Lista de plantillas recargada después de crear`);
                // Abrir offcanvas secundario después de cargar
                setTimeout(() => {
                    const offcanvasSecundario = d.getElementById('offcanvas-container-secundario');
                    if (offcanvasSecundario && w.bootstrap) {
                        try {
                            // Verificar que el elemento tenga los atributos necesarios
                            if (!offcanvasSecundario.hasAttribute('tabindex')) {
                                offcanvasSecundario.setAttribute('tabindex', '-1');
                            }
                            
                            const instance = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasSecundario, {
                                backdrop: true,
                                keyboard: true
                            });
                            instance.show();
                        } catch (error) {
                            console.error(`[${MOD}] Error al abrir offcanvas secundario:`, error);
                        }
                    }
                }, 100);
            }).catch((error) => {
                console.error(`[${MOD}] Error al recargar lista:`, error);
            });
        } else {
            // Fallback: cerrar offcanvas si HTMX no está disponible
            const offcanvasEl = form.closest('.offcanvas');
            if (w.bootstrap && offcanvasEl) {
                try {
                    const instance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
                    if (instance) instance.hide();
                } catch (error) {
                    console.warn(`[${MOD}] Error al cerrar offcanvas:`, error);
                }
            }
        }
        
        // Refrescar tabla principal si existe (para el workspace principal)
        if (w.cotizacionesPage && w.cotizacionesPage.configTable && typeof w.cotizacionesPage.configTable.replaceData === 'function') {
            w.cotizacionesPage.configTable.replaceData();
        }
    });
})(window, document);
