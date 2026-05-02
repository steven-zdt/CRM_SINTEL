/**
 * Gasto Editor Module - Formulario de Gasto
 * 
 * Namespace: window.Sintel.Gastos.GastoEditor
 * Version: v2.61.8
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Gastos = window.Sintel.Gastos || {};

    function init(formSelector) {
        const form = document.querySelector(formSelector);
        if (!form) {
            console.error('[GastoEditor] Formulario no encontrado:', formSelector);
            return;
        }

        // Calcular retenciones en tiempo real
        const inputs = form.querySelectorAll('[name="subtotal"], [name="retefuente_porcentaje"], [name="reteica_porcentaje"]');
        inputs.forEach(input => {
            input.addEventListener('change', calcularTotal);
            input.addEventListener('input', calcularTotal);
        });

        form.addEventListener('submit', handleSubmit);
        document.body.addEventListener('htmx:afterRequest', handleAfterRequest);

        // Cargar selects dinamicos (delegado a Gastos.Utils con cache 5min)
        cargarProveedores();
        cargarCuentasContables();
    }

    function calcularTotal() {
        const form = document.querySelector('#gasto-form');
        if (!form) return;

        const subtotal = parseFloat(form.querySelector('[name="subtotal"]')?.value) || 0;
        const retefuentePct = parseFloat(form.querySelector('[name="retefuente_porcentaje"]')?.value) || 0;
        const reteicaPct = parseFloat(form.querySelector('[name="reteica_porcentaje"]')?.value) || 0;

        // Convertir porcentajes
        const retefuente = subtotal * (retefuentePct / 100);
        const reteica = subtotal * (reteicaPct / 100);
        const total = subtotal - retefuente - reteica;

        const totalInput = form.querySelector('[name="total_neto"]');
        if (totalInput) {
            totalInput.value = total.toFixed(2);
        }

        const preview = form.querySelector('#calculo-preview');
        if (preview) {
            preview.innerHTML = `
                Subtotal: $${subtotal.toFixed(2)}<br>
                ReteFuente (${retefuentePct}%): -$${retefuente.toFixed(2)}<br>
                ReteICA (${reteicaPct}%): -$${reteica.toFixed(2)}<br>
                <strong>Total: $${total.toFixed(2)}</strong>
            `;
        }
    }

    function cargarProveedores() {
        window.Sintel.Gastos.Utils.loadProveedoresSelect('[name="proveedor_uuid"]');
    }

    function cargarCuentasContables() {
        window.Sintel.Gastos.Utils.loadCuentasSelect('[name="cuenta_contable_uuid"]');
    }

    function handleSubmit(e) {
        const form = e.target;
        const subtotal = parseFloat(form.querySelector('[name="subtotal"]')?.value) || 0;

        if (subtotal <= 0) {
            e.preventDefault();
            window.UIManager?.notifyError('El subtotal debe ser mayor a 0');
            return false;
        }

        return true;
    }

    function handleAfterRequest(evt) {
        if (!evt.detail.successful) {
            try {
                const response = JSON.parse(evt.detail.xhr.response);
                window.UIManager?.handleError({
                    error: response.error || 'Error al guardar gasto',
                    detail: response.detail
                });
            } catch (e) {
                window.UIManager?.notifyError('Error inesperado');
            }
            return;
        }

        try {
            const response = JSON.parse(evt.detail.xhr.response);
            
            const offcanvas = document.querySelector('#gastoOffcanvas');
            if (offcanvas && bootstrap?.Offcanvas) {
                bootstrap.Offcanvas.getInstance(offcanvas)?.hide();
            }

            window.UIManager?.notifySuccess(response.message || 'Gasto registrado correctamente');
            window.Sintel.Gastos.GastoList?.reload();
            window.Sintel.Gastos.GastoList?.loadSummary('#gastos-summary');
        } catch (e) {
            console.error('[GastoEditor] Error procesando respuesta:', e);
        }
    }

    window.Sintel.Gastos.GastoEditor = {
        init,
        calcularTotal
    };

})();
