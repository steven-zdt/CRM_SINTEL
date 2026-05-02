/**
 * resolucion_dian_main.js - Modulo Listado de Resoluciones DIAN v2.61 - Feature-Sliced Architecture
 * Namespace: w.AppResolucionDIAN
 *
 * Reemplaza: gastos_resoluciones_list.js
 *
 * Dependencias globales:
 * - w.TabulatorFactory
 * - w.gastosAPI  (gastos.api.js)
 * - w.DOMUtils
 */
(function (w, d) {
  'use strict';

  const MOD = '[resolucion-dian.main]';
  const TABLE_SELECTOR = '#grid-resoluciones';
  const API_URL = '/api/v1/resoluciones-dian/';

  let table = null;

  if (!w.AppResolucion) {
    w.AppResolucion = {};
  }
  // Compatibilidad: alias para código legacy
  if (!w.AppResolucionDIAN) {
    w.AppResolucionDIAN = w.AppResolucion;
  }

  // ---------------------------------------------------------------------------
  // HELPERS
  // ---------------------------------------------------------------------------

  function fmtDate(dateStr) {
    if (!dateStr) return '---';
    try { return new Date(dateStr).toLocaleDateString('es-CO'); } catch (e) { return dateStr; }
  }

  // ---------------------------------------------------------------------------
  // COLUMNAS TABULATOR
  // ---------------------------------------------------------------------------

  function getColumns() {
    return [
      {
        title: 'Numero Resolucion',
        field: 'numero_resolucion',
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const vigente = rowData.vigente === true;
          const val = cell.getValue();
          if (vigente) {
            return `<strong>${val}</strong> <span class="badge bg-success badge-sm">VIGENTE</span>`;
          }
          return val;
        }
      },
      {
        title: 'Prefijo',
        field: 'prefijo',
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '---';
        }
      },
      {
        title: 'Rango',
        field: 'rango_desde',
        formatter: function(cell) {
          const data = cell.getRow().getData();
          return `${data.rango_desde || 0} - ${data.rango_hasta || 0}`;
        }
      },
      {
        title: 'Fecha Emision',
        field: 'fecha_resolucion',
        formatter: function(cell) { return fmtDate(cell.getValue()); }
      },
      {
        title: 'Fecha Inicio',
        field: 'fecha_inicio',
        formatter: function(cell) { return fmtDate(cell.getValue()); }
      },
      {
        title: 'Fecha Fin',
        field: 'fecha_fin',
        formatter: function(cell) { return fmtDate(cell.getValue()); }
      },
      {
        title: 'Documentos',
        field: 'conteo_documentos',
        formatter: function(cell) {
          const val = cell.getValue() || 0;
          return `<span class="badge bg-secondary">${val}</span>`;
        },
        hozAlign: 'center'
      },
      {
        title: 'Estado',
        field: 'vigente',
        formatter: function(cell) {
          return cell.getValue() === true
            ? '<span class="badge bg-success">Vigente</span>'
            : '<span class="badge bg-secondary">Inactiva</span>';
        },
        headerSort: false
      },
      {
        title: 'Acciones',
        field: 'id',
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id      = parseInt(rowData.id, 10);
          const conteo  = parseInt(rowData.conteo_documentos, 10) || 0;
          const vigente = rowData.vigente === true;

          const btnVer = `<button type="button" class="btn btn-sm btn-link text-primary p-0 me-2"
              data-action="ver" data-id="${id}" title="Ver detalle">
              <i class="bi bi-eye"></i>
            </button>`;

          let btnAction = '';
          if (vigente) {
            btnAction = `<button type="button" class="btn btn-sm btn-link text-warning p-0"
                data-action="desactivar" data-id="${id}" title="Desactivar resolucion">
                <i class="bi bi-toggle-off"></i>
              </button>`;
          } else if (conteo === 0) {
            btnAction = `<button type="button" class="btn btn-sm btn-link text-danger p-0"
                data-action="eliminar" data-id="${id}" title="Eliminar resolucion inactiva">
                <i class="bi bi-trash"></i>
              </button>`;
          } else {
            btnAction = `<button type="button" class="btn btn-sm btn-link text-muted p-0 opacity-50"
                disabled title="No se puede eliminar: ${conteo} documento(s) asociado(s)">
                <i class="bi bi-trash"></i>
              </button>`;
          }

          return btnVer + btnAction;
        },
        headerSort: false,
        hozAlign: 'center',
        width: 110
      }
    ];
  }

  // ---------------------------------------------------------------------------
  // TABLA
  // ---------------------------------------------------------------------------

  function configurarEventosDelegados() {
    const container = d.querySelector(TABLE_SELECTOR);
    if (!container) {
      console.warn(`${MOD} Contenedor ${TABLE_SELECTOR} no encontrado para delegacion de eventos`);
      return;
    }
    container.addEventListener('click', function(e) {
      const btn = e.target.closest('button[data-action]');
      if (!btn || btn.disabled) return;
      e.preventDefault();
      e.stopPropagation();

      const action = btn.getAttribute('data-action');
      const id     = parseInt(btn.getAttribute('data-id'), 10);
      if (!id || isNaN(id)) return;

      switch (action) {
        case 'ver':
          w.AppResolucion?.ver?.(id);
          break;
        case 'desactivar':
          w.AppResolucion?.desactivar?.(id);
          break;
        case 'eliminar':
          w.AppResolucion?.eliminar?.(id);
          break;
      }
    });
  }

  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(`${MOD} TabulatorFactory no disponible`);
      return null;
    }
    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, getColumns(), {});
    return table;
  }

  function refresh() {
    if (table) table.replaceData();
  }

  // ---------------------------------------------------------------------------
  // INICIALIZACION
  // ---------------------------------------------------------------------------

  function inicializarModulo() {
    console.log(`${MOD} Inicializando modulo de resoluciones DIAN...`);
    table = initTable();
    configurarEventosDelegados();

    w.AppResolucion.table = table;
    w.AppResolucion.refresh = refresh;
    w.AppResolucionDIAN = w.AppResolucion;

    if (!w.AppGastos) {
      w.AppGastos = {};
    }
    w.AppGastos.refreshResoluciones = refresh;

    console.log(`${MOD} Modulo inicializado (w.AppResolucion)`);
  }

  // LAZY: solo cuando el workspace sea visible
  if (w.DOMUtils?.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce('#workspace-gastos', function() {
      setTimeout(() => inicializarModulo(), 500);
    });
  } else {
    console.warn(`${MOD} DOMUtils no disponible, iniciando inmediatamente`);
    function initFallback() {
      if (d.readyState === 'loading') { d.addEventListener('DOMContentLoaded', initFallback); return; }
      setTimeout(() => inicializarModulo(), 500);
    }
    initFallback();
  }

  // Re-inicializar cuando se muestre el tab de gastos
  d.addEventListener('shown.bs.tab', function(e) {
    const target = e.target.getAttribute('data-bs-target');
    if (target && (target === '#pane-gastos' || target.includes('gastos'))) {
      if (!w.AppResolucion.table) {
        setTimeout(() => inicializarModulo(), 500);
      } else {
        refresh();
      }
    }
  });

})(window, document);
