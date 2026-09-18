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
  const KPI_URL = '/api/v1/proveedores/cuentas-pagar/dashboard-kpis/';
  let kpiBound = false;

  // Funcion global de refresco: dispara el evento que el panel HTMX escucha
  // via hx-trigger="load, cuentas-pagar-updated from:body".
  w.refreshCuentasPagarTable = function () {
    d.body.dispatchEvent(new CustomEvent('cuentas-pagar-updated'));
  };

  function _fmtCop(v) {
    const n = parseFloat(v) || 0;
    // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
    if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
      return '$' + w.DOMUtils.formatCurrency(Math.round(n), { minimumFractionDigits: 0, maximumFractionDigits: 0, showSymbol: false });
    }
    return '$' + Math.round(n).toLocaleString('es-CO');
  }

  /**
   * Carga los KPIs del resumen (Pendiente/Vencida/Pagado historico) --
   * mismo patron visual que la barra de KPIs de clientes/Cartera.
   */
  async function cargarKPIs() {
    try {
      const resp = await fetch(KPI_URL, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!resp.ok) return;
      const data = await resp.json();
      const el = (id) => d.getElementById(id);
      if (el('cxp-pendiente-monto')) el('cxp-pendiente-monto').textContent = _fmtCop(data.deuda_total_pendiente);
      if (el('cxp-vencida-monto')) el('cxp-vencida-monto').textContent = _fmtCop(data.deuda_vencida);
      if (el('cxp-pagado-monto')) el('cxp-pagado-monto').textContent = _fmtCop(data.total_pagado_historico);
    } catch (err) {
      console.error(`${MOD} Error cargando KPIs:`, err);
    }
  }

  function initKPIRefresh() {
    if (kpiBound) return;
    kpiBound = true;
    cargarKPIs();
    // Mismo evento que recarga la tabla -- se mantienen sincronizados.
    d.body.addEventListener('cuentas-pagar-updated', cargarKPIs);
  }

  // Exportar al Namespace (mantiene compatibilidad con
  // cuentas_pagar_editor.js, que llama a .refresh() tras registrar un abono)
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.CuentasPagarList = {
    refresh: () => w.refreshCuentasPagarTable()
  };

  initKPIRefresh();

})(window, document);
