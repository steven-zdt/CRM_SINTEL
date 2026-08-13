/**
 * Feature: Listado de Empresa (singleton por tenant)
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#empresa-panel,
 * cargada por atributos hx-get/hx-trigger declarados en empresa_list.html).
 * Columnas viven en tables.py/views.py (server-side).
 * Namespace: window.EmpresaListModule
 */
(function(w, d) {
    'use strict';

    const MOD = '[empresa.list]';

    // Helper anti-backdrop-acumulado (patron inventario v3.9.0)
    function mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(el);
    }

    // Funcion global de refresco: dispara el evento que el panel HTMX escucha
    // via hx-trigger="load, empresa-updated from:body" (ver empresa_list.html).
    w.refreshEmpresaTable = function () {
        d.body.dispatchEvent(new CustomEvent('empresa-updated'));
    };

    function initListEvents() {
        d.body.addEventListener('click', async (e) => {
            const btn = e.target.closest('#empresa-panel .btn-edit-empresa');
            if (!btn) return;

            e.preventDefault();
            e.stopPropagation();

            const id = btn.getAttribute('data-id');
            if (!id) {
                console.warn(`${MOD} Botón sin data-id`);
                return;
            }

            const originalHTML = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

            try {
                await htmx.ajax('GET', `/api/v1/empresas/gestor-offcanvas/?id=${id}`, {
                    target: '#offcanvas-container-empresa',
                    swap: 'innerHTML'
                });
                const offcanvasEl = d.getElementById('offcanvas-empresa');
                if (offcanvasEl) {
                    mostrarOffcanvasSeguro(offcanvasEl);
                }
            } catch (error) {
                console.error(`${MOD} Error al cargar Offcanvas:`, error);
                w.SintelFeedback?.error?.('Error al cargar el formulario de empresa');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            }
        });
    }

    function initEventListeners() {
        d.addEventListener('empresaGuardada', () => {
            w.refreshEmpresaTable();
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

    w.EmpresaListModule = {
        init,
        refresh: () => w.refreshEmpresaTable(),
        mostrarOffcanvasSeguro
    };

})(window, document);
