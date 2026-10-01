/**
 * Feature: Listado de Facturas v5.0.0
 * - Tablas DataTables 3.x (#tabla-facturas-venta / #tabla-facturas-compra,
 *   mismo patron ya validado en Ventas/Bancos -- ver
 *   docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), pobladas via ajax
 *   contra POST /api/v1/facturas/dt/?naturaleza=venta|compra. Reemplaza
 *   FacturaTable/FacturaTableView (django-tables2, retirados).
 * - Este archivo maneja: init de ambas tablas, acciones de fila
 *   (editar/ver/eliminar), los botones rapidos de "Pago" (columna 5,
 *   estado_pago), el resumen de KPIs (Ventas Netas / Compras Netas,
 *   independiente de la tabla), y el evento 'facturaGuardada' que ahora
 *   recarga ambas tablas via ajax.reload() en vez de HTMX.
 * - No se replico la fila de filtro por columna completa (Cliente/
 *   Vencimiento/Total/DIAN/Cot.) que si tiene Ventas -- alcance acotado
 *   para cubrir primero todas las apps a nivel de UI (busqueda global +
 *   filtro rapido de Pago, que ya cubre el caso de uso mas pedido);
 *   ampliar despues si se prioriza, mismo patron ya probado
 *   (insertarFilaFiltros() post-init) si hace falta.
 * - Simplificación consciente respecto a la versión Tabulator: se retiró el
 *   click-en-fila para abrir el detalle (el botón "Ver" ya cubre ese caso) —
 *   ver REPORTE_FASE_5_PILOTO_TABLAS.md para el detalle de esta decisión.
 */
