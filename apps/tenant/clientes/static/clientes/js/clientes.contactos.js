/**
 * Feature: Gestión de Contactos de Clientes v2.61
 * ⚠️ Feature-Sliced Architecture: Módulo para crear/editar contactos
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual: Event-based, sin try/catch genéricos
 * 
 * Dependencias globales requeridas:
 * - Sintel.Core.Http (F32.7, core-http.js) - HTTP wrapper
 * - window.SintelFeedback (definido en feedback.js) - Notificaciones
 */
(function(w, d) {
    'use strict';

    w.AppCliente = w.AppCliente || {};

    // ============================================================
    // DOM SELECTORS (SSoT)
    // ============================================================
    const DOM = {
        offcanvas:          '#offcanvas-contacto-cliente',
        form:               '#form-contacto-cliente',
        btnGuardar:         '#btn-guardar-contacto',
        btnCancelar:        '#btn-cancelar-contacto',
        feedback:           '#form-contacto-cliente-feedback',
        contactoId:         '#contacto-id',
        
        // Relación con cliente
        clienteSelect:      '#contacto-cliente-select',
        clienteInput:       '#contacto-cliente-id',
        selectContainer:    '#contacto-cliente-select-container',
        
        // Campos específicos
        activo:             '#contacto-activo',
        is_principal:       '#contacto-is_principal',
        
        // Utilidades dinámicas
        contenedorContactos: '#contenedor-contactos',
        btnAgregarContacto:  '#btn-agregar-contacto'
    };

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
        const form = d.querySelector(DOM.form);
        if (!form) {
            console.error('[clientes.contactos] Formulario no encontrado');
            return null;
        }

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        const clienteInput = d.querySelector(DOM.clienteInput);
        const clienteSelect = d.querySelector(DOM.clienteSelect);

        if (clienteSelect && clienteInput) {
            clienteInput.value = clienteSelect.value || clienteInput.value || '';
        }

        // Convertir checkboxes
        data.activo = d.querySelector(DOM.activo)?.checked ?? false;
        data.is_principal = d.querySelector(DOM.is_principal)?.checked ?? false;

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

        const contactoId = d.querySelector(DOM.contactoId)?.value;
        const btnGuardar = d.querySelector(DOM.btnGuardar);

        // Deshabilitar botón
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        try {
            // T-9: delega a la SSoT de endpoints (clientes.api.js).
            const response = contactoId
                ? await w.contactosAPI.update(contactoId, payload)
                : await w.contactosAPI.create(payload);

            if (response.ok) {
                if (w.UIManager?.success) {
                    w.UIManager.success(
                        contactoId 
                            ? 'Contacto actualizado correctamente'
                            : 'Contacto agregado correctamente'
                    );
                }

                // ⚠️ v2.62: Cerrar offcanvas usando el orquestador central
                if (w.UIManager?.handleOffcanvas) {
                    w.UIManager.handleOffcanvas(DOM.offcanvas, 'hide');
                }

                // Disparar evento para recargar tabla
                d.dispatchEvent(new CustomEvent('contactoGuardado'));
            } else {
                // Error
                const errorContainer = d.querySelector(DOM.feedback);
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
        const offcanvasEl = d.querySelector(DOM.offcanvas);
        if (!offcanvasEl) return;

        const clienteSelect = d.querySelector(DOM.clienteSelect);
        const clienteInput = d.querySelector(DOM.clienteInput);

        if (clienteSelect) {
            clienteSelect.removeAttribute('name');
            clienteSelect.addEventListener('change', function() {
                if (clienteInput) {
                    clienteInput.value = clienteSelect.value || '';
                }
            });
        }
        
        // ⚠️ Poblar select si es creación global
        const selectContainer = d.querySelector(DOM.selectContainer);
        if (selectContainer && selectContainer.style.display !== 'none') {
            if (clienteSelect) {
                try {
                    const response = await w.clientesAPI.list({ activo: true, page_size: 1000 });
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

        // ⚠️ v2.62: Delegación de eventos para botones del formulario (evita duplicidad)
        // Se adjuntan al documento una sola vez o se limpian previo a init
        const setupEventListeners = () => {
            const form = d.querySelector(DOM.form);
            if (!form) return;

            // Limpiar listeners previos si el elemento persiste (fallback)
            const btnGuardar = d.querySelector(DOM.btnGuardar);
            if (btnGuardar) {
                const newBtn = btnGuardar.cloneNode(true);
                btnGuardar.parentNode.replaceChild(newBtn, btnGuardar);
                newBtn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    await guardarContacto();
                });
            }

            const btnCancelar = d.querySelector(DOM.btnCancelar);
            if (btnCancelar) {
                btnCancelar.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (w.UIManager?.handleOffcanvas) {
                        w.UIManager.handleOffcanvas(DOM.offcanvas, 'hide');
                    }
                });
            }

            form.onsubmit = async (e) => {
                e.preventDefault();
                await guardarContacto();
            };
        };

        setupEventListeners();

        // Botones para agregar/eliminar contactos dinámicos (si están presentes)
        const btnAgregarContacto = d.querySelector(DOM.btnAgregarContacto);
        if (btnAgregarContacto) {
            btnAgregarContacto.addEventListener('click', () => {
                w.ClienteUtils.agregarContacto(DOM.contenedorContactos);
            });
        }

        const contenedorContactos = d.querySelector(DOM.contenedorContactos);
        if (contenedorContactos) {
            contenedorContactos.addEventListener('click', w.ClienteUtils.eliminarContacto);
        }

        // Formulario submit
        const form = d.querySelector(DOM.form);
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
        if (e.target?.id === DOM.offcanvas.substring(1)) {
            initFormulario();
        }
    });

    // Inicialización en DOMContentLoaded (por si ya existe el offcanvas)
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', function() {
            if (d.querySelector(DOM.offcanvas)) {
                initFormulario();
            }
        });
    } else if (d.querySelector(DOM.offcanvas)) {
        initFormulario();
    }

    // Exponer API pública
    w.ContactosModule = {
        guardar: guardarContacto,
        inicializar: initFormulario
    };

    w.AppCliente.contactos = w.ContactosModule;

})(window, document);
