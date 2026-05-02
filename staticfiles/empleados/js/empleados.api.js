/**
 * Empleados API - SSoT de URLs y endpoints
 * 
 * Namespace: window.Sintel.Empleados.API
 * Versión: v2.61.4
 */
(function() {
    'use strict';

    // Namespace
    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};

    /**
     * API Endpoints para Empleados
     */
    const API = {
        // Base URL
        base: '/api/v1/empleados',
        
        // Empleados
        empleados: {
            list: '/api/v1/empleados/',
            detail: (id) => `/api/v1/empleados/${id}/`,
            summary: '/api/v1/empleados/summary/',
            historial: (id) => `/api/v1/empleados/${id}/historial-nominas/`,
            contratoDisponible: (id) => `/api/v1/empleados/${id}/contrato-disponible/`,
            gestorOffcanvas: '/api/v1/empleados/gestor-offcanvas/'
        },
        
        // Contratos
        contratos: {
            list: '/api/v1/empleados/contratos/',
            detail: (id) => `/api/v1/empleados/contratos/${id}/`,
            crearOffcanvas: '/api/v1/empleados/contratos/render-offcanvas/crear/',
            editarOffcanvas: (id) => `/api/v1/empleados/contratos/${id}/render-offcanvas/editar/`,
            cancelar: (id) => `/api/v1/empleados/contratos/${id}/cancelar/`
        },
        
        // Devengos (Nómina)
        devengos: {
            list: '/api/v1/empleados/devengos/',
            detail: (id) => `/api/v1/empleados/devengos/${id}/`,
            anular: (id) => `/api/v1/empleados/devengos/${id}/anular/`
        }
    };

    /**
     * Headers por defecto para fetch
     */
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
    };

    /**
     * Inyectar JWT si está disponible
     */
    function getHeaders() {
        const headers = { ...defaultHeaders };
        const token = window.jwtAuth?.getAccessToken?.();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    // Exportar API
    window.Sintel.Empleados.API = API;
    window.Sintel.Empleados.getHeaders = getHeaders;

})();
