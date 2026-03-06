/**
 * Módulo JavaScript para el workspace de Facturas.
 * 
 * Funcionalidades:
 * - Upload de archivos XML UBL
 * - Visualización de lista de facturas
 * - Ver detalle de factura
 * - Eliminar factura (rollback de error de carga)
 * - Manejo de errores minimalista
 */
import { csrftoken } from "../_csrf.js";

const API_LIST = "/api/v1/facturas/";
const API_UPLOAD = "/api/v1/core/documentos/upload/";  // ⚠️ v2.36: Endpoint universal

/**
 * Muestra error de importación en modal minimalista.
 */
function showImportError({ code, message }) {
  const m = document.getElementById("import-error-modal");
  if (!m) {
    console.warn("Modal import-error-modal no encontrado");
    return;
  }
  const titleEl = m.querySelector(".modal-title");
  const bodyEl = m.querySelector(".modal-body");
  if (titleEl) titleEl.textContent = "⚠️ Error al importar";
  if (bodyEl) {
    bodyEl.innerHTML = `<p class="mb-0">${escapeHtml(message)}</p><div class="text-muted small mt-1">${escapeHtml(code)}</div>`;
  }
  // Abrir modal según tu lib de UI (Bootstrap):
  if (window.bootstrap && bootstrap.Modal) {
    const modalInstance = new bootstrap.Modal(m);
    modalInstance.show();
  } else {
    m.style.display = "block";
    m.classList.add("show");
  }
}

/**
 * Escapa HTML para prevenir XSS.
 */
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Importa UBL desde input de archivo.
 * FORÉNSICA: Incluye logs de diagnóstico sin secretos.
 * @param {HTMLElement} inputFileEl - Input de tipo file
 * @param {string} naturaleza - "VENTA" | "COMPRA"
 * @param {boolean} preview - Si es true, solo parsea sin persistir
 * @returns {Promise<Object>} Payload de respuesta
 */
export async function importarUblDesdeInput({ inputFileEl, naturaleza = "VENTA", preview = false }) {
  const f = inputFileEl.files && inputFileEl.files[0];
  const fd = new FormData();
  if (f) fd.append("file", f); // CLAVE EXACTA esperada por el backend
  fd.append("naturaleza", naturaleza);

  // FORÉNSICA CLIENTE: Log de construcción de FormData (sin secretos)
  console.debug("[upload/forensics] building FormData:", {
    hasFile: !!f,
    fileName: f?.name,
    fileSize: f?.size,
    naturaleza,
    preview,
    hasCsrfToken: !!csrftoken
  });

  const url = `${API_UPLOAD}${preview ? "?preview=true" : ""}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "X-CSRFToken": csrftoken || "", "Accept": "application/json" },
    body: fd,
    credentials: "same-origin"
  });

  // FORÉNSICA CLIENTE: Log de respuesta (sin secretos)
  console.debug("[upload/forensics] response:", {
    status: res.status,
    ok: res.ok,
    contentType: res.headers.get("content-type")
  });

  let payload = null;
  try {
    payload = await res.json();
  } catch {
    // Non-JSON fallback
    payload = null;
  }
  
  if (!res.ok) {
    const code = payload?.error || "unknown";
    const message = payload?.message || `Error (${res.status})`;
    console.warn("[upload/forensics] error response:", { code, message, status: res.status });
    showImportError({ code, message });
    throw new Error(`${code}: ${message}`);
  }
  
  console.debug("[upload/forensics] success:", { numero: payload?.numero, id: payload?.id });
  
  // Actualización en tiempo real: insertar/actualizar fila sin recargar página
  if (payload && payload.id) {
    // respuesta 201/200 con objeto persistido: upsert optimista
    upsertRow(payload);
  } else {
    // por si envías un DTO en preview: re-carga no-cache para consolidar
    // (no debería pasar en modo persist, pero por seguridad)
    await loadTabla();
  }
  
  return payload;
}

/**
 * Formatea dinero según moneda.
 */
function fmtMoney(v, cur = "COP") {
  try {
    return new Intl.NumberFormat("es-CO", { style: "currency", currency: cur }).format(Number(v || 0));
  } catch {
    return Number(v || 0).toFixed(2);
  }
}

/**
 * Selector para fila de factura por ID.
 */
function rowSelector(id) {
  return `#tbl-facturas tbody tr[data-id="${id}"]`;
}

