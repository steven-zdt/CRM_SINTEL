/**
 * Feature: Listado de Ordenes de Compra v5.1.0
 * - Tabla "Ordenes de Compra" es DataTables 3.x (#tabla-ordenes-compra,
 *   mismo patron ya validado en Ventas/Bancos/Facturas/Clientes/Proveedores
 *   -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via
 *   ajax contra POST /api/v1/compras/dt/. OrdenCompraTable/OrdenCompraTableView
 *   (django-tables2) retirados; los KPIs siguen server-rendered via HTMX
 *   (kpis_compras.html).
 * - Tabla "Plantillas de Numeracion" (#tabla-plantillas-compra) tambien
 *   migrada a DataTables 3.x, poblada via ajax contra
 *   POST /api/v1/compras/plantillas/dt/ (PlantillaOrdenCompraViewSet.dt()).
 *   PlantillaOrdenCompraTable/PlantillaOrdenCompraTableView (django-tables2)
 *   retirados.
 * - Este archivo maneja: init de ambas tablas, acciones de fila
 *   (ver/editar/eliminar/cambiar estado, activar/desactivar plantilla), el
 *   formulario de "Nueva Plantilla", y el manejo de offcanvas.
 */
(function(w, d) {
    'use strict';

    // Namespace
    w.Sintel = w.Sintel || {};
    w.Sintel.Compras = w.Sintel.Compras || {};

    // ─── Modulo ComprasList ───────────────────────────────────────────────────

    const ComprasList = {
        refresh: function() {
            if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
                w.Sintel.Core.DataTablesFactory.reload('#tabla-ordenes-compra');
            }
            // Los KPIs siguen server-rendered via HTMX (kpis_compras.html).
            d.body.dispatchEvent(new CustomEvent('compra-updated'));
        },

        reload: function() {
            this.refresh();
        },

        verDetalle: function(uuid) {
            const url = w.Sintel.Compras.API.endpoints.renderDetalle(uuid);
            if (w.htmx) {
                w.htmx.ajax('GET', url, { target: '#offcanvas-container-compras', swap: 'innerHTML' });
            } else {
                this.loadAndShowOffcanvas(url);
            }
        },

        editarCompra: function(uuid) {
            const url = w.Sintel.Compras.API.endpoints.renderEditar(uuid);
            if (w.htmx) {
                w.htmx.ajax('GET', url, { target: '#offcanvas-container-compras', swap: 'innerHTML' });
            } else {
                this.loadAndShowOffcanvas(url);
            }
        },

        eliminarCompra: async function(uuid) {
            const confirmed = await w.UIManager?.confirm(
                "¿Está seguro de eliminar esta orden de compra permanentemente? Esta acción solo se permite para órdenes en estado Borrador."
            );
            if (!confirmed) return;

            try {
                const response = await w.Sintel.Compras.API.eliminar(uuid);
                if (response.success || response.ok) {
                    w.UIManager?.notifySuccess("Orden de compra eliminada correctamente");
                    this.refresh();
                } else {
                    const msg = response.message || response.detail || "Error al eliminar la orden";
                    w.UIManager?.notifyError(msg);
                }
            } catch (error) {
                w.UIManager?.handleError(error);
            }
        },

        loadAndShowOffcanvas: async function(url) {
            const container = d.querySelector("#offcanvas-container-compras");
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

                        const formCompra = offcanvasEl.querySelector('#compra-crear-form') || offcanvasEl.querySelector('#compra-editar-form');
                        if (formCompra) {
                            d.body.dispatchEvent(new CustomEvent('compra-editor-init', { detail: { form: formCompra } }));
                        }
                    } catch (bootstrapError) {
                        console.error("[ComprasList] Error al inicializar Bootstrap Offcanvas:", bootstrapError);
                    }
                }, 10);
            } catch (error) {
                console.error("[ComprasList] Error cargando offcanvas:", error);
            }
        }
    };

    // ─── DataTables (tabla "Ordenes de Compra") ────────────────────────────

    var TABLA_ORDENES_SELECTOR = '#tabla-ordenes-compra';
    var TABLA_ORDENES_URL = '/api/v1/compras/dt/';
    var _ordenesTablaInicializada = false;

    var BADGE_ESTADO_ORDEN = {
        BORRADOR: ['bg-secondary bg-opacity-10 text-secondary', 'border-secondary border-opacity-20'],
        PENDIENTE: ['bg-warning bg-opacity-10 text-warning-emphasis', 'border-warning border-opacity-20'],
        APROBADA: ['bg-success bg-opacity-10 text-success', 'border-success border-opacity-20'],
        PARCIAL: ['bg-info bg-opacity-10 text-info-emphasis', 'border-info border-opacity-20'],
        RECIBIDA: ['bg-info bg-opacity-10 text-info-emphasis', 'border-info border-opacity-20'],
        ANULADA: ['bg-danger bg-opacity-10 text-danger', 'border-danger border-opacity-20'],
    };

    function escapeHtmlOrden(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function formatFechaOrden(iso) {
        if (!iso) return null;
        var parsed = new Date(iso + 'T00:00:00');
        if (isNaN(parsed.getTime())) return escapeHtmlOrden(iso);
        return parsed.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
    }

    function renderConsecutivo(value) {
        return '<span class="fw-bold text-primary" style="font-size:0.85rem;">' + escapeHtmlOrden(value || '—') + '</span>';
    }

    function renderFecha(value) {
        var f = formatFechaOrden(value);
        return f ? '<i class="bi bi-calendar2 me-1 text-muted"></i>' + f : '<span class="text-muted">—</span>';
    }

    function renderFechaEntrega(value) {
        if (!value) return '<span class="text-muted fst-italic small">No definida</span>';
        return '<i class="bi bi-calendar-check text-muted me-1"></i>' + escapeHtmlOrden(formatFechaOrden(value));
    }

    function renderProveedorOrden(data, type, row) {
        var nombre = row.proveedor_nombre || '—';
        var nitHtml = row.proveedor_nit
            ? '<div class="mt-1 small text-muted">NIT: <code class="text-secondary">' + escapeHtmlOrden(row.proveedor_nit) + '</code></div>' : '';
        return '<div class="fw-semibold text-dark small">' + escapeHtmlOrden(nombre) + '</div>' + nitHtml;
    }

    function renderProyectoOrden(data, type, row) {
        if (!row.proyecto_nombre) return '<span class="text-muted small">—</span>';
        return '<span class="badge bg-light text-dark border border-secondary"><i class="bi bi-folder text-secondary me-1"></i>' + escapeHtmlOrden(row.proyecto_nombre) + '</span>';
    }

    function renderTotalOrden(value) {
        var formatted = (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(value) : value;
        return '<span class="fw-bold text-dark">' + formatted + '</span>';
    }

    function renderEstadoOrden(value) {
        var cfg = BADGE_ESTADO_ORDEN[value] || ['bg-secondary text-white', 'border-secondary'];
        return '<span class="badge ' + cfg[0] + ' border ' + cfg[1] + ' px-2 py-1">' + escapeHtmlOrden(value) + '</span>';
    }

    function renderAccionesOrden(data, type, row) {
        var canEdit = row.estado === 'BORRADOR' || row.estado === 'PENDIENTE';
        var canDelete = row.estado === 'BORRADOR';
        var editCls = canEdit ? 'btn-outline-primary' : 'btn-light disabled';
        var deleteCls = canDelete ? 'btn-outline-danger' : 'btn-light disabled';
        return '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-info btn-view-compra" data-uuid="' + escapeHtmlOrden(row.uuid) + '" title="Ver Detalle"><i class="bi bi-eye"></i></button>' +
            '<button type="button" class="btn ' + editCls + ' btn-edit-compra" data-uuid="' + escapeHtmlOrden(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn ' + deleteCls + ' btn-delete-compra" data-uuid="' + escapeHtmlOrden(row.uuid) + '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    var ORDENES_COLUMNS = [
        { data: 'consecutivo', title: 'Consecutivo', render: renderConsecutivo },
        { data: 'fecha', title: 'Fecha Emisión', render: renderFecha },
        { data: 'fecha_entrega', title: 'Fecha Entrega', render: renderFechaEntrega },
        { data: null, title: 'Proveedor', render: renderProveedorOrden },
        { data: null, title: 'Proyecto', orderable: false, searchable: false, render: renderProyectoOrden },
        { data: 'sede_nombre', title: 'Sede' },
        { data: 'total', title: 'Total', render: function (v) { return renderTotalOrden(v); } },
        { data: 'estado', title: 'Estado', render: renderEstadoOrden },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccionesOrden },
    ];

    function initOrdenesTabla() {
        if (_ordenesTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_ORDENES_SELECTOR, TABLA_ORDENES_URL, ORDENES_COLUMNS, {
            pageLength: 20,
            order: [[1, 'desc']],
        });
        _ordenesTablaInicializada = true;
    }

    // ─── DataTables (tabla "Plantillas de Numeracion") ──────────────────────

    var TABLA_PLANTILLAS_SELECTOR = '#tabla-plantillas-compra';
    var TABLA_PLANTILLAS_URL = '/api/v1/compras/plantillas/dt/';
    var _plantillasTablaInicializada = false;

    function renderPrefijoPlantilla(value) {
        return value ? escapeHtmlOrden(value) : '<span class="text-muted small">—</span>';
    }

    function renderRangoPlantilla(data, type, row) {
        return escapeHtmlOrden(row.rango_desde) + ' – ' + escapeHtmlOrden(row.rango_hasta);
    }

    var TIPO_DOCUMENTO_LABELS_PLANTILLA = {
        ORDEN_COMPRA: 'Orden de Compra',
        REQUISICION: 'Requisición de Compra',
    };

    function renderTipoDocumentoPlantilla(value) {
        var label = TIPO_DOCUMENTO_LABELS_PLANTILLA[value] || value;
        return '<span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-20 px-2 py-1">' +
            escapeHtmlOrden(label) + '</span>';
    }

    function renderVigentePlantilla(value) {
        if (value) {
            return '<span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-20 px-2 py-1">Vigente</span>';
        }
        return '<span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-20 px-2 py-1">Inactiva</span>';
    }

    function renderAccionesPlantilla(data, type, row) {
        var toggleLabel = row.vigente ? 'Desactivar' : 'Activar';
        var toggleIcon = row.vigente ? 'bi-toggle2-off' : 'bi-toggle2-on';
        var toggleCls = row.vigente ? 'btn-outline-secondary' : 'btn-outline-success';
        return '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-primary btn-editar-plantilla" data-uuid="' + escapeHtmlOrden(row.uuid) + '" title="Editar">' +
            '<i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn ' + toggleCls + ' btn-toggle-plantilla" data-uuid="' + escapeHtmlOrden(row.uuid) +
            '" data-vigente="' + (row.vigente ? 'true' : 'false') + '" title="' + toggleLabel + '"><i class="bi ' + toggleIcon + '"></i></button>' +
            '</div>';
    }

    var PLANTILLAS_COLUMNS = [
        { data: 'nombre', title: 'Nombre' },
        { data: 'tipo_documento', title: 'Tipo de Documento', render: function (v) { return renderTipoDocumentoPlantilla(v); } },
        { data: 'prefijo', title: 'Prefijo', render: function (v) { return renderPrefijoPlantilla(v); } },
        { data: null, title: 'Rango', orderable: false, render: renderRangoPlantilla },
        { data: 'consecutivo_actual', title: 'Siguiente Consecutivo' },
        { data: 'vigente', title: 'Estado', render: function (v) { return renderVigentePlantilla(v); } },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccionesPlantilla },
    ];

    function initPlantillasTabla() {
        if (_plantillasTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_PLANTILLAS_SELECTOR, TABLA_PLANTILLAS_URL, PLANTILLAS_COLUMNS, {
            pageLength: 20,
            order: [[5, 'desc']],
        });
        _plantillasTablaInicializada = true;
    }

    // ─── Event Delegation (Acciones de la Grilla y Acciones de Estado en Detalle) ────
    // Los botones son render-eados por compras_list.js (renderAccionesOrden,
    // ver DataTables abajo) y conservan las mismas clases/data-uuid que
    // antes. Se ancla a document.body (persistente, la tabla DataTables se
    // recrea via ajax.reload(), nunca via innerHTML swap del contenedor).

    function initListEvents() {
        {
            d.body.addEventListener('click', async (e) => {
                const btnView = e.target.closest('.btn-view-compra');
                const btnEdit = e.target.closest('.btn-edit-compra');
                const btnDel = e.target.closest('.btn-delete-compra');

                if (btnView) {
                    e.preventDefault();
                    e.stopPropagation();
                    const uuid = btnView.getAttribute('data-uuid');
                    if (uuid) ComprasList.verDetalle(uuid);
                    return;
                }

                if (btnEdit) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (btnEdit.classList.contains('disabled')) return;
                    const uuid = btnEdit.getAttribute('data-uuid');
                    if (uuid) ComprasList.editarCompra(uuid);
                    return;
                }

                if (btnDel) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (btnDel.classList.contains('disabled')) return;
                    const uuid = btnDel.getAttribute('data-uuid');
                    if (uuid) ComprasList.eliminarCompra(uuid);
                    return;
                }
            });
        }

        // CO-1 (2026-09-12): editar/activar/desactivar plantilla desde la
        // fila. DataTables no pasa por HTMX en el swap de <tbody> -- el
        // boton "Editar" ya no puede ser un hx-get declarativo (tables.py
        // lo tenia asi, htmx.process() nunca corre sobre filas inyectadas
        // por ajax.reload()), se dispara con htmx.ajax() manual. Delegado
        // sobre document.body (persistente -- la tabla se recrea via
        // ajax.reload(), nunca via innerHTML swap de un contenedor).
        d.body.addEventListener('click', async (e) => {
            if (!e.target.closest(TABLA_PLANTILLAS_SELECTOR)) return;

            const btnEditar = e.target.closest('.btn-editar-plantilla');
            if (btnEditar) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnEditar.getAttribute('data-uuid');
                if (uuid && w.htmx) {
                    w.htmx.ajax('GET', `/api/v1/compras/plantillas/render-offcanvas/editar/?uuid=${uuid}`, {
                        target: '#offcanvas-container-plantillas', swap: 'innerHTML',
                    });
                }
                return;
            }

            const btnToggle = e.target.closest('.btn-toggle-plantilla');
            if (btnToggle) {
                e.preventDefault();
                e.stopPropagation();

                const uuid = btnToggle.getAttribute('data-uuid');
                const vigenteActual = btnToggle.getAttribute('data-vigente') === 'true';
                const nuevoVigente = !vigenteActual;
                const accionLabel = nuevoVigente ? 'activar' : 'desactivar';
                if (!uuid) return;

                const confirmed = await w.UIManager?.confirm(`¿Está seguro de ${accionLabel} esta plantilla?`);
                if (!confirmed) return;

                btnToggle.disabled = true;
                try {
                    await w.Sintel.Compras.API.plantillas.update(uuid, { vigente: nuevoVigente });
                    w.UIManager?.notifySuccess(`Plantilla ${nuevoVigente ? 'activada' : 'desactivada'} correctamente`);
                    d.body.dispatchEvent(new CustomEvent('plantilla-changed'));
                } catch (error) {
                    btnToggle.disabled = false;
                    w.UIManager?.handleError(error);
                }
            }
        });

        // 'plantilla-changed' lo dispara tanto el toggle de arriba como el
        // formulario de creacion/edicion (mas abajo) -- antes disparaba el
        // hx-trigger del panel HTMX retirado; ahora recarga la tabla directo.
        d.body.addEventListener('plantilla-changed', function () {
            if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
                w.Sintel.Core.DataTablesFactory.reload(TABLA_PLANTILLAS_SELECTOR);
            }
        });

        // Delegacion para los botones de cambiar de estado en el Offcanvas de Detalle
        const container = d.querySelector('#offcanvas-container-compras');
        if (container) {
            container.addEventListener('click', async (e) => {
                const btnEstado = e.target.closest('.btn-cambiar-estado');
                if (btnEstado) {
                    e.preventDefault();
                    e.stopPropagation();
                    const uuid = btnEstado.getAttribute('data-uuid');
                    const nuevoEstado = btnEstado.getAttribute('data-estado');
                    if (!uuid || !nuevoEstado) return;

                    const confirmed = await w.UIManager?.confirm(`¿Está seguro de cambiar el estado de esta orden a ${nuevoEstado}?`);
                    if (!confirmed) return;

                    try {
                        const response = await w.Sintel.Compras.API.cambiarEstado(uuid, nuevoEstado);
                        if (response.uuid) {
                            w.UIManager?.notifySuccess(`Estado cambiado a ${nuevoEstado} correctamente`);

                            const offcanvasEl = container.querySelector('.offcanvas');
                            if (offcanvasEl && w.bootstrap?.Offcanvas) {
                                const instance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
                                if (instance) instance.hide();
                            }

                            ComprasList.refresh();
                        } else {
                            w.UIManager?.notifyError("Error al cambiar el estado");
                        }
                    } catch (error) {
                        w.UIManager?.handleError(error);
                    }
                    return;
                }

                // ── Vincular Requisicion existente (adicional a las ya    ──
                // exigidas al crear la Orden). Busqueda client-side sobre el
                // listado de "disponibles-para-orden" (con saldo real via
                // ProcurementBudgetControlService) -- mismo criterio de
                // seleccion EXPLICITA (nunca auto-match) que Facturas.
                const reqWidget = e.target.closest('#compra-requisicion-widget');
                if (reqWidget) {
                    if (e.target.closest('[data-compra-requisicion-action="mostrar-buscador"]')) {
                        mostrarBuscadorRequisicion(reqWidget);
                        return;
                    }

                    // Quitar una requisicion PENDIENTE (modo creacion, aun sin
                    // guardar la Orden) -- solo local, nunca llama al backend.
                    const btnQuitarPendienteReq = e.target.closest('[data-compra-requisicion-action="quitar-pendiente"]');
                    if (btnQuitarPendienteReq) {
                        const requisicionUuid = btnQuitarPendienteReq.getAttribute('data-requisicion-uuid');
                        reqWidget._requisicionesPendientes = (reqWidget._requisicionesPendientes || [])
                            .filter((r) => r.uuid !== requisicionUuid);
                        renderRequisicionesPendientes(reqWidget);
                        // Contraparte de la sincronizacion automatica: quita del
                        // Detalle de Items solo las filas que vinieron de esta
                        // requisicion (nunca las cargadas a mano).
                        const formReq = reqWidget.closest('form');
                        if (formReq) w.Sintel.Compras.Editor?.quitarItemsDeRequisicion(formReq, requisicionUuid);
                        return;
                    }

                    const btnQuitarReq = e.target.closest('[data-compra-requisicion-action="quitar"]');
                    if (btnQuitarReq) {
                        const requisicionUuid = btnQuitarReq.getAttribute('data-requisicion-uuid');
                        const requisicionNumero = btnQuitarReq.getAttribute('data-requisicion-numero') || '';
                        if (!w.confirm('Quitar la requisicion ' + requisicionNumero + ' de esta Orden de Compra?')) return;
                        const compraUuidReq = reqWidget.getAttribute('data-compra-uuid');
                        btnQuitarReq.disabled = true;
                        w.Sintel.Compras.API.desvincularRequisicion(compraUuidReq, requisicionUuid).then(() => {
                            w.UIManager?.notifySuccess('Requisicion desvinculada.');
                            _cerrarOffcanvasCompraDesde(reqWidget);
                            ComprasList.refresh();
                        }).catch((err) => {
                            btnQuitarReq.disabled = false;
                            const msg = (err.data && (err.data.message || err.data.detail)) || 'No se pudo quitar la requisicion.';
                            w.UIManager?.notifyError(msg);
                        });
                        return;
                    }

                    if (e.target.closest('#compra-requisicion-cancelar-confirm')) {
                        renderResultadosRequisicion(reqWidget, reqWidget.querySelector('#compra-requisicion-buscar-input')?.value || '');
                        return;
                    }

                    if (e.target.closest('#compra-requisicion-confirmar')) {
                        guardarVinculoRequisicion(reqWidget);
                        return;
                    }

                    const btnSeleccionarReq = e.target.closest('[data-requisicion-uuid]:not([data-compra-requisicion-action])');
                    if (btnSeleccionarReq) {
                        seleccionarRequisicionCompra(
                            reqWidget,
                            btnSeleccionarReq.getAttribute('data-requisicion-uuid'),
                            btnSeleccionarReq.getAttribute('data-requisicion-numero'),
                            btnSeleccionarReq.getAttribute('data-requisicion-saldo'),
                        );
                        return;
                    }
                    return;
                }

                // ── Vincular Factura existente (FACTURAS-VENTAS-COMPRAS-01) ──
                // Busqueda + seleccion EXPLICITA (nunca auto-match/auto-assign).
                const widget = e.target.closest('#compra-factura-widget');
                if (!widget) return;

                if (e.target.closest('[data-compra-factura-action="mostrar-buscador"]')) {
                    mostrarBuscadorCompra(widget);
                    return;
                }

                // Quitar la factura pendiente (modo creacion, aun sin
                // guardar) -- ver guardarAsociacionCompra().
                if (e.target.closest('[data-compra-factura-action="quitar-pendiente"]')) {
                    delete widget.dataset.facturaPendienteUuid;
                    delete widget.dataset.facturaPendienteNumero;
                    const asociadaDiv = widget.querySelector('#compra-factura-asociada');
                    if (asociadaDiv) { asociadaDiv.classList.add('d-none'); asociadaDiv.innerHTML = ''; }
                    mostrarBuscadorCompra(widget);
                    return;
                }

                // "Cambiar factura": PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase
                // 16 -- flujo explicito Desvincular -> seleccionar nueva ->
                // vincular, nunca un PATCH silencioso sobre factura_asociada.
                // Se desvincula primero (el backend bloquea con 409 si ya hay
                // pagos aplicados) y solo si eso funciona se abre el buscador.
                const btnCambiar = e.target.closest('[data-compra-factura-action="cambiar"]');
                if (btnCambiar) {
                    if (!w.confirm('Esto quitara el vinculo con la factura actual. Deseas continuar?')) return;
                    btnCambiar.disabled = true;
                    const compraUuid = widget.getAttribute('data-compra-uuid');
                    w.Sintel.Compras.API.desvincularFactura(compraUuid).then(() => {
                        w.UIManager?.notifySuccess('Factura desvinculada.');
                        mostrarBuscadorCompra(widget);
                        ComprasList.refresh();
                    }).catch((err) => {
                        btnCambiar.disabled = false;
                        const msg = (err.data && (err.data.message || err.data.detail)) || 'No se pudo desvincular la factura.';
                        w.UIManager?.notifyError(msg);
                    });
                    return;
                }

                const btnSeleccionar = e.target.closest('[data-factura-uuid]');
                if (btnSeleccionar) {
                    seleccionarFacturaCompra(
                        widget,
                        btnSeleccionar.getAttribute('data-factura-uuid'),
                        btnSeleccionar.getAttribute('data-factura-numero'),
                    );
                    return;
                }

                if (e.target.closest('#compra-factura-cancelar-confirm')) {
                    buscarFacturasCompra(widget, widget.querySelector('#compra-factura-buscar-input')?.value || '');
                    return;
                }

                if (e.target.closest('#compra-factura-confirmar')) {
                    guardarAsociacionCompra(widget, container);
                }
            });

            container.addEventListener('input', (e) => {
                const reqInput = e.target.closest('#compra-requisicion-buscar-input');
                if (reqInput) {
                    // Filtro client-side sobre el cache ya cargado -- sin
                    // round-trip por tecla, el dataset es chico (requisiciones
                    // con saldo disponible de la empresa).
                    const reqWidget = reqInput.closest('#compra-requisicion-widget');
                    renderResultadosRequisicion(reqWidget, reqInput.value);
                }
            });

            let debounceIdCompraFactura = null;
            container.addEventListener('input', (e) => {
                const input = e.target.closest('#compra-factura-buscar-input');
                if (!input) return;
                const widget = input.closest('#compra-factura-widget');
                clearTimeout(debounceIdCompraFactura);
                debounceIdCompraFactura = setTimeout(() => buscarFacturasCompra(widget, input.value), 350);
            });
        }
    }

    // ─── Vincular Requisicion existente ────────────────────────────────────

    function mostrarBuscadorRequisicion(widget) {
        const panel = widget.querySelector('#compra-requisicion-buscador-panel');
        if (panel) panel.classList.remove('d-none');
        const input = widget.querySelector('#compra-requisicion-buscar-input');
        if (input) input.focus();
        if (!widget._requisicionesDisponiblesCache) {
            cargarRequisicionesDisponibles(widget);
        }
    }

    function cargarRequisicionesDisponibles(widget) {
        const resultados = widget.querySelector('#compra-requisicion-buscar-resultados');
        if (resultados) resultados.innerHTML = '<div class="text-muted p-2"><i class="bi bi-arrow-repeat"></i> Cargando requisiciones disponibles...</div>';
        w.Sintel.Compras.API.requisiciones.disponiblesParaOrden().then((items) => {
            widget._requisicionesDisponiblesCache = items || [];
            renderResultadosRequisicion(widget, widget.querySelector('#compra-requisicion-buscar-input')?.value || '');
        }).catch(() => {
            if (resultados) resultados.innerHTML = '<div class="text-danger p-2">Error al cargar requisiciones disponibles.</div>';
        });
    }

    function renderResultadosRequisicion(widget, q) {
        const resultados = widget.querySelector('#compra-requisicion-buscar-resultados');
        if (!resultados) return;
        const cache = widget._requisicionesDisponiblesCache;
        if (!cache) {
            // Todavia no ha terminado la primera carga.
            return;
        }
        // Modo creacion (pendientes locales): nunca ofrecer de nuevo una
        // requisicion ya agregada -- evita duplicarla en la misma Orden
        // antes incluso de guardarla.
        const pendientesUuids = (widget._requisicionesPendientes || []).map((r) => r.uuid);
        let items = cache.filter((r) => pendientesUuids.indexOf(r.uuid) === -1);

        q = (q || '').trim().toLowerCase();
        if (q) items = items.filter((r) => (r.numero_documento || '').toLowerCase().includes(q));

        if (!items.length) {
            resultados.innerHTML = '<div class="text-muted p-2">' +
                (cache.length ? 'Sin resultados.' : 'No hay requisiciones disponibles con saldo.') +
                '</div>';
            return;
        }
        resultados.innerHTML = items.map((r) => `
            <div class="d-flex align-items-center justify-content-between border-bottom py-2 px-1">
              <div>
                <div class="fw-semibold">${r.numero_documento}</div>
                <div class="text-muted" style="font-size:0.78rem;">Saldo disponible: $${r.saldo}</div>
              </div>
              <button type="button" class="btn btn-sm btn-primary flex-shrink-0"
                      data-requisicion-uuid="${r.uuid}" data-requisicion-numero="${r.numero_documento}" data-requisicion-saldo="${r.saldo}">
                Seleccionar
              </button>
            </div>
        `).join('');
    }

    function seleccionarRequisicionCompra(widget, requisicionUuid, requisicionNumero, requisicionSaldo) {
        const resultados = widget.querySelector('#compra-requisicion-buscar-resultados');
        if (!resultados) return;
        resultados.innerHTML = `
            <div class="alert alert-warning p-2 small mb-0">
              Vincular la requisicion <strong>${requisicionNumero}</strong> a esta Orden de Compra?
              <div class="mt-2 d-flex gap-2">
                <button type="button" class="btn btn-success btn-sm" id="compra-requisicion-confirmar"
                        data-requisicion-uuid-confirm="${requisicionUuid}"
                        data-requisicion-numero-confirm="${requisicionNumero}"
                        data-requisicion-saldo-confirm="${requisicionSaldo || 0}">Vincular</button>
                <button type="button" class="btn btn-secondary btn-sm" id="compra-requisicion-cancelar-confirm">Cancelar</button>
              </div>
            </div>
        `;
    }

    function _fmtMoneyCompra(value) {
        const n = parseFloat(value) || 0;
        return (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(n) : ('$' + n.toLocaleString('en-US'));
    }

    // Modo creacion: renderiza la lista de requisiciones PENDIENTES (aun no
    // guardadas) -- mismo widget que usa la Orden ya existente, pero sin
    // tocar el backend hasta handleFormSubmit() (compras_editor.js).
    function renderRequisicionesPendientes(widget) {
        const lista = widget.querySelector('#compra-requisicion-lista');
        const totalEl = widget.querySelector('#compra-requisicion-total-seleccionado');
        if (!lista) return;
        const pendientes = widget._requisicionesPendientes || [];

        if (!pendientes.length) {
            lista.innerHTML = '<div class="text-muted small mb-2">Sin requisiciones agregadas.</div>';
        } else {
            lista.innerHTML = pendientes.map((r) => `
                <div class="d-flex align-items-center justify-content-between border rounded p-2 mb-2">
                  <div>
                    <div class="fw-semibold">${r.numero}</div>
                    <div class="text-muted small">Monto asignado: ${_fmtMoneyCompra(r.saldo)}</div>
                  </div>
                  <button type="button" class="btn btn-outline-danger btn-sm" data-compra-requisicion-action="quitar-pendiente" data-requisicion-uuid="${r.uuid}">
                    <i class="bi bi-x-lg"></i>
                  </button>
                </div>
            `).join('');
        }

        if (totalEl) {
            const total = pendientes.reduce((acc, r) => acc + (parseFloat(r.saldo) || 0), 0);
            totalEl.textContent = 'Total seleccionado: ' + _fmtMoneyCompra(total);
        }
    }

    function _cerrarOffcanvasCompraDesde(el) {
        // No re-renderizar el offcanvas ABIERTO in-place (via htmx swap):
        // Bootstrap mantiene su propia instancia (backdrop, focus trap)
        // sobre el nodo .offcanvas actual -- reemplazar ese DOM mientras
        // sigue "shown" deja handlers internos de Bootstrap apuntando a
        // nodos ya removidos (bug real encontrado en vivo: TypeError
        // "Cannot read properties of null (reading 'classList')" dentro de
        // bootstrap.bundle.min.js). Mismo patron ya usado por
        // guardarAsociacionCompra() para Facturas: cerrar limpio via la
        // API de Bootstrap y refrescar solo la grilla.
        const offcanvasEl = el.closest('.offcanvas');
        if (offcanvasEl && w.bootstrap?.Offcanvas) {
            const instance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
            if (instance) instance.hide();
        }
    }

    function guardarVinculoRequisicion(widget) {
        const btn = widget.querySelector('#compra-requisicion-confirmar');
        if (!btn) return;
        const requisicionUuid = btn.getAttribute('data-requisicion-uuid-confirm');
        const requisicionNumero = btn.getAttribute('data-requisicion-numero-confirm') || '';
        const requisicionSaldo = btn.getAttribute('data-requisicion-saldo-confirm') || '0';
        const compraUuid = widget.getAttribute('data-compra-uuid');

        // Formulario "Nueva Orden de Compra": la Orden aun no existe --
        // se acumula localmente (nunca duplicada, ya excluida de la
        // busqueda en renderResultadosRequisicion) y se envia junto con el
        // resto del formulario al crear (handleFormSubmit en
        // compras_editor.js).
        if (!compraUuid) {
            widget._requisicionesPendientes = widget._requisicionesPendientes || [];
            widget._requisicionesPendientes.push({ uuid: requisicionUuid, numero: requisicionNumero, saldo: requisicionSaldo });
            renderRequisicionesPendientes(widget);
            mostrarBuscadorRequisicion(widget);
            renderResultadosRequisicion(widget, widget.querySelector('#compra-requisicion-buscar-input')?.value || '');

            // Sincroniza automaticamente el Detalle de Items con los items de
            // la requisicion recien vinculada (Val. Unitario <-
            // valor_unitario_estimado) -- complementa "Agregar Item" manual,
            // nunca lo reemplaza. Best effort: si falla, la requisicion ya
            // quedo agregada igual, el usuario puede cargar el detalle a mano.
            const formReq = widget.closest('form');
            if (formReq && w.Sintel.Compras.API.requisiciones.get) {
                w.Sintel.Compras.API.requisiciones.get(requisicionUuid).then((detalle) => {
                    const items = (detalle && detalle.items) || [];
                    w.Sintel.Compras.Editor?.agregarItemsDesdeRequisicion(formReq, requisicionUuid, items);
                }).catch((err) => {
                    console.warn('[compras.list] No se pudo sincronizar el Detalle de Items desde la requisicion:', err);
                });
            }
            return;
        }

        btn.disabled = true;
        w.Sintel.Compras.API.vincularRequisicion(compraUuid, requisicionUuid).then(() => {
            w.UIManager?.notifySuccess('Requisicion vinculada correctamente.');
            _cerrarOffcanvasCompraDesde(widget);
            ComprasList.refresh();
        }).catch((err) => {
            btn.disabled = false;
            const msg = (err.data && (err.data.message || err.data.detail)) || 'Error al vincular la requisicion.';
            w.UIManager?.notifyError(msg);
        });
    }

    function mostrarBuscadorCompra(widget) {
        const asociadaDiv = widget.querySelector('#compra-factura-asociada');
        const buscadorDiv = widget.querySelector('#compra-factura-buscador');
        const panel = widget.querySelector('#compra-factura-buscador-panel');
        if (asociadaDiv) asociadaDiv.classList.add('d-none');
        if (buscadorDiv) buscadorDiv.classList.remove('d-none');
        if (panel) panel.classList.remove('d-none');
        const input = widget.querySelector('#compra-factura-buscar-input');
        if (input) input.focus();
    }

    function buscarFacturasCompra(widget, q) {
        const resultados = widget.querySelector('#compra-factura-buscar-resultados');
        if (!resultados) return;
        q = (q || '').trim();
        if (q.length < 2) {
            resultados.innerHTML = '<div class="text-muted p-2">Escribe al menos 2 caracteres...</div>';
            return;
        }
        resultados.innerHTML = '<div class="text-muted p-2"><i class="bi bi-arrow-repeat"></i> Buscando...</div>';
        w.Sintel.Compras.API.buscarFacturasCompra(q).then((items) => {
            if (!items || !items.length) {
                resultados.innerHTML = '<div class="text-muted p-2">Sin resultados.</div>';
                return;
            }
            resultados.innerHTML = items.map((f) => `
                <div class="d-flex align-items-center justify-content-between border-bottom py-2 px-1">
                  <div>
                    <div class="fw-semibold">${f.numero}</div>
                    <div class="text-muted" style="font-size:0.78rem;">${f.fecha} &middot; ${f.tercero || f.cliente || 'N/A'} &middot; $${f.total}</div>
                  </div>
                  <button type="button" class="btn btn-sm btn-primary flex-shrink-0"
                          data-factura-uuid="${f.uuid}" data-factura-numero="${f.numero}">
                    Seleccionar
                  </button>
                </div>
            `).join('');
        }).catch(() => {
            resultados.innerHTML = '<div class="text-danger p-2">Error al buscar facturas.</div>';
        });
    }

    function seleccionarFacturaCompra(widget, facturaUuid, facturaNumero) {
        const resultados = widget.querySelector('#compra-factura-buscar-resultados');
        if (!resultados) return;
        resultados.innerHTML = `
            <div class="alert alert-warning p-2 small mb-0">
              Asociar la factura <strong>${facturaNumero}</strong> a esta Orden de Compra?
              <div class="mt-2 d-flex gap-2">
                <button type="button" class="btn btn-success btn-sm" id="compra-factura-confirmar"
                        data-factura-uuid-confirm="${facturaUuid}" data-factura-numero-confirm="${facturaNumero}">Guardar asociacion</button>
                <button type="button" class="btn btn-secondary btn-sm" id="compra-factura-cancelar-confirm">Cancelar</button>
              </div>
            </div>
        `;
    }

    function guardarAsociacionCompra(widget, container) {
        const btn = widget.querySelector('#compra-factura-confirmar');
        if (!btn) return;
        const facturaUuid = btn.getAttribute('data-factura-uuid-confirm');
        const facturaNumero = btn.getAttribute('data-factura-numero-confirm') || '';
        const compraUuid = widget.getAttribute('data-compra-uuid');

        // PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 28: formulario "Nueva
        // Orden de Compra" -- la Orden aun no existe (sin data-compra-uuid).
        // Se DIFIERE la vinculacion real hasta que compras_editor.js cree la
        // Orden (handleFormSubmit) -- nunca se llama vincular-factura con un
        // uuid inexistente. Mismo patron que Ventas (facturaPendienteUuid).
        if (!compraUuid) {
            widget.dataset.facturaPendienteUuid = facturaUuid;
            widget.dataset.facturaPendienteNumero = facturaNumero;
            const asociadaDiv = widget.querySelector('#compra-factura-asociada');
            const buscadorDiv = widget.querySelector('#compra-factura-buscador');
            if (asociadaDiv) {
                asociadaDiv.classList.remove('d-none');
                asociadaDiv.innerHTML =
                    '<div class="alert alert-info p-2 small mb-0">' +
                    '  <i class="bi bi-link-45deg me-1"></i>' +
                    '  Se vinculará <strong>' + facturaNumero + '</strong> al crear esta orden.' +
                    '  <button type="button" class="btn btn-sm btn-outline-secondary ms-2" data-compra-factura-action="quitar-pendiente">Quitar</button>' +
                    '</div>';
            }
            if (buscadorDiv) buscadorDiv.classList.add('d-none');
            return;
        }

        btn.disabled = true;
        w.Sintel.Compras.API.vincularFactura(compraUuid, facturaUuid).then(() => {
            w.UIManager?.notifySuccess('Factura asociada correctamente.');
            const offcanvasEl = container.querySelector('.offcanvas');
            if (offcanvasEl && w.bootstrap?.Offcanvas) {
                const instance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (instance) instance.hide();
            }
            ComprasList.refresh();
        }).catch((err) => {
            btn.disabled = false;
            const msg = (err.data && (err.data.message || err.data.detail)) || 'Error al asociar la factura.';
            w.UIManager?.notifyError(msg);
        });
    }

    // ─── Plantilla Form ───────────────────────────────────────────────────────

    function initPlantillaForm(offcanvasEl) {
        const API = w.Sintel?.Compras?.API;
        if (!API) {
            console.error('[ComprasList] API no disponible para plantilla form');
            return;
        }

        const form = offcanvasEl.querySelector('#plantilla-crear-form');
        const modo = form ? form.getAttribute('data-mode') : 'create';
        const plantillaUuid = form ? form.getAttribute('data-plantilla-uuid') : null;
        const feedbackEl = offcanvasEl.querySelector('#form-plantilla-crear-feedback');
        const previewNum = offcanvasEl.querySelector('#plt-preview-num');
        const previewRango = offcanvasEl.querySelector('#plt-preview-rango');
        const tipoDocumentoEl = offcanvasEl.querySelector('#plt-tipo-documento');
        const nombreEl = offcanvasEl.querySelector('#plt-nombre');
        const prefijoEl = offcanvasEl.querySelector('#plt-prefijo');
        const vigente = offcanvasEl.querySelector('#plt-vigente');
        const rangoDesde = offcanvasEl.querySelector('#plt-rango-desde');
        const rangoHasta = offcanvasEl.querySelector('#plt-rango-hasta');
        const btnGuardar = offcanvasEl.querySelector('#btn-guardar-plantilla');

        if (!form) return;

        function updatePreview() {
            const prefijo = prefijoEl?.value?.trim() || '';
            const desde = parseInt(rangoDesde?.value, 10) || 1;
            const hasta = parseInt(rangoHasta?.value, 10) || 9999;
            const primerNum = prefijo ? `${prefijo}-${desde}` : String(desde);
            if (previewNum) previewNum.textContent = primerNum;
            if (previewRango) previewRango.textContent = `${desde} – ${hasta}`;
        }

        [prefijoEl, rangoDesde, rangoHasta].forEach((el) => {
            if (el) el.addEventListener('input', updatePreview);
        });
        updatePreview();

        function showError(msg) {
            if (!feedbackEl) return;
            feedbackEl.textContent = msg;
            feedbackEl.classList.remove('d-none');
        }

        function hideError() {
            if (!feedbackEl) return;
            feedbackEl.classList.add('d-none');
            feedbackEl.textContent = '';
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideError();

            const nombre = nombreEl?.value?.trim() || '';
            const prefijo = prefijoEl?.value?.trim() || '';
            const desde = parseInt(rangoDesde?.value, 10);
            const hasta = parseInt(rangoHasta?.value, 10);
            const esVigente = vigente ? vigente.checked : true;

            if (!nombre) { showError('El nombre es obligatorio.'); return; }
            if (!desde || !hasta) { showError('Ingrese un rango valido.'); return; }
            if (hasta < desde) { showError('El rango hasta debe ser mayor o igual al rango desde.'); return; }

            const esEdicion = (modo === 'edit');
            if (btnGuardar) { btnGuardar.disabled = true; btnGuardar.textContent = esEdicion ? 'Guardando...' : 'Creando...'; }

            try {
                const payload = { nombre, rango_desde: desde, rango_hasta: hasta, vigente: esVigente };
                if (prefijo) payload.prefijo = prefijo;
                // El tipo de documento se fija solo al crear -- en edicion el
                // <select> queda disabled (nunca se puede reasignar una
                // plantilla ya en uso a otro tipo de documento).
                if (!esEdicion && tipoDocumentoEl) payload.tipo_documento = tipoDocumentoEl.value;

                if (esEdicion) {
                    await API.plantillas.update(plantillaUuid, payload);
                } else {
                    await API.plantillas.create(payload);
                }

                const bsInstance = w.bootstrap?.Offcanvas?.getInstance(offcanvasEl);
                if (bsInstance) bsInstance.hide();

                // CO-1/CO-8 (2026-09-12): evento unico para crear/editar --
                // refresca el panel de gestion de plantillas (antes
                // 'plantilla-created' no tenia ningun listener real).
                d.body.dispatchEvent(new CustomEvent('plantilla-changed', { detail: payload }));
                w.UIManager?.showNotification?.(
                    esEdicion ? 'Plantilla actualizada correctamente' : 'Plantilla creada correctamente', 'success'
                );
            } catch (err) {
                const data = err.data || {};
                const msgs = Object.values(data).flat().join(' ') || `Error ${err.status || ''}`;
                showError(msgs);
                console.error('[ComprasList] Error guardando plantilla:', err);
            } finally {
                if (btnGuardar) {
                    btnGuardar.disabled = false;
                    btnGuardar.textContent = esEdicion ? 'Guardar Cambios' : 'Crear Plantilla';
                }
            }
        });
    }

    // ─── Setup ─────────────────────────────────────────────────────────────

    function setup() {
        initOrdenesTabla();
        initPlantillasTabla();
        initListEvents();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

    // Manejo de Offcanvas con HTMX — Ordenes de Compra
    d.body.addEventListener('htmx:afterSettle', (evt) => {
        const target = evt.detail.target;

        if (target && target.id === 'offcanvas-container-compras') {
            setTimeout(() => {
                const offcanvasEl = target.querySelector('.offcanvas');
                if (offcanvasEl && w.bootstrap?.Offcanvas) {
                    try {
                        w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                        const formCompra = offcanvasEl.querySelector('#compra-crear-form') || offcanvasEl.querySelector('#compra-editar-form');
                        if (formCompra) {
                            d.body.dispatchEvent(new CustomEvent('compra-editor-init', { detail: { form: formCompra } }));
                        }
                    } catch (error) {
                        console.error('[ComprasList] Error abriendo offcanvas HTMX:', error);
                    }
                }
            }, 10);
        }

        if (target && target.id === 'offcanvas-container-plantillas') {
            setTimeout(() => {
                const offcanvasEl = target.querySelector('.offcanvas');
                if (offcanvasEl && w.bootstrap?.Offcanvas) {
                    try {
                        w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                        initPlantillaForm(offcanvasEl);
                    } catch (error) {
                        console.error('[ComprasList] Error abriendo offcanvas plantilla HTMX:', error);
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
                    if (instance) instance.dispose();
                }
            } catch (e) {
                console.warn('[ComprasList] Error limpiando offcanvas:', e);
            }
        }
    });

    // API Publica
    w.Sintel.Compras.ComprasList = ComprasList;
    w.Sintel.Compras.List = ComprasList; // Alias

})(window, document);
