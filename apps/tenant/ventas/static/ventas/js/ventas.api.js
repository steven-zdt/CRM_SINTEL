/**
 * ventas.api.js — SSoT de URLs y llamadas HTTP para el modulo Ventas.
 * Namespace: window.Sintel.Ventas.API
 */
(function (w) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    const API_ROOT = '/api/v1/ventas/';
    const RESOLUCIONES_ROOT = '/api/v1/ventas/resoluciones/';

    // F32.6: migrado a Sintel.Core.Http -- ya no reimplementa fetch+CSRF+JWT
    // (violaba el contrato "solo URLs+metodos", F31.3/F32.1). getHeaders()
    // se conserva solo por compatibilidad hacia atras (w.Sintel.Ventas.getHeaders
    // se exportaba publicamente; no se encontro ningun consumidor externo,
    // pero se deja el shape identico por si acaso). El contrato PUBLICO de
    // _fetch() (lanza Error con .status/.data en fallo) no cambia -- solo
    // el transporte interno.
    function getHeaders() {
        var headers = { 'Content-Type': 'application/json' };
        var csrf = w.Sintel?.Core?.Http?.csrf ? w.Sintel.Core.Http.csrf() : null;
        if (csrf) headers['X-CSRFToken'] = csrf;
        var token = w.jwtAuth && typeof w.jwtAuth.getAccessToken === 'function'
            ? w.jwtAuth.getAccessToken()
            : null;
        if (token) headers['Authorization'] = 'Bearer ' + token;
        return headers;
    }

    async function _fetch(method, url, data) {
        var res = await w.Sintel.Core.Http.request(method, url, data === null ? undefined : data);
        if (!res.ok) {
            var ex = new Error('[Ventas.API] ' + method + ' ' + url + ' -> ' + res.status);
            ex.status = res.status;
            ex.data = res.data || { detail: 'HTTP ' + res.status };
            throw ex;
        }
        if (res.status === 204) return { success: true };
        return res.data;
    }

    var API = {
        // ── Endpoints de Venta ───────────────────────────────────────────

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

        procesarFacturar: function (uuid) {
            return _fetch('POST', API_ROOT + uuid + '/procesar-facturar/');
        },

        anular: function (uuid, motivo) {
            return _fetch('POST', API_ROOT + uuid + '/anular/', { motivo: motivo || '' });
        },

        // ── Endpoints de renderizado HTMX — Venta ───────────────────────

        renderCrear: function () {
            return API_ROOT + 'render-offcanvas/crear/';
        },

        renderDetalle: function (uuid) {
            return API_ROOT + 'render-offcanvas/detalle/?uuid=' + uuid;
        },

        // ── Endpoints de ResolucionFacturacion ──────────────────────────

        resoluciones: {
            list: function (params) {
                var url = new URL(RESOLUCIONES_ROOT, w.location.origin);
                if (params) Object.keys(params).forEach(function (k) {
                    if (params[k] !== null && params[k] !== undefined) url.searchParams.set(k, params[k]);
                });
                return _fetch('GET', url.toString());
            },

            detail: function (uuid) {
                return _fetch('GET', RESOLUCIONES_ROOT + uuid + '/');
            },

            create: function (data) {
                return _fetch('POST', RESOLUCIONES_ROOT, data);
            },

            update: function (uuid, data) {
                return _fetch('PATCH', RESOLUCIONES_ROOT + uuid + '/', data);
            },

            eliminar: function (uuid) {
                return _fetch('DELETE', RESOLUCIONES_ROOT + uuid + '/');
            },

            renderCrear: function () {
                return RESOLUCIONES_ROOT + 'render-offcanvas/crear/';
            },

            renderEditar: function (uuid) {
                return RESOLUCIONES_ROOT + 'render-offcanvas/editar/?uuid=' + uuid;
            },
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
