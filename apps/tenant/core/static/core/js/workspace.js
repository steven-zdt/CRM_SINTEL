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
            'dashboard': '📊 Dashboard',
            'empresa': '🏢 Empresa',
            'facturas': '🧾 Facturas',
            'contabilidad': '📚 Contabilidad',
            'inventario': '📦 Inventario',
            'empleados': '👥 Empleados',
            'gastos': '💰 Gastos',
            'bancos': '🏦 Bancos',
            'proveedores': '🏪 Proveedores',
            'clientes': '👤 Clientes',
            'cotizaciones': '📝 Cotizaciones',
            'proyectos': '📋 Proyectos',
            'ventas': 'Ventas',
            'compras': 'Compras',
            'perfil': '👤 Perfil',
            'mailinbox': '📧 Correo Entrante'
          };
          title.textContent = titles[tabName] || 'Workspace';
        }
        
        // ⚠️ v3.0: Disparar evento personalizado para que cada módulo se auto-inicialice
        console.log('[workspace] Dispatching tab-activated:', tabName);
        document.dispatchEvent(new CustomEvent('tab-activated', { detail: { tabName } }));
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
      const redirectUrl = data.redirect_url || '/static/tenant/core/auth/login.html';
      window.location.replace(redirectUrl);
    } catch (error) {
      console.error('[workspace] Error en logout:', error);
      // Fallback: redirigir a la página de login
      window.location.replace('/static/tenant/core/auth/login.html');
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
    // Ensure API calls include credentials so HttpOnly cookies are sent
    (function setupFetchForCookies(){
      try {
        const _fetch = window.fetch;
        window.fetch = function(resource, init){
          try {
            const url = (typeof resource === 'string') ? resource : resource.url || '';
            const isApi = url.startsWith('/api/') || url.includes('/api/');
            if (isApi) {
              init = init || {};
              // ensure credentials include cookies for cross-origin or same-origin
              if (!init.credentials) init.credentials = 'include';
            }
          } catch (err) {
            console.warn('[workspace] setupFetchForCookies error', err);
          }
          return _fetch.apply(this, arguments);
        };
        console.log('[workspace] fetch patched to include credentials for API calls');
      } catch (e) {
        console.warn('[workspace] Could not patch fetch for cookies', e);
      }
    })();

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
