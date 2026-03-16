/**
 * Feature: Editor y Contactos - Clientes v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - w.clientesAPI (definido en clientes.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 */
(function(w, d) {
    'use strict';

    /**
     * Recolectar datos del formulario del Offcanvas
     * @returns {Object} Datos del cliente y array de contactos
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
        data.activo = activoCheckbox ? activoCheckbox.checked : true;
        
        // Remover campos vacíos
        Object.keys(data).forEach(key => {
            if (data[key] === '' || data[key] === null) {
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
                activo: item.querySelector('.contacto-activo')?.checked !== false,
                is_principal: item.querySelector('.contacto-principal')?.checked === true
            };
            
            // Solo agregar si tiene nombre y email (requeridos)
            if (contacto.nombre_completo && contacto.email) {
                contactos.push(contacto);
            }
        });

        // Agregar contactos al payload si hay alguno
        if (contactos.length > 0) {
            data.contactos = contactos;
        }

        return data;
    }

    /**
     * Guardar cliente
     * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
     * ⚠️ v2.60: Maneja Offcanvas y contactos dinámicos
     */
    async function guardarCliente() {
        const data = recolectarDatosFormulario();
        if (!data) {
            return;
        }

        const id = d.querySelector('#cliente-id')?.value;
        const offcanvasEl = d.querySelector('#offcanvas-cliente');
        
        // ⚠️ Error Boundary v2.60: Guardar estado original del botón
        const btnGuardar = d.querySelector('#btn-guardar-cliente');
        const btnOriginalText = btnGuardar?.innerHTML || '';
        const btnOriginalDisabled = btnGuardar?.disabled || false;
        
        // ⚠️ Error Boundary v2.60: Mostrar estado de loading
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        }

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        let res;
        if (id) {
            res = await w.clientesAPI.update(id, data);
        } else {
            res = await w.clientesAPI.create(data);
        }
        
        // ⚠️ Error Boundary v2.60: Restaurar estado del botón ANTES de procesar respuesta
        if (btnGuardar) {
            btnGuardar.disabled = btnOriginalDisabled;
            btnGuardar.innerHTML = btnOriginalText;
        }
        
        // ⚠️ DEBUG: Log detallado para diagnóstico de error 400
        if (!res.ok) {
            console.error('[clientes.editor] ❌ Error al guardar cliente');
            console.error('[clientes.editor] Status:', res.status);
            console.error('[clientes.editor] Payload enviado:', JSON.stringify(data, null, 2));
            console.error('[clientes.editor] Respuesta del servidor:', JSON.stringify(res.data, null, 2));
        }
        
        // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
        if (!res.ok) {
            // ⚠️ Error Boundary v2.60: Para errores 400 (validación), usar handleError y mantener offcanvas abierto
            if (res.status === 400) {
                // ⚠️ Error Boundary: Usar handleError para mostrar error en offcanvas y mantener abierto
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(res, '[clientes.editor]', {
                        modalSelector: '#offcanvas-cliente',
                        errorContainerSelector: '#form-cliente-feedback'
                    });
                } else {
                    console.warn('[clientes.editor] UIManager.handleError no está disponible, usando fallback');
                    // Fallback: mostrar error manualmente si UIManager no está disponible
                    const errorContainer = offcanvasEl?.querySelector('#form-cliente-feedback');
                    if (errorContainer) {
                        let errorMessage = 'Error de validación';
                        let errorHTML = '';
                        
                        if (res.data) {
                            // ⚠️ v2.60: Procesar errores de validación de DRF
                            // DRF puede retornar errores en formato: { "campo": ["mensaje1", "mensaje2"], "detail_code": "invalid" }
                            const errorData = res.data;
                            
                            // Ignorar campos técnicos como "detail_code"
                            const errorFields = Object.keys(errorData).filter(key => key !== 'detail_code' && key !== 'detail');
                            
                            if (errorFields.length > 0) {
                                // Hay errores de campos específicos
                                const errorList = errorFields.map(field => {
                                    const fieldErrors = Array.isArray(errorData[field]) 
                                        ? errorData[field]
                                        : [String(errorData[field])];
                                    
                                    // Traducir nombre del campo a español si es necesario
                                    const fieldLabels = {
                                        'numero_documento': 'Número de Documento',
                                        'razon_social': 'Razón Social',
                                        'email': 'Email',
                                        'telefono': 'Teléfono',
                                        'direccion': 'Dirección',
                                        'ciudad': 'Ciudad',
                                        'tipo_persona': 'Tipo de Persona',
                                        'tipo_documento': 'Tipo de Documento',
                                        'regimen_tributario': 'Régimen Tributario'
                                    };
                                    
                                    const fieldLabel = fieldLabels[field] || field;
                                    return `<strong>${fieldLabel}:</strong> ${fieldErrors.join(', ')}`;
                                });
                                
                                errorHTML = `<div><i class="bi bi-exclamation-triangle me-2"></i><strong>Errores de validación:</strong><ul class="mb-0 mt-2">${errorList.map(err => `<li>${err}</li>`).join('')}</ul></div>`;
                                errorMessage = errorFields.map(field => {
                                    const fieldErrors = Array.isArray(errorData[field]) 
                                        ? errorData[field].join(', ')
                                        : String(errorData[field]);
                                    const fieldLabels = {
                                        'numero_documento': 'Número de Documento',
                                        'razon_social': 'Razón Social',
                                        'email': 'Email',
                                        'telefono': 'Teléfono',
                                        'direccion': 'Dirección',
                                        'ciudad': 'Ciudad',
                                        'tipo_persona': 'Tipo de Persona',
                                        'tipo_documento': 'Tipo de Documento',
                                        'regimen_tributario': 'Régimen Tributario'
                                    };
                                    const fieldLabel = fieldLabels[field] || field;
                                    return `${fieldLabel}: ${fieldErrors}`;
                                }).join(' | ');
                            } else if (errorData.detail) {
                                // Error general en "detail"
                                if (typeof errorData.detail === 'string') {
                                    errorMessage = errorData.detail;
                                    errorHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${errorData.detail}`;
                                } else if (Array.isArray(errorData.detail)) {
                                    errorMessage = errorData.detail.join(', ');
                                    errorHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${errorData.detail.join(', ')}`;
                                }
                            }
                        }
                        
                        errorContainer.className = 'alert alert-danger';
                        if (errorHTML) {
                            errorContainer.innerHTML = errorHTML;
                        } else {
                            errorContainer.textContent = errorMessage;
                        }
                        errorContainer.classList.remove('d-none');
                        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        
                        // ⚠️ v2.60: También mostrar notificación con SintelFeedback si está disponible
                        if (w.SintelFeedback) {
                            w.SintelFeedback.error(errorMessage);
                        }
                    } else {
                        // Si no hay contenedor, usar SintelFeedback como último recurso
                        console.error('[clientes.editor] Contenedor de errores #form-cliente-feedback no encontrado');
                        if (w.SintelFeedback) {
                            const errorMsg = res.data?.numero_documento?.[0] || res.data?.detail || 'Error al guardar el cliente';
                            w.SintelFeedback.error(errorMsg);
                        }
                    }
                }
                
                // ⚠️ Error Boundary: Offcanvas permanece abierto para que el usuario corrija los datos
                return;
            }
            
            // ⚠️ Error Boundary: Para otros errores (500, 403, etc.), usar handleError
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError(res, '[clientes.editor]', {
                    modalSelector: '#offcanvas-cliente',
                    errorContainerSelector: '#form-cliente-feedback'
                });
            }
            return;
        }

        // Éxito: cerrar offcanvas con Bootstrap API
        if (offcanvasEl) {
            const offcanvasInstance = bootstrap.Offcanvas.getInstance(offcanvasEl);
            if (offcanvasInstance) {
                offcanvasInstance.hide();
            }
        }
        
        // Mostrar notificación de éxito
        if (w.SintelFeedback) {
            w.SintelFeedback.success(id ? 'Cliente actualizado exitosamente' : 'Cliente creado exitosamente');
        }
        
        // ⚠️ Disparar evento personalizado para que el listado recargue automáticamente
        d.dispatchEvent(new Event('clienteGuardado'));
    }

    /**
     * Abrir Offcanvas para crear nuevo cliente
     */
    function abrirOffcanvasCrear() {
        // ⚠️ v2.60: Cargar offcanvas vacío mediante HTMX (usando contenedor de list.html)
        const container = d.querySelector('#offcanvas-container-clientes');
        if (container && typeof htmx !== 'undefined') {
            htmx.ajax('GET', '/api/v1/clientes/offcanvas/', {
                target: '#offcanvas-container-clientes',
                swap: 'innerHTML'
            }).then((response) => {
                // ⚠️ Safeguard: Solo mostrar offcanvas si la respuesta fue exitosa (200) y el elemento existe
                if (response && response.status === 200) {
                    const offcanvasEl = d.querySelector('#offcanvas-cliente');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                        offcanvas.show();
                    } else {
                        console.warn('[clientes.editor] Offcanvas no encontrado en el DOM o Bootstrap no disponible');
                    }
                } else {
                    console.error('[clientes.editor] Respuesta del servidor no exitosa:', response?.status);
                    if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                        w.UIManager.notifyError({ status: response?.status || 500, data: { detail: 'Error al cargar formulario de creación' } }, '[clientes.editor]');
                    }
                }
            }).catch(err => {
                console.error('[clientes.editor] Error al cargar offcanvas de creación:', err);
                if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                    w.UIManager.notifyError({ status: 500, data: { detail: 'Error al cargar formulario de creación' } }, '[clientes.editor]');
                }
            });
        } else {
            console.error('[clientes.editor] Contenedor de offcanvas o HTMX no disponible');
        }
    }

    /**
     * Abrir Offcanvas para editar cliente
     * ⚠️ v2.60: La vista Django maneja la carga de datos del cliente
     */
    function abrirOffcanvasEditar(id) {
        // ⚠️ v2.60: Cargar offcanvas con datos mediante HTMX (usando contenedor de list.html)
        const container = d.querySelector('#offcanvas-container-clientes');
        if (container && typeof htmx !== 'undefined') {
            htmx.ajax('GET', `/api/v1/clientes/offcanvas/?id=${id}`, {
                target: '#offcanvas-container-clientes',
                swap: 'innerHTML'
            }).then((response) => {
                // ⚠️ Safeguard: Solo mostrar offcanvas si la respuesta fue exitosa (200) y el elemento existe
                if (response && response.status === 200) {
                    const offcanvasEl = d.querySelector('#offcanvas-cliente');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                        offcanvas.show();
                    } else {
                        console.warn('[clientes.editor] Offcanvas no encontrado en el DOM o Bootstrap no disponible');
                    }
                } else {
                    console.error('[clientes.editor] Respuesta del servidor no exitosa:', response?.status);
                    if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                        w.UIManager.notifyError({ status: response?.status || 500, data: { detail: 'Error al cargar formulario de edición' } }, '[clientes.editor]');
                    }
                }
            }).catch(err => {
                console.error('[clientes.editor] Error al cargar offcanvas:', err);
                if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                    w.UIManager.notifyError({ status: 500, data: { detail: 'Error al cargar formulario de edición' } }, '[clientes.editor]');
                }
            });
        } else {
            console.error('[clientes.editor] Contenedor de offcanvas o HTMX no disponible');
        }
    }

    // Inicializar eventos del editor
    function initEditorEvents() {
        // Submit formulario - ⚠️ CRÍTICO: Prevenir envío tradicional
        const form = d.querySelector('#form-cliente');
        if (form) {
            // Prevenir envío tradicional (GET)
            form.setAttribute('method', 'POST');
            form.setAttribute('onsubmit', 'return false;');
            
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                await guardarCliente();
            });
        }
        
        // También interceptar el botón de submit directamente (event delegation para HTMX)
        d.addEventListener('click', function(e) {
            if (e.target && e.target.id === 'btn-guardar-cliente') {
                e.preventDefault();
                e.stopPropagation();
                guardarCliente();
            }
        });

        // Escuchar eventos de edición y eliminación desde el listado
        d.addEventListener('clienteEditar', function(e) {
            if (e.detail && e.detail.id) {
                abrirOffcanvasEditar(e.detail.id);
            }
        });

        // ⚠️ v2.61: Implementación completa de eliminación con confirmación
        d.addEventListener('clienteEliminar', function(e) {
            if (e.detail && e.detail.id) {
                const clienteId = e.detail.id;
                
                // Confirmación con SweetAlert2
                if (w.Swal) {
                    w.Swal.fire({
                        title: '¿Eliminar Cliente?',
                        text: "Esta acción no se puede deshacer. El cliente debe estar inactivo para poder eliminarlo.",
                        icon: 'warning',
                        showCancelButton: true,
                        confirmButtonColor: '#d33',
                        cancelButtonColor: '#3085d6',
                        confirmButtonText: 'Sí, eliminar',
                        cancelButtonText: 'Cancelar'
                    }).then(async (result) => {
                        if (result.isConfirmed) {
                            await eliminarCliente(clienteId);
                        }
                    });
                } else {
                    // Fallback: confirmación simple
                    if (confirm('¿Está seguro que desea eliminar este cliente?')) {
                        eliminarCliente(clienteId);
                    }
                }
            }
        });
        
        /**
         * Eliminar un cliente
         * @param {number} clienteId - ID del cliente a eliminar
         */
        async function eliminarCliente(clienteId) {
            try {
                // ⚠️ Llamar a la API para eliminar
                const response = await w.clientesAPI.delete(clienteId);
                
                if (response.ok || response.status === 204) {
                    // Éxito
                    if (w.SintelFeedback) {
                        w.SintelFeedback.success('Cliente eliminado exitosamente');
                    }
                    
                    // Disparar evento para recargar la tabla
                    d.dispatchEvent(new CustomEvent('clienteEliminado'));
                } else {
                    // Error específico del backend
                    let errorMessage = 'Error al eliminar el cliente';
                    
                    if (response.status === 400 && response.data) {
                        // Error de validación (cliente activo)
                        if (response.data.activo || response.data.detail) {
                            errorMessage = 'No se puede eliminar un cliente activo. Cámbielo a "Inactivo" en el formulario de edición antes de intentar borrarlo.';
                        }
                    } else if (response.status === 404) {
                        errorMessage = 'Cliente no encontrado';
                    }
                    
                    if (w.SintelFeedback) {
                        w.SintelFeedback.error(errorMessage);
                    }
                }
            } catch (error) {
                console.error('[clientes.editor] Error eliminando cliente:', error);
                if (w.SintelFeedback) {
                    w.SintelFeedback.error('Error de conexión al eliminar el cliente');
                }
            }
        }
    }

    // Inicialización
    function init() {
        // Verificar dependencias
        if (!w.clientesAPI) {
            console.error('[clientes.editor] ❌ CRÍTICO: window.clientesAPI no está disponible.');
            return;
        }
        
        initEditorEvents();
    }

    // Auto-inicialización
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exponer API pública
    w.ClientesEditorModule = {
        guardar: guardarCliente,
        abrirCrear: abrirOffcanvasCrear,
        abrirEditar: abrirOffcanvasEditar
    };

    // Mantener compatibilidad con API antigua
    w.ClientesModule = w.ClientesModule || {};
    w.ClientesModule.abrirModalCrear = abrirOffcanvasCrear;
    w.ClientesModule.editar = abrirOffcanvasEditar;

})(window, document);
