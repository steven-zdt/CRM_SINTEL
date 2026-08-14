/**
 * Feature: Listado de Sede
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#sedes-panel,
 * cargada por atributos hx-get/hx-trigger declarados en empresa_list.html).
 * Columnas viven en tables.py/views.py (server-side).
 * Namespace: window.SedeListModule
 */
(function(w, d) {
    'use strict';

    const MOD = '[sede.list]';

    // Helper anti-backdrop-acumulado (patron inventario v3.9.0)
    function mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(el);
    }

    // Funcion global de refresco: dispara el evento que el panel HTMX escucha
    // via hx-trigger="load, sede-updated from:body" (ver empresa_list.html).
    w.refreshSedeTable = function () {
        d.body.dispatchEvent(new CustomEvent('sede-updated'));
    };

    function initListEvents() {
        d.body.addEventListener('click', async (e) => {
            const btnEdit   = e.target.closest('#sedes-panel .btn-edit-sede');
            const btnDelete = e.target.closest('#sedes-panel .btn-delete-sede');

            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnEdit.getAttribute('data-uuid');
                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `/api/v1/empresas/sedes/render-offcanvas/?uuid=${uuid}`, {
                        target: '#offcanvas-container-sede',
                        swap: 'innerHTML'
                    });
                    mostrarOffcanvasSeguro(d.getElementById('offcanvas-sede'));
                } catch (error) {
                    console.error(`${MOD} Error al cargar offcanvas:`, error);
                    w.SintelFeedback?.error?.('Error al cargar el formulario de sede');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
            }

            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnDelete.getAttribute('data-uuid');
                if (!uuid || !(await w.UIManager?.confirm('Eliminar esta sede?'))) return;
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const res = await w.Sintel.Core.Http.request('DELETE', `/api/v1/empresas/sedes/${uuid}/`);
                    if (res.ok) {
                        w.SintelFeedback?.success?.('Sede eliminada correctamente');
                        d.dispatchEvent(new Event('sedeGuardada'));
                    } else {
                        w.SintelFeedback?.error?.(res.data?.error || 'Error al eliminar la sede');
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar sede:`, error);
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
            }
        });
    }

    function initEventListeners() {
        d.addEventListener('sedeGuardada', () => {
            w.refreshSedeTable();
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

    w.SedeListModule = {
        init,
        refresh: () => w.refreshSedeTable(),
        mostrarOffcanvasSeguro
    };

})(window, document);
