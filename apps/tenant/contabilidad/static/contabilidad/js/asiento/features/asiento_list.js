/**
 * asiento_list.js - Feature List para AsientoContable
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#asientos-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_asientos.html).
 * Este archivo solo maneja: acciones de fila (ver/editar/aprobar/eliminar),
 * apertura de offcanvas, y el disparo del evento que hace que HTMX vuelva a
 * pedir la tabla al backend tras una mutacion. Columnas/orden/paginacion/
 * filtros viven en tables.py/views.py (server-side) -- no reimplementar aqui.
 */
(function (w, d) {
  'use strict';

  const PANEL_SELECTOR = '#asientos-panel';
  const API_URL = '/api/v1/contabilidad/asientos-contables/';

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
    htmx.ajax('GET', url, { target: '#offcanvas-container-asiento', swap: 'innerHTML' })
      .then(() => showOffcanvas(offcanvasId));
  }

  function attachTableListeners() {
    const panel = d.querySelector(PANEL_SELECTOR);
    if (!panel) return;

    panel.addEventListener('click', (ev) => {
      const btnVer = ev.target.closest('.btn-ver-asiento');
      const btnEditar = ev.target.closest('.btn-editar-asiento');
      const btnAprobar = ev.target.closest('.btn-aprobar-asiento');
      const btnEliminar = ev.target.closest('.btn-eliminar-asiento');

      if (btnVer) {
        ev.preventDefault();
        const uuid = btnVer.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/detalle/`, 'offcanvas-asiento-detalle');
        return;
      }

      if (btnEditar) {
        ev.preventDefault();
        const uuid = btnEditar.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/editar/`, 'offcanvas-asiento-editar');
        return;
      }

      if (btnAprobar) {
        ev.preventDefault();
        const uuid = btnAprobar.dataset.uuid;
        if (uuid && w.AsientoEditor && typeof w.AsientoEditor.aprobar === 'function') {
          w.AsientoEditor.aprobar(uuid);
        }
        return;
      }

      if (btnEliminar) {
        ev.preventDefault();
        const uuid = btnEliminar.dataset.uuid;
        if (uuid && confirm('¿Está seguro de que desea eliminar este asiento contable?')) {
          if (w.AsientoEditor && typeof w.AsientoEditor.delete === 'function') {
            w.AsientoEditor.delete(uuid);
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

  // Exportar API pública -- AsientoEditor llama a reload() tras crear/editar/aprobar/eliminar
  w.AsientoList = Object.freeze({
    init,
    reload: () => d.body.dispatchEvent(new CustomEvent('asiento-updated')),
  });
})(window, document);
