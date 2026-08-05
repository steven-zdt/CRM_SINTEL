// @ts-nocheck
/**
 * Feature: Editor/Formulario — MailInboxConfig v4.2
 * FSD §7.2: modulo independiente por modelo.
 * Maneja: guardado, probar conexion, toggle password, HTMX settle.
 * Namespace: window.MailInboxConfigEditorModule
 */
(function(w, d) {
    'use strict';

    const MOD = '[mailinboxconfig.editor]';
    const CONTAINER_ID = 'offcanvas-container-mailinbox';

    // ── Helpers ───────────────────────────────────────────────────────────────

    function _recolectarPayload(form, isEdit) {
        const fd  = new FormData(form);
        const out = {};
        const boolFields = ['is_active', 'imap_ssl', 'imap_starttls', 'imap_mark_as_seen'];
        const intFields  = ['imap_port', 'imap_max_attachment_mb'];

        for (const [k, v] of fd.entries()) {
            if (k === 'id') continue;
            if (k === 'imap_password' && isEdit && (!v || !v.trim())) continue;
            if (boolFields.includes(k)) { out[k] = (v === 'on'); continue; }
            if (intFields.includes(k))  { out[k] = parseInt(v) || null; continue; }
            out[k] = v || null;
        }

        boolFields.forEach(f => { if (!(f in out)) out[f] = false; });
        return out;
    }

    // ── Inicializar formulario (llamado tras htmx:afterSettle) ────────────────

    function initForm() {
        const offcanvasEl = d.getElementById('offcanvas-mailinbox');
        if (!offcanvasEl) return;

        // Guard (FE-A1): initForm() se programa via setTimeout desde el
        // listener htmx:afterSettle cada vez que se abre el offcanvas.
        if (offcanvasEl.dataset.editorInitialized) return;
        offcanvasEl.dataset.editorInitialized = 'true';

        const form       = d.getElementById('form-mailinbox');
        const btnGuardar = d.getElementById('btn-guardar-mailinbox');
        const btnProbar  = d.getElementById('btn-probar-conexion-mailinbox');
        const configId   = offcanvasEl.dataset.configId || d.getElementById('mailinbox-id')?.value;
        const isEdit     = !!(configId && configId.trim() !== '');

        console.log(`${MOD} init — isEdit=${isEdit}, id=${configId}`);

        // Toggle password visibility
        offcanvasEl.querySelectorAll('.btn-toggle-pwd').forEach(btn => {
            btn.addEventListener('click', () => {
                const inp = d.getElementById(btn.dataset.target);
                if (!inp) return;
                inp.type = inp.type === 'password' ? 'text' : 'password';
                btn.querySelector('i').className = inp.type === 'password' ? 'bi bi-eye' : 'bi bi-eye-slash';
            });
        });

        // Guardar
        if (btnGuardar && form) {
            btnGuardar.addEventListener('click', async () => {
                if (!form.checkValidity()) { form.reportValidity(); return; }

                const prev = btnGuardar.innerHTML;
                btnGuardar.disabled = true;
                btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

                try {
                    const payload = _recolectarPayload(form, isEdit);
                    const method  = isEdit ? 'PATCH' : 'POST';
                    const url     = isEdit
                        ? `/api/v1/empresas/mail-inbox-config/${configId}/`
                        : '/api/v1/empresas/mail-inbox-config/';

                    const resp = await w.http(method, url, payload);

                    if (!resp.ok) {
                        w.UIManager?.notifyError?.(resp, MOD) ??
                        w.SintelFeedback?.error?.(resp.data?.detail || 'Error al guardar');
                        return;
                    }

                    w.UIManager?.notifySuccess?.(isEdit ? 'Configuracion actualizada' : 'Configuracion creada') ??
                    w.SintelFeedback?.success?.(isEdit ? 'Configuracion actualizada' : 'Configuracion creada');

                    bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
                    d.dispatchEvent(new Event('mailinboxConfigGuardado'));

                } catch (err) {
                    console.error(`${MOD} Error guardando:`, err);
                    w.SintelFeedback?.error?.('Error inesperado al guardar');
                } finally {
                    btnGuardar.disabled = false;
                    btnGuardar.innerHTML = prev;
                }
            });
        }

        // Probar conexion
        if (btnProbar && form) {
            btnProbar.addEventListener('click', async () => {
                const resultEl = d.getElementById('test-connection-result');
                const prev = btnProbar.innerHTML;
                btnProbar.disabled = true;
                btnProbar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Probando...';

                try {
                    const fd = new FormData(form);
                    const testPayload = {
                        host:        fd.get('imap_host'),
                        port:        parseInt(fd.get('imap_port')) || 993,
                        protocol:    'imap',
                        username:    fd.get('imap_username'),
                        password:    fd.get('imap_password') || '',
                        use_ssl:     fd.get('imap_ssl')      === 'on',
                        use_starttls: fd.get('imap_starttls') === 'on',
                    };

                    const resp = await w.http('POST', '/api/v1/empresas/mail-inbox-config/test-connection/', testPayload);

                    if (resultEl) {
                        resultEl.classList.remove('d-none');
                        if (resp.ok && resp.data?.ok) {
                            resultEl.className = 'mt-2 alert alert-success small';
                            resultEl.innerHTML = `<i class="bi bi-check-circle me-1"></i>${resp.data.message || 'Conexion exitosa'}`;
                        } else {
                            resultEl.className = 'mt-2 alert alert-danger small';
                            resultEl.innerHTML = `<i class="bi bi-x-circle me-1"></i>${resp.data?.message || resp.data?.detail || 'Error al conectar'}`;
                        }
                    }
                } catch (err) {
                    console.error(`${MOD} Error probando conexion:`, err);
                    if (resultEl) {
                        resultEl.classList.remove('d-none');
                        resultEl.className = 'mt-2 alert alert-danger small';
                        resultEl.innerHTML = `<i class="bi bi-x-circle me-1"></i>Error: ${err.message}`;
                    }
                } finally {
                    btnProbar.disabled = false;
                    btnProbar.innerHTML = prev;
                }
            });
        }
    }

    // ── Listener HTMX: activa el offcanvas y el formulario tras inyeccion ─────

    function setupOffcanvasLoadListener() {
        d.body.addEventListener('htmx:afterSettle', (evt) => {
            const target = evt.detail.target;
            if (!target || target.id !== CONTAINER_ID) return;

            const offcanvasEl = target.querySelector('#offcanvas-mailinbox');
            if (offcanvasEl && w.bootstrap?.Offcanvas) {
                d.querySelectorAll('.offcanvas-backdrop').forEach(function(b) { b.remove(); });
                d.body.classList.remove('overflow-hidden', 'modal-open');
                var prev = bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (prev) prev.dispose();
                new bootstrap.Offcanvas(offcanvasEl).show();
                setTimeout(initForm, 80);
            }
        });
    }

    setupOffcanvasLoadListener();

    w.MailInboxConfigEditorModule = { initForm };

})(window, document);
