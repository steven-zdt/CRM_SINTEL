/**
 * Feature: Listado Proyectos
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#proyectos-panel,
 * cargada por atributos hx-get/hx-trigger declarados en proyectos_list.html).
 * Columnas, KPIs agregados y filtro por fase viven en tables.py/views.py/
 * selectors.py (server-side). Este archivo solo conserva:
 * - Delegacion global de clicks (editar/eliminar/tareas-cortas) sobre
 *   document.body, robusta a los swaps HTMX del panel.
 * - Toggle visual de la clase "active" en los chips de fase (UI pura, no
 *   dispara la carga de datos por si sola -- eso lo hace el atributo
 *   hx-get del propio boton).
 */
(function (w, d) {
    'use strict';

    const MOD = '[proyectos.list]';

    // ─── Chips de Fase: toggle visual ──────────────────────────────────────────

    function initFiltrosFase() {
        const contenedor = d.getElementById('filtros-fase-proyectos');
        if (!contenedor) return;
        contenedor.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-fase]');
            if (!btn) return;
            contenedor.querySelectorAll('[data-fase]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    }

    // ─── Event Delegation (Editar / Eliminar / Tareas Cortas) ──────────────────

    function initListEvents() {
        d.body.addEventListener('click', async (e) => {
            // Tareas cortas: delegado por proyectos.nueva_tarea.list.js
            // (escucha .btn-tareas-cortas sobre document.body, no se toca aqui)

            // Editar
            const btnEdit = e.target.closest('#proyectos-panel .btn-edit-proyecto');
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
            const btnDel = e.target.closest('#proyectos-panel .btn-delete-proyecto');
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

    // Funcion global de refresco: dispara el evento que el panel HTMX escucha
    // via hx-trigger="load, proyecto-updated from:body" (ver proyectos_list.html).
    w.refreshProyectosTable = function () {
        d.body.dispatchEvent(new CustomEvent('proyecto-updated'));
    };

    function init() {
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
