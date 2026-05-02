/**
 * contacto_cliente_form.js - Manejo de formularios para Contacto de Cliente v2.61
 * Feature-Sliced: Lógica de recolección y guardado de formularios
 */
(function(w, d) {
  'use strict';

  w.AppContactoCliente = w.AppContactoCliente || {};

  /**
   * Recolectar datos del formulario de contacto
   */
  function recolectarDatosFormulario() {
    const form = d.querySelector('#form-contacto-cliente');
    if (!form) {
      console.error('[contacto_cliente_form] Formulario no encontrado');
      return null;
    }

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Convertir checkboxes
    const activoCheckbox = d.querySelector('#contacto-activo');
    const principalCheckbox = d.querySelector('#contacto-principal');
    data.activo = activoCheckbox?.checked ?? false;
    data.is_principal = principalCheckbox?.checked ?? false;
    
    // Normalizar cliente_id
    const clienteIdInput = d.querySelector('#contacto-cliente-id');
    if (clienteIdInput?.value) {
      data.cliente = parseInt(clienteIdInput.value) || null;
    }
    
    // Remover campos vacíos
    Object.keys(data).forEach(key => {
      if (key !== 'id' && (data[key] === '' || data[key] === null)) {
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
      if (w.UIManager?.notifyError) {
        w.UIManager.notifyError({
          status: 400,
          data: { detail: 'No se pudo recolectar los datos del formulario' }
        }, 'Contactos');
      }
      return;
    }

    const contactoId = d.querySelector('#contacto-id')?.value;
    const offcanvasEl = d.querySelector('#offcanvas-contacto-cliente');
    
    // Deshabilitar botón mientras se guarda
    const btnGuardar = d.querySelector('#btn-guardar-contacto-cliente');
    if (btnGuardar) {
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
    }

    // Llamar a la API
    const response = contactoId 
      ? await w.contactosClienteAPI.update(contactoId, payload)
      : await w.contactosClienteAPI.create(payload);
    
    if (response && response.ok) {
      // Éxito
      if (w.UIManager?.success) {
        w.UIManager.success(
          contactoId 
            ? 'Contacto actualizado exitosamente' 
            : 'Contacto creado exitosamente'
        );
      }

      // Cerrar offcanvas
      if (offcanvasEl && window.bootstrap) {
        const offcanvasInstance = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (offcanvasInstance) {
          offcanvasInstance.hide();
        }
      }

      // Disparar evento para recargar tabla
      d.dispatchEvent(new CustomEvent('contactoGuardado'));
    } else {
      // Error
      if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = contactoId 
          ? '<i class="bi bi-save me-1"></i>Actualizar'
          : '<i class="bi bi-save me-1"></i>Guardar';
      }
      
      // Mostrar errores en contenedor
      if (response?.status === 400 && response?.data) {
        const errorContainer = offcanvasEl?.querySelector('#form-contacto-cliente-feedback');
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

      if (w.UIManager?.notifyError) {
        w.UIManager.notifyError(response || {
          status: 500,
          data: { detail: 'Error al guardar el contacto' }
        }, 'Contactos');
      }
    }
  }

  /**
   * Inicializar eventos del formulario
   */
  function initFormulario() {
    const offcanvasEl = d.querySelector('#offcanvas-contacto-cliente');
    if (!offcanvasEl) return;

    // Botón guardar
    const btnGuardar = d.querySelector('#btn-guardar-contacto-cliente');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        await guardarContacto();
      });
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

    // Selector de cliente (rellenar si es necesario)
    const clienteSelect = d.querySelector('#contacto-cliente-select');
    const clienteInput = d.querySelector('#contacto-cliente-id');
    
    if (clienteSelect && !clienteInput?.value) {
      clienteSelect.removeAttribute('name');
      clienteSelect.addEventListener('change', function() {
        if (clienteInput) {
          clienteInput.value = clienteSelect.value || '';
        }
      });
    }

    console.log('[contacto_cliente_form] Formulario inicializado');
  }

  /**
   * Escuchar evento cuando el offcanvas se inyecta en el DOM
   */
  d.addEventListener('shown.bs.offcanvas', function(e) {
    if (e.target?.id === 'offcanvas-contacto-cliente') {
      initFormulario();
    }
  });

  // Inicialización en DOMContentLoaded
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
  w.ContactoClienteFormModule = {
    guardar: guardarContacto
  };

  w.AppContactoCliente.form = w.ContactoClienteFormModule;

})(window, document);
