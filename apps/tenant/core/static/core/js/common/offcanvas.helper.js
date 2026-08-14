/**
 * offcanvas.helper.js - SSoT para abrir/cerrar un Bootstrap Offcanvas de forma segura.
 * Namespace: window.Sintel.Core.mostrarOffcanvasSeguro
 *
 * Consolida las 16 reimplementaciones locales de "mostrarOffcanvasSeguro"
 * encontradas en la auditoria (FE-A5, AUDITORIA_ENTERPRISE_2026-07-26.md),
 * 2 de las cuales estaban rotas (usaban bootstrap.Offcanvas.getOrCreateInstance
 * sin dispose previo — FE-A4).
 *
 * F33.4: extendido con un segundo parametro opcional {action:'show'|'hide'}
 * (default 'show', compatible con los ~25 llamadores existentes sin
 * cambios). Consolida tambien UIManager.handleOffcanvas (F33.0 §12b),
 * una segunda implementacion "safe offcanvas" escrita independientemente
 * con adopcion comparable (~22 archivos) -- UIManager.handleOffcanvas
 * ahora delega aqui como alias, un solo cuerpo de logica real. La
 * limpieza de backdrops incluye tambien '.modal-backdrop' y
 * documentElement.style.overflow (heredado de UIManager._forceCleanup,
 * mas completo que la limpieza original de este archivo).
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

    function _limpiarBackdrops() {
        d.querySelectorAll('.offcanvas-backdrop, .modal-backdrop').forEach(function (bd) { bd.remove(); });
        d.body.classList.remove('overflow-hidden', 'modal-open', 'offcanvas-open');
        d.body.style.overflow = '';
        d.body.style.paddingRight = '';
        d.documentElement.style.overflow = '';
    }

    function _resolverEl(elOrId) {
        return (typeof elOrId === 'string')
            ? d.getElementById(elOrId.replace(/^#/, '')) || d.querySelector(elOrId)
            : elOrId;
    }

    function mostrarOffcanvasSeguro(elOrId, opts) {
        var action = (opts && opts.action) || 'show';
        var el = _resolverEl(elOrId);

        if (!el || !w.bootstrap || !w.bootstrap.Offcanvas) return null;

        try {
            var prev = w.bootstrap.Offcanvas.getInstance(el);

            if (action === 'hide') {
                var instanceToHide = prev || new w.bootstrap.Offcanvas(el);
                instanceToHide.hide();
                el.addEventListener('hidden.bs.offcanvas', function () {
                    if (d.body.contains(el)) {
                        var current = w.bootstrap.Offcanvas.getInstance(el);
                        if (current) { try { current.dispose(); } catch (_) { /* noop */ } }
                    }
                }, { once: true });
                return instanceToHide;
            }

            _limpiarBackdrops();
            if (prev) {
                try { prev.dispose(); } catch (_) { /* noop */ }
            }

            var instance = new w.bootstrap.Offcanvas(el);
            instance.show();
            return instance;
        } catch (err) {
            console.error('[offcanvas.helper] Error en mostrarOffcanvasSeguro:', err);
            _limpiarBackdrops();
            return null;
        }
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Core = w.Sintel.Core || {};
    w.Sintel.Core.mostrarOffcanvasSeguro = mostrarOffcanvasSeguro;

})(window, document);
