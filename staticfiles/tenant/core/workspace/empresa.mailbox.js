/**
 * UI Module para MailInboxConfig (API-First) - CRUD Completo.
 * 
 * ⚠️ SSoT: Gestiona configuraciones de buzones de correo desde Empresa.
 * ⚠️ JSON-only: Consume APIs REST con SessionAuthentication + CSRF.
 * ⚠️ CRUD: Crear, Listar, Ver, Editar, Eliminar configuraciones.
 * ⚠️ TEST: Prueba conexión IMAP sin persistir.
 */
(function () {
  'use strict';
  
  const BASE_EMPRESA_API = "/api/v1/core/empresa";
  const TEST_CONFIG_API = "/api/v1/core/maildigester/configs/test/";
  
  // ===== HELPERS CSRF + FETCH =====
  
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }
  
  function getCSRF() {
    return getCookie('csrftoken');
  }
  
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
  
  function showFeedback(elementId, message, type = 'info') {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = message;
    el.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} mt-3`;
    el.classList.remove('d-none');
    if (type === 'success' || type === 'error') {
      setTimeout(() => {
        el.classList.add('d-none');
      }, 5000);
    }
  }
  
  function hideFeedback(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.classList.add('d-none');
  }
  
  async function apiGet(url) {
    const r = await fetch(url, { 
      credentials: "same-origin",
      headers: {
        "Accept": "application/json",
      }
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || j.message || `GET ${url} → ${r.status}`);
    }
    return r.json();
  }
  
  async function apiPost(url, body) {
    const r = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRFToken": getCSRF(),
      },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || j.message || `POST ${url} → ${r.status}`);
    }
    return r.json();
  }
  
  async function apiPatch(url, body) {
    const r = await fetch(url, {
      method: "PATCH",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRFToken": getCSRF(),
      },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || j.message || `PATCH ${url} → ${r.status}`);
    }
    return r.json();
  }
  
  async function apiDelete(url) {
    const r = await fetch(url, {
      method: "DELETE",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": getCSRF(),
      }
    });
    if (r.status === 204 || r.status === 200) {
      return {};
    }
    const j = await r.json().catch(() => ({}));
    throw new Error(j.detail || j.message || `DELETE ${url} → ${r.status}`);
  }
  
  // ===== UI UTILS =====
  
  function uiLockForm(locked) {
    const form = document.getElementById('mailboxForm');
    if (!form) return;
    const inputs = form.querySelectorAll('input, select, button');
    inputs.forEach(el => {
      if (el.id !== 'btn-test-mail-config' && el.id !== 'btnGuardar' && el.id !== 'btn-mailbox-cancel') {
        el.disabled = !!locked;
      }
    });
    const btnTest = document.getElementById('btn-test-mail-config');
    const btnSave = document.getElementById('btnGuardar');
    if (btnTest) btnTest.disabled = !!locked;
    if (btnSave) btnSave.disabled = !!locked;
  }
  
  function showForm(show) {
    const formPanel = document.getElementById('mailbox-form-panel');
    const listPanel = document.getElementById('mailbox-configs-panel');
    if (formPanel) formPanel.classList.toggle('hidden', !show);
    if (listPanel) listPanel.classList.toggle('hidden', show);
  }
  
  function showList(show) {
    const formPanel = document.getElementById('mailbox-form-panel');
    const listPanel = document.getElementById('mailbox-configs-panel');
    if (formPanel) formPanel.classList.toggle('hidden', show);
    if (listPanel) listPanel.classList.toggle('hidden', !show);
  }
  
  // ===== FORM HELPERS =====
  
  function getFormValues() {
    const getValue = (id, defaultValue = '') => {
      const el = document.getElementById(id);
      return el?.value?.trim() || defaultValue;
    };
    const getChecked = (id, defaultValue = false) => {
      const el = document.getElementById(id);
      return el?.checked !== undefined ? el.checked : defaultValue;
    };
    const getInt = (id, defaultValue = 0) => {
      const el = document.getElementById(id);
      return parseInt(el?.value, 10) || defaultValue;
    };
    
    const provider = getValue('mail-provider', 'custom');
    
    return {
      provider: provider,
      nombre: getValue('nombre', ''),
      email_address: getValue('mail-email', ''),
      // IMAP
      imap_host: getValue('mail-host', ''),
      imap_port: getInt('mail-port', 993),
      imap_ssl: getChecked('mail-ssl', true),
      imap_starttls: getChecked('mail-starttls', false),
      imap_username: getValue('mail-username', ''),
      imap_password: getValue('mail-password', ''),
      imap_mailbox: getValue('mail-mailbox', 'INBOX'),
      imap_mark_as_seen: getChecked('mail-mark-seen', true),
      imap_move_processed_to: getValue('mail-move-to', null),
      imap_max_attachment_mb: getInt('mail-max-mb', 50),
      // SMTP
      smtp_host: getValue('mail-smtp-host', ''),
      smtp_port: getInt('mail-smtp-port', 587),
      smtp_ssl: getChecked('mail-smtp-ssl', false),
      smtp_starttls: getChecked('mail-smtp-starttls', true),
      smtp_username: getValue('mail-smtp-username', ''),
      smtp_password: getValue('mail-smtp-password', ''),
      is_active: getChecked('is_active', true),
    };
  }
  
  function setFormValues(d = {}) {
    const setValue = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.value = value || '';
    };
    const setChecked = (id, checked) => {
      const el = document.getElementById(id);
      if (el) el.checked = !!checked;
    };
    
    setValue('config_id', d.id || '');
    setValue('mail-provider', d.provider || 'custom');
    setValue('nombre', d.nombre || d.alias || '');
    setValue('mail-email', d.email_address || '');
    
    // IMAP
    setValue('mail-host', d.imap_host || d.host || '');
    setValue('mail-port', d.imap_port || d.port || 993);
    setChecked('mail-ssl', d.imap_ssl !== undefined ? d.imap_ssl : (d.ssl !== undefined ? d.ssl : true));
    setChecked('mail-starttls', d.imap_starttls || false);
    setValue('mail-username', d.imap_username || d.username || '');
    setValue('mail-password', ''); // nunca mostrar password
    setValue('mail-mailbox', d.imap_mailbox || d.mailbox || 'INBOX');
    setChecked('mail-mark-seen', d.imap_mark_as_seen !== undefined ? d.imap_mark_as_seen : (d.mark_as_seen !== undefined ? d.mark_as_seen : true));
    setValue('mail-move-to', d.imap_move_processed_to || d.move_processed_to || '');
    setValue('mail-max-mb', d.imap_max_attachment_mb || d.max_attachment_mb || 50);
    
    // SMTP
    setValue('mail-smtp-host', d.smtp_host || '');
    setValue('mail-smtp-port', d.smtp_port || 587);
    setChecked('mail-smtp-ssl', d.smtp_ssl || false);
    setChecked('mail-smtp-starttls', d.smtp_starttls !== undefined ? d.smtp_starttls : true);
    setValue('mail-smtp-username', d.smtp_username || '');
    setValue('mail-smtp-password', ''); // nunca mostrar password
    
    setChecked('is_active', d.is_active !== false);
    
    // Disparar cambio de proveedor para autocompletar/bloquear
    setProviderPreset(d.provider || 'custom');
  }
  
  // ===== PRESET GMAIL =====
  
  function setProviderPreset(provider) {
    const setValue = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.value = value;
    };
    
    const setChecked = (id, checked) => {
      const el = document.getElementById(id);
      if (el) el.checked = checked;
    };
    
    const lock = (ids, lock) => {
      ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.readOnly = lock;
          el.disabled = lock;
          el.classList.toggle('bg-gray-100', lock);
        }
      });
    };
    
    const lockCheckbox = (id, lock) => {
      const el = document.getElementById(id);
      if (el) el.disabled = lock;
    };
    
    const gmailHelp = document.getElementById('gmail-help');
    
    if (provider === 'gmail') {
      // Autocompletar valores Gmail
      setValue('mail-host', 'imap.gmail.com');
      setValue('mail-port', '993');
      setChecked('mail-ssl', true);
      setChecked('mail-starttls', false);
      setValue('mail-smtp-host', 'smtp.gmail.com');
      setValue('mail-smtp-port', '587');
      setChecked('mail-smtp-ssl', false);
      setChecked('mail-smtp-starttls', true);
      
      // Bloquear campos
      lock(['mail-host', 'mail-port', 'mail-smtp-host', 'mail-smtp-port'], true);
      lockCheckbox('mail-ssl', true);
      lockCheckbox('mail-starttls', true);
      lockCheckbox('mail-smtp-ssl', true);
      lockCheckbox('mail-smtp-starttls', true);
      
      // Mostrar ayuda
      if (gmailHelp) gmailHelp.classList.remove('hidden');
    } else {
      // Desbloquear campos
      lock(['mail-host', 'mail-port', 'mail-smtp-host', 'mail-smtp-port'], false);
      lockCheckbox('mail-ssl', false);
      lockCheckbox('mail-starttls', false);
      lockCheckbox('mail-smtp-ssl', false);
      lockCheckbox('mail-smtp-starttls', false);
      
      // Ocultar ayuda
      if (gmailHelp) gmailHelp.classList.add('hidden');
    }
  }
  
  // ===== CRUD OPERATIONS =====
  
  async function loadConfigsList() {
    const tbody = document.querySelector('#tablaConfigs tbody') || document.querySelector('#tbl-mailbox-configs tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="8" class="py-2 text-center">Cargando…</td></tr>';
    
    try {
      const data = await apiGet(`${BASE_EMPRESA_API}/mailbox/configs/`);
      const items = Array.isArray(data) ? data : (Array.isArray(data.results) ? data.results : []);
      
      tbody.innerHTML = '';
      
      if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="py-2 text-center text-gray-500">No hay configuraciones guardadas</td></tr>';
        return;
      }
      
      items.forEach(cfg => {
        const tr = document.createElement('tr');
        tr.className = 'border-b hover:bg-gray-50';
        const provider = cfg.provider === 'gmail' ? 'Gmail' : 'Personalizado';
        const host = cfg.imap_host || cfg.host || '';
        const mailbox = cfg.imap_mailbox || cfg.mailbox || 'INBOX';
        tr.innerHTML = `
          <td class="py-1">${cfg.id}</td>
          <td class="py-1">${escapeHtml(cfg.nombre || cfg.alias || '')}</td>
          <td class="py-1">${escapeHtml(cfg.email_address || '')}</td>
          <td class="py-1">${escapeHtml(provider)}</td>
          <td class="py-1">${cfg.is_active ? 'Sí' : 'No'}</td>
          <td class="py-1">
            <button class="btn-xs text-indigo-600 hover:underline" data-action="view" data-id="${cfg.id}">Ver</button>
            <button class="btn-xs text-indigo-600 hover:underline" data-action="edit" data-id="${cfg.id}">Editar</button>
            <button class="btn-xs text-red-600 hover:underline" data-action="delete" data-id="${cfg.id}">Eliminar</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
      
      // Wire botones de acción
      tbody.querySelectorAll('button[data-action]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const action = btn.dataset.action;
          const id = btn.dataset.id;
          if (action === 'view' || action === 'edit') {
            loadConfigDetail(id);
          } else if (action === 'delete') {
            submitDelete(id);
          }
        });
      });
    } catch (err) {
      console.error('Error cargando configuraciones:', err);
      tbody.innerHTML = '<tr><td colspan="8" class="py-2 text-center text-red-500">Error al cargar configuraciones</td></tr>';
      showFeedback('feedback-mailbox-list', `Error: ${err.message}`, 'error');
    }
  }
  
  async function loadConfigDetail(id) {
    try {
      const d = await apiGet(`${BASE_EMPRESA_API}/mailbox/configs/${id}/`);
      setFormValues(d);
      const titleEl = document.getElementById('mailbox-form-title');
      if (titleEl) titleEl.textContent = `Editar configuración #${id}`;
      const btnSave = document.getElementById('btnGuardar');
      if (btnSave) btnSave.dataset.id = String(id);
      showList(false);
      showForm(true);
    } catch (err) {
      console.error('Error cargando detalle:', err);
      showFeedback('feedback-mailbox-form', `Error: ${err.message}`, 'error');
    }
  }
  
  function newConfigForm() {
    setFormValues({ provider: 'gmail' });
    const titleEl = document.getElementById('mailbox-form-title');
    if (titleEl) titleEl.textContent = 'Nueva configuración';
    const btnSave = document.getElementById('btnGuardar');
    if (btnSave) delete btnSave.dataset.id;
    showList(false);
    showForm(true);
  }
  
  async function submitCreate() {
    const payload = getFormValues();
    uiLockForm(true);
    hideFeedback('feedback-mailbox-form');
    
    try {
      // Validaciones
      if (!payload.nombre) {
        showFeedback('feedback-mailbox-form', 'El nombre (alias) es obligatorio.', 'error');
        uiLockForm(false);
        return;
      }
      
      if (payload.provider !== 'gmail' && !payload.imap_host) {
        showFeedback('feedback-mailbox-form', 'El host IMAP es obligatorio.', 'error');
        uiLockForm(false);
        return;
      }
      
      const username = payload.imap_username || (payload.provider === 'gmail' ? payload.email_address : '');
      if (!username) {
        showFeedback('feedback-mailbox-form', 'El usuario es obligatorio (o proporciona email principal para Gmail).', 'error');
        uiLockForm(false);
        return;
      }
      
      if (!payload.imap_password) {
        showFeedback('feedback-mailbox-form', 'La contraseña IMAP es obligatoria para crear una nueva configuración.', 'error');
        uiLockForm(false);
        return;
      }
      
      const resp = await apiPost(`${BASE_EMPRESA_API}/mailbox/configs/`, payload);
      showFeedback('feedback-mailbox-form', 'Configuración creada correctamente.', 'success');
      
      // Limpiar password
      const passwordEl = document.getElementById('mail-password');
      if (passwordEl) passwordEl.value = '';
      const smtpPasswordEl = document.getElementById('mail-smtp-password');
      if (smtpPasswordEl) smtpPasswordEl.value = '';
      
      await loadConfigsList();
      setTimeout(() => {
        showForm(false);
        showList(true);
      }, 1500);
    } catch (err) {
      console.error('Error creando configuración:', err);
      showFeedback('feedback-mailbox-form', `Error: ${err.message}`, 'error');
    } finally {
      uiLockForm(false);
    }
  }
  
  async function submitUpdate(id) {
    const payload = getFormValues();
    uiLockForm(true);
    hideFeedback('feedback-mailbox-form');
    
    try {
      // Validaciones
      if (!payload.nombre) {
        showFeedback('feedback-mailbox-form', 'El nombre (alias) es obligatorio.', 'error');
        uiLockForm(false);
        return;
      }
      
      if (payload.provider !== 'gmail' && !payload.imap_host) {
        showFeedback('feedback-mailbox-form', 'El host IMAP es obligatorio.', 'error');
        uiLockForm(false);
        return;
      }
      
      // Si no hay password, no enviarlo (para no sobrescribir)
      if (!payload.imap_password) {
        delete payload.imap_password;
      }
      if (!payload.smtp_password) {
        delete payload.smtp_password;
      }
      
      const resp = await apiPatch(`${BASE_EMPRESA_API}/mailbox/configs/${id}/`, payload);
      showFeedback('feedback-mailbox-form', 'Configuración actualizada correctamente.', 'success');
      
      // Limpiar password
      const passwordEl = document.getElementById('mail-password');
      if (passwordEl) passwordEl.value = '';
      const smtpPasswordEl = document.getElementById('mail-smtp-password');
      if (smtpPasswordEl) smtpPasswordEl.value = '';
      
      await loadConfigsList();
      setTimeout(() => {
        showForm(false);
        showList(true);
      }, 1500);
    } catch (err) {
      console.error('Error actualizando configuración:', err);
      showFeedback('feedback-mailbox-form', `Error: ${err.message}`, 'error');
    } finally {
      uiLockForm(false);
    }
  }
  
  async function submitDelete(id) {
    if (!confirm(`¿Eliminar configuración #${id}?`)) return;
    
    try {
      await apiDelete(`${BASE_EMPRESA_API}/mailbox/configs/${id}/`);
      showFeedback('feedback-mailbox-list', 'Configuración eliminada correctamente.', 'success');
      await loadConfigsList();
    } catch (err) {
      console.error('Error eliminando configuración:', err);
      showFeedback('feedback-mailbox-list', `Error: ${err.message}`, 'error');
    }
  }
  
  // ===== TEST CONNECTION =====
  
  async function testConnectionFromForm() {
    const p = getFormValues();
    hideFeedback('feedback-mail-config');
    showFeedback('feedback-mail-config', 'Probando conexión…', 'info');
    uiLockForm(true);
    
    try {
      // Validaciones
      if (p.provider !== 'gmail' && !p.imap_host) {
        showFeedback('feedback-mail-config', 'El host IMAP es obligatorio.', 'error');
        uiLockForm(false);
        return;
      }
      
      const username = p.imap_username || (p.provider === 'gmail' ? p.email_address : '');
      if (!username) {
        showFeedback('feedback-mail-config', 'El usuario es obligatorio (o proporciona email principal para Gmail).', 'error');
        uiLockForm(false);
        return;
      }
      
      if (!p.imap_password) {
        showFeedback('feedback-mail-config', 'La contraseña es obligatoria para probar la conexión.', 'error');
        uiLockForm(false);
        return;
      }
      
      const body = {
        provider: p.provider,
        email_address: p.email_address,
        host: p.provider === 'gmail' ? undefined : p.imap_host,
        port: p.provider === 'gmail' ? undefined : p.imap_port,
        protocol: 'imap',
        ssl: p.provider === 'gmail' ? undefined : p.imap_ssl,
        starttls: p.provider === 'gmail' ? undefined : p.imap_starttls,
        username: username,
        password: p.imap_password,
        mailbox: p.imap_mailbox || 'INBOX',
      };
      
      const resp = await apiPost(TEST_CONFIG_API, body);
      
      if (resp.ok) {
        const caps = resp.capabilities?.join(', ') || 'N/A';
        const banner = resp.banner ? `Banner: ${escapeHtml(resp.banner)}. ` : '';
        showFeedback('feedback-mail-config', `✓ Conexión exitosa. ${banner}Capabilities: ${caps}`, 'success');
      } else {
        let msg = resp.message || 'Error desconocido';
        const code = resp.code;
        
        if (code === 'AUTHENTICATIONFAILED') {
          msg = 'Credenciales inválidas. En Gmail activa IMAP y, si tienes 2FA, usa Contraseña de App (no tu contraseña normal).';
        } else if (code === 'IMAP_DISABLED') {
          msg = 'IMAP deshabilitado en Gmail. Actívalo en Settings → Forwarding and POP/IMAP → Enable IMAP.';
        } else if (code === 'TLS_ERROR') {
          msg = 'Fallo de conexión segura (IMAPS 993). Verifica puerto/SSL y firewall.';
        }
        
        showFeedback('feedback-mail-config', `✗ Error de conexión: ${escapeHtml(msg)}`, 'error');
      }
    } catch (err) {
      console.error('Error probando conexión:', err);
      const msg = err.message || 'Error desconocido';
      showFeedback('feedback-mail-config', `✗ Error: ${escapeHtml(msg)}`, 'error');
    } finally {
      uiLockForm(false);
    }
  }
  
  // ===== LISTENERS =====
  
  function attachListenersOnce() {
    // Botón "Nueva Configuración"
    const btnNew = document.getElementById('btn-mailbox-new');
    if (btnNew && !btnNew.dataset.listenerAttached) {
      btnNew.addEventListener('click', newConfigForm);
      btnNew.dataset.listenerAttached = 'true';
    }
    
    // Selector de proveedor
    const providerSel = document.getElementById('mail-provider');
    if (providerSel && !providerSel.dataset.listenerAttached) {
      providerSel.addEventListener('change', (e) => setProviderPreset(e.target.value));
      providerSel.dataset.listenerAttached = 'true';
    }
    
    // Botón "Probar conexión"
    const btnTest = document.getElementById('btn-test-mail-config');
    if (btnTest && !btnTest.dataset.listenerAttached) {
      btnTest.addEventListener('click', testConnectionFromForm);
      btnTest.dataset.listenerAttached = 'true';
    }
    
    // Botón "Guardar"
    const btnSave = document.getElementById('btnGuardar');
    if (btnSave && !btnSave.dataset.listenerAttached) {
      btnSave.addEventListener('click', async () => {
        const id = btnSave.dataset.id;
        if (id) {
          await submitUpdate(id);
        } else {
          await submitCreate();
        }
      });
      btnSave.dataset.listenerAttached = 'true';
    }
    
    // Botón "Cancelar"
    const btnCancel = document.getElementById('btn-mailbox-cancel');
    if (btnCancel && !btnCancel.dataset.listenerAttached) {
      btnCancel.addEventListener('click', () => {
        showForm(false);
        showList(true);
      });
      btnCancel.dataset.listenerAttached = 'true';
    }
    
    // Delegación para acciones de la tabla
    const tbody = document.querySelector('#tablaConfigs tbody') || document.querySelector('#tbl-mailbox-configs tbody');
    if (tbody && !tbody.dataset.listenerAttached) {
      tbody.addEventListener('click', (ev) => {
        const btn = ev.target.closest('button[data-action]');
        if (!btn) return;
        const id = btn.dataset.id;
        const act = btn.dataset.action;
        if (act === 'view' || act === 'edit') {
          loadConfigDetail(id);
        } else if (act === 'delete') {
          submitDelete(id);
        }
      });
      tbody.dataset.listenerAttached = 'true';
    }
  }
  
  // ===== INIT =====
  
  document.addEventListener('DOMContentLoaded', async () => {
    attachListenersOnce();
    await loadConfigsList();
  });
  
  // Exponer funciones globalmente para compatibilidad
  window.empresaMailbox = {
    loadConfigsList,
    loadConfigDetail,
    newConfigForm,
    submitCreate,
    submitUpdate,
    submitDelete,
    testConnectionFromForm,
    setProviderPreset,
  };
})();
