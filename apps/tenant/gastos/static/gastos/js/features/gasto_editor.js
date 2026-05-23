/**
 * Gastos Editor Module - Formulario de creación/edición de Gastos
 * 
 * Namespace: window.Sintel.Gastos.Editor
 * Versión: v2.62.0
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Gastos = window.Sintel.Gastos || {};

    let _proveedoresCache = [];
    let _retenciones = {
        retefuente_porcentaje: 0,
        reteica_porcentaje: 0,
        reteiva_porcentaje: 0
    };

    /**
     * Inicializa el editor de gastos.
     * @param {string|HTMLElement} formSelector 
     */
    async function init(formSelector) {
        const form = (typeof formSelector === 'string') ? document.querySelector(formSelector) : formSelector;
        if (!form) return;
        
        if (form.dataset.gastoEditorBound === 'true') return;
        form.dataset.gastoEditorBound = 'true';

        console.log('[GastoEditor] Inicializando:', form.id);

        const offcanvasEl = form.closest('.offcanvas');
        
        // Cargar catálogos
        await Promise.allSettled([
            cargarResoluciones(form),
            cargarProveedores(form)
        ]);

        // Inicializar buscador de cuentas (v3.7.1)
        initCuentaSearch(form);

        // Inicializar selectores de inventario
        initInventarioSelects(form);

        // ── Eventos para Valores Financieros (Input editable) ────────────────
        const subtotalInput = form.querySelector('#subtotal');

        if (subtotalInput) {
            subtotalInput.addEventListener('input', function () {
                calcularTotales(form);
            });
        }

        // ── Eventos para Retenciones (Selects) ──────────────────────────────
        const retefuenteSelect = form.querySelector('#retefuente_select');
        const reteicaSelect = form.querySelector('#reteica_select');
        const retefuentePctInput = form.querySelector('#retefuente_porcentaje');
        const reteicaPctInput = form.querySelector('#reteica_porcentaje');

        if (retefuenteSelect) {
            retefuenteSelect.addEventListener('change', function () {
                if (retefuentePctInput) retefuentePctInput.value = this.value || '0';
                calcularTotales(form);
            });
        }

        if (reteicaSelect) {
            reteicaSelect.addEventListener('change', function () {
                if (reteicaPctInput) reteicaPctInput.value = this.value || '0';
                calcularTotales(form);
            });
        }

        // Cambio de proveedor
        form.querySelector('#proveedor_uuid')?.addEventListener('change', (e) => {
            actualizarInfoProveedor(form, e.target.value);
            calcularTotales(form);
        });

        // Submit
        form.addEventListener('submit', handleSubmit);

        // ── Precargar valores en Edit mode ────────────────────────────────────
        if (subtotalInput) {
            const subtotalVal = parseFloat(subtotalInput.value) || 0;
            if (subtotalVal > 0) {
                subtotalInput.value = subtotalVal;
            }
        }

        // Preseleccionar retenciones si ya están configuradas
        const retefuenteVal = retefuentePctInput?.value;
        const reteicaVal = reteicaPctInput?.value;
        if (retefuenteVal && retefuenteSelect) {
            const matchOpt = [...retefuenteSelect.options].find(o => o.value == retefuenteVal);
            if (matchOpt) retefuenteSelect.value = retefuenteVal;
        }
        if (reteicaVal && reteicaSelect) {
            const matchOpt = [...reteicaSelect.options].find(o => o.value == reteicaVal);
            if (matchOpt) reteicaSelect.value = reteicaVal;
        }

        // Inicializar cálculos si ya hay datos (Edición)
        calcularTotales(form);
    }

    /**
     * Carga las resoluciones DIAN en el select.
     */
    async function cargarResoluciones(form) {
        const select = form.querySelector('#resolucion');
        if (!select) return;

        const currentValue = select.dataset.selected || select.dataset.value || select.value;

        try {
            const preOption = select.querySelector(`option[value="${currentValue}"]`);
            const preText = preOption ? preOption.textContent : null;

            const response = await fetch(window.Sintel.Gastos.API.resoluciones.list, {
                headers: window.Sintel.Gastos.getHeaders()
            });
            const result = await response.json();
            const resoluciones = Array.isArray(result) ? result : (result.results || []);

            select.innerHTML = '<option value="">Seleccione...</option>';
            let found = false;
            resoluciones.forEach(res => {
                const opt = document.createElement('option');
                opt.value = res.id;
                opt.textContent = `${res.prefijo || ''} ${res.numero_resolucion}`;
                if (res.id?.toString() === currentValue?.toString()) {
                    opt.selected = true;
                    found = true;
                }
                select.appendChild(opt);
            });

            if (currentValue && !found && preText) {
                const opt = document.createElement('option');
                opt.value = currentValue;
                opt.textContent = preText;
                opt.selected = true;
                select.appendChild(opt);
            }

            // Si es creación y no hay selección, intentar cargar la activa
            if (!select.value && !form.dataset.uuid) {
                try {
                    const activeRes = await fetch(window.Sintel.Gastos.API.resoluciones.activa, {
                        headers: window.Sintel.Gastos.getHeaders()
                    });
                    if (activeRes.ok) {
                        const resData = await activeRes.json();
                        if (resData && resData.id) select.value = resData.id;
                    }
                } catch (err) {
                    console.warn('[GastoEditor] No se pudo cargar resolucion activa.');
                }
            }
        } catch (e) {
            console.error('[GastoEditor] Error resoluciones:', e);
        }
    }

    /**
     * Carga proveedores.
     */
    async function cargarProveedores(form) {
        const select = form.querySelector('#proveedor_uuid');
        if (!select) return;

        const currentValue = select.dataset.selected || select.dataset.value || select.value;

        try {
            const preOption = select.querySelector(`option[value="${currentValue}"]`);
            const preText = preOption ? preOption.textContent : null;

            const response = await fetch(window.Sintel.Gastos.API.proveedores.list, {
                headers: window.Sintel.Gastos.getHeaders()
            });
            const result = await response.json();
            _proveedoresCache = Array.isArray(result) ? result : (result.results || []);

            select.innerHTML = '<option value="">Seleccione...</option>';
            let found = false;
            _proveedoresCache.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.razon_social;
                if (p.id?.toString() === currentValue?.toString()) {
                    opt.selected = true;
                    found = true;
                }
                select.appendChild(opt);
            });

            if (currentValue && !found && preText) {
                const opt = document.createElement('option');
                opt.value = currentValue;
                opt.textContent = preText;
                opt.selected = true;
                select.appendChild(opt);
                
                // Agregar al cache local ficticio para que actualizarInfoProveedor no falle
                _proveedoresCache.push({
                    id: currentValue,
                    razon_social: preText,
                    numero_documento: form.querySelector('#vendedor_nit_display')?.textContent || '',
                    telefono_contacto: form.querySelector('#vendedor_telefono_display')?.textContent || '',
                    direccion: form.querySelector('#vendedor_direccion_display')?.textContent || ''
                });
            }
            
            if (currentValue) actualizarInfoProveedor(form, currentValue);
        } catch (e) {
            console.error('[GastoEditor] Error proveedores:', e);
        }
    }

    function actualizarInfoProveedor(form, uuid) {
        const p = _proveedoresCache.find(x => x.id == uuid);
        const nit = form.querySelector('#vendedor_nit_display');
        const tel = form.querySelector('#vendedor_telefono_display');
        const dir = form.querySelector('#vendedor_direccion_display');

        if (nit) nit.textContent = p ? (p.numero_documento || 'N/A') : 'N/A';
        if (tel) tel.textContent = p ? (p.telefono_contacto || 'N/A') : 'N/A';
        if (dir) dir.textContent = p ? (p.direccion || 'Seleccione un proveedor') : 'Seleccione un proveedor';

        // Obtener retenciones configuradas para este proveedor
        if (p && p.numero_documento) {
            obtenerRetencionesProveedor(form, p.numero_documento);
        }
    }

    async function obtenerRetencionesProveedor(form, nit) {
        try {
            const config = await window.Sintel.Gastos.API.contabilidad.obtenerRetenciones(nit);
            if (config) {
                const retefuentePct = form.querySelector('#retefuente_porcentaje');
                const reteicaPct = form.querySelector('#reteica_porcentaje');
                const reteivaAct = form.querySelector('#reteiva_porcentaje');

                if (retefuentePct) retefuentePct.value = config.retefuente_porcentaje || 0;
                if (reteicaPct) reteicaPct.value = config.reteica_porcentaje || 0;
                if (reteivaAct) reteivaAct.value = config.reteiva_porcentaje || 0;

                _retenciones = config;
                calcularTotales(form);
            }
        } catch (err) {
            console.warn('[GastoEditor] No se pudieron cargar retenciones del proveedor:', err);
            // Limpiar retenciones en caso de error
            const retefuentePct = form.querySelector('#retefuente_porcentaje');
            const reteicaPct = form.querySelector('#reteica_porcentaje');
            const reteivaAct = form.querySelector('#reteiva_porcentaje');
            if (retefuentePct) retefuentePct.value = 0;
            if (reteicaPct) reteicaPct.value = 0;
            if (reteivaAct) reteivaAct.value = 0;
            calcularTotales(form);
        }
    }

    function calcularTotales(form) {
        const subtotal = parseFloat(form.querySelector('#subtotal')?.value) || 0;

        // v3.7.2: Calcular retenciones basadas en porcentajes configurados
        const retefuentePct = parseFloat(form.querySelector('#retefuente_porcentaje')?.value) || 0;
        const reteicaPct = parseFloat(form.querySelector('#reteica_porcentaje')?.value) || 0;
        const reteivaAct = parseFloat(form.querySelector('#reteiva_porcentaje')?.value) || 0;

        const monto_retefuente = (subtotal * retefuentePct / 100);
        const monto_reteica = (subtotal * reteicaPct / 100);
        const monto_reteiva = (subtotal * reteivaAct / 100);

        const total_retenciones = monto_retefuente + monto_reteica + monto_reteiva;
        const total = subtotal - total_retenciones;

        const fmt = (n) => n.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

        // Actualizar badges de porcentaje
        const pctBadge = (id, pct) => {
            const el = form.querySelector(id);
            if (el) el.textContent = pct > 0 ? `${pct}%` : '0%';
        };
        pctBadge('#retefuente_pct_badge', retefuentePct);
        pctBadge('#reteica_pct_badge', reteicaPct);
        pctBadge('#reteiva_pct_badge', reteivaAct);

        // Actualizar displays de montos
        const setDisplay = (id, val) => {
            const el = form.querySelector(id);
            if (el) el.textContent = `$${fmt(val)}`;
        };
        setDisplay('#retefuente_display', monto_retefuente);
        setDisplay('#reteica_display', monto_reteica);
        setDisplay('#reteiva_display', monto_reteiva);
        setDisplay('#total_retenciones_display', total_retenciones);
        setDisplay('#total_display', total);

        const totalInput = form.querySelector('#total');
        if (totalInput) totalInput.value = total.toFixed(2);
    }

    function collectData(form) {
        let gastoUuidVal = form.querySelector('#cuenta_gasto_uuid')?.value;

        // Validate UUID format - if it's just a number or invalid, set to null
        if (gastoUuidVal && gastoUuidVal.length < 32) {
            gastoUuidVal = null;
        }

        const tipoRelacion = form.querySelector('#tipo_relacion_inventario')?.value || 'NINGUNO';

        return {
            resolucion_dian: form.querySelector('#resolucion')?.value,
            fecha: form.querySelector('#fecha')?.value,
            proveedor: form.querySelector('#proveedor_uuid')?.value,
            numero_documento_proveedor: form.querySelector('#numero_documento_proveedor')?.value,
            categoria_contable: form.querySelector('#categoria_contable')?.value,
            descripcion: form.querySelector('#descripcion')?.value,
            observaciones: form.querySelector('#observaciones')?.value,
            subtotal: parseFloat(form.querySelector('#subtotal')?.value) || 0,
            total: parseFloat(form.querySelector('#total')?.value) || 0,
            cuenta_gasto_uuid: gastoUuidVal || null,
            producto_relacionado: tipoRelacion === 'PRODUCTO' ? (form.querySelector('#producto_relacionado')?.value || null) : null,
            servicio_relacionado: tipoRelacion === 'SERVICIO' ? (form.querySelector('#servicio_relacionado')?.value || null) : null,
            activo_relacionado: tipoRelacion === 'ACTIVO_FIJO' ? (form.querySelector('#activo_relacionado')?.value || null) : null
        };
    }

    /**
     * Inicializa el buscador de cuentas contables (v3.7.1)
     */
    function initCuentaSearch(form) {
        const searchInput = form.querySelector('#cuenta_gasto_search');
        const uuidInput = form.querySelector('#cuenta_gasto_uuid');
        const suggestions = form.querySelector('#cuenta-gasto-suggestions');

        if (!searchInput || !uuidInput || !suggestions) return;

        // Si ya hay un UUID (Edición), cargar el nombre
        if (uuidInput.value && !searchInput.value) {
            getCuentaByUuid(uuidInput.value).then(cuenta => {
                if (cuenta) searchInput.value = `${cuenta.codigo} - ${cuenta.nombre}`;
            });
        }

        let debounceTimer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();

            if (query.length < 2) {
                suggestions.classList.add('d-none');
                return;
            }

            debounceTimer = setTimeout(async () => {
                try {
                    const url = window.Sintel.Gastos.API.contabilidad.searchCuentas(query);
                    const response = await fetch(url, { headers: window.Sintel.Gastos.getHeaders() });
                    const result = await response.json();
                    const cuentas = result.results || [];
                    renderSuggestions(cuentas, suggestions, searchInput, uuidInput);
                } catch (err) {
                    console.error('[GastoEditor] Error buscando cuentas:', err);
                }
            }, 300);
        });

        // Cerrar sugerencias al hacer click fuera
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestions.contains(e.target)) {
                suggestions.classList.add('d-none');
            }
        });
    }

    function renderSuggestions(cuentas, container, searchInput, uuidInput) {
        if (cuentas.length === 0) {
            container.innerHTML = '<div class="list-group-item small text-muted">No se encontraron cuentas</div>';
        } else {
            container.innerHTML = cuentas.map(c => `
                <button type="button" class="list-group-item list-group-item-action small py-2" 
                        data-uuid="${c.id}" data-label="${c.codigo} - ${c.nombre}">
                    <div class="d-flex justify-content-between align-items-center">
                        <span><strong>${c.codigo}</strong> - ${c.nombre}</span>
                        <span class="badge bg-light text-muted">${c.tipo_display || ''}</span>
                    </div>
                </button>
            `).join('');
        }

        container.classList.remove('d-none');

        container.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                searchInput.value = btn.dataset.label;
                uuidInput.value = btn.dataset.uuid;
                container.classList.add('d-none');
            });
        });
    }

    async function getCuentaByUuid(uuid) {
        try {
            const url = window.Sintel.Gastos.API.contabilidad.getCuentaByUuid(uuid);
            const response = await fetch(url, { headers: window.Sintel.Gastos.getHeaders() });
            if (!response.ok) return null;
            const data = await response.json();
            const results = data.results || data;
            return Array.isArray(results) ? results[0] : results;
        } catch (err) {
            console.warn('[GastoEditor] No se pudo recuperar detalle de cuenta:', uuid);
            return null;
        }
    }

    /**
     * Manejo del submit.
     */
    async function handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const submitBtn = form.querySelector('[type="submit"]') || document.querySelector(`button[form="${form.id}"]`);
        const uuid = form.dataset.uuid;
        const isEdit = !!uuid;

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const data = collectData(form);
        console.log('[GastoEditor] Datos a enviar:', data);

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
        }

        try {
            let result;
            if (isEdit) {
                result = await window.Sintel.Gastos.API.gastos.update(uuid, data);
                window.UIManager?.notifySuccess('Gasto actualizado correctamente');
                document.body.dispatchEvent(new CustomEvent('gasto-updated', { detail: result }));
            } else {
                result = await window.Sintel.Gastos.API.gastos.create(data);
                window.UIManager?.notifySuccess('Gasto creado correctamente');
                document.body.dispatchEvent(new CustomEvent('gasto-created', { detail: result }));
            }

            // Cerrar offcanvas
            const offcanvasEl = form.closest('.offcanvas');
            if (offcanvasEl) {
                window.UIManager?.handleOffcanvas('#' + offcanvasEl.id, 'hide');
            }

        } catch (error) {
            console.error('[GastoEditor] Full error object:', error);
            console.error('[GastoEditor] Error data:', error.data);

            let errorMsg = 'Error al procesar la solicitud';

            if (error.data) {
                // Handle detail first (usually string)
                if (error.data.detail && typeof error.data.detail === 'string') {
                    errorMsg = error.data.detail;
                }
                // Handle message - could be string or object
                else if (error.data.message) {
                    if (typeof error.data.message === 'string') {
                        errorMsg = error.data.message;
                    } else if (typeof error.data.message === 'object') {
                        // For validation errors with field-level details
                        const fieldErrors = Object.entries(error.data.message)
                            .map(([field, msgs]) => {
                                const msgText = Array.isArray(msgs) ? msgs[0] : msgs;
                                return `${field}: ${msgText}`;
                            })
                            .join('\n');
                        errorMsg = fieldErrors || JSON.stringify(error.data.message);
                    }
                }
                // Fallback to full JSON
                else {
                    errorMsg = JSON.stringify(error.data);
                }
            } else if (error.message) {
                errorMsg = error.message;
            }

            window.UIManager?.notifyError(`Error: ${errorMsg}`);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = isEdit ? '<i class="bi bi-save me-2"></i>Guardar Cambios' : '<i class="bi bi-plus-circle me-2"></i>Crear Gasto';
            }
        }
    }

    /**
     * Gestión e inicialización de selectores de inventario (Fase 4 - Trazabilidad).
     */
    async function cargarProductos(form) {
        const select = form.querySelector('#producto_relacionado');
        if (!select) return;
        const currentValue = select.dataset.selected || select.dataset.value || select.value;

        try {
            const preOption = select.querySelector(`option[value="${currentValue}"]`);
            const preText = preOption ? preOption.textContent : null;

            const response = await fetch(window.Sintel.Gastos.API.inventario.productos, {
                headers: window.Sintel.Gastos.getHeaders()
            });
            const result = await response.json();
            const items = Array.isArray(result) ? result : (result.results || []);

            select.innerHTML = '<option value="">Seleccione producto...</option>';
            let found = false;
            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = `${item.codigo || ''} - ${item.nombre}`;
                if (item.id?.toString() === currentValue?.toString()) {
                    opt.selected = true;
                    found = true;
                }
                select.appendChild(opt);
            });

            if (currentValue && !found && preText) {
                const opt = document.createElement('option');
                opt.value = currentValue;
                opt.textContent = preText;
                opt.selected = true;
                select.appendChild(opt);
            }
        } catch (e) {
            console.error('[GastoEditor] Error productos:', e);
        }
    }

    async function cargarServicios(form) {
        const select = form.querySelector('#servicio_relacionado');
        if (!select) return;
        const currentValue = select.dataset.selected || select.dataset.value || select.value;

        try {
            const preOption = select.querySelector(`option[value="${currentValue}"]`);
            const preText = preOption ? preOption.textContent : null;

            const response = await fetch(window.Sintel.Gastos.API.inventario.servicios, {
                headers: window.Sintel.Gastos.getHeaders()
            });
            const result = await response.json();
            const items = Array.isArray(result) ? result : (result.results || []);

            select.innerHTML = '<option value="">Seleccione servicio...</option>';
            let found = false;
            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = `${item.codigo || ''} - ${item.nombre}`;
                if (item.id?.toString() === currentValue?.toString()) {
                    opt.selected = true;
                    found = true;
                }
                select.appendChild(opt);
            });

            if (currentValue && !found && preText) {
                const opt = document.createElement('option');
                opt.value = currentValue;
                opt.textContent = preText;
                opt.selected = true;
                select.appendChild(opt);
            }
        } catch (e) {
            console.error('[GastoEditor] Error servicios:', e);
        }
    }

    async function cargarActivos(form) {
        const select = form.querySelector('#activo_relacionado');
        if (!select) return;
        const currentValue = select.dataset.selected || select.dataset.value || select.value;

        try {
            const preOption = select.querySelector(`option[value="${currentValue}"]`);
            const preText = preOption ? preOption.textContent : null;

            const response = await fetch(window.Sintel.Gastos.API.inventario.activos, {
                headers: window.Sintel.Gastos.getHeaders()
            });
            const result = await response.json();
            const items = Array.isArray(result) ? result : (result.results || []);

            select.innerHTML = '<option value="">Seleccione activo fijo...</option>';
            let found = false;
            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = `${item.codigo || ''} - ${item.nombre}`;
                if (item.id?.toString() === currentValue?.toString()) {
                    opt.selected = true;
                    found = true;
                }
                select.appendChild(opt);
            });

            if (currentValue && !found && preText) {
                const opt = document.createElement('option');
                opt.value = currentValue;
                opt.textContent = preText;
                opt.selected = true;
                select.appendChild(opt);
            }
        } catch (e) {
            console.error('[GastoEditor] Error activos fijos:', e);
        }
    }

    function initInventarioSelects(form) {
        const tipoRelacionSelect = form.querySelector('#tipo_relacion_inventario');
        if (!tipoRelacionSelect) return;

        const wrapperProducto = form.querySelector('#wrapper_producto_relacionado');
        const wrapperServicio = form.querySelector('#wrapper_servicio_relacionado');
        const wrapperActivo = form.querySelector('#wrapper_activo_relacionado');

        const selectProducto = form.querySelector('#producto_relacionado');
        const selectServicio = form.querySelector('#servicio_relacionado');
        const selectActivo = form.querySelector('#activo_relacionado');

        function ocultarTodos() {
            if (wrapperProducto) wrapperProducto.classList.add('d-none');
            if (wrapperServicio) wrapperServicio.classList.add('d-none');
            if (wrapperActivo) wrapperActivo.classList.add('d-none');
        }

        tipoRelacionSelect.addEventListener('change', async function() {
            const tipo = this.value;
            ocultarTodos();

            // Limpiar valores seleccionados al ocultar
            if (selectProducto) selectProducto.value = '';
            if (selectServicio) selectServicio.value = '';
            if (selectActivo) selectActivo.value = '';

            if (tipo === 'PRODUCTO') {
                if (wrapperProducto) wrapperProducto.classList.remove('d-none');
                await cargarProductos(form);
            } else if (tipo === 'SERVICIO') {
                if (wrapperServicio) wrapperServicio.classList.remove('d-none');
                await cargarServicios(form);
            } else if (tipo === 'ACTIVO_FIJO') {
                if (wrapperActivo) wrapperActivo.classList.remove('d-none');
                await cargarActivos(form);
            }
        });

        // Lógica de detección de valores preexistentes (Modo Edición)
        const valProd = selectProducto?.dataset.selected;
        const valServ = selectServicio?.dataset.selected;
        const valAct = selectActivo?.dataset.selected;

        const isValid = (val) => val && val !== 'None' && val !== 'null' && val !== 'undefined' && val.trim() !== '';

        if (isValid(valProd)) {
            tipoRelacionSelect.value = 'PRODUCTO';
            if (wrapperProducto) wrapperProducto.classList.remove('d-none');
            cargarProductos(form);
        } else if (isValid(valServ)) {
            tipoRelacionSelect.value = 'SERVICIO';
            if (wrapperServicio) wrapperServicio.classList.remove('d-none');
            cargarServicios(form);
        } else if (isValid(valAct)) {
            tipoRelacionSelect.value = 'ACTIVO_FIJO';
            if (wrapperActivo) wrapperActivo.classList.remove('d-none');
            cargarActivos(form);
        } else {
            tipoRelacionSelect.value = 'NINGUNO';
            ocultarTodos();
        }
    }

    // Exportar
    window.Sintel.Gastos.Editor = { init, cargarResoluciones, calcularTotales, initInventarioSelects, cargarProductos, cargarServicios, cargarActivos };

    // Inicialización HTMX
    document.body.addEventListener('htmx:afterSettle', (evt) => {
        const form = evt.detail.target.querySelector('#gasto-form') || (evt.detail.target.id === 'gasto-form' ? evt.detail.target : null);
        if (form) init(form);
    });

})();
