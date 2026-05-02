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

  function initClientesTable() {
    try {
      if (w.clientesDT && typeof w.clientesDT.init === 'function') {
        w.clientesDT.init();
      }
    } catch (err) {
      console.error('[clientes.module] Error inicializando clientesDT:', err);
      if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
        w.UIManager.notifyError({ status: 500, data: { detail: 'Error inicializando el módulo de Clientes.' } }, '[clientes.module]');
      } else if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
        w.SintelFeedback.error('Error inicializando el módulo de Clientes.');
      }
    }
  }

  // Lazy init cuando el tab del workspace cambia a "clientes"
  // workspace.js dispara shown.bs.tab para tabs Bootstrap internos, pero el sidebar
  // es custom; por eso escuchamos el evento "hashchange" y clicks en el nav.
  function bindLazyInit() {
    // Caso 1: navegación por hash (#clientes)
    function maybeInitFromHash() {
      if (w.location && typeof w.location.hash === 'string' && w.location.hash === '#clientes') {
        initClientesTable();
      }
    }

    w.addEventListener('hashchange', maybeInitFromHash);

    // Caso 2: click en sidebar (workspace)
    const nav = d.getElementById('nav');
    if (nav) {
      nav.addEventListener('click', function(e) {
        const link = e.target.closest('a[data-tab]');
        if (!link) return;
        const tabName = link.getAttribute('data-tab');
        if (tabName === 'clientes') {
          // dejar que el DOM muestre el tab primero
          setTimeout(initClientesTable, 0);
        }
      });
    }

    // Caso 3: si ya estamos en hash #clientes al cargar
    maybeInitFromHash();
  }

  // Export simple
  w.ClientesWorkspaceModule = {
    init: initClientesTable,
    bind: bindLazyInit,
  };

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', bindLazyInit);
  } else {
    bindLazyInit();
  }
})(window, document);
