/**
 * gastos_resolucion.js - Módulo de Configuración de Resolución DIAN v2.60 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.60: Migrado de Modal a Offcanvas con HTMX
 * - Gestión de formulario de configuración de resolución DIAN
 * - Validación de campos y rangos
 * - Manejo de respuesta del servidor
 * - Post-acción: Cerrar offcanvas y refrescar estado
 * 
 * Dependencias globales requeridas:
 * - w.gastosAPI (definido en gastos.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.AppGastos (definido en gastos_main.js) - Para refrescar estado
 * - HTMX (cargado en workspace.html)
 */
(function (w, d) {
  'use strict';

  const MOD = '[gastos.resolucion]';

  // ⚠️ CRÍTICO v2.60: Exponer AppGastos INMEDIATAMENTE (antes de definir funciones)
  if (!w.AppGastos) {
    w.AppGastos = {};
    console.log(`${MOD} AppGastos expuesto inmediatamente (se actualizará con funciones reales)`);
  }

  /**
   * Función para mostrar el offcanvas de configuración de resolución
   * ⚠️ v2.60: HTMX - Carga offcanvas dinámicamente
   */
  async function mostrar() {
    const container = d.getElementById('offcanvas-container-gastos');
    if (!container) {
      console.error(`${MOD} Contenedor #offcanvas-container-gastos no encontrado`);
      return;
    }

    const url = '/api/v1/gastos/render-offcanvas/resolucion/';

    try {
      // ⚠️ HTMX: Cargar HTML desde el servidor
      await htmx.ajax('GET', url, {
        target: '#offcanvas-container-gastos',
        swap: 'innerHTML'
      });

      // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
      await new Promise(resolve => setTimeout(resolve, 50));

      // Inicializar valores por defecto
      inicializarValoresPorDefecto();

      // Inicializar y mostrar el Offcanvas
      const offcanvasEl = d.getElementById('offcanvas-resolucion-config');
      if (offcanvasEl) {
        if (w.bootstrap && w.bootstrap.Offcanvas) {
          const offcanvas = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          offcanvas.show();
        }
      } else {
        console.warn(`${MOD} Offcanvas cargado pero elemento #offcanvas-resolucion-config no encontrado`);
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar Offcanvas:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario de configuración' } }, MOD);
      }
    }
  }

  /**
   * Inicializar valores por defecto en el formulario
   * ⚠️ v2.60: Establece fechas por defecto al abrir el offcanvas
   */
  function inicializarValoresPorDefecto() {
    const form = d.getElementById('form-resolucion-config');
    if (!form) {
      console.warn(`${MOD} Formulario #form-resolucion-config no encontrado`);
      return;
    }

    const fechaResolucion = form.querySelector('input[name="fecha_resolucion"]');
    if (fechaResolucion && !fechaResolucion.value) {
      fechaResolucion.value = new Date().toISOString().split('T')[0];
    }

    const fechaFin = form.querySelector('input[name="fecha_fin"]');
    if (fechaFin && !fechaFin.value) {
      const hoy = new Date();
      hoy.setFullYear(hoy.getFullYear() + 1);
      fechaFin.value = hoy.toISOString().split('T')[0];
    }

    // Limpiar feedback anterior
    const feedbackEl = d.getElementById('feedback-config-resolucion');
    if (feedbackEl) {
      feedbackEl.textContent = '';
      feedbackEl.className = 'alert d-none';
      feedbackEl.style.display = 'none';
    }
  }

  /**
   * Función callback después de guardar resolución exitosamente
   * ⚠️ v2.60: Post-acción - Cerrar offcanvas, mostrar mensaje y refrescar estado
   */
  function onResolucionSaved(response) {
    try {
      const data = typeof response === 'string' ? JSON.parse(response) : response;
      
      if (!data) {
        console.warn(`${MOD} Respuesta vacía del servidor`);
        return;
      }

      const feedbackEl = d.getElementById('feedback-config-resolucion');
      if (feedbackEl) {
        const fechaResolucion = data.fecha_resolucion ? new Date(data.fecha_resolucion).toLocaleDateString('es-CO') : 'N/A';
        const fechaInicio = data.fecha_inicio ? new Date(data.fecha_inicio).toLocaleDateString('es-CO') : 'N/A';
        const fechaFin = data.fecha_fin ? new Date(data.fecha_fin).toLocaleDateString('es-CO') : 'N/A';
        const vigenteBadge = data.vigente 
          ? '<span class="badge bg-success ms-2">VIGENTE</span>' 
          : '<span class="badge bg-secondary ms-2">INACTIVA</span>';
        
        feedbackEl.className = 'alert alert-success';
        feedbackEl.innerHTML = `
          <div class="d-flex align-items-start">
            <i class="bi bi-check-circle-fill me-2 fs-5"></i>
            <div class="flex-grow-1">
              <strong>Resolución DIAN guardada correctamente</strong>${vigenteBadge}
              <hr class="my-2">
              <div class="small">
                <div class="row g-2">
                  <div class="col-md-6"><strong>Número:</strong> ${data.numero_resolucion || 'N/A'}</div>
                  <div class="col-md-6"><strong>Prefijo:</strong> ${data.prefijo || 'N/A'}</div>
                  <div class="col-md-6"><strong>Rango:</strong> ${data.rango_desde || 'N/A'} - ${data.rango_hasta || 'N/A'}</div>
                  <div class="col-md-6"><strong>Fecha Emisión:</strong> ${fechaResolucion}</div>
                  <div class="col-md-6"><strong>Fecha Inicio:</strong> ${fechaInicio}</div>
                  <div class="col-md-6"><strong>Fecha Fin:</strong> ${fechaFin}</div>
                </div>
              </div>
            </div>
          </div>
        `;
        feedbackEl.style.display = 'block';
        feedbackEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      // Mostrar notificación de éxito
      if (w.DOMUtils && typeof w.DOMUtils.showToast === 'function') {
        w.DOMUtils.showToast('Resolución DIAN configurada correctamente', 'success');
      } else if (w.SintelFeedback) {
        w.SintelFeedback.success('Resolución DIAN configurada correctamente');
      }

      // ⚠️ v2.60: Sincronización INMEDIATA - Actualizar select de resolución en formulario de creación
      // Si el offcanvas de creación está abierto, actualizar el select automáticamente
      // Se ejecuta inmediatamente para que el usuario vea la nueva resolución disponible
      if (w.AppGastos && typeof w.AppGastos.actualizarSelectResolucion === 'function') {
        // Usar setTimeout para asegurar que el DOM esté listo después de la respuesta HTMX
        setTimeout(async () => {
          await w.AppGastos.actualizarSelectResolucion();
        }, 100);
      }

      // ⚠️ Post-acción: Cerrar offcanvas después de 3 segundos y refrescar estado
      setTimeout(() => {
        const offcanvasEl = d.getElementById('offcanvas-resolucion-config');
        if (offcanvasEl) {
          const offcanvas = w.bootstrap.Offcanvas.getInstance(offcanvasEl);
          if (offcanvas) {
            offcanvas.hide();
          }
        }

        // Limpiar formulario
        const form = d.getElementById('form-resolucion-config');
        if (form) {
          form.reset();
        }

        // Limpiar feedback
        if (feedbackEl) {
          feedbackEl.innerHTML = '';
          feedbackEl.className = 'alert d-none';
          feedbackEl.style.display = 'none';
        }

        // ⚠️ Post-acción: Refrescar estado (verificar resolución activa)
        if (w.AppGastos && typeof w.AppGastos.verificarResolucionActiva === 'function') {
          w.AppGastos.verificarResolucionActiva();
        }

        // ⚠️ v2.60: Refrescar tabla de resoluciones después de guardar
        if (w.AppGastos && typeof w.AppGastos.refreshResoluciones === 'function') {
          w.AppGastos.refreshResoluciones();
        }
      }, 3000);
    } catch (error) {
      console.error(`${MOD} Error procesando respuesta:`, error);
    }
  }

  // ⚠️ CRÍTICO v2.60: Exponer funciones INMEDIATAMENTE después de definirlas
  if (w.AppGastos) {
    w.AppGastos.mostrarResolucion = mostrar;
    w.AppGastos.onResolucionSaved = onResolucionSaved;
  }

  console.log(`${MOD} Módulo de configuración de resolución inicializado`);

})(window, document);
