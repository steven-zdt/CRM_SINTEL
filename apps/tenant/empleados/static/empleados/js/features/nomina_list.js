// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Nomina List Module — Master-Detail, Fase 5-BIS: tablas server-rendered via
 * django-tables2 + HTMX.
 *
 * Panel Izquierdo (Master, #nomina-master-panel): empleados con nominas,
 * cada fila lleva hx-get/hx-target (via row_attrs en tables.py) que carga
 * el panel Detail al hacer click -- no requiere JS para la carga en si,
 * solo para el resaltado visual de la fila activa.
 * Panel Derecho (Detail, #nomina-detail-panel): historico de nominas del
 * empleado seleccionado (header + tabla, ambos renderizados server-side
 * juntos en cada click porque el header depende del empleado).
 *
 * Namespace: window.Sintel.Empleados.NominaList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MASTER_PANEL = '#nomina-master-panel';
    const DETAIL_PANEL = '#nomina-detail-panel';

    let empleadoActivoUuid = null;

    // init()/redraw() ya no inicializan nada (los paneles HTMX se auto-cargan);
    // se conservan porque empleados.module.js las invoca al activar el sub-tab.
    function init() {}
    function redraw() {}

    function reload() {
        d.body.dispatchEvent(new CustomEvent('nomina-updated'));
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

    // ── Resaltado visual de la fila activa en el Master ──────────────────────

    function attachMasterListeners() {
        const panel = d.querySelector(MASTER_PANEL);
        if (!panel) return;

        panel.addEventListener('click', (ev) => {
            const row = ev.target.closest('.fila-master-nomina');
            if (!row) return;
            panel.querySelectorAll('.fila-master-nomina').forEach((r) => r.classList.remove('table-active', 'fw-bold'));
            row.classList.add('table-active', 'fw-bold');
            empleadoActivoUuid = row.dataset.empleadoUuid || null;
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
