/**
 * UI Module para Landing - Panel Informativo Read-Only
 */

(function() {
  'use strict';

  if (typeof window.landingAPI === 'undefined') {
    console.error('[landing.ui] landingAPI no está disponible. Cargar landing.api.js primero.');
    return;
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async function renderLanding(container) {
    if (!container) {
      console.error('[landing.ui] Container no encontrado');
      return;
    }

    container.innerHTML = '<div class="text-center text-muted py-4">Cargando información...</div>';

    try {
      const r = await window.landingAPI.getLandingResumen();

      if (!r.ok) {
        container.innerHTML = `<div class="alert alert-danger">Error ${r.status}: ${escapeHtml(r.data?.detail || 'Error desconocido')}</div>`;
        return;
      }

      const data = r.data || {};

      container.innerHTML = `
        <div class="card">
          <div class="card-header">
            <h5 class="card-title mb-0">🏠 Información del Tenant</h5>
          </div>
          <div class="card-body">
            <div id="landing-feedback" class="alert d-none" role="alert"></div>
            
            ${data.nombre ? `
            <div class="mb-3">
              <strong>Nombre:</strong><br>
              <span>${escapeHtml(data.nombre)}</span>
            </div>
            ` : ''}
            
            ${data.descripcion ? `
            <div class="mb-3">
              <strong>Descripción:</strong><br>
              <span>${escapeHtml(data.descripcion)}</span>
            </div>
            ` : ''}
            
            ${data.email_contacto ? `
            <div class="mb-3">
              <strong>Email de Contacto:</strong><br>
              <span>${escapeHtml(data.email_contacto)}</span>
            </div>
            ` : ''}
            
            ${data.telefono ? `
            <div class="mb-3">
              <strong>Teléfono:</strong><br>
              <span>${escapeHtml(data.telefono)}</span>
            </div>
            ` : ''}
          </div>
        </div>
      `;

    } catch (error) {
      console.error('[landing.ui] Error cargando landing:', error);
      container.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(error.message || 'Error desconocido')}</div>`;
    }
  }

  if (typeof window !== 'undefined') {
    window.landingUI = {
      renderLanding,
    };
  }
})();
