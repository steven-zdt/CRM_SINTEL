/**
 * productos_list.js - Controlador de Lista de Productos
 * Namespace: window.Sintel.Inventario.Productos.List
 *
 * La tabla "Productos" es DataTables 3.x (#tabla-productos, mismo patron ya
 * validado en Ventas/Bancos/Facturas/Clientes/Proveedores/Compras/Gastos/
 * Empleados/Proyectos -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md),
 * poblada via ajax contra POST /api/v1/inventario/productos/dt/.
 * ProductoTable/ProductoTableView (django-tables2) retirados.
 * Categoria/Servicio/ActivoFijo siguen en django-tables2/HTMX -- no
 * migradas en esta pasada. Los KPIs siguen server-rendered via HTMX
 * (kpis_productos.html).
 *
 * Nota: ProductoListSerializer expone "id" como el UUID (source='uuid') y
 * "pk" como el id entero -- por eso los renders/acciones usan row.id.
 *
 * Las acciones de fila (editar/kardex/eliminar) se delegan sobre document.body
 * (ya lo hacian antes de esta migracion, sin cambios).
 */
(function (w, d) {
    'use strict';

    const MOD = '[productos.list]';
    const CORE_API_BASE = '/api/v1/inventario/productos';
    let _delegated = false;
    let _eliminandoProducto = false;

    var TABLA_PRODUCTOS_SELECTOR = '#tabla-productos';
    var TABLA_PRODUCTOS_URL = '/api/v1/inventario/productos/dt/';
    var _productosTablaInicializada = false;

    function escapeHtmlProducto(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderNombreProducto(data, type, row) {
        var cat = row.categoria_nombre
            ? '<span class="badge bg-light text-secondary border" style="font-size:.65rem;font-weight:500">' + escapeHtmlProducto(row.categoria_nombre) + '</span>' : '';
        var cod = row.codigo
            ? '<span class="font-monospace text-muted me-1" style="font-size:.72rem">' + escapeHtmlProducto(row.codigo) + '</span>' : '';
        return '<div class="py-1 lh-sm"><div class="fw-semibold">' + escapeHtmlProducto(row.nombre || '—') + '</div>' +
            '<div class="d-flex align-items-center gap-1 mt-1">' + cod + cat + '</div></div>';
    }

    function renderStockProducto(data, type, row) {
        var actual = parseFloat(row.stock_actual || 0);
        var minimo = parseFloat(row.stock_minimo || 0);
        var alerta = actual <= minimo;
        var cls = alerta ? 'bg-danger' : 'bg-success';
        var icon = alerta ? '<i class="bi bi-exclamation-triangle-fill me-1" style="font-size:.7rem"></i>' : '';
        var unidad = row.unidad ? '<span class="text-muted">' + escapeHtmlProducto(row.unidad) + '</span>' : '';
        return '<div class="text-center lh-sm"><span class="badge ' + cls + '">' + icon + actual.toLocaleString('en-US', { maximumFractionDigits: 2 }) + ' ' + unidad + '</span>' +
            '<div class="text-muted mt-1" style="font-size:.68rem">mín ' + minimo.toLocaleString('en-US', { maximumFractionDigits: 2 }) + '</div></div>';
    }

    function renderPrecioProducto(data, type, row) {
        var precio = row.precio_venta ? '$' + parseFloat(row.precio_venta).toLocaleString('en-US', { maximumFractionDigits: 0 }) : '$0';
        var costo = row.costo_promedio
            ? '<div class="text-muted mt-1" style="font-size:.72rem">Costo: $' + parseFloat(row.costo_promedio).toLocaleString('en-US', { maximumFractionDigits: 0 }) + '</div>' : '';
        return '<div class="text-end lh-sm"><div class="fw-semibold">' + precio + '</div>' + costo + '</div>';
    }

    function renderEstadoProducto(value) {
        if (value) return '<span class="badge bg-success-subtle text-success border border-success-subtle">Activo</span>';
        return '<span class="badge bg-secondary-subtle text-secondary border">Inactivo</span>';
    }

    function renderAccionesProducto(data, type, row) {
        return '<div class="btn-group btn-group-sm" role="group">' +
            '<button type="button" class="btn btn-outline-primary btn-edit-producto" data-uuid="' + escapeHtmlProducto(row.id) + '" title="Editar" aria-label="Editar producto"><i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn btn-outline-info btn-ver-kardex" data-uuid="' + escapeHtmlProducto(row.id) + '" title="Kardex" aria-label="Ver kardex del producto"><i class="bi bi-list-ul"></i></button>' +
            '<button type="button" class="btn btn-outline-danger btn-delete-producto" data-uuid="' + escapeHtmlProducto(row.id) + '" title="Eliminar" aria-label="Eliminar producto"><i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    var PRODUCTOS_COLUMNS = [
        { data: null, title: 'Producto', render: renderNombreProducto },
        { data: null, title: 'Stock', render: renderStockProducto },
        { data: null, title: 'Precio / Costo', render: renderPrecioProducto },
        { data: 'activo', title: 'Estado', render: renderEstadoProducto },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccionesProducto },
    ];

    function initProductosTabla() {
        if (_productosTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_PRODUCTOS_SELECTOR, TABLA_PRODUCTOS_URL, PRODUCTOS_COLUMNS, {
            pageLength: 15,
            order: [[0, 'asc']],
        });
        _productosTablaInicializada = true;
    }

    function refresh() {
        if (w.Sintel && w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_PRODUCTOS_SELECTOR);
        }
        d.body.dispatchEvent(new CustomEvent('producto-updated'));
    }

    function init() {
        initProductosTabla();
    }

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

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initProductosTabla);
    } else {
        initProductosTabla();
    }

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
