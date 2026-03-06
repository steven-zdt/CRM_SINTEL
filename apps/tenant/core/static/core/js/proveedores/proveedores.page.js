/**
 * proveedores.page.js - Módulo Proveedores v2.60 - Tabulator Implementation
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Lazy Loading: Usa DOMUtils.onVisibleOnce() para inicialización diferida
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.http() (definido en http.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - htmx (para cargar offcanvas)
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores.page]';
  const GRID_ID = '#grid-proveedores';
  const SEARCH_ID = '#search-proveedor';
  const API_URL = '/api/v1/proveedores/';
  const TAB_ID = '#tab-proveedores';
  let table = null;

  /**
   * Abrir offcanvas de proveedor vía HTMX
   * ⚠️ Paso 4: Acciones - La columna de acciones debe llamar a openProveedorOffcanvas(id) mediante HTMX
   */
  async function openProveedorOffcanvas(id) {
    const url = id 
      ? `${API_URL}gestor-offcanvas/?id=${id}`
      : `${API_URL}gestor-offcanvas/`;
    
    // ⚠️ Paso 4: Usar htmx.ajax para cargar el offcanvas
    await htmx.ajax('GET', url, {
      target: '#offcanvas-container-proveedor',
      swap: 'innerHTML'
    });

    const offcanvasEl = d.getElementById('offcanvas-proveedor');
    if (offcanvasEl) {
      const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
      offcanvas.show();
      
      // Configurar eventos del formulario después de que el offcanvas esté visible
      setTimeout(function() {
        configurarEventosFormulario();
      }, 100);
    }
  }

  /**
   * Configurar eventos del formulario de proveedor
   */
  function configurarEventosFormulario() {
    const form = d.querySelector('#form-proveedor');
    if (!form) return;

    // Remover listeners anteriores si existen (evitar duplicados)
    const nuevoForm = form.cloneNode(true);
    form.parentNode.replaceChild(nuevoForm, form);

    // Listener para el botón de guardar
    const btnGuardar = d.querySelector('#btn-guardar-proveedor');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        await guardarProveedor();
      });
    }

    // Listener para el submit del formulario (HTMX)
    nuevoForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      e.stopPropagation();
      await guardarProveedor();
    });
  }

  /**
   * Guardar proveedor (crear o actualizar)
   * ⚠️ Paso 4: Aislamiento de Error - Usa window.UIManager.handleError para procesar la respuesta de la API
   */
  async function guardarProveedor() {
    const form = d.querySelector('#form-proveedor');
    if (!form) {
      console.error(`${MOD} Formulario #form-proveedor no encontrado`);
      return;
    }

    const formData = new FormData(form);
    const payload = {
      tipo_persona: formData.get('tipo_persona')?.trim() || '',
      tipo_documento: formData.get('tipo_documento')?.trim() || '',
      numero_documento: formData.get('numero_documento')?.trim() || '',
      digito_verificacion: formData.get('digito_verificacion')?.trim() || '',
      razon_social: formData.get('razon_social')?.trim() || '',
      nombre_comercial: formData.get('nombre_comercial')?.trim() || '',
      regimen_tributario: formData.get('regimen_tributario')?.trim() || '',
      actividad_economica_ciiu: formData.get('actividad_economica_ciiu')?.trim() || '',
      responsable_iva: formData.get('responsable_iva') === 'on' || formData.get('responsable_iva') === 'true',
      gran_contribuyente: formData.get('gran_contribuyente') === 'on' || formData.get('gran_contribuyente') === 'true',
      autoretenedor: formData.get('autoretenedor') === 'on' || formData.get('autoretenedor') === 'true',
      email_contacto: formData.get('email_contacto')?.trim() || '',
      telefono_contacto: formData.get('telefono_contacto')?.trim() || '',
      direccion: formData.get('direccion')?.trim() || '',
      ciudad: formData.get('ciudad')?.trim() || '',
      plazo_pago_dias: parseInt(formData.get('plazo_pago_dias') || '30', 10) || 30,
      banco: formData.get('banco')?.trim() || '',
      tipo_cuenta: formData.get('tipo_cuenta')?.trim() || '',
      numero_cuenta: formData.get('numero_cuenta')?.trim() || '',
      activo: formData.get('activo') === 'on' || formData.get('activo') === 'true',
      observaciones: formData.get('observaciones')?.trim() || ''
    };

    // Validación básica
    if (!payload.tipo_persona || !payload.tipo_documento || !payload.numero_documento || !payload.razon_social) {
      const errorContainer = d.querySelector('#form-feedback');
      if (errorContainer) {
        errorContainer.className = 'alert alert-danger';
        errorContainer.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-2"></i>Los campos Tipo Persona, Tipo Documento, Número Documento y Razón Social son requeridos.';
        errorContainer.classList.remove('d-none');
      }
      return;
    }

    const proveedorId = formData.get('id');
    let res;

    // ⚠️ Paso 4: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    if (proveedorId) {
      // Actualizar
      res = await w.http('PATCH', `${API_URL}${proveedorId}/`, payload);
    } else {
      // Crear
      res = await w.http('POST', API_URL, payload);
    }

    // ⚠️ Paso 4: Aislamiento de Error - Usa UIManager.handleError para procesar la respuesta
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD, {
          modalSelector: '#offcanvas-proveedor',
          errorContainerSelector: '#form-feedback'
        });
      }
      return;
    }

    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success(proveedorId ? 'Proveedor actualizado correctamente' : 'Proveedor creado correctamente');
    }

    // Cerrar offcanvas
    const offcanvasEl = d.getElementById('offcanvas-proveedor');
    if (offcanvasEl) {
      const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
      if (offcanvas) {
        offcanvas.hide();
      }
    }

    // Refrescar tabla
    if (table) {
      table.replaceData();
    }
  }

  /**
   * Eliminar proveedor
   * ⚠️ Paso 4: Aislamiento de Error - Usa UIManager.handleError para procesar la respuesta
   */
  async function eliminarProveedor(id) {
    // Validar que el proveedor no esté activo
    const resGet = await w.http('GET', `${API_URL}${id}/`);
    
    if (!resGet.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(resGet, MOD);
      }
      return;
    }

    const data = resGet.data;
    
    // Validar que el proveedor no esté activo
    if (data.activo) {
      if (w.SintelFeedback) {
        w.SintelFeedback.error('El proveedor está activo. Desactívelo primero.');
      }
      return;
    }
    
    // Confirmar eliminación
    if (!confirm('¿Está seguro de eliminar este proveedor? Esta acción no se puede deshacer.')) {
      return;
    }

    // ⚠️ Paso 4: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.http('DELETE', `${API_URL}${id}/`);

    // ⚠️ Paso 4: Aislamiento de Error - Usa UIManager.handleError para procesar la respuesta
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD);
      }
      return;
    }

    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Proveedor eliminado correctamente');
    }
    
    if (table) {
      table.replaceData();
    }
  }

  /**
   * Definir columnas específicas del módulo
   */
  function getColumns() {
    return [
      {
        title: "ID",
        field: "id",
        width: 60,
        headerSort: false
      },
      {
        title: "NIT/Documento",
        field: "nit",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '---';
        },
        width: 150,
        headerFilter: "input"
      },
      {
        title: "Razón Social",
        field: "razon_social",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '---';
        },
        minWidth: 250,
        headerFilter: "input"
      },
      {
        title: "Nombre Comercial",
        field: "nombre_comercial",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '<span class="text-muted">---</span>';
        },
        width: 200,
        headerFilter: "input"
      },
      {
        title: "Contacto",
        field: "contacto_principal",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '<span class="text-muted">---</span>';
        },
        width: 180
      },
      {
        title: "Ciudad",
        field: "ciudad",
        formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
          return cell.getValue() || '<span class="text-muted">---</span>';
        },
        width: 120
      },
      {
        title: "Estado",
        field: "estado",
        formatter: function(cell) {
          const estado = cell.getValue();
          if (estado === 'Activo') {
            return '<span class="badge bg-success">Activo</span>';
          }
          return '<span class="badge bg-secondary">Inactivo</span>';
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
          
          // Deshabilitar botón eliminar si está activo
          const deleteDisabled = isActive ? 'disabled' : '';
          const deleteClass = isActive ? 'opacity-50' : '';
          
          return `
            <div class="btn-group btn-group-sm" role="group">
              <button type="button" class="btn btn-outline-primary btn-edit-proveedor" data-id="${id}" title="Editar Proveedor">
                <i class="bi bi-pencil"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-delete-proveedor ${deleteClass}" data-id="${id}" ${deleteDisabled} title="${isActive ? 'Desactive primero para eliminar' : 'Eliminar Proveedor'}">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          `;
        },
        width: 150,
        headerSort: false,
        resizable: false
      }
    ];
  }

  /**
   * Inicializar tabla de proveedores
   * ⚠️ Paso 4: Tabulator Factory - Inicializa la tabla usando window.TabulatorFactory.create()
   */
  function initTable() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) {
      console.warn(`${MOD} Contenedor ${GRID_ID} no encontrado`);
      return;
    }

    // ⚠️ Anti-Zombies: Destruir instancia previa si existe
    if (w.SintelProveedoresTables && w.SintelProveedoresTables.proveedores) {
      try {
        w.SintelProveedoresTables.proveedores.destroy();
      } catch (error) {
        console.warn(`${MOD} Error al destruir tabla previa:`, error);
      }
    }

    // ⚠️ Verificar que TabulatorFactory esté disponible
    if (!w.TabulatorFactory || typeof w.TabulatorFactory.create !== 'function') {
      console.error(`${MOD} TabulatorFactory no está disponible`);
      return;
    }

    // ⚠️ Paso 4: Tabulator Factory - Inicializa la tabla usando window.TabulatorFactory.create()
    table = w.TabulatorFactory.create(
      GRID_ID,
      API_URL,
      getColumns(),
      {
        searchInputSelector: SEARCH_ID
      }
    );

    // Guardar instancia en singleton global
    if (!w.SintelProveedoresTables) {
      w.SintelProveedoresTables = {};
    }
    w.SintelProveedoresTables.proveedores = table;

    // ⚠️ Event Delegation: Manejar clics en botones de acción
    initListEvents();
  }

  /**
   * Inicializar eventos de la lista (Event Delegation)
   */
  function initListEvents() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return;

    // Event Delegation para botones de acción
    gridEl.addEventListener('click', async function(e) {
      const btn = e.target.closest('button');
      if (!btn) return;

      // Botón Editar
      if (btn.classList.contains('btn-edit-proveedor')) {
        e.preventDefault();
        const id = btn.getAttribute('data-id');
        if (!id) return;

        // ⚠️ Paso 4: Acciones - La columna de acciones debe llamar a openProveedorOffcanvas(id) mediante HTMX
        await openProveedorOffcanvas(id);
        return;
      }

      // Botón Eliminar
      if (btn.classList.contains('btn-delete-proveedor')) {
        e.preventDefault();
        const id = btn.getAttribute('data-id');
        if (!id) return;

        // Validar que no esté deshabilitado
        if (btn.disabled) {
          if (w.SintelFeedback) {
            w.SintelFeedback.error('No se puede eliminar un proveedor activo. Desactívelo primero.');
          }
          return;
        }

        await eliminarProveedor(id);
      }
    });

    // Event Delegation: Clic en fila para editar
    if (table) {
      table.on('rowClick', async function(e, row) {
        const data = row.getData();
        if (!data || !data.id) return;

        // ⚠️ Paso 4: Acciones - La columna de acciones debe llamar a openProveedorOffcanvas(id) mediante HTMX
        await openProveedorOffcanvas(data.id);
      });
    }
  }

  /**
   * Inicializar el módulo completo
   * ⚠️ v2.60: Prevención de doble inicialización - Verifica que la tabla no exista antes de inicializar
   */
  function initProveedores() {
    // ⚠️ GUARDA: Prevenir doble inicialización
    if (table && w.SintelProveedoresTables && w.SintelProveedoresTables.proveedores) {
      console.log(`${MOD} Tabla ya inicializada, omitiendo inicialización duplicada`);
      return;
    }
    
    console.log(`${MOD} Inicializando módulo de proveedores...`);
    
    // Inicializar tabla
    initTable();
    
    // Configurar botón "Nuevo Proveedor"
    const btnNuevo = d.querySelector('#btn-nuevo-proveedor');
    if (btnNuevo) {
      btnNuevo.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        await openProveedorOffcanvas(null);
      });
    }

    // También configurar el botón legacy si existe
    const btnNuevoLegacy = d.querySelector('button[onclick*="abrirModalCrear"]');
    if (btnNuevoLegacy) {
      btnNuevoLegacy.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        await openProveedorOffcanvas(null);
      });
    }
  }

  /**
   * ⚠️ Paso 4: Lazy Loading - Encapsula la lógica en DOMUtils.onVisibleOnce('#tab-proveedores', initProveedores)
   * ⚠️ v2.60: Prevención de doble inicialización - Solo inicializar una vez mediante onVisibleOnce
   */
  if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
    const selectors = [
      GRID_ID,
      '#tab-proveedores',
      '#tab-proveedores ' + GRID_ID,
      '#workspace #tab-proveedores',
      '#workspace #tab-proveedores ' + GRID_ID
    ];
    
    let targetSelector = null;
    for (const selector of selectors) {
      const el = d.querySelector(selector);
      if (el) {
        targetSelector = selector;
        break;
      }
    }
    
    if (targetSelector) {
      // ⚠️ v2.60: ÚNICA inicialización mediante onVisibleOnce - Eliminados fallbacks y listeners adicionales
      w.DOMUtils.onVisibleOnce(targetSelector, function(el) {
        console.log(`${MOD} Contenedor visible, inicializando tabla...`);
        initProveedores();
      }, { once: true, timeout: 30000 });
    } else {
      console.warn(`${MOD} Selectores de contenedor no encontrados, usando fallback DOMContentLoaded`);
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initProveedores);
      } else {
        initProveedores();
      }
    }
  } else {
    console.warn(`${MOD} DOMUtils.onVisibleOnce no está disponible, usando fallback DOMContentLoaded`);
    if (d.readyState === 'loading') {
      d.addEventListener('DOMContentLoaded', initProveedores);
    } else {
      initProveedores();
    }
  }

  // ⚠️ v2.60: Listeners adicionales eliminados para prevenir doble inicialización
  // La inicialización se maneja exclusivamente mediante DOMUtils.onVisibleOnce

  // Exponer API pública
  w.ProveedoresModule = {
    init: initProveedores,
    openProveedorOffcanvas: openProveedorOffcanvas,
    eliminar: eliminarProveedor,
    refresh: function() {
      if (table) {
        table.replaceData();
      }
    }
  };

})(window, document);
