/**
 * DOM Utils - Helpers centralizados para manipulación DOM
 * 
 * ⚠️ v2.37: Helpers compartidos para verificación de elementos y visibilidad
 * - Verificación segura de elementos
 * - Detección de visibilidad
 * - Espera de visibilidad con timeout
 */

(function (w) {
  'use strict';

  function getEl(selector) {
    const el = document.querySelector(selector);
    const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
    if (!el && DEBUG) {
      console.warn('[DOMUtils] Elemento no encontrado:', selector);
    }
    return el;
  }

  function isVisible(el) {
    if (!el) return false;
    if (el.offsetParent === null) return false;
    const st = window.getComputedStyle(el);
    if (!st) return false;
    if (st.display === 'none' || st.visibility === 'hidden') return false;
    const opacity = parseFloat(st.opacity || '1');
    if (opacity === 0) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function waitForVisible(selectorOrEl, { interval = 120, timeout = 10000 } = {}) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const get = () => (typeof selectorOrEl === 'string' 
        ? document.querySelector(selectorOrEl) 
        : selectorOrEl);
      
      const check = () => {
        const el = get();
        if (el && isVisible(el)) {
          resolve(el);
          return true;
        }
        if (Date.now() - start > timeout) {
          reject(new Error(`Timeout esperando visibilidad: ${selectorOrEl}`));
          return true;
        }
        return false;
      };

      // Intento inmediato
      if (check()) return;

      // Polling
      const timer = setInterval(() => {
        if (check()) {
          clearInterval(timer);
        }
      }, interval);
    });
  }

  /**
   * Espera a que cualquiera de los selectores dados esté visible
   * Útil para tablas en tabs/accordions donde el contenedor o la tabla misma pueden estar visibles
   * @param {string[]} selectors - Array de selectores CSS
   * @param {Object} options - { timeout: 6000, interval: 120 }
   * @returns {Promise<Element>} Primer elemento visible encontrado
   */
  async function awaitVisibleAny(selectors, { timeout = 6000, interval = 120 } = {}) {
    if (!Array.isArray(selectors) || selectors.length === 0) {
      throw new Error('[DOMUtils.awaitVisibleAny] selectors debe ser un array no vacío');
    }

    const start = Date.now();
    while (Date.now() - start < timeout) {
      for (const s of selectors) {
        const el = document.querySelector(s);
        if (isVisible(el)) return el;
      }
      await new Promise(r => setTimeout(r, interval));
    }
    throw new Error(`Timeout esperando visibilidad de cualquiera: ${selectors.join(' | ')}`);
  }

  /**
   * Registra un callback que se ejecuta la primera vez que un elemento se vuelve visible
   * Útil para inicializar Tabulator cuando un tab/accordion se muestra
   * @param {string|Element} targetSelector - Selector CSS o elemento HTML a observar
   * @param {Function} callback - Función a ejecutar cuando el elemento se vuelve visible
   * @param {Object} options - { once: true, timeout: 30000 }
   */
  function onVisibleOnce(targetSelector, callback, { once = true, timeout = 30000 } = {}) {
    if (typeof callback !== 'function') {
      throw new Error('[DOMUtils.onVisibleOnce] callback debe ser una función');
    }

    // ⚠️ v3.3: Normalizar targetSelector - si es Element, convertirlo a selector o mantenerlo como Element
    let normalizedSelector = targetSelector;
    let isElement = false;
    
    // ⚠️ v3.3: Detectar si es un string que representa un objeto convertido (ej: '[object HTMLDivElement]')
    if (typeof targetSelector === 'string' && targetSelector.startsWith('[object ') && targetSelector.endsWith(']')) {
      throw new Error('[DOMUtils.onVisibleOnce] Se recibió un elemento HTML convertido a string. Pasa el selector CSS (ej: "#id") o el elemento directamente, no String(elemento).');
    }
    
    if (targetSelector instanceof Element) {
      // Si es un Element, intentar obtener su ID o usar el elemento directamente
      if (targetSelector.id) {
        normalizedSelector = '#' + targetSelector.id;
        isElement = false;
        console.warn('[DOMUtils.onVisibleOnce] Se recibió un Element. Usando su ID como selector:', normalizedSelector);
      } else {
        // Si no tiene ID, mantenerlo como Element pero crear un selector temporal
        normalizedSelector = targetSelector;
        isElement = true;
        console.warn('[DOMUtils.onVisibleOnce] Se recibió un Element sin ID. Usando el elemento directamente. Considera pasar un selector CSS en su lugar.');
      }
    } else if (typeof targetSelector !== 'string') {
      // Si es algo raro (como un objeto convertido a string), lanzar error
      throw new Error('[DOMUtils.onVisibleOnce] targetSelector debe ser un string (selector CSS) o un Element. Recibido: ' + typeof targetSelector + ' (' + String(targetSelector) + ')');
    }

    let fired = false;
    const tryRun = () => {
      try {
        // ⚠️ v3.3: Si es Element, usarlo directamente; si es string, usar querySelector
        let el;
        if (isElement) {
          // Verificar que el elemento aún existe en el DOM
          if (normalizedSelector.parentNode === null && !document.body.contains(normalizedSelector)) {
            // Elemento ya no está en el DOM, no hacer nada
            return;
          }
          el = normalizedSelector;
        } else {
          // Es un string selector
          el = document.querySelector(normalizedSelector);
        }
        
        if (el && !fired && isVisible(el)) {
          fired = true;
          callback(el);
        }
      } catch (err) {
        // ⚠️ v3.3: Silenciar errores de querySelector si el selector es inválido
        // Esto puede ocurrir si targetSelector fue convertido a string incorrectamente
        if (err.message && err.message.includes('not a valid selector')) {
          console.warn('[DOMUtils.onVisibleOnce] Selector inválido ignorado:', normalizedSelector);
          return;
        }
        throw err;
      }
    };

    // Bootstrap tabs/accordions
    document.addEventListener('shown.bs.tab', tryRun, { once: once });
    document.addEventListener('shown.bs.collapse', tryRun, { once: once });

    // Mutations
    const mo = new MutationObserver(tryRun);
    mo.observe(document.body, { attributes: true, childList: true, subtree: true });

    // Intento inmediato
    setTimeout(tryRun, 0);

    // Cleanup después de timeout
    if (timeout > 0) {
      setTimeout(() => {
        mo.disconnect();
      }, timeout);
    }

    return () => {
      mo.disconnect();
    };
  }

  /**
   * Formatea un valor numérico como moneda colombiana (COP)
   * @param {number|string} value - Valor a formatear
   * @param {Object} options - Opciones de formateo
   * @returns {string} Valor formateado como moneda COP
   */
  function formatCurrency(value, options = {}) {
    if (value === null || value === undefined || value === '') return '-';
    
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(numValue)) return '-';
    
    const {
      minimumFractionDigits = 0,
      maximumFractionDigits = 2,
      showSymbol = true
    } = options;
    
    try {
      const formatter = new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits,
        maximumFractionDigits,
      });
      
      const formatted = formatter.format(numValue);
      
      // Si no se quiere mostrar símbolo, removerlo
      if (!showSymbol) {
        return formatted.replace(/[COP$\s]/g, '').trim();
      }
      
      return formatted;
    } catch (err) {
      // Fallback simple si Intl.NumberFormat falla
      return `$${numValue.toLocaleString('es-CO', { minimumFractionDigits, maximumFractionDigits })}`;
    }
  }

  w.DOMUtils = Object.freeze({
    getEl,
    isVisible,
    waitForVisible,
    awaitVisibleAny,
    onVisibleOnce,
    formatCurrency
  });
})(window);
