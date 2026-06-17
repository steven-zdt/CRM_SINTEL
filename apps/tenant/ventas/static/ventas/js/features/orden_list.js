/**
 * orden_list.js — Grilla Tabulator para Ordenes de Venta v3.10.5
 * Namespace: window.Sintel.Ventas (compartido con editor)
 *
 * Anti-Zombies: destruye instancias previas al re-montar (HTMX swap).
 * KPIs: calculados desde los datos del grid, sin endpoints extra.
 */
(function (w, d) {
    'use strict';

    var MOD = '[ventas.list]';

    // Anti-Zombies
    if (w._SintelVentasTable) {
        try { w._SintelVentasTable.destroy(); } catch (_) {}
        w._SintelVentasTable = null;
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    // ── Utilidades de Formato ──────────────────────────────────────────────

    function fmtMoneda(v) {
        var n = parseFloat(v);
        if ((v === null || v === undefined || v === '') && v !== 0) return '—';
        if (isNaN(n)) return '—';
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP',
            minimumFractionDigits: 0, maximumFractionDigits: 0
        }).format(n);
    }

    function fmtFecha(v) {
        if (!v) return '—';
        try {
            return new Date(v + 'T00:00:00').toLocaleDateString('es-CO', {
                day: '2-digit', month: 'short', year: 'numeric'
            });
        } catch (_) { return v; }
    }

    var ESTADO_CONFIG = {
        BORRADOR:   { cls: 'secondary', label: 'Borrador' },
        CONFIRMADA: { cls: 'primary',   label: 'Confirmada' },
        FACTURADA:  { cls: 'success',   label: 'Facturada' },
        ANULADA:    { cls: 'danger',    label: 'Anulada' },
    };

    function chipEstado(estado) {
        var cfg = ESTADO_CONFIG[estado] || { cls: 'dark', label: estado };
        return '<span class="badge bg-' + cfg.cls + '" style="font-size:0.78rem;">' + cfg.label + '</span>';
    }

    // ── KPIs ──────────────────────────────────────────────────────────────

    function actualizarKPIs(rows) {
        var elTotal      = d.getElementById('kpi-ventas-total');
        var elMonto      = d.getElementById('kpi-ventas-monto');
        var elConfirm    = d.getElementById('kpi-ventas-confirmadas');
        var elFacturadas = d.getElementById('kpi-ventas-facturadas');
        if (!elTotal) return;

        var activas = rows.filter(function (r) { return r.estado !== 'ANULADA'; });
        elTotal.textContent      = rows.length;
        elMonto.textContent      = fmtMoneda(activas.reduce(function (s, r) { return s + (parseFloat(r.total) || 0); }, 0));
        elConfirm.textContent    = rows.filter(function (r) { return r.estado === 'CONFIRMADA'; }).length;
        elFacturadas.textContent = rows.filter(function (r) { return r.estado === 'FACTURADA'; }).length;
    }

    // ── Columnas ──────────────────────────────────────────────────────────

    function getColumnas() {
        return [
            {
                title: 'Cliente',
                field: 'cliente_nombre',
                minWidth: 200,
                formatter: function (cell) {
                    var row  = cell.getRow().getData();
                    var nom  = row.cliente_nombre  || '—';
                    var doc  = row.cliente_documento || '';
                    return '<div style="line-height:1.35;">'
                        + '<div class="fw-semibold text-dark text-truncate small" title="' + nom + '">' + nom + '</div>'
                        + (doc ? '<div class="text-muted" style="font-size:0.72rem;">NIT: ' + doc + '</div>' : '')
                        + '</div>';
                }
            },
            {
                title: 'Fecha',
                field: 'fecha_emision',
                width: 120,
                formatter: function (cell) {
                    return '<div style="font-size:0.8rem;">'
                        + '<i class="bi bi-calendar text-muted me-1"></i>'
                        + fmtFecha(cell.getValue())
                        + '</div>';
                }
            },
            {
                title: 'Estado',
                field: 'estado',
                width: 130,
                formatter: function (cell) {
                    return chipEstado(cell.getValue());
                }
            },
            {
                title: 'Total',
                field: 'total',
                width: 130,
                hozAlign: 'right',
                formatter: function (cell) {
                    return '<div class="fw-semibold text-end">' + fmtMoneda(cell.getValue()) + '</div>';
                }
            },
            {
                title: 'Acciones',
                field: '_acciones',
                width: 100,
                hozAlign: 'center',
                headerSort: false,
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    return '<button class="btn btn-sm btn-outline-secondary" '
                        + 'data-action="ver-detalle" data-uuid="' + row.uuid + '" '
                        + 'title="Ver detalle">'
                        + '<i class="bi bi-eye"></i></button>';
                },
                cellClick: function (e, cell) {
                    var btn = e.target.closest('[data-action="ver-detalle"]');
                    if (!btn) return;
                    var uuid = btn.getAttribute('data-uuid');
                    if (!uuid) return;
                    w.Sintel.Ventas.List.abrirDetalle(uuid);
                }
            }
        ];
    }

    // ── Modulo List ───────────────────────────────────────────────────────

    var List = {
        table: null,
        tableId: '#grid-ventas',
        _initializing: false,

        init: function (retry) {
            retry = retry || 0;
            var container = d.querySelector(this.tableId);
            if (this.table || !container || this._initializing) return;
            this._initializing = true;

            if (!w.TabulatorFactory) {
                if (retry < 5) {
                    this._initializing = false;
                    setTimeout(function () { List.init(retry + 1); }, 500);
                } else {
                    console.error(MOD, 'TabulatorFactory no disponible.');
                    this._initializing = false;
                }
                return;
            }

            var spinnerEl = d.querySelector('[data-spinner="ventas"]');
            if (spinnerEl) spinnerEl.style.display = 'none';
            container.style.display = 'block';

            try {
                var apiUrl = (w.Sintel.Ventas.API && w.Sintel.Ventas.API.list)
                    ? '/api/v1/ventas/'
                    : '/api/v1/ventas/';

                this.table = w.TabulatorFactory.create(
                    this.tableId,
                    apiUrl,
                    getColumnas(),
                    {
                        initialSort: [{ field: 'fecha_emision', dir: 'desc' }],
                        placeholder: 'No se encontraron ordenes de venta',
                        searchInputSelector: '#search-orden-venta',
                    }
                );

                if (this.table) {
                    w._SintelVentasTable = this.table;
                    this.table.on('dataLoaded', function (data) {
                        actualizarKPIs(data);
                    });
                    this.table.on('dataFiltered', function (_f, rows) {
                        actualizarKPIs(rows.map(function (r) { return r.getData(); }));
                    });
                    this._initializing = false;
                } else {
                    this._initializing = false;
                    setTimeout(function () { List.init(0); }, 1000);
                }
            } catch (err) {
                console.error(MOD, 'Error critico al inicializar:', err);
                this._initializing = false;
            }
        },

        recargar: function () {
            if (this.table && typeof this.table.replaceData === 'function') {
                this.table.replaceData();
            }
        },

        abrirDetalle: function (uuid) {
            var url = w.Sintel.Ventas.API.renderDetalle(uuid);
            var container = d.getElementById('offcanvas-container-ventas');
            if (!container) return;

            htmx.ajax('GET', url, { target: '#offcanvas-container-ventas', swap: 'innerHTML' });
        },
    };

    w.Sintel.Ventas.List = List;

    // Auto-init cuando el DOM este listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', function () { List.init(); });
    } else {
        List.init();
    }

})(window, document);
