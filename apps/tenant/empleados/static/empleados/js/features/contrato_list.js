// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Contrato List Module — Fase 5-BIS: tabla server-rendered via
 * django-tables2 + HTMX (#contratos-panel, cargada por atributos
 * hx-get/hx-trigger declarados en empleados_list.html -- carga solo al
 * abrir el sub-tab de Contratos por primera vez).
 * Namespace: window.Sintel.Empleados.ContratoList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[ContratoList]';
    const PANEL_SELECTOR = '#contratos-panel';
    const API = () => w.Sintel.Empleados.API;

    // init()/redraw() ya no inicializan nada (el panel HTMX se auto-carga);
    // se conservan porque empleados.module.js las invoca al activar el sub-tab.
    function init() {}
    function redraw() {}

    function reload() {
        d.body.dispatchEvent(new CustomEvent('contrato-updated'));
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

    // ── Acciones de fila (delegado sobre el panel persistente) ──────────────

    function attachTableListeners() {
        const panel = d.querySelector(PANEL_SELECTOR);
        if (!panel) return;

        panel.addEventListener('click', (ev) => {
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

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', attachTableListeners);
    } else {
        attachTableListeners();
    }

    w.Sintel.Empleados.ContratoList = { init, reload, redraw };

})(window, document);