/**
 * Renderiza HTML de una fila de factura.
 */
function renderFilaHTML(row) {
  return `
    <tr data-id="${row.id}">
      <td>${escapeHtml(row.numero || "-")}</td>
      <td>${escapeHtml(row.naturaleza || "-")}</td>
      <td><div>${escapeHtml(row.emisor_razon_social || "-")}</div><div class="small text-muted">NIT: ${escapeHtml(row.emisor_nit || "-")}</div></td>
      <td><div>${escapeHtml(row.receptor_razon_social || "-")}</div><div class="small text-muted">NIT: ${escapeHtml(row.receptor_nit || "-")}</div></td>
      <td>${escapeHtml((row.fecha_emision || "").replace("T", " ").split(".")[0])}</td>
      <td class="text-end">${fmtMoney(row.subtotal, row.moneda)}</td>
      <td class="text-end">${fmtMoney(row.impuestos, row.moneda)}</td>
      <td class="text-end">${fmtMoney(row.total, row.moneda)}</td>
      <td>
        <button class="btn btn-sm btn-outline-secondary" data-action="ver" data-id="${row.id}" data-test="btn-ver">Ver</button>
        <button class="btn btn-sm btn-outline-danger ms-1" data-action="eliminar" data-id="${row.id}" data-test="btn-eliminar">Eliminar</button>
      </td>
    </tr>`;
}

/**
 * Inserta o actualiza una fila en la tabla (actualización en tiempo real).
 */
function upsertRow(row) {
  const tbody = document.querySelector("#tbl-facturas tbody");
  if (!tbody) {
    console.warn("tbody de #tbl-facturas no encontrado");
    return;
  }
  const existing = document.querySelector(rowSelector(row.id));
  const html = renderFilaHTML(row);
  if (existing) {
    existing.outerHTML = html;  // actualiza en sitio
  } else {
    tbody.insertAdjacentHTML("afterbegin", html);  // inserta arriba
  }
}

/**
 * Elimina una fila de la tabla por ID (actualización en tiempo real).
 */
function removeRow(id) {
  const tr = document.querySelector(rowSelector(id));
  if (tr) {
    tr.remove();
  }
}

/**
 * Obtiene lista de facturas desde la API con cache-buster y no-store.
 * @param {Object} params - Parámetros de búsqueda/filtrado
 * @param {string} params.q - Búsqueda por número/NIT/razón social (mapeado a 'search' para DRF)
 * @param {string} params.ordering - Ordenamiento (default: "-fecha_emision")
 * @param {number} params.page - Página (default: 1)
 * @param {number} params.page_size - Tamaño de página (default: 10)
 */
async function fetchFacturas(params = {}) {
  const base = API_LIST;
  const defaultParams = { ordering: "-fecha_emision", page: 1, page_size: 10 };
  const apiParams = { ...defaultParams };
  // Mapear 'q' a 'search' para DRF SearchFilter
  if (params.q) {
    apiParams.search = params.q;
  }
  // Copiar otros parámetros
  Object.assign(apiParams, params);
  delete apiParams.q; // Eliminar 'q' ya que lo mapeamos a 'search'
  
  const qs = new URLSearchParams(apiParams);
  qs.set("_", Date.now());  // cache-buster
  const res = await fetch(`${base}?${qs.toString()}`, {
    headers: { "Accept": "application/json" },
    cache: "no-store"  // evita caché del navegador
  });
  if (!res.ok) throw new Error("No se pudo obtener facturas");
  return await res.json();
}

/**
 * Renderiza una fila de factura en la tabla (helper para loadTabla).
 */
