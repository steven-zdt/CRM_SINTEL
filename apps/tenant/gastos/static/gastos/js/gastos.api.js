/**
 * Gastos API - SSoT de URLs y endpoints
 * 
 * Namespace: window.Sintel.Gastos.API
 * Version: v2.62.0
 */
(function() {
    'use strict';

    // Namespace
    window.Sintel = window.Sintel || {};
    window.Sintel.Gastos = window.Sintel.Gastos || {};

    const API_ROOT = '/api/v1/gastos/';
    const RESOLUCION_ROOT = '/api/v1/resoluciones-dian/';

    /**
     * API Endpoints para Gastos (Gateway Directo)
     */
    const API = {
        gastos: {
            list: API_ROOT,
            detail: (id) => `${API_ROOT}${id}/`,
            anular: (id) => `${API_ROOT}${id}/anular/`,
            create: async function(data) {
                const response = await fetch(API_ROOT, {
                    method: 'POST',
                    headers: window.Sintel.Gastos.getHeaders(),
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    let errorData = {};
                    try {
                        errorData = await response.json();
                    } catch(e) {
                        errorData = { detail: `HTTP ${response.status}` };
                    }
                    const error = new Error('Gasto creation failed');
                    error.status = response.status;
                    error.data = errorData;
                    console.error('[API] Gasto create error:', errorData);
                    throw error;
                }
                return await response.json();
            },
            update: async function(uuid, data) {
                const response = await fetch(`${API_ROOT}${uuid}/`, {
                    method: 'PATCH',
                    headers: window.Sintel.Gastos.getHeaders(),
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    let errorData = {};
                    try {
                        errorData = await response.json();
                    } catch(e) {
                        errorData = { detail: `HTTP ${response.status}` };
                    }
                    const error = new Error('Gasto update failed');
                    error.status = response.status;
                    error.data = errorData;
                    console.error('[API] Gasto update error:', errorData);
                    throw error;
                }
                return await response.json();
            },
        },
        resoluciones: {
            list: RESOLUCION_ROOT,
            detail: (id) => `${RESOLUCION_ROOT}${id}/`,
            create: async function(data) {
                const response = await fetch(RESOLUCION_ROOT, {
                    method: 'POST',
                    headers: window.Sintel.Gastos.getHeaders(),
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    try { response.data = await response.json(); } catch(e) {}
                    throw response;
                }
                return await response.json();
            },
            update: async function(uuid, data) {
                const response = await fetch(`${RESOLUCION_ROOT}${uuid}/`, {
                    method: 'PUT',
                    headers: window.Sintel.Gastos.getHeaders(),
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    try { response.data = await response.json(); } catch(e) {}
                    throw response;
                }
                return await response.json();
            },
            activa: `${RESOLUCION_ROOT}activa/`
        },
        contabilidad: {
            searchCuentas: (q) => `/api/v1/contabilidad/cuentas-contables/?search=${encodeURIComponent(q)}&app_origen=gastos&activa=true&tipo=GASTO`,
            getCuentaByUuid: (uuid) => `/api/v1/contabilidad/cuentas-contables/?uuid=${encodeURIComponent(uuid)}&app_origen=gastos`,
            obtenerRetenciones: async function(nit) {
                const response = await fetch(`/api/v1/contabilidad/retenciones/obtener-por-tercero/?nit=${encodeURIComponent(nit)}&tipo_tercero=PROVEEDOR&naturaleza=COMPRA`, {
                    headers: window.Sintel.Gastos.getHeaders()
                });
                if (!response.ok) return null;
                return await response.json();
            }
        },
        proveedores: {
            list: '/api/v1/proveedores/'
        },
        
        // Renderizado (HTMX / Views)
        endpoints: {
            renderCrear: () => `${API_ROOT}render-offcanvas/crear/`,
            renderEditar: (id) => `${API_ROOT}render-offcanvas/editar/?uuid=${id}`,
            renderDetalle: (id) => `${API_ROOT}render-offcanvas/detalle/?uuid=${id}`,
            renderResolucion: (id) => id ? `${API_ROOT}render-offcanvas/resolucion/?id=${id}` : `${API_ROOT}render-offcanvas/resolucion/`
        },

        /**
         * Acciones asincronas
         */
        anular: async function(uuid, motivo = "Anulacion administrativa") {
            const url = this.gastos.anular(uuid);
            const response = await fetch(url, {
                method: 'POST',
                headers: window.Sintel.Gastos.getHeaders(),
                body: JSON.stringify({ motivo: motivo })
            });
            if (!response.ok) {
                try { response.data = await response.json(); } catch(e) {}
                throw response;
            }
            return await response.json();
        },

        eliminar: async function(uuid) {
            const url = this.gastos.detail(uuid);
            const response = await fetch(url, {
                method: 'DELETE',
                headers: window.Sintel.Gastos.getHeaders()
            });
            if (!response.ok) {
                try { response.data = await response.json(); } catch(e) {}
                throw response;
            }
            return response.status === 204 ? {success: true} : await response.json();
        }
    };

    /**
     * Headers por defecto con JWT (v2.62)
     */
    function getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
        };
        
        // window.jwtAuth expuesto globalmente en jwt-auth.js
        const token = window.jwtAuth?.getAccessToken?.();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    // Exportar
    window.Sintel.Gastos.API = API;
    window.Sintel.Gastos.getHeaders = getHeaders;

})();
