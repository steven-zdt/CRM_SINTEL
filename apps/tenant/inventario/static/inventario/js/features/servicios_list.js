/**
 * servicios_list.js - Controlador de Lista de Servicios
 * Namespace: window.ServiciosList (legacy, consumido por servicios_editor.js)
 *
 * Tabla "Servicios" es DataTables 3.x (#tabla-servicios, mismo patron ya
 * validado en Ventas/Bancos/Facturas/Clientes/Proveedores/Compras/Gastos/
 * Empleados/Proyectos/Inventario -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via ajax
 * contra POST /api/v1/inventario/servicios/dt/. ServicioTable/
 * ServicioTableView (django-tables2) retirados.
 *
 * Las acciones de fila (editar/eliminar) se delegan sobre document.body
 * (persistente -- la tabla se recrea via ajax.reload(), nunca via
 * innerHTML swap de un contenedor).
 */
(function (w, d) {
    'use strict';

    const MOD = '[servicios.list]';
    const CORE_API_BASE = '/api/v1/inventario/servicios';
    const TABLA_SELECTOR = '#tabla-servicios';
    const TABLA_URL = '/api/v1/inventario/servicios/dt/';
    let _delegated = false;
    let _tablaInicializada = false;

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderCodigo(value) {
        return value ? escapeHtml(value) : '<span class="text-muted">---</span>';
    }

    function renderCategoria(data, type, row) {
        if (!row.categoria) return '<span class="text-muted">Sin categoría</span>';
        return escapeHtml(row.categoria_nombre || '');
    }

    function renderPrecioVenta(value) {
        var n = parseFloat(value) || 0;
        return '$' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
    }

    function renderActivo(value) {
        if (value) return '<span class="badge bg-success">Activo</span>';
        return '<span class="badge bg-secondary">Inactivo</span>';
    }

    function renderAcciones(data, type, row) {
        return '<div class="btn-group btn-group-sm" role="group">' +
            '<button type="button" class="btn btn-outline-primary btn-edit-servicio" data-uuid="' + escapeHtml(row.id) + '" title="Editar">' +
            '<i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn btn-outline-danger btn-delete-servicio" data-uuid="' + escapeHtml(row.id) + '" title="Eliminar">' +
            '<i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    // Nota: en ServicioListSerializer el campo JSON "id" es en realidad el
    // UUID (source='uuid') -- "pk" es el id entero. Los botones de accion
    // usan row.id (mismo patron ya documentado en productos_list.js).
    var COLUMNS = [
        { data: 'codigo', title: 'Código', render: function (v) { return renderCodigo(v); } },
        { data: 'nombre', title: 'Servicio' },
        { data: null, title: 'Categoría', render: renderCategoria },
        { data: 'precio_venta', title: 'Precio Venta', render: function (v) { return renderPrecioVenta(v); } },
        { data: 'activo', title: 'Estado', render: function (v) { return renderActivo(v); } },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
    ];

    function initTabla() {
        if (_tablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, TABLA_URL, COLUMNS, {
            pageLength: 20,
            order: [[1, 'asc']],
        });
        _tablaInicializada = true;
    }

    function refresh() {
        if (w.Sintel && w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
        }
    }

    function init() {
        initTabla();
    }

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
                    // T-9: delega a la SSoT de endpoints (inventario.api.js).
                    const deleteRes = await w.Sintel.Inventario.API.servicios.delete(uuid);
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

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initTabla);
    } else {
        initTabla();
    }

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
