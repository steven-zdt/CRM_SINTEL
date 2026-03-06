/**
 * facturas.api.js - Wrapper de API Facturas v2.60
 * ⚠️ Aislamiento Gradual: Capa de Datos - Retorna siempre {ok, status, data}
 * 
 * Consume exclusivamente DRF endpoints:
 * - GET /api/v1/facturas/ (listar con filtros)
 * - GET /api/v1/facturas/{id}/ (detalle)
 * - GET /api/v1/facturas/summary/ (resumen financiero)
 * - POST /api/v1/core/documentos/upload/?preview=true|false (subida universal, parse-only)
 * - GET /api/v1/core/documentos/{id}/xml/ (ver XML)
 * - DELETE /api/v1/core/documentos/{id}/ (eliminar)
 * - DELETE /api/v1/facturas/{id}/ (eliminar factura)
 * - POST /api/v1/facturas/create-from-dto/ (persistir desde DTO, opcional)
 */

(function() {
  'use strict';

  // Asegurar que http() esté disponible
  if (typeof window.http !== 'function') {
    console.error('[facturas.api] http() no está disponible. Cargar lib/http.js primero.');
    return;
  }

  const API_BASE = '/api/v1';
  const CORE_API_BASE = '/api/v1/core';

  /**
   * Lista facturas con filtros
   * @param {Object} params - Parámetros de filtro
   * @param {string} [params.naturaleza] - VENTA o COMPRA
   * @param {string} [params.nit] - NIT de emisor o receptor
   * @param {string} [params.fecha_emision__date__gte] - Fecha desde (YYYY-MM-DD)
   * @param {string} [params.fecha_emision__date__lte] - Fecha hasta (YYYY-MM-DD)
   * @param {string} [params.search] - Búsqueda general
   * @param {string} [params.ordering] - Ordenamiento
   * @param {number} [params.page] - Página (si hay paginación)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function listFacturas(params = {}) {
    const queryParams = new URLSearchParams();
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        queryParams.append(key, params[key]);
      }
    });
    
    const url = queryParams.toString() 
      ? `${API_BASE}/facturas/?${queryParams.toString()}`
      : `${API_BASE}/facturas/`;
    
    return await window.http('GET', url);
  }

  /**
   * Obtiene detalle de una factura
   * @param {number} id - ID de la factura
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getFactura(id) {
    return await window.http('GET', `${API_BASE}/facturas/${id}/`);
  }

  /**
   * Sube un documento XML al endpoint universal (parse-only)
   * @param {File|FormData} fileOrFormData - Archivo o FormData con el archivo
   * @param {boolean} preview - Si true, solo parsea (no persiste)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function uploadDocumento(fileOrFormData, preview = true) {
    let formData;
    
    if (fileOrFormData instanceof FormData) {
      formData = fileOrFormData;
    } else if (fileOrFormData instanceof File) {
      formData = new FormData();
      formData.append('file', fileOrFormData);
    } else {
      throw new Error('Debe proporcionar un File o FormData');
    }

    const url = `${CORE_API_BASE}/documentos/upload/?preview=${preview ? 'true' : 'false'}`;
    return await window.http('POST', url, formData);
  }

  /**
   * Obtiene el XML de un documento
   * @param {number} documentId - ID del documento
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getDocumentXML(documentId) {
    // ⚠️ v2.60: Usar http() helper para consistencia
    // El endpoint puede retornar XML directo o JSON con campo xml
    const response = await fetch(`${CORE_API_BASE}/documentos/${documentId}/xml/`, {
      method: 'GET',
      headers: {
        'Accept': 'application/xml, application/json, text/xml',
        'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') || '' : '',
      },
      credentials: 'same-origin',
    });

    const contentType = response.headers.get('content-type') || '';
    let data = null;
    
    if (contentType.includes('application/xml') || contentType.includes('text/xml')) {
      const text = await response.text();
      return { ok: response.ok, status: response.status, data: { xml: text } };
    } else {
      const text = await response.text();
      // ⚠️ v2.60: Simplificar try/catch
      try {
        data = JSON.parse(text);
      } catch {
        data = { xml: text };
      }
    }

    return { ok: response.ok, status: response.status, data };
  }

  /**
   * Obtiene resumen financiero (ventas/compras)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getSummary() {
    return await window.http('GET', `${API_BASE}/facturas/summary/`);
  }

  /**
   * Elimina una factura
   * @param {number} id - ID de la factura
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function deleteFactura(id) {
    return await window.http('DELETE', `${API_BASE}/facturas/${id}/`);
  }

  /**
   * Elimina un documento
   * @param {number} documentId - ID del documento
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function deleteDocument(documentId) {
    return await window.http('DELETE', `${CORE_API_BASE}/documentos/${documentId}/`);
  }

  /**
   * Crea una factura desde DTO (persistencia en app)
   * ⚠️ v2.60: Soporta file_bytes y file_type para anexos (XML/PDF)
   * @param {Object} dto - DTO del documento parseado
   * @param {boolean} persistAnexos - Si true, persiste anexos también
   * @param {string} [fileBytesB64] - Archivo codificado en base64 (opcional)
   * @param {string} [fileType] - Tipo de archivo ('xml' o 'pdf', default: 'xml')
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function createFacturaFromDTO(dto, persistAnexos = true, fileBytesB64 = null, fileType = 'xml') {
    const payload = {
      dto: dto,
      persist_anexos: persistAnexos,
    };
    
    // ⚠️ v2.60: Incluir file_bytes y file_type si están disponibles
    if (fileBytesB64) {
      payload.file_content_bytes = fileBytesB64;
      payload.file_type = fileType;
    }
    
    return await window.http('POST', `${API_BASE}/facturas/create-from-dto/`, payload);
  }

  /**
   * Pre-visualiza facturas desde buzón de correo sin persistirlas (solo metadatos)
   * ⚠️ PRE-VISUALIZACIÓN: Extrae metadatos pero NO persiste las facturas
   * @param {number} configId - ID de la configuración de buzón
   * @param {number} limitMessages - Límite de mensajes a procesar (default: 50)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function previewMailbox(configId, limitMessages = 50) {
    return await window.http('POST', `${API_BASE}/facturas/ingesta-correo/preview/`, {
      config_id: configId,
      limit_messages: limitMessages,
    });
  }

  /**
   * Sincroniza facturas desde buzón de correo
   * @param {number} configId - ID de la configuración de buzón
   * @param {number} limitMessages - Límite de mensajes a procesar (default: 50)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function syncMailbox(configId, limitMessages = 50) {
    return await window.http('POST', `${CORE_API_BASE}/maildigester/run/`, {
      config_id: configId,
      limit_messages: limitMessages,
    });
  }

  /**
   * Lista configuraciones activas de buzones de correo
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function listMailConfigs() {
    return await window.http('GET', `${CORE_API_BASE}/maildigester/configs/`);
  }

  /**
   * Lista ejecuciones recientes de sincronización de correo
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function listMailRuns() {
    return await window.http('GET', `${CORE_API_BASE}/maildigester/runs/`);
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.facturasAPI = {
      listFacturas,
      getFactura,
      getSummary,
      uploadDocumento,
      getDocumentXML,
      deleteDocument,
      deleteFactura,
      createFacturaFromDTO,
      previewMailbox,  // ⚠️ NUEVO: Pre-visualización de facturas desde correo
      syncMailbox,
      listMailConfigs,
      listMailRuns,
    };
  }
})();
