/**
 * Compras API - SSoT de URLs y endpoints
 * 
 * Namespace: window.Sintel.Compras.API
 */
(function() {
    'use strict';

    // Namespace
    window.Sintel = window.Sintel || {};
    window.Sintel.Compras = window.Sintel.Compras || {};

    const API_ROOT = '/api/v1/compras/';
    const PLANTILLAS_ROOT = `${API_ROOT}plantillas/`;

    /**
     * API Endpoints para Compras (Gateway Directo)
     */
    const API = {
        compras: {
            list: API_ROOT,
            detail: (id) => `${API_ROOT}${id}/`,
            cambiarEstado: (id) => `${API_ROOT}${id}/cambiar-estado/`,
            create: async function(data) {
                const response = await fetch(API_ROOT, {
                    method: 'POST',
                    headers: await window.Sintel.Compras.getHeaders(),
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    let errorData = {};
                    try {
                        errorData = await response.json();
                    } catch(e) {
                        errorData = { detail: `HTTP ${response.status}` };
                    }
                    const error = new Error('Orden de compra creation failed');
                    error.status = response.status;
                    error.data = errorData;
                    console.error('[API] OrdenCompra create error:', errorData);
                    throw error;
                }
                return await response.json();
            },
            update: async function(uuid, data) {
                const response = await fetch(`${API_ROOT}${uuid}/`, {
                    method: 'PATCH',
                    headers: await window.Sintel.Compras.getHeaders(),
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    let errorData = {};
                    try {
                        errorData = await response.json();
                    } catch(e) {
                        errorData = { detail: `HTTP ${response.status}` };
                    }
                    const error = new Error('Orden de compra update failed');
                    error.status = response.status;
                    error.data = errorData;
                    console.error('[API] OrdenCompra update error:', errorData);
                    throw error;
                }
                return await response.json();
            },
        },
        plantillas: {
            list: PLANTILLAS_ROOT,
            detail: (uuid) => `${PLANTILLAS_ROOT}${uuid}/`,
            renderCrear: () => `${PLANTILLAS_ROOT}render-offcanvas/crear/`,
            create: async function(data) {
                const response = await fetch(PLANTILLAS_ROOT, {
                    method: 'POST',
                    headers: await window.Sintel.Compras.getHeaders(),
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    let errorData = {};
                    try { errorData = await response.json(); } catch(e) { errorData = { detail: `HTTP ${response.status}` }; }
                    const error = new Error('Plantilla creation failed');
                    error.status = response.status;
                    error.data = errorData;
                    throw error;
                }
                return await response.json();
            },
        },
        proveedores: {
            list: '/api/v1/proveedores/'
        },
        proyectos: {
            list: '/api/v1/proyectos/'
        },

        // Renderizado (HTMX / Views) - Ordenes
        endpoints: {
            renderCrear: () => `${API_ROOT}render-offcanvas/crear/`,
            renderEditar: (id) => `${API_ROOT}render-offcanvas/editar/?uuid=${id}`,
            renderDetalle: (id) => `${API_ROOT}render-offcanvas/detalle/?uuid=${id}`
        },

        /**
         * Acciones asincronas
         */
        cambiarEstado: async function(uuid, estado) {
            const url = this.compras.cambiarEstado(uuid);
            const response = await fetch(url, {
                method: 'POST',
                headers: await window.Sintel.Compras.getHeaders(),
                body: JSON.stringify({ estado: estado })
            });
            if (!response.ok) {
                try { response.data = await response.json(); } catch(e) {}
                throw response;
            }
            return await response.json();
        },

        eliminar: async function(uuid) {
            const url = this.compras.detail(uuid);
            const response = await fetch(url, {
                method: 'DELETE',
                headers: await window.Sintel.Compras.getHeaders()
            });
            if (!response.ok) {
                try { response.data = await response.json(); } catch(e) {}
                throw response;
            }
            return response.status === 204 ? {success: true} : await response.json();
        }
    };

    /**
     * Headers por defecto con JWT
     * FE-A9: CSRF via window.getCookie (SSoT, core/js/lib/http.js) — no
     * depende de un input de formulario tradicional que puede no existir
     * en paginas API-first.
     */
    async function getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.getCookie?.('csrftoken') || ''
        };
        
        try {
            if (window.jwtAuth && typeof window.jwtAuth.getValidAccessToken === 'function') {
                const token = await window.jwtAuth.getValidAccessToken();
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                }
            } else {
                const token = window.jwtAuth?.getAccessToken?.();
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                }
            }
        } catch (err) {
            console.warn('[Compras.API] Error al obtener JWT token:', err);
        }
        return headers;
    }

    // Exportar
    window.Sintel.Compras.API = API;
    window.Sintel.Compras.getHeaders = getHeaders;

})();
