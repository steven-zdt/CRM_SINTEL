/**
 * clientes.module.js - Orquestación UI (Workspace) para Clientes v2.60
 *
 * Responsabilidad:
 * - Inicializar el módulo de clientes solo cuando el usuario activa el tab "Clientes"
 * - Integrar manejo de errores con UIManager/SintelFeedback (sin alerts nativos)
 *
 * Nota: La lógica de Tabulator vive en features/clientes_list.js.
 */

(function(w, d) {
  'use strict';

  let initialized = false;

  function initClientesTable() {
    if (initialized) {
      // Si ya está inicializado, opcionalmente refrescar datos
      if (w.clientesDT && typeof w.clientesDT.refresh === 'function') {
        w.clientesDT.refresh();
      }
      return;
    }

    try {
      if (w.clientesDT && typeof w.clientesDT.init === 'function') {
        w.clientesDT.init();
        initialized = true;
        console.log('[clientes.module] Inicializado correctamente');
      }
    } catch (err) {
      console.error('[clientes.module] Error inicializando clientesDT:', err);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Error inicializando el módulo de Clientes.' } }, '[clientes.module]');
      }
    }
  }

  /**
   * Registro centralizado de inicialización v2.60.2
   */
  function handleInit() {
    // Pequeño delay de cortesía para estabilizar el DOM y evitar colisiones de mensajes en el navegador
    setTimeout(initClientesTable, 50);
  }

  // Escuchar evento centralizado de workspace.js
  d.addEventListener('tab-activated', function(event) {
    if (event.detail?.tabName === 'clientes') {
      handleInit();
    }
  });

  // Caso: Carga directa con hash
  if (w.location.hash === '#clientes') {
    if (d.readyState === 'loading') {
      d.addEventListener('DOMContentLoaded', handleInit);
    } else {
      handleInit();
    }
  }

  // Export simple
  w.ClientesWorkspaceModule = {
    init: initClientesTable
  };

})(window, document);
