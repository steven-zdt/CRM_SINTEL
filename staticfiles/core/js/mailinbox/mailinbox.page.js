/**
 * mailinbox.page.js - Módulo MailInboxConfig v2.60 - Tabulator Implementation
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.mailinboxAPI (definido en mailinbox.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.mailinboxModals (definido en mailinbox.modals.js) - opcional
 */
(function (w, d) {
  'use strict';

  const TABLE_SELECTOR = '#grid-mailinbox';
  const SEARCH_SELECTOR = '#search-mailinbox';
  const API_URL = '/api/v1/empresas/mail-inbox-config/';
  const TAB_ID = '#tab-empresa'; // Comparte tab con Empresa
  let table = null;

  // Helper: Renderizar badge de proveedor
  function renderProvider(provider) {
    if (!provider) return '<span class="badge bg-secondary">N/A</span>';
    const badges = {
      'gmail': 'bg-danger',
      'custom': 'bg-secondary'
    };
    const labels = {
      'gmail': 'Gmail',
      'custom': 'Personalizado'
    };
    const badgeClass = badges[provider] || 'bg-secondary';
    const label = labels[provider] || provider;
    return `<span class="badge ${badgeClass}">${label}</span>`;
  }

  // Helper: Renderizar badge de estado
  function renderStatus(status) {
    if (!status) return '<span class="badge bg-secondary">N/A</span>';
    const badges = {
      'active': 'bg-success',
      'inactive': 'bg-secondary'
    };
    const labels = {
      'active': 'Activa',
      'inactive': 'Inactiva'
    };
    const badgeClass = badges[status] || 'bg-secondary';
    const label = labels[status] || status;
    return `<span class="badge ${badgeClass}">${label}</span>`;
  }

  // Helper: Renderizar badge booleano
  function renderBoolean(value) {
    if (value) {
      return '<span class="badge bg-success">Sí</span>';
    } else {
      return '<span class="badge bg-secondary">No</span>';
    }
  }

  // Definir columnas específicas del módulo
  function getColumns() {
    return [
      {
        title: "Nombre",
        field: "nombre",
        formatter: w.TabulatorFactory.formatters.valueOrFallback,
        minWidth: 150
      },
      {
        title: "Email",
        field: "email_address",
        formatter: w.TabulatorFactory.formatters.valueOrFallback,
        width: 200
      },
      {
        title: "Proveedor",
        field: "provider",
        formatter: function(cell) {
          return renderProvider(cell.getValue());
        },
        width: 120
      },
      {
        title: "Host IMAP",
        field: "imap_host",
        formatter: w.TabulatorFactory.formatters.valueOrFallback,
        width: 180
      },
      {
        title: "Puerto IMAP",
        field: "imap_port",
        formatter: w.TabulatorFactory.formatters.valueOrFallback,
        width: 120
      },
      {
        title: "SSL",
        field: "imap_ssl",
        formatter: function(cell) {
          return renderBoolean(cell.getValue());
        },
        width: 80
      },
      {
        title: "Activa",
        field: "is_active",
        formatter: function(cell) {
          return renderBoolean(cell.getValue());
        },
        width: 100
      },
      {
        title: "Estado",
        field: "status",
        formatter: function(cell) {
          return renderStatus(cell.getValue());
        },
        width: 100
      },
      {
        title: "Última Sinc.",
        field: "last_sync_display",
        formatter: w.TabulatorFactory.formatters.valueOrFallback,
        width: 120
      },
      {
        title: "Acciones",
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const id = rowData.id;
          
          let buttons = '';
          
          // Botón Editar (v2.60: Usa offcanvas con HTMX)
          buttons += `
            <button class="btn btn-sm btn-link text-primary p-0 me-2" onclick="if(window.mailinboxOffcanvas){window.mailinboxOffcanvas.abrirEditar(${id});}" title="Editar Configuración">
              <i class="bi bi-pencil"></i>
            </button>
          `;
          
          // Botón Probar Conexión (v2.60: Ahora prueba directamente la conexión usando el ID)
          buttons += `
            <button class="btn btn-sm btn-link text-info p-0 me-2" onclick="window.mailinboxPage?.probarConexion(${id})" title="Probar Conexión (Backend)">
              <i class="bi bi-wifi"></i>
            </button>
          `;
          
          // Botón Eliminar
          buttons += `
            <button class="btn btn-sm btn-link text-danger p-0" onclick="window.mailinboxPage?.eliminar(${id})" title="Eliminar Configuración">
              <i class="fas fa-trash"></i>
            </button>
          `;
          
          return buttons || '-';
        },
        headerSort: false,
        hozAlign: "center",
        width: 200
      }
    ];
  }

  // Inicializar tabla
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error('[mailinbox.page] TabulatorFactory no está disponible');
      return null;
    }

    const columns = getColumns();
    table = w.TabulatorFactory.create(TABLE_SELECTOR, API_URL, columns, {
      searchInputSelector: SEARCH_SELECTOR
    });

    return table;
  }

  // Funciones de acciones
  async function editar(id) {
    console.log('[mailinbox.page] Editar configuración', id);
    if (w.mailinboxModals && typeof w.mailinboxModals.showEdit === 'function') {
      w.mailinboxModals.showEdit(id);
    } else {
      // Fallback: abrir modal directamente y cargar datos
      console.warn('[mailinbox.page] mailinboxModals.showEdit no disponible, usando fallback');
      const modal = d.querySelector('#modal-mailinbox-form');
      if (modal) {
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
        
        // Cargar datos si es necesario
        if (id) {
          // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
          // ⚠️ VALIDACIÓN CRÍTICA: Verificar que mailinboxAPI esté disponible
          if (!w.mailinboxAPI || typeof w.mailinboxAPI.get !== 'function') {
            const errorMsg = 'Error: El módulo de API no está disponible. Por favor, recargue la página.';
            console.error('[mailinbox.page] mailinboxAPI o mailinboxAPI.get no está disponible');
            
            if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
              w.SintelFeedback.error(errorMsg);
            } else {
              alert(errorMsg);
            }
            return;
          }
          
          const res = await w.mailinboxAPI.get(id);
          
          // ⚠️ v2.60: Aislamiento Gradual - Lógica de Negocio solo verifica ok
          if (!res.ok) {
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
              w.UIManager.handleError(res, '[mailinbox.page]', {
                modalSelector: '#modal-mailinbox-form',
                errorContainerSelector: '#mailinbox-form-feedback'
              });
            }
            return;
          }
          
          const data = res.data;
            
            // Llenar formulario con los datos
            const idInput = d.getElementById('mailinbox-id');
            if (idInput) idInput.value = data.id || '';
            
            const nombreInput = d.getElementById('mailinbox-nombre');
            if (nombreInput) nombreInput.value = data.nombre || '';
            
            const emailInput = d.getElementById('mailinbox-email_address');
            if (emailInput) emailInput.value = data.email_address || '';
            
            const providerSelect = d.getElementById('mailinbox-provider');
            if (providerSelect) providerSelect.value = data.provider || 'custom';
            
            const isActiveCheck = d.getElementById('mailinbox-is_active');
            if (isActiveCheck) isActiveCheck.checked = data.is_active !== false;
            
            const imapHostInput = d.getElementById('mailinbox-imap_host');
            if (imapHostInput) imapHostInput.value = data.imap_host || '';
            
            const imapPortInput = d.getElementById('mailinbox-imap_port');
            if (imapPortInput) imapPortInput.value = data.imap_port || 993;
            
            const imapUsernameInput = d.getElementById('mailinbox-imap_username');
            if (imapUsernameInput) imapUsernameInput.value = data.imap_username || '';
            
            // Password no se carga por seguridad, se deja vacío
            
            const imapSslCheck = d.getElementById('mailinbox-imap_ssl');
            if (imapSslCheck) imapSslCheck.checked = data.imap_ssl !== false;
            
            const imapStarttlsCheck = d.getElementById('mailinbox-imap_starttls');
            if (imapStarttlsCheck) imapStarttlsCheck.checked = data.imap_starttls || false;
            
            const imapMailboxInput = d.getElementById('mailinbox-imap_mailbox');
            if (imapMailboxInput) imapMailboxInput.value = data.imap_mailbox || 'INBOX';
            
            const imapMarkAsSeenCheck = d.getElementById('mailinbox-imap_mark_as_seen');
            if (imapMarkAsSeenCheck) imapMarkAsSeenCheck.checked = data.imap_mark_as_seen !== false;
            
            const imapMaxAttachmentInput = d.getElementById('mailinbox-imap_max_attachment_mb');
            if (imapMaxAttachmentInput) imapMaxAttachmentInput.value = data.imap_max_attachment_mb || 50;
            
            const imapMoveToInput = d.getElementById('mailinbox-imap_move_processed_to');
            if (imapMoveToInput) imapMoveToInput.value = data.imap_move_processed_to || '';
            
            // Actualizar título del modal
            const modalTitle = d.getElementById('modal-mailinbox-form-label');
            if (modalTitle) modalTitle.textContent = 'Editar Configuración';
            
            const btnGuardarTexto = d.getElementById('btn-guardar-mailinbox-texto');
            if (btnGuardarTexto) btnGuardarTexto.textContent = 'Actualizar';
        } else {
          // Modo creación: limpiar formulario
          const form = d.getElementById('form-mailinbox');
          if (form) form.reset();
          const idInput = d.getElementById('mailinbox-id');
          if (idInput) idInput.value = '';
          
          // Actualizar título del modal
          const modalTitle = d.getElementById('modal-mailinbox-form-label');
          if (modalTitle) modalTitle.textContent = 'Nueva Configuración';
          
          const btnGuardarTexto = d.getElementById('btn-guardar-mailinbox-texto');
          if (btnGuardarTexto) btnGuardarTexto.textContent = 'Guardar';
        }
        
        bsModal.show();
      } else {
        console.error('[mailinbox.page] Modal de edición no encontrado');
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError({ status: 500, data: { detail: 'Modal de edición no encontrado' } }, '[mailinbox.page]');
        }
      }
    }
  }

  function crear() {
    console.log('[mailinbox.page] Crear configuración');
    if (w.mailinboxModals && typeof w.mailinboxModals.showCreate === 'function') {
      w.mailinboxModals.showCreate();
    } else {
      // Fallback: abrir modal directamente
      console.warn('[mailinbox.page] mailinboxModals.showCreate no disponible, usando fallback');
      editar(null); // Usar editar con null para modo creación
    }
  }
  
  // Función para recopilar datos del formulario
  function collectMailInboxPayload() {
    const idInput = d.getElementById('mailinbox-id');
    const id = idInput ? idInput.value : null;
    
    const payload = {
      nombre: d.getElementById('mailinbox-nombre')?.value || '',
      email_address: d.getElementById('mailinbox-email_address')?.value || '',
      provider: d.getElementById('mailinbox-provider')?.value || 'custom',
      is_active: d.getElementById('mailinbox-is_active')?.checked || false,
      imap_host: d.getElementById('mailinbox-imap_host')?.value || '',
      imap_port: parseInt(d.getElementById('mailinbox-imap_port')?.value || '993', 10),
      imap_username: d.getElementById('mailinbox-imap_username')?.value || '',
      imap_password: d.getElementById('mailinbox-imap_password')?.value || '',
      imap_ssl: d.getElementById('mailinbox-imap_ssl')?.checked || false,
      imap_starttls: d.getElementById('mailinbox-imap_starttls')?.checked || false,
      imap_mailbox: d.getElementById('mailinbox-imap_mailbox')?.value || 'INBOX',
      imap_mark_as_seen: d.getElementById('mailinbox-imap_mark_as_seen')?.checked || false,
      imap_max_attachment_mb: parseInt(d.getElementById('mailinbox-imap_max_attachment_mb')?.value || '50', 10),
      imap_move_processed_to: d.getElementById('mailinbox-imap_move_processed_to')?.value || '',
    };
    
    // Eliminar campos vacíos opcionales
    if (!payload.imap_move_processed_to) {
      delete payload.imap_move_processed_to;
    }
    
    return { id, payload };
  }
  
  // Función para guardar (crear o actualizar)
  async function guardar() {
    console.log('[mailinbox.page] Guardar configuración');
    
    const { id, payload } = collectMailInboxPayload();
    
    // Validaciones básicas
    if (!payload.nombre || !payload.imap_host || !payload.imap_port || !payload.imap_username) {
      if (w.notyf) {
        if (w.SintelFeedback) {
          w.SintelFeedback.error('Por favor complete todos los campos requeridos');
        }
      }
      return;
    }
    
    // Si no hay password y es creación, requerir password
    if (!id && !payload.imap_password) {
      if (w.notyf) {
        if (w.SintelFeedback) {
          w.SintelFeedback.error('La contraseña es requerida para crear una nueva configuración');
        }
      }
      return;
    }
    
    // Si no hay password y es edición, no incluir el campo (mantener la existente)
    if (id && !payload.imap_password) {
      delete payload.imap_password;
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    // ⚠️ VALIDACIÓN CRÍTICA: Verificar que mailinboxAPI esté disponible antes de usar
    if (!w.mailinboxAPI) {
      const errorMsg = 'Error: El módulo de API no está disponible. Por favor, recargue la página.';
      console.error('[mailinbox.page] mailinboxAPI no está disponible');
      
      // Mostrar error al usuario
      if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error(errorMsg);
      } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(
          { ok: false, status: 500, data: { detail: errorMsg } },
          '[mailinbox.page]',
          {
            modalSelector: '#modal-mailinbox-form',
            errorContainerSelector: '#mailinbox-form-feedback'
          }
        );
      } else {
        alert(errorMsg);
      }
      return;
    }
    
    // Validar que los métodos necesarios estén disponibles
    if (!w.mailinboxAPI.create || !w.mailinboxAPI.update) {
      const errorMsg = 'Error: Los métodos de API no están disponibles. Por favor, recargue la página.';
      console.error('[mailinbox.page] mailinboxAPI.create o mailinboxAPI.update no están disponibles');
      
      if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error(errorMsg);
      } else {
        alert(errorMsg);
      }
      return;
    }
    
    // ⚠️ GUARDAR: Llamar al método apropiado según si es creación o actualización
    const res = id 
      ? await w.mailinboxAPI.update(id, payload)
      : await w.mailinboxAPI.create(payload);
    
    // ⚠️ v2.60: Aislamiento Gradual - Lógica de Negocio solo verifica ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, '[mailinbox.page]', {
          modalSelector: '#modal-mailinbox-form',
          errorContainerSelector: '#mailinbox-form-feedback'
        });
      }
      return;
    }
    
    // Éxito: mostrar notificación y cerrar modal
    if (w.SintelFeedback) {
      w.SintelFeedback.success(id ? 'Configuración actualizada correctamente' : 'Configuración creada correctamente');
    }
    
    // Cerrar modal usando UIManager
    if (w.UIManager && typeof w.UIManager.handleModal === 'function') {
      w.UIManager.handleModal('#modal-mailinbox-form', 'hide');
    } else {
      // Fallback: cerrar modal manualmente
      const modal = d.querySelector('#modal-mailinbox-form');
      if (modal) {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) bsModal.hide();
      }
    }
    
    // Refrescar tabla
    if (table) {
      table.replaceData();
    }
  }

  async function probarConexion(id) {
    console.log('[mailinbox.page] Probar conexión configuración', id);
    
    if (w.SintelFeedback) {
      w.SintelFeedback.info('Probando conexión en segundo plano...');
    }
    
    if (!w.mailinboxAPI || typeof w.mailinboxAPI.testConnection !== 'function') {
      console.error('[mailinbox.page] mailinboxAPI.testConnection no está disponible');
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API de prueba de conexión no disponible' } }, '[mailinbox.page]');
      }
      return;
    }
    
    const testRes = await w.mailinboxAPI.testConnection(id);
    
    if (!testRes.ok) {
      if (w.SintelFeedback) {
        const errorMsg = testRes.data?.message || testRes.data?.detail || 'Error en la conexión al servidor de correo. Verifique sus credenciales.';
        w.SintelFeedback.error(errorMsg);
      } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(testRes, '[mailinbox.page]');
      }
      return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success(testRes.data?.message || 'Conexión exitosa');
    }
  }
  
  /**
   * Ejecutar prueba de conexión
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function ejecutarTestConexion(testData) {
    if (w.SintelFeedback) {
      w.SintelFeedback.info('Probando conexión...');
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    if (!w.mailinboxAPI || typeof w.mailinboxAPI.testConnectionWithData !== 'function') {
      console.error('[mailinbox.page] mailinboxAPI.testConnectionWithData no está disponible');
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'API de prueba de conexión no disponible' } }, '[mailinbox.page]');
      }
      return;
    }
    
    const testRes = await w.mailinboxAPI.testConnectionWithData(testData);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!testRes.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(testRes, '[mailinbox.page]');
      }
      return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success(testRes.data?.message || 'Conexión exitosa');
    }
  }

  /**
   * Eliminar configuración
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function eliminar(id) {
    if (!confirm('¿Está seguro de eliminar esta configuración de correo? Esta acción es irreversible.')) {
      return;
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    // ⚠️ VALIDACIÓN CRÍTICA: Verificar que mailinboxAPI y el método estén disponibles
    if (!w.mailinboxAPI || typeof w.mailinboxAPI.delete !== 'function') {
      const errorMsg = 'Error: El módulo de API no está disponible. Por favor, recargue la página.';
      console.error('[mailinbox.page] mailinboxAPI.delete no está disponible');
      
      if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error(errorMsg);
      } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: errorMsg } }, '[mailinbox.page]');
      } else {
        alert(errorMsg);
      }
      return;
    }
    
    const deleteRes = await w.mailinboxAPI.delete(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!deleteRes.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(deleteRes, '[mailinbox.page]');
      }
      return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Configuración eliminada correctamente');
    }
    if (table) {
      table.replaceData();
    }
  }

  // Función para configurar eventos (reutilizable)
  function configurarEventos() {
    console.log('[mailinbox.page] Configurando eventos...');
    
    // Asegurar que el módulo esté inicializado
    if (!w.mailinboxPage) {
      console.warn('[mailinbox.page] mailinboxPage no está inicializado aún, inicializando...');
      w.mailinboxPage = {
        table: table,
        refresh: function() {
          if (table) {
            table.replaceData();
          }
        },
        editar: editar,
        crear: crear,
        guardar: guardar,
        probarConexion: probarConexion,
        eliminar: eliminar
      };
    }

    // Botón crear
    // ⚠️ v2.60: Botón crear ahora usa HTMX directamente (definido en mailinbox_list.html)
    // El listener se maneja automáticamente por HTMX
    const btnCrear = d.getElementById('btn-mailinbox-crear');
    if (btnCrear && w.htmx) {
      // HTMX ya maneja el click, pero agregamos listener para abrir offcanvas después de cargar
      btnCrear.addEventListener('htmx:afterSwap', (evt) => {
        if (evt.detail.target.id === 'offcanvas-container-mailinbox') {
          setTimeout(() => {
            const offcanvasEl = d.querySelector('#offcanvas-mailinbox');
            if (offcanvasEl && w.bootstrap) {
              const bsOffcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
              bsOffcanvas.show();
              
              // Inicializar eventos del offcanvas
              if (w.mailinboxOffcanvas && typeof w.mailinboxOffcanvas.init === 'function') {
                w.mailinboxOffcanvas.init();
              }
            }
          }, 100);
        }
      });
    }
    if (btnCrear) {
      const nuevoBtn = btnCrear.cloneNode(true);
      nuevoBtn.removeAttribute('onclick');
      btnCrear.parentNode.replaceChild(nuevoBtn, btnCrear);
      
      nuevoBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('[mailinbox.page] Click en botón "Nueva Configuración"');
        crear();
      });
    }
    
    // Botón guardar del modal
    const btnGuardar = d.getElementById('btn-guardar-mailinbox');
    if (btnGuardar) {
      const nuevoBtnGuardar = btnGuardar.cloneNode(true);
      nuevoBtnGuardar.removeAttribute('onclick');
      btnGuardar.parentNode.replaceChild(nuevoBtnGuardar, btnGuardar);
      
      nuevoBtnGuardar.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('[mailinbox.page] Click en botón "Guardar"');
        guardar();
      });
    }
    
    // Limpiar feedback cuando se abre el modal
    const modal = d.querySelector('#modal-mailinbox-form');
    if (modal) {
      modal.addEventListener('show.bs.modal', function() {
        const feedback = d.getElementById('mailinbox-form-feedback');
        if (feedback) {
          feedback.classList.add('d-none');
          feedback.textContent = '';
        }
      });
    }
  }

  // Función para inicializar el módulo completo
  async function inicializarModulo() {
    console.log('[mailinbox.page] Inicializando módulo completo...');
    
    // Verificar dependencias críticas
    if (!w.TabulatorFactory) {
      console.error('[mailinbox.page] ❌ CRÍTICO: TabulatorFactory no está disponible.');
      return;
    }

    // Inicializar tabla
    table = initTable();
    
    // Exponer módulo globalmente ANTES de configurar eventos
    w.mailinboxPage = {
      table: table,
      refresh: function() {
        if (table) {
          table.replaceData();
        }
      },
      editar: editar,
      crear: crear,
      guardar: guardar,
      probarConexion: probarConexion,
      eliminar: eliminar
    };
    
    console.log('[mailinbox.page] Módulo expuesto globalmente:', w.mailinboxPage);
    
    // Configurar eventos DESPUÉS de inicializar el módulo
    configurarEventos();
  }

  // Lazy Loading: Inicializar solo cuando el tab sea visible
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(TAB_ID, function() {
      console.log('[mailinbox.page] Tab de empresa visible, inicializando mailinbox...');
      inicializarModulo().catch(err => {
        console.error('[mailinbox.page] Error en inicialización:', err);
      });
    });
  } else {
    // Fallback si DOMUtils no está disponible
    console.warn('[mailinbox.page] DOMUtils no disponible, inicializando inmediatamente');
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      
      inicializarModulo().catch(err => {
        console.error('[mailinbox.page] Error en inicialización (fallback):', err);
      });
    }
    initFallback();
  }
  
  // También configurar eventos cuando el tab de empresa se muestre (Bootstrap event)
  d.addEventListener('shown.bs.tab', function(e) {
    if (e.target && (e.target.getAttribute('data-tab') === 'empresa' || e.target.getAttribute('data-bs-target') === TAB_ID)) {
      console.log('[mailinbox.page] Tab de empresa mostrado, verificando eventos...');
      // Asegurar que el módulo esté inicializado
      if (!w.mailinboxPage) {
        console.log('[mailinbox.page] Módulo no inicializado, inicializando desde evento shown.bs.tab...');
        inicializarModulo().catch(err => {
          console.error('[mailinbox.page] Error en inicialización desde evento:', err);
        });
      } else {
        setTimeout(configurarEventos, 100);
      }
    }
  });

})(window, document);
