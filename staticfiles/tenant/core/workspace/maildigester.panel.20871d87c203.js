/**
 * Panel de configuración de MailInboxConfig y prueba de conexión.
 * 
 * ⚠️ SSoT: Gestiona configuraciones de buzones desde Empresa.
 * ⚠️ API-First: Consume /api/v1/core/empresa/mailbox/configs/ y /api/v1/core/maildigester/configs/test/
 */

(function() {
  'use strict';

  const BASE_EMPRESA_API = "/api/v1/core/empresa";
  const TEST_CONFIG_API = "/api/v1/core/maildigester/configs/test/";

  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function showFeedback(message, type = 'info') {
    const el = document.getElementById('feedback-mail-config');
    if (!el) return;
    
    el.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'}`;
    el.textContent = message;
    el.classList.remove('d-none');
    el.setAttribute('aria-live', 'polite');
  }

  function hideFeedback() {
    const el = document.getElementById('feedback-mail-config');
    if (!el) return;
    el.classList.add('d-none');
    el.textContent = '';
  }

  async function loadConfigs() {
    try {
      const res = await fetch(`${BASE_EMPRESA_API}/mailbox/configs/`, {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      });

      if (!res.ok) {
        console.error('[maildigester.panel] Error cargando configuraciones:', res.status);
        return [];
      }

      const data = await res.json();
      const items = Array.isArray(data) ? data : (Array.isArray(data.results) ? data.results : []);
      return items;
    } catch (err) {
      console.error('[maildigester.panel] Error en loadConfigs:', err);
      return [];
    }
  }

  async function populateConfigSelect() {
    const select = document.getElementById('mail-config-select');
    if (!select) return;

    const configs = await loadConfigs();
    
    // Limpiar opciones existentes (excepto la primera placeholder)
    while (select.children.length > 1) {
      select.removeChild(select.lastChild);
    }

    configs.forEach(cfg => {
      const opt = document.createElement('option');
      opt.value = cfg.id;
      opt.textContent = `${cfg.nombre || 'Sin nombre'} (${cfg.protocol?.toUpperCase() || 'IMAP'}://${cfg.username || ''}@${cfg.host || ''}:${cfg.port || 993})`;
      select.appendChild(opt);
    });
  }

  function readFormData() {
    // Intentar leer desde los inputs nuevos primero, luego fallback a los antiguos
    const getValue = (newId, oldId, defaultValue = '') => {
      const el = document.getElementById(newId) || document.getElementById(oldId);
      return el?.value?.trim() || defaultValue;
    };
    const getChecked = (newId, oldId, defaultValue = false) => {
      const el = document.getElementById(newId) || document.getElementById(oldId);
      return el?.checked !== false;
    };
    const getInt = (newId, oldId, defaultValue = 0) => {
      const el = document.getElementById(newId) || document.getElementById(oldId);
      return parseInt(el?.value, 10) || defaultValue;
    };

    // Leer proveedor
    const providerEl = document.getElementById('mail-provider');
    const provider = providerEl?.value || 'custom';

    // Leer protocolo desde select existente
    const protocolEl = document.getElementById('protocol');
    const protocol = protocolEl?.value || 'imap';

    return {
      provider: provider,
      email_address: getValue('mail-email', 'email_address', ''),
      host: getValue('mail-host', 'host', ''),
      port: getInt('mail-port', 'port', 993),
      protocol: protocol,
      ssl: getChecked('mail-ssl', 'ssl', true),
      starttls: getChecked('mail-starttls', 'starttls', false),
      username: getValue('mail-username', 'username', ''),
      password: getValue('mail-password', 'password', ''),
      mailbox: getValue('mail-mailbox', 'mailbox', 'INBOX'),
      mark_as_seen: getChecked('mail-mark-seen', 'mark_as_seen', true),
      move_processed_to: getValue('mail-move-to', 'move_processed_to', null),
      max_attachment_mb: getInt('mail-max-mb', 'max_attachment_mb', 50)
    };
  }

  function validateFormData(data) {
    // Si es Gmail, no validar host/port (se autocompletan)
    if (data.provider !== 'gmail') {
      if (!data.host) {
        showFeedback('El host es obligatorio.', 'error');
        return false;
      }
      if (data.port < 1 || data.port > 65535) {
        showFeedback('El puerto debe estar entre 1 y 65535.', 'error');
        return false;
      }
    }
    
    // Username: si es Gmail y no hay username, usar email_address
    const username = data.username || (data.provider === 'gmail' ? data.email_address : '');
    if (!username) {
      showFeedback('El usuario es obligatorio (o proporciona email principal para Gmail).', 'error');
      return false;
    }
    
    if (!data.password) {
      showFeedback('La contraseña es obligatoria para probar la conexión.', 'error');
      return false;
    }
    
    return true;
  }

  function onProviderChange() {
    const providerEl = document.getElementById('mail-provider');
    const provider = providerEl?.value || 'custom';
    
    const hostEl = document.getElementById('mail-host') || document.getElementById('host');
    const portEl = document.getElementById('mail-port') || document.getElementById('port');
    const sslEl = document.getElementById('mail-ssl') || document.getElementById('ssl');
    const starttlsEl = document.getElementById('mail-starttls');
    const smtpHostEl = document.getElementById('mail-smtp-host');
    const smtpPortEl = document.getElementById('mail-smtp-port');
    const smtpSslEl = document.getElementById('mail-smtp-ssl');
    const smtpStarttlsEl = document.getElementById('mail-smtp-starttls');
    const gmailHelpEl = document.getElementById('gmail-help');
    
    if (provider === 'gmail') {
      // Mostrar ayuda de Gmail
      if (gmailHelpEl) {
        gmailHelpEl.classList.remove('hidden');
      }
      
      // Autocompletar y bloquear campos IMAP
      if (hostEl) {
        hostEl.value = 'imap.gmail.com';
        hostEl.readOnly = true;
        hostEl.classList.add('bg-light');
      }
      if (portEl) {
        portEl.value = '993';
        portEl.readOnly = true;
        portEl.classList.add('bg-light');
      }
      if (sslEl) {
        sslEl.checked = true;
        sslEl.disabled = true;
      }
      if (starttlsEl) {
        starttlsEl.checked = false;
        starttlsEl.disabled = true;
      }
      
      // Autocompletar SMTP (587 TLS por defecto)
      if (smtpHostEl) {
        smtpHostEl.value = 'smtp.gmail.com';
        smtpHostEl.readOnly = true;
        smtpHostEl.classList.add('bg-light');
      }
      if (smtpPortEl) {
        smtpPortEl.value = '587';
        smtpPortEl.readOnly = true;
        smtpPortEl.classList.add('bg-light');
      }
      if (smtpSslEl) {
        smtpSslEl.checked = false;
        smtpSslEl.disabled = true;
      }
      if (smtpStarttlsEl) {
        smtpStarttlsEl.checked = true;
        smtpStarttlsEl.disabled = true;
      }
    } else {
      // Custom: ocultar ayuda y desbloquear campos
      if (gmailHelpEl) {
        gmailHelpEl.classList.add('hidden');
      }
      
      if (hostEl) {
        hostEl.readOnly = false;
        hostEl.classList.remove('bg-light');
      }
      if (portEl) {
        portEl.readOnly = false;
        portEl.classList.remove('bg-light');
      }
      if (sslEl) {
        sslEl.disabled = false;
      }
      if (starttlsEl) {
        starttlsEl.disabled = false;
      }
      if (smtpHostEl) {
        smtpHostEl.readOnly = false;
        smtpHostEl.classList.remove('bg-light');
      }
      if (smtpPortEl) {
        smtpPortEl.readOnly = false;
        smtpPortEl.classList.remove('bg-light');
      }
      if (smtpSslEl) {
        smtpSslEl.disabled = false;
      }
      if (smtpStarttlsEl) {
        smtpStarttlsEl.disabled = false;
      }
    }
  }

  async function testConnection() {
    hideFeedback();
    
    const formData = readFormData();
    if (!validateFormData(formData)) {
      return;
    }

    showFeedback('Probando conexión...', 'info');

    try {
      // Si es Gmail, usar email_address como username si no hay username
      const username = formData.username || (formData.provider === 'gmail' ? formData.email_address : '');
      
      // Construir payload - SIEMPRE incluir provider cuando es Gmail
      const payload = {
        provider: formData.provider || 'custom',  // Crítico: siempre enviar provider
        email_address: formData.email_address,
        // Para Gmail, no enviar host/port/ssl/starttls (el servidor los fuerza)
        // Para custom, enviar los valores del formulario
        ...(formData.provider === 'gmail' ? {} : {
          host: formData.host,
          port: formData.port,
          ssl: formData.ssl,
          starttls: formData.starttls
        }),
        protocol: formData.protocol || 'imap',
        username: username,
        password: formData.password,
        mailbox: formData.mailbox || 'INBOX'
      };

      // Logging seguro ANTES del fetch (sin contraseña)
      console.debug('[mail test] body(safe):', {
        provider: payload.provider,
        imap_host: formData.provider === 'gmail' ? 'imap.gmail.com' : payload.host,
        imap_port: formData.provider === 'gmail' ? 993 : payload.port,
        imap_ssl: formData.provider === 'gmail' ? true : payload.ssl,
        imap_starttls: formData.provider === 'gmail' ? false : payload.starttls,
        imap_username: username,
        email_address: formData.email_address
      });

      const csrftoken = getCookie('csrftoken');
      if (!csrftoken) {
        showFeedback('Error: No se encontró token CSRF. Por favor, recarga la página.', 'error');
        return;
      }

      const res = await fetch(TEST_CONFIG_API, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify(payload)
      });

      const result = await res.json();

      if (res.ok && result.ok) {
        const caps = result.capabilities?.join(', ') || 'N/A';
        const banner = result.banner ? `Banner: ${escapeHtml(result.banner)}. ` : '';
        showFeedback(`✓ Conexión exitosa. ${banner}Capabilities: ${caps}`, 'success');
      } else {
        // Mapeo de códigos de error específicos con mensajes mejorados
        let msg = result.message || 'Error desconocido';
        const code = result.code;
        
        if (code === 'AUTHENTICATIONFAILED') {
          msg = 'Credenciales inválidas. En Gmail activa IMAP y, si tienes 2FA, usa Contraseña de App (no tu contraseña normal).';
        } else if (code === 'IMAP_DISABLED') {
          msg = 'IMAP deshabilitado en Gmail. Actívalo en Settings → Forwarding and POP/IMAP → Enable IMAP.';
        } else if (code === 'TLS_ERROR') {
          msg = 'Fallo de conexión segura (IMAPS 993). Verifica puerto/SSL y firewall; prueba con: openssl s_client -connect imap.gmail.com:993 -crlf -quiet';
        }
        // Si no hay código específico pero el mensaje contiene indicios, intentar mapear
        else if (formData.provider === 'gmail') {
          const msgUpper = msg.toUpperCase();
          if (msgUpper.includes('AUTHENTICATION') || msgUpper.includes('LOGIN') || msgUpper.includes('AUTHENTICATE')) {
            msg = 'Credenciales inválidas. En Gmail activa IMAP y, si tienes 2FA, usa Contraseña de App (no tu contraseña normal).';
          } else if (msgUpper.includes('NOT ENABLED') || msgUpper.includes('IMAP') && (msgUpper.includes('DISABLED') || msgUpper.includes('ENABLE'))) {
            msg = 'IMAP deshabilitado en Gmail. Actívalo en Settings → Forwarding and POP/IMAP → Enable IMAP.';
          } else if (msgUpper.includes('EOF') || msgUpper.includes('TLS') || msgUpper.includes('SSL') || msgUpper.includes('CERTIFICATE')) {
            msg = 'Fallo de conexión segura (IMAPS 993). Verifica puerto/SSL y firewall; prueba con: openssl s_client -connect imap.gmail.com:993 -crlf -quiet';
          }
        }
        
        showFeedback(`✗ Error de conexión: ${escapeHtml(msg)}`, 'error');
      }
    } catch (err) {
      console.error('[maildigester.panel] Error probando conexión:', err);
      showFeedback(`Error de red: ${err.message}`, 'error');
    }
  }

  // Inicialización
  document.addEventListener('DOMContentLoaded', () => {
    const btnTest = document.getElementById('btn-test-mail-config');
    if (btnTest && !btnTest.dataset.listenerAttached) {
      btnTest.addEventListener('click', testConnection);
      btnTest.dataset.listenerAttached = 'true';
    }

    // Listener para cambio de proveedor
    const providerEl = document.getElementById('mail-provider');
    if (providerEl && !providerEl.dataset.listenerAttached) {
      providerEl.addEventListener('change', onProviderChange);
      providerEl.dataset.listenerAttached = 'true';
      // Ejecutar una vez al cargar para aplicar estado inicial
      onProviderChange();
    }

    // Cargar configuraciones al iniciar
    populateConfigSelect().catch(err => {
      console.error('[maildigester.panel] Error inicializando:', err);
    });
  });

  // Exponer funciones globales si es necesario
  if (typeof window !== 'undefined') {
    window.maildigesterPanel = {
      loadConfigs: populateConfigSelect,
      testConnection: testConnection
    };
  }
})();
