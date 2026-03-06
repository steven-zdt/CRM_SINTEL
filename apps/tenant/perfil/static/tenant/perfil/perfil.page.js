/**
 * Página JavaScript para el workspace de Perfil.
 * 
 * ⚠️ v2.30: API-First - Consume /api/v1/perfil/perfiles/me/
 * - Normaliza payload: excluye campos vacíos o envía null
 * - Sintaxis JS segura: catch (err) en todos los bloques
 * - Listener único: data-listener-attached para evitar doble registro
 */

// Guard: no reventar si la página no es Perfil
document.addEventListener('DOMContentLoaded', () => {
  const $section = document.querySelector('#view-perfil');
  if (!$section) return; // no es la página de perfil, salir

  // Exposición opcional global (si tu código existente lo usa)
  if (!window.loadPerfil) window.loadPerfil = loadPerfil;
  if (!window.savePerfil) window.savePerfil = savePerfil;
  if (!window.getConfigFromForm) window.getConfigFromForm = getConfigFromForm;

  // Init UI
  bindPerfilHandlers();
  // Primera carga
  loadPerfil().catch(err => console.error('[perfil] Error en loadPerfil:', err));
});

/* ====== Helpers mínimos ====== */
function getCookie(name) {
  const m = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]+)`));
  return m ? decodeURIComponent(m[2]) : '';
}

function goLogin(reason) {
  console.warn(`[perfil] Redirigiendo a login: ${reason}`);
  window.location.href = '/login/';
}

/* ====== Helpers de configuración ====== */
function getConfigFromForm() {
  const st = document.getElementById("status-perfil");
  const configValue = document.querySelector('#pf_config')?.value?.trim();
  
  if (!configValue) {
    return {}; // Normalizar vacío a {} (no null)
  }
  
  try {
    const cfg = JSON.parse(configValue);
    // Validar que sea un objeto (dict)
    if (typeof cfg !== "object" || Array.isArray(cfg) || cfg === null) {
      if (st) {
        st.className = "status err";
        st.textContent = "Config debe ser un objeto JSON válido (no array ni null).";
      }
      throw new Error("Config inválido");
    }
    return cfg;
  } catch (err) {
    if (st) {
      st.className = "status err";
      st.textContent = "Config debe ser JSON válido.";
    }
    throw err;
  }
}

/* ====== Cargar perfil ====== */
async function loadPerfil() {
  const st = document.getElementById("status-perfil");
  
  try {
    const res = await fetch("/api/v1/perfil/perfiles/me/", {
      headers: { "Accept": "application/json" },
      credentials: "same-origin",
    });
    
    if (res.status === 401) {
      goLogin("401");
      return;
    }
    
    if (!res.ok) {
      const text = await res.text();
      let data = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch (err) {
        data = { detail: text };
      }
      if (st) {
        st.className = "status err";
        st.textContent = data?.detail || data?.error || `Error ${res.status}`;
      }
      return;
    }
    
    const p = await res.json();
    
    // Llenar campos del formulario
    const set = (id, val) => {
      const el = document.querySelector(`#${id}`);
      if (el) el.value = val ?? "";
    };
    
    set("pf_nombre", p?.user_full_name ?? "");
    set("pf_email", p?.user_email ?? "");
    set("pf_cargo", p?.cargo ?? "");
    set("pf_departamento", p?.departamento ?? "");
    set("pf_telefono", p?.telefono_corporativo ?? "");
    set("pf_config", p?.configuracion ? JSON.stringify(p.configuracion) : "");
    
    // Mostrar preview del avatar si existe
    const preview = document.getElementById("pf_avatar_preview");
    if (preview && p?.avatar_url) {
      preview.innerHTML = `<img src="${p.avatar_url}" alt="Avatar" style="max-width: 100px; max-height: 100px; border-radius: 8px;" />`;
    } else if (preview) {
      preview.innerHTML = "";
    }
    
    if (st) {
      st.className = "status";
      st.textContent = "Perfil cargado.";
    }
  } catch (err) {
    console.error("[perfil] Error cargando perfil:", err);
    if (st) {
      st.className = "status err";
      st.textContent = "Error al cargar el perfil.";
    }
  }
}

