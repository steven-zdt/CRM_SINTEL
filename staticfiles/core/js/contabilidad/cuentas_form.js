/**
 * cuentas_form.js - Gestión de Formularios de Cuentas v2.61
 * Responsabilidad: HTMX Offcanvas y Persistencia (Zero Trust).
 */
(function (w, d) {
  'use strict';

  const MOD = '[cuentas:form]';
  const API_BASE = '/api/v1/contabilidad/cuentas-contables/';
  const CONTAINER = '#offcanvas-container-cuentas';

  async function openOffcanvas(id, action = 'detalle') {
    const baseUrl = `${API_BASE}${id ? id + '/' : ''}render-offcanvas/`;
    const url = action === 'detalle' ? `${baseUrl}detalle/` : `${baseUrl}crear/`;

    await htmx.ajax('GET', url, {
      target: CONTAINER,
      swap: 'innerHTML'
    });

    const offcanvasEl = d.querySelector(`${CONTAINER} .offcanvas`);
    if (offcanvasEl) {
      bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
      if (action !== 'detalle') configurarFormulario(offcanvasEl);
    }
  }

  function configurarFormulario(container) {
    const form = container.querySelector('form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await guardar(form);
    });
  }

  async function guardar(form) {
    if (!form.checkValidity()) return form.reportValidity();

    // 🛡️ DOM SHIELD
    const selects = form.querySelectorAll('select[name]');
    const shields = new Map();
    selects.forEach(s => { shields.set(s, s.name); s.removeAttribute('name'); });

    const formData = new FormData(form);
    selects.forEach(s => s.name = shields.get(s));

    const id = formData.get('id');
    const payload = Object.fromEntries(formData);
    payload.activa = payload.activa === 'true' || payload.activa === 'on';
    
    // ⚠️ IDOR Protection: El backend ya escala a nivel de empresa por tenant-isolation
    const res = await w.http(id ? 'PATCH' : 'POST', id ? `${API_BASE}${id}/` : API_BASE, payload);

    if (!res.ok) {
      return w.UIManager?.handleError(res, MOD, { errorContainerSelector: '.error-injector' });
    }

    w.SintelFeedback?.success('Cuenta procesada correctamente');
    bootstrap.Offcanvas.getInstance(form.closest('.offcanvas'))?.hide();
    w.AppCuentas?.refresh();
  }

  async function eliminar(id) {
    if (!confirm('¿Seguro que desea eliminar esta cuenta?')) return;
    const res = await w.http('DELETE', `${API_BASE}${id}/`);
    if (!res.ok) return w.UIManager?.handleError(res, MOD);
    
    w.SintelFeedback?.success('Cuenta eliminada');
    w.AppCuentas?.refresh();
  }

  w.AppCuentas = w.AppCuentas || {};
  w.AppCuentas.openOffcanvas = openOffcanvas;
  w.AppCuentas.eliminar = eliminar;

})(window, document);
