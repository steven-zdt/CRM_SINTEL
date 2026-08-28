/**
 * categorias_list.js - Controlador de Lista de Categorías
 * Namespace: window.Sintel.Inventario.Categorias.List
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#categorias-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_categorias.html).
 * Columnas/orden/paginacion viven en tables.py/views.py (server-side).
 * Las acciones de fila (editar/eliminar) se delegan sobre document.body para
 * sobrevivir a los re-renders HTMX del panel.
 */
(function (w, d) {
    'use strict';

    const MOD = '[categorias.list]';
    const CORE_API_BASE = '/api/v1/inventario/categorias';
    let _delegated = false;

    function refresh() {
        d.body.dispatchEvent(new CustomEvent('categoria-updated'));
    }

    // init()/redraw() ya no inicializan nada (el panel HTMX se auto-carga con
    // hx-trigger="load"); se conservan como no-ops por compatibilidad con
    // quien las invoque al activarse el tab de categorías.
    function init() {}

    function initDelegation() {
        if (_delegated) return;
        _delegated = true;

        d.body.addEventListener('click', async (e) => {
            const btnEdit = e.target.closest('.btn-edit-categoria');
            if (btnEdit) {
                e.preventDefault();
                const uuid = btnEdit.dataset.uuid;
                if (!uuid) return;
                try {
                    await htmx.ajax('GET', `${CORE_API_BASE}/gestor-offcanvas/?id=${uuid}`, {
                        target: '#offcanvas-container-categorias',
                        swap: 'innerHTML'
                    });
                    const offcanvasEl = d.getElementById('offcanvas-categorias');
                    if (offcanvasEl) w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al cargar el formulario de categoría');
                }
                return;
            }

            const btnDelete = e.target.closest('.btn-delete-categoria');
            if (btnDelete) {
                e.preventDefault();
                const uuid = btnDelete.dataset.uuid;
                if (!uuid) return;
                if (!(await w.UIManager?.confirm('¿Está seguro de eliminar esta categoría? Los ítems asociados quedarán sin categoría.'))) return;

                btnDelete.disabled = true;
                const originalHTML = btnDelete.innerHTML;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const res = await w.Sintel.Core.Http.request('DELETE', `${CORE_API_BASE}/${uuid}/`);
                    if (!res.ok) {
                        if (w.UIManager?.handleError) {
                            w.UIManager.handleError(res, MOD);
                        } else if (w.SintelFeedback?.error) {
                            w.SintelFeedback.error('Error al eliminar la categoría');
                        }
                        btnDelete.disabled = false;
                        btnDelete.innerHTML = originalHTML;
                        return;
                    }
                    if (w.SintelFeedback?.success) w.SintelFeedback.success('Categoría eliminada correctamente');
                    refresh();
                } catch (error) {
                    console.error(`${MOD} Error al eliminar categoría:`, error);
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al eliminar la categoría');
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
                return;
            }
        });
    }

    initDelegation();

    w.Sintel = w.Sintel || {};
    w.Sintel.Inventario = w.Sintel.Inventario || {};
    w.Sintel.Inventario.Categorias = w.Sintel.Inventario.Categorias || {};
    w.Sintel.Inventario.Categorias.List = {
        init: init,
        recargar: refresh
    };

    // Deprecated fallback (compatibilidad con llamadas legacy)
    w.CategoriasList = w.Sintel.Inventario.Categorias.List;

})(window, document);
