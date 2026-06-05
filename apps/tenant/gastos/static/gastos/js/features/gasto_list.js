/**
 * Feature: Listado de Gastos y Resoluciones v3.10.0
 * - KPIs calculados dinamicamente desde datos del grid de gastos
 * - TabulatorFactory standard con layout fitDataFill
 * - Columnas redisenadas estilo Proyectos (apilados y chips de estado)
 * - Event Delegation y Anti-Zombies integrados
 */
(function(w, d) {
    'use strict';

    const MOD = '[gastos.list]';

    // Anti-Zombies: destruir instancias previas en HTMX swap
    if (w.SintelGastosTables) {
        Object.values(w.SintelGastosTables).forEach(tb => {
            if (tb && typeof tb.destroy === 'function') {
                try { tb.destroy(); } catch (_) {}
            }
        });
    }
    w.SintelGastosTables = {};

    // Namespace
    w.Sintel = w.Sintel || {};
    w.Sintel.Gastos = w.Sintel.Gastos || {};

    // ─── Utilidades de Formateo ───────────────────────────────────────────────

    function fmtMoneda(v) {
        const n = parseFloat(v);
        if (!v && v !== 0 || isNaN(n)) return '—';
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP',
            minimumFractionDigits: 0, maximumFractionDigits: 0
        }).format(n);
    }

    function fmtFecha(v) {
        if (!v) return '—';
        try {
            return new Date(v + 'T00:00:00').toLocaleDateString('es-CO', {
                day: '2-digit', month: 'short', year: 'numeric'
            });
        } catch (_) { return v; }
    }

    // ─── KPIs Dinamicos de Gastos ─────────────────────────────────────────────

    function actualizarKPIs(rows) {
        const summaryEl = d.getElementById('gastos-summary');
        if (!summaryEl) return;

        const totalQty = rows.length;
        const activos = rows.filter(r => !r.ds_anulado);
        const activosQty = activos.length;
        const anuladosQty = totalQty - activosQty;
        const totalMonto = activos.reduce((s, r) => s + (parseFloat(r.ds_total) || 0), 0);

        summaryEl.innerHTML = `
            <div class="row g-3">
                <div class="col-6 col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body py-3 px-3 d-flex align-items-center gap-3">
                            <div class="rounded-circle bg-primary bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0" style="width:42px;height:42px;">
                                <i class="bi bi-receipt text-primary fs-5"></i>
                            </div>
                            <div>
                                <div class="fs-4 fw-bold lh-1 mb-1">${totalQty}</div>
                                <div class="small text-muted">Total Documentos</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body py-3 px-3 d-flex align-items-center gap-3">
                            <div class="rounded-circle bg-success bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0" style="width:42px;height:42px;">
                                <i class="bi bi-cash-coin text-success fs-5"></i>
                            </div>
                            <div>
                                <div class="fs-6 fw-bold lh-1 mb-1">${fmtMoneda(totalMonto)}</div>
                                <div class="small text-muted">Monto Activo</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body py-3 px-3 d-flex align-items-center gap-3">
                            <div class="rounded-circle bg-info bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0" style="width:42px;height:42px;">
                                <i class="bi bi-check-circle text-info fs-5"></i>
                            </div>
                            <div>
                                <div class="fs-4 fw-bold lh-1 mb-1">${activosQty}</div>
                                <div class="small text-muted">Gastos Activos</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body py-3 px-3 d-flex align-items-center gap-3">
                            <div class="rounded-circle bg-danger bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0" style="width:42px;height:42px;">
                                <i class="bi bi-x-circle text-danger fs-5"></i>
                            </div>
                            <div>
                                <div class="fs-4 fw-bold lh-1 mb-1">${anuladosQty}</div>
                                <div class="small text-muted">Anulados</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // ─── Modulo GastoList ─────────────────────────────────────────────────────

    const GastoList = {
        table: null,
        tableId: "#grid-gastos",
        _initializing: false,

        init: function(retryCount = 0) {
            const container = d.querySelector(this.tableId);
            if (this.table || !container || this._initializing) return;

            this._initializing = true;
            console.log("[GastoList] Inicializando tabla v3.10.0...");

            if (!w.TabulatorFactory) {
                if (retryCount < 5) {
                    console.warn("[GastoList] TabulatorFactory no disponible, reintentando...");
                    this._initializing = false;
                    setTimeout(() => this.init(retryCount + 1), 500);
                } else {
                    console.error("[GastoList] TabulatorFactory no disponible despues de 5 intentos");
                    w.UIManager?.notifyError("Error al cargar la tabla de gastos");
                    this._initializing = false;
                }
                return;
            }

            container.style.display = 'block';
            const spinner = d.querySelector('[data-spinner="gastos"]');
            if (spinner) spinner.style.display = 'none';

            try {
                const apiUrl = w.Sintel.Gastos.API?.gastos?.list || '/api/v1/gastos/';
                const columns = this.getColumnas();

                console.log("[GastoList] Creando tabla en contenedor:", this.tableId);
                this.table = w.TabulatorFactory.create(this.tableId, apiUrl, columns, {
                    initialSort: [{ field: "ds_fecha", dir: "desc" }],
                    placeholder: "No se encontraron gastos registrados",
                    searchInputSelector: '#search-gasto'
                });

                if (this.table) {
                    w.SintelGastosTables.gastos = this.table;

                    // Calcular KPIs con base en los datos de la grilla
                    this.table.on('dataLoaded', function(data) {
                        actualizarKPIs(data);
                    });
                    this.table.on('dataFiltered', function(_filters, rows) {
                        actualizarKPIs(rows.map(r => r.getData()));
                    });

                    this._initializing = false;
                } else {
                    console.warn("[GastoList] Fallo la creacion de la tabla, reintentando...");
                    this._initializing = false;
                    setTimeout(() => this.init(0), 1000);
                }
            } catch (error) {
                console.error("[GastoList] Error critico al inicializar:", error);
                w.UIManager?.notifyError("Error al inicializar tabla de gastos");
                this._initializing = false;
            }
        },

        getColumnas: function() {
            return [
                // 1. Documento (Numero + Doc. Proveedor apilados)
                {
                    title: "Documento",
                    field: "ds_numero_documento",
                    frozen: true,
                    width: 170,
                    formatter: function(cell) {
                        const row = cell.getRow().getData();
                        const num = row.ds_numero_documento || '—';
                        const prov = row.ds_numero_documento_proveedor;
                        return `
                            <div style="line-height:1.35;">
                                <div class="fw-semibold text-primary" style="font-size:0.85rem;">${num}</div>
                                ${prov ? `<div class="mt-1 small" style="font-size:0.72rem;"><span class="text-muted">Prov:</span> <code class="text-secondary">${prov}</code></div>` : ''}
                            </div>
                        `;
                    }
                },
                // 2. Fecha (Formato local colombiano con icono)
                {
                    title: "Fecha",
                    field: "ds_fecha",
                    width: 120,
                    formatter: function(cell) {
                        return `
                            <div style="font-size:0.8rem;">
                                <i class="bi bi-calendar-event text-muted me-1"></i>${fmtFecha(cell.getValue())}
                            </div>
                        `;
                    }
                },
                // 3. Vendedor / Proveedor (Con iniciales del tercero)
                {
                    title: "Vendedor / Proveedor",
                    field: "ds_vendedor",
                    minWidth: 200,
                    formatter: function(cell) {
                        const nombre = cell.getValue() || '—';
                        const iniciales = nombre.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
                        return `
                            <div class="d-flex align-items-center gap-2">
                                <div class="rounded-circle bg-primary bg-opacity-10 text-primary d-flex align-items-center justify-content-center flex-shrink-0 fw-bold"
                                     style="width:26px;height:26px;font-size:0.65rem;">${iniciales}</div>
                                <span class="text-truncate small" style="max-width:160px;" title="${nombre}">${nombre}</span>
                            </div>
                        `;
                    }
                },
                // 4. Clasificacion (Categoria + Asociado apilados)
                {
                    title: "Clasificación / Asociación",
                    field: "categoria_contable_display",
                    width: 200,
                    formatter: function(cell) {
                        const row = cell.getRow().getData();
                        const cat = row.categoria_contable_display || '—';
                        let assocHtml = '';
                        if (row.producto_relacionado_nombre) {
                            assocHtml = `<span class="badge bg-light text-dark border border-info" style="font-size:0.65rem;"><i class="bi bi-box text-info me-1"></i>${row.producto_relacionado_nombre}</span>`;
                        } else if (row.servicio_relacionado_nombre) {
                            assocHtml = `<span class="badge bg-light text-dark border border-warning" style="font-size:0.65rem;"><i class="bi bi-gear text-warning me-1"></i>${row.servicio_relacionado_nombre}</span>`;
                        } else if (row.activo_relacionado_nombre) {
                            assocHtml = `<span class="badge bg-light text-dark border border-primary" style="font-size:0.65rem;"><i class="bi bi-building text-primary me-1"></i>${row.activo_relacionado_nombre}</span>`;
                        }
                        return `
                            <div style="line-height:1.35;">
                                <div class="fw-semibold text-truncate small" style="max-width:180px;" title="${cat}">${cat}</div>
                                ${assocHtml ? `<div class="mt-1">${assocHtml}</div>` : ''}
                            </div>
                        `;
                    }
                },
                // 5. Total (Moneda premium)
                { 
                    title: "Total", 
                    field: "ds_total", 
                    width: 130, 
                    hozAlign: "right", 
                    formatter: function(cell) {
                        return `<div class="fw-bold text-dark" style="font-size:0.85rem;">${fmtMoneda(cell.getValue())}</div>`;
                    }
                },
                // 6. Estado (Chips premium)
                {
                    title: "Estado",
                    field: "ds_anulado",
                    width: 100,
                    hozAlign: "center",
                    formatter: function(cell) {
                        const anulado = cell.getValue();
                        return anulado 
                            ? '<span class="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-20 px-2 py-1">Anulado</span>' 
                            : '<span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-20 px-2 py-1">Activo</span>';
                    }
                },
                // 7. Acciones (Frozen con Event Delegation)
                {
                    title: "",
                    field: "uuid",
                    headerSort: false,
                    hozAlign: "center",
                    width: 150,
                    frozen: true,
                    formatter: function(cell) {
                        const data = cell.getRow().getData();
                        const uuid = data.uuid;
                        const isAnulado = data.ds_anulado;
                        const btnEditClass = isAnulado ? "btn-light disabled" : "btn-outline-primary";
                        const btnCancelClass = isAnulado ? "btn-light disabled" : "btn-outline-warning";
                        
                        return `
                            <div class="btn-group btn-group-sm">
                                <button type="button" class="btn btn-outline-info btn-view-gasto" data-uuid="${uuid}" title="Ver Detalle">
                                    <i class="bi bi-eye"></i>
                                </button>
                                <button type="button" class="btn ${btnEditClass} btn-edit-gasto" data-uuid="${uuid}" title="Editar">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button type="button" class="btn ${btnCancelClass} btn-cancel-gasto" data-uuid="${uuid}" title="Anular">
                                    <i class="bi bi-x-circle"></i>
                                </button>
                                <button type="button" class="btn btn-outline-danger btn-delete-gasto" data-uuid="${uuid}" data-anulado="${isAnulado ? 'true' : 'false'}" title="Eliminar">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        `;
                    }
                }
            ];
        },

        refresh: function() {
            if (this.table) {
                const tbl = this.table;
                setTimeout(() => tbl.replaceData(), 50);
            }
        },

        reload: function() {
            this.refresh();
        },

        verDetalle: function(uuid) {
            const url = w.Sintel.Gastos.API.endpoints.renderDetalle(uuid);
            if (w.htmx) {
                w.htmx.ajax('GET', url, { target: '#offcanvas-container-gastos', swap: 'innerHTML' });
            } else {
                this.loadAndShowOffcanvas(url);
            }
        },

        editarGasto: function(uuid) {
            const url = w.Sintel.Gastos.API.endpoints.renderEditar(uuid);
            if (w.htmx) {
                w.htmx.ajax('GET', url, { target: '#offcanvas-container-gastos', swap: 'innerHTML' });
            } else {
                this.loadAndShowOffcanvas(url);
            }
        },

        anularGasto: async function(uuid) {
            const confirmed = await w.UIManager?.confirm("¿Está seguro de anular este gasto? Esta acción es irreversible.");
            if (!confirmed) return;

            try {
                const response = await w.Sintel.Gastos.API.anular(uuid);
                if (response.id || response.message) {
                    w.UIManager?.notifySuccess("Gasto anulado correctamente");
                    this.refresh();
                } else {
                    w.UIManager?.notifyError("Error al anular el gasto");
                }
            } catch (error) {
                w.UIManager?.handleError(error);
            }
        },

        eliminarGasto: async function(uuid, isAnulado) {
            if (!isAnulado) {
                w.UIManager?.notifyError("El gasto está activo. Debe anularlo antes de poder eliminarlo permanentemente.");
                return;
            }

            const confirmed = await w.UIManager?.confirm("¿Está seguro de eliminar este gasto de forma PERMANENTE? Esta acción no se puede deshacer.");
            if (!confirmed) return;

            try {
                const response = await w.Sintel.Gastos.API.eliminar(uuid);
                if (response.ok || response.success || response.status === 204 || response.message) {
                    w.UIManager?.notifySuccess("Gasto eliminado permanentemente");
                    this.refresh();
                } else {
                    const msg = response.data?.detail || response.data?.message || "Error al eliminar el gasto";
                    w.UIManager?.notifyError(msg);
                }
            } catch (error) {
                w.UIManager?.handleError(error);
            }
        },

        loadAndShowOffcanvas: async function(url) {
            const container = d.querySelector("#offcanvas-container-gastos");
            if (!container) return;

            try {
                const response = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                const html = await response.text();

                const existingOffcanvas = container.querySelector('.offcanvas');
                if (existingOffcanvas && w.bootstrap?.Offcanvas) {
                    const instance = w.bootstrap.Offcanvas.getInstance(existingOffcanvas);
                    if (instance) instance.hide();
                }

                container.innerHTML = html;

                setTimeout(() => {
                    const offcanvasEl = container.querySelector('.offcanvas');
                    if (!offcanvasEl) return;

                    try {
                        const offcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
                        offcanvas.show();

                        const formGasto = offcanvasEl.querySelector('#gasto-form');
                        if (formGasto) {
                            d.body.dispatchEvent(new CustomEvent('gasto-editor-init', { detail: { form: formGasto } }));
                        }

                        const formRes = offcanvasEl.querySelector('#resolucion-form');
                        if (formRes) {
                            d.body.dispatchEvent(new CustomEvent('resolucion-editor-init', { detail: { form: formRes } }));
                        }
                    } catch (bootstrapError) {
                        console.error("[GastoList] Error al inicializar Bootstrap Offcanvas:", bootstrapError);
                    }
                }, 10);
            } catch (error) {
                console.error("[GastoList] Error cargando offcanvas:", error);
            }
        }
    };

    // ─── Modulo ResolucionList ────────────────────────────────────────────────

    const ResolucionList = {
        table: null,
        tableId: "#grid-resoluciones",
        _initializing: false,

        init: function(retryCount = 0) {
            const container = d.querySelector(this.tableId);
            if (this.table || !container || this._initializing) return;

            this._initializing = true;
            console.log('[ResolucionList] Inicializando tabla de resoluciones v3.10.0...');

            if (!w.TabulatorFactory) {
                if (retryCount < 5) {
                    this._initializing = false;
                    setTimeout(() => this.init(retryCount + 1), 500);
                } else {
                    this._initializing = false;
                }
                return;
            }

            try {
                container.style.display = 'block';
                const spinner = d.querySelector('[data-spinner="resoluciones"]');
                if (spinner) spinner.style.display = 'none';

                const apiUrl = w.Sintel.Gastos.API?.resoluciones?.list || '/api/v1/gastos/resoluciones/';
                const columns = [
                    // 1. Resolucion y Prefijo apilados
                    {
                        title: "Resolución",
                        field: "numero_resolucion",
                        frozen: true,
                        width: 190,
                        formatter: function(cell) {
                            const row = cell.getRow().getData();
                            return `
                                <div style="line-height:1.35;">
                                  <div class="fw-semibold text-dark" style="font-size:0.85rem;">${row.numero_resolucion || '—'}</div>
                                  ${row.prefijo ? `<div class="mt-1" style="font-size:0.72rem;"><span class="text-muted">Prefijo:</span> <code class="text-secondary">${row.prefijo}</code></div>` : ''}
                                </div>`;
                        }
                    },
                    // 2. Rango autorizado apilados
                    {
                        title: "Rango Autorizado",
                        field: "rango_desde",
                        width: 150,
                        formatter: function(cell) {
                            const row = cell.getRow().getData();
                            return `
                                <div style="line-height:1.35; font-size:0.78rem;">
                                  <div><span class="text-muted">Desde:</span> ${row.rango_desde || '—'}</div>
                                  <div><span class="text-muted">Hasta:</span> ${row.rango_hasta || '—'}</div>
                                </div>`;
                        }
                    },
                    // 3. Vencimiento con icono
                    {
                        title: "Vencimiento",
                        field: "fecha_fin",
                        width: 140,
                        formatter: function(cell) {
                            return `<div style="font-size:0.8rem;"><i class="bi bi-calendar-event text-muted me-1"></i>${fmtFecha(cell.getValue())}</div>`;
                        }
                    },
                    // 4. Estado (Badge premium)
                    { 
                        title: "Estado", 
                        field: "vigente", 
                        width: 120, 
                        hozAlign: "center",
                        formatter: function(cell) {
                            return cell.getValue()
                                ? '<span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-20 px-2 py-1">Vigente</span>'
                                : '<span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-20 px-2 py-1">Vencida/Inactiva</span>';
                        }
                    },
                    // 5. Acciones con Event Delegation
                    {
                        title: "", 
                        field: "uuid",
                        headerSort: false, 
                        width: 110,
                        hozAlign: "center",
                        frozen: true,
                        formatter: function(cell) {
                            const data = cell.getRow().getData();
                            const uuid = data.uuid;
                            return `
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-primary btn-edit-resolucion" data-uuid="${uuid}" title="Editar Resolución">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    ${data.vigente ? `
                                    <button class="btn btn-outline-warning btn-deactivate-resolucion" data-uuid="${uuid}" title="Desactivar">
                                        <i class="bi bi-slash-circle"></i>
                                    </button>` : ''}
                                </div>`;
                        }
                    }
                ];

                this.table = w.TabulatorFactory.create(this.tableId, apiUrl, columns, {
                    placeholder: "No hay resoluciones registradas",
                    searchInputSelector: '#search-resolucion'
                });
                
                if (this.table) {
                    w.SintelGastosTables.resoluciones = this.table;
                    this._initializing = false;
                } else {
                    this._initializing = false;
                }
            } catch (error) {
                console.error("[ResolucionList] Error critico al inicializar:", error);
                w.UIManager?.notifyError("Error al cargar lista de resoluciones");
                this._initializing = false;
            }
        },

        reload: function() {
            if (this.table) {
                const tbl = this.table;
                setTimeout(() => tbl.replaceData(), 50);
            }
        },

        desactivar: async function(uuid) {
            try {
                const response = await fetch(`/api/v1/gastos/resoluciones/${uuid}/desactivar/`, {
                    method: 'POST',
                    headers: w.Sintel.Gastos.getHeaders()
                });
                
                if (response.ok) {
                    w.UIManager?.notifySuccess('Resolución desactivada');
                    this.reload();
                } else {
                    const data = await response.json();
                    w.UIManager?.handleError({error: data.detail || 'Error al desactivar'});
                }
            } catch (e) {
                console.error('[ResolucionList] Error:', e);
                w.UIManager?.notifyError('Error de conexión');
            }
        }
    };

    // ─── Event Delegation (Acciones de la Grilla) ─────────────────────────────

    function initListEvents() {
        // Gastos Grid Events
        const gridGastos = d.querySelector('#grid-gastos');
        if (gridGastos) {
            gridGastos.addEventListener('click', async (e) => {
                const btnView = e.target.closest('.btn-view-gasto');
                const btnEdit = e.target.closest('.btn-edit-gasto');
                const btnCancel = e.target.closest('.btn-cancel-gasto');
                const btnDel = e.target.closest('.btn-delete-gasto');

                if (btnView) {
                    e.preventDefault();
                    e.stopPropagation();
                    const uuid = btnView.getAttribute('data-uuid');
                    if (uuid) GastoList.verDetalle(uuid);
                    return;
                }

                if (btnEdit) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (btnEdit.classList.contains('disabled')) return;
                    const uuid = btnEdit.getAttribute('data-uuid');
                    if (uuid) GastoList.editarGasto(uuid);
                    return;
                }

                if (btnCancel) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (btnCancel.classList.contains('disabled')) return;
                    const uuid = btnCancel.getAttribute('data-uuid');
                    if (uuid) GastoList.anularGasto(uuid);
                    return;
                }

                if (btnDel) {
                    e.preventDefault();
                    e.stopPropagation();
                    const uuid = btnDel.getAttribute('data-uuid');
                    const anulado = btnDel.getAttribute('data-anulado') === 'true';
                    if (uuid) GastoList.eliminarGasto(uuid, anulado);
                    return;
                }
            });
        }

        // Resoluciones Grid Events
        const gridResoluciones = d.querySelector('#grid-resoluciones');
        if (gridResoluciones) {
            gridResoluciones.addEventListener('click', async (e) => {
                const btnEdit = e.target.closest('.btn-edit-resolucion');
                const btnDeactivate = e.target.closest('.btn-deactivate-resolucion');

                if (btnEdit) {
                    e.preventDefault();
                    e.stopPropagation();
                    const uuid = btnEdit.getAttribute('data-uuid');
                    if (uuid) {
                        const url = w.Sintel.Gastos.API.endpoints.renderResolucion(uuid);
                        if (w.htmx) {
                            w.htmx.ajax('GET', url, { target: '#offcanvas-container-gastos', swap: 'innerHTML' });
                        } else {
                            GastoList.loadAndShowOffcanvas(url);
                        }
                    }
                    return;
                }

                if (btnDeactivate) {
                    e.preventDefault();
                    e.stopPropagation();
                    const uuid = btnDeactivate.getAttribute('data-uuid');
                    if (uuid) {
                        const confirmed = await w.UIManager?.confirm("¿Desea desactivar esta resolución? Esta acción no se puede deshacer.");
                        if (confirmed) ResolucionList.desactivar(uuid);
                    }
                    return;
                }
            });
        }
    }

    // ─── Setup e Inicializacion Segura ────────────────────────────────────────

    function setup() {
        console.log('[GastoList] Setup iniciado');
        GastoList.init();
        ResolucionList.init();
        initListEvents();
    }

    // Cargar segun el estado del DOM
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

    // Manejo de Offcanvas con HTMX
    d.body.addEventListener('htmx:afterSettle', (evt) => {
        const target = evt.detail.target;
        if (target && target.id === 'offcanvas-container-gastos') {
            setTimeout(() => {
                const offcanvasEl = target.querySelector('.offcanvas');
                if (offcanvasEl && w.bootstrap?.Offcanvas) {
                    try {
                        const offcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
                        offcanvas.show();

                        const formGasto = offcanvasEl.querySelector('#gasto-form');
                        if (formGasto) {
                            d.body.dispatchEvent(new CustomEvent('gasto-editor-init', { detail: { form: formGasto } }));
                        }
                    } catch (error) {
                        console.error('[GastoList] Error abriendo offcanvas HTMX:', error);
                    }
                }
            }, 10);
        }
    });

    d.body.addEventListener('htmx:beforeCleanupElement', (evt) => {
        const el = evt?.detail?.elt;
        if (el && el.classList && el.classList.contains('offcanvas')) {
            try {
                if (w.bootstrap?.Offcanvas) {
                    const instance = w.bootstrap.Offcanvas.getInstance(el);
                    if (instance) instance.hide();
                }
            } catch (e) {
                console.warn('[GastoList] Error limpiando offcanvas:', e);
            }
        }
    });

    // Eventos de Sincronizacion Reactiva
    d.body.addEventListener('gasto-created', () => {
        GastoList.refresh();
    });

    d.body.addEventListener('gasto-updated', () => {
        GastoList.refresh();
    });

    d.body.addEventListener('resolucion-created', () => {
        ResolucionList.reload();
    });

    // Manejo de Tabs de Bootstrap
    d.addEventListener('shown.bs.tab', (e) => {
        const targetId = e.target.id;
        if (targetId === 'tab-resoluciones' || targetId === 'resoluciones-tab') {
            ResolucionList.init();
        }
        if (targetId === 'tab-gastos' || targetId === 'gastos-tab') {
            GastoList.init();
        }
    });

    // API Publica
    w.Sintel.Gastos.GastoList = GastoList;
    w.Sintel.Gastos.ResolucionList = ResolucionList;
    w.Sintel.Gastos.List = GastoList; // Legacy alias

})(window, document);
