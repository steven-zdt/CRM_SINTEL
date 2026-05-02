/**
 * proveedores_main.js - Orquestador del Módulo Proveedores v2.61
 * Feature-Sliced Architecture: Responsable de la Grilla y Eventos de Lista.
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
        minWidth: 250,
        headerFilter: "input"
      },
      {
        title: "Nombre Comercial",
        field: "nombre_comercial",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback,
        width: 200,
        headerFilter: "input"
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
        width: 100,
        hozAlign: "center"
      },
      {
        title: "Acciones",
        field: "acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id = rowData.id;
          const isActive = rowData.activo === true;
          const deleteDisabled = isActive ? 'disabled' : '';
          const deleteClass = isActive ? 'opacity-50' : '';
          
          return `
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-primary btn-edit-proveedor" data-id="${id}" title="Editar">
                <i class="bi bi-pencil"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-delete-proveedor ${deleteClass}" data-id="${id}" ${deleteDisabled} title="Eliminar">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        width: 120,
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
   * Delegación de eventos para la lista
   */
  function initListEvents() {
    if (listEventsBound) return;

    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return;

    listEventsBound = true;

    gridEl.addEventListener('click', function(e) {
      const btn = e.target.closest('.btn-edit-proveedor, .btn-delete-proveedor');
      if (!btn) return;

      e.stopPropagation();

      if (btn.disabled || btn.classList.contains('disabled')) return;

      const id = btn.getAttribute('data-id');
      if (!id) return;

      if (btn.classList.contains('btn-edit-proveedor')) {
        w.AppProveedor?.openOffcanvas(id);
      } else if (btn.classList.contains('btn-delete-proveedor')) {
        w.AppProveedor?.eliminar(id);
      }
    });

    if (table) {
      table.on('rowClick', (e, row) => {
        // Patron del proyecto: prevenir rowClick durante eliminacion
        if (_eliminandoProveedor) return;

        // Evitar abrir offcanvas si el clic fue en un boton de accion
        const target = e.target || e.originalEvent?.target;
        if (target && target.closest && target.closest('button')) return;

        const id = row.getData().id;
        if (id) w.AppProveedor?.openOffcanvas(id);
      });
    }
  }

  function bindNuevoButton() {
    const btnNuevo = d.querySelector('#btn-nuevo-proveedor');
    if (!btnNuevo) return;

    if (newButtonBound && btnNuevo.dataset.boundNuevoProveedor === 'true') {
      return;
    }

    const replacement = btnNuevo.cloneNode(true);
    btnNuevo.parentNode.replaceChild(replacement, btnNuevo);
    replacement.dataset.boundNuevoProveedor = 'true';
    replacement.addEventListener('click', function () {
      w.AppProveedor?.openOffcanvas(null);
    });
    newButtonBound = true;
  }

  /**
   * Inicialización diferida del módulo
   */
  function init() {
    const tabEl = d.querySelector(TAB_ID);
    const gridEl = d.querySelector(GRID_ID);
    if (!tabEl || !gridEl) return;

    bindNuevoButton();

    if (!initialized) {
      initTable();
      initialized = true;
    } else if (table) {
      w.AppProveedor.refresh();
    }
  }

  // Registro en Namespace Global
  w.AppProveedor = w.AppProveedor || {};
  w.AppProveedor.init = init;
  w.AppProveedor.refresh = () => table && table.replaceData();

  // Lazy Load
  if (w.DOMUtils?.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(TAB_ID, init);
  } else {
    d.addEventListener('DOMContentLoaded', init);
  }

  d.addEventListener('tab-activated', function (event) {
    if (event.detail?.tabName === 'proveedores') {
      init();
    }
  });

})(window, document);
