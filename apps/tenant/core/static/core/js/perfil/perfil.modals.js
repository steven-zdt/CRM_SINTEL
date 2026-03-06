/**
 * Modales para Perfil
 *
 * Maneja modal de editar perfil (solo edición, no create/delete).
 * Sigue el patrón canónico de Facturas.
 */

(function() {
  'use strict';

  if (typeof window.perfilAPI === 'undefined') {
    console.error('[perfil.modals] perfilAPI no está disponible. Cargar perfil.api.js primero.');
    return;
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function getErrorMessage(status, data) {
    if (status === 422) {
      return data?.message || data?.detail || 'Datos inválidos (422). Verifique los campos.';
    } else if (status === 400) {
      return data?.message || data?.detail || 'Error de validación (400).';
    } else if (status === 401 || status === 403) {
      return data?.detail || data?.message || 'No tienes permisos para realizar esta acción.';
    } else {
      return data?.detail || data?.message || `Error HTTP ${status}`;
    }
  }

  async function showEditModal() {
    const modal = document.getElementById('modal-perfil-edit');
    if (!modal) {
      console.error('[perfil.modals] Modal de editar no encontrado');
      return;
    }

    try {
      const r = await window.perfilAPI.getMiPerfil();
      
      if (!r.ok) {
        if (w.SintelFeedback) {
          w.SintelFeedback.handleAPIError(r, '[perfil.modals]');
        } else {
          if (w.SintelFeedback) {
          w.SintelFeedback.handleAPIError(r, '[perfil.modals]');
        } else {
          // ⚠️ v2.60: Usar UIManager para mostrar error
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError(r, '[perfil.modals]');
          }
        }
        }
        return;
      }

      const perfil = r.data;

      document.getElementById('perfil-edit-first_name').value = perfil.first_name || '';
      document.getElementById('perfil-edit-last_name').value = perfil.last_name || '';
      document.getElementById('perfil-edit-email').value = perfil.email || '';
      document.getElementById('perfil-edit-phone').value = perfil.phone || '';

      // Mostrar avatar actual si existe
      const avatarPreview = document.getElementById('perfil-edit-avatar-preview');
      if (avatarPreview) {
        if (perfil.avatar) {
          avatarPreview.innerHTML = `<img src="${escapeHtml(perfil.avatar)}" alt="Avatar actual" style="max-height: 100px;" />`;
        } else {
          avatarPreview.innerHTML = '';
        }
      }

      const feedback = document.getElementById('perfil-modal-feedback');
      if (feedback) {
        feedback.classList.add('d-none');
        feedback.textContent = '';
      }

    // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
    if (w.bootstrap && w.bootstrap.Modal) {
      const modalInstance = w.bootstrap.Modal.getOrCreateInstance(modal);
      modal.addEventListener('shown.bs.modal', function focusFirstInput() {
        const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
        if (firstInput) {
          firstInput.focus();
        }
        modal.removeEventListener('shown.bs.modal', focusFirstInput);
      }, { once: true });
      modalInstance.show();
    } else if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
      // Fallback: usar UIManager si Bootstrap no está disponible
      const modalId = modal.id ? `#${modal.id}` : null;
      if (modalId) {
        w.UIManager.handleModal(modalId, 'show');
      }
    }

    } catch (error) {
      console.error('[perfil.modals] Error cargando perfil:', error);
      if (w.SintelFeedback) {
        w.SintelFeedback.handleAPIError(error, '[perfil.modals]');
      } else {
        if (w.SintelFeedback) {
        w.SintelFeedback.handleAPIError(error, '[perfil.modals]');
      } else {
        // ⚠️ v2.60: Usar UIManager para mostrar error
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 500, data: { detail: error.message || 'Error desconocido' } }, '[perfil.modals]');
        }
      }
      }
    }
  }

  async function handleConfirm() {
    const feedback = document.getElementById('perfil-modal-feedback');

    const formData = {
      first_name: document.getElementById('perfil-edit-first_name')?.value.trim() || null,
      last_name: document.getElementById('perfil-edit-last_name')?.value.trim() || null,
      email: document.getElementById('perfil-edit-email')?.value.trim() || null,
      phone: document.getElementById('perfil-edit-phone')?.value.trim() || null,
    };

    try {
      // Actualizar perfil básico
      const r = await window.perfilAPI.updateMiPerfil(formData);

      if (!r.ok) {
        const errorMsg = getErrorMessage(r.status, r.data);
        if (feedback) {
          feedback.className = 'alert alert-danger';
          feedback.textContent = errorMsg;
          feedback.classList.remove('d-none');
        }
        return;
      }

      // Si hay avatar, actualizarlo por separado
      const avatarFile = document.getElementById('perfil-edit-avatar')?.files[0];
      if (avatarFile) {
        const avatarR = await window.perfilAPI.updateMiPerfilAvatar(avatarFile);
        if (!avatarR.ok) {
          if (feedback) {
            feedback.className = 'alert alert-warning';
            feedback.textContent = 'Perfil actualizado, pero hubo un error al actualizar el avatar';
            feedback.classList.remove('d-none');
          }
          return;
        }
      }

      if (feedback) {
        feedback.className = 'alert alert-success';
        feedback.textContent = 'Perfil actualizado correctamente';
        feedback.classList.remove('d-none');
      }

      setTimeout(() => {
        const modal = document.getElementById('modal-perfil-edit');
        if (modal) {
          // ⚠️ v2.60: Usar UIManager para cerrar modal
          if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
            const modalId = modal.id ? `#${modal.id}` : null;
            if (modalId) {
              w.UIManager.handleModal(modalId, 'hide');
            }
          }
        }

        // Recargar perfil
        if (typeof window.perfilUI !== 'undefined' && window.perfilUI.reloadPerfil) {
          window.perfilUI.reloadPerfil();
        }
      }, 1500);

    } catch (error) {
      console.error('[perfil.modals] Error guardando:', error);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error: ${error.message || 'Error desconocido'}`;
        feedback.classList.remove('d-none');
      }
    }
  }

  function initModalEvents() {
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest('button[data-action="confirm"]');
      if (btn && btn.closest('#modal-perfil-edit')) {
        ev.preventDefault();
        handleConfirm();
      }

      const modalOpenBtn = ev.target.closest('[data-modal-open]');
      if (modalOpenBtn) {
        const target = modalOpenBtn.dataset.modalOpen;
        if (target === '#modal-perfil-edit') {
          ev.preventDefault();
          showEditModal();
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initModalEvents);
  } else {
    initModalEvents();
  }

  if (typeof window !== 'undefined') {
    window.perfilModals = {
      showEditModal,
      handleConfirm,
    };
  }
})();
