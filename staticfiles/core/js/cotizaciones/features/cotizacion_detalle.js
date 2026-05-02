/**
 * Módulo de Detalle de Cotizaciones v2.61
 * 
 * ⚠️ Feature-Sliced Architecture - Módulo independiente para visualización de detalles
 * - Solo lectura (read-only)
 * - No permite edición
 * - Muestra información completa de la cotización y sus items
 * 
 * @module cotizacion_detalle
 */

(function (w, d) {
  'use strict';

  const MOD = 'cotizacion-detalle';
  const OFFCANVAS_ID = 'offcanvas-container';
  const EDITOR_ID = 'modal-cotizacion-detalle';

  // ─── Estado del módulo ────────────────────────────────────────────────────────
  let _uuid = null;
  let _initialized = false;

  // ─── Funciones principales ────────────────────────────────────────────────────

  /**
   * Formatear valores de moneda con separadores de miles
   * ⚠️ v2.61: Reemplaza el uso de humanize.intcomma que no está disponible
   */
  function formatearMoneda(valor) {
    if (!valor && valor !== 0) return '$0';
    const num = parseFloat(valor) || 0;
    return '$' + num.toLocaleString('es-CO', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
  }

  /**
   * Formatear todos los valores de moneda en el offcanvas
   * ⚠️ v2.61: Reemplaza el uso de humanize.intcomma que no está disponible
   */
  function formatearValoresMoneda() {
    // Formatear valores en la tabla de items y otros elementos con clase currency-value
    const currencyValues = d.querySelectorAll('#' + EDITOR_ID + ' .currency-value');
    currencyValues.forEach(function(el) {
      if (el.hasAttribute('data-value')) {
        const valor = parseFloat(el.getAttribute('data-value')) || 0;
        el.textContent = formatearMoneda(valor);
      }
    });

    // Formatear total con impuestos
    const elTotalImpuestos = d.getElementById('detalle-total-impuestos');
    if (elTotalImpuestos && elTotalImpuestos.hasAttribute('data-value')) {
      const valor = parseFloat(elTotalImpuestos.getAttribute('data-value')) || 0;
      const span = elTotalImpuestos.querySelector('.currency-value');
      if (span) {
        span.textContent = formatearMoneda(valor);
      } else {
        // Si no hay span, actualizar directamente el div
        elTotalImpuestos.textContent = formatearMoneda(valor);
      }
    }
  }

  /**
   * Calcular subtotal desde los items mostrados en la tabla
   */
  function calcularSubtotal() {
    const tabla = d.querySelector('#' + EDITOR_ID + ' table tbody');
    if (!tabla) return;

    let subtotal = 0;
    const filas = tabla.querySelectorAll('tr');
    
    filas.forEach(function(fila) {
      const celdaSubtotal = fila.querySelector('td:last-child');
      if (celdaSubtotal) {
        const currencyValue = celdaSubtotal.querySelector('.currency-value');
        if (currencyValue && currencyValue.hasAttribute('data-value')) {
          const valor = parseFloat(currencyValue.getAttribute('data-value')) || 0;
          subtotal += valor;
        }
      }
    });

    // Actualizar el elemento de subtotal
    const elSubtotal = d.getElementById('detalle-subtotal');
    if (elSubtotal) {
      elSubtotal.textContent = formatearMoneda(subtotal);
    }
  }

  /**
   * Inicializar el módulo de detalle
   * ⚠️ v2.61: Solo lectura - No requiere inicialización compleja
   */
  function init() {
    console.log(`[${MOD}] ========== INICIANDO MÓDULO DE DETALLE ==========`);

    const editorDiv = d.getElementById(EDITOR_ID);
    if (!editorDiv) {
      console.error(`[${MOD}] ❌ ${EDITOR_ID} NO encontrado en DOM`);
      return;
    }
    console.log(`[${MOD}] ✅ ${EDITOR_ID} encontrado en DOM`);

    // Obtener UUID de la cotización
    _uuid = editorDiv.getAttribute('data-cotizacion-uuid');
    if (!_uuid) {
      console.warn(`[${MOD}] ⚠️ UUID no encontrado en ${EDITOR_ID}`);
      return;
    }
    console.log(`[${MOD}] ✅ UUID de cotización: ${_uuid}`);

    // Formatear todos los valores de moneda con separadores de miles
    formatearValoresMoneda();

    // Calcular subtotal desde los items
    calcularSubtotal();

    // Marcar como inicializado
    _initialized = true;
    console.log(`[${MOD}] ✅ Módulo de detalle inicializado correctamente`);
  }

  /**
   * Resetear estado del módulo
   */
  function resetState() {
    _uuid = null;
    _initialized = false;
    console.log(`[${MOD}] Estado del módulo reseteado`);
  }

  // ─── Exponer módulo globalmente ──────────────────────────────────────────────
  w.CotizacionDetalleModule = {
    init: init,
    resetState: resetState,
    getUuid: () => _uuid,
    isInitialized: () => _initialized
  };

  // ─── Listeners de ciclo de vida ──────────────────────────────────────────────

  // ⚠️ v2.61: HTMX: se disparará cuando el partial cargue vía hx-get - Con safeguards mejorados
  d.body.addEventListener('htmx:afterSwap', function (e) {
    // ⚠️ SAFEGUARD 1: Solo inicializar si el target es el contenedor del editor
    if (!e.detail || !e.detail.target || e.detail.target.id !== OFFCANVAS_ID) {
      return; // No es nuestro contenedor, ignorar silenciosamente
    }

    // ⚠️ SAFEGUARD 2: PRIORIDAD - Verificar PRIMERO dentro del target si existe el editor de DETALLE
    // Buscar dentro del contenido recién cargado por HTMX (más confiable que buscar en todo el DOM)
    var editorDetalleDiv = e.detail.target.querySelector('#' + EDITOR_ID);
    if (!editorDetalleDiv) {
      // No mostrar warning si es un swap de creación/edición (no es nuestro caso)
      return;
    }

    // ⚠️ SAFEGUARD 3: Verificar el atributo data-mode para mayor seguridad
    var dataMode = editorDetalleDiv.getAttribute('data-mode');
    if (dataMode && dataMode !== 'detalle') {
      console.log('[' + MOD + '] HTMX swap detectado pero data-mode="' + dataMode + '" (no es detalle). Abortando.');
      return;
    }

    // ⚠️ SAFEGUARD 4: Verificar que tenga UUID
    var uuid = editorDetalleDiv.getAttribute('data-cotizacion-uuid');
    if (!uuid || uuid === '' || uuid === 'None') {
      console.log('[' + MOD + '] HTMX swap detectado pero NO tiene UUID. Abortando.');
      return;
    }

    console.log('[' + MOD + '] HTMX swap detectado → init()');

    // ⚠️ v2.61: Usar setTimeout para asegurar que el DOM esté completamente renderizado
    setTimeout(function() {
      if (d.getElementById(EDITOR_ID)) {
        resetState();
        init();
      }
    }, 100);
  });

  // Fallback: cuando el offcanvas ya está visible pero init aún no corrió
  d.body.addEventListener('shown.bs.offcanvas', function (e) {
    if (e.target && e.target.id === OFFCANVAS_ID) {
      var editorDiv = d.getElementById(EDITOR_ID);
      if (editorDiv && !editorDiv.getAttribute('data-init')) {
        console.log('[' + MOD + '] shown.bs.offcanvas fallback → init()');
        init();
        editorDiv.setAttribute('data-init', 'true');
      }
    }
  });

  // Limpiar estado cuando se cierra el offcanvas
  d.body.addEventListener('hidden.bs.offcanvas', function (e) {
    if (e.target && e.target.id === OFFCANVAS_ID) {
      console.log('[' + MOD + '] Offcanvas cerrado → resetState()');
      resetState();
    }
  });

})(window, document);
