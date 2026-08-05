/**
 * Dashboard API v3.9.4 — SSoT de URLs y endpoints
 * Pull Model Delegado: Métricas consolidadas desde extractores
 *
 * Namespace: window.Sintel.Dashboard.API
 * Versión: v3.9.4
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Dashboard = window.Sintel.Dashboard || {};

    const API = {
        // Endpoints principales (v3.9.4 Pull Model)
        dashboard: {
            metricas: '/api/v1/dashboard/',              // GET — métricas consolidadas
            invalidarCache: '/api/v1/dashboard/invalidar-cache/',  // POST — invalida caché (admin)
            kpisPorSede: '/api/v1/dashboard/kpis-por-sede/',      // GET — KPIs por sede

            // Legacy (v3.5 compatibilidad)
            data: '/api/v1/dashboard/data/',
            summary: '/api/v1/dashboard/summary/',
            kpis: '/api/v1/dashboard/kpis/',
            quickActions: '/api/v1/dashboard/quick-actions/'
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

    /**
     * Obtiene métricas consolidadas del dashboard.
     * GET /api/v1/dashboard/
     */
    async function obtenerMetricas() {
        const response = await fetch(API.dashboard.metricas, {
            method: 'GET',
            headers: getHeaders()
        });
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Invalida el caché de métricas (solo admins).
     * POST /api/v1/dashboard/invalidar-cache/
     */
    async function invalidarCache() {
        const response = await fetch(API.dashboard.invalidarCache, {
            method: 'POST',
            headers: getHeaders()
        });
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Obtiene KPIs por sede.
     * GET /api/v1/dashboard/kpis-por-sede/
     */
    async function obtenerKpisPorSede(fechaInicio = '', fechaFin = '') {
        let url = API.dashboard.kpisPorSede;
        const params = [];
        if (fechaInicio) params.push(`fecha_inicio=${fechaInicio}`);
        if (fechaFin) params.push(`fecha_fin=${fechaFin}`);
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        const response = await fetch(url, {
            method: 'GET',
            headers: getHeaders()
        });
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }

    window.Sintel.Dashboard.API = API;
    window.Sintel.Dashboard.getHeaders = getHeaders;
    window.Sintel.Dashboard.obtenerMetricas = obtenerMetricas;
    window.Sintel.Dashboard.invalidarCache = invalidarCache;
    window.Sintel.Dashboard.obtenerKpisPorSede = obtenerKpisPorSede;
})();
