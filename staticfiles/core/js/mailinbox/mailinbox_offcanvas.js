/**
 * mailinbox_offcanvas.js - Lógica para Offcanvas de MailInboxConfig v2.60
 * ⚠️ HTMX-Driven: Offcanvas cargado dinámicamente desde ViewSet
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 */
(function (w, d) {
  'use strict';

  const MOD = '[mailinbox.offcanvas]';
  const OFFCANVAS_ID = '#offcanvas-mailinbox';
  const FORM_ID = '#form-mailinbox';

  /**
   * Inicializar eventos del offcanvas
   */
  function initOffcanvasEvents() {
    // ⚠️ v2.60: Buscar offcanvas en múltiples ubicaciones posibles
    let offcanvasEl = null;
    
    // 1. Buscar en el contenedor global (workspace.html)
    const globalContainer = d.getElementById('offcanvas-container-mailinbox');
    if (globalContainer) {
      offcanvasEl = globalContainer.querySelector(OFFCANVAS_ID);
    }
    
    // 2. Si no se encuentra, buscar en el contenedor local (mailinbox_list.html)
    if (!offcanvasEl) {
      const localContainer = d.querySelector('#mailinbox-module-container #offcanvas-container-mailinbox');
      if (localContainer) {
        offcanvasEl = localContainer.querySelector(OFFCANVAS_ID);
      }
    }
    
    // 3. Último recurso: buscar directamente en el DOM
    if (!offcanvasEl) {
      offcanvasEl = d.querySelector(OFFCANVAS_ID);
    }
    
    if (!offcanvasEl) {
      console.warn(`${MOD} Offcanvas no encontrado. Asegúrese de que HTMX haya cargado el contenido.`);
      return;
    }

    // Toggle mostrar/ocultar contraseña
    const btnTogglePassword = d.getElementById('btn-toggle-password');
    const inputPassword = d.getElementById('mailinbox-imap_password');
    const iconTogglePassword = d.getElementById('icon-toggle-password');
    
    if (btnTogglePassword && inputPassword && iconTogglePassword) {
      btnTogglePassword.addEventListener('click', () => {
        const type = inputPassword.type === 'password' ? 'text' : 'password';
        inputPassword.type = type;
        iconTogglePassword.classList.toggle('bi-eye');
        iconTogglePassword.classList.toggle('bi-eye-slash');
      });
    }

    // Listener para cuando el offcanvas se muestra (Bootstrap event)
    offcanvasEl.addEventListener('shown.bs.offcanvas', () => {
      console.log(`${MOD} Offcanvas mostrado`);
      // El formulario ya está cargado por HTMX
    });

    // Listener para cuando el offcanvas se oculta (limpiar formulario)
    offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
      console.log(`${MOD} Offcanvas ocultado, limpiando formulario`);
      // Buscar el formulario dentro del contenedor
      const containerEl = d.getElementById('offcanvas-container-mailinbox');
      const form = containerEl ? containerEl.querySelector(FORM_ID) : d.querySelector(FORM_ID);
      if (form) {
        form.reset();
        const idInput = d.getElementById('mailinbox-id');
        if (idInput) idInput.value = '';
        
        // Limpiar resultado de prueba de conexión
        const testResult = d.getElementById('test-connection-result');
        if (testResult) {
          testResult.classList.add('d-none');
          testResult.innerHTML = '';
        }
      }
    });

    // Botón Probar Conexión
    const btnProbarConexion = d.getElementById('btn-probar-conexion-mailinbox');
    if (btnProbarConexion) {
      btnProbarConexion.addEventListener('click', async () => {
        await probarConexion();
      });
    }

    // Botón Guardar
    const btnGuardar = d.getElementById('btn-guardar-mailinbox');
    if (btnGuardar) {
      btnGuardar.addEventListener('click', async () => {
        await guardarConfiguracion();
      });
    }
  }

  /**
   * Probar conexión con el buzón de correo
   */
  async function probarConexion() {
    const btnProbar = d.getElementById('btn-probar-conexion-mailinbox');
    const testResult = d.getElementById('test-connection-result');
    
    if (!btnProbar || !testResult) {
      console.warn(`${MOD} Elementos para probar conexión no encontrados`);
      return;
    }

    // Recolectar datos del formulario
    const formData = recolectarDatosFormulario();
    
    // Validar campos mínimos
    if (!formData.imap_host || !formData.imap_port || !formData.imap_username || !formData.imap_password) {
      testResult.className = 'mt-2 alert alert-warning';
      testResult.classList.remove('d-none');
      testResult.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Por favor complete todos los campos requeridos (Host, Puerto, Usuario y Contraseña)';
      return;
    }

    // Preparar payload para test-connection
    const payload = {
      host: formData.imap_host,
      port: parseInt(formData.imap_port, 10),
      protocol: 'imap',
      username: formData.imap_username,
      password: formData.imap_password,
      use_ssl: formData.imap_ssl || false,
      use_starttls: formData.imap_starttls || false,
    };

    // Deshabilitar botón durante la prueba
    const originalHTML = btnProbar.innerHTML;
    btnProbar.disabled = true;
    btnProbar.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Probando...';

    try {
      // Llamar al endpoint de prueba de conexión
      let res;
      if (w.http && typeof w.http === 'function') {
        res = await w.http('POST', '/api/v1/empresas/mail-inbox-config/test-connection/', payload);
      } else {
        throw new Error('HTTP client no disponible');
      }

      // Mostrar resultado
      testResult.classList.remove('d-none');
      
      if (res.ok && res.data && res.data.ok) {
        testResult.className = 'mt-2 alert alert-success';
        testResult.innerHTML = `<i class="bi bi-check-circle"></i> <strong>¡Conexión exitosa!</strong><br><small>${res.data.message || 'La conexión al buzón de correo se estableció correctamente.'}</small>`;
      } else {
        testResult.className = 'mt-2 alert alert-danger';
        const errorMsg = res.data?.message || 'Error al probar la conexión. Verifique las credenciales y la configuración.';
        testResult.innerHTML = `<i class="bi bi-x-circle"></i> <strong>Error de conexión</strong><br><small>${errorMsg}</small>`;
      }
    } catch (error) {
      console.error(`${MOD} Error al probar conexión:`, error);
      testResult.classList.remove('d-none');
      testResult.className = 'mt-2 alert alert-danger';
      testResult.innerHTML = `<i class="bi bi-x-circle"></i> <strong>Error inesperado</strong><br><small>${error.message || 'Error al probar la conexión'}</small>`;
    } finally {
      // Restaurar botón
      btnProbar.disabled = false;
      btnProbar.innerHTML = originalHTML;
    }
  }

  /**
   * Recolectar datos del formulario
   */
  function recolectarDatosFormulario() {
    return {
      id: d.getElementById('mailinbox-id')?.value || null,
      nombre: d.getElementById('mailinbox-nombre')?.value || '',
      email_address: d.getElementById('mailinbox-email_address')?.value || '',
      provider: d.getElementById('mailinbox-provider')?.value || 'custom',
      is_active: d.getElementById('mailinbox-is_active')?.checked || false,
      imap_host: d.getElementById('mailinbox-imap_host')?.value || '',
      imap_port: d.getElementById('mailinbox-imap_port')?.value || '993',
      imap_username: d.getElementById('mailinbox-imap_username')?.value || '',
      imap_password: d.getElementById('mailinbox-imap_password')?.value || '',
      imap_ssl: d.getElementById('mailinbox-imap_ssl')?.checked || false,
      imap_starttls: d.getElementById('mailinbox-imap_starttls')?.checked || false,
      imap_mailbox: d.getElementById('mailinbox-imap_mailbox')?.value || 'INBOX',
      imap_mark_as_seen: d.getElementById('mailinbox-imap_mark_as_seen')?.checked || false,
      imap_max_attachment_mb: d.getElementById('mailinbox-imap_max_attachment_mb')?.value || '50',
      imap_move_processed_to: d.getElementById('mailinbox-imap_move_processed_to')?.value || '',
    };
  }

  /**
   * Guardar configuración (crear o actualizar)
   */
  async function guardarConfiguracion() {
    const btnGuardar = d.getElementById('btn-guardar-mailinbox');
    if (!btnGuardar) {
      console.warn(`${MOD} Botón guardar no encontrado`);
      return;
    }

    const formData = recolectarDatosFormulario();
    
    // Validaciones básicas
    if (!formData.nombre || !formData.imap_host || !formData.imap_port || !formData.imap_username) {
      if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
        w.SintelFeedback.warning('Por favor complete todos los campos requeridos');
      } else {
        alert('Por favor complete todos los campos requeridos');
      }
      return;
    }

    // Si es edición, la contraseña es opcional (solo se actualiza si se proporciona)
    if (!formData.id && !formData.imap_password) {
      if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
        w.SintelFeedback.warning('La contraseña es requerida para crear una nueva configuración');
      } else {
        alert('La contraseña es requerida para crear una nueva configuración');
      }
      return;
    }

    // Deshabilitar botón durante el guardado
    const originalHTML = btnGuardar.innerHTML;
    btnGuardar.disabled = true;
    btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Guardando...';

    try {
      let res;
      const payload = { ...formData };
      
      // Eliminar campos vacíos opcionales
      if (!payload.imap_move_processed_to) {
        delete payload.imap_move_processed_to;
      }
      
      // Si es edición y no hay contraseña, no enviarla
      if (formData.id && !formData.imap_password) {
        delete payload.imap_password;
      }

      if (w.http && typeof w.http === 'function') {
        if (formData.id) {
          // Actualizar
          res = await w.http('PATCH', `/api/v1/empresas/mail-inbox-config/${formData.id}/`, payload);
        } else {
          // Crear
          res = await w.http('POST', '/api/v1/empresas/mail-inbox-config/', payload);
        }
      } else {
        throw new Error('HTTP client no disponible');
      }

      if (res.ok) {
        // Cerrar offcanvas (buscar dentro del contenedor)
        const containerEl = d.getElementById('offcanvas-container-mailinbox');
        const offcanvasEl = containerEl ? containerEl.querySelector(OFFCANVAS_ID) : d.querySelector(OFFCANVAS_ID);
        if (offcanvasEl) {
          const bsOffcanvas = w.bootstrap?.Offcanvas?.getInstance(offcanvasEl);
          if (bsOffcanvas) {
            bsOffcanvas.hide();
          }
        }

        // Refrescar tabla
        if (w.mailinboxModals && typeof w.mailinboxModals.refresh === 'function') {
          w.mailinboxModals.refresh();
        } else if (w.mailinbox && typeof w.mailinbox.refresh === 'function') {
          w.mailinbox.refresh();
        }

        // Mostrar mensaje de éxito
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
          w.SintelFeedback.success(formData.id ? 'Configuración actualizada correctamente' : 'Configuración creada correctamente');
        }
      } else {
        // El error será manejado por error_injector.js
        console.error(`${MOD} Error al guardar:`, res);
      }
    } catch (error) {
      console.error(`${MOD} Error inesperado al guardar:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: error.message } }, MOD);
      }
    } finally {
      // Restaurar botón
      btnGuardar.disabled = false;
      btnGuardar.innerHTML = originalHTML;
    }
  }

  /**
   * Abrir offcanvas para editar (llamado desde mailinbox.page.js)
   */
  function abrirEditar(id) {
    const container = d.getElementById('offcanvas-container-mailinbox');
    if (!container) {
      console.warn(`${MOD} Contenedor de offcanvas no encontrado`);
      return;
    }

    // Cargar offcanvas con HTMX
    const url = id 
      ? `/api/v1/empresas/mail-inbox-config/render-offcanvas/?id=${id}`
      : '/api/v1/empresas/mail-inbox-config/render-offcanvas/';
    
    if (w.htmx) {
      // ⚠️ v2.60: Usar htmx:afterSettle para garantizar que el DOM esté completamente actualizado
      // Escuchar el evento antes de hacer la petición
      const handleAfterSettle = (evt) => {
        const target = evt.detail.target;
        if (target && (target.id === 'offcanvas-container-mailinbox' || target.closest('#offcanvas-container-mailinbox'))) {
          console.log(`${MOD} Offcanvas cargado por HTMX (afterSettle en abrirEditar), inicializando...`);
          
          const containerEl = d.getElementById('offcanvas-container-mailinbox');
          const offcanvasEl = containerEl ? containerEl.querySelector(OFFCANVAS_ID) : null;
          
          if (offcanvasEl) {
            // Inicializar eventos
            initOffcanvasEvents();
            
            // Mostrar offcanvas
            if (w.bootstrap && w.bootstrap.Offcanvas) {
              const bsOffcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
              bsOffcanvas.show();
              console.log(`${MOD} Offcanvas abierto correctamente`);
            } else {
              console.error(`${MOD} Bootstrap.Offcanvas no está disponible`);
            }
            
            // Remover el listener una vez procesado
            d.body.removeEventListener('htmx:afterSettle', handleAfterSettle);
          } else {
            console.error(`${MOD} Offcanvas no encontrado después de afterSettle`);
          }
        }
      };
      
      // Agregar listener temporal para este caso específico
      d.body.addEventListener('htmx:afterSettle', handleAfterSettle);
      
      // Realizar la petición HTMX
      w.htmx.ajax('GET', url, {
        target: '#offcanvas-container-mailinbox',
        swap: 'innerHTML'
      });
    } else {
      console.error(`${MOD} HTMX no está disponible`);
    }
  }

  // Exponer funciones globalmente
  if (!w.mailinboxOffcanvas) {
    w.mailinboxOffcanvas = {};
  }
  w.mailinboxOffcanvas.init = initOffcanvasEvents;
  w.mailinboxOffcanvas.abrirEditar = abrirEditar;
  w.mailinboxOffcanvas.probarConexion = probarConexion;
  w.mailinboxOffcanvas.guardar = guardarConfiguracion;

  // ⚠️ v2.60: Listener global para eventos HTMX usando htmx:afterSettle (garantiza DOM completamente actualizado)
  // ⚠️ IMPORTANTE: NO inicializar automáticamente en DOMContentLoaded porque el offcanvas se carga dinámicamente con HTMX
  // ⚠️ DELEGACIÓN DE EVENTOS: Escucha globalmente para cualquier swap en el contenedor de mailinbox
  if (d.body) {
    // htmx:afterSettle se dispara DESPUÉS de que HTMX haya terminado de actualizar el DOM
    // Esto garantiza que el offcanvas esté completamente disponible antes de inicializar eventos
    d.body.addEventListener('htmx:afterSettle', function(evt) {
      // ⚠️ Validar que el swap haya ocurrido en nuestro contenedor de mailinbox
      const target = evt.detail.target;
      if (!target) return;
      
      // Verificar si el target es el contenedor o está dentro de él
      const isTargetContainer = target.id === 'offcanvas-container-mailinbox';
      const isInsideContainer = target.closest && target.closest('#offcanvas-container-mailinbox');
      
      if (isTargetContainer || isInsideContainer) {
        console.info(`${MOD} Offcanvas cargado por HTMX (afterSettle), buscando elemento...`);
        
        // ⚠️ Buscar el offcanvas con ID exacto (sin selector CSS)
        const offcanvasEl = d.getElementById('offcanvas-mailinbox');
        
        if (offcanvasEl) {
          console.info(`${MOD} Elemento encontrado (ID: offcanvas-mailinbox), inicializando eventos...`);
          
          // ⚠️ Evitar inicialización duplicada: verificar si ya tiene eventos
          if (!offcanvasEl.dataset.eventsInitialized) {
            initOffcanvasEvents();
            offcanvasEl.dataset.eventsInitialized = 'true';
            console.log(`${MOD} Eventos del offcanvas inicializados correctamente`);
          } else {
            console.log(`${MOD} Eventos del offcanvas ya estaban inicializados`);
          }
        } else {
          console.error(`${MOD} Error: El ID "offcanvas-mailinbox" no existe en el HTML recibido. Target:`, target);
          // ⚠️ Debug: Mostrar contenido del contenedor para diagnóstico
          const containerEl = d.getElementById('offcanvas-container-mailinbox');
          if (containerEl) {
            console.warn(`${MOD} Contenido del contenedor:`, containerEl.innerHTML.substring(0, 200));
          }
        }
      }
    });
  }

  console.log(`${MOD} Módulo de offcanvas inicializado`);

})(window, document);
