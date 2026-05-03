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
    const CONTAINER_ID = 'offcanvas-container-empleados';

    /**
     * Abrir offcanvas de devengo (nómina) vía HTMX
     */
    async function open(empleadoId, devengoId = null) {
        let url;
        if (devengoId) {
            url = `${API_URL}gestor-offcanvas/?tipo=devengo&id=${devengoId}`;
        } else if (empleadoId) {
            url = `${API_URL}gestor-offcanvas/?tipo=devengo&empleado_id=${empleadoId}`;
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

            const offcanvasEl = d.getElementById('offcanvas-devengo');
            if (offcanvasEl) {
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                bsOffcanvas.show();
            }
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al cargar el formulario de nómina');
        }
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
