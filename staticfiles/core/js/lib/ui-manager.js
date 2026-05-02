/**
 * UIManager - Orquestador Central de UI (Error Boundary Pattern v2.60)
 * 
 * ⚠️ ARQUITECTURA v2.60:
 * - Aísla la lógica de negocio de la presentación de errores
 * - Centraliza el manejo de modales y formularios
 * - Compatible con Zero Trust v2.40
 * - Usa SintelFeedback para notificaciones
 * 
 * Dependencias:
 * - SintelFeedback (apps/tenant/core/static/core/js/utils/feedback.js)
 * - Bootstrap 5 (para modales)
 */

(function(w, d) {
  'use strict';

  /**
   * ⚠️ v2.60: Aislamiento Gradual - Boundary que decide dónde mostrar el error
   * 
   * Decide si el error debe mostrarse como:
   * - Notificación flotante (toast): Para errores generales
   * - Mensaje dentro del modal: Si hay un modal abierto y un contenedor de error disponible
   * 
   * @param {Object} response - Objeto de respuesta de la API con formato {ok, status, data}
   * @param {string} context - Contexto para logs (ej: "[mailinbox.page]")
   * @param {Object} options - Opciones de configuración
   * @param {string} options.modalSelector - Selector del modal (ej: '#modal-mailinbox-form')
   * @param {string} options.errorContainerSelector - Selector del contenedor de error dentro del modal (ej: '#mailinbox-form-feedback')
   * @returns {boolean} true si el error fue manejado, false en caso contrario
   */
  function handleError(response, context = '', options = {}) {
    if (!response) {
      console.warn(`${context} handleError llamado sin respuesta`);
      return false;
    }

    // Si la respuesta es exitosa, no hay error
    if (response.ok) {
      return false;
    }

    // ⚠️ REGLA DE ORO: Si el error es 401, NO mostrar alerta (interceptor global maneja)
    if (response.status === 401) {
      console.warn(`${context} Error 401 detectado, omitiendo feedback (interceptor global manejará redirección)`);
      return false;
    }

    // ⚠️ v2.61: DEBUG - Log detallado de la respuesta para diagnóstico
    console.log(`${context} [DEBUG] Procesando error:`, {
      status: response.status,
      statusText: response.statusText,
      hasData: !!response.data,
      dataType: typeof response.data,
      dataKeys: response.data && typeof response.data === 'object' ? Object.keys(response.data) : 'N/A',
      dataDetail: response.data?.detail,
      dataDetailType: typeof response.data?.detail,
      isDetailArray: Array.isArray(response.data?.detail),
      fullData: response.data
    });

    // Extraer mensaje de error
    let errorMessage = 'Error desconocido';
    if (response.data) {
      if (response.data.detail) {
        // ⚠️ v2.60: Manejar detail como string, array u objeto
        if (typeof response.data.detail === 'string') {
          errorMessage = response.data.detail;
        } else if (Array.isArray(response.data.detail)) {
          // ⚠️ v2.61: Si detail es un array, unir los mensajes
          errorMessage = response.data.detail.join(', ');
          console.log(`${context} [DEBUG] Mensaje extraído de array detail:`, errorMessage);
        } else if (typeof response.data.detail === 'object') {
          // Si detail es un objeto (errores de validación por campo), aplanarlo
          const errorFields = Object.keys(response.data.detail);
          const errorMessages = errorFields.map(field => {
            const fieldErrors = Array.isArray(response.data.detail[field]) 
              ? response.data.detail[field].join(', ')
              : String(response.data.detail[field]);
            return `${field}: ${fieldErrors}`;
          });
          errorMessage = errorMessages.join(' | ');
        }
      } else if (response.data.message) {
        errorMessage = response.data.message;
      } else if (typeof response.data === 'string') {
        errorMessage = response.data;
      } else if (Array.isArray(response.data)) {
        errorMessage = response.data.join(', ');
      } else if (typeof response.data === 'object') {
        // ⚠️ v2.60: Si data es un objeto de errores de validación (DRF), aplanarlo
        const errorFields = Object.keys(response.data);
        const errorMessages = errorFields.map(field => {
          const fieldErrors = Array.isArray(response.data[field]) 
            ? response.data[field].join(', ')
            : String(response.data[field]);
          return `${field}: ${fieldErrors}`;
        });
        errorMessage = errorMessages.join(' | ');
      }
    }

    // ⚠️ v2.61: DEBUG - Log del mensaje final extraído
    console.log(`${context} [DEBUG] Mensaje de error final:`, errorMessage);

    // Decidir dónde mostrar el error
    const { modalSelector, errorContainerSelector } = options;
    
    // ⚠️ v2.61: Si hay un contenedor de error (con o sin modal), intentar mostrar ahí primero
    if (errorContainerSelector) {
      const errorContainer = d.querySelector(errorContainerSelector);
      
      if (errorContainer) {
        try {
          // Configurar el contenedor como alerta de error
          errorContainer.className = 'alert alert-danger';
          errorContainer.innerHTML = `<strong><i class="bi bi-exclamation-triangle me-2"></i>Error:</strong> ${errorMessage}`;
          errorContainer.classList.remove('d-none');
          errorContainer.style.display = 'block';
          
          // Scroll al contenedor de error si es necesario
          errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          
          console.log(`${context} ✅ Error mostrado en contenedor:`, errorMessage);
          return true;
        } catch (err) {
          console.error(`${context} ❌ Error al mostrar error en contenedor:`, err);
          // Fallback a notificación flotante
        }
      } else {
        console.warn(`${context} ⚠️ Contenedor de error no encontrado:`, errorContainerSelector);
      }
    }
    
    // Si hay un modal abierto y un contenedor de error, mostrar ahí
    if (modalSelector && errorContainerSelector) {
      const modalElement = d.querySelector(modalSelector);
      const errorContainer = d.querySelector(errorContainerSelector);
      
      // ⚠️ DEBUG: Log para diagnóstico
      console.log(`${context} Intentando mostrar error en modal:`, {
        modalSelector,
        errorContainerSelector,
        modalElement: !!modalElement,
        errorContainer: !!errorContainer,
        modalVisible: modalElement?.classList.contains('show')
      });
      
      // Verificar que el modal esté visible (abierto) o simplemente que exista
      if (modalElement && errorContainer) {
        // ⚠️ v2.60: Mostrar error incluso si el modal no está visible (puede estar en proceso de apertura)
        try {
          errorContainer.className = 'alert alert-danger';
          errorContainer.textContent = errorMessage;
          errorContainer.classList.remove('d-none');
          errorContainer.style.display = 'block';
          
          // Scroll al contenedor de error si es necesario
          errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          
          console.log(`${context} ✅ Error mostrado en modal:`, errorMessage);
          return true;
        } catch (err) {
          console.error(`${context} ❌ Error al mostrar error en modal:`, err);
          // Fallback a notificación flotante
        }
      } else {
        console.warn(`${context} ⚠️ Modal o contenedor de error no encontrado:`, {
          modalElement: !!modalElement,
          errorContainer: !!errorContainer
        });
      }
    }

    // Fallback: mostrar como notificación flotante
    notifyError(response, context);
    return true;
  }

  /**
   * Procesa un objeto de respuesta de error de la API y muestra notificación flotante
   * 
   * ⚠️ REGLA DE ORO: Si el error es 401, NO mostrar alerta (interceptor global maneja)
   * 
   * @param {Object|Response|Error} response - Objeto de respuesta de error de la API
   * @param {string} context - Contexto para logs (ej: "[TabulatorFactory]")
   */
  function notifyError(response, context = '') {
    if (!response) {
      console.warn(`${context} notifyError llamado sin respuesta`);
      return;
    }

    // Si SintelFeedback está disponible, usarlo (preferido)
    if (w.SintelFeedback && typeof w.SintelFeedback.handleAPIError === 'function') {
      w.SintelFeedback.handleAPIError(response, context);
      return;
    }

    // Fallback: usar notyf si está disponible
    if (w.notyf && typeof w.notyf.error === 'function') {
      let message = 'Error desconocido';
      
      // Extraer mensaje del objeto de respuesta
      if (response.data) {
        if (response.data.detail) {
          // ⚠️ v2.60: Manejar detail como string, array u objeto
          if (typeof response.data.detail === 'string') {
            message = response.data.detail;
          } else if (Array.isArray(response.data.detail)) {
            message = response.data.detail.join(', ');
          } else if (typeof response.data.detail === 'object') {
            // Si detail es un objeto (errores de validación por campo), aplanarlo
            const errorFields = Object.keys(response.data.detail);
            const errorMessages = errorFields.map(field => {
              const fieldErrors = Array.isArray(response.data.detail[field]) 
                ? response.data.detail[field].join(', ')
                : String(response.data.detail[field]);
              return `${field}: ${fieldErrors}`;
            });
            message = errorMessages.join(' | ');
          }
        } else if (response.data.message) {
          message = response.data.message;
        } else if (typeof response.data === 'string') {
          message = response.data;
        } else if (Array.isArray(response.data)) {
          message = response.data.join(', ');
        } else if (typeof response.data === 'object') {
          // ⚠️ v2.60: Si data es un objeto de errores de validación (DRF), aplanarlo
          const errorFields = Object.keys(response.data);
          const errorMessages = errorFields.map(field => {
            const fieldErrors = Array.isArray(response.data[field]) 
              ? response.data[field].join(', ')
              : String(response.data[field]);
            return `${field}: ${fieldErrors}`;
          });
          message = errorMessages.join(' | ');
        }
      } else if (response.message) {
        message = response.message;
      } else if (typeof response === 'string') {
        message = response;
      }

      // ⚠️ REGLA DE ORO: Si es 401, NO mostrar notificación
      if (response.status === 401) {
        console.warn(`${context} Error 401 detectado, omitiendo notificación (interceptor global manejará redirección)`);
        return;
      }

      w.notyf.error({
        message: message,
        duration: 5000,
        dismissible: true
      });
      return;
    }

    // Fallback final: console.error
    console.error(`${context} Error de API:`, response);
  }

  /**
   * Maneja la apertura/cierre de modales Bootstrap 5 de forma segura
   * 
   * @param {string} selector - Selector CSS del modal (ej: '#modal-cliente')
   * @param {string} action - Acción a realizar: 'show' o 'hide'
   * @returns {boolean} true si la operación fue exitosa, false en caso contrario
   */
  function handleModal(selector, action = 'show') {
    if (!selector) {
      console.error('[UIManager] handleModal: selector requerido');
      return false;
    }

    const modalElement = d.querySelector(selector);
    if (!modalElement) {
      console.error(`[UIManager] handleModal: Modal ${selector} no encontrado`);
      return false;
    }

    // Verificar que Bootstrap 5 esté disponible
    if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
      console.error('[UIManager] handleModal: Bootstrap 5 no está disponible');
      return false;
    }

    try {
      // Obtener o crear instancia del modal
      let modalInstance = bootstrap.Modal.getInstance(modalElement);
      if (!modalInstance) {
        modalInstance = new bootstrap.Modal(modalElement);
      }

      // Ejecutar acción
      if (action === 'show') {
        modalInstance.show();
      } else if (action === 'hide') {
        modalInstance.hide();
      } else {
        console.error(`[UIManager] handleModal: Acción "${action}" no válida. Use "show" o "hide"`);
        return false;
      }

      return true;
    } catch (error) {
      console.error(`[UIManager] handleModal: Error al ${action} modal ${selector}:`, error);
      return false;
    }
  }

  /**
   * Limpia un formulario y oculta contenedores de error locales
   * 
   * @param {string} selector - Selector CSS del formulario (ej: '#form-cliente')
   * @returns {boolean} true si la operación fue exitosa, false en caso contrario
   */
  function resetForm(selector) {
    if (!selector) {
      console.error('[UIManager] resetForm: selector requerido');
      return false;
    }

    const formElement = d.querySelector(selector);
    if (!formElement) {
      console.warn(`[UIManager] resetForm: Formulario ${selector} no encontrado`);
      return false;
    }

    try {
      // Resetear formulario nativo
      if (formElement.reset && typeof formElement.reset === 'function') {
        formElement.reset();
      } else {
        // Fallback: limpiar campos manualmente
        const inputs = formElement.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
          if (input.type === 'checkbox' || input.type === 'radio') {
            input.checked = false;
          } else {
            input.value = '';
          }
        });
      }

      // Ocultar contenedores de error locales
      const errorContainers = formElement.querySelectorAll('.alert-danger, .invalid-feedback, .error-message');
      errorContainers.forEach(container => {
        container.style.display = 'none';
        container.textContent = '';
      });

      // Remover clases de error de Bootstrap
      const invalidInputs = formElement.querySelectorAll('.is-invalid');
      invalidInputs.forEach(input => {
        input.classList.remove('is-invalid');
      });

      return true;
    } catch (error) {
      console.error(`[UIManager] resetForm: Error al limpiar formulario ${selector}:`, error);
      return false;
    }
  }

  // ============================================
  // v3.4 — Atajos globales: showError / showSuccess / showInfo
  // Centralizan los `showError(...)` que estaban definidos localmente
  // en clientes.list.js, facturas.page.js, etc.
  // ============================================

  function _toast(level, msg) {
    const text = (msg && typeof msg === 'object') ? JSON.stringify(msg) : String(msg ?? '');
    if (w.SintelFeedback && typeof w.SintelFeedback[level] === 'function') {
      w.SintelFeedback[level](text);
      return;
    }
    // Fallback: usar notyf si está disponible (vía window.notyf o window.Notyf)
    const NotyfClass = w.Notyf || (w.notyf && w.notyf.constructor);
    if (NotyfClass) {
      try {
        const n = w._notyfInstance || (w._notyfInstance = new NotyfClass({ duration: 4000, dismissible: true }));
        n[level === 'success' ? 'success' : 'error'](text);
        return;
      } catch (_) { /* fallthrough */ }
    }
    // Fallback final: console (no romper UX)
    (console[level] || console.log)(`[ui] ${level}: ${text}`);
  }

  w.showError   = function (msg) { _toast('error',   msg); };
  w.showSuccess = function (msg) { _toast('success', msg); };
  w.showInfo    = function (msg) { _toast('info',    msg); };

  // Exportar objeto global
  w.UIManager = {
    handleError,  // ⚠️ v2.60: Boundary principal (decide dónde mostrar error)
    notifyError,  // Notificación flotante (fallback)
    handleModal,
    resetForm,
    showError: w.showError,
    showSuccess: w.showSuccess,
    showInfo: w.showInfo
  };

  console.log('[UIManager] Orquestador central de UI inicializado v3.4');

})(window, document);
