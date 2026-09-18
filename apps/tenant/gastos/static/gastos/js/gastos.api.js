/**
 * Gastos API - SSoT de URLs y endpoints
 *
 * Namespace: window.Sintel.Gastos.API
 *
 * F32.6: migrado a Sintel.Core.Http -- ya no reimplementa fetch+CSRF+JWT
 * (violaba el contrato "solo URLs+metodos", F31.3/F32.1). El contrato
 * PUBLICO de cada metodo no cambia -- solo el transporte interno,
 * consolidado en _fetch(). Efecto colateral correcto: JWT ahora usa
 * getValidAccessToken() (con refresh) via Core.Http -- antes usaba
 * getAccessToken() a secas (gastos era uno de los 5 de 6 que no
 * refrescaban, F32.1 S5).
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Gastos = window.Sintel.Gastos || {};

    const API_ROOT = '/api/v1/gastos/';
    const RESOLUCION_ROOT = '/api/v1/gastos/resoluciones/';

    async function _fetch(method, url, data) {
        const res = await window.Sintel.Core.Http.request(method, url, data);
        if (!res.ok) {
            const error = new Error(`[Gastos.API] ${method} ${url} -> ${res.status}`);
            error.status = res.status;
            error.data = res.data || { detail: `HTTP ${res.status}` };
            throw error;
        }
        if (res.status === 204) return { success: true };
        return res.data;
    }

    const API = {
        gastos: {
            list: API_ROOT,
            detail: (id) => `${API_ROOT}${id}/`,
            anular: (id) => `${API_ROOT}${id}/anular/`,
            create: (data) => _fetch('POST', API_ROOT, data),
            update: (uuid, data) => _fetch('PATCH', `${API_ROOT}${uuid}/`, data),
        },
        resoluciones: {
            list: RESOLUCION_ROOT,
            detail: (id) => `${RESOLUCION_ROOT}${id}/`,
            create: RESOLUCION_ROOT,
            update: (uuid) => `${RESOLUCION_ROOT}${uuid}/`,
            activa: `${RESOLUCION_ROOT}activa/`
        },
        contabilidad: {
            searchCuentas: (q) => `/api/v1/contabilidad/cuentas-contables/?search=${encodeURIComponent(q)}&app_origen=gastos&activa=true&tipo=GASTO`,
            getCuentaByUuid: (uuid) => `/api/v1/contabilidad/cuentas-contables/?uuid=${encodeURIComponent(uuid)}&app_origen=gastos`,
            obtenerRetenciones: async function(nit) {
                // Comportamiento original preservado: retorna null en fallo,
                // no lanza (a diferencia del resto de metodos de este API).
                const res = await window.Sintel.Core.Http.get(
                    `/api/v1/contabilidad/retenciones/obtener-por-tercero/?nit=${encodeURIComponent(nit)}&tipo_tercero=PROVEEDOR&naturaleza=COMPRA`
                );
                return res.ok ? res.data : null;
            }
        },
        proveedores: {
            list: '/api/v1/proveedores/'
        },
        inventario: {
            searchMovimientos: (q) => `/api/v1/inventario/movimientos/?search=${encodeURIComponent(q)}&page_size=10`,
        },
        proyectos: {
            // GASTOS_PROYECTOS_01: reutiliza el listado de Proyectos ya existente
            // (?search=) -- no se crea un endpoint nuevo.
            search: (q) => `/api/v1/proyectos/?search=${encodeURIComponent(q)}&page_size=10`,
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
        anular: function(uuid, motivo = "Anulacion administrativa") {
            return _fetch('POST', this.gastos.anular(uuid), { motivo: motivo });
        },

        eliminar: function(uuid) {
            return _fetch('DELETE', this.gastos.detail(uuid));
        }
    };

    // getHeaders() se conserva por compatibilidad hacia atras (F32.6,
    // mismo criterio que ventas.api.js/compras.api.js).
    function getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const csrf = window.Sintel?.Core?.Http?.csrf ? window.Sintel.Core.Http.csrf() : null;
        if (csrf) headers['X-CSRFToken'] = csrf;
        const token = window.jwtAuth?.getAccessToken?.();
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    }

    // Exportar
    window.Sintel.Gastos.API = API;
    window.Sintel.Gastos.getHeaders = getHeaders;

})();
