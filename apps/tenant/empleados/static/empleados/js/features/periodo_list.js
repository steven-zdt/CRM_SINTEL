// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Periodo List Module — tabla "Periodos de Nomina" es DataTables 3.x
 * (#tabla-periodos-nomina, mismo patron ya validado en Ventas/Bancos/
 * Facturas/Clientes/Proveedores/Compras/Gastos/Empleados -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via ajax
 * contra POST /api/v1/empleados/periodos-nomina/dt/.
 * PeriodoNominaTable/PeriodoNominaTableView (django-tables2) retirados.
 * Namespace: window.Sintel.Empleados.PeriodoList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const TABLA_SELECTOR = '#tabla-periodos-nomina';
    const TABLA_URL = '/api/v1/empleados/periodos-nomina/dt/';
    let _tablaInicializada = false;

    var BADGE_ESTADO = {
        ABIERTO: ['bg-primary', 'bi-unlock'],
        PRELIQUIDADO: ['bg-info text-dark', 'bi-calculator'],
        EN_REVISION: ['bg-warning text-dark', 'bi-eye'],
        APROBADO: ['bg-info text-dark', 'bi-hand-thumbs-up'],
        PAGADO: ['bg-success', 'bi-cash-coin'],
        CERRADO: ['bg-secondary', 'bi-lock'],
        ANULADO: ['bg-danger', 'bi-x-circle'],
        BLOQUEADO: ['bg-dark', 'bi-slash-circle'],
    };

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderPeriodo(value) {
        return '<span class="fw-semibold font-monospace">' + escapeHtml(value) + '</span>';
    }

    function renderVigencia(data, type, row) {
        return '<span class="small"><i class="bi bi-calendar-range text-muted me-1"></i>' +
            escapeHtml(row.fecha_inicio) + ' → ' + escapeHtml(row.fecha_fin) + '</span>';
    }

    function renderEmpleadosCount(value) {
        return '<span class="badge bg-secondary-subtle text-secondary-emphasis">' + (value || 0) + '</span>';
    }

    function renderTotalNeto(value) {
        var monto = value || 0;
        return '<span class="fw-semibold text-success">$' + Number(monto).toLocaleString('en-US', { maximumFractionDigits: 0 }) + '</span>';
    }

    function renderEstado(data, type, row) {
        var cfg = BADGE_ESTADO[row.estado] || ['bg-secondary', 'bi-question-circle'];
        return '<span class="badge ' + cfg[0] + '"><i class="bi ' + cfg[1] + ' me-1"></i>' + escapeHtml(row.estado_display || row.estado) + '</span>';
    }

    function renderAcciones(data, type, row) {
        return '<button type="button" class="btn btn-outline-primary btn-sm py-0 px-2 btn-gestionar-periodo" ' +
            'data-uuid="' + escapeHtml(row.uuid) + '" title="Ver / Gestionar"><i class="bi bi-arrow-right-circle me-1"></i>Gestionar</button>';
    }

    var COLUMNS = [
        { data: 'periodo_mes', title: 'Período', render: function (v) { return renderPeriodo(v); } },
        { data: null, title: 'Vigencia', orderable: false, render: renderVigencia },
        { data: 'fecha_pago', title: 'Fecha de Pago' },
        { data: 'empleados_count', title: 'Empleados', orderable: false, render: function (v) { return renderEmpleadosCount(v); } },
        { data: 'total_neto_periodo', title: 'Total Neto', orderable: false, render: function (v) { return renderTotalNeto(v); } },
        { data: null, title: 'Estado', render: renderEstado },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
    ];

    function initTabla() {
        if (_tablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, TABLA_URL, COLUMNS, {
            pageLength: 20,
            order: [[0, 'desc']],
        });
        _tablaInicializada = true;
    }

    /**
     * empleados.module.js invoca init() al activarse el sub-tab "Periodos de
     * Nomina" -- initTabla() es idempotente (guard _tablaInicializada),
     * seguro llamarla tambien aqui (cubre el caso de que el tab estuviera
     * oculto cuando setup() corrio la primera vez).
     */
    function init() {
        initTabla();
    }

    function redraw() {}

    function reload() {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
        }
    }

    function attachTableListeners() {
        d.body.addEventListener('click', (ev) => {
            if (!ev.target.closest(TABLA_SELECTOR)) return;
            const btn = ev.target.closest('.btn-gestionar-periodo');
            if (!btn) return;
            ev.preventDefault();
            const uuid = btn.dataset.uuid;
            if (!uuid) return;
            w.Sintel.Empleados.PeriodoDetail?.open(uuid);
        });
    }

    function attachToolbarListeners() {
        const btnNuevo = d.getElementById('btn-nuevo-periodo');
        if (btnNuevo && !btnNuevo.dataset.bound) {
            btnNuevo.dataset.bound = '1';
            btnNuevo.addEventListener('click', () => {
                w.Sintel.Empleados.PeriodoEditor?.open();
            });
        }

        const selectEstado = d.getElementById('empleados-filtro-estado-periodo');
        if (selectEstado && !selectEstado.dataset.bound) {
            selectEstado.dataset.bound = '1';
            selectEstado.addEventListener('change', () => {
                if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
                    w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 5, selectEstado.value);
                }
            });
        }
    }

    function _init() {
        initTabla();
        attachTableListeners();
        attachToolbarListeners();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

    w.Sintel.Empleados.PeriodoList = { init, reload, redraw };

})(window, document);
