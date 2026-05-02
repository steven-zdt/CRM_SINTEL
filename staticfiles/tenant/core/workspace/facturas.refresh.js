/**
 * Módulo para refrescar la tabla de Facturas tras eventos de importación.
 * 
 * ⚠️ Integración: Escucha evento global 'facturas:refresh' y dispara recarga.
 */

(function() {
  'use strict';

  function refreshFacturas() {
    // Intentar usar la función global loadTabla si existe (desde facturas.page.js)
    if (typeof window.loadTabla === 'function') {
      window.loadTabla().catch(err => {
        console.error('[facturas.refresh] Error refrescando tabla:', err);
      });
    } else {
      // Fallback: recargar manualmente si la función no está disponible
      console.warn('[facturas.refresh] loadTabla no disponible, intentando recarga manual');
      
      // Disparar evento para que otros módulos puedan escuchar
      window.dispatchEvent(new CustomEvent('facturas:refresh:manual'));
    }
  }

  // Escuchar evento global
  window.addEventListener('facturas:refresh', () => {
    refreshFacturas();
  });

  // Exponer función global
  if (typeof window !== 'undefined') {
    window.facturasRefresh = {
      refresh: refreshFacturas
    };
  }
})();
