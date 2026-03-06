/**
 * Utilitario HTTP para la consola (fetch + CSRF + manejo de errores).
 * 
 * ⚠️ API-First: Todas las peticiones consumen exclusivamente APIs JSON.
 * 
 * Uso:
 *     import { http } from './http.js';
 *     
 *     // GET
 *     const data = await http.get('/api/public/v1/impuestos/contribuyentes-tipos/');
 *     
 *     // POST
 *     const created = await http.post('/api/public/v1/impuestos/contribuyentes-tipos/', {
 *         nombre: 'Test',
 *         clase: 'PJ'
 *     });
 *     
 *     // PATCH
 *     const updated = await http.patch('/api/public/v1/impuestos/contribuyentes-tipos/1/', {
 *         nombre: 'Updated'
 *     });
 *     
 *     // DELETE
 *     await http.delete('/api/public/v1/impuestos/contribuyentes-tipos/1/');
 */
(function() {
    'use strict';

    /**
     * Obtiene el token CSRF desde el meta tag.
     */
    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    /**
     * Maneja errores HTTP y retorna mensajes legibles.
     */
    function handleError(response, data) {
        if (data && data.detail) {
            return new Error(data.detail);
        }
        if (data && data.non_field_errors && data.non_field_errors.length > 0) {
            return new Error(data.non_field_errors[0]);
        }
        if (data && typeof data === 'object') {
            // Errores de validación por campo
            const errors = Object.entries(data)
                .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
                .join('; ');
            return new Error(errors || `HTTP ${response.status}`);
        }
        return new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    /**
     * Realiza una petición HTTP con autenticación y CSRF.
     */
    async function request(url, options = {}) {
        const defaultOptions = {
            credentials: 'include', // Incluir cookies (sesión)
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...(options.headers || {}),
            },
        };

        try {
            const response = await fetch(url, mergedOptions);
            
            // Parsear respuesta (puede ser JSON o texto)
            let data;
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                throw handleError(response, data);
            }

            return data;
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            }
            throw new Error(`Error de red: ${error.message || 'Desconocido'}`);
        }
    }

    /**
     * Cliente HTTP con métodos helper.
     */
    const http = {
        /**
         * GET request.
         */
        async get(url, params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const fullUrl = queryString ? `${url}?${queryString}` : url;
            return request(fullUrl, { method: 'GET' });
        },

        /**
         * POST request.
         */
        async post(url, data = {}) {
            return request(url, {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },

        /**
         * PATCH request.
         */
        async patch(url, data = {}) {
            return request(url, {
                method: 'PATCH',
                body: JSON.stringify(data),
            });
        },

        /**
         * PUT request.
         */
        async put(url, data = {}) {
            return request(url, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        },

        /**
         * DELETE request.
         */
        async delete(url) {
            return request(url, { method: 'DELETE' });
        },
    };

    // Exportar para uso en módulos ES6
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { http };
    } else {
        // Global para uso en scripts inline
        window.http = http;
    }
})();
