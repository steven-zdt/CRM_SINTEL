/**
 * Entry Point del Módulo Landing
 */

(function() {
  'use strict';

  const OUTLET_ID = 'workspace-router-outlet';

  async function initLandingPage() {
    console.log('[landing.page] Inicializando módulo Landing');

    const outlet = document.getElementById(OUTLET_ID);
    if (!outlet) {
      console.error('[landing.page] Outlet no encontrado:', OUTLET_ID);
      return;
    }

    if (typeof window.landingAPI === 'undefined' || typeof window.landingUI === 'undefined') {
      console.error('[landing.page] Módulos no disponibles');
      outlet.innerHTML = '<div class="alert alert-danger">Error: Módulos no cargados</div>';
      return;
    }

    await window.landingUI.renderLanding(outlet);
  }

  if (typeof window !== 'undefined') {
    window.initLandingPage = initLandingPage;
  }
})();
