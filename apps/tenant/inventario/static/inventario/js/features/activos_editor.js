/**
 * Feature: Editor - Activos Fijos v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (CORE_API_BASE)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - Sintel.Core.Http (F32.7, core-http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 * - w.inventarioAPI (definido en inventario.api.js) - API wrapper (opcional)
 * - w.ActivosList (definido en activos_list.js) - Feature: Listado (para recargar tabla)
 * 
 * CRUD:
 * - CREATE: Crear nuevo activo fijo
 * - UPDATE: Actualizar activo fijo existente
 */
(function(w, d) {
    'use strict';

    const MOD = '[activos.editor]';
    const CORE_API_BASE = '/api/v1/inventario/activos'; // Core API Facade
    const FORM_ID = '#form-activo';
    const FEEDBACK_ID = '#form-activo-feedback';
    const OFFCANVAS_ID = '#offcanvas-activos';

    // Protección contra doble envío (mismo patrón que productos_editor.js/servicios_editor.js).
    let _guardandoActivo = false;

    /**
     * Recolectar datos del formulario de activo
     * @returns {Object|null} Datos del activo o null si hay error
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector(FORM_ID);
        if (!form) {
            console.error(`${MOD} Formulario ${FORM_ID} no encontrado`);
            return null;
        }

        const formData = new FormData(form);
        const payload = {
            codigo: formData.get('codigo')?.trim() || '',
            nombre: formData.get('nombre')?.trim() || '',
            categoria: formData.get('categoria') || null,
            marca: formData.get('marca')?.trim() || '',
            modelo: formData.get('modelo')?.trim() || '',
            descripcion: formData.get('descripcion')?.trim() || '',
            ubicacion: formData.get('ubicacion')?.trim() || '',
            responsable: formData.get('responsable')?.trim() || '',
            fecha_adquisicion: formData.get('fecha_adquisicion') || null,
            costo_adquisicion: parseFloat(formData.get('costo_adquisicion') || '0') || 0,
            estado: formData.get('estado') || 'ACTIVO',
        };

        // Validación básica
        if (!payload.codigo || !payload.nombre || !payload.estado) {
            mostrarError('Los campos Código, Nombre y Estado son requeridos.');
            return null;
        }
        if (payload.codigo.length < 2) {
            mostrarError('El Código debe tener al menos 2 caracteres.');
            return null;
        }
        if (payload.codigo.length > 64) {
            mostrarError('El Código no puede superar 64 caracteres.');
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
     * Obtener ID de activo desde el formulario
     * @returns {string|null} ID del activo o null si es creación
     */
    function obtenerActivoId() {
        const form = d.querySelector(FORM_ID);
        if (!form) return null;
        
        const idInput = form.querySelector('#activo-id');
        if (!idInput) return null;
        
        const id = idInput.value?.trim();
        return id || null;
    }

    /**
     * Cargar categorias en el select via Utils centralizado (cache 5min)
     * @param {number|null} categoriaSeleccionada - ID de categoria a seleccionar
     */
    async function cargarCategorias(categoriaSeleccionada = null) {
        await w.Sintel.Inventario.Utils.loadCategoriasSelect(
            '#activo-categoria', 'ACTIVO', categoriaSeleccionada, 'Seleccione...'
        );
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
     * Guardar activo (crear o actualizar)
     * ⚠️ v2.61.3: CRUD - CREATE/UPDATE
     * @param {Event} e - Evento del formulario (opcional)
     */
    async function guardarActivo(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        if (_guardandoActivo) {
            console.warn(`${MOD} Guardado ya en proceso, ignorando solicitud duplicada`);
            return;
        }

        ocultarError();

        const payload = recolectarDatosFormulario();
        if (!payload) {
            return;
        }

        _guardandoActivo = true;
        const btnGuardar = d.querySelector(FORM_ID + ' #btn-guardar-activo');
        const btnOriginalHTML = btnGuardar ? btnGuardar.innerHTML : '';
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        const activoId = obtenerActivoId();
        let res;

        // ⚠️ v2.61.3: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
            console.error(`${MOD} Sintel.Core.Http no está disponible`);
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError({ status: 500, data: { detail: 'API no disponible' } }, MOD);
            }
            _guardandoActivo = false;
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = btnOriginalHTML;
            }
            return;
        }

        try {
            if (activoId) {
                // ⚠️ UPDATE: Actualizar activo existente
                console.log(`${MOD} Actualizando activo ID: ${activoId}`);
                res = await w.Sintel.Core.Http.request('PATCH', `${CORE_API_BASE}/${activoId}/`, payload);
            } else {
                // ⚠️ CREATE: Crear nuevo activo
                console.log(`${MOD} Creando nuevo activo`);
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
                    mostrarError(res.data?.detail || res.data?.message || 'Error al guardar el activo');
                }
                return;
            }

            // Éxito
            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                const accion = activoId ? 'actualizado' : 'creado';
                w.SintelFeedback.success(`Activo fijo ${accion} correctamente`);
            }

            // Cerrar offcanvas
            cerrarOffcanvas();

            // Recargar tabla de activos
            if (w.ActivosList && typeof w.ActivosList.recargar === 'function') {
                w.ActivosList.recargar();
            } else if (window.SintelInventarioTables && window.SintelInventarioTables.activos) {
                window.SintelInventarioTables.activos.replaceData();
            }

        } catch (error) {
            console.error(`${MOD} Error al guardar activo:`, error);
            mostrarError('Error inesperado al guardar el activo');
        } finally {
            _guardandoActivo = false;
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = btnOriginalHTML;
            }
        }
    }

    /**
     * Inicializar eventos del formulario
     */
    function initFormEvents() {
        const form = d.querySelector(FORM_ID);
        if (!form) {
            console.warn(`${MOD} Formulario ${FORM_ID} no encontrado`);
            return;
        }

        // Guard (FE-A1): evita registrar el submit 2 veces si init() se llama
        // mas de una vez para el mismo form.
        if (form.dataset.editorInitialized) return;
        form.dataset.editorInitialized = 'true';

        // ⚠️ Prevenir submit nativo del formulario
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            guardarActivo(e);
        });

        // Botón guardar (si existe)
        const btnGuardar = form.querySelector('#btn-guardar-activo');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', function(e) {
                e.preventDefault();
                guardarActivo(e);
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
        
        // Cargar categorías si el select existe
        const form = d.querySelector(FORM_ID);
        if (form) {
            const selectCategoria = form.querySelector('#activo-categoria');
            if (selectCategoria) {
                const activoId = obtenerActivoId();
                // Si es edición, obtener la categoría del activo
                if (activoId) {
                    // La categoría ya viene en el template, solo cargar opciones
                    cargarCategorias();
                } else {
                    // Si es creación, cargar categorías sin selección
                    cargarCategorias();
                }
            }


        }
    }



    // ⚠️ Exposición global del módulo
    if (!w.ActivosEditor) {
        w.ActivosEditor = {
            init: init,
            guardar: guardarActivo,
            recolectarDatos: recolectarDatosFormulario,
            cargarCategorias: cargarCategorias,
            cerrar: cerrarOffcanvas
        };
    }

    // ⚠️ HTMX: Reinicializar cuando se carga el offcanvas
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', function(event) {
            if (event.detail.target.id === 'offcanvas-container-activos') {
                // Esperar un momento para que el DOM se actualice
                setTimeout(function() {
                    const offcanvasEl = d.querySelector(OFFCANVAS_ID);
                    if (offcanvasEl) {
                        console.log(`${MOD} Offcanvas cargado vía HTMX, inicializando editor...`);
                        init();
                    }
                }, 50);
            }
        });
    }

    // ⚠️ Bootstrap: Reinicializar cuando se muestra el offcanvas
    if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
        const offcanvasEl = d.querySelector(OFFCANVAS_ID);
        if (offcanvasEl) {
            offcanvasEl.addEventListener('shown.bs.offcanvas', function() {
                console.log(`${MOD} Offcanvas mostrado, inicializando editor...`);
                init();
            });
        }
    }

})(window, document);
