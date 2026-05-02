/**
 * Página JavaScript para el workspace de Facturas.
 * 
 * Consolidado desde:
 * - apps/tenant/core/templates/tenant/core/workspace.html (JS inline)
 * - apps/tenant/landing/static/tenant/landing/workspace/facturas.js
 * 
 * Funcionalidades:
 * - Upload de archivos XML UBL
 * - Visualización de lista de facturas
 * - Ver detalle de factura
 * - Eliminar factura (rollback de error de carga)
 * - Búsqueda y filtrado
 * - Manejo de errores minimalista
 */

// ⚠️ Inicialización del módulo Facturas
let initialized = false;

function initFacturasModule() {
  if (initialized) return; // Evitar inicialización múltiple
  
  const $table = document.querySelector('#tbl-facturas');
  const $modalImport = document.getElementById('import-modal');
  if (!$table || !$modalImport) return; // no es la página de facturas, salir

  initialized = true;

  // Exposición opcional global (si tu código existente lo usa)
  if (!window.loadTabla) window.loadTabla = loadTabla;
  if (!window.importarUblDesdeInput) window.importarUblDesdeInput = importarUblDesdeInput;
  // Helpers de feedback
  if (!window.showErrorLocal) window.showErrorLocal = showErrorLocal;
  if (!window.showWarnLocal) window.showWarnLocal = showWarnLocal;
  if (!window.showInfoLocal) window.showInfoLocal = showInfoLocal;
  if (!window.showSuccessLocal) window.showSuccessLocal = showSuccessLocal;
  if (!window.showToast) window.showToast = showToast;
  if (!window.hideLocal) window.hideLocal = hideLocal;

  // Init UI
  bindToolbar();
  bindTable();
  
  // Primera carga (solo si la sección es visible)
  const viewFacturas = document.getElementById('view-facturas');
  if (viewFacturas && !viewFacturas.hasAttribute('hidden')) {
    loadTabla().catch(console.error);
  }
  
  // Suscribirse a evento global de "refrescar facturas" después de import
  // (evitar duplicar listeners)
  document.addEventListener('facturas:refresh', () => {
    loadTabla().catch(console.error);
  }, { once: false });
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
  initFacturasModule();
  
  // También inicializar cuando la sección se muestre (MutationObserver o evento)
  const viewFacturas = document.getElementById('view-facturas');
  if (viewFacturas) {
    // Observer para detectar cuando se muestra la sección
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'hidden') {
          if (!viewFacturas.hasAttribute('hidden')) {
            // Sección visible: inicializar si no está inicializado
            if (!initialized) {
              initFacturasModule();
            }
            // Cargar datos si la tabla está vacía
            const tbody = document.querySelector('#tbl-facturas tbody');
            if (tbody && !tbody.querySelector('tr')) {
              loadTabla().catch(console.error);
            }
          }
        }
      });
    });
    
    observer.observe(viewFacturas, { attributes: true, attributeFilter: ['hidden'] });
    
    // Si ya está visible al cargar, inicializar inmediatamente
    if (!viewFacturas.hasAttribute('hidden')) {
      initFacturasModule();
    }
  }
});

/* ====== Helpers mínimos ====== */
function cacheBuster(url) {
  const u = new URL(url, window.location.origin);
  u.searchParams.set('_', Date.now());
  return u.toString();
}

