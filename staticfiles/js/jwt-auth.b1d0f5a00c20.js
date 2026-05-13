/**
 * Helper global para autenticación JWT en la consola.
 * 
 * Proporciona funciones para:
 * - Login/obtener tokens
 * - Refresh de tokens
 * - Almacenamiento seguro de tokens
 * - Inyección automática de Authorization: Bearer en requests
 * 
 * Referencia: https://django-rest-framework-simplejwt.readthedocs.io/
 */

const jwtAuth = {
    /**
     * Detecta si estamos en el dominio público o en un tenant.
     */
    isPublicHost() {
        const hostname = window.location.hostname;
        return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'sintel.com' || hostname.endsWith('.sintel.com') === false;
    },

    /**
     * Obtiene el access token desde localStorage.
     */
    getAccessToken() {
        return localStorage.getItem('jwt_access_token') || null;
    },

    /**
     * Obtiene el refresh token desde localStorage.
     */
    getRefreshToken() {
        return localStorage.getItem('jwt_refresh_token') || null;
    },

    /**
     * Guarda tokens en localStorage.
     */
    setTokens(access, refresh) {
        localStorage.setItem('jwt_access_token', access);
        if (refresh) {
            localStorage.setItem('jwt_refresh_token', refresh);
        }
    },

    /**
     * Limpia tokens de localStorage (logout).
     */
    clearTokens() {
        localStorage.removeItem('jwt_access_token');
        localStorage.removeItem('jwt_refresh_token');
    },

    /**
     * Login: Obtiene tokens desde /api/token/ (esquema público).
     * 
     * @param {string} username - Username o email del usuario
     * @param {string} password - Contraseña
     * @returns {Promise<{access: string, refresh: string}>}
     */
    async login(username, password) {
        const response = await fetch('/api/token/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Error de autenticación' }));
            throw new Error(error.detail || 'Error de autenticación');
        }

        const { access, refresh } = await response.json();
        this.setTokens(access, refresh);
        return { access, refresh };
    },

    /**
     * Refresh: Renueva el access token usando el refresh token.
     * 
     * @returns {Promise<string>} Nuevo access token
     */
    async refresh() {
        const refresh = this.getRefreshToken();
        if (!refresh) {
            throw new Error('No hay refresh token disponible');
        }

        const response = await fetch('/api/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh }),
        });

        if (!response.ok) {
            // Si el refresh falla, limpiar tokens y forzar re-login
            this.clearTokens();
            const error = await response.json().catch(() => ({ detail: 'Refresh token inválido' }));
            throw new Error(error.detail || 'Refresh token inválido');
        }

        const { access } = await response.json();
        this.setTokens(access, null); // refresh no cambia (a menos que ROTATE_REFRESH_TOKENS=True)
        return access;
    },

    /**
     * Verifica si un token es válido.
     * 
     * @param {string} token - Token a verificar (opcional, usa access token por defecto)
     * @returns {Promise<boolean>}
     */
    async verify(token = null) {
        const tokenToVerify = token || this.getAccessToken();
        if (!tokenToVerify) {
            return false;
        }

        try {
            const response = await fetch('/api/token/verify/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: tokenToVerify }),
                credentials: 'same-origin', // Incluir cookies si es necesario
            });

            // Si el token es inválido o expirado, retornar false sin lanzar error
            if (!response.ok) {
                // 401 significa que el token es inválido/expirado (comportamiento esperado)
                if (response.status === 401) {
                    return false;
                }
                // Otros errores (500, etc.) también retornan false
                console.debug('Token verify falló:', response.status, response.statusText);
                return false;
            }

            return true;
        } catch (error) {
            // Error de red u otro error, retornar false sin lanzar excepción
            console.debug('Error verificando token:', error.message);
            return false;
        }
    },

    /**
     * Obtiene el access token, refrescándolo si es necesario.
     * 
     * @returns {Promise<string|null>}
     */
    async getValidAccessToken() {
        const access = this.getAccessToken();
        
        // Si no hay access token, intentar obtener desde sesión o refresh
        if (!access) {
            // Primero intentar obtener desde sesión (Core API prioritario para tenants)
            try {
                // Intentar endpoint centralizado de Core
                let response = await fetch('/api/v1/core/auth/from-session/', {
                    method: 'GET',
                    credentials: 'include',
                });
                
                // Si falla y estamos en dominio público, intentar endpoint legacy (consola pública)
                if (!response.ok && this.isPublicHost()) {
                    response = await fetch('/console/jwt/from-session/', {
                        method: 'GET',
                        credentials: 'include',
                    });
                }
                
                if (response.ok) {
                    const { access: newAccess, refresh } = await response.json();
                    this.setTokens(newAccess, refresh);
                    return newAccess;
                }
            } catch (error) {
                console.debug('No se pudo obtener JWT desde sesión:', error.message);
            }
            
            // Si no hay refresh token, retornar null
            const refresh = this.getRefreshToken();
            if (!refresh) {
                return null;
            }
            
            // Intentar refresh
            try {
                return await this.refresh();
            } catch (error) {
                console.debug('No se pudo refrescar token:', error.message);
                return null;
            }
        }

        // Verificar si el token es válido (sin lanzar errores si falla)
        const isValid = await this.verify(access);
        if (!isValid) {
            // Token expirado o inválido, intentar refresh
            const refresh = this.getRefreshToken();
            if (!refresh) {
                // Si no hay refresh token, intentar obtener desde sesión (priorizar Core API)
                try {
                    let response = await fetch('/api/v1/core/auth/from-session/', {
                        method: 'GET',
                        credentials: 'include',
                    });
                    
                    if (!response.ok && this.isPublicHost()) {
                        response = await fetch('/console/jwt/from-session/', {
                            method: 'GET',
                            credentials: 'include',
                        });
                    }
                    
                    if (response.ok) {
                        const { access: newAccess, refresh: newRefresh } = await response.json();
                        this.setTokens(newAccess, newRefresh);
                        return newAccess;
                    }
                } catch (error) {
                    console.debug('No se pudo obtener JWT desde sesión:', error.message);
                }
                return null;
            }
            
            try {
                return await this.refresh();
            } catch (error) {
                console.debug('No se pudo refrescar token:', error.message);
                return null;
            }
        }

        return access;
    },

    /**
     * Inyecta Authorization: Bearer en headers de una petición.
     * 
     * @param {Headers|Object} headers - Headers existentes
     * @returns {Promise<Headers|Object>} Headers con Authorization agregado
     */
    async injectAuthHeader(headers) {
        const access = await this.getValidAccessToken();
        if (!access) {
            throw new Error('No hay token de acceso disponible. Por favor, inicia sesión.');
        }

        // Si headers es un objeto Headers (Fetch API), usar setHeader
        if (headers instanceof Headers) {
            headers.set('Authorization', `Bearer ${access}`);
        } else {
            // Si es un objeto plano (jQuery, etc.), asignar directamente
            headers = headers || {};
            headers['Authorization'] = `Bearer ${access}`;
        }

        return headers;
    }
};

