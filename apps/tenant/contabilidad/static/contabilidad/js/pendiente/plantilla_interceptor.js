/**
 * plantilla_interceptor.js - Interceptor de Plantilla Sugerida v3.17.0
 *
 * Responsabilidades:
 *   1. Abre el offcanvas de edicion de PlantillaContable para la plantilla
 *      borrador recien inferida por el backend.
 *   2. Tras guardar la plantilla como activo=True, invoca el callback
 *      para desbloquear el offcanvas de contabilizacion.
 *   3. Expone window.Sintel.Contabilidad.PlantillaInterceptor como API publica.
 *
 * Dependencias: Sintel.Core.Http (F32.7), window.bootstrap, window.PlantillaAPI (plantilla.api.js),
 *               window.UIManager, window.SintelFeedback (opcional)
 *
 * Namespace: window.Sintel.Contabilidad (AGENTS.md §23)
 */
(function (w, d) {
  'use strict';

  const MOD = '[plantilla.interceptor]';
  const CONTAINER_ID = 'offcanvas-plantilla-interceptor';
  const API_PLANTILLAS = '/api/v1/contabilidad/plantillas-contables/';

  // ─────────────────────────────────────────────────────────────── utilidades
  function log(...args) { console.log(MOD, ...args); }
  function warn(...args) { console.warn(MOD, ...args); }

  function mostrarFeedback(msg, tipo) {
    if (w.SintelFeedback) {
      if (tipo === 'success') w.SintelFeedback.success(msg);
      else w.SintelFeedback.error(msg);
    } else if (w.notyf) {
      if (tipo === 'success') w.notyf.success(msg);
      else w.notyf.error(msg);
    }
  }

  // ─────────────────────────────────────── contenedor offcanvas del interceptor
  function obtenerOCrearContenedor() {
    let cont = d.getElementById(CONTAINER_ID);
    if (!cont) {
      cont = d.createElement('div');
      cont.id = CONTAINER_ID;
      d.body.appendChild(cont);
    }
    return cont;
  }

  // ───────────────────────────────── cargar HTML del offcanvas editar plantilla
  async function cargarEditorHTML(uuid) {
    const url = API_PLANTILLAS + uuid + '/render-offcanvas/editar/';
    try {
      const res = await w.Sintel.Core.Http.request('GET', url, null, { responseType: 'html' });
      // Sintel.Core.Http.request devuelve { ok, status, data }. Si data es HTML string lo usamos directamente.
      // Algunas versiones de http.js del proyecto retornan la respuesta cruda en .data.
      if (typeof res === 'string') return res;
      if (res && typeof res.data === 'string') return res.data;
      // Fallback: fetch nativo
      const r = await fetch(url, {
        headers: {
          'Accept': 'text/html',
          'Authorization': 'Bearer ' + (w.jwtAuth?.getAccessToken?.() || ''),
          'X-CSRFToken': getCsrf(),
        },
      });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return await r.text();
    } catch (e) {
      warn('cargarEditorHTML error:', e);
      throw e;
    }
  }

  function getCsrf() {
    const el = d.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : (getCookie('csrftoken') || '');
  }

  function getCookie(name) {
    const match = d.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  // ───────────────────────────────── guardar plantilla como activo=True via API
  async function activarPlantilla(uuid) {
    if (!w.PlantillaAPI) {
      // Fallback a fetch nativo
      const r = await fetch(API_PLANTILLAS + uuid + '/', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + (w.jwtAuth?.getAccessToken?.() || ''),
          'X-CSRFToken': getCsrf(),
        },
        body: JSON.stringify({ activo: true }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || ('HTTP ' + r.status));
      }
      return await r.json();
    }
    return await w.PlantillaAPI.update(uuid, { activo: true });
  }

  // ──────────────────────────────────── abrir editor con validacion NIIF nivel 6
  async function abrirEditorPlantilla(uuid, onActivadaCallback) {
    if (!uuid) { warn('uuid es requerido'); return; }

    log('Abriendo editor para plantilla borrador uuid=', uuid);

    const contenedor = obtenerOCrearContenedor();
    contenedor.innerHTML = '<div class="text-center py-5"><span class="spinner-border text-primary"></span></div>';

    // Intentar cargar HTML del offcanvas
    let html = '';
    try {
      html = await cargarEditorHTML(uuid);
    } catch (e) {
      contenedor.innerHTML = '';
      mostrarFeedback('No se pudo cargar el editor de plantilla: ' + (e.message || e), 'error');
      return;
    }

    // Inyectar en el contenedor
    contenedor.innerHTML = html;

    // Activar scripts del fragmento HTML
    contenedor.querySelectorAll('script').forEach(function (oldScript) {
      const newScript = d.createElement('script');
      if (oldScript.src) {
        newScript.src = oldScript.src;
      } else {
        newScript.textContent = oldScript.textContent;
      }
      d.body.appendChild(newScript);
    });

    // Buscar el elemento offcanvas dentro del fragmento
    const offcanvasEl = contenedor.querySelector('.offcanvas');
    if (!offcanvasEl) {
      warn('No se encontro elemento .offcanvas en el fragmento cargado');
      mostrarFeedback('Error al renderizar el editor de plantilla.', 'error');
      return;
    }

    // Mostrar offcanvas con Bootstrap
    const bsOffcanvas = new w.bootstrap.Offcanvas(offcanvasEl, { backdrop: true, scroll: false });
    bsOffcanvas.show();

    // Agregar boton "Guardar y Activar" si no existe ya en el offcanvas
    _inyectarBotonActivar(offcanvasEl, uuid, bsOffcanvas, onActivadaCallback);

    log('Editor abierto para plantilla', uuid);
  }

  // ──────────────────────── inyectar boton "Guardar y Activar" en el offcanvas
  function _inyectarBotonActivar(offcanvasEl, uuid, bsOffcanvas, onActivadaCallback) {
    // Buscar footer del offcanvas (o crear uno)
    let footer = offcanvasEl.querySelector('.offcanvas-footer, .offcanvas-body .d-flex.gap-2:last-child');
    if (!footer) {
      footer = offcanvasEl.querySelector('.offcanvas-body');
    }
    if (!footer) return;

    // Evitar duplicados
    if (footer.querySelector('#btn-activar-plantilla-interceptor')) return;

    const wrapper = d.createElement('div');
    wrapper.className = 'mt-3 border-top pt-3';
    wrapper.innerHTML = [
      '<div class="d-flex gap-2 align-items-center">',
      '  <button type="button" id="btn-activar-plantilla-interceptor"',
      '          class="btn btn-success btn-sm fw-semibold">',
      '    <i class="bi bi-check-circle me-1"></i>Guardar y Activar Plantilla',
      '  </button>',
      '  <small class="text-muted">',
      '    <i class="bi bi-info-circle me-1"></i>',
      '    NIIF PYMES: Solo cuentas auxiliares (nivel 6) son validas.',
      '  </small>',
      '</div>',
    ].join('');

    footer.appendChild(wrapper);

    const btnActivar = wrapper.querySelector('#btn-activar-plantilla-interceptor');
    btnActivar.addEventListener('click', async function () {
      // Validar que todas las cuentas son nivel 6 antes de activar
      if (!_validarCuentasNivel6(offcanvasEl)) return;

      btnActivar.disabled = true;
      btnActivar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Activando...';

      try {
        await activarPlantilla(uuid);
        mostrarFeedback('Plantilla activada. Las cuentas han sido validadas (NIIF nivel 6).', 'success');
        bsOffcanvas.hide();
        if (typeof onActivadaCallback === 'function') onActivadaCallback(uuid);
      } catch (e) {
        warn('Error al activar plantilla:', e);
        mostrarFeedback('No se pudo activar la plantilla: ' + (e.message || e), 'error');
        btnActivar.disabled = false;
        btnActivar.innerHTML = '<i class="bi bi-check-circle me-1"></i>Guardar y Activar Plantilla';
      }
    });
  }

  // ──────────────────────────────────────── validacion NIIF: cuentas nivel 6
  // Los codigos de cuenta estan en elementos <code> dentro de <td> en #tbody-lineas-plantilla
  function _validarCuentasNivel6(offcanvasEl) {
    const scope = offcanvasEl || d;
    const tbody = scope.querySelector('#tbody-lineas-plantilla') || scope;
    const codigos = [];
    tbody.querySelectorAll('td code').forEach(function (el) {
      const cod = (el.textContent || '').trim();
      if (cod && cod !== '-') codigos.push(cod);
    });

    const noAuxiliares = codigos.filter(function (cod) {
      return cod.length !== 6 || !/^\d{6}$/.test(cod);
    });

    if (noAuxiliares.length > 0) {
      mostrarFeedback(
        'NIIF PYMES: Todas las cuentas de la plantilla deben ser auxiliares (Nivel 6 — 6 digitos). '
        + 'Cuentas no auxiliares detectadas: ' + noAuxiliares.join(', '),
        'error'
      );
      return false;
    }
    return true;
  }

  // ─────────────────────────────────────────────────────── API publica global
  w.Sintel = w.Sintel || {};
  w.Sintel.Contabilidad = w.Sintel.Contabilidad || {};

  const PlantillaInterceptor = Object.freeze({
    abrirEditorPlantilla: abrirEditorPlantilla,
    validarCuentasNivel6: _validarCuentasNivel6,
    activarPlantilla: activarPlantilla,
  });

  w.Sintel.Contabilidad.PlantillaInterceptor = PlantillaInterceptor;
  // Alias de compatibilidad con el inline script del template
  w.PlantillaInterceptor = PlantillaInterceptor;

  log('Modulo cargado');
})(window, document);
