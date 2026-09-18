// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Liquidacion List Module — Master-Detail, Fase 5-BIS: tablas server-rendered
 * via django-tables2 + HTMX.
 *
 * Panel Izquierdo (Master, #liq-master-panel): TODOS los empleados, cada fila
 * lleva hx-get/hx-target (via row_attrs en tables.py) que carga el panel
 * Detail al hacer click -- no requiere JS para la carga en si, solo para el
 * resaltado visual de la fila activa.
 * Panel Derecho (Detail, #liq-detail-panel-content): historico de
 * liquidaciones del empleado seleccionado (header + filtros por tipo + tabla,
 * renderizados juntos server-side en cada click/cambio de filtro).
 *
 * Namespace: window.Sintel.Empleados.LiquidacionList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[LiquidacionList]';
    const API_BASE = '/api/v1/empleados/liquidaciones-prestaciones/';
    const MASTER_PANEL = '#liq-master-panel';
    const DETAIL_PANEL = '#liq-detail-panel-content';

    let empleadoActivoUuid = null;

    // init()/redraw() ya no inicializan nada (los paneles HTMX se auto-cargan);
    // se conservan porque empleados.module.js las invoca al activar el sub-tab.
    function init() {}
    function redraw() {}

    function reload() {
        d.body.dispatchEvent(new CustomEvent('liquidacion-updated'));
        if (empleadoActivoUuid && w.htmx) {
            w.htmx.ajax('GET', `/ui/empleados/liquidaciones/detalle/tabla/?empleado_uuid=${empleadoActivoUuid}`, {
                target: DETAIL_PANEL,
                swap: 'innerHTML',
            });
        }
    }

    // ── Resaltado visual de la fila activa en el Master ──────────────────────

    function attachMasterListeners() {
        const panel = d.querySelector(MASTER_PANEL);
        if (!panel) return;

        panel.addEventListener('click', (ev) => {
            const row = ev.target.closest('.fila-master-liquidacion');
            if (!row) return;
            panel.querySelectorAll('.fila-master-liquidacion').forEach((r) => r.classList.remove('table-active', 'fw-bold'));
            row.classList.add('table-active', 'fw-bold');
            empleadoActivoUuid = row.dataset.empleadoUuid || null;
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
