/**
 * UI Module para Dashboard - Renderizado
 * 
 * Panel consolidado read-only que muestra resumen de múltiples apps.
 */

(function() {
  'use strict';

  if (typeof window.dashboardAPI === 'undefined') {
    console.error('[dashboard.ui] dashboardAPI no está disponible. Cargar dashboard.api.js primero.');
    return;
  }

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
   * Formatea dinero
   */
  function fmtMoney(value, currency = 'COP') {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: currency,
    }).format(Number(value || 0));
  }

  /**
   * Renderiza el panel de dashboard
   * @param {HTMLElement} container - Contenedor donde renderizar
   */
  async function renderDashboard(container) {
    if (!container) {
      console.error('[dashboard.ui] Container no encontrado');
      return;
    }

    container.innerHTML = '<div class="text-center text-muted py-4">Cargando dashboard...</div>';

    try {
      const r = await window.dashboardAPI.getDashboard();

      if (!r.ok) {
        container.innerHTML = `<div class="alert alert-danger">Error ${r.status}: ${escapeHtml(r.data?.detail || 'Error desconocido')}</div>`;
        return;
      }

      const data = r.data;
      
      // Renderizar tarjetas de resumen
      container.innerHTML = `
        <div class="row g-3">
          ${data.empresa ? `
          <div class="col-md-6 col-lg-3">
            <div class="card">
              <div class="card-body">
                <h6 class="card-title">🏢 Empresa</h6>
                <p class="mb-0">${escapeHtml(data.empresa.razon_social || 'No configurada')}</p>
              </div>
            </div>
          </div>
          ` : ''}
          ${data.facturas ? `
          <div class="col-md-6 col-lg-3">
            <div class="card">
              <div class="card-body">
                <h6 class="card-title">🧾 Facturas</h6>
                <p class="mb-0">Total: ${data.facturas.total || 0}</p>
                <small class="text-muted">Ventas: ${data.facturas.ventas || 0} | Compras: ${data.facturas.compras || 0}</small>
              </div>
            </div>
          </div>
          ` : ''}
          ${data.contabilidad ? `
          <div class="col-md-6 col-lg-3">
            <div class="card">
              <div class="card-body">
                <h6 class="card-title">📚 Contabilidad</h6>
                <p class="mb-0">Cuentas: ${data.contabilidad.total_cuentas || 0}</p>
                <small class="text-muted">Asientos: ${data.contabilidad.total_asientos || 0}</small>
              </div>
            </div>
          </div>
          ` : ''}
          ${data.perfil ? `
          <div class="col-md-6 col-lg-3">
            <div class="card">
              <div class="card-body">
                <h6 class="card-title">👤 Perfil</h6>
                <p class="mb-0">${escapeHtml(data.perfil.nombre || 'Usuario')}</p>
                <small class="text-muted">${escapeHtml(data.perfil.email || '')}</small>
              </div>
            </div>
          </div>
          ` : ''}
        </div>
      `;

    } catch (error) {
      console.error('[dashboard.ui] Error cargando dashboard:', error);
      container.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(error.message || 'Error desconocido')}</div>`;
    }
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.dashboardUI = {
      renderDashboard,
    };
  }
})();
