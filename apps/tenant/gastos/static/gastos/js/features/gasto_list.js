/**
 * Feature: Listado de Gastos y Resoluciones v5.1.0
 * - Tabla "Gastos" (Documentos Soporte) es DataTables 3.x (#tabla-gastos,
 *   mismo patron ya validado en Ventas/Bancos/Facturas/Clientes/Proveedores/
 *   Compras -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md),
 *   poblada via ajax contra POST /api/v1/gastos/dt/. DocumentoSoporteTable/
 *   DocumentoSoporteTableView (django-tables2) retirados.
 * - Tabla "Resoluciones DIAN" (#tabla-resoluciones) tambien migrada a
 *   DataTables 3.x, poblada via ajax contra
 *   POST /api/v1/gastos/resoluciones/dt/ (ResolucionDIANViewSet.dt()).
 *   ResolucionDIANTable/ResolucionDIANTableView (django-tables2) retirados.
 * - Este archivo maneja: init de ambas tablas, acciones de fila
 *   (ver/editar/anular/eliminar/desactivar), y apertura de offcanvas.
 */
(function(w, d) {
    'use strict';

    // Namespace
    w.Sintel = w.Sintel || {};
    w.Sintel.Gastos = w.Sintel.Gastos || {};

    // ─── Modulo GastoList ─────────────────────────────────────────────────────

    const GastoList = {
        refresh: function() {
            if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
                w.Sintel.Core.DataTablesFactory.reload('#tabla-gastos');
            }
            // Los KPIs siguen server-rendered via HTMX (kpis_gastos.html).
            d.body.dispatchEvent(new CustomEvent('gasto-updated'));
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
                        w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);

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
        reload: function() {
            if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
                w.Sintel.Core.DataTablesFactory.reload(TABLA_RESOLUCIONES_SELECTOR);
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

    // ─── DataTables (tabla "Gastos" / Documentos Soporte) ──────────────────

    var TABLA_GASTOS_SELECTOR = '#tabla-gastos';
    var TABLA_GASTOS_URL = '/api/v1/gastos/dt/';
    var _gastosTablaInicializada = false;

    function escapeHtmlGasto(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderDocumentoGasto(data, type, row) {
        var numero = row.ds_numero_documento_proveedor || row.ds_numero_documento;
        return '<span class="fw-semibold text-primary" style="font-size:0.85rem;">' + escapeHtmlGasto(numero) + '</span>';
    }

    function renderFechaGasto(data, type, row) {
        return escapeHtmlGasto(row.ds_fecha);
    }

    function renderTotalGasto(data, type, row) {
        var formatted = (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(row.ds_total) : row.ds_total;
        return '<span class="fw-bold">' + formatted + '</span>';
    }

    function renderEstadoGasto(data, type, row) {
        if (row.ds_anulado) {
            return '<span class="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-20 px-2 py-1">Anulado</span>';
        }
        return '<span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-20 px-2 py-1">Activo</span>';
    }

    function renderAccionesGasto(data, type, row) {
        var anulado = row.ds_anulado;
        var editCls = anulado ? 'btn-light disabled' : 'btn-outline-primary';
        var cancelCls = anulado ? 'btn-light disabled' : 'btn-outline-warning';
        return '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-info btn-view-gasto" data-uuid="' + escapeHtmlGasto(row.uuid) + '" title="Ver Detalle"><i class="bi bi-eye"></i></button>' +
            '<button type="button" class="btn ' + editCls + ' btn-edit-gasto" data-uuid="' + escapeHtmlGasto(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn ' + cancelCls + ' btn-cancel-gasto" data-uuid="' + escapeHtmlGasto(row.uuid) + '" title="Anular"><i class="bi bi-x-circle"></i></button>' +
            '<button type="button" class="btn btn-outline-danger btn-delete-gasto" data-uuid="' + escapeHtmlGasto(row.uuid) + '" data-anulado="' + (anulado ? 'true' : 'false') + '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    var GASTOS_COLUMNS = [
        { data: null, title: 'Documento', render: renderDocumentoGasto },
        { data: null, title: 'Fecha', render: renderFechaGasto },
        { data: 'ds_vendedor', title: 'Vendedor / Proveedor' },
        { data: 'categoria_contable_display', title: 'Clasificación' },
        { data: null, title: 'Total', className: 'text-end', render: renderTotalGasto },
        { data: null, title: 'Estado', orderable: false, render: renderEstadoGasto },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccionesGasto },
    ];

    function initGastosTabla() {
        if (_gastosTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_GASTOS_SELECTOR, TABLA_GASTOS_URL, GASTOS_COLUMNS, {
            pageLength: 20,
            order: [[1, 'desc']],
        });
        _gastosTablaInicializada = true;
    }

    // ─── DataTables (tabla "Resoluciones DIAN") ─────────────────────────────

    var TABLA_RESOLUCIONES_SELECTOR = '#tabla-resoluciones';
    var TABLA_RESOLUCIONES_URL = '/api/v1/gastos/resoluciones/dt/';
    var _resolucionesTablaInicializada = false;

    function renderResolucion(data, type, row) {
        return '<div style="line-height:1.35;">' +
            '<div class="fw-semibold text-dark" style="font-size:0.85rem;">' + escapeHtmlGasto(row.numero_resolucion || '—') + '</div>' +
            '<div class="mt-1" style="font-size:0.72rem;"><span class="text-muted">Prefijo:</span> ' +
            '<code class="text-secondary">' + escapeHtmlGasto(row.prefijo || '—') + '</code></div>' +
            '</div>';
    }

    function renderRango(data, type, row) {
        return '<div style="font-size:0.78rem;"><span class="text-muted">Desde:</span> ' + escapeHtmlGasto(row.rango_desde) +
            ' &nbsp;<span class="text-muted">Hasta:</span> ' + escapeHtmlGasto(row.rango_hasta) + '</div>';
    }

    function renderEstadoResolucion(data, type, row) {
        if (row.vigente) {
            return '<span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-20 px-2 py-1">Vigente</span>';
        }
        return '<span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-20 px-2 py-1">Vencida/Inactiva</span>';
    }

    function renderAccionesResolucion(data, type, row) {
        var desactivarBtn = '';
        if (row.vigente) {
            desactivarBtn = '<button type="button" class="btn btn-outline-warning btn-deactivate-resolucion" data-uuid="' +
                escapeHtmlGasto(row.uuid) + '" title="Desactivar"><i class="bi bi-slash-circle"></i></button>';
        }
        return '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-primary btn-edit-resolucion" data-uuid="' + escapeHtmlGasto(row.uuid) +
            '" title="Editar Resolución"><i class="bi bi-pencil"></i></button>' + desactivarBtn + '</div>';
    }

    var RESOLUCIONES_COLUMNS = [
        { data: null, title: 'Resolución', render: renderResolucion },
        { data: null, title: 'Rango Autorizado', orderable: false, render: renderRango },
        { data: 'fecha_fin', title: 'Vencimiento' },
        { data: null, title: 'Estado', render: renderEstadoResolucion },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccionesResolucion },
    ];

    function initResolucionesTabla() {
        if (_resolucionesTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_RESOLUCIONES_SELECTOR, TABLA_RESOLUCIONES_URL, RESOLUCIONES_COLUMNS, {
            pageLength: 20,
            order: [[2, 'desc']],
        });
        insertarFilaFiltrosResoluciones();
        bindFiltrosResoluciones();
        _resolucionesTablaInicializada = true;
    }

    // DataTables reescribe el <thead> completo al inicializarse -- la fila de
    // filtros se construye e inserta en JS DESPUES de crear el DataTable (ver
    // el mismo patron ya documentado en venta_list.js/insertarFilaFiltros()).

    function filaFiltrosResolucionesHtml() {
        return '<tr id="fila-filtros-resoluciones" class="table-light">' +
            '<th><input type="text" class="form-control form-control-sm" id="filtro-resolucion-numero" placeholder="Filtrar resolución..."></th>' +
            '<th></th>' +
            '<th><div class="d-flex gap-1">' +
            '<input type="date" class="form-control form-control-sm" id="filtro-resolucion-fecha-desde" title="Desde">' +
            '<input type="date" class="form-control form-control-sm" id="filtro-resolucion-fecha-hasta" title="Hasta">' +
            '</div></th>' +
            '<th><select class="form-select form-select-sm" id="filtro-resolucion-estado">' +
            '<option value="">Todas</option>' +
            '<option value="true">Vigente</option>' +
            '<option value="false">Vencida/Inactiva</option>' +
            '</select></th>' +
            '<th></th>' +
            '</tr>';
    }

    function insertarFilaFiltrosResoluciones() {
        var thead = d.querySelector(TABLA_RESOLUCIONES_SELECTOR + ' thead');
        if (!thead || d.getElementById('filtro-resolucion-numero')) return;
        thead.insertAdjacentHTML('beforeend', filaFiltrosResolucionesHtml());
    }

    function debounceResoluciones(fn, delay) {
        var timer = null;
        return function () {
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () { fn.apply(null, args); }, delay);
        };
    }

    function bindFiltrosResoluciones() {
        var Factory = w.Sintel.Core.DataTablesFactory;

        var inputNumero = d.getElementById('filtro-resolucion-numero');
        if (inputNumero) {
            inputNumero.addEventListener('keyup', debounceResoluciones(function () {
                Factory.columnSearch(TABLA_RESOLUCIONES_SELECTOR, 0, inputNumero.value);
            }, 400));
        }

        var fechaDesde = d.getElementById('filtro-resolucion-fecha-desde');
        var fechaHasta = d.getElementById('filtro-resolucion-fecha-hasta');
        function aplicarRangoFecha() {
            Factory.columnRangeSearch(TABLA_RESOLUCIONES_SELECTOR, 2, fechaDesde.value, fechaHasta.value);
        }
        if (fechaDesde) fechaDesde.addEventListener('change', aplicarRangoFecha);
        if (fechaHasta) fechaHasta.addEventListener('change', aplicarRangoFecha);

        var selectEstado = d.getElementById('filtro-resolucion-estado');
        if (selectEstado) {
            selectEstado.addEventListener('change', function () {
                Factory.columnSearch(TABLA_RESOLUCIONES_SELECTOR, 3, selectEstado.value);
            });
        }
    }

    // ─── Event Delegation (Acciones de la Grilla) ─────────────────────────────
    // Los botones son server-rendered por tables.py (render_acciones) y conservan
    // las mismas clases/data-uuid que antes, por eso esta delegacion no cambia.

    function initListEvents() {
        // Gastos: acciones de fila de la tabla DataTables (#tabla-gastos).
        // Delegado sobre document.body (persistente -- la tabla se recrea
        // via ajax.reload(), nunca via innerHTML swap de un contenedor).
        {
            d.body.addEventListener('click', async (e) => {
                if (!e.target.closest('#tabla-gastos')) return;
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

        // Resoluciones: acciones de fila de la tabla DataTables (#tabla-resoluciones).
        // Delegado sobre document.body (persistente -- la tabla se recrea via
        // ajax.reload(), nunca via innerHTML swap de un contenedor).
        {
            d.body.addEventListener('click', async (e) => {
                if (!e.target.closest('#tabla-resoluciones')) return;
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

        // 'resolucion-created' lo dispara resolucion_editor.js tras crear/editar
        // (ver document.body.dispatchEvent en handleSubmit) -- antes disparaba
        // el hx-trigger del panel HTMX retirado; ahora recarga la tabla directo.
        d.body.addEventListener('resolucion-created', function () {
            ResolucionList.reload();
        });
    }

    // ─── Setup e Inicializacion Segura ────────────────────────────────────────
    // #tabla-gastos y #tabla-resoluciones son esqueletos estaticos que no se
    // reinsertan via HTMX -- initGastosTabla()/initResolucionesTabla() tienen
    // su propio guard (_gastosTablaInicializada/_resolucionesTablaInicializada)
    // por eso, y este script no se re-ejecuta completo como antes.

    function setup() {
        initGastosTabla();
        initResolucionesTabla();
        initListEvents();
    }

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
                        w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);

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

    // API Publica
    w.Sintel.Gastos.GastoList = GastoList;
    w.Sintel.Gastos.ResolucionList = ResolucionList;
    w.Sintel.Gastos.List = GastoList; // Legacy alias

})(window, document);
