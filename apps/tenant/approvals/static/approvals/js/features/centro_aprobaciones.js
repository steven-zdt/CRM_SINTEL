/**
 * Feature: Centro de Aprobaciones (Fase 8/9 de
 * PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md).
 *
 * Banner + KPIs + bandeja server-side (DataTables 3.x) + offcanvas de
 * revision con ruta del proceso, resumen financiero e historial. Todos los
 * numeros provienen del backend (#6/#7 del plan) -- ningun calculo de
 * riesgo/prioridad/saldo se reimplementa aqui.
 *
 * Namespace: window.Sintel.Approvals.Centro
 */
(function(w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Approvals = w.Sintel.Approvals || {};

    var TABLA_SELECTOR = '#tabla-centro-aprobaciones';
    var _tablaInicializada = false;
    var _resumenCargado = false;

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function fmtMoney(value) {
        var n = parseFloat(value) || 0;
        return (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(n) : ('$' + n.toLocaleString('en-US'));
    }

    function fmtFecha(iso) {
        if (!iso) return '—';
        var parsed = new Date(iso);
        if (isNaN(parsed.getTime())) return escapeHtml(iso);
        return parsed.toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    function fmtTiempoPendiente(horas) {
        if (horas === null || horas === undefined) return '—';
        if (horas < 1) return Math.round(horas * 60) + 'm';
        if (horas < 24) return horas.toFixed(1) + 'h';
        return (horas / 24).toFixed(1) + 'd';
    }

    var PRIORIDAD_CFG = {
        ALTA:  { emoji: '🔴', label: 'Crítica', cls: 'bg-danger bg-opacity-10 text-danger border-danger border-opacity-25' },
        MEDIA: { emoji: '🟠', label: 'Riesgo',  cls: 'bg-warning bg-opacity-10 text-warning-emphasis border-warning border-opacity-25' },
        BAJA:  { emoji: '🟢', label: 'Normal',  cls: 'bg-success bg-opacity-10 text-success border-success border-opacity-25' },
    };

    var ESTADO_CFG = {
        PENDIENTE: 'bg-warning bg-opacity-10 text-warning-emphasis border-warning border-opacity-25',
        APROBADA:  'bg-success bg-opacity-10 text-success border-success border-opacity-25',
        RECHAZADA: 'bg-danger bg-opacity-10 text-danger border-danger border-opacity-25',
        CANCELADA: 'bg-dark bg-opacity-10 text-dark border-dark border-opacity-25',
    };

    function renderPrioridadBadge(value) {
        var cfg = PRIORIDAD_CFG[value] || { emoji: '', label: value, cls: 'bg-secondary text-white' };
        return '<span class="badge border ' + cfg.cls + '">' + cfg.emoji + ' ' + escapeHtml(cfg.label) + '</span>';
    }

    function renderEstadoBadge(value) {
        var cls = ESTADO_CFG[value] || 'bg-secondary text-white';
        return '<span class="badge border ' + cls + '">' + escapeHtml(value) + '</span>';
    }

    // ── Banner / KPIs ───────────────────────────────────────────────────

    async function cargarResumen() {
        try {
            var r = await w.Sintel.Approvals.API.resumen();
            d.getElementById('centro-aprobaciones-section').hidden = false;

            var titulo = d.getElementById('ca-banner-titulo');
            titulo.textContent = r.pendientes + (r.pendientes === 1 ? ' solicitud pendiente de revisión' : ' solicitudes pendientes de revisión');

            var pillsHtml = '';
            if (r.criticas) pillsHtml += '<span class="ca-pill ca-pill-critica">🔴 ' + r.criticas + ' críticas</span>';
            if (r.riesgo) pillsHtml += '<span class="ca-pill ca-pill-riesgo">🟠 ' + r.riesgo + ' con riesgo</span>';
            if (r.normales) pillsHtml += '<span class="ca-pill ca-pill-normal">🟢 ' + r.normales + ' normales</span>';
            d.getElementById('ca-banner-pills').innerHTML = pillsHtml || '<span class="text-muted small">Sin solicitudes pendientes.</span>';
            d.getElementById('ca-banner-subtitulo').textContent = 'Actualizado ' + new Date().toLocaleTimeString('es-CO');

            d.getElementById('ca-kpi-pendientes').textContent = r.pendientes;
            d.getElementById('ca-kpi-riesgo').textContent = r.criticas;
            d.getElementById('ca-kpi-aprobadas-hoy').textContent = r.aprobadas_hoy;
            d.getElementById('ca-kpi-rechazadas').textContent = r.rechazadas;
            d.getElementById('ca-kpi-valor-pendiente').textContent = fmtMoney(r.valor_pendiente);
            d.getElementById('ca-kpi-antiguedad').textContent = fmtTiempoPendiente(r.antiguedad_promedio_horas);

            _resumenCargado = true;
        } catch (err) {
            // 403 = usuario no-ADMIN, el Centro simplemente no se muestra
            // (permiso ya validado en backend, #29 del plan) -- no es un error.
            if (err && err.status === 403) {
                var section = d.getElementById('centro-aprobaciones-section');
                if (section) section.hidden = true;
                return;
            }
            console.error('[CentroAprobaciones] Error cargando resumen:', err);
        }
    }

    // ── Bandeja (DataTables 3.x) ─────────────────────────────────────────

    function renderDocumento(data, type, row) {
        var snap = row.snapshot_financiero || {};
        return '<span class="fw-bold text-primary" style="font-size:.85rem;">' + escapeHtml(snap.numero || row.objeto_uuid) + '</span>';
    }

    function renderProyecto(data, type, row) {
        var snap = row.snapshot_financiero || {};
        if (!snap.proyecto_nombre) return '<span class="text-muted small">—</span>';
        return '<span class="badge bg-light text-dark border border-secondary"><i class="bi bi-folder text-secondary me-1"></i>' + escapeHtml(snap.proyecto_nombre) + '</span>';
    }

    function renderOrigen(data, type, row) {
        var snap = row.snapshot_financiero || {};
        if (!snap.cotizacion_numero) return '<span class="text-muted small">—</span>';
        return '<span class="badge bg-info bg-opacity-10 text-info-emphasis border border-info border-opacity-25">' + escapeHtml(snap.cotizacion_numero) + '</span>';
    }

    function renderValor(data, type, row) {
        var snap = row.snapshot_financiero || {};
        return '<span class="fw-bold">' + fmtMoney(snap.valor) + '</span>';
    }

    function renderRiesgo(data, type, row) {
        var snap = row.snapshot_financiero || {};
        if (snap.riesgo_pct === null || snap.riesgo_pct === undefined) return '<span class="text-muted small">—</span>';
        var pct = Math.round(parseFloat(snap.riesgo_pct) * 100);
        var cfg = PRIORIDAD_CFG[row.prioridad] || { cls: 'bg-secondary text-white' };
        return '<span class="badge border ' + cfg.cls + '">' + pct + '%</span>';
    }

    function renderTiempoPendiente(value) {
        return fmtTiempoPendiente(value);
    }

    function renderAccion(data, type, row) {
        if (row.estado !== 'PENDIENTE') {
            return '<button type="button" class="btn btn-sm btn-outline-secondary btn-ca-revisar" data-uuid="' + escapeHtml(row.uuid) + '"><i class="bi bi-eye"></i></button>';
        }
        return '<button type="button" class="btn btn-sm btn-primary btn-ca-revisar" data-uuid="' + escapeHtml(row.uuid) + '">REVISAR</button>';
    }

    var CA_COLUMNS = [
        { data: 'prioridad', title: 'Prioridad', render: renderPrioridadBadge },
        { data: 'tipo_documento', title: 'Tipo', orderable: false },
        { data: null, title: 'Documento', orderable: false, render: renderDocumento },
        { data: 'solicitante_nombre', title: 'Solicitante', orderable: false },
        { data: null, title: 'Proyecto', orderable: false, searchable: false, render: renderProyecto },
        { data: null, title: 'Origen', orderable: false, searchable: false, render: renderOrigen },
        { data: null, title: 'Valor', orderable: false, render: renderValor },
        { data: null, title: 'Riesgo', orderable: false, searchable: false, render: renderRiesgo },
        { data: 'tiempo_pendiente_horas', title: 'Tiempo Pendiente', render: renderTiempoPendiente },
        { data: 'estado', title: 'Estado', render: renderEstadoBadge },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccion },
    ];

    function initTabla() {
        if (_tablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        if (!d.querySelector(TABLA_SELECTOR)) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, w.Sintel.Approvals.API.dtUrl, CA_COLUMNS, {
            pageLength: 10,
            order: [[8, 'desc']],
        });
        _tablaInicializada = true;

        var filtroEstado = d.getElementById('ca-filtro-estado');
        var filtroPrioridad = d.getElementById('ca-filtro-prioridad');
        if (filtroEstado) filtroEstado.addEventListener('change', function() {
            w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 9, filtroEstado.value);
        });
        if (filtroPrioridad) filtroPrioridad.addEventListener('change', function() {
            w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 0, filtroPrioridad.value);
        });
    }

    function refrescarTodo() {
        cargarResumen();
        if (_tablaInicializada) w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
    }

    // ── Offcanvas de revision (Fase 9) ───────────────────────────────────

    var TIPO_DOCUMENTO_WORKSPACE_TAB = {
        REQUISICION: 'compras',
        COTIZACION: 'cotizaciones',
        PROYECTO: 'proyectos',
        ORDEN_COMPRA: 'compras',
    };

    function renderNodo(node) {
        var tab = TIPO_DOCUMENTO_WORKSPACE_TAB[node.tipo] || null;
        var link = tab ? '<a href="/workspace/#' + tab + '" class="small ms-2">Ver</a>' : '';
        return '<div class="ca-ruta-nodo">' +
            '<div>' +
            '<strong>' + escapeHtml(node.tipo) + ' ' + escapeHtml(node.numero || '') + '</strong>' + link +
            '<div class="small text-muted">' + escapeHtml(node.estado || '') + (node.valor ? ' · ' + fmtMoney(node.valor) : '') + '</div>' +
            '</div></div>';
    }

    function renderResumenFinanciero(fs) {
        if (!fs) return '<dt class="col-12 text-muted">Sin datos financieros.</dt>';
        var rows = [
            ['Cotización', fs.valor_cotizacion],
            ['Saldo Cotización', fs.saldo_cotizacion],
            ['Requisición', fs.valor_requisicion],
            ['Comprometido', fs.comprometido_requisicion],
            ['Saldo Requisición', fs.saldo_requisicion],
        ];
        return rows.filter(function(r) { return r[1] !== undefined && r[1] !== null; }).map(function(r) {
            return '<dt class="col-7">' + escapeHtml(r[0]) + '</dt><dd class="col-5 text-end">' + fmtMoney(r[1]) + '</dd>';
        }).join('');
    }

    function renderAlertas(alerts) {
        if (!alerts || !alerts.length) return '';
        return alerts.map(function(a) {
            return '<div class="alert alert-danger py-2 px-3 small mb-2">' + escapeHtml(a.mensaje || a) + '</div>';
        }).join('');
    }

    function renderTimeline(items) {
        if (!items || !items.length) return '<div class="text-muted small">Sin eventos.</div>';
        return items.map(function(t) {
            return '<div class="ca-timeline-item"><strong>' + escapeHtml(t.evento) + '</strong> (' + escapeHtml(t.fuente) + ') — ' +
                escapeHtml(t.usuario || '') + '<div class="text-muted">' + fmtFecha(t.fecha) + (t.observacion ? ' · ' + escapeHtml(t.observacion) : '') + '</div></div>';
        }).join('');
    }

    async function abrirRevisar(uuid) {
        var offcanvasEl = d.getElementById('offcanvas-revisar-solicitud');
        if (!offcanvasEl) return;
        offcanvasEl.setAttribute('data-solicitud-uuid', uuid);

        offcanvasEl.querySelector('#ca-revisar-loading').classList.remove('d-none');
        offcanvasEl.querySelector('#ca-revisar-contenido').classList.add('d-none');
        offcanvasEl.querySelector('#ca-revisar-footer').classList.add('d-none');
        offcanvasEl.querySelector('#ca-revisar-feedback').classList.add('d-none');
        offcanvasEl.querySelector('#ca-revisar-rechazar-panel').classList.add('d-none');

        try { w.Sintel.Core.mostrarOffcanvasSeguro(offcanvasEl); } catch (e) { console.error('[CentroAprobaciones] offcanvas', e); }

        try {
            var dto = await w.Sintel.Approvals.API.trazabilidad(uuid);

            offcanvasEl.querySelector('#ca-revisar-estado-badge').outerHTML =
                '<span id="ca-revisar-estado-badge" class="badge">' + renderEstadoBadge(dto.request.estado) + '</span>';
            offcanvasEl.querySelector('#ca-revisar-solicitante').textContent = dto.request.solicitante || '—';
            offcanvasEl.querySelector('#ca-revisar-fecha').textContent = fmtFecha(dto.request.fecha_envio);

            offcanvasEl.querySelector('#ca-revisar-ruta').innerHTML = (dto.nodes || []).map(renderNodo).join('');
            offcanvasEl.querySelector('#ca-revisar-resumen-financiero').innerHTML = renderResumenFinanciero(dto.financial_summary);
            offcanvasEl.querySelector('#ca-revisar-alertas').innerHTML = renderAlertas(dto.alerts);
            offcanvasEl.querySelector('#ca-revisar-timeline').innerHTML = renderTimeline(dto.timeline);

            offcanvasEl.querySelector('#ca-revisar-loading').classList.add('d-none');
            offcanvasEl.querySelector('#ca-revisar-contenido').classList.remove('d-none');
            if (dto.request.estado === 'PENDIENTE') {
                offcanvasEl.querySelector('#ca-revisar-footer').classList.remove('d-none');
            }
        } catch (err) {
            offcanvasEl.querySelector('#ca-revisar-loading').classList.add('d-none');
            var fb = offcanvasEl.querySelector('#ca-revisar-feedback');
            fb.textContent = (err.data && err.data.message) || 'Error al cargar la trazabilidad.';
            fb.classList.remove('d-none');
        }
    }

    function initEvents() {
        d.body.addEventListener('click', function(e) {
            var btn = e.target.closest('.btn-ca-revisar');
            if (btn) {
                e.preventDefault();
                abrirRevisar(btn.getAttribute('data-uuid'));
                return;
            }

            var offcanvasEl = e.target.closest('#offcanvas-revisar-solicitud');
            if (!offcanvasEl) return;
            var uuid = offcanvasEl.getAttribute('data-solicitud-uuid');

            if (e.target.closest('#btn-ca-aprobar')) {
                e.preventDefault();
                w.UIManager?.confirm('¿Aprobar esta solicitud?').then(async function(confirmed) {
                    if (!confirmed) return;
                    try {
                        await w.Sintel.Approvals.API.aprobar(uuid, '');
                        w.UIManager?.notifySuccess?.('Solicitud aprobada.');
                        var inst = w.bootstrap?.Offcanvas?.getInstance(offcanvasEl);
                        if (inst) inst.hide();
                        refrescarTodo();
                        d.body.dispatchEvent(new CustomEvent('requisicion-changed'));
                    } catch (err) {
                        w.UIManager?.notifyError?.((err.data && err.data.message) || 'Error al aprobar.');
                    }
                });
                return;
            }

            if (e.target.closest('#btn-ca-mostrar-rechazar')) {
                e.preventDefault();
                offcanvasEl.querySelector('#ca-revisar-rechazar-panel')?.classList.remove('d-none');
                return;
            }

            if (e.target.closest('#btn-ca-cancelar-rechazo')) {
                e.preventDefault();
                offcanvasEl.querySelector('#ca-revisar-rechazar-panel')?.classList.add('d-none');
                return;
            }

            if (e.target.closest('#btn-ca-confirmar-rechazo')) {
                e.preventDefault();
                var motivo = offcanvasEl.querySelector('#ca-revisar-motivo-rechazo')?.value?.trim();
                if (!motivo) { w.UIManager?.notifyError?.('Debe indicar el motivo del rechazo.'); return; }
                (async function() {
                    try {
                        await w.Sintel.Approvals.API.rechazar(uuid, motivo);
                        w.UIManager?.notifySuccess?.('Solicitud rechazada.');
                        var inst = w.bootstrap?.Offcanvas?.getInstance(offcanvasEl);
                        if (inst) inst.hide();
                        refrescarTodo();
                        d.body.dispatchEvent(new CustomEvent('requisicion-changed'));
                    } catch (err) {
                        w.UIManager?.notifyError?.((err.data && err.data.message) || 'Error al rechazar.');
                    }
                })();
                return;
            }
        });

        d.body.addEventListener('htmx:beforeCleanupElement', function(evt) {
            var el = evt?.detail?.elt;
            if (el && el.id === 'offcanvas-revisar-solicitud') {
                try {
                    var instance = w.bootstrap?.Offcanvas?.getInstance(el);
                    if (instance) instance.dispose();
                } catch (e) { /* noop */ }
            }
        });
    }

    // ── Setup ────────────────────────────────────────────────────────────

    function setup() {
        cargarResumen();
        initTabla();
        initEvents();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

    d.body.addEventListener('tab-activated', function(evt) {
        if (evt?.detail?.tabName !== 'dashboard') return;
        if (!_resumenCargado) cargarResumen();
        initTabla();
        if (_tablaInicializada) w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
    });

    w.Sintel.Approvals.Centro = { refrescarTodo: refrescarTodo };

})(window, document);
