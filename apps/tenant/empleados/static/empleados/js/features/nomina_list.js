// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Nomina List Module — Master-Detail.
 *
 * Panel Izquierdo (Master, #tabla-nomina-master): empleados con nominas, es
 * DataTables 3.x (mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos/Empleados -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblado via ajax
 * contra POST /api/v1/empleados/con-nominas/dt/
 * (EmpleadoViewSet.con_nominas_dt()). NominaEmpleadoMasterTable/
 * NominaMasterTableView (django-tables2) retirados. Cada fila lleva
 * data-empleado-uuid (ver createdRow) -- el click en una fila carga el
 * panel Detail (sin usar row_attrs de django-tables2, que ya no aplica).
 *
 * Panel Derecho (Detail, #nomina-detail-panel): historico de nominas del
 * empleado seleccionado (header + tabla, ambos renderizados server-side
 * juntos en cada click porque el header depende del empleado) -- sigue en
 * django-tables2 + HTMX, no es un listado plano independiente.
 *
 * Namespace: window.Sintel.Empleados.NominaList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const TABLA_MASTER_SELECTOR = '#tabla-nomina-master';
    const TABLA_MASTER_URL = '/api/v1/empleados/con-nominas/dt/';
    const DETAIL_PANEL = '#nomina-detail-panel';
    let _masterTablaInicializada = false;

    let empleadoActivoUuid = null;

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderEmpleado(data, type, row) {
        var nombre = (row.primer_nombre + ' ' + row.primer_apellido).trim();
        var total = row.total_nominas || 0;
        return '<div class="d-flex align-items-start justify-content-between gap-1 py-1">' +
            '<div class="lh-sm"><div class="fw-semibold small">' + escapeHtml(nombre) + '</div>' +
            '<div class="text-muted" style="font-size:.72rem;"><code>' + escapeHtml(row.numero_documento || '') + '</code></div></div>' +
            '<span class="badge bg-primary-subtle text-primary border border-primary-subtle flex-shrink-0 mt-1">' + total + '</span>' +
            '</div>';
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
                tr.classList.add('fila-master-nomina');
                tr.style.cursor = 'pointer';
            },
        });
        _masterTablaInicializada = true;
    }

    /**
     * empleados.module.js invoca init() al activarse el sub-tab "Nominas" --
     * initMasterTabla() es idempotente (guard _masterTablaInicializada),
     * seguro llamarla tambien aqui.
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
            const detailPanel = d.querySelector(DETAIL_PANEL);
            if (detailPanel) {
                w.htmx.ajax('GET', `/ui/empleados/nominas/detalle/tabla/?empleado_uuid=${empleadoActivoUuid}`, {
                    target: DETAIL_PANEL,
                    swap: 'innerHTML',
                });
            }
        }
    }

    function getEmpleadoSeleccionado() {
        return empleadoActivoUuid ? { uuid: empleadoActivoUuid } : null;
    }

    // ── Seleccion de fila en el Master: resaltado visual + carga del Detail ──

    function attachMasterListeners() {
        d.body.addEventListener('click', (ev) => {
            const row = ev.target.closest(TABLA_MASTER_SELECTOR + ' tbody tr[data-empleado-uuid]');
            if (!row) return;
            d.querySelectorAll(TABLA_MASTER_SELECTOR + ' .fila-master-nomina').forEach((r) => r.classList.remove('table-active', 'fw-bold'));
            row.classList.add('table-active', 'fw-bold');
            empleadoActivoUuid = row.dataset.empleadoUuid || null;
            if (empleadoActivoUuid && w.htmx) {
                w.htmx.ajax('GET', `/ui/empleados/nominas/detalle/tabla/?empleado_uuid=${empleadoActivoUuid}`, {
                    target: DETAIL_PANEL,
                    swap: 'innerHTML',
                });
            }
        });
    }

    // ── Acciones del Detail (nueva nomina / anular) ──────────────────────────

    async function anularDevengo(uuid) {
        if (!uuid) return;
        if (!(await w.UIManager?.confirm('¿Confirma anular esta nómina? La operación no puede revertirse.'))) return;
        try {
            // T-9: delega a la SSoT de endpoints (empleados.api.js).
            const resp = await w.Sintel.Core.Http.request('POST', w.Sintel.Empleados.API.devengos.anular(uuid));
            if (resp.ok) {
                w.UIManager?.notifySuccess('Nómina anulada correctamente');
                reload();
            } else {
                w.UIManager?.handleError(resp);
            }
        } catch (err) {
            console.error('[NominaList] Error anulando:', err);
            w.UIManager?.notifyError('Error al anular la nómina');
        }
    }

    // feature 2026-09-10: "Ver" detalle de una nomina (solo lectura) --
    // mismo patron ya probado en liquidacion_list.js/abrirDetalleLiquidacion.
    function abrirDetalleNomina(uuid) {
        const url = `/api/v1/empleados/devengos/${uuid}/render-offcanvas/detalle/`;
        const container = d.getElementById('offcanvas-container-nominas');
        if (!container) {
            console.error('[NominaList] No se encontro #offcanvas-container-nominas');
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

    function attachDetailListeners() {
        const panel = d.querySelector(DETAIL_PANEL);
        if (!panel) return;

        panel.addEventListener('click', (ev) => {
            const btnNueva = ev.target.closest('.btn-nueva-nomina-header');
            if (btnNueva) {
                ev.preventDefault();
                const uuid = btnNueva.dataset.empleadoUuid;
                const nombre = btnNueva.dataset.empleadoNombre;
                w.Sintel?.Empleados?.DevengoEditor?.openParaEmpleado?.(uuid, nombre);
                return;
            }

            const btnVer = ev.target.closest('.btn-ver-nomina');
            if (btnVer) {
                ev.preventDefault();
                abrirDetalleNomina(btnVer.dataset.uuid);
                return;
            }

            const btnAnular = ev.target.closest('.btn-anular-nomina');
            if (btnAnular) {
                ev.preventDefault();
                anularDevengo(btnAnular.dataset.uuid);
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

    w.Sintel.Empleados.NominaList = { init, reload, redraw, anularDevengo, getEmpleadoSeleccionado };

})(window, document);
