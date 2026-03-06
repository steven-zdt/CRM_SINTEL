/**
 * gastos_resoluciones_list.js - Módulo de Listado de Resoluciones DIAN v2.60 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * 
 * ⚠️ v2.60: Lista todas las resoluciones DIAN disponibles en el workspace de gastos
 * - Inicialización de Tabulator Factory para resoluciones
 * - Muestra estado vigente, rangos, fechas y conteo de documentos
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.gastosAPI (definido en gastos.api.js) - Capa de Datos
 * - w.AppGastos (definido en gastos_main.js) - Para refrescar estado
 */
(function (w, d) {
  'use strict';

  const MOD = '[gastos.resoluciones.list]';
  const TABLE_SELECTOR = '#grid-resoluciones';
  const API_URL = '/api/v1/resoluciones-dian/';
  const TAB_ID = '#tab-gastos';
  let table = null;

  // Helper: Formatear fecha
  function fmtDate(dateStr) {
    if (!dateStr) return '---';
    try {
      return new Date(dateStr).toLocaleDateString('es-CO');
    } catch (e) {
      return dateStr;
    }
  }

  // Definir columnas específicas del módulo
  function getColumns() {
    return [
      {
        title: "Número Resolución",
        field: "numero_resolucion",
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
        title: "Prefijo",
        field: "prefijo",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '---';
        }
      },
      {
        title: "Rango",
        field: "rango_desde",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const desde = rowData.rango_desde || 0;
          const hasta = rowData.rango_hasta || 0;
          return `${desde} - ${hasta}`;
        }
      },
      {
        title: "Fecha Emisión",
        field: "fecha_resolucion",
        formatter: function(cell) {
          return fmtDate(cell.getValue());
        }
      },
      {
        title: "Fecha Inicio",
        field: "fecha_inicio",
        formatter: function(cell) {
          return fmtDate(cell.getValue());
        }
      },
      {
        title: "Fecha Fin",
        field: "fecha_fin",
        formatter: function(cell) {
          return fmtDate(cell.getValue());
        }
      },
      {
        title: "Documentos",
        field: "conteo_documentos",
        formatter: function(cell) {
          const val = cell.getValue() || 0;
          return `<span class="badge bg-secondary">${val}</span>`;
        },
        hozAlign: "center"
      },
      {
        title: "Estado",
        field: "vigente",
        formatter: function(cell) {
          const vigente = cell.getValue() === true;
          if (vigente) {
            return '<span class="badge bg-success">Vigente</span>';
          } else {
            return '<span class="badge bg-secondary">Inactiva</span>';
          }
        },
        headerSort: false
      }
    ];
  }

  // Inicializar tabla
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(`${MOD} TabulatorFactory no está disponible`);
      return null;
    }

    const columns = getColumns();
    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, columns, {
      // Sin búsqueda por ahora (puede agregarse después)
    });

    return table;
  }

  // Función para refrescar tabla
  function refresh() {
    if (table) {
      table.replaceData();
    }
  }

  // Función para inicializar el módulo completo
  function inicializarModulo() {
    console.log(`${MOD} Inicializando módulo de listado de resoluciones...`);
    
    // Inicializar tabla
    table = initTable();
    
    // Exponer módulo globalmente
    if (!w.AppGastos) {
      w.AppGastos = {};
    }
    
    // Asignar funciones principales
    w.AppGastos.resolucionesTable = table;
    w.AppGastos.refreshResoluciones = refresh;
    
    console.log(`${MOD} Módulo de listado de resoluciones inicializado`);
  }

  // Lazy Loading: Inicializar solo cuando el workspace de gastos sea visible
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    // Usar el selector del workspace de gastos
    w.DOMUtils.onVisibleOnce('#workspace-gastos', function() {
      console.log(`${MOD} Workspace de gastos visible, inicializando listado de resoluciones...`);
      // Esperar un poco para que la tabla principal se inicialice primero
      setTimeout(() => {
        inicializarModulo();
      }, 500);
    });
  } else {
    // Fallback si DOMUtils no está disponible
    console.warn(`${MOD} DOMUtils no disponible, inicializando inmediatamente`);
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      
      setTimeout(() => {
        inicializarModulo();
      }, 500);
    }
    initFallback();
  }

  // También inicializar cuando el tab de gastos se muestre (Bootstrap event)
  d.addEventListener('shown.bs.tab', function(e) {
    const target = e.target.getAttribute('data-bs-target');
    if (target && (target === '#pane-gastos' || target.includes('gastos'))) {
      console.log(`${MOD} Tab de gastos mostrado, verificando inicialización de resoluciones...`);
      // Asegurar que el módulo esté inicializado
      if (!w.AppGastos || !w.AppGastos.resolucionesTable) {
        console.log(`${MOD} Módulo no inicializado, inicializando desde evento shown.bs.tab...`);
        setTimeout(() => {
          inicializarModulo();
        }, 500);
      } else {
        // Refrescar datos
        refresh();
      }
    }
  });

})(window, document);