async function jsonFetch(url, opts={}) {
  const res = await fetch(cacheBuster(url), { cache:'no-store', ...opts });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function getCsrf() {
  const m = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[2]) : '';
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function fmtMoney(v, cur='COP') {
  try { 
    return new Intl.NumberFormat('es-CO', {style:'currency', currency:cur}).format(Number(v || 0)); 
  } catch { 
    return Number(v || 0).toFixed(2); 
  }
}

/* ====== Helpers de ALERTA en modales ====== */
function setAlert(el, type, html) {
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.innerHTML = html;
  el.classList.remove('d-none');
}

function clearAlert(el) {
  if (!el) return;
  el.className = 'alert d-none';
  el.innerHTML = '';
}

function showErrorLocal(modalFeedbackId, code, message) {
  const el = document.getElementById(modalFeedbackId);
  const safeMsg = message || 'Se produjo un error.';
  const safeCode = code ? `<div class="small text-muted mt-1">${escapeHtml(code)}</div>` : '';
  setAlert(el, 'danger', `<strong>⚠️ ${escapeHtml(safeMsg)}</strong>${safeCode}`);
}

function showWarnLocal(modalFeedbackId, message) {
  const el = document.getElementById(modalFeedbackId);
  setAlert(el, 'warning', `<strong>⚠️ ${escapeHtml(message || 'Revisa los datos.')}</strong>`);
}

function showInfoLocal(modalFeedbackId, message) {
  const el = document.getElementById(modalFeedbackId);
  setAlert(el, 'info', escapeHtml(message || 'Información relevante.'));
}

function showSuccessLocal(modalFeedbackId, message) {
  const el = document.getElementById(modalFeedbackId);
  setAlert(el, 'success', `<strong>✔ ${escapeHtml(message || 'Operación exitosa.')}</strong>`);
}

function hideLocal(modalFeedbackId) {
  clearAlert(document.getElementById(modalFeedbackId));
}

/* ====== Helper de TOAST global ====== */
function showToast(message, theme = 'dark') {
  const toastEl = document.getElementById('toast-feedback');
  const body = document.getElementById('toast-body');
  if (!toastEl || !body) return;
  body.textContent = message || 'Operación completada.';
  // Mapear temas: success -> success, danger -> danger, warning -> warning, info -> info, dark -> dark
  const themeMap = {
    'success': 'success',
    'danger': 'danger',
    'warning': 'warning',
    'info': 'info',
    'dark': 'dark'
  };
  const bsTheme = themeMap[theme] || 'dark';
  toastEl.className = `toast align-items-center text-bg-${bsTheme} border-0`;
  if (window.bootstrap && bootstrap.Toast) {
    const toastInstance = new bootstrap.Toast(toastEl, { delay: 3000, autohide: true });
    toastInstance.show();
  }
}

/* ====== Helper legacy (mantener compatibilidad) ====== */
function showError(code, message) {
  const m = document.getElementById('import-error-modal');
  if (!m) return alert(`${code}: ${message}`);
  const titleEl = m.querySelector('.modal-title');
  const bodyEl = m.querySelector('.modal-body');
  if (titleEl) titleEl.textContent = '⚠️ Error';
  if (bodyEl) {
    bodyEl.innerHTML = `<p class="mb-0">${escapeHtml(message)}</p><div class="text-muted small mt-1">${escapeHtml(code)}</div>`;
  }
  if (window.bootstrap && bootstrap.Modal) {
    new bootstrap.Modal(m).show();
  } else {
    m.style.display = 'block';
    m.classList.add('show');
  }
}

/* ====== Acciones ====== */
async function loadTabla(params={}) {
  try {
    const base = '/api/v1/facturas/';
    const defaultParams = { ordering: '-fecha_emision', page: 1, page_size: 50 }; // Aumentado a 50 para ver más registros
    const apiParams = { ...defaultParams };
    
    // Mapear 'q' a 'search' para DRF SearchFilter (solo si hay valor)
    if (params.q && params.q.trim()) {
      apiParams.search = params.q.trim();
    }
    
    // Copiar otros parámetros (excluyendo 'q' que ya fue mapeado)
    const { q, ...otherParams } = params;
    Object.assign(apiParams, otherParams);
    
    const qs = new URLSearchParams(apiParams);
    qs.set('_', Date.now()); // cache-buster
    
    const url = `${base}?${qs.toString()}`;
    
    console.debug('[facturas] Cargando facturas desde:', url);
    
    const res = await fetch(url, {
      credentials: 'same-origin',  // ⚠️ CRÍTICO: Necesario para SessionAuthentication
      headers: { 'Accept': 'application/json' },
      cache: 'no-store'
    });
    
    if (!res.ok) {
      // Manejar 401 de forma inteligente (no crítico, mostrar error local)
      if (res.status === 401) {
        const tbody = document.querySelector('#tbl-facturas tbody');
        if (tbody) {
          tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">Sesión expirada. Por favor, recarga la página.</td></tr>';
        }
        showError('auth_error', 'Tu sesión ha expirado. Por favor, recarga la página.');
        return;
      }
      const errorText = await res.text().catch(() => '');
      console.error('[facturas] Error HTTP:', res.status, errorText);
      throw new Error(`No se pudo obtener facturas: ${res.status} ${errorText.substring(0, 100)}`);
    }
    
    const data = await res.json();
    console.debug('[facturas] Respuesta API:', { count: data.count, results: data.results?.length || 0, hasNext: !!data.next });
    
    const items = data.results || data;
    
    const tbody = document.querySelector('#tbl-facturas tbody');
    if (!tbody) {
      console.warn('[facturas] tbody de #tbl-facturas no encontrado');
      return;
    }
    
    // Limpiar tabla
    tbody.innerHTML = '';
    
    // Si no hay items, mostrar mensaje
    if (!items || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">No hay facturas registradas.</td></tr>';
      console.info('[facturas] No hay facturas para mostrar');
      return;
    }
    
    // Renderizar filas
    console.debug('[facturas] Renderizando', items.length, 'facturas');
    items.forEach(row => renderRow(row));
  } catch (error) {
    console.error('[facturas] Error al cargar facturas:', error);
    const tbody = document.querySelector('#tbl-facturas tbody');
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">Error al cargar: ${escapeHtml(error.message || 'Error desconocido')}</td></tr>`;
    }
    showError('load_error', `No se pudo cargar la lista de facturas: ${error.message || 'Error desconocido'}`);
  }
}

