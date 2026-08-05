/**
 * resolucion_list.js — Grilla Tabulator para Resoluciones de Facturacion DIAN v3.16.x
 * Namespace: window.Sintel.Ventas.ResolucionList
 *
 * Anti-Zombies: destruye instancias previas al re-montar.
 */
(function (w, d) {
    'use strict';

    var MOD = '[ventas.resolucion-list]';

    if (w._SintelResolucionTable) {
        try { w._SintelResolucionTable.destroy(); } catch (_) {}
        w._SintelResolucionTable = null;
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    // ── Utilidades ────────────────────────────────────────────────────

    function fmtFecha(v) {
        if (!v) return '—';
        try {
            return new Date(v + 'T00:00:00').toLocaleDateString('es-CO', {
                day: '2-digit', month: 'short', year: 'numeric'
            });
        } catch (_) { return v; }
    }

    function chipVigente(vigente) {
        return vigente
            ? '<span class="badge bg-success" style="font-size:0.75rem;">Activa</span>'
            : '<span class="badge bg-secondary" style="font-size:0.75rem;">Inactiva</span>';
    }

    function chipAgotada(agotada) {
        return agotada
            ? '<span class="badge bg-danger ms-1" style="font-size:0.72rem;">Agotada</span>'
            : '';
    }

    // ── Columnas ──────────────────────────────────────────────────────

    function getColumnas() {
        return [
            {
                title: 'Numero Resolucion',
                field: 'numero_resolucion',
                minWidth: 150,
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var prefijo = row.prefijo ? '<span class="badge bg-primary-subtle text-primary me-1">' + row.prefijo + '</span>' : '';
                    return prefijo + '<span class="fw-semibold">' + (cell.getValue() || '—') + '</span>';
                }
            },
            {
                title: 'Tipo',
                field: 'tipo_display',
                width: 120,
                formatter: function (cell) {
                    return '<span class="text-muted small">' + (cell.getValue() || cell.getRow().getData().tipo || '—') + '</span>';
                }
            },
            {
                title: 'Rango',
                field: 'rango_desde',
                width: 150,
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    var actual = row.consecutivo_actual || row.rango_desde;
                    return '<div style="font-size:0.8rem;">'
                        + row.rango_desde + ' – ' + row.rango_hasta
                        + '<div class="text-muted" style="font-size:0.72rem;">Siguiente: ' + actual + '</div>'
                        + '</div>';
                }
            },
            {
                title: 'Vigencia',
                field: 'fecha_desde',
                width: 170,
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    return '<div style="font-size:0.78rem;">'
                        + fmtFecha(row.fecha_desde) + ' a ' + fmtFecha(row.fecha_hasta)
                        + '</div>';
                }
            },
            {
                title: 'Estado',
                field: 'vigente',
                width: 130,
                formatter: function (cell) {
                    var row = cell.getRow().getData();
                    return chipVigente(cell.getValue()) + chipAgotada(row.agotada);
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
                    return '<button class="btn btn-sm btn-outline-secondary"'
                        + ' data-action="editar-resolucion" data-uuid="' + row.uuid + '"'
                        + ' title="Editar">'
                        + '<i class="bi bi-pencil"></i></button>';
                },
                cellClick: function (e, cell) {
                    var btn = e.target.closest('[data-action="editar-resolucion"]');
                    if (!btn) return;
                    var uuid = btn.getAttribute('data-uuid');
                    if (!uuid) return;
                    w.Sintel.Ventas.ResolucionList.abrirEditar(uuid);
                }
            }
        ];
    }

    // ── Modulo ResolucionList ─────────────────────────────────────────

    var ResolucionList = {
        table: null,
        tableId: '#grid-resoluciones',
        _initializing: false,

        init: function (retry) {
            retry = retry || 0;
            var container = d.querySelector(this.tableId);
            if (this.table || !container || this._initializing) return;
            this._initializing = true;

            if (!w.TabulatorFactory) {
                if (retry < 5) {
                    this._initializing = false;
                    setTimeout(function () { ResolucionList.init(retry + 1); }, 500);
                } else {
                    console.error(MOD, 'TabulatorFactory no disponible.');
                    this._initializing = false;
                }
                return;
            }

            try {
                this.table = w.TabulatorFactory.create(
                    this.tableId,
                    '/api/v1/ventas/resoluciones/',
                    getColumnas(),
                    {
                        initialSort: [{ field: 'vigente', dir: 'desc' }],
                        placeholder: 'No hay resoluciones registradas',
                    }
                );

                if (this.table) {
                    w._SintelResolucionTable = this.table;
                    this._initializing = false;
                } else {
                    this._initializing = false;
                    setTimeout(function () { ResolucionList.init(0); }, 1000);
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

        abrirEditar: function (uuid) {
            var url = w.Sintel.Ventas.API.resoluciones.renderEditar(uuid);
            var container = d.getElementById('offcanvas-container-ventas');
            if (!container) return;
            htmx.ajax('GET', url, { target: '#offcanvas-container-ventas', swap: 'innerHTML' });
        },
    };

    w.Sintel.Ventas.ResolucionList = ResolucionList;

})(window, document);
