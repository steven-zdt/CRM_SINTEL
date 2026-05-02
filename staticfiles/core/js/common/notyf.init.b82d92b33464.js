/**
 * notyf.init.js - v2.95
 * Inicialización global de Notyf para notificaciones toast.
 * 
 * ⚠️ DEPENDENCIA: Requiere notyf.min.js cargado desde CDN antes de este script.
 * ⚠️ ORDEN DE CARGA: CDN (notyf.min.js) → Este archivo (notyf.init.js)
 * 
 * Uso:
 * - window.notyf.success('Mensaje de éxito')
 * - window.notyf.error('Mensaje de error')
 * - window.notyf.info('Mensaje informativo')
 * - window.notyf.warning('Mensaje de advertencia')
 */
(function(w) {
    'use strict';

    // Verificar que Notyf esté disponible
    if (typeof Notyf === 'undefined') {
        console.error('[notyf.init] Notyf no está disponible. Asegúrate de cargar notyf.min.js desde CDN antes de este script.');
        // Crear un shim para evitar errores
        w.notyf = {
            success: function(msg) { console.log('[NOTYF-SHIM] Success:', msg); },
            error: function(msg) { console.error('[NOTYF-SHIM] Error:', msg); },
            info: function(msg) { console.info('[NOTYF-SHIM] Info:', msg); },
            warning: function(msg) { console.warn('[NOTYF-SHIM] Warning:', msg); }
        };
        return;
    }

    // Configuración de Notyf
    const notyf = new Notyf({
        duration: 4000, // Duración en milisegundos (4 segundos)
        position: {
            x: 'right', // Posición horizontal: 'left' | 'center' | 'right'
            y: 'top',   // Posición vertical: 'top' | 'bottom'
        },
        types: [
            {
                type: 'success',
                background: '#10b981', // Verde
                icon: {
                    className: 'fas fa-check-circle',
                    tagName: 'i',
                    text: ''
                },
                dismissible: true
            },
            {
                type: 'error',
                background: '#ef4444', // Rojo
                icon: {
                    className: 'fas fa-exclamation-circle',
                    tagName: 'i',
                    text: ''
                },
                dismissible: true
            },
            {
                type: 'info',
                background: '#3b82f6', // Azul
                icon: {
                    className: 'fas fa-info-circle',
                    tagName: 'i',
                    text: ''
                },
                dismissible: true
            },
            {
                type: 'warning',
                background: '#f59e0b', // Amarillo/Naranja
                icon: {
                    className: 'fas fa-exclamation-triangle',
                    tagName: 'i',
                    text: ''
                },
                dismissible: true
            }
        ],
        ripple: true, // Efecto de onda al hacer click
        dismissible: true, // Permite cerrar haciendo click
        pauseOnHover: true // Pausa el temporizador al pasar el mouse
    });

    // ⚠️ v2.40: Agregar métodos helper para compatibilidad
    // Notyf v3 puede requerir usar notyf.open() en lugar de métodos directos
    // Estos helpers aseguran que info() y warning() estén disponibles
    const notyfWrapper = {
        success: function(message) {
            try {
                // Intentar usar método directo si existe
                if (typeof notyf.success === 'function') {
                    return notyf.success(message);
                }
                // Fallback: usar open()
                return notyf.open({ type: 'success', message: message });
            } catch (e) {
                console.error('[notyf.init] Error en success:', e);
                return null;
            }
        },
        error: function(message) {
            try {
                if (typeof notyf.error === 'function') {
                    return notyf.error(message);
                }
                return notyf.open({ type: 'error', message: message });
            } catch (e) {
                console.error('[notyf.init] Error en error:', e);
                return null;
            }
        },
        info: function(message) {
            try {
                // Intentar usar método directo si existe
                if (typeof notyf.info === 'function') {
                    return notyf.info(message);
                }
                // Fallback: usar open()
                return notyf.open({ type: 'info', message: message });
            } catch (e) {
                console.error('[notyf.init] Error en info:', e);
                return null;
            }
        },
        warning: function(message) {
            try {
                if (typeof notyf.warning === 'function') {
                    return notyf.warning(message);
                }
                return notyf.open({ type: 'warning', message: message });
            } catch (e) {
                console.error('[notyf.init] Error en warning:', e);
                return null;
            }
        },
        // Exponer también el método open() original por si se necesita
        open: function(options) {
            try {
                return notyf.open(options);
            } catch (e) {
                console.error('[notyf.init] Error en open:', e);
                return null;
            }
        }
    };

    // Exponer globalmente
    w.notyf = notyfWrapper;

    // Log de confirmación (solo en desarrollo)
    if (w.console && w.console.log) {
        console.log('[notyf.init] ✅ Notyf inicializado correctamente con métodos helper');
    }
})(window);
