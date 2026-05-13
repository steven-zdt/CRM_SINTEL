/**
 * Feature: Editor - Facturas v2.60
 * ⚠️ Feature-Sliced Architecture: Lógica de creación/edición y manejo de Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - w.http (definido en lib/http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 */
(function(w, d) {
    'use strict';

    const MOD = '[facturas.editor]';

    /**
     * Recolectar ítems de la tabla de factura
     * @returns {Array} Array de objetos con datos de ítems
     */
    function recolectarItems() {
        const tbody = d.querySelector('#tbody-items-factura');
        // ⚠️ Validación temprana: Si no hay tabla, es la vista de "Subir" o "Lectura"
        if (!tbody) {
            return []; // Retorna array vacío silenciosamente
        }

        const rows = tbody.querySelectorAll('tr[data-item-id]');
        const items = [];

        rows.forEach((row, index) => {
            const codigo = row.querySelector('td:nth-child(2)')?.textContent?.trim() || '';
            const descripcion = row.querySelector('td:nth-child(3)')?.textContent?.trim() || '';
            const cantidad = parseFloat(row.querySelector('td:nth-child(4)')?.textContent?.replace(/[^\d.,]/g, '').replace(',', '.')) || 0;
            const unidad = row.querySelector('td:nth-child(5)')?.textContent?.trim() || 'UND';
            const valorUnitario = parseFloat(row.querySelector('td:nth-child(6)')?.textContent?.replace(/[^\d.,]/g, '').replace(',', '.')) || 0;
            const porcentajeIva = parseFloat(row.querySelector('td:nth-child(7)')?.textContent?.replace(/[^\d.,]/g, '').replace(',', '.')) || 0;
            const itemId = row.getAttribute('data-item-id');

            if (descripcion && cantidad > 0 && valorUnitario > 0) {
                items.push({
                    id: itemId || null,
                    codigo: codigo,
                    descripcion: descripcion,
                    cantidad: cantidad,
                    unidad_medida: unidad,
                    valor_unitario: valorUnitario,
                    porcentaje_iva: porcentajeIva,
                    orden: index + 1
                });
            }
        });

        return items;
    }

    /**
     * Calcular totales desde los ítems
     * @returns {Object} Objeto con subtotal, impuestos y total
     */
    function calcularTotales() {
        const items = recolectarItems();
        let subtotal = 0;
        let impuestos = 0;

        items.forEach(item => {
            const subtotalItem = item.cantidad * item.valor_unitario;
            const ivaItem = subtotalItem * (item.porcentaje_iva / 100);
            subtotal += subtotalItem;
            impuestos += ivaItem;
        });

        const total = subtotal + impuestos;

        return {
            subtotal: parseFloat(subtotal.toFixed(2)),
            impuestos: parseFloat(impuestos.toFixed(2)),
            total: parseFloat(total.toFixed(2))
        };
    }

    /**
     * Actualizar totales en el DOM
     * ⚠️ Validación temprana: Solo actualiza si los elementos existen
     */
    function actualizarTotalesEnDOM() {
        // ⚠️ Validación temprana: Verificar si existe el formulario de edición
        const form = d.querySelector('#form-factura');
        if (!form) {
            // Modo "Subir" o "Lectura" - no hay totales que actualizar
            return;
        }
        
        const totales = calcularTotales();
        
        const subtotalEl = d.querySelector('#factura-subtotal');
        const impuestosEl = d.querySelector('#factura-impuestos');
        const totalEl = d.querySelector('#factura-total');

        if (subtotalEl) {
            subtotalEl.textContent = formatearMoneda(totales.subtotal);
        }
        if (impuestosEl) {
            impuestosEl.textContent = formatearMoneda(totales.impuestos);
        }
        if (totalEl) {
            totalEl.textContent = formatearMoneda(totales.total);
        }
    }

    /**
     * Formatear moneda
     */
    function formatearMoneda(value) {
        if (value === null || value === undefined || value === '') return '$ 0,00';
        const num = parseFloat(value);
        if (isNaN(num)) return '$ 0,00';
        return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: 'COP',
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }).format(num);
    }

    /**
     * Recolectar datos del formulario del Offcanvas
     * @returns {Object} Datos de la factura con ítems y totales
     */
    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-factura');
        // ⚠️ Validación temprana: Si no hay formulario, es la vista de "Subir" o "Lectura"
        if (!form) {
            return null; // Retorna null silenciosamente (sin log de error)
        }

        // ⚠️ DOM Shield: Remover names de selects temporalmente para evitar que se recolecte el texto visible de plugins JS
        // Se asume que los valores reales están en inputs hidden con el nombre correcto
        const selectsHtml = form.querySelectorAll('select');
        const selectNames = new Map();
        selectsHtml.forEach(select => {
            if (select.hasAttribute('name')) {
                selectNames.set(select, select.getAttribute('name'));
                select.removeAttribute('name');
            }
        });

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // ⚠️ DOM Shield: Restaurar names originales
        selectNames.forEach((name, select) => {
            select.setAttribute('name', name);
        });

        // Remover campos vacíos
        Object.keys(data).forEach(key => {
            if (data[key] === '' || data[key] === null) {
                delete data[key];
            }
        });

        // ⚠️ Recolectar ítems
        const items = recolectarItems();
        data.items = items;

        // ⚠️ Calcular y agregar totales
        const totales = calcularTotales();
        data.subtotal = totales.subtotal;
        data.impuestos = totales.impuestos;
        data.total = totales.total;

        // ⚠️ Conversión de tipos numéricos
        if (data.consecutivo) {
            data.consecutivo = parseInt(data.consecutivo);
        }
        if (data.subtotal) {
            data.subtotal = parseFloat(data.subtotal);
        }
        if (data.impuestos) {
            data.impuestos = parseFloat(data.impuestos);
        }
        if (data.total) {
            data.total = parseFloat(data.total);
        }

        // [v3.7.0] Cuenta Contable
        const cuentaUuid = d.querySelector('#factura-cuenta_contable_uuid')?.value;
        if (cuentaUuid) {
            data.cuenta_contable_uuid = cuentaUuid;
        }

        return data;
    }

    /**
     * Emitir factura
     * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
     * ⚠️ v2.60: Maneja Offcanvas y Error Boundary
     */
    async function emitirFactura() {
        const data = recolectarDatosFormulario();
        if (!data) {
            return;
        }

        // Validar que hay al menos un ítem
        if (!data.items || data.items.length === 0) {
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError({
                    data: { detail: 'Debe agregar al menos un ítem a la factura.' }
                }, MOD);
            } else {
                alert('Debe agregar al menos un ítem a la factura.');
            }
            return;
        }

        const id = d.querySelector('#factura-id')?.value;
        const offcanvasEl = d.querySelector('#offcanvas-factura');
        
        // ⚠️ Error Boundary v2.60: Guardar estado original del botón
        const btnGuardar = d.querySelector('#btn-guardar-factura');
        const btnOriginalText = btnGuardar?.innerHTML || '';
        const btnOriginalDisabled = btnGuardar?.disabled || false;
        
        // ⚠️ Error Boundary v2.60: Mostrar estado de loading
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...';
        }

        // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
        let res;
        if (id) {
            // Actualizar factura existente (solo si es borrador)
            res = await w.http('PATCH', `/api/v1/facturas/${id}/`, data);
        } else {
            // Crear nueva factura
            res = await w.http('POST', '/api/v1/facturas/', data);
        }

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
                    errorContainerSelector: '#form-factura-feedback'
                });
            } else {
                // Fallback: Mostrar error básico
                const errorContainer = d.querySelector('#form-factura-feedback');
                if (errorContainer) {
                    errorContainer.classList.remove('d-none');
                    errorContainer.textContent = res.data?.detail || 'Error al guardar la factura';
                }
            }
            return;
        }

        // ⚠️ Éxito: Cerrar Offcanvas, mostrar feedback y disparar evento
        if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
            const offcanvasInstance = bootstrap.Offcanvas.getInstance(offcanvasEl);
            if (offcanvasInstance) {
                offcanvasInstance.hide();
            }
        }

        // ⚠️ Feedback visual
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
            w.SintelFeedback.success('Factura guardada correctamente');
        }

        // ⚠️ Evento personalizado para recarga reactiva del grid
        d.dispatchEvent(new Event('facturaGuardada'));

        console.log(`${MOD} Factura guardada correctamente`);
    }

    /**
     * Configurar listeners del formulario
     * ⚠️ Validación temprana: Solo inicializa si el formulario de edición existe
     */
    function initEditorEvents() {
        const form = d.querySelector('#form-factura');
        // ⚠️ Validación temprana: Si no hay formulario, es la vista de "Subir" o "Lectura"
        if (!form) {
            // Modo "Subir" o "Lectura" - Editor inactivo (comportamiento esperado)
            return; // Detiene la ejecución aquí, evitando errores en cascada
        }

        // Listener para el botón de guardar
        const btnGuardar = d.querySelector('#btn-guardar-factura');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', (e) => {
                e.preventDefault();
                emitirFactura();
            });
        }

        // Listener para el submit del formulario (prevenir submit tradicional)
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            emitirFactura();
        });

        // [v3.7.0] Buscador de Cuentas Contables
        initCuentaContableSearch();

        // [v3.7.0] Buscador de Cliente/Proveedor para extraer retenciones
        initClienteProveedorSearch();

        // ⚠️ Listener para botón agregar ítem
        const btnAgregarItem = d.querySelector('#btn-agregar-item');
        if (btnAgregarItem) {
            btnAgregarItem.addEventListener('click', () => {
                // TODO: Implementar lógica para agregar ítem dinámicamente
                console.log(`${MOD} Agregar ítem (pendiente implementación)`);
            });
        }

        // ⚠️ Event Delegation: Eliminar ítem
        const tbody = d.querySelector('#tbody-items-factura');
        if (tbody) {
            tbody.addEventListener('click', (e) => {
                const btnEliminar = e.target.closest('.btn-eliminar-item');
                if (btnEliminar) {
                    e.preventDefault();
                    const itemId = btnEliminar.getAttribute('data-item-id');
                    const row = btnEliminar.closest('tr');
                    
                    if (row && confirm('¿Está seguro de eliminar este ítem?')) {
                        row.remove();
                        actualizarTotalesEnDOM();
                        
                        // Si no quedan ítems, mostrar mensaje
                        const remainingRows = tbody.querySelectorAll('tr[data-item-id]');
                        if (remainingRows.length === 0) {
                            const rowSinItems = d.querySelector('#row-sin-items');
                            if (!rowSinItems) {
                                const newRow = d.createElement('tr');
                                newRow.id = 'row-sin-items';
                                newRow.innerHTML = '<td colspan="9" class="text-center text-muted py-4"><i class="bi bi-inbox"></i> No hay ítems agregados</td>';
                                tbody.appendChild(newRow);
                            }
                        }
                    }
                }
            });
        }

        // ⚠️ Limpieza: Limpiar formulario cuando se cierre el Offcanvas
        const offcanvasEl = d.querySelector('#offcanvas-factura');
        if (offcanvasEl) {
            offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
                // Limpiar contenedor de errores
                const errorContainer = d.querySelector('#form-factura-feedback');
                if (errorContainer) {
                    errorContainer.classList.add('d-none');
                    errorContainer.textContent = '';
                }
                
                // Limpiar formulario (opcional, depende de si queremos mantener datos)
                // form.reset();
            });
        }

        console.log(`${MOD} Event listeners del editor configurados`);
    }

    /**
     * [v3.7.0] Inicializar buscador asíncrono de cuentas contables
     */
    function initCuentaContableSearch() {
        const searchInput = d.querySelector('#factura-cuenta_contable_search');
        const uuidInput = d.querySelector('#factura-cuenta_contable_uuid');
        const suggestions = d.querySelector('#factura-cuenta-suggestions');

        if (!searchInput || !uuidInput || !suggestions) return;

        let debounceTimer;

        searchInput.addEventListener('input', () => {
            const query = searchInput.value.trim();
            clearTimeout(debounceTimer);

            if (query.length < 2) {
                suggestions.classList.add('d-none');
                return;
            }

            debounceTimer = setTimeout(async () => {
                // ⚠️ Aislamiento Gradual: Usar facturasAPI.searchCuentas
                const res = await w.facturasAPI.searchCuentas(query);
                if (res.ok && res.data) {
                    const results = Array.isArray(res.data) ? res.data : (res.data.results || []);
                    renderSuggestions(results);
                }
            }, 300);
        });

        function renderSuggestions(data) {
            suggestions.innerHTML = '';
            if (!data || !data.length) {
                suggestions.classList.add('d-none');
                return;
            }

            data.forEach(cuenta => {
                const item = d.createElement('button');
                item.type = 'button';
                item.className = 'list-group-item list-group-item-action small py-2';
                item.innerHTML = `<div><span class="fw-bold text-primary">${cuenta.codigo}</span> - ${cuenta.nombre}</div>`;
                
                item.addEventListener('click', () => {
                    searchInput.value = `${cuenta.codigo} - ${cuenta.nombre}`;
                    uuidInput.value = cuenta.uuid;
                    suggestions.classList.add('d-none');
                    // Feedback visual
                    searchInput.classList.add('is-valid');
                    setTimeout(() => searchInput.classList.remove('is-valid'), 2000);
                });
                suggestions.appendChild(item);
            });
            suggestions.classList.remove('d-none');
        }

        // Cerrar sugerencias al hacer click fuera
        d.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
                suggestions.classList.add('d-none');
            }
        });

        // Limpiar UUID si el campo de búsqueda se vacía
        searchInput.addEventListener('change', () => {
            if (!searchInput.value.trim()) {
                uuidInput.value = '';
            }
        });

        // [v3.7.0] Pre-poblar campo de texto si hay UUID inicial (modo edición)
        // §18: resolución via HTTP al endpoint de contabilidad, no via Python import
        const initialUuid = uuidInput.value.trim();
        if (initialUuid && !searchInput.value.trim()) {
            w.facturasAPI.getCuentaByUuid(initialUuid).then(response => {
                if (response && response.ok && response.data) {
                    const results = Array.isArray(response.data) ? response.data : (response.data.results || []);
                    if (results.length > 0) {
                        const cuenta = results[0];
                        searchInput.value = `${cuenta.codigo} - ${cuenta.nombre}`;
                    }
                }
            }).catch(err => {
                console.warn('[facturas.editor:cuenta_search] No se pudo pre-cargar cuenta:', err);
            });
        }
    }

    /**
     * [v3.7.0] Inicializar buscador de Cliente/Proveedor para extraer retenciones
     */
    function initClienteProveedorSearch() {
        const searchInput = d.querySelector('#factura-cliente-proveedor-search');
        const suggestions = d.querySelector('#factura-cliente-proveedor-suggestions');
        const btnLimpiar = d.querySelector('#btn-limpiar-cliente-proveedor');
        const naturalezaSelect = d.querySelector('#factura-naturaleza');

        if (!searchInput || !suggestions) return;

        let debounceTimer;

        // Actualizar etiqueta según naturaleza
        function actualizarEtiqueta() {
            const naturaleza = naturalezaSelect.value;
            const etiquetaEls = d.querySelectorAll('#label-cliente-proveedor, #label-cliente-proveedor-2');
            const tipo = naturaleza === 'VENTA' ? 'Cliente' : 'Proveedor';
            etiquetaEls.forEach(el => el.textContent = tipo.toLowerCase());
        }

        naturalezaSelect.addEventListener('change', actualizarEtiqueta);
        actualizarEtiqueta(); // Inicializar

        searchInput.addEventListener('input', () => {
            const query = searchInput.value.trim();
            clearTimeout(debounceTimer);

            if (query.length < 2) {
                suggestions.classList.add('d-none');
                return;
            }

            debounceTimer = setTimeout(async () => {
                const naturaleza = naturalezaSelect.value || 'VENTA';
                // TODO: Buscar cliente/proveedor por NIT o razón social
                // Por ahora, solo mostrar un placeholder
                renderSuggestionsClienteProveedor([]);
            }, 300);
        });

        function renderSuggestionsClienteProveedor(data) {
            suggestions.innerHTML = '';
            if (!data || !data.length) {
                suggestions.classList.add('d-none');
                return;
            }

            data.forEach(item => {
                const btnItem = d.createElement('button');
                btnItem.type = 'button';
                btnItem.className = 'list-group-item list-group-item-action small py-2';
                btnItem.innerHTML = `<div><span class="fw-bold text-primary">${item.nit}</span> - ${item.razon_social}</div>`;

                btnItem.addEventListener('click', async () => {
                    searchInput.value = `${item.nit} - ${item.razon_social}`;
                    suggestions.classList.add('d-none');

                    // Cargar retenciones
                    await cargarRetenciones(item.nit);

                    // Feedback visual
                    searchInput.classList.add('is-valid');
                    setTimeout(() => searchInput.classList.remove('is-valid'), 2000);
                });
                suggestions.appendChild(btnItem);
            });
            suggestions.classList.remove('d-none');
        }

        async function cargarRetenciones(nit) {
            const naturaleza = naturalezaSelect.value || 'VENTA';

            // Para COMPRA, las retenciones ya están en el XML — no consultar Proveedores
            if (naturaleza === 'COMPRA') {
                d.querySelector('#factura-retefuente-porcentaje').value = '0.00';
                d.querySelector('#factura-reteica-porcentaje').value = '0.00';
                d.querySelector('#factura-reteiva-porcentaje').value = '0.00';
                d.querySelector('#helper-retefuente').textContent = '';
                d.querySelector('#helper-reteica').textContent = '';
                d.querySelector('#helper-reteiva').textContent = '';
                return;
            }

            // VENTA: extraer desde Clientes
            try {
                const response = await fetch(
                    `/api/v1/facturas/obtener-retenciones/?nit=${encodeURIComponent(nit)}&naturaleza=${naturaleza}`,
                    { headers: { 'Content-Type': 'application/json' } }
                );

                if (!response.ok) {
                    console.warn('[facturas.editor:retenciones] Error obteniendo retenciones');
                    return;
                }

                const data = await response.json();

                // Cargar porcentajes en campos read-only
                d.querySelector('#factura-retefuente-porcentaje').value = data.retefuente_porcentaje || '0.00';
                d.querySelector('#factura-reteica-porcentaje').value = data.reteica_porcentaje || '0.00';
                d.querySelector('#factura-reteiva-porcentaje').value = data.reteiva_porcentaje || '0.00';

                // Mostrar helpers con fórmula de cálculo
                if (data.aplica_retefuente) {
                    d.querySelector('#helper-retefuente').textContent =
                        `= Subtotal × ${data.retefuente_porcentaje}%`;
                }
                if (data.aplica_reteica) {
                    d.querySelector('#helper-reteica').textContent =
                        `= Subtotal × ${data.reteica_porcentaje}%`;
                }
                if (data.aplica_reteiva) {
                    d.querySelector('#helper-reteiva').textContent =
                        `= Subtotal × ${data.reteiva_porcentaje}%`;
                }

            } catch (err) {
                console.warn('[facturas.editor:retenciones] Error:', err);
            }
        }

        // Botón limpiar
        if (btnLimpiar) {
            btnLimpiar.addEventListener('click', () => {
                searchInput.value = '';
                suggestions.classList.add('d-none');
                d.querySelector('#factura-retefuente-porcentaje').value = '';
                d.querySelector('#factura-reteica-porcentaje').value = '';
                d.querySelector('#factura-reteiva-porcentaje').value = '';
                d.querySelector('#helper-retefuente').textContent = '';
                d.querySelector('#helper-reteica').textContent = '';
                d.querySelector('#helper-reteiva').textContent = '';
            });
        }

        // Cerrar sugerencias al hacer click fuera
        d.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
                suggestions.classList.add('d-none');
            }
        });
    }

    // Inicialización principal
    function init() {
        console.log(`${MOD} Inicializando módulo de editor...`);
        
        // ⚠️ Lazy Loading: Solo inicializar cuando el Offcanvas esté presente
        const offcanvasEl = d.querySelector('#offcanvas-factura');
        if (offcanvasEl) {
            initEditorEvents();
            // Actualizar totales si hay ítems cargados
            actualizarTotalesEnDOM();
        } else {
            // Si no existe, escuchar cuando se cree (HTMX)
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1 && node.id === 'offcanvas-factura') {
                            initEditorEvents();
                            actualizarTotalesEnDOM();
                            observer.disconnect();
                        }
                    });
                });
            });

            const container = d.querySelector('#offcanvas-container-facturas');
            if (container) {
                observer.observe(container, { childList: true, subtree: true });
            }
        }
    }

    // Auto-inicializar cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ⚠️ HTMX: Reinicializar cuando se cargue el Offcanvas vía HTMX
    // ⚠️ Validación temprana: Solo inicializa si el formulario de edición existe
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSwap', (event) => {
            if (event.detail.target.id === 'offcanvas-container-facturas') {
                // Pequeño delay para asegurar que el DOM esté completamente renderizado
                setTimeout(() => {
                    // ⚠️ Validación temprana: Solo inicializar si existe el formulario de edición
                    const form = d.querySelector('#form-factura');
                    if (form) {
                        // Solo inicializar si estamos en modo edición (formulario existe)
                        initEditorEvents();
                        actualizarTotalesEnDOM();
                    }
                    // Modo "Subir" (form-upload-factura) o "Lectura": no requieren inicialización
                }, 50);
            }
        });
    }

    // ⚠️ API Pública: Exponer funciones para uso externo
    w.FacturasEditorModule = {
        init,
        emitirFactura,
        recolectarItems,
        calcularTotales,
        actualizarTotalesEnDOM
    };

    // ⚠️ Compatibilidad: Alias para uso legacy
    if (!w.FacturasModule) {
        w.FacturasModule = {};
    }
    w.FacturasModule.emitirFactura = emitirFactura;

})(window, document);
