// apps/tenant/clientes/static/tenant/clientes/clientes.page.js
(function ClientesModule() {
  const API_BASE = "/api/v1";
  const tableBody = document.querySelector("#clientes-table tbody");
  const feedback = document.getElementById("clientes-list-feedback");
  const createSubmit = document.getElementById("cliente-create-submit");
  const editSubmit = document.getElementById("cliente-edit-submit");
  const deleteConfirm = document.getElementById("cliente-delete-confirm");

  function getCSRF() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : "";
  }

  async function listClientes(params = {}) {
    const qs = new URLSearchParams(params).toString();
    const resp = await fetch(`${API_BASE}/clientes/${qs ? "?" + qs : ""}`, { credentials: "same-origin" });
    if (!resp.ok) {
      if (resp.status === 401) {
        // NO redirigir a login; solo mostrar error en feedback local
        throw new Error("No has iniciado sesión para clientes o no tienes permisos. (401)");
      }
      if (resp.status === 404) {
        throw new Error("Endpoint /api/v1/clientes/ no disponible (ver TENANT_URLCONF).");
      }
      if (resp.status === 403) {
        throw new Error("No tienes permisos para ver clientes en este tenant.");
      }
      const text = await resp.text().catch(() => "");
      throw new Error(`Error listando clientes (HTTP ${resp.status}). ${text}`);
    }
    return resp.json();
  }

  function renderRows(payload) {
    if (!tableBody) return;
    const items = payload.results ?? payload;
    tableBody.innerHTML = "";

    if (!Array.isArray(items) || items.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No hay clientes registrados</td></tr>';
      return;
    }

    items.forEach(c => {
      const activo = c.activo ? "Sí" : "No";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${c.razon_social || ""}</td>
        <td>${c.tipo_documento || ""}-${c.numero_documento || ""}</td>
        <td>${c.segmento || ""}</td>
        <td>${c.email || ""}</td>
        <td>${c.telefono || ""}</td>
        <td>${activo}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-outline-primary" data-action="edit" data-id="${c.id}" data-bs-toggle="modal" data-bs-target="#cliente-edit-modal">Editar</button>
          <button class="btn btn-sm btn-outline-danger" data-action="del" data-id="${c.id}" data-bs-toggle="modal" data-bs-target="#cliente-delete-modal">Eliminar</button>
        </td>
      `;
      tableBody.appendChild(tr);
    });
  }

  async function refresh() {
    if (feedback) {
      feedback.textContent = "";
      feedback.className = "";
    }
    try {
      const data = await listClientes({ ordering: "razon_social" });
      renderRows(data);
    } catch (err) {
      // Mostrar error en feedback local, sin redirigir a login
      console.error("[clientes] Error refrescando:", err);
      if (feedback) {
        feedback.className = "alert alert-warning mt-2";
        feedback.textContent = err.message || "No se pudieron cargar los clientes.";
      }
      if (tableBody) {
        tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">${err.message || "Error al cargar"}</td></tr>`;
      }
    }
  }

  async function createCliente(payload) {
    const resp = await fetch(`${API_BASE}/clientes/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      if (resp.status === 401) {
        throw new Error("No has iniciado sesión para crear clientes o no tienes permisos. (401)");
      }
      if (resp.status === 403) {
        throw new Error("No tienes permisos para crear clientes en este tenant.");
      }
      throw await resp.json().catch(() => ({detail:"Error al crear cliente"}));
    }
    return resp.json();
  }

  async function patchCliente(id, payload) {
    const resp = await fetch(`${API_BASE}/clientes/${id}/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      if (resp.status === 401) {
        throw new Error("No has iniciado sesión para editar clientes o no tienes permisos. (401)");
      }
      if (resp.status === 403) {
        throw new Error("No tienes permisos para editar clientes en este tenant.");
      }
      throw await resp.json().catch(() => ({detail:"Error al actualizar cliente"}));
    }
    return resp.json();
  }

  async function deleteCliente(id) {
    const resp = await fetch(`${API_BASE}/clientes/${id}/`, {
      method: "DELETE",
      headers: { "X-CSRFToken": getCSRF() },
      credentials: "same-origin",
    });
    if (!resp.ok && resp.status !== 204) {
      if (resp.status === 401) {
        throw new Error("No has iniciado sesión para eliminar clientes o no tienes permisos. (401)");
      }
      if (resp.status === 403) {
        throw new Error("No tienes permisos para eliminar clientes en este tenant.");
      }
      throw await resp.json().catch(() => ({detail:"Error al eliminar cliente"}));
    }
    return true;
  }

  async function getCliente(id) {
    const resp = await fetch(`${API_BASE}/clientes/${id}/`, { credentials: "same-origin" });
    if (!resp.ok) {
      if (resp.status === 401) {
        throw new Error("No has iniciado sesión para ver el cliente o no tienes permisos. (401)");
      }
      if (resp.status === 403) {
        throw new Error("No tienes permisos para ver este cliente en este tenant.");
      }
      throw await resp.json();
    }
    return resp.json();
  }

  function fillEditForm(data) {
    const fields = [
      "tipo_persona", "tipo_documento", "numero_documento", "segmento",
      "razon_social", "nombre_comercial", "regimen_tributario", "responsable_iva",
      "actividad_economica_ciiu", "email", "telefono", "direccion", "ciudad",
      "contacto_nombre", "contacto_telefono", "banco", "tipo_cuenta", "numero_cuenta",
      "activo", "observaciones"
    ];
    fields.forEach(field => {
      const el = document.getElementById(`edit-${field}`);
      if (el) {
        if (el.type === "email") {
          el.value = data[field] || "";
        } else if (el.tagName === "SELECT") {
          el.value = data[field] || "";
        } else if (el.tagName === "TEXTAREA") {
          el.value = data[field] || "";
        } else {
          el.value = data[field] || "";
        }
      }
    });
  }

  // Wireup
  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-action]");
    if (!btn) return;
    const id = btn.getAttribute("data-id");
    const act = btn.getAttribute("data-action");
    if (act === "edit") {
      const form = document.getElementById("cliente-edit-form");
      if (form) {
        form.setAttribute("data-id", id);
        getCliente(id).then(fillEditForm).catch(err => {
          const feedbackEl = document.getElementById("cliente-edit-feedback");
          if (feedbackEl) feedbackEl.textContent = err?.detail ?? err?.message ?? "Error";
        });
      }
    } else if (act === "del") {
      if (deleteConfirm) {
        deleteConfirm.setAttribute("data-id", id);
      }
    }
  });

  createSubmit?.addEventListener("click", async () => {
    const form = document.getElementById("cliente-create-form");
    if (!form) return;
    const payload = Object.fromEntries(new FormData(form).entries());
    
    // Normalizar booleanos
    payload.activo = String(payload.activo || "true") === "true";
    payload.responsable_iva = String(payload.responsable_iva || "false") === "true";
    
    // Limpiar campos vacíos opcionales
    if (!payload.nombre_comercial) delete payload.nombre_comercial;
    if (!payload.actividad_economica_ciiu) delete payload.actividad_economica_ciiu;
    if (!payload.email) delete payload.email;
    if (!payload.telefono) delete payload.telefono;
    if (!payload.direccion) delete payload.direccion;
    if (!payload.ciudad) delete payload.ciudad;
    if (!payload.contacto_nombre) delete payload.contacto_nombre;
    if (!payload.contacto_telefono) delete payload.contacto_telefono;
    if (!payload.banco) delete payload.banco;
    if (!payload.tipo_cuenta) delete payload.tipo_cuenta;
    if (!payload.numero_cuenta) delete payload.numero_cuenta;
    if (!payload.observaciones) delete payload.observaciones;

    try {
      await createCliente(payload);
      await refresh();
      const feedbackEl = document.getElementById("cliente-create-feedback");
      if (feedbackEl) feedbackEl.textContent = "";
      const modal = bootstrap.Modal.getInstance(document.getElementById("cliente-create-modal"));
      if (modal) modal.hide();
    } catch (err) {
      const el = document.getElementById("cliente-create-feedback");
      if (el) el.textContent = err.detail || err.message || "Error";
    }
  });

  editSubmit?.addEventListener("click", async () => {
    const form = document.getElementById("cliente-edit-form");
    if (!form) return;
    const id = form.getAttribute("data-id");
    if (!id) return;
    
    const payload = Object.fromEntries(new FormData(form).entries());
    delete payload.id;
    
    // Normalizar booleanos
    payload.activo = String(payload.activo || "true") === "true";
    payload.responsable_iva = String(payload.responsable_iva || "false") === "true";
    
    // Limpiar campos vacíos opcionales
    if (!payload.nombre_comercial) delete payload.nombre_comercial;
    if (!payload.actividad_economica_ciiu) delete payload.actividad_economica_ciiu;
    if (!payload.email) delete payload.email;
    if (!payload.telefono) delete payload.telefono;
    if (!payload.direccion) delete payload.direccion;
    if (!payload.ciudad) delete payload.ciudad;
    if (!payload.contacto_nombre) delete payload.contacto_nombre;
    if (!payload.contacto_telefono) delete payload.contacto_telefono;
    if (!payload.banco) delete payload.banco;
    if (!payload.tipo_cuenta) delete payload.tipo_cuenta;
    if (!payload.numero_cuenta) delete payload.numero_cuenta;
    if (!payload.observaciones) delete payload.observaciones;

    try {
      await patchCliente(id, payload);
      await refresh();
      const feedbackEl = document.getElementById("cliente-edit-feedback");
      if (feedbackEl) feedbackEl.textContent = "";
      const modal = bootstrap.Modal.getInstance(document.getElementById("cliente-edit-modal"));
      if (modal) modal.hide();
    } catch (err) {
      const el = document.getElementById("cliente-edit-feedback");
      if (el) el.textContent = err.detail || err.message || "Error";
    }
  });

  deleteConfirm?.addEventListener("click", async (ev) => {
    const id = ev.currentTarget.getAttribute("data-id");
    if (!id) return;
    try {
      await deleteCliente(id);
      await refresh();
      const feedbackEl = document.getElementById("cliente-delete-feedback");
      if (feedbackEl) feedbackEl.textContent = "";
      const modal = bootstrap.Modal.getInstance(document.getElementById("cliente-delete-modal"));
      if (modal) modal.hide();
    } catch (err) {
      const el = document.getElementById("cliente-delete-feedback");
      if (el) el.textContent = err.detail || err.message || "Error";
    }
  });

  // Limpiar formularios al cerrar modales
  const createModal = document.getElementById("cliente-create-modal");
  const editModal = document.getElementById("cliente-edit-modal");
  
  if (createModal) {
    createModal.addEventListener("hidden.bs.modal", () => {
      const form = document.getElementById("cliente-create-form");
      if (form) form.reset();
      const feedbackEl = document.getElementById("cliente-create-feedback");
      if (feedbackEl) feedbackEl.textContent = "";
    });
  }
  
  if (editModal) {
    editModal.addEventListener("hidden.bs.modal", () => {
      const form = document.getElementById("cliente-edit-form");
      if (form) form.reset();
      const feedbackEl = document.getElementById("cliente-edit-feedback");
      if (feedbackEl) feedbackEl.textContent = "";
    });
  }

  // init - exponer función refresh globalmente para que workspace pueda llamarla
  window.refreshClientes = refresh;
  
  // Auto-inicializar si la vista de clientes está visible
  function initIfVisible() {
    const viewClientes = document.getElementById("view-clientes");
    if (viewClientes && !viewClientes.hidden) {
      refresh();
    }
  }
  
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      initIfVisible();
      // También escuchar cambios de visibilidad
      const observer = new MutationObserver(() => initIfVisible());
      const viewClientes = document.getElementById("view-clientes");
      if (viewClientes) {
        observer.observe(viewClientes, { attributes: true, attributeFilter: ["hidden"] });
      }
    });
  } else {
    setTimeout(initIfVisible, 100);
    // También escuchar cambios de visibilidad
    const observer = new MutationObserver(() => initIfVisible());
    const viewClientes = document.getElementById("view-clientes");
    if (viewClientes) {
      observer.observe(viewClientes, { attributes: true, attributeFilter: ["hidden"] });
    }
  }
})();
