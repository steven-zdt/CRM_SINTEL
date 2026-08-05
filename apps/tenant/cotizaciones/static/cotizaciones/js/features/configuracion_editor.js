/**
 * configuracion_editor.js - Feature Module para Gestión de Plantillas/Configuración v2.62.0
 */
(function (w, d) {
  'use strict';

  const MOD = '[configuracion.editor]';
  const OFFCANVAS_CREAR_ID = '#offcanvas-container';
  const OFFCANVAS_EDITAR_ID = '#offcanvas-container';
  const FORM_CREAR_ID = '#form-configuracion-crear';
  const FORM_EDITAR_ID = '#form-configuracion-editar';

  /**
   * Recolecta los datos del formulario y los convierte a objeto JSON
   */
  function collectFormData(formId) {
    const form = d.querySelector(formId);
    if (!form) {
      console.error(MOD, 'Formulario no encontrado:', formId);
      return null;
    }

    const formData = new FormData(form);
    const data = {};
    
    for (const [key, value] of formData.entries()) {
      if (key === 'id') continue;
      
      // Manejo de booleanos (Checkboxes)
      if (key === 'es_activo') {
        data[key] = value === 'on' || value === 'true' || value === true;
      } else if (key === 'dias_validez' || key === 'semilla_inicial') {
        data[key] = parseInt(value) || 0;
      } else {
        data[key] = value || '';
      }
    }

    // Si es_activo no está en formData (checkbox desmarcado), ponerlo en false
    if (!data.hasOwnProperty('es_activo') && form.querySelector('input[name="es_activo"]')) {
      data.es_activo = false;
    }

    // ⚠️ v2.62: El backend obtiene empresa_id automáticamente
    delete data.empresa;
    delete data.empresa_id;

    return data;
  }

  /**
   * Maneja el guardado de una configuración
   */
  async function handleSave(mode) {
    const formId = mode === 'create' ? FORM_CREAR_ID : FORM_EDITAR_ID;
    const offcanvasId = mode === 'create' ? OFFCANVAS_CREAR_ID : OFFCANVAS_EDITAR_ID;
    
    const api = w.Sintel?.Cotizaciones?.api;
    if (!api) {
      console.error(MOD, 'API de Cotizaciones no disponible');
      return;
    }

    const data = collectFormData(formId);
    if (!data) return;

    try {
      let response;
      if (mode === 'create') {
        response = await api.createConfiguracion(data);
      } else {
        const uuidInput = d.querySelector(formId + ' input[name="uuid"]') || d.querySelector('#input-config-uuid') || d.querySelector(formId + ' input[name="id"]');
        const uuid = uuidInput ? uuidInput.value : null;
        if (!uuid) throw new Error('UUID de configuración no encontrado');
        response = await api.updateConfiguracion(uuid, data);
      }

      if (response && (response.id || response.uuid)) {
        if (w.UIManager) w.UIManager.showSuccess('Configuración guardada correctamente');
        
        // Refrescar lista si existe
        const listFeature = w.Sintel?.Cotizaciones?.features?.configuracionList;
        if (listFeature && typeof listFeature.reload === 'function') {
          listFeature.reload();
        }

        // Cerrar offcanvas
        if (w.UIManager) w.UIManager.handleOffcanvas(offcanvasId, 'hide');
      }
    } catch (error) {
      console.error(MOD, 'Error al guardar:', error);
      if (w.UIManager) w.UIManager.handleError(error, MOD);
    }
  }

  /**
   * Inicialización de eventos para botones de guardado
   */
  function attachListeners() {
    // Guard en `document.body` (no en el objeto w.Sintel.*.configuracionEditor:
    // ese objeto se redeclara mas abajo en cada carga del script, asi que un
    // flag guardado ahi nunca sobrevive a la siguiente ejecucion — quedaba
    // siempre en false y el guard anterior era un no-op, FE-A1).
    if (d.body.dataset.configuracionEditorInitialized) return;
    d.body.dataset.configuracionEditorInitialized = 'true';

    d.addEventListener('click', function(e) {
      const btnCrear = e.target.closest('#btn-configuracion-crear-submit');
      if (btnCrear) {
        e.preventDefault();
        handleSave('create');
        return;
      }

      const btnEditar = e.target.closest('#btn-configuracion-editar-submit');
      if (btnEditar) {
        e.preventDefault();
        handleSave('update');
        return;
      }
    });
  }

  // Exportar feature
  w.Sintel.Cotizaciones.features.configuracionEditor = {
    init: attachListeners,
    save: handleSave
  };

  // Auto-init
  attachListeners();

})(window, document);
