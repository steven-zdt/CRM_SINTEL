// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * extracto_list.js - Controlador de Lista de Extractos Bancarios
 * Namespace: window.Sintel.Bancos.ExtractoList
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#extractos-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_bancos.html).
 * Columnas/orden/paginacion viven en tables.py/views.py (server-side).
 * Las acciones de fila (ver/conciliar/procesar/eliminar) las maneja
 * bancos.main.js via delegacion global sobre document.body -- no se tocan aqui.
 */
(function (w, d) {
  'use strict';

  const MOD = '[bancos:extracto_list]';

  function refresh() {
    d.body.dispatchEvent(new CustomEvent('extracto-updated'));
  }

  // init()/redraw() ya no inicializan nada (el panel HTMX se auto-carga con
  // hx-trigger="load"); se conservan como no-ops porque bancos.main.js las
  // invoca al activarse el tab/sub-tab de extractos.
  function init() {}
  function redraw() {}

  async function procesarExtracto(uuid) {
    if (!uuid) return;

    if (w.UIManager?.showLoading) {
      w.UIManager.showLoading('Procesando extracto bancario...');
    }

    const api = w.Sintel.Bancos.API;
    if (!api || !api.extractos) return;

    const res = await api.extractos.procesar(uuid);

    if (w.UIManager?.hideLoading) {
      w.UIManager.hideLoading();
    }

    if (!res.ok) {
      return w.UIManager?.handleError(res, MOD);
    }

    if (w.UIManager?.showSuccess) {
      w.UIManager.showSuccess('Extracto procesado exitosamente.');
    }

    refresh();
  }

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.ExtractoList = {
    init: init,
    refresh: refresh,
    redraw: redraw,
    procesarExtracto: procesarExtracto
  };

})(window, document);
