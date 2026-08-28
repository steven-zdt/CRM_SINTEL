/**
 * servicios_list.js - Controlador de Lista de Servicios
 * Namespace: window.ServiciosList (legacy, consumido por servicios_editor.js)
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#servicios-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_servicios.html).
 * Columnas/orden/paginacion viven en tables.py/views.py (server-side).
 * Las acciones de fila (editar/eliminar) se delegan sobre document.body para
 * sobrevivir a los re-renders HTMX del panel.
 */
(function (w, d) {
    'use strict';

    const MOD = '[servicios.list]';
    const CORE_API_BASE = '/api/v1/inventario/servicios';
    let _delegated = false;

    function refresh() {
        d.body.dispatchEvent(new CustomEvent('servicio-updated'));
    }

    function init() {}

    function initDelegation() {
        if (_delegated) return;
        _delegated = true;

        d.body.addEventListener('click', async (e) => {
            // Botón Editar
            const btnEdit = e.target.closest('.btn-edit-servicio');
            if (btnEdit) {
                e.preventDefault();
                const uuid = btnEdit.dataset.uuid;
                if (!uuid) return;

                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `${CORE_API_BASE}/gestor-offcanvas/?id=${uuid}`, {
                        target: '#offcanvas-container-servicios',
                        swap: 'innerHTML'
                    });
                    const offcanvasEl = d.getElementById('offcanvas-inventario-servicio');
                    if (offcanvasEl) w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al cargar el formulario de servicio');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-servicio');
            if (btnDelete) {
                e.preventDefault();
                const uuid = btnDelete.dataset.uuid;
                if (!uuid) return;
                if (!(await w.UIManager?.confirm('¿Está seguro de eliminar este servicio? Esta acción no se puede deshacer.'))) return;

                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const deleteRes = await w.Sintel.Core.Http.request('DELETE', `${CORE_API_BASE}/${uuid}/`);
                    if (!deleteRes.ok) {
                        if (w.UIManager?.handleError) {
                            w.UIManager.handleError(deleteRes, MOD, {
                                modalSelector: '#offcanvas-inventario-servicio',
                                errorContainerSelector: '#form-inventario-servicio-feedback'
                            });
                        }
                        return;
                    }

                    const offcanvasServicio = d.getElementById('offcanvas-inventario-servicio');
                    if (offcanvasServicio && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const instance = bootstrap.Offcanvas.getInstance(offcanvasServicio);
                        if (instance) instance.hide();
                    }

                    if (w.SintelFeedback?.success) w.SintelFeedback.success('Servicio eliminado correctamente');
                    refresh();
                } catch (error) {
                    console.error(`${MOD} Error al eliminar servicio:`, error);
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al eliminar el servicio');
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
                return;
            }
        });
    }

    initDelegation();

    // Namespace legacy plano — servicios_editor.js lo consume directamente,
    // no via window.Sintel.Inventario.Servicios.List.
    if (!w.ServiciosList) {
        w.ServiciosList = {
            init: init,
            recargar: refresh
        };
    }

    // Alias anidado: list_servicios.html referencia
    // window.Sintel.Inventario.Servicios.List.recargar() (boton "Recargar",
    // mismo patron que Productos/Categorias). Sin esto el boton era un no-op.
    w.Sintel = w.Sintel || {};
    w.Sintel.Inventario = w.Sintel.Inventario || {};
    w.Sintel.Inventario.Servicios = w.Sintel.Inventario.Servicios || {};
    w.Sintel.Inventario.Servicios.List = w.ServiciosList;

})(window, document);
