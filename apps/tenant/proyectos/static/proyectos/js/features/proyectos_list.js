/**
 * Feature: Listado Proyectos
 * La tabla "Proyectos" es DataTables 3.x (#tabla-proyectos, mismo patron ya
 * validado en Ventas/Bancos/Facturas/Clientes/Proveedores/Compras/Gastos/
 * Empleados -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md),
 * poblada via ajax contra POST /api/v1/proyectos/dt/. ProyectoTable/
 * ProyectoTableView (django-tables2) retirados. TareaCortaTable ("Tareas
 * Cortas") sigue en django-tables2/HTMX -- no migrada en esta pasada.
 *
 * Este archivo maneja: init de la tabla, delegacion global de clicks
 * (editar/eliminar/tareas-cortas) sobre document.body, y los chips de
 * filtro por fase (columna 1, fase_actual).
 */
(function (w, d) {
    'use strict';

    const MOD = '[proyectos.list]';

    // ─── DataTables (tabla "Proyectos") ────────────────────────────────────

    var TABLA_PROYECTOS_SELECTOR = '#tabla-proyectos';
    var TABLA_PROYECTOS_URL = '/api/v1/proyectos/dt/';
    var _proyectosTablaInicializada = false;

    var FASE_MAP = {
        BORRADOR: ['bg-secondary', 'Borrador'], INICIO: ['bg-info text-dark', 'Inicio'],
        PLANEACION: ['bg-primary', 'Planeación'], EJECUCION: ['bg-warning text-dark', 'Ejecución'],
        CIERRE: ['bg-success', 'Cierre'],
    };
    var ESTADO_TAREA_MAP = {
        PENDIENTE: ['bg-secondary', 'Pendiente'], EN_PROCESO: ['bg-primary', 'En Proceso'],
        DETENIDO: ['bg-danger', 'Detenido'], COMPLETADO: ['bg-success', 'Completado'],
    };
    var MESES_PROYECTO = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

    function escapeHtmlProyecto(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function fmtFechaProyecto(iso) {
        if (!iso) return '—';
        var parsed = new Date(iso + 'T00:00:00');
        if (isNaN(parsed.getTime())) return escapeHtmlProyecto(iso);
        return String(parsed.getDate()).padStart(2, '0') + ' ' + MESES_PROYECTO[parsed.getMonth()] + ' ' + parsed.getFullYear();
    }

    function fmtMonedaProyecto(value) {
        var n = parseFloat(value || 0);
        if (isNaN(n)) return '—';
        return '$ ' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
    }

    function renderNombreProyecto(data, type, row) {
        var tipoHtml = row.tipo_servicio_display
            ? '<span class="badge bg-light text-secondary border fw-normal me-1" style="font-size:0.65rem;">' + escapeHtmlProyecto(row.tipo_servicio_display) + '</span>' : '';
        var codigoHtml = row.codigo ? '<code class="text-muted" style="font-size:0.7rem;">' + escapeHtmlProyecto(row.codigo) + '</code>' : '';
        return '<div style="line-height:1.35;">' +
            '<div class="fw-semibold text-truncate" style="max-width:200px;" title="' + escapeHtmlProyecto(row.nombre) + '">' + escapeHtmlProyecto(row.nombre || '—') + '</div>' +
            '<div class="mt-1">' + tipoHtml + codigoHtml + '</div></div>';
    }

    function renderFaseProyecto(value) {
        var cfg = FASE_MAP[value] || ['bg-secondary', value || '—'];
        return '<span class="badge ' + cfg[0] + ' px-2 py-1">' + escapeHtmlProyecto(cfg[1]) + '</span>';
    }

    function renderEstadoTareaProyecto(value) {
        var cfg = ESTADO_TAREA_MAP[value] || ['bg-light text-dark', value || '—'];
        return '<span class="badge ' + cfg[0] + ' px-2 py-1">' + escapeHtmlProyecto(cfg[1]) + '</span>';
    }

    function renderAvanceProyecto(value) {
        var pct = value || 0;
        var color = pct >= 80 ? '#198754' : pct >= 40 ? '#ffc107' : '#6c757d';
        return '<div style="line-height:1.2;"><div class="fw-semibold" style="font-size:0.8rem;color:' + color + ';">' + pct + '%</div>' +
            '<div class="progress mt-1" style="height:5px;border-radius:3px;"><div class="progress-bar" style="width:' + pct + '%;background:' + color + ';"></div></div></div>';
    }

    function renderResponsableProyecto(data, type, row) {
        var nombre = row.responsable_actual_nombre;
        if (!nombre) return '<span class="text-muted small">—</span>';
        var iniciales = nombre.split(' ').slice(0, 2).map(function (w2) { return w2[0]; }).join('').toUpperCase();
        return '<div class="d-flex align-items-center gap-2">' +
            '<div class="rounded-circle bg-primary bg-opacity-10 text-primary d-flex align-items-center justify-content-center flex-shrink-0 fw-bold" style="width:26px;height:26px;font-size:0.65rem;">' + escapeHtmlProyecto(iniciales) + '</div>' +
            '<span class="text-truncate small" style="max-width:110px;" title="' + escapeHtmlProyecto(nombre) + '">' + escapeHtmlProyecto(nombre) + '</span></div>';
    }

    function renderClienteProyecto(value) {
        if (!value) return '<span class="text-muted small">—</span>';
        return '<span class="text-truncate d-block small" style="max-width:145px;" title="' + escapeHtmlProyecto(value) + '">' + escapeHtmlProyecto(value) + '</span>';
    }

    function renderDocumentosProyecto(data, type, row) {
        var parts = [];
        if (row.factura_costo_numero) {
            parts.push('<span class="badge bg-light text-dark border fw-semibold" style="font-size:0.7rem;"><i class="bi bi-receipt me-1"></i>' + escapeHtmlProyecto(row.factura_costo_numero) + '</span>');
        }
        if (row.cotizacion_numero) {
            parts.push('<span class="badge bg-info-subtle text-info-emphasis border border-info fw-semibold" style="font-size:0.7rem;"><i class="bi bi-file-earmark-text me-1"></i>' + escapeHtmlProyecto(row.cotizacion_numero) + '</span>');
        }
        if (!parts.length) return '<span class="text-muted small">—</span>';
        return '<div class="d-flex flex-column gap-1 align-items-center">' + parts.join('') + '</div>';
    }

    function renderPeriodoProyecto(data, type, row) {
        return '<div style="line-height:1.35;font-size:0.78rem;">' +
            '<div><i class="bi bi-calendar-event text-muted me-1"></i>' + fmtFechaProyecto(row.fecha_inicio) + '</div>' +
            '<div class="text-muted"><i class="bi bi-calendar-x me-1"></i>' + fmtFechaProyecto(row.fecha_fin_prevista) + '</div></div>';
    }

    function renderContratoProyecto(data, type, row) {
        var margen = parseFloat(row.margen_rentabilidad || 0);
        var badgeCls = margen > 0 ? 'bg-success' : margen < 0 ? 'bg-danger' : 'bg-secondary';
        return '<div style="line-height:1.35; text-align:right;">' +
            '<div class="fw-semibold" style="font-size:0.85rem;">' + fmtMonedaProyecto(row.valor_contrato_proyectado) + '</div>' +
            '<div class="mt-1"><span class="badge ' + badgeCls + ' px-1" style="font-size:0.7rem;"><i class="bi bi-graph-up me-1"></i>' + margen.toFixed(1) + '%</span></div></div>';
    }

    function renderAccionesProyecto(data, type, row) {
        var empUuid = row.responsable_empleado_uuid || '';
        var empNombre = row.responsable_actual_nombre || '';
        return '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-secondary btn-tareas-cortas" data-uuid="' + escapeHtmlProyecto(row.uuid) + '" data-emp-uuid="' + escapeHtmlProyecto(empUuid) + '" data-emp-nombre="' + escapeHtmlProyecto(empNombre) + '" title="Tareas Cortas"><i class="bi bi-list-task"></i></button>' +
            '<button type="button" class="btn btn-outline-primary btn-edit-proyecto" data-uuid="' + escapeHtmlProyecto(row.uuid) + '" title="Editar proyecto"><i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn btn-outline-danger btn-delete-proyecto" data-uuid="' + escapeHtmlProyecto(row.uuid) + '" title="Eliminar proyecto"><i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    var PROYECTOS_COLUMNS = [
        { data: null, title: 'Proyecto', render: renderNombreProyecto },
        { data: 'fase_actual', title: 'Fase', render: renderFaseProyecto },
        { data: 'estado_tarea', title: 'Estado', render: renderEstadoTareaProyecto },
        { data: 'porcentaje_avance', title: 'Avance', render: renderAvanceProyecto },
        { data: null, title: 'Responsable', render: renderResponsableProyecto },
        { data: 'cliente_nombre', title: 'Cliente', render: renderClienteProyecto },
        { data: null, title: 'Documentos', orderable: false, searchable: false, render: renderDocumentosProyecto },
        { data: null, title: 'Período', orderable: false, searchable: false, render: renderPeriodoProyecto },
        { data: null, title: 'Contrato / Margen', orderable: false, searchable: false, render: renderContratoProyecto },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccionesProyecto },
    ];

    function initProyectosTabla() {
        if (_proyectosTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_PROYECTOS_SELECTOR, TABLA_PROYECTOS_URL, PROYECTOS_COLUMNS, {
            pageLength: 20,
            order: [],
        });
        _proyectosTablaInicializada = true;
    }

    // ─── Chips de Fase: filtro real (columna 1) + toggle visual ────────────────

    function initFiltrosFase() {
        const contenedor = d.getElementById('filtros-fase-proyectos');
        if (!contenedor) return;
        contenedor.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-fase]');
            if (!btn) return;
            contenedor.querySelectorAll('[data-fase]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_PROYECTOS_SELECTOR, 1, btn.getAttribute('data-fase'));
        });
    }

    // ─── Event Delegation (Editar / Eliminar / Tareas Cortas) ──────────────────

    function initListEvents() {
        d.body.addEventListener('click', async (e) => {
            // Tareas cortas: delegado por proyectos.nueva_tarea.list.js
            // (escucha .btn-tareas-cortas sobre document.body, no se toca aqui)

            // Editar
            const btnEdit = e.target.closest('#tabla-proyectos .btn-edit-proyecto');
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
            const btnDel = e.target.closest('#tabla-proyectos .btn-delete-proyecto');
            if (btnDel) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnDel.getAttribute('data-uuid');
                if (!uuid) return;
                if (!(await w.UIManager?.confirm('¿Eliminar este proyecto? Esta acción no se puede deshacer.'))) return;
                const orig = btnDel.innerHTML;
                btnDel.disabled = true;
                btnDel.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    // T-9: delega a la SSoT de endpoints (proyectos.api.js).
                    const res = await w.proyectosAPI.delete(uuid);
                    if (res.ok) {
                        w.SintelFeedback?.success?.('Proyecto eliminado correctamente');
                        w.refreshProyectosTable?.();
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
            w.refreshProyectosTable?.();
        });
    }

    // Funcion global de refresco: recarga la tabla DataTables + dispara el
    // evento que el panel HTMX de KPIs escucha via
    // hx-trigger="load, proyecto-updated from:body".
    w.refreshProyectosTable = function () {
        if (w.Sintel && w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_PROYECTOS_SELECTOR);
        }
        d.body.dispatchEvent(new CustomEvent('proyecto-updated'));
    };

    function init() {
        initProyectosTabla();
        initListEvents();
        initFiltrosFase();
        initEventListeners();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // API pública (compatibilidad con codigo existente que llama a estos metodos)
    w.ProyectosListModule = {
        init,
        refresh: () => w.refreshProyectosTable?.()
    };
    w.ProyectosModule = w.ProyectosModule || { refresh: () => w.refreshProyectosTable?.() };

})(window, document);
