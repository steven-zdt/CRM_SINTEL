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

    async function init(formSelector) {
        const form = (typeof formSelector === 'string') ? document.querySelector(formSelector) : formSelector;
        if (!form) {
            console.error('[ResolucionEditor] Formulario no encontrado:', formSelector);
            return;
        }
        if (form.dataset.resolucionEditorBound === 'true') {
            return;
        }
        form.dataset.resolucionEditorBound = 'true';

        console.log('[ResolucionEditor] Inicializando formulario:', form.id);

        // Asegurar que el offcanvas de Bootstrap esté inicializado para que los botones de cierre funcionen
        const offcanvasEl = form.closest('.offcanvas');
        if (offcanvasEl && window.bootstrap) {
            if (!window.bootstrap.Offcanvas.getInstance(offcanvasEl)) {
                new window.bootstrap.Offcanvas(offcanvasEl);
            }
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

    async function handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        
        if (!validarFechas(form) || !validarRangos(form)) {
            return false;
        }

        // UI Feedback
        const submitBtn = form.querySelector('[type="submit"]');
        const originalBtnText = submitBtn ? submitBtn.innerHTML : '';

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
            window.UIManager?.notifyError('Complete todos los campos requeridos');
            return false;
        }

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
        }

        // Mapeo de datos para JSON (DRF)
        const formData = new FormData(form);
        const data = {
            numero_resolucion: formData.get('numero_resolucion'),
            prefijo: formData.get('prefijo'),
            rango_desde: parseInt(formData.get('rango_desde')) || 0,
            rango_hasta: parseInt(formData.get('rango_hasta')) || 0,
            fecha_resolucion: formData.get('fecha_resolucion'),
            fecha_inicio: formData.get('fecha_inicio') || null,
            fecha_fin: formData.get('fecha_fin'),
            clave_tecnica: formData.get('clave_tecnica'),
            vigente: form.querySelector('[name="vigente"]')?.checked || false
        };

        const uuid = form.querySelector('[name="uuid"]')?.value;
        const api = window.Sintel.Gastos.API.resoluciones;
        const url = uuid ? api.update(uuid) : api.create;
        const method = uuid ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: window.Sintel.Gastos.getHeaders(),
                body: JSON.stringify(data)
            });

            const result = await response.json().catch(() => ({}));

            if (!response.ok) {
                if (response.status === 422 || response.status === 400) {
                    window.UIManager?.handleError(result);
                } else {
                    throw new Error(result.message || result.detail || 'Error en el servidor');
                }
                return;
            }

            // Éxito
            window.UIManager?.notifySuccess('Resolución guardada correctamente');
            
            const offcanvasEl = form.closest('.offcanvas');
            if (offcanvasEl && offcanvasEl.id) {
                window.UIManager?.handleOffcanvas('#' + offcanvasEl.id, 'hide');
                
                // Limpieza de seguridad: remover backdrops huérfanos
                setTimeout(() => {
                    document.querySelectorAll('.offcanvas-backdrop').forEach(el => el.remove());
                    document.body.style.overflow = '';
                    document.body.style.paddingRight = '';
                }, 400);
            }

            // Disparar evento global para sincronización entre módulos (v2.62.3)
            document.body.dispatchEvent(new CustomEvent('resolucion-created', {
                detail: result
            }));

        } catch (error) {
            console.error('[ResolucionEditor] Error:', error);
            window.UIManager?.notifyError(error.message || 'Error al procesar la solicitud');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        }
    }

    window.Sintel.Gastos.ResolucionEditor = {
        init,
        validarFechas,
        validarRangos
    };

    // --- Orquestación de Eventos ---

    // 1. Inicialización para carga inicial
    document.addEventListener('DOMContentLoaded', () => {
        const form = document.querySelector('#resolucion-form');
        if (form) init(form);
    });

    // 2. Inicialización para HTMX (v2.62)
    document.body.addEventListener('htmx:afterSettle', (evt) => {
        const target = evt.detail.target;
        if (!target) return;
        
        const form = target.id === 'resolucion-form' ? target : target.querySelector('#resolucion-form');
        if (form) {
            console.log('[ResolucionEditor] Detectado formulario vía HTMX:', form.id);
            init(form);
        }
    });

    // 3. Listener para eventos manuales
    document.body.addEventListener('resolucion-editor-init', (e) => {
        const form = e.detail?.form || document.querySelector('#resolucion-form');
        if (form) init(form);
    });

})();
