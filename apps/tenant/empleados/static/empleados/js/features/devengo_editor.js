/**
 * Devengo Editor Module - Feature: Editor de Devengos (Nóminas)
 * ⚠️ Feature-Sliced Architecture v2.61.8
 * Maneja la apertura de offcanvas y eventos HTMX de devengos
 * 
 * Namespace: window.Sintel.Empleados.DevengoEditor
 */
(function(w, d) {
    'use strict';

    const MOD = '[DevengoEditor]';
    const API_URL = '/api/v1/empleados/';
    const CONTAINER_ID = 'offcanvas-container-nominas';

    /**
     * Abrir offcanvas de devengo (nómina) vía HTMX
     * El offcanvas será abierto automáticamente por el listener en empleado_list.js
     */
    async function open(empleadoId, devengoId = null) {
        let url;
        if (devengoId) {
            url = `${API_URL}gestor-offcanvas/?tipo=devengo&id=${devengoId}`;
        } else if (empleadoId) {
            url = `${API_URL}gestor-offcanvas/?tipo=devengo&empleado=${empleadoId}`;
        } else {
            console.error(`${MOD} ID de empleado o devengo no proporcionado`);
            return;
        }

        console.log(`${MOD} Cargando offcanvas: ${url}`);

        try {
            await htmx.ajax('GET', url, {
                target: `#${CONTAINER_ID}`,
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al cargar el formulario de nómina');
        }
    }

    /**
     * Dispara automáticamente el cálculo de nómina cuando el offcanvas se inyecta
     */
    function triggerPreviewCalculo() {
        const form = d.getElementById('form-devengo');
        if (!form) return;

        const wrapper = d.getElementById('devengo-campos-calculados-wrapper');
        if (!wrapper) return;

        const contrato = d.getElementById('devengo-contrato-id');
        const diasLaborados = d.getElementById('devengo-dias_laborados');

        if (!contrato?.value || !diasLaborados?.value) {
            console.log(`${MOD} Campos incompletos, no dispara preview`);
            return;
        }

        console.log(`${MOD} Disparando preview-calculo automático`);

        htmx.ajax('POST', `${API_URL}devengos/preview-calculo/`, {
            target: '#devengo-campos-calculados-wrapper',
            swap: 'innerHTML',
            headers: {
                'X-CSRFToken': (w.API_HELPERS && typeof w.API_HELPERS.getCSRF === 'function') 
                    ? w.API_HELPERS.getCSRF() 
                    : (w.getCookie ? w.getCookie('csrftoken') : d.querySelector('[name=csrfmiddlewaretoken]')?.value)
            },
            values: {
                contrato: contrato.value,
                dias_laborados: diasLaborados.value,
                periodo_mes: d.getElementById('devengo-periodo_mes')?.value || '',
                fecha_pago: d.getElementById('devengo-fecha_pago')?.value || '',
                otros_devengos: d.getElementById('devengo-otros_devengos')?.value || '0',
                prestamos: d.getElementById('devengo-prestamos')?.value || '0',
                descuentos_operativos: d.getElementById('devengo-descuentos_operativos')?.value || '0'
            }
        });
    }

    /**
     * Listener que dispara preview-calculo cuando el offcanvas se inyecta
     */
    function setupOffcanvasLoadListener() {
        d.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail.target;
            if (!target) return;

            const offcanvasEl = target.querySelector('#offcanvas-devengo');
            if (!offcanvasEl) return;

            // Pequeño delay para asegurar que el DOM está listo
            setTimeout(triggerPreviewCalculo, 100);
        });
    }

    /**
     * Configurar eventos HTMX para manejo de errores y éxito
     */
    function setupHTMXListeners() {
        d.body.addEventListener('htmx:afterRequest', function(evt) {
            const target = evt.target;
            const isDevengoForm = target.id === 'form-devengo';
            const requestPath = evt.detail.pathInfo?.requestPath || '';
            const isPreview = requestPath.includes('preview-calculo');

            if (evt.detail.successful && isDevengoForm && !isPreview) {
                // 1. Cerrar Offcanvas
                const offcanvasEl = d.getElementById('offcanvas-devengo');
                if (offcanvasEl) {
                    bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
                }

                // 2. Notificar éxito
                window.UIManager?.notifySuccess('Nómina registrada correctamente');

                // 3. Recargar tabla
                window.Sintel.Empleados.EmpleadoList?.reload();
            }
        });
    }

    // Inicializar listeners
    setupHTMXListeners();
    setupOffcanvasLoadListener();

    // Exportar
    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};
    window.Sintel.Empleados.DevengoEditor = {
        open,
        openDevengoOffcanvas: open
    };

    // Alias legacy
    window.DevengosEditor = window.Sintel.Empleados.DevengoEditor;

})(window, document);