// Auto-login en consola si el usuario ya tiene sesión activa
// Obtiene JWT token automáticamente desde la sesión de Django (Core API prioritario)
document.addEventListener('DOMContentLoaded', async function() {
    // Si no hay JWT token, intentar obtenerlo desde la sesión activa
    if (!jwtAuth.getAccessToken()) {
        try {
            // Intentar primero endpoint centralizado de Core (v2.61+)
            let response = await fetch('/api/v1/core/auth/from-session/', {
                method: 'GET',
                credentials: 'include', // Incluir cookies de sesión
            });
            
            // Si falla y estamos en dominio público, caer en endpoint legacy
            if (!response.ok && jwtAuth.isPublicHost()) {
                response = await fetch('/console/jwt/from-session/', {
                    method: 'GET',
                    credentials: 'include',
                });
            }
            
            if (response.ok) {
                const { access, refresh } = await response.json();
                jwtAuth.setTokens(access, refresh);
                console.log('✅ JWT token obtenido desde sesión activa');
            }
        } catch (error) {
            // Silenciar error: el usuario puede no estar autenticado o no tener sesión
            console.debug('No se pudo obtener JWT desde sesión:', error.message);
        }
    }
});

// Exponer a window para disponibilidad global (v2.62)
window.jwtAuth = jwtAuth;

