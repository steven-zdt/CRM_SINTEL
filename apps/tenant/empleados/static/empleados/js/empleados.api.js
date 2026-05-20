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
        },

        // Contabilidad (Vínculos)
        contabilidad: {
            search: (query) => `/api/v1/contabilidad/cuentas-contables/?search=${encodeURIComponent(query || '')}&app_origen=empleados&activa=true&solo_auxiliares=true`,
            getByUuid: (uuid) => `/api/v1/contabilidad/cuentas-contables/?uuid=${uuid}&app_origen=empleados&activa=true`
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

    /**
     * Wrapper para fetch con soporte JWT
     */
    async function request(url, options = {}) {
        const headers = getHeaders();
        const config = {
            ...options,
            headers: {
                ...headers,
                ...options.headers
            }
        };

        const response = await fetch(url, config);
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            return { ok: false, status: response.status, data };
        }
        const data = await response.json();
        return { ok: true, status: response.status, data };
    }

    // Exportar API
    window.Sintel.Empleados.API = API;
    window.Sintel.Empleados.getHeaders = getHeaders;
    window.Sintel.Empleados.request = request;

    /**
     * [v3.5] Obtiene el detalle de una cuenta contable por UUID
     */
    window.Sintel.Empleados.API.getCuentaByUuid = async (uuid) => {
        if (!uuid) return { ok: false, data: null };
        const url = API.contabilidad.getByUuid(uuid);
        return await request(url);
    };

})();
