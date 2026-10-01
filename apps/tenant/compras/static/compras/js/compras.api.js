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
    const REQUISICIONES_ROOT = `${API_ROOT}requisiciones/`;
    const COTIZACIONES_ROOT = '/api/v1/cotizaciones/';

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
        cotizaciones: {
            list: COTIZACIONES_ROOT,
            // Detalle completo (incluye `items[]` e `iva_porcentaje` a nivel
            // de documento) -- usado para sincronizar el Detalle de Items de
            // "Nueva Requisición de Compra" al vincular una cotización
            // (origen o adicional). Ver requisiciones_editor.js::agregarItemsDesdeCotizacion.
            get: (uuid) => _fetch('GET', `${COTIZACIONES_ROOT}${uuid}/`),
        },
        requisiciones: {
            list: REQUISICIONES_ROOT,
            detail: (uuid) => `${REQUISICIONES_ROOT}${uuid}/`,
            // Detalle completo (incluye `items`) -- usado para sincronizar
            // automaticamente el Detalle de Items de "Nueva Orden de Compra"
            // al vincular una requisicion (compras_list.js::guardarVinculoRequisicion).
            get: (uuid) => _fetch('GET', `${REQUISICIONES_ROOT}${uuid}/`),
            create: (data) => _fetch('POST', REQUISICIONES_ROOT, data),
            update: (uuid, data) => _fetch('PATCH', `${REQUISICIONES_ROOT}${uuid}/`, data),
            eliminar: (uuid) => _fetch('DELETE', `${REQUISICIONES_ROOT}${uuid}/`),
            enviarAprobacion: (uuid) => _fetch('POST', `${REQUISICIONES_ROOT}${uuid}/enviar-aprobacion/`),
            aprobar: (uuid, comentario) => _fetch('POST', `${REQUISICIONES_ROOT}${uuid}/aprobar/`, { comentario: comentario || '' }),
            rechazar: (uuid, motivo) => _fetch('POST', `${REQUISICIONES_ROOT}${uuid}/rechazar/`, { motivo: motivo }),
            cancelar: (uuid, motivo) => _fetch('POST', `${REQUISICIONES_ROOT}${uuid}/cancelar/`, { motivo: motivo || '' }),
            crearOrden: (uuid, orden, items) => _fetch('POST', `${REQUISICIONES_ROOT}${uuid}/crear-orden/`, { orden: orden, items: items }),
            sincronizarTrazabilidad: (uuid) => _fetch('POST', `${REQUISICIONES_ROOT}${uuid}/sincronizar-trazabilidad/`),
            vincularCotizacion: (uuid, cotizacionUuid, opts) => _fetch('POST', `${REQUISICIONES_ROOT}${uuid}/vincular-cotizacion/`, Object.assign({ cotizacion_uuid: cotizacionUuid }, opts || {})),
            // PLAN_NUEVA_REQUISICION_FORMULARIO.md #4/#12: cotizaciones
            // filtradas en BACKEND (excluye las ya vinculadas a CUALQUIER
            // requisicion) -- usado por el widget "Vincular Cotización" en
            // "Nueva Requisición de Compra" (requisiciones_editor.js).
            cotizacionesDisponibles: () => _fetch('GET', `${REQUISICIONES_ROOT}cotizaciones-disponibles/`),
            renderCrear: () => `${REQUISICIONES_ROOT}render-offcanvas/crear/`,
            renderEditar: (uuid) => `${REQUISICIONES_ROOT}render-offcanvas/editar/?uuid=${uuid}`,
            renderDetalle: (uuid) => `${REQUISICIONES_ROOT}render-offcanvas/detalle/?uuid=${uuid}`,
            // Fase 10 de PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md (#32):
            // Requisiciones aptas para consolidar en una Orden de Compra,
            // con saldo real (uuid/numero/cotizacion/proyecto/valor_total/
            // valor_comprometido/saldo/estado) -- reemplaza el uso de
            // requisiciones.list + filtro client-side por estado.
            disponiblesParaOrden: () => _fetch('GET', `${API_ROOT}requisiciones/disponibles-para-orden/`),
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

        // PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS: elimina unicamente el vinculo
        // (nunca la Factura fiscal en si).
        desvincularFactura: function(uuid) {
            return _fetch('POST', `${API_ROOT}${uuid}/desvincular-factura/`);
        },

        // Vincula una Requisicion existente (con saldo disponible) a una
        // Orden de Compra YA CREADA -- complementa la seleccion obligatoria
        // al crear (mismo patron que vincularFactura/desvincularFactura).
        vincularRequisicion: function(uuid, requisicionUuid) {
            return _fetch('POST', `${API_ROOT}${uuid}/vincular-requisicion/`, { requisicion_uuid: requisicionUuid });
        },

        desvincularRequisicion: function(uuid, requisicionUuid) {
            return _fetch('POST', `${API_ROOT}${uuid}/desvincular-requisicion/`, { requisicion_uuid: requisicionUuid });
        },

        // Reutiliza el buscador ya existente de Facturas (FASE 20/21: no se
        // crea un segundo endpoint de busqueda) -- filtra por naturaleza=COMPRA,
        // excluye las que ya estan vinculadas a otra Orden de Compra, y busca
        // solo por numero o proveedor (nombre/NIT) -- nunca por CUFE.
        buscarFacturasCompra: function(q) {
            const url = new URL('/api/v1/facturas/buscar-para-movimiento/', window.location.origin);
            url.searchParams.set('q', q);
            url.searchParams.set('naturaleza', 'COMPRA');
            url.searchParams.set('excluir_vinculadas', 'compra');
            url.searchParams.set('sin_cufe', '1');
            return _fetch('GET', url.toString());
        },
    };

    // Exportar
    window.Sintel.Compras.API = API;

})();
