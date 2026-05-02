/**
 * UI Module para MailDigester - Renderizado y Eventos
 * 
 * Panel de control para ingesta de facturas desde correo.
 * Incluye: selector de config, límite de mensajes, botones iniciar/detener,
 * tabla de ejecuciones, polling automático.
 */

(function() {
  'use strict';

  // Asegurar que mailAPI esté disponible
  if (typeof window.mailAPI === 'undefined') {
    console.error('[mail.ui] mailAPI no está disponible. Cargar mail.api.js primero.');
    return;
  }

  let pollingInterval = null;

  /**
   * Escapa HTML para prevenir XSS
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Formatea fecha
   */
  function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('es-CO');
  }

  /**
   * Obtiene badge de estado
   */
  function getStatusBadge(status) {
    const badges = {
      'PENDING': '<span class="badge bg-secondary">Pendiente</span>',
      'RUNNING': '<span class="badge bg-primary">Ejecutando</span>',
      'SUCCESS': '<span class="badge bg-success">Éxito</span>',
      'FAILURE': '<span class="badge bg-danger">Error</span>',
      'CANCELED': '<span class="badge bg-warning">Cancelado</span>',
      'ABORTED': '<span class="badge bg-dark">Abortado</span>',
    };
    return badges[status] || `<span class="badge bg-secondary">${escapeHtml(status)}</span>`;
  }

  /**
   * Renderiza el panel de MailDigester
   * @param {HTMLElement} container - Contenedor donde renderizar
   */
  async function renderMailPanel(container) {
    if (!container) {
      console.error('[mail.ui] Container no encontrado');
      return;
    }

    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <h5 class="card-title mb-0">📧 MailDigester - Ingesta de Facturas desde Correo</h5>
        </div>
        <div class="card-body">
          <div id="mail-feedback" class="alert d-none" role="alert"></div>
          
          <!-- Controles -->
          <div class="row mb-3">
            <div class="col-md-6">
              <label for="mail-config-select" class="form-label">Configuración de Buzón</label>
              <select id="mail-config-select" class="form-select">
                <option value="">Cargando...</option>
              </select>
            </div>
            <div class="col-md-4">
              <label for="mail-limit-input" class="form-label">Límite de Mensajes</label>
              <input type="number" id="mail-limit-input" class="form-control" value="50" min="1" max="500" />
            </div>
            <div class="col-md-2 d-flex align-items-end">
              <button id="btn-mail-start" class="btn btn-primary w-100">Iniciar</button>
            </div>
          </div>

          <!-- Tabla de Ejecuciones -->
          <div class="table-responsive">
            <table id="mail-runs-table" class="table table-sm">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Config</th>
                  <th>Estado</th>
                  <th>Iniciado</th>
                  <th>Finalizado</th>
                  <th>Importados</th>
                  <th>Duplicados</th>
                  <th>Errores</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody id="mail-runs-tbody">
                <tr><td colspan="9" class="text-center text-muted">Cargando...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    // Bind eventos
    const btnStart = container.querySelector('#btn-mail-start');
    if (btnStart) {
      btnStart.addEventListener('click', handleStartRun);
    }

    // Cargar datos iniciales
    await loadConfigs();
    await loadRuns();

    // Iniciar polling
    startPolling();
  }

  /**
   * Carga configuraciones de buzones
   */
  async function loadConfigs() {
    const select = document.getElementById('mail-config-select');
    if (!select) return;

    try {
      const r = await window.mailAPI.listConfigs();
      if (!r.ok) {
        select.innerHTML = '<option value="">Error cargando configuraciones</option>';
        return;
      }

      const configs = Array.isArray(r.data) ? r.data : (r.data?.results || []);
      select.innerHTML = '<option value="">Selecciona una configuración...</option>';
      
      configs.forEach(cfg => {
        if (cfg.is_active) {
          const opt = document.createElement('option');
          opt.value = cfg.id;
          opt.textContent = `${cfg.nombre || 'Config'} (${cfg.email_address || cfg.username || ''})`;
          select.appendChild(opt);
        }
      });
    } catch (error) {
      console.error('[mail.ui] Error cargando configuraciones:', error);
      select.innerHTML = '<option value="">Error cargando configuraciones</option>';
    }
  }

  /**
   * Carga ejecuciones
   */
  async function loadRuns() {
    const tbody = document.getElementById('mail-runs-tbody');
    if (!tbody) return;

    try {
      const r = await window.mailAPI.listRuns();
      if (!r.ok) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-danger">Error cargando ejecuciones</td></tr>';
        return;
      }

      const runs = Array.isArray(r.data) ? r.data : (r.data?.results || []);
      tbody.innerHTML = '';

      if (runs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No hay ejecuciones</td></tr>';
        return;
      }

      runs.forEach(run => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${run.id || '-'}</td>
          <td>${escapeHtml(run.config_nombre || '-')}</td>
          <td>${getStatusBadge(run.status)}</td>
          <td>${formatDate(run.started_at)}</td>
          <td>${formatDate(run.finished_at)}</td>
          <td>${run.counts?.imported || 0}</td>
          <td>${run.counts?.duplicates || 0}</td>
          <td>${run.counts?.errors || 0}</td>
          <td>
            ${run.status === 'RUNNING' || run.status === 'PENDING' ? `
              <button class="btn btn-sm btn-warning" onclick="window.mailUI.stopRun(${run.id})">Detener</button>
            ` : ''}
            <button class="btn btn-sm btn-info" onclick="window.mailUI.showDetails(${run.id})">Detalles</button>
            ${run.status !== 'RUNNING' && run.status !== 'PENDING' ? `
              <button class="btn btn-sm btn-danger" onclick="window.mailUI.deleteRun(${run.id})">Eliminar</button>
            ` : ''}
          </td>
        `;
        tbody.appendChild(tr);
      });

      // Verificar si hay ejecuciones activas para continuar polling
      const hasActive = runs.some(r => r.status === 'RUNNING' || r.status === 'PENDING');
      if (!hasActive) {
        stopPolling();
      }

    } catch (error) {
      console.error('[mail.ui] Error cargando ejecuciones:', error);
      tbody.innerHTML = '<tr><td colspan="9" class="text-center text-danger">Error cargando ejecuciones</td></tr>';
    }
  }

  /**
   * Maneja el inicio de una ejecución
   */
  async function handleStartRun() {
    const configId = document.getElementById('mail-config-select')?.value;
    const limit = parseInt(document.getElementById('mail-limit-input')?.value || '50');
    const feedback = document.getElementById('mail-feedback');

    if (!configId) {
      if (feedback) {
        feedback.className = 'alert alert-warning';
        feedback.textContent = 'Selecciona una configuración de buzón';
        feedback.classList.remove('d-none');
      }
      return;
    }

    try {
      const r = await window.mailAPI.run(parseInt(configId), limit);
      if (!r.ok) {
        const errorMsg = r.data?.detail || r.data?.error || `Error ${r.status}`;
        if (feedback) {
          feedback.className = 'alert alert-danger';
          feedback.textContent = errorMsg;
          feedback.classList.remove('d-none');
        }
        return;
      }

      if (feedback) {
        feedback.className = 'alert alert-success';
        feedback.textContent = 'Ejecución iniciada correctamente';
        feedback.classList.remove('d-none');
      }

      // Recargar ejecuciones y reiniciar polling
      await loadRuns();
      startPolling();

    } catch (error) {
      console.error('[mail.ui] Error iniciando ejecución:', error);
      if (feedback) {
        feedback.className = 'alert alert-danger';
        feedback.textContent = `Error: ${error.message}`;
        feedback.classList.remove('d-none');
      }
    }
  }

  /**
   * Detiene una ejecución
   */
  async function stopRun(runId) {
    if (!confirm('¿Estás seguro de detener esta ejecución?')) {
      return;
    }

    try {
      const r = await window.mailAPI.stop(runId);
      if (!r.ok) {
        alert(r.data?.detail || `Error ${r.status}`);
        return;
      }

      await loadRuns();
    } catch (error) {
      console.error('[mail.ui] Error deteniendo ejecución:', error);
      alert(`Error: ${error.message}`);
    }
  }

  /**
   * Muestra detalles de una ejecución
   */
  async function showDetails(runId) {
    try {
      const r = await window.mailAPI.getRunDetails(runId);
      if (!r.ok) {
        alert(r.data?.detail || `Error ${r.status}`);
        return;
      }

      const details = r.data;
      const detailsHtml = `
        <div class="modal fade" id="mail-details-modal" tabindex="-1">
          <div class="modal-dialog modal-lg">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">Detalles de Ejecución #${runId}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <pre>${escapeHtml(JSON.stringify(details, null, 2))}</pre>
              </div>
            </div>
          </div>
        </div>
      `;
      
      document.body.insertAdjacentHTML('beforeend', detailsHtml);
      const modal = new bootstrap.Modal(document.getElementById('mail-details-modal'));
      modal.show();
      
      // Limpiar modal al cerrar
      document.getElementById('mail-details-modal').addEventListener('hidden.bs.modal', function() {
        this.remove();
      });

    } catch (error) {
      console.error('[mail.ui] Error obteniendo detalles:', error);
      alert(`Error: ${error.message}`);
    }
  }

  /**
   * Elimina una ejecución
   */
  async function deleteRun(runId) {
    if (!confirm('¿Estás seguro de eliminar esta ejecución?')) {
      return;
    }

    try {
      const r = await window.mailAPI.deleteRun(runId);
      if (!r.ok) {
        alert(r.data?.detail || `Error ${r.status}`);
        return;
      }

      await loadRuns();
    } catch (error) {
      console.error('[mail.ui] Error eliminando ejecución:', error);
      alert(`Error: ${error.message}`);
    }
  }

  /**
   * Inicia polling de ejecuciones
   */
  function startPolling() {
    if (pollingInterval) return; // Ya está activo

    pollingInterval = setInterval(async () => {
      await loadRuns();
    }, 5000); // Cada 5 segundos
  }

  /**
   * Detiene polling
   */
  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.mailUI = {
      renderMailPanel,
      loadConfigs,
      loadRuns,
      stopRun,
      showDetails,
      deleteRun,
      startPolling,
      stopPolling,
    };
  }
})();
