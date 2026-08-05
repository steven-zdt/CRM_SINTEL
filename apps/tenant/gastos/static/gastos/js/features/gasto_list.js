/**
 * Feature: Listado de Gastos y Resoluciones v4.0.0
 * - Tablas server-rendered via django-tables2 + HTMX (#gastos-panel / #resoluciones-panel,
 *   cargadas por atributos hx-get/hx-trigger declarados en gastos_list.html).
 * - Este archivo solo maneja: acciones de fila (ver/editar/anular/eliminar/desactivar),
 *   apertura de offcanvas, y disparo de los eventos que hacen que HTMX vuelva a pedir
 *   la tabla al backend tras una mutacion.
 * - PLAN_UNICO_CORRECCIONES.md Fase 5-BIS: reemplazo de Tabulator, no reimplementar
 *   aqui logica de columnas/paginacion/orden — eso vive en tables.py (server-side).
 */
(function(w, d) {
    'use strict';

    // Namespace
    w.Sintel = w.Sintel || {};
    w.Sintel.Gastos = w.Sintel.Gastos || {};

    // ─── Modulo GastoList ─────────────────────────────────────────────────────

    const GastoList = {
        refresh: function() {
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
        reload: function() {
            d.body.dispatchEvent(new CustomEvent('resolucion-created'));
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
    // Los botones son server-rendered por tables.py (render_acciones) y conservan
    // las mismas clases/data-uuid que antes, por eso esta delegacion no cambia.

    function initListEvents() {
        // Gastos Panel Events (delegado sobre el contenedor HTMX, sobrevive a los swaps)
        const panelGastos = d.querySelector('#gastos-panel');
        if (panelGastos) {
            panelGastos.addEventListener('click', async (e) => {
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

        // Resoluciones Panel Events
        const panelResoluciones = d.querySelector('#resoluciones-panel');
        if (panelResoluciones) {
            panelResoluciones.addEventListener('click', async (e) => {
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
    // Este script se re-ejecuta completo cada vez que HTMX vuelve a insertar el
    // modulo "gastos" (nuevo <script> = nuevo closure = nuevos #gastos-panel/
    // #resoluciones-panel), asi que no hace falta un guard "ya inicializado":
    // no hay riesgo de doble-listener porque los contenedores tambien son nuevos.

    function setup() {
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

    // API Publica
    w.Sintel.Gastos.GastoList = GastoList;
    w.Sintel.Gastos.ResolucionList = ResolucionList;
    w.Sintel.Gastos.List = GastoList; // Legacy alias

})(window, document);
