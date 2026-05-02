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

  if (typeof w.http !== 'function') {
    console.error(`[${MOD}] ❌ window.http no está disponible. Cargar lib/http.js primero.`);
    w.proyectosAPI = { error: 'window.http no está disponible' };
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
      return w.http('GET', url);
    },

    /** GET /api/v1/proyectos/{id}/ */
    get: async (id) => {
      console.log(`[${MOD}] get(${id})`);
      if (!id) return { ok: false, status: 400, data: { detail: 'ID requerido' } };
      return w.http('GET', `${API_BASE}/${id}/`);
    },

    /** POST /api/v1/proyectos/ */
    create: async (data) => {
      console.log(`[${MOD}] create()`, data);
      return w.http('POST', `${API_BASE}/`, data);
    },

    /** PUT /api/v1/proyectos/{id}/ */
    update: async (id, data) => {
      console.log(`[${MOD}] update(${id})`, data);
      if (!id) return { ok: false, status: 400, data: { detail: 'ID requerido' } };
      return w.http('PUT', `${API_BASE}/${id}/`, data);
    },

    /** POST /api/v1/proyectos/{id}/avanzar-fase/ */
    avanzarFase: async (id, fase, responsableId = null, responsableNombre = null) => {
      console.log(`[${MOD}] avanzarFase(${id}, ${fase})`);
      if (!id || !fase) return { ok: false, status: 400, data: { detail: 'ID y fase requeridos' } };
      
      const payload = { fase };
      if (responsableId) payload.responsable_id = responsableId;
      if (responsableNombre) payload.responsable_nombre = responsableNombre;
      
      return w.http('POST', `${API_BASE}/${id}/avanzar-fase/`, payload);
    },

    /** PATCH /api/v1/proyectos/{id}/ 
     * ⚠️ Dispara el recálculo financiero (P&L) en services.py sin alterar datos reales
     */
    syncCostos: async (id) => {
      console.log(`[${MOD}] syncCostos(${id})`);
      if (!id) return { ok: false, status: 400, data: { detail: 'ID requerido' } };
      
      const result = await w.http('GET', `${API_BASE}/${id}/`);
      if (!result.ok) {
        console.error(`[${MOD}] syncCostos() falló al obtener el proyecto:`, result);
        return result;
      }

      const proyecto = result.data;
      return w.http('PATCH', `${API_BASE}/${id}/`, { 
        porcentaje_avance: proyecto.porcentaje_avance || 0
      });
    },

    /** DELETE /api/v1/proyectos/{id}/ (Hard Delete manejado en services.py) */
    delete: async (id) => {
      console.log(`[${MOD}] delete(${id})`);
      if (!id) return { ok: false, status: 400, data: { detail: 'ID requerido' } };
      return w.http('DELETE', `${API_BASE}/${id}/`);
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

  console.log(`[${MOD}] ✅ API inicializada correctamente.`);
})(window);