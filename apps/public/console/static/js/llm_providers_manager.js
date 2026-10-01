/**
 * Gestion del LLM Provider Hub (Fase 8,
 * PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md).
 *
 * Consume apps/public/console/api/views_llm_providers.py via window.http
 * (http.js -- inyecta CSRF/JWT automaticamente). Mismo patron API-First
 * que users_manager.js/tenants_manager.js: esta pagina solo renderiza,
 * cero logica de negocio en el cliente.
 *
 * SEGURIDAD: solo debe cargarse en el dominio publico (mismo hard-stop
 * que el resto de la consola).
 */
(function () {
  'use strict';

  const hostname = window.location.hostname;
  const isPublicHost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'sintel.net.co';
  if (!isPublicHost) {
    console.error('ERROR DE SEGURIDAD: LLM Providers Manager no debe cargarse en dominios de tenant.');
    throw new Error('LLM Providers Manager: Hard stop - cargado en dominio de tenant');
  }

  const API_BASE = '/api/admin/v1/console/llm/';

  // Fuente de verdad de que campos necesita cada tipo de conexion -- viene
  // SIEMPRE del backend (apps/public/console/api/llm_connection_schemas.py,
  // auditado contra los adapters reales). Este archivo NUNCA hardcodea
  // "si type===X entonces mostrar Y" con reglas propias -- solo lee esto.
  let connectionSchemas = {};

  const CAP_LABELS = [
    ['supports_tools', 'Tools'],
    ['supports_streaming', 'Streaming'],
    ['supports_structured_output', 'Structured output'],
    ['supports_vision', 'Vision'],
    ['supports_reasoning', 'Reasoning'],
  ];

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function showNotification(message, type) {
    const container = document.getElementById('messages-container');
    if (!container) return;
    const cls = {
      success: 'bg-green-50 text-green-800 border-green-400',
      error: 'bg-red-50 text-red-800 border-red-400',
      info: 'bg-blue-50 text-blue-800 border-blue-400',
    }[type || 'info'];
    const alert = document.createElement('div');
    alert.className = `rounded-lg p-4 shadow-sm border-l-4 ${cls}`;
    alert.innerHTML = `<p class="text-sm font-medium">${esc(message)}</p>`;
    container.appendChild(alert);
    setTimeout(() => alert.remove(), 6000);
  }

  // ============================================================
  // Modelo activo
  // ============================================================

  async function loadActive() {
    const el = document.getElementById('active-model-card');
    try {
      const data = await window.http.get(API_BASE + 'active/');
      const skippedNote = data.skipped_disabled
        ? `<p class="mt-2 text-xs text-amber-600">Nota: "${esc(data.skipped_disabled.model_identifier)}" (${esc(data.skipped_disabled.provider_name)}) fue la ultima activacion, pero esta deshabilitado -- el sistema lo salto automaticamente. Habilitalo de nuevo si quieres volver a usarlo.</p>`
        : '';
      if (!data.active) {
        el.innerHTML = `
          <div class="flex items-center gap-3">
            <span class="llm-cap-badge llm-badge-unverified">Fuente: .env</span>
            <span class="text-sm text-gray-600">Nadie ha activado un modelo habilitado desde la consola todavia -- el sistema usa <code>AI_PROVIDER</code> del entorno.</span>
          </div>${skippedNote}`;
        return;
      }
      const a = data.active;
      el.innerHTML = `
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="llm-cap-badge llm-badge-active">${esc(a.provider_name)}</span>
              <span class="text-lg font-semibold text-gray-900">${esc(a.model_identifier)}</span>
            </div>
            <p class="text-sm text-gray-500">
              Activado por ${esc(a.activated_by_email || 'desconocido')} el ${esc(new Date(a.activated_at).toLocaleString('es-CO'))}
              ${a.reason ? ' &middot; ' + esc(a.reason) : ''}
            </p>
          </div>
          <span class="llm-cap-badge llm-badge-verified">Fuente: consola (DB)</span>
        </div>${skippedNote}`;
    } catch (err) {
      el.innerHTML = `<div class="text-sm text-red-600">Error cargando modelo activo: ${esc(err.message)}</div>`;
    }
  }

  // ============================================================
  // Providers + modelos
  // ============================================================

  function capBadges(model) {
    return CAP_LABELS.map(([field, label]) => {
      const on = !!model[field];
      return `<span class="llm-cap-badge ${on ? 'llm-cap-on' : 'llm-cap-off'}">${label}</span>`;
    }).join('');
  }

  function healthBadge(model) {
    if (!model.last_health_check_at) return '<span class="llm-cap-badge llm-cap-off">sin probar</span>';
    const when = new Date(model.last_health_check_at).toLocaleString('es-CO');
    return model.last_health_reachable
      ? `<span class="llm-cap-badge llm-cap-on" title="Ultima comprobacion: ${esc(when)}">OK</span>`
      : `<span class="llm-cap-badge llm-badge-unverified" title="Ultima comprobacion: ${esc(when)}">Fallo</span>`;
  }

  function modelRow(provider, model) {
    const verifiedBadge = model.verified
      ? '<span class="llm-cap-badge llm-badge-verified">verificado</span>'
      : '<span class="llm-cap-badge llm-badge-unverified">sin verificar</span>';
    const enabledBadge = model.enabled
      ? '<span class="llm-cap-badge llm-cap-on">habilitado</span>'
      : '<span class="llm-cap-badge llm-cap-off">deshabilitado</span>';
    return `
      <tr data-model-id="${model.id}">
        <td class="px-4 py-3 text-sm font-mono text-gray-800">${esc(model.model_identifier)}</td>
        <td class="px-4 py-3">${enabledBadge}${verifiedBadge}</td>
        <td class="px-4 py-3">${healthBadge(model)}</td>
        <td class="px-4 py-3">${capBadges(model)}</td>
        <td class="px-4 py-3">
          <input type="number" min="1" class="input-fallback-priority w-16 rounded border-gray-300 text-xs py-1 px-2" data-model-id="${model.id}" value="${model.fallback_priority != null ? model.fallback_priority : ''}" placeholder="--" title="Prioridad de fallback -- menor numero = se prueba primero si el modelo activo falla. Vacio = no es candidato de fallback.">
        </td>
        <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
          <button class="btn-toggle-model text-xs text-gray-600 hover:text-gray-900 border border-gray-300 rounded px-2 py-1" data-model-id="${model.id}" data-enabled="${model.enabled}">${model.enabled ? 'Deshabilitar' : 'Habilitar'}</button>
          <button class="btn-verify-model text-xs text-indigo-600 hover:text-indigo-800" data-model-id="${model.id}">Verificar capacidades</button>
          <button class="btn-activate-model text-xs font-semibold text-white rounded px-2 py-1 ${model.enabled ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-gray-300 cursor-not-allowed'}" data-model-id="${model.id}" data-provider-id="${provider.id}" ${model.enabled ? '' : 'disabled title="Habilita el modelo primero"'}>Activar</button>
          <button class="btn-delete-model text-xs text-red-600 hover:text-red-800" data-model-id="${model.id}" data-model-name="${esc(model.model_identifier)}">Eliminar</button>
        </td>
      </tr>`;
  }

  function providerCard(provider) {
    const models = provider.models_config || [];
    const modelsHtml = models.length
      ? `<table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">Modelo</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">Estado</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">Salud</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">Capacidades</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">Fallback</th>
              <th class="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">${models.map((m) => modelRow(provider, m)).join('')}</tbody>
        </table>`
      : '<p class="px-4 py-3 text-sm text-gray-400">Sin modelos configurados todavia.</p>';

    const enabledBadge = provider.enabled
      ? '<span class="llm-cap-badge llm-cap-on">habilitado</span>'
      : '<span class="llm-cap-badge llm-cap-off">deshabilitado</span>';
    const localBadge = provider.is_local ? '<span class="llm-cap-badge llm-badge-active">local</span>' : '';

    const schema = connectionSchemas[provider.provider_type] || {};
    const typeLabel = schema.label || provider.provider_type;
    const detailParts = [typeLabel];
    if (schema.requires_base_url) detailParts.push(provider.base_url || 'sin base_url configurado');
    if (schema.requires_secret || schema.secret_optional) {
      detailParts.push(provider.secret_masked ? 'API key: ' + provider.secret_masked : 'sin API key configurada');
    }

    return `
      <div class="bg-white shadow-xl rounded-xl overflow-hidden border border-gray-200" data-provider-id="${provider.id}">
        <div class="px-6 py-4 bg-gradient-to-r from-gray-50 to-white border-b border-gray-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-base font-semibold text-gray-900">${esc(provider.name)}</h3>
              <span class="text-xs text-gray-400 font-mono">${esc(provider.slug)}</span>
              ${enabledBadge}${localBadge}
            </div>
            <p class="text-xs text-gray-500 mt-1">${esc(detailParts.join(' · '))}</p>
          </div>
          <div class="space-x-2">
            <button class="btn-toggle-provider text-xs text-gray-600 hover:text-gray-900 border border-gray-300 rounded px-2 py-1" data-provider-id="${provider.id}" data-enabled="${provider.enabled}">${provider.enabled ? 'Deshabilitar' : 'Habilitar'}</button>
            <button class="btn-add-model text-xs text-white bg-gray-700 hover:bg-gray-800 rounded px-2 py-1" data-provider-id="${provider.id}" data-provider-name="${esc(provider.name)}">+ Modelo</button>
            <button class="btn-test-provider text-xs text-gray-600 hover:text-gray-900 border border-gray-300 rounded px-2 py-1" data-provider-id="${provider.id}">Probar conexion</button>
            <button class="btn-edit-provider text-xs text-gray-600 hover:text-gray-900 border border-gray-300 rounded px-2 py-1" data-provider-id="${provider.id}">Editar</button>
            <button class="btn-delete-provider text-xs text-red-600 hover:text-red-800 border border-red-200 rounded px-2 py-1" data-provider-id="${provider.id}">Eliminar</button>
          </div>
        </div>
        <div class="overflow-x-auto">${modelsHtml}</div>
        <div class="px-6 py-2 text-xs text-gray-400 provider-test-result" data-provider-id="${provider.id}"></div>
      </div>`;
  }

  let providersCache = [];

  async function loadProviders() {
    const el = document.getElementById('providers-list');
    try {
      providersCache = await window.http.get(API_BASE + 'providers/');
      el.innerHTML = providersCache.length
        ? providersCache.map(providerCard).join('')
        : '<p class="text-sm text-gray-400">Sin providers configurados. Usa "Nuevo Provider" o corre <code>manage.py sync_llm_providers</code>.</p>';
    } catch (err) {
      el.innerHTML = `<div class="text-sm text-red-600">Error cargando providers: ${esc(err.message)}</div>`;
    }
  }

  // ============================================================
  // Auditoria
  // ============================================================

  async function loadAudit() {
    const tbody = document.getElementById('audit-log-body');
    try {
      const logs = await window.http.get(API_BASE + 'audit/');
      tbody.innerHTML = logs.length
        ? logs.map((a) => `
          <tr>
            <td class="px-4 py-2 text-gray-500 whitespace-nowrap">${esc(new Date(a.timestamp).toLocaleString('es-CO'))}</td>
            <td class="px-4 py-2 font-medium text-gray-800">${esc(a.action)}</td>
            <td class="px-4 py-2 text-gray-600">${esc(a.provider_slug || '-')}</td>
            <td class="px-4 py-2 text-gray-600">${esc(a.actor_email || '-')}</td>
            <td class="px-4 py-2">${a.result === 'OK' ? '<span class="llm-cap-badge llm-cap-on">OK</span>' : '<span class="llm-cap-badge llm-badge-unverified">' + esc(a.result) + '</span>'}</td>
            <td class="px-4 py-2 text-gray-500 font-mono text-xs">${esc(JSON.stringify(a.detail || {}))}</td>
          </tr>`).join('')
        : '<tr><td colspan="6" class="px-4 py-4 text-gray-400">Sin actividad registrada todavia.</td></tr>';
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" class="px-4 py-4 text-red-600">Error: ${esc(err.message)}</td></tr>`;
    }
  }

  // ============================================================
  // Acciones
  // ============================================================

  async function testProvider(providerId) {
    const resultEl = document.querySelector(`.provider-test-result[data-provider-id="${providerId}"]`);
    if (resultEl) resultEl.textContent = 'Probando conexion...';
    try {
      const res = await window.http.post(API_BASE + `providers/${providerId}/test/`, {});
      // Plan Seccion 29 (HEALTH): reachable+auth+HTTP resumidos en
      // "alcanzable"; model_available; tools/structured output (solo si ya
      // fueron verificados alguna vez, nunca adivinados); latencia; ultima
      // comprobacion.
      const parts = [res.reachable ? `Alcanzable (${Math.round(res.latency_ms)} ms)` : `No alcanzable: ${res.error || 'sin detalle'}`];
      if (res.model_available === false) parts.push('modelo no disponible en el servidor');
      if (res.capabilities_verified) {
        parts.push(`tools=${res.supports_tools ? 'si' : 'no'}`, `structured_output=${res.supports_structured_output ? 'si' : 'no'}`);
      }
      if (res.checked_at) parts.push('comprobado ' + new Date(res.checked_at).toLocaleString('es-CO'));
      const text = parts.join(' · ');
      const cls = 'px-6 py-2 text-xs provider-test-result ' + (res.reachable ? 'text-green-600' : 'text-red-600');

      // loadProviders() re-renderiza toda la tarjeta (incluido este div,
      // vacio de nuevo) -- se refresca PRIMERO (trae los badges de "Salud"
      // al dia) y el mensaje de esta prueba se re-inserta despues sobre el
      // nodo ya renderizado, para no perderlo.
      await loadProviders();
      const freshEl = document.querySelector(`.provider-test-result[data-provider-id="${providerId}"]`);
      if (freshEl) { freshEl.textContent = text; freshEl.className = cls; }
    } catch (err) {
      if (resultEl) resultEl.textContent = 'Error: ' + err.message;
      showNotification('No se pudo probar la conexion: ' + err.message, 'error');
    }
  }

  async function verifyModel(modelId) {
    try {
      await window.http.post(API_BASE + `models/${modelId}/verify/`, {});
      showNotification('Capacidades verificadas.', 'success');
      await loadProviders();
    } catch (err) {
      showNotification('No se pudo verificar el modelo: ' + err.message, 'error');
    }
  }

  async function activateModel(modelId) {
    const reason = window.prompt('Motivo de la activacion (opcional):', '');
    if (reason === null) return; // cancelado
    try {
      await window.http.post(API_BASE + `models/${modelId}/activate/`, { reason });
      showNotification('Modelo activado. El sistema lo usara en la siguiente llamada, sin reiniciar.', 'success');
      await Promise.all([loadActive(), loadAudit()]);
    } catch (err) {
      showNotification('No se pudo activar el modelo: ' + err.message, 'error');
    }
  }

  async function toggleModelEnabled(modelId, currentlyEnabled) {
    try {
      await window.http.patch(API_BASE + `models/${modelId}/`, { enabled: !currentlyEnabled });
      showNotification(currentlyEnabled ? 'Modelo deshabilitado.' : 'Modelo habilitado.', 'success');
      // Deshabilitar/habilitar un modelo puede cambiar lo que
      // resolve_active_llm() usa de verdad AHORA MISMO (ver
      // _load_active_provider_from_db(), filtra por enabled=True) -- la
      // tarjeta de "modelo en uso" tiene que refrescarse tambien, no solo
      // la lista de providers.
      await Promise.all([loadProviders(), loadActive()]);
    } catch (err) {
      showNotification('No se pudo cambiar el estado del modelo: ' + err.message, 'error');
    }
  }

  async function toggleProviderEnabled(providerId, currentlyEnabled) {
    try {
      await window.http.patch(API_BASE + `providers/${providerId}/`, { enabled: !currentlyEnabled });
      showNotification(currentlyEnabled ? 'Provider deshabilitado.' : 'Provider habilitado.', 'success');
      await Promise.all([loadProviders(), loadActive()]);
    } catch (err) {
      showNotification('No se pudo cambiar el estado del provider: ' + err.message, 'error');
    }
  }

  // Fase 10 (Fallback, plan Seccion 28): "definir una policy, no una
  // cadena hardcoded" -- fallback_priority es la UNICA perilla que el
  // usuario controla; resolve_fallback_llm() (backend) hace el resto.
  async function updateFallbackPriority(modelId, rawValue) {
    const value = rawValue.trim();
    const payload = { fallback_priority: value === '' ? null : Number(value) };
    try {
      await window.http.patch(API_BASE + `models/${modelId}/`, payload);
      showNotification(value === '' ? 'Modelo removido de la cadena de fallback.' : `Prioridad de fallback actualizada a ${value}.`, 'success');
    } catch (err) {
      showNotification('No se pudo actualizar la prioridad de fallback: ' + err.message, 'error');
      await loadProviders(); // revertir el input visualmente al valor real
    }
  }

  async function deleteProvider(providerId) {
    const provider = providersCache.find((p) => p.id === providerId);
    if (!window.confirm(`Eliminar el provider "${provider ? provider.name : providerId}"? Esta accion no se puede deshacer.`)) return;
    try {
      await window.http.delete(API_BASE + `providers/${providerId}/`);
      showNotification('Provider eliminado.', 'success');
      await loadProviders();
    } catch (err) {
      showNotification('No se pudo eliminar: ' + err.message, 'error');
    }
  }

  // ============================================================
  // Modal Nuevo/Editar Provider
  // ============================================================

  const modal = document.getElementById('provider-modal');
  const form = document.getElementById('provider-form');

  async function loadConnectionSchemas() {
    try {
      const data = await window.http.get(API_BASE + 'connection-schemas/');
      connectionSchemas = {};
      (data.schemas || []).forEach((s) => { connectionSchemas[s.provider_type] = s; });
      const select = document.getElementById('provider-type');
      select.innerHTML = (data.schemas || [])
        .map((s) => `<option value="${esc(s.provider_type)}">${esc(s.label)}</option>`)
        .join('');
    } catch (err) {
      showNotification('No se pudo cargar la lista de tipos de conexion: ' + err.message, 'error');
    }
  }

  // Aplica al formulario lo que el backend dice que ese tipo necesita --
  // muestra/oculta/renombra campos, nunca decide por su cuenta que campo
  // corresponde a que tipo (esa regla vive solo en connectionSchemas).
  function applyConnectionSchema(providerType, currentValues) {
    const schema = connectionSchemas[providerType] || {};
    const values = currentValues || {};

    const baseUrlWrapper = document.getElementById('provider-base-url-wrapper');
    const baseUrlInput = document.getElementById('provider-base-url');
    if (schema.requires_base_url) {
      baseUrlWrapper.classList.remove('hidden');
      baseUrlInput.required = true;
      baseUrlInput.disabled = false;
      document.getElementById('provider-base-url-label').innerHTML =
        (schema.base_url_label || 'Base URL') + ' <span class="text-red-500">*</span>';
      baseUrlInput.placeholder = schema.base_url_placeholder || '';
      baseUrlInput.value = values.base_url != null ? values.base_url : (schema.base_url_default || '');
    } else {
      baseUrlWrapper.classList.add('hidden');
      baseUrlInput.required = false;
      baseUrlInput.disabled = true;
      baseUrlInput.value = '';
    }

    const secretWrapper = document.getElementById('provider-secret-wrapper');
    const secretInput = document.getElementById('provider-secret');
    if (schema.requires_secret || schema.secret_optional) {
      secretWrapper.classList.remove('hidden');
      secretInput.disabled = false;
      const req = schema.requires_secret ? ' <span class="text-red-500">*</span>' : ' <span class="text-gray-400">(opcional)</span>';
      document.getElementById('provider-secret-label').innerHTML = (schema.secret_label || 'API Key / Secreto') + req;
    } else {
      secretWrapper.classList.add('hidden');
      secretInput.disabled = true;
      secretInput.value = '';
    }

    document.getElementById('provider-type-notes').textContent = schema.notes || '';
  }

  function openModal(provider) {
    form.reset();
    document.getElementById('provider-form-errors').classList.add('hidden');
    if (provider) {
      document.getElementById('provider-modal-title').textContent = 'Editar Provider';
      document.getElementById('provider-id').value = provider.id;
      document.getElementById('provider-name').value = provider.name;
      document.getElementById('provider-slug').value = provider.slug;
      document.getElementById('provider-type').value = provider.provider_type;
      document.getElementById('provider-is-local').checked = !!provider.is_local;
      document.getElementById('provider-enabled').checked = !!provider.enabled;
      applyConnectionSchema(provider.provider_type, { base_url: provider.base_url || '' });
      document.getElementById('provider-secret-hint').textContent = provider.secret_masked
        ? `Actual: ${provider.secret_masked}`
        : 'Sin secreto configurado.';
    } else {
      document.getElementById('provider-modal-title').textContent = 'Nuevo Provider';
      document.getElementById('provider-id').value = '';
      document.getElementById('provider-enabled').checked = true;
      document.getElementById('provider-secret-hint').textContent = '';
      const firstType = document.getElementById('provider-type').value;
      applyConnectionSchema(firstType, {});
    }
    modal.classList.remove('hidden');
  }

  function closeModal() {
    modal.classList.add('hidden');
  }

  async function submitProviderForm(ev) {
    ev.preventDefault();
    const id = document.getElementById('provider-id').value;
    const payload = {
      name: document.getElementById('provider-name').value.trim(),
      slug: document.getElementById('provider-slug').value.trim(),
      provider_type: document.getElementById('provider-type').value,
      base_url: document.getElementById('provider-base-url').value.trim(),
      is_local: document.getElementById('provider-is-local').checked,
      enabled: document.getElementById('provider-enabled').checked,
    };
    const secret = document.getElementById('provider-secret').value;
    if (secret) payload.secret = secret;

    const errorsEl = document.getElementById('provider-form-errors');
    errorsEl.classList.add('hidden');
    try {
      if (id) {
        await window.http.patch(API_BASE + `providers/${id}/`, payload);
      } else {
        await window.http.post(API_BASE + 'providers/', payload);
      }
      showNotification('Provider guardado.', 'success');
      closeModal();
      await loadProviders();
    } catch (err) {
      errorsEl.textContent = err.message;
      errorsEl.classList.remove('hidden');
    }
  }

  // ============================================================
  // Modal Nuevo Modelo
  // ============================================================

  const modelModal = document.getElementById('model-modal');
  const modelForm = document.getElementById('model-form');

  function openModelModal(providerId, providerName) {
    modelForm.reset();
    document.getElementById('model-form-errors').classList.add('hidden');
    document.getElementById('model-provider-id').value = providerId;
    document.getElementById('model-enabled').checked = true;
    document.getElementById('model-modal-provider-label').textContent = `Provider: ${providerName}`;

    const provider = providersCache.find((p) => String(p.id) === String(providerId));
    const schema = provider ? (connectionSchemas[provider.provider_type] || {}) : {};
    const discoverySection = document.getElementById('model-discovery-section');
    const discoverySelect = document.getElementById('model-discovery-select');
    discoverySelect.innerHTML = '<option value="">-- Elegir de la lista detectada --</option>';
    document.getElementById('model-discovery-status').textContent = '';

    if (schema.supports_model_discovery) {
      discoverySection.classList.remove('hidden');
      document.getElementById('model-identifier-hint').textContent =
        'Tambien puedes escribirlo a mano si prefieres.';
    } else {
      discoverySection.classList.add('hidden');
      document.getElementById('model-identifier-hint').textContent =
        `Este tipo de conexion no expone descubrimiento automatico de modelos -- escribe el identificador exacto que espera el proveedor.`;
    }
    modelModal.classList.remove('hidden');
  }

  function closeModelModal() {
    modelModal.classList.add('hidden');
  }

  async function discoverModels() {
    const providerId = document.getElementById('model-provider-id').value;
    const statusEl = document.getElementById('model-discovery-status');
    const select = document.getElementById('model-discovery-select');
    statusEl.textContent = 'Consultando el servidor...';
    try {
      const res = await window.http.post(API_BASE + `providers/${providerId}/discover-models/`, {});
      if (!res.supported) {
        statusEl.textContent = res.reason || 'Este provider no soporta descubrimiento.';
        return;
      }
      if (res.error) {
        statusEl.textContent = 'Error: ' + res.error;
        return;
      }
      select.innerHTML = '<option value="">-- Elegir de la lista detectada --</option>' +
        (res.models || []).map((m) => `<option value="${esc(m.model_id)}">${esc(m.model_id)}${m.context_window ? ' (' + m.context_window + ' tokens ctx)' : ''}</option>`).join('');
      statusEl.textContent = res.models && res.models.length
        ? `${res.models.length} modelo(s) detectado(s) en el servidor.`
        : 'El servidor no reporto ningun modelo instalado.';
    } catch (err) {
      statusEl.textContent = 'Error: ' + err.message;
    }
  }

  async function submitModelForm(ev) {
    ev.preventDefault();
    const providerId = document.getElementById('model-provider-id').value;
    const payload = {
      model_identifier: document.getElementById('model-identifier').value.trim(),
      display_name: document.getElementById('model-display-name').value.trim(),
      enabled: document.getElementById('model-enabled').checked,
    };
    const errorsEl = document.getElementById('model-form-errors');
    errorsEl.classList.add('hidden');
    try {
      await window.http.post(API_BASE + `providers/${providerId}/models/`, payload);
      showNotification('Modelo agregado.', 'success');
      closeModelModal();
      await loadProviders();
    } catch (err) {
      errorsEl.textContent = err.message;
      errorsEl.classList.remove('hidden');
    }
  }

  async function deleteModel(modelId, modelName) {
    if (!window.confirm(`Eliminar el modelo "${modelName}"?`)) return;
    try {
      await window.http.delete(API_BASE + `models/${modelId}/`);
      showNotification('Modelo eliminado.', 'success');
      await loadProviders();
    } catch (err) {
      showNotification('No se pudo eliminar el modelo: ' + err.message, 'error');
    }
  }

  // ============================================================
  // Wiring de eventos (delegacion, la lista se re-renderiza)
  // ============================================================

  document.addEventListener('DOMContentLoaded', async () => {
    await loadConnectionSchemas();
    loadActive();
    loadProviders();
    loadAudit();

    document.getElementById('provider-type').addEventListener('change', (ev) => {
      applyConnectionSchema(ev.target.value, {});
    });

    document.getElementById('btn-new-provider').addEventListener('click', () => openModal(null));
    document.getElementById('provider-modal-close').addEventListener('click', closeModal);
    document.getElementById('provider-btn-cancel').addEventListener('click', closeModal);
    document.getElementById('provider-modal-backdrop').addEventListener('click', closeModal);
    form.addEventListener('submit', submitProviderForm);
    document.getElementById('btn-refresh-audit').addEventListener('click', loadAudit);

    document.getElementById('model-modal-close').addEventListener('click', closeModelModal);
    document.getElementById('model-btn-cancel').addEventListener('click', closeModelModal);
    document.getElementById('model-modal-backdrop').addEventListener('click', closeModelModal);
    modelForm.addEventListener('submit', submitModelForm);
    document.getElementById('btn-discover-models').addEventListener('click', discoverModels);
    document.getElementById('model-discovery-select').addEventListener('change', (ev) => {
      if (ev.target.value) {
        document.getElementById('model-identifier').value = ev.target.value;
      }
    });

    document.getElementById('providers-list').addEventListener('click', (ev) => {
      const testBtn = ev.target.closest('.btn-test-provider');
      if (testBtn) return testProvider(testBtn.dataset.providerId);

      const verifyBtn = ev.target.closest('.btn-verify-model');
      if (verifyBtn) return verifyModel(verifyBtn.dataset.modelId);

      const activateBtn = ev.target.closest('.btn-activate-model');
      if (activateBtn) return activateModel(activateBtn.dataset.modelId);

      const toggleModelBtn = ev.target.closest('.btn-toggle-model');
      if (toggleModelBtn) return toggleModelEnabled(toggleModelBtn.dataset.modelId, toggleModelBtn.dataset.enabled === 'true');

      const deleteModelBtn = ev.target.closest('.btn-delete-model');
      if (deleteModelBtn) return deleteModel(deleteModelBtn.dataset.modelId, deleteModelBtn.dataset.modelName);

      const addModelBtn = ev.target.closest('.btn-add-model');
      if (addModelBtn) return openModelModal(addModelBtn.dataset.providerId, addModelBtn.dataset.providerName);

      const toggleProviderBtn = ev.target.closest('.btn-toggle-provider');
      if (toggleProviderBtn) return toggleProviderEnabled(Number(toggleProviderBtn.dataset.providerId), toggleProviderBtn.dataset.enabled === 'true');

      const editBtn = ev.target.closest('.btn-edit-provider');
      if (editBtn) {
        const provider = providersCache.find((p) => String(p.id) === editBtn.dataset.providerId);
        if (provider) openModal(provider);
        return;
      }

      const deleteBtn = ev.target.closest('.btn-delete-provider');
      if (deleteBtn) return deleteProvider(Number(deleteBtn.dataset.providerId));
    });

    document.getElementById('providers-list').addEventListener('change', (ev) => {
      const fallbackInput = ev.target.closest('.input-fallback-priority');
      if (fallbackInput) return updateFallbackPriority(fallbackInput.dataset.modelId, fallbackInput.value);
    });
  });
})();
