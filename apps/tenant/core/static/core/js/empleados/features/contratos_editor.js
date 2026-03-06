/**
 * contratos_editor.js - Feature: Editor de Contratos
 * ⚠️ Feature-Sliced Architecture v2.60
 * Maneja la apertura de offcanvas de contratos
 */
(function (w, d) {
  'use strict';

  const MOD = '[contratos.editor]';
  const API_URL = '/api/v1/empleados/';

  /**
   * Abrir offcanvas de contrato vía HTMX
   * ⚠️ v2.60: Para crear contrato nuevo, pasar empleado_id
   */
  async function openContratoOffcanvas(empleadoId, contratoId = null) {
    let url;
    if (contratoId) {
      url = `${API_URL}gestor-offcanvas/?tipo=contrato&id=${contratoId}`;
    } else if (empleadoId) {
      url = `${API_URL}gestor-offcanvas/?tipo=contrato&empleado=${empleadoId}`;
    } else {
      console.error(`${MOD} ❌ No se proporcionó empleadoId ni contratoId`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 400, data: { detail: 'Se requiere un ID de empleado o contrato para abrir el offcanvas de contrato.' } },
          MOD
        );
      }
      return;
    }
    
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

    console.log(`${MOD} Cargando offcanvas de contrato: ${url}`);
    
    try {
      await htmx.ajax('GET', url, {
        target: '#offcanvas-container-contrato',
        swap: 'innerHTML',
        headers: {
          'X-CSRFToken': d.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
      });

      const offcanvasEl = d.getElementById('offcanvas-contrato');
      if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        offcanvas.show();
        console.log(`${MOD} ✅ Offcanvas de contrato abierto correctamente`);
      } else {
        console.warn(`${MOD} ⚠️ Offcanvas #offcanvas-contrato no encontrado después de cargar HTMX`);
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(
            { status: 500, data: { detail: 'El offcanvas no se cargó correctamente. Verifique que el endpoint gestor-offcanvas retorne el HTML correcto.' } },
            MOD
          );
        }
      }
    } catch (error) {
      console.error(`${MOD} ❌ Error al cargar offcanvas de contrato:`, error);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Error al cargar el formulario de contrato: ${error.message || error}` } },
          MOD
        );
      }
    }
  }

  /**
   * Configurar eventos HTMX para manejo de éxito en contratos
   * ⚠️ Paso 3: Los templates son puramente declarativos, el éxito se maneja aquí
   */
  function configurarEventosHTMX() {
    // ⚠️ Manejo de éxito HTMX para contratos
    d.addEventListener('htmx:afterOnLoad', function(event) {
      // Solo procesar respuestas exitosas de creación/actualización de contratos
      if (event.detail.path && event.detail.path.includes('/api/v1/empleados/contratos/')) {
        const method = event.detail.xhr?.method || event.detail.requestConfig?.method;
        if (method === 'POST' || method === 'PATCH' || method === 'PUT') {
          try {
            const statusCode = event.detail.xhr?.status || event.detail.xhr?.statusCode;
            
            // ⚠️ Verificar si la petición fue exitosa (201 Created o 200 OK)
            if (statusCode === 201 || statusCode === 200) {
              const responseData = event.detail.xhr?.responseJSON || event.detail.xhr?.response;
              let parsedResponse = responseData;
              if (typeof responseData === 'string') {
                try {
                  parsedResponse = JSON.parse(responseData);
                } catch (e) {
                  parsedResponse = null;
                }
              }
              
              // Determinar mensaje según el tipo de operación
              const wasUpdated = parsedResponse?.was_updated === true || statusCode === 200;
              const message = parsedResponse?.message || (wasUpdated ? 'Contrato actualizado correctamente' : 'Contrato creado correctamente');
              
              // ⚠️ v2.60: Flujo de UX de éxito - Paso 1: Mostrar mensaje de éxito
              // Usar SintelFeedback si está disponible, fallback a UIManager
              if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function' && message) {
                w.SintelFeedback.success(message);
              } else if (w.UIManager && typeof w.UIManager.notifySuccess === 'function') {
                w.UIManager.notifySuccess(message);
              } else {
                console.log(`${MOD} ✅ ${message}`);
              }
              
              // ⚠️ v2.60: Flujo de UX de éxito - Paso 2: Cerrar Offcanvas activo
              // NO recargar la página, solo cerrar el offcanvas
              const offcanvasEl = d.getElementById('offcanvas-contrato');
              if (offcanvasEl) {
                const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (offcanvas) {
                  offcanvas.hide();
                  console.log(`${MOD} ✅ Offcanvas cerrado después de operación exitosa`);
                }
              }
              
              // ⚠️ v2.60: Flujo de UX de éxito - Paso 3: Refrescar tabla en segundo plano
              // Mantener paginación y estado actual, solo actualizar datos
              setTimeout(function() {
                if (w.EmpleadosList && typeof w.EmpleadosList.refresh === 'function') {
                  w.EmpleadosList.refresh();
                  console.log(`${MOD} ✅ Tabla de empleados refrescada en segundo plano`);
                }
              }, 300); // Delay corto para permitir que el offcanvas se cierre primero
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
  w.ContratosEditor = {
    open: openContratoOffcanvas,
    openContratoOffcanvas: openContratoOffcanvas // Alias para compatibilidad
  };

  // ⚠️ v2.60: Event listener global para interceptar respuestas HTMX del formulario de contrato
  // Se dispara después de cada petición HTMX (htmx:afterRequest)
  d.body.addEventListener('htmx:afterRequest', function(e) {
    // Verificar si la petición proviene del formulario de contrato y fue exitosa
    const isContratoForm = e.target.closest('#offcanvas-contrato') || e.target.id === 'form-contrato';
    
    if (e.detail.successful && isContratoForm) {
      // 1. Cerrar Offcanvas
      const offcanvasEl = d.getElementById('offcanvas-contrato');
      if (offcanvasEl) {
        const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (bsOffcanvas) {
          bsOffcanvas.hide();
          console.log(`${MOD} ✅ Offcanvas cerrado vía htmx:afterRequest`);
        }
      }

      // 2. Mostrar mensaje de éxito
      let msg = 'Contrato guardado exitosamente.';
      try {
        const response = JSON.parse(e.detail.xhr.response);
        if (response.message) msg = response.message;
      } catch (err) {
        // Si no se puede parsear, usar mensaje por defecto
      }
      
      if (w.UIManager && typeof w.UIManager.showToast === 'function') {
        w.UIManager.showToast('Éxito', msg, 'success');
      } else if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
        w.SintelFeedback.success(msg);
      } else {
        alert(msg);
      }

      // 3. Refrescar la tabla
      if (w.EmpleadosList && typeof w.EmpleadosList.refresh === 'function') {
        setTimeout(function() {
          w.EmpleadosList.refresh();
          console.log(`${MOD} ✅ Tabla refrescada vía htmx:afterRequest`);
        }, 300);
      }
    }
  });

  console.log(`${MOD} ✅ Feature ContratosEditor cargado`);

})(window, document);
