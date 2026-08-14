/**
 * productos_list.js - Controlador de Lista de Productos
 * Namespace: window.Sintel.Inventario.Productos.List
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#productos-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_productos.html).
 * Columnas/orden/paginacion/KPIs viven en tables.py/views.py (server-side).
 * Las acciones de fila (editar/kardex/eliminar) se delegan sobre document.body
 * para sobrevivir a los re-renders HTMX del panel.
 */
(function (w, d) {
    'use strict';

    const MOD = '[productos.list]';
    const CORE_API_BASE = '/api/v1/inventario/productos';
    let _delegated = false;
    let _eliminandoProducto = false;

    function refresh() {
        d.body.dispatchEvent(new CustomEvent('producto-updated'));
    }

    function init() {}

    /**
     * Ver Kardex de producto
     * @param {string} productoUuid - UUID del producto
     */
    async function verKardex(productoUuid) {
        if (!productoUuid) {
            console.warn(`${MOD} UUID de producto no proporcionado`);
            return;
        }

        try {
            let productoRes, kardexRes;
            if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http) {
                productoRes = await w.Sintel.Core.Http.request('GET', `${CORE_API_BASE}/${productoUuid}/`);
                kardexRes = await w.Sintel.Core.Http.request('GET', `${CORE_API_BASE}/${productoUuid}/kardex/`);
            } else {
                console.error(`${MOD} API no disponible`);
                return;
            }

            if (!productoRes.ok || !productoRes.data) {
                if (w.UIManager?.handleError) w.UIManager.handleError(productoRes, MOD);
                return;
            }
            if (!kardexRes.ok) {
                if (w.UIManager?.handleError) w.UIManager.handleError(kardexRes, MOD);
                return;
            }

            const producto = productoRes.data;
            const movimientos = Array.isArray(kardexRes.data) ? kardexRes.data : (kardexRes.data.results || []);

            const infoEl = d.querySelector('#kardex-producto-info');
            if (infoEl) {
                const stockActual = parseFloat(producto.stock_actual || 0);
                const stockMinimo = parseFloat(producto.stock_minimo || 0);
                const stockColor = stockActual <= stockMinimo ? 'bg-danger' : 'bg-success';
                infoEl.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <strong>Código:</strong> ${producto.codigo || '-'}<br>
                            <strong>Nombre:</strong> ${producto.nombre || '-'}
                        </div>
                        <div class="col-md-6">
                            <strong>Stock Actual:</strong> <span class="badge ${stockColor}">${stockActual.toFixed(2)}</span><br>
                            <strong>Stock Mínimo:</strong> ${stockMinimo.toFixed(2)}
                        </div>
                    </div>
                `;
            }

            const tbody = d.querySelector('#table-kardex tbody');
            if (tbody) {
                if (movimientos.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No hay movimientos registrados</td></tr>';
                } else {
                    tbody.innerHTML = movimientos.map(mov => {
                        const fecha = mov.created_at ? new Date(mov.created_at).toLocaleString('es-CO') : '-';
                        const tipo = mov.tipo_display || mov.tipo || '-';
                        const cantidad = parseFloat(mov.cantidad || 0).toFixed(3);
                        const referencia = mov.origen_referencia || mov.cliente_referencia || '-';
                        const observaciones = mov.observaciones || '-';
                        const tipoColor = (tipo.includes('ENTRADA') || tipo.includes('entrada')) ? 'success' : 'danger';
                        return `
                            <tr>
                                <td>${fecha}</td>
                                <td><span class="badge bg-${tipoColor}">${tipo}</span></td>
                                <td class="text-end">${cantidad}</td>
                                <td>${referencia}</td>
                                <td>${observaciones}</td>
                            </tr>
                        `;
                    }).join('');
                }
            }

            const modalEl = d.querySelector('#modal-kardex');
            if (modalEl && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                bootstrap.Modal.getOrCreateInstance(modalEl).show();
            } else {
                console.warn(`${MOD} Modal #modal-kardex no encontrado o Bootstrap no disponible`);
            }
        } catch (error) {
            console.error(`${MOD} Error al obtener kardex:`, error);
            if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al cargar el kardex del producto');
        }
    }

    function initDelegation() {
        if (_delegated) return;
        _delegated = true;

        d.body.addEventListener('click', async (e) => {
            // Botón Editar
            const btnEdit = e.target.closest('.btn-edit-producto');
            if (btnEdit) {
                e.preventDefault();
                const uuid = btnEdit.dataset.uuid;
                if (!uuid) return;

                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `${CORE_API_BASE}/gestor-offcanvas/?id=${uuid}`, {
                        target: '#offcanvas-container-inventario',
                        swap: 'innerHTML'
                    });
                    const offcanvasEl = d.getElementById('offcanvas-inventario');
                    if (offcanvasEl) w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al cargar el formulario de producto');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Ver Kardex
            const btnKardex = e.target.closest('.btn-ver-kardex');
            if (btnKardex) {
                e.preventDefault();
                const uuid = btnKardex.dataset.uuid;
                if (!uuid) return;

                const originalHTML = btnKardex.innerHTML;
                btnKardex.disabled = true;
                btnKardex.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await verKardex(uuid);
                } finally {
                    btnKardex.disabled = false;
                    btnKardex.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-producto');
            if (btnDelete) {
                e.preventDefault();
                const uuid = btnDelete.dataset.uuid;
                if (!uuid) return;

                let productoRes;
                if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http) {
                    productoRes = await w.Sintel.Core.Http.request('GET', `${CORE_API_BASE}/${uuid}/`);
                } else {
                    console.error(`${MOD} API no disponible`);
                    return;
                }
                if (!productoRes.ok || !productoRes.data) {
                    if (w.UIManager?.handleError) w.UIManager.handleError(productoRes, MOD);
                    return;
                }

                const producto = productoRes.data;
                if (producto.activo) {
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('El producto está activo. Desactívelo primero.');
                    return;
                }

                let mensajeConfirmacion = '¿Está seguro de eliminar este producto?';
                const stock = parseFloat(producto.stock_actual || 0);
                if (stock > 0) {
                    mensajeConfirmacion += `\n\nEste producto tiene ${stock} unidades en stock.`;
                }
                mensajeConfirmacion += '\n\n⚠️ ADVERTENCIA: Esta acción eliminará:';
                mensajeConfirmacion += '\n- El producto';
                mensajeConfirmacion += '\n- Todo el stock asociado';
                mensajeConfirmacion += '\n- Todo el historial de movimientos (Kardex)';
                mensajeConfirmacion += '\n\nEsta acción es irreversible.';

                if (!(await w.UIManager?.confirm(mensajeConfirmacion))) return;

                _eliminandoProducto = true;
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const deleteRes = await w.Sintel.Core.Http.request('DELETE', `${CORE_API_BASE}/${uuid}/`);
                    if (!deleteRes.ok) {
                        if (w.UIManager?.handleError) w.UIManager.handleError(deleteRes, MOD);
                        return;
                    }

                    const offcanvasProducto = d.getElementById('offcanvas-inventario');
                    if (offcanvasProducto && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const instance = bootstrap.Offcanvas.getInstance(offcanvasProducto);
                        if (instance) instance.hide();
                    }

                    if (w.SintelFeedback?.success) w.SintelFeedback.success('Producto eliminado correctamente. Stock y kardex eliminados.');
                    refresh();
                } catch (error) {
                    console.error(`${MOD} Error al eliminar producto:`, error);
                    if (w.SintelFeedback?.error) w.SintelFeedback.error('Error al eliminar el producto');
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                    _eliminandoProducto = false;
                }
                return;
            }
        });
    }

    initDelegation();

    w.Sintel = w.Sintel || {};
    w.Sintel.Inventario = w.Sintel.Inventario || {};
    w.Sintel.Inventario.Productos = w.Sintel.Inventario.Productos || {};
    w.Sintel.Inventario.Productos.List = {
        init: init,
        recargar: refresh
    };

    // Deprecated fallback (compatibilidad con llamadas legacy)
    w.ProductosList = w.Sintel.Inventario.Productos.List;

})(window, document);
