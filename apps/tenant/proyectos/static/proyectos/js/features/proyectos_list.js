/**
 * Feature: Listado Proyectos v3.9.6
 * - KPIs calculados desde datos del grid
 * - Filtros por fase (chips)
 * - Columnas rediseñadas: Proyecto+Código, Responsable, Avance, Documentos, Período, Contrato/Margen
 */
(function (w, d) {
    'use strict';

    const MOD = '[proyectos.list]';
    let table  = null;

    // Anti-Zombies: destruir instancias previas en HTMX swap
    if (window.SintelProyectosTables) {
        Object.values(window.SintelProyectosTables).forEach(tb => {
            if (tb && typeof tb.destroy === 'function') {
                try { tb.destroy(); } catch (_) {}
            }
        });
    }
    window.SintelProyectosTables = {};

    // ─── Utilidades ───────────────────────────────────────────────────────────

    function fmtMoneda(v) {
        const n = parseFloat(v);
        if (!v && v !== 0 || isNaN(n)) return '—';
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP',
            minimumFractionDigits: 0, maximumFractionDigits: 0
        }).format(n);
    }

    function fmtFecha(v) {
        if (!v) return '—';
        try {
            return new Date(v + 'T00:00:00').toLocaleDateString('es-CO', {
                day: '2-digit', month: 'short', year: 'numeric'
            });
        } catch (_) { return v; }
    }

    // ─── KPIs ─────────────────────────────────────────────────────────────────

    function actualizarKPIs(rows) {
        const total       = rows.length;
        const ejecucion   = rows.filter(r => r.estado_tarea === 'EN_PROCESO').length;
        const completados = rows.filter(r => r.estado_tarea === 'COMPLETADO').length;
        const pendientes  = rows.filter(r => r.estado_tarea === 'PENDIENTE').length;
        const cartera     = rows.reduce((s, r) => s + (parseFloat(r.valor_contrato_proyectado) || 0), 0);
        const avanceProm  = total
            ? Math.round(rows.reduce((s, r) => s + (parseFloat(r.porcentaje_avance) || 0), 0) / total)
            : 0;

        const set = (id, v) => { const el = d.getElementById(id); if (el) el.textContent = v; };
        set('kpi-total',       total);
        set('kpi-ejecucion',   ejecucion);
        set('kpi-completados', completados);
        set('kpi-pendientes',  pendientes);
        set('kpi-cartera',     fmtMoneda(cartera));
        set('kpi-avance',      avanceProm + '%');
    }

    // ─── Columnas ─────────────────────────────────────────────────────────────

    function getColumns() {
        return [
            // 1. Proyecto — nombre + código + tipo_servicio
            {
                title: "Proyecto",
                field: "nombre",
                frozen: true,
                minWidth: 230,
                formatter: function (cell) {
                    const row      = cell.getRow().getData();
                    const nombre   = row.nombre   || '—';
                    const codigo   = row.codigo   || '';
                    const tipo     = row.tipo_servicio_display || '';
                    const tipoHtml = tipo
                        ? `<span class="badge bg-light text-secondary border fw-normal me-1" style="font-size:0.65rem;">${tipo}</span>`
                        : '';
                    return `
                        <div style="line-height:1.35;">
                          <div class="fw-semibold text-truncate" style="max-width:200px;" title="${nombre}">${nombre}</div>
                          <div class="mt-1">${tipoHtml}${codigo ? `<code class="text-muted" style="font-size:0.7rem;">${codigo}</code>` : ''}</div>
                        </div>`;
                }
            },
            // 2. Fase
            {
                title: "Fase",
                field: "fase_actual",
                width: 118,
                hozAlign: "center",
                headerHozAlign: "center",
                formatter: function (cell) {
                    const fase = cell.getValue();
                    const MAP = {
                        'BORRADOR':   ['bg-secondary',            'Borrador'],
                        'INICIO':     ['bg-info text-dark',       'Inicio'],
                        'PLANEACION': ['bg-primary',              'Planeación'],
                        'EJECUCION':  ['bg-warning text-dark',    'Ejecución'],
                        'CIERRE':     ['bg-success',              'Cierre'],
                    };
                    const [cls, label] = MAP[fase] || ['bg-secondary', fase || '—'];
                    return `<span class="badge ${cls} px-2 py-1">${label}</span>`;
                }
            },
            // 3. Estado
            {
                title: "Estado",
                field: "estado_tarea",
                width: 120,
                hozAlign: "center",
                headerHozAlign: "center",
                formatter: function (cell) {
                    const est = cell.getValue();
                    const MAP = {
                        'PENDIENTE':  ['bg-secondary', 'Pendiente'],
                        'EN_PROCESO': ['bg-primary',   'En Proceso'],
                        'DETENIDO':   ['bg-danger',    'Detenido'],
                        'COMPLETADO': ['bg-success',   'Completado'],
                    };
                    const [cls, label] = MAP[est] || ['bg-light text-dark', est || '—'];
                    return `<span class="badge ${cls} px-2 py-1">${label}</span>`;
                }
            },
            // 4. Avance
            {
                title: "Avance",
                field: "porcentaje_avance",
                width: 110,
                hozAlign: "center",
                headerHozAlign: "center",
                formatter: function (cell) {
                    const pct = parseFloat(cell.getValue()) || 0;
                    const color = pct >= 80 ? '#198754' : pct >= 40 ? '#ffc107' : '#6c757d';
                    return `
                        <div style="line-height:1.2;">
                          <div class="fw-semibold" style="font-size:0.8rem;color:${color};">${pct.toFixed(0)}%</div>
                          <div class="progress mt-1" style="height:5px;border-radius:3px;">
                            <div class="progress-bar" style="width:${pct}%;background:${color};"></div>
                          </div>
                        </div>`;
                }
            },
            // 5. Responsable
            {
                title: "Responsable",
                field: "responsable_actual_nombre",
                minWidth: 150,
                formatter: function (cell) {
                    const nombre = cell.getValue();
                    if (!nombre) return '<span class="text-muted small">—</span>';
                    const iniciales = nombre.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
                    return `
                        <div class="d-flex align-items-center gap-2">
                          <div class="rounded-circle bg-primary bg-opacity-10 text-primary d-flex align-items-center justify-content-center flex-shrink-0 fw-bold"
                               style="width:26px;height:26px;font-size:0.65rem;">${iniciales}</div>
                          <span class="text-truncate small" style="max-width:110px;" title="${nombre}">${nombre}</span>
                        </div>`;
                }
            },
            // 6. Cliente
            {
                title: "Cliente",
                field: "cliente_nombre",
                minWidth: 160,
                formatter: function (cell) {
                    const v = cell.getValue();
                    if (!v) return '<span class="text-muted small">—</span>';
                    return `<span class="text-truncate d-block small" style="max-width:145px;" title="${v}">${v}</span>`;
                }
            },
            // 7. Documentos — Factura + Cotización apiladas
            {
                title: "Documentos",
                field: "factura_costo_numero",
                width: 160,
                hozAlign: "center",
                headerHozAlign: "center",
                formatter: function (cell) {
                    const row       = cell.getRow().getData();
                    const factura   = row.factura_costo_numero;
                    const cotizacion= row.cotizacion_numero;
                    const parts     = [];
                    if (factura)    parts.push(`<span class="badge bg-light text-dark border fw-semibold" style="font-size:0.7rem;"><i class="bi bi-receipt me-1"></i>${factura}</span>`);
                    if (cotizacion) parts.push(`<span class="badge bg-info-subtle text-info-emphasis border border-info fw-semibold" style="font-size:0.7rem;"><i class="bi bi-file-earmark-text me-1"></i>${cotizacion}</span>`);
                    if (!parts.length) return '<span class="text-muted small">—</span>';
                    return `<div class="d-flex flex-column gap-1 align-items-center">${parts.join('')}</div>`;
                }
            },
            // 8. Período — inicio a fin estimado apiladas
            {
                title: "Período",
                field: "fecha_inicio",
                width: 140,
                hozAlign: "center",
                headerHozAlign: "center",
                formatter: function (cell) {
                    const row   = cell.getRow().getData();
                    const ini   = fmtFecha(row.fecha_inicio);
                    const fin   = fmtFecha(row.fecha_fin_estimada);
                    return `
                        <div style="line-height:1.35;font-size:0.78rem;">
                          <div><i class="bi bi-calendar-event text-muted me-1"></i>${ini}</div>
                          <div class="text-muted"><i class="bi bi-calendar-x me-1"></i>${fin}</div>
                        </div>`;
                }
            },
            // 9. Contrato + Margen apilados
            {
                title: "Contrato / Margen",
                field: "valor_contrato_proyectado",
                width: 165,
                hozAlign: "right",
                headerHozAlign: "right",
                formatter: function (cell) {
                    const row       = cell.getRow().getData();
                    const contrato  = parseFloat(row.valor_contrato_proyectado) || 0;
                    const margen    = parseFloat(row.margen_rentabilidad)        || 0;
                    const badgeCls  = margen > 0 ? 'bg-success' : margen < 0 ? 'bg-danger' : 'bg-secondary';
                    return `
                        <div style="line-height:1.35; text-align:right;">
                          <div class="fw-semibold" style="font-size:0.85rem;">${fmtMoneda(contrato)}</div>
                          <div class="mt-1">
                            <span class="badge ${badgeCls} px-1" style="font-size:0.7rem;">
                              <i class="bi bi-graph-up me-1"></i>${margen.toFixed(1)}%
                            </span>
                          </div>
                        </div>`;
                }
            },
            // 10. Acciones — frozen
            {
                title: "",
                field: "uuid",
                headerSort: false,
                hozAlign: "center",
                width: 116,
                frozen: true,
                formatter: function (cell) {
                    const row  = cell.getRow().getData();
                    const uuid = row.uuid;
                    const empUuid = row.responsable_empleado_uuid || '';
                    const empNombre = row.responsable_actual_nombre || '';
                    return `
                        <div class="btn-group btn-group-sm">
                          <button type="button" class="btn btn-outline-secondary btn-tareas-cortas"
                                  data-uuid="${uuid}"
                                  data-emp-uuid="${empUuid}"
                                  data-emp-nombre="${empNombre}"
                                  title="Tareas Cortas">
                            <i class="bi bi-list-task"></i>
                          </button>
                          <button type="button" class="btn btn-outline-primary btn-edit-proyecto"
                                  data-uuid="${uuid}" title="Editar proyecto">
                            <i class="bi bi-pencil"></i>
                          </button>
                          <button type="button" class="btn btn-outline-danger btn-delete-proyecto"
                                  data-uuid="${uuid}" title="Eliminar proyecto">
                            <i class="bi bi-trash"></i>
                          </button>
                        </div>`;
                }
            }
        ];
    }

    // ─── Inicializar Tabulator ─────────────────────────────────────────────────

    function initTabulator() {
        if (!w.TabulatorFactory) {
            console.error(`${MOD} TabulatorFactory no disponible`);
            return;
        }
        const gridEl = d.querySelector('#grid-proyectos');
        if (!gridEl) { console.warn(`${MOD} #grid-proyectos no encontrado`); return; }

        if (window.SintelProyectosTables.main) {
            try { window.SintelProyectosTables.main.destroy(); } catch (_) {}
        }

        table = w.TabulatorFactory.create(
            '#grid-proyectos',
            '/api/v1/proyectos/',
            getColumns(),
            { searchInputSelector: '#search-proyecto' }
        );

        if (table) {
            window.SintelProyectosTables.main = table;

            // Calcular KPIs tras cargar datos
            table.on('dataLoaded', function (data) {
                actualizarKPIs(data);
            });
            table.on('dataFiltered', function (_filters, rows) {
                actualizarKPIs(rows.map(r => r.getData()));
            });
        }
        return table;
    }

    // ─── Filtros por Fase ─────────────────────────────────────────────────────

    function initFiltrosFase() {
        const contenedor = d.getElementById('filtros-fase-proyectos');
        if (!contenedor) return;

        contenedor.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-fase]');
            if (!btn) return;

            // Activar chip
            contenedor.querySelectorAll('[data-fase]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const fase = btn.getAttribute('data-fase');
            if (!table) return;
            table.clearFilter(true);  // quitar filtros anteriores
            if (fase) {
                table.setFilter('fase_actual', '=', fase);
            }
        });
    }

    // ─── Event Delegation (Editar / Eliminar) ─────────────────────────────────

    function initListEvents() {
        const gridEl = d.querySelector('#grid-proyectos');
        if (!gridEl) return;

        gridEl.addEventListener('click', async (e) => {
            // Editar
            const btnEdit = e.target.closest('.btn-edit-proyecto');
            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnEdit.getAttribute('data-uuid');
                if (!uuid) return;
                const orig = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `/api/v1/proyectos/gestor-offcanvas/?uuid=${uuid}`, {
                        target: '#offcanvas-container-proyectos', swap: 'innerHTML'
                    });
                } catch (_) {
                    w.SintelFeedback?.error?.('Error al cargar el formulario de proyecto');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = orig;
                }
                return;
            }

            // Eliminar
            const btnDel = e.target.closest('.btn-delete-proyecto');
            if (btnDel) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnDel.getAttribute('data-uuid');
                if (!uuid) return;
                if (!confirm('¿Eliminar este proyecto? Esta acción no se puede deshacer.')) return;
                const orig = btnDel.innerHTML;
                btnDel.disabled = true;
                btnDel.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const res = await w.http('DELETE', `/api/v1/proyectos/${uuid}/`);
                    if (res.ok) {
                        w.SintelFeedback?.success?.('Proyecto eliminado correctamente');
                        table?.replaceData?.();
                    } else {
                        w.UIManager?.handleError?.(res, MOD) || alert('Error al eliminar');
                    }
                } catch (_) {
                    w.SintelFeedback?.error?.('Error al eliminar el proyecto');
                } finally {
                    btnDel.disabled = false;
                    btnDel.innerHTML = orig;
                }
                return;
            }
        });
    }

    // ─── Evento proyectoGuardado ───────────────────────────────────────────────

    function initEventListeners() {
        d.addEventListener('proyectoGuardado', () => {
            table?.replaceData?.();
        });
    }

    // ─── Init ─────────────────────────────────────────────────────────────────

    function init() {
        const tabEl = d.querySelector('#tab-proyectos');
        if (tabEl && w.DOMUtils?.onVisibleOnce) {
            w.DOMUtils.onVisibleOnce(tabEl.id ? '#' + tabEl.id : tabEl, () => {
                initTabulator();
                initListEvents();
                initFiltrosFase();
                initEventListeners();
            });
        } else {
            initTabulator();
            initListEvents();
            initFiltrosFase();
            initEventListeners();
        }
    }

    // HTMX: limpiar zombie en swap
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:beforeSwap', (ev) => {
            if (ev.detail.target.id === 'tab-proyectos-content' ||
                ev.detail.target.closest?.('#tab-proyectos-content')) {
                try { window.SintelProyectosTables.main?.destroy?.(); } catch (_) {}
                delete window.SintelProyectosTables.main;
            }
        });
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // API pública
    w.ProyectosListModule = {
        init,
        refresh: () => table?.replaceData?.(),
        getTable: () => table
    };
    w.ProyectosModule = w.ProyectosModule || { refresh: () => table?.replaceData?.() };

})(window, document);
