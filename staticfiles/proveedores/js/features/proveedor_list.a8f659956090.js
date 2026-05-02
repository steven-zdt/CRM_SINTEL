/**
 * Proveedor List Module - Tabla de Proveedores con Tabulator
 * 
 * Namespace: window.Sintel.Proveedores.ProveedorList
 * Versión: v3.5
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Proveedores = window.Sintel.Proveedores || {};

    let proveedorIdEliminar = null;

    const defaultConfig = {
        layout: "fitColumns",
        pagination: true,
        paginationMode: "remote",
        ajaxURL: window.Sintel.Proveedores.API.proveedores.list,
        ajaxConfig: {
            method: "GET",
            headers: window.Sintel.Proveedores.getHeaders()
        },
        columns: [
            { title: "NIT", field: "numero_documento", headerFilter: true, width: 120 },
            { title: "Razón Social", field: "razon_social", headerFilter: true },
            { title: "Nombre Comercial", field: "nombre_comercial", headerFilter: true },
            { 
                title: "Estado", 
                field: "activo", 
                formatter: function(cell) {
                    return cell.getValue() ? 
                        '<span class="badge bg-success">Activo</span>' : 
                        '<span class="badge bg-danger">Inactivo</span>';
                }
            },
            { title: "Contacto", field: "email_contacto" },
            { title: "Teléfono", field: "telefono_contacto" },
            {
                title: "Acciones",
                width: 150,
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    return '<div class="btn-group btn-group-sm" role="group">' +
                        '<button class="btn btn-primary" onclick="Sintel.Proveedores.ProveedorList.editar(\'' + data.id + '\')" title="Editar"><i class="bi bi-pencil"></i></button>' +
                        '<button class="btn btn-info" onclick="Sintel.Proveedores.ProveedorList.verDetalle(\'' + data.id + '\')" title="Ver"><i class="bi bi-eye"></i></button>' +
                        '<button class="btn btn-danger" onclick="Sintel.Proveedores.ProveedorList.confirmarEliminar(\'' + data.id + '\')" title="Eliminar"><i class="bi bi-trash"></i></button>' +
                        '</div>';
                }
            }
        ]
    };

    function init(selector, config) {
        config = config || {};
        const element = document.querySelector(selector);
        if (!element) {
            console.error('[ProveedorList] Selector no encontrado:', selector);
            return null;
        }

        const mergedConfig = Object.assign({}, defaultConfig, config);
        const table = new Tabulator(element, mergedConfig);
        window.Sintel.Proveedores.table = table;

        const btnConfirmar = document.getElementById('btn-confirmar-eliminar');
        if (btnConfirmar) {
            btnConfirmar.addEventListener('click', ejecutarEliminar);
        }

        return table;
    }

    function reload() {
        if (window.Sintel.Proveedores.table) {
            window.Sintel.Proveedores.table.setData();
        }
    }

    function loadSummary(selector) {
        const element = document.querySelector(selector);
        if (!element) return;

        fetch(window.Sintel.Proveedores.API.proveedores.summary, {
            headers: window.Sintel.Proveedores.getHeaders()
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            element.innerHTML = '<div class="col-md-4"><div class="card"><div class="card-body"><h6 class="card-title text-muted">Total Proveedores</h6><h4 class="text-primary">' + (data.total_proveedores || 0) + '</h4></div></div></div>' +
                '<div class="col-md-4"><div class="card"><div class="card-body"><h6 class="card-title text-muted">Activos</h6><h4 class="text-success">' + (data.proveedores_activos || 0) + '</h4></div></div></div>' +
                '<div class="col-md-4"><div class="card"><div class="card-body"><h6 class="card-title text-muted">Inactivos</h6><h4 class="text-danger">' + (data.proveedores_inactivos || 0) + '</h4></div></div></div>';
        })
        .catch(function(err) {
            console.error('[ProveedorList] Error cargando summary:', err);
            element.innerHTML = '<div class="alert alert-warning">Error cargando resumen</div>';
        });
    }

    function editar(id) {
        const url = window.Sintel.Proveedores.API.proveedores.gestorOffcanvas + '?tipo=proveedor&id=' + id;
        htmx.ajax('GET', url, {
            target: '#offcanvas-container',
            swap: 'innerHTML'
        });
    }

    function verDetalle(id) {
        const url = window.Sintel.Proveedores.API.proveedores.detail(id);
        fetch(url, {
            headers: window.Sintel.Proveedores.getHeaders()
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            console.log('[ProveedorList] Detalle:', data);
        })
        .catch(function(err) { console.error('[ProveedorList] Error:', err); });
    }

    function crear() {
        const url = window.Sintel.Proveedores.API.proveedores.gestorOffcanvas + '?tipo=proveedor';
        htmx.ajax('GET', url, {
            target: '#offcanvas-container',
            swap: 'innerHTML'
        });
    }

    function confirmarEliminar(id) {
        proveedorIdEliminar = id;
        const modal = new bootstrap.Modal(document.getElementById('confirmarEliminarModal'));
        modal.show();
    }

    function ejecutarEliminar() {
        if (!proveedorIdEliminar) return;

        const url = window.Sintel.Proveedores.API.proveedores.detail(proveedorIdEliminar);
        
        fetch(url, {
            method: 'DELETE',
            headers: window.Sintel.Proveedores.getHeaders()
        })
        .then(function(r) {
            if (r.ok) {
                const modalEl = document.getElementById('confirmarEliminarModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                modal.hide();

                if (window.UIManager) {
                    window.UIManager.notifySuccess('Proveedor eliminado correctamente');
                }
                reload();
                loadSummary('#proveedores-summary');
            } else {
                return r.json().then(function(err) { throw err; });
            }
        })
        .catch(function(err) {
            console.error('[ProveedorList] Error eliminando:', err);
            if (window.UIManager) {
                window.UIManager.notifyError(err.error || 'Error al eliminar proveedor');
            }
        })
        .finally(function() {
            proveedorIdEliminar = null;
        });
    }

    window.Sintel.Proveedores.ProveedorList = {
        init,
        reload,
        loadSummary,
        editar,
        verDetalle,
        crear,
        confirmarEliminar,
        ejecutarEliminar
    };
})();
