/**
 * producto_editor.js - Feature Module para el Editor de Productos v2.62.0
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};
  w.Sintel.Cotizaciones.features = w.Sintel.Cotizaciones.features || {};

  var ProductoEditor = {
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
      var endpoint = form.dataset.endpoint || api.productosUrl;
      var method = form.dataset.method || 'POST';

      var payload = {};
      new FormData(form).forEach(function(v, k) { payload[k] = v; });

      // Bug real (auditoria de modernizacion, 2026-08-27): antes no se
      // verificaba response.ok ni existia .catch() -- un 400 de validacion
      // del backend se leia igual con r.json() y caia en el .then() de
      // "exito": se mostraba "Producto guardado", se cerraba el offcanvas y
      // se refrescaba la tabla, aunque nada se hubiera guardado realmente.
      // Ademas el boton nunca se deshabilitaba (doble-submit posible).
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
        if (w.UIManager) w.UIManager.notifySuccess('Producto guardado');
        if (w.Sintel.Cotizaciones.ui) w.Sintel.Cotizaciones.ui.hideOffcanvas();
        if (w.Sintel.Cotizaciones.features.productoList && w.Sintel.Cotizaciones.features.productoList.table) {
            w.Sintel.Cotizaciones.features.productoList.table.replaceData();
        }
      })
      .catch(function (error) {
        if (w.UIManager) w.UIManager.handleError(error, '[ProductoEditor]');
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
    }
  };

  w.Sintel.Cotizaciones.features.productoEditor = ProductoEditor;

})(window, document);
