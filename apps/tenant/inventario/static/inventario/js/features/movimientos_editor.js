/**
 * Feature: Editor - Movimientos Universales de Inventario v3.9.1
 * Campos protegidos: nombre/precio del item son solo lectura.
 * Unica variable editable por usuario: Cantidad + Tipo de Movimiento.
 * El costo_unitario se toma automaticamente del item seleccionado.
 */
(function(w, d) {
    'use strict';

    const MOD = '[movimientos.editor.v391]';
    const ENDPOINTS = {
        MOVIMIENTO: '/api/v1/inventario/movimientos/',
        HISTORIAL_SERVICIO: '/api/v1/inventario/historial-servicios/',
        PRODUCTOS: '/api/v1/inventario/productos/',
        ACTIVOS: '/api/v1/inventario/activos/',
        SERVICIOS: '/api/v1/inventario/servicios/'
    };

    const SELECTORS = {
        FORM: '#form-movimiento',
        OFFCANVAS: '#offcanvas-movimientos',
        FEEDBACK: '#feedback-movimiento',
        CATEGORIA: '#categoria_origen',
        ITEM: '#item_seleccionado',
        TIPO_MOV: '#tipo_movimiento',
        CANTIDAD: '#movimiento-cantidad',
        COSTO: '#movimiento-costo',          // hidden input
        NOMBRE_REF: '#movimiento-nombre-ref', // readonly display
        PRECIO_REF: '#movimiento-precio-ref', // readonly display
        STOCK_REF: '#movimiento-stock-ref',   // readonly display
        STOCK_REF_CONTAINER: '#stock_ref_container',
        ORIGEN: '#movimiento-origen',
        OBS: '#movimiento-observaciones',
        CAMPOS_KARDEX: '#campos_kardex',
        CAMPOS_COMUNES: '#campos_comunes',
        BTN_GUARDAR: '#btn-guardar-movimiento',
        CANTIDAD_CONTAINER: '#cantidad_container',
        ITEM_HELP: '#item_help_text',
        PANEL_REF: '#panel_referencia_item'
    };

    const TIPOS_MOVIMIENTO = {
        PRODUCTO: [
            { value: 'ENTRADA_COMPRA', label: 'Compra' },
            { value: 'ENTRADA_AJUSTE', label: 'Ajuste (+)' },
            { value: 'ENTRADA_DEVOLUCION', label: 'Devolucion Cliente' },
            { value: 'SALIDA_VENTA', label: 'Venta' },
            { value: 'SALIDA_BAJA', label: 'Baja / Deterioro' },
            { value: 'SALIDA_CONSUMO', label: 'Consumo Interno' }
        ],
        ACTIVO_FIJO: [
            { value: 'ASIGNACION_RESPONSABLE', label: 'Asignacion de Responsable' },
            { value: 'TRASLADO_MANTENIMIENTO', label: 'Traslado a Mantenimiento' },
            { value: 'RETORNO_MANTENIMIENTO', label: 'Retorno de Mantenimiento' },
            { value: 'SALIDA_BAJA_ACTIVO', label: 'Baja de Activo' }
        ]
    };

    let estadoFormulario = { categoriaActual: null, itemSeleccionado: null };
    let itemsCargadosBuffer = [];

    // =========================================================================
    // 1. MUTACION DEL DOM
    // =========================================================================

    function mutatUIParaCategoria(categoria) {
        const kardex = d.querySelector(SELECTORS.CAMPOS_KARDEX);
        const comunes = d.querySelector(SELECTORS.CAMPOS_COMUNES);
        const cantContainer = d.querySelector(SELECTORS.CANTIDAD_CONTAINER);

        if (kardex) kardex.classList.add('d-none');
        if (comunes) comunes.classList.add('d-none');
        if (cantContainer) cantContainer.classList.add('d-none');

        if (!categoria) return;

        if (comunes) comunes.classList.remove('d-none');

        if (categoria === 'PRODUCTO' || categoria === 'ACTIVO_FIJO') {
            if (kardex) kardex.classList.remove('d-none');
            if (categoria === 'PRODUCTO' && cantContainer) {
                cantContainer.classList.remove('d-none');
            }
        }
    }

    function rellenarTiposMovimiento(categoria) {
        const select = d.querySelector(SELECTORS.TIPO_MOV);
        if (!select) return;
        select.innerHTML = '<option value="">— Seleccionar —</option>';
        select.disabled = true;
        const tipos = TIPOS_MOVIMIENTO[categoria] || [];
        tipos.forEach(t => {
            const opt = d.createElement('option');
            opt.value = t.value;
            opt.textContent = t.label;
            select.appendChild(opt);
        });
        if (tipos.length > 0) select.disabled = false;
    }

    function limpiarPanelReferencia() {
        const panel = d.querySelector(SELECTORS.PANEL_REF);
        if (panel) panel.classList.add('d-none');
        const nombreRef = d.querySelector(SELECTORS.NOMBRE_REF);
        const precioRef = d.querySelector(SELECTORS.PRECIO_REF);
        const stockRef = d.querySelector(SELECTORS.STOCK_REF);
        if (nombreRef) nombreRef.value = '';
        if (precioRef) precioRef.value = '';
        if (stockRef) stockRef.value = '';
        const costoHidden = d.querySelector(SELECTORS.COSTO);
        if (costoHidden) costoHidden.value = '0';
    }

    // =========================================================================
    // 2. AUTO-LLENADO DE REFERENCIA (Campos protegidos)
    // =========================================================================

    /**
     * Actualiza el costo unitario oculto segun el tipo de movimiento.
     * Se llama tambien cuando cambia el tipo (ENTRADA vs SALIDA).
     */
    function actualizarCostoPorTipo(item, categoria) {
        const inputCosto = d.querySelector(SELECTORS.COSTO);
        if (!inputCosto || !item || categoria !== 'PRODUCTO') return;
        const tipo = d.querySelector(SELECTORS.TIPO_MOV)?.value || '';
        const esEntrada = tipo.startsWith('ENTRADA');
        const precio = parseFloat(item.precio_venta || 0);
        const costo = parseFloat(item.costo_promedio || 0);
        inputCosto.value = (esEntrada ? costo : precio).toFixed(2);
    }

    /**
     * Rellena los campos de referencia (solo lectura) con los datos del item.
     * Tambien inyecta el costo_unitario en el input oculto.
     */
    function autoRellenarPorItem(item, categoria) {
        const panel = d.querySelector(SELECTORS.PANEL_REF);
        const nombreRef = d.querySelector(SELECTORS.NOMBRE_REF);
        const precioRef = d.querySelector(SELECTORS.PRECIO_REF);
        const stockRef = d.querySelector(SELECTORS.STOCK_REF);
        const stockContainer = d.querySelector(SELECTORS.STOCK_REF_CONTAINER);
        const inputCosto = d.querySelector(SELECTORS.COSTO);

        if (!item || !panel) return;
        panel.classList.remove('d-none');
        if (nombreRef) nombreRef.value = item.nombre || '';

        if (categoria === 'PRODUCTO') {
            const unidad = item.unidad || 'UND';
            const stock = parseFloat(item.stock_actual || 0).toFixed(3);
            const precio = parseFloat(item.precio_venta || 0).toFixed(2);
            const costoProm = parseFloat(item.costo_promedio || 0).toFixed(2);

            if (precioRef) precioRef.value = 'Precio Vta: $' + precio + ' | Costo Prom: $' + costoProm;
            if (stockRef) stockRef.value = 'Stock: ' + stock + ' ' + unidad;
            if (stockContainer) stockContainer.classList.remove('d-none');

            // Costo segun tipo de movimiento actual
            actualizarCostoPorTipo(item, categoria);

        } else if (categoria === 'SERVICIO') {
            const precio = parseFloat(item.precio_venta || 0).toFixed(2);
            if (precioRef) precioRef.value = 'Precio Servicio: $' + precio;
            if (stockRef) stockRef.value = '';
            if (stockContainer) stockContainer.classList.add('d-none');
            if (inputCosto) inputCosto.value = precio;

        } else if (categoria === 'ACTIVO_FIJO') {
            const costoAdq = parseFloat(item.costo_adquisicion || 0).toFixed(2);
            if (precioRef) precioRef.value = 'Costo Adquisicion: $' + costoAdq;
            if (stockRef) stockRef.value = '';
            if (stockContainer) stockContainer.classList.add('d-none');
            if (inputCosto) inputCosto.value = '0.00';
        }
    }

    // =========================================================================
    // 3. VALIDACION Y FETCH
    // =========================================================================

    function validarYHabilitarGuardar() {
        const categoria = d.querySelector(SELECTORS.CATEGORIA)?.value || '';
        const item = d.querySelector(SELECTORS.ITEM)?.value || '';
        const tipo = d.querySelector(SELECTORS.TIPO_MOV)?.value || '';
        const cantidad = parseFloat(d.querySelector(SELECTORS.CANTIDAD)?.value || 0);
        const btn = d.querySelector(SELECTORS.BTN_GUARDAR);

        let esValido = false;
        if (categoria && item) {
            if (categoria === 'SERVICIO') {
                esValido = true;
            } else if (categoria === 'ACTIVO_FIJO' && tipo) {
                esValido = true;
            } else if (tipo && cantidad > 0) {
                esValido = true;
            }
        }
        if (btn) btn.disabled = !esValido;
    }

    async function cargarItemsPorCategoria(categoria) {
        const itemSelect = d.querySelector(SELECTORS.ITEM);
        if (!itemSelect) return;

        itemSelect.disabled = true;
        itemSelect.innerHTML = '<option value="">Cargando...</option>';

        const endpointMap = {
            PRODUCTO: ENDPOINTS.PRODUCTOS,
            ACTIVO_FIJO: ENDPOINTS.ACTIVOS,
            SERVICIO: ENDPOINTS.SERVICIOS
        };
        const endpoint = endpointMap[categoria];
        if (!endpoint) return;

        try {
            if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
                mostrarError('HTTP client no disponible');
                return;
            }
            const res = await w.Sintel.Core.Http.request('GET', endpoint);
            if (!res.ok || !res.data) {
                mostrarError('Error al cargar ' + categoria);
                itemSelect.innerHTML = '<option value="">Error al cargar items</option>';
                return;
            }
            const items = Array.isArray(res.data) ? res.data : (res.data.results || []);
            itemsCargadosBuffer = items;

            itemSelect.innerHTML = '<option value="">— Seleccionar —</option>';
            items.forEach(item => {
                const opt = d.createElement('option');
                opt.value = item.id || item.uuid;
                const cod = item.codigo || '';
                opt.textContent = cod ? '[' + cod + '] ' + (item.nombre || '') : (item.nombre || 'Sin nombre');
                itemSelect.appendChild(opt);
            });
            itemSelect.disabled = false;

            const help = d.querySelector(SELECTORS.ITEM_HELP);
            if (help) help.textContent = items.length + ' ' + categoria.toLowerCase() + ' disponible(s)';
        } catch (err) {
            console.error(MOD, 'Error cargando items:', err);
            mostrarError('Error al cargar ' + categoria);
            itemSelect.innerHTML = '<option value="">Error al cargar</option>';
        }
    }

    // =========================================================================
    // 4. CONSTRUCCION DE PAYLOAD
    // =========================================================================

    function recolectarYConstructorPayload() {
        const categoria = d.querySelector(SELECTORS.CATEGORIA)?.value || '';
        const itemId = d.querySelector(SELECTORS.ITEM)?.value;
        const tipo = d.querySelector(SELECTORS.TIPO_MOV)?.value || '';
        const cantidad = parseFloat(d.querySelector(SELECTORS.CANTIDAD)?.value || 1);
        const costo = parseFloat(d.querySelector(SELECTORS.COSTO)?.value || 0);  // desde hidden
        const origen = d.querySelector(SELECTORS.ORIGEN)?.value?.trim() || '';
        const obs = d.querySelector(SELECTORS.OBS)?.value?.trim() || '';

        // Recopilar factura links (si existen)
        const facturaUuidInput = d.getElementById('movimiento-factura-uuid');
        const facturaNumeroInput = d.getElementById('movimiento-factura-numero');
        const facturaUuid = facturaUuidInput?.value?.trim() || null;
        const facturaNumero = facturaNumeroInput?.value?.trim() || null;

        if (!categoria || !itemId) {
            mostrarError('Debe seleccionar categoria e item');
            return null;
        }
        if (categoria === 'PRODUCTO' && (!tipo || cantidad <= 0)) {
            mostrarError('Debe seleccionar tipo y cantidad valida');
            return null;
        }
        if (categoria === 'ACTIVO_FIJO' && !tipo) {
            mostrarError('Debe seleccionar el tipo de movimiento');
            return null;
        }

        const base = {
            origen_referencia: origen,
            observaciones: obs,
            cliente_referencia: '',
            factura_uuid: facturaUuid,
            factura_numero: facturaNumero
        };

        if (categoria === 'PRODUCTO') {
            return {
                endpoint: ENDPOINTS.MOVIMIENTO,
                payload: { ...base, producto: itemId, tipo, cantidad, costo_unitario: costo }
            };
        }
        if (categoria === 'ACTIVO_FIJO') {
            return {
                endpoint: ENDPOINTS.MOVIMIENTO,
                payload: { ...base, activo_fijo: itemId, tipo, cantidad: 1, costo_unitario: 0 }
            };
        }
        if (categoria === 'SERVICIO') {
            return {
                endpoint: ENDPOINTS.HISTORIAL_SERVICIO,
                payload: {
                    ...base, servicio: itemId, cantidad,
                    valor_cobrado: costo,
                    fecha_registro: new Date().toISOString().split('T')[0]
                }
            };
        }
        return null;
    }

    // =========================================================================
    // 5. FEEDBACK UI
    // =========================================================================

    function mostrarError(mensaje) {
        const el = d.querySelector(SELECTORS.FEEDBACK);
        if (el) {
            el.className = 'alert alert-danger';
            el.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-2"></i>' + mensaje;
            el.classList.remove('d-none');
        }
    }
    function ocultarError() {
        const el = d.querySelector(SELECTORS.FEEDBACK);
        if (el) { el.classList.add('d-none'); el.innerHTML = ''; }
    }
    function cerrarOffcanvas() {
        const el = d.querySelector(SELECTORS.OFFCANVAS);
        if (el && w.bootstrap?.Offcanvas) {
            const inst = w.bootstrap.Offcanvas.getInstance(el);
            if (inst) inst.hide();
        }
    }

    // =========================================================================
    // 6. GUARDAR (CREAR o EDITAR)
    // =========================================================================

    async function guardarMovimiento(e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        ocultarError();

        const movimientoUuid = (d.getElementById('movimiento-uuid')?.value || '').trim();
        const modoEdicion = Boolean(movimientoUuid);

        const resultado = recolectarYConstructorPayload();
        if (!resultado) return;

        const { endpoint, payload } = resultado;
        const btn = d.querySelector(SELECTORS.BTN_GUARDAR);
        const btnOriginal = btn?.innerHTML || '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Guardando...'; }

        try {
            if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
                mostrarError('HTTP client no disponible');
                return;
            }
            let res;
            if (modoEdicion) {
                // T-9: delega a la SSoT de endpoints (inventario.api.js).
                res = await w.Sintel.Inventario.API.movimientos.update(movimientoUuid, {
                    tipo: payload.tipo,
                    cantidad: payload.cantidad,
                    costo_unitario: payload.costo_unitario,
                    origen_referencia: payload.origen_referencia,
                    observaciones: payload.observaciones,
                    factura_uuid: payload.factura_uuid,
                    factura_numero: payload.factura_numero
                });
            } else {
                res = await w.Sintel.Core.Http.request('POST', endpoint, payload);
            }

            if (btn) { btn.disabled = false; btn.innerHTML = btnOriginal; }

            if (!res.ok) {
                const msg = res.data?.detail || res.data?.message
                    || (res.data && JSON.stringify(res.data)) || 'Error al guardar';
                mostrarError(msg);
                return;
            }

            w.SintelFeedback?.success?.(modoEdicion ? 'Movimiento actualizado.' : 'Movimiento registrado.');
            cerrarOffcanvas();
            w.MovimientosList?.recargar?.();

        } catch (err) {
            console.error(MOD, 'Error:', err);
            mostrarError('Error inesperado');
            if (btn) { btn.disabled = false; btn.innerHTML = btnOriginal; }
        }
    }

    // =========================================================================
    // 7. LISTENERS
    // =========================================================================

    function attachListeners() {
        const form = d.querySelector(SELECTORS.FORM);
        if (!form) return;

        // Guard (FE-A1): w.MovimientosEditor.init() se expone para invocarse
        // externamente por cada apertura del offcanvas — este guard evita
        // duplicar listeners si algun caller lo invoca mas de una vez.
        if (form.dataset.editorInitialized) return;
        form.dataset.editorInitialized = 'true';

        // Cambio de categoria → fetch dinamico
        const catSelect = d.querySelector(SELECTORS.CATEGORIA);
        if (catSelect) {
            catSelect.addEventListener('change', function() {
                const cat = this.value;
                estadoFormulario.categoriaActual = cat;
                mutatUIParaCategoria(cat);
                if (cat) rellenarTiposMovimiento(cat);
                limpiarPanelReferencia();
                itemsCargadosBuffer = [];
                if (cat) {
                    cargarItemsPorCategoria(cat);
                } else {
                    const itSel = d.querySelector(SELECTORS.ITEM);
                    if (itSel) {
                        itSel.disabled = true;
                        itSel.innerHTML = '<option value="">— Seleccione una categoria primero —</option>';
                    }
                }
                ocultarError();
                validarYHabilitarGuardar();
            });
        }

        // Cambio de item → auto-relleno de referencia
        const itSel = d.querySelector(SELECTORS.ITEM);
        if (itSel) {
            itSel.addEventListener('change', function() {
                const itemId = this.value;
                estadoFormulario.itemSeleccionado = itemId;
                if (!itemId) {
                    limpiarPanelReferencia();
                } else {
                    const found = itemsCargadosBuffer.find(i => i.id === itemId || i.uuid === itemId);
                    if (found) autoRellenarPorItem(found, estadoFormulario.categoriaActual);
                }
                validarYHabilitarGuardar();
            });
        }

        // Cambio de tipo → actualiza costo segun ENTRADA/SALIDA (solo en modo crear)
        const tipoSel = d.querySelector(SELECTORS.TIPO_MOV);
        if (tipoSel) {
            tipoSel.addEventListener('change', function() {
                const modoEdicion = Boolean((d.getElementById('movimiento-uuid')?.value || '').trim());
                if (!modoEdicion && estadoFormulario.categoriaActual === 'PRODUCTO') {
                    const itemId = d.querySelector(SELECTORS.ITEM)?.value;
                    const found = itemsCargadosBuffer.find(i => i.id === itemId || i.uuid === itemId);
                    if (found) actualizarCostoPorTipo(found, 'PRODUCTO');
                }
                validarYHabilitarGuardar();
            });
        }

        // Cantidad y otros campos → validar
        [SELECTORS.CANTIDAD, SELECTORS.ORIGEN, SELECTORS.OBS].forEach(sel => {
            const el = d.querySelector(sel);
            if (el) {
                el.addEventListener('change', validarYHabilitarGuardar);
                el.addEventListener('input', validarYHabilitarGuardar);
            }
        });

        // Prevenir submit nativo
        form.addEventListener('submit', function(e) { e.preventDefault(); });

        // Unico punto de entrada del boton guardar
        const btn = d.querySelector(SELECTORS.BTN_GUARDAR);
        if (btn) btn.addEventListener('click', guardarMovimiento);
    }

    // =========================================================================
    // 8. MODO EDICION — Pre-relleno completo
    // =========================================================================

    async function preRellenarModoEdicion() {
        const dataInput = d.getElementById('movimiento-data-json');
        if (!dataInput || !dataInput.value) return;

        let datos;
        try { datos = JSON.parse(dataInput.value); } catch (_) { return; }
        if (!datos || !datos.item_tipo) return;

        // 1. Activar y bloquear categoria
        const catSel = d.querySelector(SELECTORS.CATEGORIA);
        if (catSel) {
            catSel.value = datos.item_tipo;
            mutatUIParaCategoria(datos.item_tipo);
            rellenarTiposMovimiento(datos.item_tipo);
        }
        estadoFormulario.categoriaActual = datos.item_tipo;

        // 2. Cargar items y poblar buffer
        await cargarItemsPorCategoria(datos.item_tipo);

        // 3. Bloquear selector de item (no se puede cambiar en edicion)
        const itSel = d.querySelector(SELECTORS.ITEM);
        if (itSel && datos.item_uuid) {
            itSel.value = datos.item_uuid;
            itSel.disabled = true;  // item fijo en edicion
            estadoFormulario.itemSeleccionado = datos.item_uuid;

            const found = itemsCargadosBuffer.find(i => i.id === datos.item_uuid || i.uuid === datos.item_uuid);
            if (found) autoRellenarPorItem(found, datos.item_tipo);
        }

        // 4. Pre-seleccionar tipo
        const tipoSel = d.querySelector(SELECTORS.TIPO_MOV);
        if (tipoSel && datos.tipo) {
            tipoSel.value = datos.tipo;
            tipoSel.disabled = false;
        }

        // 5. Pre-rellenar campos editables
        const cantInput = d.querySelector(SELECTORS.CANTIDAD);
        const costoHidden = d.querySelector(SELECTORS.COSTO);
        const origenInput = d.querySelector(SELECTORS.ORIGEN);
        const obsInput = d.querySelector(SELECTORS.OBS);

        if (cantInput && datos.cantidad) cantInput.value = datos.cantidad;
        // En edicion, el costo almacenado tiene precedencia sobre el calculado del item
        if (costoHidden && datos.costo_unitario) costoHidden.value = datos.costo_unitario;
        if (origenInput && datos.origen_referencia) origenInput.value = datos.origen_referencia;
        if (obsInput && datos.observaciones) obsInput.value = datos.observaciones;

        validarYHabilitarGuardar();
    }

    // =========================================================================
    // 9. INICIALIZACION
    // =========================================================================

    function init() {
        attachListeners();
        ocultarError();

        const form = d.querySelector(SELECTORS.FORM);
        if (form) form.reset();

        mutatUIParaCategoria(null);
        limpiarPanelReferencia();
        itemsCargadosBuffer = [];

        const catSel = d.querySelector(SELECTORS.CATEGORIA);
        if (catSel) catSel.value = '';

        const itSel = d.querySelector(SELECTORS.ITEM);
        if (itSel) {
            itSel.disabled = true;
            itSel.innerHTML = '<option value="">— Seleccione una categoria primero —</option>';
        }

        validarYHabilitarGuardar();

        const dataInput = d.getElementById('movimiento-data-json');
        if (dataInput && dataInput.value) {
            setTimeout(preRellenarModoEdicion, 50);
        }
    }

    if (!w.MovimientosEditor) {
        w.MovimientosEditor = {
            init,
            guardar: guardarMovimiento,
            abrir: function() {
                const el = d.querySelector(SELECTORS.OFFCANVAS);
                if (el) {
                    w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
                }
            },
            cerrar: cerrarOffcanvas
        };
    }

})(window, document);