async function importarUblDesdeInput({ inputFileEl, inputTextEl, preview=false }) {
  // ⚠️ IMPORTANTE: La naturaleza se calcula automáticamente en el backend (Service Layer)
  // No enviar naturaleza desde el cliente; el backend la determina comparando emisor_nit vs empresa_nit
  
  // Determinar si es archivo o texto
  const f = inputFileEl?.files?.[0];
  const xmlText = inputTextEl?.value?.trim();
  
  let url, body, headers;
  
  // ⚠️ URL relativa (sin protocolo/host) con trailing slash
  const baseUrl = '/api/v1/core/documentos/upload/';  // ⚠️ v2.36: Endpoint universal
  
  if (f) {
    // Importar desde archivo
    const fd = new FormData();
    fd.append('file', f);
    // ⚠️ NO enviar naturaleza; se calcula en el backend
    
    url = baseUrl + (preview ? '?preview=true' : '');
    body = fd;
    headers = { 'X-CSRFToken': getCsrf(), 'Accept': 'application/json' };
  } else if (xmlText) {
    // Importar desde texto XML
    url = baseUrl + (preview ? '?preview=true' : '');
    body = JSON.stringify({ xml: xmlText });
    headers = { 
      'X-CSRFToken': getCsrf(), 
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };
  } else {
    throw new Error('Selecciona un archivo XML o pega el contenido XML');
  }
  
  const res = await fetch(url, {
    method: 'POST',
    headers,
    body,
    credentials: 'same-origin',
    cache: 'no-store'
  });
  
  let payload = null;
  try { 
    payload = await res.json(); 
  } catch {
    // Non-JSON fallback
    payload = null;
  }
  
  if (!res.ok) {
    const code = payload?.error || 'unknown';
    const message = payload?.message || `Error (${res.status})`;
    
    // Manejo específico de errores según código HTTP
    if (res.status === 422) {
      // Error 422: Empresa no configurada (SSoT faltante)
      if (code === 'empresa_no_configurada') {
        throw new Error(`⚠️ ${message}\n\nPor favor, configura la Empresa del tenant con su NIT antes de importar facturas.`);
      }
    }
    
    // Lanzar error para que el handler del botón lo capture y muestre en feedback local
    throw new Error(message);
  }
  
  // Si es preview, retornar el DTO sin persistir
  if (preview && payload) {
    return payload;
  }
  
  // Si es persistencia, upsert en vivo si viene objeto persistido
  if (payload && payload.id) {
    upsertRow(payload);
  } else if (payload && payload.factura && payload.factura.id) {
    // Si viene en formato {preview: false, factura: {...}}, usar factura
    upsertRow(payload.factura);
  } else {
    // Por si acaso, recargar tabla completa
    await loadTabla();
  }
  
  return payload;
}

/* ====== Wiring ====== */
function bindToolbar() {
  const btnBuscar = document.getElementById('btn-buscar');
  const txtBuscar = document.getElementById('txt-buscar');
  const btnRefrescar = document.getElementById('btn-refrescar');
  const btnConfirmImport = document.getElementById('btn-confirm-import');
  const inputFile = document.getElementById('input-ubl-file');

  btnBuscar?.addEventListener('click', () => {
    const q = (txtBuscar?.value || '').trim();
    // Solo pasar 'q' si hay texto, de lo contrario recargar sin filtro
    if (q) {
      loadTabla({ q });
    } else {
      loadTabla(); // Recargar sin filtro de búsqueda
    }
  });
  
  txtBuscar?.addEventListener('keypress', e => { 
    if (e.key === 'Enter') {
      e.preventDefault(); // Evitar submit si está dentro de un form
      btnBuscar?.click(); 
    }
  });
  
  btnRefrescar?.addEventListener('click', () => loadTabla());
  
  btnConfirmImport?.addEventListener('click', async (ev) => {
    const modal = document.getElementById('import-modal');
    const fbId = 'feedback-import';
    const inputText = document.getElementById('input-ubl-text');
    hideLocal(fbId);

    // ⚠️ FASE 3: Prevenir doble submit
    disableWhileRunning(btnConfirmImport, true);

    try {
      // Validación mínima antes de enviar
      const hasFile = inputFile?.files?.length > 0;
      const hasText = inputText?.value?.trim();
      
      if (!hasFile && !hasText) {
        showWarnLocal(fbId, 'Selecciona un archivo XML o pega el contenido XML antes de importar.');
        disableWhileRunning(btnConfirmImport, false);
        return;
      }

      // ⚠️ FASE 3: Usar flujo async (upload → polling → materialización)
      let fileOrBlob = null;
      
      if (hasFile) {
        fileOrBlob = inputFile.files[0];
      } else if (hasText) {
        // Convertir texto XML a Blob
        fileOrBlob = new Blob([inputText.value.trim()], { type: 'application/xml' });
      }

      // Subir async y esperar materialización
      await subirUblAsync(fileOrBlob);

      // Éxito: feedback local + toast + cierre del modal
      showSuccessLocal(fbId, 'Factura importada y materializada correctamente.');
      showToast('Factura importada', 'success');
      
      // Emitir evento global para refrescar tabla (evitar duplicar listeners)
      document.dispatchEvent(new CustomEvent('facturas:refresh'));
      
      // Cerrar modal después de un breve delay para que el usuario vea el mensaje de éxito
      setTimeout(() => {
        if (window.bootstrap && bootstrap.Modal) {
          const modalInstance = bootstrap.Modal.getInstance(modal);
          if (modalInstance) modalInstance.hide();
        }
        if (inputFile) inputFile.value = '';
        if (inputText) inputText.value = '';
        hideLocal(fbId);
      }, 1500);
    } catch (e) {
      // El fetch ya devuelve {error,message}; muéstralo de forma clara
      const errorMsg = (e && e.message) ? e.message : 'Error al importar UBL.';
      // Extraer código de error si está disponible
      let errorCode = 'unknown';
      if (errorMsg.includes('missing_xml') || errorMsg.includes('Falta archivo')) {
        errorCode = 'missing_xml';
      } else if (errorMsg.includes('duplicate') || errorMsg.includes('ya existe')) {
        errorCode = 'duplicate';
      } else if (errorMsg.includes('dto_parse_error') || errorMsg.includes('parsear')) {
        errorCode = 'dto_parse_error';
      } else if (errorMsg.includes('empresa_no_configurada') || errorMsg.includes('Empresa no configurada')) {
        errorCode = 'empresa_no_configurada';
      } else if (errorMsg.includes('empresa_error')) {
        errorCode = 'empresa_error';
      } else if (errorMsg.includes('Tiempo de espera agotado')) {
        errorCode = 'timeout';
      } else if (errorMsg.includes('Materialización falló')) {
        errorCode = 'materialization_failed';
      }
      
      showErrorLocal(fbId, errorCode, errorMsg);
      // Toast opcional para errores críticos
      if (errorCode === 'duplicate') {
        showToast('La factura ya existe', 'warning');
      } else if (errorCode === 'empresa_no_configurada') {
        showToast('Configura la Empresa del tenant primero', 'danger');
      } else if (errorCode === 'timeout') {
        showToast('Tiempo de espera agotado. La tarea puede estar procesándose en segundo plano.', 'warning');
      } else {
        showToast('Error al importar', 'danger');
      }
    } finally {
      // ⚠️ FASE 3: Rehabilitar botón
      disableWhileRunning(btnConfirmImport, false);
    }
  }, { once: false }); // Permitir múltiples clicks (después de completar)
}

