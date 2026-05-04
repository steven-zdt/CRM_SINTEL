/**
 * Feature: Gestión de Contactos de Clientes v2.61
 * ⚠️ Feature-Sliced Architecture: Módulo para crear/editar contactos
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual: Event-based, sin try/catch genéricos
 * 
 * Dependencias globales requeridas:
 * - window.http (definido en lib/api.js) - HTTP wrapper
 * - window.SintelFeedback (definido en feedback.js) - Notificaciones
 */
(function(w, d) {
    'use strict';

    w.AppCliente = w.AppCliente || {};

    /**
     * Eliminar contacto del contenedor dinámico
     */
    function eliminarContactoDinamico(e) {
        const btn = e.target.closest('.btn-eliminar-contacto');
        if (!btn) return;

        const contactoItem = btn.closest('.contacto-item');
        if (contactoItem) {
            contactoItem.remove();
        }
    }

    /**
     * Recolectar datos del formulario de contacto
     * @returns {Object} Datos del contacto
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-contacto-cliente');
        if (!form) {
            console.error('[clientes.contactos] Formulario no encontrado');
            return null;
        }

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        const clienteInput = d.querySelector('#contacto-cliente-id');
        const clienteSelect = d.querySelector('#contacto-cliente-select');

        if (clienteSelect && clienteInput) {
            clienteInput.value = clienteSelect.value || clienteInput.value || '';
        }

        // Convertir checkboxes
        data.activo = d.querySelector('#contacto-activo')?.checked ?? false;
        data.is_principal = d.querySelector('#contacto-is_principal')?.checked ?? false;

        // Remover campos vacíos
        Object.keys(data).forEach(key => {
            if (data[key] === '' || data[key] === null) {
                delete data[key];
            }
        });

        return data;
    }

    /**
     * Guardar contacto (crear o actualizar)
     */
    async function guardarContacto() {
        const payload = recolectarDatosFormulario();
        if (!payload) {
            if (w.UIManager?.handleError) {
                w.UIManager.handleError({
                    status: 400,
                    data: {
                        detail: 'No se pudo recolectar los datos del formulario'
                    }
                }, 'Clientes');
            }
            return;
        }

        const contactoId = d.querySelector('#contacto-id')?.value;
        const btnGuardar = d.querySelector('#btn-guardar-contacto');

        // Deshabilitar botón
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        try {
            const url = contactoId
                ? `/api/v1/clientes/contactos/${contactoId}/`
                : '/api/v1/clientes/contactos/';
            
            const method = contactoId ? 'PATCH' : 'POST';
            
            const response = await w.http(method, url, payload);

            if (response.ok) {
                if (w.UIManager?.success) {
                    w.UIManager.success(
                        contactoId 
                            ? 'Contacto actualizado correctamente'
                            : 'Contacto agregado correctamente'
                    );
                }

                // Cerrar offcanvas
                const offcanvasEl = d.getElementById('offcanvas-contacto-cliente');
                if (offcanvasEl && w.bootstrap) {
                    const offcanvasInstance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
                    if (offcanvasInstance) {
                        offcanvasInstance.hide();
                    }
                }

                // Disparar evento para recargar tabla
                d.dispatchEvent(new CustomEvent('contactoGuardado'));
            } else {
                // Error
                const errorContainer = d.querySelector('#form-contacto-cliente-feedback');
                if (errorContainer && response.data) {
                    const errorFields = Object.keys(response.data).filter(k => k !== 'detail');
                    if (errorFields.length > 0) {
                        const errorList = errorFields.map(field => {
                            const msg = Array.isArray(response.data[field])
                                ? response.data[field].join(', ')
                                : response.data[field];
                            return `<li><strong>${field}:</strong> ${msg}</li>`;
                        }).join('');
                        errorContainer.innerHTML = `<ul class="mb-0">${errorList}</ul>`;
                    }
                    errorContainer.classList.remove('d-none');
                }

                if (w.UIManager?.handleError) {
                    w.UIManager.handleError(response, 'Clientes');
                }
            }
        } catch (error) {
            console.error('[clientes.contactos:guardar] Error', error);
            if (w.UIManager?.handleError) {
                w.UIManager.handleError({
                    status: 500,
                    data: {
                        detail: 'Error de conexion'
                    }
                }, 'Clientes');
            }
        } finally {
            // Restaurar botón
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = contactoId
                    ? '<i class="bi bi-save me-1"></i>Actualizar Contacto'
                    : '<i class="bi bi-save me-1"></i>Guardar Contacto';
            }
        }
    }

    /**
     * Inicializar formulario de contactos
     */
    async function initFormulario() {
        const offcanvasEl = d.querySelector('#offcanvas-contacto-cliente');
        if (!offcanvasEl) return;

        const clienteSelect = d.querySelector('#contacto-cliente-select');
        const clienteInput = d.querySelector('#contacto-cliente-id');

        if (clienteSelect) {
            clienteSelect.removeAttribute('name');
            clienteSelect.addEventListener('change', function() {
                if (clienteInput) {
                    clienteInput.value = clienteSelect.value || '';
                }
            });
        }
        
        // ⚠️ Poblar select si es creación global
        const selectContainer = d.querySelector('#contacto-cliente-select-container');
        if (selectContainer && selectContainer.style.display !== 'none') {
            if (clienteSelect) {
                try {
                    const response = await w.clientesAPI.list({ page_size: 1000 });
                    if (response.ok) {
                        const clientes = response.data.results || response.data;
                        clienteSelect.innerHTML = '<option value="">Seleccione un cliente...</option>' + 
                            clientes.map(c => `<option value="${c.id}">${c.razon_social}</option>`).join('');

                        if (clienteInput?.value) {
                            clienteSelect.value = clienteInput.value;
                        }
                    }
                } catch (e) {
                    console.error('[clientes.contactos:init] Error cargando lista de clientes', e);
                    if (w.UIManager?.handleError) {
                        w.UIManager.handleError({
                            status: 500,
                            data: {
                                detail: 'Error al cargar la lista de clientes'
                            }
                        }, 'Clientes');
                    }
                }
            }
        }

        // Botón guardar
        const btnGuardar = d.querySelector('#btn-guardar-contacto');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                await guardarContacto();
            });
        }

        // Botón cancelar
        const btnCancelar = d.querySelector('#btn-cancelar-contacto');
        if (btnCancelar) {
            btnCancelar.addEventListener('click', function(e) {
                e.preventDefault();
                if (offcanvasEl && w.bootstrap) {
                    const offcanvasInstance = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
                    if (offcanvasInstance) {
                        offcanvasInstance.hide();
                    }
                }
            });
        }

        // Botones para agregar/eliminar contactos dinámicos (si están presentes)
        const btnAgregarContacto = d.querySelector('#btn-agregar-contacto');
        if (btnAgregarContacto) {
            btnAgregarContacto.addEventListener('click', () => {
                w.ClienteUtils.agregarContacto('#contenedor-contactos');
            });
        }

        const contenedorContactos = d.querySelector('#contenedor-contactos');
        if (contenedorContactos) {
            contenedorContactos.addEventListener('click', w.ClienteUtils.eliminarContacto);
        }

        // Formulario submit
        const form = d.querySelector('#form-contacto-cliente');
        if (form) {
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                await guardarContacto();
            });
        }

        console.log('[clientes.contactos] Formulario de contactos inicializado');
    }

    /**
     * Escuchar evento cuando offcanvas se muestra
     */
    d.addEventListener('shown.bs.offcanvas', function(e) {
        if (e.target?.id === 'offcanvas-contacto-cliente') {
            initFormulario();
        }
    });

    // Inicialización en DOMContentLoaded (por si ya existe el offcanvas)
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', function() {
            if (d.querySelector('#offcanvas-contacto-cliente')) {
                initFormulario();
            }
        });
    } else if (d.querySelector('#offcanvas-contacto-cliente')) {
        initFormulario();
    }

    // Exponer API pública
    w.ContactosModule = {
        guardar: guardarContacto,
        inicializar: initFormulario
    };

    w.AppCliente.contactos = w.ContactosModule;

})(window, document);
