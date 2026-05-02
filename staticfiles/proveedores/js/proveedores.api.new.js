/**
 * Proveedores API - SSoT de URLs y endpoints v3.5
 * 
 * Namespace: window.Sintel.Proveedores.API
 * Versión: v3.5
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Proveedores = window.Sintel.Proveedores || {};

    const API = {
        proveedores: {
            list: '/api/v1/proveedores/',
            detail: (id) => '/api/v1/proveedores/' + id + '/',
            summary: '/api/v1/proveedores/summary/',
            gestorOffcanvas: '/api/v1/proveedores/gestor-offcanvas/'
        }
    };

    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
    };

    function getHeaders() {
        const headers = Object.assign({}, defaultHeaders);
        const token = window.jwtAuth?.getAccessToken?.();
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }
        return headers;
    }

    window.Sintel.Proveedores.API = API;
    window.Sintel.Proveedores.getHeaders = getHeaders;
})();