// ⚠️ FASE 3: Helper para deshabilitar botones mientras corre operación
function disableWhileRunning(el, running = true) {
  if (!el) return;
  el.disabled = running;
  el.classList.toggle('disabled', running);
}

// ⚠️ REVERSIÓN: Flujo de dos pasos (parseo → persistencia)
// Paso 1: Parsear con endpoint universal (preview=true)
// Paso 2: Persistir con endpoint de la app
async function subirUblAsync(fileOrBlob) {
  const form = new FormData();
  form.append('file', fileOrBlob);
  
  // Paso 1: Parsear con endpoint universal (NO persiste)
  const parseUrl = `/api/v1/core/documentos/upload/?preview=true`;  // ⚠️ v2.36: Endpoint universal
  
  const parseRes = await fetch(parseUrl, {
    method: 'POST',
    body: form,
    credentials: 'same-origin',
    headers: {
      'X-CSRFToken': getCsrf() || '',
    },
  });
  
  if (!parseRes.ok) {
    const data = await parseRes.json().catch(() => ({}));
    throw new Error(data.message || `Error al parsear XML (${parseRes.status})`);
  }
  
  const parseData = await parseRes.json();
  const dto = parseData.dto || parseData;
  
  if (!dto) {
    throw new Error('El endpoint no devolvió un DTO válido');
  }
  
  // Paso 2: Persistir con endpoint de la app
  const persistUrl = `/api/v1/facturas/create-from-dto/`;
  
  const persistRes = await fetch(persistUrl, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrf() || '',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      dto: dto,
      persist_anexos: true
    }),
  });
  
  if (!persistRes.ok) {
    const data = await persistRes.json().catch(() => ({}));
    
    if (persistRes.status === 409) {
      throw new Error(data.message || 'Documento duplicado. Ya existe una factura con el mismo CUFE.');
    } else if (persistRes.status === 422) {
      throw new Error(data.message || 'Error de validación. Verifique que el documento sea válido.');
    } else {
      throw new Error(data.message || `Error al persistir (${persistRes.status})`);
    }
  }
  
  const persistedData = await persistRes.json();
  
  // Actualizar tabla con el resultado
  if (persistedData.id) {
    upsertRow(persistedData);
  } else {
    await loadTabla();
  }
  
  return persistedData;
}

// ⚠️ REVERSIÓN: Esta función ya no es necesaria
// El flujo ahora es directo: parseo → persistencia (sin polling)
// Se mantiene por compatibilidad pero no se usa
async function pollYMaterializa(taskId, { intervalMs = 2000, maxAttempts = 90 } = {}) {
  // ⚠️ DEPRECADO: Ya no se usa polling, el flujo es directo
  throw new Error('Esta función está deprecada. Use subirUblAsync() que maneja parseo y persistencia directamente.');
}

// ⚠️ FASE 3: Eliminar factura (rollback de error de carga)
async function eliminarFactura(id) {
  const url = `/api/v1/facturas/${id}/`;
  
  try {
    const res = await fetch(url, {
      method: 'DELETE',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': getCsrf() || '',
        'Accept': 'application/json',
      },
    });
    
    if (res.status === 204) {
      // Éxito: eliminar fila de la tabla
      removeRow(id);
      showToast('Factura eliminada', 'success');
      // Disparar evento para refrescar si es necesario
      document.dispatchEvent(new CustomEvent('facturas:refresh'));
      return;
    }
    
    // Manejar errores específicos
    const data = await res.json().catch(() => ({}));
    const code = data.error || 'unknown';
    const message = data.message || `Error (${res.status})`;
    
    if (res.status === 404) {
      showToast('Factura no encontrada', 'warning');
      removeRow(id); // Eliminar de la tabla si no existe
    } else if (res.status === 409) {
      showToast(message || 'La factura tiene relaciones protegidas y no puede ser eliminada', 'danger');
    } else if (res.status === 422) {
      showToast(message || 'No se puede eliminar esta factura (puede estar contabilizada)', 'danger');
    } else {
      showToast(message || `Error al eliminar factura (${res.status})`, 'danger');
    }
  } catch (error) {
    console.error('Error al eliminar factura:', error);
    showToast('Error de conexión al eliminar factura', 'danger');
  }
}

