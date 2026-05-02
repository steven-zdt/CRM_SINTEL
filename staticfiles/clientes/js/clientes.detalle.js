/**
 * Feature: Ver Detalle Cliente v2.61
 * ⚠️ Feature-Sliced Architecture: Módulo específico para vista de solo lectura
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ Read-Only: Solo lectura, sin capacidad de edición
 * 
 * Dependencias globales requeridas:
 * - w.clientesAPI (definido en clientes.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 */
(function(w, d) {
    'use strict';

    let offcanvasInstance = null;

    /**
     * Inicializar eventos del offcanvas de detalle
     */
    function initOffcanvasDetalle() {
        const offcanvasEl = d.getElementById('offcanvas-cliente-detalle');
        if (!offcanvasEl) {
            console.warn('[cliente.detalle] Offcanvas no encontrado');
            return;
        }

        // Obtener instancia de Bootstrap Offcanvas
        if (w.bootstrap && w.bootstrap.Offcanvas) {
            offcanvasInstance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
        }

        // Limpiar al cerrar
        offcanvasEl.addEventListener('hidden.bs.offcanvas', function() {
            const container = d.querySelector('#offcanvas-container-clientes');
            if (container) {
                container.innerHTML = '';
            }
        }, { once: true });

        console.log('[cliente.detalle] Offcanvas de detalle inicializado');
    }

    /**
     * Escuchar evento de inicialización desde el template
     */
    d.addEventListener('initClienteDetalle', function() {
        console.log('[cliente.detalle] Evento initClienteDetalle recibido');
        initOffcanvasDetalle();
    });

    // Exponer API pública (opcional)
    w.ClienteDetalleModule = {
        init: initOffcanvasDetalle
    };

})(window, document);
