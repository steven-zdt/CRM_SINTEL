/**
 * Empleado List Module - Tabla de Empleados con Tabulator
 * 
 * Namespace: window.Sintel.Empleados.EmpleadoList
 * Versión: v2.61.4
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};

    // ID del empleado a eliminar (para el modal)
    let empleadoIdEliminar = null;

    /**
     * Configuración de la tabla de empleados
     */
    const defaultConfig = {
        layout: "fitColumns",
        pagination: true,
        paginationMode: "remote",
        ajaxURL: window.Sintel.Empleados.API.empleados.list,
        ajaxConfig: {
            method: "GET",
            headers: window.Sintel.Empleados.getHeaders()
        },
        columns: [
            { title: "Documento", field: "numero_documento", headerFilter: true, width: 120 },
            { title: "Nombre", field: "primer_nombre", headerFilter: true },
            { title: "Apellido", field: "primer_apellido", headerFilter: true },
            { 
                title: "Estado", 
                field: "estado", 
                formatter: function(cell) {
                    const estado = cell.getValue();
                    const badgeClass = estado === 'ACTIVO' ? 'bg-success' : 
                                       estado === 'RETIRADO' ? 'bg-danger' : 'bg-secondary';
                    return '<span class="badge ' + badgeClass + '">' + (estado || 'N/A') + '</span>';
                }
            },
            { title: "Ingreso", field: "fecha_ingreso", width: 100 },
            {
                title: "Acciones",
                width: 150,
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    return '<div class="btn-group btn-group-sm" role="group">' +
                        '<button class="btn btn-primary" onclick="Sintel.Empleados.EmpleadoList.editar(\'' + data.id + '\')" title="Editar"><i class="bi bi-pencil"></i></button>' +
                        '<button class="btn btn-info" onclick="Sintel.Empleados.EmpleadoList.verDetalle(\'' + data.id + '\')" title="Ver Detalle"><i class="bi bi-eye"></i></button>' +
                        '<button class="btn btn-danger" onclick="Sintel.Empleados.EmpleadoList.confirmarEliminar(\'' + data.id + '\')" title="Eliminar"><i class="bi bi-trash"></i></button>' +
                        '</div>';
                }
            }
        ]
    };

    /**
     * Inicializa la tabla de empleados
     */
    function init(selector, config = {}) {
        const element = document.querySelector(selector);
        if (!element) {
            console.error('[EmpleadoList] Selector no encontrado:', selector);
            return null;
        }

        const mergedConfig = { ...defaultConfig, ...config };
        const table = new Tabulator(element, mergedConfig);

        // Guardar referencia
        window.Sintel.Empleados.table = table;

        // Configurar evento de confirmar eliminar
        const btnConfirmar = document.getElementById('btn-confirmar-eliminar');
        if (btnConfirmar) {
            btnConfirmar.addEventListener('click', ejecutarEliminar);
        }

        return table;
    }

    /**
     * Cargar resumen de empleados
     */
    function loadSummary(selector) {
        const element = document.querySelector(selector);
        if (!element) return;

        fetch(window.Sintel.Empleados.API.empleados.summary, {
            headers: window.Sintel.Empleados.getHeaders()
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            element.innerHTML = '<div class="col-md-3"><div class="card"><div class="card-body"><h6 class="card-title text-muted">Total Empleados</h6><h4 class="text-primary">' + (data.total_empleados || 0) + '</h4></div></div></div>' +
                '<div class="col-md-3"><div class="card"><div class="card-body"><h6 class="card-title text-muted">Activos</h6><h4 class="text-success">' + (data.empleados_activos || 0) + '</h4></div></div></div>' +
                '<div class="col-md-3"><div class="card"><div class="card-body"><h6 class="card-title text-muted">Retirados</h6><h4 class="text-danger">' + (data.empleados_retirados || 0) + '</h4></div></div></div>' +
                '<div class="col-md-3"><div class="card"><div class="card-body"><h6 class="card-title text-muted">Nominas Mes</h6><h4 class="text-info">' + (data.total_nomina_mes || 0) + '</h4></div></div></div>';
        })
        .catch(function(err) {
            console.error('[EmpleadoList] Error cargando summary:', err);
            element.innerHTML = '<div class="alert alert-warning">Error cargando resumen</div>';
        });
    }

    /**
     * Ver detalle de empleado
     */
    function verDetalle(id) {
        const url = window.Sintel.Empleados.API.empleados.detail(id);
        
        fetch(url, {
            headers: window.Sintel.Empleados.getHeaders()
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            console.log('[EmpleadoList] Detalle:', data);
        })
        .catch(function(err) { console.error('[EmpleadoList] Error:', err); });
    }

    /**
     * Mostrar modal de confirmacion para eliminar
     */
    function confirmarEliminar(id) {
        empleadoIdEliminar = id;
        const modal = new bootstrap.Modal(document.getElementById('confirmarEliminarModal'));
        modal.show();
    }

    /**
     * Ejecutar eliminacion del empleado
     */
    function ejecutarEliminar() {
        if (!empleadoIdEliminar) return;

        const url = window.Sintel.Empleados.API.empleados.detail(empleadoIdEliminar);
        
        fetch(url, {
            method: 'DELETE',
            headers: window.Sintel.Empleados.getHeaders()
        })
        .then(function(r) {
            if (r.ok) {
                const modalEl = document.getElementById('confirmarEliminarModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                modal.hide();

                if (window.UIManager) {
                    window.UIManager.notifySuccess('Empleado eliminado correctamente');
                }

                reload();
                loadSummary('#empleados-summary');
            } else {
                return r.json().then(function(err) { throw err; });
            }
        })
        .catch(function(err) {
            console.error('[EmpleadoList] Error eliminando:', err);
            if (window.UIManager) {
                window.UIManager.notifyError(err.error || 'Error al eliminar empleado');
            }
        })
        .finally(function() {
            empleadoIdEliminar = null;
        });
    }

    /**
     * Recargar datos de la tabla
     */
    function reload() {
        if (window.Sintel.Empleados.table) {
            window.Sintel.Empleados.table.setData();
        }
    }

    /**
     * Abrir offcanvas para editar empleado
     */
    function editar(id) {
        const url = window.Sintel.Empleados.API.empleados.gestorOffcanvas + `?tipo=empleado&id=${id}`;
        
        htmx.ajax('GET', url, {
            target: '#offcanvas-container',
            swap: 'innerHTML'
        });
    }

    /**
     * Abrir offcanvas para crear empleado
     */
    function crear() {
        const url = window.Sintel.Empleados.API.empleados.gestorOffcanvas + '?tipo=empleado';
        
        htmx.ajax('GET', url, {
            target: '#offcanvas-container',
            swap: 'innerHTML'
        });
    }

    // Exportar modulo
    window.Sintel.Empleados.EmpleadoList = {
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
