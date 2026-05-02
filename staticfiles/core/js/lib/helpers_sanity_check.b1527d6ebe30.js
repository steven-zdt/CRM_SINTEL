/**
 * Helpers Sanity Check - Verificación de disponibilidad de helpers Core
 * 
 * ⚠️ FASE 0: Script de verificación para asegurar que todos los helpers
 * estén disponibles antes de que los módulos intenten usarlos.
 * 
 * Este script debe cargarse DESPUÉS de assets_core.html y ANTES de cualquier
 * script de módulo/app.
 */

(function (w, d) {
  'use strict';

  const REQUIRED_HELPERS = [
    { name: 'API_HELPERS', check: () => w.API_HELPERS && typeof w.API_HELPERS === 'object' },
    { name: 'DOMUtils', check: () => w.DOMUtils && typeof w.DOMUtils === 'object' },
    { name: 'DataTablesUtils', check: () => w.DataTablesUtils && typeof w.DataTablesUtils === 'object' },
    { name: 'Routes', check: () => w.Routes && typeof w.Routes === 'object' },
    { name: 'CRUD', check: () => w.CRUD && typeof w.CRUD === 'object' },
    { name: 'Module', check: () => w.Module && typeof w.Module === 'object' }
  ];

  const REQUIRED_FUNCTIONS = [
    { helper: 'API_HELPERS', func: 'safeFetchJson', check: () => w.API_HELPERS?.safeFetchJson && typeof w.API_HELPERS.safeFetchJson === 'function' },
    { helper: 'API_HELPERS', func: 'getCSRF', check: () => w.API_HELPERS?.getCSRF && typeof w.API_HELPERS.getCSRF === 'function' },
    { helper: 'API_HELPERS', func: 'withTrailingSlash', check: () => w.API_HELPERS?.withTrailingSlash && typeof w.API_HELPERS.withTrailingSlash === 'function' },
    { helper: 'DOMUtils', func: 'waitForVisible', check: () => w.DOMUtils?.waitForVisible && typeof w.DOMUtils.waitForVisible === 'function' },
    { helper: 'DOMUtils', func: 'awaitVisibleAny', check: () => w.DOMUtils?.awaitVisibleAny && typeof w.DOMUtils.awaitVisibleAny === 'function' },
    { helper: 'DataTablesUtils', func: 'initServerSide', check: () => w.DataTablesUtils?.initServerSide && typeof w.DataTablesUtils.initServerSide === 'function' },
    { helper: 'DataTablesUtils', func: 'safeDestroy', check: () => w.DataTablesUtils?.safeDestroy && typeof w.DataTablesUtils.safeDestroy === 'function' },
    { helper: 'Routes', func: 'get', check: () => w.Routes?.get && typeof w.Routes.get === 'function' },
    { helper: 'Routes', func: 'collectionUrl', check: () => w.Routes?.collectionUrl && typeof w.Routes.collectionUrl === 'function' },
    { helper: 'CRUD', func: 'create', check: () => w.CRUD?.create && typeof w.CRUD.create === 'function' },
    { helper: 'Module', func: 'init', check: () => w.Module?.init && typeof w.Module.init === 'function' }
  ];

  /**
   * Ejecuta el sanity check
   */
  function runSanityCheck() {
    const results = {
      timestamp: new Date().toISOString(),
      helpers: {},
      functions: {},
      allOk: true,
      errors: []
    };

    // Verificar helpers
    REQUIRED_HELPERS.forEach(({ name, check }) => {
      const ok = check();
      results.helpers[name] = ok;
      if (!ok) {
        results.allOk = false;
        results.errors.push(`Helper ${name} no está disponible`);
      }
    });

    // Verificar funciones críticas
    REQUIRED_FUNCTIONS.forEach(({ helper, func, check }) => {
      const ok = check();
      const key = `${helper}.${func}`;
      results.functions[key] = ok;
      if (!ok) {
        results.allOk = false;
        results.errors.push(`Función ${helper}.${func} no está disponible`);
      }
    });

    // Log resultados
    if (results.allOk) {
      const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
      if (DEBUG) {
        console.log('[Helpers Sanity Check] ✅ Todos los helpers están disponibles');
      }
    } else {
      console.error('[Helpers Sanity Check] ❌ Errores detectados:', results.errors);
      console.error('[Helpers Sanity Check] Resultados:', results);
    }

    // Exponer resultados globalmente
    w.__HELPERS_SANITY_CHECK = results;

    return results;
  }

  // Ejecutar cuando DOM esté listo
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', runSanityCheck);
  } else {
    runSanityCheck();
  }

  // También exponer función manual
  w.runHelpersSanityCheck = runSanityCheck;
})(window, document);
