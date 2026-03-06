/**
 * perfil.page.js - Módulo Perfil v2.40 - Tabulator Implementation
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Lazy Loading: Usa DOMUtils.onVisibleOnce() para inicialización diferida
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - DOMUtils: onVisibleOnce()
 * - w.perfilAPI (definido en perfil.api.js)
 * - w.perfilModals (definido en perfil.modals.js) - opcional
 */
(function (w, d) {
  'use strict';

  const MOD = 'perfil';
  const CONTAINER_ID = '#tab-perfil';
  const GRID_ID = '#grid-perfil';
  const SEARCH_INPUT_ID = '#search-perfil';
  const API_URL = '/api/v1/perfil/perfiles/';
  
  let table = null;

  function getColumns() {
    return [
      { title: "ID", field: "id", visible: false },
      { 
        title: "Usuario", 
        field: "user_full_name", 
        minWidth: 200,
        formatter: function(cell) {
          const rowData = cell.getRow().getData();
          const nombre = rowData.user_full_name || rowData.user_email || '-';
          const email = rowData.user_email || '';
          return `
            <div>
              <strong>${nombre}</strong>
              ${email ? `<br><small class="text-muted">${email}</small>` : ''}
            </div>
          `;
        }
      },
      { 
        title: "Cargo", 
        field: "cargo", 
        width: 150,
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '<span class="text-muted">-</span>';
        }
      },
      { 
        title: "Departamento", 
        field: "departamento", 
        width: 150,
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '<span class="text-muted">-</span>';
        }
      },
      { 
        title: "Teléfono", 
        field: "telefono_corporativo", 
        width: 120,
        formatter: function(cell) {
          const val = cell.getValue();
          return val || '<span class="text-muted">-</span>';
        }
      },
      { 
        title: "Avatar", 
        field: "avatar_url", 
        width: 80,
        hozAlign: "center",
        formatter: function(cell) {
          const avatarUrl = cell.getValue();
          if (avatarUrl) {
            return `<img src="${avatarUrl}" alt="Avatar" class="rounded-circle" style="width: 40px; height: 40px; object-fit: cover;" />`;
          }
          return '<i class="fas fa-user-circle text-muted" style="font-size: 40px;"></i>';
        }
      },
      { 
        title: "Acciones", 
        hozAlign: "center", 
        width: 180, 
        headerSort: false,
        formatter: function(cell) {
          const data = cell.getRow().getData();
          const id = data.id;
          
          let html = '<div class="btn-group btn-group-sm" role="group">';
          
          // Botón Ver
          html += `<button type="button" class="btn btn-outline-primary" data-action="ver" data-id="${id}" title="Ver Perfil">
            <i class="fas fa-eye"></i>
          </button>`;
          
          // Botón Editar (solo si es el perfil del usuario actual)
          // Nota: Esto se puede validar en el backend también
          html += `<button type="button" class="btn btn-outline-success" data-action="editar" data-id="${id}" title="Editar Perfil">
            <i class="fas fa-edit"></i>
          </button>`;
          
          html += '</div>';
          return html;
        }
      }
    ];
  }

  // Inicializar tabla
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(`[${MOD}.page] TabulatorFactory no está disponible`);
      return null;
    }

    const columns = getColumns();
    table = w.TabulatorFactory.create(GRID_ID, API_URL, columns, {
      searchInputSelector: SEARCH_INPUT_ID
    });

    // ⚠️ v2.40: Event delegation para botones de acciones
    if (table) {
      const container = d.querySelector(GRID_ID);
      if (container) {
        container.addEventListener('click', function(e) {
          const btn = e.target.closest('button[data-action]');
          if (!btn) return;
          
          e.preventDefault();
          e.stopPropagation();
          
          const action = btn.getAttribute('data-action');
          const id = parseInt(btn.getAttribute('data-id'), 10);
          
          if (!id || isNaN(id)) {
            console.warn(`[${MOD}.page] ID no válido:`, id);
            return;
          }
          
          // Ejecutar acción según el botón
          switch (action) {
            case 'ver':
              if (w.perfilModals && typeof w.perfilModals.showDetail === 'function') {
                w.perfilModals.showDetail(id);
              } else if (typeof handleVerPerfil === 'function') {
                handleVerPerfil(id);
              }
              break;
            case 'editar':
              if (w.perfilModals && typeof w.perfilModals.showEdit === 'function') {
                w.perfilModals.showEdit(id);
              } else if (typeof handleEditarPerfil === 'function') {
                handleEditarPerfil(id);
              }
              break;
            default:
              console.warn(`[${MOD}.page] Acción no reconocida:`, action);
          }
        });
      }
    }

    return table;
  }

  // Función para verificar dependencias
  function verificarDependencias() {
    const dependencias = {
      TabulatorFactory: w.TabulatorFactory,
      perfilAPI: w.perfilAPI
    };
    
    const faltantes = Object.keys(dependencias).filter(key => !dependencias[key]);
    
    if (faltantes.length > 0) {
      console.warn(`[${MOD}.page] ⚠️ Dependencias faltantes:`, faltantes);
      return false;
    }
    
    return true;
  }

  // Función para inicializar el módulo completo
  async function inicializarModulo() {
    console.log(`[${MOD}.page] Inicializando módulo completo...`);
    
    // Verificar dependencias críticas
    if (!w.TabulatorFactory) {
      console.error(`[${MOD}.page] ❌ CRÍTICO: TabulatorFactory no está disponible.`);
      return;
    }
    
    // Verificar todas las dependencias
    if (!verificarDependencias()) {
      console.error(`[${MOD}.page] ❌ Faltan dependencias críticas. Revisa el orden de carga de scripts.`);
      return;
    }
    
    console.log(`[${MOD}.page] ✅ Todas las dependencias están disponibles`);
    console.log(`[${MOD}.page] - TabulatorFactory:`, !!w.TabulatorFactory);
    console.log(`[${MOD}.page] - perfilAPI:`, !!w.perfilAPI);
    
    // Inicializar tabla
    initTable();
    
    // Exponer módulo globalmente ANTES de configurar eventos
    w.perfilPage = {
      table: table,
      refresh: function() {
        if (table) {
          table.replaceData();
        }
      }
    };
    
    console.log(`[${MOD}.page] Módulo expuesto globalmente:`, w.perfilPage);
    
    // Configurar eventos DESPUÉS de inicializar el módulo
    configurarEventos();
  }

  // Función para configurar eventos
  function configurarEventos() {
    console.log(`[${MOD}.page] Configurando eventos...`);
    
    // Botón Crear (si existe)
    const btnCrear = d.getElementById('btn-perfil-crear');
    if (btnCrear) {
      const nuevoBtn = btnCrear.cloneNode(true);
      nuevoBtn.removeAttribute('onclick');
      btnCrear.parentNode.replaceChild(nuevoBtn, btnCrear);
      
      nuevoBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log(`[${MOD}.page] Click en botón "Nuevo Perfil"`);
        // Aquí se puede agregar lógica para crear nuevo perfil si es necesario
        if (w.perfilModals && typeof w.perfilModals.showCreate === 'function') {
          w.perfilModals.showCreate();
        }
      });
    }

    // Botón Refrescar
    const btnRefrescar = d.getElementById('btn-refrescar-perfil');
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', function() {
        console.log(`[${MOD}.page] Refrescando tabla...`);
        if (table) {
          table.replaceData();
        }
      });
    }
  }

  // Lazy Loading: Inicializar solo cuando el tab sea visible
  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(CONTAINER_ID, function() {
      console.log(`[${MOD}.page] Tab de perfil visible, inicializando...`);
      inicializarModulo().catch(err => {
        console.error(`[${MOD}.page] Error en inicialización:`, err);
      });
    });
  } else {
    // Fallback si DOMUtils no está disponible
    console.warn(`[${MOD}.page] DOMUtils no disponible, inicializando inmediatamente`);
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      
      inicializarModulo().catch(err => {
        console.error(`[${MOD}.page] Error en inicialización (fallback):`, err);
      });
    }
    initFallback();
  }
  
  // También configurar eventos cuando el tab de perfil se muestre (Bootstrap event)
  d.addEventListener('shown.bs.tab', function(e) {
    const target = e.target;
    const isPerfilTab = target && (
      target.getAttribute('data-tab') === 'perfil' || 
      target.getAttribute('data-bs-target') === CONTAINER_ID ||
      target.getAttribute('href') === CONTAINER_ID ||
      target.getAttribute('href') === '#perfil'
    );
    
    if (isPerfilTab) {
      console.log(`[${MOD}.page] Tab de perfil mostrado, verificando eventos...`);
      // Asegurar que el módulo esté inicializado
      if (!w.perfilPage || !w.perfilPage.table) {
        console.log(`[${MOD}.page] Módulo no inicializado, inicializando ahora...`);
        inicializarModulo().catch(err => {
          console.error(`[${MOD}.page] Error en inicialización (shown.bs.tab):`, err);
        });
      } else {
        // Redraw de la tabla si ya está inicializada
        if (w.perfilPage.table && typeof w.perfilPage.table.redraw === 'function') {
          setTimeout(() => {
            w.perfilPage.table.redraw();
          }, 100);
        }
      }
    }
  });

})(window, document);