function bindTable() {
  const tbl = document.getElementById('tbl-facturas');
  if (!tbl) return;
  
  // ⚠️ FASE 3: Event delegation para eliminar factura
  // ⚠️ FASE 4: Event delegation para ver factura (modal con anexos)
  // ⚠️ FASE 8: Event delegation para ver nota crédito
  const tbody = tbl.querySelector('tbody');
  if (tbody) {
    tbody.addEventListener('click', async (ev) => {
      // Manejar enlace "Aplicar NC" (Nueva funcionalidad)
      const linkAplicarNc = ev.target.closest('.link-aplicar-nc');
      if (linkAplicarNc) {
        ev.preventDefault();
        const facturaId = linkAplicarNc.getAttribute('data-factura-id');
        const facturaNumero = linkAplicarNc.getAttribute('data-factura-numero');
        const facturaCufe = linkAplicarNc.getAttribute('data-factura-cufe');
        if (facturaId) {
          abrirModalAplicarNC({
            id: facturaId,
            numero: facturaNumero,
            cufe: facturaCufe
          });
        }
        return;
      }
      
      // Manejar enlace "NC" (Fase 8) - Ver NC existente
      const linkNc = ev.target.closest('.link-nc');
      if (linkNc) {
        ev.preventDefault();
        const ncId = linkNc.getAttribute('data-nc-id');
        if (ncId) {
          await abrirModalNotaCredito(ncId).catch(console.error);
        }
        return;
      }
      
      // Manejar botón "Ver" (Fase 4)
      const btnView = ev.target.closest('[data-action="view-factura"]');
      if (btnView) {
        const id = btnView.getAttribute('data-id');
        const num = btnView.getAttribute('data-numero') || '';
        if (id) {
          await abrirModalFactura(id, num).catch(console.error);
        }
        return;
      }
      
      // Manejar botón "Eliminar" (Fase 3)
      const btn = ev.target.closest('[data-action="eliminar"]');
      if (!btn) return;
      
      const id = btn.getAttribute('data-id');
      if (!id) return;
      
      if (!confirm('⚠️ Esta factura será eliminada solo del sistema SINTEL por error de carga. Esta acción es irreversible.')) {
        return;
      }
      
      await eliminarFactura(id);
    });
  }
}

/* ====== DOM helpers ====== */
function renderRow(row) {
  const tbody = document.querySelector('#tbl-facturas tbody');
  if (!tbody) return;
  tbody.insertAdjacentHTML('beforeend', rowHTML(row));
}

/**
 * Renderiza badge de naturaleza usando el valor calculado por backend (Service Layer + SSoT).
 * ⚠️ IMPORTANTE: No recalcula lógica; usa directamente row.naturaleza del JSON.
 */
function naturalezaBadge(n) {
  // Normalizar: convertir a string, uppercase, y trim
  const v = (n || '').toString().toUpperCase().trim();
  
  if (v === 'VENTA') {
    return '<span class="badge text-bg-success">Venta</span>';
  }
  if (v === 'COMPRA') {
    return '<span class="badge text-bg-primary">Compra</span>';
  }
  // Si no es VENTA ni COMPRA (null, undefined, o valor inválido), mostrar placeholder
  return '<span class="badge text-bg-secondary">—</span>';
}

function rowHTML(row) {
  // ⚠️ SSoT: Usa directamente row.naturaleza calculada por backend (Service Layer)
  // No aplicar defaults ni recalcular lógica en la UI
  
  // Columna NC: mostrar enlace si tiene nota crédito
  let ncCell = '<span class="text-muted">No</span>';
  if (row.has_nc && row.nota_credito_id) {
    ncCell = `<a href="#" class="link-nc text-primary" data-nc-id="${row.nota_credito_id}" data-test="link-nc">Sí</a>`;
  }
  
  return `
    <tr data-id="${row.id}">
      <td>${escapeHtml(row.numero || '-')}</td>
      <td>${naturalezaBadge(row.naturaleza)}</td>
      <td>${ncCell}</td>
      <td><div>${escapeHtml(row.emisor_razon_social || '-')}</div><div class="small text-muted">NIT: ${escapeHtml(row.emisor_nit || '-')}</div></td>
      <td><div>${escapeHtml(row.receptor_razon_social || '-')}</div><div class="small text-muted">NIT: ${escapeHtml(row.receptor_nit || '-')}</div></td>
      <td>${escapeHtml((row.fecha_emision || '').replace('T', ' ').split('.')[0])}</td>
      <td class="text-end">${fmtMoney(row.subtotal, row.moneda)}</td>
      <td class="text-end">${fmtMoney(row.impuestos, row.moneda)}</td>
      <td class="text-end">${fmtMoney(row.total, row.moneda)}</td>
      <td class="d-flex gap-2">
        <button class="btn btn-sm btn-outline-primary" data-action="view-factura" data-id="${row.id}" data-numero="${escapeHtml(row.numero || '')}" data-test="btn-ver">Ver</button>
        ${!row.has_nc ? `<a href="#" class="btn btn-sm btn-outline-success link-aplicar-nc" data-factura-id="${row.id}" data-factura-numero="${escapeHtml(row.numero || '')}" data-factura-cufe="${escapeHtml(row.cufe || '')}" data-test="btn-aplicar-nc">Aplicar NC</a>` : ''}
        ${row.has_nc && row.nota_credito_id ? `<a href="#" class="btn btn-sm btn-outline-info link-nc" data-nc-id="${row.nota_credito_id}" data-test="btn-ver-nc">Ver NC</a>` : ''}
        <button class="btn btn-sm btn-outline-danger" data-action="eliminar" data-id="${row.id}" data-test="btn-eliminar">Eliminar</button>
      </td>
    </tr>`;
}

function upsertRow(row) {
  const t = document.querySelector(`#tbl-facturas tbody tr[data-id="${row.id}"]`);
  const html = rowHTML(row);
  if (t) {
    t.outerHTML = html;
  } else {
    const tbody = document.querySelector('#tbl-facturas tbody');
    if (tbody) tbody.insertAdjacentHTML('afterbegin', html);
  }
}

