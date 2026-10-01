/**
 * Approvals API - SSoT de URLs y endpoints del Centro de Aprobaciones.
 *
 * Namespace: window.Sintel.Approvals.API
 * Mismo patron que compras.api.js (Http centralizado, nunca fetch directo).
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Approvals = window.Sintel.Approvals || {};

    const API_ROOT = '/api/v1/dashboard/aprobaciones/';

    async function _fetch(method, url, data) {
        const res = await window.Sintel.Core.Http.request(method, url, data);
        if (!res.ok) {
            const error = new Error(`[Approvals.API] ${method} ${url} -> ${res.status}`);
            error.status = res.status;
            error.data = res.data || { detail: `HTTP ${res.status}` };
            throw error;
        }
        if (res.status === 204) return { success: true };
        return res.data;
    }

    const API = {
        list: API_ROOT,
        dtUrl: `${API_ROOT}dt/`,
        detail: (uuid) => `${API_ROOT}${uuid}/`,
        resumen: () => _fetch('GET', `${API_ROOT}resumen/`),
        trazabilidad: (uuid) => _fetch('GET', `${API_ROOT}${uuid}/trazabilidad/`),
        aprobar: (uuid, observacion) => _fetch('POST', `${API_ROOT}${uuid}/aprobar/`, { observacion: observacion || '' }),
        rechazar: (uuid, motivo) => _fetch('POST', `${API_ROOT}${uuid}/rechazar/`, { motivo: motivo }),
    };

    window.Sintel.Approvals.API = API;

})();
