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

        // Eliminar campos inmutables del XML (backend los rechaza con 400 en cualquier PATCH)
        // SSoT: matches XML_IMMUTABLE_FIELDS en models.py
        const XML_IMMUTABLE = new Set([
            'id', 'numero', 'prefijo', 'consecutivo', 'tipo', 'naturaleza', 'fecha_emision',
            'emisor_nit', 'emisor_razon_social', 'emisor_direccion', 'emisor_email', 'emisor_telefono',
            'emisor_actividad_ciiu',
            'receptor_nit', 'receptor_razon_social', 'receptor_direccion', 'receptor_email', 'receptor_telefono',
            'moneda', 'subtotal', 'impuestos', 'total', 'cufe', 'qr_code', 'qr_url',
            'autorizacion_numero', 'autorizacion_prefijo', 'autorizacion_rango_desde',
            'autorizacion_rango_hasta', 'autorizacion_vigencia_inicio', 'autorizacion_vigencia_fin',
        ]);
        Object.keys(data).forEach(k => { if (XML_IMMUTABLE.has(k)) delete data[k]; });

        // Cotización (v3.10.1): incluir en PATCH estándar (editable en MANUAL_EDITABLE_FIELDS)
        const cotizacionUuid = getCotizacionUuidFromEditor();
        if (cotizacionUuid !== undefined) {
            data.cotizacion_uuid = cotizacionUuid;
        }

        return data;
    }

    function getCotizacionUuidFromEditor() {
        const select = d.querySelector('#factura-cotizacion_uuid');
        if (!select) return undefined;
        return select.value || null;
    }

    function getClienteUuidFromEditor() {
        const select = d.querySelector('#factura-cliente_uuid');
        if (!select) return undefined;
        return select.value || null;
    }

    function getProveedorUuidFromEditor() {
        const select = d.querySelector('#factura-proveedor_uuid');
        if (!select) return undefined;
        return select.value || null;
    }

    /**
     * Guardar vinculaciones de inventario para cada ítem de la factura
     * v3.9.2: Después de guardar la factura, actualiza los campos item_inventario_*
     */
    async function guardarVinculacionesInventario() {
        const rows = d.querySelectorAll('tr[data-item-id]');
        if (!rows.length) return;

        for (const row of rows) {
            const itemId = row.getAttribute('data-item-id');
            const hiddenContainer = row.querySelector('[data-inventario-fields]');

            // Solo guardar si hay vinculación
            if (!hiddenContainer || !hiddenContainer.innerHTML.trim()) continue;

            // Extraer UUIDs de los hidden inputs
            const uuidInput = hiddenContainer.querySelector('input[name*="uuid"]');
            const tipoInput = hiddenContainer.querySelector('input[name*="tipo"]');
            const codigoInput = hiddenContainer.querySelector('input[name*="codigo"]');

            if (!uuidInput || !tipoInput || !codigoInput) continue;

            const data = {
                item_inventario_uuid: uuidInput.value,
                item_inventario_tipo: tipoInput.value,
                item_inventario_codigo: codigoInput.value
            };

            // PATCH a /api/v1/items-factura/{itemId}/
            const res = await w.http('PATCH', `/api/v1/items-factura/${itemId}/`, data);
            if (!res.ok) {
                console.warn(`${MOD} Error al guardar vinculación del ítem ${itemId}:`, res.data);
            }
        }
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

        const id = d.querySelector('#factura-id')?.value;

        // Validar que hay al menos un ítem (solo para nuevas facturas; las existentes tienen ítems de XML)
        if (!id && (!data.items || data.items.length === 0)) {
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError(
                    { ok: false, status: 422, data: { detail: 'Debe agregar al menos un ítem a la factura.' } },
                    MOD,
                    { errorContainerSelector: '#form-factura-feedback' }
                );
            } else {
                alert('Debe agregar al menos un ítem a la factura.');
            }
            return;
        }

        // Para facturas existentes los ítems son de XML e ignorados por el backend
        if (id) {
            delete data.items;
        }

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

        const cotizacionUuid = getCotizacionUuidFromEditor();
        if (id && cotizacionUuid !== undefined && w.facturasAPI && typeof w.facturasAPI.vincularCotizacion === 'function') {
            const linkRes = await w.facturasAPI.vincularCotizacion(id, cotizacionUuid);
            if (!linkRes.ok) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(linkRes, MOD, {
                        errorContainerSelector: '#form-factura-feedback'
                    });
                }
                return;
            }
        }

        const clienteUuid = getClienteUuidFromEditor();
        if (id && clienteUuid && w.facturasAPI && typeof w.facturasAPI.vincularCliente === 'function') {
            const clienteRes = await w.facturasAPI.vincularCliente(id, clienteUuid);
            if (!clienteRes.ok) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(clienteRes, MOD, {
                        errorContainerSelector: '#form-factura-feedback'
                    });
                }
                return;
            }
        }

        const proveedorUuid = getProveedorUuidFromEditor();
        if (id && proveedorUuid && w.facturasAPI && typeof w.facturasAPI.vincularProveedor === 'function') {
            const proveedorRes = await w.facturasAPI.vincularProveedor(id, proveedorUuid);
            if (!proveedorRes.ok) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(proveedorRes, MOD, {
                        errorContainerSelector: '#form-factura-feedback'
                    });
                }
                return;
            }
        }

        // ⚠️ v3.9.2: Guardar vinculaciones de inventario de cada ítem
        await guardarVinculacionesInventario();

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
        if (!form) return;

        // Guard: evitar doble inicialización en el mismo form (MutationObserver + htmx:afterSwap)
        if (form.dataset.editorInitialized === 'true') return;
        form.dataset.editorInitialized = 'true';

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

        // Sincronizar selects "select-shield" con sus hidden inputs (estado, categoria)
        form.querySelectorAll('select.select-shield[data-target]').forEach(select => {
            const hiddenInput = form.querySelector(`input[type="hidden"][name="${select.dataset.target}"]`);
            if (!hiddenInput) return;
            hiddenInput.value = select.value;
            select.addEventListener('change', () => { hiddenInput.value = select.value; });
        });

        initCotizacionSelect();
        initClienteSelect();
        initProveedorSelect();
        initResumenPagosBancos(form);



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

    async function initCotizacionSelect() {
        const select = d.querySelector('#factura-cotizacion_uuid');
        if (!select || select.dataset.loaded === 'true') return;

        const current = select.dataset.current || '';
        const currentLabel = select.dataset.currentLabel || '';

        try {
            const res = await w.http('GET', '/api/v1/cotizaciones/?page_size=100');
            if (!res || !res.ok) return;

            const rows = Array.isArray(res.data) ? res.data : (res.data.results || []);
            rows.forEach(cotizacion => {
                if (!cotizacion.uuid || select.querySelector(`option[value="${cotizacion.uuid}"]`)) return;
                const option = d.createElement('option');
                option.value = cotizacion.uuid;
                option.textContent = cotizacion.codigo_unico || cotizacion.numero_cotizacion || cotizacion.uuid;
                option.selected = cotizacion.uuid === current;
                select.appendChild(option);
            });

            if (current && currentLabel && !select.querySelector(`option[value="${current}"]`)) {
                const option = d.createElement('option');
                option.value = current;
                option.textContent = currentLabel;
                option.selected = true;
                select.appendChild(option);
            }

            select.dataset.loaded = 'true';
        } catch (error) {
            console.warn('[facturas.editor:cotizacion_select] No se pudieron cargar cotizaciones:', error);
        }
    }

    // ── CLIENTE SEARCH + QUICK CREATE ───────────────────────────────────

    function initClienteSelect() {
        // Entry point called from initEditorEvents — delegates to search + quick-create
        initClienteSearch();
        initQuickCreateCliente();
    }

    function initClienteSearch() {
        const searchInput = d.querySelector('#factura-cliente_search');
        const uuidInput = d.querySelector('#factura-cliente_uuid');
        const suggestions = d.querySelector('#factura-cliente-suggestions');
        if (!searchInput || !uuidInput || !suggestions) return;

        let debounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const q = searchInput.value.trim();
            if (q.length < 2) { suggestions.classList.add('d-none'); return; }
            debounceTimer = setTimeout(async () => {
                const res = await w.http('GET', `/api/v1/clientes/?search=${encodeURIComponent(q)}&page_size=10`);
                if (!res || !res.ok) return;
                const items = Array.isArray(res.data) ? res.data : (res.data.results || []);
                renderEntidadSuggestions(items, suggestions, searchInput, uuidInput, 'cliente',
                    c => c.razon_social || c.numero_documento,
                    c => c.numero_documento ? `Doc: ${c.numero_documento}` : '');
            }, 280);
        });

        searchInput.addEventListener('change', () => {
            if (!searchInput.value.trim()) {
                uuidInput.value = '';
                renderFichaVacia('ficha-cliente-container', 'cliente');
                actualizarBadgeVinculado('badge-cliente-vinculado', false);
            }
        });

        d.addEventListener('click', e => {
            if (!suggestions.contains(e.target) && !searchInput.contains(e.target)) {
                suggestions.classList.add('d-none');
            }
        });
    }

    function initQuickCreateCliente() {
        const btn = d.querySelector('#btn-quick-crear-cliente');
        if (!btn) return;
        btn.addEventListener('click', () => abrirModalCrearEntidad('cliente'));
    }

    // ── PROVEEDOR SEARCH + QUICK CREATE ──────────────────────────────────

    function initProveedorSelect() {
        // Entry point called from initEditorEvents — delegates to search + quick-create
        initProveedorSearch();
        initQuickCreateProveedor();
    }

    function initProveedorSearch() {
        const searchInput = d.querySelector('#factura-proveedor_search');
        const uuidInput = d.querySelector('#factura-proveedor_uuid');
        const suggestions = d.querySelector('#factura-proveedor-suggestions');
        if (!searchInput || !uuidInput || !suggestions) return;

        let debounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const q = searchInput.value.trim();
            if (q.length < 2) { suggestions.classList.add('d-none'); return; }
            debounceTimer = setTimeout(async () => {
                const res = await w.http('GET', `/api/v1/proveedores/?search=${encodeURIComponent(q)}&page_size=10`);
                if (!res || !res.ok) return;
                const items = Array.isArray(res.data) ? res.data : (res.data.results || []);
                renderEntidadSuggestions(items, suggestions, searchInput, uuidInput, 'proveedor',
                    p => p.razon_social || p.numero_documento || p.nit,
                    p => (p.numero_documento || p.nit) ? `NIT: ${p.numero_documento || p.nit}` : '');
            }, 280);
        });

        searchInput.addEventListener('change', () => {
            if (!searchInput.value.trim()) {
                uuidInput.value = '';
                renderFichaVacia('ficha-proveedor-container', 'proveedor');
                actualizarBadgeVinculado('badge-proveedor-vinculado', false);
            }
        });

        d.addEventListener('click', e => {
            if (!suggestions.contains(e.target) && !searchInput.contains(e.target)) {
                suggestions.classList.add('d-none');
            }
        });
    }

    function initQuickCreateProveedor() {
        const btn = d.querySelector('#btn-quick-crear-proveedor');
        if (!btn) return;
        btn.addEventListener('click', () => abrirModalCrearEntidad('proveedor'));
    }

    // ── SHARED HELPERS ────────────────────────────────────────────────────

    function renderEntidadSuggestions(items, container, searchInput, uuidInput, tipo, labelFn, subFn) {
        if (items.length === 0) {
            container.innerHTML = '<div class="list-group-item small text-muted py-2">No se encontraron resultados</div>';
        } else {
            container.innerHTML = items.map(item => {
                const label = labelFn(item);
                const sub = subFn(item);
                return `<button type="button" class="list-group-item list-group-item-action small py-2"
                            data-uuid="${item.uuid}" data-label="${label}">
                    <div class="fw-semibold">${label}</div>
                    ${sub ? `<small class="text-muted">${sub}</small>` : ''}
                </button>`;
            }).join('');
        }
        container.classList.remove('d-none');

        container.querySelectorAll('button[data-uuid]').forEach(btn => {
            btn.addEventListener('click', async () => {
                uuidInput.value = btn.dataset.uuid;
                searchInput.value = btn.dataset.label;
                container.classList.add('d-none');
                actualizarBadgeVinculado(`badge-${tipo}-vinculado`, true);
                await refreshEntidadFicha(tipo, btn.dataset.uuid);
            });
        });
    }

    async function refreshEntidadFicha(tipo, uuid) {
        const endpoint = tipo === 'cliente' ? `/api/v1/clientes/${uuid}/` : `/api/v1/proveedores/${uuid}/`;
        const containerId = tipo === 'cliente' ? 'ficha-cliente-container' : 'ficha-proveedor-container';
        const container = d.getElementById(containerId);
        if (!container) return;

        try {
            const res = await w.http('GET', endpoint);
            if (!res || !res.ok || !res.data) return;
            const data = res.data;
            const nombre = data.razon_social || data.nombre || '';
            const comercial = data.nombre_comercial || '';
            const doc = data.numero_documento || data.nit || '';
            const email = data.email || '';
            const tel = data.telefono || '';

            const iconClass = tipo === 'cliente' ? 'bi-person-fill text-primary' : 'bi-truck';
            const iconStyle = tipo === 'cliente' ? 'background:rgba(13,110,253,.1)' : 'background:rgba(133,100,4,.12)';
            const iconColor = tipo === 'cliente' ? '' : 'style="color:#856404;"';

            container.innerHTML = `
            <div class="card bg-light border-0">
              <div class="card-body py-2 px-3">
                <div class="d-flex align-items-start gap-3">
                  <div class="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                       style="width:42px;height:42px;${iconStyle}">
                    <i class="bi ${iconClass} fs-5" ${iconColor}></i>
                  </div>
                  <div class="flex-grow-1 min-width-0">
                    <div class="fw-semibold">${nombre}</div>
                    ${comercial ? `<div class="text-muted small">${comercial}</div>` : ''}
                    <div class="row g-2 mt-1">
                      ${doc ? `<div class="col-sm-6"><span class="text-muted small"><i class="bi bi-card-text me-1"></i>Doc:</span> <span class="small fw-semibold">${doc}</span></div>` : ''}
                      ${email ? `<div class="col-sm-6 text-truncate"><span class="text-muted small"><i class="bi bi-envelope me-1"></i></span> <span class="small">${email}</span></div>` : ''}
                      ${tel ? `<div class="col-sm-6"><span class="text-muted small"><i class="bi bi-telephone me-1"></i></span> <span class="small">${tel}</span></div>` : ''}
                    </div>
                  </div>
                </div>
              </div>
            </div>`;
        } catch (err) {
            console.warn(`[facturas.editor] No se pudo actualizar ficha ${tipo}:`, err);
        }
    }

    function renderFichaVacia(containerId, tipo) {
        const container = d.getElementById(containerId);
        if (!container) return;
        const icon = tipo === 'cliente' ? 'bi-person-x' : 'bi-truck';
        const msg = tipo === 'cliente' ? 'Sin cliente vinculado. Busca o crea uno.' : 'Sin proveedor vinculado. Busca o crea uno.';
        container.innerHTML = `<div class="text-muted small text-center py-3 border rounded bg-light">
            <i class="bi ${icon} fs-4 d-block mb-1 text-secondary"></i>${msg}</div>`;
    }

    function actualizarBadgeVinculado(badgeId, vinculado) {
        const badge = d.getElementById(badgeId);
        if (!badge) return;
        if (vinculado) {
            badge.className = 'badge ms-auto bg-success';
            badge.textContent = 'Vinculado';
        } else {
            badge.className = 'badge ms-auto bg-warning text-dark';
            badge.textContent = 'Sin vincular';
        }
    }

    // ── QUICK CREATE MODAL ────────────────────────────────────────────────

    function abrirModalCrearEntidad(tipo) {
        const modalId = `modal-crear-${tipo}`;
        d.getElementById(modalId)?.remove(); // eliminar instancia anterior si existe

        const isCliente = tipo === 'cliente';

        // Pre-diligenciar con datos del XML de la factura (receptor→cliente, emisor→proveedor)
        const facturaForm = d.querySelector('#form-factura');
        const naturaleza = facturaForm?.dataset.naturaleza || '';
        const prefill = {};
        if (isCliente && naturaleza === 'VENTA') {
            prefill.numero_documento = d.querySelector('[name="receptor_nit"]')?.value || '';
            prefill.razon_social     = d.querySelector('[name="receptor_razon_social"]')?.value || '';
            prefill.email            = d.querySelector('[name="receptor_email"]')?.value || '';
            prefill.telefono         = d.querySelector('[name="receptor_telefono"]')?.value || '';
        } else if (!isCliente && naturaleza === 'COMPRA') {
            prefill.numero_documento = d.querySelector('[name="emisor_nit"]')?.value || '';
            prefill.razon_social     = d.querySelector('[name="emisor_razon_social"]')?.value || '';
            prefill.email            = d.querySelector('[name="emisor_email"]')?.value || '';
            prefill.telefono         = d.querySelector('[name="emisor_telefono"]')?.value || '';
        }
        const hasPrefill = !!(prefill.numero_documento || prefill.razon_social);

        const titulo = isCliente ? 'Nuevo Cliente' : 'Nuevo Proveedor';
        const color = isCliente ? 'primary' : 'warning';
        const icon = isCliente ? 'bi-person-plus' : 'bi-truck';

        const regimenOpts = [
            ['ORDINARIO', 'Régimen Ordinario'],
            ['SIMPLE', 'Régimen Simple'],
            ['ESPECIAL', 'Régimen Especial'],
            ['NO_RESPONSABLE', 'No Responsable de IVA'],
        ].map(([v, l]) => `<option value="${v}">${l}</option>`).join('');

        const tipoPersonaOpts = [
            ['NATURAL', 'Persona Natural'],
            ['JURIDICA', 'Persona Jurídica'],
        ].map(([v, l]) => `<option value="${v}" ${!isCliente && v === 'JURIDICA' ? 'selected' : ''}>${l}</option>`).join('');

        const tipoDocOpts = [
            ['NIT', 'NIT'],
            ['CC', 'Cédula de Ciudadanía'],
            ['CE', 'Cédula de Extranjería'],
            ['PASAPORTE', 'Pasaporte'],
        ].map(([v, l]) => `<option value="${v}" ${!isCliente && v === 'NIT' ? 'selected' : ''}>${l}</option>`).join('');

        const extraFields = isCliente ? `
            <div class="col-12">
              <label class="form-label small fw-semibold">Tipo Persona <span class="text-danger">*</span></label>
              <select class="form-select form-select-sm" name="tipo_persona" required>${tipoPersonaOpts}</select>
            </div>
            <div class="col-12">
              <label class="form-label small fw-semibold">Tipo Documento <span class="text-danger">*</span></label>
              <select class="form-select form-select-sm" name="tipo_documento" required>${tipoDocOpts}</select>
            </div>` : `
            <div class="col-6">
              <label class="form-label small fw-semibold">Tipo Persona</label>
              <select class="form-select form-select-sm" name="tipo_persona">${tipoPersonaOpts}</select>
            </div>
            <div class="col-6">
              <label class="form-label small fw-semibold">Tipo Documento</label>
              <select class="form-select form-select-sm" name="tipo_documento">${tipoDocOpts}</select>
            </div>`;

        const html = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header bg-${color} ${color === 'warning' ? 'text-dark' : 'text-white'}">
                <h5 class="modal-title"><i class="bi ${icon} me-2"></i>${titulo}${hasPrefill ? ' <span class="badge bg-light text-dark border ms-2" style="font-size:.6rem;vertical-align:middle;"><i class=\'bi bi-magic me-1\'></i>Auto</span>' : ''}</h5>
                <button type="button" class="btn-close ${color !== 'warning' ? 'btn-close-white' : ''}" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <div id="${modalId}-error" class="alert alert-danger d-none small py-2 mb-3"></div>
                <form id="${modalId}-form">
                  <div class="row g-3">
                    ${extraFields}
                    <div class="col-12">
                      <label class="form-label small fw-semibold">Número de Documento <span class="text-danger">*</span></label>
                      <input type="text" class="form-control form-control-sm" name="numero_documento"
                             placeholder="Ej: 9001234567" value="${prefill.numero_documento || ''}" required>
                    </div>
                    <div class="col-12">
                      <label class="form-label small fw-semibold">Razón Social / Nombre <span class="text-danger">*</span></label>
                      <input type="text" class="form-control form-control-sm" name="razon_social"
                             placeholder="${isCliente ? 'Nombre completo o razón social' : 'Razón social del proveedor'}"
                             value="${prefill.razon_social || ''}" required>
                    </div>
                    <div class="col-12">
                      <label class="form-label small fw-semibold">Régimen Tributario <span class="text-danger">*</span></label>
                      <select class="form-select form-select-sm" name="regimen_tributario" required>
                        ${regimenOpts}
                      </select>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label small fw-semibold">Email</label>
                      <input type="email" class="form-control form-control-sm" name="email"
                             placeholder="correo@empresa.com" value="${prefill.email || ''}">
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label small fw-semibold">Teléfono</label>
                      <input type="text" class="form-control form-control-sm" name="telefono"
                             placeholder="300 000 0000" value="${prefill.telefono || ''}">
                    </div>
                  </div>
                </form>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-${color} btn-sm" id="${modalId}-submit">
                  <i class="bi bi-check-circle me-1"></i>Crear
                </button>
              </div>
            </div>
          </div>
        </div>`;

        const wrapper = d.createElement('div');
        wrapper.innerHTML = html;
        d.body.appendChild(wrapper);

        const modalEl = d.getElementById(modalId);
        const bsModal = new bootstrap.Modal(modalEl);
        bsModal.show();

        modalEl.addEventListener('hidden.bs.modal', () => wrapper.remove());

        d.getElementById(`${modalId}-submit`).addEventListener('click', async () => {
            const form = d.getElementById(`${modalId}-form`);
            const errorDiv = d.getElementById(`${modalId}-error`);
            if (!form.checkValidity()) { form.reportValidity(); return; }

            const payload = Object.fromEntries(new FormData(form));
            // Remove empty optional strings
            Object.keys(payload).forEach(k => { if (payload[k] === '') delete payload[k]; });

            const submitBtn = d.getElementById(`${modalId}-submit`);
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Creando...';
            errorDiv.classList.add('d-none');

            const endpoint = isCliente ? '/api/v1/clientes/' : '/api/v1/proveedores/';
            const res = await w.http('POST', endpoint, payload);

            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Crear';

            if (!res || !res.ok) {
                const msg = res?.data ? JSON.stringify(res.data) : 'Error al crear';
                errorDiv.textContent = msg;
                errorDiv.classList.remove('d-none');
                return;
            }

            const created = res.data;
            const uuidInput = d.querySelector(`#factura-${tipo}_uuid`);
            const searchInput = d.querySelector(`#factura-${tipo}_search`);
            if (uuidInput) uuidInput.value = created.uuid;
            if (searchInput) searchInput.value = created.razon_social || created.numero_documento || '';

            actualizarBadgeVinculado(`badge-${tipo}-vinculado`, true);
            await refreshEntidadFicha(tipo, created.uuid);

            if (w.SintelFeedback) w.SintelFeedback.success(`${isCliente ? 'Cliente' : 'Proveedor'} creado y vinculado`);
            bsModal.hide();
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
    // afterSettle: DOM estable tras swap — no usar afterSwap + setTimeout (skill htmx.md §12)
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:afterSettle', (event) => {
            if (event.detail.target.id === 'offcanvas-container-facturas') {
                const form = d.querySelector('#form-factura');
                if (form) {
                    initEditorEvents();
                    actualizarTotalesEnDOM();
                }
                // Modo Subir (form-upload-factura) o Lectura: no requieren inicializacion
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

    // ── v3.11.0: Resumen de Pagos Bancos + Bloqueo estado_pago ──────────────
    function initResumenPagosBancos(form) {
        const medioPagoEl  = form.querySelector('#factura-medio-pago-codigo');
        const estadoPagoEl = form.querySelector('#factura-estado-pago');
        const hidEstado    = form.querySelector('input[name="estado_pago"]');
        const badgeMedio   = d.getElementById('badge-medio-pago');
        const rpPagado     = d.getElementById('rp-pagado');
        const rpSaldo      = d.getElementById('rp-saldo');
        const rpAlerta     = d.getElementById('rp-alerta');

        if (!medioPagoEl || !estadoPagoEl) return;

        // Leer valores del servidor inyectados en data- del formulario
        const totalPagadoBancos = parseFloat(form.dataset.totalPagadoBancos || '0') || 0;
        const saldoPendiente    = parseFloat(form.dataset.saldoPendiente    || '0') || 0;

        const COP = (v) => '$' + new Intl.NumberFormat('es-CO', { minimumFractionDigits: 0 }).format(v);

        function _aplicarReglas() {
            const esEfectivo = medioPagoEl.value.trim() === '10';

            // Actualizar badge
            if (badgeMedio) {
                badgeMedio.textContent  = esEfectivo ? 'Efectivo' : 'Bancario';
                badgeMedio.className    = 'badge ms-auto ' + (esEfectivo ? 'bg-secondary' : 'bg-primary');
                badgeMedio.style.fontSize = '.62rem';
            }

            // Actualizar indicadores numéricos
            if (rpPagado) {
                rpPagado.textContent  = COP(totalPagadoBancos);
                rpPagado.className    = 'fw-bold font-monospace ' + (totalPagadoBancos > 0 ? 'text-success' : 'text-muted');
            }
            if (rpSaldo) {
                rpSaldo.textContent = COP(saldoPendiente);
                rpSaldo.className   = 'fw-bold font-monospace ' + (saldoPendiente > 0 ? 'text-danger' : 'text-success');
            }

            if (esEfectivo) {
                // Efectivo: sin restricciones
                estadoPagoEl.disabled = false;
                Array.from(estadoPagoEl.options).forEach(o => o.disabled = false);
                if (rpAlerta) rpAlerta.classList.add('d-none');
                return;
            }

            // No efectivo: aplicar reglas según conciliacion
            if (totalPagadoBancos === 0) {
                // Sin conciliacion → forzar NO_PAGADA
                estadoPagoEl.value     = 'NO_PAGADA';
                if (hidEstado) hidEstado.value = 'NO_PAGADA';
                Array.from(estadoPagoEl.options).forEach(o => {
                    o.disabled = o.value !== 'NO_PAGADA';
                });
                if (rpAlerta) {
                    rpAlerta.innerHTML  = '<i class="bi bi-exclamation-circle me-1"></i>Sin conciliaciones bancarias. Solo puede ser <strong>NO_PAGADA</strong>.';
                    rpAlerta.className  = 'mt-2 alert alert-warning py-1 px-2 small';
                    rpAlerta.classList.remove('d-none');
                }
            } else if (saldoPendiente <= 0) {
                // 100% conciliado → forzar PAGADA
                estadoPagoEl.value     = 'PAGADA';
                if (hidEstado) hidEstado.value = 'PAGADA';
                Array.from(estadoPagoEl.options).forEach(o => {
                    o.disabled = o.value !== 'PAGADA';
                });
                if (rpAlerta) {
                    rpAlerta.innerHTML  = '<i class="bi bi-check-circle me-1 text-success"></i>100% conciliado. Estado forzado a <strong>PAGADA</strong>.';
                    rpAlerta.className  = 'mt-2 alert alert-success py-1 px-2 small';
                    rpAlerta.classList.remove('d-none');
                }
            } else {
                // Pago parcial
                estadoPagoEl.value     = 'PAGO_PARCIAL';
                if (hidEstado) hidEstado.value = 'PAGO_PARCIAL';
                Array.from(estadoPagoEl.options).forEach(o => {
                    o.disabled = !['PAGO_PARCIAL', 'PAGADA'].includes(o.value);
                });
                if (rpAlerta) {
                    rpAlerta.innerHTML  = `<i class="bi bi-info-circle me-1"></i>Pago parcial. Saldo pendiente: <strong>${COP(saldoPendiente)}</strong>. Marcar como PAGADA solo si hay retenciones u otros ajustes.`;
                    rpAlerta.className  = 'mt-2 alert alert-info py-1 px-2 small';
                    rpAlerta.classList.remove('d-none');
                }
            }
        }

        // Sincronizar hidden input cuando el usuario cambia estado_pago manualmente
        estadoPagoEl.addEventListener('change', () => {
            if (hidEstado) hidEstado.value = estadoPagoEl.value;
        });

        // Reaccionar al cambio de medio de pago
        medioPagoEl.addEventListener('input', _aplicarReglas);
        medioPagoEl.addEventListener('change', _aplicarReglas);

        // Aplicar reglas al abrir el formulario
        _aplicarReglas();
    }

})(window, document);
