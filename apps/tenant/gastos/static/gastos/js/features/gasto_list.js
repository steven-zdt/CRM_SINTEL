(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Gastos = window.Sintel.Gastos || {};

    /**
     * Gasto List Module
     */
    const GastoList = {
        table: null,
        tableId: "#grid-gastos",

        init: function() {
            const container = document.querySelector(this.tableId);
            if (this.table || !container) return;

            console.log("[GastoList] Inicializando tabla v2.62...");

            // Mostrar grid y ocultar spinner
            container.style.display = 'block';
            const spinner = document.querySelector('[data-spinner="gastos"]');
            if (spinner) spinner.style.display = 'none';

            try {
                const apiUrl = window.Sintel.Gastos.API?.gastos?.list || '/api/v1/gastos/';
                const columns = this.getColumnas();
                
                this.table = window.TabulatorFactory.create(this.tableId, apiUrl, columns, {
                    initialSort: [{ field: "ds_fecha", dir: "desc" }],
                    placeholder: "No se encontraron gastos registrados"
                });
            } catch (error) {
                console.error("[GastoList] Error al inicializar Tabulator:", error);
            }
        },

        getColumnas: function() {
            return [
                { title: "N° Gasto", field: "ds_numero_documento", width: 120, headerFilter: "input" },
                { title: "Doc. Proveedor", field: "ds_numero_documento_proveedor", width: 150, headerFilter: "input" },
                { title: "Fecha", field: "ds_fecha", width: 110, headerFilter: "input" },
                { title: "Vendedor / Proveedor", field: "ds_vendedor", minWidth: 200, headerFilter: "input" },
                { title: "Categoría", field: "categoria_contable_display", width: 150, headerFilter: "input" },
                { 
                    title: "Total", 
                    field: "ds_total", 
                    width: 130, 
                    hozAlign: "right", 
                    formatter: "money", 
                    formatterParams: { precision: 0, decimal: ",", thousand: "." } 
                },
                {
                    title: "Estado",
                    field: "ds_anulado",
                    width: 100,
                    hozAlign: "center",
                    formatter: function(cell) {
                        const anulado = cell.getValue();
                        return anulado 
                            ? '<span class="badge bg-danger">Anulado</span>' 
                            : '<span class="badge bg-success">Activo</span>';
                    }
                },
                {
                    title: "Acciones",
                    headerSort: false,
                    width: 160,
                    hozAlign: "center",
                    formatter: function(cell) {
                        const data = cell.getData();
                        const isAnulado = data.ds_anulado;
                        const btnEditClass = isAnulado ? "btn-light disabled" : "btn-outline-primary";
                        const btnCancelClass = isAnulado ? "btn-light disabled" : "btn-outline-warning";
                        
                        return `
                            <div class="btn-group btn-group-sm shadow-sm" role="group">
                                <button class="btn btn-outline-info" data-action="view" title="Ver Detalle">
                                    <i class="bi bi-eye"></i>
                                </button>
                                <button class="btn ${btnEditClass}" data-action="edit" title="Editar">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn ${btnCancelClass}" data-action="cancel" title="Anular">
                                    <i class="bi bi-x-circle"></i>
                                </button>
                                <button class="btn btn-outline-danger" data-action="delete" title="Eliminar">
                                    <i class="bi bi-trash3"></i>
                                </button>
                            </div>
                        `;
                    },
                    cellClick: (e, cell) => GastoList.handleCellAction(e, cell)
                }
            ];
        },

        refresh: function() {
            if (this.table) this.table.setData();
        },

        reload: function() {
            this.refresh();
        },

        handleCellAction: function(e, cell) {
            const btn = e.target.closest("[data-action]");
            if (!btn) return;

            const action = btn.dataset.action;
            const data = cell.getRow().getData();
            const uuid = data.id;

            switch (action) {
                case 'view': this.verDetalle(uuid); break;
                case 'edit': this.editarGasto(uuid); break;
                case 'cancel': this.anularGasto(uuid); break;
                case 'delete': this.eliminarGasto(uuid); break;
            }
        },

        verDetalle: function(uuid) {
            const url = window.Sintel.Gastos.API.endpoints.renderDetalle(uuid);
            if (window.htmx) {
                window.htmx.ajax('GET', url, { target: '#offcanvas-container-gastos', swap: 'innerHTML' });
            } else {
                this.loadAndShowOffcanvas(url, 'offcanvas-gasto-detalle');
            }
        },

        editarGasto: function(uuid) {
            const url = window.Sintel.Gastos.API.endpoints.renderEditar(uuid);
            if (window.htmx) {
                window.htmx.ajax('GET', url, { target: '#offcanvas-container-gastos', swap: 'innerHTML' });
            } else {
                this.loadAndShowOffcanvas(url, 'offcanvas-gasto-editar');
            }
        },

        anularGasto: async function(uuid) {
            const confirmed = await window.UIManager?.confirm("¿Está seguro de anular este gasto? Esta acción es irreversible.");
            if (!confirmed) return;

            try {
                const response = await window.Sintel.Gastos.API.anular(uuid);
                if (response.id || response.message) {
                    window.UIManager?.notifySuccess("Gasto anulado correctamente");
                    this.refresh();
                } else {
                    window.UIManager?.notifyError("Error al anular el gasto");
                }
            } catch (error) {
                window.UIManager?.handleError(error);
            }
        },

        eliminarGasto: async function(uuid) {
            const row = this.table.getRow(uuid);
            const data = row ? row.getData() : {};
            const isAnulado = data.ds_anulado === true || data.ds_anulado === 'true';

            // [STANDARDIZATION] Bloquear si no está anulado
            if (!isAnulado) {
                window.UIManager?.notifyError("El gasto está activo. Debe anularlo antes de poder eliminarlo permanentemente.");
                return;
            }

            const confirmed = await window.UIManager?.confirm("¿Está seguro de eliminar este gasto de forma PERMANENTE? Esta acción no se puede deshacer.");
            if (!confirmed) return;

            try {
                const response = await window.Sintel.Gastos.API.eliminar(uuid);
                // El backend retorna 204 No Content para eliminacion exitosa
                if (response.status === 204 || response.success || response.message) {
                    window.UIManager?.notifySuccess("Gasto eliminado permanentemente");
                    this.refresh();
                } else {
                    const msg = response.data?.detail || response.data?.message || "Error al eliminar el gasto";
                    window.UIManager?.notifyError(msg);
                }
            } catch (error) {
                window.UIManager?.handleError(error);
            }
        },

        loadAndShowOffcanvas: async function(url, offcanvasId) {
            const container = document.querySelector("#offcanvas-container-gastos");
            if (!container) return;

            try {
                const response = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                const html = await response.text();
                container.innerHTML = html;
                
                const offcanvasEl = container.querySelector('.offcanvas');
                if (offcanvasEl) {
                    if (offcanvasId) offcanvasEl.id = offcanvasId;
                    
                    // IMPORTANTE: Primero mostrar para asegurar que Bootstrap lo registre
                    window.UIManager?.handleOffcanvas(offcanvasEl, 'show');
                    
                    // Notificar al editor para inicializar el formulario si existe
                    const formGasto = offcanvasEl.querySelector('#gasto-form');
                    if (formGasto) {
                        document.body.dispatchEvent(new CustomEvent('gasto-editor-init', { detail: { form: formGasto } }));
                    }
                    
                    const formRes = offcanvasEl.querySelector('#resolucion-form');
                    if (formRes) {
                        document.body.dispatchEvent(new CustomEvent('resolucion-editor-init', { detail: { form: formRes } }));
                    }
                }
            } catch (error) {
                console.error("[GastoList] Error cargando offcanvas:", error);
                window.UIManager?.notifyError("No se pudo cargar el formulario");
            }
        }
    };

    /**
     * Resolucion List Module
     */
    const ResolucionList = {
        table: null,
        tableId: "#grid-resoluciones",

        init: function() {
            const container = document.querySelector(this.tableId);
            if (this.table || !container) return;

            console.log('[ResolucionList] Inicializando tabla de resoluciones v2.62...');
            
            try {
                // Mostrar grid y ocultar spinner
                container.style.display = 'block';
                const spinner = document.querySelector('[data-spinner="resoluciones"]');
                if (spinner) spinner.style.display = 'none';

                const apiUrl = window.Sintel.Gastos.API?.resoluciones?.list || '/api/v1/resoluciones-dian/';
                const columns = [
                    { title: "N° Resolución", field: "numero_resolucion", width: 150, headerFilter: "input" },
                    { title: "Prefijo", field: "prefijo", width: 100, headerFilter: "input" },
                    { title: "Desde", field: "rango_desde", width: 100 },
                    { title: "Hasta", field: "rango_hasta", width: 100 },
                    { title: "Vencimiento", field: "fecha_fin", width: 120 },
                    { 
                        title: "Estado", 
                        field: "vigente", 
                        width: 100, 
                        hozAlign: "center", 
                        formatter: "tickCross", 
                        formatterParams: { allowEmpty: true } 
                    },
                    {
                        title: "Acciones", 
                        headerSort: false, 
                        width: 130,
                        hozAlign: "center",
                        formatter: (cell) => {
                            const data = cell.getData();
                            return `
                                <div class="btn-group btn-group-sm shadow-sm" role="group">
                                    <button class="btn btn-outline-primary" data-action="edit" title="Editar Resolución">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    ${data.vigente ? `
                                    <button class="btn btn-outline-warning" data-action="deactivate" title="Desactivar">
                                        <i class="bi bi-slash-circle"></i>
                                    </button>` : ''}
                                </div>`;
                        },
                        cellClick: (e, cell) => ResolucionList.handleCellAction(e, cell)
                    }
                ];

                this.table = window.TabulatorFactory?.create(this.tableId, apiUrl, columns, {
                    placeholder: "No hay resoluciones registradas"
                });
            } catch (error) {
                console.error("[ResolucionList] Error crítico al inicializar:", error);
                window.UIManager?.notifyError("Error al cargar lista de resoluciones");
            }
        },

        reload: function() {
            if (this.table) this.table.setData();
        },

        handleCellAction: function(e, cell) {
            const btn = e.target.closest("[data-action]");
            if (!btn) return;

            const action = btn.dataset.action;
            const data = cell.getRow().getData();
            const uuid = data.id || data.uuid;

            switch (action) {
                case 'edit':
                    const url = window.Sintel.Gastos.API.endpoints.renderResolucion(uuid);
                    if (window.htmx) {
                        window.htmx.ajax('GET', url, { target: '#offcanvas-container-gastos', swap: 'innerHTML' });
                    } else {
                        window.Sintel.Gastos.GastoList.loadAndShowOffcanvas(url, 'offcanvas-resolucion-editar');
                    }
                    break;
                case 'deactivate':
                    window.UIManager?.confirm("¿Desea desactivar esta resolución? Esta acción no se puede deshacer.").then(confirmed => {
                        if (confirmed) this.desactivar(uuid);
                    });
                    break;
            }
        },

        desactivar: async function(uuid) {
            try {
                const response = await fetch(`/api/v1/resoluciones-dian/${uuid}/desactivar/`, {
                    method: 'POST',
                    headers: window.Sintel.Gastos.getHeaders()
                });
                
                if (response.ok) {
                    window.UIManager?.notifySuccess('Resolución desactivada');
                    this.reload();
                } else {
                    const data = await response.json();
                    window.UIManager?.handleError({error: data.detail || 'Error al desactivar'});
                }
            } catch (e) {
                console.error('[ResolucionList] Error:', e);
                window.UIManager?.notifyError('Error de conexión');
            }
        }
    };

    // Export to namespace
    window.Sintel.Gastos.GastoList = GastoList;
    window.Sintel.Gastos.ResolucionList = ResolucionList;
    window.Sintel.Gastos.List = GastoList; // Legacy alias

    // --- Orquestación de Eventos ---
    
    // 1. Inicialización para carga inicial (si existe)
    function setup() {
        GastoList.init();
        ResolucionList.init();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

    // 2. Manejo Centralizado de Offcanvas vía HTMX (v2.62.3 compatible)
    // Escucha cuando HTMX inyecta contenido en el contenedor de offcanvas de gastos
    document.body.addEventListener('htmx:afterSettle', (evt) => {
        const target = evt.detail.target;
        if (target && target.id === 'offcanvas-container-gastos') {
            const offcanvasEl = target.querySelector('.offcanvas');
            if (offcanvasEl && window.UIManager?.handleOffcanvas) {
                console.log('[GastoList] Detectado offcanvas vía HTMX, abriendo:', offcanvasEl.id);
                window.UIManager.handleOffcanvas(offcanvasEl, 'show');
            }
        }
    });

    // ⚠️ v2.62.4: Prevención de TypeError en Bootstrap (Scroll Lock)
    // Limpia cualquier instancia de offcanvas antes de que HTMX remueva el elemento del DOM
    document.body.addEventListener('htmx:beforeCleanupElement', (evt) => {
        const el = evt.detail.elt;
        if (el && el.classList.contains('offcanvas')) {
            console.log('[GastoList] Limpiando instancia offcanvas vía UIManager antes de swap:', el.id);
            window.UIManager?.destroyOffcanvas(el);
        }
    });

    // 3. Sincronización Reactiva: Refrescar tablas cuando se crean/editan registros
    document.body.addEventListener('gasto-created', () => {
        console.log('[GastoList] Gasto creado detectado, refrescando tabla...');
        GastoList.refresh();
    });

    document.body.addEventListener('gasto-updated', () => {
        console.log('[GastoList] Gasto actualizado detectado, refrescando tabla...');
        GastoList.refresh();
    });

    document.body.addEventListener('resolucion-created', () => {
        console.log('[ResolucionList] Resolución creada detectada, refrescando tabla...');
        ResolucionList.reload();
    });

    // Tab handling
    document.addEventListener('shown.bs.tab', (e) => {
        if (e.target.id === 'resoluciones-tab') ResolucionList.init();
        if (e.target.id === 'gastos-tab') GastoList.init();
    });

    // Public API
    window.Sintel.Gastos.GastoList = GastoList;
    window.Sintel.Gastos.ResolucionList = ResolucionList;

})();
