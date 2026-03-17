/**
 * AJAX Setup CSRF - Red de seguridad global para jQuery
 * 
 * ⚠️ FASE 2: Setup global de jQuery para inyectar CSRF automáticamente
 * en todas las peticiones AJAX que modifiquen estado (POST, PUT, PATCH, DELETE)
 * 
 * Este es un seguro extra para cualquier llamada jQuery que no pase por
 * DataTables o por nuestros helpers centralizados.
 * 
 * DataTables ya inyecta CSRF por beforeSend en su configuración;
 * este setup cubre otras llamadas jQuery que puedan existir en el frontend.
 */

(function (w) {
  'use strict';

  // Verificar que jQuery esté disponible
  if (!w.jQuery || typeof w.jQuery.ajaxSetup !== 'function') {
    const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
    if (DEBUG) {
      console.warn('[ajax-setup-csrf] jQuery no disponible, omitiendo setup');
    }
    return;
  }

  const $ = w.jQuery;

  /**
   * Setup global de jQuery para inyectar CSRF en mutaciones
   * Patrón común recomendado por la comunidad jQuery para CSRF por defecto
   */
  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      // Solo mutaciones necesitan CSRF; GET raramente lo requiere
      const method = (settings.type || 'GET').toUpperCase();
      
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        // Obtener token fresco en cada request
        const token = (w.API_HELPERS && typeof w.API_HELPERS.getCSRF === 'function')
          ? w.API_HELPERS.getCSRF()
          : null;
        
        if (token) {
          // Intentar ambos nombres de header (algunos backends usan uno u otro)
          xhr.setRequestHeader('X-CSRFToken', token);
          xhr.setRequestHeader('X-CSRF-TOKEN', token);
        } else {
          const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
          if (DEBUG) {
            console.warn('[ajax-setup-csrf] CSRF token no encontrado para método', method);
          }
        }
      }
    }
  });

  // ⚠️ HTMX: Setup global de CSRF para HTMX (usa XMLHttpRequest internamente)
  if (typeof document !== 'undefined') {
    document.body.addEventListener('htmx:configRequest', function(event) {
      const method = (event.detail.verb || 'GET').toUpperCase();
      // Solo mutaciones necesitan CSRF
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const token = (w.API_HELPERS && typeof w.API_HELPERS.getCSRF === 'function')
          ? w.API_HELPERS.getCSRF()
          : null;
        if (token) {
          event.detail.headers['X-CSRFToken'] = token;
        } else {
          const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
          if (DEBUG) {
            console.warn('[ajax-setup-csrf] Token CSRF no encontrado para método HTMX', method);
          }
        }
      }
    });
  }
})(window);
