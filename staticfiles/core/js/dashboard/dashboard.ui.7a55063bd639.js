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

  function fmtNumber(value) {
    return new Intl.NumberFormat('es-CO').format(Number(value || 0));
  }

  function metricCard(label, value, detail) {
    return `
      <article class="metric-card">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
        <small>${escapeHtml(detail)}</small>
      </article>
    `;
  }

  function timelineItem(iconClass, title, description, meta) {
    return `
      <div class="timeline-item">
        <div class="timeline-badge"><i class="${escapeHtml(iconClass)}"></i></div>
        <div>
          <strong>${escapeHtml(title)}</strong>
          <p>${escapeHtml(description)}</p>
          <small>${escapeHtml(meta)}</small>
        </div>
      </div>
    `;
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

    container.innerHTML = '<div class="text-center text-muted py-4">Cargando indicadores del dashboard...</div>';

    try {
      const r = await window.dashboardAPI.getDashboard();

      if (!r.ok) {
        container.innerHTML = `<div class="alert alert-danger">Error ${r.status}: ${escapeHtml(r.data?.detail || 'Error desconocido')}</div>`;
        return;
      }

      const data = r.data || {};
      const empresa = data.empresa || {};
      const facturas = data.facturas || {};
      const contabilidad = data.contabilidad || {};
      const perfil = data.perfil || {};

      const facturasTotal = facturas.total || 0;
      const ventasTotal = facturas.ventas || 0;
      const comprasTotal = facturas.compras || 0;
      const cuentasTotal = contabilidad.total_cuentas || 0;
      const asientosTotal = contabilidad.total_asientos || 0;

      container.innerHTML = `
        <section class="panel">
          <div class="panel-body">
            <div class="section-head">
              <div>
                <h2>Indicadores vivos del tenant</h2>
                <p>Resumen alimentado por Core API para lectura ejecutiva antes de entrar al workspace.</p>
              </div>
            </div>

            <div class="metric-grid">
              ${metricCard(
                'Empresa activa',
                empresa.razon_social || 'Pendiente',
                empresa.nit ? `NIT ${empresa.nit}` : 'Configura los datos base del emisor'
              )}
              ${metricCard(
                'Facturas registradas',
                fmtNumber(facturasTotal),
                `Ventas ${fmtNumber(ventasTotal)} | Compras ${fmtNumber(comprasTotal)}`
              )}
              ${metricCard(
                'Contabilidad',
                fmtNumber(cuentasTotal),
                `Cuentas con ${fmtNumber(asientosTotal)} asientos acumulados`
              )}
            </div>

            <div class="content-grid" style="margin-top: 18px;">
              <div>
                <div class="signal-card" style="margin-bottom: 14px;">
                  <strong>Perfil operativo</strong>
                  <p>
                    ${escapeHtml(perfil.nombre || perfil.user_full_name || 'Usuario del tenant')}
                    ${perfil.email ? `(${escapeHtml(perfil.email)})` : ''}
                  </p>
                </div>

                <div class="nav-grid">
                  <a class="nav-card" href="/workspace/">
                    <i class="fa-solid fa-compass"></i>
                    <strong>Workspace principal</strong>
                    <span>Ir al compositor central para operar modulos, tablas y flujos del tenant.</span>
                  </a>
                  <a class="nav-card" href="/workspace/#facturas">
                    <i class="fa-solid fa-file-invoice"></i>
                    <strong>Canal de facturas</strong>
                    <span>${escapeHtml(`Valor referencial ${fmtMoney(facturas.valor_total || 0)}`)}</span>
                  </a>
                </div>
              </div>

              <div>
                <div class="timeline">
                  ${timelineItem(
                    'fa-solid fa-building',
                    'Empresa y emision',
                    empresa.razon_social ? 'La configuracion base de la empresa ya esta disponible para operar.' : 'Falta completar la configuracion principal del tenant.',
                    'Dominio de control administrativo'
                  )}
                  ${timelineItem(
                    'fa-solid fa-receipt',
                    'Facturacion',
                    `El tenant reporta ${fmtNumber(facturasTotal)} documentos con visibilidad inmediata desde dashboard.`,
                    'Seguimiento de ventas y compras'
                  )}
                  ${timelineItem(
                    'fa-solid fa-book-open',
                    'Contabilidad',
                    `Existen ${fmtNumber(cuentasTotal)} cuentas y ${fmtNumber(asientosTotal)} asientos visibles en la fachada core.`,
                    'Preparado para drill-down en workspace'
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>
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
