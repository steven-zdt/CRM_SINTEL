/**
 * Feature: Listado de MailInboxConfig
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#mailinboxconfig-panel,
 * cargada por atributos hx-get/hx-trigger declarados en mailinbox_list.html).
 * Columnas viven en tables.py/views.py (server-side).
 * Namespace: window.MailInboxConfigListModule
 */
(function(w, d) {
    'use strict';

    const MOD = '[mailinboxconfig.list]';
    const CONTAINER_ID = 'offcanvas-container-mailinbox';

    // Helper anti-backdrop-acumulado (patron inventario v3.9.0)
    function mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(el);
    }

    // Funcion global de refresco: dispara el evento que el panel HTMX escucha
    // via hx-trigger="load, mailinboxconfig-updated from:body" (ver mailinbox_list.html).
    w.refreshMailInboxConfigTable = function () {
        d.body.dispatchEvent(new CustomEvent('mailinboxconfig-updated'));
    };

    function initListEvents() {
        d.body.addEventListener('click', async (e) => {
            const btnEdit   = e.target.closest('#mailinboxconfig-panel .btn-edit-mailinbox');
            const btnDelete = e.target.closest('#mailinboxconfig-panel .btn-delete-mailinbox');

            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();
                const id = btnEdit.getAttribute('data-id');
                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `/api/v1/empresas/mail-inbox-config/render-offcanvas/?id=${id}`, {
                        target: `#${CONTAINER_ID}`,
                        swap: 'innerHTML'
                    });
                    const el = d.getElementById('offcanvas-mailinbox');
                    if (el) {
                        mostrarOffcanvasSeguro(el);
                    }
                } catch (error) {
                    console.error(`${MOD} Error abriendo editor:`, error);
                    w.SintelFeedback?.error?.('Error al cargar el formulario');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
            }

            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                const id = btnDelete.getAttribute('data-id');
                if (!id || !(await w.UIManager?.confirm('Eliminar esta configuracion de buzon?'))) return;
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const res = await w.Sintel.Core.Http.request('DELETE', `/api/v1/empresas/mail-inbox-config/${id}/`);
                    if (res.ok) {
                        w.SintelFeedback?.success?.('Configuracion eliminada');
                        d.dispatchEvent(new Event('mailinboxConfigGuardado'));
                    } else {
                        w.SintelFeedback?.error?.(res.data?.error || 'Error al eliminar');
                    }
                } catch (error) {
                    console.error(`${MOD} Error eliminando:`, error);
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
            }
        });
    }

    function initEventListeners() {
        d.addEventListener('mailinboxConfigGuardado', () => {
            w.refreshMailInboxConfigTable();
        });
    }

    // El boton "Nueva Configuracion" (#btn-mailinbox-crear, en mailinbox_list.html)
    // ya abre el offcanvas via atributos hx-get/hx-target propios -- no requiere
    // binding JS adicional. Su apertura visual la dispara el hx-on::after-request
    // inline del propio boton.

    function init() {
        initListEvents();
        initEventListeners();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    w.MailInboxConfigListModule = {
        init,
        refresh: () => w.refreshMailInboxConfigTable(),
        mostrarOffcanvasSeguro
    };

})(window, document);
