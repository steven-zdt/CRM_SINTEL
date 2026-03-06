/**
 * gastos.page.js - Módulo Gastos v2.60 - Tabulator Implementation
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.40: Sistema de Documento Soporte Inmutable según normativa DIAN
 * - Panel de analítica con Retefuente y ReteICA
 * - Validación de resolución activa antes de crear (abre modal de configuración si no existe)
 * - Gestión de formulario de configuración de resolución DIAN
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.gastosAPI (definido en gastos.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.gastosModals (definido en gastos.modals.js)
 */
(function (w, d) {
  'use strict';

  const TABLE_SELECTOR = '#grid-gastos';
  const SEARCH_SELECTOR = '#search-gasto';
  const API_URL = '/api/v1/gastos/';
  const TAB_ID = '#tab-gastos';
  let table = null;
  let state = {
    summary: null
  };

  // Helper: Obtener CSRF token
  function getCookie(name) {
    const value = `; ${d.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  // Formatear dinero
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
      console.warn('[gastos.page] Error cargando resumen:', res.status);
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

  // Definir columnas específicas del módulo
  function getColumns() {
    return [
      {
        title: "Documento",
        field: "ds_numero_documento",  // ⚠️ v2.40: Usa campo completo del serializer (prefijo + consecutivo)
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
        field: "ds_fecha",
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
        title: "Vendedor / Proveedor",
        field: "ds_vendedor",
        formatter: w.TabulatorFactory.formatters.valueOrFallback
      },
      {
        title: "Categoría",
        field: "categoria_contable_display",
        formatter: function(cell) {
          const data = cell.getRow().getData();
          return data.categoria_contable_display || data.categoria_contable || '---';
        }
      },
      {
        title: "Centro de Costo",
        field: "centro_costo_display",
        formatter: function(cell) {
          const data = cell.getRow().getData();
          return data.centro_costo_display || data.centro_costo || '---';
        }
      },
      {
        title: "Total Neto",
        field: "ds_total",
        formatter: function(cell) {
          const val = parseFloat(cell.getValue()) || 0;
          return fmtMoney(val);
        },
        hozAlign: "right"
      },
      {
        title: "Estado",
        field: "ds_activo",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const activo = rowData.ds_activo === true;
          const anulado = rowData.ds_anulado === true;
          
          if (anulado) {
            return '<span class="badge bg-danger">ANULADO</span>';
          } else if (activo) {
            return '<span class="badge bg-success">ACTIVO</span>';
          } else {
            return '<span class="badge bg-warning">INACTIVO</span>';
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
            <button type="button" class="btn btn-sm btn-link text-primary p-0 me-2" data-action="ver" data-id="${id}" title="Ver Detalle">
              <i class="fas fa-eye"></i>
            </button>
          `;
          
          // ⚠️ v2.40: Lógica de desactivar/anular
          if (!anulado) {
            if (activo) {
              // Si está activo: mostrar botón Desactivar
              buttons += `
                <button type="button" class="btn btn-sm btn-link text-warning p-0 me-2" data-action="desactivar" data-id="${id}" title="Desactivar Documento">
                  <i class="fas fa-toggle-off"></i>
                </button>
              `;
              // Botón Anular deshabilitado si está activo
              buttons += `
                <button type="button" class="btn btn-sm btn-link text-muted p-0 opacity-50" disabled title="Debe desactivar primero para anular">
                  <i class="fas fa-ban"></i>
                </button>
              `;
            } else {
              // Si está inactivo: mostrar botón Anular
              buttons += `
                <button type="button" class="btn btn-sm btn-link text-danger p-0" data-action="anular" data-id="${id}" title="Anular Documento">
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
      console.error('[gastos.page] TabulatorFactory no está disponible');
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
            console.warn('[gastos.page] ID no válido:', id);
            return;
          }
          
          // Ejecutar acción según el botón
          switch (action) {
            case 'ver':
              if (w.gastosPage && typeof w.gastosPage.showDetail === 'function') {
                w.gastosPage.showDetail(id);
              }
              break;
            case 'desactivar':
              if (w.gastosPage && typeof w.gastosPage.confirmarDesactivar === 'function') {
                w.gastosPage.confirmarDesactivar(id);
              }
              break;
            case 'anular':
              if (w.gastosPage && typeof w.gastosPage.confirmarAnulacion === 'function') {
                w.gastosPage.confirmarAnulacion(id);
              }
              break;
            default:
              console.warn('[gastos.page] Acción no reconocida:', action);
          }
        });
      }
    }

    return table;
  }

  // Función para configurar eventos (reutilizable)
  function configurarEventos() {
    console.log('[gastos.page] Configurando eventos...');
    
    // Asegurar que el módulo esté inicializado
    if (!w.gastosPage) {
      console.warn('[gastos.page] gastosPage no está inicializado aún, inicializando...');
      w.gastosPage = {
        table: table,
        refresh: async function() {
          await renderSummary();
          if (table) {
            table.replaceData();
          }
        },
        showDetail: function(id) {
          if (w.gastosModals && typeof w.gastosModals.showDetail === 'function') {
            w.gastosModals.showDetail(id);
          }
        },
        confirmarAnulacion: confirmarAnulacion
      };
    }
    
    // Botón refrescar
    const btnRefrescar = d.getElementById('btn-refrescar-gastos');
    if (btnRefrescar) {
      const nuevoBtn = btnRefrescar.cloneNode(true);
      btnRefrescar.parentNode.replaceChild(nuevoBtn, btnRefrescar);
      
      nuevoBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('[gastos.page] Refrescando tabla y resumen...');
        await renderSummary();
        if (table) {
          table.replaceData();
        }
      });
    }

    // Botón crear gasto
    const btnCrear = d.getElementById('btn-gastos-crear');
    if (btnCrear) {
      // Clonar botón para eliminar event listeners existentes y atributos onclick
      const nuevoBtn = btnCrear.cloneNode(true);
      // Eliminar atributo onclick si existe (evita doble ejecución)
      nuevoBtn.removeAttribute('onclick');
      btnCrear.parentNode.replaceChild(nuevoBtn, btnCrear);
      
      nuevoBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('[gastos.page] Click en botón "Nuevo Gasto"');
        
        // Validar resolución activa antes de abrir modal
        const res = await w.gastosAPI.getResolucionActiva();
        if (!res.ok || res.status === 404) {
          // No hay resolución activa, abrir modal de configuración
          console.log('[gastos.page] No hay resolución activa, abriendo modal de configuración');
          const modalConfigEl = d.getElementById('modal-resolucion-config');
          if (modalConfigEl) {
            // ⚠️ CRÍTICO: Usar getOrCreateInstance para evitar conflictos de aria-hidden (patrón de clientes)
            if (w.bootstrap && w.bootstrap.Modal) {
              const modal = w.bootstrap.Modal.getOrCreateInstance(modalConfigEl);
              modalConfigEl.addEventListener('shown.bs.modal', function focusFirstInput() {
                const firstInput = modalConfigEl.querySelector('input:not([type="hidden"]), select, textarea');
                if (firstInput) {
                  firstInput.focus();
                }
                modalConfigEl.removeEventListener('shown.bs.modal', focusFirstInput);
              }, { once: true });
              modal.show();
            } else if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
              // Fallback: usar UIManager si Bootstrap no está disponible
              w.UIManager.handleModal('#modal-resolucion-config', 'show');
            }
          }
          return;
        }
        // Hay resolución activa, abrir modal de creación
        console.log('[gastos.page] Resolución activa encontrada, abriendo modal de creación');
        if (w.gastosModals && typeof w.gastosModals.showCreate === 'function') {
          w.gastosModals.showCreate();
        } else {
          console.warn('[gastos.page] gastosModals.showCreate no está disponible');
        }
      });
    }
    
    // Botón configurar resolución
    const btnConfig = d.getElementById('btn-config-resolucion');
    if (btnConfig) {
      // Clonar botón para eliminar event listeners existentes y atributos onclick
      const nuevoBtn = btnConfig.cloneNode(true);
      // Eliminar atributo onclick si existe (evita doble ejecución)
      nuevoBtn.removeAttribute('onclick');
      btnConfig.parentNode.replaceChild(nuevoBtn, btnConfig);
      
      nuevoBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('[gastos.page] Click en botón "Configurar Resolución"');
        
        const modalConfigEl = d.getElementById('modal-resolucion-config');
        if (!modalConfigEl) {
          console.error('[gastos.page] Modal de configuración no encontrado');
          return;
        }
        
        const modalConfig = bootstrap.Modal.getOrCreateInstance(modalConfigEl);
        
        // Establecer valores por defecto en el formulario de configuración
        const form = d.getElementById('form-resolucion-config');
        if (form) {
          const fechaResolucion = form.querySelector('input[name="fecha_resolucion"]');
          if (fechaResolucion && !fechaResolucion.value) {
            fechaResolucion.value = new Date().toISOString().split('T')[0];
          }
          
          const fechaFin = form.querySelector('input[name="fecha_fin"]');
          if (fechaFin && !fechaFin.value) {
            const hoy = new Date();
            hoy.setFullYear(hoy.getFullYear() + 1);
            fechaFin.value = hoy.toISOString().split('T')[0];
          }
          
          const feedbackEl = d.getElementById('feedback-config-resolucion');
          if (feedbackEl) {
            feedbackEl.textContent = '';
            feedbackEl.className = '';
            feedbackEl.style.display = 'none';
          }
        }
        
        modalConfig.show();
      });
    }
    
    // Formulario de configuración de resolución
    const formResolucion = d.getElementById('form-resolucion-config');
    if (formResolucion) {
      const nuevoForm = formResolucion.cloneNode(true);
      formResolucion.parentNode.replaceChild(nuevoForm, formResolucion);
      
      nuevoForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!nuevoForm.checkValidity()) {
          nuevoForm.reportValidity();
          return;
        }
        
        const formData = new FormData(nuevoForm);
        const payload = {
          numero_resolucion: formData.get('numero_resolucion'),
          prefijo: formData.get('prefijo'),
          rango_desde: parseInt(formData.get('rango_desde')),
          rango_hasta: parseInt(formData.get('rango_hasta')),
          fecha_resolucion: formData.get('fecha_resolucion'),
          fecha_fin: formData.get('fecha_fin'),
          clave_tecnica: formData.get('clave_tecnica') || '',
          vigente: formData.get('vigente') === 'on'
        };
        
        const res = await w.gastosAPI.setConfigResolucion(payload);
        
        if (res.ok && res.data) {
          const resolucion = res.data;
          const feedbackEl = d.getElementById('feedback-config-resolucion');
          
          if (feedbackEl) {
            const fechaResolucion = resolucion.fecha_resolucion ? new Date(resolucion.fecha_resolucion).toLocaleDateString('es-CO') : 'N/A';
            const fechaInicio = resolucion.fecha_inicio ? new Date(resolucion.fecha_inicio).toLocaleDateString('es-CO') : 'N/A';
            const fechaFin = resolucion.fecha_fin ? new Date(resolucion.fecha_fin).toLocaleDateString('es-CO') : 'N/A';
            const vigenteBadge = resolucion.vigente 
              ? '<span class="badge bg-success ms-2">VIGENTE</span>' 
              : '<span class="badge bg-secondary ms-2">INACTIVA</span>';
            
            feedbackEl.className = 'alert alert-success';
            feedbackEl.innerHTML = `
              <div class="d-flex align-items-start">
                <i class="bi bi-check-circle-fill me-2 fs-5"></i>
                <div class="flex-grow-1">
                  <strong>Resolución DIAN guardada correctamente</strong>${vigenteBadge}
                  <hr class="my-2">
                  <div class="small">
                    <div class="row g-2">
                      <div class="col-md-6"><strong>Número:</strong> ${resolucion.numero_resolucion || 'N/A'}</div>
                      <div class="col-md-6"><strong>Prefijo:</strong> ${resolucion.prefijo || 'N/A'}</div>
                      <div class="col-md-6"><strong>Rango:</strong> ${resolucion.rango_desde || 'N/A'} - ${resolucion.rango_hasta || 'N/A'}</div>
                      <div class="col-md-6"><strong>Fecha Emisión:</strong> ${fechaResolucion}</div>
                      <div class="col-md-6"><strong>Fecha Inicio:</strong> ${fechaInicio}</div>
                      <div class="col-md-6"><strong>Fecha Fin:</strong> ${fechaFin}</div>
                    </div>
                  </div>
                </div>
              </div>
            `;
            feedbackEl.style.display = 'block';
            feedbackEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
          
          if (w.DOMUtils && typeof w.DOMUtils.showToast === 'function') {
            w.DOMUtils.showToast('Resolución DIAN configurada correctamente', 'success');
          } else if (w.SintelFeedback) {
            w.SintelFeedback.success('Resolución DIAN configurada correctamente');
          }
          
          setTimeout(() => {
            const modalConfig = bootstrap.Modal.getInstance(d.getElementById('modal-resolucion-config'));
            if (modalConfig) {
              modalConfig.hide();
              nuevoForm.reset();
              if (feedbackEl) {
                feedbackEl.innerHTML = '';
                feedbackEl.className = '';
                feedbackEl.style.display = 'none';
              }
            }
          }, 3000);
        } else {
          // ⚠️ v2.60: Error Boundary - Mostrar error en modal y mantener abierto
          const errorContainer = d.getElementById('feedback-config-resolucion');
          if (errorContainer) {
            let errorMessage = 'Error al guardar resolución';
            if (res.data) {
              if (res.data.detail) {
                errorMessage = res.data.detail;
              } else if (res.data.message) {
                errorMessage = res.data.message;
              } else if (typeof res.data === 'string') {
                errorMessage = res.data;
              } else if (Array.isArray(res.data)) {
                errorMessage = res.data.join(', ');
              } else if (typeof res.data === 'object') {
                const errorFields = Object.keys(res.data);
                const errorMessages = errorFields.map(field => {
                  const fieldErrors = Array.isArray(res.data[field]) 
                    ? res.data[field].join(', ')
                    : String(res.data[field]);
                  return `${field}: ${fieldErrors}`;
                });
                errorMessage = errorMessages.join(' | ');
              }
            }
            
            errorContainer.className = 'alert alert-danger';
            errorContainer.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Error:</strong> ${errorMessage}`;
            errorContainer.style.display = 'block';
            errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
          
          // ⚠️ Error Boundary: Usar notifyError para mostrar notificación adicional
          if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
            w.UIManager.notifyError(res, 'Gastos: Configurar Resolución');
          }
        }
      });
    }
    
    // Botón guardar gasto
    const btnGuardar = d.getElementById('btn-guardar-gasto');
    if (btnGuardar) {
      const nuevoBtn = btnGuardar.cloneNode(true);
      btnGuardar.parentNode.replaceChild(nuevoBtn, btnGuardar);
      
      nuevoBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (w.gastosModals && typeof w.gastosModals.save === 'function') {
          w.gastosModals.save();
        }
      });
    }
  }

  /**
   * Función para confirmar desactivación
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function confirmarDesactivar(id) {
    if (!confirm('¿Está seguro de desactivar este Documento Soporte? Debe estar desactivado para poder anularlo.')) {
      return;
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.gastosAPI.desactivar(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[gastos.page]');
      }
      return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Documento desactivado correctamente. Ahora puede anularlo si lo desea.');
    }
    
    if (table) {
      table.replaceData();
    }
  }

  /**
   * Función para confirmar anulación
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function confirmarAnulacion(id) {
    if (!confirm('¿Está seguro de anular este Documento Soporte? Esta acción es irreversible y afectará los totales financieros.')) {
      return;
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.gastosAPI.anular(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[gastos.page]');
      }
      return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Documento anulado correctamente');
    }
    
    await renderSummary();
    if (table) {
      table.replaceData();
    }
  }

  // Función para inicializar el módulo completo
  async function inicializarModulo() {
    console.log('[gastos.page] Inicializando módulo completo...');
    
    // Renderizar resumen primero
    await renderSummary();
    
    // Inicializar tabla
    table = initTable();
    
    // Exponer módulo globalmente ANTES de configurar eventos
    w.gastosPage = {
      table: table,
      refresh: async function() {
        await renderSummary();
        if (table) {
          table.replaceData();
        }
      },
      showDetail: function(id) {
        if (w.gastosModals && typeof w.gastosModals.showDetail === 'function') {
          w.gastosModals.showDetail(id);
        }
      },
      confirmarDesactivar: confirmarDesactivar,  // ⚠️ v2.40: Función para desactivar
      confirmarAnulacion: confirmarAnulacion
    };
    
    console.log('[gastos.page] Módulo expuesto globalmente:', w.gastosPage);
    
    // Configurar eventos DESPUÉS de inicializar el módulo
    configurarEventos();
  }

  // Lazy Loading: Inicializar solo cuando el tab sea visible
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(TAB_ID, function() {
      console.log('[gastos.page] Tab de gastos visible, inicializando...');
      inicializarModulo().catch(err => {
        console.error('[gastos.page] Error en inicialización:', err);
      });
    });
  } else {
    // Fallback si DOMUtils no está disponible
    console.warn('[gastos.page] DOMUtils no disponible, inicializando inmediatamente');
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      
      inicializarModulo().catch(err => {
        console.error('[gastos.page] Error en inicialización (fallback):', err);
      });
    }
    initFallback();
  }
  
  // También configurar eventos cuando el tab de gastos se muestre (Bootstrap event)
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-tab') === 'gastos' || e.target.getAttribute('data-bs-target') === TAB_ID)) {
      console.log('[gastos.page] Tab de gastos mostrado, verificando eventos...');
      // Asegurar que el módulo esté inicializado
      if (!w.gastosPage) {
        console.log('[gastos.page] Módulo no inicializado, inicializando desde evento shown.bs.tab...');
        inicializarModulo().catch(err => {
          console.error('[gastos.page] Error en inicialización desde evento:', err);
        });
      } else {
        setTimeout(configurarEventos, 100);
      }
    }
  });

})(window, document);
