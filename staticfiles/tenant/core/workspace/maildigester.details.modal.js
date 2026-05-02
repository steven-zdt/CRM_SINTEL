/**
 * Modal de detalles de ejecución de ingesta.
 * 
 * ⚠️ API-First: Consume /api/v1/core/maildigester/run/{id}/details/
 */

(function() {
  'use strict';

  const RUN_DETAILS_API = (runId) => `/api/v1/core/maildigester/run/${runId}/details/`;

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function getStatusBadgeClass(status) {
    switch (status) {
      case 'imported': return 'success';
      case 'duplicate': return 'warning';
      case 'error': return 'danger';
      default: return 'secondary';
    }
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return 'N/A';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  async function loadDetails(runId) {
    const contentEl = document.getElementById('run-details-content');
    if (!contentEl) return;

    contentEl.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Cargando...</span></div></div>';

    try {
      const res = await fetch(RUN_DETAILS_API(runId), {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      });

      if (!res.ok) {
        contentEl.innerHTML = `<div class="alert alert-danger">Error al cargar detalles (${res.status})</div>`;
        return;
      }

      const data = await res.json();
      const xmlItems = data.xml_items || [];

      let html = `
        <div class="mb-3">
          <h6>Estado: <span class="badge bg-${data.status === 'SUCCESS' ? 'success' : data.status === 'FAILURE' ? 'danger' : 'secondary'}">${escapeHtml(data.status)}</span></h6>
          <p class="mb-0"><strong>XMLs detectados:</strong> ${xmlItems.length}</p>
        </div>
      `;

      if (xmlItems.length > 0) {
        html += `
          <div class="table-responsive">
            <table class="table table-sm table-hover">
              <thead>
                <tr>
                  <th>Archivo</th>
                  <th>Tamaño</th>
                  <th>Estado</th>
                  <th>Origen</th>
                  <th>Mensaje</th>
                </tr>
              </thead>
              <tbody>
        `;

        xmlItems.forEach(item => {
          const statusClass = getStatusBadgeClass(item.status);
          const sourceKind = item.source_kind || 'unknown';
          html += `
            <tr>
              <td><code>${escapeHtml(item.filename || 'N/A')}</code></td>
              <td>${formatBytes(item.size)}</td>
              <td><span class="badge bg-${statusClass}">${escapeHtml(item.status || 'unknown')}</span></td>
              <td><small class="text-muted">${escapeHtml(sourceKind)}</small></td>
              <td>${escapeHtml(item.message || '')}</td>
            </tr>
          `;
        });

        html += `
              </tbody>
            </table>
          </div>
        `;
      } else {
        html += '<p class="text-muted">No se detectaron XMLs en esta ejecución.</p>';
      }

      contentEl.innerHTML = html;
    } catch (err) {
      console.error('[maildigester.details] Error cargando detalles:', err);
      contentEl.innerHTML = `<div class="alert alert-danger">Error de red: ${err.message}</div>`;
    }
  }

  function showDetails(runId) {
    const modalEl = document.getElementById('modal-mail-run-details');
    if (!modalEl) {
      console.error('[maildigester.details] Modal no encontrado');
      return;
    }

    // Cargar detalles
    loadDetails(runId);

    // Mostrar modal
    if (window.bootstrap && bootstrap.Modal) {
      const modal = new bootstrap.Modal(modalEl);
      modal.show();

      // Gestionar foco al abrir
      modalEl.addEventListener('shown.bs.modal', () => {
        const firstFocusable = modalEl.querySelector('h6, .badge, table');
        if (firstFocusable) {
          firstFocusable.focus();
        }
      }, { once: true });

      // Cerrar con ESC
      modalEl.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          modal.hide();
        }
      });
    }
  }

  // Exponer función global
  if (typeof window !== 'undefined') {
    window.maildigesterDetails = {
      showDetails: showDetails
    };
  }
})();
