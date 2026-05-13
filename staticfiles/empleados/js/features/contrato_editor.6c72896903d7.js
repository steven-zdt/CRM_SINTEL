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
    function setupOffcanvasLoadListener() {
        d.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail.target;
            if (!target || target.id !== CONTAINER_ID) return;

            const offcanvasEl = target.querySelector('.offcanvas');
            if (offcanvasEl && window.bootstrap) {
                console.log(`${MOD} Activando offcanvas: ${offcanvasEl.id}`);
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                bsOffcanvas.show();

                // Inicializar lógica del formulario tras apertura
                const form = offcanvasEl.querySelector('form');
                if (form) {
                    setTimeout(() => initForm(form.id), 100);
                }
            }
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

    /**
     * Handler global para respuestas exitosas de HTMX en contratos
     */
    d.body.addEventListener('htmx:afterRequest', function(evt) {
        const target = evt.target;
        const isContratoForm = target.id === 'form-contrato-crear' || target.id === 'form-contrato-editar';
        
        if (evt.detail.successful && isContratoForm) {
            // 1. Cerrar Offcanvas
            const offcanvasEl = d.querySelector('.offcanvas.show');
            if (offcanvasEl) {
                bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
            }

            // 2. Notificar éxito
            let msg = 'Operación realizada correctamente';
            try {
                const resp = JSON.parse(evt.detail.xhr.response);
                if (resp.message) msg = resp.message;
            } catch(e) {}
            window.UIManager?.notifySuccess(msg);

            // 3. Recargar tabla
            window.Sintel.Empleados.EmpleadoList?.reload();
        }
    });

    // Inicializar listeners
    setupOffcanvasLoadListener();

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
