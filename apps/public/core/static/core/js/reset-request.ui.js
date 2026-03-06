/**
 * UI Module para Reset Request (API-First).
 * ⚠️ CENTRALIZADO: Este JS vive en apps/public/core/static/core/js/reset-request.ui.js
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
                pageTitleEl.textContent = `Restablecer contraseña - ${nombre}`;
            }
        }
    } catch (error) {
        console.warn('No se pudo cargar el branding:', error);
    }
}

(function() {
    // Cargar branding al inicio
    loadBranding();
    
    const $ = (id) => document.getElementById(id);
    const csrf = getCookie('csrftoken');
    
    function showAlert(type, message) {
        const container = $('alert-container');
        if (!container) return;
        
        // Limpiar alertas anteriores
        container.innerHTML = '';
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        alert.setAttribute('role', 'alert');
        container.appendChild(alert);
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
    
    $('reset-request-form')?.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        clearErrors();
        
        const email = $('reset-email').value.trim();
        
        if (!email) {
            setError('reset-email', 'Ingresa tu email.');
            return;
        }
        
        const submitBtn = $('submit-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Enviando...';
        
        try {
            // ⚠️ POLÍTICA: Consumir Core API centralizado
            const response = await fetch('/api/v1/core/auth/password-reset/request/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(csrf ? { 'X-CSRFToken': csrf } : {})
                },
                body: JSON.stringify({ email }),
                credentials: 'include',
            });
            
            const data = await response.json().catch(() => ({}));
            
            // La respuesta debe ser 200 siempre (evitar enumeración de usuarios)
            if (response.ok || response.status === 200) {
                showAlert('success', 'Si el email existe en este tenant, recibirás un enlace para restablecer tu contraseña.');
                $('reset-request-form').reset();
            } else {
                // Si hay un error específico (ej: usuario sin contraseña usable)
                if (response.status === 400 && data.detail) {
                    showAlert('error', data.detail);
                } else {
                    showAlert('error', 'Error al procesar la solicitud. Intenta nuevamente.');
                }
            }
        } catch (error) {
            console.error('Error en reset request:', error);
            showAlert('error', 'Error de red. Intenta nuevamente.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Enviar instrucciones';
        }
    });
})(window, document);
