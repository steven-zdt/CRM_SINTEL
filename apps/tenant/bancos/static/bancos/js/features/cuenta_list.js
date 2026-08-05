// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * cuenta_list.js - Controlador de Lista de Cuentas Bancarias
 * Namespace: window.Sintel.Bancos.CuentaList
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX (#cuentas-panel,
 * cargada por atributos hx-get/hx-trigger declarados en list_bancos.html).
 * Columnas/orden/paginacion viven en tables.py/views.py (server-side).
 * Las acciones de fila (editar/eliminar) las maneja bancos.main.js via
 * delegacion global sobre document.body -- no se tocan aqui.
 */
(function (w, d) {
  'use strict';

  function refresh() {
    d.body.dispatchEvent(new CustomEvent('cuenta-updated'));
  }

  // init()/redraw() ya no inicializan nada (el panel HTMX se auto-carga con
  // hx-trigger="load"); se conservan como no-ops porque bancos.main.js las
  // invoca al activarse el tab/sub-tab de cuentas.
  function init() {}
  function redraw() {}

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.CuentaList = {
    init: init,
    refresh: refresh,
    redraw: redraw
  };

})(window, document);
