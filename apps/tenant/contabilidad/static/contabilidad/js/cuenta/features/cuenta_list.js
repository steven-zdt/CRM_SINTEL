/**
 * cuenta_list.js - Feature List para CuentaContable
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#contabilidad-cuentas-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_cuentas.html).
 * Este archivo solo maneja: acciones de fila (ver/editar/eliminar), apertura
 * de offcanvas, y el disparo del evento que hace que HTMX vuelva a pedir la
 * tabla al backend tras una mutacion. Columnas/orden/paginacion viven en
 * tables.py (server-side) -- no reimplementar aqui.
 */
(function (w, d) {
  'use strict';

  const PANEL_SELECTOR = '#contabilidad-cuentas-panel';
  const API_URL = '/api/v1/contabilidad/cuentas-contables/';

  function showOffcanvas(id) {
    const el = d.getElementById(id);
    if (!el) return;
    if (w.UIManager?.handleOffcanvas) {
      w.UIManager.handleOffcanvas(el, 'show');
    } else {
      const p = w.bootstrap?.Offcanvas?.getInstance(el);
      if (p) p.dispose();
      d.querySelectorAll('.offcanvas-backdrop').forEach((b) => b.remove());
      new w.bootstrap.Offcanvas(el).show();
    }
  }

  function htmxLoad(url, offcanvasId) {
    if (typeof htmx === 'undefined') return;
    htmx.ajax('GET', url, { target: '#offcanvas-container-cuentas', swap: 'innerHTML' })
      .then(() => showOffcanvas(offcanvasId));
  }

  function attachTableListeners() {
    const panel = d.querySelector(PANEL_SELECTOR);
    if (!panel) return;

    panel.addEventListener('click', (ev) => {
      const btnVer = ev.target.closest('.btn-ver-cuenta');
      const btnEditar = ev.target.closest('.btn-editar-cuenta');
      const btnEliminar = ev.target.closest('.btn-eliminar-cuenta');

      if (btnVer) {
        ev.preventDefault();
        const uuid = btnVer.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/detalle/`, 'offcanvas-cuenta-detalle');
        return;
      }

      if (btnEditar) {
        ev.preventDefault();
        const uuid = btnEditar.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/editar/`, 'offcanvas-cuenta-editar');
        return;
      }

      if (btnEliminar) {
        ev.preventDefault();
        const uuid = btnEliminar.dataset.uuid;
        if (uuid && confirm('¿Está seguro de que desea eliminar esta cuenta contable?')) {
          if (w.CuentaEditor && typeof w.CuentaEditor.delete === 'function') {
            w.CuentaEditor.delete(uuid);
          }
        }
      }
    });
  }

  function init() {
    attachTableListeners();
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Exportar API pública -- CuentaEditor llama a reload() tras crear/editar/eliminar
  w.CuentaList = Object.freeze({
    init,
    reload: () => d.body.dispatchEvent(new CustomEvent('cuenta-updated')),
  });
})(window, document);
