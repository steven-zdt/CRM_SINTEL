/**
 * HTMX Event Handlers globales v2.60
 * ⚠️ Feature-Sliced: Solo manejo de errores globales HTMX
 */
(function(w, d) {
  'use strict';

  d.body.addEventListener('htmx:responseError', function(event) {
    const detail = event.detail;
    const status = detail.xhr?.status || 500;
    const responseText = detail.xhr?.responseText || '';
    
    let errorData = { detail: 'Error al cargar el contenido' };
    try {
      errorData = JSON.parse(responseText);
    } catch (e) {
      errorData = { detail: responseText || 'Error desconocido de red' };
    }
    
    if (w.UIManager?.notifyError) {
      w.UIManager.notifyError({ status, data: errorData }, 'HTMX Interceptor');
    }
  });

  d.body.addEventListener('htmx:sendError', function() {
    if (w.UIManager?.notifyError) {
      w.UIManager.notifyError({ status: 0, data: { detail: 'Error de conexión de red.' } }, 'Red');
    }
  });

})(window, document);
