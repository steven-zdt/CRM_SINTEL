/**
 * SintelFeedback - Sistema de Feedback y Errores Centralizado v2.40
 * 
 * ⚠️ ARQUITECTURA v2.40:
 * - Utilidad global para manejo de feedback y errores
 * - Usa SweetAlert2 para alertas modales
 * - Usa Toast para notificaciones no bloqueantes
 * - Manejo automático de errores 401 (redirección al login)
 * 
 * ⚠️ REGLA DE ORO: Si el error es 401 (Unauthorized), NO mostrar alerta,
 * dejar que el interceptor global maneje la redirección al login.
 * 
 * Dependencias:
 * - SweetAlert2 (Swal) - CDN o local
 * - window.http (definido en lib/http.js) - para detectar errores 401
 */

(function(w, d) {
  'use strict';

  // Verificar que SweetAlert2 esté disponible
  if (typeof Swal === 'undefined') {
    console.error('[SintelFeedback] SweetAlert2 (Swal) no está disponible. Cargar SweetAlert2 primero.');
    // Crear objeto stub para evitar errores
    w.SintelFeedback = {
      success: function() { console.warn('[SintelFeedback] Swal no disponible'); },
      handleAPIError: function() { console.warn('[SintelFeedback] Swal no disponible'); },
      error: function() { console.warn('[SintelFeedback] Swal no disponible'); },
      warning: function() { console.warn('[SintelFeedback] Swal no disponible'); },
      info: function() { console.warn('[SintelFeedback] Swal no disponible'); },
    };
    return;
  }

  /**
   * Muestra un toast de éxito (verde) en la esquina superior derecha
   * @param {string} msg - Mensaje a mostrar
   * @param {number} duration - Duración en ms (default: 3000)
   */
  function success(msg, duration = 3000) {
    if (!msg) return;
    
    Swal.fire({
      icon: 'success',
      title: 'Éxito',
      text: msg,
      toast: true,
      position: 'top-end',
      showConfirmButton: false,
      timer: duration,
      timerProgressBar: true,
    });
  }

  /**
   * Muestra un toast de error (rojo) en la esquina superior derecha
   * @param {string} msg - Mensaje a mostrar
   * @param {number} duration - Duración en ms (default: 5000)
   */
  function error(msg, duration = 5000) {
    if (!msg) return;
    
    Swal.fire({
      icon: 'error',
      title: 'Error',
      text: msg,
      toast: true,
      position: 'top-end',
      showConfirmButton: false,
      timer: duration,
      timerProgressBar: true,
    });
  }

  /**
   * Muestra un toast de advertencia (amarillo) en la esquina superior derecha
   * @param {string} msg - Mensaje a mostrar
   * @param {number} duration - Duración en ms (default: 4000)
   */
  function warning(msg, duration = 4000) {
    if (!msg) return;
    
    Swal.fire({
      icon: 'warning',
      title: 'Advertencia',
      text: msg,
      toast: true,
      position: 'top-end',
      showConfirmButton: false,
      timer: duration,
      timerProgressBar: true,
    });
  }

  /**
   * Muestra un toast de información (azul) en la esquina superior derecha
   * @param {string} msg - Mensaje a mostrar
   * @param {number} duration - Duración en ms (default: 3000)
   */
  function info(msg, duration = 3000) {
    if (!msg) return;
    
    Swal.fire({
      icon: 'info',
      title: 'Información',
      text: msg,
      toast: true,
      position: 'top-end',
      showConfirmButton: false,
      timer: duration,
      timerProgressBar: true,
    });
  }

  /**
   * Analiza un objeto de error de la API y muestra una alerta modal roja
   * 
   * ⚠️ REGLA DE ORO: Si el error es 401 (Unauthorized), NO mostrar alerta,
   * dejar que el interceptor global maneje la redirección al login.
   * 
   * @param {Object|Error|Response} error - Objeto de error de la API
   * @param {string} prefix - Prefijo para logs (ej: "[cotizaciones.page]")
   * @param {boolean} showModal - Si es true, muestra modal; si es false, solo toast (default: true)
   */
  function handleAPIError(error, prefix = '', showModal = true) {
    if (!error) {
      console.warn(`${prefix} handleAPIError llamado sin error`);
      return;
    }

    // Extraer información del error
    let status = null;
    let message = 'Error desconocido';
    let detail = null;
    let code = null;

    // Si es un objeto de respuesta de window.http
    if (error.status !== undefined) {
      status = error.status;
      if (error.data) {
        // ⚠️ v2.60: DRF devuelve errores como objetos con arrays: {"campo": ["Error 1", "Error 2"]}
        // Necesitamos aplanar estos errores, incluso si están anidados profundamente
        if (typeof error.data === 'object' && !Array.isArray(error.data)) {
          // Si es un objeto con errores de validación, aplanarlo recursivamente
          const errorMessages = [];
          
          /**
           * ⚠️ v2.60: Función recursiva para aplanar objetos de error anidados
           * Maneja casos como: {"campo": {"subcampo": ["Error"]}} o {"campo": [{"subcampo": "Error"}]}
           */
          function flattenError(obj, prefix = '') {
            if (Array.isArray(obj)) {
              // Si es un array, procesar cada elemento
              obj.forEach((item, index) => {
                if (typeof item === 'object' && item !== null) {
                  flattenError(item, prefix ? `${prefix}[${index}]` : String(index));
                } else {
                  errorMessages.push(prefix ? `${prefix}: ${String(item)}` : String(item));
                }
              });
            } else if (typeof obj === 'object' && obj !== null) {
              // Si es un objeto, procesar cada propiedad
              for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                  const value = obj[key];
                  const newPrefix = prefix ? `${prefix}.${key}` : key;
                  
                  if (Array.isArray(value)) {
                    // Si el valor es un array, unir los mensajes
                    const arrayMessages = value.map(v => {
                      if (typeof v === 'object' && v !== null) {
                        return JSON.stringify(v);
                      }
                      return String(v);
                    });
                    errorMessages.push(`${newPrefix}: ${arrayMessages.join(', ')}`);
                  } else if (typeof value === 'object' && value !== null) {
                    // Si el valor es un objeto, procesarlo recursivamente
                    flattenError(value, newPrefix);
                  } else {
                    // Si es un valor primitivo, agregarlo directamente
                    errorMessages.push(`${newPrefix}: ${String(value)}`);
                  }
                }
              }
            } else {
              // Si es un valor primitivo, agregarlo directamente
              errorMessages.push(prefix ? `${prefix}: ${String(obj)}` : String(obj));
            }
          }
          
          // Procesar el objeto de error
          flattenError(error.data);
          
          if (errorMessages.length > 0) {
            message = errorMessages.join('\n');
          } else {
            message = error.data.message || error.data.detail || error.data.error || message;
          }
        } else if (Array.isArray(error.data)) {
          // Si es un array directo, unirlo
          message = error.data.map(item => {
            if (typeof item === 'object' && item !== null) {
              return JSON.stringify(item);
            }
            return String(item);
          }).join('\n');
        } else {
          message = error.data.message || error.data.detail || error.data.error || message;
        }
        
        detail = error.data.detail || error.data.error || null;
        code = error.data.code || null;
      }
    }
    // Si es un objeto de error estándar
    else if (error.message) {
      message = error.message;
    }
    // Si es un string
    else if (typeof error === 'string') {
      message = error;
    }

    // ⚠️ REGLA DE ORO: Si es 401, NO mostrar alerta, dejar que el interceptor maneje
    if (status === 401) {
      console.warn(`${prefix} Error 401 detectado, omitiendo feedback (interceptor global manejará redirección)`);
      return;
    }

    // Log del error
    if (prefix) {
      console.error(`${prefix} Error de API:`, {
        status,
        message,
        detail,
        code,
        error
      });
    }

    // Construir mensaje completo - Asegurar que sea string
    // ⚠️ v2.60: Manejar arrays y objetos anidados usando Object.values().flat()
    let fullMessage = message || 'Error desconocido';
    
    // ⚠️ CRÍTICO: Si el error es un objeto de DRF, convertirlo a string
    // Simplificado según instrucciones: Object.values().flat().join(' ')
    if (typeof fullMessage === 'object' && fullMessage !== null) {
      try {
        // Si es un objeto, usar Object.values().flat() para aplanar
        fullMessage = Object.values(fullMessage).flat(Infinity).join(' ');
      } catch (e) {
        // Si falla el aplanado, usar JSON.stringify como fallback
        try {
          fullMessage = JSON.stringify(fullMessage);
        } catch (e2) {
          fullMessage = String(fullMessage);
        }
      }
    } else if (Array.isArray(fullMessage)) {
      // Si es un array, aplanarlo y convertir a string
      fullMessage = fullMessage.flat(Infinity).join(' ');
    } else if (typeof fullMessage !== 'string') {
      // Si no es string, intentar convertirlo
      fullMessage = String(fullMessage);
    }
    
    // ⚠️ CRÍTICO: Asegurar que sea string final
    if (typeof fullMessage !== 'string') {
      fullMessage = String(fullMessage);
    }
    
    if (detail && detail !== message) {
      // Aplanar detail si es un array u objeto
      let detailStr = detail;
      if (Array.isArray(detail)) {
        detailStr = detail.join(', ');
      } else if (typeof detail === 'object') {
        detailStr = JSON.stringify(detail);
      } else {
        detailStr = String(detail);
      }
      fullMessage += `\n\nDetalle: ${detailStr}`;
    }
    if (code) {
      fullMessage += `\n\nCódigo: ${code}`;
    }

    // Mostrar alerta modal o toast según showModal
    if (showModal) {
      Swal.fire({
        icon: 'error',
        title: 'Error',
        html: fullMessage.replace(/\n/g, '<br>'),
        confirmButtonText: 'Aceptar',
        confirmButtonColor: '#dc3545',
      });
    } else {
      error(fullMessage);
    }
  }

  // Exportar objeto global
  w.SintelFeedback = {
    success,
    error,
    warning,
    info,
    handleAPIError,
  };

  console.log('[SintelFeedback] Sistema de feedback inicializado');

})(window, document);
