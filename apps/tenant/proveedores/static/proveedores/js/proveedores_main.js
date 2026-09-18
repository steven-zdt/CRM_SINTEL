// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * proveedores_main.js - Orquestador del Módulo Proveedores
 * Fase 5-BIS: la grilla "Directorio de Proveedores" es server-rendered via
 * django-tables2 + HTMX (#proveedores-panel, cargada por atributos
 * hx-get/hx-trigger declarados en proveedores_list.html). Columnas y el
 * resumen de cuentas por pagar viven en tables.py/views.py/selectors.py
 * (server-side).
 *
 * Este archivo solo conserva la delegacion de eventos: editar/eliminar
 * (botones) y click-en-fila para abrir el detalle (data-uuid en <tr>, ver
 * row_attrs en tables.py) -- ambos sobre document.body, robustos a los
 * swaps HTMX del panel.
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:main]';
  let listEventsBound = false;

  // Funcion global de refresco: dispara el evento que el panel HTMX escucha
  // via hx-trigger="load, proveedor-updated from:body".
  w.refreshProveedoresTable = function () {
    d.body.dispatchEvent(new CustomEvent('proveedor-updated'));
  };

  /**
   * Delegación de eventos resiliente (v2.61.7)
   */
  function initListEvents() {
    if (listEventsBound) return;

    console.log(`${MOD} Inicializando delegación de eventos global...`);

    d.addEventListener('click', function(e) {
      // Acciones de Tabla (Ver/Editar/Representantes/Eliminar)
      // NOTA: Boton "Nuevo" es HTMX declarativo (hx-get en [data-create-button]) — no requiere JS.
      const btnAction = e.target.closest(
        '.btn-view-proveedor, .btn-edit-proveedor, .btn-representantes-proveedor, .btn-delete-proveedor'
      );
      if (btnAction) {
        e.stopPropagation();
        if (btnAction.disabled || btnAction.classList.contains('disabled')) return;

        const id = btnAction.getAttribute('data-id');
        if (!id) return;

        if (btnAction.classList.contains('btn-view-proveedor')) {
          w.Sintel.Proveedores.Form?.openDetalle(id);
        } else if (btnAction.classList.contains('btn-edit-proveedor')) {
          w.Sintel.Proveedores.Form?.openOffcanvas(id);
        } else if (btnAction.classList.contains('btn-representantes-proveedor')) {
          w.Sintel.Proveedores.Form?.openDetalle(id, 'representantes');
        } else if (btnAction.classList.contains('btn-delete-proveedor')) {
          w.Sintel.Proveedores.Form?.eliminar(id);
        }
        return;
      }

      // Click en fila (fuera de un boton) abre detalle -- replica el
      // rowClick de Tabulator. data-uuid viene de row_attrs en tables.py.
      const row = e.target.closest('#proveedores-panel tbody tr[data-uuid]');
      if (row) {
        if (e.target.closest('button')) return;
        const identifier = row.getAttribute('data-uuid');
        if (identifier) w.Sintel.Proveedores.Form?.openDetalle(identifier);
      }

      // Chips de filtro (Directorio / Cuentas por Pagar): marcar visualmente
      // el chip clickeado como activo dentro de su propio grupo -- hx-get/
      // hx-include ya disparan la recarga de la tabla via HTMX, esto solo
      // sincroniza el estado visual del boton.
      const chip = e.target.closest('[data-filtro-prov], [data-filtro-cxp]');
      if (chip) {
        const grupo = chip.closest('#filtros-tipo-proveedores, #filtros-estado-cuentas-pagar');
        grupo?.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
        chip.classList.add('active');
      }
    });

    listEventsBound = true;
  }

  /**
   * Vincula eventos de cambio de subtab (v3.17.0: agregado soporte para Representantes)
   */
  function initSubtabRedraws() {
    const tabCuentasPagar = d.querySelector('#subtab-cuentas-pagar-btn');
    const tabRepresentantes = d.querySelector('#subtab-representantes-btn');

    if (tabCuentasPagar) {
      tabCuentasPagar.addEventListener('shown.bs.tab', function() {
        console.log(`${MOD} Subtab Cuentas por Pagar activado.`);
      });
    }

    if (tabRepresentantes) {
      // Representantes: inicializado por representantes_directory.html (lazy-load)
      tabRepresentantes.addEventListener('shown.bs.tab', function() {
        console.log(`${MOD} Subtab Representantes activado (v3.17.0).`);
      });
    }
  }

  // Registro en Namespace Global
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.Main = {
    init: initListEvents,
    redraw: () => {},
    refresh: () => w.refreshProveedoresTable()
  };

  initListEvents();
  initSubtabRedraws();

})(window, document);
