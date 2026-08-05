/**
 * Feature: Editor de Ordenes de Compra v3.10.5
 * - Manejo del ciclo de vida del Offcanvas
 * - Calculos en tiempo real de Subtotal, IVA y Neto
 * - Inyeccion dinamica de proveedores y proyectos con cache
 * - Envio de formulario mediante API REST (Double Semantic Verification)
 */
(function(w, d) {
    'use strict';

    const MOD = '[compras.editor]';

    w.Sintel = w.Sintel || {};
    w.Sintel.Compras = w.Sintel.Compras || {};

    // Helper de Formateo de Moneda
    function formatCurrency(val) {
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP',
            minimumFractionDigits: 0, maximumFractionDigits: 0
        }).format(val);
    }

    // ─── Calculos de Totales ──────────────────────────────────────────────────

    function actualizarFilaTotal(row) {
        const cantidadInput = row.querySelector('.item-cantidad');
        const valorInput = row.querySelector('.item-valor-unitario');
        const ivaSelect = row.querySelector('.item-iva');
        const totalInput = row.querySelector('.item-total');

        if (!cantidadInput || !valorInput || !ivaSelect || !totalInput) return;

        const cantidad = parseFloat(cantidadInput.value) || 0;
        const valorUnitario = parseFloat(valorInput.value) || 0;
        const porcentajeIva = parseFloat(ivaSelect.value) || 0;

        const subtotal = cantidad * valorUnitario;
        const valorIva = subtotal * (porcentajeIva / 100);
        const total = subtotal + valorIva;

        totalInput.value = total.toFixed(2);
    }

    function actualizarTotales(form) {
        let subtotalAcumulado = 0;
        let impuestosAcumulado = 0;
        let totalAcumulado = 0;

        const rows = form.querySelectorAll('.item-row');
        rows.forEach(row => {
            const cantidadInput = row.querySelector('.item-cantidad');
            const valorInput = row.querySelector('.item-valor-unitario');
            const ivaSelect = row.querySelector('.item-iva');

            if (cantidadInput && valorInput && ivaSelect) {
                const cantidad = parseFloat(cantidadInput.value) || 0;
                const valorUnitario = parseFloat(valorInput.value) || 0;
                const porcentajeIva = parseFloat(ivaSelect.value) || 0;

                const subtotal = cantidad * valorUnitario;
                const valorIva = subtotal * (porcentajeIva / 100);
                const total = subtotal + valorIva;

                subtotalAcumulado += subtotal;
                impuestosAcumulado += valorIva;
                totalAcumulado += total;
            }
        });

        const subtotalEl = form.querySelector('#resumen-subtotal');
        const impuestosEl = form.querySelector('#resumen-impuestos');
        const totalEl = form.querySelector('#resumen-total');

        if (subtotalEl) subtotalEl.textContent = formatCurrency(subtotalAcumulado);
        if (impuestosEl) impuestosEl.textContent = formatCurrency(impuestosAcumulado);
        if (totalEl) totalEl.textContent = formatCurrency(totalAcumulado);
    }

    // ─── Dynamic Row Management ───────────────────────────────────────────────

    function bindRowEvents(row, form) {
        const inputs = row.querySelectorAll('.item-cantidad, .item-valor-unitario, .item-iva');
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                actualizarFilaTotal(row);
                actualizarTotales(form);
            });
        });

        const btnEliminar = row.querySelector('.btn-eliminar-item');
        if (btnEliminar) {
            btnEliminar.addEventListener('click', (e) => {
                e.preventDefault();
                row.remove();
                actualizarTotales(form);
            });
        }
    }

    function agregarItemRow(tbody, form) {
        const row = d.createElement('tr');
        row.className = 'item-row';
        row.innerHTML = `
            <td>
                <input type="text" class="form-control form-control-sm item-descripcion" placeholder="Nombre o descripción del item..." required>
                <input type="hidden" class="item-inventario-uuid" value="">
            </td>
            <td>
                <input type="number" class="form-control form-control-sm text-end item-cantidad" value="1.00" step="any" min="0.01" required>
            </td>
            <td>
                <input type="number" class="form-control form-control-sm text-end item-valor-unitario" value="0.00" step="any" min="0.00" required>
            </td>
            <td>
                <select class="form-select form-select-sm text-end item-iva">
                    <option value="0">0%</option>
                    <option value="5">5%</option>
                    <option value="19" selected>19%</option>
                </select>
            </td>
            <td>
                <input type="text" class="form-control form-control-sm text-end bg-light item-total" value="0.00" readonly disabled>
            </td>
            <td class="text-center">
                <button type="button" class="btn btn-link link-danger p-0 btn-eliminar-item" title="Eliminar item">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;

        tbody.appendChild(row);
        bindRowEvents(row, form);
        actualizarFilaTotal(row);
        actualizarTotales(form);
    }

    // ─── Form Submission y Guardado ───────────────────────────────────────────

    function recolectarDatos(form) {
        const mode = form.getAttribute('data-mode');
        const uuid = form.getAttribute('data-uuid');

        const plantillaVal = form.querySelector('#plantilla')?.value || null;
        const fechaVal = form.querySelector('#fecha')?.value || null;
        const fechaEntregaVal = form.querySelector('#fecha_entrega')?.value || null;
        const proveedorVal = form.querySelector('#proveedor')?.value || null;
        const proyectoVal = form.querySelector('#proyecto')?.value || null;
        const observacionesVal = form.querySelector('#observaciones')?.value || '';

        const items = [];
        const rows = form.querySelectorAll('.item-row');
        rows.forEach(row => {
            const desc = row.querySelector('.item-descripcion')?.value?.trim();
            const cant = parseFloat(row.querySelector('.item-cantidad')?.value) || 0;
            const valUnit = parseFloat(row.querySelector('.item-valor-unitario')?.value) || 0;
            const pctIva = parseInt(row.querySelector('.item-iva')?.value) || 0;
            const invUuid = row.querySelector('.item-inventario-uuid')?.value || null;

            if (desc) {
                items.push({
                    descripcion: desc,
                    item_inventario_uuid: invUuid,
                    cantidad: cant,
                    valor_unitario: valUnit,
                    porcentaje_iva: pctIva
                });
            }
        });

        const payload = {
            fecha: fechaVal,
            fecha_entrega: fechaEntregaVal || null,
            proveedor: proveedorVal,
            proyecto: proyectoVal || null,
            observaciones: observacionesVal,
            items: items
        };

        if (mode === 'create') {
            payload.plantilla = plantillaVal;
        }

        return { mode, uuid, payload };
    }

    async function handleFormSubmit(e, form) {
        e.preventDefault();
        e.stopPropagation();

        const btnSave = form.querySelector('#btn-guardar-compra') || d.querySelector(`[form="${form.id}"]`);
        if (btnSave) btnSave.disabled = true;

        const feedbackId = form.id === 'compra-crear-form' ? '#form-compra-crear-feedback' : '#form-compra-editar-feedback';
        const feedbackEl = form.querySelector(feedbackId) || d.querySelector(feedbackId);
        if (feedbackEl) {
            feedbackEl.classList.add('d-none');
            feedbackEl.textContent = '';
        }

        const { mode, uuid, payload } = recolectarDatos(form);

        // Validacion cliente: Al menos un item
        if (payload.items.length === 0) {
            w.UIManager?.notifyError("Debe agregar al menos un item con descripción");
            if (btnSave) btnSave.disabled = false;
            return;
        }

        if (mode === 'create') {
            const plantillaSel = form.querySelector('#plantilla');
            if (plantillaSel && plantillaSel.value) {
                const opt = plantillaSel.options[plantillaSel.selectedIndex];
                const actual = parseInt(opt.getAttribute('data-actual')) || 1;
                const hasta = parseInt(opt.getAttribute('data-hasta')) || 0;
                if (hasta > 0 && actual > hasta) {
                    w.UIManager?.notifyError("La plantilla seleccionada está agotada.");
                    if (btnSave) btnSave.disabled = false;
                    return;
                }
            }
        }

        try {
            let result;
            if (mode === 'create') {
                result = await w.Sintel.Compras.API.compras.create(payload);
                w.UIManager?.notifySuccess("Orden de compra creada correctamente");
            } else {
                result = await w.Sintel.Compras.API.compras.update(uuid, payload);
                w.UIManager?.notifySuccess("Orden de compra actualizada correctamente");
            }

            // Notificar a la lista para recargar grilla
            const eventName = mode === 'create' ? 'compra-created' : 'compra-updated';
            d.body.dispatchEvent(new CustomEvent(eventName, { detail: result }));

            // Cerrar Offcanvas
            const offcanvasEl = form.closest('.offcanvas');
            if (offcanvasEl && w.bootstrap?.Offcanvas) {
                const instance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (instance) instance.hide();
            }
        } catch (error) {
            console.error(MOD, 'Error en submit de OrdenCompra:', error);
            
            // Mostrar error en feedback modal
            if (feedbackEl) {
                feedbackEl.classList.remove('d-none');
                if (error.data) {
                    let errMsg = '';
                    if (typeof error.data === 'object') {
                        Object.keys(error.data).forEach(k => {
                            const val = error.data[k];
                            const label = k.charAt(0).toUpperCase() + k.slice(1);
                            errMsg += `${label}: ${Array.isArray(val) ? val.join(', ') : JSON.stringify(val)}\n`;
                        });
                    } else {
                        errMsg = error.message || "Error al procesar la solicitud";
                    }
                    feedbackEl.innerText = errMsg;
                } else {
                    feedbackEl.textContent = error.message || "Error de red o de servidor";
                }
            }

            w.UIManager?.handleError(error);
            if (btnSave) btnSave.disabled = false;
        }
    }

    // ─── Información de Plantilla de Numeración ──────────────────────────────

    function actualizarInfoPlantilla() {
        const sel = d.getElementById('plantilla');
        const infoEl = d.getElementById('plantilla-info');
        if (!sel || !infoEl) return;

        if (!sel.value) {
            infoEl.textContent = '';
            infoEl.className = 'form-text mt-1 text-muted';
            return;
        }

        const opt = sel.options[sel.selectedIndex];
        if (!opt) return;

        const prefijo = opt.getAttribute('data-prefijo') || '';
        const actual = parseInt(opt.getAttribute('data-actual')) || 1;
        const hasta = parseInt(opt.getAttribute('data-hasta')) || 0;

        const proxNum = prefijo ? `${prefijo}-${actual}` : `${actual}`;
        let msg = `Número a asignar: ${proxNum}`;
        let textClass = 'text-muted';

        if (hasta > 0) {
            const disponibles = hasta - actual + 1;
            if (disponibles <= 0) {
                msg = `¡Plantilla Agotada! Límite: ${hasta}.`;
                textClass = 'text-danger fw-bold';
            } else if (disponibles <= 5) {
                msg = `Número a asignar: ${proxNum} (Próxima a agotarse, quedan ${disponibles})`;
                textClass = 'text-warning fw-semibold';
            } else {
                msg = `Número a asignar: ${proxNum} (Rango hasta ${hasta})`;
            }
        }

        infoEl.textContent = msg;
        infoEl.className = `form-text mt-1 ${textClass}`;
    }

    // ─── Inicializacion del Editor ───────────────────────────────────────────

    async function initializeEditor(form) {
        if (form.dataset.editorInitialized) return;
        form.dataset.editorInitialized = 'true';

        console.log(MOD, 'Inicializando formulario:', form.id);

        const mode = form.getAttribute('data-mode');
        const tbody = form.querySelector('#items-tbody');

        // Cargar combos de proveedores y proyectos de forma asincrona
        const provSelect = form.querySelector('#proveedor');
        const currentProv = provSelect ? provSelect.value : null;

        const projSelect = form.querySelector('#proyecto');
        const currentProj = projSelect ? projSelect.value : null;

        // Cargar catalogos dinamicamente
        w.Sintel.Compras.Utils.loadProveedoresSelect('#proveedor', currentProv, 'Seleccione Proveedor *');
        w.Sintel.Compras.Utils.loadProyectosSelect('#proyecto', currentProj, 'Seleccione Proyecto (Opcional)');

        // Bindear eventos a las filas existentes (en edicion)
        if (tbody) {
            const rows = tbody.querySelectorAll('.item-row');
            rows.forEach(row => {
                bindRowEvents(row, form);
                actualizarFilaTotal(row);
            });
            actualizarTotales(form);

            // Agregar primer fila por defecto si esta en creacion y vacio
            if (mode === 'create' && rows.length === 0) {
                agregarItemRow(tbody, form);
            }
        }

        // Configurar dropdown de plantilla de numeracion
        const plantillaSel = form.querySelector('#plantilla');
        if (plantillaSel) {
            plantillaSel.addEventListener('change', actualizarInfoPlantilla);
            actualizarInfoPlantilla();
        }

        // Agregar Item
        const btnAgregar = form.querySelector('#btn-agregar-item');
        if (btnAgregar && tbody) {
            btnAgregar.addEventListener('click', (e) => {
                e.preventDefault();
                agregarItemRow(tbody, form);
            });
        }

        // Submit del formulario
        form.addEventListener('submit', (e) => handleFormSubmit(e, form));
    }

    // Registrar Event Listeners globales
    d.body.addEventListener('compra-editor-init', (e) => {
        const form = e.detail?.form;
        if (form) {
            initializeEditor(form);
        }
    });

    // Auto-detectar formulario si ya esta cargado al iniciar el script
    function autoInit() {
        const form = d.querySelector('#compra-crear-form') || d.querySelector('#compra-editar-form');
        if (form) {
            initializeEditor(form);
        }
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', autoInit);
    } else {
        autoInit();
    }

    // Exportar namespace
    w.Sintel.Compras.Editor = {
        initializeEditor: initializeEditor,
        actualizarTotales: actualizarTotales
    };

})(window, document);
