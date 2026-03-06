/**
 * empleados_editor.js - Feature: Editor de Empleados
 * ⚠️ Feature-Sliced Architecture v2.60
 * Maneja la apertura de offcanvas y eliminación de empleados
 */
(function (w, d) {
  'use strict';

  const MOD = '[empleados.editor]';
  const API_URL = '/api/v1/empleados/';

  /**
   * Abrir offcanvas de empleado vía HTMX
   * ⚠️ v2.60: Acciones - La columna de acciones debe llamar a openEmpleadoOffcanvas(id) mediante HTMX
   */
  async function openEmpleadoOffcanvas(id) {
    const url = id 
      ? `${API_URL}gestor-offcanvas/?tipo=empleado&id=${id}`
      : `${API_URL}gestor-offcanvas/?tipo=empleado`;
    
    // ⚠️ v2.60: Usar htmx.ajax para cargar el offcanvas
    if (typeof htmx === 'undefined' || !htmx.ajax) {
      console.error(`${MOD} ❌ HTMX no está disponible`);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'HTMX no está disponible. Verifique que la librería se haya cargado correctamente.' } }, MOD);
      }
      return;
    }

    console.log(`${MOD} Cargando offcanvas de empleado: ${url}`);
    
    try {
      await htmx.ajax('GET', url, {
        target: '#offcanvas-container-empleado',
        swap: 'innerHTML',
        headers: {
          'X-CSRFToken': d.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
      });

      const offcanvasEl = d.getElementById('offcanvas-empleado');
      if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        offcanvas.show();
        console.log(`${MOD} ✅ Offcanvas de empleado abierto correctamente`);
      } else {
        console.warn(`${MOD} ⚠️ Offcanvas #offcanvas-empleado no encontrado después de cargar HTMX`);
        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
          w.UIManager.notifyError(
            { status: 500, data: { detail: 'El offcanvas no se cargó correctamente. Verifique que el endpoint gestor-offcanvas retorne el HTML correcto.' } },
            MOD
          );
        }
      }
    } catch (error) {
      console.error(`${MOD} ❌ Error al cargar offcanvas de empleado:`, error);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError(
          { status: 500, data: { detail: `Error al cargar el formulario de empleado: ${error.message || error}` } },
          MOD
        );
      }
    }
  }

  /**
   * Eliminar empleado (solo si está retirado)
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   */
  async function eliminarEmpleado(id) {
    if (!confirm('¿Está seguro de que desea eliminar definitivamente este empleado? Esta acción no se puede deshacer.')) {
      return;
    }

    const res = await w.http('DELETE', `${API_URL}${id}/`);
    
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD);
      }
      return;
    }

    if (w.SintelFeedback) {
      w.SintelFeedback.success('Empleado eliminado correctamente');
    }

    // Refrescar tabla y panel de resumen
    if (w.EmpleadosList && typeof w.EmpleadosList.refresh === 'function') {
      w.EmpleadosList.refresh();
    }
  }

  /**
   * Configurar eventos HTMX para manejo de éxito en empleados
   * ⚠️ Paso 3: Los templates son puramente declarativos, el éxito se maneja aquí
   */
  function configurarEventosHTMX() {
    // ⚠️ Manejo de éxito HTMX para empleados
    d.addEventListener('htmx:afterOnLoad', function(event) {
      // Solo procesar respuestas exitosas de creación/actualización de empleados
      if (event.detail.path && event.detail.path.includes('/api/v1/empleados/') && 
          !event.detail.path.includes('/contratos/') && !event.detail.path.includes('/devengos/')) {
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
              const message = parsedResponse?.message || (wasUpdated ? 'Empleado actualizado correctamente' : 'Empleado creado correctamente');
              
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
              const offcanvasEl = d.getElementById('offcanvas-empleado');
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
              
              // ⚠️ Si es una actualización (200 OK), redirigir a la lista de empleados
              if (wasUpdated) {
                // Navegar al tab de empleados usando el enlace de navegación
                // Esto activa el listener de workspace.js que maneja la navegación
                setTimeout(function() {
                  const empleadosLink = d.querySelector('#nav a[data-tab="empleados"]');
                  if (empleadosLink) {
                    empleadosLink.click();
                    console.log(`${MOD} ✅ Redirigido a lista de empleados después de actualización`);
                  } else {
                    // Fallback: cambiar hash de URL (workspace.js escucha hashchange)
                    window.location.hash = '#empleados';
                    console.log(`${MOD} ✅ Redirigido a lista de empleados vía hash`);
                  }
                }, 500); // Delay mayor para asegurar que el refresh se complete
              }
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
  w.EmpleadosEditor = {
    open: openEmpleadoOffcanvas,
    openEmpleadoOffcanvas: openEmpleadoOffcanvas, // Alias para compatibilidad
    delete: eliminarEmpleado,
    eliminarEmpleado: eliminarEmpleado // Alias para compatibilidad
  };

  // ⚠️ v2.60: Event listener global para interceptar respuestas HTMX del formulario de empleado
  // Se dispara después de cada petición HTMX (htmx:afterRequest)
  d.body.addEventListener('htmx:afterRequest', function(e) {
    // Verificar si la petición proviene del formulario de empleado y fue exitosa
    const isEmpleadoForm = e.target.closest('#offcanvas-empleado') || e.target.id === 'form-empleado';
    
    if (e.detail.successful && isEmpleadoForm) {
      // 1. Cerrar Offcanvas
      const offcanvasEl = d.getElementById('offcanvas-empleado');
      if (offcanvasEl) {
        const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (bsOffcanvas) {
          bsOffcanvas.hide();
          console.log(`${MOD} ✅ Offcanvas cerrado vía htmx:afterRequest`);
        }
      }

      // 2. Mostrar mensaje de éxito
      let msg = 'Empleado guardado exitosamente.';
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

  console.log(`${MOD} ✅ Feature EmpleadosEditor cargado`);

})(window, document);
