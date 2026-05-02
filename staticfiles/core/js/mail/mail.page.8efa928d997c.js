/**
 * Entry Point del Módulo MailDigester
 * 
 * Función de inicialización que se llama desde el router cuando se navega a #mail
 */

(function() {
  'use strict';

  const OUTLET_ID = 'workspace-router-outlet';

  /**
   * Inicializa la página de MailDigester
   * @returns {Promise<void>}
   */
  async function initMailDigesterPage() {
    console.log('[mail.page] Inicializando módulo MailDigester');

    const outlet = document.getElementById(OUTLET_ID);
    if (!outlet) {
      console.error('[mail.page] Outlet no encontrado:', OUTLET_ID);
      return;
    }

    // Asegurar que los módulos estén cargados
    if (typeof window.mailAPI === 'undefined') {
      console.error('[mail.page] mailAPI no está disponible');
      outlet.innerHTML = '<div class="alert alert-danger">Error: Módulo de API no cargado</div>';
      return;
    }

    if (typeof window.mailUI === 'undefined') {
      console.error('[mail.page] mailUI no está disponible');
      outlet.innerHTML = '<div class="alert alert-danger">Error: Módulo de UI no cargado</div>';
      return;
    }

    // Renderizar panel
    await window.mailUI.renderMailPanel(outlet);
  }

  // Exportar para uso global (router)
  if (typeof window !== 'undefined') {
    window.initMailDigesterPage = initMailDigesterPage;
  }
})();
