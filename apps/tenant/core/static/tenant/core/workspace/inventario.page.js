// apps/tenant/core/static/tenant/core/workspace/inventario.page.js
// Helper CSRF
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

// INVENTARIO API (no Core)
const API_BASE = "/api/v1/inventario";

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

async function apiPost(path, data) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken") || "",
    },
    body: JSON.stringify(data || {})
  });
  if (!res.ok) {
    let msg = "";
    try { msg = await res.text(); } catch (e) {}
    throw new Error(`POST ${path} -> ${res.status} ${msg}`);
  }
  return res.json();
}

// --- UI logic ---
async function cargarResumen() {
  const data = await apiGet("/catalogo/resumen/"); // NUEVO endpoint directo
  const el = document.querySelector("#inv-resumen");
  if (!el) return;
  el.innerHTML = `
    <div class="row g-2">
      <div class="col"><div class="card p-2"><b>Productos</b><div>${data.conteo.productos}</div></div></div>
      <div class="col"><div class="card p-2"><b>Servicios</b><div>${data.conteo.servicios}</div></div></div>
      <div class="col"><div class="card p-2"><b>Stock total</b><div>${data.stock_total}</div></div></div>
    </div>
    <div class="mt-3">
      <b>Últimos movimientos</b>
      <ul class="list-group">
        ${data.ultimos_movimientos.map(m => `<li class="list-group-item">
          [${m.tipo}] ${m.catalogo__codigo} - ${m.catalogo__nombre} x ${m.cantidad}
        </li>`).join("")}
      </ul>
    </div>
  `;
}

async function cargarCatalogo() {
  const tabla = document.querySelector("#inv-catalogo tbody");
  if (!tabla) return;
  const search = document.querySelector("#inv-buscar")?.value || "";
  const url = search ? `/catalogo/?search=${encodeURIComponent(search)}&limit=50` : `/catalogo/?limit=50`;
  const data = await apiGet(url);
  // data es un listado paginado si usas DRF PageNumberPagination, ajusta según tu paginator
  const results = Array.isArray(data) ? data : (data.results || []);
  tabla.innerHTML = results.map(r => `
    <tr>
      <td>${r.id}</td>
      <td>${r.tipo}</td>
      <td>${r.codigo}</td>
      <td>${r.nombre}</td>
      <td class="text-end">${r.precio_lista}</td>
      <td>${r.activo ? "Sí" : "No"}</td>
      <td><button class="btn btn-sm btn-outline-primary" data-id="${r.id}" data-codigo="${r.codigo}" data-accion="stock">Stock</button></td>
    </tr>
  `).join("");
}

async function mostrarStock(id) {
  const data = await apiGet(`/catalogo/${id}/stock/`);
  alert(`Stock de ${id}: ${data.stock}`);
}

async function registrarEntrada() {
  const id = Number(prompt("ID catálogo (PRODUCTO):"));
  const cant = prompt("Cantidad:");
  const ref = prompt("Referencia (opcional):") || null;
  if (!id || !cant) return;
  // En la API de inventario, definimos el endpoint de entrada bajo ItemFacturaCatalogoViewSet
  // con url_path="registrar-entrada": /vinculos/item-catalogo/registrar-entrada/
  await apiPost("/vinculos/item-catalogo/registrar-entrada/", {
    catalogo: id,
    cantidad: cant,
    referencia: ref
  });
  await cargarResumen();
}

// --- Smoke test (DEBUG + staff/superuser) ---
async function runInventarioSmoke() {
  try {
    // El smoke test está en Core API, no en inventario directo
    const csrf = getCookie("csrftoken") || "";
    const res = await fetch("/api/v1/core/inventario/smoke/run/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
      },
      body: JSON.stringify({})
    });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(`POST /smoke/run/ -> ${res.status} ${msg}`);
    }
    const data = await res.json();
    renderSmokeResult(data);
  } catch (err) {
    alert("No se pudo ejecutar el smoke test: " + err.message);
  }
}

function renderSmokeResult(res) {
  const box = document.querySelector("#inv-smoke-result");
  if (!box) return;
  if (!res || !Array.isArray(res.steps)) {
    box.innerHTML = `<div class="alert alert-danger">Formato de respuesta inválido.</div>`;
    return;
  }
  const badge = (ok, skipped) => skipped ? `<span class="badge text-bg-secondary">SKIPPED</span>` :
    ok ? `<span class="badge text-bg-success">OK</span>` : `<span class="badge text-bg-danger">FAIL</span>`;
  const items = res.steps.map(s => `
    <li class="list-group-item d-flex justify-content-between align-items-start">
      <div>
        <div><b>${s.step}</b></div>
        ${s.detail ? `<small class="text-muted">${s.detail}</small>` : ""}
      </div>
      <div>${badge(s.ok, s.skipped)}</div>
    </li>
  `).join("");
  box.innerHTML = `
    <div class="card">
      <div class="card-header d-flex justify-content-between">
        <div><b>Inventario - Smoke Test</b></div>
        <div>${res.success ? '<span class="badge text-bg-success">SUCCESS</span>' : '<span class="badge text-bg-danger">FAILED</span>'}</div>
      </div>
      <ul class="list-group list-group-flush">${items}</ul>
    </div>`;
}

document.addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-accion]");
  if (!btn) return;
  const accion = btn.dataset.accion;
  const id = Number(btn.dataset.id);
  if (accion === "stock") mostrarStock(id);
});

document.addEventListener("DOMContentLoaded", async () => {
  await cargarResumen();
  await cargarCatalogo();
  const btnBuscar = document.querySelector("#inv-btn-buscar");
  if (btnBuscar) btnBuscar.addEventListener("click", cargarCatalogo);
  const btnEntrada = document.querySelector("#inv-btn-entrada");
  if (btnEntrada) btnEntrada.addEventListener("click", registrarEntrada);
  const btnSmoke = document.querySelector("#inv-btn-smoke");
  if (btnSmoke) btnSmoke.addEventListener("click", runInventarioSmoke);
});

// Exponer funciones globalmente para que hydrateView pueda llamarlas
window.cargarResumen = cargarResumen;
window.cargarCatalogo = cargarCatalogo;
