// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * proveedores_main.js - Orquestador del Módulo Proveedores v3.7
 * Feature-Sliced Architecture: Responsable de la Grilla y Eventos de Lista.
 * v3.7: Boton Nuevo delegado a HTMX declarativo (hx-get). JS solo maneja editar/eliminar.
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:main]';
  const TAB_ID = '#tab-proveedores';
  const GRID_ID = '#grid-proveedores';
  const SEARCH_ID = '#search-proveedor';
  const API_URL = '/api/v1/proveedores/';
  let table = null;
  let initialized = false;
  let listEventsBound = false;
  let newButtonBound = false;
  let _eliminandoProveedor = false; // Flag para prevenir rowClick durante eliminacion

  /**
   * Formatea el estado de cuentas por pagar de un proveedor.
   * Lee el campo cuentas_pagar_resumen inyectado por el backend.
   */
  function fmtCuentasPagar(cell) {
    const data = cell.getRow().getData();
    const c = data.cuentas_pagar_resumen;
    if (!c || c.total_count === 0) {
      return '<span class="text-muted small">Sin facturas</span>';
    }

    const fmt = (v) => parseFloat(v || 0).toLocaleString('es-CO', {
      style: 'currency', currency: 'COP', maximumFractionDigits: 0
    });

    const parts = [];

    if (c.pendiente_count > 0) {
      parts.push(
        `<span class="badge bg-warning text-dark" title="Facturas pendientes de pago">` +
        `<i class="bi bi-clock me-1"></i>${c.pendiente_count} pend.</span> ` +
        `<span class="small text-warning fw-semibold">${fmt(c.pendiente_monto)}</span>`
      );
    }
    if (c.pagada_count > 0 && c.pendiente_count === 0) {
      parts.push(
        `<span class="badge bg-success" title="Todas las facturas pagadas">` +
        `<i class="bi bi-check-circle me-1"></i>${c.pagada_count} pagadas</span>`
      );
    } else if (c.pagada_count > 0) {
      parts.push(
        `<span class="badge bg-light text-success border border-success" title="${c.pagada_count} facturas pagadas">` +
        `${c.pagada_count} pag.</span>`
      );
    }

    return parts.join(' ') || '<span class="text-muted small">—</span>';
  }

  /**
   * Definir columnas vinculadas a TabulatorFactory
   */
  function getColumns() {
    return [
      { title: "ID", field: "id", width: 60, headerSort: false },
      {
        title: "NIT/Documento",
        field: "nit",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback,
        width: 150,
        headerFilter: "input"
      },
      {
        title: "Razón Social",
        field: "razon_social",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback,
        minWidth: 200,
        headerFilter: "input"
      },
      {
        title: "Cuentas por Pagar",
        field: "cuentas_pagar_resumen",
        formatter: fmtCuentasPagar,
        minWidth: 220,
        headerSort: false,
        tooltip: false,
      },
      {
        title: "Estado",
        field: "estado",
        formatter: function(cell) {
          const estado = cell.getValue();
          return estado === 'Activo'
            ? '<span class="badge bg-success">Activo</span>'
            : '<span class="badge bg-secondary">Inactivo</span>';
        },
        width: 90,
        hozAlign: "center"
      },
      {
        title: "Acciones",
        field: "acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const identifier = rowData.uuid || rowData.id;
          const isActive = rowData.activo === true;
          const deleteDisabled = isActive ? 'disabled' : '';
          const deleteClass = isActive ? 'opacity-50' : '';

          return `
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-primary btn-edit-proveedor" data-id="${identifier}" title="Editar">
                <i class="bi bi-pencil"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-delete-proveedor ${deleteClass}" data-id="${identifier}" ${deleteDisabled} title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        width: 110,
        headerSort: false
      }
    ];
  }

  /**
   * Inicializar tabla
   */
  function initTable() {
    if (!w.TabulatorFactory) return console.error(`${MOD} TabulatorFactory no disponible`);

    // Destruir previa si existe
    if (w.SintelProveedoresTables?.proveedores) {
        w.SintelProveedoresTables.proveedores.destroy();
    }

    table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), {
      searchInputSelector: SEARCH_ID
    });

    if (!w.SintelProveedoresTables) w.SintelProveedoresTables = {};
    w.SintelProveedoresTables.proveedores = table;

    initListEvents();
  }

  /**
   * Delegación de eventos resiliente (v2.61.7)
   */
  function initListEvents() {
    if (listEventsBound) return;

    console.log(`${MOD} Inicializando delegación de eventos global...`);
    
    d.addEventListener('click', function(e) {
      // Acciones de Tabla (Editar/Eliminar)
      // NOTA: Boton "Nuevo" es HTMX declarativo (hx-get en [data-create-button]) — no requiere JS.
      const btnAction = e.target.closest('.btn-edit-proveedor, .btn-delete-proveedor');
      if (btnAction) {
        e.stopPropagation();
        if (btnAction.disabled || btnAction.classList.contains('disabled')) return;
        
        const id = btnAction.getAttribute('data-id');
        if (!id) return;

        if (btnAction.classList.contains('btn-edit-proveedor')) {
          w.Sintel.Proveedores.Form?.openOffcanvas(id);
        } else if (btnAction.classList.contains('btn-delete-proveedor')) {
          w.Sintel.Proveedores.Form?.eliminar(id);
        }
      }
    });

    listEventsBound = true;

    // Vinculación con eventos de Tabulator
    if (table) {
      table.on('rowClick', (e, row) => {
        if (_eliminandoProveedor) return;
        const target = e.target || e.originalEvent?.target;
        if (target && target.closest && target.closest('button')) return;
        const rowData = row.getData();
        const identifier = rowData.uuid || rowData.id;
        // rowClick abre detalle (read-only + historial facturas de compra)
        if (identifier) w.Sintel.Proveedores.Form?.openDetalle(identifier);
      });
    }
  }

  /**
   * Vincula eventos de cambio de subtab para redibujar Tabulator
   */
  function initSubtabRedraws() {
    const tabDirectorio = d.querySelector('#subtab-directorio-btn');
    const tabCuentasPagar = d.querySelector('#subtab-cuentas-pagar-btn');

    if (tabDirectorio) {
      tabDirectorio.addEventListener('shown.bs.tab', function() {
        if (table) table.redraw(true);
      });
    }

    if (tabCuentasPagar) {
      // shown.bs.tab: init() primero + redraw (skill: tabulator.md §6)
      tabCuentasPagar.addEventListener('shown.bs.tab', function() {
        console.log(`${MOD} Subtab Cuentas por Pagar activado.`);
        const cxp = w.Sintel?.Proveedores?.CuentasPagarList;
        if (cxp?.init) cxp.init();
        requestAnimationFrame(() => {
          if (w.SintelProveedoresTables?.cuentas_pagar?.redraw) {
            w.SintelProveedoresTables.cuentas_pagar.redraw(true);
          }
        });
      });
    }
  }

  /**
   * Inicialización controlada del módulo
   */
  function init() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return; // No estamos en la vista de proveedores

    if (initialized) {
      if (table) w.Sintel.Proveedores.Main.refresh();
      return;
    }

    console.log(`${MOD} Ejecutando orquestación inicial...`);
    initTable();
    initSubtabRedraws();
    initialized = true;
    console.log(`${MOD} Módulo estabilizado.`);
  }

  function redraw() {
    if (table && typeof table.redraw === 'function') table.redraw(true);
  }

  // Registro en Namespace Global
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.Main = {
    init: init,
    redraw: redraw,
    refresh: () => {
      if (table && typeof table.replaceData === 'function') {
        table.replaceData().catch(err => console.warn(`${MOD} Error al refrescar tabla:`, err));
      }
    }
  };

  // Delegación inmediata (disponible antes de la carga del tab)
  initListEvents();

  // Escuchar activación de tab
  d.addEventListener('tab-activated', function (event) {
    if (event.detail?.tabName === 'proveedores') {
      setTimeout(function () {
        init();
        // Forzar redibujado: Tabulator puede haber inicializado en contenedor oculto
        requestAnimationFrame(function () {
          redraw();
        });
      }, 100);
    }
  });

  // Fallback: solo inicializar si el tab ya es visible al cargar la página
  // (evita inicializar Tabulator en contenedor oculto con width=0)
  function _initSiVisible() {
    const section = d.getElementById('tab-proveedores');
    if (section && section.style.display !== 'none') {
      init();
    }
  }

  if (d.readyState === 'complete') _initSiVisible();
  else w.addEventListener('load', _initSiVisible);

})(window, document);
