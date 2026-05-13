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

        // Eventos de cálculo
        const calcFields = ['#subtotal', '#retefuente_porcentaje', '#reteica_porcentaje'];
        calcFields.forEach(selector => {
            const el = form.querySelector(selector);
            if (el) {
                el.addEventListener('input', () => calcularTotales(form));
                el.addEventListener('change', () => calcularTotales(form));
            }
        });

        // Cambio de proveedor
        form.querySelector('#proveedor_uuid')?.addEventListener('change', (e) => {
            actualizarInfoProveedor(form, e.target.value);
            calcularTotales(form);
        });

        // Submit
        form.addEventListener('submit', handleSubmit);

        // Inicializar cálculos si ya hay datos (Edición)
        calcularTotales(form);
    }

    /**
     * Carga las resoluciones DIAN en el select.
     */
    async function cargarResoluciones(form) {
        const select = form.querySelector('#resolucion');
        if (!select) return;

        const currentValue = select.dataset.value || select.value;

        try {
            const response = await fetch(window.Sintel.Gastos.API.resoluciones.list, {
                headers: window.Sintel.Gastos.getHeaders()
            });
            const result = await response.json();
            const resoluciones = Array.isArray(result) ? result : (result.results || []);

            select.innerHTML = '<option value="">Seleccione...</option>';
            resoluciones.forEach(res => {
                const opt = document.createElement('option');
                opt.value = res.id;
                opt.textContent = `${res.prefijo || ''} ${res.numero_resolucion}`;
                opt.selected = (res.id == currentValue);
                select.appendChild(opt);
            });

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

        const currentValue = select.dataset.value || select.value;

        try {
            const response = await fetch(window.Sintel.Gastos.API.proveedores.list, {
                headers: window.Sintel.Gastos.getHeaders()
            });
            const result = await response.json();
            _proveedoresCache = Array.isArray(result) ? result : (result.results || []);

            select.innerHTML = '<option value="">Seleccione...</option>';
            _proveedoresCache.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.razon_social;
                opt.selected = (p.id == currentValue);
                select.appendChild(opt);
            });
            
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
    }

    function calcularTotales(form) {
        const subtotal = parseFloat(form.querySelector('#subtotal')?.value) || 0;
        const rfPorc = parseFloat(form.querySelector('#retefuente_porcentaje')?.value) || 0;
        const riPorc = parseFloat(form.querySelector('#reteica_porcentaje')?.value) || 0;

        // En el HTML los valores ya son decimales (0.04, 0.0069), no dividir por 100
        const rfVal = subtotal * rfPorc;
        const riVal = subtotal * riPorc;
        const total = subtotal - rfVal - riVal;

        const totalInput = form.querySelector('#total');
        if (totalInput) totalInput.value = total.toFixed(2);

        const totalDisplay = form.querySelector('#total_display');
        if (totalDisplay) {
            totalDisplay.textContent = `$${total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }

        const preview = form.querySelector('#calculo-preview');
        if (preview) {
            preview.innerHTML = `Subtotal: <strong>$${subtotal.toLocaleString()}</strong> | Retenciones: <span class="text-danger">-$${(rfVal + riVal).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>`;
        }
    }

    /**
     * Recolección Zero Trust de datos (v3.7.1 - Integración Contable §18).
     */
    function collectData(form) {
        const gastoUuidVal = form.querySelector('#cuenta_gasto_uuid')?.value;
        const contraUuidVal = form.querySelector('#cuenta_contrapartida_uuid')?.value;

        return {
            descripcion: form.querySelector('#descripcion')?.value,
            documento_soporte: {
                resolucion: form.querySelector('#resolucion')?.value,
                fecha: form.querySelector('#fecha')?.value,
                proveedor: form.querySelector('#proveedor_uuid')?.value,
                numero_documento_proveedor: form.querySelector('#numero_documento_proveedor')?.value,
                categoria_contable: form.querySelector('#categoria_contable')?.value,
                observaciones: form.querySelector('#observaciones')?.value,
                subtotal: parseFloat(form.querySelector('#subtotal')?.value) || 0,
                retefuente_porcentaje: parseFloat(form.querySelector('#retefuente_porcentaje')?.value) || 0,
                reteica_porcentaje: parseFloat(form.querySelector('#reteica_porcentaje')?.value) || 0,
                total: parseFloat(form.querySelector('#total')?.value) || 0,
                cuenta_gasto_uuid: gastoUuidVal || null,
                cuenta_contrapartida_uuid: contraUuidVal || null
            }
        };
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
            console.error('[GastoEditor] Error:', error);
            if (error.data) {
                window.UIManager?.handleError(error.data);
            } else {
                window.UIManager?.notifyError('Error al procesar la solicitud');
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = isEdit ? '<i class="bi bi-save me-2"></i>Guardar Cambios' : '<i class="bi bi-plus-circle me-2"></i>Crear Gasto';
            }
        }
    }

    // Exportar
    window.Sintel.Gastos.Editor = { init, cargarResoluciones, calcularTotales };

    // Inicialización HTMX
    document.body.addEventListener('htmx:afterSettle', (evt) => {
        const form = evt.detail.target.querySelector('#gasto-form') || (evt.detail.target.id === 'gasto-form' ? evt.detail.target : null);
        if (form) init(form);
    });

})();
