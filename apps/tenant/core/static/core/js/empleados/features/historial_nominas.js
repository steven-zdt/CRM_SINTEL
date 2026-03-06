/**
 * historial_nominas.js - Feature: Historial de Nóminas
 * ⚠️ Feature-Sliced Architecture v2.60
 * Maneja la visualización y acciones del historial de nóminas
 */
(function (w, d) {
  'use strict';

  const MOD = '[historial.nominas]';
  const API_URL = '/api/v1/empleados/';

  /**
   * Abrir historial de nóminas vía HTMX
   * ⚠️ v2.60: Carga el offcanvas con el historial de nóminas del empleado
   */
  async function openHistorialNominas(empleadoId) {
    if (!empleadoId) {
      console.error(`${MOD} ID de empleado no proporcionado`);
      return;
    }
    
    const url = `${API_URL}${empleadoId}/historial-nominas/`;
    
    if (typeof htmx === 'undefined' || !htmx.ajax) {
      console.error(`${MOD} HTMX no está disponible`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'HTMX no está disponible' } }, MOD);
      }
      return;
    }

    await htmx.ajax('GET', url, {
      target: '#offcanvas-container-historial-nominas',
      swap: 'innerHTML'
    });

    const offcanvasEl = d.getElementById('offcanvas-historial-nominas');
    if (offcanvasEl) {
      const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
      offcanvas.show();
      
      // Inicializar tabla después de que el offcanvas esté visible
      setTimeout(function() {
        initHistorialNominas(empleadoId);
      }, 300);
    }
  }
  
  /**
   * Inicializar tabla de historial de nóminas usando TabulatorFactory
   * ⚠️ v2.60: Usa TabulatorFactory.create() con paginación remota
   */
  function initHistorialNominas(empleadoId) {
    console.log(`${MOD} Inicializando historial de nóminas para empleado ${empleadoId}...`);
    
    // ⚠️ Validación de parámetros
    if (!empleadoId || isNaN(parseInt(empleadoId, 10))) {
      console.error(`${MOD} ❌ ID de empleado inválido: ${empleadoId}`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 400, data: { detail: 'ID de empleado inválido para cargar historial de nóminas.' } },
          MOD
        );
      }
      return;
    }
    
    const gridEl = d.querySelector('#grid-historial-nominas');
    if (!gridEl) {
      console.error(`${MOD} ❌ Contenedor #grid-historial-nominas no encontrado`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: 'Contenedor de historial de nóminas no encontrado. Verifique que el offcanvas esté correctamente cargado.' } },
          MOD
        );
      }
      return;
    }

    // ⚠️ Anti-Zombies Pattern: Destruir instancia previa si existe
    if (w.SintelEmpleadosTables && w.SintelEmpleadosTables.historialNominas) {
      try {
        console.log(`${MOD} ⚠️ Destruyendo instancia previa de historial...`);
        w.SintelEmpleadosTables.historialNominas.destroy();
        w.SintelEmpleadosTables.historialNominas = null;
      } catch (error) {
        console.warn(`${MOD} Error al destruir tabla previa:`, error);
      }
    }
    
    // ⚠️ Anti-Zombies: Limpiar cualquier contenido residual en el contenedor
    try {
      gridEl.innerHTML = '';
      console.log(`${MOD} ✅ Contenedor #grid-historial-nominas limpiado`);
    } catch (error) {
      console.warn(`${MOD} Error al limpiar contenedor:`, error);
    }

    // ⚠️ Validación de dependencias críticas
    if (!w.TabulatorFactory || typeof w.TabulatorFactory.create !== 'function') {
      console.error(`${MOD} ❌ CRÍTICO: TabulatorFactory no está disponible.`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: 'TabulatorFactory no está disponible. Verifique que assets_core.html se haya cargado correctamente.' } },
          MOD
        );
      }
      return;
    }
    
    if (!w.http || typeof w.http !== 'function') {
      console.error(`${MOD} ❌ CRÍTICO: window.http no está disponible.`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: 'window.http no está disponible. Verifique que http.js se haya cargado correctamente.' } },
          MOD
        );
      }
      return;
    }
    
    console.log(`${MOD} ✅ Dependencias validadas: TabulatorFactory y window.http disponibles`);

    // ⚠️ v2.60: Endpoint específico para historial de nóminas del empleado
    const historialUrl = `/api/v1/empleados/devengos/?empleado=${empleadoId}`;
    
    // ⚠️ v2.60: Columnas del historial de nóminas
    const columns = [
      { title: "ID", field: "id", visible: false },
      { 
        title: "Periodo", 
        field: "periodo_mes", 
        width: 120,
        formatter: (cell) => {
          const val = cell.getValue();
          return val || '-';
        }
      },
      { 
        title: "Fecha de Pago", 
        field: "fecha_pago", 
        width: 140,
        formatter: (cell) => {
          const val = cell.getValue();
          return val ? new Date(val).toLocaleDateString('es-CO') : '-';
        }
      },
      { 
        title: "Días Laborados", 
        field: "dias_laborados", 
        width: 130,
        formatter: (cell) => {
          const val = cell.getValue();
          return val ? parseFloat(val).toFixed(2) : '-';
        }
      },
      { 
        title: "Neto a Pagar (COP)", 
        field: "neto_pagar", 
        width: 180,
        formatter: (cell) => {
          const val = cell.getValue();
          if (!val) return '-';
          const num = parseFloat(val);
          if (isNaN(num)) return '-';
          return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: 'COP',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          }).format(num);
        }
      },
      { 
        title: "Estado", 
        field: "anulado", 
        width: 100,
        formatter: (cell) => {
          const anulado = cell.getValue();
          if (anulado) {
            return '<span class="badge bg-danger">Anulado</span>';
          }
          return '<span class="badge bg-success">Activo</span>';
        }
      },
      { 
        title: "Acciones", 
        hozAlign: "center", 
        width: 220, 
        headerSort: false,
        formatter: (function(empleadoIdParam) {
          return function(cell) {
            const data = cell.getRow().getData();
            const id = data.id;
            const anulado = data.anulado === true;
            
            let html = '<div class="btn-group btn-group-sm" role="group">';
            
            if (!anulado) {
              html += `<button type="button" class="btn btn-outline-info btn-sm btn-ver-nomina-historial" 
                       data-devengo-id="${id}" 
                       title="Ver/Editar Nómina">
                <i class="bi bi-eye me-1"></i>Ver
              </button>`;
              
              html += `<button type="button" class="btn btn-outline-danger btn-sm btn-eliminar-nomina-historial" 
                       data-devengo-id="${id}" 
                       data-empleado-id="${empleadoIdParam}"
                       title="Eliminar Nómina">
                <i class="bi bi-trash me-1"></i>Eliminar
              </button>`;
            } else {
              html += `<button type="button" class="btn btn-outline-secondary btn-sm" disabled title="Nómina Anulada">
                <i class="bi bi-lock me-1"></i>Anulada
              </button>`;
            }
            
            html += '</div>';
            return html;
          };
        })(empleadoId)
      }
    ];

    // ⚠️ v2.60: Configuración de Tabulator con paginación remota
    const tableConfig = {
      searchInputSelector: '#search-historial-nominas',
      pagination: true,
      paginationMode: "remote",
      paginationSize: 10,
      paginationSizeSelector: [10, 25, 50, 100],
      layout: "fitColumns",
      responsiveLayout: "hide",
      placeholder: "No hay nóminas registradas para este empleado",
      locale: "es"
    };

    const table = w.TabulatorFactory.create('#grid-historial-nominas', historialUrl, columns, tableConfig);

    // ⚠️ v2.60: Guardar instancia en singleton global
    if (!w.SintelEmpleadosTables) {
      w.SintelEmpleadosTables = {};
    }
    w.SintelEmpleadosTables.historialNominas = table;

    // ⚠️ v2.60: Configurar event delegation para botones de acciones
    const offcanvasHistorial = d.querySelector('#offcanvas-historial-nominas');
    if (offcanvasHistorial) {
      // ⚠️ Anti-Zombies: Usar atributo de marca para evitar múltiples listeners
      if (offcanvasHistorial.hasAttribute('data-historial-listener')) {
        console.log(`${MOD} ⚠️ Listener ya existe en offcanvas historial, omitiendo duplicado...`);
      } else {
        offcanvasHistorial.setAttribute('data-historial-listener', 'true');
        
        // Agregar event delegation al offcanvas
        offcanvasHistorial.addEventListener('click', function(e) {
          // Botón Ver/Editar
          const btnVer = e.target.closest('.btn-ver-nomina-historial');
          if (btnVer) {
            e.preventDefault();
            e.stopPropagation();
            
            const devengoId = btnVer.getAttribute('data-devengo-id');
            
            if (!devengoId) {
              console.error(`${MOD} ❌ ID de devengo no encontrado`);
              if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError(
                  { status: 400, data: { detail: 'Error: No se pudo identificar la nómina a ver.' } },
                  MOD
                );
              }
              return;
            }
            
            console.log(`${MOD} Abriendo offcanvas de nómina para ver/editar: ${devengoId}`);
            
            btnVer.disabled = true;
            const originalHTML = btnVer.innerHTML;
            btnVer.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Cargando...';
            
            // Usar DevengosEditor para abrir el offcanvas
            if (w.DevengosEditor && typeof w.DevengosEditor.openDevengoOffcanvas === 'function') {
              w.DevengosEditor.openDevengoOffcanvas(null, devengoId).then(function() {
                btnVer.disabled = false;
                btnVer.innerHTML = originalHTML;
              }).catch(function(error) {
                console.error(`${MOD} ❌ Error al cargar offcanvas de nómina:`, error);
                btnVer.disabled = false;
                btnVer.innerHTML = originalHTML;
                
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                  w.UIManager.handleError(
                    { status: 500, data: { detail: `Error al cargar el formulario de nómina: ${error.message || error}` } },
                    MOD,
                    {errorContainerSelector: '#form-historial-feedback'}
                  );
                }
              });
            } else {
              console.error(`${MOD} ❌ DevengosEditor no está disponible`);
              btnVer.disabled = false;
              btnVer.innerHTML = originalHTML;
            }
            
            return;
          }
          
          // Botón Eliminar
          const btnEliminar = e.target.closest('.btn-eliminar-nomina-historial');
          if (btnEliminar) {
            e.preventDefault();
            e.stopPropagation();
            
            const devengoId = btnEliminar.getAttribute('data-devengo-id');
            const empleadoId = btnEliminar.getAttribute('data-empleado-id');
            
            if (!devengoId || !empleadoId) {
              console.error(`${MOD} ❌ ID de devengo o empleado no encontrado`);
              if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                w.UIManager.notifyError(
                  { status: 400, data: { detail: 'Error: No se pudo identificar la nómina a eliminar.' } },
                  MOD
                );
              }
              return;
            }
            
            // Confirmar eliminación
            if (!confirm('¿Está seguro de que desea eliminar esta nómina? Esta acción no se puede deshacer.')) {
              return;
            }
            
            btnEliminar.disabled = true;
            const originalHTML = btnEliminar.innerHTML;
            btnEliminar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando...';
            
            // Realizar petición DELETE usando window.http
            if (w.http && typeof w.http === 'function') {
              w.http('DELETE', `/api/v1/empleados/devengos/${devengoId}/`)
                .then(function(response) {
                  if (response.ok) {
                    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                      w.SintelFeedback.success('Nómina eliminada correctamente');
                    }
                    
                    // Refrescar tabla de historial
                    if (w.SintelEmpleadosTables && w.SintelEmpleadosTables.historialNominas) {
                      try {
                        w.SintelEmpleadosTables.historialNominas.replaceData();
                        console.log(`${MOD} ✅ Tabla de historial refrescada después de eliminar`);
                      } catch (error) {
                        console.error(`${MOD} ❌ Error al refrescar tabla:`, error);
                      }
                    }
                    
                    // También refrescar tabla principal de empleados
                    if (w.EmpleadosList && typeof w.EmpleadosList.refresh === 'function') {
                      w.EmpleadosList.refresh();
                    }
                  } else {
                    btnEliminar.disabled = false;
                    btnEliminar.innerHTML = originalHTML;
                    
                    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                      w.UIManager.handleError(response, MOD, {errorContainerSelector: '#form-historial-feedback'});
                    }
                  }
                })
                .catch(function(error) {
                  console.error(`${MOD} ❌ Error en petición DELETE:`, error);
                  btnEliminar.disabled = false;
                  btnEliminar.innerHTML = originalHTML;
                  
                  if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(
                      { status: 500, data: { detail: `Error de conexión: ${error.message || error}` } },
                      MOD,
                      {errorContainerSelector: '#form-historial-feedback'}
                    );
                  }
                });
            } else {
              console.error(`${MOD} ❌ window.http no está disponible`);
              btnEliminar.disabled = false;
              btnEliminar.innerHTML = originalHTML;
            }
          }
        });
        console.log(`${MOD} ✅ Event delegation configurado para botones de acciones en historial`);
      }
    } else {
      console.warn(`${MOD} ⚠️ Offcanvas #offcanvas-historial-nominas no encontrado, event delegation no configurado`);
    }

    console.log(`${MOD} ✅ Historial de nóminas inicializado correctamente para empleado ${empleadoId}`);
  }

  /**
   * Anular devengo (nómina)
   * ⚠️ v2.60: Realiza POST al endpoint de anulación
   */
  async function anular(devengoId) {
    if (!devengoId) {
      console.error(`${MOD} ID de devengo no proporcionado`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 400, data: { detail: 'Se requiere un ID de devengo para anular la nómina.' } },
          MOD
        );
      }
      return;
    }

    if (!confirm('¿Está seguro de que desea anular esta nómina? Esta acción marcará la nómina como anulada.')) {
      return;
    }

    if (!w.http || typeof w.http !== 'function') {
      console.error(`${MOD} ❌ window.http no está disponible`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: 'window.http no está disponible. Verifique que http.js se haya cargado correctamente.' } },
          MOD
        );
      }
      return;
    }

    const res = await w.http('POST', `/api/v1/empleados/devengos/${devengoId}/anular/`);
    
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD, {errorContainerSelector: '#form-historial-feedback'});
      }
      return;
    }

    if (w.SintelFeedback) {
      w.SintelFeedback.success('Nómina anulada correctamente');
    }

    // Refrescar tabla de historial
    if (w.SintelEmpleadosTables && w.SintelEmpleadosTables.historialNominas) {
      try {
        w.SintelEmpleadosTables.historialNominas.replaceData();
        console.log(`${MOD} ✅ Tabla de historial refrescada después de anular`);
      } catch (error) {
        console.error(`${MOD} ❌ Error al refrescar tabla:`, error);
      }
    }

    // También refrescar tabla principal de empleados
    if (w.EmpleadosList && typeof w.EmpleadosList.refresh === 'function') {
      w.EmpleadosList.refresh();
    }
  }

  // Exponer namespace global
  w.HistorialNominas = {
    open: openHistorialNominas,
    openHistorialNominas: openHistorialNominas, // Alias para compatibilidad
    initHistorialNominas: initHistorialNominas,
    anular: anular
  };

  console.log(`${MOD} ✅ Feature HistorialNominas cargado`);

})(window, document);
