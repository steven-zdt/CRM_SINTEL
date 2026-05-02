/**
 * Modal Service - Servicio agnóstico para manejo de modales Bootstrap
 * 
 * ⚠️ FASE 1: Servicio centralizado para abrir/cerrar modales
 * - Abstrae la lógica de Bootstrap modals
 * - Permite pasar título, body y onSubmit de forma simple
 * - Mantiene UI homogénea entre módulos
 */

(function (w) {
  'use strict';

  /**
   * Abre un modal con título, body y callback onSubmit
   * @param {Object} config - Configuración del modal
   * @param {string} config.id - ID del elemento modal
   * @param {string} [config.title] - Título del modal (opcional)
   * @param {string|HTMLElement} [config.body] - Contenido del body (opcional)
   * @param {Function} [config.onSubmit] - Callback al hacer submit (opcional)
   * @returns {boolean} true si el modal se abrió correctamente
   */
  function open({ id, title, body, onSubmit }) {
    const modal = document.getElementById(id);
    if (!modal) {
      console.warn('[ModalService] Modal no encontrado:', id);
      return false;
    }

    // Actualizar título si se proporciona
    if (title !== undefined) {
      const titleEl = modal.querySelector('.modal-title');
      if (titleEl) {
        titleEl.textContent = title;
      }
    }

    // Actualizar body si se proporciona
    if (body !== undefined) {
      const bodyEl = modal.querySelector('.modal-body');
      if (bodyEl) {
        if (typeof body === 'string') {
          bodyEl.innerHTML = body;
        } else if (body instanceof HTMLElement) {
          bodyEl.innerHTML = '';
          bodyEl.appendChild(body);
        }
      }
    }

    // Configurar botón de submit si existe
    const submitBtn = modal.querySelector('[data-action="submit"], .btn-primary[type="submit"], button[type="submit"]');
    if (submitBtn && typeof onSubmit === 'function') {
      // Remover listeners anteriores
      const newSubmitBtn = submitBtn.cloneNode(true);
      submitBtn.parentNode.replaceChild(newSubmitBtn, submitBtn);
      
      newSubmitBtn.onclick = async (e) => {
        e.preventDefault();
        try {
          newSubmitBtn.disabled = true;
          await onSubmit();
          // El modal se cierra automáticamente si onSubmit no lanza error
          // Si se necesita cerrar manualmente, usar close(id) en onSubmit
        } catch (err) {
          console.error('[ModalService] Error en onSubmit:', err);
          // No cerrar el modal si hay error, permitir al usuario corregir
        } finally {
          newSubmitBtn.disabled = false;
        }
      };
    }

    // Abrir modal usando Bootstrap
    if (w.bootstrap && w.bootstrap.Modal) {
      const bsModal = w.bootstrap.Modal.getOrCreateInstance(modal);
      bsModal.show();
      return true;
    } else if (w.jQuery && w.jQuery.fn && w.jQuery.fn.modal) {
      // Fallback a jQuery Bootstrap 4
      w.jQuery(modal).modal('show');
      return true;
    } else {
      console.warn('[ModalService] Bootstrap no disponible');
      return false;
    }
  }

  /**
   * Cierra un modal
   * @param {string} id - ID del elemento modal
   * @returns {boolean} true si el modal se cerró correctamente
   */
  function close(id) {
    const modal = document.getElementById(id);
    if (!modal) {
      console.warn('[ModalService] Modal no encontrado:', id);
      return false;
    }

    // Cerrar modal usando Bootstrap
    if (w.bootstrap && w.bootstrap.Modal) {
      const bsModal = w.bootstrap.Modal.getInstance(modal);
      if (bsModal) {
        bsModal.hide();
        return true;
      }
    } else if (w.jQuery && w.jQuery.fn && w.jQuery.fn.modal) {
      // Fallback a jQuery Bootstrap 4
      w.jQuery(modal).modal('hide');
      return true;
    }

    return false;
  }

  /**
   * Limpia el contenido de un modal (útil para resetear antes de abrir)
   * @param {string} id - ID del elemento modal
   */
  function clear(id) {
    const modal = document.getElementById(id);
    if (!modal) return;

    const bodyEl = modal.querySelector('.modal-body');
    if (bodyEl) {
      bodyEl.innerHTML = '';
    }

    // Resetear formularios dentro del modal
    const forms = modal.querySelectorAll('form');
    forms.forEach(form => form.reset());
  }

  // Exportar API pública
  w.ModalService = Object.freeze({
    open,
    close,
    clear
  });
})(window);
