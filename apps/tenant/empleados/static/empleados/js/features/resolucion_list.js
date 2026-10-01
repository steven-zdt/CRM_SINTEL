// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Resolucion List Module — tabla "Resoluciones DIAN" (nomina electronica) es
 * DataTables 3.x (#tabla-resoluciones-empleados, mismo patron ya validado en
 * Ventas/Bancos/Facturas/Clientes/Proveedores/Compras/Gastos/Empleados -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via ajax
 * contra POST /api/v1/empleados/resoluciones-dian/dt/.
 * ResolucionDIANTable/ResolucionDIANTableView (django-tables2) retirados.
 * Namespace: window.Sintel.Empleados.ResolucionList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[ResolucionList]';
    const TABLA_SELECTOR = '#tabla-resoluciones-empleados';
    const TABLA_URL = '/api/v1/empleados/resoluciones-dian/dt/';
    let _tablaInicializada = false;

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderNumeroResolucion(value) {
        if (!value) return '<span class="text-muted">—</span>';
        return '<i class="bi bi-file-earmark-lock text-primary me-2"></i><span class="fw-semibold">' + escapeHtml(value) + '</span>';
    }

    function renderPrefijo(value) {
        if (!value) return '—';
        return '<span class="badge bg-secondary font-monospace">' + escapeHtml(value) + '</span>';
    }

    function renderRango(data, type, row) {
        var desde = Number(row.rango_desde || 0).toLocaleString('en-US');
        var hasta = Number(row.rango_hasta || 0).toLocaleString('en-US');
        return '<span class="font-monospace small">' + desde + ' – ' + hasta + '</span>';
    }

    function renderConsecutivo(data, type, row) {
        var pct = row.rango_hasta ? Math.round((row.consecutivo / row.rango_hasta) * 100) : 0;
        var cls = pct >= 90 ? 'text-danger fw-bold' : pct >= 70 ? 'text-warning fw-semibold' : 'text-success fw-semibold';
        return '<span class="' + cls + '">' + Number(row.consecutivo || 0).toLocaleString('en-US') + '</span>';
    }

    function renderVigencia(data, type, row) {
        return '<span class="small"><i class="bi bi-calendar-range text-muted me-1"></i>' +
            escapeHtml(row.fecha_inicio) + ' → ' + escapeHtml(row.fecha_fin) + '</span>';
    }

    function renderVigente(value) {
        if (value) return '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Vigente</span>';
        return '<span class="badge bg-secondary">Inactiva</span>';
    }

    function renderAcciones(data, type, row) {
        return '<button type="button" class="btn btn-outline-danger btn-sm py-0 px-2 btn-eliminar-resolucion" ' +
            'data-uuid="' + escapeHtml(row.uuid) + '" title="Eliminar"><i class="bi bi-trash"></i></button>';
    }

    var COLUMNS = [
        { data: 'numero_resolucion', title: 'Nro Resolución', render: function (v) { return renderNumeroResolucion(v); } },
        { data: 'prefijo', title: 'Prefijo', render: function (v) { return renderPrefijo(v); } },
        { data: null, title: 'Rango', orderable: false, render: renderRango },
        { data: null, title: 'Consecutivo', render: renderConsecutivo },
        { data: null, title: 'Vigencia', orderable: false, render: renderVigencia },
        { data: 'vigente', title: 'Estado', render: function (v) { return renderVigente(v); } },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
    ];

    function initTabla() {
        if (_tablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, TABLA_URL, COLUMNS, {
            pageLength: 20,
            order: [[5, 'desc']],
        });
        _tablaInicializada = true;
    }

    /**
     * empleados.module.js invoca init() al activarse el sub-tab "Resoluciones
     * DIAN" -- initTabla() es idempotente (guard _tablaInicializada), seguro
     * llamarla tambien aqui (cubre el caso de que el tab estuviera oculto
     * cuando setup() corrio la primera vez).
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

    async function _eliminar(uuid) {
        try {
            // T-9: delega a la SSoT de endpoints (empleados.api.js).
            const res = await w.Sintel.Core.Http.request('DELETE', w.Sintel.Empleados.API.resoluciones.detail(uuid));
            if (res.ok) {
                w.UIManager?.notifySuccess('Resolución eliminada correctamente');
                reload();
            } else {
                const msg = res.data?.detail || 'Error al eliminar la resolución';
                w.UIManager?.notifyError(msg);
            }
        } catch (err) {
            console.error(`${MOD} Error al eliminar:`, err);
            w.UIManager?.notifyError('Error de conexión al eliminar la resolución');
        }
    }

    function attachTableListeners() {
        d.body.addEventListener('click', async (ev) => {
            if (!ev.target.closest(TABLA_SELECTOR)) return;
            const btn = ev.target.closest('.btn-eliminar-resolucion');
            if (!btn) return;
            ev.preventDefault();
            const uuid = btn.dataset.uuid;
            if (!uuid) return;
            if (!(await w.UIManager?.confirm('¿Eliminar esta resolución DIAN? Esta acción no se puede deshacer.'))) return;
            _eliminar(uuid);
        });
    }

    function setup() {
        initTabla();
        attachTableListeners();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

    w.Sintel.Empleados.ResolucionList = { init, reload, redraw };

})(window, document);
