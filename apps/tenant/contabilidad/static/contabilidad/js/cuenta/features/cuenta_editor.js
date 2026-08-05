/**
 * cuenta_editor.js - Feature Editor para CuentaContable v2.60
 * ⚠️ Feature-Sliced Design: Encargado exclusivamente del ciclo de vida del Offcanvas (abrir, recolectar FormData, guardar)
 * ⚠️ Error Boundary: Todo el manejo de errores (400, 422, 500) DEBE delegarse al UIManager y error_injector.js
 * ⚠️ PROHIBIDO: Uso de alert() o manejo manual de errores
 * 
 * Dependencias globales requeridas:
 * - CuentaAPI (definido en cuenta.api.js)
 * - UIManager (definido en ui-manager.js)
 * - CuentaList (definido en cuenta_list.js) - Para refrescar tabla después de guardar
 */
(function (w, d) {
  'use strict';

  const MOD = '[cuenta.editor]';
  const OFFCANVAS_CONTAINER_ID = '#offcanvas-container-cuenta';
  const ERROR_CONTAINER_ID = '#error-container-cuenta';

  /**
   * Recolecta los datos del formulario y los convierte a objeto JSON
   * @param {string} formId - ID del formulario
   * @returns {Object} Datos del formulario
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
      if (key === 'id') {
        // Ignorar ID en creación
        continue;
      } else if (key === 'activa') {
        // Convertir string 'true'/'false' a boolean
        data[key] = value === 'true' || value === true;
      } else if (key === 'cuenta_padre') {
        // Convertir a int o null
        data[key] = value && value.trim() ? parseInt(value) : null;
      } else if (key === 'codigo' || key === 'nombre' || key === 'tipo' || key === 'descripcion') {
        // Campos de texto: trim y validar
        data[key] = value ? value.trim() : (key === 'descripcion' ? '' : null);
      } else {
        data[key] = value || null;
      }
    }
    
    // ⚠️ v2.60: El backend obtiene automáticamente la empresa del tenant (singleton)
    // No enviar 'empresa' en el payload
    delete data.empresa;

    return data;
  }

  /**
   * Cierra el offcanvas activo
   * @param {string} offcanvasId - ID del offcanvas
   */
  function closeOffcanvas(offcanvasId) {
    const offcanvasEl = d.querySelector(offcanvasId);
    if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
      const offcanvas = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
      if (offcanvas) {
        offcanvas.hide();
      }
    }
  }

  /**
   * Maneja el guardado de una cuenta (crear o actualizar)
   * ⚠️ Error Boundary: Errores delegados a UIManager
   */
  async function handleSave(mode) {
    const formId = mode === 'create' ? '#form-cuenta-crear' : '#form-cuenta-editar';
    const offcanvasId = mode === 'create' ? '#offcanvas-cuenta-crear' : '#offcanvas-cuenta-editar';
    
    if (!w.CuentaAPI) {
      console.error(MOD, 'CuentaAPI no está disponible');
      return;
    }

    const data = collectFormData(formId);
    if (!data) return;

    try {
      let result;
      if (mode === 'create') {
        result = await w.CuentaAPI.create(data);
      } else {
        const id = d.querySelector('#input-id')?.value;
        if (!id) {
          console.error(MOD, 'ID de cuenta no encontrado para actualización');
          return;
        }
        result = await w.CuentaAPI.update(parseInt(id), data);
      }

      // Éxito: Recargar tabla y cerrar offcanvas
      if (w.CuentaList && typeof w.CuentaList.reload === 'function') {
        w.CuentaList.reload();
      }

      closeOffcanvas(offcanvasId);

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success(mode === 'create' ? 'Cuenta creada correctamente' : 'Cuenta actualizada correctamente');
      }
    } catch (error) {
      // ⚠️ Error Boundary: Delegar manejo de errores a error_injector.js o UIManager
      console.error(MOD, 'Error guardando cuenta:', error);
      
      // ⚠️ v2.60: Manejo estructurado de errores de DRF (ValidationError)
      // El error lanzado por cuenta.api.js tiene: status, data, response
      if (error && typeof error === 'object' && 'status' in error && 'data' in error) {
        // Error estructurado de http.js (422 con detalles de validación)
        // Construir un objeto XHR simulado para ErrorHandler.show()
        if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
          const mockXHR = {
            status: error.status,
            statusText: error.status === 422 ? 'Unprocessable Entity' : 'Error',
            response: JSON.stringify(error.data),
            responseText: JSON.stringify(error.data)
          };
          w.ErrorHandler.show(mockXHR);
        } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          const errorDetail = {
            xhr: {
              status: error.status,
              responseText: JSON.stringify(error.data)
            }
          };
          w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
        } else if (w.SintelFeedback) {
          const msg = error.data?.message || error.data?.detail || 'Error al guardar la cuenta.';
          w.SintelFeedback.error(msg);
        }
      } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: error.status || 500,
            responseText: typeof error === 'string' ? error : JSON.stringify(error)
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al guardar la cuenta. Por favor, intente nuevamente.');
      }
    }
  }

  /**
   * Maneja la eliminación de una cuenta
   * ⚠️ Error Boundary: Errores delegados a UIManager
   */
  async function handleDelete(id) {
    if (!id) {
      console.error(MOD, 'ID de cuenta requerido');
      return;
    }

    if (!w.CuentaAPI) {
      console.error(MOD, 'CuentaAPI no está disponible');
      return;
    }

    try {
      await w.CuentaAPI.delete(id);

      // Éxito: Recargar tabla
      if (w.CuentaList && typeof w.CuentaList.reload === 'function') {
        w.CuentaList.reload();
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Cuenta eliminada correctamente');
      }
    } catch (error) {
      // ⚠️ Error Boundary: Delegar manejo de errores a ErrorHandler o UIManager
      console.error(MOD, 'Error eliminando cuenta:', error);
      
      // ⚠️ v2.60: Manejo estructurado de errores de DRF
      if (error && typeof error === 'object' && 'status' in error && 'data' in error) {
        // Construir un objeto XHR simulado para ErrorHandler.show()
        if (w.ErrorHandler && typeof w.ErrorHandler.show === 'function') {
          const mockXHR = {
            status: error.status,
            statusText: error.status === 422 ? 'Unprocessable Entity' : 'Error',
            response: JSON.stringify(error.data),
            responseText: JSON.stringify(error.data)
          };
          w.ErrorHandler.show(mockXHR);
        } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          const errorDetail = {
            xhr: {
              status: error.status,
              responseText: JSON.stringify(error.data)
            }
          };
          w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
        } else if (w.SintelFeedback) {
          w.SintelFeedback.error(error.data?.message || error.data?.detail || 'Error al eliminar la cuenta.');
        }
      } else if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: error.status || 500,
            responseText: typeof error === 'string' ? error : JSON.stringify(error)
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al eliminar la cuenta. Por favor, intente nuevamente.');
      }
    }
  }

  /**
   * Event delegation para botones de guardado
   */
  function attachEditorListeners() {
    // Guardar crear
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-guardar-cuenta-crear');
      if (btn) {
        ev.preventDefault();
        handleSave('create');
      }
    });

    // Guardar editar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-guardar-cuenta-editar');
      if (btn) {
        ev.preventDefault();
        handleSave('update');
      }
    });
  }

  /**
   * Inicialización
   */
  function init() {
    // Guard: attachEditorListeners() registra listeners delegados en `document`
    // — sin este guard, cada recarga HTMX del modulo "cuenta" vuelve a ejecutar
    // este script y duplica los listeners globales (FE-A1/A2).
    if (d.body.dataset.cuentaEditorInitialized) return;
    d.body.dataset.cuentaEditorInitialized = 'true';

    attachEditorListeners();
  }

  // Inicializar cuando el DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Exportar API pública
  if (typeof w !== 'undefined') {
    w.CuentaEditor = Object.freeze({
      save: handleSave,
      delete: handleDelete,
      closeOffcanvas: closeOffcanvas
    });
  }
})(window, document);
