/**
 * contratos_editar.js - Módulo de Formulario de Contratos (EDITAR) v2.61
 * ⚠️ Feature-Sliced Architecture - Lógica exclusiva para edición de contratos
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ HTMX: Usa HTMX para cargar offcanvas dinámicamente
 * 
 * Dependencias globales requeridas:
 * - w.empleadosAPI (definido en empleados.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - HTMX (cargado globalmente)
 * - Bootstrap (cargado globalmente)
 */
(function (w, d) {
  'use strict';

  const MOD = '[contratos.editar]';
  const OFFCANVAS_ID = 'offcanvas-contrato-editar';
  const OFFCANVAS_CONTAINER_ID = 'offcanvas-container-contrato';
  const API_BASE = '/api/v1/empleados/';
  const CONTRATOS_API = `${API_BASE}contratos/`;

  /**
   * Cargar offcanvas de edición de contrato
   * ⚠️ v2.61: Usa endpoint render-offcanvas/editar
   */
  async function cargarOffcanvasEditarContrato(contratoId) {
    if (!contratoId) {
      console.error(`${MOD} ❌ ID de contrato no proporcionado`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 400, data: { detail: 'Se requiere un ID de contrato para editar.' } },
          MOD
        );
      }
      return;
    }

    const url = `${CONTRATOS_API}${contratoId}/render-offcanvas/editar/`;

    if (typeof htmx === 'undefined' || !htmx.ajax) {
      console.error(`${MOD} ❌ HTMX no está disponible`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: 'HTMX no está disponible. Verifique que la librería se haya cargado correctamente.' } },
          MOD
        );
      }
      return;
    }

    console.log(`${MOD} Cargando offcanvas de edición de contrato: ${url}`);

    try {
      await htmx.ajax('GET', url, {
        target: `#${OFFCANVAS_CONTAINER_ID}`,
        swap: 'innerHTML',
        headers: {
          'X-CSRFToken': d.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
      });

      const offcanvasEl = d.getElementById(OFFCANVAS_ID);
      if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        offcanvas.show();
        console.log(`${MOD} ✅ Offcanvas de edición de contrato abierto correctamente`);
        
        // Inicializar formulario después de que el offcanvas esté visible
        setTimeout(function() {
          inicializarFormularioEdicion();
        }, 300);
      } else {
        console.warn(`${MOD} ⚠️ Offcanvas ${OFFCANVAS_ID} no encontrado después de cargar HTMX`);
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(
            { status: 500, data: { detail: 'El offcanvas no se cargó correctamente. Verifique que el endpoint retorne el HTML correcto.' } },
            MOD
          );
        }
      }
    } catch (error) {
      console.error(`${MOD} ❌ Error al cargar offcanvas de edición de contrato:`, error);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Error al cargar el formulario de contrato: ${error.message || error}` } },
          MOD
        );
      }
    }
  }

  /**
   * Inicializar formulario de edición
   * ⚠️ v2.61: Configura eventos y validaciones del formulario
   */
  function inicializarFormularioEdicion() {
    const form = d.getElementById('form-contrato-editar');
    if (!form) {
      console.warn(`${MOD} ⚠️ Formulario form-contrato-editar no encontrado`);
      return;
    }

    // Configurar checkbox de contrato indefinido
    const checkboxIndefinido = d.getElementById('contrato-editar-indefinido');
    const fechaFinInput = d.getElementById('contrato-editar-fecha_fin');
    
    if (checkboxIndefinido && fechaFinInput) {
      checkboxIndefinido.addEventListener('change', function() {
        if (this.checked) {
          fechaFinInput.value = '';
          fechaFinInput.disabled = true;
        } else {
          fechaFinInput.disabled = false;
        }
      });
      
      // Inicializar estado del checkbox basado en si fecha_fin está vacía
      if (!fechaFinInput.value || fechaFinInput.value === '') {
        checkboxIndefinido.checked = true;
        fechaFinInput.disabled = true;
      } else {
        checkboxIndefinido.checked = false;
        fechaFinInput.disabled = false;
      }
    }

    console.log(`${MOD} ✅ Formulario de edición inicializado`);
  }

  /**
   * Configurar eventos HTMX para manejo de éxito y errores
   * ⚠️ v2.61: Manejo de respuestas HTMX del formulario de edición
   */
  function configurarEventosHTMX() {
    // Manejo de éxito HTMX para actualización de contratos
    d.addEventListener('htmx:afterOnLoad', function(event) {
      // Solo procesar respuestas exitosas de actualización de contratos
      if (event.detail.path && event.detail.path.includes('/api/v1/empleados/contratos/')) {
        const method = event.detail.xhr?.method || event.detail.requestConfig?.method;
        if (method === 'PATCH' || method === 'PUT') {
          try {
            const statusCode = event.detail.xhr?.status || event.detail.xhr?.statusCode;
            
            // Verificar si la petición fue exitosa (200 OK)
            if (statusCode === 200) {
              const responseData = event.detail.xhr?.responseJSON || event.detail.xhr?.response;
              let parsedResponse = responseData;
              if (typeof responseData === 'string') {
                try {
                  parsedResponse = JSON.parse(responseData);
                } catch (e) {
                  parsedResponse = null;
                }
              }
              
              const message = parsedResponse?.message || 'Contrato actualizado correctamente';
              
              // Mostrar mensaje de éxito
              if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function' && message) {
                w.SintelFeedback.success(message);
              } else if (w.UIManager && typeof w.UIManager.notifySuccess === 'function') {
                w.UIManager.notifySuccess(message);
              } else {
                console.log(`${MOD} ✅ ${message}`);
              }
              
              // Cerrar Offcanvas
              const offcanvasEl = d.getElementById(OFFCANVAS_ID);
              if (offcanvasEl) {
                const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (offcanvas) {
                  offcanvas.hide();
                  console.log(`${MOD} ✅ Offcanvas cerrado después de actualización exitosa`);
                }
              }
              
              // Refrescar tabla en segundo plano
              setTimeout(function() {
                if (w.EmpleadosList && typeof w.EmpleadosList.refresh === 'function') {
                  w.EmpleadosList.refresh();
                  console.log(`${MOD} ✅ Tabla de empleados refrescada en segundo plano`);
                }
              }, 300);
            }
          } catch (e) {
            console.warn(`${MOD} ⚠️ Error al procesar respuesta exitosa:`, e);
          }
        }
      }
    });
  }

  // Inicializar eventos HTMX al cargar
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', configurarEventosHTMX);
  } else {
    configurarEventosHTMX();
  }

  // Exponer namespace global
  w.ContratosEditar = {
    cargarOffcanvasEditarContrato: cargarOffcanvasEditarContrato,
    open: cargarOffcanvasEditarContrato // Alias para compatibilidad
  };

  console.log(`${MOD} ✅ Módulo ContratosEditar cargado`);

})(window, document);
