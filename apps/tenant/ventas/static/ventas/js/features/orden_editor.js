/**
 * orden_editor.js — Logica de offcanvas Crear y Detalle para Ordenes de Venta v3.10.5
 * Namespace: window.Sintel.Ventas.Editor
 *
 * Reglas:
 *   - mostrarOffcanvasSeguro(el) para abrir Bootstrap offcanvas (anti-backdrop)
 *   - NUNCA parseInt() sobre UUIDs — usar getAttribute('data-uuid') o formData.get()
 *   - Siempre capturar cliente como UUID desde data-uuid del <option> seleccionado
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
        var el = typeof elOrId === 'string' ? d.getElementById(elOrId) : elOrId;
        if (!el) return;
        var existingBackdrops = d.querySelectorAll('.offcanvas-backdrop');
        existingBackdrops.forEach(function (bd) { bd.remove(); });
        d.body.classList.remove('offcanvas-open');
        d.body.style.overflow = '';

        try {
            var instance = bootstrap.Offcanvas.getInstance(el);
            if (instance) {
                instance.dispose();
            }
            var oc = new bootstrap.Offcanvas(el);
            oc.show();
        } catch (err) {
            console.error(MOD, 'Error al abrir offcanvas:', err);
        }
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

    function getCSRFToken() {
        var el = d.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    // ── Gestion de Items ───────────────────────────────────────────────────

    var _itemCounter = 0;

    function crearFilaItem(idx) {
        var tr = d.createElement('tr');
        tr.setAttribute('data-item-idx', idx);
        tr.innerHTML = [
            '<td><input type="text" class="form-control form-control-sm item-descripcion" ',
            '     placeholder="Descripcion" required></td>',
            '<td><input type="number" class="form-control form-control-sm item-cantidad" ',
            '     value="1" min="0.0001" step="0.0001" required></td>',
            '<td><input type="number" class="form-control form-control-sm item-precio" ',
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
            '  <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar-item" ',
            '          title="Eliminar item">',
            '    <i class="bi bi-trash3"></i>',
            '  </button>',
            '</td>',
        ].join('');
        return tr;
    }

    function calcularTotalesForm() {
        var tbody = d.getElementById('orden-items-body');
        if (!tbody) return;

        var subtotal = 0;
        var impuestos = 0;

        tbody.querySelectorAll('tr[data-item-idx]').forEach(function (tr) {
            var cant = parseFloat(tr.querySelector('.item-cantidad').value) || 0;
            var precio = parseFloat(tr.querySelector('.item-precio').value) || 0;
            var iva = parseFloat(tr.querySelector('.item-iva').value) || 0;
            var sub = cant * precio;
            subtotal += sub;
            impuestos += sub * (iva / 100);
            tr.querySelector('.item-subtotal').textContent = fmtMoneda(sub);
        });

        var total = subtotal + impuestos;
        var elSub = d.getElementById('orden-display-subtotal');
        var elIva = d.getElementById('orden-display-iva');
        var elTot = d.getElementById('orden-display-total');
        if (elSub) elSub.textContent = fmtMoneda(subtotal);
        if (elIva) elIva.textContent = fmtMoneda(impuestos);
        if (elTot) elTot.textContent = fmtMoneda(total);
    }

    function agregarFilaItem() {
        var tbody = d.getElementById('orden-items-body');
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
        var tbody = d.getElementById('orden-items-body');
        if (!tbody) return [];
        var items = [];
        tbody.querySelectorAll('tr[data-item-idx]').forEach(function (tr) {
            items.push({
                descripcion: tr.querySelector('.item-descripcion').value.trim(),
                cantidad: parseFloat(tr.querySelector('.item-cantidad').value) || 1,
                precio_unitario: parseFloat(tr.querySelector('.item-precio').value) || 0,
                tasa_iva: parseFloat(tr.querySelector('.item-iva').value) || 0,
            });
        });
        return items;
    }

    // ── Captura de Cliente (sin parseInt) ─────────────────────────────────

    function capturarClienteUUID() {
        var sel = d.getElementById('orden-cliente');
        if (!sel || !sel.value) return null;
        var opt = sel.options[sel.selectedIndex];
        return opt ? (opt.getAttribute('data-uuid') || null) : null;
    }

    // ── Bindings del formulario Crear ──────────────────────────────────────

    function bindFormCrear(offcanvasEl) {
        var btnAgregar = d.getElementById('btn-agregar-item-orden');
        if (btnAgregar) {
            var nuevoAgregar = btnAgregar.cloneNode(true);
            btnAgregar.parentNode.replaceChild(nuevoAgregar, btnAgregar);
            nuevoAgregar.addEventListener('click', agregarFilaItem);
        }

        var clienteSel = d.getElementById('orden-cliente');
        var clienteHidden = d.getElementById('orden-cliente-id');
        if (clienteSel && clienteHidden) {
            clienteSel.addEventListener('change', function () {
                var uuid = capturarClienteUUID();
                clienteHidden.value = uuid || '';
            });
        }

        var btnBorrador = d.getElementById('btn-guardar-borrador');
        if (btnBorrador) {
            var nuevoBorrador = btnBorrador.cloneNode(true);
            btnBorrador.parentNode.replaceChild(nuevoBorrador, btnBorrador);
            nuevoBorrador.addEventListener('click', function () { guardarOrden(false); });
        }

        var btnConfirmar = d.getElementById('btn-guardar-confirmar');
        if (btnConfirmar) {
            var nuevoConfirmar = btnConfirmar.cloneNode(true);
            btnConfirmar.parentNode.replaceChild(nuevoConfirmar, btnConfirmar);
            nuevoConfirmar.addEventListener('click', function () { guardarOrden(true); });
        }

        agregarFilaItem();
        calcularTotalesForm();
        mostrarOffcanvasSeguro(offcanvasEl);
    }

    // ── Guardar Orden (Crear) ──────────────────────────────────────────────

    function guardarOrden(confirmarInmediato) {
        ocultarFeedback('form-venta-crear-feedback');

        var clienteUUID = capturarClienteUUID();
        if (!clienteUUID) {
            mostrarFeedback('form-venta-crear-feedback', 'Debe seleccionar un cliente.', 'danger');
            return;
        }

        var fechaEmision = d.getElementById('orden-fecha-emision');
        if (!fechaEmision || !fechaEmision.value) {
            mostrarFeedback('form-venta-crear-feedback', 'La fecha de emision es requerida.', 'danger');
            return;
        }

        var items = recolectarItems();
        if (items.length === 0) {
            mostrarFeedback('form-venta-crear-feedback', 'Debe agregar al menos un item.', 'danger');
            return;
        }

        for (var i = 0; i < items.length; i++) {
            if (!items[i].descripcion) {
                mostrarFeedback('form-venta-crear-feedback', 'Todos los items deben tener descripcion.', 'danger');
                return;
            }
            if (!items[i].precio_unitario || items[i].precio_unitario <= 0) {
                mostrarFeedback('form-venta-crear-feedback', 'Todos los items deben tener precio unitario mayor a 0.', 'danger');
                return;
            }
        }

        var payload = {
            cliente: clienteUUID,
            fecha_emision: fechaEmision.value,
            fecha_vencimiento: (d.getElementById('orden-fecha-vencimiento') || {}).value || null,
            observaciones: (d.getElementById('orden-observaciones') || {}).value || '',
            items: items,
        };

        var btnB = d.getElementById('btn-guardar-borrador');
        var btnC = d.getElementById('btn-guardar-confirmar');
        if (btnB) btnB.disabled = true;
        if (btnC) btnC.disabled = true;

        var API = w.Sintel.Ventas.API;
        API.create(payload)
            .then(function (orden) {
                if (!confirmarInmediato) {
                    _cerrarOffcanvasCrear();
                    if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                    return;
                }
                return API.confirmar(orden.uuid).then(function () {
                    _cerrarOffcanvasCrear();
                    if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                });
            })
            .catch(function (err) {
                var msg = 'Error al guardar la orden.';
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
                if (btnC) btnC.disabled = false;
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
                var uuid = btn.getAttribute('data-venta-uuid');
                if (!action || !uuid) return;

                var API = w.Sintel.Ventas.API;
                btn.disabled = true;
                ocultarFeedback('detalle-venta-feedback');

                var promesa;
                if (action === 'confirmar') {
                    promesa = API.confirmar(uuid);
                } else if (action === 'facturar') {
                    promesa = API.facturar(uuid);
                } else if (action === 'anular') {
                    var motivo = w.prompt('Motivo de la anulacion (opcional):') || '';
                    promesa = API.anular(uuid, motivo);
                } else {
                    btn.disabled = false;
                    return;
                }

                promesa.then(function (resp) {
                    _cerrarOffcanvasDetalle(offcanvasEl);
                    if (w.Sintel.Ventas.List) { w.Sintel.Ventas.List.recargar(); }
                    if (action === 'facturar' && resp && resp.factura_uuid) {
                        mostrarFeedback('detalle-venta-feedback',
                            'Factura generada exitosamente.',
                            'success');
                    }
                }).catch(function (err) {
                    btn.disabled = false;
                    var msg = 'Error al ejecutar la accion.';
                    if (err.data && err.data.detail) msg = err.data.detail;
                    else if (err.data && err.data.error) msg = err.data.error;
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
