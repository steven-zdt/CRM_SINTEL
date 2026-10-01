// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * Empleado List Module — tabla "Empleados" (directorio) es DataTables 3.x
 * (#tabla-empleados, mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via ajax
 * contra POST /api/v1/empleados/dt/. EmpleadoTable/EmpleadoTableView
 * (django-tables2) retirados. Contratos/Resoluciones/Nominas/Liquidaciones
 * siguen en django-tables2/HTMX -- no migradas en esta pasada.
 * Namespace: window.Sintel.Empleados.EmpleadoList
 *
 * Este archivo maneja: init de la tabla, acciones de fila
 * (ver/editar/eliminar), y el resumen de estadisticas (panel-resumen-empleados,
 * endpoint JSON aparte -- no es una grilla y no cambia con esta migracion).
 */
(function (w, d) {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};

    const TABLA_EMPLEADOS_SELECTOR = '#tabla-empleados';
    const TABLA_EMPLEADOS_URL = '/api/v1/empleados/dt/';
    let _empleadosTablaInicializada = false;

    let empleadoIdEliminar = null;

    var BADGE_ESTADO_EMPLEADO = { ACTIVO: ['bg-success', 'bi-check-circle'], RETIRADO: ['bg-danger', 'bi-x-circle'] };

    function escapeHtmlEmpleado(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderFotoEmpleado(data, type, row) {
        if (row.foto_url) {
            return '<img src="' + escapeHtmlEmpleado(row.foto_url) + '" alt="" style="width:36px;height:36px;border-radius:50%;object-fit:cover;border:2px solid #dee2e6;">';
        }
        var iniciales = ((row.primer_nombre || '?').slice(0, 1) + (row.primer_apellido || '').slice(0, 1)).toUpperCase() || '?';
        var color = row.estado === 'RETIRADO' ? '#adb5bd' : '#0d6efd';
        return '<div style="width:36px;height:36px;border-radius:50%;background:' + color + '20;' +
            'border:2px solid ' + color + '40;display:flex;align-items:center;justify-content:center;' +
            'font-size:.75rem;font-weight:700;color:' + color + ';">' + escapeHtmlEmpleado(iniciales) + '</div>';
    }

    function renderNombreEmpleado(data, type, row) {
        var nombre = (row.primer_nombre + ' ' + row.primer_apellido).trim();
        var doc = row.numero_documento ? '<div class="small text-muted">' + escapeHtmlEmpleado(row.numero_documento) + '</div>' : '';
        return '<div class="fw-semibold lh-sm">' + escapeHtmlEmpleado(nombre) + '</div>' + doc;
    }

    function renderEstadoEmpleado(value) {
        var cfg = BADGE_ESTADO_EMPLEADO[value] || ['bg-secondary', ''];
        var icon = cfg[1] ? '<i class="bi ' + cfg[1] + ' me-1"></i>' : '';
        return '<span class="badge ' + cfg[0] + '">' + icon + escapeHtmlEmpleado(value || 'N/A') + '</span>';
    }

    function renderCargoEmpleado(value) {
        if (!value) return '<span class="text-muted">—</span>';
        return '<i class="bi bi-briefcase text-info me-1"></i><span>' + escapeHtmlEmpleado(value) + '</span>';
    }

    function renderContactoEmpleado(data, type, row) {
        var filas = [];
        if (row.email) filas.push('<i class="bi bi-envelope text-info me-1"></i><span class="small">' + escapeHtmlEmpleado(row.email) + '</span>');
        if (row.telefono) filas.push('<i class="bi bi-telephone text-success me-1"></i><span class="small">' + escapeHtmlEmpleado(row.telefono) + '</span>');
        return filas.length ? filas.join('<br>') : '<span class="text-muted">—</span>';
    }

    function renderAccionesEmpleado(data, type, row) {
        var nombre = (row.primer_nombre + ' ' + row.primer_apellido).trim();
        return '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-info btn-ver-empleado" data-uuid="' + escapeHtmlEmpleado(row.uuid) + '" title="Ver detalle"><i class="bi bi-eye"></i></button>' +
            '<button type="button" class="btn btn-outline-primary btn-editar-empleado" data-uuid="' + escapeHtmlEmpleado(row.uuid) + '" title="Editar empleado"><i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn btn-outline-danger btn-eliminar-empleado" data-uuid="' + escapeHtmlEmpleado(row.uuid) + '" data-nombre="' + escapeHtmlEmpleado(nombre) + '" data-doc="' + escapeHtmlEmpleado(row.numero_documento || '') + '" title="Eliminar permanentemente"><i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    var EMPLEADOS_COLUMNS = [
        { data: null, title: '', orderable: false, searchable: false, render: renderFotoEmpleado },
        { data: null, title: 'Empleado', render: renderNombreEmpleado },
        { data: 'estado', title: 'Estado', render: renderEstadoEmpleado },
        { data: 'fecha_ingreso', title: 'Ingreso' },
        { data: 'cargo', title: 'Cargo', orderable: false, render: renderCargoEmpleado },
        { data: null, title: 'Contacto', orderable: false, searchable: false, render: renderContactoEmpleado },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccionesEmpleado },
    ];

    function initEmpleadosTabla() {
        if (_empleadosTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_EMPLEADOS_SELECTOR, TABLA_EMPLEADOS_URL, EMPLEADOS_COLUMNS, {
            pageLength: 20,
            order: [[1, 'asc']],
        });
        _empleadosTablaInicializada = true;
    }

    /**
     * empleados.module.js invoca init() al activarse el sub-tab "Empleados"
     * -- initEmpleadosTabla() es idempotente (guard _empleadosTablaInicializada),
     * asi que es seguro llamarla aqui tambien (cubre el caso de que el tab
     * estuviera oculto -- display:none -- cuando setup() corrio la primera vez).
     */
    function init() {
        initEmpleadosTabla();
        loadSummary('#panel-resumen-empleados');
    }

    function reload() {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_EMPLEADOS_SELECTOR);
        }
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
                        : new Intl.NumberFormat('en-US', {
                            style: 'currency', currency: 'USD', minimumFractionDigits: 0
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
        d.body.addEventListener('click', (ev) => {
            if (!ev.target.closest(TABLA_EMPLEADOS_SELECTOR)) return;

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
                confirmarEliminar(uuid, btnEliminar.dataset.nombre || '', btnEliminar.dataset.doc || '');
            }
        });
    }

    function setup() {
        initEmpleadosTabla();
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
