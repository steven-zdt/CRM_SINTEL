// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * cuentas_pagar_list.js - Submodulo Cuentas por Pagar List
 * Fase 5-BIS: tabla server-rendered via django-tables2 + HTMX
 * (#cuentas-pagar-panel, cargada por atributos hx-get/hx-trigger declarados
 * en proveedores_list.html). Columnas viven en tables.py/views.py
 * (server-side). El boton "Abono" (.btn-abono-cuentas-pagar) sigue siendo
 * manejado por cuentas_pagar_editor.js (delegacion global en document, sin
 * cambios necesarios ahi).
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:cuentas-pagar]';

  // Funcion global de refresco: dispara el evento que el panel HTMX escucha
  // via hx-trigger="load, cuentas-pagar-updated from:body".
  w.refreshCuentasPagarTable = function () {
    d.body.dispatchEvent(new CustomEvent('cuentas-pagar-updated'));
  };

  // Exportar al Namespace (mantiene compatibilidad con
  // cuentas_pagar_editor.js, que llama a .refresh() tras registrar un abono)
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.CuentasPagarList = {
    refresh: () => w.refreshCuentasPagarTable()
  };

})(window, document);
