/**
 * libro_diario.api.js — API client para el Libro Diario Contable v3.7.7
 *
 * v3.7.7: Soporta periodo_uuid (primario) o fecha_inicio/fecha_fin (fallback).
 * Dependencias: Sintel.Core.Http (F32.7, core-http.js)
 */
(function (w) {
  'use strict';

  const MOD = '[libro.diario.api]';
  const API_BASE = '/api/v1/contabilidad/libro-diario/';

  const LibroDiarioAPI = {
    /**
     * Obtiene asientos contables del periodo indicado.
     * @param {Object} params
     * @param {string} [params.periodo_uuid]  - UUID del PeriodoContable (prioritario)
     * @param {string} [params.fecha_inicio]  - 'YYYY-MM-DD' (fallback si no hay periodo_uuid)
     * @param {string} [params.fecha_fin]     - 'YYYY-MM-DD'
     * @param {string} [params.estado]        - 'BORRADOR' | 'APROBADO' | 'CERRADO'
     * @param {string} [params.search]        - Texto libre (numero o descripcion)
     * @returns {Promise<Array>} Lista de AsientoContableListSerializer
     */
    list: async function (params) {
      const url = new URL(API_BASE, w.location.origin);
      if (params) {
        if (params.periodo_uuid)  url.searchParams.append('periodo_uuid',  params.periodo_uuid);
        if (params.fecha_inicio)  url.searchParams.append('fecha_inicio',  params.fecha_inicio);
        if (params.fecha_fin)     url.searchParams.append('fecha_fin',     params.fecha_fin);
        if (params.estado)        url.searchParams.append('estado',        params.estado);
        if (params.search)        url.searchParams.append('search',        params.search);
      }

      const response = await w.Sintel.Core.Http.request('GET', url.pathname + url.search);
      if (!response.ok) {
        const msg = response.data?.detail || response.data?.error || `HTTP ${response.status}`;
        const err = new Error(msg);
        err.status = response.status;
        err.data = response.data;
        throw err;
      }
      return response.data;
    }
  };

  if (typeof w !== 'undefined') {
    w.LibroDiarioAPI = Object.freeze(LibroDiarioAPI);
  }
})(window);
