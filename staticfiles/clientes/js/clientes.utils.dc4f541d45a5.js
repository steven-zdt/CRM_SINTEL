/**
 * clientes.utils.js - Utilidades compartidas para módulo Clientes
 */
(function(w, d) {
    'use strict';

    w.AppCliente = w.AppCliente || {};

    w.ClienteUtils = {
        /**
         * Actualiza la visibilidad del boton "Eliminar" en cada contacto.
         * Oculto cuando hay solo un contacto; visible cuando hay 2 o mas.
         */
        _actualizarBotonesEliminar: function(contenedor) {
            const items = contenedor.querySelectorAll('.contacto-item');
            const soloUno = items.length <= 1;
            items.forEach(function(item) {
                const btn = item.querySelector('.btn-eliminar-contacto');
                if (btn) btn.style.display = soloUno ? 'none' : '';
            });
        },

        agregarContacto: function(contenedorId) {
            const contenedor = d.querySelector(contenedorId);
            if (!contenedor) return;

            // Prevenir duplicados: el ultimo contacto debe tener nombre y email antes de agregar otro
            const items = contenedor.querySelectorAll('.contacto-item');
            if (items.length > 0) {
                const ultimo = items[items.length - 1];
                const nombreInput = ultimo.querySelector('.contacto-nombre');
                const emailInput = ultimo.querySelector('.contacto-email');
                const nombre = (nombreInput?.value || '').trim();
                const email = (emailInput?.value || '').trim();
                if (!nombre || !email) {
                    if (nombreInput && !nombre) nombreInput.classList.add('is-invalid');
                    if (emailInput && !email) emailInput.classList.add('is-invalid');
                    console.warn('[clientes.utils] Complete los campos del contacto anterior antes de agregar uno nuevo.');
                    return;
                }
            }

            const contactoHTML = `
                <div class="card mb-2 contacto-item">
                    <div class="card-body p-3">
                        <div class="row g-2">
                            <div class="col-md-5">
                                <label class="form-label small">Nombre Completo *</label>
                                <input type="text" class="form-control form-control-sm contacto-nombre" required />
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small">Cargo</label>
                                <input type="text" class="form-control form-control-sm contacto-cargo" />
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small">Teléfono</label>
                                <input type="text" class="form-control form-control-sm contacto-telefono" />
                            </div>
                            <div class="col-md-5">
                                <label class="form-label small">Email *</label>
                                <input type="email" class="form-control form-control-sm contacto-email" required />
                            </div>
                            <div class="col-md-4">
                                <div class="form-check mt-4">
                                    <input class="form-check-input contacto-activo" type="checkbox" checked />
                                    <label class="form-check-label small">Activo</label>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="form-check mt-4">
                                    <input class="form-check-input contacto-principal" type="checkbox" />
                                    <label class="form-check-label small">Principal</label>
                                </div>
                            </div>
                            <div class="col-12 text-end">
                                <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar-contacto">
                                    <i class="bi bi-trash"></i> Eliminar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            contenedor.insertAdjacentHTML('beforeend', contactoHTML);
            this._actualizarBotonesEliminar(contenedor);
        },

        eliminarContacto: function(e) {
            const btn = e.target.closest('.btn-eliminar-contacto');
            if (!btn) return;
            const contactoItem = btn.closest('.contacto-item');
            if (!contactoItem) return;
            const contenedor = contactoItem.parentElement;
            contactoItem.remove();
            if (contenedor) w.ClienteUtils._actualizarBotonesEliminar(contenedor);
        }
    };

    w.AppCliente.utils = w.ClienteUtils;
    
    console.log('[clientes.utils] ✅ ClienteUtils inicializado');
})(window, document);