/**
 * Feature: Editor - Servicios v2.61.3
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
 * - w.ServiciosList (definido en servicios_list.js) - Feature: Listado (para recargar tabla)
 * 
 * CRUD:
 * - CREATE: Crear nuevo servicio
 * - UPDATE: Actualizar servicio existente
 */
(function(w, d) {
    'use strict';

    const MOD = '[servicios.editor]';
    const CORE_API_BASE = '/api/v1/inventario/servicios'; // Core API Facade
    const FORM_ID = '#form-servicio';
    const FEEDBACK_ID = '#form-inventario-servicio-feedback';
    const OFFCANVAS_ID = '#offcanvas-inventario-servicio';
    
    // ⚠️ v2.61.3: Flag para prevenir doble envío
    let _guardandoServicio = false;



    /**
     * Recolectar datos del formulario de servicio
     * @returns {Object|null} Datos del servicio o null si hay error
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
            descripcion: formData.get('descripcion')?.trim() || '',
            precio_venta: parseFloat(formData.get('precio_venta') || '0') || 0,
            activo: formData.get('activo') === 'on' || formData.get('activo') === 'true',
        };

        // Validación básica
        if (!payload.codigo || !payload.nombre) {
            mostrarError('Los campos Código y Nombre son requeridos.');
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
     * Obtener ID de servicio desde el formulario
     * @returns {string|null} ID del servicio o null si es creación
     */
    function obtenerServicioId() {
        const form = d.querySelector(FORM_ID);
        if (!form) return null;
        
        const idInput = form.querySelector('#servicio-id');
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
            '#servicio-categoria', 'SERVICIO', categoriaSeleccionada, 'Sin categoria'
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
     * Guardar servicio (crear o actualizar)
     * ⚠️ v2.61.3: CRUD - CREATE/UPDATE
     * ⚠️ Protección contra doble envío
     * @param {Event} e - Evento del formulario (opcional)
     */
    async function guardarServicio(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // ⚠️ v2.61.3: Prevenir doble envío
        if (_guardandoServicio) {
            console.warn(`${MOD} Guardado ya en proceso, ignorando solicitud duplicada`);
            return;
        }

        ocultarError();

        const payload = recolectarDatosFormulario();
        if (!payload) {
            return;
        }

        // ⚠️ v2.61.3: Activar flag y deshabilitar botón
        _guardandoServicio = true;
        const btnGuardar = d.querySelector('#btn-guardar-servicio');
        const btnOriginalHTML = btnGuardar ? btnGuardar.innerHTML : '';
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        const servicioId = obtenerServicioId();
        let res;

        // ⚠️ v2.61.3: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
            console.error(`${MOD} Sintel.Core.Http no está disponible`);
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError({ status: 500, data: { detail: 'API no disponible' } }, MOD);
            }
            return;
        }

        try {
            if (servicioId) {
                // ⚠️ UPDATE: Actualizar servicio existente
                console.log(`${MOD} Actualizando servicio ID: ${servicioId}`);
                res = await w.Sintel.Core.Http.request('PATCH', `${CORE_API_BASE}/${servicioId}/`, payload);
            } else {
                // ⚠️ CREATE: Crear nuevo servicio
                console.log(`${MOD} Creando nuevo servicio`);
                res = await w.Sintel.Core.Http.request('POST', `${CORE_API_BASE}/`, payload);
            }

            // ⚠️ v2.61.3: Aislamiento Gradual - Solo verificar ok
            if (!res.ok) {
                // Restaurar botón en caso de error
                _guardandoServicio = false;
                if (btnGuardar) {
                    btnGuardar.disabled = false;
                    btnGuardar.innerHTML = btnOriginalHTML;
                }
                
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(res, MOD, {
                        modalSelector: OFFCANVAS_ID,
                        errorContainerSelector: FEEDBACK_ID
                    });
                } else {
                    mostrarError(res.data?.detail || res.data?.message || 'Error al guardar el servicio');
                }
                return;
            }

            // ⚠️ v2.61.3: Resetear flag después de éxito
            _guardandoServicio = false;
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = btnOriginalHTML;
            }

            // Éxito
            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                const accion = servicioId ? 'actualizado' : 'creado';
                w.SintelFeedback.success(`Servicio ${accion} correctamente`);
            }

            // Cerrar offcanvas
            cerrarOffcanvas();

            // Recargar tabla de servicios
            if (w.ServiciosList && typeof w.ServiciosList.recargar === 'function') {
                w.ServiciosList.recargar();
            } else if (window.SintelInventarioTables && window.SintelInventarioTables.servicios) {
                window.SintelInventarioTables.servicios.replaceData();
            }

        } catch (error) {
            console.error(`${MOD} Error al guardar servicio:`, error);
            // ⚠️ v2.61.3: Restaurar estado en caso de excepción
            _guardandoServicio = false;
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = btnOriginalHTML;
            }
            mostrarError('Error inesperado al guardar el servicio');
        }
    }

    /**
     * Inicializar eventos del formulario
     * ⚠️ v2.61.3: Prevenir listeners duplicados usando data-init flag
     */
    function initFormEvents() {
        const form = d.querySelector(FORM_ID);
        if (!form) {
            console.warn(`${MOD} Formulario ${FORM_ID} no encontrado`);
            return;
        }

        // ⚠️ v2.61.3: Prevenir duplicación de listeners
        if (form.getAttribute('data-init') === 'true') {
            console.log(`${MOD} Formulario ya inicializado, omitiendo.`);
            return;
        }
        form.setAttribute('data-init', 'true');

        // ⚠️ Prevenir submit nativo del formulario
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            guardarServicio(e);
        });

        // Botón guardar (si existe)
        const btnGuardar = form.querySelector('#btn-guardar-servicio');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', function(e) {
                e.preventDefault();
                guardarServicio(e);
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
            const selectCategoria = form.querySelector('#servicio-categoria');
            if (selectCategoria) {
                // Leer el UUID de categoría actual (data-attr del template) para re-seleccionar tras JS load
                const categoriaUuid = selectCategoria.dataset.categoriaUuid || null;
                cargarCategorias(categoriaUuid);
            }


        }
    }



    // ⚠️ Exposición global del módulo
    if (!w.ServiciosEditor) {
        w.ServiciosEditor = {
            init: init,
            guardar: guardarServicio,
            recolectarDatos: recolectarDatosFormulario,
            cargarCategorias: cargarCategorias,
            cerrar: cerrarOffcanvas
        };
    }

    // ── Historial Servicio ────────────────────────────────────────────────────

    async function initHistorialServicio() {
        const form = d.querySelector('#form-historial-servicio');
        if (!form || form.getAttribute('data-init') === 'true') return;
        form.setAttribute('data-init', 'true');

        // Poblar select de servicios activos
        const select = form.querySelector('#historial-servicio-select');
        if (select && select.options.length <= 1) {
            try {
                const res = await w.Sintel.Core.Http.request('GET', '/api/v1/inventario/servicios/?activo=true&page_size=200');
                if (res.ok && res.data) {
                    const items = res.data.results || res.data;
                    items.forEach(function(s) {
                        const opt = d.createElement('option');
                        opt.value = s.id;
                        opt.textContent = `${s.codigo ? s.codigo + ' — ' : ''}${s.nombre}`;
                        select.appendChild(opt);
                    });
                }
            } catch (_) {}
        }

        // Guardar historial
        const btnGuardar = form.querySelector('#btn-guardar-historial');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', async function() {
                const errorDiv = d.querySelector('#form-historial-feedback');
                if (errorDiv) { errorDiv.classList.add('d-none'); errorDiv.textContent = ''; }

                if (!form.checkValidity()) { form.reportValidity(); return; }

                const fd = new FormData(form);
                const payload = {
                    servicio: fd.get('servicio') || null,
                    fecha_registro: fd.get('fecha_registro') || null,
                    cantidad: parseFloat(fd.get('cantidad') || '0') || 0,
                    valor_cobrado: parseFloat(fd.get('valor_cobrado') || '0') || 0,
                    origen_referencia: fd.get('origen_referencia')?.trim() || null,
                    observaciones: fd.get('observaciones')?.trim() || null,
                };
                if (!payload.servicio) {
                    if (errorDiv) { errorDiv.textContent = 'Seleccione un servicio.'; errorDiv.classList.remove('d-none'); }
                    return;
                }

                const original = btnGuardar.innerHTML;
                btnGuardar.disabled = true;
                btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Registrando...';

                const res = await w.Sintel.Core.Http.request('POST', '/api/v1/inventario/historial-servicios/', payload);

                btnGuardar.disabled = false;
                btnGuardar.innerHTML = original;

                if (!res.ok) {
                    const msg = res.data?.detail || res.data?.non_field_errors?.[0] || JSON.stringify(res.data) || 'Error al registrar';
                    if (errorDiv) { errorDiv.textContent = msg; errorDiv.classList.remove('d-none'); }
                    return;
                }

                if (w.SintelFeedback) w.SintelFeedback.success('Historial registrado correctamente');

                // Cerrar offcanvas de historial
                const offEl = d.getElementById('offcanvas-historial-servicio');
                if (offEl && w.bootstrap?.Offcanvas) {
                    const inst = bootstrap.Offcanvas.getInstance(offEl);
                    if (inst) inst.hide();
                }

                // Recargar tabla si está disponible
                if (w.ServiciosList && typeof w.ServiciosList.recargar === 'function') {
                    w.ServiciosList.recargar();
                }
            });
        }
    }

    // ⚠️ HTMX: Reinicializar cuando se carga el offcanvas
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', function(event) {
            if (event.detail.target.id === 'offcanvas-container-historial-servicio') {
                setTimeout(initHistorialServicio, 50);
            }
            if (event.detail.target.id === 'offcanvas-container-servicios') {
                // ⚠️ v2.61.3: Limpiar el flag para permitir la reinicialización del editor
                const form = d.querySelector(FORM_ID);
                if (form) {
                    form.removeAttribute('data-init');
                }
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
