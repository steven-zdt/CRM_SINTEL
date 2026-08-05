/**
 * venta_list.js — Feature List para Venta
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#ventas-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_ventas.html).
 * Este archivo solo maneja: accion de fila (ver detalle), apertura de
 * offcanvas, el toggle visual de los pills de filtro por estado, y el
 * disparo del evento que hace que HTMX vuelva a pedir la tabla al backend
 * tras una mutacion. Columnas/orden/paginacion/KPIs viven en
 * tables.py/views.py (server-side) -- no reimplementar aqui.
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    var PANEL_SELECTOR = '#ventas-panel';

    var List = {
        reload: function () {
            d.body.dispatchEvent(new CustomEvent('venta-updated'));
        },

        recargar: function () {
            this.reload();
        },

        abrirDetalle: function (uuid) {
            var url = w.Sintel.Ventas.API.renderDetalle(uuid);
            var container = d.getElementById('offcanvas-container-ventas');
            if (!container) return;
            htmx.ajax('GET', url, { target: '#offcanvas-container-ventas', swap: 'innerHTML' });
        },
    };

    w.Sintel.Ventas.List = List;

    // ── Acciones de fila (delegado sobre el panel persistente) ──────────────

    function attachTableListeners() {
        var panel = d.querySelector(PANEL_SELECTOR);
        if (!panel) return;

        panel.addEventListener('click', function (ev) {
            var btn = ev.target.closest('.btn-ver-venta');
            if (!btn) return;
            ev.preventDefault();
            var uuid = btn.dataset.uuid;
            if (uuid) List.abrirDetalle(uuid);
        });
    }

    // ── Filtros de estado (pills) — solo toggle visual, la carga la hace HTMX ──

    function bindFiltrosEstado() {
        var pills = d.querySelectorAll('[data-filtro-venta-estado]');
        pills.forEach(function (btn) {
            btn.addEventListener('click', function () {
                pills.forEach(function (b) { b.classList.remove('active'); });
                btn.classList.add('active');
            });
        });
    }

    function setup() {
        attachTableListeners();
        bindFiltrosEstado();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

})(window, document);
