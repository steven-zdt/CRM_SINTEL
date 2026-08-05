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
        if (isNaN(n)) return '$0';
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP',
            minimumFractionDigits: 0, maximumFractionDigits: 0
        }).format(n);
    }

    function mostrarOffcanvasSeguro(elOrId) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel && w.Sintel.Core && w.Sintel.Core.mostrarOffcanvasSeguro(elOrId);
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

    function crearFilaItem(idx) {
        var tr = d.createElement('tr');
        tr.setAttribute('data-item-idx', idx);
        tr.innerHTML = [
            '<td><input type="text" class="form-control form-control-sm item-descripcion"',
            '     placeholder="Descripcion" required></td>',
            '<td><input type="number" class="form-control form-control-sm item-cantidad"',
            '     value="1" min="0.0001" step="0.0001" required></td>',
            '<td><input type="number" class="form-control form-control-sm item-precio"',
            '     placeholder="0" min="0" step="1" required></td>',
            '<td>',
            '  <select class="form-select form-select-sm item-iva">',
            '    <option value="0">0%</option>',
            '    <option value="5">5%</option>',
            '    <option value="19" selected>19%</option>',
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

    function agregarFilaItem() {
        var tbody = d.getElementById('venta-items-body');
        if (!tbody) return;
        _itemCounter += 1;
        var tr = crearFilaItem(_itemCounter);
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
        if (!sel || !sel.value) return null;
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
        var btnAgregar = d.getElementById('btn-agregar-item-venta');
        if (btnAgregar) {
            var nuevoAgregar = btnAgregar.cloneNode(true);
            btnAgregar.parentNode.replaceChild(nuevoAgregar, btnAgregar);
            nuevoAgregar.addEventListener('click', agregarFilaItem);
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
            nuevoB.addEventListener('click', function () { guardarVenta(false); });
        }

        var btnDian = d.getElementById('btn-facturar-dian');
        if (btnDian) {
            var nuevoD = btnDian.cloneNode(true);
            btnDian.parentNode.replaceChild(nuevoD, btnDian);
            nuevoD.addEventListener('click', function () { guardarVenta(true); });
        }

        agregarFilaItem();
        calcularTotalesForm();
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

    function guardarVenta(facturarDian) {
        var payload = _validarYConstruirPayload();
        if (!payload) return;

        var API = w.Sintel.Ventas.API;
        var btnB = d.getElementById('btn-guardar-borrador');
        var btnD = d.getElementById('btn-facturar-dian');
        if (btnB) btnB.disabled = true;
        if (btnD) btnD.disabled = true;

        API.create(payload)
            .then(function (venta) {
                if (!facturarDian) {
                    _cerrarOffcanvasCrear();
                    if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                    return;
                }
                return API.procesarFacturar(venta.uuid).then(function () {
                    _cerrarOffcanvasCrear();
                    if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                });
            })
            .catch(function (err) {
                var msg = 'Error al guardar la venta.';
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
        },

        abrirCrear: function () {
            var url = w.Sintel && w.Sintel.Ventas && w.Sintel.Ventas.API
                ? w.Sintel.Ventas.API.renderCrear()
                : '/api/v1/ventas/render-offcanvas/crear/';
            var container = d.getElementById('offcanvas-container-ventas');
            if (!container) return;
            htmx.ajax('GET', url, { target: '#offcanvas-container-ventas', swap: 'innerHTML' });
        },
    };

    w.Sintel.Ventas.Editor = Editor;

    d.dispatchEvent(new CustomEvent('sintel:ventas:editor:ready'));

})(window, document);
