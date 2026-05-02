/**
 * Helper para obtener cookies (CSRF token)
 * Requerido cuando se usa SessionAuthentication en DRF (mismo origen)
 * ⚠️ CENTRALIZADO: Este JS vive en apps/public/core/static/core/js/_csrf.js
 */
export function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(c => {
            c = c.trim();
            if (c.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(c.substring(name.length + 1));
            }
        });
    }
    return cookieValue;
}
