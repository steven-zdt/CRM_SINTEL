/**
 * Dashboard API - SSoT de URLs y endpoints
 * 
 * Namespace: window.Sintel.Dashboard.API
 * Versión: v3.5
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Dashboard = window.Sintel.Dashboard || {};

    const API = {
        dashboard: {
            summary: '/api/v1/dashboard/summary/',
            activity: '/api/v1/dashboard/activity/',
            widgets: '/api/v1/dashboard/widgets/'
        },
        facturas: {
            summary: '/api/v1/facturas/summary/'
        },
        clientes: {
            summary: '/api/v1/clientes/summary/'
        }
    };

    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
    };

    function getHeaders() {
        const headers = { ...defaultHeaders };
        const token = window.jwtAuth?.getAccessToken?.();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    window.Sintel.Dashboard.API = API;
    window.Sintel.Dashboard.getHeaders = getHeaders;
})();
