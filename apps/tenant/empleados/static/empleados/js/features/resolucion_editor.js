// @ts-nocheck
/**
 * Resolucion Editor — CRUD Resoluciones DIAN
 * Namespace: window.Sintel.Empleados.ResolucionEditor
 * Skills: htmx.md §2 | vanilla-js.md §2 | ui-management.md §26
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[ResolucionEditor]';
    const API_BASE   = '/api/v1/empleados/resoluciones-dian/';
    const CONTAINER  = '#offcanvas-container-resoluciones';
    const OC_ID      = 'offcanvas-resolucion-crear';
    const FORM_ID    = 'form-resolucion-crear';
    const BTN_ID     = 'btn-guardar-resolucion-crear';
    const FEEDBACK   = 'form-resolucion-crear-feedback';

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

    // ── Guardar via Sintel.Core.Http (F32.7, antes window.http) ─────────────
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
        // checkbox vigente: si no está en el FormData (unchecked), forzar false
        if (!('vigente' in payload)) payload.vigente = false;
        else payload.vigente = true;

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';
        _ocultarFeedback();

        try {
            // T-9: delega a la SSoT de endpoints (empleados.api.js).
            const res = await w.Sintel.Core.Http.request('POST', w.Sintel.Empleados.API.resoluciones.list, payload);
            if (res.ok) {
                w.UIManager?.notifySuccess('Resolución DIAN creada correctamente');
                _cerrar();
                w.Sintel.Empleados.ResolucionList?.reload();
            } else {
                const errData = res.data || {};
                const msg = errData.detail
                    || Object.values(errData).flat().join(' | ')
                    || 'Error al guardar la resolución';
                _mostrarError(msg);
            }
        } catch (err) {
            console.error(`${MOD} Error al guardar:`, err);
            _mostrarError('Error de conexión. Inténtelo nuevamente.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Crear Resolución';
        }
    }

    // ── Setup del offcanvas recién cargado ────────────────────────────────────
    function _setupOffcanvas(offcanvasEl) {
        const btn = offcanvasEl.querySelector(`#${BTN_ID}`);
        if (btn && !btn.dataset.bound) {
            btn.dataset.bound = '1';
            // Quitar hx-post del botón para que no use HTMX — lo maneja JS
            btn.removeAttribute('hx-post');
            btn.removeAttribute('hx-include');
            btn.removeAttribute('hx-swap');
            btn.removeAttribute('hx-target');
            btn.addEventListener('click', () => _guardar(offcanvasEl));
        }
    }

    // ── Escuchar carga de offcanvas via HTMX (skill: htmx.md §2) ────────────
    // Guard: registrado en `document.body` (persiste entre recargas HTMX del
    // modulo "empleados") — sin este guard, cada recarga del script duplica
    // el listener y `_mostrar`/`_setupOffcanvas` se disparan N veces (FE-A1/A2).
    if (!d.body.dataset.resolucionEmpleadosEditorInitialized) {
        d.body.dataset.resolucionEmpleadosEditorInitialized = 'true';

        d.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail?.target;
            if (!target || target.id !== CONTAINER.replace('#', '')) return;
            const el = target.querySelector('.offcanvas');
            if (!el) return;
            _mostrar(el);
            _setupOffcanvas(el);
        });
    }

    w.Sintel.Empleados.ResolucionEditor = { open };

})(window, document);
