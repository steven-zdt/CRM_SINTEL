/**
 * plantilla.api.js - API para PlantillaContable + LineaPlantilla v3.16.2
 * Feature-Sliced Design: encapsula todas las peticiones HTTP al endpoint DRF.
 * Dependencias: w.http (http.js)
 */
(function (w) {
  'use strict';

  const MOD = '[plantilla.api]';
  const BASE = '/api/v1/contabilidad/plantillas-contables/';

  const PlantillaAPI = {

    list: async function (params = {}) {
      const url = new URL(BASE, w.location.origin);
      if (params.page)              url.searchParams.append('page', params.page);
      if (params.page_size)         url.searchParams.append('page_size', params.page_size);
      if (params.search)            url.searchParams.append('search', params.search);
      if (params.tipo_transaccion)  url.searchParams.append('tipo_transaccion', params.tipo_transaccion);
      if (params.activo !== undefined && params.activo !== '') {
        url.searchParams.append('activo', params.activo);
      }
      const res = await w.http('GET', url.pathname + url.search);
      if (!res.ok) throw new Error('Error ' + res.status);
      return res.data;
    },

    retrieve: async function (uuid) {
      const res = await w.http('GET', BASE + uuid + '/');
      if (!res.ok) throw new Error('Error ' + res.status);
      return res.data;
    },

    create: async function (data) {
      const res = await w.http('POST', BASE, data);
      if (!res.ok) throw res;
      return res.data;
    },

    update: async function (uuid, data) {
      const res = await w.http('PATCH', BASE + uuid + '/', data);
      if (!res.ok) throw res;
      return res.data;
    },

    destroy: async function (uuid) {
      const res = await w.http('DELETE', BASE + uuid + '/');
      if (!res.ok) throw new Error('Error ' + res.status);
    },

    agregarLinea: async function (uuid, data) {
      const res = await w.http('POST', BASE + uuid + '/lineas/', data);
      if (!res.ok) throw res;
      return res.data;
    },

    eliminarLinea: async function (uuid, lineaId) {
      const res = await w.http('DELETE', BASE + uuid + '/lineas/' + lineaId + '/');
      if (!res.ok) throw new Error('Error ' + res.status);
    },
  };

  if (typeof w !== 'undefined') {
    w.PlantillaAPI = Object.freeze(PlantillaAPI);
  }
})(window);
