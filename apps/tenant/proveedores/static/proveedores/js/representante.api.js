/**
 * representante.api.js — API Client para Representantes v3.17.2
 * SSoT (Single Source of Truth) para todas las URLs y operaciones CRUD.
 * Namespace: window.Sintel.Representante
 *
 * Contrato: cada metodo resuelve a res.data directamente y lanza Error en 4xx/5xx.
 * Los llamadores usan try/catch — nunca necesitan .ok ni .status.
 */

window.Sintel = window.Sintel || {};
window.Sintel.Representante = window.Sintel.Representante || {};

(function (api) {
  'use strict';

  const w = window;
  const BASE_URL = '/api/v1/proveedores/representantes';

  function _fail(res, fallback) {
    const msg = res.data?.detail || res.data?.error || JSON.stringify(res.data) || fallback;
    throw new Error(msg);
  }

  /**
   * GET /api/v1/proveedores/representantes/?proveedor_uuid={uuid}
   * Lista representantes de un proveedor (o de toda la empresa si no hay uuid).
   * Retorna: { count, results: [...] }
   */
  api.listar = async (proveedorUuid, options = {}) => {
    const params = new URLSearchParams();
    if (proveedorUuid) params.set('proveedor_uuid', proveedorUuid);
    Object.entries(options).forEach(([k, v]) => params.set(k, v));
    const res = await w.http('GET', `${BASE_URL}/?${params.toString()}`);
    if (!res.ok) _fail(res, 'Error listando representantes');
    return res.data;
  };

  /**
   * GET /api/v1/proveedores/representantes/{uuid}/
   * Retorna: { uuid, nombre_completo, tipo_documento, ... }
   */
  api.obtener = async (uuid) => {
    const res = await w.http('GET', `${BASE_URL}/${uuid}/`);
    if (!res.ok) _fail(res, 'Error obteniendo representante');
    return res.data;
  };

  /**
   * POST /api/v1/proveedores/representantes/
   * Crea un nuevo representante.
   * Retorna: objeto Representante creado.
   */
  api.crear = async (data, proveedorUuid) => {
    const payload = { ...data, proveedor_uuid: proveedorUuid };
    const res = await w.http('POST', `${BASE_URL}/`, payload);
    if (!res.ok) _fail(res, 'Error creando representante');
    return res.data;
  };

  /**
   * PATCH /api/v1/proveedores/representantes/{uuid}/
   * Actualiza campos de un representante.
   * Retorna: objeto Representante actualizado.
   */
  api.actualizar = async (uuid, data) => {
    const res = await w.http('PATCH', `${BASE_URL}/${uuid}/`, data);
    if (!res.ok) _fail(res, 'Error actualizando representante');
    return res.data;
  };

  /**
   * DELETE /api/v1/proveedores/representantes/{uuid}/
   * Elimina un representante.
   * Retorna: true si exitoso.
   */
  api.eliminar = async (uuid) => {
    const res = await w.http('DELETE', `${BASE_URL}/${uuid}/`);
    if (!res.ok) _fail(res, 'Error eliminando representante');
    return true;
  };

  api.getTipoDocumentoDisplay = (tipoDoc) => {
    const map = {
      CC:  'Cedula de Ciudadania',
      CE:  'Cedula de Extranjeria',
      PA:  'Pasaporte',
      NIT: 'NIT',
    };
    return map[tipoDoc] || tipoDoc;
  };

})(window.Sintel.Representante);
