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

    /**
     * Agregar contacto dinámicamente al contenedor del formulario
     */
    function agregarContactoDinamico() {
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

        // Convertir checkboxes
        data.activo = d.querySelector('#contacto-activo')?.checked || true;
        data.is_principal = d.querySelector('#contacto-is_principal')?.checked || false;

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
            if (w.SintelFeedback) {
                w.SintelFeedback.error('No se pudo recolectar los datos del formulario');
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
                if (w.SintelFeedback) {
                    w.SintelFeedback.success(
                        contactoId 
                            ? 'Contacto actualizado correctamente'
                            : 'Contacto agregado correctamente'
                    );
                }

                // Cerrar offcanvas
                const offcanvasEl = d.getElementById('offcanvas-contactos');
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
                const errorContainer = d.querySelector('#form-contacto-feedback');
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
                } else if (w.SintelFeedback) {
                    w.SintelFeedback.error('Error al guardar el contacto');
                }
            }
        } catch (error) {
            console.error('[clientes.contactos] Error guardando:', error);
            if (w.SintelFeedback) {
                w.SintelFeedback.error('Error de conexión');
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
        const offcanvasEl = d.querySelector('#offcanvas-contactos');
        if (!offcanvasEl) return;
        
        // ⚠️ Poblar select si es creación global
        const selectContainer = d.querySelector('#contacto-cliente-select-container');
        if (selectContainer && selectContainer.style.display !== 'none') {
            const selectEl = d.querySelector('#contacto-cliente-select');
            if (selectEl) {
                try {
                    const response = await w.clientesAPI.list({ page_size: 1000 });
                    if (response.ok) {
                        const clientes = response.data.results || response.data;
                        selectEl.innerHTML = '<option value="">Seleccione un cliente...</option>' + 
                            clientes.map(c => `<option value="${c.id}">${c.razon_social}</option>`).join('');
                    }
                } catch (e) {
                    console.error('[clientes.contactos] Error cargando lista de clientes', e);
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
            btnAgregarContacto.addEventListener('click', agregarContactoDinamico);
        }

        const contenedorContactos = d.querySelector('#contenedor-contactos');
        if (contenedorContactos) {
            contenedorContactos.addEventListener('click', eliminarContactoDinamico);
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
        if (e.target?.id === 'offcanvas-contactos') {
            initFormulario();
        }
    });

    // Inicialización en DOMContentLoaded (por si ya existe el offcanvas)
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', function() {
            if (d.querySelector('#offcanvas-contactos')) {
                initFormulario();
            }
        });
    } else if (d.querySelector('#offcanvas-contactos')) {
        initFormulario();
    }

    // Exponer API pública
    w.ContactosModule = {
        guardar: guardarContacto,
        inicializar: initFormulario
    };

})(window, document);