function removeRow(id) {
  const tr = document.querySelector(`#tbl-facturas tbody tr[data-id="${id}"]`);
  if (tr) tr.remove();
}

// ⚠️ FASE 4: Abrir modal de detalle de factura con anexos XML
async function abrirModalFactura(id, numero) {
  // Limpiar contenido previo
  document.getElementById('fxm-numero').textContent = numero || id;
  document.getElementById('fxm-ubl').textContent = '';
  document.getElementById('fxm-app').textContent = '';
  document.getElementById('fxm-ubl-meta').textContent = 'Cargando...';
  document.getElementById('fxm-app-meta').textContent = '';
  
  // Abrir modal (Bootstrap 5)
  const modalEl = document.getElementById('factura-xml-modal');
  if (!modalEl) {
    console.error('Modal factura-xml-modal no encontrado');
    return;
  }
  const modal = window.bootstrap && window.bootstrap.Modal ? 
    window.bootstrap.Modal.getOrCreateInstance(modalEl) : null;
  if (modal) {
    modal.show();
  } else {
    // Fallback si Bootstrap no está disponible
    modalEl.style.display = 'block';
    modalEl.classList.add('show');
  }
  
  // 1) Traer detalle para saber qué anexos existen y sus tamaños
  const detailUrl = `/api/v1/facturas/${id}/`;
  try {
    const res = await fetch(detailUrl, { 
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) {
      document.getElementById('fxm-ubl-meta').textContent = 'No se pudo cargar el detalle.';
      return;
    }
    const dto = await res.json();
    
    // Configurar enlaces de descarga
    const aUbl = document.getElementById('fxm-ubl-download');
    const aApp = document.getElementById('fxm-app-download');
    if (aUbl) aUbl.href = `/api/v1/facturas/${id}/xml/`;
    if (aApp) aApp.href = `/api/v1/facturas/${id}/app-response/`;
    
    // 2) Si hay UBL, cargarlo inline (GET /xml)
    if (dto.has_ubl_xml) {
      try {
        const u = await fetch(aUbl.href, { 
          credentials: 'same-origin',
          headers: { 'Accept': 'application/xml, text/xml, */*' }
        });
        if (u.status === 200) {
          const text = await u.text();
          document.getElementById('fxm-ubl').textContent = text;
          const size = dto.anexos_meta?.ubl_size || text.length;
          document.getElementById('fxm-ubl-meta').textContent = `Tamaño ~ ${Math.round(size / 1024)} KB`;
        } else if (u.status === 204) {
          document.getElementById('fxm-ubl-meta').textContent = 'Sin contenido UBL.';
        } else {
          document.getElementById('fxm-ubl-meta').textContent = `Error ${u.status}`;
        }
      } catch (e) {
        document.getElementById('fxm-ubl-meta').textContent = `Error al cargar UBL: ${e.message}`;
      }
    } else {
      document.getElementById('fxm-ubl-meta').textContent = 'Sin contenido UBL.';
    }
    
    // 3) Response DIAN lazy bajo pestaña (cargar solo cuando se active la pestaña)
    const tabApp = document.querySelector('button[data-bs-target="#tab-app"]');
    if (tabApp) {
      const loadAppResponse = async () => {
        if (document.getElementById('fxm-app').textContent.trim().length) return; // ya cargado
        
        if (!dto.has_application_response_xml) {
          document.getElementById('fxm-app-meta').textContent = 'Sin ApplicationResponse.';
          return;
        }
        
        try {
          const a = await fetch(aApp.href, { 
            credentials: 'same-origin',
            headers: { 'Accept': 'application/xml, text/xml, */*' }
          });
          if (a.status === 200) {
            const text = await a.text();
            document.getElementById('fxm-app').textContent = text;
            const size = dto.anexos_meta?.app_response_size || text.length;
            document.getElementById('fxm-app-meta').textContent = `Tamaño ~ ${Math.round(size / 1024)} KB`;
          } else if (a.status === 204) {
            document.getElementById('fxm-app-meta').textContent = 'Sin contenido.';
          } else {
            document.getElementById('fxm-app-meta').textContent = `Error ${a.status}`;
          }
        } catch (e) {
          document.getElementById('fxm-app-meta').textContent = `Error al cargar Response: ${e.message}`;
        }
      };
      
      // Vincular una sola vez al evento shown.bs.tab
      tabApp.addEventListener('shown.bs.tab', loadAppResponse, { once: true });
    }
    
    // 4) Copiar al portapapeles
    const btnUblCopy = document.getElementById('fxm-ubl-copy');
    const btnAppCopy = document.getElementById('fxm-app-copy');
    
    if (btnUblCopy) {
      btnUblCopy.onclick = () => {
        const text = document.getElementById('fxm-ubl').textContent || '';
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(() => {
            console.log('UBL copiado al portapapeles');
            showToast('UBL copiado', 'success');
          }).catch(err => {
            console.error('Error al copiar UBL:', err);
            showToast('Error al copiar', 'danger');
          });
        } else {
          // Fallback para navegadores antiguos
          const textarea = document.createElement('textarea');
          textarea.value = text;
          document.body.appendChild(textarea);
          textarea.select();
          try {
            document.execCommand('copy');
            showToast('UBL copiado', 'success');
          } catch (err) {
            showToast('Error al copiar', 'danger');
          }
          document.body.removeChild(textarea);
        }
      };
    }
    
    if (btnAppCopy) {
      btnAppCopy.onclick = () => {
        const text = document.getElementById('fxm-app').textContent || '';
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(() => {
            console.log('Response DIAN copiado al portapapeles');
            showToast('Response DIAN copiado', 'success');
          }).catch(err => {
            console.error('Error al copiar Response:', err);
            showToast('Error al copiar', 'danger');
          });
        } else {
          // Fallback para navegadores antiguos
          const textarea = document.createElement('textarea');
          textarea.value = text;
          document.body.appendChild(textarea);
          textarea.select();
          try {
            document.execCommand('copy');
            showToast('Response DIAN copiado', 'success');
          } catch (err) {
            showToast('Error al copiar', 'danger');
          }
          document.body.removeChild(textarea);
        }
      };
    }
  } catch (error) {
    console.error('Error al abrir modal de factura:', error);
    document.getElementById('fxm-ubl-meta').textContent = 'Error al cargar el detalle.';
  }
}

