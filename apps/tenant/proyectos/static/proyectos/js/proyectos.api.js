/**
 * proyectos.api.js - v3.3
 * Manejo de peticiones HTTP para el módulo de Proyectos.
 * ⚠️ API-First: Consume DRF REST API (v2.40)
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ Alineado con Service Layer v3.3 (Zero-Coupling)
 */
(function(w) {
  'use strict';

  const API_BASE = '/api/v1/proyectos';
  const MOD = 'proyectos.api';

  if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
    console.error(`[${MOD}] ❌ Sintel.Core.Http no está disponible. Cargar core-http.js primero.`);
    w.proyectosAPI = { error: 'Sintel.Core.Http no está disponible' };
    return;
  }

  function buildUrlWithParams(baseUrl, params = {}) {
    if (!params || Object.keys(params).length === 0) return baseUrl;
    const url = new URL(baseUrl, w.location.origin);
    Object.keys(params).forEach(key => {
      const value = params[key];
      if (value !== null && value !== undefined && value !== '') {
        url.searchParams.append(key, value);
      }
    });
    return url.toString();
  }

  w.proyectosAPI = {
    /** GET /api/v1/proyectos/ */
    list: async (params = {}) => {
      console.log(`[${MOD}] list()`, params);
      const url = buildUrlWithParams(`${API_BASE}/`, params);
      return w.Sintel.Core.Http.request('GET', url);
    },

    /** GET /api/v1/proyectos/{uuid}/ */
    get: async (uuid) => {
      console.log(`[${MOD}] get(${uuid})`);
      if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
      return w.Sintel.Core.Http.request('GET', `${API_BASE}/${uuid}/`);
    },

    /** POST /api/v1/proyectos/ */
    create: async (data) => {
      console.log(`[${MOD}] create()`, data);
      return w.Sintel.Core.Http.request('POST', `${API_BASE}/`, data);
    },

    /** PUT /api/v1/proyectos/{uuid}/ */
    update: async (uuid, data) => {
      console.log(`[${MOD}] update(${uuid})`, data);
      if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
      return w.Sintel.Core.Http.request('PUT', `${API_BASE}/${uuid}/`, data);
    },

    /** POST /api/v1/proyectos/{uuid}/avanzar-fase/ */
    avanzarFase: async (uuid, fase, responsableId = null, responsableNombre = null) => {
      console.log(`[${MOD}] avanzarFase(${uuid}, ${fase})`);
      if (!uuid || !fase) return { ok: false, status: 400, data: { detail: 'UUID y fase requeridos' } };

      const payload = { fase };
      if (responsableId) payload.responsable_id = responsableId;
      if (responsableNombre) payload.responsable_nombre = responsableNombre;

      return w.Sintel.Core.Http.request('POST', `${API_BASE}/${uuid}/avanzar-fase/`, payload);
    },

    /** PATCH /api/v1/proyectos/{uuid}/
     * Dispara el recalculo financiero (P&L) en services.py sin alterar datos reales.
     */
    syncCostos: async (uuid) => {
      console.log(`[${MOD}] syncCostos(${uuid})`);
      if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };

      const result = await w.Sintel.Core.Http.request('GET', `${API_BASE}/${uuid}/`);
      if (!result.ok) {
        console.error(`[${MOD}] syncCostos() fallo al obtener el proyecto:`, result);
        return result;
      }

      const proyecto = result.data;
      return w.Sintel.Core.Http.request('PATCH', `${API_BASE}/${uuid}/`, {
        porcentaje_avance: proyecto.porcentaje_avance || 0
      });
    },

    /** DELETE /api/v1/proyectos/{uuid}/ (Hard Delete manejado en services.py) */
    delete: async (uuid) => {
      console.log(`[${MOD}] delete(${uuid})`);
      if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
      return w.Sintel.Core.Http.request('DELETE', `${API_BASE}/${uuid}/`);
    },

    /** GET /api/v1/inventario/movimientos/?search=<q>
     *  Busqueda de movimientos Kardex para autocomplete (Pull Model v3.8+).
     */
    searchMovimientos: (q) => buildUrlWithParams('/api/v1/inventario/movimientos/', { search: q, page_size: 10 }),

    /** GET /api/v1/facturas/lista-centro-costos/
     *  Vínculo cross-app para centros de costos.
     */
    fetchCentrosCostos: async () => {
      console.log(`[${MOD}] fetchCentrosCostos()`);
      return w.Sintel.Core.Http.request('GET', '/api/v1/facturas/lista-centro-costos/');
    },

    /** Presupuesto Planeado (v3.5.2) */
    presupuesto: {
      /** GET /api/v1/proyectos/items-presupuesto/?proyecto_uuid=<uuid> */
      list: async (proyectoUuid) => {
        console.log(`[${MOD}] presupuesto.list(${proyectoUuid})`);
        if (!proyectoUuid) return { ok: false, status: 400, data: { detail: 'proyecto_uuid requerido' } };
        const url = buildUrlWithParams(`${API_BASE}/items-presupuesto/`, { proyecto_uuid: proyectoUuid });
        return w.Sintel.Core.Http.request('GET', url);
      },

      /** POST /api/v1/proyectos/items-presupuesto/ */
      create: async (data) => {
        console.log(`[${MOD}] presupuesto.create()`, data);
        return w.Sintel.Core.Http.request('POST', `${API_BASE}/items-presupuesto/`, data);
      },

      /** DELETE /api/v1/proyectos/items-presupuesto/<id>/ */
      delete: async (itemId) => {
        console.log(`[${MOD}] presupuesto.delete(${itemId})`);
        if (!itemId) return { ok: false, status: 400, data: { detail: 'Item ID requerido' } };
        return w.Sintel.Core.Http.request('DELETE', `${API_BASE}/items-presupuesto/${itemId}/`);
      }
    },

    tareasDiarias: {
      /** GET /api/v1/proyectos/tareas-diarias/?proyecto_uuid=<uuid> */
      list: async (proyectoUuid, fechaInicio, fechaFin) => {
        console.log(`[${MOD}] tareasDiarias.list(${proyectoUuid})`);
        const params = { proyecto_uuid: proyectoUuid };
        if (fechaInicio) params.fecha_inicio = fechaInicio;
        if (fechaFin) params.fecha_fin = fechaFin;
        const url = buildUrlWithParams(`${API_BASE}/tareas-diarias/`, params);
        return w.Sintel.Core.Http.request('GET', url);
      },

      /** POST /api/v1/proyectos/tareas-diarias/ */
      create: async (data) => {
        console.log(`[${MOD}] tareasDiarias.create()`, data);
        return w.Sintel.Core.Http.request('POST', `${API_BASE}/tareas-diarias/`, data);
      },

      /** POST /api/v1/proyectos/tareas-diarias/<id>/cambiar-estado/ */
      cambiarEstado: async (tareaId, nuevoEstado) => {
        console.log(`[${MOD}] tareasDiarias.cambiarEstado(${tareaId}, ${nuevoEstado})`);
        if (!tareaId || !nuevoEstado) return { ok: false, status: 400, data: { detail: 'Tarea ID y nuevo estado requeridos' } };
        return w.Sintel.Core.Http.request('POST', `${API_BASE}/tareas-diarias/${tareaId}/cambiar-estado/`, { nuevo_estado: nuevoEstado });
      },

      /** DELETE /api/v1/proyectos/tareas-diarias/<id>/ */
      delete: async (tareaId) => {
        console.log(`[${MOD}] tareasDiarias.delete(${tareaId})`);
        if (!tareaId) return { ok: false, status: 400, data: { detail: 'Tarea ID requerido' } };
        return w.Sintel.Core.Http.request('DELETE', `${API_BASE}/tareas-diarias/${tareaId}/`);
      }
    },

    tareasCortas: {
      /** GET /api/v1/proyectos/tareas-cortas/?empleado_uuid=<uuid> */
      list: async (empleadoUuid, params = {}) => {
        console.log(`[${MOD}] tareasCortas.list(${empleadoUuid})`);
        const qp = {};
        if (empleadoUuid) qp.empleado_uuid = empleadoUuid;
        Object.assign(qp, params);
        const url = buildUrlWithParams(`${API_BASE}/tareas-cortas/`, qp);
        return w.Sintel.Core.Http.request('GET', url);
      },

      /** POST /api/v1/proyectos/tareas-cortas/ */
      create: async (data) => {
        console.log(`[${MOD}] tareasCortas.create()`, data);
        return w.Sintel.Core.Http.request('POST', `${API_BASE}/tareas-cortas/`, data);
      },

      /** PATCH /api/v1/proyectos/tareas-cortas/<uuid>/ */
      update: async (uuid, data) => {
        console.log(`[${MOD}] tareasCortas.update(${uuid})`, data);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return w.Sintel.Core.Http.request('PATCH', `${API_BASE}/tareas-cortas/${uuid}/`, data);
      },

      /** POST /api/v1/proyectos/tareas-cortas/<uuid>/cambiar-estado/ */
      cambiarEstado: async (uuid, nuevoEstado) => {
        console.log(`[${MOD}] tareasCortas.cambiarEstado(${uuid}, ${nuevoEstado})`);
        if (!uuid || !nuevoEstado) return { ok: false, status: 400, data: { detail: 'UUID y estado requeridos' } };
        return w.Sintel.Core.Http.request('POST', `${API_BASE}/tareas-cortas/${uuid}/cambiar-estado/`, { nuevo_estado: nuevoEstado });
      },

      /** DELETE /api/v1/proyectos/tareas-cortas/<uuid>/ */
      delete: async (uuid) => {
        console.log(`[${MOD}] tareasCortas.delete(${uuid})`);
        if (!uuid) return { ok: false, status: 400, data: { detail: 'UUID requerido' } };
        return w.Sintel.Core.Http.request('DELETE', `${API_BASE}/tareas-cortas/${uuid}/`);
      }
    },

    lookups: {
      clientes: async (search = '') => {
        const url = buildUrlWithParams('/api/v1/clientes/', {
          search,
          page_size: 500,
          ordering: 'razon_social'
        });
        return w.Sintel.Core.Http.request('GET', url);
      },

      empleados: async (search = '') => {
        const url = buildUrlWithParams('/api/v1/empleados/', {
          search,
          page_size: 500,
          ordering: 'primer_apellido'
        });
        return w.Sintel.Core.Http.request('GET', url);
      }
    },

    formatCurrency: (value) => {
      if (value === null || value === undefined || value === '') return '$ 0,00';
      const num = parseFloat(value);
      if (isNaN(num)) return '$ 0,00';
      return new Intl.NumberFormat('es-CO', {
        style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 2
      }).format(num);
    }
  };

  console.log(`[${MOD}] API inicializada correctamente.`);
})(window);