function renderFila(tbody, row) {
  const html = renderFilaHTML(row);
  tbody.insertAdjacentHTML("beforeend", html);
}

/**
 * Carga y renderiza la tabla de facturas.
 * @param {Object} params - Parámetros de búsqueda/filtrado (opcional)
 */
export async function loadTabla(params = {}) {
  try {
    const data = await fetchFacturas(params);
    const items = data.results || data;
    const tbody = document.querySelector("#tbl-facturas tbody");
    if (!tbody) {
      console.warn("tbody de #tbl-facturas no encontrado");
      return;
    }
    tbody.innerHTML = "";
    items.forEach(row => renderFila(tbody, row));
  } catch (error) {
    console.error("Error al cargar facturas:", error);
    showImportError({ code: "load_error", message: "No se pudo cargar la lista de facturas." });
  }
}

/**
 * Elimina una factura (rollback de error de carga).
 * FORÉNSICA: Logs de diagnóstico.
 * Actualiza UI en tiempo real sin recargar página.
 */
async function eliminarFactura(id) {
  console.debug("[delete/forensics] deleting factura:", { id, hasCsrfToken: !!csrftoken });
  
  const res = await fetch(`${API_LIST}${id}/`, {
    method: "DELETE",
    headers: { "X-CSRFToken": csrftoken || "", "Accept": "application/json" },
    credentials: "same-origin",
    cache: "no-store"
  });
  
  console.debug("[delete/forensics] response:", { status: res.status, ok: res.ok });
  
  if (res.status !== 204) {
    const payload = await res.json().catch(() => null);
    const code = payload?.error || "unknown";
    const message = payload?.message || `Error (${res.status})`;
    console.warn("[delete/forensics] error:", { code, message, status: res.status });
    showImportError({ code, message });
    throw new Error(`${code}: ${message}`);
  }
  
  // Éxito: actualiza UI en vivo sin recargar página
  removeRow(id);
}

/**
 * Muestra detalle de factura en modal.
 * FORÉNSICA: Logs de diagnóstico.
 */
async function verDetalleFactura(id) {
  console.debug("[detail/forensics] fetching factura:", { id });
  
  try {
    const res = await fetch(`${API_LIST}${id}/`, { headers: { "Accept": "application/json" } });
    console.debug("[detail/forensics] response:", { status: res.status, ok: res.ok });
    
    if (!res.ok) {
      showImportError({ code: "detail_error", message: `Error (${res.status})` });
      return;
    }
    const row = await res.json();
    console.debug("[detail/forensics] success:", { numero: row.numero, id: row.id });
    
    // Reutiliza el import-error-modal para mostrar un "detalle" rápido (o crea uno específico)
    const detailMsg = `Factura ${row.numero || "N/A"} — ${row.emisor_razon_social || "N/A"}\n` +
      `Receptor: ${row.receptor_razon_social || "N/A"}\n` +
      `Total: ${fmtMoney(row.total, row.moneda)}\n` +
      `Fecha: ${row.fecha_emision || "N/A"}`;
    showImportError({ code: `detalle:${row.id}`, message: detailMsg });
  } catch (error) {
    console.error("[detail/forensics] error:", error);
    showImportError({ code: "detail_error", message: "No se pudo obtener el detalle de la factura." });
  }
}

/**
 * Vincula eventos de UI.
 */
