// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Periodo List Module — Fase 5-BIS: tabla server-rendered via
 * django-tables2 + HTMX (#empleados-periodos-panel, cargada por atributos
 * hx-get/hx-trigger declarados en empleados_list.html -- carga solo al
 * abrir el sub-tab de Periodos de Nomina por primera vez).
 * Namespace: window.Sintel.Empleados.PeriodoList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const PANEL_SELECTOR = '#empleados-periodos-panel';

    // init()/redraw() no inicializan nada (el panel HTMX se auto-carga);
    // se conservan por si el orquestador del modulo las invoca.
    function init() {}
    function redraw() {}

    function reload() {
        d.body.dispatchEvent(new CustomEvent('periodo-updated'));
    }

    function attachTableListeners() {
        const panel = d.querySelector(PANEL_SELECTOR);
        if (!panel) return;

        panel.addEventListener('click', (ev) => {
            const btn = ev.target.closest('.btn-gestionar-periodo');
            if (!btn) return;
            ev.preventDefault();
            const uuid = btn.dataset.uuid;
            if (!uuid) return;
            w.Sintel.Empleados.PeriodoDetail?.open(uuid);
        });
    }

    function attachToolbarListeners() {
        const btnNuevo = d.getElementById('btn-nuevo-periodo');
        if (btnNuevo && !btnNuevo.dataset.bound) {
            btnNuevo.dataset.bound = '1';
            btnNuevo.addEventListener('click', () => {
                w.Sintel.Empleados.PeriodoEditor?.open();
            });
        }
    }

    function _init() {
        attachTableListeners();
        attachToolbarListeners();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

    w.Sintel.Empleados.PeriodoList = { init, reload, redraw };

})(window, document);
