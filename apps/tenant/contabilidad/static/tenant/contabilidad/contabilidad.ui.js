/**
 * UI Module para Contabilidad (API-First).
 * 
 * Este módulo inicializa la UI de contabilidad después de que el partial HTML es inyectado.
 * Carga datos desde las APIs JSON de la app contabilidad.
 * 
 * ⚠️ API-First: Todos los datos se obtienen vía fetch() desde /api/v1/contabilidad/
 */
(function() {
    'use strict';
    
    const ContabilidadUI = {
        /**
         * Inicializa la UI de contabilidad.
         * 
         * Se llama automáticamente después de que el partial es inyectado vía HTMX.
         */
        init: function() {
            const summaryElement = document.querySelector('[data-partial="contabilidad-summary"]');
            if (!summaryElement) {
                console.warn('ContabilidadUI: No se encontró el elemento [data-partial="contabilidad-summary"]');
                return;
            }
            
            // Cargar datos de contabilidad desde la API
            this.loadContabilidadData();
        },
        
        /**
         * Carga los datos de contabilidad desde la API JSON.
         */
        loadContabilidadData: async function() {
            const loadingEl = document.getElementById('contabilidad-loading');
            const contentEl = document.getElementById('contabilidad-content');
            const errorEl = document.getElementById('contabilidad-error');
            
            try {
                // Obtener CSRF token
                const csrftoken = this.getCookie('csrftoken') || '';
                
                // Fetch resumen contable
                // Obtener cuentas contables y calcular resumen
                const response = await fetch('/api/v1/contabilidad/cuentas-contables/', {
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
                
                // La API puede retornar un objeto con 'results' (paginación) o un array directo
                const cuentas = data.results || (Array.isArray(data) ? data : []);
                
                // Calcular resumen desde las cuentas
                // Nota: Las cuentas no tienen saldo directo, solo tipo
                // Para un resumen real, se necesitaría calcular desde movimientos
                const resumen = this.calcularResumen(cuentas);
                this.renderResumen(resumen);
                if (contentEl) contentEl.style.display = 'block';
            } catch (error) {
                console.error('ContabilidadUI: Error al cargar datos:', error);
                if (loadingEl) loadingEl.style.display = 'none';
                if (contentEl) contentEl.style.display = 'none';
                if (errorEl) {
                    errorEl.textContent = 'Error al cargar resumen contable.';
                    errorEl.style.display = 'block';
                }
            }
        },
        
        /**
         * Calcula el resumen contable desde las cuentas.
         * 
         * Nota: Las cuentas no tienen saldo directo.
         * Para un resumen real, se necesitaría calcular desde movimientos contables.
         * Por ahora, solo contamos cuentas por tipo.
         */
        calcularResumen: function(cuentas) {
            const resumen = {
                activos: 0,
                pasivos: 0,
                patrimonio: 0,
            };
            
            if (Array.isArray(cuentas)) {
                // Contar cuentas activas por tipo (no saldos, ya que no están en el modelo)
                cuentas.forEach(cuenta => {
                    if (cuenta.activa !== false) {
                        if (cuenta.tipo === 'ACTIVO') {
                            resumen.activos++;
                        } else if (cuenta.tipo === 'PASIVO') {
                            resumen.pasivos++;
                        } else if (cuenta.tipo === 'PATRIMONIO') {
                            resumen.patrimonio++;
                        }
                    }
                });
            }
            
            // Si no hay datos, mostrar "-"
            if (resumen.activos === 0 && resumen.pasivos === 0 && resumen.patrimonio === 0) {
                return { activos: null, pasivos: null, patrimonio: null };
            }
            
            return resumen;
        },
        
        /**
         * Renderiza el resumen contable en el DOM.
         */
        renderResumen: function(resumen) {
            const setValue = (id, value) => {
                const el = document.getElementById(id);
                if (el) {
                    if (value === null || value === undefined) {
                        el.textContent = '-';
                    } else if (typeof value === 'number') {
                        // Si es número, mostrar como cantidad de cuentas o saldo
                        el.textContent = value > 0 ? value.toString() : '-';
                    } else {
                        el.textContent = value;
                    }
                }
            };
            
            setValue('contabilidad-activos', resumen.activos);
            setValue('contabilidad-pasivos', resumen.pasivos);
            setValue('contabilidad-patrimonio', resumen.patrimonio);
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
    window.ContabilidadUI = ContabilidadUI;
})();