function bindUI() {
  // Abrir modal importar
  const btnOpen = document.getElementById("btn-importar-ubl");
  const modal = document.getElementById("import-modal");
  const input = document.getElementById("input-ubl-file");
  const btnConfirm = document.getElementById("btn-confirm-import");
  const btnCancel = document.getElementById("btn-cancel-import");
  
  btnOpen?.addEventListener("click", () => {
    if (window.bootstrap && bootstrap.Modal) {
      const modalInstance = new bootstrap.Modal(modal);
      modalInstance.show();
    } else {
      modal.style.display = "block";
      modal.classList.add("show");
    }
  });
  
  btnCancel?.addEventListener("click", () => {
    if (window.bootstrap && bootstrap.Modal) {
      const modalInstance = bootstrap.Modal.getInstance(modal);
      modalInstance?.hide();
    } else {
      modal.style.display = "none";
      modal.classList.remove("show");
    }
  });
  
  btnConfirm?.addEventListener("click", async () => {
    try {
      const payload = await importarUblDesdeInput({ inputFileEl: input, preview: false });
      // importarUblDesdeInput ya hace upsertRow() si payload.id existe
      // Solo recargamos si no hay payload.id (caso edge)
      if (!payload || !payload.id) {
        await loadTabla();
      }
    } catch (e) {
      // Ya mostramos modal error en importarUblDesdeInput
    } finally {
      if (window.bootstrap && bootstrap.Modal) {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        modalInstance?.hide();
      } else {
        modal.style.display = "none";
        modal.classList.remove("show");
      }
      // Limpiar input
      if (input) input.value = "";
    }
  });

  // Acciones ver/eliminar en la tabla
  const tbl = document.getElementById("tbl-facturas");
  tbl?.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button[data-action]");
    if (!btn) return;
    const id = btn.getAttribute("data-id");
    const action = btn.getAttribute("data-action");
    
    if (action === "eliminar") {
      if (!confirm("⚠️ Esta factura será eliminada solo del sistema SINTEL por error de carga. Esta acción es irreversible.")) {
        return;
      }
      try {
        await eliminarFactura(id);
        // eliminarFactura ya hace removeRow() en caso de éxito
        // No necesitamos recargar toda la tabla
      } catch (e) {
        // Ya mostramos modal error en eliminarFactura
      }
    }
    
    if (action === "ver") {
      await verDetalleFactura(id);
    }
  });
}

/**
 * Crea factura de prueba (smoke test).
 */
export async function crearSmoke() {
  // Función placeholder para smoke test
  console.info("[smoke] Crear factura de prueba - no implementado aún");
  alert("Función de creación de prueba no implementada aún.");
}

/**
 * Carga estado del módulo.
 * @returns {Promise<string>} HTML con el estado
 */
export async function cargarEstado() {
  try {
    const data = await fetchFacturas({ page_size: 1 });
    const total = data.count || 0;
    return `
      <div class="mb-2"><strong>Total de facturas:</strong> ${total}</div>
      <div class="mb-2"><strong>Servicio:</strong> Activo</div>
      <div class="mb-2"><strong>Upload:</strong> Funcional</div>
      <div class="mb-2"><strong>Visualización:</strong> Funcional</div>
      <div><strong>Eliminación:</strong> Funcional</div>
    `;
  } catch (error) {
    return `<div class="text-danger">Error al cargar estado: ${error.message}</div>`;
  }
}

/**
 * Abre el modal de importación UBL (compatibilidad hacia atrás).
 */
window.openUblModal = function() {
  const modal = document.getElementById("import-modal");
  if (modal && window.bootstrap) {
    new bootstrap.Modal(modal).show();
  }
};

/**
 * Inicializa el módulo de facturas.
 */
export async function initFacturas() {
  // Mostrar la tabla si está oculta
  const tbl = document.getElementById("tbl-facturas");
  if (tbl && tbl.style.display === "none") {
    tbl.style.display = "";
  }
  // Ocultar la tabla DataTables si existe (evitar duplicados)
  const tbDataTables = document.getElementById("tb-facturas");
  if (tbDataTables) {
    tbDataTables.style.display = "none";
  }
  
  bindUI();
  await loadTabla();
  
  // Exponer funciones globalmente para compatibilidad con scripts inline
  window.loadTabla = loadTabla;
  window.importarUblDesdeInput = importarUblDesdeInput;
  window.crearSmoke = crearSmoke;
  window.cargarEstado = cargarEstado;
  
  // Compatibilidad hacia atrás: redirigir handlers legacy al nuevo modal
  document.getElementById("btn-ubl-import")?.addEventListener("click", () => {
    // Redirigir al nuevo modal si existe
    if (typeof window.openUblModal === "function") {
      window.openUblModal();
    }
  });
}
