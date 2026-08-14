/**
 * plantilla_list.js - Feature List para PlantillaContable
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#plantillas-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_plantillas.html).
 * Este archivo solo maneja: acciones de fila (ver/editar/eliminar), apertura
 * de offcanvas, y el disparo del evento que hace que HTMX vuelva a pedir la
 * tabla al backend tras una mutacion. Columnas/orden/paginacion/filtros viven
 * en tables.py/views.py (server-side) -- no reimplementar aqui.
 */
(function (w, d) {
  'use strict';

  const PANEL_SELECTOR = '#plantillas-panel';
  const API_URL = '/api/v1/contabilidad/plantillas-contables/';

  function showOffcanvas(id) {
    const el = d.getElementById(id);
    if (!el) return;
    w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
  }

  function htmxLoad(url, offcanvasId) {
    if (typeof htmx === 'undefined') return;
    htmx.ajax('GET', url, { target: '#offcanvas-container-plantilla', swap: 'innerHTML' })
      .then(() => showOffcanvas(offcanvasId));
  }

  function attachTableListeners() {
    const panel = d.querySelector(PANEL_SELECTOR);
    if (!panel) return;

    panel.addEventListener('click', async (ev) => {
      const btnVer = ev.target.closest('.btn-ver-plantilla');
      const btnEditar = ev.target.closest('.btn-editar-plantilla');
      const btnEliminar = ev.target.closest('.btn-eliminar-plantilla');

      if (btnVer) {
        ev.preventDefault();
        const uuid = btnVer.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/detalle/`, 'offcanvas-plantilla-detalle');
        return;
      }

      if (btnEditar) {
        ev.preventDefault();
        const uuid = btnEditar.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/editar/`, 'offcanvas-plantilla-editar');
        return;
      }

      if (btnEliminar) {
        ev.preventDefault();
        const uuid = btnEliminar.dataset.uuid;
        if (uuid && (await w.UIManager?.confirm('Eliminar esta plantilla contable? Se eliminaran todas sus lineas.'))) {
          if (w.PlantillaEditor && typeof w.PlantillaEditor.delete === 'function') {
            w.PlantillaEditor.delete(uuid);
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

  // Exportar API pública -- PlantillaEditor llama a reload() tras crear/editar/eliminar
  w.PlantillaList = Object.freeze({
    init,
    reload: () => d.body.dispatchEvent(new CustomEvent('plantilla-updated')),
  });
})(window, document);
