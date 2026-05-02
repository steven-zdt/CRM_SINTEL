/**
 * facturas.main.js - Orquestador central (FacturaController) del modulo Facturas
 * SINTEL v2.61.5 - JS-SINTEL Standard
 *
 * Responsabilidades:
 * - Inyectar y coordinar los sub-modulos: utils, api, table, ui, sync
 * - Exponer las acciones publicas del CRUD: ver, subirNueva, eliminar, guardar, recargar
 * - Montar event listeners del toolbar y delegar a sub-modulos
 * - Escuchar 'sintel:facturas:sincronizado' y refrescar la tabla
 * - Gestionar el resumen de ventas/compras en el DOM
 *
 * Expone: window.Sintel.Facturas (root namespace + FacturaController)
 *         window.AppFacturas (alias de compatibilidad para onclick heredados en templates)
 * Dependencias: todos los otros facturas.*.js, cargados antes en el template
 */

(function (w, d) {
    'use strict';

    var MOD = '[facturas.main]';

    w.Sintel = w.Sintel || {};
    // Preservar namespaces ya creados por los otros modulos
    var _prev = w.Sintel.Factura || {};

    var FacturaController = {

        // -------------------------------------------------------
        // Inicializacion
        // -------------------------------------------------------

        /**
         * Inicializa el modulo: tabla, listeners de toolbar, HTMX y eventos personalizados.
         * Debe llamarse una vez por DOMContentLoaded o htmx:load.
         */
        init: function () {
            console.log(MOD + ':init inicio');

            // Montar sub-modulos
            this.utils = _prev.utils || w.Sintel.Factura.utils || {};
            this.api   = _prev.api   || w.Sintel.Factura.api   || {};
            this.table = _prev.table || w.Sintel.Factura.table || {};
            this.ui    = _prev.ui    || w.Sintel.Factura.ui    || {};
            this.sync  = _prev.sync  || w.Sintel.Factura.sync  || {};

            // Inicializar Tabulator
            if (typeof this.table.init === 'function') {
                this.table.init();
            }

            // Registrar listener HX-Trigger: listaFacturasChanged (reactivo sin polling)
            if (typeof this.table.initHXTrigger === 'function') {
                this.table.initHXTrigger();
            }

            // Inicializar event delegation de filas
            if (typeof this.table.initEventos === 'function') {
                this.table.initEventos();
            }
            if (typeof this.ui.initHTMX === 'function') {
                this.ui.initHTMX();
            }

            // Inicializar event delegation del offcanvas
            if (typeof this.ui.initEventosOffcanvas === 'function') {
                this.ui.initEventosOffcanvas();
            }

            // Toolbar: delegar eventos del panel de control
            this._initToolbar();

            // Escuchar evento de sincronizacion completada
            d.addEventListener('sintel:facturas:sincronizado', function () {
                FacturaController.recargar();
            });

            // Escuchar evento legacy de factura guardada
            d.addEventListener('facturaGuardada', function () {
                FacturaController.recargar();
            });

            // Cargar resumen inicial
            this.recargarResumen();

            console.log(MOD + ':init completado');
        },

        // -------------------------------------------------------
        // Acciones CRUD publicas
        // -------------------------------------------------------

        /**
         * Abre el offcanvas de detalle para la factura indicada.
         * Valida el ID antes de enviar (IDOR pre-check).
         * @param {number|string} rawId
         */
        ver: function (rawId) {
            var id = this.utils.validarId ? this.utils.validarId(rawId) : parseInt(rawId, 10);
            if (!id) {
                console.error(MOD + ':ver ID invalido:', rawId);
                return;
            }
            if (typeof this.ui.abrirDetalle === 'function') this.ui.abrirDetalle(id);
        },

        /**
         * Abre el offcanvas de carga/creacion de una nueva factura.
         */
        subirNueva: function () {
            if (typeof this.ui.abrirCrear === 'function') this.ui.abrirCrear();
        },

        /**
         * Elimina una factura previa confirmacion del usuario.
         * Validacion IDOR client-side: verifica que el ID sea un entero positivo.
         * @param {number|string} rawId
         */
        eliminar: async function (rawId) {
            var id = this.utils.validarId ? this.utils.validarId(rawId) : parseInt(rawId, 10);
            if (!id) {
                console.error(MOD + ':eliminar ID invalido:', rawId);
                return;
            }

            if (!confirm('Esta accion eliminara la factura permanentemente. No se puede deshacer.')) return;

            var res = await this.api.eliminar(id);
            if (!res.ok) {
                if (w.UIManager) w.UIManager.handleError(res, MOD);
                return;
            }

            if (w.SintelFeedback) w.SintelFeedback.success('Factura eliminada');
            this.recargar();
        },

        /**
         * Recolecta el payload del formulario activo y lo envia a la API (crear o actualizar).
         * Incluye DOM Shield y validacion de campos obligatorios.
         */
        guardar: async function () {
            if (typeof this.ui.limpiarFeedbackForm === 'function') this.ui.limpiarFeedbackForm();

            var payload = typeof this.ui.recolectarPayload === 'function' ? this.ui.recolectarPayload() : null;
            if (!payload) {
                console.error(MOD + ':guardar formulario no disponible');
                return;
            }

            // Determinar si es creacion o actualizacion
            var isEdicion = !!(payload.id);
            var facturaId = isEdicion ? (this.utils.validarId ? this.utils.validarId(payload.id) : parseInt(payload.id, 10)) : null;

            if (isEdicion && !facturaId) {
                console.error(MOD + ':guardar ID de edicion invalido:', payload.id);
                return;
            }

            var btn = d.querySelector('#btn-guardar-factura');
            if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...'; }

            var res;
            if (isEdicion) {
                res = await this.api.actualizar(facturaId, payload);
            } else {
                res = await this.api.crear(payload);
            }

            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-save me-2"></i>Guardar'; }

            if (!res.ok) {
                if (typeof this.ui.mostrarErroresForm === 'function') this.ui.mostrarErroresForm(res);
                return;
            }

            if (typeof this.ui.cerrar === 'function') this.ui.cerrar();
            if (w.SintelFeedback) w.SintelFeedback.success(isEdicion ? 'Factura actualizada' : 'Factura guardada');
            this.recargar();
        },

        /**
         * Refresca la tabla Tabulator y recarga el resumen de cifras.
         */
        recargar: function () {
            if (typeof this.table.refresh === 'function') this.table.refresh();
            this.recargarResumen();
        },

        /**
         * Solicita las cifras del resumen (ventas/compras) al backend y actualiza el DOM.
         */
        recargarResumen: async function () {
            if (!this.api || typeof this.api.obtenerResumen !== 'function') return;

            var res = await this.api.obtenerResumen();
            if (!res.ok || !res.data) return;

            var fmt = (this.utils && this.utils.formatearMoneda) ? this.utils.formatearMoneda : function (v) { return v; };

            function set(id, valor) {
                var el = d.getElementById(id);
                if (el) el.textContent = fmt(valor || 0);
            }

            var s = res.data;
            set('ventas-total-neto',    s.ventas_total);
            set('ventas-subtotal-neto', s.ventas_subtotal);
            set('ventas-impuestos-neto',s.ventas_impuestos);
            set('compras-total-neto',   s.compras_total);
            set('compras-subtotal-neto',s.compras_subtotal);
            set('compras-impuestos-neto',s.compras_impuestos);
        },

        /**
         * Inicia la sincronizacion de correo para la configuracion indicada.
         * Abre el offcanvas de pendientes y delega a facturas.sync.js.
         * @param {number|string} configId
         */
        sincronizarCorreo: function (configId) {
            // Abrir el offcanvas de pendientes
            var offcanvasEl = d.getElementById('offcanvas-facturas-pendientes');
            if (offcanvasEl) {
                var bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                bsOffcanvas.show();
            }
            if (typeof this.sync.sincronizar === 'function') {
                this.sync.sincronizar(configId);
            } else {
                console.error(MOD + ':sincronizarCorreo modulo sync no disponible');
            }
        },

        // -------------------------------------------------------
        // Event listeners del toolbar
        // -------------------------------------------------------

        /**
         * Registra event delegation en el toolbar de facturas.
         * Un solo listener para todos los botones usando data-action.
         */
        _initToolbar: function () {
            var self = this;

            // Busqueda en la tabla Tabulator
            var searchInput = d.getElementById('search-factura');
            if (searchInput) {
                searchInput.addEventListener('input', function () {
                    var table = typeof self.table.getInstance === 'function' ? self.table.getInstance() : null;
                    if (table) {
                        table.setFilter([
                            [
                                { field: 'numero',             type: 'like', value: searchInput.value },
                                { field: 'emisor_razon_social',type: 'like', value: searchInput.value },
                                { field: 'receptor_razon_social', type: 'like', value: searchInput.value }
                            ]
                        ]);
                    }
                });
            }

            // Toolbar: boton nueva factura (btn-subir-factura en list HTML)
            var btnNueva = d.getElementById('btn-subir-factura') || d.getElementById('btn-nueva-factura');
            if (btnNueva) {
                btnNueva.addEventListener('click', function () { self.subirNueva(); });
            }

            // Toolbar: boton recargar (btn-refresh-facturas en list HTML)
            var btnRecargar = d.getElementById('btn-refresh-facturas') || d.getElementById('btn-recargar-facturas');
            if (btnRecargar) {
                btnRecargar.addEventListener('click', function () { self.recargar(); });
            }

            // Toolbar: boton sincronizar correo (btn-sync-mail en list HTML)
            var btnSync = d.getElementById('btn-sync-mail') || d.getElementById('btn-sync-facturas');
            if (btnSync) {
                btnSync.addEventListener('click', function () {
                    var configId = btnSync.getAttribute('data-config-id') || btnSync.getAttribute('data-buzon-id') || 1;
                    self.sincronizarCorreo(configId);
                });
            }

            // Event delegation general en #grid-facturas (backup para acciones de la tabla)
            var grid = d.getElementById('grid-facturas');
            if (grid) {
                if (grid._facturasMainListener) {
                    grid.removeEventListener('click', grid._facturasMainListener);
                }
                grid._facturasMainListener = function (e) {
                    var btn = e.target.closest('[data-action]');
                    if (!btn) return;
                    var action = btn.getAttribute('data-action');
                    var id     = btn.getAttribute('data-id') || btn.getAttribute('data-factura-id');
                    if (action === 'ver')      self.ver(id);
                    if (action === 'eliminar') self.eliminar(id);
                };
                grid.addEventListener('click', grid._facturasMainListener);
            }

            // Submit del formulario de edicion/creacion
            var formFactura = d.getElementById('form-factura');
            if (formFactura) {
                formFactura.addEventListener('submit', function (e) {
                    e.preventDefault();
                    self.guardar();
                });
            }

            console.log(MOD + ':_initToolbar event listeners registrados');
        }
    };

    // -------------------------------------------------------
    // Registrar en el namespace global
    // -------------------------------------------------------

    // Preservar sub-namespaces ya asignados por los otros modulos
    FacturaController.utils = _prev.utils;
    FacturaController.api   = _prev.api;
    FacturaController.table = _prev.table;
    FacturaController.ui    = _prev.ui;
    FacturaController.sync  = _prev.sync;

    w.Sintel.Factura = FacturaController;

    // Aliases de compatibilidad para onclick heredados en templates HTML
    w.AppFactura = FacturaController;

    // Autoarranque cuando el DOM este listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', function () { FacturaController.init(); });
    } else {
        // DOM ya listo (ej: HTMX partial swap)
        FacturaController.init();
    }

    // Redraw al activar tab (Tabulator no renderiza bien en display:none)
    d.addEventListener('tab-activated', function (event) {
        if (event.detail && event.detail.tabName === 'facturas') {
            var tbl = FacturaController.table && FacturaController.table.getInstance
                ? FacturaController.table.getInstance()
                : null;
            if (tbl && typeof tbl.redraw === 'function') {
                tbl.redraw(true);
            }
        }
    });

    console.log(MOD + ':namespace window.Sintel.Factura registrado');
    console.log(MOD + ':alias window.AppFactura registrado');

})(window, document);
