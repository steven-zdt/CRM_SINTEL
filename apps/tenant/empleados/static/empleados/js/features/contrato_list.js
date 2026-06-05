// @ts-nocheck
/**
 * Contrato List Module - Tabla independiente de Contratos
 *
 * Namespace: window.Sintel.Empleados.ContratoList
 * Version: v3.10.1 - Migrado a TabulatorFactory (mismo patron que EmpleadoList)
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[ContratoList]';
    let table = null;
    const API = () => w.Sintel.Empleados.API;

    // ── Formatters ─────────────────────────────────────────────────────────────

    const COP = (val) => {
        const n = parseFloat(val) || 0;
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP', minimumFractionDigits: 0
        }).format(n);
    };

    const tipoBadge = (tipo) => {
        const map = {
            'INDEFINIDO':  'bg-success',
            'FIJO':        'bg-primary',
            'OBRA':        'bg-warning text-dark',
            'PRESTACION':  'bg-secondary',
        };
        return map[tipo] || 'bg-secondary';
    };

    const estadoBadge = (estado) => {
        const map = {
            'ACTIVO':    'bg-success',
            'INACTIVO':  'bg-danger',
            'HISTORICO': 'bg-secondary',
            'CANCELADO': 'bg-dark',
        };
        return map[estado] || 'bg-secondary';
    };

    // ── Acciones de celda ──────────────────────────────────────────────────────

    function handleCellAction(e, cell) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        const action  = btn.dataset.action;
        const uuid    = btn.dataset.uuid;

        switch (action) {
            case 'ver-detalle':
                if (w.Sintel.Empleados.ContratoEditor) {
                    w.Sintel.Empleados.ContratoEditor.openDetail(uuid);
                }
                break;
            case 'editar':
                if (w.Sintel.Empleados.ContratoEditor) {
                    w.Sintel.Empleados.ContratoEditor.open(null, uuid);
                }
                break;
            case 'cancelar':
                cancelarContrato(uuid);
                break;
            default:
                console.warn(`${MOD} Accion desconocida: ${action}`);
        }
    }

    // ── Columnas ───────────────────────────────────────────────────────────────

    function getColumnas() {
        return [
            {
                title: 'Empleado',
                field: 'empleado_nombre',
                minWidth: 180,
                headerFilter: 'input',
                formatter: (cell) => {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-person text-primary me-2"></i><span class="fw-semibold">${val}</span>`;
                },
            },
            {
                title: 'Tipo Contrato',
                field: 'tipo',
                width: 140,
                hozAlign: 'center',
                headerHozAlign: 'center',
                formatter: (cell) => {
                    const val  = cell.getValue() || '';
                    const disp = cell.getRow().getData().tipo_display || val;
                    const icon = val === 'INDEFINIDO' ? '<i class="bi bi-infinite"></i>' :
                                 val === 'FIJO' ? '<i class="bi bi-hourglass"></i>' :
                                 val === 'OBRA' ? '<i class="bi bi-briefcase"></i>' :
                                 val === 'PRESTACION' ? '<i class="bi bi-person-check"></i>' : '';
                    return `<span class="badge ${tipoBadge(val)} px-2">${icon} ${disp}</span>`;
                },
            },
            {
                title: 'Inicio',
                field: 'fecha_inicio',
                width: 110,
                hozAlign: 'center',
                formatter: (cell) => {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-calendar-event text-success me-1"></i><span class="small">${val}</span>`;
                },
            },
            {
                title: 'Fin',
                field: 'fecha_fin',
                width: 110,
                hozAlign: 'center',
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    if (data.tipo === 'INDEFINIDO' || !cell.getValue()) {
                        return '<span class="badge bg-light text-dark"><i class="bi bi-infinite me-1"></i>Indefinido</span>';
                    }
                    return `<i class="bi bi-calendar-x text-danger me-1"></i><span class="small">${cell.getValue()}</span>`;
                },
            },
            {
                title: 'Salario',
                field: 'salario_mensual',
                width: 140,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: (cell) => {
                    const val = cell.getValue();
                    if (!val || val === 0) return '<span class="text-muted">—</span>';
                    return `<span class="text-success fw-semibold"><i class="bi bi-cash-coin me-1"></i>${COP(val)}</span>`;
                },
            },
            {
                title: 'Estado',
                field: 'estado',
                width: 130,
                hozAlign: 'center',
                headerHozAlign: 'center',
                formatter: (cell) => {
                    const val  = cell.getValue() || '';
                    const disp = cell.getRow().getData().estado_display || val;
                    const icon = val === 'ACTIVO' ? '<i class="bi bi-check-circle me-1"></i>' :
                                 val === 'INACTIVO' ? '<i class="bi bi-pause-circle me-1"></i>' :
                                 val === 'CANCELADO' ? '<i class="bi bi-x-circle me-1"></i>' : '';
                    return `<span class="badge ${estadoBadge(val)} px-2">${icon}${disp}</span>`;
                },
            },
            {
                title: 'Acciones',
                width: 180,
                hozAlign: 'center',
                headerSort: false,
                formatter: (cell) => {
                    const data    = cell.getRow().getData();
                    const uuid    = data.uuid || '';
                    const esActivo = data.estado === 'ACTIVO';

                    let html = '<div class="btn-group btn-group-sm">';
                    html += `<button data-action="ver-detalle" data-uuid="${uuid}"
                                class="btn btn-outline-secondary" title="Ver Detalle">
                                <i class="bi bi-eye"></i>
                             </button>`;
                    if (esActivo) {
                        html += `<button data-action="editar" data-uuid="${uuid}"
                                    class="btn btn-outline-primary" title="Editar">
                                    <i class="bi bi-pencil"></i>
                                 </button>`;
                        html += `<button data-action="cancelar" data-uuid="${uuid}"
                                    class="btn btn-outline-danger" title="Cancelar Contrato">
                                    <i class="bi bi-x-circle"></i>
                                 </button>`;
                    }
                    html += '</div>';
                    return html;
                },
                cellClick: (e, cell) => handleCellAction(e, cell),
            },
        ];
    }

    // ── Cancelar Contrato ──────────────────────────────────────────────────────

    async function cancelarContrato(uuid) {
        if (!uuid) return;
        if (!confirm('Confirmar cancelacion del contrato. Esta accion no se puede deshacer.')) return;

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

    // ── Inicializar tabla ──────────────────────────────────────────────────────

    async function init(gridSelector) {
        const el = d.querySelector(gridSelector);
        if (!el) {
            console.warn(`${MOD} Container ${gridSelector} no encontrado`);
            return;
        }

        if (table) {
            console.log(`${MOD} Tabla ya inicializada, omitiendo...`);
            return table;
        }

        const api = API();
        if (!api) { console.error(`${MOD} API no disponible`); return; }

        if (!w.TabulatorFactory) {
            console.warn(`${MOD} TabulatorFactory no disponible, reintentando en 100ms...`);
            setTimeout(() => init(gridSelector), 100);
            return;
        }

        table = w.TabulatorFactory.create(gridSelector, api.contratos.list, getColumnas(), {
            searchInputSelector: '#search-contrato',
            paginationSize: 15,
            paginationSizeSelector: [10, 15, 25, 50],
        });

        console.log(`${MOD} Tabla inicializada: ${api.contratos.list}`);
        return table;
    }

    // ── Reload ─────────────────────────────────────────────────────────────────

    function reload() {
        if (table) {
            table.setData();
        }
    }

    function redraw() {
        if (table) {
            table.redraw(true);
        }
    }

    // ── Export ─────────────────────────────────────────────────────────────────

    w.Sintel.Empleados.ContratoList = { init, reload, redraw };

})(window, document);
