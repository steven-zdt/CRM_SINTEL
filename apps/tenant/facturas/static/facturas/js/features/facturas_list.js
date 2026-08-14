/**
 * Feature: Listado de Facturas v4.0.0
 * - Tablas server-rendered via django-tables2 + HTMX (#panel-ventas / #panel-compras,
 *   cargadas por los atributos hx-get/hx-trigger declarados en list_factura.html).
 * - Este archivo solo maneja: acciones de fila (editar/ver/eliminar), el resumen
 *   de KPIs (Ventas Netas / Compras Netas, independiente de la tabla), y el
 *   despacho del evento 'facturaGuardada' que hace que HTMX recargue ambos
 *   paneles tras crear/editar/eliminar una factura.
 * - PLAN_UNICO_CORRECCIONES.md Fase 5-BIS: reemplazo de Tabulator. Los filtros
 *   rápidos de "Pago" y la búsqueda ahora son server-side (ver tables.py/views.py
 *   en apps/tenant/facturas/), no reimplementar aquí lógica de columnas/filtrado.
 * - Simplificación consciente respecto a la versión Tabulator: se retiró el
 *   click-en-fila para abrir el detalle (el botón "Ver" ya cubre ese caso) —
 *   ver REPORTE_FASE_5_PILOTO_TABLAS.md para el detalle de esta decisión.
 */
(function(w, d) {
    'use strict';

    const MOD = '[facturas.list]';

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
                    const res = await w.Sintel.Core.Http.request('DELETE', `/api/v1/facturas/${id}/`);

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
                return new Intl.NumberFormat('es-CO', {
                    style: 'currency',
                    currency: 'COP',
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

    // ── Recarga reactiva del resumen tras guardar factura ──────────────────────
    // (la recarga de los paneles de tabla ya la maneja HTMX via hx-trigger)
    function initEventListeners() {
        d.addEventListener('facturaGuardada', () => {
            loadSummary();
            console.log(`${MOD} Summary refrescado tras guardar factura`);
        });
    }

    // ── Inicialización principal ────────────────────────────────────────────
    function init() {
        console.log(`${MOD} Inicializando módulo de listado...`);
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
