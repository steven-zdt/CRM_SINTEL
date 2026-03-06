/**
 * gastos_anular.js - Módulo de Anulación de Gastos v2.60 - Feature-Sliced Architecture
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ Aislamiento Gradual v2.60: Sin bloques try/catch, usa UIManager.handleError()
 * 
 * ⚠️ v2.40: Sistema de Documento Soporte Inmutable
 * - Flujo desactivar -> anular (dos pasos obligatorios)
 * - Validación de estado antes de anular
 * - Actualización de resumen después de anular
 * 
 * Dependencias globales requeridas:
 * - w.gastosAPI (definido en gastos.api.js) - Capa de Datos
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.AppGastos (definido en gastos_main.js) - Para refrescar tabla
 */
(function (w, d) {
  'use strict';

  const MOD = '[gastos.anular]';

  // ⚠️ CRÍTICO v2.60: Exponer AppGastos INMEDIATAMENTE (antes de definir funciones)
  if (!w.AppGastos) {
    w.AppGastos = {};
    console.log(`${MOD} AppGastos expuesto inmediatamente (se actualizará con funciones reales)`);
  }

  /**
   * Función para confirmar desactivación
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   * ⚠️ REGLA CRÍTICA: Paso previo obligatorio antes de anular
   */
  async function desactivar(id) {
    if (!confirm('¿Está seguro de desactivar este Documento Soporte? Debe estar desactivado para poder anularlo.')) {
      return;
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.gastosAPI.desactivar(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD);
      }
      return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Documento desactivado correctamente. Ahora puede anularlo si lo desea.');
    }
    
    // Refrescar tabla
    if (w.AppGastos && typeof w.AppGastos.refresh === 'function') {
      w.AppGastos.refresh();
    }
  }

  /**
   * Función para ver detalle de gasto
   * ⚠️ v2.60: HTMX - Carga offcanvas dinámicamente
   */
  async function ver(id) {
    const container = d.getElementById('offcanvas-container-gastos');
    if (!container) {
      console.error(`${MOD} Contenedor #offcanvas-container-gastos no encontrado`);
      return;
    }

    const url = `/api/v1/gastos/gestor-offcanvas/?id=${id}&simple=true`;

    try {
      // ⚠️ HTMX: Cargar HTML desde el servidor
      await htmx.ajax('GET', url, {
        target: '#offcanvas-container-gastos',
        swap: 'innerHTML'
      });

      // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
      await new Promise(resolve => setTimeout(resolve, 50));

      // Inicializar y mostrar el Offcanvas
      const offcanvasEl = d.getElementById('offcanvas-gasto-detalle');
      if (offcanvasEl) {
        if (w.bootstrap && w.bootstrap.Offcanvas) {
          const offcanvas = w.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
          offcanvas.show();
        }
      } else {
        console.warn(`${MOD} Offcanvas cargado pero elemento #offcanvas-gasto-detalle no encontrado`);
      }
    } catch (error) {
      console.error(`${MOD} Error al cargar Offcanvas:`, error);
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el detalle' } }, MOD);
      }
    }
  }

  /**
   * Función para confirmar anulación
   * ⚠️ v2.60: Aislamiento Gradual - Sin try/catch, solo verifica ok
   * ⚠️ REGLA CRÍTICA: Solo se puede anular si está desactivado (activo=False)
   * ⚠️ v2.60: Validación obligatoria - No se puede anular si activo no es false
   */
  async function anular(id) {
    // ⚠️ v2.60: Validación previa - Obtener estado del documento antes de intentar anular
    const resGet = await w.gastosAPI.get(id);
    
    if (!resGet.ok || !resGet.data) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(resGet, MOD);
      }
      return;
    }
    
    // ⚠️ v2.60: Validación obligatoria - Verificar que activo sea false
    const documento = resGet.data;
    const activo = documento.ds_activo !== false;  // Verificar que NO sea activo
    
    if (activo) {
      const mensaje = 'No se puede anular un documento que está activo. Debe desactivarlo primero.';
      if (w.SintelFeedback) {
        w.SintelFeedback.error(mensaje);
      } else if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ ok: false, status: 422, data: { detail: mensaje } }, MOD);
      } else {
        alert(mensaje);
      }
      return;
    }
    
    // ⚠️ v2.60: Validación adicional - Verificar que no esté ya anulado
    if (documento.ds_anulado === true) {
      const mensaje = 'Este documento ya está anulado.';
      if (w.SintelFeedback) {
        w.SintelFeedback.warning(mensaje);
      } else {
        alert(mensaje);
      }
      return;
    }
    
    if (!confirm('¿Está seguro de anular este Documento Soporte? Esta acción es irreversible y afectará los totales financieros.')) {
      return;
    }
    
    // ⚠️ v2.60: Aislamiento Gradual - Capa de Datos retorna {ok, status, data}
    const res = await w.gastosAPI.anular(id);
    
    // ⚠️ v2.60: Aislamiento Gradual - Solo verificar ok
    if (!res.ok) {
      if (w.UIManager && typeof w.UIManager.handleError === 'function') {
        w.UIManager.handleError(res, MOD);
      }
      return;
    }
    
    // Éxito
    if (w.SintelFeedback) {
      w.SintelFeedback.success('Documento anulado correctamente');
    }
    
    // Refrescar tabla y resumen
    if (w.AppGastos && typeof w.AppGastos.refresh === 'function') {
      w.AppGastos.refresh();
    }
  }

  // ⚠️ CRÍTICO v2.60: Exponer funciones INMEDIATAMENTE después de definirlas
  if (w.AppGastos) {
    w.AppGastos.ver = ver;
    w.AppGastos.desactivar = desactivar;
    w.AppGastos.anular = anular;
  }

  console.log(`${MOD} Módulo de anulación inicializado`);

})(window, document);
