/**
 * OnboardingChecklist (FASE 2, mision UX 2026-08-21) - Progreso de configuracion
 * inicial mostrado en la pantalla de bienvenida del workspace (#workspace-welcome).
 *
 * API-First: solo lee de endpoints REST ya existentes (empresa, empleados,
 * clientes, proveedores, inventario) -- no crea ningun endpoint nuevo ni
 * duplica datos. Vanilla JS, mismo patron que sede_selector.js.
 */
(function (w, d) {
  'use strict';

  const STEPS = [
    { key: 'cuenta', label: 'Tu cuenta esta activa', tab: null },
    { key: 'empresa', label: 'Completa los datos de tu empresa', tab: 'empresa' },
    { key: 'equipo', label: 'Invita a tu equipo', tab: 'empleados' },
    { key: 'clientes', label: 'Registra tu primer cliente', tab: 'clientes' },
    { key: 'proveedores', label: 'Registra tu primer proveedor', tab: 'proveedores' },
    { key: 'inventario', label: 'Carga tu primer producto o servicio', tab: 'inventario' },
  ];

  async function fetchCount(url) {
    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) return 0;
      const data = await resp.json();
      return typeof data.count === 'number' ? data.count : 0;
    } catch (err) {
      console.warn('[OnboardingChecklist] Error consultando', url, err);
      return 0;
    }
  }

  async function fetchEmpresaCompleta() {
    try {
      const resp = await fetch('/api/v1/empresas/mi-empresa/', { credentials: 'same-origin' });
      if (resp.status !== 200) return false;
      const data = await resp.json();
      return Boolean(data.razon_social && data.nit && data.direccion && data.ciudad);
    } catch (err) {
      console.warn('[OnboardingChecklist] Error consultando mi-empresa', err);
      return false;
    }
  }

  function renderStep(step, done) {
    const li = d.createElement('li');
    li.className = 'list-group-item d-flex align-items-center justify-content-between px-0';

    const iconSpan = d.createElement('span');
    iconSpan.className = 'd-flex align-items-center gap-2';
    iconSpan.innerHTML = done
      ? '<i class="bi bi-check-circle-fill text-success" aria-hidden="true"></i>'
      : '<i class="bi bi-circle text-muted" aria-hidden="true"></i>';
    const labelEl = d.createElement('span');
    labelEl.className = done ? 'text-muted text-decoration-line-through' : '';
    labelEl.textContent = step.label;
    iconSpan.appendChild(labelEl);
    li.appendChild(iconSpan);

    if (!done && step.tab) {
      const btn = d.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-sm btn-outline-secondary';
      btn.textContent = 'Configurar';
      btn.addEventListener('click', () => {
        const navLink = d.querySelector(`#nav a[data-tab="${step.tab}"]`);
        if (navLink) navLink.click();
      });
      li.appendChild(btn);
    }

    return li;
  }

  async function init() {
    const card = d.getElementById('onboarding-checklist');
    const list = d.getElementById('onboarding-steps');
    const bar = d.getElementById('onboarding-progress-bar');
    const label = d.getElementById('onboarding-progress-label');
    if (!card || !list || !bar || !label) return;

    const [empresaOk, equipoCount, clientesCount, proveedoresCount, productosCount, serviciosCount] = await Promise.all([
      fetchEmpresaCompleta(),
      fetchCount('/api/v1/empleados/?page_size=1'),
      fetchCount('/api/v1/clientes/?page_size=1'),
      fetchCount('/api/v1/proveedores/?page_size=1'),
      fetchCount('/api/v1/inventario/productos/?page_size=1'),
      fetchCount('/api/v1/inventario/servicios/?page_size=1'),
    ]);

    const doneMap = {
      cuenta: true,
      empresa: empresaOk,
      equipo: equipoCount > 0,
      clientes: clientesCount > 0,
      proveedores: proveedoresCount > 0,
      inventario: (productosCount + serviciosCount) > 0,
    };

    const totalDone = STEPS.reduce((acc, step) => acc + (doneMap[step.key] ? 1 : 0), 0);

    // Ya todo configurado: no insistir, dejar solo el mensaje generico de bienvenida.
    if (totalDone >= STEPS.length) return;

    list.innerHTML = '';
    STEPS.forEach((step) => list.appendChild(renderStep(step, doneMap[step.key])));

    const pct = Math.round((totalDone / STEPS.length) * 100);
    bar.style.width = pct + '%';
    bar.setAttribute('aria-valuenow', String(pct));
    label.textContent = `${totalDone}/${STEPS.length}`;

    card.classList.remove('d-none');
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  w.Sintel = w.Sintel || {};
  w.Sintel.Core = w.Sintel.Core || {};
  w.Sintel.Core.OnboardingChecklist = { init };
})(window, document);
