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

    // ============================================================
    // DOM SELECTORS (SSoT)
    // ============================================================
    const DOM = {
        offcanvas:          '#offcanvas-cliente',
        form:               '#form-cliente',
        btnGuardar:         '#btn-guardar-cliente',
        feedback:           '#form-cliente-feedback',
        clienteId:          '#cliente-id',
        
        // Contenedor de contactos dinámicos
        contenedorContactos: '#contenedor-contactos',
        btnAgregarContacto:  '#btn-agregar-contacto',
        
        // Selectores de campos (prefijo cliente-)
        fields: {
            tipo_persona:       '#cliente-tipo_persona',
            tipo_documento:     '#cliente-tipo_documento',
            numero_documento:   '#cliente-numero_documento',
            razon_social:       '#cliente-razon_social',
            nombre_comercial:   '#cliente-nombre_comercial',
            regimen_tributario: '#cliente-regimen_tributario',
            email:              '#cliente-email',
            telefono:           '#cliente-telefono',
            direccion:          '#cliente-direccion',
            ciudad:             '#cliente-ciudad',
            observaciones:      '#cliente-observaciones',
            activo:             '#cliente-activo',
            // [v3.5.0] Retenciones
            es_retenedor:       '#cliente-es_retenedor',
            aplica_retefuente:  '#cliente-aplica_retefuente',
            retefuente_porcentaje: '#cliente-retefuente_porcentaje',
            aplica_reteica:     '#cliente-aplica_reteica',
            reteica_porcentaje: '#cliente-reteica_porcentaje',
            aplica_reteiva:     '#cliente-aplica_reteiva',
            reteiva_porcentaje: '#cliente-reteiva_porcentaje',
        }
    };

    /**
     * Recolectar datos del formulario
     * Zero Trust: recoleccion manual campo por campo (no FormData para evitar
     * que inputs ocultos o checkboxes desactivados contaminen el payload).
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector(DOM.form);
        if (!form) {
            console.error('[clientes.editor] Formulario no encontrado');
            return null;
        }

        const getText = (selector) => (form.querySelector(selector)?.value || '').trim();
        const getBool = (selector) => form.querySelector(selector)?.checked ?? false;

        // Construccion explicita del payload principal (DOM Shield)
        const data = {
            tipo_persona:       getText(DOM.fields.tipo_persona),
            tipo_documento:     getText(DOM.fields.tipo_documento),
            numero_documento:   getText(DOM.fields.numero_documento),
            razon_social:       getText(DOM.fields.razon_social),
            nombre_comercial:   getText(DOM.fields.nombre_comercial),
            regimen_tributario: getText(DOM.fields.regimen_tributario),
            email:              getText(DOM.fields.email),
            telefono:           getText(DOM.fields.telefono),
            direccion:          getText(DOM.fields.direccion),
            ciudad:             getText(DOM.fields.ciudad),
            observaciones:      getText(DOM.fields.observaciones),
            activo:             getBool(DOM.fields.activo),
            // [v3.5.0] Retenciones
            es_retenedor:       getBool(DOM.fields.es_retenedor),
            aplica_retefuente:  getBool(DOM.fields.aplica_retefuente),
            retefuente_porcentaje: parseFloat(getText(DOM.fields.retefuente_porcentaje)) || 0,
            aplica_reteica:     getBool(DOM.fields.aplica_reteica),
            reteica_porcentaje: parseFloat(getText(DOM.fields.reteica_porcentaje)) || 0,
            aplica_reteiva:     getBool(DOM.fields.aplica_reteiva),
            reteiva_porcentaje: parseFloat(getText(DOM.fields.reteiva_porcentaje)) || 0,
        };

        // Remover campos de texto opcionales vacios
        ['nombre_comercial', 'email', 'telefono', 'direccion', 'ciudad', 'observaciones'].forEach(key => {
            if (!data[key]) delete data[key];
        });

        // Recolectar contactos del contenedor dinamico (Zero Trust: cada campo explicito)
        const contactos = [];
        const contactoItems = d.querySelectorAll('#contenedor-contactos .contacto-item');

        contactoItems.forEach(item => {
            const nombre_completo = (item.querySelector('.contacto-nombre')?.value || '').trim();
            const email = (item.querySelector('.contacto-email')?.value || '').trim();

            // Ignorar filas sin datos minimos requeridos
            if (!nombre_completo || !email) return;

            // Normalizar ID: null para nuevos, entero para existentes
            const rawId = item.getAttribute('data-contacto-id');
            const contactoId = rawId ? (parseInt(rawId, 10) || null) : null;

            contactos.push({
                id:              contactoId,
                nombre_completo,
                cargo:           (item.querySelector('.contacto-cargo')?.value || '').trim(),
                email,
                telefono:        (item.querySelector('.contacto-telefono')?.value || '').trim(),
                activo:          item.querySelector('.contacto-activo')?.checked ?? true,
                is_principal:    item.querySelector('.contacto-principal')?.checked ?? false,
            });
        });

        // Siempre enviar contactos (array vacio = reemplazo total / limpiar todos)
        data.contactos = contactos;

        return data;
    }

    /**
     * Formatear errores de DRF correctamente, incluyendo arrays de objetos anidados.
     * Evita el bug '[object Object]' cuando DRF retorna contactos: [{email: ["msg"]}].
     */
    function formatApiError(val) {
        if (Array.isArray(val)) {
            return val.map(function(item) {
                if (item && typeof item === 'object') {
                    return Object.entries(item)
                        .map(function(pair) { return pair[0] + ': ' + formatApiError(pair[1]); })
                        .join('; ');
                }
                return String(item);
            }).join(' | ');
        }
        if (val && typeof val === 'object') {
            return Object.entries(val)
                .map(function(pair) { return pair[0] + ': ' + formatApiError(pair[1]); })
                .join('; ');
        }
        return String(val || '');
    }

    /**
     * Validar campos requeridos antes de llamar a la API.
     * Retorna un mensaje de error o null si todo está bien.
     */
    function validarCamposRequeridos(payload) {
        const requeridos = [
            { campo: 'tipo_persona',       etiqueta: 'Tipo de Persona' },
            { campo: 'tipo_documento',     etiqueta: 'Tipo de Documento' },
            { campo: 'numero_documento',   etiqueta: 'Número de Documento' },
            { campo: 'razon_social',       etiqueta: 'Razón Social' },
            { campo: 'regimen_tributario', etiqueta: 'Régimen Tributario' },
        ];
        const faltantes = requeridos
            .filter(r => !payload[r.campo])
            .map(r => r.etiqueta);
        return faltantes.length ? 'Campos obligatorios incompletos: ' + faltantes.join(', ') + '.' : null;
    }

    async function guardarCliente() {
        const payload = recolectarDatosFormulario();
        const offcanvasEl = d.querySelector(DOM.offcanvas);
        const errorContainer = offcanvasEl?.querySelector(DOM.feedback);

        if (!payload) {
            if (errorContainer) {
                errorContainer.textContent = 'No se pudo recolectar los datos del formulario.';
                errorContainer.classList.remove('d-none');
            }
            return;
        }

        // Validar campos requeridos antes de llamar a la API
        const errorValidacion = validarCamposRequeridos(payload);
        if (errorValidacion) {
            if (errorContainer) {
                errorContainer.textContent = errorValidacion;
                errorContainer.classList.remove('d-none');
                errorContainer.classList.add('alert', 'alert-danger', 'mb-3');
                errorContainer.style.display = 'block';
            }
            return;
        }

        const clienteId = d.querySelector(DOM.clienteId)?.value;

        // Deshabilitar botón mientras se guarda
        const btnGuardar = d.querySelector(DOM.btnGuardar);
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
            if (w.UIManager?.success) {
                w.UIManager.success(clienteId ? 'Cliente actualizado exitosamente' : 'Cliente creado exitosamente');
            }

            // ⚠️ v2.62: Cerrar offcanvas usando el orquestador central
            if (w.UIManager?.handleOffcanvas) {
                w.UIManager.handleOffcanvas(DOM.offcanvas, 'hide');
            }

            // Disparar evento para recargar la tabla
            d.dispatchEvent(new CustomEvent('clienteGuardado'));
        } else {
            // Restaurar boton de guardado
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = clienteId
                    ? '<i class="bi bi-save me-1"></i>Actualizar'
                    : '<i class="bi bi-save me-1"></i>Guardar';
            }

            // Error boundary: renderizar errores en el contenedor del offcanvas
            const errorData = (response && response.data) ? response.data : { detail: 'Error al guardar el cliente.' };

            if (errorContainer) {
                errorContainer.classList.remove('d-none');
                errorContainer.classList.add('alert', 'alert-danger', 'mb-3');
                errorContainer.style.display = 'block';

                if (errorData.detail && typeof errorData.detail === 'string') {
                    errorContainer.textContent = errorData.detail;
                } else {
                    // Formatear errores de campo (incluye contactos anidados)
                    const fields = Object.keys(errorData).filter(function(k) { return k !== 'detail'; });
                    if (fields.length > 0) {
                        const items = fields.map(function(field) {
                            return '<li><strong>' + field.toUpperCase() + ':</strong> ' + formatApiError(errorData[field]) + '</li>';
                        }).join('');
                        errorContainer.innerHTML = '<ul class="mb-0">' + items + '</ul>';
                    } else {
                        errorContainer.textContent = 'Error de validacion. Revise los datos del formulario.';
                    }
                }
            }

            console.error('[clientes.editor:guardar] Error ' + (response?.status || 500), errorData);
        }
    }

    /**
     * Inicializar eventos del formulario
     */
    function initFormulario() {
        const offcanvasEl = d.querySelector(DOM.offcanvas);
        if (!offcanvasEl) return;

        // Botón agregar contacto
        const btnAgregarContacto = d.querySelector(DOM.btnAgregarContacto);
        if (btnAgregarContacto) {
            btnAgregarContacto.addEventListener('click', () => {
                w.ClienteUtils.agregarContacto(DOM.contenedorContactos);
            });
        }

        // Event delegation para eliminar contactos
        const contenedorContactos = d.querySelector(DOM.contenedorContactos);
        if (contenedorContactos) {
            contenedorContactos.addEventListener('click', w.ClienteUtils.eliminarContacto);
        }

        // Inicializar contactos
        if (contenedorContactos) {
            const clienteId = d.querySelector(DOM.clienteId)?.value;
            if (!clienteId) {
                // Modo CREAR: limpiar el contenedor e inyectar exactamente un contacto vacio
                contenedorContactos.innerHTML = '';
                w.ClienteUtils.agregarContacto(DOM.contenedorContactos);
            } else if (!contenedorContactos.querySelector('.contacto-item')) {
                // Modo EDITAR sin contactos previos: agregar uno vacio
                w.ClienteUtils.agregarContacto(DOM.contenedorContactos);
            }
            // Sincronizar visibilidad del boton Eliminar
            w.ClienteUtils._actualizarBotonesEliminar(contenedorContactos);
        }

        // [v3.5.0] Lógica de Retenciones
        const checkRetenedor = d.querySelector(DOM.fields.es_retenedor);
        const contenedorRetenciones = d.querySelector('#contenedor-retenciones');
        
        if (checkRetenedor && contenedorRetenciones) {
            const toggleRetenciones = () => {
                const isRetenedor = checkRetenedor.checked;
                console.log('[clientes.editor] Toggling retenciones:', isRetenedor);
                
                if (isRetenedor) {
                    contenedorRetenciones.classList.remove('d-none');
                    contenedorRetenciones.style.display = 'block';
                } else {
                    contenedorRetenciones.classList.add('d-none');
                    contenedorRetenciones.style.display = 'none';
                }
                
                if (!isRetenedor) {
                    // Limpiar todo si se apaga el switch (Zero Waste Frontend)
                    ['aplica_retefuente', 'aplica_reteica', 'aplica_reteiva'].forEach(f => {
                        const cb = d.querySelector(DOM.fields[f]);
                        if (cb) cb.checked = false;
                    });
                    ['retefuente_porcentaje', 'reteica_porcentaje', 'reteiva_porcentaje'].forEach(f => {
                        const inp = d.querySelector(DOM.fields[f]);
                        if (inp) {
                            inp.value = 0;
                            inp.disabled = true;
                        }
                    });
                }
            };

            // v3.5.1: Control fino por campo de retención
            ['retefuente', 'reteica', 'reteiva'].forEach(key => {
                const cb = d.querySelector(DOM.fields[`aplica_${key}`]);
                const inp = d.querySelector(DOM.fields[`${key}_porcentaje`]);
                if (cb && inp) {
                    const syncInput = () => {
                        inp.disabled = !cb.checked;
                        if (!cb.checked) inp.value = 0;
                    };
                    cb.addEventListener('change', syncInput);
                    syncInput(); // Inicial
                }
            });

            checkRetenedor.addEventListener('change', toggleRetenciones);
            // Ejecutar inicial (para modo edición)
            toggleRetenciones();
        }

        // ⚠️ v2.62: Delegación de eventos para botones del formulario (evita duplicidad)
        const setupEventListeners = () => {
            const btnGuardar = d.querySelector(DOM.btnGuardar);
            if (btnGuardar) {
                // Clonar para limpiar listeners previos si el elemento persiste
                const newBtn = btnGuardar.cloneNode(true);
                btnGuardar.parentNode.replaceChild(newBtn, btnGuardar);
                newBtn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    await guardarCliente();
                });
            }

            const form = d.querySelector(DOM.form);
            if (form) {
                form.onsubmit = async (e) => {
                    e.preventDefault();
                    await guardarCliente();
                };
            }
        };

        setupEventListeners();

        console.log('[clientes.editor] Formulario inicializado');
    }

    /**
     * [v3.5.0] Inicializar buscador asíncrono de cuentas contables
     */

    /**
     * Escuchar evento cuando el offcanvas se inyecta en el DOM
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
    w.ClientesEditorModule = {
        guardar: guardarCliente
    };

    w.AppCliente.form = w.ClientesEditorModule;

})(window, document);
