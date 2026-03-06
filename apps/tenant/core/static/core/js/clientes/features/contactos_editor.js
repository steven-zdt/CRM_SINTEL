/**
 * Feature: Editor de Contactos - Clientes v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica aislada para CRUD de contactos
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual v2.60: Error Boundary Pattern con UIManager
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en lib/api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Notificaciones
 */
(function(w, d) {
    'use strict';

    const API_BASE = '/api/v1/clientes/contactos';
    let currentClienteId = null;

    /**
     * Renderizar lista de contactos en el contenedor
     * @param {Array} contactos - Array de contactos
     */
    function renderizarListaContactos(contactos) {
        const container = d.querySelector('#lista-contactos-cliente');
        if (!container) {
            console.warn('[contactos.editor] Contenedor #lista-contactos-cliente no encontrado');
            return;
        }

        if (!contactos || contactos.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info mb-0">
                    <i class="bi bi-info-circle me-2"></i>No hay contactos registrados para este cliente.
                </div>
            `;
            return;
        }

        // Renderizar tarjetas de contactos
        container.innerHTML = contactos.map(contacto => {
            const badges = [];
            if (contacto.is_principal) {
                badges.push('<span class="badge bg-primary ms-2">Principal</span>');
            }
            if (!contacto.activo) {
                badges.push('<span class="badge bg-secondary ms-2">Inactivo</span>');
            }

            return `
                <div class="card mb-2 contacto-item-card" data-contacto-id="${contacto.id}">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">
                                    ${contacto.nombre_completo || 'Sin nombre'}
                                    ${badges.join('')}
                                </h6>
                                ${contacto.cargo ? `<p class="text-muted small mb-1"><i class="bi bi-briefcase me-1"></i>${contacto.cargo}</p>` : ''}
                                <p class="text-muted small mb-1"><i class="bi bi-envelope me-1"></i>${contacto.email || 'Sin email'}</p>
                                ${contacto.telefono ? `<p class="text-muted small mb-0"><i class="bi bi-telephone me-1"></i>${contacto.telefono}</p>` : ''}
                            </div>
                            <div class="btn-group btn-group-sm">
                                <button type="button" class="btn btn-outline-primary btn-editar-contacto" 
                                        data-contacto-id="${contacto.id}" title="Editar Contacto">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button type="button" class="btn btn-outline-danger btn-eliminar-contacto" 
                                        data-contacto-id="${contacto.id}" title="Eliminar Contacto">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Cargar y renderizar contactos de un cliente
     * @param {number} clienteId - ID del cliente
     */
    async function cargarContactos(clienteId) {
        if (!clienteId) {
            console.error('[contactos.editor] clienteId es requerido');
            return;
        }

        try {
            const res = await w.http('GET', `${API_BASE}/?cliente=${clienteId}`);
            
            if (res.ok && res.data) {
                // Si la respuesta es paginada, extraer results
                const contactos = Array.isArray(res.data) ? res.data : (res.data.results || []);
                renderizarListaContactos(contactos);
            } else {
                console.error('[contactos.editor] Error al cargar contactos:', res.status, res.data);
                renderizarListaContactos([]);
            }
        } catch (error) {
            console.error('[contactos.editor] Error al cargar contactos:', error);
            renderizarListaContactos([]);
        }
    }

    /**
     * Limpiar formulario de contacto
     */
    function limpiarFormulario() {
        const form = d.querySelector('#form-contacto-cliente');
        if (!form) return;

        form.reset();
        // Limpiar campo oculto de ID
        const contactoIdInput = d.querySelector('#contacto-id');
        if (contactoIdInput) {
            contactoIdInput.value = '';
        }
        // Restaurar checkbox activo a checked
        const activoCheckbox = d.querySelector('#contacto-activo');
        if (activoCheckbox) {
            activoCheckbox.checked = true;
        }
        // ⚠️ v2.60: Limpiar select de cliente si existe
        const clienteSelect = d.querySelector('#contacto-cliente-select');
        if (clienteSelect) {
            clienteSelect.value = '';
        }
    }

    /**
     * Recolectar datos del formulario de contacto
     * @returns {Object} Datos del contacto
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-contacto-cliente');
        if (!form) {
            console.error('[contactos.editor] Formulario no encontrado');
            return null;
        }

        const formData = new FormData(form);
        const data = {
            nombre_completo: formData.get('nombre_completo') || '',
            cargo: formData.get('cargo') || '',
            email: formData.get('email') || '',
            telefono: formData.get('telefono') || '',
            activo: d.querySelector('#contacto-activo')?.checked !== false,
            is_principal: d.querySelector('#contacto-is_principal')?.checked === true
        };

        // Remover campos vacíos (excepto activo que siempre debe estar)
        Object.keys(data).forEach(key => {
            if (key !== 'activo' && (data[key] === '' || data[key] === null)) {
                delete data[key];
            }
        });

        return data;
    }

    /**
     * Guardar contacto (crear o actualizar)
     * @param {Event} e - Evento del formulario
     * @param {number} clienteId - ID del cliente
     */
    async function guardarContacto(e, clienteId) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        if (!clienteId) {
            console.error('[contactos.editor] clienteId es requerido');
            return;
        }

        const form = d.querySelector('#form-contacto-cliente');
        if (!form) {
            console.error('[contactos.editor] Formulario no encontrado');
            return;
        }

        // Validar formulario HTML5
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const data = recolectarDatosFormulario();
        if (!data) {
            return;
        }

        // Inyectar cliente_id
        data.cliente = clienteId;

        // ⚠️ Error Boundary v2.60: Guardar estado original del botón
        const btnGuardar = d.querySelector('#btn-guardar-contacto');
        const btnOriginalText = btnGuardar?.innerHTML || '';
        const btnOriginalDisabled = btnGuardar?.disabled || false;

        // ⚠️ Error Boundary v2.60: Mostrar estado de loading
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        }

        // Obtener ID del contacto si está en modo edición
        const contactoId = d.querySelector('#contacto-id')?.value;

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        let res;
        if (contactoId) {
            // Actualizar contacto existente
            res = await w.http('PATCH', `${API_BASE}/${contactoId}/`, data);
        } else {
            // Crear nuevo contacto
            res = await w.http('POST', `${API_BASE}/`, data);
        }

        // ⚠️ Error Boundary v2.60: Restaurar estado del botón ANTES de procesar respuesta
        if (btnGuardar) {
            btnGuardar.disabled = btnOriginalDisabled;
            btnGuardar.innerHTML = btnOriginalText;
        }

        // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
        if (!res.ok) {
            // ⚠️ Error Boundary v2.60: Para errores 400 (validación), usar handleError y mantener offcanvas abierto
            if (res.status === 400) {
                // ⚠️ Error Boundary: Usar handleError para mostrar error en offcanvas y mantener abierto
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(res, '[contactos.editor]', {
                        modalSelector: '#offcanvas-contactos',
                        feedbackSelector: '#form-contacto-feedback'
                    });
                } else {
                    // Fallback: mostrar error básico
                    const feedbackEl = d.querySelector('#form-contacto-feedback');
                    if (feedbackEl) {
                        feedbackEl.classList.remove('d-none');
                        feedbackEl.textContent = res.data?.detail || 'Error al guardar el contacto';
                    }
                }
            } else {
                // Otros errores (500, etc.)
                if (w.SintelFeedback) {
                    w.SintelFeedback.error('Error al guardar el contacto. Por favor, intente nuevamente.');
                }
            }
            return;
        }

        // ⚠️ Éxito: Limpiar formulario, mostrar feedback y recargar lista
        limpiarFormulario();
        
        if (w.SintelFeedback) {
            w.SintelFeedback.success(contactoId ? 'Contacto actualizado correctamente' : 'Contacto creado correctamente');
        }

        // Ocultar contenedor de errores si estaba visible
        const feedbackEl = d.querySelector('#form-contacto-feedback');
        if (feedbackEl) {
            feedbackEl.classList.add('d-none');
            feedbackEl.textContent = '';
        }

        // Recargar lista de contactos (si estamos en el gestor de un cliente específico)
        if (currentClienteId) {
            await cargarContactos(currentClienteId);
        }

        // Disparar evento para recargar el grid global
        d.dispatchEvent(new CustomEvent('contactoGuardado', { detail: { id: res.data?.id || contactoId } }));
    }

    /**
     * Editar contacto (cargar datos en el formulario)
     * @param {number} contactoId - ID del contacto
     */
    async function editarContacto(contactoId) {
        if (!contactoId) {
            console.error('[contactos.editor] contactoId es requerido');
            return;
        }

        try {
            const res = await w.http('GET', `${API_BASE}/${contactoId}/`);
            
            if (res.ok && res.data) {
                const contacto = res.data;
                
                // Llenar formulario con datos del contacto
                const nombreInput = d.querySelector('#contacto-nombre_completo');
                if (nombreInput) nombreInput.value = contacto.nombre_completo || '';
                
                const cargoInput = d.querySelector('#contacto-cargo');
                if (cargoInput) cargoInput.value = contacto.cargo || '';
                
                const emailInput = d.querySelector('#contacto-email');
                if (emailInput) emailInput.value = contacto.email || '';
                
                const telefonoInput = d.querySelector('#contacto-telefono');
                if (telefonoInput) telefonoInput.value = contacto.telefono || '';
                
                const activoCheckbox = d.querySelector('#contacto-activo');
                if (activoCheckbox) activoCheckbox.checked = contacto.activo !== false;
                
                const principalCheckbox = d.querySelector('#contacto-is_principal');
                if (principalCheckbox) principalCheckbox.checked = contacto.is_principal === true;
                
                // Guardar ID del contacto para actualización
                const contactoIdInput = d.querySelector('#contacto-id');
                if (contactoIdInput) contactoIdInput.value = contacto.id;

                // ⚠️ v2.60: Ocultar selector de cliente en modo edición (el cliente no se puede cambiar)
                const selectContainer = d.querySelector('#contacto-cliente-select-container');
                if (selectContainer) {
                    selectContainer.style.display = 'none';
                }

                // Cambiar texto del botón
                const btnGuardar = d.querySelector('#btn-guardar-contacto');
                if (btnGuardar) {
                    btnGuardar.innerHTML = '<i class="bi bi-save me-1"></i>Actualizar Contacto';
                }

                // Scroll al formulario
                const form = d.querySelector('#form-contacto-cliente');
                if (form) {
                    form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            } else {
                console.error('[contactos.editor] Error al cargar contacto:', res.status, res.data);
                if (w.SintelFeedback) {
                    w.SintelFeedback.error('No se pudo cargar el contacto para editar.');
                }
            }
        } catch (error) {
            console.error('[contactos.editor] Error al cargar contacto:', error);
            if (w.SintelFeedback) {
                w.SintelFeedback.error('Error al cargar el contacto.');
            }
        }
    }

    /**
     * Eliminar contacto
     * @param {number} contactoId - ID del contacto
     */
    async function eliminarContacto(contactoId) {
        if (!contactoId) {
            console.error('[contactos.editor] contactoId es requerido');
            return;
        }

        // Confirmación estándar
        if (!confirm('¿Está seguro de que desea eliminar este contacto?')) {
            return;
        }

        try {
            const res = await w.http('DELETE', `${API_BASE}/${contactoId}/`);
            
            if (res.ok) {
                if (w.SintelFeedback) {
                    w.SintelFeedback.success('Contacto eliminado correctamente');
                }
                
                // Recargar lista de contactos (si estamos en el gestor de un cliente específico)
                if (currentClienteId) {
                    await cargarContactos(currentClienteId);
                }
                
                // Disparar evento para recargar el grid global
                d.dispatchEvent(new CustomEvent('contactoEliminado', { detail: { id: contactoId } }));
            } else {
                console.error('[contactos.editor] Error al eliminar contacto:', res.status, res.data);
                if (w.SintelFeedback) {
                    w.SintelFeedback.error(res.data?.detail || 'Error al eliminar el contacto');
                }
            }
        } catch (error) {
            console.error('[contactos.editor] Error al eliminar contacto:', error);
            if (w.SintelFeedback) {
                w.SintelFeedback.error('Error al eliminar el contacto.');
            }
        }
    }

    /**
     * Cargar clientes en el select (cuando no hay cliente_id)
     */
    async function cargarClientesEnSelect() {
        const select = d.querySelector('#contacto-cliente-select');
        if (!select) return;

        select.innerHTML = '<option value="">Cargando clientes...</option>';

        try {
            const res = await w.http('GET', '/api/v1/clientes/?page_size=100&activo=true');
            
            if (!res.ok) {
                select.innerHTML = '<option value="">Error al cargar clientes</option>';
                console.error('[contactos.editor] Error al cargar clientes:', res);
                return;
            }

            const clientes = res.data?.results || res.data || [];
            select.innerHTML = '<option value="">Seleccione un cliente...</option>';

            clientes.forEach(cliente => {
                const option = d.createElement('option');
                option.value = cliente.id;
                option.textContent = `${cliente.razon_social || 'Sin nombre'}${cliente.numero_documento ? ` (${cliente.numero_documento})` : ''}`;
                select.appendChild(option);
            });

            console.log(`[contactos.editor] ✅ ${clientes.length} clientes cargados en el select`);
        } catch (error) {
            console.error('[contactos.editor] Error al cargar clientes:', error);
            select.innerHTML = '<option value="">Error al cargar clientes</option>';
        }
    }

    /**
     * Configurar eventos del gestor de contactos
     * @param {number} clienteId - ID del cliente (opcional, null si se debe seleccionar)
     */
    function configurarEventos(clienteId) {
        // Event delegation para botones de editar y eliminar
        const listaContainer = d.querySelector('#lista-contactos-cliente');
        if (listaContainer) {
            listaContainer.addEventListener('click', function(e) {
                const btn = e.target.closest('button');
                if (!btn) return;

                const contactoId = parseInt(btn.getAttribute('data-contacto-id'), 10);
                if (!contactoId || isNaN(contactoId)) return;

                if (btn.classList.contains('btn-editar-contacto')) {
                    e.preventDefault();
                    e.stopPropagation();
                    editarContacto(contactoId);
                } else if (btn.classList.contains('btn-eliminar-contacto')) {
                    e.preventDefault();
                    e.stopPropagation();
                    eliminarContacto(contactoId);
                }
            });
        }

        // Event listener para el formulario
        const form = d.querySelector('#form-contacto-cliente');
        if (form) {
            // ⚠️ v2.60: Usar once: false para permitir múltiples configuraciones (HTMX puede recargar el offcanvas)
            // Pero verificar si ya tiene el listener para evitar duplicados
            if (!form.dataset.listenerAttached) {
                form.addEventListener('submit', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Obtener cliente_id: primero del select, luego del input hidden, luego del parámetro
                    const clienteSelect = d.querySelector('#contacto-cliente-select');
                    const clienteIdFromSelect = clienteSelect ? parseInt(clienteSelect.value, 10) : null;
                    const clienteIdInput = d.querySelector('#contacto-cliente-id');
                    const clienteIdFromInput = clienteIdInput ? parseInt(clienteIdInput.value, 10) : null;
                    const clienteIdFinal = clienteIdFromSelect || clienteIdFromInput || clienteId;
                    
                    if (!clienteIdFinal || isNaN(clienteIdFinal)) {
                        if (w.SintelFeedback) {
                            w.SintelFeedback.error('Debe seleccionar un cliente antes de guardar el contacto.');
                        }
                        // Enfocar el select si existe
                        if (clienteSelect) {
                            clienteSelect.focus();
                        }
                        return;
                    }
                    
                    guardarContacto(e, clienteIdFinal);
                });
                form.dataset.listenerAttached = 'true';
            }
        }
        
        // ⚠️ v2.60: Listener para el select de cliente (cuando se selecciona un cliente)
        const clienteSelect = d.querySelector('#contacto-cliente-select');
        if (clienteSelect) {
            clienteSelect.addEventListener('change', function(e) {
                const selectedClienteId = parseInt(e.target.value, 10);
                const clienteIdInput = d.querySelector('#contacto-cliente-id');
                if (clienteIdInput && selectedClienteId) {
                    clienteIdInput.value = selectedClienteId;
                }
            });
        }

        // ⚠️ v2.60: Listener directo al botón "Guardar Contacto" como fallback (por si el submit no funciona)
        const btnGuardar = d.querySelector('#btn-guardar-contacto');
        if (btnGuardar && !btnGuardar.dataset.listenerAttached) {
            btnGuardar.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Obtener cliente_id: primero del select, luego del input hidden, luego del parámetro
                const clienteSelect = d.querySelector('#contacto-cliente-select');
                const clienteIdFromSelect = clienteSelect ? parseInt(clienteSelect.value, 10) : null;
                const clienteIdInput = d.querySelector('#contacto-cliente-id');
                const clienteIdFromInput = clienteIdInput ? parseInt(clienteIdInput.value, 10) : null;
                const clienteIdFinal = clienteIdFromSelect || clienteIdFromInput || clienteId;
                
                if (!clienteIdFinal || isNaN(clienteIdFinal)) {
                    if (w.SintelFeedback) {
                        w.SintelFeedback.error('Debe seleccionar un cliente antes de guardar el contacto.');
                    }
                    // Enfocar el select si existe
                    if (clienteSelect) {
                        clienteSelect.focus();
                    }
                    return;
                }
                
                guardarContacto(e, clienteIdFinal);
            });
            btnGuardar.dataset.listenerAttached = 'true';
        }

        // Botón cancelar (limpiar formulario)
        const btnCancelar = d.querySelector('#btn-cancelar-contacto');
        if (btnCancelar) {
            btnCancelar.addEventListener('click', function() {
                limpiarFormulario();
                // Restaurar texto del botón guardar
                const btnGuardar = d.querySelector('#btn-guardar-contacto');
                if (btnGuardar) {
                    btnGuardar.innerHTML = '<i class="bi bi-save me-1"></i>Guardar Contacto';
                }
                // ⚠️ v2.60: Si no hay cliente_id, mostrar el selector de cliente
                if (!clienteId) {
                    const selectContainer = d.querySelector('#contacto-cliente-select-container');
                    if (selectContainer) {
                        selectContainer.style.display = 'block';
                    }
                }
            });
        }
    }

    /**
     * Inicializar gestor de contactos
     * @param {number|null} clienteId - ID del cliente (null si se debe seleccionar)
     */
    async function inicializarGestorContactos(clienteId) {
        currentClienteId = clienteId;

        // Configurar eventos
        configurarEventos(clienteId);

        // ⚠️ v2.60: Si no hay clienteId, cargar clientes en el select y mostrar el selector
        if (!clienteId) {
            const selectContainer = d.querySelector('#contacto-cliente-select-container');
            if (selectContainer) {
                selectContainer.style.display = 'block';
            }
            // Actualizar título del offcanvas
            const titleEl = d.querySelector('#offcanvas-contactos-title');
            if (titleEl) {
                titleEl.textContent = 'Contactos - Seleccionar Cliente';
            }
            await cargarClientesEnSelect();
        } else {
            // Si hay clienteId, ocultar el selector y cargar contactos del cliente
            const selectContainer = d.querySelector('#contacto-cliente-select-container');
            if (selectContainer) {
                selectContainer.style.display = 'none';
            }
            // Cargar y renderizar contactos
            await cargarContactos(clienteId);
        }
    }

    // ⚠️ Escuchar evento personalizado para inicializar el gestor
    d.addEventListener('initContactosEditor', function(e) {
        const clienteId = e.detail?.cliente_id;
        const contactoId = e.detail?.contacto_id; // Para edición desde el grid
        
        // ⚠️ v2.60: clienteId puede ser null/undefined cuando se abre desde el módulo Contactos (modo selección)
        // En este caso, inicializamos el gestor sin cliente_id para mostrar el selector de cliente
        // No es un error, es el comportamiento esperado cuando se crea un contacto sin cliente pre-seleccionado
        if (!clienteId) {
            // Si no se proporciona cliente_id, inicializar en modo selección
            console.log('[contactos.editor] Inicializando gestor en modo selección de cliente');
            inicializarGestorContactos(null);
        } else {
            // Si hay cliente_id, inicializar normalmente
            inicializarGestorContactos(clienteId);
        }
        
        // Si hay contacto_id, cargar el contacto para editar
        if (contactoId) {
            setTimeout(() => {
                editarContacto(contactoId);
            }, 300); // Esperar a que el offcanvas esté completamente renderizado
        }
    });

    // ⚠️ Escuchar evento de eliminación desde el grid
    d.addEventListener('contactoEliminar', async function(e) {
        const contactoId = e.detail?.id;
        if (contactoId) {
            await eliminarContacto(contactoId);
            // Disparar evento de eliminación exitosa
            d.dispatchEvent(new CustomEvent('contactoEliminado', { detail: { id: contactoId } }));
        }
    });

    // ⚠️ v2.60: Limpieza de DOM - Limpiar estado cuando se cierre el offcanvas
    d.addEventListener('hidden.bs.offcanvas', function(e) {
        const offcanvasEl = e.target;
        // Verificar que sea el offcanvas de contactos
        if (offcanvasEl && offcanvasEl.id === 'offcanvas-contactos') {
            // Limpiar formulario
            limpiarFormulario();
            // Resetear cliente actual
            currentClienteId = null;
            console.log('[contactos.editor] Offcanvas de contactos cerrado, estado limpiado');
        }
    });

    // Exponer API pública
    w.ContactosEditorModule = {
        inicializar: inicializarGestorContactos,
        cargarContactos: cargarContactos,
        guardarContacto: guardarContacto,
        editarContacto: editarContacto,
        eliminarContacto: eliminarContacto
    };

})(window, document);