// ⚠️ FASE 8: Abrir modal de detalle de Nota Crédito
async function abrirModalNotaCredito(ncId) {
  const loadingEl = document.getElementById('ncm-loading');
  const contentEl = document.getElementById('ncm-content');
  
  // Mostrar loading, ocultar contenido
  if (loadingEl) loadingEl.classList.remove('d-none');
  if (contentEl) contentEl.classList.add('d-none');
  
  // Abrir modal (Bootstrap 5)
  const modalEl = document.getElementById('nota-credito-modal');
  if (!modalEl) {
    console.error('Modal nota-credito-modal no encontrado');
    return;
  }
  const modal = window.bootstrap && window.bootstrap.Modal ? 
    window.bootstrap.Modal.getOrCreateInstance(modalEl) : null;
  if (modal) {
    modal.show();
  } else {
    // Fallback si Bootstrap no está disponible
    modalEl.style.display = 'block';
    modalEl.classList.add('show');
  }
  
  try {
    // Cargar detalle de nota crédito
    const detailUrl = `/api/v1/notas-credito/${ncId}/`;
    const res = await fetch(detailUrl, { 
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }
    });
    
    if (!res.ok) {
      throw new Error(`Error ${res.status}: No se pudo cargar la nota crédito`);
    }
    
    const nota = await res.json();
    
    // Llenar campos del modal
    document.getElementById('ncm-numero').textContent = nota.numero || '-';
    document.getElementById('ncm-numero-val').textContent = nota.numero || '-';
    document.getElementById('ncm-cude').textContent = nota.cude || '-';
    document.getElementById('ncm-fecha-emision').textContent = 
      (nota.fecha_emision || '').replace('T', ' ').split('.')[0] || '-';
    document.getElementById('ncm-moneda').textContent = nota.moneda || '-';
    document.getElementById('ncm-subtotal').textContent = fmtMoney(nota.subtotal, nota.moneda);
    document.getElementById('ncm-impuestos').textContent = fmtMoney(nota.impuestos, nota.moneda);
    document.getElementById('ncm-total').textContent = fmtMoney(nota.total, nota.moneda);
    document.getElementById('ncm-motivo').textContent = nota.motivo || '(Sin motivo especificado)';
    document.getElementById('ncm-ref-factura-numero').textContent = nota.ref_factura_numero || nota.factura_numero || '-';
    document.getElementById('ncm-ref-factura-cufe').textContent = nota.ref_factura_cufe || nota.factura_cufe || '-';
    
    // Configurar enlace al XML
    const xmlLink = document.getElementById('ncm-xml-link');
    if (xmlLink) {
      xmlLink.href = `/api/v1/notas-credito/${ncId}/xml/`;
    }
    
    // Ocultar loading, mostrar contenido
    if (loadingEl) loadingEl.classList.add('d-none');
    if (contentEl) contentEl.classList.remove('d-none');
    
  } catch (error) {
    console.error('Error al cargar nota crédito:', error);
    if (loadingEl) {
      loadingEl.textContent = `Error: ${error.message || 'Error desconocido'}`;
      loadingEl.classList.remove('d-none');
    }
    if (contentEl) contentEl.classList.add('d-none');
  }
}

// === Funcionalidad: Aplicar Nota Crédito ===

// Estado del modal
let currentFacturaNC = { id: null, numero: null, cufe: null };

// Abrir modal desde acciones
function abrirModalAplicarNC(factura) {
  currentFacturaNC = {
    id: factura.id,
    numero: factura.numero || '',
    cufe: factura.cufe || ''
  };
  
  // Rellenar campos visibles/ocultos
  const numeroEl = document.getElementById('nc-factura-numero');
  const cufeEl = document.getElementById('nc-factura-cufe');
  const idHidden = document.getElementById('nc-factura-id-hidden');
  const numeroHidden = document.getElementById('nc-factura-numero-hidden');
  const cufeHidden = document.getElementById('nc-factura-cufe-hidden');
  const fileInput = document.getElementById('nc-file');
  const feedback = document.getElementById('nc-feedback');
  
  if (numeroEl) numeroEl.textContent = currentFacturaNC.numero;
  if (cufeEl) cufeEl.textContent = currentFacturaNC.cufe;
  if (idHidden) idHidden.value = currentFacturaNC.id;
  if (numeroHidden) numeroHidden.value = currentFacturaNC.numero;
  if (cufeHidden) cufeHidden.value = currentFacturaNC.cufe;
  if (fileInput) fileInput.value = '';
  if (feedback) clearAlert(feedback);
  
  // Abrir modal (Bootstrap 5)
  const modalEl = document.getElementById('aplicarNCModal');
  if (!modalEl) {
    console.error('Modal aplicarNCModal no encontrado');
    return;
  }
  const modal = window.bootstrap && window.bootstrap.Modal ? 
    window.bootstrap.Modal.getOrCreateInstance(modalEl) : null;
  if (modal) {
    modal.show();
  } else {
    modalEl.style.display = 'block';
    modalEl.classList.add('show');
  }
}

