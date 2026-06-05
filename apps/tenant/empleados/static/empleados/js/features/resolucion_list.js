// @ts-nocheck
/**
 * Resolucion List Module — Tabla de Resoluciones DIAN
 * Namespace: window.Sintel.Empleados.ResolucionList
 * Skills: tabulator.md §1, §3, §6 | vanilla-js.md §1, §2 | htmx.md §2
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[ResolucionList]';
    const API_BASE = '/api/v1/empleados/resoluciones-dian/';
    const CONTAINER_ID = 'offcanvas-container-resoluciones';

    let table = null;

    const COP = (v) => {
        const n = parseInt(v, 10); if (isNaN(n)) return '—';
        return n.toLocaleString('es-CO');
    };

    // ── Columnas (skill: tabulator.md §2, §3) ──────────────────────────────────
    function getColumnas() {
        return [
            {
                title: 'Nro Resolucion',
                field: 'numero_resolucion',
                minWidth: 160,
                formatter(cell) {
                    const v = cell.getValue();
                    return v
                        ? `<i class="bi bi-file-earmark-lock text-primary me-2"></i><span class="fw-semibold">${v}</span>`
                        : '<span class="text-muted">—</span>';
                },
            },
            {
                title: 'Prefijo',
                field: 'prefijo',
                width: 90,
                hozAlign: 'center',
                formatter: (cell) => cell.getValue()
                    ? `<span class="badge bg-secondary font-monospace">${cell.getValue()}</span>`
                    : '—',
            },
            {
                title: 'Rango',
                field: 'rango_desde',
                width: 160,
                hozAlign: 'center',
                formatter(cell) {
                    const row = cell.getRow().getData();
                    return `<span class="font-monospace small">${COP(row.rango_desde)} – ${COP(row.rango_hasta)}</span>`;
                },
            },
            {
                title: 'Consecutivo',
                field: 'consecutivo',
                width: 120,
                hozAlign: 'center',
                formatter(cell) {
                    const row = cell.getRow().getData();
                    const val = cell.getValue() || 0;
                    const hasta = row.rango_hasta || 0;
                    const pct = hasta > 0 ? Math.round((val / hasta) * 100) : 0;
                    const cls = pct >= 90 ? 'text-danger fw-bold' : pct >= 70 ? 'text-warning fw-semibold' : 'text-success fw-semibold';
                    return `<span class="${cls}">${COP(val)}</span>`;
                },
            },
            {
                title: 'Vigencia',
                field: 'fecha_inicio',
                minWidth: 180,
                formatter(cell) {
                    const row = cell.getRow().getData();
                    const ini = row.fecha_inicio || '—';
                    const fin = row.fecha_fin || '—';
                    return `<span class="small"><i class="bi bi-calendar-range text-muted me-1"></i>${ini} → ${fin}</span>`;
                },
            },
            {
                title: 'Estado',
                field: 'vigente',
                width: 100,
                hozAlign: 'center',
                formatter: (cell) => cell.getValue()
                    ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Vigente</span>'
                    : '<span class="badge bg-secondary">Inactiva</span>',
            },
            {
                title: '',
                width: 80,
                hozAlign: 'center',
                headerSort: false,
                formatter(cell) {
                    const uuid = cell.getRow().getData().uuid;
                    return `<button class="btn btn-outline-danger btn-sm py-0 px-2" data-action="del-resolucion" data-uuid="${uuid}" title="Eliminar">
                        <i class="bi bi-trash"></i>
                    </button>`;
                },
                cellClick(e, cell) {
                    const btn = e.target.closest('[data-action="del-resolucion"]');
                    if (!btn) return;
                    const uuid = btn.dataset.uuid;
                    if (!uuid) return;
                    if (!confirm('¿Eliminar esta resolución DIAN? Esta acción no se puede deshacer.')) return;
                    _eliminar(uuid);
                },
            },
        ];
    }

    async function _eliminar(uuid) {
        try {
            const res = await w.http('DELETE', `${API_BASE}${uuid}/`);
            if (res.ok) {
                w.UIManager?.notifySuccess('Resolución eliminada correctamente');
                reload();
            } else {
                const msg = res.data?.detail || 'Error al eliminar la resolución';
                w.UIManager?.notifyError(msg);
            }
        } catch (err) {
            console.error(`${MOD} Error al eliminar:`, err);
            w.UIManager?.notifyError('Error de conexión al eliminar la resolución');
        }
    }

    // ── Inicializar tabla (skill: tabulator.md §1, §6) ────────────────────────
    function init(gridSelector) {
        if (table) { table.redraw(true); return; }
        if (!w.TabulatorFactory) {
            console.warn(`${MOD} TabulatorFactory no disponible, reintentando...`);
            setTimeout(() => init(gridSelector), 200);
            return;
        }

        table = w.TabulatorFactory.create(
            gridSelector,
            API_BASE,
            getColumnas(),
            { searchInputSelector: '#search-resolucion' }
        );

        if (table) {
            console.log(`${MOD} Tabla inicializada`);
        }
    }

    function reload() {
        if (table?.replaceData) table.replaceData();
    }

    function redraw() {
        if (table?.redraw) table.redraw(true);
    }

    w.Sintel.Empleados.ResolucionList = { init, reload, redraw };

})(window, document);
