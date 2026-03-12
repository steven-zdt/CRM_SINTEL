/**
 * cotizaciones.page.js - Módulo Cotizaciones v2.60 - Tabulator Implementation
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ CONVERSIÓN A FACTURA: Endpoint especial para convertir cotización aceptada a factura
 * ⚠️ AISLAMIENTO: 100% privado (Tenant-Specific), sin referencias al esquema público
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce(), fmtMoney()
 * - w.cotizacionesAPI (definido en cotizaciones.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.CotizacionesHelpers (definido en cotizaciones.helpers.js) - funciones utilitarias
 */
(function (w, d) {
  'use strict';

  const MOD = 'cotizaciones.page';
  const TABLE_SELECTOR = '#tabla-cotizaciones-principal'; // ⚠️ Sincronizado con Modelo Cotizacion - ID en list.html: tabla-cotizaciones-principal
  const SEARCH_SELECTOR = '#search-cotizacion'; // ⚠️ Debe coincidir con el ID en list.html (search-cotizacion)
  const CONFIG_TABLE_SELECTOR = '#grid-configuraciones-parametros'; // ⚠️ Tabla de configuraciones
  const CONFIG_SEARCH_SELECTOR = '#search-configuracion'; // ⚠️ Búsqueda de configuraciones
  const CONFIG_API_URL = '/api/v1/cotizaciones/configuracion/';
  const API_URL = '/api/v1/cotizaciones/';
  const TAB_ID = '#tab-cotizaciones';
  const SUBTAB_ID = '#subtab-cotizaciones'; // ⚠️ Sub-tab donde está la tabla
  let table = null;
  let configTable = null; // ⚠️ Tabla de configuraciones
  let tableInitialized = false; // ⚠️ v2.61: Flag para evitar inicializaciones múltiples

  /**
   * Formatear moneda usando localizador del sistema
   */
  function fmtMoney(v) {
    if (w.DOMUtils && typeof w.DOMUtils.fmtMoney === 'function') {
      return w.DOMUtils.fmtMoney(v);
    }
    // Fallback: formateo básico
    const num = parseFloat(v) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(num);
  }

  /**
   * Formatear fecha en formato corto (DD/MM/YYYY)
   */
  function formatDate(dateString) {
    if (!dateString) return '-';
    // ⚠️ v2.60: Helper simple - try/catch interno para parsing de fecha (no es error de API)
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return dateString;
      return date.toLocaleDateString('es-CO', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    } catch (err) {
      // ⚠️ v2.60: Error de parsing local, retornar valor original
      return dateString;
    }
  }

  /**
   * Verificar si una cotización está vencida
   */
  function isVencida(fechaVencimiento) {
    if (!fechaVencimiento) return false;
    // ⚠️ v2.60: Helper simple - try/catch interno para parsing de fecha (no es error de API)
    try {
      const fechaVenc = new Date(fechaVencimiento);
      const hoy = new Date();
      hoy.setHours(0, 0, 0, 0);
      fechaVenc.setHours(0, 0, 0, 0);
      return fechaVenc < hoy;
    } catch (err) {
      // ⚠️ v2.60: Error de parsing local, retornar false (no vencida)
      return false;
    }
  }

  /**
   * Formatear badge de estado con lógica de vencimiento
   */
  function formatEstado(estado, estadoDisplay, fechaVencimiento) {
    if (!estado) return '-';
    
    const estadoText = estadoDisplay || estado;
    const vencida = isVencida(fechaVencimiento);
    let badgeClass = 'badge bg-secondary';
    
    // ⚠️ v2.40: Cotizaciones VENCIDAS se muestran en danger
    if (vencida && estado.toUpperCase() !== 'ACEPTADA' && estado.toUpperCase() !== 'CANCELADA') {
      badgeClass = 'badge bg-danger';
    } else {
      switch (estado.toUpperCase()) {
        case 'ACEPTADA':
          badgeClass = 'badge bg-success';
          break;
        case 'PENDIENTE':
          badgeClass = 'badge bg-warning text-dark';
          break;
        case 'RECHAZADA':
        case 'CANCELADA':
          badgeClass = 'badge bg-danger';
          break;
        case 'ENVIADA':
          badgeClass = 'badge bg-info';
          break;
        default:
          badgeClass = 'badge bg-secondary';
      }
    }
    
    return `<span class="${badgeClass}">${estadoText}</span>`;
  }

  /**
   * Fetcher Resiliente v2.60: Maneja HATEOAS (results) y arrays planos
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function fetchCotizacionList(params = {}) {
    if (!w.cotizacionesAPI || typeof w.cotizacionesAPI.list !== 'function') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API de cotizaciones no disponible' } }, `[${MOD}]`);
      }
      return [];
    }

    const response = await w.cotizacionesAPI.list(params);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!response.ok) {
      // ⚠️ v2.60: Manejo silencioso de errores 401 (el interceptor global maneja la sesión)
      if (response.status === 401) {
        return [];
      }
      
      // ⚠️ v2.60: Delegar a UIManager para mostrar error
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(response, `[${MOD}]`);
      }
      return [];
    }

    // Manejar respuesta HATEOAS (results) o array plano
    let data = [];
    if (response.data) {
      if (Array.isArray(response.data)) {
        // Array plano
        data = response.data;
      } else if (response.data.results && Array.isArray(response.data.results)) {
        // HATEOAS con results
        data = response.data.results;
      } else if (response.data.data && Array.isArray(response.data.data)) {
        // Formato alternativo
        data = response.data.data;
      } else {
        // ⚠️ v2.60: Aislamiento Gradual - Sin logs de formato no reconocido
        data = [];
      }
    }

    // ⚠️ CRÍTICO: Asegurar que siempre retornamos un array
    return Array.isArray(data) ? data : [];
  }

  /**
   * ⚠️ v2.60: Obtener lista de configuraciones desde la API
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function fetchConfiguracionesList(params = {}) {
    if (!w.cotizacionesAPI || typeof w.cotizacionesAPI.listConfiguraciones !== 'function') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API de configuraciones no disponible' } }, `[${MOD}]`);
      }
      return [];
    }

    // ⚠️ v2.60: Asegurar que siempre se incluya es_activo=true si no se especifica explícitamente
    const finalParams = { ...params };
    if (finalParams.es_activo === undefined) {
      finalParams.es_activo = true;
    }
    
    console.log('[cotizaciones.page] Llamando a listConfiguraciones con params:', finalParams);
    const response = await w.cotizacionesAPI.listConfiguraciones(finalParams);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!response.ok) {
      if (response.status === 401) {
        return [];
      }
      
      // ⚠️ v2.60: Delegar a UIManager para mostrar error
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(response, `[${MOD}]`);
      }
      return [];
    }

    let data = [];
    if (response.data) {
      if (Array.isArray(response.data)) {
        data = response.data;
      } else if (response.data.results && Array.isArray(response.data.results)) {
        data = response.data.results;
      }
    }
    return data;
  }

  /**
   * ⚠️ v2.60: Obtener columnas para tabla de configuraciones
   */
  function getConfiguracionesColumns() {
    return [
      {
        title: "Nombre",
        field: "nombre_configuracion",
        width: 250,
        sorter: "string",
        headerFilter: false // ⚠️ Explícitamente deshabilitado para evitar errores
      },
      {
        title: "Tipo",
        field: "tipo_plantilla_display",
        formatter: function(cell) {
          const tipo = cell.getValue();
          const tipos = {
            'MIXTO': 'badge bg-primary',
            'EQUIPO': 'badge bg-info',
            'MATERIAL': 'badge bg-warning text-dark',
            'SERVICIO': 'badge bg-success'
          };
          const badgeClass = tipos[tipo] || 'badge bg-secondary';
          return `<span class="${badgeClass}">${tipo || '-'}</span>`;
        },
        width: 120,
        hozAlign: "center",
        headerFilter: false // ⚠️ Explícitamente deshabilitado para evitar errores
      },
      {
        title: "Activo",
        field: "es_activo",
        formatter: function(cell) {
          const isActive = cell.getValue();
          return isActive 
            ? '<i class="bi bi-check-circle-fill text-success"></i>' 
            : '<i class="bi bi-x-circle-fill text-secondary"></i>';
        },
        width: 80,
        hozAlign: "center",
        headerFilter: false // ⚠️ Explícitamente deshabilitado para evitar errores
      },
      {
        title: "IVA (%)",
        field: "iva_porcentaje_default",
        formatter: function(cell) {
          const val = cell.getValue();
          return val ? `${parseFloat(val).toFixed(2)}%` : '-';
        },
        width: 100,
        hozAlign: "right",
        sorter: "number",
        headerFilter: false // ⚠️ Explícitamente deshabilitado para evitar errores
      },
      {
        title: "AIU",
        field: "usa_aiu",
        formatter: function(cell) {
          const usaAIU = cell.getValue();
          return usaAIU 
            ? '<span class="badge bg-success">Sí</span>' 
            : '<span class="badge bg-secondary">No</span>';
        },
        width: 80,
        hozAlign: "center",
        headerFilter: false // ⚠️ Explícitamente deshabilitado para evitar errores
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id = rowData.id;
          
          if (!id) return '-';
          
          let buttons = '';
          buttons += `<button class="btn btn-sm btn-link text-primary p-0 me-2" data-action="editar-config" data-id="${id}" title="Editar Configuración"><i class="fas fa-pencil-alt"></i></button>`;
          buttons += `<button class="btn btn-sm btn-link text-danger p-0 me-2" data-action="eliminar-config" data-id="${id}" title="Eliminar Configuración"><i class="fas fa-trash"></i></button>`;
          
          return buttons || '-';
        },
        headerSort: false,
        headerFilter: false, // ⚠️ Columna de acciones no necesita filtro
        hozAlign: "center",
        width: 150
      }
    ];
  }

  /**
   * ⚠️ v2.60: Inicializar tabla de configuraciones
   */
  function initConfiguracionesTable() {
    if (!w.TabulatorFactory) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'TabulatorFactory no está disponible' } }, `[${MOD}]`);
      }
      return null;
    }

    const container = d.querySelector(CONFIG_TABLE_SELECTOR);
    if (!container) {
      // ⚠️ v2.60: Contenedor no encontrado (puede estar en collapse cerrado), retornar null
      return null;
    }

    let columns = getConfiguracionesColumns();
    
    // ⚠️ CRÍTICO: Sanitizar columnas antes de pasarlas al Factory
    columns = sanitizeColumns(columns);
    
    // ⚠️ CRÍTICO: Usar URL directa con slash final para evitar 404
    // TabulatorFactory manejará automáticamente la paginación y búsqueda
    const tableConfig = {
      searchInputSelector: CONFIG_SEARCH_SELECTOR,
      // ⚠️ v2.60: Parámetros fijos para filtrar solo activos
      ajaxParams: {
        es_activo: true
      }
      // ⚠️ v2.60: No usar ajaxURL personalizado, dejar que TabulatorFactory use CONFIG_API_URL directamente
      // Esto asegura que la URL termine con / y Django la reconozca correctamente
    };

    // ⚠️ CRÍTICO: CONFIG_API_URL ya tiene el slash final: '/api/v1/cotizaciones/configuracion/'
    const configTable = w.TabulatorFactory.create(CONFIG_TABLE_SELECTOR, CONFIG_API_URL, columns, tableConfig);

    if (configTable) {
      // Event delegation para botones de acciones
      container.addEventListener('click', function(e) {
        const btn = e.target.closest('button[data-action]');
        if (btn && !btn.disabled) {
          const action = btn.getAttribute('data-action');
          const id = btn.getAttribute('data-id');
          if (id) {
            handleConfigActionClick(action, parseInt(id, 10));
          }
        }
      });
    }

    return configTable;
  }

  /**
   * ⚠️ v2.60: Manejar acciones de la tabla de configuraciones
   */
  function handleConfigActionClick(action, id) {
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de operación
    switch (action) {
      case 'editar-config':
        editarConfiguracion(id);
        break;
      case 'eliminar-config':
        eliminarConfiguracion(id);
        break;
      default:
        // ⚠️ v2.60: Aislamiento Gradual - Sin logs de acción desconocida
        break;
    }
  }

  /**
   * ⚠️ v2.60: Editar configuración
   */
  function editarConfiguracion(id) {
    // TODO: Implementar modal de edición
    if (w.SintelFeedback) {
      w.SintelFeedback.info('Funcionalidad de edición en desarrollo');
    }
  }

  /**
   * ⚠️ v2.60: Eliminar configuración
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function eliminarConfiguracion(id) {
    if (!confirm('¿Está seguro de eliminar este perfil de configuración?')) {
      return;
    }

    if (!w.cotizacionesAPI || typeof w.cotizacionesAPI.deleteConfiguracion !== 'function') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API de eliminación no disponible' } }, `[${MOD}]`);
      }
      return;
    }

    const deleteRes = await w.cotizacionesAPI.deleteConfiguracion(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!deleteRes.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(deleteRes, `[${MOD}]`);
      }
      return;
    }

    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Perfil de configuración eliminado correctamente');
    }
    if (configTable) {
      configTable.replaceData();
    }
    // También refrescar selectores de plantillas
    if (w.CotizacionesHelpers && typeof w.CotizacionesHelpers.recargarSelectoresPlantillas === 'function') {
      await w.CotizacionesHelpers.recargarSelectoresPlantillas();
    }
  }

  /**
   * Definir columnas de Tabulator (exactamente 7)
   * ⚠️ v2.40: Nombres de campos según CotizacionListSerializer
   * ⚠️ v2.61: Optimizado para usar todo el ancho disponible de la página
   */
  function getColumns() {
    return [
      {
        title: "NÚMERO",
        field: "codigo_unico", // ⚠️ Sincronización: Usar codigo_unico del modelo (ej: "STS. 0422-2026")
        formatter: function(cell) {
          const value = cell.getValue();
          return value || '-';
        },
        minWidth: 160,
        widthGrow: 1.2,
        headerFilter: "input"
      },
      {
        title: "Fecha",
        field: "fecha_emision",
        formatter: function(cell) {
          return formatDate(cell.getValue());
        },
        minWidth: 110,
        widthGrow: 0.8,
        sorter: "date",
        headerFilter: false // ⚠️ Explícitamente deshabilitado para evitar errores
      },
      {
        title: "CLIENTE",
        field: "cliente_nombre", // ⚠️ Sincronización: Usar cliente_nombre del serializer (ReadOnlyField)
        formatter: function(cell) {
          const value = cell.getValue();
          // ⚠️ Fallback: Si cliente_nombre no está disponible, usar cliente_display
          if (!value) {
            const rowData = cell.getRow().getData();
            return rowData.cliente_display || 'Sin cliente';
          }
          return value;
        },
        minWidth: 250,
        widthGrow: 3, // ⚠️ v2.61: Mayor crecimiento para aprovechar espacio disponible
        headerFilter: "input"
      },
      {
        title: "TOTAL",
        field: "total_con_impuestos", // ⚠️ Sincronización: Usar total_con_impuestos del modelo (campo real)
        formatter: function(cell) {
          const value = cell.getValue();
          // ⚠️ Manejar valores nulos o undefined
          if (value === null || value === undefined) {
            return fmtMoney(0);
          }
          return fmtMoney(value);
        },
        minWidth: 140,
        widthGrow: 1.5,
        hozAlign: "right",
        sorter: "number",
        headerFilter: false, // ⚠️ Explícitamente deshabilitado para evitar errores
        bottomCalc: "sum", // ⚠️ Calcular suma total en el pie de la tabla
        bottomCalcFormatter: function(cell) {
          const value = parseFloat(cell.getValue()) || 0;
          return fmtMoney(value);
        }
      },
      {
        title: "Estado",
        field: "estado",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          return formatEstado(rowData.estado, rowData.estado_display, rowData.fecha_vencimiento);
        },
        minWidth: 120,
        widthGrow: 1,
        headerFilter: "select",
        headerFilterParams: {
          values: {
            "": "Todos",
            "BORRADOR": "Borrador",
            "ENVIADA": "Enviada",
            "ACEPTADA": "Aceptada"
          }
        }
      },
      {
        title: "Vencimiento",
        field: "fecha_vencimiento",
        formatter: function(cell) {
          const fechaStr = cell.getValue();
          const fechaFormateada = formatDate(fechaStr);
          const vencida = isVencida(fechaStr);
          
          // ⚠️ v2.40: Mostrar fecha vencida en danger
          if (vencida) {
            return `<span class="text-danger">${fechaFormateada}</span>`;
          }
          return fechaFormateada;
        },
        minWidth: 120,
        widthGrow: 1,
        sorter: "date",
        headerFilter: false // ⚠️ Explícitamente deshabilitado para evitar errores
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const uuid = rowData.uuid || rowData.id; // Preferir UUID
          const estado = rowData.estado ? rowData.estado.toUpperCase() : '';
          
          if (!uuid) return '-';
          
          let buttons = '';
          
          // ⚠️ v2.61: Botón Editar con HTMX usando nuevo endpoint render-offcanvas/editar/ (alineado con patrón de contabilidad)
          buttons += `
            <button class="btn btn-sm btn-outline-primary"
                    hx-get="/api/v1/cotizaciones/${uuid}/render-offcanvas/editar/"
                    hx-target="#offcanvas-container"
                    hx-swap="innerHTML"
                    hx-indicator="#spinner"
                    data-bs-toggle="offcanvas"
                    data-bs-target="#offcanvas-container"
                    title="Editar Cotización">
              <i class="bi bi-pencil"></i> Editar
            </button>
          `;
          
          // Botón Convertir a Factura (solo si está ACEPTADA)
          if (estado === 'ACEPTADA') {
            buttons += `
              <button class="btn btn-sm btn-link text-success p-0 me-2" data-action="convertir-factura" data-uuid="${uuid}" title="Convertir a Factura">
                <i class="fas fa-file-invoice-dollar"></i>
              </button>
            `;
          }
          
          // Botón Ver PDF
          buttons += `
            <button class="btn btn-sm btn-outline-secondary" 
                    onclick="window.open('${API_URL}${uuid}/exportar-pdf/', '_blank'); return false;"
                    title="Ver PDF">
              <i class="bi bi-file-pdf"></i>
            </button>
          `;
          
          // ⚠️ v2.61: Botón Ver Detalle con HTMX usando nuevo endpoint render-offcanvas/detalle/ (alineado con patrón de contabilidad)
          buttons += `
            <button class="btn btn-sm btn-outline-info"
                    hx-get="/api/v1/cotizaciones/render-offcanvas/detalle/?id=${uuid}"
                    hx-target="#offcanvas-container"
                    hx-swap="innerHTML"
                    hx-indicator="#spinner"
                    data-bs-toggle="offcanvas"
                    data-bs-target="#offcanvas-container"
                    title="Ver Detalle">
              <i class="bi bi-eye"></i> Ver Detalle
            </button>
          `;
          
          // Botón Eliminar
          buttons += `
            <button class="btn btn-sm btn-link text-danger p-0 me-2" data-action="eliminar" data-uuid="${uuid}" title="Eliminar Cotización">
              <i class="fas fa-trash"></i>
            </button>
          `;
          
          return `<div class="d-flex gap-1">${buttons}</div>` || '-';
        },
        headerSort: false,
        headerFilter: false, // ⚠️ Columna de acciones no necesita filtro
        hozAlign: "center",
        minWidth: 280,
        widthGrow: 1.5,
        widthShrink: 0 // ⚠️ v2.61: No reducir ancho de acciones para mantener botones visibles
      }
    ];
  }

  /**
   * ⚠️ Sanitizar columnas: Asegurar que headerFilter nunca sea true o undefined
   * Convierte headerFilter: true a "input" y elimina cualquier undefined
   */
  function sanitizeColumns(columns) {
    if (!Array.isArray(columns)) return columns;
    
    return columns.map(col => {
      const sanitized = { ...col };
      
      // ⚠️ CRÍTICO: Sanitizar headerFilter
      if (sanitized.headerFilter === true) {
        sanitized.headerFilter = "input";
      } else if (sanitized.headerFilter === undefined || sanitized.headerFilter === null) {
        // Si no está definido, deshabilitarlo explícitamente
        sanitized.headerFilter = false;
      } else if (typeof sanitized.headerFilter === 'string') {
        // Validar que sea un string válido
        const validFilters = ['input', 'number', 'text', 'select', 'list', 'tickCross', 'date'];
        if (!validFilters.includes(sanitized.headerFilter)) {
          sanitized.headerFilter = "input"; // Fallback seguro
        }
      }
      
      // ⚠️ CRÍTICO: Sanitizar editor (no debe ser undefined)
      if (sanitized.editor === undefined || sanitized.editor === null) {
        // Si no hay editor definido y hay headerFilter, mantener editor como false
        if (sanitized.headerFilter && sanitized.headerFilter !== false) {
          sanitized.editor = false; // No editable por defecto
        }
      } else if (typeof sanitized.editor === 'boolean' && sanitized.editor === true) {
        // Si editor: true, convertirlo a "input" (Tabulator no acepta true)
        sanitized.editor = "input";
      }
      
      return sanitized;
    });
  }

  /**
   * Inicializar tabla Tabulator
   */
  function initTable() {
    // ⚠️ v2.61: Evitar inicializaciones múltiples
    if (tableInitialized && table) {
      console.log(`[${MOD}] Tabla ya inicializada, omitiendo...`);
      return table;
    }
    
    if (!w.TabulatorFactory) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'TabulatorFactory no está disponible' } }, `[${MOD}]`);
      }
      return null;
    }

    let columns = getColumns();
    
    // ⚠️ CRÍTICO: Sanitizar columnas antes de pasarlas al Factory
    columns = sanitizeColumns(columns);
    
    // Configurar ajaxURL con fetcher personalizado
    const tableConfig = {
      searchInputSelector: SEARCH_SELECTOR,
      layout: "fitDataFill", // ⚠️ v2.61: Usar fitDataFill para aprovechar todo el ancho disponible
      ajaxURL: function(url, config, params) {
        // Usar fetcher resiliente
        return fetchCotizacionList(params).then(data => {
          // ⚠️ CRÍTICO: Asegurar que siempre retornamos un array
          return Array.isArray(data) ? data : [];
        }).catch(err => {
          // ⚠️ v2.60: Delegar a UIManager si es un error de API
          if (err && err.status && w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError(err, `[${MOD}]`);
          }
          return [];
        });
      }
    };

    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, columns, tableConfig);
    
    // ⚠️ v2.61: Marcar como inicializada si se creó correctamente
    if (table) {
      tableInitialized = true;
      console.log(`[${MOD}] Tabla inicializada correctamente`);
    }

    // ⚠️ FASE 1: Event delegation para botones de acciones (solo para botones sin HTMX)
    if (table) {
      const container = d.querySelector(TABLE_SELECTOR);
      if (container) {
        container.addEventListener('click', function(e) {
          const btn = e.target.closest('button[data-action]');
          if (btn && !btn.disabled) {
            const action = btn.getAttribute('data-action');
            const id = btn.getAttribute('data-id');
            const uuid = btn.getAttribute('data-uuid');
            const identifier = uuid || id; // Preferir UUID si está disponible
            if (identifier) {
              handleActionClick(action, identifier);
            }
          }
        });
      }
      
      // ⚠️ FASE 1: Asegurar que HTMX procese los nuevos botones después de renderizar
      // Esto es necesario porque Tabulator renderiza las celdas dinámicamente
      if (table && typeof table.on === 'function') {
        table.on('dataLoaded', function() {
          // ⚠️ FASE 1: Procesar elementos HTMX después de cargar datos
          if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
            const container = d.querySelector(TABLE_SELECTOR);
            if (container) {
              htmx.process(container);
            }
          }
        });
        
        table.on('dataProcessed', function() {
          // ⚠️ FASE 1: Procesar elementos HTMX después de procesar datos
          if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
            const container = d.querySelector(TABLE_SELECTOR);
            if (container) {
              htmx.process(container);
            }
          }
        });
      }
    }

    return table;
  }

  /**
   * Manejar clicks en botones de acciones
   * ⚠️ v2.60: Usa UUID en lugar de ID para seguridad
   */
  function handleActionClick(action, uuid) {
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de operación
    switch (action) {
      case 'editar':
        editar(uuid);
        break;
      case 'ver':
        verDetalle(uuid);
        break;
      case 'eliminar':
        handleDelete(uuid);
        break;
      case 'convertir-factura':
        handleConvertirAFactura(uuid);
        break;
      default:
        // ⚠️ v2.60: Aislamiento Gradual - Sin logs de acción desconocida
        break;
    }
  }

  /**
   * Editar cotización
   * ⚠️ v2.61: Usa UUID - Abre el editor en offcanvas usando el nuevo endpoint
   * Alineado con patrón de contabilidad: /api/v1/cotizaciones/{uuid}/render-offcanvas/editar/
   */
  function editar(uuid) {
    if (!uuid) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 400, data: { detail: 'UUID de cotización no proporcionado' } }, `[${MOD}]`);
      }
      return;
    }
    
    // ⚠️ v2.61: Usar nuevo endpoint render-offcanvas/editar/ alineado con patrón de contabilidad
    const editorUrl = `/api/v1/cotizaciones/${uuid}/render-offcanvas/editar/`;
    const editorContainer = d.getElementById('offcanvas-container');
    
    if (!editorContainer) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Contenedor del editor no disponible' } }, `[${MOD}]`);
      }
      return;
    }
    
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', editorUrl, {
        target: '#offcanvas-container',
        swap: 'innerHTML'
      }).then(() => {
        if (w.bootstrap && w.bootstrap.Offcanvas) {
          const editorOffcanvasInstance = w.bootstrap.Offcanvas.getOrCreateInstance(editorContainer);
          editorOffcanvasInstance.show();
        }
      }).catch((error) => {
        console.error(`[${MOD}] Error al cargar el editor:`, error);
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 500, data: { detail: 'Error al cargar el editor de cotización' } }, `[${MOD}]`);
        }
      });
    } else {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'HTMX no está disponible' } }, `[${MOD}]`);
      }
    }
  }

  /**
   * Ver detalle de cotización
   * ⚠️ v2.61: Usa UUID - Abre el offcanvas de detalle en modo solo lectura usando HTMX
   * Alineado con patrón de contabilidad: /api/v1/cotizaciones/render-offcanvas/detalle/?id={uuid}
   */
  function verDetalle(uuid) {
    if (!uuid) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 400, data: { detail: 'UUID de cotización no proporcionado' } }, `[${MOD}]`);
      }
      return;
    }
    
    // ⚠️ v2.61: Usar nuevo endpoint render-offcanvas/detalle/ alineado con patrón de contabilidad
    const detalleUrl = `/api/v1/cotizaciones/render-offcanvas/detalle/?id=${uuid}`;
    const detalleContainer = d.getElementById('offcanvas-container');
    
    if (!detalleContainer) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Contenedor del offcanvas no disponible' } }, `[${MOD}]`);
      }
      return;
    }
    
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', detalleUrl, {
        target: '#offcanvas-container',
        swap: 'innerHTML'
      }).then(() => {
        if (w.bootstrap && w.bootstrap.Offcanvas) {
          const detalleOffcanvasInstance = w.bootstrap.Offcanvas.getOrCreateInstance(detalleContainer);
          detalleOffcanvasInstance.show();
        }
      }).catch((error) => {
        console.error(`[${MOD}] Error al cargar el detalle:`, error);
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 500, data: { detail: 'Error al cargar el detalle de cotización' } }, `[${MOD}]`);
        }
      });
    } else {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'HTMX no está disponible' } }, `[${MOD}]`);
      }
    }
  }

  /**
   * Crear nueva cotización
   */
  function crear() {
    // ⚠️ v2.60: Verificar disponibilidad con múltiples estrategias
    // ⚠️ v2.60: La creación de cotizaciones se maneja exclusivamente en cotizacion_crear.js
    // No es necesario llamar a showCreate() aquí, cotizacion_crear.js se inicializa automáticamente cuando HTMX carga el offcanvas
  }

  /**
   * Handle Delete con lógica de "Inactivación" v2.40
   * ⚠️ v2.60: Usa UUID y actualiza estado antes de eliminar
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function handleDelete(uuid) {
    if (!confirm('¿Está seguro de eliminar esta cotización? Esta acción cambiará el estado a CANCELADA y luego eliminará el registro.')) {
      return;
    }

    // Paso 1: Inactivar (PATCH) - Cambiar estado a CANCELADA
    if (w.cotizacionesAPI && typeof w.cotizacionesAPI.update === 'function') {
      const estadoRes = await w.cotizacionesAPI.update(uuid, { estado: 'CANCELADA' });
      
      // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
      if (!estadoRes.ok) {
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          w.UIManager.handleError(estadoRes, `[${MOD}]`);
        }
        return;
      }
      
      // ⚠️ v2.60: Aislamiento Gradual - Sin logs de éxito
    } else {
      // ⚠️ v2.60: Si update no está disponible, continuar con delete directamente
    }

    // Paso 2: Eliminar registro (DELETE)
    if (!w.cotizacionesAPI || typeof w.cotizacionesAPI.delete !== 'function') {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API de eliminación no disponible' } }, `[${MOD}]`);
      }
      return;
    }

    const deleteRes = await w.cotizacionesAPI.delete(uuid);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!deleteRes.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(deleteRes, `[${MOD}]`);
      }
      return;
    }

    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Cotización eliminada correctamente');
    }
    // Refrescar tabla
    if (table) {
      table.replaceData();
    }
  }

  /**
   * Convertir cotización ACEPTADA a factura
   * ⚠️ v2.60: Usa UUID - Funcionalidad pendiente de implementación en backend
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch
   */
  async function handleConvertirAFactura(uuid) {
    if (!confirm('¿Está seguro de convertir esta cotización ACEPTADA a factura? Esta acción es irreversible.')) {
      return;
    }

    if (!w.cotizacionesAPI) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API de cotizaciones no disponible' } }, `[${MOD}]`);
      }
      return;
    }

    // ⚠️ TODO: Implementar endpoint de conversión en backend
    // Por ahora, mostrar mensaje informativo
    if (w.SintelFeedback) {
      w.SintelFeedback.info('La funcionalidad de conversión a factura estará disponible próximamente');
    }
  }

  /**
   * Configurar eventos de botones
   */
  function configurarEventos() {
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de operación
    
    // Botón crear - ⚠️ v2.60: Simplificado según auditoría
    const btnCrear = d.getElementById('btn-cotizaciones-crear');
    if (btnCrear) {
      // Remover cualquier listener anterior
      const nuevoBtn = btnCrear.cloneNode(true);
      nuevoBtn.removeAttribute('onclick');
      btnCrear.parentNode.replaceChild(nuevoBtn, btnCrear);
      
      // ⚠️ v2.60: Manejador simplificado - llamada directa al objeto global
      nuevoBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // ⚠️ v2.60: La creación se maneja en cotizacion_crear.js, no es necesario llamar a showCreate()
        // El botón "Nueva Cotización" usa HTMX para cargar el offcanvas y cotizacion_crear.js maneja toda la lógica
      });
    }

    // ⚠️ v2.60: El botón "Ver Parámetros" ahora usa HTMX directamente en el HTML
    // No necesita event listener adicional, HTMX maneja la carga del offcanvas
    // El botón está configurado con hx-get, hx-target y data-bs-toggle en list.html

    // Botón refrescar
    const btnRefrescar = d.getElementById('btn-refrescar-cotizaciones');
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        if (table) {
          table.replaceData();
        }
      });
    }
  }

  /**
   * ⚠️ v2.61: Limpiar estado del módulo (usado al cambiar de página o reiniciar)
   */
  function limpiarEstado() {
    if (table && typeof table.destroy === 'function') {
      try {
        table.destroy();
      } catch (e) {
        console.warn(`[${MOD}] Error al destruir tabla principal:`, e);
      }
    }
    if (configTable && typeof configTable.destroy === 'function') {
      try {
        configTable.destroy();
      } catch (e) {
        console.warn(`[${MOD}] Error al destruir tabla de configuraciones:`, e);
      }
    }
    table = null;
    configTable = null;
    tableInitialized = false;
    console.log(`[${MOD}] Estado limpiado`);
  }

  /**
   * ⚠️ v2.61: Cargar estadísticas desde el backend
   */
  async function cargarEstadisticas() {
    try {
      if (!w.http || typeof w.http !== 'function') {
        console.warn(`[${MOD}] w.http no disponible para cargar estadísticas`);
        return;
      }

      const response = await w.http('GET', `${API_URL}estadisticas/`);
      
      if (response && response.ok && response.data) {
        const stats = response.data;
        
        // Actualizar Total Neto
        const elTotalNeto = d.getElementById('total-cotizaciones-neto');
        if (elTotalNeto) {
          elTotalNeto.textContent = fmtMoney(parseFloat(stats.total_neto) || 0);
        }
        
        // Actualizar Cantidad Total
        const elCantidadTotal = d.getElementById('cantidad-cotizaciones');
        if (elCantidadTotal) {
          elCantidadTotal.textContent = stats.cantidad_total || 0;
        }
        
        // Actualizar Aceptadas
        const elAceptadas = d.getElementById('cantidad-aceptadas');
        if (elAceptadas) {
          elAceptadas.textContent = stats.cantidad_aceptadas || 0;
        }
        
        // Actualizar Enviadas
        const elEnviadas = d.getElementById('cantidad-enviadas');
        if (elEnviadas) {
          elEnviadas.textContent = stats.cantidad_enviadas || 0;
        }
        
        // Actualizar Borrador
        const elBorrador = d.getElementById('cantidad-borrador');
        if (elBorrador) {
          elBorrador.textContent = stats.cantidad_borrador || 0;
        }
      } else {
        console.warn(`[${MOD}] Error al cargar estadísticas:`, response);
      }
    } catch (error) {
      console.error(`[${MOD}] Error al cargar estadísticas:`, error);
      // ⚠️ v2.60: Error silencioso - no interrumpir la inicialización del módulo
    }
  }

  /**
   * Inicializar módulo completo
   */
  async function inicializarModulo() {
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de operación
    
    // ⚠️ v2.61: Verificar si el contenedor está visible antes de inicializar
    const tabElement = d.querySelector(TAB_ID);
    if (!tabElement || tabElement.style.display === 'none') {
      console.log(`[${MOD}] Tab no visible, omitiendo inicialización`);
      return;
    }
    
    // Verificar dependencias críticas
    if (!w.TabulatorFactory) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'TabulatorFactory no está disponible' } }, `[${MOD}]`);
      }
      return;
    }

    if (!w.cotizacionesAPI) {
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'cotizacionesAPI no está disponible' } }, `[${MOD}]`);
      }
      return;
    }

    // ⚠️ v2.61: Limpiar estado previo si existe antes de reinicializar
    if (tableInitialized) {
      console.log(`[${MOD}] Reinicializando módulo, limpiando estado previo...`);
      limpiarEstado();
    }

    // ⚠️ v2.61: Cargar estadísticas desde el backend
    cargarEstadisticas();

    // Inicializar tabla principal de cotizaciones
    table = initTable();
    
    // ⚠️ v2.61: NO inicializar tabla de configuraciones automáticamente
    // Solo se inicializará cuando el usuario expanda el collapse (lazy loading)
    // Esto evita peticiones HTTP innecesarias cuando el collapse está cerrado
    configTable = null;
    
    // Exponer módulo globalmente ANTES de configurar eventos
    /**
     * Ver PDF de cotización
     * ⚠️ Abre el PDF en una nueva ventana usando window.open
     */
    function verPDF(uuid) {
      if (!uuid) {
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 400, data: { detail: 'UUID de cotización no válido' } }, `[${MOD}]`);
        }
        return;
      }
      
      // Abrir PDF en nueva ventana
      const pdfUrl = `${API_URL}${uuid}/exportar-pdf/`;
      window.open(pdfUrl, '_blank');
    }

    w.cotizacionesPage = {
      table: table,
      configTable: configTable, // ⚠️ v2.60: Exponer tabla de configuraciones
      refresh: function() {
        if (table) {
          table.replaceData();
        }
        // ⚠️ v2.61: Actualizar estadísticas al refrescar
        cargarEstadisticas();
      },
      refreshConfiguraciones: function() {
        if (configTable) {
          configTable.replaceData();
        }
      },
      editar: editar,
      verDetalle: verDetalle,
      crear: crear,
      eliminar: handleDelete,
      convertirAFactura: handleConvertirAFactura,
      verPDF: verPDF, // ⚠️ Método para ver PDF
      cargarEstadisticas: cargarEstadisticas // ⚠️ v2.61: Exponer método de estadísticas
    };
    
    // ⚠️ Exponer también como window.CotizacionesPage para compatibilidad
    w.CotizacionesPage = w.cotizacionesPage;
    
    // ⚠️ v2.60: Aislamiento Gradual - Sin logs de éxito
    
    // Configurar eventos DESPUÉS de inicializar el módulo
    configurarEventos();
    
    // ⚠️ v2.61: Inicializar tabla de configuraciones SOLO cuando el collapse se expanda (lazy loading)
    // Esto evita peticiones HTTP innecesarias cuando el collapse está cerrado
    const collapseElement = d.querySelector('#collapse-configuraciones');
    if (collapseElement) {
      collapseElement.addEventListener('shown.bs.collapse', function() {
        console.log(`[${MOD}] Collapse de configuraciones expandido, inicializando tabla...`);
        if (!configTable) {
          try {
            configTable = initConfiguracionesTable();
            if (configTable && w.cotizacionesPage) {
              w.cotizacionesPage.configTable = configTable;
              console.log(`[${MOD}] Tabla de configuraciones inicializada correctamente`);
            }
          } catch (err) {
            console.error(`[${MOD}] Error al inicializar tabla de configuraciones:`, err);
            configTable = null;
          }
        } else {
          // Si ya existe, refrescar datos
          console.log(`[${MOD}] Tabla de configuraciones ya existe, refrescando datos...`);
          configTable.replaceData();
        }
      });
    }
  }

  // Lazy Loading: Inicializar solo cuando el tab sea visible
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(TAB_ID, function() {
      inicializarModulo().catch(err => {
        // ⚠️ v2.60: Error de inicialización, delegar a UIManager
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 500, data: { detail: 'Error al inicializar módulo de cotizaciones' } }, `[${MOD}]`);
        }
      });
    });
  } else {
    // Fallback si DOMUtils no está disponible
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      
      inicializarModulo().catch(err => {
        // ⚠️ v2.60: Error de inicialización, delegar a UIManager
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 500, data: { detail: 'Error al inicializar módulo de cotizaciones' } }, `[${MOD}]`);
        }
      });
    }
    initFallback();
  }
  
  // ⚠️ v2.61: Limpiar estado cuando se oculta el tab
  d.addEventListener('hidden.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-tab') === 'cotizaciones' || e.target.getAttribute('data-bs-target') === TAB_ID)) {
      console.log(`[${MOD}] Tab ocultado, limpiando estado...`);
      // No limpiar completamente, solo marcar como no inicializado para permitir reinicialización
      // tableInitialized = false;
    }
  });

  // ⚠️ v2.61: También configurar eventos cuando el tab de cotizaciones se muestre (Bootstrap event)
  // Asegurar que HTMX procese los atributos cuando el tab se muestra
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-tab') === 'cotizaciones' || e.target.getAttribute('data-bs-target') === TAB_ID)) {
      // ⚠️ v2.61: Verificar si el tab está visible antes de inicializar
      const tabElement = d.querySelector(TAB_ID);
      if (!tabElement || tabElement.style.display === 'none') {
        console.log(`[${MOD}] Tab no visible, omitiendo inicialización`);
        return;
      }
      
      // Asegurar que el módulo esté inicializado
      if (!w.cotizacionesPage || !tableInitialized) {
        inicializarModulo().catch(err => {
          // ⚠️ v2.60: Error de inicialización, delegar a UIManager
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError({ status: 500, data: { detail: 'Error al inicializar módulo de cotizaciones' } }, `[${MOD}]`);
          }
        });
      } else {
        setTimeout(configurarEventos, 100);
      }
      
      // ⚠️ v2.61: Procesar atributos HTMX cuando se muestra el tab (crítico para botones)
      setTimeout(function() {
        if (typeof htmx !== 'undefined' && typeof htmx.process === 'function') {
          const tabElement = d.querySelector(TAB_ID);
          if (tabElement) {
            htmx.process(tabElement);
            console.log(`[${MOD}] HTMX procesado para tab de cotizaciones`);
          }
          
          // ⚠️ v2.61: Procesar específicamente el botón de crear
          const btnCrear = d.getElementById('btn-cotizaciones-crear');
          if (btnCrear) {
            htmx.process(btnCrear);
            console.log(`[${MOD}] Botón "Nueva Cotización" procesado por HTMX`);
          } else {
            console.warn(`[${MOD}] Botón "Nueva Cotización" no encontrado`);
          }
        } else {
          console.warn(`[${MOD}] HTMX no está disponible`);
        }
      }, 200);
    }
  });
  
  // ⚠️ v2.61: Listener directo para el botón como fallback (si HTMX no procesa correctamente)
  // Usar event delegation para capturar clics incluso si el botón se carga dinámicamente
  function setupButtonListener() {
    const btnCrear = d.getElementById('btn-cotizaciones-crear');
    if (btnCrear) {
      // Remover listener anterior si existe
      btnCrear.removeEventListener('click', handleButtonClick);
      // Agregar listener de clic directo como fallback
      btnCrear.addEventListener('click', handleButtonClick);
      console.log(`[${MOD}] Listener de clic configurado para botón "Nueva Cotización"`);
    }
  }
  
  function handleButtonClick(e) {
    const btnCrear = e.currentTarget || d.getElementById('btn-cotizaciones-crear');
    if (!btnCrear) return;
    
    console.log(`[${MOD}] Clic detectado en botón "Nueva Cotización"`);
    
    // Verificar si HTMX está disponible y procesando
    if (typeof htmx !== 'undefined') {
      const url = btnCrear.getAttribute('hx-get');
      const target = btnCrear.getAttribute('hx-target');
      
      if (url && target) {
        console.log(`[${MOD}] Ejecutando HTMX request: ${url} -> ${target}`);
        htmx.ajax('GET', url, {
          target: target,
          swap: 'innerHTML',
          indicator: '#spinner'
        }).then(() => {
          console.log(`[${MOD}] HTMX request completado`);
        }).catch((error) => {
          console.error(`[${MOD}] Error en HTMX request:`, error);
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError({ status: 500, data: { detail: 'Error al cargar el formulario de cotización' } }, `[${MOD}]`);
          }
        });
      } else {
        console.error(`[${MOD}] Botón no tiene atributos hx-get o hx-target`);
      }
    } else {
      console.error(`[${MOD}] HTMX no está disponible`);
    }
  }
  
  // Configurar listener cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', setupButtonListener);
  } else {
    setupButtonListener();
  }
  
  // También configurar cuando se muestra el tab
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-tab') === 'cotizaciones' || e.target.getAttribute('data-bs-target') === TAB_ID)) {
      setTimeout(setupButtonListener, 100);
    }
  });

})(window, document);
