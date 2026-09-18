/**
 * Compras API - SSoT de URLs y endpoints
 *
 * Namespace: window.Sintel.Compras.API
 *
 * F32.6: migrado a Sintel.Core.Http -- ya no reimplementa fetch+CSRF+JWT
 * (violaba el contrato "solo URLs+metodos", F31.3/F32.1). El contrato
 * PUBLICO de cada metodo (lanza Error con .status/.data en fallo) no
 * cambia -- solo el transporte interno, unificado en _fetch().
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Compras = window.Sintel.Compras || {};

    const API_ROOT = '/api/v1/compras/';
    const PLANTILLAS_ROOT = `${API_ROOT}plantillas/`;

    async function _fetch(method, url, data) {
        const res = await window.Sintel.Core.Http.request(method, url, data);
        if (!res.ok) {
            const error = new Error(`[Compras.API] ${method} ${url} -> ${res.status}`);
            error.status = res.status;
            error.data = res.data || { detail: `HTTP ${res.status}` };
            throw error;
        }
        if (res.status === 204) return { success: true };
        return res.data;
    }

    const API = {
        compras: {
            list: API_ROOT,
            detail: (id) => `${API_ROOT}${id}/`,
            cambiarEstado: (id) => `${API_ROOT}${id}/cambiar-estado/`,
            create: (data) => _fetch('POST', API_ROOT, data),
            update: (uuid, data) => _fetch('PATCH', `${API_ROOT}${uuid}/`, data),
        },
        plantillas: {
            list: PLANTILLAS_ROOT,
            detail: (uuid) => `${PLANTILLAS_ROOT}${uuid}/`,
            renderCrear: () => `${PLANTILLAS_ROOT}render-offcanvas/crear/`,
            renderEditar: (uuid) => `${PLANTILLAS_ROOT}render-offcanvas/editar/?uuid=${uuid}`,
            create: (data) => _fetch('POST', PLANTILLAS_ROOT, data),
            update: (uuid, data) => _fetch('PATCH', `${PLANTILLAS_ROOT}${uuid}/`, data),
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
        cambiarEstado: function(uuid, estado) {
            return _fetch('POST', this.compras.cambiarEstado(uuid), { estado: estado });
        },

        eliminar: function(uuid) {
            return _fetch('DELETE', this.compras.detail(uuid));
        },

        // FACTURAS-VENTAS-COMPRAS-01: asociacion MANUAL de una Factura ya
        // persistida (naturaleza COMPRA) -- nunca crea/emite una Factura.
        vincularFactura: function(uuid, facturaUuid) {
            return _fetch('POST', `${API_ROOT}${uuid}/vincular-factura/`, { factura_uuid: facturaUuid });
        },

        // Reutiliza el buscador ya existente de Facturas (FASE 20/21: no se
        // crea un segundo endpoint de busqueda) -- filtra por naturaleza=COMPRA.
        buscarFacturasCompra: function(q) {
            const url = new URL('/api/v1/facturas/buscar-para-movimiento/', window.location.origin);
            url.searchParams.set('q', q);
            url.searchParams.set('naturaleza', 'COMPRA');
            return _fetch('GET', url.toString());
        },
    };

    // getHeaders() se conserva por compatibilidad hacia atras -- no se
    // encontro ningun consumidor externo de window.Sintel.Compras.getHeaders,
    // pero se deja el shape identico por si acaso (F32.6, mismo criterio
    // que ventas.api.js).
    async function getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const csrf = window.Sintel?.Core?.Http?.csrf ? window.Sintel.Core.Http.csrf() : null;
        if (csrf) headers['X-CSRFToken'] = csrf;
        try {
            if (window.jwtAuth && typeof window.jwtAuth.getValidAccessToken === 'function') {
                const token = await window.jwtAuth.getValidAccessToken();
                if (token) headers['Authorization'] = `Bearer ${token}`;
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
