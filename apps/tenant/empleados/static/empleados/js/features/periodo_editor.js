// @ts-nocheck
/**
 * Periodo Editor — Crear Periodo de Nomina
 * Namespace: window.Sintel.Empleados.PeriodoEditor
 * Skills: htmx.md §2 | vanilla-js.md §2 | ui-management.md §26
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[PeriodoEditor]';
    const API_BASE   = '/api/v1/empleados/periodos-nomina/';
    const CONTAINER  = '#offcanvas-container-periodos';
    const OC_ID      = 'offcanvas-periodo-crear';
    const FORM_ID    = 'form-periodo-crear';
    const BTN_ID     = 'btn-guardar-periodo-crear';
    const FEEDBACK   = 'form-periodo-crear-feedback';

    // ── Abrir offcanvas crear ─────────────────────────────────────────────────
    function open() {
        htmx.ajax('GET', `${API_BASE}render-offcanvas/crear/`, {
            target: CONTAINER,
            swap: 'innerHTML',
        });
    }

    // ── Mostrar offcanvas — UIManager (skill: ui-management.md §26) ──────────
    function _mostrar(el) {
        if (w.UIManager?.handleOffcanvas) {
            w.UIManager.handleOffcanvas(el, 'show');
        } else {
            // SSoT: window.Sintel.Core.mostrarOffcanvasSeguro (AGENTS.md §26 — nunca getOrCreateInstance)
            w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
        }
    }

    function _cerrar() {
        const el = d.getElementById(OC_ID);
        if (!el) return;
        if (w.UIManager?.handleOffcanvas) {
            w.UIManager.handleOffcanvas(el, 'hide');
        } else {
            bootstrap.Offcanvas.getInstance(el)?.hide();
        }
    }

    // ── Mostrar error en el feedback del form ─────────────────────────────────
    function _mostrarError(msg) {
        const fb = d.getElementById(FEEDBACK);
        if (!fb) return;
        fb.textContent = msg;
        fb.classList.remove('d-none', 'alert-success');
        fb.classList.add('alert-danger');
    }

    function _ocultarFeedback() {
        const fb = d.getElementById(FEEDBACK);
        if (fb) fb.classList.add('d-none');
    }

    // ── Guardar via Sintel.Core.Http ─────────────────────────────────────────
    async function _guardar(offcanvasEl) {
        const form = offcanvasEl.querySelector(`#${FORM_ID}`);
        const btn  = offcanvasEl.querySelector(`#${BTN_ID}`);
        if (!form || !btn) return;

        if (!form.checkValidity()) { form.reportValidity(); return; }

        const fd = new FormData(form);
        const payload = {};
        fd.forEach((val, key) => {
            if (key === 'csrfmiddlewaretoken') return;
            payload[key] = val;
        });

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';
        _ocultarFeedback();

        try {
            // T-9: delega a la SSoT de endpoints (empleados.api.js).
            const res = await w.Sintel.Core.Http.request('POST', w.Sintel.Empleados.API.periodos.list, payload);
            if (res.ok) {
                w.UIManager?.notifySuccess('Período de nómina creado correctamente');
                _cerrar();
                w.Sintel.Empleados.PeriodoList?.reload();
            } else {
                const errData = res.data || {};
                const msg = errData.detail
                    || Object.values(errData).flat().join(' | ')
                    || 'Error al guardar el período';
                _mostrarError(msg);
            }
        } catch (err) {
            console.error(`${MOD} Error al guardar:`, err);
            _mostrarError('Error de conexión. Inténtelo nuevamente.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Crear Período';
        }
    }

    // ── Setup del offcanvas recién cargado ────────────────────────────────────
    function _setupOffcanvas(offcanvasEl) {
        const btn = offcanvasEl.querySelector(`#${BTN_ID}`);
        if (btn && !btn.dataset.bound) {
            btn.dataset.bound = '1';
            btn.addEventListener('click', () => _guardar(offcanvasEl));
        }
    }

    // ── Escuchar carga de offcanvas via HTMX (skill: htmx.md §2) ────────────
    // Guard: registrado en `document.body` — evita listeners duplicados en
    // recargas del modulo "empleados" (mismo patron que ResolucionEditor).
    if (!d.body.dataset.periodoEmpleadosEditorInitialized) {
        d.body.dataset.periodoEmpleadosEditorInitialized = 'true';

        d.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail?.target;
            if (!target || target.id !== CONTAINER.replace('#', '')) return;
            const el = target.querySelector('.offcanvas');
            if (!el) return;
            _mostrar(el);
            _setupOffcanvas(el);
        });
    }

    w.Sintel.Empleados.PeriodoEditor = { open };

})(window, document);
