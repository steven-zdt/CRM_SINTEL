/**
 * Entry Point del Módulo Dashboard
 */

(function() {
  'use strict';

  const OUTLET_ID = 'workspace-router-outlet';

  async function initDashboardPage() {
    console.log('[dashboard.page] Inicializando módulo Dashboard');

    const outlet = document.getElementById(OUTLET_ID);
    if (!outlet) {
      console.error('[dashboard.page] Outlet no encontrado:', OUTLET_ID);
      return;
    }

    if (typeof window.dashboardAPI === 'undefined' || typeof window.dashboardUI === 'undefined') {
      console.error('[dashboard.page] Módulos no disponibles');
      outlet.innerHTML = '<div class="alert alert-danger">Error: Módulos no cargados</div>';
      return;
    }

    await window.dashboardUI.renderDashboard(outlet);
  }

  if (typeof window !== 'undefined') {
    window.initDashboardPage = initDashboardPage;
  }
})();
