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

        // CO-1 (2026-09-12): activar/desactivar plantilla desde la fila --
        // el edit (hx-get declarativo, ver tables.py) no necesita JS.
        const panelPlantillas = d.querySelector('#plantillas-panel');
        if (panelPlantillas) {
            panelPlantillas.addEventListener('click', async (e) => {
                const btnToggle = e.target.closest('.btn-toggle-plantilla');
                if (!btnToggle) return;
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
                    return;
                }

                // ── Vincular Factura existente (FACTURAS-VENTAS-COMPRAS-01) ──
                // Busqueda + seleccion EXPLICITA (nunca auto-match/auto-assign).
                const widget = e.target.closest('#compra-factura-widget');
                if (!widget) return;

                if (e.target.closest('[data-compra-factura-action="mostrar-buscador"]') ||
                    e.target.closest('[data-compra-factura-action="cambiar"]')) {
                    const asociadaDiv = widget.querySelector('#compra-factura-asociada');
                    const buscadorDiv = widget.querySelector('#compra-factura-buscador');
                    const panel = widget.querySelector('#compra-factura-buscador-panel');
                    if (asociadaDiv) asociadaDiv.classList.add('d-none');
                    if (buscadorDiv) buscadorDiv.classList.remove('d-none');
                    if (panel) panel.classList.remove('d-none');
                    const input = widget.querySelector('#compra-factura-buscar-input');
                    if (input) input.focus();
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
                        data-factura-uuid-confirm="${facturaUuid}">Guardar asociacion</button>
                <button type="button" class="btn btn-secondary btn-sm" id="compra-factura-cancelar-confirm">Cancelar</button>
              </div>
            </div>
        `;
    }

    function guardarAsociacionCompra(widget, container) {
        const btn = widget.querySelector('#compra-factura-confirmar');
        if (!btn) return;
        const facturaUuid = btn.getAttribute('data-factura-uuid-confirm');
        const compraUuid = widget.getAttribute('data-compra-uuid');
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
