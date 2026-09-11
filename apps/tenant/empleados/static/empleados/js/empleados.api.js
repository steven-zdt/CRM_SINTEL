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
        // Periodos de Nomina
        periodos: {
            list:            '/api/v1/empleados/periodos-nomina/',
            detail:          (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/`,
            crearOffcanvas:  '/api/v1/empleados/periodos-nomina/render-offcanvas/crear/',
            resumen:         (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/resumen/`,
            preliquidar:     (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/preliquidar/`,
            enviarRevision:  (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/enviar-revision/`,
            rechazarRevision:(uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/rechazar-revision/`,
            aprobar:         (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/aprobar/`,
            marcarPagado:    (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/marcar-pagado/`,
            cerrar:          (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/cerrar/`,
            anular:          (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/anular/`,
            bloquear:        (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/bloquear/`,
            desbloquear:     (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/desbloquear/`,
            empleadosPendientes: (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/empleados-pendientes/`,
            empleadosLiquidados: (uuid) => `/api/v1/empleados/periodos-nomina/${uuid}/empleados-liquidados/`,
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

    // F32.6: migrado a Sintel.Core.Http -- ya no reimplementa fetch+CSRF+JWT
    // (violaba el contrato "solo URLs+metodos", F31.3/F32.1). getHeaders()
    // se conserva por compatibilidad hacia atras (exportada publicamente,
    // sin consumidores externos encontrados). request() mantiene su firma
    // y forma de retorno {ok,status,data} identicas -- el unico consumidor
    // real (contrato_list.js:38) llama request(url, {method:'POST'}) sin
    // body, verificado antes de migrar.
    function getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const csrf = window.Sintel?.Core?.Http?.csrf ? window.Sintel.Core.Http.csrf() : null;
        if (csrf) headers['X-CSRFToken'] = csrf;
        const token = window.jwtAuth?.getAccessToken?.();
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    }

    async function request(url, options = {}) {
        return window.Sintel.Core.Http.request(
            options.method || 'GET', url, options.body, { headers: options.headers }
        );
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
