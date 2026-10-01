/**
 * activos_list.js - Controlador de Lista de Activos Fijos
 * Namespace: window.ActivosList (legacy, consumido por activos_editor.js)
 *
 * Tabla "Activos Fijos" es DataTables 3.x (#tabla-activos, mismo patron ya
 * validado en Ventas/Bancos/Facturas/Clientes/Proveedores/Compras/Gastos/
 * Empleados/Proyectos/Inventario -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via ajax
 * contra POST /api/v1/inventario/activos/dt/. ActivoFijoTable/
 * ActivoFijoTableView (django-tables2) retirados. Los KPIs (total/valor
 * libros/por estado) siguen server-rendered via HTMX (kpis_activos.html,
 * ActivoFijoKpisView) -- mismo patron ya usado en Ventas/Compras/Gastos/
 * Proyectos.
 *
 * Las acciones de fila (editar/eliminar) se delegan sobre document.body
 * (persistente -- la tabla se recrea via ajax.reload(), nunca via
 * innerHTML swap de un contenedor).
 */
(function (w, d) {
    'use strict';

    const MOD = '[activos.list]';
    const CORE_API_BASE = '/api/v1/inventario/activos';
    const TABLA_SELECTOR = '#tabla-activos';
    const TABLA_URL = '/api/v1/inventario/activos/dt/';
    let _delegated = false;
    let _tablaInicializada = false;

    var BADGE_ESTADO = {
        ACTIVO: ['bg-success', 'bi-check-circle-fill', 'En Uso'],
        MANTENIMIENTO: ['bg-warning', 'bi-tools', 'Mantenimiento'],
        BAJA: ['bg-danger', 'bi-x-circle-fill', 'De Baja'],
        VENDIDO: ['bg-secondary', 'bi-tag-fill', 'Vendido'],
    };

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderActivo(data, type, row) {
        var cat = row.categoria ? '<span class="badge bg-light text-secondary border" style="font-size:.65rem;font-weight:500">' +
            escapeHtml(row.categoria_nombre || '') + '</span>' : '';
        var cod = row.codigo ? '<span class="font-monospace text-muted me-1" style="font-size:.72rem">' + escapeHtml(row.codigo) + '</span>' : '';
        var resp = row.responsable ? '<div class="mt-1"><span class="text-muted" style="font-size:.72rem"><i class="bi bi-person me-1"></i>' +
            escapeHtml(row.responsable) + '</span></div>' : '';
        return '<div class="py-1 lh-sm"><div class="fw-semibold">' + escapeHtml(row.nombre || '—') + '</div>' +
            '<div class="d-flex align-items-center gap-1 mt-1">' + cod + cat + '</div>' + resp + '</div>';
    }

    function renderAdquisicion(data, type, row) {
        var fecha = row.fecha_adquisicion ? new Date(row.fecha_adquisicion + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
        var costo = row.costo_adquisicion ? '<div class="fw-semibold mt-1">$' + Number(row.costo_adquisicion).toLocaleString('en-US', { maximumFractionDigits: 0 }) + '</div>' : '';
        return '<div class="text-end lh-sm"><div class="text-muted" style="font-size:.8rem">' + fecha + '</div>' + costo + '</div>';
    }

    function renderEstado(data, type, row) {
        var cfg = BADGE_ESTADO[row.estado] || ['bg-secondary', 'bi-question-circle', row.estado_display || row.estado || '—'];
        return '<span class="badge ' + cfg[0] + '"><i class="bi ' + cfg[1] + ' me-1"></i>' + escapeHtml(cfg[2]) + '</span>';
    }

    function renderAcciones(data, type, row) {
        return '<div class="btn-group btn-group-sm" role="group">' +
            '<button type="button" class="btn btn-outline-primary btn-edit-activo" data-uuid="' + escapeHtml(row.id) + '" title="Editar">' +
            '<i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn btn-outline-danger btn-delete-activo" data-uuid="' + escapeHtml(row.id) + '" title="Eliminar">' +
            '<i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    // Nota: en ActivoFijoListSerializer el campo JSON "id" es en realidad el
    // UUID (source='uuid') -- "pk" es el id entero. Los botones de accion
    // usan row.id (mismo patron ya documentado en productos_list.js).
    var COLUMNS = [
        { data: null, title: 'Activo', render: renderActivo },
        { data: null, title: 'Adquisición', className: 'text-end', render: renderAdquisicion },
        { data: null, title: 'Estado', render: renderEstado },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
    ];

    function initTabla() {
        if (_tablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, TABLA_URL, COLUMNS, {
            pageLength: 20,
            order: [[0, 'asc']],
        });
        _tablaInicializada = true;
    }

    function refresh() {
        if (w.Sintel && w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
        }
        // Los KPIs siguen server-rendered via HTMX (kpis_activos.html).
        d.body.dispatchEvent(new CustomEvent('activo-updated'));
    }

    function init() {
        initTabla();
    }

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
                    // T-9: delega a la SSoT de endpoints (inventario.api.js).
                    activoRes = await w.Sintel.Inventario.API.activos.get(uuid);
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
                    const deleteRes = await w.Sintel.Inventario.API.activos.delete(uuid);
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

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initTabla);
    } else {
        initTabla();
    }

    // Namespace legacy plano — activos_editor.js lo consume directamente.
    if (!w.ActivosList) {
        w.ActivosList = {
            init: init,
            recargar: refresh
        };
    }

})(window, document);