/* ====== Guardar perfil ====== */
async function savePerfil() {
  const st = document.getElementById("status-perfil");
  
  try {
    // Leer valores del formulario
    const cargo = document.querySelector('#pf_cargo')?.value.trim() || "";
    const departamento = document.querySelector('#pf_departamento')?.value.trim() || "";
    const telCorp = document.querySelector('#pf_telefono')?.value.trim() || "";
    const configuracion = getConfigFromForm();

    // Normalizar payload: excluir campos vacíos o enviar null
    const payload = {};
    
    // Cargo: opcional, excluir si está vacío
    if (cargo) {
      payload.cargo = cargo;
    }
    
    // Departamento: opcional, excluir si está vacío
    if (departamento) {
      payload.departamento = departamento;
    }
    
    // Teléfono corporativo: opcional, excluir si está vacío
    if (telCorp) {
      payload.telefono_corporativo = telCorp;
    }
    
    // Configuración: siempre incluir (normalizada a {} si vacía)
    payload.configuracion = configuracion;

    console.debug('[perfil] Payload normalizado:', payload);

    // Verificar si se envió avatar (multipart) o solo JSON
    const avatarFile = document.querySelector('#pf_avatar')?.files?.[0];
    const hasAvatar = avatarFile && avatarFile.size > 0;
    
    // Preparar request: FormData si hay avatar, JSON si no
    let requestData;
    let isFormData = false;
    
    if (hasAvatar) {
      const formData = new FormData();
      
      // Agregar campos normalizados
      if (payload.cargo) formData.append('cargo', payload.cargo);
      if (payload.departamento) formData.append('departamento', payload.departamento);
      if (payload.telefono_corporativo) formData.append('telefono_corporativo', payload.telefono_corporativo);
      formData.append('configuracion', JSON.stringify(payload.configuracion));
      formData.append('avatar', avatarFile);
      
      const csrfToken = getCookie("csrftoken");
      if (csrfToken) {
        formData.append("csrfmiddlewaretoken", csrfToken);
      }
      
      requestData = formData;
      isFormData = true;
    } else {
      requestData = payload;
    }
    
    // Hacer request PATCH
    const init = {
      method: 'PATCH',
      headers: { "Accept": "application/json" },
      credentials: "same-origin",
    };
    
    if (isFormData) {
      init.body = requestData;
    } else {
      init.headers["Content-Type"] = "application/json";
      const csrfToken = getCookie("csrftoken");
      if (csrfToken) {
        init.headers["X-CSRFToken"] = csrfToken;
      }
      init.body = JSON.stringify(requestData);
    }
    
    const res = await fetch("/api/v1/perfil/perfiles/me/", init);
    
    if (res.status === 401) {
      goLogin("401");
      return;
    }
    
    const text = await res.text();
    let responseData = null;
    try {
      responseData = text ? JSON.parse(text) : null;
    } catch (err) {
      responseData = { detail: text };
    }
    
    const r = { ok: res.ok, status: res.status, data: responseData };
    
    if (!r.ok) {
      const msg = r.data?.error || r.data?.detail || r.data?.message || `Error ${r.status}`;
      
      if (r.status === 400) {
        if (st) {
          st.className = "status err";
          st.textContent = msg;
        }
      } else if (r.status === 403) {
        const csrfToken = getCookie("csrftoken");
        const diagnosticMsg = csrfToken 
          ? "Permisos insuficientes: requiere autenticación válida."
          : "Error de autenticación: falta token CSRF. Recarga la página e intenta nuevamente.";
        if (st) {
          st.className = "status err";
          st.textContent = diagnosticMsg;
        }
      } else if (r.status === 503 && r.data?.detail_code === "tenant_schema_unmigrated") {
        if (st) {
          st.className = "status err";
          st.textContent = "⚠️ Migraciones del tenant pendientes. Intenta en unos segundos o contacta al administrador.";
        }
      } else {
        if (st) {
          st.className = "status err";
          st.textContent = msg;
        }
      }
      return;
    }
    
    // Éxito: limpiar input de archivo y recargar perfil
    const avatarInput = document.querySelector('#pf_avatar');
    if (avatarInput) avatarInput.value = "";
    
    if (st) {
      st.className = "status ok";
      st.textContent = "Perfil actualizado.";
    }
    
    await loadPerfil();
    
    // Nota: setReadOnly y showEditActions deben estar definidos en workspace.html
    if (typeof setReadOnly === 'function') {
      setReadOnly('SECTION_PERFIL', true);
    }
    if (typeof showEditActions === 'function') {
      showEditActions("perfil", false);
    }
  } catch (err) {
    console.error("[perfil] Error inesperado en savePerfil:", err, err.stack);
    if (st) {
      st.className = "status err";
      st.textContent = `Error: ${err.message || "Error desconocido"}`;
    }
  }
}

/* ====== Wiring ====== */
function bindPerfilHandlers() {
  const btnSavePerfil = document.getElementById("btn-save-perfil");
  
  if (btnSavePerfil && !btnSavePerfil.dataset.listenerAttached) {
    btnSavePerfil.dataset.listenerAttached = "true";
    btnSavePerfil.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      console.log("[perfil] Botón Guardar Perfil clickeado");
      savePerfil().catch(err => {
        console.error("[perfil] Error en savePerfil:", err);
        const st = document.getElementById("status-perfil");
        if (st) {
          st.className = "status err";
          st.textContent = `Error: ${err.message || "Error desconocido"}`;
        }
      });
    });
  }
}
