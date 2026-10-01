/**
 * Feature: Listado y maquina de estados de Requisiciones de Compra
 * DataTables 3.x (#tabla-requisiciones-compra), mismo patron que
 * compras_list.js (ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md).
 */
(function(w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Compras = w.Sintel.Compras || {};

    const RequisicionesList = {
        refresh: function() {
            if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
                w.Sintel.Core.DataTablesFactory.reload('#tabla-requisiciones-compra');
            }
            d.body.dispatchEvent(new CustomEvent('requisicion-updated'));
        },

        verDetalle: function(uuid) {
            const url = w.Sintel.Compras.API.requisiciones.renderDetalle(uuid);
            if (w.htmx) {
                w.htmx.ajax('GET', url, { target: '#offcanvas-container-requisiciones', swap: 'innerHTML' });
            }
        },

        editar: function(uuid) {
            const url = w.Sintel.Compras.API.requisiciones.renderEditar(uuid);
            if (w.htmx) {
                w.htmx.ajax('GET', url, { target: '#offcanvas-container-requisiciones', swap: 'innerHTML' });
            }
        },

        eliminar: async function(uuid) {
            const confirmed = await w.UIManager?.confirm(
                '¿Está seguro de eliminar esta requisición? Solo se permite en estado Borrador.'
            );
            if (!confirmed) return;
            try {
                await w.Sintel.Compras.API.requisiciones.eliminar(uuid);
                w.UIManager?.notifySuccess('Requisición eliminada correctamente');
                this.refresh();
            } catch (error) {
                w.UIManager?.handleError?.(error) || w.UIManager?.notifyError?.(error?.data?.message || 'Error al eliminar.');
            }
        }
    };

    // ─── DataTables ──────────────────────────────────────────────────────

    var TABLA_SELECTOR = '#tabla-requisiciones-compra';
    var TABLA_URL = '/api/v1/compras/requisiciones/dt/';
    var _tablaInicializada = false;

    var BADGE_ESTADO_REQ = {
        BORRADOR: ['bg-secondary bg-opacity-10 text-secondary', 'border-secondary border-opacity-20'],
        PENDIENTE_APROBACION: ['bg-warning bg-opacity-10 text-warning-emphasis', 'border-warning border-opacity-20'],
        APROBADA: ['bg-success bg-opacity-10 text-success', 'border-success border-opacity-20'],
        RECHAZADA: ['bg-danger bg-opacity-10 text-danger', 'border-danger border-opacity-20'],
        CANCELADA: ['bg-dark bg-opacity-10 text-dark', 'border-dark border-opacity-20'],
        EN_PROCESO_COMPRA: ['bg-info bg-opacity-10 text-info-emphasis', 'border-info border-opacity-20'],
        PARCIALMENTE_ATENDIDA: ['bg-info bg-opacity-10 text-info-emphasis', 'border-info border-opacity-20'],
        ATENDIDA: ['bg-success bg-opacity-10 text-success', 'border-success border-opacity-20'],
    };

    function escapeHtmlReq(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function formatFechaReq(iso) {
        if (!iso) return null;
        var parsed = new Date(iso + 'T00:00:00');
        if (isNaN(parsed.getTime())) return escapeHtmlReq(iso);
        return parsed.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
    }

    function renderNumero(value) {
        return '<span class="fw-bold text-primary" style="font-size:0.85rem;">' + escapeHtmlReq(value || '—') + '</span>';
    }

    function renderFechaReq(value) {
        var f = formatFechaReq(value);
        return f ? '<i class="bi bi-calendar2 me-1 text-muted"></i>' + f : '<span class="text-muted">—</span>';
    }

    function renderSolicitante(data, type, row) {
        return escapeHtmlReq(row.solicitante_nombre || '—');
    }

    function renderProyectoReq(data, type, row) {
        if (!row.proyecto_nombre) return '<span class="text-muted small">—</span>';
        return '<span class="badge bg-light text-dark border border-secondary"><i class="bi bi-folder text-secondary me-1"></i>' + escapeHtmlReq(row.proyecto_nombre) + '</span>';
    }

    function renderCotizacionOrigenReq(data, type, row) {
        if (!row.cotizacion_origen_numero) return '<span class="text-muted small">—</span>';
        return '<span class="badge bg-info bg-opacity-10 text-info-emphasis border border-info border-opacity-25">' +
            '<i class="bi bi-file-earmark-text me-1"></i>' + escapeHtmlReq(row.cotizacion_origen_numero) + '</span>';
    }

    function renderTotalReq(value) {
        var formatted = (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(value) : value;
        return '<span class="fw-bold text-dark">' + formatted + '</span>';
    }

    function renderEstadoReq(value) {
        var cfg = BADGE_ESTADO_REQ[value] || ['bg-secondary text-white', 'border-secondary'];
        return '<span class="badge ' + cfg[0] + ' border ' + cfg[1] + ' px-2 py-1">' + escapeHtmlReq(value) + '</span>';
    }

    function renderAccionesReq(data, type, row) {
        var canEdit = row.estado === 'BORRADOR';
        var canDelete = row.estado === 'BORRADOR';
        var editCls = canEdit ? 'btn-outline-primary' : 'btn-light disabled';
        var deleteCls = canDelete ? 'btn-outline-danger' : 'btn-light disabled';
        return '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-info btn-view-req" data-uuid="' + escapeHtmlReq(row.uuid) + '" title="Ver Detalle"><i class="bi bi-eye"></i></button>' +
            '<button type="button" class="btn ' + editCls + ' btn-edit-req" data-uuid="' + escapeHtmlReq(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn ' + deleteCls + ' btn-delete-req" data-uuid="' + escapeHtmlReq(row.uuid) + '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    var REQ_COLUMNS = [
        { data: 'numero_documento', title: 'Número', render: renderNumero },
        { data: 'fecha_solicitud', title: 'Fecha Solicitud', render: renderFechaReq },
        { data: 'fecha_necesidad', title: 'Fecha Necesidad', render: renderFechaReq },
        { data: null, title: 'Solicitante', orderable: false, render: renderSolicitante },
        { data: null, title: 'Cotización Origen', orderable: false, searchable: false, render: renderCotizacionOrigenReq },
        { data: null, title: 'Proyecto', orderable: false, searchable: false, render: renderProyectoReq },
        { data: 'total_estimado', title: 'Total Estimado', render: function(v) { return renderTotalReq(v); } },
        { data: 'estado', title: 'Estado', render: renderEstadoReq },
        { data: null, title: '', orderable: false, searchable: false, render: renderAccionesReq },
    ];

    function initTabla() {
        if (_tablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        if (!d.querySelector(TABLA_SELECTOR)) return;
        w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, TABLA_URL, REQ_COLUMNS, {
            pageLength: 20,
            order: [[1, 'desc']],
        });
        _tablaInicializada = true;
    }

    // ─── Panel "Generar Orden de Compra" ────────────────────────────────

    var _plantillasCache = null;

    // Fase 5 (PLAN_OPTIMIZACION_COMPRAS...): unico transporte oficial
    // (Sintel.Core.Http, mismo motor que compras.api.js::_fetch) -- antes
    // era el ultimo consumidor interno de getHeaders()+fetch() directo.
    async function fetchJson(url) {
        var res = await w.Sintel.Core.Http.request('GET', url);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        var data = res.data;
        return (data && data.results) || data;
    }

    async function poblarSelectPlantillas(select) {
        if (!_plantillasCache) {
            try { _plantillasCache = await fetchJson('/api/v1/compras/plantillas/?vigente=true'); }
            catch (e) { _plantillasCache = []; }
        }
        select.innerHTML = '<option value="">Seleccione plantilla...</option>' +
            _plantillasCache.map(function(p) {
                return '<option value="' + p.uuid + '">' + escapeHtmlReq(p.nombre) + (p.prefijo ? ' (' + p.prefijo + ')' : '') + '</option>';
            }).join('');
    }

    // Fase 4 (PLAN_OPTIMIZACION_COMPRAS...): buscador bajo demanda -- antes
    // precargaba `/api/v1/proveedores/` UNA vez sin `?search=` (paginado 20
    // por defecto), asi que un proveedor fuera de los primeros 20 de la
    // empresa era imposible de seleccionar para "Generar Orden de Compra".
    function initBuscadorProveedorOrden(offcanvasEl) {
        var inputBuscar = offcanvasEl.querySelector('#req-orden-proveedor-buscar');
        if (!inputBuscar || inputBuscar.dataset.buscadorInitialized) return;
        inputBuscar.dataset.buscadorInitialized = 'true';
        w.Sintel.Compras.Utils.initBuscadorAsync(offcanvasEl, {
            inputSelector: '#req-orden-proveedor-buscar',
            hiddenSelector: '#req-orden-proveedor',
            resultsSelector: '#req-orden-proveedor-resultados',
            fetchFn: function(q) { return w.Sintel.Compras.Utils.fetchProveedores(q); },
            getValue: function(p) { return p.uuid || p.id; },
            getLabel: function(p) { return (p.razon_social || p.nombre || '') + ' (' + (p.numero_documento || p.nit || '') + ')'; },
        });
    }

    // Fase 4 (PLAN_OPTIMIZACION_COMPRAS...): buscador bajo demanda -- antes
    // precargaba `/api/v1/cotizaciones/` UNA vez sin `?search=` (paginado 20
    // por defecto). `_cotizacionVincYaVinculadas` se actualiza en cada
    // apertura del panel (ver click de `.btn-req-mostrar-vincular-cotizacion`
    // mas abajo) y se aplica como filtro sobre cada pagina de resultados.
    var _cotizacionVincYaVinculadas = [];
    function initBuscadorCotizacionVinc(offcanvasEl) {
        var inputBuscar = offcanvasEl.querySelector('#req-cotizacion-buscar');
        if (!inputBuscar || inputBuscar.dataset.buscadorInitialized) return;
        inputBuscar.dataset.buscadorInitialized = 'true';
        w.Sintel.Compras.Utils.initBuscadorAsync(offcanvasEl, {
            inputSelector: '#req-cotizacion-buscar',
            hiddenSelector: '#req-cotizacion-select',
            resultsSelector: '#req-cotizacion-resultados',
            minChars: 2,
            fetchFn: function(q) {
                return w.Sintel.Compras.Utils.fetchCotizaciones(q).then(function(items) {
                    return items.filter(function(c) { return _cotizacionVincYaVinculadas.indexOf(c.uuid) === -1; });
                });
            },
            getValue: function(c) { return c.uuid || c.id; },
            getLabel: function(c) { return (c.numero_cotizacion || '') + ' — ' + (c.cliente_nombre || c.cliente_razon_social || 'Sin cliente'); },
        });
    }

    function mostrarPanelGenerarOrden(offcanvasEl) {
        var panel = offcanvasEl.querySelector('#req-generar-orden-panel');
        var tbody = offcanvasEl.querySelector('#req-orden-items-tbody');
        if (!panel || !tbody) return;

        var filasItems = offcanvasEl.querySelectorAll('.table-items tbody tr[data-item-uuid]');
        tbody.innerHTML = '';
        var hayPendientes = false;
        filasItems.forEach(function(tr) {
            var pendiente = parseFloat(tr.getAttribute('data-item-pendiente')) || 0;
            if (pendiente <= 0) return;
            hayPendientes = true;
            var itemUuid = tr.getAttribute('data-item-uuid');
            var desc = tr.getAttribute('data-item-descripcion');
            var row = d.createElement('tr');
            row.setAttribute('data-item-uuid', itemUuid);
            row.innerHTML =
                '<td><input type="checkbox" class="req-orden-item-check" checked></td>' +
                '<td>' + escapeHtmlReq(desc) + '</td>' +
                '<td class="text-end">' + pendiente + '</td>' +
                '<td><input type="number" step="0.01" min="0.01" max="' + pendiente + '" value="' + pendiente + '" class="form-control form-control-sm text-end req-orden-item-cantidad"></td>';
            tbody.appendChild(row);
        });

        if (!hayPendientes) {
            w.UIManager?.notifyError?.('No hay items pendientes por ordenar en esta requisición.');
            return;
        }

        panel.classList.remove('d-none');
        poblarSelectPlantillas(offcanvasEl.querySelector('#req-orden-plantilla'));
        initBuscadorProveedorOrden(offcanvasEl);
        panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    async function confirmarGenerarOrden(offcanvasEl) {
        var uuid = offcanvasEl.getAttribute('data-requisicion-uuid');
        var plantilla = offcanvasEl.querySelector('#req-orden-plantilla')?.value;
        var proveedor = offcanvasEl.querySelector('#req-orden-proveedor')?.value;
        var feedbackEl = offcanvasEl.querySelector('#req-generar-orden-feedback');
        var hoy = new Date().toISOString().slice(0, 10);

        function showError(msg) {
            if (feedbackEl) { feedbackEl.textContent = msg; feedbackEl.classList.remove('d-none'); }
        }

        if (!plantilla || !proveedor) {
            showError('Debe seleccionar plantilla y proveedor.');
            return;
        }

        var items = [];
        offcanvasEl.querySelectorAll('#req-orden-items-tbody tr').forEach(function(tr) {
            var check = tr.querySelector('.req-orden-item-check');
            if (!check || !check.checked) return;
            var cantidad = parseFloat(tr.querySelector('.req-orden-item-cantidad')?.value) || 0;
            if (cantidad <= 0) return;
            items.push({ requisicion_item_uuid: tr.getAttribute('data-item-uuid'), cantidad: cantidad });
        });

        if (!items.length) {
            showError('Debe seleccionar al menos un item con cantidad mayor a cero.');
            return;
        }

        var btn = offcanvasEl.querySelector('#btn-confirmar-generar-orden');
        if (btn) { btn.disabled = true; btn.textContent = 'Generando...'; }

        try {
            await w.Sintel.Compras.API.requisiciones.crearOrden(uuid, {
                plantilla: plantilla, proveedor: proveedor, fecha: hoy,
            }, items);
            w.UIManager?.notifySuccess?.('Orden de compra generada correctamente.');
            var bsInstance = w.bootstrap?.Offcanvas?.getInstance(offcanvasEl);
            if (bsInstance) bsInstance.hide();
            RequisicionesList.refresh();
            d.body.dispatchEvent(new CustomEvent('compra-updated'));
        } catch (err) {
            var msg = (err.data && (err.data.message || err.data.detail)) || 'Error al generar la orden de compra.';
            showError(msg);
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = 'Generar Orden de Compra'; }
        }
    }

    // ─── Event Delegation ────────────────────────────────────────────────

    function initListEvents() {
        d.body.addEventListener('click', async function(e) {
            var btnView = e.target.closest('.btn-view-req');
            var btnEdit = e.target.closest('.btn-edit-req');
            var btnDel = e.target.closest('.btn-delete-req');

            if (btnView) {
                e.preventDefault(); e.stopPropagation();
                var uuid = btnView.getAttribute('data-uuid');
                if (uuid) RequisicionesList.verDetalle(uuid);
                return;
            }
            if (btnEdit) {
                e.preventDefault(); e.stopPropagation();
                if (btnEdit.classList.contains('disabled')) return;
                var uuid2 = btnEdit.getAttribute('data-uuid');
                if (uuid2) RequisicionesList.editar(uuid2);
                return;
            }
            if (btnDel) {
                e.preventDefault(); e.stopPropagation();
                if (btnDel.classList.contains('disabled')) return;
                var uuid3 = btnDel.getAttribute('data-uuid');
                if (uuid3) RequisicionesList.eliminar(uuid3);
                return;
            }
        });

        d.body.addEventListener('requisicion-changed', function() { RequisicionesList.refresh(); });

        var container = d.querySelector('#offcanvas-container-requisiciones');
        if (!container) return;

        container.addEventListener('click', async function(e) {
            var offcanvasEl = container.querySelector('.offcanvas');
            if (!offcanvasEl) return;
            var uuid = offcanvasEl.getAttribute('data-requisicion-uuid');

            function cerrarYRefrescar(msg) {
                w.UIManager?.notifySuccess?.(msg);
                var bsInstance = w.bootstrap?.Offcanvas?.getInstance(offcanvasEl);
                if (bsInstance) bsInstance.hide();
                RequisicionesList.refresh();
            }

            if (e.target.closest('.btn-req-enviar-aprobacion')) {
                e.preventDefault();
                var confirmed = await w.UIManager?.confirm('¿Enviar esta requisición a aprobación?');
                if (!confirmed) return;
                try {
                    await w.Sintel.Compras.API.requisiciones.enviarAprobacion(uuid);
                    cerrarYRefrescar('Requisición enviada a aprobación.');
                } catch (err) {
                    w.UIManager?.notifyError?.((err.data && err.data.message) || 'Error al enviar a aprobación.');
                }
                return;
            }

            if (e.target.closest('.btn-req-aprobar')) {
                e.preventDefault();
                var confirmedA = await w.UIManager?.confirm('¿Aprobar esta requisición?');
                if (!confirmedA) return;
                try {
                    await w.Sintel.Compras.API.requisiciones.aprobar(uuid);
                    cerrarYRefrescar('Requisición aprobada.');
                } catch (err) {
                    w.UIManager?.notifyError?.((err.data && err.data.message) || 'Error al aprobar.');
                }
                return;
            }

            if (e.target.closest('.btn-req-cancelar')) {
                e.preventDefault();
                var confirmedC = await w.UIManager?.confirm('¿Cancelar esta requisición? Esta accion no se puede revertir.');
                if (!confirmedC) return;
                try {
                    await w.Sintel.Compras.API.requisiciones.cancelar(uuid);
                    cerrarYRefrescar('Requisición cancelada.');
                } catch (err) {
                    w.UIManager?.notifyError?.((err.data && err.data.message) || 'Error al cancelar.');
                }
                return;
            }

            if (e.target.closest('.btn-req-mostrar-rechazar')) {
                e.preventDefault();
                offcanvasEl.querySelector('#req-rechazar-panel')?.classList.remove('d-none');
                offcanvasEl.querySelector('#req-rechazar-panel')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }

            if (e.target.closest('#btn-cancelar-rechazo')) {
                e.preventDefault();
                offcanvasEl.querySelector('#req-rechazar-panel')?.classList.add('d-none');
                return;
            }

            if (e.target.closest('#btn-confirmar-rechazo')) {
                e.preventDefault();
                var motivo = offcanvasEl.querySelector('#req-motivo-rechazo')?.value?.trim();
                if (!motivo) {
                    w.UIManager?.notifyError?.('Debe indicar el motivo del rechazo.');
                    return;
                }
                try {
                    await w.Sintel.Compras.API.requisiciones.rechazar(uuid, motivo);
                    cerrarYRefrescar('Requisición rechazada.');
                } catch (err) {
                    w.UIManager?.notifyError?.((err.data && err.data.message) || 'Error al rechazar.');
                }
                return;
            }

            if (e.target.closest('.btn-req-mostrar-generar-orden')) {
                e.preventDefault();
                mostrarPanelGenerarOrden(offcanvasEl);
                return;
            }

            if (e.target.closest('.btn-req-mostrar-vincular-cotizacion')) {
                e.preventDefault();
                var panelVinc = offcanvasEl.querySelector('#req-vincular-cotizacion-panel');
                var selectVinc = offcanvasEl.querySelector('#req-cotizacion-select');
                if (!panelVinc || !selectVinc) return;
                var yaVinculadas = Array.prototype.map.call(
                    offcanvasEl.querySelectorAll('[data-cotizacion-vinculada-uuid]'),
                    function(el) { return el.getAttribute('data-cotizacion-vinculada-uuid'); }
                );
                panelVinc.classList.remove('d-none');
                _cotizacionVincYaVinculadas = yaVinculadas;
                initBuscadorCotizacionVinc(offcanvasEl);
                panelVinc.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }

            if (e.target.closest('#btn-cancelar-vincular-cotizacion')) {
                e.preventDefault();
                offcanvasEl.querySelector('#req-vincular-cotizacion-panel')?.classList.add('d-none');
                return;
            }

            if (e.target.closest('#btn-confirmar-vincular-cotizacion')) {
                e.preventDefault();
                var cotizacionUuid = offcanvasEl.querySelector('#req-cotizacion-select')?.value;
                var feedbackVinc = offcanvasEl.querySelector('#req-vincular-cotizacion-feedback');
                function showErrorVinc(msg) {
                    if (feedbackVinc) { feedbackVinc.textContent = msg; feedbackVinc.classList.remove('d-none'); }
                }
                if (!cotizacionUuid) { showErrorVinc('Debe seleccionar una cotización.'); return; }
                var btnVinc = offcanvasEl.querySelector('#btn-confirmar-vincular-cotizacion');
                if (btnVinc) { btnVinc.disabled = true; btnVinc.textContent = 'Vinculando...'; }
                try {
                    await w.Sintel.Compras.API.requisiciones.vincularCotizacion(uuid, cotizacionUuid);
                    w.UIManager?.notifySuccess?.('Cotización vinculada correctamente.');
                    RequisicionesList.verDetalle(uuid);
                } catch (err) {
                    showErrorVinc((err.data && err.data.message) || 'Error al vincular la cotización.');
                } finally {
                    if (btnVinc) { btnVinc.disabled = false; btnVinc.textContent = 'Vincular'; }
                }
                return;
            }

            if (e.target.closest('.btn-req-sincronizar-trazabilidad')) {
                e.preventDefault();
                try {
                    const resultado = await w.Sintel.Compras.API.requisiciones.sincronizarTrazabilidad(uuid);
                    if (resultado.cotizacion || resultado.factura) {
                        w.UIManager?.notifySuccess?.('Trazabilidad sincronizada desde el proyecto.');
                    } else {
                        w.UIManager?.notifyInfo?.('No se encontró cotización ni factura asociada al proyecto todavía.')
                            || w.UIManager?.notifySuccess?.('No se encontró cotización ni factura asociada al proyecto todavía.');
                    }
                    RequisicionesList.verDetalle(uuid);
                } catch (err) {
                    w.UIManager?.notifyError?.((err.data && err.data.message) || 'Error al sincronizar trazabilidad.');
                }
                return;
            }

            if (e.target.closest('#btn-cancelar-generar-orden')) {
                e.preventDefault();
                offcanvasEl.querySelector('#req-generar-orden-panel')?.classList.add('d-none');
                return;
            }

            if (e.target.closest('#req-orden-check-all')) {
                var checked = e.target.checked;
                offcanvasEl.querySelectorAll('.req-orden-item-check').forEach(function(cb) { cb.checked = checked; });
                return;
            }

            if (e.target.closest('#btn-confirmar-generar-orden')) {
                e.preventDefault();
                confirmarGenerarOrden(offcanvasEl);
                return;
            }
        });
    }

    // ─── Setup ───────────────────────────────────────────────────────────

    function setup() {
        initTabla();
        initListEvents();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }

    d.body.addEventListener('tab-activated', function(evt) {
        if (evt?.detail?.tabName !== 'compras') return;
        initTabla();
        if (_tablaInicializada && w.Sintel.Core?.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
        }
    });

    d.body.addEventListener('htmx:afterSettle', function(evt) {
        var target = evt.detail.target;
        if (!target || target.id !== 'offcanvas-container-requisiciones') return;
        setTimeout(function() {
            var offcanvasEl = target.querySelector('.offcanvas');
            if (!offcanvasEl || !w.bootstrap?.Offcanvas) return;
            try {
                w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                var form = offcanvasEl.querySelector('#requisicion-crear-form');
                if (form) w.Sintel.Compras.initRequisicionForm?.(offcanvasEl);
            } catch (error) {
                console.error('[RequisicionesList] Error abriendo offcanvas HTMX:', error);
            }
        }, 10);
    });

    d.body.addEventListener('htmx:beforeCleanupElement', function(evt) {
        var el = evt?.detail?.elt;
        if (el && el.classList && el.classList.contains('offcanvas') && el.closest('#offcanvas-container-requisiciones')) {
            try {
                if (w.bootstrap?.Offcanvas) {
                    var instance = w.bootstrap.Offcanvas.getInstance(el);
                    if (instance) instance.dispose();
                }
            } catch (e) { console.warn('[RequisicionesList] Error limpiando offcanvas:', e); }
        }
    });

    w.Sintel.Compras.RequisicionesList = RequisicionesList;

})(window, document);
