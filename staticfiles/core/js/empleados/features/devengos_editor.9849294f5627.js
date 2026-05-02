/**
 * devengos_editor.js - Feature: Editor de Devengos (Nóminas)
 * ⚠️ Feature-Sliced Architecture v2.60
 * Maneja la apertura de offcanvas y eventos HTMX de devengos
 */
(function (w, d) {
  'use strict';

  const MOD = '[devengos.editor]';
  const API_URL = '/api/v1/empleados/';

  /**
   * Abrir offcanvas de devengo (nómina) vía HTMX
   * ⚠️ v2.60: Para crear devengo nuevo, pasar empleado_id
   */
  async function openDevengoOffcanvas(empleadoId, devengoId = null) {
    let url;
    if (devengoId) {
      url = `${API_URL}gestor-offcanvas/?tipo=devengo&id=${devengoId}`;
    } else if (empleadoId) {
      url = `${API_URL}gestor-offcanvas/?tipo=devengo&empleado=${empleadoId}`;
    } else {
      console.error(`${MOD} ❌ No se proporcionó empleadoId ni devengoId`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 400, data: { detail: 'Se requiere un ID de empleado o devengo para abrir el offcanvas de nómina.' } },
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

    console.log(`${MOD} Cargando offcanvas de nómina: ${url}`);
    
    try {
      await htmx.ajax('GET', url, {
        target: '#offcanvas-container-devengo',
        swap: 'innerHTML',
        headers: {
          'X-CSRFToken': d.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
      });

      const offcanvasEl = d.getElementById('offcanvas-devengo');
      if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        offcanvas.show();
        console.log(`${MOD} ✅ Offcanvas de nómina abierto correctamente`);
      } else {
        console.warn(`${MOD} ⚠️ Offcanvas #offcanvas-devengo no encontrado después de cargar HTMX`);
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(
            { status: 500, data: { detail: 'El offcanvas no se cargó correctamente. Verifique que el endpoint gestor-offcanvas retorne el HTML correcto.' } },
            MOD
          );
        }
      }
    } catch (error) {
      console.error(`${MOD} ❌ Error al cargar offcanvas de nómina:`, error);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Error al cargar el formulario de nómina: ${error.message || error}` } },
          MOD
        );
      }
    }
  }

  /**
   * Configurar eventos HTMX para manejo de errores y éxito en devengos
   * ⚠️ Paso 5.3: Perfeccionar el ciclo de vida HTMX - Manejo de errores
   */
  function configurarEventosHTMX() {
    // ⚠️ Manejo de errores HTMX para devengos
    d.addEventListener('htmx:responseError', function(event) {
      // Solo procesar errores de endpoints de devengos
      if (event.detail.path && event.detail.path.includes('/api/v1/empleados/devengos/')) {
        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
          const errorContainerSelector = '#form-devengo-feedback';
          
          // ⚠️ Capturar error específico de duplicado de nómina
          try {
            const responseData = event.detail.xhr?.responseJSON || event.detail.xhr?.response;
            let parsedResponse = responseData;
            if (typeof responseData === 'string') {
              try {
                parsedResponse = JSON.parse(responseData);
              } catch (e) {
                parsedResponse = null;
              }
            }
            
            // ⚠️ Verificar si es error de duplicado (409 Conflict) o días excedidos (400)
            const statusCode = event.detail.xhr?.status || event.detail.xhr?.statusCode;
            const path = event.detail.path;
            const isDevengoEndpoint = path.includes('/devengos/') && !path.includes('/preview-calculo/');
            
            // ⚠️ Error de duplicado (409 Conflict) - Solo para devengos
            const isDuplicateError = isDevengoEndpoint && (statusCode === 409 || 
              (parsedResponse && (
                parsedResponse.code === 'duplicate_nomina' ||
                (parsedResponse.error && parsedResponse.error.includes('Ya existe una nómina'))
              )));
            
            // ⚠️ Error de días excedidos (400 Bad Request con código dias_excedidos) - Solo para devengos
            const isDiasExcedidosError = isDevengoEndpoint && parsedResponse && parsedResponse.code === 'dias_excedidos';
            
            // ⚠️ Manejar errores específicos de devengos (409 o 400 con dias_excedidos)
            // NO cerrar el offcanvas para permitir al usuario corregir los datos
            if (isDuplicateError || isDiasExcedidosError) {
              // ⚠️ Error de Integridad - Bloquear botón y mostrar mensaje específico
              const btnGuardar = d.getElementById('btn-guardar-devengo');
              if (btnGuardar && isDuplicateError) {
                btnGuardar.disabled = true;
                btnGuardar.classList.remove('btn-primary');
                btnGuardar.classList.add('btn-secondary');
                btnGuardar.innerHTML = '<i class="bi bi-lock me-1"></i>Nómina Duplicada (Deshabilitado)';
              }
              
              // ⚠️ Mostrar mensaje específico
              const errorMessage = parsedResponse?.error || parsedResponse?.detail || 
                (isDuplicateError 
                  ? 'Error de Integridad: Ya existe un registro de pago para este empleado en la fecha y periodo seleccionados.'
                  : 'La suma de días laborados excede los 31 días del mes.');
              
              // Construir mensaje completo
              const devengoExistenteId = parsedResponse?.devengo_existente_id;
              let mensajeCompleto = '';
              
              if (isDuplicateError) {
                mensajeCompleto = `
                  <i class="bi bi-exclamation-triangle-fill me-2"></i>
                  <strong>Error de Integridad:</strong> ${errorMessage}
                  <br>
                  <small class="mt-2 d-block">
                    <i class="bi bi-info-circle me-1"></i>
                    Use el <strong>Historial de Nóminas</strong> para anular el registro previo antes de intentar uno nuevo.
                    <br>
                    <strong>Nota:</strong> Puede registrar múltiples nóminas en el mismo mes cambiando la fecha de pago.
                `;
                
                // Agregar enlace opcional para ver el registro existente
                if (devengoExistenteId) {
                  mensajeCompleto += `
                    <br>
                    <button type="button" class="btn btn-sm btn-outline-info mt-2" 
                            onclick="if(window.DevengosEditor && window.DevengosEditor.openDevengoOffcanvas) { 
                              window.DevengosEditor.openDevengoOffcanvas(null, ${devengoExistenteId}); 
                            }">
                      <i class="bi bi-eye me-1"></i>Ver Registro Existente (ID: ${devengoExistenteId})
                    </button>
                  `;
                }
                mensajeCompleto += `</small>`;
                
                // Marcar campos como inválidos
                const periodoInput = d.getElementById('devengo-periodo_mes');
                const fechaPagoInput = d.getElementById('devengo-fecha_pago');
                if (periodoInput) {
                  periodoInput.classList.add('is-invalid');
                  periodoInput.setAttribute('aria-invalid', 'true');
                }
                if (fechaPagoInput) {
                  fechaPagoInput.classList.add('is-invalid');
                  fechaPagoInput.setAttribute('aria-invalid', 'true');
                }
                
                // ⚠️ Re-habilitar botón cuando el usuario cambie periodo o fecha de pago
                const reenableButton = function() {
                  if (btnGuardar && btnGuardar.disabled) {
                    btnGuardar.disabled = false;
                    btnGuardar.classList.remove('btn-secondary');
                    btnGuardar.classList.add('btn-primary');
                    btnGuardar.innerHTML = '<i class="bi bi-check-lg me-1"></i>Guardar Nómina';
                    
                    // Limpiar estados de error
                    if (periodoInput) {
                      periodoInput.classList.remove('is-invalid');
                      periodoInput.removeAttribute('aria-invalid');
                    }
                    if (fechaPagoInput) {
                      fechaPagoInput.classList.remove('is-invalid');
                      fechaPagoInput.removeAttribute('aria-invalid');
                    }
                    
                    // Ocultar mensaje de error
                    const feedbackEl = d.querySelector(errorContainerSelector);
                    if (feedbackEl) {
                      feedbackEl.classList.add('d-none');
                    }
                  }
                };
                
                // Agregar listeners para re-habilitar cuando cambien los campos
                if (periodoInput) {
                  periodoInput.addEventListener('change', reenableButton, { once: true });
                  periodoInput.addEventListener('input', reenableButton, { once: true });
                }
                if (fechaPagoInput) {
                  fechaPagoInput.addEventListener('change', reenableButton, { once: true });
                  fechaPagoInput.addEventListener('input', reenableButton, { once: true });
                }
              } else if (isDiasExcedidosError) {
                mensajeCompleto = `
                  <i class="bi bi-exclamation-triangle-fill me-2"></i>
                  <strong>Días Excedidos:</strong> ${errorMessage}
                  <br>
                  <small class="mt-2 d-block">
                    <i class="bi bi-info-circle me-1"></i>
                    Días registrados: ${parsedResponse?.dias_registrados || '0'}, 
                    Días nuevos: ${parsedResponse?.dias_nuevos || '0'}, 
                    Total: ${parsedResponse?.total || '0'} días.
                    <br>
                    El mes tiene un máximo de 31 días. Revise las nóminas existentes en el Historial.
                  </small>
                `;
                
                // Marcar campo dias_laborados como inválido
                const diasInput = d.getElementById('devengo-dias_laborados');
                if (diasInput) {
                  diasInput.classList.add('is-invalid');
                  diasInput.setAttribute('aria-invalid', 'true');
                }
              }
              
              // Mostrar mensaje en el contenedor de feedback
              const feedbackEl = d.querySelector(errorContainerSelector);
              if (feedbackEl) {
                feedbackEl.classList.remove('d-none');
                feedbackEl.classList.remove('alert-warning', 'alert-info');
                feedbackEl.classList.add('alert-danger');
                feedbackEl.innerHTML = mensajeCompleto;
              }
              
              // Mostrar toast de advertencia si está disponible
              if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
                w.SintelFeedback.warning(errorMessage);
              }
              
              // ⚠️ NO cerrar el offcanvas después de error 409/400 - permitir al usuario corregir los datos
              return;
            }
          } catch (e) {
            console.warn(`${MOD} Error al procesar respuesta de error:`, e);
          }
          
          // ⚠️ UIManager.handleError procesa automáticamente errores 400 con estructura JSON
          w.UIManager.handleError(event.detail, MOD, {
            errorContainerSelector: errorContainerSelector
          });
        }
      }
    });

    // ⚠️ Manejo de éxito HTMX para devengos
    d.addEventListener('htmx:afterOnLoad', function(event) {
      // Solo procesar respuestas exitosas de creación/actualización de devengos
      if (event.detail.path && event.detail.path.includes('/api/v1/empleados/devengos/')) {
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
              const message = parsedResponse?.message || (wasUpdated ? 'Nómina actualizada correctamente' : 'Nómina creada correctamente');
              
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
              const offcanvasEl = d.getElementById('offcanvas-devengo');
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
                // Refrescar tabla principal de empleados y panel de resumen
                if (w.EmpleadosList && typeof w.EmpleadosList.refresh === 'function') {
                  w.EmpleadosList.refresh();
                  console.log(`${MOD} ✅ Tabla de empleados refrescada en segundo plano`);
                }
                
                // Refrescar historial de nóminas si está abierto
                if (w.SintelEmpleadosTables && w.SintelEmpleadosTables.historialNominas) {
                  try {
                    w.SintelEmpleadosTables.historialNominas.replaceData();
                    console.log(`${MOD} ✅ Historial de nóminas refrescado después de guardar`);
                  } catch (error) {
                    console.warn(`${MOD} Error al refrescar historial:`, error);
                  }
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
  w.DevengosEditor = {
    open: openDevengoOffcanvas,
    openDevengoOffcanvas: openDevengoOffcanvas // Alias para compatibilidad
  };

  // ⚠️ v2.60: Event listener global para interceptar respuestas HTMX del formulario de devengo/nómina
  // Se dispara después de cada petición HTMX (htmx:afterRequest)
  d.body.addEventListener('htmx:afterRequest', function(e) {
    // Verificar si la petición proviene del formulario de devengo y fue exitosa
    const isDevengoForm = e.target.closest('#offcanvas-devengo') || e.target.id === 'form-devengo';
    
    // Solo actuar en creación/edición exitosa, no en previsualización (preview-calculo)
    // Evitar cerrar el offcanvas si la URL era de preview-calculo
    const requestPath = e.detail.pathInfo?.requestPath || e.detail.path || '';
    const isPreviewCalculo = requestPath.includes('preview-calculo');
    
    if (e.detail.successful && isDevengoForm && !isPreviewCalculo) {
      // 1. Cerrar Offcanvas
      const offcanvasEl = d.getElementById('offcanvas-devengo');
      if (offcanvasEl) {
        const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (bsOffcanvas) {
          bsOffcanvas.hide();
          console.log(`${MOD} ✅ Offcanvas cerrado vía htmx:afterRequest`);
        }
      }

      // 2. Mostrar mensaje de éxito
      let msg = 'Nómina registrada exitosamente.';
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
          
          // También refrescar historial de nóminas si está abierto
          if (w.SintelEmpleadosTables && w.SintelEmpleadosTables.historialNominas) {
            try {
              w.SintelEmpleadosTables.historialNominas.replaceData();
              console.log(`${MOD} ✅ Historial de nóminas refrescado vía htmx:afterRequest`);
            } catch (error) {
              console.warn(`${MOD} Error al refrescar historial:`, error);
            }
          }
        }, 300);
      }
    }
  });

  console.log(`${MOD} ✅ Feature DevengosEditor cargado`);

})(window, document);
