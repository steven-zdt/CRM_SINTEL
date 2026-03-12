/**
 * Feature: Editor - Movimientos de Inventario (Kardex) v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de creación y manejo de Modal
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (CORE_API_BASE)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en lib/http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 * - w.inventarioAPI (definido en inventario.api.js) - API wrapper (opcional)
 * - w.MovimientosList (definido en movimientos_list.js) - Feature: Listado (para recargar tabla)
 * 
 * CRUD:
 * - CREATE: Registrar nuevo movimiento de inventario
 * ⚠️ NOTA: No hay UPDATE/DELETE por integridad del Kardex (movimientos históricos)
 */
(function(w, d) {
    'use strict';

    const MOD = '[movimientos.editor]';
    const CORE_API_BASE = '/api/v1/core/v1/inventario/movimientos'; // Core API Facade
    const FORM_ID = '#form-movimiento';
    const FEEDBACK_ID = '#feedback-movimiento';
    const MODAL_ID = '#modal-movimiento';

    /**
     * Recolectar datos del formulario de movimiento
     * @returns {Object|null} Datos del movimiento o null si hay error
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector(FORM_ID);
        if (!form) {
            console.error(`${MOD} Formulario ${FORM_ID} no encontrado`);
            return null;
        }

        const formData = new FormData(form);
        const payload = {
            producto: formData.get('producto') ? parseInt(formData.get('producto'), 10) : null,
            tipo: formData.get('tipo') || '',
            cantidad: parseFloat(formData.get('cantidad')) || 0,
            origen_referencia: formData.get('origen_referencia')?.trim() || '',
            observaciones: formData.get('observaciones')?.trim() || ''
        };

        // Validación básica
        if (!payload.producto || !payload.tipo || !payload.cantidad || payload.cantidad <= 0) {
            mostrarError('Los campos Producto, Tipo Movimiento y Cantidad son requeridos. La cantidad debe ser mayor a cero.');
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
     * Cargar productos en el select
     */
    async function cargarProductos() {
        if (!w.http || typeof w.http !== 'function') {
            console.warn(`${MOD} w.http no disponible para cargar productos`);
            return;
        }

        try {
            // ⚠️ v2.61.3: Usar Core API Facade para cargar productos
            const res = await w.http('GET', '/api/v1/core/v1/inventario/productos/');
            
            if (!res.ok || !res.data) {
                console.warn(`${MOD} Error al cargar productos`);
                return;
            }

            const productos = Array.isArray(res.data) ? res.data : (res.data.results || []);
            const select = d.querySelector('#movimiento-producto');
            if (!select) return;

            // Limpiar opciones
            select.innerHTML = '<option value="">Seleccione...</option>';

            // Agregar productos
            productos.forEach(prod => {
                const option = d.createElement('option');
                option.value = prod.id;
                option.textContent = `${prod.codigo} - ${prod.nombre}`;
                select.appendChild(option);
            });
        } catch (error) {
            console.error(`${MOD} Error al cargar productos:`, error);
        }
    }

    /**
     * Cerrar modal
     */
    function cerrarModal() {
        const modalEl = d.querySelector(MODAL_ID);
        if (modalEl && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            const instance = bootstrap.Modal.getInstance(modalEl);
            if (instance) {
                instance.hide();
            }
        }
    }

    /**
     * Abrir modal para crear movimiento
     */
    function abrirModalCrear() {
        // Verificar que Bootstrap esté disponible
        if (typeof bootstrap === 'undefined') {
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Bootstrap no está cargado' } }, MOD);
            }
            return;
        }
        
        // Buscar modal
        const modalEl = d.querySelector(MODAL_ID);
        if (!modalEl) {
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError({ status: 500, data: { detail: 'Error: Modal no encontrado. Verifique que modals_movimientos.html esté incluido.' } }, MOD);
            }
            return;
        }

        // Limpiar formulario
        const form = d.querySelector(FORM_ID);
        if (form) {
            form.reset();
        }

        // Ocultar contenedor de error
        ocultarError();

        // Cargar productos (async, no bloquea la apertura del modal)
        cargarProductos();

        // Abrir modal usando Bootstrap 5
        // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden
        if (w.bootstrap && w.bootstrap.Modal) {
            const modal = w.bootstrap.Modal.getOrCreateInstance(modalEl);
            modalEl.addEventListener('shown.bs.modal', function focusFirstInput() {
                const firstInput = modalEl.querySelector('input:not([type="hidden"]), select, textarea');
                if (firstInput) {
                    firstInput.focus();
                }
                modalEl.removeEventListener('shown.bs.modal', focusFirstInput);
            }, { once: true });
            modal.show();
        } else if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
            // Fallback: usar UIManager si Bootstrap no está disponible
            w.UIManager.handleModal(MODAL_ID, 'show');
        }
    }

    /**
     * Guardar movimiento (crear)
     * ⚠️ v2.61.3: CRUD - CREATE
     * @param {Event} e - Evento del formulario (opcional)
     */
    async function guardarMovimiento(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ocultarError();

        const payload = recolectarDatosFormulario();
        if (!payload) {
            return;
        }

        // ⚠️ v2.61.3: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        if (!w.http || typeof w.http !== 'function') {
            console.error(`${MOD} w.http no está disponible`);
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError({ status: 500, data: { detail: 'API no disponible' } }, MOD);
            }
            return;
        }

        // ⚠️ Loading state
        const btnGuardar = d.querySelector('#btn-guardar-movimiento');
        const btnOriginalHTML = btnGuardar?.innerHTML || '';
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Guardando...';
        }

        try {
            // ⚠️ CREATE: Crear nuevo movimiento
            console.log(`${MOD} Creando nuevo movimiento`);
            const res = await w.http('POST', `${CORE_API_BASE}/`, payload);

            // Restaurar estado del botón ANTES de procesar respuesta
            if (btnGuardar) {
                btnGuardar.disabled = false;
                btnGuardar.innerHTML = btnOriginalHTML;
            }

            // ⚠️ v2.61.3: Aislamiento Gradual - Solo verificar ok
            if (!res.ok) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(res, MOD, {
                        modalSelector: MODAL_ID,
                        errorContainerSelector: FEEDBACK_ID
                    });
                } else {
                    mostrarError(res.data?.detail || res.data?.message || 'Error al guardar el movimiento');
                }
                return;
            }

            // Éxito
            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                w.SintelFeedback.success('Movimiento registrado correctamente');
            }

            // Cerrar modal
            cerrarModal();

            // Recargar tabla de movimientos
            if (w.MovimientosList && typeof w.MovimientosList.recargar === 'function') {
                w.MovimientosList.recargar();
            } else if (window.SintelInventarioTables && window.SintelInventarioTables.movimientos) {
                window.SintelInventarioTables.movimientos.replaceData();
            }

        } catch (error) {
            console.error(`${MOD} Error al guardar movimiento:`, error);
            mostrarError('Error inesperado al guardar el movimiento');
            
            // Restaurar estado del botón en caso de error
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

        // ⚠️ Prevenir submit nativo del formulario
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            guardarMovimiento(e);
        });

        // Botón guardar (si existe)
        const btnGuardar = form.querySelector('#btn-guardar-movimiento');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', function(e) {
                e.preventDefault();
                guardarMovimiento(e);
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
     * ⚠️ Se llama cuando se carga el modal o cuando se muestra
     */
    function init() {
        console.log(`${MOD} Inicializando módulo de editor...`);
        initFormEvents();
    }

    // ⚠️ Exposición global del módulo
    if (!w.MovimientosEditor) {
        w.MovimientosEditor = {
            init: init,
            guardar: guardarMovimiento,
            abrirModalCrear: abrirModalCrear,
            recolectarDatos: recolectarDatosFormulario,
            cargarProductos: cargarProductos,
            cerrar: cerrarModal
        };
    }

    // ⚠️ Bootstrap: Reinicializar cuando se muestra el modal
    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        const modalEl = d.querySelector(MODAL_ID);
        if (modalEl) {
            modalEl.addEventListener('shown.bs.modal', function() {
                console.log(`${MOD} Modal mostrado, inicializando editor...`);
                init();
                // Cargar productos cuando se muestra el modal
                cargarProductos();
            });
        }
    }

    // ⚠️ Configurar botón "Nuevo Movimiento" si existe
    function configurarBotonNuevo() {
        const btnNuevo = d.querySelector('#btn-nuevo-movimiento');
        if (btnNuevo) {
            // Remover listeners anteriores si existen (evitar duplicados)
            const nuevoBtn = btnNuevo.cloneNode(true);
            btnNuevo.parentNode.replaceChild(nuevoBtn, btnNuevo);
            
            nuevoBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                abrirModalCrear();
            });
            
            return true;
        }
        return false;
    }

    // ⚠️ v2.61.3: Configurar botón "Nuevo Movimiento" si existe
    // El botón puede no existir si el módulo se carga en un contexto diferente
    function inicializarBotonNuevo() {
        if (!configurarBotonNuevo()) {
            // Si no está disponible, intentar después de un delay
            setTimeout(() => {
                configurarBotonNuevo(); // Silencioso: no mostrar warning si no existe
            }, 500);
        }
    }

    // Intentar configurar el botón inmediatamente
    inicializarBotonNuevo();

    // ⚠️ HTMX: Reinicializar cuando se carga el contenido vía HTMX
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', function(event) {
            if (event.detail.target.id === 'pane-movimientos' || 
                event.detail.target.id === 'tab-movimientos-content' ||
                event.detail.target.id === 'grid-movimientos') {
                setTimeout(() => {
                    inicializarBotonNuevo();
                }, 100);
            }
        });
    }

})(window, document);
