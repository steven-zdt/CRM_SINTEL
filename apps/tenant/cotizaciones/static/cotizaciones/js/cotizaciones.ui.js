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

      // Convertir IDs numericos (solo si consisten puramente en digitos)
      ['cliente', 'configuracion'].forEach(function (k) {
        if (payload[k] && /^\d+$/.test(payload[k])) {
          payload[k] = parseInt(payload[k], 10) || payload[k];
        }
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

    // Borrado seguro -- regla real: CotizacionService.eliminar_cotizacion()
    // solo admite BORRADOR/ENVIADA (APROBADA/RECHAZADA/ARCHIVADA nunca se
    // borran, la trazabilidad se conserva via esos estados). Hallazgo real
    // (2026-09-25): esta condicion comparaba contra 'CANCELADA', el nombre
    // de estado anterior al rename de COTIZACIONES-02 -- nunca coincidia
    // con un valor real.
    if (estado !== 'BORRADOR' && estado !== 'ENVIADA') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError('La cotización "' + codigo + '" está en estado ' + estado + ' y ya no admite eliminación.');
      } else {
        alert('La cotización ya no admite eliminación en este estado.');
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

  // ── Maquina de estados (2026-09-25) ──────────────────────────────────
  // BORRADOR->ENVIADA (generar-pdf, gated por PDF exitoso)->APROBADA|
  // RECHAZADA (con motivo obligatorio) -- endpoints reales ya existentes
  // en CotizacionViewSet, ver business_service.py::cambiar_estado().

  /**
   * POST generico a un endpoint de transicion de estado (aprobar/rechazar).
   */
  function _cambiarEstado(uuid, accion, payload) {
    var api = w.Sintel.Cotizaciones.api;
    if (!api) return;
    var url = accion === 'aprobar' ? api.aprobarUrl(uuid) : api.rechazarUrl(uuid);
    var headers = typeof api.getHeaders === 'function' ? api.getHeaders() : { 'Content-Type': 'application/json' };

    fetch(url, { method: 'POST', headers: headers, credentials: 'same-origin', body: JSON.stringify(payload || {}) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok) throw data;
          return data;
        });
      })
      .then(function () {
        var msg = accion === 'aprobar' ? 'Cotizacion aprobada correctamente.' : 'Cotizacion rechazada correctamente.';
        if (w.UIManager && typeof w.UIManager.notifySuccess === 'function') {
          w.UIManager.notifySuccess(msg);
        }
        if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.refresh === 'function') {
          w.Sintel.Cotizaciones.table.refresh();
        }
      })
      .catch(function (err) {
        console.error(MOD + ' Error cambiando estado (' + accion + '):', err);
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(err);
        } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          var detail = (err && err.estado && err.estado[0]) || err.message || err.detail || 'Error al cambiar estado';
          w.UIManager.notifyError(detail);
        }
      });
  }

  /**
   * Enviar (BORRADOR -> ENVIADA): genera el PDF real (POST generar-pdf/,
   * mismo endpoint que descarga el archivo) y solo si tiene exito
   * transiciona el estado -- exactamente el contrato de
   * CotizacionService.generar_pdf_y_enviar(). El PDF se abre en una
   * pestana nueva, misma UX que el boton "Descargar PDF" ya existente.
   */
  function confirmarEnviar(uuid) {
    var doEnviar = function () {
      var api = w.Sintel.Cotizaciones.api;
      if (!api) return;
      var headers = typeof api.getHeaders === 'function' ? api.getHeaders() : {};

      fetch(api.generarPdfUrl(uuid), { method: 'POST', headers: headers, credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok) return r.json().then(function (err) { throw err; });
          return r.blob();
        })
        .then(function (blob) {
          var url = URL.createObjectURL(blob);
          window.open(url, '_blank');
          setTimeout(function () { URL.revokeObjectURL(url); }, 60000);
          if (w.UIManager && typeof w.UIManager.notifySuccess === 'function') {
            w.UIManager.notifySuccess('Cotizacion enviada correctamente (PDF generado).');
          }
          if (w.Sintel.Cotizaciones.table && typeof w.Sintel.Cotizaciones.table.refresh === 'function') {
            w.Sintel.Cotizaciones.table.refresh();
          }
        })
        .catch(function (err) {
          console.error(MOD + ' Error enviando cotizacion:', err);
          if (w.UIManager && typeof w.UIManager.handleError === 'function') {
            w.UIManager.handleError(err);
          } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError(err.message || err.detail || 'Error al enviar cotizacion');
          }
        });
    };

    if (w.UIManager && typeof w.UIManager.confirm === 'function') {
      w.UIManager.confirm('Se generara el PDF y la cotizacion pasara a estado Enviada.', 'Enviar cotizacion?')
        .then(function (ok) { if (ok) doEnviar(); });
    } else if (w.confirm('Enviar esta cotizacion? Se generara el PDF y pasara a estado Enviada.')) {
      doEnviar();
    }
  }

  /**
   * Aprobar (ENVIADA -> APROBADA).
   */
  function confirmarAprobar(uuid) {
    var doAprobar = function () { _cambiarEstado(uuid, 'aprobar', {}); };

    if (w.UIManager && typeof w.UIManager.confirm === 'function') {
      w.UIManager.confirm('La cotizacion pasara a estado Aprobada.', 'Aprobar cotizacion?')
        .then(function (ok) { if (ok) doAprobar(); });
    } else if (w.confirm('Aprobar esta cotizacion?')) {
      doAprobar();
    }
  }

  /**
   * Rechazar (ENVIADA -> RECHAZADA) -- exige un motivo (concepto de por
   * que no se aplico), guardado en CotizacionHistorialEstado.motivo via
   * cambiar_estado(). Usa SweetAlert2 (input: 'textarea') cuando esta
   * disponible (mismo lib que UIManager.confirm ya usa); fallback a
   * window.prompt si no.
   */
  function confirmarRechazar(uuid) {
    if (typeof Swal !== 'undefined') {
      Swal.fire({
        title: 'Rechazar cotizacion',
        text: 'Indica el motivo por el que no se aplico (obligatorio).',
        input: 'textarea',
        inputPlaceholder: 'Ej: el cliente eligio otro proveedor por precio...',
        showCancelButton: true,
        confirmButtonText: 'Rechazar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#dc3545',
        reverseButtons: true,
        inputValidator: function (value) {
          if (!value || !value.trim()) return 'El motivo es obligatorio.';
        },
      }).then(function (result) {
        if (result.isConfirmed) {
          _cambiarEstado(uuid, 'rechazar', { motivo: result.value.trim() });
        }
      });
      return;
    }

    var motivo = w.prompt('Motivo del rechazo (obligatorio):', '');
    if (motivo === null) return;
    motivo = motivo.trim();
    if (!motivo) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError('El motivo es obligatorio para rechazar.');
      }
      return;
    }
    _cambiarEstado(uuid, 'rechazar', { motivo: motivo });
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
        // Bind forms dentro del offcanvas (cada formulario chequea si ya esta bound).
        // form-cotizacion-crear/-editar removidos (auditoria de
        // modernizacion, 2026-08-27): sus templates
        // (offcanvas_crear_cotizacion.html/offcanvas_editar_cotizacion.html)
        // eran huerfanos -- ningun view los renderizaba, el flujo real de
        // Cotizacion usa editor_cotizacion.html + cotizacion_editor.js.
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
    ejecutarEliminar: ejecutarEliminar,
    confirmarEnviar: confirmarEnviar,
    confirmarAprobar: confirmarAprobar,
    confirmarRechazar: confirmarRechazar
  };

})(window, document);
