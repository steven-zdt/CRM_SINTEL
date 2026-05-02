/**
 * periodos_form.js - Manejo de Formularios de Períodos Contables v2.61
 * ⚠️ Feature-Sliced Design: Script dedicado exclusivamente para formularios de PeriodoContable
 * ⚠️ Namespace: window.PeriodosForm
 * 
 * Funcionalidades:
 * 1. Validación de formulario
 * 2. Sincronización de campos
 * 3. Manejo de envío (POST/PATCH)
 * 4. Manejo de errores
 */

(function (w, d) {
  'use strict';

  const MOD = '[periodos.form]';
  const API_URL = '/api/v1/contabilidad/periodos-contables/';
  const FORM_ID = '#form-periodo-crear';
  const ERROR_CONTAINER_ID = '#error-container-periodos';

  console.log(`%c${MOD} ✅ Módulo cargado`, 'color: #51cf66; font-weight: bold; font-size: 12px;');

  /**
   * Objeto PeriodosForm - Namespace principal
   */
  const PeriodosForm = {
    /**
     * Inicializar módulo
     */
    init: function () {
      console.log(`${MOD} Inicializando...`);
      
      this.bindEvents();
      
      console.log(`${MOD} ✅ Inicialización completada`);
    },

    /**
     * Vincular eventos
     */
    bindEvents: function () {
      // Delegación: Envío de formulario
      d.addEventListener('submit', (e) => {
        if (e.target.id === 'form-periodo-crear' || e.target.id === 'form-periodo-editar') {
          e.preventDefault();
          this.handleSubmit(e.target);
        }
      });

      console.log(`${MOD} Eventos vinculados`);
    },

    /**
     * Validar formulario
     */
    validate: function (form) {
      console.log(`${MOD} Validando formulario...`);

      const nombre = form.querySelector('[name="nombre"]')?.value || '';
      const fechaInicio = form.querySelector('[name="fecha_inicio"]')?.value || '';
      const fechaFin = form.querySelector('[name="fecha_fin"]')?.value || '';

      // Validaciones básicas
      if (!nombre || typeof nombre !== 'string' || nombre.trim().length === 0) {
        console.error(`${MOD} Nombre es requerido`);
        return false;
      }

      if (!fechaInicio || typeof fechaInicio !== 'string' || fechaInicio.trim().length === 0) {
        console.error(`${MOD} Fecha de inicio es requerida`);
        return false;
      }

      if (!fechaFin || typeof fechaFin !== 'string' || fechaFin.trim().length === 0) {
        console.error(`${MOD} Fecha de fin es requerida`);
        return false;
      }

      // Validar que fecha_fin > fecha_inicio
      const inicio = new Date(fechaInicio);
      const fin = new Date(fechaFin);

      if (fin <= inicio) {
        console.error(`${MOD} Fecha de fin debe ser posterior a fecha de inicio`);
        return false;
      }

      console.log(`${MOD} ✅ Validación completada`);
      return true;
    },

    /**
     * Manejar envío de formulario
     */
    handleSubmit: function (form) {
      console.log(`${MOD} Enviando formulario...`);

      // Validar
      if (!this.validate(form)) {
        console.error(`${MOD} Validación fallida`);
        return;
      }

      // Obtener datos
      const formData = new FormData(form);
      const data = Object.fromEntries(formData);

      // Normalizar datos
      data.nombre = (data.nombre || '').trim();
      data.fecha_inicio = (data.fecha_inicio || '').trim();
      data.fecha_fin = (data.fecha_fin || '').trim();

      console.log(`${MOD} Datos a enviar:`, data);

      // Determinar si es crear o editar
      const uuid = form.dataset.uuid;
      const method = uuid ? 'PATCH' : 'POST';
      const url = uuid ? `${API_URL}${uuid}/` : API_URL;

      // Enviar
      htmx.ajax(method, url, {
        values: data,
        onAfterRequest: (xhr) => {
          if (xhr.status === 201 || xhr.status === 200) {
            console.log(`${MOD} ✅ Período guardado correctamente`);
            
            // Mostrar feedback
            if (w.SintelFeedback) {
              w.SintelFeedback.success('Período guardado correctamente');
            }

            // Cerrar offcanvas
            const offcanvasEl = form.closest('.offcanvas');
            if (offcanvasEl && w.bootstrap && w.bootstrap.Offcanvas) {
              w.bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
            }

            // Recargar tabla
            if (w.PeriodosPage) {
              w.PeriodosPage.reloadTable();
            }
          } else {
            console.error(`${MOD} Error al guardar período:`, xhr);
            
            // Mostrar error
            if (w.UIManager) {
              w.UIManager.handleError(xhr, MOD, { errorContainerSelector: ERROR_CONTAINER_ID });
            }
          }
        }
      });
    },

    /**
     * Debug - Ver estado actual
     */
    debug: function () {
      const form = d.querySelector(FORM_ID);
      console.log(`${MOD} Estado actual:`, {
        form: form ? 'Encontrado' : 'No encontrado',
        nombre: form?.querySelector('[name="nombre"]')?.value || '',
        fechaInicio: form?.querySelector('[name="fecha_inicio"]')?.value || '',
        fechaFin: form?.querySelector('[name="fecha_fin"]')?.value || ''
      });
    }
  };

  /**
   * Exponer en window
   */
  w.PeriodosForm = PeriodosForm;

  /**
   * Inicializar cuando el DOM esté listo
   */
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', () => {
      PeriodosForm.init();
    });
  } else {
    PeriodosForm.init();
  }

  /**
   * Re-inicializar con HTMX
   */
  d.addEventListener('htmx:afterSwap', () => {
    if (d.querySelector(FORM_ID)) {
      PeriodosForm.init();
    }
  });

})(window, document);
