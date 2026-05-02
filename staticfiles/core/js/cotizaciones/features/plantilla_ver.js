/**
 * plantilla_ver.js - Ver Detalles de Plantilla v2.60
 * ⚠️ Feature-Sliced: Módulo dedicado para vista de solo lectura
 */
(function(w, d) {
    'use strict';

    async function cargarDetalle() {
        // ⚠️ Obtener el ID de la plantilla desde window.lastViewedPlantillaId o desde la URL
        let plantillaId = w.lastViewedPlantillaId;
        
        // Fallback: Intentar obtener el ID de la URL si no está en window
        if (!plantillaId) {
            const pathParts = w.location.pathname.split('/');
            const idFromUrl = pathParts[pathParts.length - 2]; // El ID está antes del último slash
            if (idFromUrl && !isNaN(parseInt(idFromUrl, 10))) {
                plantillaId = parseInt(idFromUrl, 10);
            }
        }
        
        if (!plantillaId) {
            console.error('[plantilla_ver] No se encontró el ID de la plantilla');
            if (w.UIManager) {
                w.UIManager.notifyError({ status: 400, data: { detail: 'ID de plantilla no proporcionado' } }, 'Ver Plantilla');
            }
            return;
        }

        const res = await w.http('GET', `/api/v1/cotizaciones/configuracion/${plantillaId}/`);
        if (!res.ok) {
            if (w.UIManager) {
                w.UIManager.notifyError(res, 'Ver Plantilla');
            }
            return;
        }

        const data = res.data;

        // ⚠️ Mapeo de datos al DOM
        const nombreEl = d.getElementById('view-nombre');
        const tipoEl = d.getElementById('view-tipo');
        const ivaEl = d.getElementById('view-iva');
        const prefijoEl = d.getElementById('view-prefijo');
        const sufijoEl = d.getElementById('view-sufijo');
        const secuenciaEl = d.getElementById('view-secuencia');

        if (nombreEl) nombreEl.textContent = data.nombre_configuracion || '-';
        if (tipoEl) tipoEl.textContent = data.tipo_plantilla_display || data.tipo_plantilla || '-';
        if (ivaEl) ivaEl.textContent = parseFloat(data.iva_porcentaje_default || 0).toFixed(2);
        if (prefijoEl) prefijoEl.textContent = data.prefijo_secuencia || '(Ninguno)';
        if (sufijoEl) sufijoEl.textContent = data.sufijo_secuencia || '(Ninguno)';
        if (secuenciaEl) secuenciaEl.textContent = data.ultimo_numero || '0';

        // ⚠️ Mostrar sección AIU solo si está activa
        const sectionAiu = d.getElementById('view-section-aiu');
        if (data.usa_aiu && sectionAiu) {
            sectionAiu.classList.remove('d-none');
            const adminEl = d.getElementById('view-aiu-admin');
            const imprevEl = d.getElementById('view-aiu-imprev');
            const utilEl = d.getElementById('view-aiu-util');
            
            if (adminEl) adminEl.textContent = parseFloat(data.aiu_admin_default || 0).toFixed(2);
            if (imprevEl) imprevEl.textContent = parseFloat(data.aiu_imprevistos_default || 0).toFixed(2);
            if (utilEl) utilEl.textContent = parseFloat(data.aiu_utilidad_default || 0).toFixed(2);
        } else if (sectionAiu) {
            sectionAiu.classList.add('d-none');
        }

        // ⚠️ Abrir el offcanvas automáticamente después de cargar los datos
        const offcanvasEl = d.getElementById('offcanvas-container');
        if (offcanvasEl && w.bootstrap) {
            const offcanvas = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
            offcanvas.show();
        }
    }

    // ⚠️ Inicialización: Esperar a que el DOM esté listo
    function init() {
        if (d.readyState === 'loading') {
            d.addEventListener('DOMContentLoaded', cargarDetalle);
        } else {
            cargarDetalle();
        }
    }

    init();

})(window, document);
