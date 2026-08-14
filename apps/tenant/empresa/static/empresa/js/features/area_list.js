/**
 * Feature: Listado de Area
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#areas-panel,
 * cargada por atributos hx-get/hx-trigger declarados en empresa_list.html).
 * Columnas viven en tables.py/views.py (server-side).
 * Namespace: window.AreaListModule
 */
(function(w, d) {
    'use strict';

    const MOD = '[area.list]';

    // Helper anti-backdrop-acumulado (patron inventario v3.9.0)
    function mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(el);
    }

    // Funcion global de refresco: dispara el evento que el panel HTMX escucha
    // via hx-trigger="load, area-updated from:body" (ver empresa_list.html).
    w.refreshAreaTable = function () {
        d.body.dispatchEvent(new CustomEvent('area-updated'));
    };

    function initListEvents() {
        d.body.addEventListener('click', async (e) => {
            const btnEdit   = e.target.closest('#areas-panel .btn-edit-area');
            const btnDelete = e.target.closest('#areas-panel .btn-delete-area');

            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnEdit.getAttribute('data-uuid');
                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `/api/v1/empresas/areas/render-offcanvas/?uuid=${uuid}`, {
                        target: '#offcanvas-container-area',
                        swap: 'innerHTML'
                    });
                    mostrarOffcanvasSeguro(d.getElementById('offcanvas-area'));
                } catch (error) {
                    console.error(`${MOD} Error al cargar offcanvas:`, error);
                    w.SintelFeedback?.error?.('Error al cargar el formulario de area');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
            }

            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnDelete.getAttribute('data-uuid');
                if (!uuid || !(await w.UIManager?.confirm('Eliminar esta area?'))) return;
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const res = await w.Sintel.Core.Http.request('DELETE', `/api/v1/empresas/areas/${uuid}/`);
                    if (res.ok) {
                        w.SintelFeedback?.success?.('Area eliminada correctamente');
                        d.dispatchEvent(new Event('areaGuardada'));
                    } else {
                        w.SintelFeedback?.error?.(res.data?.error || 'Error al eliminar el area');
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar area:`, error);
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
            }
        });
    }

    function initEventListeners() {
        d.addEventListener('areaGuardada', () => {
            w.refreshAreaTable();
        });
    }

    function init() {
        initListEvents();
        initEventListeners();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    w.AreaListModule = {
        init,
        refresh: () => w.refreshAreaTable(),
        mostrarOffcanvasSeguro
    };

})(window, document);
