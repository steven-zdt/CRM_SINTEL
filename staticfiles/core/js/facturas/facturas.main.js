/**
 * facturas.main.js - copied minimal orchestrator for core static
 * Synchronized from apps/tenant/facturas/static/facturas/js/facturas.main.js
 */
(function (w, d) {
    'use strict';

    var MOD = '[facturas.main]';

    w.Sintel = w.Sintel || {};
    var _prev = w.Sintel.Facturas || {};

    var FacturaController = {
        init: function () {
            console.log(MOD + ':init (core wrapper)');
            this.utils = _prev.utils || w.Sintel.Facturas.utils || {};
            this.api   = _prev.api   || w.Sintel.Facturas.api   || {};
            this.table = _prev.table || w.Sintel.Facturas.table || {};
            this.ui    = _prev.ui    || w.Sintel.Facturas.ui    || {};
            this.sync  = _prev.sync  || w.Sintel.Facturas.sync  || {};

            if (typeof this.table.init === 'function') this.table.init();
            if (typeof this.ui.initHTMX === 'function') this.ui.initHTMX();
            this._initToolbar();
            this.recargarResumen();
        },
        ver: function (rawId) { var id = parseInt(rawId, 10); if (!id) return; if (typeof this.ui.abrirDetalle === 'function') this.ui.abrirDetalle(id); },
        subirNueva: function () { if (typeof this.ui.abrirCrear === 'function') this.ui.abrirCrear(); },
        eliminar: async function (rawId) { var id = parseInt(rawId, 10); if (!id) return; if (typeof this.api.eliminar === 'function') await this.api.eliminar(id); this.recargar(); },
        guardar: async function () { var payload = (this.ui && this.ui.recolectarPayload) ? this.ui.recolectarPayload() : null; if (!payload) return; var res = this.api.crear ? await this.api.crear(payload) : {ok:false}; if (res.ok && typeof this.ui.cerrar==='function') this.ui.cerrar(); this.recargar(); },
        recargar: function () { if (typeof this.table.refresh === 'function') this.table.refresh(); this.recargarResumen(); },
        recargarResumen: async function () { if (!this.api || typeof this.api.obtenerResumen !== 'function') return; var res = await this.api.obtenerResumen(); if (!res.ok) return; },
        _initToolbar: function () { var self=this; var btnNueva = d.getElementById('btn-subir-factura'); if (btnNueva) btnNueva.addEventListener('click', function(){self.subirNueva();}); }
    };

    FacturaController.utils = _prev.utils;
    FacturaController.api   = _prev.api;
    FacturaController.table = _prev.table;
    FacturaController.ui    = _prev.ui;
    FacturaController.sync  = _prev.sync;

    w.Sintel.Facturas = FacturaController;
    w.AppFacturas = FacturaController;

    if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', function(){ FacturaController.init(); }); else FacturaController.init();

})(window, document);
