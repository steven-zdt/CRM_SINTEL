/**
 * Gastos API - SSoT de URLs y endpoints
 * 
 * Namespace: window.Sintel.Gastos.API
 * Versión: v2.61.4
 */
(function() {
    'use strict';

    // Namespace
    window.Sintel = window.Sintel || {};
    window.Sintel.Gastos = window.Sintel.Gastos || {};

    /**
     * API Endpoints para Gastos
     */
    const API = {
        // Gastos
        gastos: {
            list: '/api/v1/gastos/',
            detail:(id)=>`/api/v1/gastos/${id}/`,
            summary: '/api/v1/gastos/summary/',
            anular:(id)=>`/api/v1/gastos/${id}/anular/`,
            desactivar:(id)=>`/api/v1/gastos/${id}/desactivar/`
        },
        
        // Resoluciones DIAN
        resoluciones: {
            list: '/api/v1/gastos/resoluciones/',
            detail: (id) => `/api/v1/gastos/resoluciones/${id}/`,
            desactivar: (id) => `/api/v1/gastos/resoluciones/${id}/desactivar/`
        },
        
        // Proveedores (externo)
        proveedores: {
            list: '/api/v1/proveedores/'
        },
        
        // Contabilidad (externo)
        contabilidad: {
            cuentasGasto: '/api/v1/contabilidad/cuentas-gasto/'
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
    window.Sintel.Gastos.API = API;
    window.Sintel.Gastos.getHeaders = getHeaders;

})();
