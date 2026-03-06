/**
 * UI Module para Perfil (API-First).
 * 
 * Este módulo inicializa la UI de perfil después de que el partial HTML es inyectado.
 * Carga datos desde las APIs JSON de la app perfil.
 * 
 * ⚠️ API-First: Todos los datos se obtienen vía fetch() desde /api/v1/perfil/
 */
(function() {
    'use strict';
    
    const PerfilUI = {
        /**
         * Inicializa la UI de perfil.
         * 
         * Se llama automáticamente después de que el partial es inyectado vía HTMX.
         */
        init: function() {
            const cardElement = document.querySelector('[data-partial="perfil-card"]');
            if (!cardElement) {
                console.warn('PerfilUI: No se encontró el elemento [data-partial="perfil-card"]');
                return;
            }
            
            // Cargar datos de perfil desde la API
            this.loadPerfilData();
        },
        
        /**
         * Carga los datos de perfil desde la API JSON.
         */
        loadPerfilData: async function() {
            const loadingEl = document.getElementById('perfil-loading');
            const contentEl = document.getElementById('perfil-content');
            const errorEl = document.getElementById('perfil-error');
            
            try {
                // Obtener CSRF token
                const csrftoken = this.getCookie('csrftoken') || '';
                
                // Fetch datos de perfil
                // La ruta es /api/v1/perfil/perfiles/me/ según el ViewSet
                const response = await fetch('/api/v1/perfil/perfiles/me/', {
                    method: 'GET',
                    credentials: 'same-origin',
                    headers: {
                        'X-CSRFToken': csrftoken,
                    },
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                
                // Ocultar loading, mostrar contenido
                if (loadingEl) loadingEl.style.display = 'none';
                if (errorEl) errorEl.style.display = 'none';
                
                if (data && data.id) {
                    // Hay perfil: mostrar datos
                    this.renderPerfilData(data);
                    if (contentEl) contentEl.style.display = 'block';
                } else {
                    // No hay perfil: mostrar mensaje
                    if (contentEl) {
                        contentEl.innerHTML = '<p>No hay perfil registrado. <a href="/perfil/">Crear perfil</a></p>';
                        contentEl.style.display = 'block';
                    }
                }
            } catch (error) {
                console.error('PerfilUI: Error al cargar datos:', error);
                if (loadingEl) loadingEl.style.display = 'none';
                if (contentEl) contentEl.style.display = 'none';
                if (errorEl) {
                    errorEl.textContent = 'Error al cargar perfil.';
                    errorEl.style.display = 'block';
                }
            }
        },
        
        /**
         * Renderiza los datos de perfil en el DOM.
         */
        renderPerfilData: function(perfil) {
            const setValue = (id, value) => {
                const el = document.getElementById(id);
                if (el) el.textContent = value || '-';
            };
            
            setValue('perfil-cargo-value', perfil.cargo);
            setValue('perfil-departamento-value', perfil.departamento);
            setValue('perfil-telefono-value', perfil.telefono_corporativo);
        },
        
        /**
         * Obtiene una cookie por nombre.
         */
        getCookie: function(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },
    };
    
    // Exponer globalmente
    window.PerfilUI = PerfilUI;
})();
