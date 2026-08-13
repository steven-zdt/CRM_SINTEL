// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * cuenta_editor.js - Gestión de Formularios CuentaBancaria
 * Namespace: window.Sintel.Bancos.CuentaEditor
 * ⚠️ FSD / Vanilla JS
 */
(function (w, d) {
  'use strict';

  const MOD = '[bancos:cuenta_editor]';
  const API_URL = '/api/v1/bancos/cuentas/';
  const CONTAINER_ID = '#offcanvas-container-bancos';

  async function openOffcanvas(uuid = null) {
    let container = d.querySelector(CONTAINER_ID);

    if (!container) {
      console.warn(`${MOD} Contenedor ${CONTAINER_ID} no encontrado. Creando...`);
      container = d.createElement('div');
      container.id = CONTAINER_ID.substring(1);
      d.body.appendChild(container);
    }

    const url = uuid
      ? `${API_URL}${uuid}/render-offcanvas/editar/`
      : `${API_URL}render-offcanvas/crear/`;

    console.log(`${MOD} Cargando formulario de cuenta desde: ${url}`);
    return htmx.ajax('GET', url, { target: CONTAINER_ID, swap: 'innerHTML' });
  }

  // Interceptar settled para configurar el offcanvas
  d.body.addEventListener('htmx:afterSettle', async (e) => {
    const target = e.detail.target;
    if (target && ('#' + target.id) === CONTAINER_ID) {
      const offcanvasEl = target.querySelector('#offcanvas-cuenta-crear, #offcanvas-cuenta-editar');
      if (!offcanvasEl) return;

      console.log(`${MOD} DOM Settle detectado para cuenta, activando offcanvas...`);

      if (w.UIManager?.handleOffcanvas) {
        w.UIManager.handleOffcanvas(offcanvasEl, 'show');
      } else {
        // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (AGENTS.md §26 — nunca getOrCreateInstance)
        w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
      }

      configurarEventos(offcanvasEl);
    }
  });

  function buildPayload(form) {
    const payload = {};
    form.querySelectorAll('input, select, textarea').forEach((field) => {
      const key = field.name;
      if (!key || field.disabled) return;

      let value = field.value;
      if (typeof value === 'string') {
        value = value.trim();
      }
      payload[key] = value;
    });

    delete payload.csrfmiddlewaretoken;
    return payload;
  }

  function configurarEventos(container) {
    const form = container.querySelector('#cuenta-form');
    if (!form) return;

    if (form.dataset.editorInitialized === 'true') return;
    form.dataset.editorInitialized = 'true';

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      await guardar(form);
    });

    // NOTA (remediacion doble-submit, auditoria 2026-08-06): #btn-guardar-cuenta
    // ya es <button type="submit" form="cuenta-form"> (ver offcanvas_crear_cuenta.html
    // / offcanvas_editar_cuenta.html) -- el navegador ya dispara el evento "submit"
    // del formulario nativamente al hacer click. Llamar ademas form.requestSubmit()
    // en un listener de "click" separado disparaba un SEGUNDO evento "submit",
    // ejecutando guardar(form) dos veces por cada click humano y creando cuentas
    // bancarias duplicadas (sin validacion de unicidad de respaldo en backend).
  }

  async function guardar(form) {
    if (!form.checkValidity()) return form.reportValidity();

    if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
      console.error(`${MOD} Sintel.Core.Http no disponible`);
      w.UIManager?.notifyError?.({ data: { detail: 'Error interno: cliente HTTP no disponible.' } });
      return;
    }

    const uuid    = form.dataset.uuid || '';
    const payload = buildPayload(form);
    const method  = uuid ? 'PUT' : 'POST';
    const url     = uuid ? `${API_URL}${uuid}/` : API_URL;

    const res = await w.Sintel.Core.Http.request(method, url, payload);

    if (!res.ok) {
      return w.UIManager?.handleError(res, MOD, {
        errorContainerSelector: '#form-cuenta-feedback'
      });
    }

    // Éxito
    if (w.UIManager?.showSuccess) {
      w.UIManager.showSuccess(uuid ? 'Cuenta bancaria actualizada' : 'Cuenta bancaria creada');
    }

    // Cerrar Offcanvas
    const offcanvasEl = form.closest('.offcanvas');
    if (offcanvasEl) {
      if (w.UIManager?.handleOffcanvas) {
        w.UIManager.handleOffcanvas(offcanvasEl, 'hide');
      } else {
        bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
      }
    }

    // Refrescar lista de cuentas
    if (w.Sintel.Bancos.CuentaList?.refresh) {
      w.Sintel.Bancos.CuentaList.refresh();
    }
  }

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.CuentaEditor = {
    openOffcanvas: openOffcanvas
  };

})(window, document);
