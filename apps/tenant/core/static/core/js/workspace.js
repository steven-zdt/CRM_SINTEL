/**
 * workspace.js - Navegación simple de tabs para workspace v2.40
 * 
 * ⚠️ v2.40: Sin JS inline, todo en archivos modulares
 */

(function() {
  'use strict';
  
  // ⚠️ v3.3: Función ajustarDataTablesInventario() ELIMINADA
  // Migrado completamente a Tabulator - Ya no se necesita ajuste de DataTables
  
  // Ocultar todos los tabs y mostrar el welcome
  function hideAllTabs() {
    document.querySelectorAll('.workspace-tab').forEach(tab => {
      tab.style.display = 'none';
    });
    const welcome = document.getElementById('workspace-welcome');
    if (welcome) welcome.style.display = 'block';
  }
  
  // Mostrar un tab específico
  function showTab(tabName) {
    hideAllTabs();
    const tab = document.getElementById('tab-' + tabName);
    if (tab) {
      tab.style.display = 'block';
      const welcome = document.getElementById('workspace-welcome');
      if (welcome) welcome.style.display = 'none';
      
      // Actualizar título
      const title = document.getElementById('viewTitle');
      if (title) {
        const titles = {
          'empresa': '🏢 Empresa',
          'facturas': '🧾 Facturas',
          'contabilidad': '📚 Contabilidad',
          'inventario': '📦 Inventario',
          'empleados': '👥 Empleados',
          'gastos': '💰 Gastos',
          'proveedores': '🏪 Proveedores',
          'clientes': '👤 Clientes',
          'proyectos': '📋 Proyectos',
          'perfil': '👤 Perfil',
          'mailinbox': '📧 Correo Entrante'
        };
        title.textContent = titles[tabName] || 'Workspace';
      }
      
      // Inicializar DataTables del módulo usando la API estándar
      // ⚠️ v2.37: Tab empresa contiene dos módulos independientes
      // ⚠️ v2.37: Tab contabilidad contiene tabs internos (cuentas y asientos)
      if (tabName === 'empresa') {
        // Inicializar ambos módulos independientes
        setTimeout(() => {
          if (window.empresaDT && typeof window.empresaDT.init === 'function') {
            window.empresaDT.init();
          }
          if (window.mailinboxDT && typeof window.mailinboxDT.init === 'function') {
            window.mailinboxDT.init();
          }
        }, 200);
      } else if (tabName === 'contabilidad') {
        // Inicializar módulo de cuentas (tab activo por defecto)
        setTimeout(() => {
          if (window.cuentasDT && typeof window.cuentasDT.init === 'function') {
            window.cuentasDT.init();
          }
        }, 200);
        
        // Listener para tabs internos de contabilidad
        setTimeout(() => {
          const cuentasTab = document.getElementById('contabilidad-cuentas-tab');
          const asientosTab = document.getElementById('contabilidad-asientos-tab');
          
          if (cuentasTab) {
            cuentasTab.addEventListener('shown.bs.tab', () => {
              if (window.cuentasDT && typeof window.cuentasDT.init === 'function') {
                window.cuentasDT.init();
              }
            });
          }
          
          if (asientosTab) {
            asientosTab.addEventListener('shown.bs.tab', () => {
              // ⚠️ v2.60: asientos_main.js expone window.AppAsientos, no window.asientosDT
              if (window.AppAsientos && typeof window.AppAsientos.init === 'function') {
                window.AppAsientos.init();
              } else if (window.asientosDT && typeof window.asientosDT.init === 'function') {
                // Fallback para compatibilidad legacy
                window.asientosDT.init();
              }
            });
          }
        }, 300);
      } else if (tabName === 'inventario') {
        // ⚠️ v2.40: Los módulos se inicializan automáticamente con DOMUtils.onVisibleOnce
        // Solo necesitamos ajustar DataTables cuando se muestre el tab principal
        setTimeout(() => {
          // ⚠️ v3.3: ajustarDataTablesInventario() eliminado - Migrado a Tabulator
        }, 200);
        
        // Listener para tabs internos de inventario (Bootstrap 5 tabs) - Solo agregar una vez
        // ⚠️ v2.40: IDs correctos son inventario-*-tab, no tab-*-tab
        // ⚠️ v2.40: Todos los módulos (Categorías, Productos, Servicios, Activos, Movimientos) 
        // usan TabulatorFactory y se inicializan automáticamente con DOMUtils.onVisibleOnce
        if (!window._inventarioTabsInitialized) {
          setTimeout(() => {
            const categoriasTab = document.getElementById('inventario-categorias-tab');
            const productosTab = document.getElementById('inventario-productos-tab');
            const serviciosTab = document.getElementById('inventario-servicios-tab');
            const activosTab = document.getElementById('inventario-activos-tab');
            const movimientosTab = document.getElementById('inventario-movimientos-tab');
            
            // Función helper para redraw de Tabulator
            const redrawTabulator = (moduleName) => {
              setTimeout(() => {
                const module = window[moduleName];
                if (module && module.table && typeof module.table.redraw === 'function') {
                  module.table.redraw();
                }
              }, 100);
            };
            
            // Todos los módulos usan TabulatorFactory ahora
            if (categoriasTab) {
              categoriasTab.addEventListener('shown.bs.tab', () => redrawTabulator('categoriasPage'));
            }
            
            if (productosTab) {
              productosTab.addEventListener('shown.bs.tab', () => redrawTabulator('InventarioProductosModule'));
            }
            
            if (serviciosTab) {
              serviciosTab.addEventListener('shown.bs.tab', () => redrawTabulator('InventarioServiciosModule'));
            }
            
            if (activosTab) {
              activosTab.addEventListener('shown.bs.tab', () => redrawTabulator('InventarioActivosModule'));
            }
            
            if (movimientosTab) {
              movimientosTab.addEventListener('shown.bs.tab', () => redrawTabulator('InventarioMovimientosModule'));
            }
            
            window._inventarioTabsInitialized = true;
          }, 300);
        }
      } else {
        // Mapeo de nombres de módulo a objetos DT para otros tabs
        const dtModules = {
          'facturas': window.facturasDT,
          'contabilidad': window.contabilidadDT,
          'empleados': window.empleadosDT,
          'gastos': window.gastosDT,
          'proveedores': window.ProveedoresModule,
          'clientes': window.clientesDT,
          'proyectos': window.ProyectosModule,
          'perfil': window.perfilDT,
        };
        
        const dtModule = dtModules[tabName];
        if (dtModule && typeof dtModule.init === 'function') {
          setTimeout(() => {
            dtModule.init();
          }, 100);
        } else {
          // Fallback: usar función genérica si existe
          const initFunc = window[`init${tabName.charAt(0).toUpperCase() + tabName.slice(1)}Page`];
          if (typeof initFunc === 'function') {
            setTimeout(initFunc, 100);
          }
        }
      }
    }
  }
  
  /**
   * Maneja el logout del usuario.
   * ⚠️ POLÍTICA API-First: Consume endpoint de logout
   */
  async function handleLogout() {
    try {
      // Obtener CSRF token
      function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
          const cookies = document.cookie.split(';');
          for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
            }
          }
        }
        return cookieValue;
      }
      
      const csrftoken = getCookie('csrftoken');
      
      // Llamar al endpoint de logout (API-First)
      const response = await fetch('/api/v1/core/auth/logout/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        credentials: 'same-origin'
      });
      
      const data = await response.json();
      
      // Usar redirect_url de la respuesta JSON (API-First)
      const redirectUrl = data.redirect_url || '/static/tenant/landing/login.html';
      window.location.replace(redirectUrl);
    } catch (error) {
      console.error('[workspace] Error en logout:', error);
      // Fallback: redirigir a la página de login
      window.location.replace('/static/tenant/landing/login.html');
    }
  }
  
  /**
   * ⚠️ LIMPIEZA: Eliminar parámetros de descuento de la URL (aplicar_descuento, porcentaje_descuento)
   * Estos parámetros no deben existir en el sistema
   */
  function limpiarParametrosDescuento() {
    const url = new URL(window.location.href);
    const paramsToRemove = ['aplicar_descuento', 'porcentaje_descuento'];
    let hasChanges = false;
    
    paramsToRemove.forEach(param => {
      if (url.searchParams.has(param)) {
        url.searchParams.delete(param);
        hasChanges = true;
      }
    });
    
    if (hasChanges) {
      // Reemplazar la URL sin los parámetros de descuento
      const newUrl = url.pathname + url.search + url.hash;
      window.history.replaceState(null, '', newUrl);
      console.log('[workspace] ✅ Parámetros de descuento eliminados de la URL');
    }
  }
  
  // Bind eventos del sidebar
  document.addEventListener('DOMContentLoaded', function() {
    // ⚠️ LIMPIEZA: Eliminar parámetros de descuento al cargar la página
    limpiarParametrosDescuento();
    
    const navLinks = document.querySelectorAll('#nav a[data-tab]');
    navLinks.forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        const tabName = this.getAttribute('data-tab');
        showTab(tabName);
        
        // Actualizar clase activa en sidebar
        navLinks.forEach(l => l.classList.remove('active'));
        this.classList.add('active');
        
        // Actualizar hash en URL (sin parámetros de descuento)
        const url = new URL(window.location.href);
        const paramsToRemove = ['aplicar_descuento', 'porcentaje_descuento'];
        paramsToRemove.forEach(param => url.searchParams.delete(param));
        const cleanUrl = url.pathname + url.search + '#' + tabName;
        window.history.pushState(null, '', cleanUrl);
      });
    });
    
    // Configurar botón de logout
    const logoutBtn = document.getElementById('account-menu-logout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function(e) {
        e.preventDefault();
        handleLogout();
      });
      console.log('[workspace] Botón de logout configurado');
    } else {
      console.warn('[workspace] Botón de logout no encontrado (#account-menu-logout)');
    }
    
    // Si hay hash en URL, mostrar ese tab
    if (window.location.hash) {
      const hash = window.location.hash.substring(1);
      showTab(hash);
      const activeLink = document.querySelector(`#nav a[data-tab="${hash}"]`);
      if (activeLink) activeLink.classList.add('active');
    }
    
    // Manejar navegación del navegador (back/forward)
    window.addEventListener('popstate', function() {
      // ⚠️ LIMPIEZA: Eliminar parámetros de descuento en navegación
      limpiarParametrosDescuento();
      
      if (window.location.hash) {
        const hash = window.location.hash.substring(1);
        showTab(hash);
        const activeLink = document.querySelector(`#nav a[data-tab="${hash}"]`);
        if (activeLink) {
          document.querySelectorAll('#nav a').forEach(l => l.classList.remove('active'));
          activeLink.classList.add('active');
        }
      } else {
        hideAllTabs();
      }
    });
    
    // ⚠️ LIMPIEZA: Limpiar parámetros de descuento también cuando cambia la URL
    window.addEventListener('hashchange', function() {
      limpiarParametrosDescuento();
    });
  });
})();
