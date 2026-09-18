/**
 * Error Service - Manejo unificado de errores DataTables
 * 
 * ⚠️ FASE 1: Servicio para manejar errores DataTables de forma centralizada
 * - Fuerza DataTable.ext.errMode='none' para evitar alertas intrusivas
 * - Captura errores vía evento dt-error.dt
 * - Loggea errores en consola (o integra con toast/notificador si aplica)
 */

(function (w) {
  'use strict';

  /**
   * Inicializa el servicio de errores DataTables
   */
  function init() {
    // Verificar que jQuery y DataTables estén disponibles
    if (!w.jQuery || !w.jQuery.fn || !w.jQuery.fn.dataTable) {
      const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
      if (DEBUG) {
        console.warn('[ErrorService] jQuery/DataTables no disponibles, omitiendo inicialización');
      }
      return;
    }

    const $ = w.jQuery;

    // Forzar errMode='none' para evitar alertas intrusivas
    // Esto permite manejar errores vía eventos en lugar de alertas
    if ($.fn.dataTable && $.fn.dataTable.ext) {
      $.fn.dataTable.ext.errMode = 'none';
    }

    // Captura TODOS los errores DataTables vía evento dt-error.dt
    // Este evento se dispara cuando DataTables encuentra un error
    $(document.body).on('dt-error.dt', function (e, settings, techNote, message) {
      const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
      
      // Loggear error en consola
      console.error('[ErrorService] DataTables error:', {
        techNote: techNote,
        message: message,
        table: settings?.sTableId || settings?.nTable?.id || 'unknown',
        endpoint: settings?.ajax?.url || 'unknown'
      });

      // Buscar elemento de feedback en la tabla afectada
      const tableId = settings?.sTableId || settings?.nTable?.id;
      if (tableId) {
        const $table = $(`#${tableId}`);
        if ($table.length) {
          const $feedback = $table.closest('.container, .row, body').find('.datatable-feedback, .alert');
          if ($feedback.length) {
            $feedback
              .removeClass('d-none alert-success')
              .addClass('alert-danger')
              .text(`Error cargando datos: ${message || techNote || 'Error desconocido'}`);
          } else {
            // Crear feedback si no existe
            const $container = $table.closest('.container, .row, .ui-module');
            if ($container.length) {
              const $newFeedback = $('<div class="alert alert-danger datatable-feedback" role="alert"></div>')
                .text(`Error cargando datos: ${message || techNote || 'Error desconocido'}`);
              $table.before($newFeedback);
            }
          }
        }
      }

      // TODO: Integrar con notificador/toast central si aplica
      // Ejemplo:
      // if (w.ToastService) {
      //   w.ToastService.error('Error cargando datos', message || techNote);
      // }
    });

    // También escuchar eventos nativos de error si DataTables los dispara
    document.body.addEventListener('dt-error', function (e) {
      const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
      if (DEBUG) {
        console.warn('[ErrorService] Evento dt-error nativo capturado:', e);
      }
    });

    const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
    if (DEBUG) {
      console.log('[ErrorService] Inicializado correctamente');
    }
  }

  // Inicializar cuando DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    // DOM ya está listo
    init();
  }

  // Exportar API pública
  w.ErrorService = Object.freeze({
    init
  });
})(window);
