/**
 * Feature: Edición de Clientes v2.61 (Refactored)
 * ⚠️ Feature-Sliced Architecture: Modulo para edición con contactos
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - w.clientesAPI (definido en clientes.api.js) - Capa de Datos
 * - w.SintelFeedback (definido en feedback.js) - Sistema de notificaciones
 */
(function(w, d) {
    'use strict';

    // No functions here anymore, using w.ClienteUtils
    
    /**
     * Recolectar datos del formulario
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-cliente');
        if (!form) {
            console.error('[clientes.editor] Formulario no encontrado');
            return null;
        }

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Convertir checkbox activo
        const activoCheckbox = d.querySelector('#cliente-activo');
        data.activo = activoCheckbox?.checked ?? false;
        
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
     * Guardar cliente (crear o actualizar)
     */
    async function guardarCliente() {
        const payload = recolectarDatosFormulario();
        if (!payload) {
            if (w.SintelFeedback) {
                w.SintelFeedback.error('No se pudo recolectar los datos del formulario');
            }
            return;
        }

        const clienteId = d.querySelector('#cliente-id')?.value;
        const offcanvasEl = d.querySelector('#offcanvas-cliente');
        
        // Deshabilitar botón mientras se guarda
        const btnGuardar = d.querySelector('#btn-guardar-cliente');
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        // ⚠️ Aislamiento Gradual: Llamar a la API
        const response = clienteId 
            ? await w.clientesAPI.update(clienteId, payload)
            : await w.clientesAPI.create(payload);
        
        if (response && response.ok) {
            // Éxito
            if (w.SintelFeedback) {
                w.SintelFeedback.success(clienteId ? 'Cliente actualizado exitosamente' : 'Cliente creado exitosamente');
            }

            // Cerrar offcanvas
            if (offcanvasEl && window.bootstrap) {
                const offcanvasInstance = bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (offcanvasInstance) {
                    offcanvasInstance.hide();
                }
            }

            // Disparar evento para recargar la tabla
            d.dispatchEvent(new CustomEvent('clienteGuardado'));
        } else {
            // Error (manejado por UIManager)
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = clienteId 
                    ? '<i class="bi bi-save me-1"></i>Actualizar'
                    : '<i class="bi bi-save me-1"></i>Guardar';
            }
            
            // Mostrar error
            if (response?.status === 400 && response?.data) {
                const errorContainer = offcanvasEl?.querySelector('#form-cliente-feedback');
                if (errorContainer) {
                    const errorFields = Object.keys(response.data).filter(k => k !== 'detail');
                    if (errorFields.length > 0) {
                        const errorList = errorFields.map(field => {
                            const msg = Array.isArray(response.data[field]) 
                                ? response.data[field].join(', ')
                                : response.data[field];
                            return `<li><strong>${field}:</strong> ${msg}</li>`;
                        }).join('');
                        errorContainer.innerHTML = `<ul class="mb-0">${errorList}</ul>`;
                    } else if (response.data.detail) {
                        errorContainer.textContent = response.data.detail;
                    }
                    errorContainer.classList.remove('d-none');
                }
            }
        }
    }

    /**
     * Inicializar eventos del formulario
     */
    function initFormulario() {
        const offcanvasEl = d.querySelector('#offcanvas-cliente');
        if (!offcanvasEl) return;

        // Botón agregar contacto
        const btnAgregarContacto = d.querySelector('#btn-agregar-contacto');
        if (btnAgregarContacto) {
            btnAgregarContacto.addEventListener('click', () => {
                w.ClienteUtils.agregarContacto('#contenedor-contactos');
            });
        }

        // Event delegation para eliminar contactos
        const contenedorContactos = d.querySelector('#contenedor-contactos');
        if (contenedorContactos) {
            contenedorContactos.addEventListener('click', w.ClienteUtils.eliminarContacto);
        }

        // Botón guardar
        const btnGuardar = d.querySelector('#btn-guardar-cliente');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                await guardarCliente();
            });
        }

        // Formulario submit
        const form = d.querySelector('#form-cliente');
        if (form) {
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                await guardarCliente();
            });
        }

        console.log('[clientes.editor] Formulario inicializado');
    }

    /**
     * Escuchar evento cuando el offcanvas se inyecta en el DOM
     */
    d.addEventListener('shown.bs.offcanvas', function(e) {
        if (e.target?.id === 'offcanvas-cliente') {
            initFormulario();
        }
    });

    // Inicialización en DOMContentLoaded (por si ya existe el offcanvas)
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', function() {
            if (d.querySelector('#offcanvas-cliente')) {
                initFormulario();
            }
        });
    } else if (d.querySelector('#offcanvas-cliente')) {
        initFormulario();
    }

    // Exponer API pública
    w.ClientesEditorModule = {
        guardar: guardarCliente
    };

})(window, document);
