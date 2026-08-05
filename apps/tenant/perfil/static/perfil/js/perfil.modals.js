// Perfil modals module -- exposes stateless modal helpers under the
// window.perfilModals namespace. Handles offcanvas form submission
// for perfil CRUD operations.
(function (w, d) {
  'use strict';

  // [RULE 2] Gateway Directo SSoT: usar Sintel.Perfil.API cuando este disponible,
  // con fallback a URL literal para robustez en carga asincrona de scripts.
  function getApiBase() {
    return (w.Sintel && w.Sintel.Perfil && w.Sintel.Perfil.API)
      ? w.Sintel.Perfil.API.BASE
      : '/api/v1/perfil/perfiles/';
  }

  // Ensure namespace
  w.Sintel = w.Sintel || {};
  w.Sintel.Perfil = w.Sintel.Perfil || {};

  function getCsrfToken() {
    var el = d.querySelector('[name=csrfmiddlewaretoken]');
    if (el) return el.value;
    var cookie = d.cookie.split(';').find(function(c) { return c.trim().startsWith('csrftoken='); });
    return cookie ? cookie.split('=')[1] : '';
  }

  function collectFormData(formId) {
    var form = d.getElementById(formId);
    if (!form) return null;
    var data = {};
    var elements = form.elements;
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      if (el.name && el.type !== 'button' && el.type !== 'submit') {
        data[el.name] = el.value;
      }
    }
    return data;
  }

  function showCreate() {
    var evt = new CustomEvent('perfil:showCreate');
    d.dispatchEvent(evt);
  }

  function showEdit(id) {
    if (!id) return;
    var API_URL = getApiBase();
    fetch(API_URL + id + '/render-offcanvas/editar/')
      .then(res => {
        if (!res.ok) throw new Error('Error cargando formulario de edición');
        return res.text();
      })
      .then(html => {
        var container = d.getElementById('modal-perfil-edit-container');
        if (container) {
          container.innerHTML = html;
          var offcanvasEl = d.getElementById('offcanvas-perfil-editar');
          var bsOffcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
          bsOffcanvas.show();
        }
      })
      .catch(err => {
        console.error(err);
        if (w.UIManager) w.UIManager.notifyError('No se pudo cargar el formulario de edición');
      });
  }

  function showDetail(id) {
    if (!id) return;
    var API_URL = getApiBase();
    fetch(API_URL + id + '/render-offcanvas/detalle/')
      .then(res => {
        if (!res.ok) throw new Error('Error cargando detalles del perfil');
        return res.text();
      })
      .then(html => {
        var container = d.getElementById('modal-perfil-edit-container');
        if (container) {
          container.innerHTML = html;
          var offcanvasEl = d.getElementById('offcanvas-perfil-detalle');
          var bsOffcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
          bsOffcanvas.show();
        }
      })
      .catch(err => {
        console.error(err);
        if (w.UIManager) w.UIManager.notifyError('No se pudo cargar el detalle del perfil');
      });
  }

  function deletePerfil(id) {
    if (!id) return;
    if (!confirm('Esta seguro de que desea eliminar este perfil?')) return;
    var API_URL = getApiBase();
    fetch(API_URL + id + '/', {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    })
    .then(function(res) {
      if (!res.ok) {
        return res.json().then(function(body) {
          throw body; // Lanza el objeto de error JSON
        }).catch(function(err) {
          // Si no es JSON o hay otro error de parseo, lanza objeto generico
          throw { message: 'Error interno del servidor al eliminar (Status: ' + res.status + ')' };
        });
      }
      return res; // Si 204 No Content, no hay body JSON
    })
    .then(function() {
      if (w.UIManager && w.UIManager.notifySuccess) {
        w.UIManager.notifySuccess('Perfil eliminado exitosamente');
      }
      if (w.refreshPerfilTable) w.refreshPerfilTable();
    })
    .catch(function(errObj) {
      console.error('[perfil.modals] deletePerfil Error:', errObj);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(errObj);
      } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ message: errObj.message || 'No se pudo eliminar el perfil' });
      } else {
        alert(errObj.message || 'No se pudo eliminar el perfil');
      }
    });
  }

  function handleSaveCreate() {
    var data = collectFormData('form-perfil-crear');
    if (!data) {
      console.warn('[perfil.modals] Formulario no encontrado');
      return;
    }
    var API_URL = getApiBase();
    var feedbackEl = d.getElementById('form-perfil-feedback');

    function hideFeedback() {
      if (feedbackEl) feedbackEl.classList.add('d-none');
    }
    function showFeedback(msg) {
      if (feedbackEl) { feedbackEl.textContent = msg; feedbackEl.classList.remove('d-none'); }
    }

    // DOM Shield: leer empresa_id desde el input hidden (no del select visible)
    var empresaIdEl = d.getElementById('perfil-empresa-id');
    var empresaIdValue = empresaIdEl ? empresaIdEl.value.trim() : '';
    if (empresaIdValue) data['empresa_id'] = empresaIdValue;

    // [PICKER] Leer sedes y areas desde window._perfilCrearGetExtras (pill-pickers)
    // Fallback a select nativo legacy si el picker no esta disponible
    if (typeof w._perfilCrearGetExtras === 'function') {
      var extras = w._perfilCrearGetExtras();
      data['sedes_uuids'] = extras.sedes_uuids || [];
      data['areas_uuids'] = extras.areas_uuids || [];
    } else {
      // legacy fallback
      var sedesSelect = d.getElementById('perfil-crear-sedes-select');
      if (sedesSelect) {
        data['sedes_uuids'] = Array.from(sedesSelect.selectedOptions)
          .map(function(opt) { return opt.value; }).filter(Boolean);
      }
      var areasSelect = d.getElementById('perfil-crear-areas-select');
      if (areasSelect) {
        data['areas_uuids'] = Array.from(areasSelect.selectedOptions)
          .map(function(opt) { return opt.value; }).filter(Boolean);
      }
    }

    // -- Validaciones frontend --
    hideFeedback();

    if (!empresaIdValue) {
      var empSel = d.getElementById('perfil-empresa-select');
      if (empSel) empSel.classList.add('is-invalid');
      showFeedback('Debes seleccionar una empresa.');
      return;
    }
    var empSel2 = d.getElementById('perfil-empresa-select');
    if (empSel2) empSel2.classList.remove('is-invalid');

    if (!data['sedes_uuids'] || data['sedes_uuids'].length === 0) {
      var sedePickerEl = d.getElementById('sede-picker');
      if (sedePickerEl) sedePickerEl.classList.add('is-invalid');
      showFeedback('Debes seleccionar al menos una sede.');
      return;
    }
    var sedePickerClean = d.getElementById('sede-picker');
    if (sedePickerClean) sedePickerClean.classList.remove('is-invalid');

    if (!data.email) { showFeedback('El email es requerido.'); return; }
    if (!data.first_name) { showFeedback('El nombre es requerido.'); return; }

    // POST al endpoint de creacion
    fetch(API_URL, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(data)
    })
    .then(function(res) {
      return res.json().then(function(body) {
        return { ok: res.ok, status: res.status, body: body };
      });
    })
    .then(function(result) {
      if (result.ok) {
        // Cerrar offcanvas
        var offcanvasEl = d.getElementById('offcanvas-perfil-crear');
        if (offcanvasEl) {
          var inst = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
          if (inst) inst.hide();
        }

        // Notificacion de exito
        if (w.UIManager && typeof w.UIManager.notifySuccess === 'function') {
          w.UIManager.notifySuccess('Perfil creado exitosamente');
        }

        // Refrescar tabla
        if (w.refreshPerfilTable) w.refreshPerfilTable();

        // Limpiar formulario
        var form = d.getElementById('form-perfil-crear');
        if (form) form.reset();
        if (feedbackEl) feedbackEl.classList.add('d-none');
      } else {
        // Mostrar error
        var msg = result.body.message || 'Error al crear el perfil.';
        if (feedbackEl) {
          feedbackEl.textContent = msg;
          feedbackEl.classList.remove('d-none');
        }
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError({ ok: false, status: result.status, data: result.body });
        }
      }
    })
    .catch(function(err) {
      console.error('[perfil.modals] Error de red:', err);
      if (feedbackEl) {
        feedbackEl.textContent = 'Error de conexion. Intente de nuevo.';
        feedbackEl.classList.remove('d-none');
      }
    });
  }

  function handleSaveEdit() {
    var data = collectFormData('form-perfil-editar');
    if (!data || !data.id) return;

    var API_URL = getApiBase();
    var feedbackEl = d.getElementById('form-perfil-editar-feedback');
    var profileId = data.id;

    // Extraer rol antes de enviar al endpoint principal (es read_only en serializer)
    var rolEl = d.getElementById('perfil-edit-rol');
    var newRol = rolEl ? data.rol : null;

    // Extract selected sedes
    var sedesSelect = d.getElementById('perfil-edit-sedes-select');
    var sedesUuids = [];
    if (sedesSelect) {
      sedesUuids = Array.from(sedesSelect.selectedOptions).map(function(opt) { return opt.value; }).filter(Boolean);
    }
    
    // Extract selected areas
    var areasSelect = d.getElementById('perfil-edit-areas-select');
    var areasUuids = [];
    if (areasSelect) {
      areasUuids = Array.from(areasSelect.selectedOptions).map(function(opt) { return opt.value; }).filter(Boolean);
    }

    // Payload para el PATCH principal (sin id ni rol)
    var payload = {};
    Object.keys(data).forEach(function(k) {
      if (k !== 'id' && k !== 'rol') payload[k] = data[k];
    });
    payload['sedes_uuids'] = sedesUuids;
    payload['areas_uuids'] = areasUuids;

    var csrfToken = getCsrfToken();

    // PATCH principal: cargo, departamento, telefono_corporativo, sedes, areas
    var mainPromise = fetch(API_URL + profileId + '/', {
      method: 'PATCH',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(payload)
    }).then(function(res) {
      return res.json().then(function(b) { return { ok: res.ok, status: res.status, body: b, isRol: false }; });
    });

    var promises = [mainPromise];

    // PATCH assign-rol: solo si ADMIN tiene el selector en el DOM y selecciono un valor
    if (newRol && rolEl) {
      var rolPromise = fetch(API_URL + profileId + '/assign-rol/', {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ rol: newRol })
      }).then(function(res) {
        return res.json().then(function(b) { return { ok: res.ok, status: res.status, body: b, isRol: true }; });
      });
      promises.push(rolPromise);
    }

    Promise.all(promises).then(function(results) {
      var errResult = results.find(function(r) { return !r.ok; });
      if (!errResult) {
        var offcanvasEl = d.getElementById('offcanvas-perfil-editar');
        if (offcanvasEl) {
          var inst = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
          if (inst) inst.hide();
        }
        if (w.UIManager) w.UIManager.notifySuccess('Perfil actualizado exitosamente');
        if (w.refreshPerfilTable) w.refreshPerfilTable();
        if (feedbackEl) feedbackEl.classList.add('d-none');
      } else {
        var msg = errResult.body.message || errResult.body.detail || 'Error al actualizar el perfil.';
        if (feedbackEl) {
          feedbackEl.textContent = msg;
          feedbackEl.classList.remove('d-none');
        }
        if (w.UIManager && w.UIManager.handleError) {
          w.UIManager.handleError({ ok: false, status: errResult.status, data: errResult.body });
        }
      }
    }).catch(function(err) {
      console.error('[perfil.modals] handleSaveEdit error:', err);
      if (feedbackEl) {
        feedbackEl.textContent = 'Error de conexion. Intente de nuevo.';
        feedbackEl.classList.remove('d-none');
      }
    });
  }

  // Delegated event listener for the save buttons inside the offcanvas
  d.addEventListener('click', function(e) {
    var btnCrear = e.target.closest('#btn-guardar-perfil-crear');
    if (btnCrear) {
      e.preventDefault();
      e.stopPropagation();
      handleSaveCreate();
      return;
    }
    
    var btnEditar = e.target.closest('#btn-guardar-perfil-editar');
    if (btnEditar) {
      e.preventDefault();
      e.stopPropagation();
      handleSaveEdit();
      return;
    }
  });

  // Expose public API
  w.perfilModals = {
    showCreate: showCreate,
    showEdit: showEdit,
    showDetail: showDetail,
    deletePerfil: deletePerfil,
    save: handleSaveCreate
  };

  w.Sintel.Perfil.Modals = Object.freeze({
    showCreate: showCreate,
    showEdit: showEdit,
    showDetail: showDetail,
    deletePerfil: deletePerfil
  });

})(window, document);
