/**
 * periodo_list.js - Feature List para PeriodoContable
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#periodos-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_periodos.html).
 * Este archivo solo maneja: acciones de fila (ver/editar/cerrar/eliminar),
 * apertura de offcanvas, y el disparo del evento que hace que HTMX vuelva a
 * pedir la tabla al backend tras una mutacion. Columnas/orden/paginacion/
 * filtros viven en tables.py/views.py (server-side) -- no reimplementar aqui.
 */
(function (w, d) {
  'use strict';

  const PANEL_SELECTOR = '#periodos-panel';
  const API_URL = '/api/v1/contabilidad/periodos-contables/';

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
    htmx.ajax('GET', url, { target: '#offcanvas-container-periodo', swap: 'innerHTML' })
      .then(() => showOffcanvas(offcanvasId));
  }

  function attachTableListeners() {
    const panel = d.querySelector(PANEL_SELECTOR);
    if (!panel) return;

    panel.addEventListener('click', (ev) => {
      const btnVer = ev.target.closest('.btn-ver-periodo');
      const btnEditar = ev.target.closest('.btn-editar-periodo');
      const btnCerrar = ev.target.closest('.btn-cerrar-periodo');
      const btnEliminar = ev.target.closest('.btn-eliminar-periodo');

      if (btnVer) {
        ev.preventDefault();
        const uuid = btnVer.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/detalle/`, 'offcanvas-periodo-detalle');
        return;
      }

      if (btnEditar) {
        ev.preventDefault();
        const uuid = btnEditar.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/editar/`, 'offcanvas-periodo-editar');
        return;
      }

      if (btnCerrar) {
        ev.preventDefault();
        const uuid = btnCerrar.dataset.uuid;
        if (uuid && w.PeriodoEditor && typeof w.PeriodoEditor.cerrar === 'function') {
          w.PeriodoEditor.cerrar(uuid);
        }
        return;
      }

      if (btnEliminar) {
        ev.preventDefault();
        const uuid = btnEliminar.dataset.uuid;
        if (uuid && confirm('¿Está seguro de que desea eliminar este periodo contable?')) {
          if (w.PeriodoEditor && typeof w.PeriodoEditor.delete === 'function') {
            w.PeriodoEditor.delete(uuid);
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

  // Exportar API pública -- PeriodoEditor llama a reload() tras crear/editar/cerrar/eliminar
  w.PeriodoList = Object.freeze({
    init,
    reload: () => d.body.dispatchEvent(new CustomEvent('periodo-updated')),
  });
})(window, document);
