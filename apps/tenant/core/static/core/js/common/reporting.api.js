/**
 * reporting.api.js — Report API Client unico del Reporting Hub.
 * Namespace: window.Sintel.Reporting.API
 *
 * SSoT de URLs y llamadas HTTP para /api/v1/reporting/. Vive en core/js/common/
 * (no en un app.api.js por app) a proposito: el contrato es el mismo para
 * cualquier dataset de cualquier dominio (Regla Absoluta #1/#3 de la mision
 * "Reporting Hub Frontend" -- no crear ventasReportAPI.js/facturasReportAPI.js
 * cuando todos usan el mismo contrato).
 *
 * Requiere Sintel.Core.Http (core-http.js) cargado antes -- mismo requisito
 * que ventas.api.js/facturas.api.js.
 */
(function (w) {
    'use strict';

    if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
        console.error('[Reporting.API] Sintel.Core.Http no esta cargado. Revisar orden de <script> en assets_core.html.');
        return;
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Reporting = w.Sintel.Reporting || {};

    const API_ROOT = '/api/v1/reporting/';

    async function _fetch(method, url, data) {
        var res = await w.Sintel.Core.Http.request(method, url, data === null ? undefined : data);
        if (!res.ok) {
            var ex = new Error('[Reporting.API] ' + method + ' ' + url + ' -> ' + res.status);
            ex.status = res.status;
            ex.data = res.data || { detail: 'HTTP ' + res.status };
            throw ex;
        }
        return res.data;
    }

    function _buildQueryString(params) {
        var query = {};
        if (params.filters) {
            Object.keys(params.filters).forEach(function (k) {
                if (params.filters[k] !== null && params.filters[k] !== undefined) {
                    query['filters[' + k + ']'] = params.filters[k];
                }
            });
        }
        if (params.group_by) query.group_by = params.group_by.join(',');
        if (params.measures) query.measures = params.measures.join(',');
        if (params.order_by) query.order_by = params.order_by;
        if (params.page) query.page = params.page;
        if (params.page_size) query.page_size = params.page_size;
        // WARNING: BUGFIX: NO usar "format" como nombre de query param --
        // DRF lo reserva para su propia negociacion de contenido
        // (URL_FORMAT_OVERRIDE). ?format=csv/xlsx hacia que DRF levantara
        // Http404 ANTES de que la vista se ejecutara (confirmado en vivo).
        if (params.export_format) query.export_format = params.export_format;
        return query;
    }

    var API = {
        /** GET /api/v1/reporting/ -- catalogo completo de datasets */
        catalog: function () {
            return _fetch('GET', API_ROOT);
        },

        /** GET /api/v1/reporting/<dataset_id>/ -- contrato de un dataset */
        detail: function (datasetId) {
            return _fetch('GET', API_ROOT + encodeURIComponent(datasetId) + '/');
        },

        /**
         * POST /api/v1/reporting/query/ -- ejecuta un ReportRequest.
         * params: {dataset_id, filters, group_by, measures, order_by, page, page_size}
         */
        query: function (params) {
            return _fetch('POST', API_ROOT + 'query/', params);
        },

        /**
         * Construye la URL de descarga directa para export (GET, sin JS
         * adicional -- un <a href> normal dispara la descarga del navegador,
         * el propio browser maneja el stream de bytes correctamente).
         *
         * WARNING: deliberadamente NO se ofrece una variante JS que descargue
         * el archivo via fetch()/Sintel.Core.Http -- ese cliente hace
         * res.text() + JSON.parse() en cada respuesta (core-http.js
         * parseBody()), lo que corrompe un binario XLSX. Un <a href> normal
         * es ademas el patron mas simple posible para "descargar archivo".
         *
         * params: {dataset_id, filters, group_by, measures, order_by, export_format}
         */
        exportUrl: function (params) {
            var url = new URL(API_ROOT + 'export/', w.location.origin);
            var query = _buildQueryString(params);
            Object.keys(query).forEach(function (k) { url.searchParams.set(k, query[k]); });
            return url.toString();
        },
    };

    w.Sintel.Reporting.API = API;
})(window);
