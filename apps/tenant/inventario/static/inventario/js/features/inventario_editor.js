/**
 * Feature: Editor - Inventario v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - Sintel.Core.Http (F32.7, core-http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 * - w.inventarioAPI (definido en inventario.api.js) - API wrapper (opcional)
 */
(function(w, d) {
    'use strict';

    const MOD = '[inventario.editor]';

    /**
     * Recolectar datos del formulario de ajuste de inventario
     * ⚠️ v2.61.3: Mapeo correcto de campos para el backend
     * Backend espera: producto (FK), tipo (string)
     * Frontend envía: producto_id -> producto, tipo_movimiento -> tipo
     * @returns {Object} Datos del movimiento
     */
    /**
     * Recolectar datos del formulario de ajuste de inventario
     * ⚠️ v2.61.3: Sincronizado con offcanvas_producto.html y backend
     * @returns {Object} Datos del movimiento
     */
    function recolectarDatosAjuste() {
        const form = d.querySelector('#form-ajuste-inventario');
        if (!form) {
            console.error(`${MOD} Formulario #form-ajuste-inventario no encontrado`);
            return null;
        }

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Remover campos vacíos
        Object.keys(data).forEach(key => {
            if (data[key] === '' || data[key] === null) {
                delete data[key];
            }
        });

        // ⚠️ v2.61.3: Conversión de tipos
        // [FE-C1] NO convertir "producto" con parseInt(): es un UUID (backend usa
        // lookup_field="uuid"), no un entero. parseInt("9abc...", 10) trunca a 9 y
        // corrompe la referencia -> el backend responde DoesNotExist en cada ajuste.
        if (data.cantidad) {
            data.cantidad = parseFloat(data.cantidad);
        }
        if (data.costo_unitario) {
            data.costo_unitario = parseFloat(data.costo_unitario);
        }

        return data;
    }


    /**
     * Validar movimiento antes de enviar (validación frontend)
     * @param {Object} data - Datos del movimiento
     * @param {Object} producto - Datos del producto (si está disponible)
     * @returns {Object} {valid: boolean, error: string|null}
     */
    async function validarMovimiento(data, producto) {
        // ⚠️ v2.61.3: Validar usando campos mapeados (producto, tipo)
        // Validar que se haya seleccionado un producto
        if (!data.producto) {
            return {
                valid: false,
                error: 'Debe seleccionar un producto'
            };
        }

        // Validar que se haya seleccionado un tipo de movimiento
        if (!data.tipo) {
            return {
                valid: false,
                error: 'Debe seleccionar un tipo de movimiento'
            };
        }

        // Validar que la cantidad sea positiva
        if (!data.cantidad || data.cantidad <= 0) {
            return {
                valid: false,
                error: 'La cantidad debe ser mayor a cero'
            };
        }

        // ⚠️ Validación crítica: No permitir salidas mayores al stock existente
        // ⚠️ v2.61.3: Usar campo mapeado 'tipo' en lugar de 'tipo_movimiento'
        const esSalida = data.tipo && data.tipo.startsWith('SALIDA_');
        
        if (esSalida) {
            // Si tenemos datos del producto en el DOM, validar stock
            let stockActual = null;
            
            if (producto && producto.stock_actual !== undefined) {
                stockActual = parseFloat(producto.stock_actual);
            } else {
                // Si no tenemos el producto en el DOM, obtenerlo de la API
                // ⚠️ v2.61.3: Usar Core API Facade para obtener producto
                // ⚠️ v2.61.3: Usar campo mapeado 'producto' en lugar de 'producto_id'
                const res = await w.Sintel.Core.Http.request('GET', `/api/v1/inventario/productos/${data.producto}/`);
                if (res.ok && res.data) {
                    stockActual = parseFloat(res.data.stock_actual || 0);
                } else {
                    return {
                        valid: false,
                        error: 'No se pudo verificar el stock del producto'
                    };
                }
            }

            if (stockActual !== null && data.cantidad > stockActual) {
                return {
                    valid: false,
                    error: `Stock insuficiente. Disponible: ${stockActual.toFixed(3)}, Solicitado: ${data.cantidad.toFixed(3)}`
                };
            }
        }

        return { valid: true, error: null };
    }

    /**
     * Procesar movimiento de inventario
     * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
     * ⚠️ v2.60: Validación frontend antes de enviar a API
     */
    async function procesarMovimiento() {
        const data = recolectarDatosAjuste();
        if (!data) {
            return;
        }

        // Obtener datos del producto si están disponibles en el DOM
        const productoIdEl = d.querySelector('#ajuste-producto-id');
        let producto = null;
        if (productoIdEl && productoIdEl.value) {
            // Intentar obtener stock actual del card informativo si existe
            const cardStock = d.querySelector('.card-body p:last-child .badge');
            if (cardStock) {
                const stockText = cardStock.textContent.trim();
                const stockMatch = stockText.match(/([\d.,]+)/);
                if (stockMatch) {
                    producto = {
                        stock_actual: parseFloat(stockMatch[1].replace(',', '.'))
                    };
                }
            }
        }

        // ⚠️ Validación frontend antes de enviar
        const validacion = await validarMovimiento(data, producto);
        if (!validacion.valid) {
            // Mostrar error en el Error Boundary
            const errorContainer = d.querySelector('#form-inventario-feedback');
            if (errorContainer) {
                errorContainer.classList.remove('d-none');
                errorContainer.innerHTML = `
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>Error de validación:</strong> ${validacion.error}
                `;
            }
            return;
        }

        const offcanvasEl = d.querySelector('#offcanvas-inventario');
        
        // ⚠️ Error Boundary v2.60: Guardar estado original del botón
        const btnGuardar = d.querySelector('#btn-guardar-ajuste');
        const btnOriginalText = btnGuardar?.innerHTML || '';
        const btnOriginalDisabled = btnGuardar?.disabled || false;
        
        // ⚠️ Error Boundary v2.60: Mostrar estado de loading
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Procesando...';
        }

        // Limpiar errores previos
        const errorContainer = d.querySelector('#form-inventario-feedback');
        if (errorContainer) {
            errorContainer.classList.add('d-none');
            errorContainer.innerHTML = '';
        }

        // Determinar endpoint según tipo de movimiento
        // ⚠️ v2.61.3: Usar Core API Facade para crear movimientos
        let endpoint = '/api/v1/inventario/movimientos/';
        let method = 'POST';

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        const res = await w.Sintel.Core.Http.request(method, endpoint, data);

        // ⚠️ Error Boundary v2.60: Restaurar estado del botón
        if (btnGuardar) {
            btnGuardar.disabled = btnOriginalDisabled;
            btnGuardar.innerHTML = btnOriginalText;
        }

        // ⚠️ v2.60: Aislamiento Gradual - Manejo de errores con UIManager
        if (!res.ok) {
            // ⚠️ Error Boundary: Inyectar errores en el contenedor de feedback
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError(res, MOD, {
                    errorContainerSelector: '#form-inventario-feedback'
                });
            } else {
                // Fallback: Mostrar error básico
                if (errorContainer) {
                    errorContainer.classList.remove('d-none');
                    errorContainer.innerHTML = `
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        <strong>Error:</strong> ${res.data?.detail || 'Error al procesar el movimiento'}
                    `;
                }
            }
            return;
        }

        // ⚠️ Éxito: Cerrar Offcanvas, mostrar feedback y disparar evento
        if (offcanvasEl) {
            const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
            if (offcanvas) {
                offcanvas.hide();
            }
        }

        // Mostrar feedback de éxito
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
            w.SintelFeedback.success('Movimiento registrado correctamente');
        }

        // Refrescar la grilla real de Productos (Fase 5-BIS, django-tables2+HTMX):
        // #productos-panel escucha `producto-updated from:body` (list_productos.html).
        // El evento `inventario-updated` en `document` no tiene ningun listener real.
        d.body.dispatchEvent(new CustomEvent('producto-updated'));
    }


    /**
     * Cargar productos disponibles en el select de ajuste
     * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
     */
    async function cargarProductosEnAjuste() {
        const select = d.querySelector('#ajuste-producto-select');
        if (!select) {
            // Si no hay select, significa que el producto ya viene pre-seleccionado
            return;
        }

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.inventarioAPI || !w.inventarioAPI.productos || typeof w.inventarioAPI.productos.list !== 'function') {
            console.warn(`${MOD} inventarioAPI.productos.list no está disponible`);
            return;
        }

        const res = await w.inventarioAPI.productos.list({ page_size: 1000 }); // Cargar todos los productos activos
        
        // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
        if (!res.ok || !res.data) {
            // ⚠️ v2.60: Delegar a UIManager para mostrar error (pero no bloquear)
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError(res, MOD);
            }
            return;
        }

        const productos = Array.isArray(res.data) ? res.data : (res.data.results || []);
        
        // Limpiar opciones existentes (excepto la primera opción vacía)
        select.innerHTML = '<option value="">Seleccionar producto...</option>';

        // Agregar productos activos
        const productosActivos = productos.filter(prod => prod.activo !== false);
        productosActivos.forEach(prod => {
            const option = d.createElement('option');
            option.value = prod.id;
            option.setAttribute('data-unidad', prod.unidad || 'UND');
            option.setAttribute('data-stock', prod.stock_actual || 0);
            option.textContent = `${prod.codigo} - ${prod.nombre}${prod.stock_actual !== undefined ? ` (Stock: ${prod.stock_actual} ${prod.unidad || 'UND'})` : ''}`;
            select.appendChild(option);
        });

        // Si solo hay un producto, seleccionarlo automáticamente
        if (productosActivos.length === 1) {
            select.value = productosActivos[0].id;
            // Actualizar unidad automáticamente
            actualizarUnidadProducto(productosActivos[0].unidad || 'UND');
        }

        // Event listener para actualizar unidad cuando se selecciona un producto
        select.addEventListener('change', function() {
            const selectedOption = select.options[select.selectedIndex];
            if (selectedOption && selectedOption.value) {
                const unidad = selectedOption.getAttribute('data-unidad') || 'UND';
                const stock = selectedOption.getAttribute('data-stock') || '0';
                actualizarUnidadProducto(unidad);
                
                // Mostrar stock actual como ayuda
                const cantidadInput = d.querySelector('#ajuste-cantidad');
                if (cantidadInput) {
                    cantidadInput.setAttribute('placeholder', `Stock actual: ${stock} ${unidad}`);
                }
            }
        });
    }

    /**
     * Actualizar la unidad del producto en el campo de cantidad
     */
    function actualizarUnidadProducto(unidad) {
        const unidadSpan = d.querySelector('#ajuste-cantidad').nextElementSibling;
        if (unidadSpan && unidadSpan.classList.contains('input-group-text')) {
            unidadSpan.textContent = unidad;
        }
    }

    /**
     * Inicializar eventos del editor
     */
    function initEditorEvents() {
        // Guard (FE-A1/A2): DOMContentLoaded/init() y htmx:afterSwap pueden
        // ambos disparar initEditorEvents() para el mismo offcanvas — sin
        // esto, el submit del formulario de ajuste queda duplicado.
        const offcanvasElGuard = d.querySelector('#offcanvas-inventario');
        if (offcanvasElGuard) {
            if (offcanvasElGuard.dataset.editorInitialized) return;
            offcanvasElGuard.dataset.editorInitialized = 'true';
        }

        // Botón guardar ajuste
        const btnGuardarAjuste = d.querySelector('#btn-guardar-ajuste');
        if (btnGuardarAjuste) {
            btnGuardarAjuste.addEventListener('click', procesarMovimiento);
        }


        // Formulario de ajuste (submit)
        const formAjuste = d.querySelector('#form-ajuste-inventario');
        if (formAjuste) {
            formAjuste.addEventListener('submit', function(e) {
                e.preventDefault();
                procesarMovimiento();
            });
        }


        // Limpiar errores cuando se cierra el Offcanvas
        const offcanvasEl = d.querySelector('#offcanvas-inventario');
        if (offcanvasEl) {
            offcanvasEl.addEventListener('hidden.bs.offcanvas', function() {
                const errorContainer = d.querySelector('#form-inventario-feedback');
                if (errorContainer) {
                    errorContainer.classList.add('d-none');
                    errorContainer.innerHTML = '';
                }
            });

            // ⚠️ v2.60: Cargar productos cuando se muestra el offcanvas de ajuste
            offcanvasEl.addEventListener('shown.bs.offcanvas', function() {
                // Verificar si es formulario de ajuste (tiene el select de productos)
                const selectProducto = d.querySelector('#ajuste-producto-select');
                if (selectProducto) {
                    // Cargar productos disponibles
                    cargarProductosEnAjuste();
                }
            });
        }
    }

    /**
     * Inicialización cuando el DOM está listo
     */
    function init() {
        // Verificar que el offcanvas exista
        const offcanvasEl = d.querySelector('#offcanvas-inventario');
        if (!offcanvasEl) {
            // Reintentar después de un delay (útil para HTMX swaps)
            setTimeout(init, 500);
            return;
        }

        initEditorEvents();
    }

    // Inicializar cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ⚠️ HTMX: Reinicializar cuando se carga el Offcanvas vía HTMX
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', function(event) {
            if (event.detail.target.id === 'offcanvas-container-inventario') {
                setTimeout(function() {
                    init();
                    // Cargar productos si es formulario de ajuste
                    const selectProducto = d.querySelector('#ajuste-producto-select');
                    if (selectProducto) {
                        cargarProductosEnAjuste();
                    }
                }, 100);
            }
        });
    }

})(window, document);
