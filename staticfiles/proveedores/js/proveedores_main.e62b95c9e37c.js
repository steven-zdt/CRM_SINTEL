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
   * Delegación de eventos resiliente (v2.61.7)
   */
  function initListEvents() {
    if (listEventsBound) return;

    console.log(`${MOD} Inicializando delegación de eventos global...`);
    
    d.addEventListener('click', function(e) {
      // 1. Botón "Nuevo" (Resiliencia total: múltiples IDs y clases)
      const btnNuevo = e.target.closest('#btn-nuevo-proveedor, #btnNuevoProveedor, .btn-nuevo-proveedor');
      if (btnNuevo) {
        console.log(`${MOD} Click en "Nuevo" detectado via delegación`);
        e.preventDefault();
        w.Sintel.Proveedores.Form?.openOffcanvas(null);
        return;
      }

      // 2. Acciones de Tabla (Editar/Eliminar)
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
        if (identifier) w.Sintel.Proveedores.Form?.openOffcanvas(identifier);
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
    initialized = true;
    console.log(`${MOD} Módulo estabilizado.`);
  }

  // Registro en Namespace Global
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.Main = {
    init: init,
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
      setTimeout(init, 100);
    }
  });

  // Fallback si ya estamos en el tab al cargar
  if (d.readyState === 'complete') init();
  else w.addEventListener('load', init);

})(window, document);
