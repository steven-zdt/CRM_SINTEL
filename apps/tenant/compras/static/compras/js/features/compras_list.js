/**
 * Feature: Listado de Ordenes de Compra v4.0.0
 * - Tabla server-rendered via django-tables2 + HTMX (#compras-panel, cargada por
 *   los atributos hx-get/hx-trigger declarados en compras_list.html).
 * - Este archivo solo maneja: acciones de fila (ver/editar/eliminar/cambiar
 *   estado), el formulario de "Nueva Plantilla", y el manejo de offcanvas.
 * - PLAN_UNICO_CORRECCIONES.md Fase 5-BIS: reemplazo de Tabulator — no
 *   reimplementar aqui columnas/paginacion/orden, eso vive en tables.py.
 */
(function(w, d) {
    'use strict';

    // Namespace
    w.Sintel = w.Sintel || {};
    w.Sintel.Compras = w.Sintel.Compras || {};

    // ─── Modulo ComprasList ───────────────────────────────────────────────────

    const ComprasList = {
        refresh: function() {
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
                        const offcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
                        offcanvas.show();

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

    // ─── Event Delegation (Acciones de la Grilla y Acciones de Estado en Detalle) ────
    // Los botones son server-rendered por tables.py (render_acciones) y
    // conservan las mismas clases/data-uuid que antes. Se ancla a
    // #compras-panel (contenedor persistente, no reemplazado por los swaps
    // hx-swap="innerHTML").

    function initListEvents() {
        const panelCompras = d.querySelector('#compras-panel');
        if (panelCompras) {
            panelCompras.addEventListener('click', async (e) => {
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
                }
            });
        }
    }

    // ─── Plantilla Form ───────────────────────────────────────────────────────

    function initPlantillaForm(offcanvasEl) {
        const API = w.Sintel?.Compras?.API;
        if (!API) {
            console.error('[ComprasList] API no disponible para plantilla form');
            return;
        }

        const form = offcanvasEl.querySelector('#plantilla-crear-form');
        const feedbackEl = offcanvasEl.querySelector('#form-plantilla-crear-feedback');
        const previewNum = offcanvasEl.querySelector('#plt-preview-num');
        const previewRango = offcanvasEl.querySelector('#plt-preview-rango');
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

            if (btnGuardar) { btnGuardar.disabled = true; btnGuardar.textContent = 'Creando...'; }

            try {
                const payload = { nombre, rango_desde: desde, rango_hasta: hasta, vigente: esVigente };
                if (prefijo) payload.prefijo = prefijo;

                await API.plantillas.create(payload);

                const bsInstance = w.bootstrap?.Offcanvas?.getInstance(offcanvasEl);
                if (bsInstance) bsInstance.hide();

                d.body.dispatchEvent(new CustomEvent('plantilla-created', { detail: payload }));
                w.UIManager?.showNotification?.('Plantilla creada correctamente', 'success');
            } catch (err) {
                const data = err.data || {};
                const msgs = Object.values(data).flat().join(' ') || `Error ${err.status || ''}`;
                showError(msgs);
                console.error('[ComprasList] Error creando plantilla:', err);
            } finally {
                if (btnGuardar) { btnGuardar.disabled = false; btnGuardar.textContent = 'Crear Plantilla'; }
            }
        });
    }

    // ─── Setup ─────────────────────────────────────────────────────────────

    function setup() {
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
                        const offcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
                        offcanvas.show();
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
                        const offcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
                        offcanvas.show();
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