(function(w, d) {
    'use strict';

    const MOD = '[facturas.list]';

    // ── DataTables (Ventas / Compras) ───────────────────────────────────────

    var TABLAS = [
        { selector: '#tabla-facturas-venta', url: '/api/v1/facturas/dt/?naturaleza=venta' },
        { selector: '#tabla-facturas-compra', url: '/api/v1/facturas/dt/?naturaleza=compra' },
    ];

    var BADGE_DIAN = {
        ACEPTADA: ['bg-success', 'bi-check-circle-fill', 'Aceptada'],
        ENVIADA: ['bg-info', 'bi-send-fill', 'Enviada'],
        BORRADOR: ['bg-secondary', 'bi-pencil', 'Borrador'],
        RECHAZADA: ['bg-danger', 'bi-x-circle-fill', 'Rechazada'],
        ANULADA: ['bg-dark', 'bi-slash-circle', 'Anulada'],
    };

    function escapeHtml(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function formatFecha(iso) {
        if (!iso) return null;
        var parsed = new Date(iso + 'T00:00:00');
        if (isNaN(parsed.getTime())) return escapeHtml(iso);
        return parsed.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: '2-digit' });
    }

    function renderNumero(data, type, row) {
        var ncBadge = row.has_nc
            ? '<span class="badge bg-warning text-dark ms-1" style="font-size:0.65rem;">NC</span>' : '';
        var fecha = formatFecha(row.fecha_emision);
        var fechaHtml = fecha
            ? '<div class="text-muted small"><i class="bi bi-calendar2 me-1"></i>' + fecha + '</div>' : '';
        return '<div class="fw-semibold">' + escapeHtml(row.numero || '---') + ncBadge + '</div>' + fechaHtml;
    }

    function renderContraparte(data, type, row) {
        var isVenta = row.naturaleza === 'VENTA';
        var nombre = isVenta ? row.receptor_razon_social : row.emisor_razon_social;
        var nit = isVenta ? row.receptor_nit : row.emisor_nit;
        var vinculado = isVenta ? !!row.cliente_uuid : !!row.proveedor_uuid;
        var pin = vinculado ? '<i class="bi bi-link-45deg text-success me-1"></i>' : '';
        return '<div class="text-truncate">' + pin + escapeHtml(nombre || '---') + '</div>' +
            '<div class="text-muted small">NIT: ' + escapeHtml(nit || '—') + '</div>';
    }

    function renderVencimiento(data, type, row) {
        var val = row.payment_due_date;
        if (!val) return '<span class="text-muted">—</span>';
        var hoy = new Date(); hoy.setHours(0, 0, 0, 0);
        var vencimiento = new Date(val + 'T00:00:00');
        var vencida = row.estado_pago !== 'PAGADA' && vencimiento < hoy;
        var cls = vencida ? 'text-danger fw-semibold' : '';
        var icono = vencida ? '<i class="bi bi-exclamation-triangle-fill me-1"></i>' : '';
        return '<span class="' + cls + '">' + icono + escapeHtml(formatFecha(val) || '—') + '</span>';
    }

    function renderTotal(value) {
        var formatted = (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
            ? w.DOMUtils.formatCurrency(value) : value;
        return '<span class="fw-semibold">' + formatted + '</span>';
    }

    function renderEstado(value) {
        var cfg = BADGE_DIAN[value] || ['bg-secondary', 'bi-question-circle', value || '---'];
        return '<span class="badge ' + cfg[0] + ' badge-sm"><i class="bi ' + cfg[1] + ' me-1"></i>' + escapeHtml(cfg[2]) + '</span>';
    }

    function renderEstadoPago(value) {
        if (value === 'PAGADA') return '<span class="badge bg-success badge-sm"><i class="bi bi-check2-all me-1"></i>Pagada</span>';
        if (value === 'PAGO_PARCIAL') return '<span class="badge bg-warning text-dark badge-sm"><i class="bi bi-clock-history me-1"></i>Parcial</span>';
        return '<span class="badge bg-danger badge-sm"><i class="bi bi-exclamation-circle me-1"></i>Pendiente</span>';
    }

    function renderCotizacion(value) {
        if (!value) return '<span class="text-muted">—</span>';
        return '<span class="badge text-bg-light border text-truncate" title="' + escapeHtml(value) +
            '" style="font-size:0.7rem;max-width:80px;"><i class="bi bi-receipt me-1"></i>' + escapeHtml(value) + '</span>';
    }

    function renderAcciones(data, type, row) {
        return '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-secondary btn-edit-factura" data-id="' + escapeHtml(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
            '<button type="button" class="btn btn-outline-primary btn-view-factura" data-id="' + escapeHtml(row.uuid) + '" title="Ver"><i class="bi bi-eye"></i></button>' +
            '<button type="button" class="btn btn-outline-danger btn-delete-factura" data-id="' + escapeHtml(row.uuid) + '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    var COLUMNS = [
        { data: 'numero', title: 'Factura', render: renderNumero },
        { data: null, title: 'Cliente / Proveedor', orderable: false, render: renderContraparte },
        { data: 'payment_due_date', title: 'Vencimiento', render: renderVencimiento },
        { data: 'total', title: 'Total', className: 'text-end', render: function (v) { return renderTotal(v); } },
        { data: 'estado', title: 'DIAN', render: renderEstado },
        { data: 'estado_pago', title: 'Pago', render: renderEstadoPago },
        { data: 'cotizacion_numero', title: 'Cot.', orderable: false, render: renderCotizacion },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
    ];

    function bindFiltroPago(tabla) {
        var contenedor = d.querySelector('[data-filtros-pago="' + tabla.selector.replace('#', '') + '"]');
        if (!contenedor) return;
        contenedor.addEventListener('click', function (ev) {
            var btn = ev.target.closest('[data-estado-pago]');
            if (!btn) return;
            contenedor.querySelectorAll('[data-estado-pago]').forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            w.Sintel.Core.DataTablesFactory.columnSearch(tabla.selector, 5, btn.getAttribute('data-estado-pago'));
        });
    }

    function initTablas() {
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        TABLAS.forEach(function (tabla) {
            if (!d.querySelector(tabla.selector)) return;
            w.Sintel.Core.DataTablesFactory.create(tabla.selector, tabla.url, COLUMNS, {
                pageLength: 20,
                order: [],
            });
            bindFiltroPago(tabla);
        });
    }

    function recargarTablas() {
        TABLAS.forEach(function (tabla) {
            if (d.querySelector(tabla.selector)) w.Sintel.Core.DataTablesFactory.reload(tabla.selector);
        });
    }

    // ── Event Delegation (Editar / Ver / Eliminar) ─────────────────────────────
    // Los botones son server-rendered por tables.py (render_acciones) y
    // conservan las mismas clases/data-id que antes, por eso esta delegacion
    // no cambia. Se ancla a #tab-facturas-content (contenedor persistente, no
    // reemplazado por los swaps hx-swap="innerHTML" de cada panel).
    function initListEvents() {
        const gridElement = d.getElementById('tab-facturas-content');
        if (!gridElement) {
            console.warn(`${MOD} #tab-facturas-content no encontrado para eventos`);
            return;
        }

        gridElement.addEventListener('click', async (e) => {
            // Botón Editar — delega al offcanvas completo (offcanvas_editar_factura.html, simple=false)
            const btnEdit = e.target.closest('.btn-edit-factura');
            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();

                const id = btnEdit.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón editar sin data-id`);
                    return;
                }

                if (w.AppFacturas && typeof w.AppFacturas.cargarOffcanvas === 'function') {
                    w.AppFacturas.cargarOffcanvas(id, false);
                } else {
                    console.error(`${MOD} AppFacturas.cargarOffcanvas no disponible`);
                }
                return;
            }

            // Botón Ver (abre Offcanvas de solo lectura)
            const btnView = e.target.closest('.btn-view-factura');
            if (btnView) {
                e.preventDefault();
                e.stopPropagation();

                const id = btnView.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón sin data-id`);
                    return;
                }

                const originalHTML = btnView.innerHTML;
                btnView.disabled = true;
                btnView.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    const offcanvasContainer = d.getElementById('offcanvas-container-facturas');
                    if (!offcanvasContainer) {
                        console.warn(`${MOD} Contenedor #offcanvas-container-facturas no encontrado`);
                        return;
                    }

                    await htmx.ajax('GET', `/api/v1/facturas/gestor-offcanvas/?uuid=${id}&simple=true&readonly=true`, {
                        target: '#offcanvas-container-facturas',
                        swap: 'innerHTML'
                    });

                    await new Promise(resolve => setTimeout(resolve, 100));

                    let offcanvasEl = d.getElementById('offcanvas-ver-factura');
                    if (!offcanvasEl) {
                        offcanvasEl = d.getElementById('offcanvas-factura');
                        if (offcanvasEl) {
                            offcanvasEl.id = 'offcanvas-ver-factura';
                            offcanvasEl.setAttribute('aria-labelledby', 'offcanvas-ver-factura-label');
                        }
                    }

                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        if (w.VerDetalleFactura && typeof w.VerDetalleFactura.ver === 'function') {
                            await w.VerDetalleFactura.ver(id);
                        } else if (typeof window.VerDetalleFactura !== 'undefined' && typeof window.VerDetalleFactura.ver === 'function') {
                            await window.VerDetalleFactura.ver(id);
                        } else if (typeof window.verDetalleFactura === 'function') {
                            await window.verDetalleFactura(id);
                        } else {
                            console.warn(`${MOD} Función verDetalleFactura no disponible.`);
                        }

                        if (w.UIManager?.handleOffcanvas) {
                            w.UIManager.handleOffcanvas(offcanvasEl, 'show');
                        } else {
                            // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (AGENTS.md §26 — nunca getOrCreateInstance)
                            w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
                        }
                    } else {
                        console.warn(`${MOD} No se pudo abrir el Offcanvas: elemento no encontrado o Bootstrap no disponible`);
                    }
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al cargar el detalle de la factura');
                    }
                } finally {
                    btnView.disabled = false;
                    btnView.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-factura');
            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();

                const id = btnDelete.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón eliminar sin data-id`);
                    return;
                }

                if (!(await w.UIManager?.confirm('¿Está seguro de eliminar esta factura? Esta acción no se puede deshacer.'))) {
                    return;
                }

                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // T-9: delega a la SSoT de endpoints (facturas.api.js).
                    const res = await w.facturasAPI.deleteFactura(id);

                    if (res.ok) {
                        const offcanvasVerFactura = d.getElementById('offcanvas-ver-factura');
                        const offcanvasFactura = d.getElementById('offcanvas-factura');

                        if (offcanvasVerFactura && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                            const instance = bootstrap.Offcanvas.getInstance(offcanvasVerFactura);
                            if (instance) instance.hide();
                        }
                        if (offcanvasFactura && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                            const instance = bootstrap.Offcanvas.getInstance(offcanvasFactura);
                            if (instance) instance.hide();
                        }

                        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                            w.SintelFeedback.success('Factura eliminada correctamente');
                        }

                        // Recarga ambos paneles HTMX (mismo evento que dispara facturas_editor.js
                        // al guardar — ver hx-trigger="... facturaGuardada from:document" en list_factura.html)
                        d.dispatchEvent(new Event('facturaGuardada'));

                        if (w.location && w.location.hash !== '#facturas') {
                            w.location.hash = '#facturas';
                        }
                    } else {
                        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                            w.UIManager.handleError(res, MOD);
                        } else {
                            alert('Error al eliminar la factura');
                        }
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar factura:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al eliminar la factura');
                    }
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
                return;
            }
        });

        console.log(`${MOD} Event delegation configurado`);
    }

    // ── Resumen de KPIs (Ventas Netas / Compras Netas) ─────────────────────────
    // Independiente de la tabla — sigue golpeando /api/v1/facturas/summary/.
    let _summaryDebounce = null;
    function loadSummary() {
        clearTimeout(_summaryDebounce);
        _summaryDebounce = setTimeout(_doLoadSummary, 150);
    }

    async function _doLoadSummary() {
        try {
            let summaryRes;
            if (w.facturasAPI && typeof w.facturasAPI.getSummary === 'function') {
                summaryRes = await w.facturasAPI.getSummary();
            } else if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http) {
                summaryRes = await w.Sintel.Core.Http.request('GET', '/api/v1/facturas/summary/');
            } else {
                console.warn(`${MOD} No hay API disponible para cargar summary`);
                return;
            }

            if (!summaryRes.ok) {
                console.error(`${MOD} Error al cargar summary:`, summaryRes);
                return;
            }

            const summary = summaryRes.data || {};
            const ventas = summary.ventas || {};
            const compras = summary.compras || {};

            function formatMoney(value) {
                if (!value || value === '0.00' || value === '0') return '$ 0,00';
                const num = parseFloat(value);
                if (isNaN(num)) return '$ 0,00';
                // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
                if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
                    return w.DOMUtils.formatCurrency(num, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
                }
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 2
                }).format(num);
            }

            const ventasTotalEl = d.getElementById('ventas-total-neto');
            const ventasSubtotalEl = d.getElementById('ventas-subtotal-neto');
            const ventasImpuestosEl = d.getElementById('ventas-impuestos-neto');
            if (ventasTotalEl) ventasTotalEl.textContent = formatMoney(ventas.total_neto || '0.00');
            if (ventasSubtotalEl) ventasSubtotalEl.textContent = formatMoney(ventas.subtotal_neto || '0.00');
            if (ventasImpuestosEl) ventasImpuestosEl.textContent = formatMoney(ventas.impuestos_neto || '0.00');

            const comprasTotalEl = d.getElementById('compras-total-neto');
            const comprasSubtotalEl = d.getElementById('compras-subtotal-neto');
            const comprasImpuestosEl = d.getElementById('compras-impuestos-neto');
            if (comprasTotalEl) comprasTotalEl.textContent = formatMoney(compras.total_neto || '0.00');
            if (comprasSubtotalEl) comprasSubtotalEl.textContent = formatMoney(compras.subtotal_neto || '0.00');
            if (comprasImpuestosEl) comprasImpuestosEl.textContent = formatMoney(compras.impuestos_neto || '0.00');
        } catch (error) {
            console.error(`${MOD} Error al cargar summary:`, error);
        }
    }

    // ── Recarga reactiva del resumen + tablas tras guardar factura ──────────
    function initEventListeners() {
        d.addEventListener('facturaGuardada', () => {
            loadSummary();
            recargarTablas();
            console.log(`${MOD} Summary y tablas refrescados tras guardar factura`);
        });
    }

    // ── Inicialización principal ────────────────────────────────────────────
    function init() {
        console.log(`${MOD} Inicializando módulo de listado...`);
        initTablas();
        initListEvents();
        initEventListeners();
        loadSummary();
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ── API Pública ─────────────────────────────────────────────────────────
    w.FacturasListModule = {
        init,
        refresh: () => {
            d.dispatchEvent(new Event('facturaGuardada'));
        },
        loadSummary
    };

    if (!w.FacturasModule) {
        w.FacturasModule = {
            refresh: () => d.dispatchEvent(new Event('facturaGuardada'))
        };
    }

})(window, document);
