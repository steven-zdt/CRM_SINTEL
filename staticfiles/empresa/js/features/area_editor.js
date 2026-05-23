/**
 * Feature: Editor/Formulario - Área v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de validación, recolección y envío del formulario Área
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 */
(function(w, d) {
    'use strict';

    const MOD = '[area.editor]';

    function initFormEvents() {
        const form = d.getElementById('form-area');
        if (!form) return;

        // Limpiar eventos anteriores si se vuelve a renderizar el offcanvas por HTMX
        const newForm = form.cloneNode(true);
        form.parentNode.replaceChild(newForm, form);

        const feedbackEl = d.getElementById('form-area-feedback');
        const btnSave = d.getElementById('btn-guardar-area');

        newForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            if (!newForm.checkValidity()) {
                newForm.classList.add('was-validated');
                return;
            }

            // Ocultar feedback previo
            if (feedbackEl) {
                feedbackEl.classList.add('d-none');
                feedbackEl.innerHTML = '';
            }

            // Bloquear botón de guardar
            let originalSaveHTML = '';
            if (btnSave) {
                originalSaveHTML = btnSave.innerHTML;
                btnSave.disabled = true;
                btnSave.innerHTML = '<i class="bi bi-hourglass-split"></i> Guardando...';
            }

            const uuid = d.getElementById('area-uuid')?.value;
            const isEdit = !!uuid;
            const method = isEdit ? 'PUT' : 'POST';
            const url = isEdit ? `/api/v1/empresas/areas/${uuid}/` : '/api/v1/empresas/areas/';

            // Recolectar datos
            const sedeVal = d.getElementById('area-sede')?.value;
            const payload = {
                sede: sedeVal ? parseInt(sedeVal, 10) : null,
                nombre: d.getElementById('area-nombre')?.value?.trim(),
                codigo_funcionamiento: d.getElementById('area-codigo_funcionamiento')?.value?.trim()
            };

            try {
                if (!w.http) {
                    throw new Error('El helper window.http no está cargado.');
                }

                const res = await w.http(method, url, payload);

                if (res.ok) {
                    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                        w.SintelFeedback.success(isEdit ? 'Área actualizada correctamente' : 'Área creada correctamente');
                    }

                    // Notificar cambios para recargar el listado
                    d.dispatchEvent(new Event('areaGuardada'));

                    // Cerrar Offcanvas
                    const offcanvasEl = d.getElementById('offcanvas-area');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const instance = bootstrap.Offcanvas.getInstance(offcanvasEl);
                        if (instance) {
                            instance.hide();
                        }
                    }
                } else {
                    console.warn(`${MOD} Respuesta fallida de la API:`, res);
                    handleFormErrors(res.data, feedbackEl, newForm);
                }
            } catch (error) {
                console.error(`${MOD} Error al enviar formulario:`, error);
                if (feedbackEl) {
                    feedbackEl.classList.remove('d-none');
                    feedbackEl.textContent = 'Ocurrió un error inesperado al procesar la solicitud.';
                }
            } finally {
                if (btnSave) {
                    btnSave.disabled = false;
                    btnSave.innerHTML = originalSaveHTML;
                }
            }
        });
    }

    function handleFormErrors(data, feedbackEl, form) {
        if (!feedbackEl) return;

        feedbackEl.classList.remove('d-none');

        if (typeof data === 'string') {
            feedbackEl.textContent = data;
            return;
        }

        if (data && typeof data === 'object') {
            if (data.error) {
                feedbackEl.textContent = data.error;
                return;
            }

            let errorMsg = 'Por favor, corrija los siguientes errores:<br><ul class="mb-0 text-start">';
            let hasErrors = false;

            for (const [field, errors] of Object.entries(data)) {
                hasErrors = true;
                const fieldName = field.charAt(0).toUpperCase() + field.slice(1);
                const errorsList = Array.isArray(errors) ? errors.join(', ') : errors;
                errorMsg += `<li><strong>${fieldName}:</strong> ${errorsList}</li>`;

                // Resaltar campo específico en el formulario
                const input = form.querySelector(`[name="${field}"]`);
                if (input) {
                    input.classList.add('is-invalid');
                    // Remover clase al escribir
                    input.addEventListener('input', function onInput() {
                        input.classList.remove('is-invalid');
                        input.removeEventListener('input', onInput);
                    });
                }
            }

            errorMsg += '</ul>';
            feedbackEl.innerHTML = hasErrors ? errorMsg : 'Error al guardar el área. Verifique los datos.';
        } else {
            feedbackEl.textContent = 'Error al procesar la solicitud.';
        }
    }

    // Inicializar cuando se inserte el offcanvas en el DOM por HTMX o carga de página
    d.addEventListener('htmx:afterSwap', (e) => {
        if (e.detail.target.id === 'offcanvas-container-area' || e.detail.target.querySelector('#form-area')) {
            initFormEvents();
        }
    });

    // En caso de que ya exista en el DOM
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFormEvents);
    } else {
        initFormEvents();
    }

})(window, document);
