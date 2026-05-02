/**
 * UI Module para Activate (API-First).
 * ⚠️ CENTRALIZADO: Este JS vive en apps/public/core/static/core/js/activate.ui.js
 * ⚠️ IMPORTANTE: Este módulo consume APIs de apps/tenant/landing/api (JSON only).
 * ⚠️ v3.3: Vanilla JS con IIFE - Sin dependencias de módulos ES6
 */
(function(w, d) {
  'use strict';
  
  // Helper: Obtener cookie (reemplaza import)
  function getCookie(name) {
    const value = `; ${d.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(';').shift());
    return null;
  }

// Helpers
function getCSRFToken() {
    return getCookie('csrftoken') || '';
}

async function jsonFetch(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    
    // Agregar CSRF token si está disponible (mismo origen)
    const csrfToken = getCSRFToken();
    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }
    
    const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include', // Incluir cookies
    });
    
    let data = null;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        data = await response.json();
    }
    
    return { response, data };
}

function setState(state) {
    // Ocultar todos los paneles
    document.querySelectorAll('.state-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    // Mostrar el panel correspondiente
    const panel = document.getElementById(`state-${state}`);
    if (panel) {
        panel.classList.add('active');
        // Focus management para accesibilidad
        const heading = panel.querySelector('h2');
        if (heading) {
            heading.setAttribute('tabindex', '-1');
            heading.focus();
        }
    }
}

function setError(elementId, message) {
    const element = document.getElementById(elementId);
    const errorDiv = element.nextElementSibling;
    
    if (errorDiv && errorDiv.classList.contains('error-message')) {
        errorDiv.textContent = message;
        errorDiv.classList.add('show');
        element.classList.add('error');
        element.setAttribute('aria-invalid', 'true');
    }
}

function clearErrors() {
    document.querySelectorAll('.error-message').forEach(el => {
        el.classList.remove('show');
        el.textContent = '';
    });
    document.querySelectorAll('input.error').forEach(el => {
        el.classList.remove('error');
        el.setAttribute('aria-invalid', 'false');
    });
}

// Obtener token de la URL
function getTokenFromURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get('token');
}

// Validar token (GET)
async function validateToken(token) {
    try {
        const { response, data } = await jsonFetch(
            `/api/v1/landing/auth/activate/?token=${encodeURIComponent(token)}`
        );
        
        if (response.status === 200) {
            setState('form');
        } else if (response.status === 409) {
            // Ya activada - mostrar UI amigable
            setState('already-activated');
        } else if (response.status === 400) {
            setState('invalid');
        } else {
            throw new Error(data?.detail || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error validando token:', error);
        setState('error');
        document.getElementById('error-message').textContent = 
            error.message || 'Error de conexión. Por favor, verifica tu conexión a internet.';
    }
}

// Enviar activación (POST)
async function submitActivation(token, password1, password2) {
    // Validación cliente
    if (password1 !== password2) {
        setError('password2', 'Las contraseñas no coinciden');
        return false;
    }
    
    if (password1.length < 8) {
        setError('password1', 'La contraseña debe tener al menos 8 caracteres');
        return false;
    }
    
    clearErrors();
    
    // Deshabilitar botón
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Activando...';
    
    try {
        const { response, data } = await jsonFetch(
            `/api/v1/landing/auth/activate/?token=${encodeURIComponent(token)}`,
            {
                method: 'POST',
                body: JSON.stringify({
                    password1,
                    password2,
                }),
            }
        );
        
        if (response.status === 200) {
            // Redirigir usando redirect_url de la API (por rol)
            if (data.redirect_url) {
                window.location.replace(data.redirect_url);
            } else {
                // Si no hay redirect_url, mostrar error (no debería pasar)
                console.error('Activación exitosa pero sin redirect_url en la respuesta');
                const formError = document.getElementById('form-error');
                formError.textContent = 'Error: No se pudo determinar la ruta de redirección. Por favor, contacta al administrador.';
                formError.classList.add('show');
                setState('form');
            }
        } else if (response.status === 409) {
            setState('already-activated');
        } else if (response.status === 400) {
            // Mostrar errores de validación
            if (data.password1) {
                setError('password1', Array.isArray(data.password1) ? data.password1[0] : data.password1);
            }
            if (data.password2) {
                setError('password2', Array.isArray(data.password2) ? data.password2[0] : data.password2);
            }
            if (data.detail) {
                const formError = document.getElementById('form-error');
                formError.textContent = data.detail;
                formError.classList.add('show');
            }
            setState('form');
        } else {
            throw new Error(data?.detail || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error activando cuenta:', error);
        const formError = document.getElementById('form-error');
        formError.textContent = error.message || 'Error de conexión. Por favor, intenta nuevamente.';
        formError.classList.add('show');
        setState('form');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Activar cuenta';
    }
    
    return false;
}

// Inicialización
// ⚠️ POLÍTICA: Cargar branding desde la API (no hardcodes)
async function loadBranding() {
    try {
        const response = await fetch('/api/v1/landing/info/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
        });

        if (response.ok) {
            const data = await response.json();
            const branding = data.branding || {};
            const nombre = branding.nombre || data.nombre || 'Sistema de Gestión';
            
            // Actualizar nombre en el header
            const brandingNameEl = document.getElementById('branding-name');
            if (brandingNameEl) {
                brandingNameEl.textContent = nombre;
            }
            
            // Actualizar título de la página
            const pageTitleEl = document.getElementById('page-title');
            if (pageTitleEl) {
                pageTitleEl.textContent = `Activar cuenta - ${nombre}`;
            }
            
            // Actualizar footer
            const footerTextEl = document.getElementById('footer-text');
            if (footerTextEl) {
                footerTextEl.textContent = `© ${new Date().getFullYear()} ${nombre}. Todos los derechos reservados.`;
            }
            
            // Actualizar link de soporte si hay email de contacto
            const supportLinkEl = document.getElementById('support-link');
            if (supportLinkEl && branding.email_contacto) {
                supportLinkEl.href = `mailto:${branding.email_contacto}`;
            }
        }
    } catch (error) {
        console.warn('No se pudo cargar el branding:', error);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Cargar branding desde la API
    loadBranding();
    const token = getTokenFromURL();
    
    if (!token) {
        setState('invalid');
        return;
    }
    
    // Validar token al cargar
    validateToken(token);
    
    // Manejar formulario de activación
    const form = document.getElementById('activation-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const password1 = document.getElementById('password1').value;
            const password2 = document.getElementById('password2').value;
            submitActivation(token, password1, password2);
        });
    }
})(window, document);
