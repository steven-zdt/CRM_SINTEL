/**
 * offcanvas.helper.js - SSoT para abrir un Bootstrap Offcanvas de forma segura.
 * Namespace: window.Sintel.Core.mostrarOffcanvasSeguro
 *
 * Consolida las 16 reimplementaciones locales de "mostrarOffcanvasSeguro"
 * encontradas en la auditoria (FE-A5, AUDITORIA_ENTERPRISE_2026-07-26.md),
 * 2 de las cuales estaban rotas (usaban bootstrap.Offcanvas.getOrCreateInstance
 * sin dispose previo — FE-A4).
 *
 * Patron obligatorio (AGENTS.md §26): SIEMPRE dispose() de la instancia
 * anterior antes de crear una nueva. Nunca usar getOrCreateInstance() sobre
 * un Offcanvas — deja backdrops/listeners huerfanos tras aperturas repetidas.
 *
 * REQUERIDO: cargar despues de Bootstrap JS y antes de cualquier modulo que
 * abra offcanvas (ver apps/tenant/core/templates/tenant/core/partials/assets_core.html).
 */
(function (w, d) {
    'use strict';

    function mostrarOffcanvasSeguro(elOrId) {
        var el = (typeof elOrId === 'string')
            ? d.getElementById(elOrId.replace(/^#/, ''))
            : elOrId;

        if (!el || !w.bootstrap || !w.bootstrap.Offcanvas) return null;

        d.querySelectorAll('.offcanvas-backdrop').forEach(function (bd) { bd.remove(); });
        d.body.classList.remove('overflow-hidden', 'modal-open', 'offcanvas-open');
        d.body.style.overflow = '';
        d.body.style.paddingRight = '';

        var prev = w.bootstrap.Offcanvas.getInstance(el);
        if (prev) {
            try { prev.dispose(); } catch (_) { /* noop */ }
        }

        try {
            var instance = new w.bootstrap.Offcanvas(el);
            instance.show();
            return instance;
        } catch (err) {
            console.error('[offcanvas.helper] Error al mostrar offcanvas:', err);
            return null;
        }
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Core = w.Sintel.Core || {};
    w.Sintel.Core.mostrarOffcanvasSeguro = mostrarOffcanvasSeguro;

})(window, document);
