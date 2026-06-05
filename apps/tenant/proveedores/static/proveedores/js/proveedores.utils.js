/**
 * proveedores.utils.js - Helpers y utilidades para el módulo de proveedores.
 * [ARCHITECTURE v3.5]
 * - Centralización de lógica de búsqueda y autocompletado.
 */
(function (w) {
    'use strict';

    const proveedoresUtils = {};

    w.AppProveedor = w.AppProveedor || {};
    w.AppProveedor.Utils = proveedoresUtils;

    // Backwards compatibility wrapper
    w.Sintel = w.Sintel || {};
    w.Sintel.Proveedores = w.Sintel.Proveedores || {};
    w.Sintel.Proveedores.Utils = w.AppProveedor.Utils;

})(window);
