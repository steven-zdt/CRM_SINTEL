/**
 * Modal para agregar/guardar XML (texto o archivo).
 * 
 * ⚠️ v2.61.1: Actualizado para usar Core API facade de facturas
 */

(function() {
  'use strict';

  // ⚠️ v2.61.1: Usar upload-ubl en lugar de upload-document (no requiere feature flag)
  const UPLOAD_DOCUMENT_API = '/api/v1/core/v1/facturas/facturas/upload-ubl/?async=false';  // Core API facade
  const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function showFeedback(message, type = 'info') {
    const el = document.getElementById('feedback-xml-import');
    if (!el) return;
    
    el.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : type === 'warning' ? 'warning' : 'info'}`;
    el.textContent = message;
    el.classList.remove('d-none');
    el.setAttribute('aria-live', 'polite');
  }

  function hideFeedback() {
    const el = document.getElementById('feedback-xml-import');
    if (!el) return;
    el.classList.add('d-none');
    el.textContent = '';
  }

  function showToast(message, type = 'info') {
    const toast = document.getElementById('toast-feedback');
    const toastBody = document.getElementById('toast-body');
    if (!toast || !toastBody) return;

    toastBody.textContent = message;
    const bgClass = type === 'success' ? 'success' : type === 'error' ? 'danger' : 'dark';
    toast.className = `toast align-items-center text-bg-${bgClass} border-0`;
    
    if (window.bootstrap && bootstrap.Toast) {
      const bsToast = new bootstrap.Toast(toast);
      bsToast.show();
    }
  }

  function validateXmlText(text) {
    if (!text || !text.trim()) {
      return { valid: false, message: 'El texto XML no puede estar vacío.' };
    }
    if (!text.includes('<Invoice') && !text.includes('<invoice')) {
      return { valid: false, message: 'El texto no parece contener un XML de factura UBL válido (debe contener <Invoice).' };
    }
    return { valid: true };
  }

  function validateXmlFile(file) {
    if (!file) {
      return { valid: false, message: 'Selecciona un archivo XML.' };
    }
    if (!file.name.toLowerCase().endsWith('.xml')) {
      return { valid: false, message: 'El archivo debe tener extensión .xml' };
    }
    const validTypes = ['text/xml', 'application/xml', 'application/xhtml+xml'];
    if (file.type && !validTypes.includes(file.type) && !file.type.startsWith('text/')) {
      return { valid: false, message: 'El archivo debe ser un XML válido.' };
    }
    if (file.size > MAX_FILE_SIZE) {
      return { valid: false, message: `El archivo es demasiado grande (máximo ${MAX_FILE_SIZE / 1024 / 1024}MB).` };
    }
    return { valid: true };
  }

  async function importFromText(xmlText) {
    const validation = validateXmlText(xmlText);
    if (!validation.valid) {
      showFeedback(validation.message, 'error');
      return false;
    }

    showFeedback('Importando XML...', 'info');

    try {
      // ⚠️ v2.36: Convertir texto XML a File y usar endpoint universal
      const blob = new Blob([xmlText], { type: 'application/xml' });
      const file = new File([blob], 'factura.xml', { type: 'application/xml' });
      
      const formData = new FormData();
      formData.append('file', file);
      
      const csrftoken = getCookie('csrftoken');
      const res = await fetch(UPLOAD_DOCUMENT_API, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: formData
      });

      const data = await res.json();

      if (res.ok) {
        if (data.persisted) {
          showFeedback('XML importado correctamente.', 'success');
          showToast('XML importado', 'success');
        } else {
          showFeedback('XML procesado en modo preview.', 'info');
          showToast('XML procesado (preview)', 'info');
        }
        
        // Disparar evento para refrescar tabla de facturas
        window.dispatchEvent(new CustomEvent('facturas:refresh'));
        
        return true;
      } else {
        const msg = data.message || data.detail || 'Error desconocido';
        if (res.status === 409 || msg.toLowerCase().includes('duplicate') || msg.toLowerCase().includes('ya existe')) {
          showFeedback('Documento duplicado (409).', 'warning');
          showToast('Documento duplicado', 'warning');
        } else if (res.status === 422) {
          showFeedback(`Documento inválido (422): ${escapeHtml(msg)}`, 'error');
          showToast('Error de validación', 'error');
        } else if (res.status === 415) {
          showFeedback('Formato no soportado (415).', 'error');
          showToast('Formato no soportado', 'error');
        } else if (res.status === 400) {
          showFeedback(`Error de parsing (400): ${escapeHtml(msg)}`, 'error');
          showToast('Error al parsear', 'error');
        } else {
          showFeedback(`Error: ${escapeHtml(msg)}`, 'error');
          showToast('Error al importar XML', 'error');
        }
        return false;
      }
    } catch (err) {
      console.error('[maildigester.xml] Error importando desde texto:', err);
      showFeedback(`Error de red: ${err.message}`, 'error');
      showToast('Error al importar XML', 'error');
      return false;
    }
  }

  async function importFromFile(file) {
    const validation = validateXmlFile(file);
    if (!validation.valid) {
      showFeedback(validation.message, 'error');
      return false;
    }

    showFeedback('Subiendo archivo XML...', 'info');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const csrftoken = getCookie('csrftoken');
      const res = await fetch(UPLOAD_DOCUMENT_API, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: formData
      });

      const data = await res.json();

      if (res.ok) {
        if (data.persisted) {
          showFeedback('Archivo XML importado correctamente.', 'success');
          showToast('XML importado', 'success');
        } else {
          showFeedback('Archivo procesado en modo preview.', 'info');
          showToast('XML procesado (preview)', 'info');
        }
        
        // Disparar evento para refrescar tabla de facturas
        window.dispatchEvent(new CustomEvent('facturas:refresh'));
        
        return true;
      } else {
        const msg = data.message || data.detail || 'Error desconocido';
        if (res.status === 409 || msg.toLowerCase().includes('duplicate') || msg.toLowerCase().includes('ya existe')) {
          showFeedback('Documento duplicado (409).', 'warning');
          showToast('Documento duplicado', 'warning');
        } else if (res.status === 422) {
          showFeedback(`Documento inválido (422): ${escapeHtml(msg)}`, 'error');
          showToast('Error de validación', 'error');
        } else if (res.status === 415) {
          showFeedback('Formato no soportado (415).', 'error');
          showToast('Formato no soportado', 'error');
        } else if (res.status === 400) {
          showFeedback(`Error de parsing (400): ${escapeHtml(msg)}`, 'error');
          showToast('Error al parsear', 'error');
        } else {
          showFeedback(`Error: ${escapeHtml(msg)}`, 'error');
          showToast('Error al importar XML', 'error');
        }
        return false;
      }
    } catch (err) {
      console.error('[maildigester.xml] Error importando desde archivo:', err);
      showFeedback(`Error de red: ${err.message}`, 'error');
      showToast('Error al importar XML', 'error');
      return false;
    }
  }

  async function saveXml() {
    hideFeedback();

    const activeTab = document.querySelector('#xml-modal-tabs .nav-link.active');
    const isTextTab = activeTab?.id === 'tab-xml-text';

    if (isTextTab) {
      const textarea = document.getElementById('input-ubl-text');
      const xmlText = textarea?.value?.trim() || '';
      const success = await importFromText(xmlText);
      if (success) {
        // Limpiar textarea y cerrar modal después de un delay
        setTimeout(() => {
          if (textarea) textarea.value = '';
          const modalEl = document.getElementById('modal-mail-xml');
          if (modalEl && window.bootstrap && bootstrap.Modal) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
          }
          hideFeedback();
        }, 1500);
      }
    } else {
      const fileInput = document.getElementById('input-ubl-file');
      const file = fileInput?.files?.[0];
      const success = await importFromFile(file);
      if (success) {
        // Limpiar input y cerrar modal después de un delay
        setTimeout(() => {
          if (fileInput) fileInput.value = '';
          const modalEl = document.getElementById('modal-mail-xml');
          if (modalEl && window.bootstrap && bootstrap.Modal) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
          }
          hideFeedback();
        }, 1500);
      }
    }
  }

  function openModal() {
    const modalEl = document.getElementById('modal-mail-xml');
    if (!modalEl) {
      console.error('[maildigester.xml] Modal no encontrado');
      return;
    }

    // Limpiar formulario
    const textarea = document.getElementById('input-ubl-text');
    const fileInput = document.getElementById('input-ubl-file');
    if (textarea) textarea.value = '';
    if (fileInput) fileInput.value = '';
    hideFeedback();

    // Mostrar modal
    if (window.bootstrap && bootstrap.Modal) {
      const modal = new bootstrap.Modal(modalEl);
      modal.show();

      // Gestionar foco al abrir
      modalEl.addEventListener('shown.bs.modal', () => {
        const firstInput = modalEl.querySelector('textarea, input[type="file"]');
        if (firstInput) {
          firstInput.focus();
        }
      }, { once: true });
    }
  }

  // Inicialización
  document.addEventListener('DOMContentLoaded', () => {
    const btnSave = document.getElementById('btn-save-xml');
    if (btnSave && !btnSave.dataset.listenerAttached) {
      btnSave.addEventListener('click', saveXml);
      btnSave.dataset.listenerAttached = 'true';
    }

    // Manejar cambio de pestañas
    const tabButtons = document.querySelectorAll('#xml-modal-tabs .nav-link');
    tabButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = btn.getAttribute('data-bs-target');
        const textSection = document.getElementById('import-text-section');
        const fileSection = document.getElementById('import-file-section');
        
        if (targetId === '#tab-xml-text') {
          if (textSection) textSection.style.display = 'block';
          if (fileSection) fileSection.style.display = 'none';
        } else {
          if (textSection) textSection.style.display = 'none';
          if (fileSection) fileSection.style.display = 'block';
        }
      });
    });
  });

  // Exponer funciones globales
  if (typeof window !== 'undefined') {
    window.maildigesterXml = {
      openModal: openModal,
      saveXml: saveXml,
      importFromText: importFromText,
      importFromFile: importFromFile
    };
  }
})();
