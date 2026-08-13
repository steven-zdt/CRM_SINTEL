/**
 * Feature: Nueva Tarea - panel de tareas cortas dentro de Proyectos.
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX
 * (#tareas-cortas-panel). A diferencia de otros paneles migrados, este
 * requiere parametros dinamicos (empleado de contexto, estado, busqueda)
 * que un hx-trigger="load" estatico no puede expresar -- se dispara
 * explicitamente via htmx.ajax() en cada refresh() (mismo mecanismo que
 * ya usan los modulos *_editor.js para cargar offcanvas con parametros).
 */
(function (w, d) {
    'use strict';

    const MOD = '[proyectos.nueva_tarea.list]';
    const TABLA_URL = '/ui/proyectos/tareas-cortas/tabla/';
    let empleadoUuid = null;
    let empleadoNombre = '';
    let estadoFiltro = '';
    let searchText = '';
    let searchDebounce = null;

    function getPanel() {
        return d.getElementById('panel-nueva-tarea');
    }

    function getTablaPanel() {
        return d.getElementById('tareas-cortas-panel');
    }

    function setText(id, value) {
        const el = d.getElementById(id);
        if (el) el.textContent = value;
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

    async function refresh() {
        const target = getTablaPanel();
        if (!target || typeof htmx === 'undefined') return;

        const params = new URLSearchParams();
        if (empleadoUuid) params.set('empleado', empleadoUuid);
        if (estadoFiltro) params.set('estado', estadoFiltro);
        if (searchText.trim()) params.set('q', searchText.trim());

        try {
            await htmx.ajax('GET', `${TABLA_URL}?${params.toString()}`, {
                target: '#tareas-cortas-panel',
                swap: 'innerHTML',
            });
        } catch (error) {
            console.error(`${MOD} Error al refrescar`, error);
        }
    }

    function open(nextEmpleadoUuid = null, nextEmpleadoNombre = '') {
        setContext(nextEmpleadoUuid, nextEmpleadoNombre);
        showPanel();
        activateTaskTab();
        refresh();
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
                refresh();
            }
        });

        d.addEventListener('input', (event) => {
            if (event.target?.id !== 'search-nueva-tarea') return;
            searchText = event.target.value || '';
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(refresh, 400);
        });

        const taskTab = d.getElementById('tab-proyectos-nueva-tarea');
        if (taskTab) {
            taskTab.addEventListener('shown.bs.tab', () => {
                showPanel();
                refresh();
            });
        }
    }

    let initialized = false;
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
