// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Contrato List Module — tabla "Contratos" es DataTables 3.x (#tabla-contratos,
 * mismo patron ya validado en Ventas/Bancos/Facturas/Clientes/Proveedores/
 * Compras/Gastos/Empleados -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md),
 * poblada via ajax contra POST /api/v1/empleados/contratos/dt/.
 * ContratoTable/ContratoTableView (django-tables2) retirados.
 * Namespace: window.Sintel.Empleados.ContratoList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[ContratoList]';
    const TABLA_SELECTOR = '#tabla-contratos';
    const TABLA_URL = '/api/v1/empleados/contratos/dt/';
    const API = () => w.Sintel.Empleados.API;
    let _tablaInicializada = false;

    var BADGE_TIPO = {
        INDEFINIDO: ['bg-success', 'bi-infinite'],
        FIJO: ['bg-primary', 'bi-hourglass'],
        OBRA: ['bg-warning text-dark', 'bi-briefcase'],
        PRESTACION: ['bg-secondary', 'bi-person-check'],
    };
    var BADGE_ESTADO = {
        ACTIVO: ['bg-success', 'bi-check-circle'],
        INACTIVO: ['bg-danger', 'bi-pause-circle'],
        HISTORICO: ['bg-secondary', ''],
        CANCELADO: ['bg-dark', 'bi-x-circle'],
    };

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderEmpleado(data, type, row) {
        if (!row.empleado) return '<span class="text-muted">—</span>';
        return '<i class="bi bi-person text-primary me-2"></i><span class="fw-semibold">' +
            escapeHtml(row.empleado_nombre || '') + '</span>';
    }

    function renderTipo(data, type, row) {
        var cfg = BADGE_TIPO[row.tipo] || ['bg-secondary', ''];
        var icon = cfg[1] ? '<i class="bi ' + cfg[1] + '"></i> ' : '';
        return '<span class="badge ' + cfg[0] + ' px-2">' + icon + escapeHtml(row.tipo_display || row.tipo) + '</span>';
    }

    function renderFechaFin(data, type, row) {
        if (row.tipo === 'INDEFINIDO' || !row.fecha_fin) {
            return '<span class="badge bg-light text-dark"><i class="bi bi-infinite me-1"></i>Indefinido</span>';
        }
        return '<i class="bi bi-calendar-x text-danger me-1"></i><span class="small">' + escapeHtml(row.fecha_fin) + '</span>';
    }

    function renderSalario(value) {
        if (!value) return '<span class="text-muted">—</span>';
        var formatted = (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(value) : ('$' + Number(value).toLocaleString('en-US'));
        return '<span class="text-success fw-semibold"><i class="bi bi-cash-coin me-1"></i>' + formatted + '</span>';
    }

    function renderEstado(data, type, row) {
        var cfg = BADGE_ESTADO[row.estado] || ['bg-secondary', ''];
        var icon = cfg[1] ? '<i class="bi ' + cfg[1] + ' me-1"></i>' : '';
        return '<span class="badge ' + cfg[0] + ' px-2">' + icon + escapeHtml(row.estado_display || row.estado) + '</span>';
    }

    function renderAcciones(data, type, row) {
        var botones = '<button type="button" class="btn btn-outline-secondary btn-ver-contrato" data-uuid="' +
            escapeHtml(row.uuid) + '" title="Ver Detalle"><i class="bi bi-eye"></i></button>';
        if (row.estado === 'ACTIVO') {
            botones += '<button type="button" class="btn btn-outline-primary btn-editar-contrato" data-uuid="' +
                escapeHtml(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
                '<button type="button" class="btn btn-outline-danger btn-cancelar-contrato" data-uuid="' +
                escapeHtml(row.uuid) + '" title="Cancelar Contrato"><i class="bi bi-x-circle"></i></button>';
        }
        return '<div class="btn-group btn-group-sm">' + botones + '</div>';
    }

    var COLUMNS = [
        { data: null, title: 'Empleado', render: renderEmpleado },
        { data: null, title: 'Tipo Contrato', render: renderTipo },
        { data: 'fecha_inicio', title: 'Inicio' },
        { data: null, title: 'Fin', orderable: false, render: renderFechaFin },
        { data: 'salario_mensual', title: 'Salario', render: function (v) { return renderSalario(v); } },
        { data: null, title: 'Estado', render: renderEstado },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
    ];

    function initTabla() {
        if (_tablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, TABLA_URL, COLUMNS, {
            pageLength: 20,
            order: [[2, 'desc']],
        });
        _tablaInicializada = true;
    }

    /**
     * empleados.module.js invoca init() al activarse el sub-tab "Contratos"
     * -- initTabla() es idempotente (guard _tablaInicializada), seguro
     * llamarla tambien aqui (cubre el caso de que el tab estuviera oculto
     * -- display:none -- cuando setup() corrio la primera vez).
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

    // ── Cancelar Contrato ──────────────────────────────────────────────────────

    async function cancelarContrato(uuid) {
        if (!uuid) return;
        if (!(await w.UIManager?.confirm('Confirmar cancelacion del contrato. Esta accion no se puede deshacer.'))) return;

        const api = API();
        if (!api) return;

        try {
            const resp = await w.Sintel.Empleados.request(api.contratos.cancelar(uuid), {
                method: 'POST',
            });

            if (resp && resp.ok) {
                w.UIManager?.notifySuccess('Contrato cancelado correctamente');
                reload();
                w.Sintel.Empleados.EmpleadoList?.reload();
            } else {
                const msg = resp?.data?.error || resp?.data?.detail || 'Error al cancelar contrato';
                w.UIManager?.notifyError(msg);
            }
        } catch (err) {
            console.error(`${MOD} Error cancelando contrato:`, err);
            w.UIManager?.notifyError('Error de conexion al cancelar contrato');
        }
    }

    // ── Acciones de fila (delegado sobre document.body -- la tabla se recrea
    // via ajax.reload(), nunca via innerHTML swap de un contenedor) ─────────

    function attachTableListeners() {
        d.body.addEventListener('click', (ev) => {
            if (!ev.target.closest(TABLA_SELECTOR)) return;
            const btnVer = ev.target.closest('.btn-ver-contrato');
            const btnEditar = ev.target.closest('.btn-editar-contrato');
            const btnCancelar = ev.target.closest('.btn-cancelar-contrato');

            if (btnVer) {
                ev.preventDefault();
                const uuid = btnVer.dataset.uuid;
                if (uuid && w.Sintel.Empleados.ContratoEditor) {
                    w.Sintel.Empleados.ContratoEditor.openDetail(uuid);
                }
                return;
            }

            if (btnEditar) {
                ev.preventDefault();
                const uuid = btnEditar.dataset.uuid;
                if (uuid && w.Sintel.Empleados.ContratoEditor) {
                    w.Sintel.Empleados.ContratoEditor.open(null, uuid);
                }
                return;
            }

            if (btnCancelar) {
                ev.preventDefault();
                const uuid = btnCancelar.dataset.uuid;
                if (uuid) cancelarContrato(uuid);
            }
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

    w.Sintel.Empleados.ContratoList = { init, reload, redraw };

})(window, document);
