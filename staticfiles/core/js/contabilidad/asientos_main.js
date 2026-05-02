/**
 * asientos_main.js - Módulo Principal de Asientos Contables v2.60 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.60: Migración de DataTables a Tabulator Factory v2.40
 * - Inicialización de Tabulator Factory
 * - Event delegation para acciones de tabla
 * - Integración con offcanvas de creación/detalle
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.AppContabilidad (definido en asientos_form.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 */
(function (w, d) {
  'use strict';

  const MOD = '[asientos.main]';
  const TABLE_SELECTOR = '#grid-asientos';
  const SEARCH_SELECTOR = '#search-asiento';
  const FILTER_ESTADO_SELECTOR = '#filter-estado-asiento';
  const FILTER_CUADRATURA_SELECTOR = '#filter-cuadratura-asiento';
  const API_URL = '/api/v1/contabilidad/asientos-contables/';
  const TAB_ID = '#subtab-asientos';
  const ERROR_CONTAINER_ID = '#error-container-asientos';
  let table = null;

  // Helper: Formatear dinero
  function fmtMoney(v) {
    if (w.DOMUtils && typeof w.DOMUtils.fmtMoney === 'function') {
      return w.DOMUtils.fmtMoney(v);
    }
    const num = parseFloat(v) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  }

  // ⚠️ v2.60: Definir columnas usando campos de ASIENTO_LIST_FIELDS
  // ⚠️ Zero Waste: Campos procesados directamente desde el serializer
  function getColumns() {
    return [
      {
        title: "Número",
        field: "numero",
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '---';
        }
      },
      {
        title: "Fecha",
        field: "fecha",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '---';
          try {
            return new Date(val).toLocaleDateString('es-CO');
          } catch (e) {
            return val;
          }
        }
      },
      {
        title: "Descripción",
        field: "descripcion",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          const val = cell.getValue();
          if (!val) return '---';
          // Truncar descripción larga
          return val.length > 50 ? val.substring(0, 50) + '...' : val;
        }
      },
      {
        title: "Estado",
        field: "estado",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '---';
          
          const badges = {
            'BORRADOR': '<span class="badge bg-secondary">Borrador</span>',
            'APROBADO': '<span class="badge bg-success">Aprobado</span>',
            'CERRADO': '<span class="badge bg-info">Cerrado</span>'
          };
          
          return badges[val] || `<span class="badge bg-light text-dark">${val}</span>`;
        }
      },
      {
        title: "Movimientos",
        field: "movimientos_count",
        formatter: function(cell) {
          const val = cell.getValue();
          const count = parseInt(val) || 0;
          if (count === 0) {
            return '<span class="text-muted">0</span>';
          }
          return `<span class="badge bg-primary">${count}</span>`;
        },
        hozAlign: "center"
      },
      {
        title: "Débito",
        field: "total_debe",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return fmtMoney(val);
        },
        hozAlign: "right"
      },
      {
        title: "Crédito",
        field: "total_haber",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return fmtMoney(val);
        },
        hozAlign: "right"
      },
      {
        title: "Cuadratura",
        field: "cuadratura",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const debe = parseFloat(rowData.total_debe) || 0;
          const haber = parseFloat(rowData.total_haber) || 0;
          const diferencia = Math.abs(debe - haber);
          
          if (diferencia < 0.01) {
            return '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Cuadrado</span>';
          } else {
            return `<span class="badge bg-danger"><i class="bi bi-x-circle"></i> ${fmtMoney(diferencia)}</span>`;
          }
        },
        hozAlign: "center"
      },
      // ⚠️ NORMATIVA: Campos de comprobante para trazabilidad
      {
        title: "Tipo Comprobante",
        field: "tipo_comprobante",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '<span class="text-muted">---</span>';
          
          const tipos = {
            'FVE': '<span class="badge bg-primary">FVE</span>',
            'CE': '<span class="badge bg-info">CE</span>',
            'RC': '<span class="badge bg-warning">RC</span>',
            'GN': '<span class="badge bg-secondary">GN</span>',
            'ND': '<span class="badge bg-danger">ND</span>',
            'NC': '<span class="badge bg-success">NC</span>'
          };
          
          return tipos[val] || `<span class="badge bg-light text-dark">${val}</span>`;
        },
        hozAlign: "center",
        width: 130
      },
      {
        title: "N° Comprobante",
        field: "numero_comprobante",
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '<span class="text-muted">---</span>';
        },
        hozAlign: "left",
        width: 150
      },
      {
        title: "Acciones",
        field: "actions",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const asientoId = rowData.id;
          const estado = rowData.estado;
          const debe = parseFloat(rowData.total_debe) || 0;
          const haber = parseFloat(rowData.total_haber) || 0;
          const diferencia = Math.abs(debe - haber);
          const estaCuadrado = diferencia < 0.01;
          const puedeAprobar = estado === 'BORRADOR' && estaCuadrado;
          
          let botones = `
            <div class="btn-group btn-group-sm" role="group">
              <button type="button" class="btn btn-outline-primary btn-ver-asiento" data-id="${asientoId}" title="Ver Detalle">
                <i class="bi bi-eye"></i>
              </button>
          `;
          
          // ⚠️ v2.61: Botón de Editar solo si está en BORRADOR
          if (estado === 'BORRADOR') {
            botones += `
              <button type="button" class="btn btn-outline-secondary btn-editar-asiento" data-id="${asientoId}" title="Editar Asiento">
                <i class="bi bi-pencil"></i>
              </button>
            `;
          }
          
          // ⚠️ v2.60 Fase 2: Botón de Aprobar solo si está en BORRADOR y cuadrado
          if (estado === 'BORRADOR') {
            if (estaCuadrado) {
              botones += `
                <button type="button" class="btn btn-outline-success btn-aprobar-asiento" data-id="${asientoId}" title="Aprobar Asiento">
                  <i class="bi bi-check-circle"></i> Aprobar
                </button>
              `;
            } else {
              botones += `
                <button type="button" class="btn btn-outline-danger btn-aprobar-asiento" data-id="${asientoId}" disabled title="No se puede aprobar: Asiento no cuadrado">
                  <i class="bi bi-x-circle"></i> No Cuadrado
                </button>
              `;
            }
          }
          
          botones += `</div>`;
          return botones;
        },
        hozAlign: "center",
        headerSort: false
      }
    ];
  }

  /**
   * Inicializar tabla Tabulator
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica disponibilidad
   */
  function initTable() {
    if (!w.TabulatorFactory) {
      console.warn(`${MOD} TabulatorFactory no está disponible. Reintentando...`);
      setTimeout(initTable, 500);
      return;
    }

    const container = d.querySelector(TABLE_SELECTOR);
    if (!container) {
      console.warn(`${MOD} Contenedor ${TABLE_SELECTOR} no encontrado`);
      return;
    }

    // ⚠️ v2.60: Usar TabulatorFactory para crear tabla
    // ⚠️ v2.60 Fase 2: Filtro por defecto: Solo BORRADOR (Dashboard del Contador)
    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, getColumns(), {
      paginationSize: 20,
      searchInputSelector: SEARCH_SELECTOR,
      ajaxParams: function(params) {
        // ⚠️ v2.61: Asegurar que params existe antes de asignar propiedades
        if (!params) {
          params = {};
        }
        
        // ⚠️ v2.60 Fase 2: Filtrar por estado BORRADOR por defecto
        const filterEstado = d.querySelector(FILTER_ESTADO_SELECTOR);
        const estado = filterEstado ? filterEstado.value : 'BORRADOR';
        
        if (estado) {
          params.estado = estado;
        }
        
        return params;
      },
      initialFilter: [
        // ⚠️ v2.60 Fase 2: Filtro inicial: Solo asientos en BORRADOR
        {field: 'estado', type: '=', value: 'BORRADOR'}
      ]
    });

    if (!table) {
      console.error(`${MOD} No se pudo crear la tabla Tabulator`);
      return;
    }

    // ⚠️ v2.60: Event delegation para acciones de tabla
    container.addEventListener('click', function(evt) {
      const btnVer = evt.target.closest('.btn-ver-asiento');
      if (btnVer) {
        const asientoId = btnVer.dataset.id;
        if (asientoId && w.AppAsientos && typeof w.AppAsientos.cargarOffcanvasDetalleAsiento === 'function') {
          w.AppAsientos.cargarOffcanvasDetalleAsiento(asientoId);
        } else {
          console.warn(`${MOD} Función cargarOffcanvasDetalleAsiento no disponible`);
        }
        return;
      }
      
      // ⚠️ v2.61: Botón de Editar
      const btnEditar = evt.target.closest('.btn-editar-asiento');
      if (btnEditar) {
        const asientoId = btnEditar.dataset.id;
        if (asientoId && w.AppAsientos && typeof w.AppAsientos.cargarOffcanvasEditarAsiento === 'function') {
          w.AppAsientos.cargarOffcanvasEditarAsiento(asientoId);
        } else {
          console.warn(`${MOD} Función cargarOffcanvasEditarAsiento no disponible`);
        }
        return;
      }
      
      // ⚠️ v2.60 Fase 2: Botón de Aprobar con validación visual
      const btnAprobar = evt.target.closest('.btn-aprobar-asiento');
      if (btnAprobar && !btnAprobar.disabled) {
        const asientoId = btnAprobar.dataset.id;
        if (asientoId) {
          aprobarAsiento(asientoId);
        }
        return;
      }
    });
    
    // ⚠️ v2.60 Fase 2: Filtros de Estado y Cuadratura
    setupFilters();

    console.log(`${MOD} Tabla Tabulator inicializada`);
  }

  /**
   * Refrescar tabla
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch
   */
  function refreshTable() {
    if (table && typeof table.replaceData === 'function') {
      table.replaceData();
      console.log(`${MOD} Tabla refrescada`);
    } else {
      console.warn(`${MOD} Tabla no disponible para refrescar`);
    }
  }
  
  /**
   * ⚠️ v2.60 Fase 2: Configurar filtros de Estado y Cuadratura
   */
  function setupFilters() {
    const filterEstado = d.querySelector(FILTER_ESTADO_SELECTOR);
    const filterCuadratura = d.querySelector(FILTER_CUADRATURA_SELECTOR);
    
    if (filterEstado) {
      filterEstado.addEventListener('change', function() {
        aplicarFiltros();
      });
    }
    
    if (filterCuadratura) {
      filterCuadratura.addEventListener('change', function() {
        aplicarFiltros();
      });
    }
  }
  
  /**
   * ⚠️ v2.60 Fase 2: Aplicar filtros de Estado y Cuadratura
   */
  function aplicarFiltros() {
    if (!table) return;
    
    const filterEstado = d.querySelector(FILTER_ESTADO_SELECTOR);
    const filterCuadratura = d.querySelector(FILTER_CUADRATURA_SELECTOR);
    
    const estado = filterEstado ? filterEstado.value : '';
    const cuadratura = filterCuadratura ? filterCuadratura.value : '';
    
    // Construir filtro combinado
    let filtro = [];
    
    if (estado) {
      filtro.push({field: 'estado', type: '=', value: estado});
    }
    
    if (cuadratura) {
      if (cuadratura === 'cuadrado') {
        // Filtrar por cuadratura = true (diferencia < 0.01)
        filtro.push({
          field: 'cuadratura',
          type: '=',
          value: true
        });
      } else if (cuadratura === 'no_cuadrado') {
        // Filtrar por cuadratura = false (diferencia >= 0.01)
        filtro.push({
          field: 'cuadratura',
          type: '=',
          value: false
        });
      }
    }
    
    // Aplicar filtros a la tabla
    if (filtro.length > 0) {
      table.setFilter(filtro);
    } else {
      table.clearFilter();
    }
  }
  
  /**
   * ⚠️ v2.60 Fase 2: Aprobar asiento con validación visual
   */
  function aprobarAsiento(asientoId) {
    if (!asientoId) {
      console.warn(`${MOD} ID de asiento no válido`);
      return;
    }
    
    // Obtener datos de la fila para validación visual
    if (!table) {
      console.warn(`${MOD} Tabla no disponible`);
      return;
    }
    
    const row = table.getRow(asientoId);
    if (!row) {
      console.warn(`${MOD} Fila no encontrada para asiento ${asientoId}`);
      return;
    }
    
    const rowData = row.getData();
    const debe = parseFloat(rowData.total_debe) || 0;
    const haber = parseFloat(rowData.total_haber) || 0;
    const diferencia = Math.abs(debe - haber);
    const estaCuadrado = diferencia < 0.01;
    
    // ⚠️ Validación Visual en Tiempo Real
    if (!estaCuadrado) {
      mostrarErrorCuadratura(debe, haber, diferencia);
      return;
    }
    
    // Confirmar aprobación
    if (!confirm(`¿Está seguro de aprobar el asiento ${rowData.numero || asientoId}?`)) {
      return;
    }
    
    // Realizar petición de aprobación
    const url = `${API_URL}${asientoId}/aprobar/`;
    const csrftoken = d.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                      d.cookie.match(/csrftoken=([^;]+)/)?.[1];
    
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      credentials: 'same-origin'
    })
    .then(response => {
      return response.json().then(data => ({ response, data }));
    })
    .then(({ response, data }) => {
      if (response.ok) {
        // Refrescar tabla
        refreshTable();
        // Ocultar error si existe
        const errorContainer = d.querySelector(ERROR_CONTAINER_ID);
        if (errorContainer) {
          errorContainer.classList.add('d-none');
        }
        // Mostrar éxito
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
          w.SintelFeedback.success(`Asiento ${rowData.numero || asientoId} aprobado correctamente`);
        }
      } else {
        // Mostrar error del servidor
        if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
          w.ErrorHandler.show(data);
        } else {
          mostrarErrorCuadratura(debe, haber, diferencia, data.message || data.detail || 'Error al aprobar asiento');
        }
      }
    })
    .catch(error => {
      console.error(`${MOD} Error al aprobar asiento:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(error);
      }
    });
  }
  
  /**
   * ⚠️ v2.60 Fase 2: Mostrar error de cuadratura usando error_injector.js
   */
  function mostrarErrorCuadratura(debe, haber, diferencia, mensajeAdicional) {
    const errorContainer = d.querySelector(ERROR_CONTAINER_ID);
    const errorMessage = d.querySelector('#error-message-asientos');
    const missingFieldsList = d.querySelector('#missing-fields-list-asientos');
    
    if (errorContainer && errorMessage) {
      const mensaje = mensajeAdicional || 
        `El asiento no está cuadrado. Débito (${fmtMoney(debe)}) no es igual a Crédito (${fmtMoney(haber)}). Diferencia: ${fmtMoney(diferencia)}.`;
      
      errorMessage.textContent = mensaje;
      errorContainer.classList.remove('d-none');
      errorContainer.classList.add('alert-danger');
      
      if (missingFieldsList) {
        missingFieldsList.innerHTML = `
          <li>Total Débito: ${fmtMoney(debe)}</li>
          <li>Total Crédito: ${fmtMoney(haber)}</li>
          <li>Diferencia: ${fmtMoney(diferencia)}</li>
          <li><strong>Acción requerida:</strong> Agregue o ajuste movimientos contables para cuadrar el asiento.</li>
        `;
      }
      
      // Scroll al contenedor de errores
      errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
      // Fallback: usar alert si no hay contenedor
      alert(mensaje);
    }
  }

  /**
   * Inicializar módulo cuando el tab esté visible
   * ⚠️ v2.60: Usa DOMUtils.onVisibleOnce para lazy loading
   */
  function init() {
    if (!w.DOMUtils || !w.DOMUtils.onVisibleOnce) {
      console.warn(`${MOD} DOMUtils.onVisibleOnce no disponible. Inicializando directamente...`);
      initTable();
      return;
    }

    // ⚠️ v2.60: Lazy loading - Solo inicializar cuando el tab esté visible
    w.DOMUtils.onVisibleOnce(TAB_ID, function() {
      console.log(`${MOD} Tab visible, inicializando tabla...`);
      initTable();
    });
  }

  // ⚠️ CRÍTICO v2.60: Exponer AppAsientos INMEDIATAMENTE (antes de definir funciones)
  if (!w.AppAsientos) {
    w.AppAsientos = {};
  }

  // Exponer funciones públicas
  w.AppAsientos.refreshGrid = refreshTable;
  w.AppAsientos.init = init;

  // Auto-inicializar cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ⚠️ v2.61: Listener adicional para evento Bootstrap tab (cuando se muestra el tab)
  // Esto asegura que la tabla se inicialice incluso si DOMUtils.onVisibleOnce no se dispara
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-bs-target') === TAB_ID || e.target.id === 'contabilidad-asientos-tab')) {
      console.log(`${MOD} Tab de asientos mostrado, verificando inicialización...`);
      const container = d.querySelector(TABLE_SELECTOR);
      if (container && !table) {
        console.log(`${MOD} Tabla no inicializada, inicializando desde evento shown.bs.tab...`);
        initTable();
      } else if (table && typeof table.replaceData === 'function') {
        // Si la tabla ya existe, refrescar datos
        console.log(`${MOD} Tabla ya inicializada, refrescando datos...`);
        table.replaceData();
      }
    }
  });

  console.log(`${MOD} Módulo cargado`);

})(window, document);
