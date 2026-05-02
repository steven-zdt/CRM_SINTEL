/**
 * contratos_form.js - Módulo de Formulario de Contratos (CREAR) v2.61
 * ⚠️ Feature-Sliced Architecture - Lógica exclusiva para creación de contratos
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

  const MOD = '[contratos.form]';
  const OFFCANVAS_ID = 'offcanvas-contrato-crear';
  const OFFCANVAS_CONTAINER_ID = 'offcanvas-container-contrato';
  const API_BASE = '/api/v1/empleados/';
  const CONTRATOS_API = `${API_BASE}contratos/`;

  /**
   * Cargar offcanvas de creación de contrato
   * ⚠️ v2.61: Usa endpoint render-offcanvas/crear
   */
  async function cargarOffcanvasCrearContrato(empleadoId) {
    if (!empleadoId) {
      console.error(`${MOD} ❌ ID de empleado no proporcionado`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 400, data: { detail: 'Se requiere un ID de empleado para crear un contrato.' } },
          MOD
        );
      }
      return;
    }

    const url = `${CONTRATOS_API}render-offcanvas/crear/?empleado=${empleadoId}`;

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

    console.log(`${MOD} Cargando offcanvas de creación de contrato: ${url}`);

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
        console.log(`${MOD} ✅ Offcanvas de creación de contrato abierto correctamente`);
        
        // Inicializar formulario después de que el offcanvas esté visible
        setTimeout(function() {
          inicializarFormularioCreacion();
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
      console.error(`${MOD} ❌ Error al cargar offcanvas de creación de contrato:`, error);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Error al cargar el formulario de contrato: ${error.message || error}` } },
          MOD
        );
      }
    }
  }

  /**
   * Inicializar formulario de creación
   * ⚠️ v2.61: Configura eventos y validaciones del formulario
   */
  function inicializarFormularioCreacion() {
    const form = d.getElementById('form-contrato-crear');
    if (!form) {
      console.warn(`${MOD} ⚠️ Formulario form-contrato-crear no encontrado`);
      return;
    }

    // Configurar checkbox de contrato indefinido
    const checkboxIndefinido = d.getElementById('contrato-crear-indefinido');
    const fechaFinInput = d.getElementById('contrato-crear-fecha_fin');
    
    if (checkboxIndefinido && fechaFinInput) {
      checkboxIndefinido.addEventListener('change', function() {
        if (this.checked) {
          fechaFinInput.value = '';
          fechaFinInput.disabled = true;
        } else {
          fechaFinInput.disabled = false;
        }
      });
      
      // Inicializar estado del checkbox
      if (checkboxIndefinido.checked) {
        fechaFinInput.disabled = true;
      }
    }

    console.log(`${MOD} ✅ Formulario de creación inicializado`);
  }

  /**
   * Configurar eventos HTMX para manejo de éxito y errores
   * ⚠️ v2.61: Manejo de respuestas HTMX del formulario de creación
   */
  function configurarEventosHTMX() {
    // Manejo de éxito HTMX para creación de contratos
    d.addEventListener('htmx:afterOnLoad', function(event) {
      // Solo procesar respuestas exitosas de creación de contratos
      if (event.detail.path && event.detail.path.includes('/api/v1/empleados/contratos/')) {
        const method = event.detail.xhr?.method || event.detail.requestConfig?.method;
        if (method === 'POST') {
          try {
            const statusCode = event.detail.xhr?.status || event.detail.xhr?.statusCode;
            
            // Verificar si la petición fue exitosa (201 Created)
            if (statusCode === 201) {
              const responseData = event.detail.xhr?.responseJSON || event.detail.xhr?.response;
              let parsedResponse = responseData;
              if (typeof responseData === 'string') {
                try {
                  parsedResponse = JSON.parse(responseData);
                } catch (e) {
                  parsedResponse = null;
                }
              }
              
              const message = parsedResponse?.message || 'Contrato creado correctamente';
              
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
                  console.log(`${MOD} ✅ Offcanvas cerrado después de creación exitosa`);
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
  w.ContratosForm = {
    cargarOffcanvasCrearContrato: cargarOffcanvasCrearContrato,
    open: cargarOffcanvasCrearContrato // Alias para compatibilidad
  };

  console.log(`${MOD} ✅ Módulo ContratosForm cargado`);

})(window, document);
