/**
 * empresa.module.js - Orquestador del módulo Empresa v2.60
 * 
 * Responsabilidad:
 * - Gestión de la Ficha de Empresa (Singleton UI)
 * - Carga y actualización de configuración global
 * - Integración con UIManager para notificaciones
 */
(function(w, d) {
    'use strict';
    
    const MOD = '[empresa.module]';
    const API_URL = '/api/v1/empresa/configuracion/';
    const FORM_SELECTOR = '#form-empresa-config';
    const LOGO_INPUT_SELECTOR = '#input-empresa-logo';
    const LOGO_PREVIEW_SELECTOR = '#img-empresa-logo-preview';

    /**
     * Inicializa el módulo
     */
    function init() {
        console.log(`${MOD} Inicializando módulo...`);
        loadEmpresaConfig();
        setupEventListeners();
    }

    /**
     * Carga la configuración actual de la empresa
     */
    async function loadEmpresaConfig() {
        if (!w.http) {
            console.error(`${MOD} w.http no disponible`);
            return;
        }

        try {
            // endpoint singleton: /api/v1/empresa/configuracion/
            // El backend retorna una lista paginada (estándar DRF) o el objeto directo si se usa retrieve
            // Dado que es singleton, usamos list y tomamos el primero, o esperamos que el backend maneje el singleton
            const response = await w.http('GET', API_URL);
            
            if (response.ok) {
                const data = response.data;
                // Si es paginado, tomar el primer resultado
                const empresa = (data.results && data.results.length > 0) ? data.results[0] : data;
                
                if (empresa && empresa.id) {
                    populateForm(empresa);
                } else {
                    console.warn(`${MOD} No se encontró configuración de empresa.`);
                }
            } else {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(response, MOD);
                } else if (w.SintelFeedback && typeof w.SintelFeedback.handleAPIError === 'function') {
                    w.SintelFeedback.handleAPIError(response, MOD);
                } else {
                    console.error(`${MOD} Error de API (404/500):`, response);
                }
            }
        } catch (error) {
            console.error(`${MOD} Error cargando config:`, error);
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError({ ok: false, status: 500, data: { detail: error.message } }, MOD);
            } else if (w.SintelFeedback && typeof w.SintelFeedback.handleAPIError === 'function') {
                w.SintelFeedback.handleAPIError({ ok: false, status: 500, data: { detail: error.message } }, MOD);
            } else {
                console.error(`${MOD} Error al cargar configuración:`, error);
            }
        }
    }

    /**
     * Rellena el formulario con los datos
     */
    function populateForm(data) {
        const form = d.querySelector(FORM_SELECTOR);
        if (!form) return;

        // Mapeo simple de campos por ID o name
        Object.keys(data).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = data[key] || '';
            }
        });

        // Preview de logo
        if (data.logo) {
            const img = d.querySelector(LOGO_PREVIEW_SELECTOR);
            if (img) img.src = data.logo;
        }
        
        // Guardar ID para PATCH
        form.setAttribute('data-id', data.id);
    }

    /**
     * Configura listeners del formulario
     */
    function setupEventListeners() {
        const form = d.querySelector(FORM_SELECTOR);
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveEmpresaConfig(form);
        });

        // Preview de imagen al seleccionar archivo
        const logoInput = d.querySelector(LOGO_INPUT_SELECTOR);
        if (logoInput) {
            logoInput.addEventListener('change', function(e) {
                if (this.files && this.files[0]) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const img = d.querySelector(LOGO_PREVIEW_SELECTOR);
                        if (img) img.src = e.target.result;
                    }
                    reader.readAsDataURL(this.files[0]);
                }
            });
        }
    }

    /**
     * Guarda los cambios (PATCH)
     */
    async function saveEmpresaConfig(form) {
        const id = form.getAttribute('data-id');
        if (!id) {
            console.error(`${MOD} No hay ID de empresa para actualizar`);
            return;
        }

        const formData = new FormData(form);
        // Si el input file está vacío, eliminarlo para no enviar update vacío
        const logoInput = d.querySelector(LOGO_INPUT_SELECTOR);
        if (logoInput && logoInput.files.length === 0) {
            formData.delete('logo');
        }

        try {
            // PATCH /api/v1/empresa/configuracion/{id}/
            const response = await w.http('PATCH', `${API_URL}${id}/`, formData);

            if (response.ok) {
                if (w.SintelFeedback) {
                    w.SintelFeedback.success('Configuración de empresa actualizada correctamente');
                }
                // Recargar datos para asegurar consistencia
                loadEmpresaConfig();
                
                // Notificar cambio global (por si el logo cambió en el header)
                d.dispatchEvent(new CustomEvent('sintel:empresa-updated', { detail: response.data }));
            } else {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(response, MOD);
                } else if (w.SintelFeedback && typeof w.SintelFeedback.handleAPIError === 'function') {
                    w.SintelFeedback.handleAPIError(response, MOD);
                } else {
                    console.error(`${MOD} Error de API (404/500):`, response);
                }
            }
        } catch (error) {
            console.error(`${MOD} Error guardando config:`, error);
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError({ ok: false, status: 500, data: { detail: error.message } }, MOD);
            } else if (w.SintelFeedback && typeof w.SintelFeedback.handleAPIError === 'function') {
                w.SintelFeedback.handleAPIError({ ok: false, status: 500, data: { detail: error.message } }, MOD);
            } else {
                console.error(`${MOD} Error al guardar configuración:`, error);
            }
        }
    }

    // Exponer API pública
    w.EmpresaModule = {
        init: init,
        refresh: loadEmpresaConfig
    };

    // Lazy init si se usa en un tab específico
    const TAB_SELECTOR = '#tab-empresa';
    if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
        w.DOMUtils.onVisibleOnce(TAB_SELECTOR, init);
    } else {
        d.addEventListener('DOMContentLoaded', () => {
            // Fallback: verificar si el tab está activo o inicializar si es la vista principal
            const tab = d.querySelector(TAB_SELECTOR);
            if (tab && !tab.classList.contains('d-none')) {
                init();
            }
        });
    }

})(window, document);
