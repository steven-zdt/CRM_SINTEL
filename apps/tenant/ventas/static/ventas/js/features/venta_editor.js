/**
 * venta_editor.js — Logica de offcanvas Crear y Detalle para Ventas v3.16.x
 * Namespace: window.Sintel.Ventas.Editor
 *
 * Reglas:
 *   - mostrarOffcanvasSeguro(el) para abrir Bootstrap offcanvas (anti-backdrop)
 *   - NUNCA parseInt() sobre UUIDs — usar getAttribute('data-uuid') del <option>
 *   - "Guardar Borrador" -> API.create(payload)
 *   - "Guardar y Facturar DIAN" -> API.create(payload) -> API.procesarFacturar(uuid)
 */
(function (w, d) {
    'use strict';

    var MOD = '[ventas.editor]';

    w.Sintel = w.Sintel || {};
    w.Sintel.Ventas = w.Sintel.Ventas || {};

    // ── Utilidades ─────────────────────────────────────────────────────────

    function fmtMoneda(v) {
        var n = parseFloat(v);
        if (isNaN(n)) return '$0,00';
        // Bug real (2026-09-18): forzar maximumFractionDigits=0 aqui
        // truncaba los centavos SOLO en la vista previa de items/totales de
        // este formulario (el valor real enviado al backend -- via
        // parseFloat() sobre el <input> -- nunca perdia precision), pero
        // visualmente parecia "omitir cifras despues de la coma" al
        // comparar contra la Factura origen (que si muestra centavos via
        // currency_cop). Se alinea con la SSoT (dom-utils.js formatCurrency,
        // maximumFractionDigits=2 por defecto) y con currency_cop.
        if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
            return w.DOMUtils.formatCurrency(n, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP',
            minimumFractionDigits: 2, maximumFractionDigits: 2
        }).format(n);
    }

    function mostrarOffcanvasSeguro(elOrId) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(elOrId);
    }

    function _escapeHtml(s) {
        return String(s === null || s === undefined ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function mostrarFeedback(containerId, mensaje, tipo) {
        var el = d.getElementById(containerId);
        if (!el) return;
        el.className = 'alert alert-' + (tipo || 'danger') + ' mt-3';
        el.textContent = mensaje;
        el.classList.remove('d-none');
    }

    function ocultarFeedback(containerId) {
        var el = d.getElementById(containerId);
        if (el) { el.classList.add('d-none'); el.textContent = ''; }
    }

    // ── Gestion de Items ───────────────────────────────────────────────────

    var _itemCounter = 0;

    function crearFilaItem(idx, itemData) {
        itemData = itemData || {};
        var cantidad    = (itemData.cantidad !== undefined && itemData.cantidad !== null) ? itemData.cantidad : 1;
        var precio      = (itemData.precio_unitario !== undefined && itemData.precio_unitario !== null) ? itemData.precio_unitario : '';
        var descripcion = itemData.descripcion || '';

        // BUG (autorrelleno desde Factura): porcentaje_iva llega desde la API
        // como string decimal ("19.00", DecimalField), pero las 3 opciones
        // fijas del select usan enteros ("0"/"5"/"19") -- la comparacion
        // estricta anterior (iva === '19') nunca coincidia y el select caia
        // silenciosamente en la PRIMERA opcion (0%), perdiendo el IVA real y
        // descuadrando el total contra la factura. Se normaliza con
        // parseFloat antes de comparar (mismo criterio que CO-5 en Compras).
        var ivaNum = (itemData.porcentaje_iva !== undefined && itemData.porcentaje_iva !== null)
            ? parseFloat(itemData.porcentaje_iva) : 19;
        if (isNaN(ivaNum)) ivaNum = 19;
        var ivaOpciones = [0, 5, 19];
        var ivaExtra = ivaOpciones.indexOf(ivaNum) === -1 ? ivaNum : null;

        var tr = d.createElement('tr');
        tr.setAttribute('data-item-idx', idx);
        tr.innerHTML = [
            '<td><input type="text" class="form-control form-control-sm item-descripcion"',
            '     placeholder="Descripcion" required value="' + _escapeHtml(descripcion) + '"></td>',
            '<td><input type="number" class="form-control form-control-sm item-cantidad"',
            '     value="' + _escapeHtml(cantidad) + '" min="0.0001" step="0.0001" required></td>',
            '<td><input type="number" class="form-control form-control-sm item-precio"',
            '     placeholder="0" min="0" step="any" required value="' + _escapeHtml(precio) + '"></td>',
            '<td>',
            '  <select class="form-select form-select-sm item-iva">',
            '    <option value="0"' + (ivaNum === 0 ? ' selected' : '') + '>0%</option>',
            '    <option value="5"' + (ivaNum === 5 ? ' selected' : '') + '>5%</option>',
            '    <option value="19"' + (ivaNum === 19 ? ' selected' : '') + '>19%</option>',
            (ivaExtra !== null
                ? '    <option value="' + ivaExtra + '" selected>' + ivaExtra + '%</option>'
                : ''),
            '  </select>',
            '</td>',
            '<td class="text-end item-subtotal fw-semibold">$0</td>',
            '<td class="text-center">',
            '  <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar-item"',
            '          title="Eliminar item">',
            '    <i class="bi bi-trash3"></i>',
            '  </button>',
            '</td>',
        ].join('');
        return tr;
    }

    function calcularTotalesForm() {
        var tbody = d.getElementById('venta-items-body');
        if (!tbody) return;

        var subtotal = 0;
        var impuestos = 0;

        tbody.querySelectorAll('tr[data-item-idx]').forEach(function (tr) {
            var cant   = parseFloat(tr.querySelector('.item-cantidad').value) || 0;
            var precio = parseFloat(tr.querySelector('.item-precio').value) || 0;
            var iva    = parseFloat(tr.querySelector('.item-iva').value) || 0;
            var sub    = cant * precio;
            subtotal  += sub;
            impuestos += sub * (iva / 100);
            tr.querySelector('.item-subtotal').textContent = fmtMoneda(sub);
        });

        var elSub = d.getElementById('venta-display-subtotal');
        var elIva = d.getElementById('venta-display-iva');
        var elTot = d.getElementById('venta-display-total');
        if (elSub) elSub.textContent = fmtMoneda(subtotal);
        if (elIva) elIva.textContent = fmtMoneda(impuestos);
        if (elTot) elTot.textContent = fmtMoneda(subtotal + impuestos);
    }

    function agregarFilaItem(itemData) {
        var tbody = d.getElementById('venta-items-body');
        if (!tbody) return;
        _itemCounter += 1;
        var tr = crearFilaItem(_itemCounter, itemData);
        tbody.appendChild(tr);

        tr.querySelector('.item-cantidad').addEventListener('input', calcularTotalesForm);
        tr.querySelector('.item-precio').addEventListener('input', calcularTotalesForm);
        tr.querySelector('.item-iva').addEventListener('change', calcularTotalesForm);
        tr.querySelector('.btn-eliminar-item').addEventListener('click', function () {
            tr.remove();
            calcularTotalesForm();
        });
    }

    function recolectarItems() {
        var tbody = d.getElementById('venta-items-body');
        if (!tbody) return [];
        var items = [];
        tbody.querySelectorAll('tr[data-item-idx]').forEach(function (tr) {
            items.push({
                descripcion:    tr.querySelector('.item-descripcion').value.trim(),
                cantidad:       parseFloat(tr.querySelector('.item-cantidad').value) || 1,
                precio_unitario: parseFloat(tr.querySelector('.item-precio').value) || 0,
                porcentaje_iva:  parseFloat(tr.querySelector('.item-iva').value) || 0,
            });
        });
        return items;
    }

    // ── Captura de Cliente y Resolucion (sin parseInt) ────────────────────

    function capturarClienteUUID() {
        var sel = d.getElementById('venta-cliente');
        if (!sel) {
            // Modo edicion: no hay <select>, el cliente esta bloqueado y su
            // UUID ya viene precargado en el hidden por el servidor.
            var hidden = d.getElementById('venta-cliente-uuid');
            return (hidden && hidden.value) || null;
        }
        if (!sel.value) return null;
        var opt = sel.options[sel.selectedIndex];
        return opt ? (opt.getAttribute('data-uuid') || null) : null;
    }

    function capturarResolucionUUID() {
        var sel = d.getElementById('venta-resolucion');
        if (!sel || !sel.value) return null;
        var opt = sel.options[sel.selectedIndex];
        return opt ? (opt.getAttribute('data-uuid') || null) : null;
    }

    function _actualizarInfoResolucion() {
        var sel = d.getElementById('venta-resolucion');
        var infoEl = d.getElementById('venta-resolucion-info');
        if (!sel || !infoEl) return;
        if (!sel.value) {
            infoEl.textContent = '';
            return;
        }
        var opt = sel.options[sel.selectedIndex];
        if (!opt) return;
        var consecutivo = opt.getAttribute('data-consecutivo') || '?';
        var prefijo = opt.getAttribute('data-prefijo') || '';
        infoEl.textContent = 'Numero a asignar: ' + (prefijo ? prefijo + consecutivo : consecutivo);
    }

    // ── Bindings del formulario Crear ──────────────────────────────────────

    function bindFormCrear(offcanvasEl) {
        var form      = d.getElementById('venta-crear-form');
        var modo      = form ? form.getAttribute('data-mode') : 'create';
        var ventaUuid = form ? form.getAttribute('data-venta-uuid') : null;

        var btnAgregar = d.getElementById('btn-agregar-item-venta');
        if (btnAgregar) {
            var nuevoAgregar = btnAgregar.cloneNode(true);
            btnAgregar.parentNode.replaceChild(nuevoAgregar, btnAgregar);
            nuevoAgregar.addEventListener('click', function () { agregarFilaItem(); });
        }

        var clienteSel    = d.getElementById('venta-cliente');
        var clienteHidden = d.getElementById('venta-cliente-uuid');
        if (clienteSel && clienteHidden) {
            clienteSel.addEventListener('change', function () {
                clienteHidden.value = capturarClienteUUID() || '';
            });
        }

        var resolucionSel = d.getElementById('venta-resolucion');
        if (resolucionSel) {
            resolucionSel.addEventListener('change', _actualizarInfoResolucion);
        }

        var btnBorrador = d.getElementById('btn-guardar-borrador');
        if (btnBorrador) {
            var nuevoB = btnBorrador.cloneNode(true);
            btnBorrador.parentNode.replaceChild(nuevoB, btnBorrador);
            if (modo === 'edit') {
                nuevoB.innerHTML = '<i class="bi bi-floppy me-1"></i>Guardar Cambios';
            }
            nuevoB.addEventListener('click', function () { guardarVenta(false, modo, ventaUuid); });
        }

        var btnDian = d.getElementById('btn-facturar-dian');
        if (btnDian) {
            var nuevoD = btnDian.cloneNode(true);
            btnDian.parentNode.replaceChild(nuevoD, btnDian);
            nuevoD.addEventListener('click', function () { guardarVenta(true, modo, ventaUuid); });
        }

        if (modo === 'edit') {
            var itemsDataEl = d.getElementById('venta-items-data');
            var itemsPrevios = [];
            if (itemsDataEl) {
                try { itemsPrevios = JSON.parse(itemsDataEl.textContent || '[]'); } catch (_e) { itemsPrevios = []; }
            }
            if (itemsPrevios.length) {
                itemsPrevios.forEach(function (it) { agregarFilaItem(it); });
            } else {
                agregarFilaItem();
            }
        } else {
            agregarFilaItem();
        }
        calcularTotalesForm();
        bindFacturaWidget(offcanvasEl);
        mostrarOffcanvasSeguro(offcanvasEl);
    }

    // ── Guardar Venta ──────────────────────────────────────────────────────

    function _validarYConstruirPayload() {
        ocultarFeedback('form-venta-crear-feedback');

        var clienteUUID = capturarClienteUUID();
        if (!clienteUUID) {
            mostrarFeedback('form-venta-crear-feedback', 'Debe seleccionar un cliente.', 'danger');
            return null;
        }

        var fechaEl = d.getElementById('venta-fecha-emision');
        if (!fechaEl || !fechaEl.value) {
            mostrarFeedback('form-venta-crear-feedback', 'La fecha de emision es requerida.', 'danger');
            return null;
        }

        var items = recolectarItems();
        if (items.length === 0) {
            mostrarFeedback('form-venta-crear-feedback', 'Debe agregar al menos un item.', 'danger');
            return null;
        }

        for (var i = 0; i < items.length; i++) {
            if (!items[i].descripcion) {
                mostrarFeedback('form-venta-crear-feedback', 'Todos los items deben tener descripcion.', 'danger');
                return null;
            }
            if (!items[i].precio_unitario || items[i].precio_unitario <= 0) {
                mostrarFeedback('form-venta-crear-feedback', 'Todos los items deben tener precio mayor a 0.', 'danger');
                return null;
            }
        }

        var resolucionUUID = capturarResolucionUUID();

        return {
            cliente:          clienteUUID,
            fecha_emision:    fechaEl.value,
            fecha_vencimiento: (d.getElementById('venta-fecha-vencimiento') || {}).value || null,
            observaciones:    (d.getElementById('venta-observaciones') || {}).value || '',
            resolucion:       resolucionUUID || null,
            items:            items,
        };
    }

    function guardarVenta(facturarDian, modo, ventaUuid) {
        var payload = _validarYConstruirPayload();
        if (!payload) return;

        var API = w.Sintel.Ventas.API;
        var btnB = d.getElementById('btn-guardar-borrador');
        var btnD = d.getElementById('btn-facturar-dian');
        if (btnB) btnB.disabled = true;
        if (btnD) btnD.disabled = true;

        var esEdicion = (modo === 'edit');
        var promesaGuardado = esEdicion ? API.update(ventaUuid, payload) : API.create(payload);

        promesaGuardado
            .then(function (venta) {
                function continuarDespuesDeVincular() {
                    if (!facturarDian) {
                        _cerrarOffcanvasCrear();
                        if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                        return;
                    }
                    return API.procesarFacturar(venta.uuid).then(function () {
                        _cerrarOffcanvasCrear();
                        if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                    });
                }

                // Si el usuario selecciono una Factura existente en el
                // widget ANTES de que la Venta existiera, la vinculacion
                // real se hace ahora que ya tenemos venta.uuid (ver
                // bindFacturaWidget -> confirmarSeleccion, modo creacion).
                var widget = d.getElementById('venta-factura-widget');
                var facturaPendienteUuid = widget && widget.dataset.facturaPendienteUuid;
                if (!esEdicion && facturaPendienteUuid) {
                    return API.vincularFactura(venta.uuid, facturaPendienteUuid)
                        .then(continuarDespuesDeVincular)
                        .catch(function (err) {
                            // La Venta SI se creo -- no se pierde ese exito
                            // por un fallo al vincular la factura pendiente.
                            console.warn(MOD, 'Venta creada pero fallo la vinculacion de factura pendiente:', err);
                            return continuarDespuesDeVincular();
                        });
                }
                return continuarDespuesDeVincular();
            })
            .catch(function (err) {
                var msg = esEdicion ? 'Error al guardar los cambios.' : 'Error al guardar la venta.';
                if (err.data) {
                    var msgs = [];
                    Object.keys(err.data).forEach(function (k) {
                        var v = err.data[k];
                        msgs.push(k + ': ' + (Array.isArray(v) ? v.join(', ') : String(v)));
                    });
                    if (msgs.length) msg = msgs.join(' | ');
                }
                mostrarFeedback('form-venta-crear-feedback', msg, 'danger');
                if (btnB) btnB.disabled = false;
                if (btnD) btnD.disabled = false;
            });
    }

    function _cerrarOffcanvasCrear() {
        var el = d.getElementById('offcanvas-venta-crear');
        if (!el) return;
        try {
            var inst = bootstrap.Offcanvas.getInstance(el);
            if (inst) inst.hide();
        } catch (_) {}
    }

    // ── Acciones en Detalle ────────────────────────────────────────────────

    function bindDetalleAcciones(offcanvasEl) {
        if (!offcanvasEl) return;

        offcanvasEl.querySelectorAll('[data-venta-action]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var action = btn.getAttribute('data-venta-action');
                var uuid   = btn.getAttribute('data-venta-uuid');
                if (!action || !uuid) return;

                if (action === 'editar') {
                    // Navega al offcanvas de edicion -- no es una llamada de
                    // API async como las demas acciones de este handler.
                    Editor.abrirEditar(uuid);
                    return;
                }

                var API = w.Sintel.Ventas.API;
                btn.disabled = true;
                ocultarFeedback('detalle-venta-feedback');

                var promesa;
                if (action === 'facturar-dian') {
                    promesa = API.procesarFacturar(uuid);
                } else if (action === 'anular') {
                    var motivo = w.prompt('Motivo de la anulacion (opcional):') || '';
                    promesa = API.anular(uuid, motivo);
                } else {
                    btn.disabled = false;
                    return;
                }

                promesa.then(function () {
                    _cerrarOffcanvasDetalle(offcanvasEl);
                    if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                }).catch(function (err) {
                    btn.disabled = false;
                    var msg = 'Error al ejecutar la accion.';
                    if (err.data && err.data.detail) msg = err.data.detail;
                    mostrarFeedback('detalle-venta-feedback', msg, 'danger');
                });
            });
        });

        mostrarOffcanvasSeguro(offcanvasEl);
    }

    function _cerrarOffcanvasDetalle(offcanvasEl) {
        try {
            var inst = bootstrap.Offcanvas.getInstance(offcanvasEl);
            if (inst) inst.hide();
        } catch (_) {}
    }

    // ── Vincular Factura existente (FACTURAS-VENTAS-COMPRAS-01) ────────────
    // Busqueda + seleccion EXPLICITA (FASE 12: nunca auto-match/auto-assign
    // -- el usuario debe pulsar "Seleccionar" y luego confirmar "Guardar").

    function bindFacturaWidget(offcanvasEl) {
        var widget = offcanvasEl.querySelector('#venta-factura-widget');
        if (!widget) return;

        var ventaUuid   = widget.getAttribute('data-venta-uuid');
        var toggleBtn   = widget.querySelector('[data-venta-factura-action="mostrar-buscador"]');
        var cambiarBtn  = widget.querySelector('[data-venta-factura-action="cambiar"]');
        var panel       = widget.querySelector('#venta-factura-buscador-panel');
        var input       = widget.querySelector('#venta-factura-buscar-input');
        var resultados  = widget.querySelector('#venta-factura-buscar-resultados');
        var asociadaDiv = widget.querySelector('#venta-factura-asociada');
        var buscadorDiv = widget.querySelector('#venta-factura-buscador');
        var debounceId  = null;

        function mostrarBuscador() {
            if (asociadaDiv) asociadaDiv.classList.add('d-none');
            if (buscadorDiv) buscadorDiv.classList.remove('d-none');
            if (panel) panel.classList.remove('d-none');
            if (input) input.focus();
        }

        if (toggleBtn) toggleBtn.addEventListener('click', mostrarBuscador);
        if (cambiarBtn) cambiarBtn.addEventListener('click', mostrarBuscador);

        function renderResultados(items) {
            if (!resultados) return;
            if (!items || !items.length) {
                resultados.innerHTML = '<div class="text-muted p-2">Sin resultados.</div>';
                return;
            }
            resultados.innerHTML = items.map(function (f) {
                return '' +
                    '<div class="d-flex align-items-center justify-content-between border-bottom py-2 px-1">' +
                    '  <div>' +
                    '    <div class="fw-semibold">' + f.numero + '</div>' +
                    '    <div class="text-muted" style="font-size:0.78rem;">' +
                    f.fecha + ' &middot; ' + (f.tercero || f.cliente || 'N/A') + ' &middot; $' + f.total +
                    '    </div>' +
                    '  </div>' +
                    '  <button type="button" class="btn btn-sm btn-primary flex-shrink-0"' +
                    '          data-factura-uuid="' + f.uuid + '" data-factura-numero="' + f.numero + '">' +
                    '    Seleccionar' +
                    '  </button>' +
                    '</div>';
            }).join('');

            resultados.querySelectorAll('button[data-factura-uuid]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    confirmarSeleccion(btn.getAttribute('data-factura-uuid'), btn.getAttribute('data-factura-numero'));
                });
            });
        }

        // FST-375 secc. 21 (autorrelleno de Nueva Venta): al vincular una
    // Factura ANTES de guardar, precarga el formulario de creacion con sus
    // datos -- antes solo se guardaba el UUID pendiente y el usuario tenia
    // que re-escribir a mano cliente/fechas/items que la factura ya trae.
    function autorrellenarDesdeFactura(facturaUuid, asociadaDiv) {
        var API = w.Sintel.Ventas.API;
        if (!API || typeof API.obtenerFacturaParaAutorrelleno !== 'function') return;

        API.obtenerFacturaParaAutorrelleno(facturaUuid).then(function (resultado) {
            var factura = resultado.factura || {};
            var items = resultado.items || [];

            // Cliente: solo se auto-selecciona si ya existe como <option>
            // (Cliente real registrado) -- nunca se crea uno nuevo desde el
            // frontend. Match por UUID primero (mas confiable), NIT despues.
            var clienteSel = d.getElementById('venta-cliente');
            var clienteHidden = d.getElementById('venta-cliente-uuid');
            var clienteEncontrado = false;
            if (clienteSel) {
                var nitFactura = String(factura.receptor_nit || '').replace(/\D/g, '');
                for (var i = 0; i < clienteSel.options.length; i++) {
                    var opt = clienteSel.options[i];
                    var optUuid = opt.getAttribute('data-uuid') || '';
                    var optDoc = String(opt.getAttribute('data-doc') || '').replace(/\D/g, '');
                    if ((factura.cliente_uuid && optUuid === factura.cliente_uuid) ||
                        (nitFactura && optDoc && optDoc === nitFactura)) {
                        clienteSel.selectedIndex = i;
                        if (clienteHidden) clienteHidden.value = optUuid;
                        clienteEncontrado = true;
                        break;
                    }
                }
            }

            // Fechas
            var fechaEmisionEl = d.getElementById('venta-fecha-emision');
            if (fechaEmisionEl && factura.fecha_emision) {
                fechaEmisionEl.value = String(factura.fecha_emision).slice(0, 10);
            }
            var fechaVencEl = d.getElementById('venta-fecha-vencimiento');
            if (fechaVencEl && factura.fecha_vencimiento) {
                fechaVencEl.value = String(factura.fecha_vencimiento).slice(0, 10);
            }

            // Items: reemplaza las filas actuales (la fila en blanco inicial
            // del formulario) por los items reales de la factura.
            if (items.length) {
                var tbody = d.getElementById('venta-items-body');
                if (tbody) tbody.innerHTML = '';
                items.forEach(function (item) {
                    agregarFilaItem({
                        descripcion: item.descripcion,
                        cantidad: item.cantidad,
                        precio_unitario: item.valor_unitario,
                        porcentaje_iva: item.porcentaje_iva,
                    });
                });
                calcularTotalesForm();
            }

            if (asociadaDiv && !clienteEncontrado && factura.receptor_nit) {
                var aviso = d.createElement('div');
                aviso.className = 'alert alert-warning p-2 small mt-2 mb-0';
                aviso.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>' +
                    'No se encontró un Cliente registrado con NIT ' + _escapeHtml(factura.receptor_nit) +
                    ' — selecciónelo manualmente o regístrelo primero.';
                asociadaDiv.appendChild(aviso);
            }
        }).catch(function (err) {
            console.warn(MOD, 'No se pudo autorrellenar desde la factura seleccionada:', err);
        });
    }

    function confirmarSeleccion(facturaUuid, facturaNumero) {
            resultados.innerHTML =
                '<div class="alert alert-warning p-2 small mb-0">' +
                '  Asociar la factura <strong>' + facturaNumero + '</strong> a esta Venta?' +
                '  <div class="mt-2 d-flex gap-2">' +
                '    <button type="button" class="btn btn-success btn-sm" id="venta-factura-confirmar">Guardar asociacion</button>' +
                '    <button type="button" class="btn btn-secondary btn-sm" id="venta-factura-cancelar-confirm">Cancelar</button>' +
                '  </div>' +
                '</div>';

            resultados.querySelector('#venta-factura-cancelar-confirm').addEventListener('click', function () {
                buscar(input.value);
            });
            resultados.querySelector('#venta-factura-confirmar').addEventListener('click', function () {
                var btn = resultados.querySelector('#venta-factura-confirmar');
                btn.disabled = true;

                if (!ventaUuid) {
                    // Modo creacion: la Venta aun no existe -- se DIFIERE la
                    // vinculacion real hasta que guardarVenta() la cree (ver
                    // abajo). Nunca se llama vincular-factura sin uuid.
                    widget.dataset.facturaPendienteUuid = facturaUuid;
                    widget.dataset.facturaPendienteNumero = facturaNumero;
                    if (asociadaDiv) {
                        asociadaDiv.classList.remove('d-none');
                        asociadaDiv.innerHTML =
                            '<div class="alert alert-info p-2 small mb-0">' +
                            '  <i class="bi bi-link-45deg me-1"></i>' +
                            '  Se vinculara <strong>' + _escapeHtml(facturaNumero) + '</strong> al guardar esta venta.' +
                            '  <button type="button" class="btn btn-sm btn-outline-secondary ms-2" id="venta-factura-pendiente-quitar">Quitar</button>' +
                            '</div>';
                        asociadaDiv.querySelector('#venta-factura-pendiente-quitar').addEventListener('click', function () {
                            delete widget.dataset.facturaPendienteUuid;
                            delete widget.dataset.facturaPendienteNumero;
                            asociadaDiv.classList.add('d-none');
                            asociadaDiv.innerHTML = '';
                            if (buscadorDiv) buscadorDiv.classList.remove('d-none');
                        });
                    }
                    if (buscadorDiv) buscadorDiv.classList.add('d-none');
                    autorrellenarDesdeFactura(facturaUuid, asociadaDiv);
                    return;
                }

                ocultarFeedback('detalle-venta-feedback');
                w.Sintel.Ventas.API.vincularFactura(ventaUuid, facturaUuid).then(function () {
                    if (offcanvasEl.id === 'offcanvas-venta-detalle') {
                        _cerrarOffcanvasDetalle(offcanvasEl);
                        if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                        return;
                    }
                    // Editar Venta (mismo offcanvas de Crear, modo edicion):
                    // NO cerrar el formulario completo -- el usuario puede
                    // seguir editando otros campos. Solo se refleja la nueva
                    // factura vinculada dentro del widget.
                    if (asociadaDiv) {
                        asociadaDiv.classList.remove('d-none');
                        asociadaDiv.innerHTML =
                            '<div class="alert alert-success p-2 small mb-2">' +
                            '  <i class="bi bi-receipt-cutoff me-1"></i><strong>' + _escapeHtml(facturaNumero) + '</strong>' +
                            '</div>' +
                            '<button type="button" class="btn btn-outline-secondary btn-sm" data-venta-factura-action="cambiar">' +
                            '  <i class="bi bi-arrow-repeat me-1"></i>Cambiar factura' +
                            '</button>';
                        var btnCambiar = asociadaDiv.querySelector('[data-venta-factura-action="cambiar"]');
                        if (btnCambiar) btnCambiar.addEventListener('click', mostrarBuscador);
                    }
                    if (buscadorDiv) buscadorDiv.classList.add('d-none');
                    if (panel) panel.classList.add('d-none');
                }).catch(function (err) {
                    btn.disabled = false;
                    var msg = (err.data && (err.data.message || err.data.detail)) || 'Error al asociar la factura.';
                    mostrarFeedback('detalle-venta-feedback', msg, 'danger');
                });
            });
        }

        function buscar(q) {
            q = (q || '').trim();
            if (q.length < 2) {
                resultados.innerHTML = '<div class="text-muted p-2">Escribe al menos 2 caracteres...</div>';
                return;
            }
            resultados.innerHTML = '<div class="text-muted p-2"><i class="bi bi-arrow-repeat spin"></i> Buscando...</div>';
            w.Sintel.Ventas.API.buscarFacturasVenta(q).then(renderResultados).catch(function () {
                resultados.innerHTML = '<div class="text-danger p-2">Error al buscar facturas.</div>';
            });
        }

        if (input) {
            input.addEventListener('input', function () {
                clearTimeout(debounceId);
                debounceId = setTimeout(function () { buscar(input.value); }, 350);
            });
        }
    }

    // ── Gestion Manual de Pago (integracion Facturas<->Ventas) ─────────────
    // Pass-through hacia la Factura vinculada -- Factura sigue siendo el
    // SSoT de estos campos (ver PATCH /api/v1/ventas/{uuid}/gestion-pago/).

    function bindGestionPagoWidget(offcanvasEl) {
        var widget = offcanvasEl.querySelector('#venta-gestion-pago-widget');
        if (!widget) return;

        var ventaUuid = widget.getAttribute('data-venta-uuid');
        var btnGuardar = widget.querySelector('#btn-guardar-gestion-pago');
        if (!btnGuardar) return;

        btnGuardar.addEventListener('click', function () {
            var data = {
                estado_pago: widget.querySelector('#gp-estado-pago').value,
                fecha_pago: widget.querySelector('#gp-fecha-pago').value || '',
                payment_due_date: widget.querySelector('#gp-fecha-limite').value || '',
                forma_pago: widget.querySelector('#gp-forma-pago').value || '',
                medio_pago_codigo: widget.querySelector('#gp-medio-pago').value || '',
            };

            btnGuardar.disabled = true;
            var feedbackEl = widget.querySelector('#venta-gestion-pago-feedback');
            if (feedbackEl) { feedbackEl.classList.add('d-none'); feedbackEl.textContent = ''; }

            w.Sintel.Ventas.API.actualizarGestionPago(ventaUuid, data).then(function () {
                btnGuardar.disabled = false;
                if (feedbackEl) {
                    feedbackEl.className = 'alert alert-success p-2 small mb-2';
                    feedbackEl.textContent = 'Gestion de pago actualizada.';
                }
                if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
            }).catch(function (err) {
                btnGuardar.disabled = false;
                var msg = 'Error al actualizar la gestion de pago.';
                if (err.data) {
                    var msgs = [];
                    Object.keys(err.data).forEach(function (k) {
                        var v = err.data[k];
                        msgs.push(k + ': ' + (Array.isArray(v) ? v.join(', ') : String(v)));
                    });
                    if (msgs.length) msg = msgs.join(' | ');
                }
                if (feedbackEl) {
                    feedbackEl.className = 'alert alert-danger p-2 small mb-2';
                    feedbackEl.textContent = msg;
                }
            });
        });
    }

    // ── API Publica del Modulo ────────────────────────────────────────────

    var Editor = {
        onHtmxLoaded: function () {
            var el = d.getElementById('offcanvas-venta-crear');
            if (!el) {
                console.warn(MOD, 'onHtmxLoaded: offcanvas-venta-crear no encontrado');
                return;
            }
            bindFormCrear(el);
        },

        onDetalleLoaded: function (offcanvasEl) {
            if (!offcanvasEl) {
                offcanvasEl = d.getElementById('offcanvas-venta-detalle');
            }
            if (!offcanvasEl) {
                console.warn(MOD, 'onDetalleLoaded: offcanvas-venta-detalle no encontrado');
                return;
            }
            bindDetalleAcciones(offcanvasEl);
            bindFacturaWidget(offcanvasEl);
            bindGestionPagoWidget(offcanvasEl);
        },

        abrirCrear: function () {
            var url = w.Sintel && w.Sintel.Ventas && w.Sintel.Ventas.API
                ? w.Sintel.Ventas.API.renderCrear()
                : '/api/v1/ventas/render-offcanvas/crear/';
            var container = d.getElementById('offcanvas-container-ventas');
            if (!container) return;
            htmx.ajax('GET', url, { target: '#offcanvas-container-ventas', swap: 'innerHTML' });
        },

        abrirEditar: function (uuid) {
            if (!uuid) return;
            var API = w.Sintel && w.Sintel.Ventas && w.Sintel.Ventas.API;
            if (!API) return;
            var container = d.getElementById('offcanvas-container-ventas');
            if (!container) return;
            htmx.ajax('GET', API.renderEditar(uuid), { target: '#offcanvas-container-ventas', swap: 'innerHTML' });
        },
    };

    w.Sintel.Ventas.Editor = Editor;

    d.dispatchEvent(new CustomEvent('sintel:ventas:editor:ready'));

})(window, document);
