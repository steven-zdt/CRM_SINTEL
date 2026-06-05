// apps/tenant/core/static/core/js/perfil/perfil.page.js (migrated to perfil app)
(function (w, d) {
  'use strict';

  const MOD = 'perfil';
  const CONTAINER_ID = '#tab-perfil';
  const GRID_ID = '#grid-perfil';
  const SEARCH_INPUT_ID = '#search-perfil';
  const API_URL = '/api/v1/perfil/perfiles/';
  
  let table = null;
  // Contexto de permisos del usuario autenticado actual (cargado desde /me/)
  let requestorContext = {};

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
        field: "departamento_nombre", 
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
        title: "Rol",
        field: "rol",
        width: 100,
        hozAlign: "center",
        formatter: function(cell) {
          const val = cell.getValue();
          const map = { 'ADMIN': 'bg-danger', 'OPERADOR': 'bg-primary', 'VISOR': 'bg-secondary' };
          const cls = map[val] || 'bg-secondary';
          return val ? '<span class="badge ' + cls + '">' + val + '</span>' : '<span class="text-muted">-</span>';
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
        width: 210, 
        headerSort: false,
        formatter: function(cell) {
          var data = cell.getRow().getData();
          var id = data.uuid || data.id;  // [RULE 14] Prefer UUID; fallback to PK for legacy rows
          // Usar requestorContext (precargado via /me/) como SSoT de permisos.
          // Fallback a available_actions por fila si el contexto no cargo aun.
          var actions = (requestorContext._actions && requestorContext._actions.length > 0)
            ? requestorContext._actions
            : (Array.isArray(data.available_actions) ? data.available_actions : []);
          var canEdit = actions.length === 0 || actions.includes('edit');
          var canAssignRol = actions.includes('assign_rol');
          // [SEG-5] Prohibir auto-eliminacion: esconder boton si la fila es el propio usuario
          var isSelf = requestorContext.user_id != null && data.user_id != null
            && Number(data.user_id) === Number(requestorContext.user_id);
          var canDelete = actions.includes('delete') && !isSelf;
          
          var html = '<div class="btn-group btn-group-sm" role="group">';
          
          html += '<button type="button" class="btn btn-outline-primary" data-action="ver" data-id="' + id + '" title="Ver Perfil"><i class="fas fa-eye"></i></button>';
          
          if (canEdit) {
            html += '<button type="button" class="btn btn-outline-success" data-action="editar" data-id="' + id + '" title="Editar Perfil"><i class="fas fa-edit"></i></button>';
          }

          if (canAssignRol) {
            html += '<button type="button" class="btn btn-outline-warning" data-action="asignar-rol" data-id="' + id + '" title="Asignar Rol"><i class="fas fa-user-shield"></i></button>';
          }

          if (canDelete) {
            html += '<button type="button" class="btn btn-outline-danger" data-action="eliminar" data-id="' + id + '" title="Eliminar Perfil"><i class="fas fa-trash"></i></button>';
          }
          
          html += '</div>';
          return html;
        }
      }
    ];
  }

  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(`[${MOD}.page] TabulatorFactory no está disponible`);
      return null;
    }

    const columns = getColumns();
    table = w.TabulatorFactory.create(GRID_ID, API_URL, columns, {
      searchInputSelector: SEARCH_INPUT_ID
    });

    if (table) {
      const container = d.querySelector(GRID_ID);
      if (container) {
        container.addEventListener('click', function(e) {
          const btn = e.target.closest('button[data-action]');
          if (!btn) return;
          
          e.preventDefault();
          e.stopPropagation();
          
          const action = btn.getAttribute('data-action');
          const id = btn.getAttribute('data-id');  // [RULE 3] UUID string — prohibido parseInt() en UUIDs
          
          if (!id) {
            console.warn(`[${MOD}.page] ID no valido:`, id);
            return;
          }
          
          switch (action) {
            case 'ver':
              if (w.perfilModals && typeof w.perfilModals.showDetail === 'function') {
                w.perfilModals.showDetail(id);
              }
              break;
            case 'editar':
              if (w.perfilModals && typeof w.perfilModals.showEdit === 'function') {
                w.perfilModals.showEdit(id);
              }
              break;
            case 'asignar-rol':
              // Reutiliza el offcanvas de edicion: la seccion de rol aparece para ADMIN
              if (w.perfilModals && typeof w.perfilModals.showEdit === 'function') {
                w.perfilModals.showEdit(id);
              }
              break;
            case 'eliminar':
              if (w.perfilModals && typeof w.perfilModals.deletePerfil === 'function') {
                w.perfilModals.deletePerfil(id);
              }
              break;
            default:
              console.warn('[' + MOD + '.page] Accion no reconocida:', action);
          }
        });
      }
    }

    return table;
  }

  function verificarDependencias() {
    const dependencias = {
      TabulatorFactory: w.TabulatorFactory,
      perfilAPI: w.perfilAPI
    };
    
    const faltantes = Object.keys(dependencias).filter(key => !dependencias[key]);
    
    if (faltantes.length > 0) {
      console.warn(`[${MOD}.page] Dependencias faltantes:`, faltantes);
      return false;
    }
    
    return true;
  }

  async function loadRequestorContext() {
    // Carga permissions_context y available_actions del perfil del usuario actual
    // (via GET /me/) y los almacena en requestorContext para uso en la UI.
    // DSV: el endpoint /me/ ya aplica aislamiento por tenant activo.
    try {
      var url = (w.Sintel && w.Sintel.Perfil && w.Sintel.Perfil.API)
        ? w.Sintel.Perfil.API.me
        : (API_URL + 'me/');
      var headers = { 'Accept': 'application/json' };
      if (w.jwtAuth && typeof w.jwtAuth.getValidAccessToken === 'function') {
        try {
          var token = await w.jwtAuth.getValidAccessToken();
          if (token) headers['Authorization'] = 'Bearer ' + token;
        } catch (e) {}
      }
      var res = await fetch(url, { credentials: 'same-origin', headers: headers });
      if (!res.ok) return;
      var myProfile = await res.json();
      requestorContext = myProfile.permissions_context || {};
      requestorContext._actions = Array.isArray(myProfile.available_actions)
        ? myProfile.available_actions : [];
      // Almacenar user_id del solicitante para comparacion per-fila en getColumns()
      requestorContext.user_id = myProfile.user_id || null;
      // Exponer en el namespace global para consumo por otros modulos (settings panel, etc.)
      w.Sintel = w.Sintel || {};
      w.Sintel.Perfil = w.Sintel.Perfil || {};
      w.Sintel.Perfil.requestorContext = requestorContext;
    } catch (e) {
      console.warn('[' + MOD + '.page] loadRequestorContext:', e.message || e);
    }
  }

  async function inicializarModulo() {
    console.log('[' + MOD + '.page] Inicializando modulo...');
    if (!verificarDependencias()) {
      console.error('[' + MOD + '.page] Faltan dependencias criticas.');
      return;
    }

    // [AUTO-ADMIN] Cargar permissions_context antes de construir la tabla
    // para que getColumns() use requestorContext correcto desde el primer render.
    await loadRequestorContext();

    initTable();

    w.perfilPage = {
      table: table,
      refresh: function() {
        if (table) {
          table.replaceData();
        }
      },
      requestorContext: requestorContext
    };

    configurarEventos();
  }

  function configurarEventos() {
    // Controlar visibilidad de 'Nuevo Perfil' segun permissions_context.
    // NO clonar/reemplazar el boton: preserva atributos HTMX (hx-get, hx-target).
    var btnCrear = d.getElementById('btn-perfil-crear');
    if (btnCrear) {
      btnCrear.style.display = requestorContext.can_create_profiles ? '' : 'none';
    }

    var btnRefrescar = d.getElementById('btn-refrescar-perfil');
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', function() {
        if (table) {
          table.replaceData();
        }
      });
    }
  }

  // Funcion global de refresco para que perfil.modals.js pueda llamarla
  // sin depender de que perfilPage ya este inicializado
  w.refreshPerfilTable = function() {
    if (table && typeof table.replaceData === 'function') {
      table.replaceData();
    } else if (w.perfilPage && w.perfilPage.table) {
      w.perfilPage.table.replaceData();
    }
  };


  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce(CONTAINER_ID, function() {
      inicializarModulo().catch(err => console.error(err));
    });
  } else {
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      inicializarModulo().catch(err => console.error(err));
    }
    initFallback();
  }

})(window, document);
