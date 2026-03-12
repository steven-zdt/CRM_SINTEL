/**
 * Feature: Editor - Productos v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (CORE_API_BASE)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en lib/http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 * - w.inventarioAPI (definido en inventario.api.js) - API wrapper (opcional)
 * - w.ProductosList (definido en productos_list.js) - Feature: Listado (para recargar tabla)
 * 
 * CRUD:
 * - CREATE: Crear nuevo producto
 * - UPDATE: Actualizar producto existente
 */
(function(w, d) {
    'use strict';

    const MOD = '[productos.editor]';
    const CORE_API_BASE = '/api/v1/core/v1/inventario/productos'; // Core API Facade
    const FORM_PRODUCTO_ID = '#form-producto';
    const FORM_AJUSTE_ID = '#form-ajuste-inventario';
    const FEEDBACK_ID = '#form-inventario-feedback';
    const OFFCANVAS_ID = '#offcanvas-inventario';
    
    // ⚠️ v2.61.3: Flag para prevenir doble envío
    let _guardandoProducto = false;

    /**
     * Recolectar datos del formulario de producto
     * ⚠️ v2.61.3: Recolecta TODOS los campos del formulario, incluyendo numéricos
     * @returns {Object|null} Datos del producto o null si hay error
     */
    function recolectarDatosProducto() {
        const form = d.querySelector(FORM_PRODUCTO_ID);
        if (!form) {
            console.error(`${MOD} Formulario ${FORM_PRODUCTO_ID} no encontrado`);
            return null;
        }

        const formData = new FormData(form);
        
        // ⚠️ v2.61.3: Helper para parsear valores numéricos correctamente
        // ⚠️ Campos con default=0 en el modelo deben retornar 0, no null
        const parseDecimal = (value, defaultValue = 0) => {
            if (!value || value === '' || value === null || value === undefined) {
                return defaultValue;
            }
            const parsed = parseFloat(value);
            return isNaN(parsed) ? defaultValue : parsed;
        };

        const parseInteger = (value) => {
            if (!value || value === '' || value === null || value === undefined) {
                return null;
            }
            const parsed = parseInt(value, 10);
            return isNaN(parsed) ? null : parsed;
        };

        // ⚠️ v2.61.3: Recolectar TODOS los campos del formulario
        // ⚠️ IMPORTANTE: precio_venta y stock_minimo tienen default=0 en el modelo, no pueden ser null
        const precioVentaValue = formData.get('precio_venta');
        const stockMinimoValue = formData.get('stock_minimo');
        
        const payload = {
            codigo: formData.get('codigo')?.trim() || '',
            nombre: formData.get('nombre')?.trim() || '',
            categoria: parseInteger(formData.get('categoria')),
            unidad: formData.get('unidad')?.trim() || 'UND',
            descripcion: formData.get('descripcion')?.trim() || null,
            // ⚠️ v2.61.3: precio_venta y stock_minimo deben ser números (0 si está vacío)
            precio_venta: parseDecimal(precioVentaValue, 0),
            stock_minimo: parseDecimal(stockMinimoValue, 0),
            activo: d.querySelector('#producto-activo')?.checked !== false
        };

        // ⚠️ v2.61.3: Validación básica
        if (!payload.codigo || !payload.nombre) {
            mostrarError('Los campos Código y Nombre son requeridos.');
            return null;
        }

        // ⚠️ v2.61.3: Log para debugging (solo en desarrollo)
        if (console && console.log) {
            console.log(`${MOD} Datos recolectados:`, payload);
        }

        return payload;
    }

    /**
     * Recolectar datos del formulario de ajuste de inventario
     * @returns {Object|null} Datos del movimiento o null si hay error
     */
    function recolectarDatosAjuste() {
        const form = d.querySelector(FORM_AJUSTE_ID);
        if (!form) {
            console.error(`${MOD} Formulario ${FORM_AJUSTE_ID} no encontrado`);
            return null;
        }

        const formData = new FormData(form);
        const productoId = formData.get('producto_id');
        
        if (!productoId) {
            mostrarError('Debe seleccionar un producto');
            return null;
        }

        const payload = {
            producto_id: parseInt(productoId),
            tipo_movimiento: formData.get('tipo_movimiento') || '',
            cantidad: parseFloat(formData.get('cantidad')) || 0,
            costo_unitario: parseFloat(formData.get('costo_unitario')) || 0,
            observaciones: formData.get('observaciones')?.trim() || ''
        };

        // Validación básica
        if (!payload.tipo_movimiento) {
            mostrarError('Debe seleccionar un tipo de movimiento');
            return null;
        }

        if (!payload.cantidad || payload.cantidad <= 0) {
            mostrarError('La cantidad debe ser mayor a cero');
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
     * Obtener ID de producto desde el formulario
     * @returns {string|null} ID del producto o null si es creación
     */
    function obtenerProductoId() {
        const form = d.querySelector(FORM_PRODUCTO_ID);
        if (!form) return null;
        
        const idInput = form.querySelector('#producto-id');
        if (!idInput) return null;
        
        const id = idInput.value?.trim();
        return id || null;
    }

    /**
     * Cargar categorías en el select
     * @param {number|null} categoriaSeleccionada - ID de categoría a seleccionar
     */
    async function cargarCategorias(categoriaSeleccionada = null) {
        if (!w.http || typeof w.http !== 'function') {
            console.warn(`${MOD} w.http no disponible para cargar categorías`);
            return;
        }

        try {
            // ⚠️ v2.61.3: Usar Core API Facade para cargar categorías
            const res = await w.http('GET', '/api/v1/core/v1/inventario/categorias/');
            
            if (!res.ok || !res.data) {
                console.warn(`${MOD} Error al cargar categorías`);
                return;
            }

            const categorias = Array.isArray(res.data) ? res.data : (res.data.results || []);
            const select = d.querySelector('#producto-categoria');
            if (!select) return;

            // Limpiar opciones
            select.innerHTML = '<option value="">Seleccione...</option>';

            // Agregar categorías (solo PRODUCTO o TODO)
            categorias.forEach(cat => {
                if (cat.aplicacion === 'PRODUCTO' || cat.aplicacion === 'TODO') {
                    const option = d.createElement('option');
                    option.value = cat.id;
                    option.textContent = cat.nombre;
                    if (categoriaSeleccionada && cat.id === categoriaSeleccionada) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                }
            });
        } catch (error) {
            console.error(`${MOD} Error al cargar categorías:`, error);
        }
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
     * Guardar producto (crear o actualizar)
     * ⚠️ v2.61.3: CRUD - CREATE/UPDATE
     * ⚠️ Protección contra doble envío
     * @param {Event} e - Evento del formulario (opcional)
     */
    async function guardarProducto(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // ⚠️ v2.61.3: Prevenir doble envío
        if (_guardandoProducto) {
            console.warn(`${MOD} Guardado ya en proceso, ignorando solicitud duplicada`);
            return;
        }

        ocultarError();

        // ⚠️ v2.61.3: Activar flag ANTES de cualquier otra operación para prevenir doble envío
        if (_guardandoProducto) {
            console.warn(`${MOD} Guardado ya en proceso (verificación adicional), ignorando solicitud duplicada`);
            return;
        }
        _guardandoProducto = true;

        const payload = recolectarDatosProducto();
        if (!payload) {
            // ⚠️ Si no hay payload válido, resetear flag
            _guardandoProducto = false;
            return;
        }
        const btnGuardar = d.querySelector('#btn-guardar-producto');
        const btnOriginalHTML = btnGuardar ? btnGuardar.innerHTML : '';
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.style.pointerEvents = 'none'; // Prevenir clics adicionales
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }
        
        // ⚠️ v2.61.3: Deshabilitar también el formulario para prevenir submit adicional
        const form = d.querySelector(FORM_PRODUCTO_ID);
        if (form) {
            form.style.pointerEvents = 'none';
        }

        const productoId = obtenerProductoId();
        let res;

        // ⚠️ v2.61.3: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.http || typeof w.http !== 'function') {
            console.error(`${MOD} w.http no está disponible`);
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError({ status: 500, data: { detail: 'API no disponible' } }, MOD, {
                    errorContainerSelector: FEEDBACK_ID
                });
            }
            return;
        }

        try {
            // ⚠️ v2.61.3: Log detallado del payload antes de enviar
            console.log(`${MOD} Payload a enviar:`, JSON.stringify(payload, null, 2));
            console.log(`${MOD} Tipos de datos:`, {
                codigo: typeof payload.codigo,
                nombre: typeof payload.nombre,
                categoria: typeof payload.categoria,
                unidad: typeof payload.unidad,
                descripcion: typeof payload.descripcion,
                precio_venta: typeof payload.precio_venta,
                stock_minimo: typeof payload.stock_minimo,
                activo: typeof payload.activo
            });

            if (productoId) {
                // ⚠️ UPDATE: Actualizar producto existente
                console.log(`${MOD} Actualizando producto ID: ${productoId}`);
                res = await w.http('PATCH', `${CORE_API_BASE}/${productoId}/`, payload);
            } else {
                // ⚠️ CREATE: Crear nuevo producto
                console.log(`${MOD} Creando nuevo producto`);
                res = await w.http('POST', `${CORE_API_BASE}/`, payload);
            }

            // ⚠️ v2.61.3: Aislamiento Gradual - Solo verificar ok
            if (!res.ok) {
                // Restaurar botón en caso de error
                _guardandoProducto = false;
                if (btnGuardar) {
                    btnGuardar.disabled = false;
                    btnGuardar.style.pointerEvents = 'auto';
                    btnGuardar.innerHTML = btnOriginalHTML;
                }
                if (form) {
                    form.style.pointerEvents = 'auto';
                }
                
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(res, MOD, {
                        modalSelector: OFFCANVAS_ID,
                        errorContainerSelector: FEEDBACK_ID
                    });
                } else {
                    mostrarError(res.data?.detail || res.data?.message || 'Error al guardar el producto');
                }
                return;
            }

            // ⚠️ v2.61.3: Resetear flag después de éxito
            _guardandoProducto = false;
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.style.pointerEvents = 'auto';
                btnGuardar.innerHTML = btnOriginalHTML;
            }
            if (form) {
                form.style.pointerEvents = 'auto';
            }

            // Éxito
            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                const accion = productoId ? 'actualizado' : 'creado';
                w.SintelFeedback.success(`Producto ${accion} correctamente`);
            }

            // Cerrar offcanvas
            cerrarOffcanvas();

            // ⚠️ v2.61.3: Recargar tabla de productos inmediatamente después de crear/actualizar
            // Usar múltiples métodos para asegurar que la recarga funcione
            setTimeout(function() {
                if (w.ProductosList && typeof w.ProductosList.recargar === 'function') {
                    console.log(`${MOD} Recargando tabla vía ProductosList.recargar()...`);
                    w.ProductosList.recargar();
                } else if (window.SintelInventarioTables && window.SintelInventarioTables.main && typeof window.SintelInventarioTables.main.replaceData === 'function') {
                    console.log(`${MOD} Recargando tabla vía SintelInventarioTables.main.replaceData()...`);
                    window.SintelInventarioTables.main.replaceData();
                } else {
                    console.warn(`${MOD} No se pudo recargar la tabla: módulos no disponibles`);
                    // Disparar evento personalizado como fallback
                    d.dispatchEvent(new CustomEvent('inventarioActualizado'));
                }
            }, 300); // Pequeño delay para asegurar que el backend haya procesado la creación

        } catch (error) {
            console.error(`${MOD} Error al guardar producto:`, error);
            // ⚠️ v2.61.3: Restaurar estado en caso de excepción
            _guardandoProducto = false;
            const btnGuardarError = d.querySelector('#btn-guardar-producto');
            const formError = d.querySelector(FORM_PRODUCTO_ID);
            if (btnGuardarError) {
                btnGuardarError.disabled = false;
                btnGuardarError.style.pointerEvents = 'auto';
                const btnOriginalHTMLError = btnGuardarError.getAttribute('data-original-html');
                if (btnOriginalHTMLError) {
                    btnGuardarError.innerHTML = btnOriginalHTMLError;
                }
            }
            if (formError) {
                formError.style.pointerEvents = 'auto';
            }
            mostrarError('Error inesperado al guardar el producto');
        }
    }

    /**
     * Procesar ajuste de inventario (movimiento)
     * ⚠️ v2.61.3: CRUD - CREATE (movimiento)
     */
    async function procesarAjuste(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ocultarError();

        const payload = recolectarDatosAjuste();
        if (!payload) {
            return;
        }

        // ⚠️ Validación adicional: Verificar stock para salidas
        const esSalida = payload.tipo_movimiento && payload.tipo_movimiento.startsWith('SALIDA_');
        if (esSalida) {
            try {
                const productoRes = await w.http('GET', `${CORE_API_BASE}/${payload.producto_id}/`);
                if (productoRes.ok && productoRes.data) {
                    const stockActual = parseFloat(productoRes.data.stock_actual || 0);
                    if (payload.cantidad > stockActual) {
                        mostrarError(`Stock insuficiente. Disponible: ${stockActual.toFixed(3)}, Solicitado: ${payload.cantidad.toFixed(3)}`);
                        return;
                    }
                }
            } catch (error) {
                console.error(`${MOD} Error al verificar stock:`, error);
                mostrarError('No se pudo verificar el stock del producto');
                return;
            }
        }

        // ⚠️ v2.61.3: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.http || typeof w.http !== 'function') {
            console.error(`${MOD} w.http no está disponible`);
            return;
        }

        try {
            // ⚠️ Loading state
            const btnGuardar = d.querySelector('#btn-guardar-ajuste');
            const btnOriginalHTML = btnGuardar?.innerHTML || '';
            if (btnGuardar) {
                btnGuardar.disabled = true;
                btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Procesando...';
            }

            // Crear movimiento
            // ⚠️ v2.61.3: Usar Core API Facade para crear movimientos
            const res = await w.http('POST', '/api/v1/core/v1/inventario/movimientos/', payload);

            // Restaurar estado del botón
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = btnOriginalHTML;
            }

            // ⚠️ v2.61.3: Aislamiento Gradual - Solo verificar ok
            if (!res.ok) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(res, MOD, {
                        modalSelector: OFFCANVAS_ID,
                        errorContainerSelector: FEEDBACK_ID
                    });
                } else {
                    mostrarError(res.data?.detail || res.data?.message || 'Error al procesar el ajuste');
                }
                return;
            }

            // Éxito
            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                w.SintelFeedback.success('Movimiento de inventario registrado correctamente');
            }

            // Cerrar offcanvas
            cerrarOffcanvas();

            // ⚠️ v2.61.3: Recargar tabla de productos inmediatamente después de procesar ajuste
            setTimeout(function() {
                if (w.ProductosList && typeof w.ProductosList.recargar === 'function') {
                    console.log(`${MOD} Recargando tabla vía ProductosList.recargar() después de ajuste...`);
                    w.ProductosList.recargar();
                } else if (window.SintelInventarioTables && window.SintelInventarioTables.main && typeof window.SintelInventarioTables.main.replaceData === 'function') {
                    console.log(`${MOD} Recargando tabla vía SintelInventarioTables.main.replaceData() después de ajuste...`);
                    window.SintelInventarioTables.main.replaceData();
                } else {
                    console.warn(`${MOD} No se pudo recargar la tabla: módulos no disponibles`);
                    // Disparar evento personalizado como fallback
                    d.dispatchEvent(new CustomEvent('inventarioActualizado'));
                }
            }, 300);

        } catch (error) {
            console.error(`${MOD} Error al procesar ajuste:`, error);
            mostrarError('Error inesperado al procesar el ajuste');
        }
    }

    /**
     * Inicializar eventos del formulario de producto
     * ⚠️ v2.61.3: Prevenir listeners duplicados usando data-init flag
     */
    function initFormProductoEvents() {
        const form = d.querySelector(FORM_PRODUCTO_ID);
        if (!form) {
            console.warn(`${MOD} Formulario ${FORM_PRODUCTO_ID} no encontrado`);
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
            e.stopPropagation();
            guardarProducto(e);
        }, { once: false, passive: false });

        // Botón guardar (si existe) - Usar once: false pero con verificación del flag
        const btnGuardar = form.querySelector('#btn-guardar-producto');
        if (btnGuardar) {
            // ⚠️ v2.61.3: Remover listener previo si existe para evitar duplicados
            const newBtnGuardar = btnGuardar.cloneNode(true);
            btnGuardar.parentNode.replaceChild(newBtnGuardar, btnGuardar);
            
            newBtnGuardar.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                // ⚠️ Verificación adicional del flag antes de ejecutar
                if (_guardandoProducto) {
                    console.warn(`${MOD} Guardado en proceso, ignorando click duplicado`);
                    return;
                }
                guardarProducto(e);
            }, { once: false, passive: false });
        }

        // Limpiar errores al cambiar campos
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', ocultarError);
            input.addEventListener('change', ocultarError);
        });
    }

    /**
     * Inicializar eventos del formulario de ajuste
     */
    function initFormAjusteEvents() {
        const form = d.querySelector(FORM_AJUSTE_ID);
        if (!form) {
            console.warn(`${MOD} Formulario ${FORM_AJUSTE_ID} no encontrado`);
            return;
        }

        // ⚠️ Prevenir submit nativo del formulario
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            procesarAjuste(e);
        });

        // Botón guardar (si existe)
        const btnGuardar = form.querySelector('#btn-guardar-ajuste');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', function(e) {
                e.preventDefault();
                procesarAjuste(e);
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
     * ⚠️ v2.61.3: Se llama cuando se carga el offcanvas vía HTMX
     * ⚠️ Protección contra inicializaciones múltiples
     */
    function init() {
        // ⚠️ v2.61.3: Verificar si ya se inicializó el offcanvas
        const offcanvasEl = d.querySelector(OFFCANVAS_ID);
        if (!offcanvasEl) {
            // El offcanvas no está en el DOM, no inicializar
            return;
        }

        // ⚠️ v2.61.3: Prevenir inicializaciones múltiples usando data-init en el offcanvas
        if (offcanvasEl.getAttribute('data-init') === 'true') {
            console.log(`${MOD} Offcanvas ya inicializado, omitiendo.`);
            return;
        }
        offcanvasEl.setAttribute('data-init', 'true');
        
        console.log(`${MOD} Inicializando módulo de editor...`);
        
        // Determinar qué formulario está presente
        const formProducto = d.querySelector(FORM_PRODUCTO_ID);
        const formAjuste = d.querySelector(FORM_AJUSTE_ID);

        if (formProducto) {
            initFormProductoEvents();
            // Cargar categorías si el select existe
            const selectCategoria = formProducto.querySelector('#producto-categoria');
            if (selectCategoria) {
                const productoId = obtenerProductoId();
                const categoriaId = formProducto.querySelector('#producto-categoria')?.value;
                cargarCategorias(categoriaId ? parseInt(categoriaId) : null);
            }
        }

        if (formAjuste) {
            initFormAjusteEvents();
        }
    }

    // ⚠️ Exposición global del módulo
    if (!w.ProductosEditor) {
        w.ProductosEditor = {
            init: init,
            guardar: guardarProducto,
            procesarAjuste: procesarAjuste,
            recolectarDatos: recolectarDatosProducto,
            cargarCategorias: cargarCategorias,
            cerrar: cerrarOffcanvas
        };
    }

    // ⚠️ v2.61.3: HTMX: ÚNICA fuente de inicialización cuando se carga el offcanvas
    // ⚠️ Eliminado listener de Bootstrap para evitar duplicados
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', function(event) {
            if (event.detail.target.id === 'offcanvas-container-inventario') {
                // ⚠️ v2.61.3: Limpiar el flag para permitir la reinicialización del editor
                const offcanvasEl = d.querySelector(OFFCANVAS_ID);
                if (offcanvasEl) {
                    offcanvasEl.removeAttribute('data-init');
                }
                // Limpiar flag del formulario también
                const form = d.querySelector(FORM_PRODUCTO_ID);
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

})(window, document);
