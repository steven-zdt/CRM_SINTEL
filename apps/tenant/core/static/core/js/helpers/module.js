/**
 * Module Helper - Bootstrap estándar por página
 * 
 * ⚠️ OLA 1: Helper centralizado para inicialización de módulos
 * - Flujo: awaitVisible(container) → Routes.get(module) → DataTablesUtils.initServerSide → callbacks
 * - Permite que *.page.js quede reducido a "configurar columnas y callbacks"
 */

(function (w) {
  'use strict';

  /**
   * Inicializa un módulo con bootstrap estándar
   * @param {Object} config - Configuración del módulo
   * @param {string} config.module - Nombre del módulo (ej: 'facturas', 'inventario.catalogo')
   * @param {string} config.container - Selector del contenedor principal
   * @param {string} [config.table] - Selector de la tabla (opcional)
   * @param {Array} [config.columns] - Columnas de DataTable (opcional)
   * @param {Object} [config.datatableOptions] - Opciones adicionales para DataTable (opcional)
   * @param {Function} [config.onInit] - Callback después de inicialización (opcional)
   * @param {Function} [config.onBindEvents] - Callback para bindear eventos (opcional)
   * @returns {Promise<Object>} Objeto con estado del módulo
   */
  async function init(config) {
    const {
      module,
      container,
      table,
      columns,
      datatableOptions = {},
      onInit,
      onBindEvents
    } = config;

    if (!module) {
      console.error('[Module] module es requerido');
      return { ok: false, error: 'module es requerido' };
    }

    if (!container) {
      console.error('[Module] container es requerido');
      return { ok: false, error: 'container es requerido' };
    }

    // 1. Esperar visibilidad del contenedor
    if (w.DOMUtils && typeof w.DOMUtils.waitForVisible === 'function') {
      try {
        await w.DOMUtils.waitForVisible(container, { timeout: 10000 });
      } catch (err) {
        console.warn('[Module] Timeout esperando visibilidad:', err);
        return { ok: false, error: 'Timeout esperando visibilidad del contenedor' };
      }
    } else {
      // Fallback: espera básica
      const el = document.querySelector(container);
      if (!el) {
        console.error('[Module] Contenedor no encontrado:', container);
        return { ok: false, error: 'Contenedor no encontrado' };
      }
    }

    // 2. Cargar rutas del módulo
    let routes = null;
    if (w.Routes && typeof w.Routes.get === 'function') {
      routes = await w.Routes.get(module);
      const DEBUG = (w.__DEBUG__ === true) || (w.API_HELPERS?.DEBUG === true);
      if (!routes && DEBUG) {
        console.warn('[Module] Rutas no encontradas para módulo:', module);
      }
    }

    // 3. Inicializar DataTable si hay tabla y columnas
    let dtInstance = null;
    if (table && columns && Array.isArray(columns) && columns.length > 0) {
      if (w.DataTablesUtils && typeof w.DataTablesUtils.initServerSide === 'function') {
        const endpoint = routes?.datatable || null;
        if (endpoint) {
          try {
            dtInstance = await w.DataTablesUtils.initServerSide({
              table,
              endpoint,
              columns,
              ...datatableOptions
            });
          } catch (err) {
            console.error('[Module] Error inicializando DataTable:', err);
            return { ok: false, error: 'Error inicializando DataTable', details: err };
          }
        } else {
          console.warn('[Module] Endpoint de DataTable no encontrado para módulo:', module);
        }
      } else {
        console.warn('[Module] DataTablesUtils.initServerSide no disponible');
      }
    }

    // 4. Ejecutar callback onInit
    const state = {
      ok: true,
      module,
      container,
      routes,
      dtInstance
    };

    if (typeof onInit === 'function') {
      try {
        await onInit(state);
      } catch (err) {
        console.error('[Module] Error en onInit:', err);
      }
    }

    // 5. Ejecutar callback onBindEvents
    if (typeof onBindEvents === 'function') {
      try {
        await onBindEvents(state);
      } catch (err) {
        console.error('[Module] Error en onBindEvents:', err);
      }
    }

    return state;
  }

  // Exportar API pública
  w.Module = Object.freeze({
    init
  });
})(window);
