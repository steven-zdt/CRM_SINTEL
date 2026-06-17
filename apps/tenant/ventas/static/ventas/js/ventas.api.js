/**
 * ventas.api.js — SSoT de URLs y llamadas HTTP para el modulo Ventas.
 * Namespace: window.Sintel.Ventas.API
 */
(function (w) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    const API_ROOT = '/api/v1/ventas/';

    function getHeaders() {
        var headers = {
            'Content-Type': 'application/json',
        };
        var csrf = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrf) headers['X-CSRFToken'] = csrf.value;
        var token = w.jwtAuth && typeof w.jwtAuth.getAccessToken === 'function'
            ? w.jwtAuth.getAccessToken()
            : null;
        if (token) headers['Authorization'] = 'Bearer ' + token;
        return headers;
    }

    async function _fetch(method, url, data) {
        var opts = { method: method, headers: getHeaders() };
        if (data !== undefined && data !== null) {
            opts.body = JSON.stringify(data);
        }
        var res = await fetch(url, opts);
        if (!res.ok) {
            var err;
            try { err = await res.json(); } catch (_) { err = { detail: 'HTTP ' + res.status }; }
            var ex = new Error('[Ventas.API] ' + method + ' ' + url + ' -> ' + res.status);
            ex.status = res.status;
            ex.data = err;
            throw ex;
        }
        if (res.status === 204) return { success: true };
        return await res.json();
    }

    var API = {
        // ── Endpoints de recurso ──────────────────────────────────────────

        list: function (params) {
            var url = new URL(API_ROOT, w.location.origin);
            if (params) Object.keys(params).forEach(function (k) {
                if (params[k] !== null && params[k] !== undefined) url.searchParams.set(k, params[k]);
            });
            return _fetch('GET', url.toString());
        },

        detail: function (uuid) {
            return _fetch('GET', API_ROOT + uuid + '/');
        },

        create: function (data) {
            return _fetch('POST', API_ROOT, data);
        },

        update: function (uuid, data) {
            return _fetch('PATCH', API_ROOT + uuid + '/', data);
        },

        eliminar: function (uuid, motivo) {
            return _fetch('DELETE', API_ROOT + uuid + '/', { motivo: motivo || '' });
        },

        // ── Acciones de maquina de estados ──────────────────────────────

        confirmar: function (uuid) {
            return _fetch('POST', API_ROOT + uuid + '/confirmar/');
        },

        facturar: function (uuid) {
            return _fetch('POST', API_ROOT + uuid + '/facturar/');
        },

        anular: function (uuid, motivo) {
            return _fetch('POST', API_ROOT + uuid + '/anular/', { motivo: motivo || '' });
        },

        // ── Endpoints de renderizado HTMX ────────────────────────────────

        renderCrear: function () {
            return API_ROOT + 'render-offcanvas/crear/';
        },

        renderDetalle: function (uuid) {
            return API_ROOT + 'render-offcanvas/detalle/?uuid=' + uuid;
        },

        // ── Listas auxiliares ────────────────────────────────────────────

        clientes: {
            list: '/api/v1/clientes/'
        },

        productos: {
            list: '/api/v1/inventario/productos/'
        },

        servicios: {
            list: '/api/v1/inventario/servicios/'
        },
    };

    w.Sintel.Ventas.API = API;
    w.Sintel.Ventas.getHeaders = getHeaders;

})(window);
