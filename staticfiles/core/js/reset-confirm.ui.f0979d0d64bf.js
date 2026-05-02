/**
 * UI Module para Reset Confirm (API-First).
 * ⚠️ DEPRECADO: Este archivo está en apps/public/core pero los flujos de auth son tenant-hosted.
 * ⚠️ NOTA: Este archivo puede ser usado desde el dominio público, pero debe redirigir al tenant.
 * ⚠️ POLÍTICA: Consumir Core API centralizado: /api/v1/core/auth/password-reset/*
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
                pageTitleEl.textContent = `Definir nueva contraseña - ${nombre}`;
            }
        }
    } catch (error) {
        console.warn('No se pudo cargar el branding:', error);
    }
}

(async function() {
    // Cargar branding al inicio
    await loadBranding();
    const $ = (id) => document.getElementById(id);
    const csrf = getCookie('csrftoken');
    
    const qs = new URLSearchParams(location.search);
    // Unificar: aceptar uid o uidb64 (ambos son equivalentes)
    const uid = qs.get('uidb64') || qs.get('uid');
    const token = qs.get('token');
    
    if (!uid || !token) {
        $('invalid').style.display = 'block';
        return;
    }
    
    // VALIDATE: Verificar token antes de mostrar formulario
    // Enviar uid (la API acepta tanto uid como uidb64)
    try {
        // ⚠️ POLÍTICA: Consumir Core API centralizado
        const validateUrl = `/api/v1/core/auth/password-reset/validate/`;
        const validateResponse = await fetch(validateUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                uid: uid,
                token: token,
            }),
            credentials: 'include',
        });
        
        if (!validateResponse.ok) {
            $('invalid').style.display = 'block';
            return;
        }
        
        // Mostrar formulario si es válido
        $('reset-confirm-form').style.display = 'block';
    } catch (error) {
        console.error('Error validando token:', error);
        $('invalid').style.display = 'block';
        return;
    }
    
    // CONFIRM: Manejar envío del formulario
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
    
    $('reset-confirm-form')?.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        clearErrors();
        
        const p1 = $('npw1').value.trim();
        const p2 = $('npw2').value.trim();
        
        // Validación cliente
        if (p1.length < 8) {
            setError('npw1', 'La contraseña debe tener al menos 8 caracteres.');
            return;
        }
        
        if (p1 !== p2) {
            setError('npw2', 'Las contraseñas no coinciden.');
            return;
        }
        
        const submitBtn = $('submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Guardando...';
        
        try {
            // ⚠️ POLÍTICA: Consumir Core API centralizado
            const response = await fetch('/api/v1/core/auth/password-reset/confirm/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(csrf ? { 'X-CSRFToken': csrf } : {})
                },
                body: JSON.stringify({ 
                    uid: uid,  // Unificado: usar uid (la API acepta uid o uidb64)
                    token: token, 
                    password1: p1, 
                    password2: p2 
                }),
                credentials: 'include',
            });
            
            const data = await response.json().catch(() => ({}));
            
            if (response.ok) {
                // Mostrar mensaje de éxito con opción de ir a la página principal
                const form = $('reset-confirm-form');
                const successMsg = $('success-message');
                const title = $('title');
                
                if (form) form.style.display = 'none';
                if (title) title.textContent = 'Contraseña restablecida';
                if (successMsg) {
                    successMsg.style.display = 'block';
                    // Usar redirect_url de la API (Opción A: "/" - página principal del tenant)
                    // Si no está disponible, usar "/" como fallback
                    const redirectUrl = data.redirect_url || '/';
                    // Opcional: redirigir automáticamente después de 3 segundos
                    setTimeout(() => {
                        window.location.replace(redirectUrl);
                    }, 3000);
                } else {
                    // Fallback: redirigir inmediatamente si no hay elemento de éxito
                    const redirectUrl = data.redirect_url || '/';
                    window.location.replace(redirectUrl);
                }
            } else {
                // Mostrar errores de validación
                if (data.password1) {
                    setError('npw1', Array.isArray(data.password1) ? data.password1[0] : data.password1);
                }
                if (data.password2) {
                    setError('npw2', Array.isArray(data.password2) ? data.password2[0] : data.password2);
                }
                if (data.detail) {
                    const formError = $('form-error');
                    formError.textContent = data.detail;
                    formError.classList.add('show');
                }
                submitBtn.disabled = false;
                submitBtn.textContent = 'Guardar y continuar';
            }
        } catch (error) {
            console.error('Error en reset confirm:', error);
            const formError = $('form-error');
            formError.textContent = 'Error de red. Intenta nuevamente.';
            formError.classList.add('show');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Guardar y continuar';
        }
    });
})(window, document);
