// @ts-nocheck
/**
 * Contrato Editor Module - Feature: Gestión de Contratos
 * ⚠️ Feature-Sliced Architecture v2.61.8
 * 
 * Namespace: window.Sintel.Empleados.ContratoEditor
 */
(function(w, d) {
    'use strict';

    const MOD = '[ContratoEditor]';
    const API_CONTRATOS = '/api/v1/empleados/contratos/';
    const CONTAINER_ID = 'offcanvas-container-contratos';

    /**
     * Abrir offcanvas de contrato (Crear o Editar)
     */
    async function open(empleadoId, contratoId = null) {
        let url;
        if (contratoId) {
            url = `${API_CONTRATOS}${contratoId}/render-offcanvas/editar/`;
        } else {
            url = `${API_CONTRATOS}render-offcanvas/crear/?empleado=${empleadoId}`;
        }

        console.log(`${MOD} Cargando offcanvas: ${url}`);
        
        try {
            await htmx.ajax('GET', url, {
                target: `#${CONTAINER_ID}`,
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al cargar el formulario de contrato');
        }
    }

    /**
     * Abrir offcanvas de detalle (solo lectura)
     */
    async function openDetail(contratoId) {
        const url = `${API_CONTRATOS}${contratoId}/render-offcanvas/detalle/`;
        
        try {
            await htmx.ajax('GET', url, {
                target: `#${CONTAINER_ID}`,
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al cargar detalle del contrato');
        }
    }

    /**
     * Listener para activar offcanvas tras inyección HTMX
     */
    function _mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
    }

    /**
     * Agrega validacion HTML5 al boton de guardar via htmx:configRequest.
     * Cancela el request si el form no pasa checkValidity().
     */
    function setupButtonValidation(offcanvasEl) {
        const form = offcanvasEl.querySelector('form');
        const btn  = offcanvasEl.querySelector(
            '#btn-guardar-contrato-crear, #btn-guardar-contrato-editar'
        );
        if (!form || !btn) return;

        btn.addEventListener('htmx:configRequest', function(e) {
            if (!form.checkValidity()) {
                form.reportValidity();
                e.preventDefault();
            }
        });
    }

    function setupOffcanvasLoadListener() {
        d.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail.target;
            if (!target || target.id !== CONTAINER_ID) return;

            const offcanvasEl = target.querySelector('.offcanvas');
            if (!offcanvasEl) return;

            console.log(`${MOD} Activando offcanvas: ${offcanvasEl.id}`);
            _mostrarOffcanvasSeguro(offcanvasEl);

            const form = offcanvasEl.querySelector('form');
            if (form) {
                setTimeout(() => initForm(form.id), 100);
            }

            setupButtonValidation(offcanvasEl);
        });
    }

    /**
     * Inicializa la lógica del formulario cargado
     */
    function initForm(formId) {
        const form = d.getElementById(formId);
        if (!form) return;

        // Checkbox Indefinido
        const prefix = formId.replace('form-', '');
        const checkboxIndefinido = d.getElementById(`${prefix}-indefinido`);
        const fechaFinInput = d.getElementById(`${prefix}-fecha_fin`);

        if (checkboxIndefinido && fechaFinInput) {
            const toggleFechaFin = () => {
                if (checkboxIndefinido.checked) {
                    fechaFinInput.value = '';
                    fechaFinInput.disabled = true;
                    fechaFinInput.required = false;
                } else {
                    fechaFinInput.disabled = false;
                    fechaFinInput.required = true;
                }
            };

            checkboxIndefinido.addEventListener('change', toggleFechaFin);
            
            // Estado inicial
            if (formId.includes('editar')) {
                // En edición, si no hay fecha_fin, marcar como indefinido
                if (!fechaFinInput.value) checkboxIndefinido.checked = true;
            }
            toggleFechaFin();
        }

        console.log(`${MOD} Formulario ${formId} inicializado`);
    }

    // Guard: setupOffcanvasLoadListener() y el listener de abajo registran
    // ambos en `document.body` (persiste entre recargas HTMX del modulo
    // "empleados") — sin este guard, cada recarga del script duplica el
    // flujo completo de "guardar contrato" (FE-A1/A2).
    if (!d.body.dataset.contratoEditorInitialized) {
        d.body.dataset.contratoEditorInitialized = 'true';

        /**
         * Handler global para botones de guardar contrato.
         * Detecta por button ID (no form ID) — el boton lleva hx-post/hx-patch directamente.
         */
        d.body.addEventListener('htmx:afterRequest', function(evt) {
            const target = evt.target;
            const isContratoBtn =
                target.id === 'btn-guardar-contrato-crear' ||
                target.id === 'btn-guardar-contrato-editar';

            if (!isContratoBtn) return;

            // Siempre restaurar el boton (exito o error)
            const esCrear = target.id === 'btn-guardar-contrato-crear';
            target.disabled = false;
            target.innerHTML = esCrear
                ? '<i class="bi bi-check-lg me-1"></i>Crear Contrato'
                : '<i class="bi bi-check-lg me-1"></i>Actualizar Contrato';

            if (!evt.detail.successful) return;

            // 1. Cerrar Offcanvas
            const offcanvasEl = d.querySelector('.offcanvas.show');
            if (offcanvasEl) {
                bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
            }

            // 2. Notificar exito
            let msg = esCrear ? 'Contrato creado correctamente' : 'Contrato actualizado correctamente';
            try {
                const resp = JSON.parse(evt.detail.xhr.response);
                if (resp.message) msg = resp.message;
            } catch(_) {}
            window.UIManager?.notifySuccess(msg);

            // 3. Recargar tablas
            window.Sintel.Empleados.ContratoList?.reload();
            window.Sintel.Empleados.EmpleadoList?.reload();
        });

        // Inicializar listeners
        setupOffcanvasLoadListener();
    }

    // Exportar al namespace
    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};
    window.Sintel.Empleados.ContratoEditor = {
        open,
        openContratoOffcanvas: open,
        openDetail
    };

    // Alias legacy para compatibilidad si fuera necesario
    window.ContratosEditor = window.Sintel.Empleados.ContratoEditor;

})(window, document);
