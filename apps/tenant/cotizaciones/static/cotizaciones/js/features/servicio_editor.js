/**
 * servicio_editor.js - Feature Module para el Editor de Servicios v2.62.0
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};
  w.Sintel.Cotizaciones.features = w.Sintel.Cotizaciones.features || {};

  var ServicioEditor = {
    init: function (formId) {
      var form = d.getElementById(formId);
      if (!form) return;
      this.bindForm(form);
    },
    bindForm: function (form) {
      var self = this;
      if (form.dataset.editorInitialized) return;
      form.dataset.editorInitialized = 'true';

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        self.save(form);
      });
    },
    save: function (form) {
      var api = w.Sintel.Cotizaciones.api;
      var endpoint = form.dataset.endpoint || api.serviciosUrl;
      var method = form.dataset.method || 'POST';

      var payload = {};
      new FormData(form).forEach(function(v, k) { payload[k] = v; });

      // Mismo bug real y mismo fix que producto_editor.js (auditoria de
      // modernizacion, 2026-08-27): antes no se verificaba response.ok ni
      // existia .catch(), y el boton nunca se deshabilitaba.
      var btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;

      fetch(endpoint, {
        method: method,
        headers: api.getHeaders(),
        body: JSON.stringify(payload)
      })
      .then(function(r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok) throw { ok: false, status: r.status, data: data };
          return data;
        });
      })
      .then(function(data) {
        if (w.UIManager) w.UIManager.notifySuccess('Servicio guardado');
        if (w.Sintel.Cotizaciones.ui) w.Sintel.Cotizaciones.ui.hideOffcanvas();
        if (w.Sintel.Cotizaciones.features.servicioList && w.Sintel.Cotizaciones.features.servicioList.table) {
            w.Sintel.Cotizaciones.features.servicioList.table.replaceData();
        }
      })
      .catch(function (error) {
        if (w.UIManager) w.UIManager.handleError(error, '[ServicioEditor]');
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
    }
  };

  w.Sintel.Cotizaciones.features.servicioEditor = ServicioEditor;

})(window, document);
