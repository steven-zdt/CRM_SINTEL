/**
 * Feature: Editar Cliente v2.61
 * ⚠️ Feature-Sliced Architecture: Módulo específico para edición de clientes
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - w.clientesAPI (definido en clientes.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en feedback.js) - Sistema de notificaciones
 */
(function(w, d) {
    'use strict';

    let offcanvasInstance = null;
    let clienteId = null;

    /**
     * Agregar un nuevo contacto al contenedor dinámico
     */
    function agregarContacto() {
        const contenedor = d.querySelector('#contenedor-contactos');
        if (!contenedor) return;

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
    }

    /**
     * Eliminar un contacto del contenedor dinámico
     */
    function eliminarContacto(e) {
        const btn = e.target.closest('.btn-eliminar-contacto');
        if (!btn) return;

        const contactoItem = btn.closest('.contacto-item');
        if (contactoItem) {
            contactoItem.remove();
        }
    }

    /**
     * Recolectar datos del formulario de edición
     * @returns {Object} Datos del cliente y array de contactos
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-cliente-editar');
        if (!form) {
            console.error('[cliente.editar] Formulario no encontrado');
            return null;
        }

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Convertir checkbox activo
        const activoCheckbox = d.querySelector('#cliente-activo');
        data.activo = activoCheckbox ? activoCheckbox.checked : true;
        
        // Remover campos vacíos (excepto id)
        Object.keys(data).forEach(key => {
            if (key !== 'id' && (data[key] === '' || data[key] === null)) {
                delete data[key];
            }
        });

        // Recolectar contactos del contenedor dinámico
        const contactos = [];
        const contactoItems = d.querySelectorAll('#contenedor-contactos .contacto-item');
        
        contactoItems.forEach(item => {
            const contacto = {
                id: item.getAttribute('data-contacto-id') || null,
                nombre_completo: item.querySelector('.contacto-nombre')?.value || '',
                cargo: item.querySelector('.contacto-cargo')?.value || '',
                email: item.querySelector('.contacto-email')?.value || '',
                telefono: item.querySelector('.contacto-telefono')?.value || '',
                activo: item.querySelector('.contacto-activo')?.checked || true,
                is_principal: item.querySelector('.contacto-principal')?.checked || false
            };

            // Solo agregar contactos con nombre y email
            if (contacto.nombre_completo && contacto.email) {
                contactos.push(contacto);
            }
        });

        // Agregar contactos al payload
        if (contactos.length > 0) {
            data.contactos = contactos;
        }

        return data;
    }

    /**
     * Actualizar cliente existente (PATCH)
     */
    async function actualizarCliente() {
        if (!clienteId) {
            console.error('[cliente.editar] No se encontró el ID del cliente');
            if (w.SintelFeedback) {
                w.SintelFeedback.error('Error: No se pudo identificar el cliente');
            }
            return;
        }

        const payload = recolectarDatosFormulario();
        if (!payload) {
            if (w.SintelFeedback) {
                w.SintelFeedback.error('No se pudo recolectar los datos del formulario');
            }
            return;
        }

        // Deshabilitar botón mientras se actualiza
        const btnGuardar = d.querySelector('#btn-guardar-cliente');
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Actualizando...';
        }

        // ⚠️ Aislamiento Gradual: No usar try/catch, dejar que los errores se propaguen
        const response = await w.clientesAPI.update(clienteId, payload);
        
        if (response && response.id) {
            // Éxito
            if (w.SintelFeedback) {
                w.SintelFeedback.success('Cliente actualizado exitosamente');
            }

            // Cerrar offcanvas
            if (offcanvasInstance) {
                offcanvasInstance.hide();
            }

            // Disparar evento para recargar la tabla
            d.dispatchEvent(new CustomEvent('clienteGuardado'));
        } else {
            // Error (manejado por UIManager)
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = '<i class="bi bi-save me-1"></i>Actualizar';
            }
        }
    }

    /**
     * Inicializar eventos del formulario de edición
     */
    function initFormularioEditar(detail) {
        const offcanvasEl = d.getElementById('offcanvas-cliente-editar');
        if (!offcanvasEl) {
            console.warn('[cliente.editar] Offcanvas no encontrado');
            return;
        }

        // Obtener ID del cliente desde el evento o desde el atributo data
        clienteId = detail?.clienteId || offcanvasEl.getAttribute('data-cliente-id');
        
        if (!clienteId) {
            console.error('[cliente.editar] No se encontró el ID del cliente');
            return;
        }

        // Obtener instancia de Bootstrap Offcanvas
        if (w.bootstrap && w.bootstrap.Offcanvas) {
            offcanvasInstance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
        }

        // Botón agregar contacto
        const btnAgregarContacto = d.querySelector('#btn-agregar-contacto');
        if (btnAgregarContacto) {
            btnAgregarContacto.addEventListener('click', agregarContacto);
        }

        // Event delegation para eliminar contactos
        const contenedorContactos = d.querySelector('#contenedor-contactos');
        if (contenedorContactos) {
            contenedorContactos.addEventListener('click', eliminarContacto);
        }

        // Botón guardar
        const btnGuardar = d.querySelector('#btn-guardar-cliente');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                await actualizarCliente();
            });
        }

        // Formulario submit
        const form = d.querySelector('#form-cliente-editar');
        if (form) {
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                await actualizarCliente();
            });
        }

        // Limpiar al cerrar
        offcanvasEl.addEventListener('hidden.bs.offcanvas', function() {
            const container = d.querySelector('#offcanvas-container-clientes');
            if (container) {
                container.innerHTML = '';
            }
            clienteId = null;
        }, { once: true });

        console.log('[cliente.editar] Formulario de edición inicializado para cliente ID:', clienteId);
    }

    /**
     * Escuchar evento de inicialización desde el template
     */
    d.addEventListener('initClienteEditar', function(e) {
        console.log('[cliente.editar] Evento initClienteEditar recibido', e.detail);
        initFormularioEditar(e.detail);
    });

    // Exponer API pública (opcional)
    w.ClienteEditarModule = {
        init: initFormularioEditar
    };

})(window, document);
