/**
 * facturas.api.js - Core API Facade del modulo Facturas
 * SINTEL v2.61.5 - JS-SINTEL Standard
 *
 * Unico lugar que conoce las URLs del backend.
 * Toda URL apunta al Core API Facade (regla ARCH-2).
 * Retorna siempre { ok, status, data }.
 *
 * Exporta: window.Sintel.Facturas.api
 * Dependencias: window.http (lib/http.js)
 */

(function (w) {
    'use strict';

    var MOD = '[facturas.api]';

    if (typeof w.http !== 'function') {
        console.error(MOD + ' window.http() no disponible. Cargar lib/http.js primero.');
        return;
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Factura = w.Sintel.Factura || {};

    // -- Gateway Directo (regla ARCH-2: todo por /api/v1/facturas/) --
    var CORE_FACTURAS = '/api/v1/facturas';
    var CORE_MAIL     = '/api/v1/facturas/ingesta-correo';

    /**
     * Lista facturas con filtros opcionales.
     * @param {Object} [params] - Pares clave/valor para query string
     * @returns {Promise<{ok, status, data}>}
     */
    async function listar(params) {
        var qs = new URLSearchParams();
        if (params) {
            Object.keys(params).forEach(function (k) {
                if (params[k] !== null && params[k] !== undefined && params[k] !== '') {
                    qs.append(k, params[k]);
                }
            });
        }
        var url = CORE_FACTURAS + '/' + (qs.toString() ? '?' + qs.toString() : '');
        return await w.http('GET', url);
    }

    /**
     * Obtiene el detalle de una factura por ID.
     * @param {number} id
     * @returns {Promise<{ok, status, data}>}
     */
    async function obtener(id) {
        return await w.http('GET', CORE_FACTURAS + '/' + id + '/');
    }

    /**
     * Crea una nueva factura con el payload indicado.
     * @param {Object} payload
     * @returns {Promise<{ok, status, data}>}
     */
    async function crear(payload) {
        return await w.http('POST', CORE_FACTURAS + '/', payload);
    }

    /**
     * Actualiza una factura existente.
     * @param {number} id
     * @param {Object} payload
     * @returns {Promise<{ok, status, data}>}
     */
    async function actualizar(id, payload) {
        return await w.http('PATCH', CORE_FACTURAS + '/' + id + '/', payload);
    }

    /**
     * Elimina una factura por ID.
     * @param {number} id
     * @returns {Promise<{ok, status, data}>}
     */
    async function eliminar(id) {
        return await w.http('DELETE', CORE_FACTURAS + '/' + id + '/');
    }

    /**
     * Obtiene el XML crudo de una factura.
     * @param {number} id
     * @returns {Promise<{ok, status, data}>}
     */
    async function obtenerXML(id) {
        var response = await fetch(CORE_FACTURAS + '/' + id + '/xml/', {
            method: 'GET',
            headers: {
                'Accept': 'application/xml, application/json, text/xml',
                'X-CSRFToken': w.getCookie ? w.getCookie('csrftoken') || '' : ''
            },
            credentials: 'same-origin'
        });
        var contentType = response.headers.get('content-type') || '';
        var data = null;
        if (contentType.includes('application/xml') || contentType.includes('text/xml')) {
            var text = await response.text();
            data = { xml: text };
        } else {
            var text = await response.text();
            try { data = JSON.parse(text); } catch (e) { data = { xml: text }; }
        }
        return { ok: response.ok, status: response.status, data: data };
    }

    /**
     * Obtiene el resumen financiero (ventas netas y compras netas).
     * El backend retorna { ventas: {total_neto, subtotal_neto, impuestos_neto}, compras: {...} }.
     * Se normaliza aqui para que main.js consuma campos planos.
     * @returns {Promise<{ok, status, data}>}
     */
    async function obtenerResumen() {
        var res = await w.http('GET', CORE_FACTURAS + '/summary/');
        if (!res.ok || !res.data) return res;
        var v = res.data.ventas  || {};
        var c = res.data.compras || {};
        res.data = {
            ventas_total:      parseFloat(v.total_neto    || 0),
            ventas_subtotal:   parseFloat(v.subtotal_neto || 0),
            ventas_impuestos:  parseFloat(v.impuestos_neto || 0),
            compras_total:     parseFloat(c.total_neto    || 0),
            compras_subtotal:  parseFloat(c.subtotal_neto || 0),
            compras_impuestos: parseFloat(c.impuestos_neto || 0)
        };
        return res;
    }

    /**
     * Sube uno o varios documentos XML/PDF al endpoint de ingesta.
     * Correccion: el forEach roto fue reemplazado por for...of con async/await correcto.
     *
     * @param {File|File[]|FormData} archivos - Archivo unico, array o FormData ya construido
     * @param {boolean} [preview=true] - Si true, solo parsea sin persistir
     * @returns {Promise<{ok, status, data}>}
     */
    async function subirDocumento(archivos, preview) {
        if (preview === undefined) preview = true;

        var formData;
        if (archivos instanceof FormData) {
            formData = archivos;
        } else if (Array.isArray(archivos)) {
            formData = new FormData();
            for (var i = 0; i < archivos.length; i++) {
                if (archivos[i] instanceof File) {
                    formData.append('files[]', archivos[i]);
                }
            }
        } else if (archivos instanceof File) {
            formData = new FormData();
            formData.append('file', archivos);
        } else {
            console.error(MOD + ':subirDocumento argumento invalido');
            return { ok: false, status: 400, data: { detail: 'Argumento invalido: se esperaba File, File[] o FormData' } };
        }

        var url = CORE_FACTURAS + '/upload-ubl/?preview=' + (preview ? 'true' : 'false') + '&async=false';
        return await w.http('POST', url, formData);
    }

    /**
     * Consulta el estado de una tarea de batch upload (Celery).
     * @param {string} taskId
     * @returns {Promise<{ok, status, data}>}
     */
    async function estadoBatchUpload(taskId) {
        if (!taskId) {
            console.error(MOD + ':estadoBatchUpload taskId requerido');
            return { ok: false, status: 400, data: { detail: 'taskId requerido' } };
        }
        return await w.http('GET', CORE_FACTURAS + '/ingest/' + taskId + '/status/');
    }

    /**
     * Persiste una factura a partir de un DTO parseado.
     * @param {Object} dto
     * @param {boolean} [persistAnexos=true]
     * @param {string|null} [fileBytesB64]
     * @param {string} [fileType='xml']
     * @returns {Promise<{ok, status, data}>}
     */
    async function crearDesdeDTO(dto, persistAnexos, fileBytesB64, fileType) {
        persistAnexos = persistAnexos !== false;
        fileType = fileType || 'xml';
        var payload = { dto: dto, persist_anexos: persistAnexos };
        if (fileBytesB64) {
            payload.file_content_bytes = fileBytesB64;
            payload.file_type = fileType;
        }
        return await w.http('POST', CORE_FACTURAS + '/create-from-dto/', payload);
    }

    /**
     * Actualiza el estado del buzon de correo tras procesar mensajes.
     * @param {number} configId
     * @param {number} lastUid
     * @param {number} messagesProcessed
     * @returns {Promise<{ok, status, data}>}
     */
    async function actualizarEstadoBuzon(configId, lastUid, messagesProcessed) {
        return await w.http('POST', CORE_FACTURAS + '/update-inbox-state/', {
            config_id: configId,
            last_uid: lastUid,
            messages_processed: messagesProcessed
        });
    }

    /**
     * Pre-visualiza facturas del buzon sin persistirlas.
     * @param {number} configId
     * @param {number} [limit=50]
     * @returns {Promise<{ok, status, data}>}
     */
    async function previewBuzon(configId, limit) {
        limit = limit || 50;
        return await w.http('POST', CORE_MAIL + '/preview/', {
            config_id: configId,
            limit_messages: limit
        });
    }

    /**
     * Lista configuraciones activas de buzones de correo.
     * @returns {Promise<{ok, status, data}>}
     */
    async function listarConfigsBuzon() {
        return await w.http('GET', CORE_MAIL + '/configs/');
    }

    /**
     * Lista ejecuciones recientes de sincronizacion de correo.
     * @returns {Promise<{ok, status, data}>}
     */
    async function listarEjecucionesBuzon() {
        return await w.http('GET', CORE_MAIL + '/runs/');
    }

    // -- Exportar --
    w.Sintel.Factura.api = {
        listar: listar,
        obtener: obtener,
        crear: crear,
        actualizar: actualizar,
        eliminar: eliminar,
        obtenerXML: obtenerXML,
        obtenerResumen: obtenerResumen,
        subirDocumento: subirDocumento,
        estadoBatchUpload: estadoBatchUpload,
        crearDesdeDTO: crearDesdeDTO,
        actualizarEstadoBuzon: actualizarEstadoBuzon,
        previewBuzon: previewBuzon,
        listarConfigsBuzon: listarConfigsBuzon,
        listarEjecucionesBuzon: listarEjecucionesBuzon,
        // Constante expuesta para uso de modulos internos
        CORE_FACTURAS: CORE_FACTURAS
    };

    // Alias de compatibilidad con codigo heredado
    w.facturasAPI = {
        listFacturas: listar,
        getFactura: obtener,
        createFactura: crear,
        updateFactura: actualizar,
        deleteFactura: eliminar,
        deleteDocument: eliminar,
        getDocumentXML: obtenerXML,
        getSummary: obtenerResumen,
        uploadDocumento: subirDocumento,
        getBatchUploadStatus: estadoBatchUpload,
        createFacturaFromDTO: crearDesdeDTO,
        previewMailbox: previewBuzon,
        listMailConfigs: listarConfigsBuzon,
        listMailRuns: listarEjecucionesBuzon
    };

})(window);
