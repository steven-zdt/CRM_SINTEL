/**
 * Modales para MailDigester
 *
 * Maneja modales especiales de ejecución (run, stop, details).
 * Sigue el patrón canónico de Facturas.
 */

(function() {
  'use strict';

  if (typeof window.mailAPI === 'undefined') {
    console.error('[mail.modals] mailAPI no está disponible. Cargar mail.api.js primero.');
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
      return data?.message || data?.detail || 'Ejecución duplicada o en curso (409).';
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

  async function showRunModal() {
    const modal = document.getElementById('modal-mail-run-confirm');
    if (!modal) {
      console.error('[mail.modals] Modal de iniciar ingesta no encontrado');
      return;
    }

    // Cargar configuraciones disponibles
    try {
      const r = await window.mailAPI.listConfigs();
      const configSelect = document.getElementById('mail-run-config-id');
      
      if (configSelect) {
        configSelect.innerHTML = '<option value="">Seleccione una configuración...</option>';
        
        if (r.ok && r.data) {
          const configs = Array.isArray(r.data) ? r.data : (r.data.results || []);
          configs.forEach(config => {
            const option = document.createElement('option');
            option.value = config.id;
            option.textContent = `${config.email_address || config.email} (${config.provider || 'IMAP'})`;
            configSelect.appendChild(option);
          });
        }
      }
    } catch (error) {
      console.error('[mail.modals] Error cargando configuraciones:', error);
    }

    const form = document.getElementById('form-mail-run');
    if (form) {
      form.reset();
      document.getElementById('mail-run-limit').value = '50';
    }
    
    const feedback = document.getElementById('mail-run-modal-feedback');
    if (feedback) {
      feedback.classList.add('d-none');
      feedback.textContent = '';
    }

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
  }

  async function showStopModal(runId) {
    const modal = document.getElementById('modal-mail-stop-confirm');
    if (!modal) {
      console.error('[mail.modals] Modal de detener ingesta no encontrado');
      return;
    }

    document.getElementById('mail-stop-run-id').value = runId || '';
    document.getElementById('mail-stop-force').checked = false;
    
    const feedback = document.getElementById('mail-stop-modal-feedback');
    if (feedback) {
      feedback.classList.add('d-none');
      feedback.textContent = '';
    }

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
  }

  async function showDetailsModal(runId) {
    const modal = document.getElementById('modal-mail-details');
    if (!modal) {
      console.error('[mail.modals] Modal de detalles no encontrado');
      return;
    }

    const content = document.getElementById('mail-details-content');
    if (!content) return;

    content.innerHTML = '<div class="text-center text-muted py-4">Cargando...</div>';

    try {
      const r = await window.mailAPI.getRunDetails(runId);
      
      if (!r.ok) {
        content.innerHTML = `<div class="alert alert-danger">${getErrorMessage(r.status, r.data)}</div>`;
        return;
      }

      const run = r.data;
      const fechaInicio = run.fecha_inicio ? new Date(run.fecha_inicio).toLocaleString('es-CO') : '-';
      const fechaFin = run.fecha_fin ? new Date(run.fecha_fin).toLocaleString('es-CO') : '-';
      
      let statusBadge = '';
      if (run.estado === 'COMPLETADO') {
        statusBadge = '<span class="badge bg-success">Completado</span>';
      } else if (run.estado === 'EN_PROCESO') {
        statusBadge = '<span class="badge bg-primary">En Proceso</span>';
      } else if (run.estado === 'DETENIDO') {
        statusBadge = '<span class="badge bg-warning">Detenido</span>';
      } else if (run.estado === 'ERROR') {
        statusBadge = '<span class="badge bg-danger">Error</span>';
      } else {
        statusBadge = `<span class="badge bg-secondary">${escapeHtml(run.estado || '-')}</span>`;
      }

      content.innerHTML = `
        <div class="row">
          <div class="col-md-6 mb-3">
            <strong>Estado:</strong><br>
            ${statusBadge}
          </div>
          <div class="col-md-6 mb-3">
            <strong>Configuración:</strong><br>
            <span>${escapeHtml(run.config_email || run.config_id || '-')}</span>
          </div>
          <div class="col-md-6 mb-3">
            <strong>Fecha Inicio:</strong><br>
            <span>${fechaInicio}</span>
          </div>
          ${run.fecha_fin ? `
          <div class="col-md-6 mb-3">
            <strong>Fecha Fin:</strong><br>
            <span>${fechaFin}</span>
          </div>
          ` : ''}
          <div class="col-md-6 mb-3">
            <strong>Mensajes Procesados:</strong><br>
            <span>${run.total_procesados || 0}</span>
          </div>
          <div class="col-md-6 mb-3">
            <strong>Facturas Creadas:</strong><br>
            <span>${run.facturas_creadas || 0}</span>
          </div>
          ${run.errores && run.errores.length > 0 ? `
          <div class="col-md-12 mb-3">
            <strong>Errores:</strong><br>
            <div class="alert alert-danger">
              <pre>${escapeHtml(JSON.stringify(run.errores, null, 2))}</pre>
            </div>
          </div>
          ` : ''}
          ${run.logs && run.logs.length > 0 ? `
          <div class="col-md-12 mb-3">
            <strong>Logs:</strong><br>
            <div class="border p-3" style="max-height: 300px; overflow-y: auto;">
              <pre class="small">${escapeHtml(run.logs.join('\n'))}</pre>
            </div>
          </div>
          ` : ''}
        </div>
      `;

      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();

    } catch (error) {
      console.error('[mail.modals] Error cargando detalles:', error);
      content.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(error.message || 'Error desconocido')}</div>`;
    }
  }

  async function handleConfirmRun() {
    const feedback = document.getElementById('mail-run-modal-feedback');
    const configId = parseInt(document.getElementById('mail-run-config-id')?.value);
    const limit = parseInt(document.getElementById('mail-run-limit')?.value || '50');

    if (!configId) {
      if (feedback) {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Por favor selecciona una configuración de buzón';
        feedback.classList.remove('d-none');
      }
      return;
    }

    try {
      const r = await window.mailAPI.run(configId, limit);

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
        feedback.textContent = 'Ingesta iniciada correctamente. Revisa el panel para ver el progreso.';
        feedback.classList.remove('d-none');
      }

      setTimeout(() => {
        const modal = document.getElementById('modal-mail-run-confirm');
        if (modal) {
          const bsModal = bootstrap.Modal.getInstance(modal);
          if (bsModal) bsModal.hide();
        }

        // Recargar lista de ejecuciones
        if (typeof window.mailUI !== 'undefined' && window.mailUI.reloadRunsList) {
          window.mailUI.reloadRunsList();
        }
      }, 2000);

    } catch (error) {
      console.error('[mail.modals] Error iniciando ingesta:', error);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error: ${error.message || 'Error desconocido'}`;
        feedback.classList.remove('d-none');
      }
    }
  }

  async function handleConfirmStop() {
    const feedback = document.getElementById('mail-stop-modal-feedback');
    const runId = parseInt(document.getElementById('mail-stop-run-id')?.value);
    const force = document.getElementById('mail-stop-force')?.checked || false;

    if (!runId) {
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = 'ID de ejecución no válido';
        feedback.classList.remove('d-none');
      }
      return;
    }

    try {
      const r = await window.mailAPI.stop(runId, force);

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
        feedback.textContent = 'Ejecución detenida correctamente';
        feedback.classList.remove('d-none');
      }

      setTimeout(() => {
        const modal = document.getElementById('modal-mail-stop-confirm');
        if (modal) {
          const bsModal = bootstrap.Modal.getInstance(modal);
          if (bsModal) bsModal.hide();
        }

        // Recargar lista de ejecuciones
        if (typeof window.mailUI !== 'undefined' && window.mailUI.reloadRunsList) {
          window.mailUI.reloadRunsList();
        }
      }, 1500);

    } catch (error) {
      console.error('[mail.modals] Error deteniendo ingesta:', error);
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
      if (btn) {
        const kind = btn.dataset.kind; // 'run' o 'stop'

        if (kind === 'run' && btn.closest('#modal-mail-run-confirm')) {
          ev.preventDefault();
          handleConfirmRun();
        } else if (kind === 'stop' && btn.closest('#modal-mail-stop-confirm')) {
          ev.preventDefault();
          handleConfirmStop();
        }
      }

      const modalOpenBtn = ev.target.closest('[data-modal-open]');
      if (modalOpenBtn) {
        const target = modalOpenBtn.dataset.modalOpen;
        if (target === '#modal-mail-run-confirm') {
          ev.preventDefault();
          showRunModal();
        } else if (target === '#modal-mail-stop-confirm') {
          const runId = parseInt(modalOpenBtn.dataset.runId);
          if (runId) {
            ev.preventDefault();
            showStopModal(runId);
          }
        } else if (target === '#modal-mail-details') {
          const runId = parseInt(modalOpenBtn.dataset.runId);
          if (runId) {
            ev.preventDefault();
            showDetailsModal(runId);
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
    window.mailModals = {
      showRunModal,
      showStopModal,
      showDetailsModal,
      handleConfirmRun,
      handleConfirmStop,
    };
  }
})();
