/**
 * SedeSelector (ADR-003) - Cambia la "sede activa" de la sesion desde el
 * dropdown del header compartido (tenant/partials/_header.html).
 *
 * Vanilla JS, sin dependencias - mismo patron que tabulator.factory.js.
 */
(function (w, d) {
    'use strict';

    function getCookie(name) {
        const value = `; ${d.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    async function cambiarSede(sedeUuid) {
        try {
            const resp = await fetch('/api/v1/core/contexto/sede/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') || '',
                },
                credentials: 'same-origin',
                body: JSON.stringify({ sede_uuid: sedeUuid }),
            });
            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                console.error('[SedeSelector] No se pudo cambiar de sede:', data.message || resp.statusText);
                return;
            }
            w.location.reload();
        } catch (err) {
            console.error('[SedeSelector] Error de red cambiando de sede:', err);
        }
    }

    function init() {
        d.querySelectorAll('[data-sede-uuid]').forEach((el) => {
            el.addEventListener('click', (ev) => {
                ev.preventDefault();
                cambiarSede(el.dataset.sedeUuid);
            });
        });
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Core = w.Sintel.Core || {};
    w.Sintel.Core.SedeSelector = { cambiarSede };
})(window, document);
