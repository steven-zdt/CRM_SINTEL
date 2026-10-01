// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Liquidacion List Module — Master-Detail.
 *
 * Panel Izquierdo (Master, #tabla-liquidacion-master): TODOS los empleados,
 * es DataTables 3.x (mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos/Empleados -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblado via ajax
 * contra POST /api/v1/empleados/con-liquidaciones/dt/
 * (EmpleadoViewSet.con_liquidaciones_dt()). LiquidacionEmpleadoMasterTable/
 * LiquidacionMasterTableView (django-tables2) retirados. Cada fila lleva
 * data-empleado-uuid (ver createdRow) -- el click en una fila carga el
 * panel Detail.
 *
 * Panel Derecho (Detail, #liq-detail-panel-content): historico de
 * liquidaciones del empleado seleccionado (header + filtros por tipo +
 * tabla, renderizados juntos server-side en cada click/cambio de filtro) --
 * sigue en django-tables2 + HTMX, no es un listado plano independiente.
 *
 * Namespace: window.Sintel.Empleados.LiquidacionList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[LiquidacionList]';
    const API_BASE = '/api/v1/empleados/liquidaciones-prestaciones/';
    const TABLA_MASTER_SELECTOR = '#tabla-liquidacion-master';
    const TABLA_MASTER_URL = '/api/v1/empleados/con-liquidaciones/dt/';
    const DETAIL_PANEL = '#liq-detail-panel-content';
    let _masterTablaInicializada = false;

    let empleadoActivoUuid = null;

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderEmpleado(data, type, row) {
        var nombre = (row.primer_nombre + ' ' + row.primer_apellido).trim();
        var total = row.total_liquidaciones || 0;
        var cls = total > 0 ? 'bg-primary' : 'bg-secondary';
        return '<div class="fw-semibold text-truncate" style="font-size:.8rem;" title="' + escapeHtml(nombre) + '">' +
            '<i class="bi bi-person-fill text-info me-1"></i>' + escapeHtml(nombre) + '</div>' +
            '<div class="text-muted" style="font-size:.68rem;">' + escapeHtml(row.numero_documento || '') + '</div>' +
            '<span class="badge ' + cls + '" style="font-size:.7rem;">' + total + '</span>';
    }

    var COLUMNS = [
        { data: null, title: 'Empleado', orderable: false, render: renderEmpleado },
    ];

    function initMasterTabla() {
        if (_masterTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_MASTER_SELECTOR, TABLA_MASTER_URL, COLUMNS, {
            pageLength: 20,
            createdRow: function (tr, rowData) {
                tr.setAttribute('data-empleado-uuid', rowData.uuid);
                tr.classList.add('fila-master-liquidacion');
                tr.style.cursor = 'pointer';
            },
        });
        _masterTablaInicializada = true;
    }

    /**
     * empleados.module.js invoca init() al activarse el sub-tab
     * "Liquidaciones" -- initMasterTabla() es idempotente (guard
     * _masterTablaInicializada), seguro llamarla tambien aqui.
     */
    function init() {
        initMasterTabla();
    }

    function redraw() {}

    function reload() {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_MASTER_SELECTOR);
        }
        if (empleadoActivoUuid && w.htmx) {
            w.htmx.ajax('GET', `/ui/empleados/liquidaciones/detalle/tabla/?empleado_uuid=${empleadoActivoUuid}`, {
                target: DETAIL_PANEL,
                swap: 'innerHTML',
            });
        }
    }

    // ── Seleccion de fila en el Master: resaltado visual + carga del Detail ──

    function attachMasterListeners() {
        d.body.addEventListener('click', (ev) => {
            const row = ev.target.closest(TABLA_MASTER_SELECTOR + ' tbody tr[data-empleado-uuid]');
            if (!row) return;
            d.querySelectorAll(TABLA_MASTER_SELECTOR + ' .fila-master-liquidacion').forEach((r) => r.classList.remove('table-active', 'fw-bold'));
            row.classList.add('table-active', 'fw-bold');
            empleadoActivoUuid = row.dataset.empleadoUuid || null;
            if (empleadoActivoUuid && w.htmx) {
                w.htmx.ajax('GET', `/ui/empleados/liquidaciones/detalle/tabla/?empleado_uuid=${empleadoActivoUuid}`, {
                    target: DETAIL_PANEL,
                    swap: 'innerHTML',
                });
            }
        });
    }

    // ── Acciones del Detail (ver / eliminar / nueva liquidacion) ─────────────

    function abrirDetalleLiquidacion(uuid) {
        const url = `${API_BASE}${uuid}/render-offcanvas/detalle/`;
        const container = d.getElementById('offcanvas-container-liquidaciones');
        if (!container) {
            console.error(`${MOD} No se encontro #offcanvas-container-liquidaciones`);
            return;
        }
        w.htmx.ajax('GET', url, { target: container, swap: 'innerHTML' }).then(() => {
            const el = container.querySelector('.offcanvas');
            if (el) {
                // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (AGENTS.md §26 — nunca getOrCreateInstance)
                w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
            }
        });
    }

    async function eliminarLiquidacion(uuid) {
        try {
            // T-9: delega a la SSoT de endpoints (empleados.api.js).
            const res = await w.Sintel.Core.Http.request('DELETE', w.Sintel.Empleados.API.liquidaciones.detail(uuid));
            if (res.ok) {
                w.UIManager?.notifySuccess('Liquidacion eliminada');
                reload();
            } else {
                w.UIManager?.notifyError(res.data?.detail || 'Error al eliminar');
            }
        } catch (err) {
            console.error(`${MOD} Error al eliminar:`, err);
            w.UIManager?.notifyError('Error de conexion');
        }
    }

    function attachDetailListeners() {
        const panel = d.querySelector(DETAIL_PANEL);
        if (!panel) return;

        panel.addEventListener('click', async (ev) => {
            const btnNueva = ev.target.closest('.btn-nueva-liquidacion-header');
            if (btnNueva) {
                ev.preventDefault();
                const uuid = btnNueva.dataset.empleadoUuid;
                w.Sintel?.Empleados?.LiquidacionEditor?.open?.(uuid);
                return;
            }

            const btnVer = ev.target.closest('.btn-ver-liquidacion');
            if (btnVer) {
                ev.preventDefault();
                abrirDetalleLiquidacion(btnVer.dataset.uuid);
                return;
            }

            const btnEliminar = ev.target.closest('.btn-eliminar-liquidacion');
            if (btnEliminar) {
                ev.preventDefault();
                if (!(await w.UIManager?.confirm('Eliminar esta liquidacion? Esta accion no se puede deshacer.'))) return;
                eliminarLiquidacion(btnEliminar.dataset.uuid);
            }
        });
    }

    function setup() {
        initMasterTabla();
        attachMasterListeners();
        attachDetailListeners();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

    w.Sintel.Empleados.LiquidacionList = { init, reload, redraw };

})(window, document);
