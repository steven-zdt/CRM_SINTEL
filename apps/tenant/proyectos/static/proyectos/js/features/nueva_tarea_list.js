/**
 * Feature: Nueva Tarea - listado dinamico.
 * Modulo independiente para tareas cortas dentro de Proyectos.
 */
(function (w, d) {
    'use strict';

    const MOD = '[proyectos.nueva_tarea.list]';
    let table = null;
    let empleadoUuid = null;
    let empleadoNombre = '';
    let initialized = false;
    let lastRows = [];
    let estadoFiltro = '';
    let searchText = '';

    function getPanel() {
        return d.getElementById('panel-nueva-tarea');
    }

    function getGrid() {
        return d.getElementById('grid-nueva-tarea');
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function fmtFecha(value) {
        if (!value) return '-';
        try {
            return new Date(value + 'T00:00:00').toLocaleDateString('es-CO', {
                day: '2-digit',
                month: 'short'
            });
        } catch (_) {
            return value;
        }
    }

    function setText(id, value) {
        const el = d.getElementById(id);
        if (el) el.textContent = value;
    }

    function actualizarKpis(rows) {
        setText('nt-kpi-total', rows.length);
        setText('nt-kpi-proceso', rows.filter(row => row.estado === 'EN_PROCESO').length);
        setText('nt-kpi-completada', rows.filter(row => row.estado === 'COMPLETADA').length);
        setText('nt-kpi-pendiente', rows.filter(row => row.estado === 'PENDIENTE').length);
    }

    function buildColumns() {
        return [
            {
                title: 'Tarea',
                field: 'titulo',
                minWidth: 170,
                formatter(cell) {
                    const row = cell.getRow().getData();
                    const titulo = escapeHtml(row.titulo || '-');
                    const desc = escapeHtml(row.descripcion || '');
                    const descCorto = desc.length > 40 ? `${desc.slice(0, 40)}...` : desc;
                    return `<div style="line-height:1.3;">
                      <div class="fw-semibold text-truncate" style="max-width:130px;" title="${titulo}">${titulo}</div>
                      ${desc ? `<div class="text-muted" style="font-size:0.7rem;" title="${desc}">${descCorto}</div>` : ''}
                    </div>`;
                }
            },
            {
                title: 'Cliente',
                field: 'cliente_nombre',
                minWidth: 180,
                formatter(cell) {
                    const row = cell.getRow().getData();
                    const nombre = escapeHtml(cell.getValue() || row.cliente_info?.label || '-');
                    const doc = escapeHtml(row.cliente_info?.numero_documento || '');
                    return `<div style="line-height:1.3;">
                      <div class="fw-semibold text-truncate" style="max-width:160px;" title="${nombre}">${nombre}</div>
                      ${doc ? `<div class="text-muted" style="font-size:0.7rem;">${doc}</div>` : ''}
                    </div>`;
                }
            },
            {
                title: 'Empleado',
                field: 'empleado_nombre',
                minWidth: 160,
                formatter(cell) {
                    const nombre = escapeHtml(cell.getValue() || '-');
                    return `<span class="text-truncate d-block small" style="max-width:145px;" title="${nombre}">${nombre}</span>`;
                }
            },
            {
                title: 'Estado',
                field: 'estado',
                width: 96,
                hozAlign: 'center',
                headerHozAlign: 'center',
                formatter(cell) {
                    const map = {
                        PENDIENTE: ['bg-secondary', 'Pendiente'],
                        EN_PROCESO: ['bg-primary', 'En Proceso'],
                        COMPLETADA: ['bg-success', 'Completada'],
                        CANCELADA: ['bg-danger', 'Cancelada']
                    };
                    const [cls, label] = map[cell.getValue()] || ['bg-light text-dark', cell.getValue() || '-'];
                    return `<span class="badge ${cls} px-2" style="font-size:0.68rem;">${label}</span>`;
                }
            },
            {
                title: 'Prior.',
                field: 'prioridad',
                width: 70,
                hozAlign: 'center',
                headerHozAlign: 'center',
                formatter(cell) {
                    const map = {
                        ALTA: 'text-danger fw-bold',
                        NORMAL: 'text-primary',
                        BAJA: 'text-muted'
                    };
                    const cls = map[cell.getValue()] || 'text-muted';
                    return `<span class="${cls}" style="font-size:0.78rem;">${cell.getValue() || '-'}</span>`;
                }
            },
            {
                title: 'Periodo',
                field: 'fecha_inicio',
                width: 108,
                hozAlign: 'center',
                headerHozAlign: 'center',
                formatter(cell) {
                    const row = cell.getRow().getData();
                    return `<div style="font-size:0.72rem;line-height:1.4;">
                      <div><i class="bi bi-calendar2 text-muted me-1"></i>${fmtFecha(row.fecha_inicio)}</div>
                      <div class="text-muted"><i class="bi bi-arrow-right me-1"></i>${fmtFecha(row.fecha_fin)}</div>
                    </div>`;
                }
            },
            {
                title: '',
                field: 'uuid',
                headerSort: false,
                width: 76,
                hozAlign: 'center',
                formatter(cell) {
                    const uuid = cell.getValue();
                    const estado = cell.getRow().getData().estado;
                    const nextMap = {
                        PENDIENTE: { nuevo: 'EN_PROCESO', icon: 'bi-play-fill', cls: 'btn-outline-primary' },
                        EN_PROCESO: { nuevo: 'COMPLETADA', icon: 'bi-check-lg', cls: 'btn-outline-success' }
                    };
                    const next = nextMap[estado];
                    const advanceButton = next
                        ? `<button class="btn btn-sm ${next.cls} btn-nt-avanzar px-1" data-uuid="${uuid}" data-estado="${next.nuevo}" title="Avanzar estado">
                             <i class="${next.icon}"></i>
                           </button>`
                        : `<button class="btn btn-sm btn-outline-secondary px-1" disabled title="${estado || ''}">
                             <i class="bi bi-lock"></i>
                           </button>`;
                    return `<div class="d-flex gap-1 justify-content-center">
                      ${advanceButton}
                      <button class="btn btn-sm btn-outline-danger btn-nt-delete px-1" data-uuid="${uuid}" title="Eliminar">
                        <i class="bi bi-trash3"></i>
                      </button>
                    </div>`;
                }
            }
        ];
    }

    function setContext(nextEmpleadoUuid, nextEmpleadoNombre) {
        empleadoUuid = nextEmpleadoUuid || null;
        empleadoNombre = nextEmpleadoNombre || '';
        setText(
            'nueva-tarea-contexto',
            empleadoNombre ? `Empleado: ${empleadoNombre}` : 'Todas las tareas cortas'
        );
    }

    function showPanel() {
        const panel = getPanel();
        if (!panel) return;
        panel.style.display = '';
    }

    function hidePanel() {
        const tab = d.getElementById('tab-proyectos-list');
        if (tab && w.bootstrap?.Tab) {
            w.bootstrap.Tab.getOrCreateInstance(tab).show();
        }
        w.Sintel?.ProyectosNuevaTareaEditor?.hide?.();
    }

    function activateTaskTab() {
        const tab = d.getElementById('tab-proyectos-nueva-tarea');
        if (!tab || !w.bootstrap?.Tab) return false;
        w.bootstrap.Tab.getOrCreateInstance(tab).show();
        return true;
    }

    function destroyTable() {
        if (table && typeof table.destroy === 'function') {
            try { table.destroy(); } catch (_) {}
        }
        table = null;
    }

    function applyFilters() {
        if (!table) return;
        table.clearFilter(true);
        table.setFilter((data) => {
            const matchesEstado = !estadoFiltro || data.estado === estadoFiltro;
            const term = searchText.trim().toLowerCase();
            if (!term) return matchesEstado;
            const haystack = [
                data.titulo,
                data.descripcion,
                data.cliente_nombre,
                data.cliente_info?.numero_documento,
                data.empleado_nombre,
                data.estado,
                data.prioridad
            ].filter(Boolean).join(' ').toLowerCase();
            return matchesEstado && haystack.includes(term);
        });
    }

    async function refresh() {
        const grid = getGrid();
        if (!grid) return;

        destroyTable();
        grid.innerHTML = '<div class="text-center text-muted p-4"><div class="spinner-border spinner-border-sm me-2"></div>Cargando...</div>';

        try {
            const response = await w.proyectosAPI?.tareasCortas?.list(empleadoUuid);
            if (!response?.ok) {
                grid.innerHTML = '<div class="text-danger p-3 small">Error al cargar tareas</div>';
                return;
            }

            const rows = Array.isArray(response.data) ? response.data : (response.data?.results || []);
            lastRows = rows;
            actualizarKpis(rows);
            grid.innerHTML = '';

            if (!rows.length) {
                grid.innerHTML = '<div class="text-muted text-center p-4" style="font-size:0.85rem;"><i class="bi bi-inbox fs-4 d-block mb-2"></i>Sin tareas cortas</div>';
                return;
            }

            table = new Tabulator('#grid-nueva-tarea', {
                data: rows,
                columns: buildColumns(),
                layout: 'fitColumns',
                height: 'auto',
                rowHeight: 52,
                placeholder: 'Sin tareas cortas'
            });
            applyFilters();
        } catch (error) {
            console.error(`${MOD} Error de red`, error);
            grid.innerHTML = '<div class="text-danger p-3 small">Error de red</div>';
        }
    }

    function open(nextEmpleadoUuid = null, nextEmpleadoNombre = '') {
        setContext(nextEmpleadoUuid, nextEmpleadoNombre);
        showPanel();
        activateTaskTab();
        w.requestAnimationFrame(() => refresh());
    }

    function openEditor(nextEmpleadoUuid = empleadoUuid, nextEmpleadoNombre = empleadoNombre) {
        open(nextEmpleadoUuid, nextEmpleadoNombre);
        w.Sintel?.ProyectosNuevaTareaEditor?.show?.();
    }

    function getContext() {
        return { empleadoUuid, empleadoNombre };
    }

    async function avanzarEstado(uuid, nuevoEstado, button) {
        if (!uuid || !nuevoEstado) return;
        if (button) button.disabled = true;
        try {
            const response = await w.proyectosAPI?.tareasCortas?.cambiarEstado(uuid, nuevoEstado);
            if (response?.ok) {
                w.UIManager?.notifySuccess?.('Estado actualizado');
                await refresh();
            } else {
                w.UIManager?.handleError?.(response, `${MOD}:estado`);
            }
        } catch (error) {
            console.error(`${MOD} Error al cambiar estado`, error);
            w.UIManager?.notifyError?.('Error al cambiar estado');
        } finally {
            if (button) button.disabled = false;
        }
    }

    async function eliminar(uuid, button) {
        if (!uuid || !confirm('Eliminar esta tarea corta?')) return;
        if (button) button.disabled = true;
        try {
            const response = await w.proyectosAPI?.tareasCortas?.delete(uuid);
            if (response?.ok) {
                w.UIManager?.notifySuccess?.('Tarea eliminada');
                await refresh();
            } else {
                w.UIManager?.handleError?.(response, `${MOD}:delete`);
            }
        } catch (error) {
            console.error(`${MOD} Error al eliminar`, error);
            w.UIManager?.notifyError?.('Error al eliminar la tarea');
        } finally {
            if (button) button.disabled = false;
        }
    }

    function bindEvents() {
        d.addEventListener('click', (event) => {
            const gridButton = event.target.closest('.btn-tareas-cortas');
            if (gridButton) {
                event.preventDefault();
                event.stopPropagation();
                open(
                    gridButton.getAttribute('data-emp-uuid') || null,
                    gridButton.getAttribute('data-emp-nombre') || ''
                );
                return;
            }

            if (event.target.closest('#btn-menu-nueva-tarea-corta')) {
                event.preventDefault();
                openEditor();
                return;
            }

            if (event.target.closest('#btn-nueva-tarea-form')) {
                event.preventDefault();
                w.Sintel?.ProyectosNuevaTareaEditor?.toggle?.();
                return;
            }

            if (event.target.closest('#btn-refresh-nueva-tarea')) {
                event.preventDefault();
                refresh();
                return;
            }

            if (event.target.closest('#btn-cerrar-nueva-tarea')) {
                event.preventDefault();
                hidePanel();
                return;
            }

            const advanceButton = event.target.closest('.btn-nt-avanzar');
            if (advanceButton) {
                event.preventDefault();
                avanzarEstado(
                    advanceButton.getAttribute('data-uuid'),
                    advanceButton.getAttribute('data-estado'),
                    advanceButton
                );
                return;
            }

            const deleteButton = event.target.closest('.btn-nt-delete');
            if (deleteButton) {
                event.preventDefault();
                eliminar(deleteButton.getAttribute('data-uuid'), deleteButton);
                return;
            }

            const estadoButton = event.target.closest('#filtros-estado-nueva-tarea [data-estado]');
            if (estadoButton) {
                event.preventDefault();
                d.querySelectorAll('#filtros-estado-nueva-tarea [data-estado]').forEach(btn => {
                    btn.classList.remove('active');
                });
                estadoButton.classList.add('active');
                estadoFiltro = estadoButton.getAttribute('data-estado') || '';
                applyFilters();
            }
        });

        d.addEventListener('input', (event) => {
            if (event.target?.id !== 'search-nueva-tarea') return;
            searchText = event.target.value || '';
            applyFilters();
        });

        const taskTab = d.getElementById('tab-proyectos-nueva-tarea');
        if (taskTab) {
            taskTab.addEventListener('shown.bs.tab', () => {
                showPanel();
                if (!lastRows.length) {
                    refresh();
                } else {
                    table?.redraw?.(true);
                }
            });
        }
    }

    function init() {
        if (initialized) return;
        initialized = true;
        bindEvents();
    }

    if (!w.Sintel) w.Sintel = {};
    w.Sintel.ProyectosNuevaTarea = {
        init,
        open,
        openEditor,
        refresh,
        getContext,
        hidePanel
    };

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(window, document);
