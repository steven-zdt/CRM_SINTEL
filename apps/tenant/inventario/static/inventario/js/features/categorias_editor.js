/**
 * Feature: Editor - Categorías v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (CORE_API_BASE)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - Sintel.Core.Http (F32.7, core-http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 * - w.Sintel.Inventario.API (definido en inventario.api.js) - API wrapper
 * - w.Sintel.Inventario.Categorias.List (definido en categorias_list.js) - Feature: Listado
 */
(function(w, d) {
    'use strict';

    const MOD = '[categorias.editor]';
    const CORE_API_BASE = '/api/v1/inventario/categorias'; // Core API Facade
    const FORM_ID = '#form-categoria';
    const FEEDBACK_ID = '#form-categoria-feedback';
    const OFFCANVAS_ID = '#offcanvas-categorias';

    // Protección contra doble envío (mismo patrón que productos_editor.js/servicios_editor.js).
    let _guardandoCategoria = false;

    w.Sintel = w.Sintel || {};
    w.Sintel.Inventario = w.Sintel.Inventario || {};
    w.Sintel.Inventario.Categorias = w.Sintel.Inventario.Categorias || {};

    /**
     * Recolectar datos del formulario de categoría
     * @returns {Object|null} Datos de la categoría o null si hay error
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector(FORM_ID);
        if (!form) {
            console.error(`${MOD} Formulario ${FORM_ID} no encontrado`);
            return null;
        }

        const formData = new FormData(form);
        const payload = {
            nombre: formData.get('nombre')?.trim() || '',
            aplicacion: formData.get('aplicacion') || 'TODO',
            descripcion: formData.get('descripcion')?.trim() || '',
            activo: formData.get('activo') === 'on' || formData.get('activo') === 'true'
        };

        // Validación básica
        if (!payload.nombre || !payload.aplicacion) {
            mostrarError('Los campos Nombre y Aplicación son requeridos.');
            return null;
        }

        return payload;
    }

    /**
     * Mostrar error en el contenedor de feedback
     * @param {string} mensaje - Mensaje de error
     */
    function mostrarError(mensaje) {
        const errorContainer = d.querySelector(FEEDBACK_ID);
        if (errorContainer) {
            errorContainer.className = 'alert alert-danger';
            errorContainer.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>${mensaje}`;
            errorContainer.classList.remove('d-none');
        }
    }

    /**
     * Ocultar error
     */
    function ocultarError() {
        const errorContainer = d.querySelector(FEEDBACK_ID);
        if (errorContainer) {
            errorContainer.classList.add('d-none');
            errorContainer.innerHTML = '';
        }
    }

    /**
     * Obtener ID de categoría desde el formulario
     * @returns {string|null} ID de la categoría o null si es creación
     */
    function obtenerCategoriaId() {
        const form = d.querySelector(FORM_ID);
        if (!form) return null;
        
        const idInput = form.querySelector('#categoria-id');
        if (!idInput) return null;
        
        const id = idInput.value?.trim();
        return id || null;
    }

    /**
     * Cerrar offcanvas
     */
    function cerrarOffcanvas() {
        const offcanvasEl = d.querySelector(OFFCANVAS_ID);
        if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
            const instance = bootstrap.Offcanvas.getInstance(offcanvasEl);
            if (instance) {
                instance.hide();
            }
        }
    }

    /**
     * Guardar categoría (crear o actualizar)
     * ⚠️ v2.61.3: CRUD - CREATE/UPDATE
     * @param {Event} e - Evento del formulario (opcional)
     */
    async function guardarCategoria(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        if (_guardandoCategoria) {
            console.warn(`${MOD} Guardado ya en proceso, ignorando solicitud duplicada`);
            return;
        }

        ocultarError();

        const payload = recolectarDatosFormulario();
        if (!payload) {
            return;
        }

        _guardandoCategoria = true;
        const btnGuardar = d.querySelector(FORM_ID + ' #btn-guardar-categoria');
        const btnOriginalHTML = btnGuardar ? btnGuardar.innerHTML : '';
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        const categoriaId = obtenerCategoriaId();
        let res;

        // ⚠️ v2.61.3: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
            console.error(`${MOD} Sintel.Core.Http no está disponible`);
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError({ status: 500, data: { detail: 'API no disponible' } }, MOD);
            }
            _guardandoCategoria = false;
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = btnOriginalHTML;
            }
            return;
        }

        try {
            if (categoriaId) {
                // ⚠️ UPDATE: Actualizar categoría existente
                console.log(`${MOD} Actualizando categoría ID: ${categoriaId}`);
                res = await w.Sintel.Core.Http.request('PATCH', `${CORE_API_BASE}/${categoriaId}/`, payload);
            } else {
                // ⚠️ CREATE: Crear nueva categoría
                console.log(`${MOD} Creando nueva categoría`);
                res = await w.Sintel.Core.Http.request('POST', `${CORE_API_BASE}/`, payload);
            }

            // ⚠️ v2.61.3: Aislamiento Gradual - Solo verificar ok
            if (!res.ok) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(res, MOD, {
                        modalSelector: OFFCANVAS_ID,
                        errorContainerSelector: FEEDBACK_ID
                    });
                } else {
                    mostrarError(res.data?.detail || res.data?.message || 'Error al guardar la categoría');
                }
                return;
            }

            // Exito
            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                const accion = categoriaId ? 'actualizada' : 'creada';
                w.SintelFeedback.success(`Categoria ${accion} correctamente`);
            }

            // Invalidar cache de categorias para que los selects recarguen datos frescos
            if (w.Sintel?.Inventario?.Utils?.invalidateCache) {
                w.Sintel.Inventario.Utils.invalidateCache();
            }

            // Cerrar offcanvas
            cerrarOffcanvas();

            // Recargar tabla de categorías
            if (w.Sintel?.Inventario?.Categorias?.List && typeof w.Sintel.Inventario.Categorias.List.recargar === 'function') {
                w.Sintel.Inventario.Categorias.List.recargar();
            } else if (w.Sintel?.Inventario?.Tables?.categorias) {
                w.Sintel.Inventario.Tables.categorias.replaceData();
            } else if (w.CategoriasList && typeof w.CategoriasList.recargar === 'function') {
                w.CategoriasList.recargar();
            }

        } catch (error) {
            console.error(`${MOD} Error al guardar categoría:`, error);
            mostrarError('Error inesperado al guardar la categoría');
        } finally {
            _guardandoCategoria = false;
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = btnOriginalHTML;
            }
        }
    }

    /**
     * Inicializar eventos del formulario
     * ⚠️ v2.61.3: Previene duplicación usando flag data-init
     */
    function initFormEvents() {
        const form = d.querySelector(FORM_ID);
        if (!form) {
            console.warn(`${MOD} Formulario ${FORM_ID} no encontrado`);
            return;
        }

        // ⚠️ v2.61.3: Prevenir duplicación - verificar si ya está inicializado
        if (form.hasAttribute('data-init')) {
            console.log(`${MOD} Formulario ya inicializado, omitiendo...`);
            return;
        }

        // ⚠️ Marcar como inicializado
        form.setAttribute('data-init', 'true');

        // ⚠️ Prevenir submit nativo del formulario
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            guardarCategoria(e);
        });

        // Botón guardar (si existe)
        const btnGuardar = form.querySelector('#btn-guardar-categoria');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', function(e) {
                e.preventDefault();
                guardarCategoria(e);
            });
        }

        // Limpiar errores al cambiar campos
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', ocultarError);
            input.addEventListener('change', ocultarError);
        });
    }

    /**
     * Inicializar módulo de editor
     * ⚠️ Se llama cuando se carga el offcanvas vía HTMX
     */
    function init() {
        console.log(`${MOD} Inicializando módulo de editor...`);
        initFormEvents();
    }

    // ⚠️ Exposición global del módulo v3.5
    w.Sintel.Inventario.Categorias.Editor = {
        init: init,
        guardar: guardarCategoria,
        recolectarDatos: recolectarDatosFormulario,
        cerrar: cerrarOffcanvas
    };

    // Deprecated fallbacks
    w.CategoriasEditor = w.Sintel.Inventario.Categorias.Editor;

    // v2.61.3: Flag de módulo para prevenir doble inicialización (race condition HTMX + Bootstrap)
    let _editorInitialized = false;

    // v2.61.3: HTMX: Reinicializar cuando se carga el offcanvas
    // Solo usar htmx:afterSwap - fuente de verdad principal para offcanvas con HTMX
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', function(event) {
            if (event.detail.target.id === 'offcanvas-container-categorias') {
                // Esperar un momento para que el DOM se actualice
                setTimeout(function() {
                    const offcanvasEl = d.querySelector(OFFCANVAS_ID);
                    if (offcanvasEl) {
                        console.log(`${MOD} Offcanvas cargado via HTMX, inicializando editor...`);
                        // Limpiar flag data-init antes de inicializar (nuevo contenido)
                        const form = d.querySelector(FORM_ID);
                        if (form) {
                            form.removeAttribute('data-init');
                        }
                        _editorInitialized = false; // Resetear flag de módulo
                        init();
                        _editorInitialized = true;
                    }
                }, 50);
            }
        });
    }

    // Bootstrap: Solo inicializar si no se inicializó via HTMX (fallback para casos sin HTMX)
    if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
        const offcanvasEl = d.querySelector(OFFCANVAS_ID);
        if (offcanvasEl) {
            offcanvasEl.addEventListener('shown.bs.offcanvas', function() {
                const form = d.querySelector(FORM_ID);
                // Solo inicializar si no tiene data-init Y no fue inicializado por HTMX
                if (form && !form.hasAttribute('data-init') && !_editorInitialized) {
                    console.log(`${MOD} Offcanvas mostrado (sin HTMX), inicializando editor...`);
                    init();
                    _editorInitialized = true;
                }
            });

            // Resetear flag cuando el offcanvas se oculta para permitir reinits en la siguiente apertura
            offcanvasEl.addEventListener('hidden.bs.offcanvas', function() {
                _editorInitialized = false;
            });
        }
    }

})(window, document);
