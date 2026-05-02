/**
 * Synchronized empresa_editor.js (copied from app static)
 */
(function(w, d) {
    'use strict';
    const MOD = '[empresa.editor]';

    function recolectarDatosFormulario() {
        const form = d.querySelector('#form-empresa');
        if (!form) { console.error(`${MOD} Formulario #form-empresa no encontrado`); return null; }
        const formData = new FormData(form);
        const cleanFormData = new FormData();
        for (const [key, value] of formData.entries()) {
            if (value instanceof File) { cleanFormData.append(key, value); }
            else if (value !== '' && value !== null && value !== undefined) { cleanFormData.append(key, value); }
        }
        return cleanFormData;
    }

    async function guardarEmpresa() {
        const data = recolectarDatosFormulario(); if (!data) return;
        const btnGuardar = d.querySelector('#btn-guardar-empresa');
        const btnOriginalText = btnGuardar?.innerHTML || '';
        const btnOriginalDisabled = btnGuardar?.disabled || false;
        if (btnGuardar) { btnGuardar.disabled = true; btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...'; }
        let res = await w.http('PATCH', '/api/v1/core/empresa/', data);
        if (btnGuardar) { btnGuardar.disabled = btnOriginalDisabled; btnGuardar.innerHTML = btnOriginalText; }
        if (!res.ok) { if (w.UIManager && typeof w.UIManager.handleError === 'function') { w.UIManager.handleError(res, MOD, { errorContainerSelector: '#form-empresa-feedback' }); } return; }
        const offcanvasEl = d.querySelector('#offcanvas-empresa'); if (offcanvasEl && typeof bootstrap !== 'undefined') { const inst = bootstrap.Offcanvas.getInstance(offcanvasEl); if (inst) inst.hide(); }
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') w.SintelFeedback.success('Empresa guardada correctamente');
        d.dispatchEvent(new Event('empresaGuardada'));
    }

    function initEditorEvents() {
        const form = d.querySelector('#form-empresa'); if (!form) return;
        const btnGuardar = d.querySelector('#btn-guardar-empresa'); if (btnGuardar) btnGuardar.addEventListener('click', (e)=>{ e.preventDefault(); guardarEmpresa(); });
        form.addEventListener('submit', (e)=>{ e.preventDefault(); guardarEmpresa(); });
    }

    function init() { const offcanvasEl = d.querySelector('#offcanvas-empresa'); if (offcanvasEl) initEditorEvents(); else { const observer = new MutationObserver((mutations)=>{ mutations.forEach((m)=>{ m.addedNodes.forEach((node)=>{ if (node.nodeType===1 && node.id==='offcanvas-empresa') { initEditorEvents(); observer.disconnect(); } }); }); }); const container = d.querySelector('#offcanvas-container-empresa'); if (container) observer.observe(container, { childList: true, subtree: true }); } }

    if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', init); else init();
    if (typeof htmx !== 'undefined') { d.addEventListener('htmx:afterSwap', (event)=>{ if (event.detail.target.id === 'offcanvas-container-empresa') setTimeout(()=>{ initEditorEvents(); },50); }); }

    w.EmpresaEditorModule = { init, guardarEmpresa };
    w.EmpresaModule = w.EmpresaEditorModule;

})(window, document);
