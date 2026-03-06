/**
 * empleados_list.js - Feature: Lista de Empleados
 * ⚠️ Feature-Sliced Architecture v2.60
 * Maneja la tabla Tabulator y delegación de eventos de la lista principal
 */
(function (w, d) {
  'use strict';

  const MOD = '[empleados.list]';
  const CONTAINER_ID = '#tab-empleados';
  const GRID_ID = '#grid-empleados';
  const SEARCH_INPUT_ID = '#search-empleado';
  const API_URL = '/api/v1/empleados/';
  
  let table = null;

  /**
   * ⚠️ v2.60: Helper para formatear valores monetarios en COP
   */
  function formatCOP(value) {
    if (value === null || value === undefined || value === '') return '$ 0,00';
    const num = parseFloat(value);
    if (isNaN(num)) return '$ 0,00';
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  }

  /**
   * Actualizar panel de resumen
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function updateSummaryPanel() {
    if (!w.http || typeof w.http !== 'function') {
      console.warn(`${MOD} w.http no está disponible`);
      return;
    }
    
    const response = await w.http('GET', `${API_URL}summary/`);
    
    if (!response.ok || !response.data) {
      console.warn(`${MOD} Error cargando resumen:`, response.status);
      return;
    }
    
    const data = response.data;
    
    // Actualizar Nómina Mes Actual (formato COP)
    const totalNomina = d.getElementById('total-nomina-mes');
    if (totalNomina && data.total_nomina_mes) {
      totalNomina.textContent = formatCOP(data.total_nomina_mes);
    }
    
    // Actualizar Empleados Pagados
    const empleadosPagados = d.getElementById('empleados-pagados');
    if (empleadosPagados && data.empleados_pagados !== undefined) {
      empleadosPagados.textContent = data.empleados_pagados;
    }
    
    // Actualizar Empleados Activos
    const empleadosActivos = d.getElementById('empleados-activos');
    if (empleadosActivos && data.empleados_activos !== undefined) {
      empleadosActivos.textContent = data.empleados_activos;
    }
  }

  function getColumns() {
    return [
      { title: "ID", field: "id", visible: false },
      { title: "Documento", field: "numero_documento", width: 120 },
      { title: "Nombre Completo", field: "nombre_completo", minWidth: 200 },
      { title: "Estado", field: "estado_display", width: 120, formatter: (cell) => {
        const estado = cell.getValue();
        const badges = {
          'ACTIVO': '<span class="badge bg-success">Activo</span>',
          'RETIRADO': '<span class="badge bg-secondary">Retirado</span>',
          'SUSPENDIDO': '<span class="badge bg-warning">Suspendido</span>'
        };
        return badges[estado] || `<span class="badge bg-secondary">${estado || '-'}</span>`;
      }},
      { title: "Fecha Ingreso", field: "fecha_ingreso", width: 120, formatter: (cell) => {
        const val = cell.getValue();
        return val ? new Date(val).toLocaleDateString('es-CO') : '-';
      }},
      { 
        title: "Acciones", 
        hozAlign: "center", 
        width: 220, 
        headerSort: false,
        formatter: function(cell) {
          const data = cell.getRow().getData();
          const id = data.id;
          
          // ⚠️ v2.60: Lógica secuencial reactiva basada en anotaciones del servidor
          const tieneContrato = data.tiene_contrato_activo === true;
          const tieneNominas = data.tiene_nominas_registradas === true;
          const estado = data.estado || data.estado_display || '';
          const esRetirado = estado === 'RETIRADO' || estado === 'Retirado';
          
          let html = '<div class="btn-group btn-group-sm" role="group">';
          
          // ⚠️ v2.60: Botón Editar Empleado (siempre visible)
          html += `<button type="button" class="btn btn-outline-primary" 
                   data-action="editar" data-id="${id}" 
                   title="Editar Empleado">
            <i class="fas fa-edit"></i>
          </button>`;
          
          // ⚠️ v2.60: Botón Ver/Editar Contrato (después de Editar) - Solo si NO está retirado
          if (!esRetirado) {
              if (tieneContrato) {
                  html += `<button type="button" class="btn btn-outline-success" 
                           data-action="ver-contrato" data-id="${id}" 
                           title="Ver/Editar Contrato">
                    <i class="fas fa-file-contract"></i>
                  </button>`;
              } else {
                  html += `<button type="button" class="btn btn-outline-success" 
                           data-action="crear-contrato" data-id="${id}" 
                           title="Crear Contrato">
                    <i class="fas fa-file-contract"></i>
                  </button>`;
              }
              
              if (tieneContrato) {
                  html += `<button type="button" class="btn btn-outline-info" 
                           data-action="registrar-nomina" data-id="${id}" 
                           title="Registrar Pago">
                    <i class="fas fa-money-bill-wave"></i>
                  </button>`;
                  
                  if (tieneNominas) {
                      html += `<button type="button" class="btn btn-outline-secondary" 
                               data-action="ver-historial" data-id="${id}" 
                               title="Ver Historial">
                        <i class="fas fa-history"></i>
                      </button>`;
                  }
              }
          }
          
          // ⚠️ v2.60: Botón Delete (visible solo si el empleado está RETIRADO)
          if (esRetirado) {
              html += `<button type="button" class="btn btn-outline-danger" 
                       data-action="eliminar" data-id="${id}" 
                       title="Eliminar Definitivamente">
                <i class="fas fa-trash"></i>
              </button>`;
          }
          
          html += '</div>';
          return html;
        }
      }
    ];
  }

  /**
   * ⚠️ v2.60: Función para manejar clicks en botones de acciones (event delegation)
   */
  function handleActionClick(e) {
    const btn = e.target.closest('button[data-action]');
    if (!btn) {
      const icon = e.target.closest('i');
      if (icon) {
        const parentBtn = icon.closest('button[data-action]');
        if (parentBtn) {
          processActionClick(parentBtn, e);
        }
      }
      return;
    }
    
    processActionClick(btn, e);
  }
  
  /**
   * ⚠️ v2.60: Función para procesar el click en un botón de acción
   * Adaptado para usar los nuevos namespaces de features
   */
  async function processActionClick(btn, e) {
    e.preventDefault();
    e.stopPropagation();
    
    const action = btn.getAttribute('data-action');
    const id = parseInt(btn.getAttribute('data-id'), 10);
    
    console.log(`${MOD} Click en botón: action=${action}, id=${id}`);
    
    if (!id || isNaN(id)) {
      console.warn(`${MOD} ID no válido:`, id);
      return;
    }
    
    switch (action) {
      case 'editar':
        if (w.EmpleadosEditor && typeof w.EmpleadosEditor.open === 'function') {
          await w.EmpleadosEditor.open(id);
        }
        break;
      case 'crear-contrato':
        if (w.ContratosEditor && typeof w.ContratosEditor.open === 'function') {
          await w.ContratosEditor.open(id);
        }
        break;
      case 'ver-contrato':
        // ⚠️ v2.60: Obtener contrato activo del empleado
        if (w.empleadosAPI && typeof w.empleadosAPI.listContratos === 'function') {
          const contratosRes = await w.empleadosAPI.listContratos({ empleado: id, estado: 'ACTIVO' });
          if (contratosRes.ok && contratosRes.data && contratosRes.data.results && contratosRes.data.results.length > 0) {
            const contrato = contratosRes.data.results[0];
            if (w.ContratosEditor && typeof w.ContratosEditor.open === 'function') {
              await w.ContratosEditor.open(id, contrato.id);
            }
          } else {
            if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
              w.UIManager.notifyError({ status: 404, data: { detail: 'No se encontró un contrato activo para este empleado' } }, MOD);
            }
          }
        } else {
          // Fallback: usar gestor-offcanvas directamente
          if (w.ContratosEditor && typeof w.ContratosEditor.open === 'function') {
            await w.ContratosEditor.open(id);
          }
        }
        break;
      case 'registrar-nomina':
        console.log(`${MOD} Acción: Registrar Nómina para empleado ${id}`);
        if (!id || isNaN(id)) {
          console.error(`${MOD} ❌ ID de empleado inválido para registrar nómina:`, id);
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError(
              { status: 400, data: { detail: 'ID de empleado inválido para registrar nómina.' } },
              MOD
            );
          }
          return;
        }
        if (w.DevengosEditor && typeof w.DevengosEditor.open === 'function') {
          await w.DevengosEditor.open(id);
        }
        break;
      case 'ver-historial':
        if (w.HistorialNominas && typeof w.HistorialNominas.open === 'function') {
          await w.HistorialNominas.open(id);
        }
        break;
      case 'eliminar':
        if (w.EmpleadosEditor && typeof w.EmpleadosEditor.delete === 'function') {
          await w.EmpleadosEditor.delete(id);
        }
        break;
      default:
        console.warn(`${MOD} Acción no reconocida:`, action);
    }
  }

  /**
   * ⚠️ v2.60: Inicializar tabla Tabulator
   * Solo se encarga de configurar la Tabulator Factory
   */
  function initEmpleadosTable() {
    console.log(`${MOD} Inicializando Tabulator para empleados...`);
    
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) {
      console.error(`${MOD} ❌ Contenedor ${GRID_ID} no encontrado`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Contenedor ${GRID_ID} no encontrado. Verifique que list.html esté correctamente incluido.` } },
          MOD
        );
      }
      return;
    }

    // ⚠️ Anti-Zombies Pattern: Destruir instancia previa si existe
    if (table && typeof table.destroy === 'function') {
      try {
        console.log(`${MOD} ⚠️ Destruyendo instancia previa de tabla...`);
        table.destroy();
        table = null;
      } catch (error) {
        console.warn(`${MOD} Error al destruir tabla previa:`, error);
      }
    }
    
    if (w.SintelEmpleadosTables && w.SintelEmpleadosTables.empleados) {
      try {
        console.log(`${MOD} ⚠️ Destruyendo instancia previa en singleton...`);
        w.SintelEmpleadosTables.empleados.destroy();
        w.SintelEmpleadosTables.empleados = null;
      } catch (error) {
        console.warn(`${MOD} Error al destruir tabla previa del singleton:`, error);
      }
    }
    
    // ⚠️ Anti-Zombies: Limpiar cualquier contenido residual en el contenedor
    try {
      gridEl.innerHTML = '';
      console.log(`${MOD} ✅ Contenedor limpiado`);
    } catch (error) {
      console.warn(`${MOD} Error al limpiar contenedor:`, error);
    }

    if (!w.TabulatorFactory || typeof w.TabulatorFactory.create !== 'function') {
      console.error(`${MOD} ❌ TabulatorFactory no está disponible.`);
      return;
    }

    // ⚠️ v2.60: Configuración explícita con paginationMode: 'remote'
    const tableConfig = {
      searchInputSelector: SEARCH_INPUT_ID,
      pagination: true,
      paginationMode: "remote",
      paginationSize: 10,
      paginationSizeSelector: [10, 25, 50, 100],
      layout: "fitColumns",
      responsiveLayout: "hide",
      placeholder: "No hay empleados registrados",
      locale: "es"
    };

    table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), tableConfig);

    // ⚠️ v2.60: Guardar instancia en singleton global
    if (!w.SintelEmpleadosTables) {
      w.SintelEmpleadosTables = {};
    }
    w.SintelEmpleadosTables.empleados = table;

    // ⚠️ v2.60: Event delegation para botones de acciones en la tabla
    const tabContainer = d.querySelector(CONTAINER_ID);
    if (tabContainer) {
      if (!tabContainer.hasAttribute('data-empleados-listener')) {
        tabContainer.addEventListener('click', handleActionClick);
        tabContainer.setAttribute('data-empleados-listener', 'true');
        console.log(`${MOD} ✅ Event listener agregado al contenedor del tab: ${CONTAINER_ID}`);
      } else {
        console.log(`${MOD} ⚠️ Event listener ya existe en el contenedor, omitiendo duplicado...`);
      }
    } else {
      console.error(`${MOD} ❌ No se encontró el contenedor del tab: ${CONTAINER_ID}`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Contenedor ${CONTAINER_ID} no encontrado. Verifique que el tab esté correctamente definido en workspace.html.` } },
          MOD
        );
      }
      // Fallback: usar el documento completo (solo una vez)
      if (!d.hasAttribute('data-empleados-fallback-listener')) {
        d.addEventListener('click', function(e) {
          if (e.target.closest(GRID_ID)) {
            handleActionClick(e);
          }
        });
        d.setAttribute('data-empleados-fallback-listener', 'true');
        console.log(`${MOD} ⚠️ Event listener agregado al documento (fallback)`);
      }
    }

    // Cargar panel de resumen
    updateSummaryPanel();

    console.log(`${MOD} ✅ Tabulator inicializado.`);
  }

  /**
   * ⚠️ v2.60: Configurar eventos del botón "Nuevo" y "Refrescar"
   */
  function configurarEventos() {
    console.log(`${MOD} Configurando eventos...`);
    
    // Botón crear
    const btnCrear = d.getElementById('btn-empleados-crear');
    if (btnCrear) {
      const nuevoBtn = btnCrear.cloneNode(true);
      nuevoBtn.removeAttribute('onclick');
      btnCrear.parentNode.replaceChild(nuevoBtn, btnCrear);
      
      nuevoBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log(`${MOD} Click en botón "Nuevo Empleado"`);
        if (w.EmpleadosEditor && typeof w.EmpleadosEditor.open === 'function') {
          await w.EmpleadosEditor.open(null);
        }
      });
    }

    // Botón refrescar
    const btnRefrescar = d.getElementById('btn-refrescar-empleados');
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', function() {
        console.log(`${MOD} Refrescando tabla...`);
        if (table) {
          table.replaceData();
        }
        updateSummaryPanel();
      });
    }
  }

  /**
   * ⚠️ v2.60: Función para inicializar el módulo completo
   */
  function inicializarModulo() {
    console.log(`${MOD} Inicializando módulo completo...`);
    
    // Verificar dependencias críticas
    if (!w.TabulatorFactory) {
      console.error(`${MOD} ❌ CRÍTICO: TabulatorFactory no está disponible.`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: 'TabulatorFactory no está disponible. Verifique que assets_core.html se haya cargado correctamente.' } },
          MOD
        );
      }
      return;
    }
    
    if (!w.DOMUtils) {
      console.error(`${MOD} ❌ CRÍTICO: DOMUtils no está disponible.`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: 'DOMUtils no está disponible. Verifique que assets_core.html se haya cargado correctamente.' } },
          MOD
        );
      }
      return;
    }
    
    console.log(`${MOD} ✅ TabulatorFactory y DOMUtils están disponibles`);
    
    // Verificar que el contenedor existe en el DOM
    const containerEl = d.querySelector(CONTAINER_ID);
    if (!containerEl) {
      console.error(`${MOD} ❌ CRÍTICO: Contenedor ${CONTAINER_ID} no encontrado en el DOM.`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Contenedor ${CONTAINER_ID} no encontrado. Verifique que el tab esté correctamente definido en workspace.html.` } },
          MOD
        );
      }
      return;
    }
    
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) {
      console.error(`${MOD} ❌ CRÍTICO: Grid ${GRID_ID} no encontrado en el DOM.`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Grid ${GRID_ID} no encontrado. Verifique que list.html esté correctamente incluido.` } },
          MOD
        );
      }
      return;
    }
    
    console.log(`${MOD} ✅ Contenedores DOM encontrados: ${CONTAINER_ID}, ${GRID_ID}`);
    
    // Inicializar tabla
    initEmpleadosTable();
    
    // Exponer módulo globalmente
    w.EmpleadosList = {
      table: table,
      /**
       * ⚠️ v2.60: Refresca la tabla Tabulator y actualiza el panel de resumen
       * Mantiene la paginación actual y recarga los datos en segundo plano
       * Sin recargar la página completa (UX fluida)
       */
      refresh: function() {
        if (table && typeof table.replaceData === 'function') {
          console.log(`${MOD} Refrescando tabla de empleados...`);
          table.replaceData(); // Refresca los datos en segundo plano manteniendo paginación
        } else {
          console.warn(`${MOD} ⚠️ Tabla no inicializada, no se puede refrescar`);
        }
        
        // Actualizar panel de resumen (totales)
        if (typeof updateSummaryPanel === 'function') {
          updateSummaryPanel();
        }
      },
      updateSummaryPanel: updateSummaryPanel
    };
    
    console.log(`${MOD} Módulo expuesto globalmente:`, w.EmpleadosList);
    
    // Configurar eventos DESPUÉS de inicializar el módulo
    configurarEventos();
  }

  // ⚠️ v2.60: Lazy Loading - Encapsula la lógica en DOMUtils.onVisibleOnce
  if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
    const selectors = [
      GRID_ID,
      CONTAINER_ID,
      '#tab-empleados',
      '#tab-empleados ' + GRID_ID,
      '#workspace #tab-empleados',
      '#workspace #tab-empleados ' + GRID_ID
    ];
    
    let targetSelector = null;
    for (const selector of selectors) {
      const el = d.querySelector(selector);
      if (el) {
        targetSelector = selector;
        console.log(`${MOD} ✅ Selector encontrado: ${selector}`);
        break;
      }
    }
    
    if (targetSelector) {
      console.log(`${MOD} Configurando lazy loading con selector: ${targetSelector}`);
      w.DOMUtils.onVisibleOnce(targetSelector, function(el) {
        console.log(`${MOD} ✅ Contenedor visible, inicializando módulo...`);
        inicializarModulo();
      }, { once: true, timeout: 30000 });
    } else {
      console.warn(`${MOD} ⚠️ Selectores de contenedor no encontrados, usando fallback DOMContentLoaded`);
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', function() {
          setTimeout(inicializarModulo, 100);
        });
      } else {
        setTimeout(inicializarModulo, 100);
      }
    }
  } else {
    console.warn(`${MOD} ⚠️ DOMUtils.onVisibleOnce no está disponible, usando fallback DOMContentLoaded`);
    if (d.readyState === 'loading') {
      d.addEventListener('DOMContentLoaded', function() {
        setTimeout(inicializarModulo, 100);
      });
    } else {
      setTimeout(inicializarModulo, 100);
    }
  }
  
  // ⚠️ v2.60: También escuchar cambios de pestaña en Bootstrap para forzar inicialización
  d.addEventListener('shown.bs.tab', function(e) {
    const targetTab = e.target.getAttribute('data-tab') || e.target.getAttribute('data-bs-target') || e.target.getAttribute('href');
    if (targetTab === 'empleados' || targetTab === '#empleados' || targetTab === '#tab-empleados' || targetTab === CONTAINER_ID) {
      console.log(`${MOD} ✅ Tab de empleados mostrado, verificando inicialización...`);
      const containerEl = d.querySelector(CONTAINER_ID);
      if (containerEl) {
        const gridEl = d.querySelector(GRID_ID);
        if (gridEl && (!table || !w.SintelEmpleadosTables || !w.SintelEmpleadosTables.empleados)) {
          console.log(`${MOD} Tabla no inicializada, forzando inicialización...`);
          setTimeout(inicializarModulo, 200);
        } else {
          console.log(`${MOD} Tabla ya inicializada`);
        }
      }
    }
  });

  console.log(`${MOD} ✅ Feature EmpleadosList cargado`);

})(window, document);
