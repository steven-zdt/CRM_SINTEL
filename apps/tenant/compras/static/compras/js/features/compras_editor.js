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
    // BUG (2026-09-12, hallazgo T-5): sin guard, un valor null/undefined/NaN
    // renderizaba el string literal "NaN" -- no se manifestaba hoy porque
    // los call-sites actuales ya filtran con parseFloat(...)||0, pero era
    // una trampa abierta para el proximo consumidor.
    function formatCurrency(val) {
        const value = (val === null || val === undefined || val === '' || isNaN(val)) ? 0 : val;
        // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
        if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
            return w.DOMUtils.formatCurrency(value, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
        }
        return new Intl.NumberFormat('en-US', {
            style: 'currency', currency: 'USD',
            minimumFractionDigits: 0, maximumFractionDigits: 0
        }).format(value);
    }

    // ─── Calculos de Totales ──────────────────────────────────────────────────
    // Fase 9 (PLAN_OPTIMIZACION_COMPRAS...): formula unica de calculo visual,
    // reutilizada por actualizarFilaTotal() y actualizarTotales() -- antes
    // duplicada identica en ambas funciones. Solo preview: el backend sigue
    // siendo la SSoT del calculo final (crud_service.py::_calcular_item).

    function calcularItem(cantidad, valorUnitario, porcentajeIva) {
        const subtotal = cantidad * valorUnitario;
        const valorIva = subtotal * (porcentajeIva / 100);
        const total = subtotal + valorIva;
        return { subtotal, valorIva, total };
    }

    function leerValoresFila(row) {
        const cantidadInput = row.querySelector('.item-cantidad');
        const valorInput = row.querySelector('.item-valor-unitario');
        const ivaSelect = row.querySelector('.item-iva');
        if (!cantidadInput || !valorInput || !ivaSelect) return null;
        return {
            cantidad: parseFloat(cantidadInput.value) || 0,
            valorUnitario: parseFloat(valorInput.value) || 0,
            porcentajeIva: parseFloat(ivaSelect.value) || 0,
        };
    }

    function actualizarFilaTotal(row) {
        const totalInput = row.querySelector('.item-total');
        const valores = leerValoresFila(row);
        if (!valores || !totalInput) return;

        const { total } = calcularItem(valores.cantidad, valores.valorUnitario, valores.porcentajeIva);
        totalInput.value = total.toFixed(2);
    }

    function actualizarTotales(form) {
        let subtotalAcumulado = 0;
        let impuestosAcumulado = 0;
        let totalAcumulado = 0;

        const rows = form.querySelectorAll('.item-row');
        rows.forEach(row => {
            const valores = leerValoresFila(row);
            if (!valores) return;

            const { subtotal, valorIva, total } = calcularItem(
                valores.cantidad, valores.valorUnitario, valores.porcentajeIva
            );
            subtotalAcumulado += subtotal;
            impuestosAcumulado += valorIva;
            totalAcumulado += total;
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

    // `datos` es opcional -- sin el, se comporta exactamente igual que antes
    // (fila en blanco para carga MANUAL via #btn-agregar-item). Con el, se
    // usa para precargar una fila desde una Requisicion vinculada (ver
    // agregarItemsDesdeRequisicion mas abajo) -- nunca reemplaza el flujo
    // manual, solo lo complementa.
    function agregarItemRow(tbody, form, datos) {
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

        if (datos) {
            // Asignado via propiedad `.value` (nunca interpolado en el HTML
            // de arriba) para no abrir una via de XSS con la descripcion
            // del item de la requisicion.
            const descInput = row.querySelector('.item-descripcion');
            const invInput = row.querySelector('.item-inventario-uuid');
            const cantInput = row.querySelector('.item-cantidad');
            const valorInput = row.querySelector('.item-valor-unitario');
            const ivaSelect = row.querySelector('.item-iva');

            if (descInput && datos.descripcion) descInput.value = datos.descripcion;
            if (invInput && datos.item_inventario_uuid) invInput.value = datos.item_inventario_uuid;
            if (cantInput && datos.cantidad !== undefined && datos.cantidad !== null && datos.cantidad !== '') {
                cantInput.value = datos.cantidad;
            }
            // Requisito explicito: el Monto/Valor Unitario Estimado de la
            // requisicion sincroniza el campo "Val. Unitario" del item.
            if (valorInput && datos.valor_unitario !== undefined && datos.valor_unitario !== null) {
                valorInput.value = datos.valor_unitario;
            }
            // El % de IVA de la requisicion viene de un input libre
            // (requisiciones_editor.js::req-item-iva, sin presets) -- no
            // asumir que siempre cae en 0/5/19. Bug real detectado: una
            // tasa fuera de esos 3 presets no matcheaba ninguna <option> y
            // el select se quedaba en su 19% por defecto, sincronizando
            // "Val. Unitario" pero perdiendo el IVA real de la requisicion.
            // Fix: si no existe la opcion, se agrega dinamicamente con el
            // valor real en vez de descartarlo.
            if (ivaSelect && datos.porcentaje_iva !== undefined && datos.porcentaje_iva !== null) {
                const ivaNum = parseFloat(datos.porcentaje_iva) || 0;
                let opt = Array.from(ivaSelect.options).find((o) => parseFloat(o.value) === ivaNum);
                if (!opt) {
                    opt = d.createElement('option');
                    opt.value = String(ivaNum);
                    opt.textContent = `${ivaNum}%`;
                    ivaSelect.appendChild(opt);
                }
                ivaSelect.value = opt.value;
            }
            if (datos.requisicion_uuid) row.dataset.requisicionUuid = datos.requisicion_uuid;
            if (datos.requisicion_item_uuid) row.dataset.requisicionItemUuid = datos.requisicion_item_uuid;
        }

        tbody.appendChild(row);
        bindRowEvents(row, form);
        actualizarFilaTotal(row);
        actualizarTotales(form);
    }

    // ─── Sincronizacion automatica de Items desde una Requisicion ─────────────
    // Al vincular una Requisicion (boton "Vincular requisición",
    // compras_list.js::guardarVinculoRequisicion), se agrega una fila de
    // Detalle de Items por cada item de la requisicion, con Val. Unitario
    // <- valor_unitario_estimado. Es una funcion ADICIONAL: el boton
    // "Agregar Item" manual sigue disponible y sin cambios de comportamiento.

    function agregarItemsDesdeRequisicion(form, requisicionUuid, items, opts) {
        const tbody = form.querySelector('#items-tbody');
        if (!tbody || !Array.isArray(items) || !items.length) return;

        // opts.forzarResync=true (panel manual "Sincronizar Requisición"):
        // reemplaza las filas ya sincronizadas desde esta requisicion con
        // datos frescos. Sin el (sincronizacion automatica al vincular),
        // evita duplicar si ya estaba sincronizada.
        const forzarResync = !!(opts && opts.forzarResync);
        const existentes = tbody.querySelectorAll(`.item-row[data-requisicion-uuid="${requisicionUuid}"]`);
        if (existentes.length) {
            if (!forzarResync) return;
            existentes.forEach((row) => row.remove());
        }

        // Limpia la fila inicial en blanco (agregada por defecto al abrir
        // el formulario) SOLO si sigue vacia -- nunca toca una fila que el
        // usuario ya haya empezado a llenar a mano.
        const filas = tbody.querySelectorAll('.item-row');
        if (filas.length === 1) {
            const unica = filas[0];
            const desc = unica.querySelector('.item-descripcion')?.value?.trim();
            const valor = parseFloat(unica.querySelector('.item-valor-unitario')?.value) || 0;
            if (!desc && !valor) unica.remove();
        }

        items.forEach((it) => {
            agregarItemRow(tbody, form, {
                descripcion: it.descripcion,
                item_inventario_uuid: it.item_inventario_uuid,
                cantidad: it.cantidad_pendiente || it.cantidad_solicitada,
                valor_unitario: it.valor_unitario_estimado,
                porcentaje_iva: it.porcentaje_iva,
                requisicion_uuid: requisicionUuid,
                requisicion_item_uuid: it.uuid,
            });
        });
    }

    // Contraparte de agregarItemsDesdeRequisicion: al quitar una requisicion
    // PENDIENTE (aun sin guardar la Orden), remueve solo las filas que se
    // sincronizaron automaticamente desde ella -- las filas cargadas a mano
    // nunca se tocan.
    function quitarItemsDeRequisicion(form, requisicionUuid) {
        const tbody = form.querySelector('#items-tbody');
        if (!tbody) return;
        tbody.querySelectorAll(`.item-row[data-requisicion-uuid="${requisicionUuid}"]`).forEach((row) => row.remove());
        actualizarTotales(form);
    }

    // ─── Panel "Sincronizar Requisición" (manual, junto a Agregar Item) ───────
    // Deja buscar/ver las requisiciones ya vinculadas a esta orden (widget
    // #compra-requisicion-widget en "Asociaciones") y disparar/re-disparar
    // la sincronizacion de sus items hacia Detalle de Items bajo demanda.

    function _escapeHtmlCompra(str) {
        const span = d.createElement('span');
        span.textContent = str === null || str === undefined ? '' : String(str);
        return span.innerHTML;
    }

    function _requisicionesVinculadasForm(form) {
        const widget = form.querySelector('#compra-requisicion-widget');
        return (widget && widget._requisicionesPendientes) || [];
    }

    function renderPanelSincronizarRequisicion(form, q) {
        const lista = form.querySelector('#sincronizar-requisicion-lista');
        if (!lista) return;

        const todas = _requisicionesVinculadasForm(form);
        if (!todas.length) {
            lista.innerHTML = '<div class="text-muted p-2">Aún no has vinculado ninguna requisición a esta orden (usa "Vincular requisición" en Asociaciones).</div>';
            return;
        }

        const query = (q || '').trim().toLowerCase();
        const items = query ? todas.filter((r) => (r.numero || '').toLowerCase().includes(query)) : todas;

        if (!items.length) {
            lista.innerHTML = '<div class="text-muted p-2">Sin resultados.</div>';
            return;
        }

        const tbody = form.querySelector('#items-tbody');
        lista.innerHTML = items.map((r) => {
            const sincronizada = !!(tbody && tbody.querySelector(`.item-row[data-requisicion-uuid="${r.uuid}"]`));
            return `
                <div class="d-flex align-items-center justify-content-between border-bottom py-2 px-1">
                  <div>
                    <div class="fw-semibold">${_escapeHtmlCompra(r.numero)}</div>
                    <div class="text-muted" style="font-size:0.78rem;">Monto asignado: ${formatCurrency(parseFloat(r.saldo) || 0)}${sincronizada ? ' &middot; <span class="text-success">Sincronizada</span>' : ''}</div>
                  </div>
                  <button type="button" class="btn btn-sm ${sincronizada ? 'btn-outline-secondary' : 'btn-primary'} flex-shrink-0"
                          data-sincronizar-requisicion-uuid="${r.uuid}">
                    ${sincronizada ? 'Re-sincronizar' : 'Sincronizar'}
                  </button>
                </div>
            `;
        }).join('');
    }

    async function ejecutarSincronizacionRequisicion(form, requisicionUuid) {
        const detalle = await w.Sintel.Compras.API.requisiciones.get(requisicionUuid);
        const items = (detalle && detalle.items) || [];
        if (!items.length) {
            w.UIManager?.notifyError('Esta requisición no tiene items para sincronizar.');
            return;
        }
        agregarItemsDesdeRequisicion(form, requisicionUuid, items, { forzarResync: true });
        w.UIManager?.notifySuccess('Detalle de Items sincronizado desde la requisición.');
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
        // Widget "Vincular requisición" (compras_list.js) -- en modo
        // creacion acumula las requisiciones elegidas en
        // widget._requisicionesPendientes (nunca llama al backend hasta
        // que exista la Orden).
        const reqWidgetForm = form.querySelector('#compra-requisicion-widget');
        const requisicionesSeleccionadas = (reqWidgetForm && reqWidgetForm._requisicionesPendientes)
            ? reqWidgetForm._requisicionesPendientes.map((r) => r.uuid)
            : [];

        const items = [];
        const rows = form.querySelectorAll('.item-row');
        rows.forEach(row => {
            const desc = row.querySelector('.item-descripcion')?.value?.trim();
            const cant = parseFloat(row.querySelector('.item-cantidad')?.value) || 0;
            const valUnit = parseFloat(row.querySelector('.item-valor-unitario')?.value) || 0;
            // parseFloat (no parseInt): una tasa sincronizada desde una
            // requisicion puede traer decimales (ej. 4.5%) -- truncarla
            // perderia precision en el payload real enviado al backend.
            const pctIva = parseFloat(row.querySelector('.item-iva')?.value) || 0;
            const invUuid = row.querySelector('.item-inventario-uuid')?.value || null;
            // Fase 6 (PLAN_OPTIMIZACION_COMPRAS...): filas ya existentes
            // (render server-side en modo edicion, ver offcanvas_editar_
            // compras.html) traen data-uuid -- se reenvia para que el
            // backend sincronice por diferencia en vez de reemplazar toda
            // la coleccion. Filas nuevas (agregarItemRow) no lo tienen.
            const itemUuid = row.dataset.uuid || null;

            if (desc) {
                const item = {
                    descripcion: desc,
                    item_inventario_uuid: invUuid,
                    cantidad: cant,
                    valor_unitario: valUnit,
                    porcentaje_iva: pctIva
                };
                if (itemUuid) item.uuid = itemUuid;
                items.push(item);
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
            // N:N -- el backend espera una lista (ver
            // OrdenCompraCreateUpdateSerializer.requisiciones). Fase 10 del
            // plan: seleccion multiple real con saldos en vivo (checklist,
            // no un <select> de una sola opcion).
            payload.requisiciones = requisicionesSeleccionadas;
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

        // Fase 4 (PLAN_OPTIMIZACION_COMPRAS...): #proveedor paso de <select
        // required> a input hidden (buscador async) -- la validacion nativa
        // del navegador no se dispara sobre un hidden, se re-valida aqui.
        if (!payload.proveedor) {
            w.UIManager?.notifyError("Debe seleccionar un proveedor.");
            if (btnSave) btnSave.disabled = false;
            return;
        }

        // Toda Orden de Compra debe tener >= 1 Requisicion, sin excepcion
        // posible (PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md #3) -- el
        // backend re-valida esto de todos modos (nunca confiar solo en JS),
        // pero se valida aqui tambien para dar feedback inmediato sin
        // round-trip.
        if (mode === 'create' && payload.requisiciones.length === 0) {
            w.UIManager?.notifyError("Debe seleccionar una Requisición de origen.");
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

                // PLAN_VINCULAR_FACTURA_COMPRA_COMPRAS Fase 28: si el usuario
                // selecciono una Factura existente en el widget ANTES de que
                // la Orden existiera, la vinculacion real se hace ahora que
                // ya tenemos result.uuid (ver compras_list.js ->
                // guardarAsociacionCompra(), modo creacion). Best effort: si
                // falla, la Orden YA se creo -- no se revierte ese exito.
                const widgetFactura = form.querySelector('#compra-factura-widget');
                const facturaPendienteUuid = widgetFactura && widgetFactura.dataset.facturaPendienteUuid;
                if (facturaPendienteUuid && result && result.uuid) {
                    try {
                        await w.Sintel.Compras.API.vincularFactura(result.uuid, facturaPendienteUuid);
                    } catch (err) {
                        console.warn(MOD, 'Orden creada pero fallo la vinculacion de factura pendiente:', err);
                        w.UIManager?.notifyError('Orden creada, pero no se pudo vincular la factura seleccionada.');
                    }
                }
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
        // Fase 10 (PLAN_OPTIMIZACION_COMPRAS...): "estimado", no "a asignar"
        // -- este numero es solo un preview client-side desde
        // consecutivo_actual; la reserva real y atomica ocurre recien en
        // OrdenCompraBusinessService._dsv_y_asignar_plantilla() al guardar.
        let msg = `Próximo número estimado: ${proxNum}`;
        let textClass = 'text-muted';

        if (hasta > 0) {
            const disponibles = hasta - actual + 1;
            if (disponibles <= 0) {
                msg = `¡Plantilla Agotada! Límite: ${hasta}.`;
                textClass = 'text-danger fw-bold';
            } else if (disponibles <= 5) {
                msg = `Próximo número estimado: ${proxNum} (Próxima a agotarse, quedan ${disponibles})`;
                textClass = 'text-warning fw-semibold';
            } else {
                msg = `Próximo número estimado: ${proxNum} (Rango hasta ${hasta})`;
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

        // Fase 4 (PLAN_OPTIMIZACION_COMPRAS...): busqueda bajo demanda en
        // vez de descargar el catalogo completo de proveedores/proyectos al
        // abrir el formulario. El valor real que viaja en el payload sigue
        // siendo el input hidden #proveedor/#proyecto (recolectarDatos()
        // no cambia).
        w.Sintel.Compras.Utils.initBuscadorAsync(form, {
            inputSelector: '#proveedor-buscar',
            hiddenSelector: '#proveedor',
            resultsSelector: '#proveedor-resultados',
            fetchFn: (q) => w.Sintel.Compras.Utils.fetchProveedores(q),
            getValue: (p) => p.uuid || p.id,
            getLabel: (p) => `${p.razon_social || p.nombre || ''} (${p.numero_documento || p.nit || ''})`,
        });
        w.Sintel.Compras.Utils.initBuscadorAsync(form, {
            inputSelector: '#proyecto-buscar',
            hiddenSelector: '#proyecto',
            resultsSelector: '#proyecto-resultados',
            clearSelector: '#btn-limpiar-proyecto',
            minChars: 2,
            fetchFn: (q) => w.Sintel.Compras.Utils.fetchProyectos(q),
            getValue: (p) => p.uuid || p.id,
            getLabel: (p) => p.nombre || p.codigo || '',
        });
        // Requisiciones: widget "Vincular requisición" (buscar + agregar),
        // carga sus propios datos on-demand al abrir el buscador -- ver
        // compras_list.js (mismo widget que la Orden ya existente).

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

        // Sincronizar Requisición (panel manual, junto a Agregar Item):
        // busca/ve las requisiciones vinculadas a esta orden y dispara la
        // sincronizacion de sus items hacia Detalle de Items bajo demanda.
        const btnSincronizarReq = form.querySelector('#btn-sincronizar-requisicion');
        const panelSincronizarReq = form.querySelector('#sincronizar-requisicion-panel');
        if (btnSincronizarReq && panelSincronizarReq) {
            btnSincronizarReq.addEventListener('click', (e) => {
                e.preventDefault();
                const abierto = !panelSincronizarReq.classList.contains('d-none');
                if (abierto) {
                    panelSincronizarReq.classList.add('d-none');
                } else {
                    panelSincronizarReq.classList.remove('d-none');
                    renderPanelSincronizarRequisicion(form, '');
                }
            });

            const btnCerrarPanel = panelSincronizarReq.querySelector('#btn-cerrar-sincronizar-requisicion');
            if (btnCerrarPanel) {
                btnCerrarPanel.addEventListener('click', (e) => {
                    e.preventDefault();
                    panelSincronizarReq.classList.add('d-none');
                });
            }

            const inputBuscarReq = panelSincronizarReq.querySelector('#sincronizar-requisicion-buscar-input');
            if (inputBuscarReq) {
                inputBuscarReq.addEventListener('input', () => {
                    renderPanelSincronizarRequisicion(form, inputBuscarReq.value);
                });
            }

            panelSincronizarReq.addEventListener('click', (e) => {
                const btnSync = e.target.closest('[data-sincronizar-requisicion-uuid]');
                if (!btnSync) return;
                e.preventDefault();
                const requisicionUuid = btnSync.getAttribute('data-sincronizar-requisicion-uuid');
                btnSync.disabled = true;
                ejecutarSincronizacionRequisicion(form, requisicionUuid)
                    .then(() => renderPanelSincronizarRequisicion(form, inputBuscarReq?.value || ''))
                    .catch((err) => {
                        console.warn(MOD, 'Error al sincronizar items desde requisicion:', err);
                        w.UIManager?.notifyError('No se pudo sincronizar el detalle de items de la requisición.');
                    })
                    .finally(() => { btnSync.disabled = false; });
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
        actualizarTotales: actualizarTotales,
        agregarItemsDesdeRequisicion: agregarItemsDesdeRequisicion,
        quitarItemsDeRequisicion: quitarItemsDeRequisicion
    };

})(window, document);
