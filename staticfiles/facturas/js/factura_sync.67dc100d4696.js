/**
 * facturas.sync.js - Sincronizacion de buzones de correo para facturas
 * SINTEL v2.61.5 - JS-SINTEL Standard
 *
 * Responsabilidades:
 * - Comunicacion con el worker Celery para ingesta de facturas desde correo
 * - Mostrar progreso de sincronizacion (tabla de pendientes)
 * - Procesar facturas individuales o en lote desde el buzon
 * - Emitir 'sintel:facturas:sincronizado' al terminar para que main.js refresque
 *
 * Exporta: window.Sintel.Factura.sync
 * Dependencias: window.Sintel.Factura.utils, window.Sintel.Factura.api,
 *               window.UIManager, window.SintelFeedback
 */

(function (w, d) {
    'use strict';

    var MOD = '[facturas.sync]';

    w.Sintel = w.Sintel || {};
    w.Sintel.Factura = w.Sintel.Factura || {};

    // Estado modular del proceso de sincronizacion
    var _state = {
        active:           false,
        configId:         null,
        pendingInvoices:  [],
        xmlDetected:      0,
        processed:        0,
        errors:           0,
        lastInboxUid:     null,
        pollingTimer:     null
    };

    // ---------------------------------------------------------
    // Seccion: Arranque del proceso de sincronizacion
    // ---------------------------------------------------------

    /**
     * Inicia el proceso de sincronizacion para la configuracion indicada.
     * Llama al endpoint de preview del buzon y muestra la lista de pendientes.
     * @param {number|string} configId - ID de la configuracion de buzon a procesar
     */
    async function sincronizar(configId) {
        if (_state.active) {
            if (w.SintelFeedback) w.SintelFeedback.warning('Ya hay una sincronizacion en curso. Espere.');
            return;
        }

        var utils = w.Sintel.Factura.utils;
        var id    = utils ? utils.validarId(configId) : parseInt(configId, 10);
        if (!id) {
            console.error(MOD + ':sincronizar configId invalido:', configId);
            if (w.SintelFeedback) w.SintelFeedback.error('Configuracion de buzon invalida');
            return;
        }

        _state.active   = true;
        _state.configId = id;
        _state.processed = 0;
        _state.errors    = 0;

        _setLoading(true);

        var api = w.Sintel.Factura.api;
        var res = await api.previewBuzon(id, 50);

        _setLoading(false);

        if (!res.ok) {
            _state.active = false;
            if (w.UIManager) w.UIManager.handleError(res, MOD);
            return;
        }

        var invoices    = (res.data && res.data.results) || (Array.isArray(res.data) ? res.data : []);
        var xmlDetected = (res.data && res.data.xml_detected) || 0;
        var lastUid     = (res.data && res.data.last_uid)     || null;

        _state.pendingInvoices = invoices;
        _state.xmlDetected     = xmlDetected;
        _state.lastInboxUid    = lastUid;

        if (invoices.length === 0) {
            _state.active = false;
            if (w.SintelFeedback) w.SintelFeedback.info('No hay facturas nuevas en el buzon');
            return;
        }

        mostrarListaPendientes(invoices, xmlDetected);
    }

    /**
     * Muestra la tabla de facturas pendientes de sincronizacion en el offcanvas.
     * @param {Array} invoices - Lista de facturas extraidas del buzon
     * @param {number} xmlDetected - Cantidad de archivos XML detectados
     */
    function mostrarListaPendientes(invoices, xmlDetected) {
        var container = d.getElementById('sync-container');
        if (!container) {
            console.warn(MOD + ':mostrarListaPendientes #sync-container no encontrado');
            return;
        }

        var utils = w.Sintel.Factura.utils || {};
        var fmt   = utils.formatearMoneda || function (v) { return v; };

        var alertXml = xmlDetected > 0 ?
            '<div class="alert alert-success alert-sm py-2 mb-3"><i class="bi bi-check-circle me-2"></i>' +
            '<strong>' + xmlDetected + '</strong> documentos XML UBL 2.1 detectados (mayor precision)</div>' : '';

        var thead = '<thead class="table-dark"><tr>' +
            '<th><input type="checkbox" id="check-all-sync" title="Seleccionar todos"></th>' +
            '<th>Remitente</th>' +
            '<th>Numero</th>' +
            '<th>Total</th>' +
            '<th>Tipo</th>' +
            '<th>Estado</th>' +
            '</tr></thead>';

        var rows = invoices.map(function (inv, idx) {
            // NOTA: inv viene del endpoint preview-buzon (views_mail_ingestion.py),
            // NO del FacturaListSerializer. Sus campos son distintos al modelo Factura:
            //   numero_factura (buzon) -> numero (modelo)
            //   valor_total    (buzon) -> total  (modelo)
            //   remitente_email (buzon) -> no tiene campo en Factura
            var numero  = inv.numero || inv.numero_factura || 'N/A';
            var total   = fmt(inv.total || inv.valor_total || 0);
            var emisor  = inv.emisor || inv.remitente_email || 'N/A';
            var tipo    = inv.tipo_archivo || (inv.xml ? 'XML' : 'PDF');
            var tipoClass = (tipo === 'XML' || tipo === 'UBL') ? 'text-success fw-bold' : 'text-muted';

            var estadoBadge = '<span class="badge bg-warning text-dark">Pendiente</span>';
            if (inv.estado === 'procesado') estadoBadge = '<span class="badge bg-success">Procesado</span>';
            if (inv.estado === 'error')     estadoBadge = '<span class="badge bg-danger">Error</span>';

            return '<tr data-sync-idx="' + idx + '">' +
                '<td><input type="checkbox" class="sync-check" value="' + idx + '"></td>' +
                '<td class="text-truncate" style="max-width:150px" title="' + (utils.escapeHtml ? utils.escapeHtml(emisor) : emisor) + '">' + (utils.escapeHtml ? utils.escapeHtml(emisor) : emisor) + '</td>' +
                '<td>' + (utils.escapeHtml ? utils.escapeHtml(numero) : numero) + '</td>' +
                '<td class="text-end">' + total + '</td>' +
                '<td class="' + tipoClass + '">' + tipo + '</td>' +
                '<td>' + estadoBadge + '</td>' +
                '</tr>';
        }).join('');

        container.innerHTML =
            alertXml +
            '<div class="d-flex justify-content-between align-items-center mb-2">' +
            '<span class="text-muted small">' + invoices.length + ' facturas encontradas en el buzon</span>' +
            '<div class="d-flex gap-2">' +
            '<button class="btn btn-sm btn-primary" id="btn-procesar-seleccionados"><i class="bi bi-download me-1"></i>Importar seleccionados</button>' +
            '<button class="btn btn-sm btn-outline-secondary" id="btn-cancelar-sync">Cancelar</button>' +
            '</div>' +
            '</div>' +
            '<div class="table-responsive"><table class="table table-sm table-hover">' + thead + '<tbody>' + rows + '</tbody></table></div>' +
            '<div id="sync-progress" class="mt-2"></div>';

        // Seleccionar todos
        var checkAll = d.getElementById('check-all-sync');
        if (checkAll) {
            checkAll.addEventListener('change', function () {
                container.querySelectorAll('.sync-check').forEach(function (cb) { cb.checked = checkAll.checked; });
            });
        }

        // Cancelar
        var btnCancelar = d.getElementById('btn-cancelar-sync');
        if (btnCancelar) {
            btnCancelar.addEventListener('click', function () {
                _state.active = false;
                container.innerHTML = '';
                if (w.SintelFeedback) w.SintelFeedback.info('Sincronizacion cancelada');
            });
        }

        // Procesar seleccionados
        var btnProcesar = d.getElementById('btn-procesar-seleccionados');
        if (btnProcesar) {
            btnProcesar.addEventListener('click', function () {
                var checked = Array.from(container.querySelectorAll('.sync-check:checked'));
                if (checked.length === 0) {
                    if (w.SintelFeedback) w.SintelFeedback.warning('Seleccione al menos una factura');
                    return;
                }
                var indices = checked.map(function (cb) { return parseInt(cb.value, 10); });
                procesarSeleccionados(indices, _state.pendingInvoices);
            });
        }
    }

    // ---------------------------------------------------------
    // Seccion: Procesamiento de facturas
    // ---------------------------------------------------------

    /**
     * Procesa en lote las facturas seleccionadas de la lista de pendientes.
     * @param {number[]} indices - Indices del array pendingInvoices a procesar
     * @param {Array} pendingInvoices - Array completo de facturas pendientes
     */
    async function procesarSeleccionados(indices, pendingInvoices) {
        if (!Array.isArray(indices) || indices.length === 0) return;

        var btnProcesar = d.getElementById('btn-procesar-seleccionados');
        if (btnProcesar) { btnProcesar.disabled = true; btnProcesar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Procesando...'; }

        var total = indices.length;
        _state.processed = 0;
        _state.errors    = 0;

        _actualizarBarraProgreso(0, total, 'Iniciando procesamiento...');

        for (var i = 0; i < indices.length; i++) {
            var idx = indices[i];
            if (idx < 0 || idx >= pendingInvoices.length) continue;

            var invoice = pendingInvoices[idx];

            // Filtro IDOR: verificar que la factura pertenece al tenant
            if (invoice.belongs_to_tenant === false) {
                console.warn(MOD + ':procesarSeleccionados factura idx=' + idx + ' no pertenece al tenant. Omitida.');
                _state.errors++;
                _marcarFilaEstado(idx, 'error');
                continue;
            }

            try {
                await procesarIndividual(invoice);
                _state.processed++;
                _marcarFilaEstado(idx, 'procesado');
            } catch (err) {
                console.error(MOD + ':procesarSeleccionados error en factura idx=' + idx, err);
                _state.errors++;
                _marcarFilaEstado(idx, 'error');
            }

            _actualizarBarraProgreso(_state.processed + _state.errors, total,
                'Procesadas ' + (_state.processed + _state.errors) + ' de ' + total);
        }

        _actualizarBarraProgreso(total, total, 'Completado');
        _finalizarSincronizacion();
    }

    /**
     * Procesa una sola factura pendiente del buzon.
     * @param {Object} invoice - Datos de la factura del buzon
     */
    async function procesarIndividual(invoice) {
        if (!invoice) throw new Error('Invoice nulo');

        var api = w.Sintel.Factura.api;
        var dto = invoice.dto || invoice;

        var res = await api.crearDesdeDTO(dto, true, invoice.file_bytes, invoice.file_type || 'xml');

        if (!res.ok) {
            var msg = (res.data && (res.data.detail || res.data.error)) || ('HTTP ' + res.status);
            throw new Error(msg);
        }

        return res.data;
    }

    // ---------------------------------------------------------
    // Seccion: Helpers de UI de progreso
    // ---------------------------------------------------------

    function _actualizarBarraProgreso(actual, total, mensaje) {
        var progDiv = d.getElementById('sync-progress');
        if (!progDiv) return;

        var pct = total > 0 ? Math.round((actual / total) * 100) : 0;

        progDiv.innerHTML =
            '<div class="mb-1 small text-muted">' + (mensaje || '') + '</div>' +
            '<div class="progress" style="height: 12px;">' +
            '<div class="progress-bar" role="progressbar" style="width:' + pct + '%" aria-valuenow="' + pct + '" aria-valuemin="0" aria-valuemax="100">' +
            pct + '%</div>' +
            '</div>';
    }

    function _marcarFilaEstado(idx, estado) {
        var row = d.querySelector('[data-sync-idx="' + idx + '"]');
        if (!row) return;

        var badgeCell = row.querySelector('td:last-child');
        if (!badgeCell) return;

        if (estado === 'procesado') {
            badgeCell.innerHTML = '<span class="badge bg-success">Procesado</span>';
        } else if (estado === 'error') {
            badgeCell.innerHTML = '<span class="badge bg-danger">Error</span>';
        }
    }

    function _setLoading(loading) {
        var container = d.getElementById('sync-container');
        if (!container) return;
        if (loading) {
            container.innerHTML =
                '<div class="text-center py-4">' +
                '<div class="spinner-border text-primary mb-2"></div>' +
                '<p class="text-muted small">Conectando con el buzon...</p>' +
                '</div>';
        }
    }

    /**
     * Finaliza el proceso de sincronizacion:
     * 1. Actualiza el last_inbox_uid en el servidor
     * 2. Emite el evento para que main.js refresque la tabla
     */
    async function _finalizarSincronizacion() {
        _state.active = false;

        // Actualizar estado del buzon
        if (_state.configId && _state.lastInboxUid) {
            var api = w.Sintel.Factura.api;
            await api.actualizarEstadoBuzon(_state.configId, _state.lastInboxUid);
        }

        var ok    = _state.processed;
        var error = _state.errors;

        // Notificar al usuario
        if (error === 0) {
            if (w.SintelFeedback) w.SintelFeedback.success('Sincronizacion completada: ' + ok + ' facturas importadas');
        } else {
            if (w.SintelFeedback) w.SintelFeedback.warning('Sincronizacion completada: ' + ok + ' importadas, ' + error + ' con error');
        }

        // Emitir evento para que FacturaController refresque la tabla
        d.dispatchEvent(new CustomEvent('sintel:facturas:sincronizado', {
            bubbles: true,
            detail: { processed: ok, errors: error }
        }));

        console.log(MOD + ':sincronizacion finalizada ok=' + ok + ' errors=' + error);
    }

    // -- Exportar --
    w.Sintel.Factura.sync = {
        sincronizar:          sincronizar,
        mostrarListaPendientes: mostrarListaPendientes,
        procesarSeleccionados: procesarSeleccionados,
        procesarIndividual:   procesarIndividual
    };

    // Alias de compatibilidad para templates con onclick heredado
    w.FacturasSyncModule = w.Sintel.Factura.sync;

})(window, document);
