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

    // UUID del empleado a eliminar (para el modal)
    let empleadoIdEliminar = null;
    let empleadoNombreEliminar = null;

    /**
     * Handler con event delegation para acciones de la celda
     */
    function handleCellAction(e, cell) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        
        switch (action) {
            case 'editar':           editar(id);         break;
            case 'crear-contrato':
            case 'editar-contrato':
                if (window.Sintel.Empleados.ContratoEditor) {
                    window.Sintel.Empleados.ContratoEditor.openContratoOffcanvas(id);
                }
                break;
            case 'registrar-nomina': registrarNomina(id);   break;
            case 'historial':
                if (window.Sintel.Empleados.NominaHistorial) {
                    window.Sintel.Empleados.NominaHistorial.openHistorial(id);
                }
                break;
            case 'eliminar': {
                const rowData = cell.getRow().getData();
                const nombre = `${rowData.primer_nombre || ''} ${rowData.primer_apellido || ''}`.trim();
                const doc = rowData.numero_documento || '';
                confirmarEliminar(id, nombre, doc);
                break;
            }
        }
    }

    /**
     * Definición de columnas para la tabla
     */
    function getColumnas() {
        return [
            { title: "Documento", field: "numero_documento", headerFilter: "input", width: 120 },
            { title: "Nombre", field: "primer_nombre", headerFilter: "input" },
            { title: "Apellido", field: "primer_apellido", headerFilter: "input" },
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
                title: 'Acciones',
                width: 250,
                hozAlign: 'center',
                headerSort: false,
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const id = data.id;
                    const uuid = data.uuid;
                    const tieneContrato = data.tiene_contrato_activo;
                    const esRetirado = data.estado === 'RETIRADO';

                    let html = '<div class="btn-group btn-group-sm">';
                    html += `<button data-action="editar" data-id="${uuid}" class="btn btn-outline-primary" title="Editar"><i class="bi bi-pencil"></i></button>`;
                    if (!esRetirado) {
                        html += `<button data-action="${tieneContrato ? 'editar-contrato' : 'crear-contrato'}" data-id="${id}" class="btn btn-outline-success" title="Contrato"><i class="bi bi-file-text"></i></button>`;
                        if (tieneContrato) {
                            html += `<button data-action="registrar-nomina" data-id="${id}" class="btn btn-outline-info" title="Nomina"><i class="bi bi-cash-coin"></i></button>`;
                            html += `<button data-action="historial" data-id="${id}" class="btn btn-outline-secondary" title="Historial"><i class="bi bi-clock-history"></i></button>`;
                        }
                    } else {
                        html += `<button data-action="eliminar" data-id="${uuid}" class="btn btn-outline-danger" title="Eliminar permanentemente"><i class="bi bi-trash"></i></button>`;
                    }
                    html += '</div>';
                    return html;
                },
                cellClick: (e, cell) => handleCellAction(e, cell)
            }
        ];
    }

    /**
     * Inicializa la tabla de empleados usando TabulatorFactory
     */
    async function init(selector, config = {}) {
        // Esperar a que TabulatorFactory esté disponible
        if (!window.TabulatorFactory) {
            console.warn('[EmpleadoList] TabulatorFactory no disponible, reintentando en 100ms...');
            setTimeout(() => init(selector, config), 100);
            return;
        }

        const apiUrl = window.Sintel.Empleados.API.empleados.list;
        const columns = getColumnas();
        
        // Opciones para TabulatorFactory
        const options = {
            searchInputSelector: config.searchInputSelector || '#search-empleado',
            paginationSize: config.paginationSize || 10,
            ...config
        };

        const table = window.TabulatorFactory.create(selector, apiUrl, columns, options);

        if (table) {
            // Guardar referencia
            window.Sintel.Empleados.table = table;

            // Configurar evento de confirmar eliminar
            const btnConfirmar = document.getElementById('btn-confirmar-eliminar');
            if (btnConfirmar) {
                // Eliminar listeners previos para evitar duplicados
                const newBtnConfirmar = btnConfirmar.cloneNode(true);
                btnConfirmar.parentNode.replaceChild(newBtnConfirmar, btnConfirmar);
                newBtnConfirmar.addEventListener('click', ejecutarEliminar);
            }
        }

        return table;
    }

    /**
     * Cargar resumen de empleados usando window.http
     */
    async function loadSummary(selector) {
        const element = document.querySelector(selector);
        if (!element) return;

        const url = window.Sintel.Empleados.API.empleados.summary;
        
        try {
            const res = await window.http('GET', url);
            if (res.ok) {
                const data = res.data;
                element.innerHTML = `
                    <div class="col-md-3">
                        <div class="card bg-glass border-0 shadow-sm">
                            <div class="card-body">
                                <h6 class="card-title text-muted mb-0">Total Empleados</h6>
                                <h4 class="text-primary mb-0">${data.total_empleados || 0}</h4>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-glass border-0 shadow-sm">
                            <div class="card-body">
                                <h6 class="card-title text-muted mb-0">Activos</h6>
                                <h4 class="text-success mb-0">${data.empleados_activos || 0}</h4>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-glass border-0 shadow-sm">
                            <div class="card-body">
                                <h6 class="card-title text-muted mb-0">Retirados</h6>
                                <h4 class="text-danger mb-0">${data.empleados_retirados || 0}</h4>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-glass border-0 shadow-sm">
                            <div class="card-body">
                                <h6 class="card-title text-muted mb-0">Nóminas Mes</h6>
                                <h4 class="text-info mb-0">${data.total_nomina_mes || 0}</h4>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                throw new Error(res.data?.detail || 'Error cargando resumen');
            }
        } catch (err) {
            console.error('[EmpleadoList] Error cargando summary:', err);
            element.innerHTML = '<div class="alert alert-warning">Error cargando resumen</div>';
        }
    }

    /**
     * Ver detalle de empleado usando window.http
     */
    async function verDetalle(id) {
        const url = window.Sintel.Empleados.API.empleados.detail(id);
        
        try {
            const res = await window.http('GET', url);
            if (res.ok) {
                console.log('[EmpleadoList] Detalle:', res.data);
                return res.data;
            }
        } catch (err) {
            console.error('[EmpleadoList] Error:', err);
        }
    }

    /**
     * Mostrar modal de confirmacion para eliminar.
     * @param {string} uuid  - UUID del empleado (lookup field del backend)
     * @param {string} nombre - Nombre completo del empleado
     * @param {string} doc   - Numero de documento
     */
    function confirmarEliminar(uuid, nombre, doc) {
        empleadoIdEliminar = uuid;
        empleadoNombreEliminar = nombre;

        // Actualizar cuerpo del modal con datos del empleado
        const modalBody = document.querySelector('#confirmarEliminarModal .modal-body');
        if (modalBody) {
            modalBody.innerHTML = `
                <p class="mb-2">Esta a punto de eliminar permanentemente al empleado:</p>
                <div class="alert alert-warning py-2 mb-3">
                    <strong>${nombre || 'Empleado'}</strong>
                    ${doc ? `<span class="text-muted ms-2">Doc: ${doc}</span>` : ''}
                </div>
                <p class="text-danger mb-1"><strong>Esta accion eliminara en cascada:</strong></p>
                <ul class="text-danger small mb-3">
                    <li>Todos sus contratos</li>
                    <li>Todos sus registros de nomina</li>
                </ul>
                <p class="text-danger fw-bold mb-0">Esta accion no se puede deshacer.</p>
            `;
        }

        const modalElement = document.getElementById('confirmarEliminarModal');
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        }
    }

    /**
     * Ejecutar eliminacion del empleado usando window.http
     */
    async function ejecutarEliminar() {
        if (!empleadoIdEliminar) return;

        const url = window.Sintel.Empleados.API.empleados.detail(empleadoIdEliminar);
        
        try {
            const res = await window.http('DELETE', url);
            if (res.ok) {
                const modalEl = document.getElementById('confirmarEliminarModal');
                if (modalEl) {
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                }

                if (window.UIManager) {
                    window.UIManager.notifySuccess('Empleado eliminado correctamente');
                }

                reload();
                loadSummary('#empleados-summary');
            } else {
                throw new Error(res.data?.error || res.data?.detail || 'Error al eliminar empleado');
            }
        } catch (err) {
            console.error('[EmpleadoList] Error eliminando:', err);
            if (window.UIManager) {
                window.UIManager.notifyError(err.message || 'Error al eliminar empleado');
            }
        } finally {
            empleadoIdEliminar = null;
        }
    }

    /**
     * Recargar datos de la tabla
     */
    function reload() {
        if (window.Sintel.Empleados.table) {
            // TabulatorFactory usa setData() para refrescar con los mismos params
            window.Sintel.Empleados.table.setData();
        }
    }

    /**
     * Abrir offcanvas para editar empleado
     */
    function editar(id) {
        if (window.Sintel.Empleados.EmpleadoEditor) {
            window.Sintel.Empleados.EmpleadoEditor.open(id);
        } else {
            console.error('[EmpleadoList] EmpleadoEditor no cargado');
        }
    }

    /**
     * Abrir offcanvas para crear empleado
     */
    function crear() {
        if (window.Sintel.Empleados.EmpleadoEditor) {
            window.Sintel.Empleados.EmpleadoEditor.open();
        } else {
            console.error('[EmpleadoList] EmpleadoEditor no cargado');
        }
    }

    /**
     * Abrir offcanvas para registrar nómina
     */
    function registrarNomina(empleadoId) {
        if (window.Sintel.Empleados.DevengoEditor && typeof window.Sintel.Empleados.DevengoEditor.open === 'function') {
            window.Sintel.Empleados.DevengoEditor.open(empleadoId);
        } else {
            console.error('[EmpleadoList] DevengoEditor no cargado');
        }
    }

    // Exportar modulo
    window.Sintel.Empleados.EmpleadoList = {
        init,
        reload,
        loadSummary,
        editar,
        verDetalle,
        crear,
        registrarNomina,
        confirmarEliminar,
        ejecutarEliminar
    };

})();
