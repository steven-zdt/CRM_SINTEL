// apps/tenant/core/static/tenant/core/workspace.js
// Main orchestrator for workspace functionality

import { cargarResumen, wireInventarioUI } from "./inventario/ui.js";
import { initCatalogoCRUD } from "./inventario/catalogo.crud.js";
import { initActivosCRUD } from "./inventario/activos.crud.js";

// Hash navigation helper (simple implementation)
// Nota: El hash navigation principal está en workspace.html, este es solo para inicializar inventario

// Smoke test runner (DEBUG + staff/superuser)
async function runInventarioSmoke() {
  try {
    function getCookie(name) {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
    }
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

function initInventario() {
  const section = document.getElementById("view-inventario");
  if (!section || section.hidden) return;
  
  // Lecturas generales
  cargarResumen().catch(console.error);
  
  // Extras UI listados/acciones
  wireInventarioUI();
  
  // CRUD
  initCatalogoCRUD();
  initActivosCRUD();
  
  // Smoke runner (solo DEBUG)
  const btnSmoke = document.getElementById("inv-btn-smoke");
  if (btnSmoke) {
    btnSmoke.addEventListener("click", runInventarioSmoke);
  }
  
  return Promise.resolve();
}

// Initialize on DOM ready
// Nota: La inicialización principal está en workspace.html (hydrateView)
// Este código solo inicializa inventario cuando se navega a esa sección
document.addEventListener("DOMContentLoaded", () => {
  // Si ya estamos en inventario al cargar, inicializar
  const hash = window.location.hash || "";
  if (hash === "#inventario") {
    initInventario();
  }
  
  // También escuchar cambios de hash
  window.addEventListener("hashchange", () => {
    if (window.location.hash === "#inventario") {
      initInventario();
    }
  });
});

// Exponer funciones globalmente para hydrateView
window.cargarResumen = cargarResumen;
window.initInventario = initInventario;
window.initActivosCRUD = initActivosCRUD;