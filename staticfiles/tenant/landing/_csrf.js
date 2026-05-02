/**
 * Utilidad CSRF para AJAX y shells estáticos.
 * 
 * Exporta función getCookie() y constante csrftoken para usar en fetch/axios.
 * 
 * Uso:
 *   import { csrftoken } from './_csrf.js';
 *   
 *   fetch('/api/v1/landing/auth/login/', {
 *     method: 'POST',
 *     headers: {
 *       'Content-Type': 'application/json',
 *       'X-CSRFToken': csrftoken
 *     },
 *     body: JSON.stringify({ email, password })
 *   });
 */
export function getCookie(name) {
  let value = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
      const cookie = c.trim();
      if (cookie.startsWith(name + '=')) {
        value = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return value;
}

export const csrftoken = getCookie('csrftoken');