// Submit del modal (inicializar cuando el DOM esté listo)
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('form-aplicar-nc');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const feedback = document.getElementById('nc-feedback');
    const fileInput = document.getElementById('nc-file');
    const doPreview = document.getElementById('nc-preview')?.checked ?? true;
    const btnSubmit = document.getElementById('btn-submit-nc');
    
    clearAlert(feedback);
    
    if (!fileInput?.files || !fileInput.files[0]) {
      showWarnLocal('nc-feedback', 'Selecciona un archivo XML de Nota Crédito.');
      return;
    }
    
    // Deshabilitar botón durante procesamiento
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.textContent = 'Procesando...';
    }
    
    try {
      // 1) Preview (opcional: recomendado)
      if (doPreview) {
        const previewOk = await previewNC(fileInput.files[0], currentFacturaNC, feedback);
        if (!previewOk) {
          if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.textContent = 'Guardar y aplicar';
          }
          return; // feedback ya informado
        }
      }
      
      // 2) Persistencia
      const persisted = await persistNC(fileInput.files[0], feedback);
      if (!persisted) {
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.textContent = 'Guardar y aplicar';
        }
        return;
      }
      
      // 3) Cerrar modal y refrescar fila/tabla
      const modalEl = document.getElementById('aplicarNCModal');
      if (modalEl) {
        const modal = window.bootstrap && window.bootstrap.Modal ? 
          window.bootstrap.Modal.getInstance(modalEl) : null;
        if (modal) {
          modal.hide();
        }
      }
      
      // Refrescar tabla
      loadTabla().catch(console.error);
      
      // Toast de éxito
      showToast('Nota Crédito aplicada correctamente', 'success');
      
    } catch (err) {
      console.error('Error al aplicar nota crédito:', err);
      showErrorLocal('nc-feedback', 'error', `Error inesperado: ${err.message || err}`);
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Guardar y aplicar';
      }
    }
  });
});

async function previewNC(file, factura, feedback) {
  const fd = new FormData();
  fd.append('file', file);
  
  try {
    const res = await fetch(`/api/v1/core/documentos/upload/?preview=true`, {  // ⚠️ v2.36: Endpoint universal
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': getCsrf() },
    });
    
    if (!res.ok) {
      const data = await safeJson(res);
      showErrorLocal('nc-feedback', 'preview_error', data?.message || 'No fue posible previsualizar la Nota Crédito.');
      return false;
    }
    
    const data = await res.json();
    
    // Verificar que es una nota crédito
    if (data.document_type !== 'creditnote.ubl21') {
      showErrorLocal('nc-feedback', 'invalid_type', 'El archivo no es una Nota Crédito UBL 2.1.');
      return false;
    }
    
    // data.dto.referencia.{numero, cufe}
    const ref = data?.dto?.referencia || {};
    if (!ref.numero || !ref.cufe) {
      showErrorLocal('nc-feedback', 'missing_reference', 'La Nota Crédito no contiene una referencia válida a una factura.');
      return false;
    }
    
    // Validar contra la fila elegida (número y CUFE)
    if (ref.numero !== factura.numero || ref.cufe !== factura.cufe) {
      showWarnLocal('nc-feedback', 
        `La Nota Crédito referencia la factura ${ref.numero} (CUFE: ${ref.cufe}), ` +
        `pero seleccionaste ${factura.numero} (CUFE: ${factura.cufe}).`
      );
      return false;
    }
    
    showInfoLocal('nc-feedback', 'Previsualización OK. Se aplicará a la factura seleccionada.');
    return true;
    
  } catch (err) {
    console.error('Error en preview:', err);
    showErrorLocal('nc-feedback', 'preview_error', `Error al previsualizar: ${err.message || err}`);
    return false;
  }
}

async function persistNC(file, feedback) {
  const fd = new FormData();
  fd.append('file', file);
  
  try {
    const res = await fetch(`/api/v1/core/documentos/upload/`, {  // ⚠️ v2.36: Endpoint universal
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': getCsrf() },
    });
    
    if (res.status === 201) {
      showSuccessLocal('nc-feedback', 'Nota Crédito aplicada correctamente.');
      return true;
    }
    
    const data = await safeJson(res);
    
    if (res.status === 409 && data?.error === 'duplicate') {
      showWarnLocal('nc-feedback', 'Esta Nota Crédito ya fue cargada (CUDE duplicado).');
      return false;
    }
    
    if (res.status === 422) {
      if (data?.error === 'missing_invoice') {
        showErrorLocal('nc-feedback', 'missing_invoice', 'La factura referenciada no existe en este tenant.');
      } else if (data?.error === 'already_has_nc') {
        showErrorLocal('nc-feedback', 'already_has_nc', 'La factura ya tiene una nota crédito asociada.');
      } else {
        showErrorLocal('nc-feedback', 'validation_error', data?.message || 'Error de validación.');
      }
      return false;
    }
    
    showErrorLocal('nc-feedback', 'persist_error', data?.message || 'No fue posible aplicar la Nota Crédito.');
    return false;
    
  } catch (err) {
    console.error('Error en persistencia:', err);
    showErrorLocal('nc-feedback', 'persist_error', `Error al aplicar: ${err.message || err}`);
    return false;
  }
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}
