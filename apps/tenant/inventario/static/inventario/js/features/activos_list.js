/**
 * activos_list.js - Controlador de Lista de Activos Fijos
 * Namespace: window.ActivosList (legacy, consumido por activos_editor.js)
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#activos-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_activos.html).
 * Columnas/orden/paginacion/KPIs viven en tables.py/views.py (server-side).
 * Las acciones de fila (editar/eliminar) se delegan sobre document.body para
 * sobrevivir a los re-renders HTMX del panel.
 */
(function (w, d) {
    'use strict';

    const MOD = '[activos.list]';
    const CORE_API_BASE = '/api/v1/inventario/activos';
    let _delegated = false;

    function refresh() {
        d.body.dispatchEvent(new CustomEvent('activo-updated'));
    }

    function init() {}

    function initDelegation() {
        if (_delegated) return;
        _delegated = true;

        d.body.addEventListener('click', async (e) => {
            // Botón Editar
            const btnEdit = e.target.closest('.btn-edit-activo');
            if (btnEdit) {
                e.preventDefault();
                const uuid = btnEdit.dataset.uuid;
                if (!uuid) return;

                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `${CORE_API_BASE}/gestor-offcanvas/?id=${uuid}`, {
                        target: '#offcanvas-container-activos',
                        swap: 'innerHTML'
                    });
                    const offcanvasEl = d.getElementById('offcanvas-activos');
                    if (offcanvasEl) w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al cargar el formulario de activo');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-activo');
            if (btnDelete) {
                e.preventDefault();
                const uuid = btnDelete.dataset.uuid;
                if (!uuid) return;

                let activoRes;
                if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http) {
                    activoRes = await w.Sintel.Core.Http.request('GET', `${CORE_API_BASE}/${uuid}/`);
                } else {
                    console.error(`${MOD} API no disponible`);
                    return;
                }
                if (!activoRes.ok || !activoRes.data) {
                    if (w.UIManager?.handleError) w.UIManager.handleError(activoRes, MOD);
                    return;
                }

                const activo = activoRes.data;
                if (activo.estado === 'ACTIVO') {
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('El activo está activo. Desactívelo primero.');
                    return;
                }

                if (!(await w.UIManager?.confirm('¿Está seguro de eliminar este activo fijo?'))) return;

                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const deleteRes = await w.Sintel.Core.Http.request('DELETE', `${CORE_API_BASE}/${uuid}/`);
                    if (!deleteRes.ok) {
                        if (w.UIManager?.handleError) w.UIManager.handleError(deleteRes, MOD);
                        return;
                    }

                    const offcanvasActivo = d.getElementById('offcanvas-activos');
                    if (offcanvasActivo && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const instance = bootstrap.Offcanvas.getInstance(offcanvasActivo);
                        if (instance) instance.hide();
                    }

                    if (w.SintelFeedback?.success) w.SintelFeedback.success('Activo fijo eliminado correctamente');
                    refresh();
                } catch (error) {
                    console.error(`${MOD} Error al eliminar activo:`, error);
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al eliminar el activo');
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
                return;
            }
        });
    }

    initDelegation();

    // Namespace legacy plano — activos_editor.js lo consume directamente.
    if (!w.ActivosList) {
        w.ActivosList = {
            init: init,
            recargar: refresh
        };
    }

})(window, document);
