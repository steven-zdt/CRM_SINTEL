// @ts-nocheck
/**
 * Nomina Historial Module - Feature: Historial de Nóminas
 * ⚠️ Feature-Sliced Architecture v2.61.8
 *
 * Namespace: window.Sintel.Empleados.NominaHistorial
 */
(function(w, d) {
    'use strict';

    const MOD = '[NominaHistorial]';
    const API_BASE = '/api/v1/empleados/';
    const CONTAINER_ID = 'offcanvas-container-nominas';

    const COP = (val) => {
        const n = parseFloat(val) || 0;
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP', minimumFractionDigits: 0
        }).format(n);
    };
    const monedaCelda = (cell) => COP(cell.getValue());

    /**
     * Abrir historial de nóminas
     */
    async function open(empleadoId) {
        if (!empleadoId) {
            console.error(`${MOD} ID de empleado no proporcionado`);
            return;
        }
        
        const url = `${API_BASE}${empleadoId}/historial-nominas/`;
        
        console.log(`${MOD} Cargando historial: ${url}`);
        
        try {
            await htmx.ajax('GET', url, {
                target: `#${CONTAINER_ID}`,
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al cargar historial de nóminas');
        }
    }

    /**
     * Listener para activar offcanvas tras inyección HTMX
     */
    function setupOffcanvasLoadListener() {
        document.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail.target;
            if (!target || target.id !== CONTAINER_ID) return;

            const offcanvasEl = target.querySelector('#offcanvas-historial-nominas');
            if (offcanvasEl && window.bootstrap) {
                console.log(`${MOD} Activando offcanvas: ${offcanvasEl.id}`);
                // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (AGENTS.md §26 — nunca getOrCreateInstance)
                window.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);

                // Inicializar tabla después de que el offcanvas esté visible
                const empleadoId = offcanvasEl.dataset.empleadoId; // Asumimos que viene en el data-attribute
                setTimeout(() => initTable(empleadoId), 300);
            }
        });
    }

    /**
     * Inicializar tabla Tabulator
     */
    function initTable(empleadoId) {
        const gridEl = d.querySelector('#grid-historial-nominas');
        if (!gridEl || !w.TabulatorFactory) return;

        const url = `${API_BASE}devengos/?empleado=${empleadoId}`;
        
        const columns = [
            {
                title: 'Período',
                field: 'fecha_inicio',
                width: 190,
                hozAlign: 'center',
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const fi = data.fecha_inicio;
                    const ff = data.fecha_fin;
                    if (fi && ff) {
                        return `<div class="small lh-sm fw-semibold">${fi}</div>
                                <div class="small text-muted lh-sm">al ${ff}</div>`;
                    }
                    return `<span class="small">${data.periodo_mes || '—'}</span>`;
                }
            },
            {
                title: 'Días',
                field: 'dias_laborados',
                width: 65,
                hozAlign: 'center',
                formatter: (cell) => {
                    const v = parseFloat(cell.getValue()) || 0;
                    return `<span class="badge bg-primary-subtle text-primary border border-primary-subtle">${v}</span>`;
                }
            },
            {
                title: 'Fecha Pago',
                field: 'fecha_pago',
                width: 130,
                hozAlign: 'center',
                formatter: (cell) => {
                    const val = cell.getValue();
                    return val ? new Date(val + 'T00:00:00').toLocaleDateString('es-CO') : '—';
                }
            },
            {
                title: 'Salario Base',
                field: 'salario_base',
                width: 140,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: monedaCelda,
            },
            {
                title: 'H.E. y Recargos',
                field: 'valor_horas_extras',
                width: 120,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: (cell) => {
                    const v = parseFloat(cell.getValue()) || 0;
                    return v > 0
                        ? `<span class="text-warning fw-semibold">${COP(v)}</span>`
                        : '<span class="text-muted">—</span>';
                }
            },
            {
                title: 'Neto a Pagar',
                field: 'neto_pagar',
                width: 140,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: (cell) => {
                    const data    = cell.getRow().getData();
                    const anulado = data.anulado;
                    if (anulado) {
                        return `<span class="text-decoration-line-through text-muted small">${COP(cell.getValue())}</span>
                                <span class="badge bg-danger ms-1">Anulada</span>`;
                    }
                    return `<strong class="text-success">${COP(cell.getValue())}</strong>`;
                }
            },
            {
                title: 'Estado',
                field: 'anulado',
                width: 90,
                hozAlign: 'center',
                formatter: (cell) => cell.getValue()
                    ? '<span class="badge bg-danger">Anulado</span>'
                    : '<span class="badge bg-success">Activo</span>'
            },
            {
                title: 'Acciones',
                width: 80,
                hozAlign: 'center',
                headerSort: false,
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    if (data.anulado) return '—';
                    return `<button class="btn btn-sm btn-outline-danger"
                                    onclick="window.Sintel.Empleados.NominaHistorial.anular('${data.uuid}')"
                                    title="Anular nómina">
                                <i class="bi bi-slash-circle"></i>
                            </button>`;
                }
            }
        ];

        const table = w.TabulatorFactory.create('#grid-historial-nominas', url, columns, {
            pagination: false,
            ajaxParams: { page_size: 200 }
        });

        // Guardar referencia
        w.Sintel.Empleados.NominaHistorial._table = table;
    }

    /**
     * Anular nómina
     */
    async function anular(id) {
        if (!(await w.UIManager?.confirm('¿Está seguro de que desea anular esta nómina?'))) return;

        try {
            const resp = await w.Sintel.Core.Http.request('POST', `${API_BASE}devengos/${id}/anular/`);
            if (resp.ok) {
                window.UIManager?.notifySuccess('Nómina anulada correctamente');
                w.Sintel.Empleados.NominaHistorial._table?.replaceData();
                window.Sintel.Empleados.EmpleadoList?.reload();
            } else {
                window.UIManager?.handleError(resp);
            }
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al anular nómina');
        }
    }

    // Inicializar listeners
    setupOffcanvasLoadListener();

    // Exportar
    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};
    window.Sintel.Empleados.NominaHistorial = {
        open,
        openHistorial: open,
        anular
    };

    // Alias legacy
    window.HistorialNominas = window.Sintel.Empleados.NominaHistorial;

})(window, document);
