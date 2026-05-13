  /**
   * facturas.api.js - Wrapper de API Facturas v2.61.2
   * [INFO] Aislamiento Gradual: Capa de Datos - Retorna siempre {ok, status, data}
   * 
   * Consume exclusivamente DRF endpoints:
   * - GET /api/v1/facturas/ (listar con filtros)
   * - GET /api/v1/facturas/{id}/ (detalle)
   * - GET /api/v1/facturas/summary/ (resumen financiero)
   * - POST /api/v1/facturas/upload-ubl/?preview=true|false&async=false (subida XML UBL)
   *   [INFO] v2.61.2: Soporta batch processing con files[] (múltiples archivos)
   *   [INFO] v2.61.2: Si > 10 archivos, delega automáticamente a Celery (retorna 202 con task_id)
   * - GET /api/v1/facturas/{id}/xml/ (ver XML)
   * - DELETE /api/v1/facturas/{id}/ (eliminar factura)
   * - POST /api/v1/facturas/create-from-dto/ (persistir desde DTO, opcional)
   * - GET /api/v1/facturas/ingest/{task_id}/status/ (consultar estado de batch upload)
   * 
   * [INFO] v2.61.2: OPTIMIZACIONES:
   * - Batch processing: upload-ubl soporta files[] (múltiples archivos)
   * - Pre-validación de idempotencia: extrae CUFE/CUDE con regex antes del parsing completo
   * - Delegación automática a Celery: si > 10 archivos, procesa asíncronamente
   * - Silent Success: actualiza FacturaAnexos si XML nuevo es más completo
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
  // [INFO] v2.61.2: Base URL directa para facturas (Gateway Directo)
  const FACTURAS_API_BASE = '/api/v1/facturas';

  /**
   * Lista facturas con filtros
   * ⚠️ v2.61.1: Actualizado para usar Core API facade
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
    
    // ⚠️ v2.61.1: Usar Core API facade
    const url = queryParams.toString() 
      ? `${FACTURAS_API_BASE}/?${queryParams.toString()}`
      : `${FACTURAS_API_BASE}/`;
    
    return await window.http('GET', url);
  }

  /**
   * Obtiene detalle de una factura
   * ⚠️ v2.61.1: Actualizado para usar Core API facade
   * @param {number} id - ID de la factura
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getFactura(id) {
    // ⚠️ v2.61.1: Usar Core API facade
    return await window.http('GET', `${FACTURAS_API_BASE}/${id}/`);
  }

  /**
   * Sube un documento XML al endpoint universal (parse-only)
   * ⚠️ v2.61.2: Actualizado para usar Core API facade de facturas con soporte de batch processing
   * @param {File|FormData|File[]} fileOrFormDataOrFiles - Archivo, FormData o array de archivos
   * @param {boolean} preview - Si true, solo parsea (no persiste)
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   * 
   * ⚠️ v2.61.2: BATCH PROCESSING:
   * - Si se proporciona un array de File, se envía como files[] para batch processing
   * - Si hay > 10 archivos, el servidor delega automáticamente a Celery (retorna 202 con task_id)
   * - Para consultar estado de batch > 10 archivos, use getBatchUploadStatus(task_id)
   */
  async function uploadDocumento(fileOrFormDataOrFiles, preview = true) {
    let formData;
    
    if (fileOrFormDataOrFiles instanceof FormData) {
      formData = fileOrFormDataOrFiles;
    } else if (Array.isArray(fileOrFormDataOrFiles)) {
      // ⚠️ v2.61.2: BATCH PROCESSING - Múltiples archivos
      formData = new FormData();
      fileOrFormDataOrFiles.forEach((file) => {
        if (file instanceof File) {
          formData.append('files[]', file);
        }
      });
    } else if (fileOrFormDataOrFiles instanceof File) {
      formData = new FormData();
      formData.append('file', fileOrFormDataOrFiles);
    } else {
      throw new Error('Debe proporcionar un File, FormData o array de Files');
    }

    // ⚠️ v2.61.2: Usar Core API facade - endpoint upload-ubl de facturas
    // Soporta batch processing: files[] para múltiples archivos
    const url = `${FACTURAS_API_BASE}/upload-ubl/?preview=${preview ? 'true' : 'false'}&async=false`;
    return await window.http('POST', url, formData);
  }

  /**
   * Consulta el estado de una tarea de batch upload
   * ⚠️ v2.61.2: Nueva función para consultar estado de procesamiento asíncrono
   * @param {string} taskId - ID de la tarea Celery retornado por uploadDocumento cuando hay > 10 archivos
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   * 
   * Retorna:
   * - state: PENDING | STARTED | SUCCESS | FAILURE | UNKNOWN
   * - result: resumen con {"creados": X, "duplicados": Y, "errores": Z, "resultados": [...]} si SUCCESS
   */
  async function getBatchUploadStatus(taskId) {
    if (!taskId) {
      throw new Error('taskId es requerido');
    }
    // ⚠️ v2.61.2: Usar Core API facade - endpoint ingest status
    return await window.http('GET', `${FACTURAS_API_BASE}/ingest/${taskId}/status/`);
  }

  /**
   * Obtiene el XML de una factura
   * ⚠️ v2.61.1: Actualizado para usar Core API facade de facturas
   * @param {number} facturaId - ID de la factura
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getDocumentXML(facturaId) {
    // ⚠️ v2.61.1: Usar Core API facade - endpoint xml de facturas
    // El endpoint puede retornar XML directo o JSON con campo xml
    const response = await fetch(`${FACTURAS_API_BASE}/${facturaId}/xml/`, {
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
   * ⚠️ v2.61.1: Actualizado para usar Core API facade
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function getSummary() {
    // ⚠️ v2.61.1: Usar Core API facade
    return await window.http('GET', `${FACTURAS_API_BASE}/summary/`);
  }

  /**
   * Elimina una factura
   * ⚠️ v2.61.1: Actualizado para usar Core API facade
   * @param {number} id - ID de la factura
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function deleteFactura(id) {
    // ⚠️ v2.61.1: Usar Core API facade
    return await window.http('DELETE', `${FACTURAS_API_BASE}/${id}/`);
  }

  /**
   * Elimina una factura (alias de deleteFactura para compatibilidad)
   * ⚠️ v2.61.1: DEPRECATED - Usar deleteFactura() en su lugar
   * @param {number} facturaId - ID de la factura
   * @returns {Promise<{ok: boolean, status: number, data: any}>}
   */
  async function deleteDocument(facturaId) {
    // ⚠️ v2.61.1: Redirigir a deleteFactura
    return await deleteFactura(facturaId);
  }

  /**
   * Crea una factura desde DTO (persistencia en app)
   * ⚠️ v2.61.1: Actualizado para usar Core API facade
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
    
    // ⚠️ v2.61.1: Usar Core API facade
    return await window.http('POST', `${FACTURAS_API_BASE}/create-from-dto/`, payload);
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
      getBatchUploadStatus,  // ⚠️ v2.61.2: Nueva función para consultar estado de batch upload
      getDocumentXML,
      deleteDocument,
      deleteFactura,
      createFacturaFromDTO,
      previewMailbox,  // ⚠️ NUEVO: Pre-visualización de facturas desde correo
      syncMailbox,
      listMailConfigs,
      listMailRuns,
      // [v3.7.0] Buscador de cuentas PUC vinculadas a facturas
      searchCuentas: (search = '') => {
        const url = `/api/v1/contabilidad/cuentas-contables/?search=${encodeURIComponent(search)}&app_origen=facturas&solo_auxiliares=true`;
        return window.http('GET', url);
      },
      // [v3.7.0] Resolver nombre de cuenta por UUID — §18: consumo HTTP, no import Python
      getCuentaByUuid: (uuid = '') => {
        const url = `/api/v1/contabilidad/cuentas-contables/?uuid=${encodeURIComponent(uuid)}&app_origen=facturas`;
        return window.http('GET', url);
      }
    };
  }
})();
