/**
 * Modales para Contabilidad (Cuentas y Asientos)
 *
 * Maneja modales de crear, editar, detalle y eliminar para cuentas y asientos.
 * Sigue el patrón canónico de Facturas.
 */

(function() {
  'use strict';

  if (typeof window.contabilidadAPI === 'undefined') {
    console.error('[contabilidad.modals] contabilidadAPI no está disponible. Cargar contabilidad.api.js primero.');
    return;
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function getErrorMessage(status, data) {
    if (status === 409) {
      return data?.message || data?.detail || 'Registro duplicado (409).';
    } else if (status === 422) {
      return data?.message || data?.detail || 'Datos inválidos (422). Verifique los campos.';
    } else if (status === 400) {
      return data?.message || data?.detail || 'Error de validación (400).';
    } else if (status === 401 || status === 403) {
      return data?.detail || data?.message || 'No tienes permisos para realizar esta acción.';
    } else {
      return data?.detail || data?.message || `Error HTTP ${status}`;
    }
  }

  // ========== CUENTAS ==========

  function showCreateCuentaModal() {
    const modal = document.getElementById('modal-cuenta-create');
    if (!modal) {
      console.error('[contabilidad.modals] Modal de crear cuenta no encontrado');
      return;
    }

    const form = document.getElementById('form-cuenta-create');
    if (form) form.reset();
    
    const feedback = document.getElementById('cuenta-modal-feedback');
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
  }

  async function showEditCuentaModal(cuentaId) {
    const modal = document.getElementById('modal-cuenta-edit');
    if (!modal) {
      console.error('[contabilidad.modals] Modal de editar cuenta no encontrado');
      return;
    }

    try {
      const r = await window.contabilidadAPI.getCuenta(cuentaId);
      
      if (!r.ok) {
        if (w.SintelFeedback) {
          w.SintelFeedback.handleAPIError(r, '[contabilidad.modals]');
        } else {
          if (w.SintelFeedback) {
          w.SintelFeedback.handleAPIError(r, '[contabilidad.modals]');
        } else {
          // ⚠️ v2.60: Usar UIManager para mostrar error
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError(r, '[contabilidad.modals]');
          }
        }
        }
        return;
      }

      const cuenta = r.data;

      document.getElementById('cuenta-edit-id').value = cuenta.id || '';
      document.getElementById('cuenta-edit-codigo').value = cuenta.codigo || '';
      document.getElementById('cuenta-edit-nombre').value = cuenta.nombre || '';
      document.getElementById('cuenta-edit-tipo').value = cuenta.tipo || '';
      document.getElementById('cuenta-edit-descripcion').value = cuenta.descripcion || '';

      const feedback = document.getElementById('cuenta-modal-feedback');
      if (feedback) {
        feedback.classList.add('d-none');
        feedback.textContent = '';
      }

      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();

    } catch (error) {
      console.error('[contabilidad.modals] Error cargando cuenta:', error);
      if (w.SintelFeedback) {
        w.SintelFeedback.handleAPIError(error, '[contabilidad.modals]');
      } else {
        if (w.SintelFeedback) {
        w.SintelFeedback.handleAPIError(error, '[contabilidad.modals]');
      } else {
        if (w.SintelFeedback) {
          w.SintelFeedback.handleAPIError(error, '[contabilidad.modals]');
        } else {
          // ⚠️ v2.60: Usar UIManager para mostrar error
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 500, data: { detail: error.message || 'Error desconocido' } }, '[contabilidad.modals]');
        }
        }
      }
      }
    }
  }

  async function showDetailCuentaModal(cuentaId) {
    const modal = document.getElementById('modal-cuenta-detail');
    if (!modal) {
      console.error('[contabilidad.modals] Modal de detalle cuenta no encontrado');
      return;
    }

    const content = document.getElementById('cuenta-detail-content');
    if (!content) return;

    content.innerHTML = '<div class="text-center text-muted py-4">Cargando...</div>';

    try {
      const r = await window.contabilidadAPI.getCuenta(cuentaId);
      
      if (!r.ok) {
        content.innerHTML = `<div class="alert alert-danger">${getErrorMessage(r.status, r.data)}</div>`;
        return;
      }

      const cuenta = r.data;

      content.innerHTML = `
        <div class="row">
          <div class="col-md-6 mb-3">
            <strong>Código:</strong><br>
            <span>${escapeHtml(cuenta.codigo || '-')}</span>
          </div>
          <div class="col-md-6 mb-3">
            <strong>Nombre:</strong><br>
            <span>${escapeHtml(cuenta.nombre || '-')}</span>
          </div>
          <div class="col-md-6 mb-3">
            <strong>Tipo:</strong><br>
            <span>${escapeHtml(cuenta.tipo || '-')}</span>
          </div>
          ${cuenta.descripcion ? `
          <div class="col-md-12 mb-3">
            <strong>Descripción:</strong><br>
            <span>${escapeHtml(cuenta.descripcion)}</span>
          </div>
          ` : ''}
        </div>
      `;

      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();

    } catch (error) {
      console.error('[contabilidad.modals] Error cargando detalle cuenta:', error);
      content.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(error.message || 'Error desconocido')}</div>`;
    }
  }

  async function confirmDeleteCuenta(cuentaId, onSuccess, onError) {
    const message = '⚠️ Esta cuenta será eliminada.\n\nEsta acción es irreversible.\n\n¿Deseas continuar?';

    if (!confirm(message)) {
      return;
    }

    try {
      const r = await window.contabilidadAPI.deleteCuenta(cuentaId);

      if (!r.ok) {
        const errorMsg = getErrorMessage(r.status, r.data);
        if (onError) onError(errorMsg);
        return;
      }

      if (onSuccess) onSuccess();

    } catch (error) {
      console.error('[contabilidad.modals] Error eliminando cuenta:', error);
      if (onError) onError(error.message || 'Error desconocido');
    }
  }

  async function handleConfirmCuenta(kind) {
    const feedback = document.getElementById('cuenta-modal-feedback');
    const isEdit = kind === 'edit';

    const prefix = isEdit ? 'cuenta-edit' : 'cuenta-create';
    const formData = {
      codigo: document.getElementById(`${prefix}-codigo`)?.value.trim(),
      nombre: document.getElementById(`${prefix}-nombre`)?.value.trim(),
      tipo: document.getElementById(`${prefix}-tipo`)?.value || null,
      descripcion: document.getElementById(`${prefix}-descripcion`)?.value.trim() || null,
    };

    if (!formData.codigo || !formData.nombre || !formData.tipo) {
      if (feedback) {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Por favor completa todos los campos requeridos';
        feedback.classList.remove('d-none');
      }
      return;
    }

    try {
      let r;
      if (isEdit) {
        const cuentaId = parseInt(document.getElementById('cuenta-edit-id')?.value);
        if (!cuentaId) {
          if (feedback) {
            feedback.className = 'alert alert-danger';
            feedback.textContent = 'ID de cuenta no válido';
            feedback.classList.remove('d-none');
          }
          return;
        }
        r = await window.contabilidadAPI.updateCuenta(cuentaId, formData);
      } else {
        r = await window.contabilidadAPI.createCuenta(formData);
      }

      if (!r.ok) {
        const errorMsg = getErrorMessage(r.status, r.data);
        if (feedback) {
          feedback.className = 'alert alert-danger';
          feedback.textContent = errorMsg;
          feedback.classList.remove('d-none');
        }
        return;
      }

      if (feedback) {
        feedback.className = 'alert alert-success';
        feedback.textContent = isEdit ? 'Cuenta actualizada correctamente' : 'Cuenta creada correctamente';
        feedback.classList.remove('d-none');
      }

      setTimeout(() => {
        const modalId = isEdit ? 'modal-cuenta-edit' : 'modal-cuenta-create';
        const modal = document.getElementById(modalId);
        if (modal) {
          // ⚠️ v2.60: Usar UIManager para cerrar modal
          if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
            const modalId = modal.id ? `#${modal.id}` : null;
            if (modalId) {
              w.UIManager.handleModal(modalId, 'hide');
            }
          }
        }

        if (typeof window.contabilidadUI !== 'undefined' && window.contabilidadUI.reloadCuentasList) {
          window.contabilidadUI.reloadCuentasList();
        }
      }, 1500);

    } catch (error) {
      console.error('[contabilidad.modals] Error guardando cuenta:', error);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error: ${error.message || 'Error desconocido'}`;
        feedback.classList.remove('d-none');
      }
    }
  }

  // ========== ASIENTOS ==========

  function showCreateAsientoModal() {
    const modal = document.getElementById('modal-asiento-create');
    if (!modal) {
      console.error('[contabilidad.modals] Modal de crear asiento no encontrado');
      return;
    }

    const form = document.getElementById('form-asiento-create');
    if (form) {
      form.reset();
      const fechaInput = document.getElementById('asiento-create-fecha');
      if (fechaInput && !fechaInput.value) {
        fechaInput.value = new Date().toISOString().split('T')[0];
      }
    }
    
    const feedback = document.getElementById('asiento-modal-feedback');
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
  }

  async function showDetailAsientoModal(asientoId) {
    const modal = document.getElementById('modal-asiento-detail');
    if (!modal) {
      console.error('[contabilidad.modals] Modal de detalle asiento no encontrado');
      return;
    }

    const content = document.getElementById('asiento-detail-content');
    if (!content) return;

    content.innerHTML = '<div class="text-center text-muted py-4">Cargando...</div>';

    try {
      const r = await window.contabilidadAPI.getAsiento(asientoId);
      
      if (!r.ok) {
        content.innerHTML = `<div class="alert alert-danger">${getErrorMessage(r.status, r.data)}</div>`;
        return;
      }

      const asiento = r.data;
      const fecha = asiento.fecha ? new Date(asiento.fecha).toLocaleDateString('es-CO') : '-';

      content.innerHTML = `
        <div class="row">
          <div class="col-md-6 mb-3">
            <strong>Número:</strong><br>
            <span>${escapeHtml(asiento.numero || '-')}</span>
          </div>
          <div class="col-md-6 mb-3">
            <strong>Fecha:</strong><br>
            <span>${fecha}</span>
          </div>
          <div class="col-md-12 mb-3">
            <strong>Descripción:</strong><br>
            <span>${escapeHtml(asiento.descripcion || '-')}</span>
          </div>
          ${asiento.movimientos && asiento.movimientos.length > 0 ? `
          <div class="col-md-12 mb-3">
            <strong>Movimientos:</strong><br>
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>Cuenta</th>
                  <th>Debe</th>
                  <th>Haber</th>
                </tr>
              </thead>
              <tbody>
                ${asiento.movimientos.map(m => `
                  <tr>
                    <td>${escapeHtml(m.cuenta_codigo || '-')}</td>
                    <td class="text-end">${m.debe ? new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(m.debe) : '-'}</td>
                    <td class="text-end">${m.haber ? new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(m.haber) : '-'}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
          ` : ''}
        </div>
      `;

      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();

    } catch (error) {
      console.error('[contabilidad.modals] Error cargando detalle asiento:', error);
      content.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(error.message || 'Error desconocido')}</div>`;
    }
  }

  async function handleConfirmAsiento(kind) {
    const feedback = document.getElementById('asiento-modal-feedback');
    const isEdit = kind === 'edit';

    const prefix = isEdit ? 'asiento-edit' : 'asiento-create';
    const formData = {
      fecha: document.getElementById(`${prefix}-fecha`)?.value || '',
      numero: document.getElementById(`${prefix}-numero`)?.value.trim() || null,
      descripcion: document.getElementById(`${prefix}-descripcion`)?.value.trim() || '',
    };

    if (!formData.fecha || !formData.descripcion) {
      if (feedback) {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Por favor completa todos los campos requeridos';
        feedback.classList.remove('d-none');
      }
      return;
    }

    try {
      let r;
      if (isEdit) {
        const asientoId = parseInt(document.getElementById('asiento-edit-id')?.value);
        if (!asientoId) {
          if (feedback) {
            feedback.className = 'alert alert-danger';
            feedback.textContent = 'ID de asiento no válido';
            feedback.classList.remove('d-none');
          }
          return;
        }
        r = await window.contabilidadAPI.updateAsiento(asientoId, formData);
      } else {
        r = await window.contabilidadAPI.createAsiento(formData);
      }

      if (!r.ok) {
        const errorMsg = getErrorMessage(r.status, r.data);
        if (feedback) {
          feedback.className = 'alert alert-danger';
          feedback.textContent = errorMsg;
          feedback.classList.remove('d-none');
        }
        return;
      }

      if (feedback) {
        feedback.className = 'alert alert-success';
        feedback.textContent = isEdit ? 'Asiento actualizado correctamente' : 'Asiento creado correctamente';
        feedback.classList.remove('d-none');
      }

      setTimeout(() => {
        const modalId = isEdit ? 'modal-asiento-edit' : 'modal-asiento-create';
        const modal = document.getElementById(modalId);
        if (modal) {
          // ⚠️ v2.60: Usar UIManager para cerrar modal
          if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
            const modalId = modal.id ? `#${modal.id}` : null;
            if (modalId) {
              w.UIManager.handleModal(modalId, 'hide');
            }
          }
        }

        if (typeof window.contabilidadUI !== 'undefined' && window.contabilidadUI.reloadAsientosList) {
          window.contabilidadUI.reloadAsientosList();
        }
      }, 1500);

    } catch (error) {
      console.error('[contabilidad.modals] Error guardando asiento:', error);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error: ${error.message || 'Error desconocido'}`;
        feedback.classList.remove('d-none');
      }
    }
  }

  // ========== EVENTOS ==========

  function initModalEvents() {
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest('button[data-action="confirm"]');
      if (btn) {
        const entity = btn.dataset.entity; // 'cuenta' o 'asiento'
        const kind = btn.dataset.kind; // 'create' o 'edit'

        if (entity === 'cuenta' && btn.closest('#modal-cuenta-create, #modal-cuenta-edit')) {
          ev.preventDefault();
          handleConfirmCuenta(kind);
        } else if (entity === 'asiento' && btn.closest('#modal-asiento-create, #modal-asiento-edit')) {
          ev.preventDefault();
          handleConfirmAsiento(kind);
        }
      }

      const modalOpenBtn = ev.target.closest('[data-modal-open]');
      if (modalOpenBtn) {
        const target = modalOpenBtn.dataset.modalOpen;
        if (target === '#modal-cuenta-create') {
          ev.preventDefault();
          showCreateCuentaModal();
        } else if (target === '#modal-cuenta-edit') {
          const cuentaId = parseInt(modalOpenBtn.dataset.cuentaId);
          if (cuentaId) {
            ev.preventDefault();
            showEditCuentaModal(cuentaId);
          }
        } else if (target === '#modal-cuenta-detail') {
          const cuentaId = parseInt(modalOpenBtn.dataset.cuentaId);
          if (cuentaId) {
            ev.preventDefault();
            showDetailCuentaModal(cuentaId);
          }
        } else if (target === '#modal-asiento-create') {
          ev.preventDefault();
          showCreateAsientoModal();
        } else if (target === '#modal-asiento-detail') {
          const asientoId = parseInt(modalOpenBtn.dataset.asientoId);
          if (asientoId) {
            ev.preventDefault();
            showDetailAsientoModal(asientoId);
          }
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
    window.contabilidadModals = {
      showCreateCuentaModal,
      showEditCuentaModal,
      showDetailCuentaModal,
      confirmDeleteCuenta,
      handleConfirmCuenta,
      showCreateAsientoModal,
      showDetailAsientoModal,
      handleConfirmAsiento,
    };
  }
})();
