// @ts-nocheck
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
     * Handler con event delegation para acciones de la celda.
     * Solo opera acciones CRUD del módulo Empleados: ver, editar y eliminar.
     */
    function handleCellAction(e, cell) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        const action = btn.dataset.action;
        const id     = btn.dataset.id;

        switch (action) {
            case 'ver':
                verDetalle(id);
                break;
            case 'editar':
                editar(id);
                break;
            case 'eliminar': {
                const rowData = cell.getRow().getData();
                const nombre  = `${rowData.primer_nombre || ''} ${rowData.primer_apellido || ''}`.trim();
                const doc     = rowData.numero_documento || '';
                confirmarEliminar(id, nombre, doc);
                break;
            }
        }
    }

    // Iniciales de respaldo para empleados sin foto
    function _initiales(data) {
        const n = (data.primer_nombre || '').charAt(0).toUpperCase();
        const a = (data.primer_apellido || '').charAt(0).toUpperCase();
        return n + a || '?';
    }

    /**
     * Definición de columnas para la tabla
     */
    function getColumnas() {
        return [
            // ── Avatar ──────────────────────────────────────────────
            {
                title: '',
                field: 'foto_url',
                width: 52,
                headerSort: false,
                hozAlign: 'center',
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const url  = cell.getValue();
                    if (url) {
                        return `<img src="${url}" alt=""
                                     style="width:36px;height:36px;border-radius:50%;object-fit:cover;border:2px solid #dee2e6;">`;
                    }
                    const ini   = _initiales(data);
                    const color = data.estado === 'RETIRADO' ? '#adb5bd' : '#0d6efd';
                    return `<div style="width:36px;height:36px;border-radius:50%;background:${color}20;
                                        border:2px solid ${color}40;display:flex;align-items:center;
                                        justify-content:center;font-size:.75rem;font-weight:700;color:${color};">
                                ${ini}
                            </div>`;
                },
            },
            // ── Empleado ─────────────────────────────────────────────
            {
                title: 'Empleado',
                field: 'nombre_completo',
                minWidth: 160,
                headerFilter: 'input',
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const nom  = cell.getValue() || `${data.primer_nombre || ''} ${data.primer_apellido || ''}`.trim();
                    const doc  = data.numero_documento ? `<div class="small text-muted">${data.numero_documento}</div>` : '';
                    return `<div class="fw-semibold lh-sm">${nom}</div>${doc}`;
                },
            },
            { title: "Estado",
              field: "estado",
              width: 110,
              hozAlign: "center",
              formatter: (cell) => {
                const estado = cell.getValue();
                let icon = '';
                let cls = 'bg-secondary';
                if (estado === 'ACTIVO') {
                  icon = '<i class="bi bi-check-circle me-1"></i>';
                  cls = 'bg-success';
                } else if (estado === 'RETIRADO') {
                  icon = '<i class="bi bi-x-circle me-1"></i>';
                  cls = 'bg-danger';
                }
                return `<span class="badge ${cls}">${icon}${estado || 'N/A'}</span>`;
              }
            },
            { title: "Ingreso",
              field: "fecha_ingreso",
              width: 110,
              formatter: (cell) => {
                const val = cell.getValue();
                if (!val) return '<span class="text-muted">—</span>';
                return `<i class="bi bi-calendar-event text-primary me-1"></i><span class="small">${val}</span>`;
              }
            },
            {
              title: "Cargo",
              field: "cargo",
              minWidth: 140,
              formatter: (cell) => {
                const val = cell.getValue();
                if (!val) return '<span class="text-muted">—</span>';
                return `<i class="bi bi-briefcase text-info me-1"></i><span>${val}</span>`;
              }
            },
            {
              title: "Contacto",
              field: "email",
              minWidth: 180,
              formatter: (cell) => {
                const email = cell.getValue();
                const data = cell.getRow().getData();
                const telefono = data.telefono || '';
                let html = '';
                if (email) html += `<i class="bi bi-envelope text-info me-1"></i><span class="small">${email}</span>`;
                if (telefono) html += `<br/><i class="bi bi-telephone text-success me-1"></i><span class="small">${telefono}</span>`;
                if (!email && !telefono) html = '<span class="text-muted">—</span>';
                return html;
              }
            },
            {
                title: 'Acciones',
                width: 140,
                hozAlign: 'center',
                headerSort: false,
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const uuid = data.uuid;
                    let html = '<div class="btn-group btn-group-sm">';
                    html += `<button data-action="ver" data-id="${uuid}" class="btn btn-outline-info" title="Ver detalle"><i class="bi bi-eye"></i></button>`;
                    html += `<button data-action="editar" data-id="${uuid}" class="btn btn-outline-primary" title="Editar empleado"><i class="bi bi-pencil"></i></button>`;
                    html += `<button data-action="eliminar" data-id="${uuid}" class="btn btn-outline-danger" title="Eliminar permanentemente"><i class="bi bi-trash"></i></button>`;
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
        // Evitar inicialización redundante
        if (window.Sintel.Empleados.table) {
            console.log('[EmpleadoList] Tabla ya inicializada, omitiendo...');
            return window.Sintel.Empleados.table;
        }

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
                
                // Intentar actualizar elementos individuales si existen
                const totalEmpEl = document.getElementById('total-empleados');
                const activosEl = document.getElementById('total-contratos-activos');
                const nominasEl = document.getElementById('total-nominas');
                const costoEl = document.getElementById('costo-nomina-mes');

                if (totalEmpEl || activosEl || nominasEl || costoEl) {
                    if (totalEmpEl) totalEmpEl.textContent = data.total_empleados || 0;
                    if (activosEl) activosEl.textContent = data.empleados_activos || 0;
                    if (nominasEl) nominasEl.textContent = data.empleados_pagados || 0;
                    if (costoEl) {
                        const val = parseFloat(data.total_nomina_mes) || 0;
                        costoEl.textContent = new Intl.NumberFormat('es-CO', {
                            style: 'currency', currency: 'COP', minimumFractionDigits: 0
                        }).format(val);
                    }
                    return;
                }

                // Fallback para estructura dinámica antigua
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
            if (element && element.id !== 'panel-resumen-empleados') {
                element.innerHTML = '<div class="alert alert-warning">Error cargando resumen</div>';
            }
        }
    }

    /**
     * Ver detalle de empleado cargando el offcanvas en modo lectura
     */
    async function verDetalle(uuid) {
        if (!uuid) return;
        const apiUrl = window.Sintel?.Empleados?.API?.empleados?.gestorOffcanvas || '/api/v1/empleados/gestor-offcanvas/';
        const url = `${apiUrl}?tipo=empleado&mode=ver&uuid=${uuid}`;
        const containerId = 'offcanvas-container-empleados';

        console.log('[EmpleadoList] Cargando detalle offcanvas:', url);
        
        try {
            await htmx.ajax('GET', url, {
                target: `#${containerId}`,
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error('[EmpleadoList] Error al cargar detalle:', error);
            if (window.UIManager) {
                window.UIManager.notifyError('Error al cargar el detalle del empleado');
            }
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
                let errorMsg = 'Error al eliminar empleado';
                if (res.data) {
                    const detail = res.data.error || res.data.detail;
                    if (detail) {
                        errorMsg = Array.isArray(detail) ? detail.join(', ') : (typeof detail === 'object' ? JSON.stringify(detail) : String(detail));
                    } else if (typeof res.data === 'object') {
                        errorMsg = JSON.stringify(res.data);
                    } else if (typeof res.data === 'string') {
                        errorMsg = res.data;
                    }
                }
                throw new Error(errorMsg);
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
