/**
 * venta_list.js — Feature List para Venta
 *
 * Piloto DataTables 3.x + ColumnControl (docs/ux/TABLES_FORMS_RELEASE_GATE.md):
 * la tabla (#tabla-ventas) ahora se puebla via ajax contra
 * POST /api/v1/ventas/dt/ usando Sintel.Core.DataTablesFactory
 * (apps/tenant/core/static/core/js/common/datatables.factory.js). Los KPIs
 * (#ventas-panel) siguen siendo un fragmento HTMX server-rendered aparte.
 *
 * Este archivo maneja: init de la tabla, filtros por columna (fila
 * #fila-filtros-ventas), accion de fila (ver detalle, eliminar
 * sincronizada), apertura de offcanvas, y el refresco tras una mutacion
 * (evento 'venta-updated' -- recarga la tabla via ajax.reload y las KPIs
 * via HTMX, sin perder la pagina actual de la tabla).
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    var TABLA_SELECTOR = '#tabla-ventas';
    var DT_URL = '/api/v1/ventas/dt/';

    var BADGE_ESTADO = {
        BORRADOR: 'bg-secondary',
        FACTURADA_DIAN: 'bg-success',
        ANULADA: 'bg-danger',
    };
    var LABEL_ESTADO = {
        BORRADOR: 'Borrador',
        FACTURADA_DIAN: 'Facturada DIAN',
        ANULADA: 'Anulada',
    };

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function formatFecha(iso) {
        if (!iso) return '—';
        var parsed = new Date(iso + 'T00:00:00');
        if (isNaN(parsed.getTime())) return escapeHtml(iso);
        return parsed.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
    }

    function renderCliente(data, type, row) {
        var nombre = escapeHtml(row.cliente_nombre || '—');
        var nit = row.cliente_documento
            ? '<div class="text-muted" style="font-size:0.72rem;">NIT: ' + escapeHtml(row.cliente_documento) + '</div>'
            : '';
        return '<div class="fw-semibold text-dark text-truncate small">' + nombre + '</div>' + nit;
    }

    function renderEstado(value) {
        var badge = BADGE_ESTADO[value] || 'bg-dark';
        var label = LABEL_ESTADO[value] || value;
        return '<span class="badge ' + badge + ' badge-sm">' + escapeHtml(label) + '</span>';
    }

    function renderFacturaNumero(data, type, row) {
        var numero = row.factura_numero;
        if (!numero) return '<span class="text-muted" style="font-size:0.78rem;">—</span>';
        return '<span class="badge bg-success-subtle text-success border border-success-subtle badge-sm">' +
            '<i class="bi bi-receipt-cutoff me-1"></i>' + escapeHtml(numero) + '</span>';
    }

    function renderTotal(value) {
        var formatted = (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(value)
            : value;
        return '<div class="fw-semibold text-end">' + formatted + '</div>';
    }

    function renderAcciones(data, type, row) {
        var verBtn = '<button type="button" class="btn btn-sm btn-outline-secondary btn-ver-venta" ' +
            'data-uuid="' + escapeHtml(row.uuid) + '" title="Ver detalle"><i class="bi bi-eye"></i></button>';
        if (!row.factura_asociada_id) return verBtn;
        var eliminarBtn = '<button type="button" class="btn btn-sm btn-outline-danger ms-1 btn-eliminar-venta-sync" ' +
            'data-uuid="' + escapeHtml(row.uuid) + '" data-numero="' + escapeHtml(row.numero_factura || '') + '" ' +
            'title="Eliminar Venta sincronizada (no afecta la Factura)"><i class="bi bi-trash3"></i></button>';
        return verBtn + eliminarBtn;
    }

    var COLUMNS = [
        { data: 'cliente_nombre', title: 'Cliente', render: renderCliente },
        { data: 'fecha_emision', title: 'Fecha', render: function (v) { return formatFecha(v); } },
        { data: 'estado', title: 'Estado', render: function (v) { return renderEstado(v); } },
        { data: 'factura_numero', title: 'Factura DIAN', orderable: false, render: renderFacturaNumero },
        { data: 'total_neto', title: 'Total', className: 'text-end', render: function (v) { return renderTotal(v); } },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
    ];

    var List = {
        reload: function () {
            d.body.dispatchEvent(new CustomEvent('venta-updated'));
        },

        recargar: function () {
            this.reload();
        },

        abrirDetalle: function (uuid) {
            var url = w.Sintel.Ventas.API.renderDetalle(uuid);
            var container = d.getElementById('offcanvas-container-ventas');
            if (!container) return;
            htmx.ajax('GET', url, { target: '#offcanvas-container-ventas', swap: 'innerHTML' });
        },

        eliminarSincronizada: async function (btn) {
            var uuid = btn.getAttribute('data-uuid');
            var numero = btn.getAttribute('data-numero') || uuid;
            if (!uuid) return;
            var confirmado = await w.UIManager?.confirm(
                'Eliminar la Venta sincronizada de la Factura "' + numero + '"?\n' +
                'La Factura NO se elimina ni se modifica -- solo esta Venta comercial, ' +
                'que volvera a aparecer como pendiente en "Sincronizar y validar facturas".'
            );
            if (!confirmado) return;

            btn.disabled = true;
            w.Sintel.Ventas.API.eliminarSincronizada(uuid)
                .then(function () {
                    List.reload();
                })
                .catch(function (err) {
                    btn.disabled = false;
                    var msg = (err.data && err.data.detail) ? err.data.detail : 'No se pudo eliminar la Venta.';
                    var feedEl = d.getElementById('feedback-ventas-list');
                    if (feedEl) {
                        feedEl.className = 'alert alert-danger mb-2';
                        feedEl.textContent = msg;
                        feedEl.classList.remove('d-none');
                    }
                });
        },
    };

    w.Sintel.Ventas.List = List;

    // ── Acciones de fila (delegado sobre la tabla, sobrevive a cada draw) ──

    function attachTableListeners() {
        var tabla = d.querySelector(TABLA_SELECTOR);
        if (!tabla) return;

        tabla.addEventListener('click', function (ev) {
            var btnVer = ev.target.closest('.btn-ver-venta');
            if (btnVer) {
                ev.preventDefault();
                var uuid = btnVer.dataset.uuid;
                if (uuid) List.abrirDetalle(uuid);
                return;
            }

            var btnEliminar = ev.target.closest('.btn-eliminar-venta-sync');
            if (btnEliminar) {
                ev.preventDefault();
                List.eliminarSincronizada(btnEliminar);
            }
        });
    }

    // ── Filtros por columna (fila #fila-filtros-ventas) ─────────────────────
    // DataTables reescribe el <thead> completo al inicializarse (lo trata como
    // fila de cabecera secundaria y sustituye su contenido por titulo+boton de
    // orden) -- cualquier <input>/<select> puesto ahi como HTML estatico queda
    // destruido antes de que este modulo pueda engancharlo. Por eso la fila de
    // filtros se construye e inserta en JS DESPUES de crear el DataTable
    // (que solo reconstruye el thead una vez, al iniciar -- los redraws
    // posteriores por busqueda/orden/paginacion no lo vuelven a tocar).

    function filaFiltrosHtml() {
        return '<tr id="fila-filtros-ventas" class="table-light">' +
            '<th><input type="text" class="form-control form-control-sm" id="filtro-venta-cliente" placeholder="Filtrar cliente..."></th>' +
            '<th><div class="d-flex gap-1">' +
            '<input type="date" class="form-control form-control-sm" id="filtro-venta-fecha-desde" title="Desde">' +
            '<input type="date" class="form-control form-control-sm" id="filtro-venta-fecha-hasta" title="Hasta">' +
            '</div></th>' +
            '<th><select class="form-select form-select-sm" id="filtro-venta-estado">' +
            '<option value="">Todas</option>' +
            '<option value="BORRADOR">Borrador</option>' +
            '<option value="FACTURADA_DIAN">Facturada DIAN</option>' +
            '<option value="ANULADA">Anulada</option>' +
            '</select></th>' +
            '<th></th>' +
            '<th><div class="d-flex gap-1">' +
            '<input type="number" class="form-control form-control-sm" id="filtro-venta-total-min" placeholder="Min">' +
            '<input type="number" class="form-control form-control-sm" id="filtro-venta-total-max" placeholder="Max">' +
            '</div></th>' +
            '<th></th>' +
            '</tr>';
    }

    function insertarFilaFiltros() {
        var thead = d.querySelector(TABLA_SELECTOR + ' thead');
        if (!thead || d.getElementById('filtro-venta-cliente')) return;
        thead.insertAdjacentHTML('beforeend', filaFiltrosHtml());
    }

    function debounce(fn, delay) {
        var timer = null;
        return function () {
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () { fn.apply(null, args); }, delay);
        };
    }

    function bindFiltrosColumna() {
        var Factory = w.Sintel.Core.DataTablesFactory;

        var inputCliente = d.getElementById('filtro-venta-cliente');
        if (inputCliente) {
            inputCliente.addEventListener('keyup', debounce(function () {
                Factory.columnSearch(TABLA_SELECTOR, 0, inputCliente.value);
            }, 400));
        }

        var fechaDesde = d.getElementById('filtro-venta-fecha-desde');
        var fechaHasta = d.getElementById('filtro-venta-fecha-hasta');
        function aplicarRangoFecha() {
            Factory.columnRangeSearch(TABLA_SELECTOR, 1, fechaDesde.value, fechaHasta.value);
        }
        if (fechaDesde) fechaDesde.addEventListener('change', aplicarRangoFecha);
        if (fechaHasta) fechaHasta.addEventListener('change', aplicarRangoFecha);

        var selectEstado = d.getElementById('filtro-venta-estado');
        if (selectEstado) {
            selectEstado.addEventListener('change', function () {
                Factory.columnSearch(TABLA_SELECTOR, 2, selectEstado.value);
            });
        }

        var totalMin = d.getElementById('filtro-venta-total-min');
        var totalMax = d.getElementById('filtro-venta-total-max');
        function aplicarRangoTotal() {
            Factory.columnRangeSearch(TABLA_SELECTOR, 4, totalMin.value, totalMax.value);
        }
        if (totalMin) totalMin.addEventListener('keyup', debounce(aplicarRangoTotal, 400));
        if (totalMax) totalMax.addEventListener('keyup', debounce(aplicarRangoTotal, 400));
    }

    // ── Init tabla + eventos globales ────────────────────────────────────

    function initTabla() {
        w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
            pageLength: 20,
            order: [[1, 'desc']],
        });
        insertarFilaFiltros();
        attachTableListeners();
        bindFiltrosColumna();
    }

    function bindRefresh() {
        var btn = d.getElementById('btn-refresh-ventas');
        if (btn) btn.addEventListener('click', function () { List.reload(); });
    }

    function bindVentaUpdated() {
        d.body.addEventListener('venta-updated', function () {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
        });
    }

    function setup() {
        initTabla();
        bindRefresh();
        bindVentaUpdated();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

})(window, document);
