// @ts-nocheck
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
            crearOffcanvas: '/api/v1/empleados/devengos/render-offcanvas/crear/',
            infoEmpleado: (empleadoId) => `/api/v1/empleados/devengos/info-empleado/?empleado=${empleadoId}`,
            anular: (id) => `/api/v1/empleados/devengos/${id}/anular/`,
            ultimoPeriodo: (empleadoId) =>
                `/api/v1/empleados/devengos/ultimo-periodo/?empleado=${empleadoId}`,
            verificarPeriodo: (empleadoId, periodoMes, dias, fechaInicio, fechaFin) => {
                const p = new URLSearchParams({ empleado: empleadoId, periodo_mes: periodoMes, dias: dias || 0 });
                if (fechaInicio) p.set('fecha_inicio', fechaInicio);
                if (fechaFin)    p.set('fecha_fin', fechaFin);
                return `/api/v1/empleados/devengos/verificar-periodo/?${p}`;
            },
            empleadosDisponibles: (fechaInicio, fechaFin) =>
                `/api/v1/empleados/devengos/empleados-disponibles/?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`,
            empleadosConNominas: (search) =>
                `/api/v1/empleados/devengos/empleados-con-nominas/${search ? '?search=' + encodeURIComponent(search) : ''}`,
        },
        // Resoluciones DIAN
        resoluciones: {
            list:            '/api/v1/empleados/resoluciones-dian/',
            detail:          (uuid) => `/api/v1/empleados/resoluciones-dian/${uuid}/`,
            crearOffcanvas:  '/api/v1/empleados/resoluciones-dian/render-offcanvas/crear/',
        },
        // Liquidaciones de Prestaciones
        liquidaciones: {
            list:            '/api/v1/empleados/liquidaciones-prestaciones/',
            detail:          (uuid) => `/api/v1/empleados/liquidaciones-prestaciones/${uuid}/`,
            crearOffcanvas:  '/api/v1/empleados/liquidaciones-prestaciones/render-offcanvas/crear/',
            simular:         (contratoUuid, fechaCorte, tipoLiq) => {
                const p = new URLSearchParams({
                    contrato_uuid:    contratoUuid || '',
                    fecha_corte:      fechaCorte   || '',
                    tipo_liquidacion: tipoLiq      || 'LIQUIDACION_DEFINITIVA',
                });
                return `/api/v1/empleados/liquidaciones-prestaciones/simular/?${p.toString()}`;
            },
        }
    };

    /**
     * Lee el CSRF token en tiempo de request (no al cargar el modulo).
     * Intenta el campo hidden del formulario primero, luego la cookie.
     */
    function getCsrfToken() {
        const domToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (domToken) return domToken;
        return document.cookie
            .split('; ')
            .find(r => r.startsWith('csrftoken='))
            ?.split('=')[1] || '';
    }

    /**
     * Headers dinamicos por request — CSRF se lee en el momento, no al cargar.
     */
    function getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        };
        const token = window.jwtAuth?.getAccessToken?.();
        if (token) headers['Authorization'] = `Bearer ${token}`;
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
     * Obtiene la lista de empleados disponibles para un período sin nóminas cruzadas.
     */
    window.Sintel.Empleados.API.getEmpleadosDisponibles = async (fechaInicio, fechaFin) => {
        if (!fechaInicio || !fechaFin) return { ok: false, data: [] };
        const url = API.devengos.empleadosDisponibles(fechaInicio, fechaFin);
        return await request(url);
    };

})();
