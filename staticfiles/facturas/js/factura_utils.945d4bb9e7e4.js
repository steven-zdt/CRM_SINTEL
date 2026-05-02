/**
 * facturas.utils.js - Utilidades puras del modulo Facturas
 * SINTEL v2.61.5 - JS-SINTEL Standard
 *
 * Unica fuente de verdad para formatters, badges y helpers de validacion.
 * Funciones puras: sin efectos secundarios, sin llamadas HTTP, sin acceso al DOM.
 *
 * Exporta: window.Sintel.Factura.utils
 * Dependencias: ninguna
 */

(function (w) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Factura = w.Sintel.Factura || {};

    /**
     * Formatea un valor numerico como moneda colombiana (o la indicada).
     * @param {number|string} value
     * @param {string} [currency='COP']
     * @returns {string}
     */
    function formatearMoneda(value, currency) {
        currency = currency || 'COP';
        if (value === null || value === undefined || value === '') return '$ 0,00';
        var num = parseFloat(value);
        if (isNaN(num)) return '$ 0,00';
        return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }).format(num);
    }

    /**
     * Formatea una fecha ISO como dd/mm/yyyy.
     * @param {string} value - Fecha en formato ISO o compatible con Date()
     * @returns {string}
     */
    function formatearFecha(value) {
        if (!value) return '---';
        try {
            var date = new Date(value);
            return date.toLocaleDateString('es-CO', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        } catch (e) {
            return value;
        }
    }

    /**
     * Formatea una fecha ISO como dd/mm/yyyy HH:mm.
     * @param {string} value
     * @returns {string}
     */
    function formatearFechaHora(value) {
        if (!value) return '---';
        try {
            var date = new Date(value);
            return date.toLocaleDateString('es-CO', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return value;
        }
    }

    /**
     * Escapa caracteres HTML para prevenir XSS.
     * @param {string} text
     * @returns {string}
     */
    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    /**
     * Renderiza un badge Bootstrap para la naturaleza de la factura.
     * @param {string} val - 'VENTA' o 'COMPRA'
     * @returns {string} HTML del badge
     */
    function badgeNaturaleza(val) {
        if (!val) return '<span class="badge bg-secondary">---</span>';
        var color = val === 'VENTA' ? 'success' : 'info';
        return '<span class="badge bg-' + color + '">' + escapeHtml(val) + '</span>';
    }

    /**
     * Renderiza un badge Bootstrap para el estado de la factura.
     * @param {string} estado
     * @returns {string} HTML del badge
     */
    function badgeEstado(estado) {
        var map = {
            'BORRADOR': 'bg-secondary',
            'ENVIADA': 'bg-primary',
            'ACEPTADA': 'bg-success',
            'RECHAZADA': 'bg-danger',
            'ANULADA': 'bg-dark'
        };
        var cls = map[estado] || 'bg-secondary';
        return '<span class="badge ' + cls + '">' + escapeHtml(estado || 'N/A') + '</span>';
    }

    /**
     * Trunca un hash largo (CUFE/CUDE) para visualizacion en tabla.
     * @param {string} hash
     * @returns {string}
     */
    function shortHash(hash) {
        if (!hash) return '';
        return hash.length > 32 ? hash.slice(0, 12) + '...' + hash.slice(-12) : hash;
    }

    /**
     * Valida y retorna un ID entero positivo o null.
     * Proteccion IDOR: verificar que el ID sea un entero finito positivo antes de enviar.
     * @param {any} rawId
     * @returns {number|null}
     */
    function validarId(rawId) {
        var id = parseInt(rawId, 10);
        if (!id || id <= 0 || !Number.isFinite(id)) return null;
        return id;
    }

    /**
     * Determina el estado de pago de una factura a partir de sus datos.
     * @param {Object} rowData
     * @returns {{texto: string, clase: string}}
     */
    function determinarEstadoPago(rowData) {
        var estado = rowData.estado || '';
        var fechaVencimiento = rowData.fecha_vencimiento;
        var hoy = new Date();
        hoy.setHours(0, 0, 0, 0);

        if (estado === 'ACEPTADA') return { texto: 'Pagada', clase: 'bg-success' };
        if (estado === 'RECHAZADA') return { texto: 'Rechazada', clase: 'bg-danger' };
        if (estado === 'ANULADA') return { texto: 'Anulada', clase: 'bg-danger' };
        if (estado === 'BORRADOR') return { texto: 'Borrador', clase: 'bg-secondary' };

        if (estado === 'ENVIADA' && fechaVencimiento) {
            var fechaVen = new Date(fechaVencimiento);
            fechaVen.setHours(0, 0, 0, 0);
            if (fechaVen < hoy) return { texto: 'Vencida', clase: 'bg-warning' };
        }
        return { texto: 'Pendiente', clase: 'bg-warning' };
    }

    // -- Exportar --
    w.Sintel.Factura.utils = {
        formatearMoneda: formatearMoneda,
        formatearFecha: formatearFecha,
        formatearFechaHora: formatearFechaHora,
        escapeHtml: escapeHtml,
        badgeNaturaleza: badgeNaturaleza,
        badgeEstado: badgeEstado,
        shortHash: shortHash,
        validarId: validarId,
        determinarEstadoPago: determinarEstadoPago
    };

})(window);
