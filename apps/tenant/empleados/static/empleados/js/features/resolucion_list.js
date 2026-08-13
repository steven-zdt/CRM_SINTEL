// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Resolucion List Module — Fase 5-BIS: tabla server-rendered via
 * django-tables2 + HTMX (#empleados-resoluciones-panel, cargada por atributos
 * hx-get/hx-trigger declarados en empleados_list.html -- carga solo al
 * abrir el sub-tab de Resoluciones DIAN por primera vez).
 * Namespace: window.Sintel.Empleados.ResolucionList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[ResolucionList]';
    const PANEL_SELECTOR = '#empleados-resoluciones-panel';
    const API_BASE = '/api/v1/empleados/resoluciones-dian/';

    // init()/redraw() ya no inicializan nada (el panel HTMX se auto-carga);
    // se conservan porque empleados.module.js las invoca al activar el sub-tab.
    function init() {}
    function redraw() {}

    function reload() {
        d.body.dispatchEvent(new CustomEvent('resolucion-updated'));
    }

    async function _eliminar(uuid) {
        try {
            const res = await w.http('DELETE', `${API_BASE}${uuid}/`);
            if (res.ok) {
                w.UIManager?.notifySuccess('Resolución eliminada correctamente');
                reload();
            } else {
                const msg = res.data?.detail || 'Error al eliminar la resolución';
                w.UIManager?.notifyError(msg);
            }
        } catch (err) {
            console.error(`${MOD} Error al eliminar:`, err);
            w.UIManager?.notifyError('Error de conexión al eliminar la resolución');
        }
    }

    function attachTableListeners() {
        const panel = d.querySelector(PANEL_SELECTOR);
        if (!panel) return;

        panel.addEventListener('click', (ev) => {
            const btn = ev.target.closest('.btn-eliminar-resolucion');
            if (!btn) return;
            ev.preventDefault();
            const uuid = btn.dataset.uuid;
            if (!uuid) return;
            if (!confirm('¿Eliminar esta resolución DIAN? Esta acción no se puede deshacer.')) return;
            _eliminar(uuid);
        });
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', attachTableListeners);
    } else {
        attachTableListeners();
    }

    w.Sintel.Empleados.ResolucionList = { init, reload, redraw };

})(window, document);
