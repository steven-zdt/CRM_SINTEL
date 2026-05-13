/**
 * cotizaciones.ui.js - DOM Shield, Offcanvas lifecycle y forms v2.61.8
 * Namespace: window.Sintel.Cotizaciones.ui
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  var MOD = '[cotizaciones.ui]';
  var OFFCANVAS_ID = 'offcanvas-container';
  var _deleteUuid = null;
  var _eventsBound = false;

  /**
   * Abre el offcanvas Bootstrap 5 usando UIManager (Safe Patterns).
   */
  function showOffcanvas() {
    if (w.UIManager && typeof w.UIManager.handleOffcanvas === 'function') {
      w.UIManager.handleOffcanvas('#' + OFFCANVAS_ID, 'show');
    }
  }

  /**
   * Cierra el offcanvas activo usando UIManager.
   */
  function hideOffcanvas() {
    if (w.UIManager && typeof w.UIManager.handleOffcanvas === 'function') {
      w.UIManager.handleOffcanvas('#' + OFFCANVAS_ID, 'hide');
    }
  }

  /**
   * Bind generico de formulario con DOM Shield.
   * Inyecta JWT Bearer + CSRF en el fetch.
   */
  function bindForm(formId) {
    var form = d.getElementById(formId);
    if (!form) return;
    if (form.dataset.bound === 'true') return;
    form.dataset.bound = 'true';

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // DOM Shield: remover name de selects visibles
      Array.from(form.querySelectorAll('select')).forEach(function (sel) {
        if (!sel.classList.contains('d-none')) sel.removeAttribute('name');
      });

      var endpoint = form.dataset.endpoint;
      var method = form.dataset.method || 'POST';
      if (!endpoint) return;

      var api = w.Sintel.Cotizaciones.api;
      var headers = api && typeof api.getHeaders === 'function'
        ? api.getHeaders()
        : { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' };

      // Recopilar payload basico (los templates definiran los campos)
      var payload = {};
      var fd = new FormData(form);
      fd.forEach(function (val, key) { payload[key] = val; });

      // Convertir IDs numericos
      ['cliente', 'configuracion'].forEach(function (k) {
        if (payload[k]) payload[k] = parseInt(payload[k], 10) || payload[k];
      });

      fetch(endpoint, {
        method: method,
        headers: headers,
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      })
        .then(function (response) {
          return response.json().catch(function () { return {}; }).then(function (data) {
            if (!response.ok) throw data;
            return data;
          });
        })
        .then(function () {
          hideOffcanvas();
          if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.refresh === 'function') {
            w.Sintel.Cotizaciones.table.refresh();
          }
          if (w.UIManager && typeof w.UIManager.notifySuccess === 'function') {
            w.UIManager.notifySuccess('Cotizacion guardada correctamente');
          }
        })
        .catch(function (error) {
          if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(error);
          } else {
            console.error(MOD + ' Error guardando cotizacion', error);
          }
        });
    });
  }

  /**
   * Confirmar eliminacion (muestra modal Bootstrap)
   */
  function confirmarEliminar(uuid, data) {
    var estado = data ? data.estado : 'BORRADOR';
    var codigo = data ? (data.codigo_unico || data.numero_cotizacion) : 'N/A';

    // Borrado Seguro: Solo permitir si está en BORRADOR o CANCELADA
    if (estado !== 'BORRADOR' && estado !== 'CANCELADA') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError('La cotización "' + codigo + '" está activa (' + estado + '). Debe cancelarla primero antes de eliminarla.');
      } else {
        alert('La cotización debe estar cancelada para ser eliminada.');
      }
      return;
    }

    _deleteUuid = uuid;
    if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
      w.UIManager.handleModal('#modal-eliminar-cotizacion', 'show');
    }
  }

  /**
   * Ejecutar eliminacion via DELETE
   */
  function ejecutarEliminar() {
    if (!_deleteUuid) return;
    var api = w.Sintel.Cotizaciones.api;
    if (!api) return;

    var url = api.deleteUrl(_deleteUuid);
    var headers = typeof api.getHeaders === 'function' ? api.getHeaders() : {};

    var btnConfirmar = d.getElementById('btn-confirmar-eliminar-cotizacion');
    if (btnConfirmar) btnConfirmar.disabled = true;

    fetch(url, { method: 'DELETE', headers: headers, credentials: 'same-origin' })
      .then(function (r) {
        if (r.ok) {
          if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
            w.UIManager.handleModal('#modal-eliminar-cotizacion', 'hide');
          }
          if (w.UIManager && typeof w.UIManager.notifySuccess === 'function') {
            w.UIManager.notifySuccess('Cotizacion eliminada correctamente');
          }
          if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.refresh === 'function') {
            w.Sintel.Cotizaciones.table.refresh();
          }
        } else {
          return r.json().then(function (err) { throw err; });
        }
      })
      .catch(function (err) {
        console.error(MOD + ' Error eliminando:', err);
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(err.error || 'Error al eliminar cotizacion');
        }
      })
      .finally(function () { 
        _deleteUuid = null; 
        var btnConfirmar = d.getElementById('btn-confirmar-eliminar-cotizacion');
        if (btnConfirmar) btnConfirmar.disabled = false;
      });
  }

  /**
   * Bind global de eventos UI (botones crear, confirmar eliminar, htmx afterSwap)
   * Solo se ejecuta UNA VEZ en toda la sesion
   */
  function bindEvents() {
    // Guard global: solo ejecutar una vez
    if (_eventsBound) return;
    _eventsBound = true;

    // Delegación de eventos para el botón confirmar eliminación
    d.addEventListener('click', function (e) {
      if (e.target && e.target.id === 'btn-confirmar-eliminar-cotizacion') {
        ejecutarEliminar();
      }
    });

    // HTMX afterSettle: mostrar offcanvas tras inyeccion de HTML
    d.body.addEventListener('htmx:afterSettle', function (evt) {
      var target = evt.detail.target;
      if (target && target.id === OFFCANVAS_ID) {
        showOffcanvas();
        // Bind forms dentro del offcanvas (cada formulario chequea si ya esta bound)
        bindForm('form-cotizacion-crear');
        bindForm('form-cotizacion-editar');
        bindForm('form-configuracion-crear');
        bindForm('form-configuracion-editar');
        // Procesar HTMX en contenido nuevo
        if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
          htmx.process(target);
        }
      }
    });
  }

  // Exponer en namespace
  w.Sintel.Cotizaciones.ui = {
    bindForm: bindForm,
    bindEvents: bindEvents,
    showOffcanvas: showOffcanvas,
    hideOffcanvas: hideOffcanvas,
    confirmarEliminar: confirmarEliminar,
    ejecutarEliminar: ejecutarEliminar
  };

})(window, document);
