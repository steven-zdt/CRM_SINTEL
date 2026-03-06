/**
 * gastos_main.js - Módulo Principal de Gastos v2.60 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.40: Sistema de Documento Soporte Inmutable según normativa DIAN
 * - Inicialización de Tabulator Factory
 * - Event delegation para acciones de tabla
 * - Carga de resumen financiero
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.gastosAPI (definido en gastos.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.AppGastos (definido en gastos_crear.js y gastos_anular.js)
 */
(function (w, d) {
  'use strict';

  const MOD = '[gastos.main]';
  const TABLE_SELECTOR = '#grid-gastos';
  const SEARCH_SELECTOR = '#search-gasto';
  const API_URL = '/api/v1/gastos/';
  const TAB_ID = '#tab-gastos';
  let table = null;
  let state = {
    summary: null
  };

  // Helper: Formatear dinero
  function fmtMoney(v) {
    if (w.DOMUtils && typeof w.DOMUtils.fmtMoney === 'function') {
      return w.DOMUtils.fmtMoney(v);
    }
    const num = parseFloat(v) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  }

  /**
   * Obtención y renderizado del panel financiero
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function renderSummary() {
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.gastosAPI.summary();
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok || !res.data) {
      console.warn(`${MOD} Error cargando resumen:`, res.status);
      return;
    }
    
    state.summary = res.data;
    
    const totalEl = d.getElementById('gasto-total-neto');
    const retefuenteEl = d.getElementById('gasto-retefuente');
    const reteicaEl = d.getElementById('gasto-reteica');
    const cantidadEl = d.getElementById('gasto-cantidad');
    
    if (totalEl) totalEl.textContent = fmtMoney(res.data.total_neto || 0);
    // ⚠️ v2.40: Mostrar Retefuente e ICA por separado
    if (retefuenteEl) retefuenteEl.textContent = fmtMoney(res.data.retefuente_neto || 0);
    if (reteicaEl) reteicaEl.textContent = fmtMoney(res.data.reteica_neto || 0);
    if (cantidadEl) cantidadEl.textContent = res.data.cantidad || 0;
  }

  // ⚠️ v2.60: Definir columnas usando campos aplanados del GastoListSerializer
  // ⚠️ Zero Waste: Campos aplanados (ds_*) procesados directamente desde el serializer
  function getColumns() {
    return [
      {
        title: "Documento",
        field: "ds_numero_documento",  // ⚠️ v2.40: Campo aplanado del serializer (prefijo + consecutivo)
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const anulado = rowData.ds_anulado === true;
          const val = cell.getValue();
          
          // ⚠️ CRÍTICO: El consecutivo SIEMPRE debe mostrarse, incluso si el documento está anulado
          let doc = val;
          if (!doc) {
            // Fallback si no viene el campo completo
            const prefijo = rowData.ds_prefijo || '';
            const consecutivo = rowData.ds_consecutivo || '';
            doc = prefijo && consecutivo ? `${prefijo} ${consecutivo}` : (consecutivo || '---');
          }
          
          // ⚠️ v2.40: El consecutivo prevalece en la lista, incluso si está anulado
          // Mostrar con estilo diferente pero siempre visible
          if (anulado) {
            return `<b class="text-muted text-decoration-line-through">${doc}</b> <span class="badge bg-danger badge-sm">ANULADO</span>`;
          }
          return `<b>${doc}</b>`;
        }
      },
      {
        title: "Fecha",
        field: "ds_fecha",  // ⚠️ v2.40: Campo aplanado del serializer
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
        title: "Proveedor",
        field: "ds_vendedor",  // ⚠️ v2.40: Campo aplanado del serializer
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '---';
        }
      },
      {
        title: "Categoría",
        field: "categoria_contable_display",  // ⚠️ v2.40: Campo display del serializer
        formatter: function(cell) {
          const data = cell.getRow().getData();
          return data.categoria_contable_display || data.categoria_contable || '---';
        }
      },
      {
        title: "Centro de Costo",
        field: "centro_costo_display",  // ⚠️ v2.40: Campo display del serializer
        formatter: function(cell) {
          const data = cell.getRow().getData();
          return data.centro_costo_display || data.centro_costo || '---';
        }
      },
      {
        title: "Total",
        field: "ds_total",  // ⚠️ v2.40: Campo aplanado del serializer
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return fmtMoney(val);
        },
        hozAlign: "right"
      },
      {
        title: "Estado",
        field: "ds_anulado",  // ⚠️ v2.40: Campo aplanado del serializer
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const activo = rowData.ds_activo === true;
          const anulado = rowData.ds_anulado === true;
          
          if (anulado) {
            return '<span class="badge bg-danger">Anulado</span>';
          } else if (activo) {
            return '<span class="badge bg-success">Activo</span>';
          } else {
            return '<span class="badge bg-warning">Inactivo</span>';
          }
        },
        headerSort: false
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id = rowData.id;
          const activo = rowData.ds_activo === true;
          const anulado = rowData.ds_anulado === true;
          
          let buttons = '';
          
          // Botón Ver Detalle (siempre disponible)
          buttons += `
            <button type="button" class="btn btn-sm btn-link text-primary p-0 me-2" 
                    data-action="ver" data-id="${id}" title="Ver Detalle">
              <i class="fas fa-eye"></i>
            </button>
          `;
          
          // ⚠️ v2.40: Lógica de desactivar/anular
          if (!anulado) {
            if (activo) {
              // Si está activo: mostrar botón Desactivar
              buttons += `
                <button type="button" class="btn btn-sm btn-link text-warning p-0 me-2" 
                        data-action="desactivar" data-id="${id}" title="Desactivar Documento">
                  <i class="fas fa-toggle-off"></i>
                </button>
              `;
              // Botón Anular deshabilitado si está activo
              buttons += `
                <button type="button" class="btn btn-sm btn-link text-muted p-0 opacity-50" disabled 
                        title="Debe desactivar primero para anular">
                  <i class="fas fa-ban"></i>
                </button>
              `;
            } else {
              // Si está inactivo: mostrar botón Anular
              buttons += `
                <button type="button" class="btn btn-sm btn-link text-danger p-0" 
                        data-action="anular" data-id="${id}" title="Anular Documento">
                  <i class="fas fa-ban"></i>
                </button>
              `;
            }
          }
          
          return buttons || '-';
        },
        headerSort: false,
        hozAlign: "center",
        width: 180
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
      searchInputSelector: SEARCH_SELECTOR
    });

    // ⚠️ v2.40: Event delegation para botones de acciones
    if (table) {
      const container = d.querySelector(TABLE_SELECTOR);
      if (container) {
        container.addEventListener('click', function(e) {
          const btn = e.target.closest('button[data-action]');
          if (!btn) return;
          
          e.preventDefault();
          e.stopPropagation();
          
          const action = btn.getAttribute('data-action');
          const id = parseInt(btn.getAttribute('data-id'), 10);
          
          if (!id || isNaN(id)) {
            console.warn(`${MOD} ID no válido:`, id);
            return;
          }
          
          // Ejecutar acción según el botón
          switch (action) {
            case 'ver':
              if (w.AppGastos && typeof w.AppGastos.ver === 'function') {
                w.AppGastos.ver(id);
              }
              break;
            case 'desactivar':
              if (w.AppGastos && typeof w.AppGastos.desactivar === 'function') {
                w.AppGastos.desactivar(id);
              }
              break;
            case 'anular':
              if (w.AppGastos && typeof w.AppGastos.anular === 'function') {
                w.AppGastos.anular(id);
              }
              break;
            default:
              console.warn(`${MOD} Acción no reconocida:`, action);
          }
        });
      }
    }

    return table;
  }

  // Función para refrescar tabla y resumen
  async function refresh() {
    await renderSummary();
    if (table) {
      table.replaceData();
    }
  }

  // Función para inicializar el módulo completo
  async function inicializarModulo() {
    console.log(`${MOD} Inicializando módulo completo...`);
    
    // Renderizar resumen primero
    await renderSummary();
    
    // Inicializar tabla
    table = initTable();
    
    // Exponer módulo globalmente
    if (!w.AppGastos) {
      w.AppGastos = {};
    }
    
    // Asignar funciones principales
    w.AppGastos.table = table;
    w.AppGastos.refresh = refresh;
    w.AppGastos.renderSummary = renderSummary;
    
    // ⚠️ v2.60: Función para verificar resolución activa (usada después de guardar resolución)
    w.AppGastos.verificarResolucionActiva = async function() {
      const res = await w.gastosAPI.getResolucionActiva();
      if (!res.ok || res.status === 404) {
        console.log(`${MOD} No hay resolución activa después de guardar`);
      } else {
        console.log(`${MOD} Resolución activa verificada correctamente`);
      }
    };
    
    console.log(`${MOD} Módulo principal inicializado`);
  }

  // Configurar eventos de botones de toolbar
  function configurarEventosToolbar() {
    console.log(`${MOD} Configurando eventos de toolbar...`);
    
    // Botón refrescar
    const btnRefrescar = d.getElementById('btn-refrescar-gastos');
    if (btnRefrescar) {
      const nuevoBtn = btnRefrescar.cloneNode(true);
      btnRefrescar.parentNode.replaceChild(nuevoBtn, btnRefrescar);
      
      nuevoBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log(`${MOD} Refrescando tabla y resumen...`);
        await refresh();
      });
    }

    // Botón crear gasto
    const btnCrear = d.getElementById('btn-gastos-crear');
    if (btnCrear) {
      const nuevoBtn = btnCrear.cloneNode(true);
      nuevoBtn.removeAttribute('onclick');
      btnCrear.parentNode.replaceChild(nuevoBtn, btnCrear);
      
      nuevoBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log(`${MOD} Click en botón "Nuevo Gasto"`);
        
        // Validar resolución activa antes de abrir offcanvas
        const res = await w.gastosAPI.getResolucionActiva();
        if (!res.ok || res.status === 404) {
          // No hay resolución activa, abrir modal de configuración
          console.log(`${MOD} No hay resolución activa, abriendo modal de configuración`);
          const modalConfigEl = d.getElementById('modal-resolucion-config');
          if (modalConfigEl) {
            if (w.bootstrap && w.bootstrap.Modal) {
              const modal = w.bootstrap.Modal.getOrCreateInstance(modalConfigEl);
              modal.show();
            }
          }
          return;
        }
        
        // Hay resolución activa, abrir offcanvas de creación
        console.log(`${MOD} Resolución activa encontrada, abriendo offcanvas de creación`);
        if (w.AppGastos && typeof w.AppGastos.crear === 'function') {
          w.AppGastos.crear();
        }
      });
    }
    
    // ⚠️ v2.60: Botón configurar resolución - Ahora usa HTMX directamente en el HTML
    // La lógica está centralizada en gastos_resolucion.js
    // Solo validamos que el botón exista y que el módulo de resolución esté disponible
    const btnConfig = d.getElementById('btn-config-resolucion');
    if (btnConfig) {
      // El botón ya tiene atributos HTMX en el HTML, solo verificamos que funcione
      console.log(`${MOD} Botón "Configurar Resolución" encontrado, usando HTMX`);
    }
  }

  // Lazy Loading: Inicializar solo cuando el tab sea visible
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(TAB_ID, function() {
      console.log(`${MOD} Tab de gastos visible, inicializando...`);
      inicializarModulo().then(() => {
        configurarEventosToolbar();
      }).catch(err => {
        console.error(`${MOD} Error en inicialización:`, err);
      });
    });
  } else {
    // Fallback si DOMUtils no está disponible
    console.warn(`${MOD} DOMUtils no disponible, inicializando inmediatamente`);
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      
      inicializarModulo().then(() => {
        configurarEventosToolbar();
      }).catch(err => {
        console.error(`${MOD} Error en inicialización (fallback):`, err);
      });
    }
    initFallback();
  }
  
  // También configurar eventos cuando el tab de gastos se muestre (Bootstrap event)
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-tab') === 'gastos' || e.target.getAttribute('data-bs-target') === TAB_ID)) {
      console.log(`${MOD} Tab de gastos mostrado, verificando eventos...`);
      // Asegurar que el módulo esté inicializado
      if (!w.AppGastos || !w.AppGastos.table) {
        console.log(`${MOD} Módulo no inicializado, inicializando desde evento shown.bs.tab...`);
        inicializarModulo().then(() => {
          configurarEventosToolbar();
        }).catch(err => {
          console.error(`${MOD} Error en inicialización desde evento:`, err);
        });
      } else {
        setTimeout(configurarEventosToolbar, 100);
      }
    }
  });

})(window, document);
