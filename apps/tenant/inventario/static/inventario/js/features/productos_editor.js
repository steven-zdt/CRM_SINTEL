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
 * - w.Sintel.Inventario.API (definido en inventario.api.js) - API wrapper
 * - w.Sintel.Inventario.Productos.List (definido en productos_list.js) - Feature: Listado
 * 
 * CRUD:
 * - CREATE: Crear nuevo producto
 * - UPDATE: Actualizar producto existente
 */
(function(w, d) {
    'use strict';

    const MOD = '[productos.editor]';
    const CORE_API_BASE = '/api/v1/inventario/productos'; // Core API Facade
    const FORM_PRODUCTO_ID = '#form-producto';
    const FORM_AJUSTE_ID = '#form-ajuste-inventario';
    const FEEDBACK_ID = '#form-inventario-feedback';
    const OFFCANVAS_ID = '#offcanvas-inventario';

    w.Sintel = w.Sintel || {};
    w.Sintel.Inventario = w.Sintel.Inventario || {};
    w.Sintel.Inventario.Productos = w.Sintel.Inventario.Productos || {};
    
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
            categoria: formData.get('categoria') || null,
            unidad: formData.get('unidad')?.trim() || 'UND',
            descripcion: formData.get('descripcion')?.trim() || null,
            // v2.61.3: precio_venta y stock_minimo deben ser numeros (0 si esta vacio)
            precio_venta: parseDecimal(precioVentaValue, 0),
            stock_minimo: parseDecimal(stockMinimoValue, 0),
            activo: d.querySelector('#producto-activo')?.checked !== false,
        };

        // ⚠️ v2.61.3: Validación básica
        if (!payload.codigo || !payload.nombre) {
            mostrarError('Los campos Código y Nombre son requeridos.');
            return null;
        }
        if (payload.codigo.length > 64) {
            mostrarError('El Código no puede superar 64 caracteres.');
            return null;
        }

        // ⚠️ v2.61.3: Log para debugging (solo en desarrollo)
        if (console && console.log) {
            console.log(`${MOD} Datos recolectados:`, payload);
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
     * Cargar categorias en el select via Utils centralizado (cache 5min)
     * @param {number|null} categoriaSeleccionada - ID de categoria a seleccionar
     */
    async function cargarCategorias(categoriaSeleccionada = null) {
        await w.Sintel.Inventario.Utils.loadCategoriasSelect(
            '#producto-categoria', 'PRODUCTO', categoriaSeleccionada, 'Seleccione...'
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
                if (w.Sintel?.Inventario?.Productos?.List && typeof w.Sintel.Inventario.Productos.List.recargar === 'function') {
                    console.log(`${MOD} Recargando tabla vía Sintel.Inventario.Productos.List.recargar()...`);
                    w.Sintel.Inventario.Productos.List.recargar();
                } else if (w.Sintel?.Inventario?.Tables?.productos && typeof w.Sintel.Inventario.Tables.productos.replaceData === 'function') {
                    console.log(`${MOD} Recargando tabla vía Sintel.Inventario.Tables.productos.replaceData()...`);
                    w.Sintel.Inventario.Tables.productos.replaceData();
                } else if (w.ProductosList && typeof w.ProductosList.recargar === 'function') {
                    w.ProductosList.recargar();
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
                cargarCategorias(categoriaId || null);
            }


        }

        if (formAjuste) {
            // Delegar a inventario_editor.js
            console.log(`${MOD} Formulario de ajuste detectado, delegando a inventario_editor.js`);
        }
    }



    // ⚠️ Exposición global del módulo v3.5
    w.Sintel.Inventario.Productos.Editor = {
        init: init,
        guardar: guardarProducto,
        recolectarDatos: recolectarDatosProducto,
        cargarCategorias: cargarCategorias,
        cerrar: cerrarOffcanvas
    };

    // Deprecated fallbacks
    w.ProductosEditor = w.Sintel.Inventario.Productos.Editor;

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
