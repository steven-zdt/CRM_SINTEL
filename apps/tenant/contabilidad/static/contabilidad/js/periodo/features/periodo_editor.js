/**
 * periodo_editor.js - Feature Editor para PeriodoContable v2.60
 * ⚠️ Feature-Sliced Design: Encargado exclusivamente del ciclo de vida del Offcanvas (abrir, recolectar FormData, guardar)
 * ⚠️ Error Boundary: Todo el manejo de errores (400, 422, 500) DEBE delegarse al UIManager y error_injector.js
 * ⚠️ PROHIBIDO: Uso de alert() o manejo manual de errores
 * 
 * Dependencias globales requeridas:
 * - PeriodoAPI (definido en periodo.api.js)
 * - UIManager (definido en ui-manager.js)
 * - PeriodoList (definido en periodo_list.js) - Para refrescar tabla después de guardar
 */
(function (w, d) {
  'use strict';

  const MOD = '[periodo.editor]';
  const OFFCANVAS_CONTAINER_ID = '#offcanvas-container-periodo';
  const ERROR_CONTAINER_ID = '#error-container-periodo';

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
      if (key === 'id') continue; // Ignorar ID en creación
      data[key] = value || null;
    }

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
   * Maneja el guardado de un periodo (crear o actualizar)
   * ⚠️ Error Boundary: Errores delegados a UIManager
   */
  async function handleSave(mode) {
    const formId = mode === 'create' ? '#form-periodo-crear' : '#form-periodo-editar';
    const offcanvasId = mode === 'create' ? '#offcanvas-periodo-crear' : '#offcanvas-periodo-editar';
    
    if (!w.PeriodoAPI) {
      console.error(MOD, 'PeriodoAPI no está disponible');
      return;
    }

    const data = collectFormData(formId);
    if (!data) return;

    try {
      let result;
      if (mode === 'create') {
        result = await w.PeriodoAPI.create(data);
      } else {
        const id = d.querySelector('#input-id')?.value;
        if (!id) {
          console.error(MOD, 'ID de periodo no encontrado para actualización');
          return;
        }
        result = await w.PeriodoAPI.update(parseInt(id), data);
      }

      // Éxito: Recargar tabla y cerrar offcanvas
      if (w.PeriodoList && typeof w.PeriodoList.reload === 'function') {
        w.PeriodoList.reload();
      }

      closeOffcanvas(offcanvasId);

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success(mode === 'create' ? 'Periodo creado correctamente' : 'Periodo actualizado correctamente');
      }
    } catch (error) {
      // ⚠️ Error Boundary: Delegar manejo de errores a UIManager
      console.error(MOD, 'Error guardando periodo:', error);
      
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: error.status || 500,
            responseText: typeof error === 'string' ? error : JSON.stringify(error)
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al guardar el periodo. Por favor, intente nuevamente.');
      }
    }
  }

  /**
   * Maneja el cierre de un periodo
   * ⚠️ Error Boundary: Errores delegados a UIManager
   */
  async function handleCerrar(id) {
    if (!id) {
      console.error(MOD, 'ID de periodo requerido');
      return;
    }

    if (!w.PeriodoAPI) {
      console.error(MOD, 'PeriodoAPI no está disponible');
      return;
    }

    const observaciones = prompt('Ingrese observaciones sobre el cierre del periodo (opcional):');
    const data = observaciones ? { observaciones: observaciones } : {};

    try {
      await w.PeriodoAPI.cerrar(id, data);

      // Éxito: Recargar tabla
      if (w.PeriodoList && typeof w.PeriodoList.reload === 'function') {
        w.PeriodoList.reload();
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Periodo cerrado correctamente');
      }
    } catch (error) {
      // ⚠️ Error Boundary: Delegar manejo de errores a UIManager
      console.error(MOD, 'Error cerrando periodo:', error);
      
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: error.status || 500,
            responseText: typeof error === 'string' ? error : JSON.stringify(error)
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al cerrar el periodo. Por favor, intente nuevamente.');
      }
    }
  }

  /**
   * Maneja la eliminación de un periodo
   * ⚠️ Error Boundary: Errores delegados a UIManager
   */
  async function handleDelete(id) {
    if (!id) {
      console.error(MOD, 'ID de periodo requerido');
      return;
    }

    if (!w.PeriodoAPI) {
      console.error(MOD, 'PeriodoAPI no está disponible');
      return;
    }

    try {
      await w.PeriodoAPI.delete(id);

      // Éxito: Recargar tabla
      if (w.PeriodoList && typeof w.PeriodoList.reload === 'function') {
        w.PeriodoList.reload();
      }

      // Mostrar feedback de éxito
      if (w.SintelFeedback) {
        w.SintelFeedback.success('Periodo eliminado correctamente');
      }
    } catch (error) {
      // ⚠️ Error Boundary: Delegar manejo de errores a UIManager
      console.error(MOD, 'Error eliminando periodo:', error);
      
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        const errorDetail = {
          xhr: {
            status: error.status || 500,
            responseText: typeof error === 'string' ? error : JSON.stringify(error)
          }
        };
        w.UIManager.handleError(errorDetail, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
      } else if (w.SintelFeedback) {
        w.SintelFeedback.error('Error al eliminar el periodo. Por favor, intente nuevamente.');
      }
    }
  }

  /**
   * Event delegation para botones de guardado
   */
  function attachEditorListeners() {
    // Guardar crear
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-guardar-periodo-crear');
      if (btn) {
        ev.preventDefault();
        handleSave('create');
      }
    });

    // Guardar editar
    d.addEventListener('click', (ev) => {
      const btn = ev.target.closest('#btn-guardar-periodo-editar');
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
    // — sin este guard, cada recarga HTMX del modulo "periodo" vuelve a ejecutar
    // este script y duplica los listeners globales (FE-A1/A2).
    if (d.body.dataset.periodoEditorInitialized) return;
    d.body.dataset.periodoEditorInitialized = 'true';

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
    w.PeriodoEditor = Object.freeze({
      save: handleSave,
      delete: handleDelete,
      cerrar: handleCerrar,
      closeOffcanvas: closeOffcanvas
    });
  }
})(window, document);
