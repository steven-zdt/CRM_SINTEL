/**
 * UI Module para Login (API-First).
 * ⚠️ CENTRALIZADO: Este JS vive en apps/public/core/static/core/js/login.ui.js
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
                pageTitleEl.textContent = `Iniciar sesión - ${nombre}`;
            }
        }
    } catch (error) {
        console.warn('No se pudo cargar el branding:', error);
    }
}

(function() {
    loadBranding();
    
    const $ = (id) => document.getElementById(id);
    const csrf = getCookie('csrftoken'); // Requerido si usas SessionAuthentication + mismo origen
    
    // Mostrar alert según reason en URL
    const urlParams = new URLSearchParams(window.location.search);
    const reason = urlParams.get('reason');
    
    if (reason === 'already_activated') {
        showAlert('info', 'Tu cuenta ya está activa. Por favor, inicia sesión o restablece tu contraseña si la olvidaste.');
    } else if (reason === 'reset_ok') {
        showAlertWithAction('success', 
            'Tu contraseña ha sido restablecida exitosamente. Ahora puedes iniciar sesión con tu nueva contraseña.',
            'Iniciar sesión',
            () => {
                // Enfocar el campo de email para facilitar el inicio de sesión
                const emailInput = $('email');
                if (emailInput) {
                    emailInput.focus();
                }
            }
        );
    }
    
    function showAlert(type, message) {
        const container = $('alert-container');
        if (!container) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        alert.setAttribute('role', 'alert');
        container.appendChild(alert);
        
        // Remover después de 5 segundos
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }
    
    function showAlertWithAction(type, message, actionText, actionCallback) {
        const container = $('alert-container');
        if (!container) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.setAttribute('role', 'alert');
        
        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        alert.appendChild(messageSpan);
        
        // Agregar botón de acción si se proporciona
        if (actionText && actionCallback) {
            const actionBtn = document.createElement('button');
            actionBtn.type = 'button';
            actionBtn.className = 'alert-action-btn';
            actionBtn.textContent = actionText;
            actionBtn.style.cssText = 'margin-left: 12px; padding: 4px 12px; background: rgba(255,255,255,0.2); border: 1px solid currentColor; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;';
            actionBtn.addEventListener('click', actionCallback);
            alert.appendChild(actionBtn);
        }
        
        container.appendChild(alert);
        
        // No remover automáticamente - el usuario puede cerrarlo manualmente o iniciar sesión
        // Opcional: remover después de 10 segundos
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 10000);
    }
    
    function setError(elementId, message) {
        const element = $(elementId);
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
    
    $('login-form')?.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        clearErrors();
        
        const email = $('email').value.trim();
        const password = $('password').value.trim();
        
        if (!email || !password) {
            $('form-error').textContent = 'Completa tus credenciales.';
            $('form-error').classList.add('show');
            return;
        }
        
        const submitBtn = $('submit-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Ingresando...';
        
        try {
            // ⚠️ IMPORTANTE: Asegurar que el payload sea JSON con las claves correctas
            const payload = {
                email: email,
                password: password
            };
            
            // ⚠️ POLÍTICA: Consumir Core API centralizado
            const response = await fetch('/api/v1/core/auth/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(csrf ? { 'X-CSRFToken': csrf } : {}) // DRF exige CSRF en POST si hay sesión/cookie
                },
                body: JSON.stringify(payload),
                credentials: 'include', // Incluir cookies
            });
            
            let data = {};
            try {
                data = await response.json();
            } catch (e) {
                console.error('Error parseando respuesta JSON:', e);
                // Si no se puede parsear JSON, intentar leer como texto
                const text = await response.text();
                console.error('Respuesta del servidor (texto):', text);
                data = { detail: 'Error al procesar la respuesta del servidor.' };
            }
            
            if (response.ok) {
                // Navegación post-login usando redirect_url de la API
                if (data.redirect_url) {
                    window.location.replace(data.redirect_url);
                } else {
                    // Si no hay redirect_url, mostrar error (no debería pasar)
                    console.error('Login exitoso pero sin redirect_url en la respuesta:', data);
                    $('form-error').textContent = 'Error: No se pudo determinar la ruta de redirección. Por favor, contacta al administrador.';
                    $('form-error').classList.add('show');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Ingresar';
                }
            } else if (response.status === 400) {
                // Error 400: Mostrar errores de validación por campo o detail
                let errorMessage = 'No fue posible iniciar sesión. Verifica tus credenciales.';
                
                // Prioridad: detail > non_field_errors > errores por campo
                if (data.detail) {
                    errorMessage = data.detail;
                } else if (data.non_field_errors && Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0) {
                    errorMessage = data.non_field_errors[0];
                } else if (data.email && Array.isArray(data.email) && data.email.length > 0) {
                    errorMessage = `Email: ${data.email[0]}`;
                    setError('email', data.email[0]);
                } else if (data.password && Array.isArray(data.password) && data.password.length > 0) {
                    errorMessage = `Contraseña: ${data.password[0]}`;
                    setError('password', data.password[0]);
                } else if (typeof data === 'string') {
                    errorMessage = data;
                }
                
                // Log detallado para depuración
                console.error('Error 400 en login:', {
                    status: response.status,
                    statusText: response.statusText,
                    data: data,
                    payload: { email: email, password: '[REDACTED]' }
                });
                
                $('form-error').textContent = errorMessage;
                $('form-error').classList.add('show');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Ingresar';
            } else if (response.status === 403) {
                // Error 403: CSRF o permisos
                let errorMessage = 'Acceso denegado. Por favor, recarga la página e intenta nuevamente.';
                
                if (data.detail) {
                    errorMessage = data.detail;
                }
                
                console.error('Error 403 en login:', {
                    status: response.status,
                    statusText: response.statusText,
                    data: data
                });
                
                $('form-error').textContent = errorMessage;
                $('form-error').classList.add('show');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Ingresar';
            } else {
                // Otros errores (500, etc.)
                let errorMessage = 'Error del servidor. Por favor, intenta más tarde.';
                
                if (data.detail) {
                    errorMessage = data.detail;
                }
                
                console.error('Error en login:', {
                    status: response.status,
                    statusText: response.statusText,
                    data: data
                });
                
                $('form-error').textContent = errorMessage;
                $('form-error').classList.add('show');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Ingresar';
            }
        } catch (error) {
            console.error('Error en login (excepción):', error);
            $('form-error').textContent = 'Error de red. Intenta nuevamente.';
            $('form-error').classList.add('show');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Ingresar';
        }
    });
})(window, document);
