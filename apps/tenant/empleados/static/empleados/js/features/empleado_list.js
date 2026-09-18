// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Empleado List Module — Fase 5-BIS: tabla server-rendered via
 * django-tables2 + HTMX (#empleados-panel, cargada por atributos
 * hx-get/hx-trigger declarados en empleados_list.html).
 * Namespace: window.Sintel.Empleados.EmpleadoList
 *
 * Este archivo maneja: acciones de fila (ver/editar/eliminar), el resumen
 * de estadisticas (panel-resumen-empleados, endpoint JSON aparte -- no es
 * una grilla y no cambia con esta migracion), y el evento que hace que
 * HTMX vuelva a pedir la tabla al backend tras una mutacion.
 */
(function (w, d) {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};

    const PANEL_SELECTOR = '#empleados-panel';

    let empleadoIdEliminar = null;

    /**
     * init()/reload() -- ya no inicializan Tabulator (el panel HTMX se
     * auto-carga con hx-trigger="load"); se conservan porque
     * empleados.module.js las invoca al activarse el sub-tab.
     */
    function init() {
        loadSummary('#panel-resumen-empleados');
    }

    function reload() {
        d.body.dispatchEvent(new CustomEvent('empleado-updated'));
    }

    /**
     * Cargar resumen de empleados usando window.http
     */
    async function loadSummary(selector) {
        const element = document.querySelector(selector);
        if (!element) return;

        const url = window.Sintel.Empleados.API.empleados.summary;

        try {
            const res = await window.Sintel.Core.Http.request('GET', url);
            if (res.ok) {
                const data = res.data;

                const totalEmpEl = document.getElementById('total-empleados');
                const activosEl = document.getElementById('total-contratos-activos');
                const nominasEl = document.getElementById('total-nominas');
                const costoEl = document.getElementById('costo-nomina-mes');

                if (totalEmpEl) totalEmpEl.textContent = data.total_empleados || 0;
                if (activosEl) activosEl.textContent = data.empleados_activos || 0;
                if (nominasEl) nominasEl.textContent = data.empleados_pagados || 0;
                if (costoEl) {
                    const val = parseFloat(data.total_nomina_mes) || 0;
                    // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
                    costoEl.textContent = (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
                        ? w.DOMUtils.formatCurrency(val, { minimumFractionDigits: 0 })
                        : new Intl.NumberFormat('es-CO', {
                            style: 'currency', currency: 'COP', minimumFractionDigits: 0
                        }).format(val);
                }
            } else {
                throw new Error(res.data?.detail || 'Error cargando resumen');
            }
        } catch (err) {
            console.error('[EmpleadoList] Error cargando summary:', err);
        }
    }

    /**
     * Ver detalle de empleado cargando el offcanvas en modo lectura
     */
    async function verDetalle(uuid) {
        if (!uuid) return;
        const apiUrl = window.Sintel?.Empleados?.API?.empleados?.gestorOffcanvas || '/api/v1/empleados/gestor-offcanvas/';
        const url = `${apiUrl}?tipo=empleado&mode=ver&uuid=${uuid}`;
        const containerId = 'offcanvas-container-empleados';

        try {
            await htmx.ajax('GET', url, {
                target: `#${containerId}`,
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error('[EmpleadoList] Error al cargar detalle:', error);
            if (window.UIManager) {
                window.UIManager.notifyError('Error al cargar el detalle del empleado');
            }
        }
    }

    /**
     * Mostrar modal de confirmacion para eliminar.
     */
    function confirmarEliminar(uuid, nombre, doc) {
        empleadoIdEliminar = uuid;

        const modalBody = document.querySelector('#confirmarEliminarModal .modal-body');
        if (modalBody) {
            modalBody.innerHTML = `
                <p class="mb-2">Esta a punto de eliminar permanentemente al empleado:</p>
                <div class="alert alert-warning py-2 mb-3">
                    <strong>${nombre || 'Empleado'}</strong>
                    ${doc ? `<span class="text-muted ms-2">Doc: ${doc}</span>` : ''}
                </div>
                <p class="text-danger mb-1"><strong>Esta accion eliminara en cascada:</strong></p>
                <ul class="text-danger small mb-3">
                    <li>Todos sus contratos</li>
                    <li>Todos sus registros de nomina</li>
                </ul>
                <p class="text-danger fw-bold mb-0">Esta accion no se puede deshacer.</p>
            `;
        }

        const modalElement = document.getElementById('confirmarEliminarModal');
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        }
    }

    /**
     * Ejecutar eliminacion del empleado usando window.http
     */
    async function ejecutarEliminar() {
        if (!empleadoIdEliminar) return;

        const url = window.Sintel.Empleados.API.empleados.detail(empleadoIdEliminar);

        try {
            const res = await window.Sintel.Core.Http.request('DELETE', url);
            if (res.ok) {
                const modalEl = document.getElementById('confirmarEliminarModal');
                if (modalEl) {
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                }

                if (window.UIManager) {
                    window.UIManager.notifySuccess('Empleado eliminado correctamente');
                }

                reload();
                loadSummary('#panel-resumen-empleados');
            } else {
                let errorMsg = 'Error al eliminar empleado';
                if (res.data) {
                    const detail = res.data.error || res.data.detail;
                    if (detail) {
                        errorMsg = Array.isArray(detail) ? detail.join(', ') : (typeof detail === 'object' ? JSON.stringify(detail) : String(detail));
                    } else if (typeof res.data === 'object') {
                        errorMsg = JSON.stringify(res.data);
                    } else if (typeof res.data === 'string') {
                        errorMsg = res.data;
                    }
                }
                throw new Error(errorMsg);
            }
        } catch (err) {
            console.error('[EmpleadoList] Error eliminando:', err);
            if (window.UIManager) {
                window.UIManager.notifyError(err.message || 'Error al eliminar empleado');
            }
        } finally {
            empleadoIdEliminar = null;
        }
    }

    function editar(id) {
        if (window.Sintel.Empleados.EmpleadoEditor) {
            window.Sintel.Empleados.EmpleadoEditor.open(id);
        } else {
            console.error('[EmpleadoList] EmpleadoEditor no cargado');
        }
    }

    function crear() {
        if (window.Sintel.Empleados.EmpleadoEditor) {
            window.Sintel.Empleados.EmpleadoEditor.open();
        } else {
            console.error('[EmpleadoList] EmpleadoEditor no cargado');
        }
    }

    // ── Acciones de fila (delegado sobre el panel persistente) ──────────────

    function attachTableListeners() {
        const panel = d.querySelector(PANEL_SELECTOR);
        if (!panel) return;

        panel.addEventListener('click', (ev) => {
            const btnVer = ev.target.closest('.btn-ver-empleado');
            const btnEditar = ev.target.closest('.btn-editar-empleado');
            const btnEliminar = ev.target.closest('.btn-eliminar-empleado');

            if (btnVer) {
                ev.preventDefault();
                const uuid = btnVer.dataset.uuid;
                if (uuid) verDetalle(uuid);
                return;
            }

            if (btnEditar) {
                ev.preventDefault();
                const uuid = btnEditar.dataset.uuid;
                if (uuid) editar(uuid);
                return;
            }

            if (btnEliminar) {
                ev.preventDefault();
                const uuid = btnEliminar.dataset.uuid;
                if (!uuid) return;
                const row = btnEliminar.closest('tr');
                const nombre = row?.querySelector('.fw-semibold.lh-sm')?.textContent?.trim() || '';
                const doc = row?.querySelector('.small.text-muted')?.textContent?.trim() || '';
                confirmarEliminar(uuid, nombre, doc);
            }
        });
    }

    function setup() {
        attachTableListeners();

        const btnConfirmar = document.getElementById('btn-confirmar-eliminar');
        if (btnConfirmar && !btnConfirmar.dataset.bound) {
            btnConfirmar.dataset.bound = '1';
            btnConfirmar.addEventListener('click', ejecutarEliminar);
        }
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

    // Exportar modulo
    window.Sintel.Empleados.EmpleadoList = {
        init,
        reload,
        loadSummary,
        editar,
        verDetalle,
        crear,
        confirmarEliminar,
        ejecutarEliminar
    };

})(window, document);
