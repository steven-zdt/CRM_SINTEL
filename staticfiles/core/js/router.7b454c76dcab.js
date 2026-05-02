/**
 * Router del Workspace - Hash-based routing
 * 
 * Maneja la navegación por hash (#empresa, #facturas, #mail, etc.)
 * e inyecta los partials de cada módulo en #workspace-router-outlet
 */

(function() {
  'use strict';

  const OUTLET_ID = 'workspace-router-outlet';
  const ROUTES = {
    'empresa': {
      init: 'initEmpresaPage',
      partial: null, // Se carga dinámicamente
    },
    'facturas': {
      init: 'initFacturasPage',
      partial: null,
    },
    'mail': {
      init: 'initMailDigesterPage',
      partial: null,
    },
    'perfil': {
      init: 'initPerfilPage',
      partial: null,
    },
    'dashboard': {
      init: 'initDashboardPage',
      partial: null,
    },
    'contabilidad': {
      init: 'initContabilidadPage',
      partial: null,
    },
    'inventario': {
      init: 'initInventarioPage',
      partial: null,
    },
    'empleados': {
      init: 'initEmpleadosPage',
      partial: null,
    },
    'gastos': {
      init: 'initGastosPage',
      partial: null,
    },
    'proveedores': {
      init: 'initProveedoresPage',
      partial: null,
    },
    'landing': {
      init: 'initLandingPage',
      partial: null,
    },
    'clientes': {
      init: 'initClientesPage',
      partial: null,
    },
  };

  let currentRoute = null;
  let currentView = null;

  /**
   * Obtiene la ruta actual desde el hash
   * @returns {string|null} Nombre de la ruta o null
   */
  function getCurrentRoute() {
    const hash = window.location.hash.slice(1); // Remover #
    if (!hash) return null;
    
    // Si hay sub-rutas (ej: #empresa/edit), tomar solo la primera parte
    const routeName = hash.split('/')[0];
    return routeName || null;
  }

  /**
   * Carga un partial HTML dinámicamente
   * @param {string} route - Nombre de la ruta
   * @returns {Promise<string>} HTML del partial
   */
  async function loadPartial(route) {
    // Por ahora, los partials se cargan desde los módulos
    // Esta función puede extenderse para cargar HTML estático si es necesario
    return '';
  }

  /**
   * Inicializa una vista del módulo
   * @param {string} route - Nombre de la ruta
   */
  async function initView(route) {
    const outlet = document.getElementById(OUTLET_ID);
    if (!outlet) {
      console.error('[router] Outlet no encontrado:', OUTLET_ID);
      return;
    }

    const routeConfig = ROUTES[route];
    if (!routeConfig) {
      console.warn('[router] Ruta no configurada:', route);
      outlet.innerHTML = `<div class="alert alert-warning">Módulo "${route}" no disponible</div>`;
      return;
    }

    // Limpiar vista anterior
    outlet.innerHTML = '<div class="text-center text-muted py-4">Cargando...</div>';

    try {
      // Llamar a la función de inicialización del módulo
      const initFn = window[routeConfig.init];
      if (typeof initFn === 'function') {
        console.log(`[router] Inicializando módulo: ${route}`);
        await initFn();
        currentView = route;
      } else {
        console.warn(`[router] Función ${routeConfig.init} no encontrada`);
        outlet.innerHTML = `<div class="alert alert-warning">Módulo "${route}" no inicializado</div>`;
      }
    } catch (error) {
      console.error(`[router] Error inicializando módulo ${route}:`, error);
      outlet.innerHTML = `<div class="alert alert-danger">Error cargando módulo: ${error.message}</div>`;
    }
  }

  /**
   * Maneja el cambio de hash
   */
  function handleHashChange() {
    const route = getCurrentRoute();
    
    if (route === currentRoute) {
      return; // Ya estamos en esta ruta
    }

    currentRoute = route;
    
    if (!route) {
      // Sin hash, mostrar vista por defecto o mensaje
      const outlet = document.getElementById(OUTLET_ID);
      if (outlet) {
        outlet.innerHTML = '<div class="alert alert-info">Selecciona un módulo del menú</div>';
      }
      return;
    }

    initView(route);
  }

  /**
   * Inicializa el router
   */
  function init() {
    console.log('[router] Inicializando router del workspace');
    
    // Manejar hash inicial
    handleHashChange();
    
    // Escuchar cambios de hash
    window.addEventListener('hashchange', handleHashChange);
    
    // Escuchar clicks en links con data-view
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[data-view]');
      if (link) {
        const view = link.getAttribute('data-view');
        if (view) {
          window.location.hash = view;
          e.preventDefault();
        }
      }
    });
  }

  // Inicializar cuando el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Exportar para uso global
  if (typeof window !== 'undefined') {
    window.workspaceRouter = {
      init,
      getCurrentRoute,
      initView,
    };
  }
})();
