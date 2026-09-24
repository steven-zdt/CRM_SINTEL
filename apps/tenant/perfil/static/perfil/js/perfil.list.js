// apps/tenant/perfil/static/perfil/js/perfil.list.js
/**
 * perfil.list.js - Migracion UI de la tabla de Perfiles a DataTables 3.x
 * (2026-09-24, ver [[feedback-verificar-markup-antes-de-fix-compartido]] en
 * memoria -- este modulo reemplaza el panel server-rendered django-tables2
 * (apps/tenant/perfil/tables.py::PerfilTable) por un DataTable client-side
 * sobre el mismo endpoint JSON que ya alimentaba a TabulatorFactory
 * (GET /api/v1/perfil/perfiles/ -- el propio docstring del ViewSet dice
 * "Retorna respuesta paginada compatible con TabulatorFactory").
 *
 * SOLO UI: no se toco backend/serializer. Dataset pequeño (perfiles por
 * tenant, tipicamente decenas) -- se pide una pagina grande (page_size=200,
 * el maximo que permite StandardResultsSetPagination) y DataTables pagina/
 * busca/ordena client-side (serverSide:false), a diferencia del patron
 * dt()+DataTablesFactory usado en las 12 apps grandes (Ventas, Facturas,
 * etc.) que sí necesitan paginacion real en servidor.
 *
 * [SEG-5] CRITICO -- replicado aqui, no relajado: PerfilTable.render_acciones
 * (server-side, ahora reemplazado en UI) nunca mostraba el boton "eliminar"
 * sobre la propia fila del usuario autenticado, aunque su rol lo permitiera.
 * El JSON de cada fila NO trae ese calculo (available_actions es por ROL del
 * solicitante, no por fila) -- se compara row.user_id contra el user_id del
 * solicitante (obtenido de GET .../me/, mismo endpoint/patron que ya usa
 * loadRequestorContext() en perfil.page.js) antes de decidir mostrar el
 * boton eliminar en cada fila.
 *
 * Los data-action/data-id de los botones son IDENTICOS al markup que
 * generaba tables.py::render_acciones -- la delegacion de clicks ya
 * existente en perfil.page.js (#perfiles-panel button[data-action]) sigue
 * funcionando sin cambios. data-id usa el "id" (PK entero) del JSON -- no
 * hay "uuid" en TenantProfileSerializer.fields, pero
 * PerfilBusinessService.get_profile() acepta ambos indistintamente
 * (ver apps/tenant/perfil/services/business_service.py::get_profile).
 */
(function (w, d) {
  'use strict';

  var TABLE_SELECTOR = '#tabla-perfiles';
  var API_LIST = '/api/v1/perfil/perfiles/?page_size=200';
  var API_ME = '/api/v1/perfil/perfiles/me/';

  var dt = null;
  var currentUserId = null;

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  async function authHeaders() {
    var headers = { Accept: 'application/json' };
    if (w.jwtAuth && typeof w.jwtAuth.getValidAccessToken === 'function') {
      try {
        var token = await w.jwtAuth.getValidAccessToken();
        if (token) headers.Authorization = 'Bearer ' + token;
      } catch (e) { /* sesion via cookie, sigue funcionando */ }
    }
    return headers;
  }

  async function loadCurrentUserId() {
    try {
      var res = await fetch(API_ME, { credentials: 'same-origin', headers: await authHeaders() });
      if (!res.ok) return;
      var me = await res.json();
      currentUserId = me.user_id || null;
    } catch (e) {
      console.warn('[perfil.list] no se pudo resolver el usuario actual (guard SEG-5 usara solo el rol):', e.message || e);
    }
  }

  var ROL_BADGE = { ADMIN: 'bg-danger', OPERADOR: 'bg-primary', VISOR: 'bg-secondary' };

  function renderUsuario(row) {
    var nombre = escapeHtml(row.user_full_name || row.user_email || '—');
    var email = row.user_email
      ? '<br><small class="text-muted">' + escapeHtml(row.user_email) + '</small>'
      : '';
    return '<div><strong>' + nombre + '</strong>' + email + '</div>';
  }

  function renderTexto(v) {
    return v ? escapeHtml(v) : '<span class="text-muted">-</span>';
  }

  function renderRol(v) {
    if (!v) return '<span class="text-muted">-</span>';
    var cls = ROL_BADGE[v] || 'bg-secondary';
    return '<span class="badge ' + cls + '">' + escapeHtml(v) + '</span>';
  }

  function renderAvatar(row) {
    if (row.avatar_url) {
      return '<img src="' + escapeHtml(row.avatar_url) + '" alt="Avatar" class="rounded-circle" ' +
        'style="width:40px;height:40px;object-fit:cover;">';
    }
    return '<i class="fas fa-user-circle text-muted" style="font-size:40px;"></i>';
  }

  function renderAcciones(row) {
    var actions = row.available_actions || [];
    var isSelf = currentUserId != null && row.user_id === currentUserId;
    var canEdit = actions.indexOf('edit') !== -1;
    var canAssignRol = actions.indexOf('assign_rol') !== -1;
    var canDelete = actions.indexOf('delete') !== -1 && !isSelf;
    var id = row.id;

    var btns = '<button type="button" class="btn btn-outline-primary" data-action="ver" data-id="' + id +
      '" title="Ver Perfil"><i class="fas fa-eye"></i></button>';
    if (canEdit) {
      btns += '<button type="button" class="btn btn-outline-success" data-action="editar" data-id="' + id +
        '" title="Editar Perfil"><i class="fas fa-edit"></i></button>';
    }
    if (canAssignRol) {
      btns += '<button type="button" class="btn btn-outline-warning" data-action="asignar-rol" data-id="' + id +
        '" title="Asignar Rol"><i class="fas fa-user-shield"></i></button>';
    }
    if (canDelete) {
      btns += '<button type="button" class="btn btn-outline-danger" data-action="eliminar" data-id="' + id +
        '" title="Eliminar Perfil"><i class="fas fa-trash"></i></button>';
    }
    return '<div class="btn-group btn-group-sm" role="group">' + btns + '</div>';
  }

  async function initTable() {
    if (typeof DataTable === 'undefined') {
      console.error('[perfil.list] DataTables no esta cargado -- revisar assets_perfil_datatables.html');
      return;
    }
    await loadCurrentUserId();

    var headers = await authHeaders();

    dt = new DataTable(TABLE_SELECTOR, {
      serverSide: false,
      processing: true,
      pageLength: 20,
      order: [[0, 'asc']],
      columns: [
        { data: null, title: 'Usuario', render: renderUsuario },
        { data: 'cargo', title: 'Cargo', render: renderTexto },
        { data: 'departamento_nombre', title: 'Departamento', render: renderTexto },
        { data: 'telefono_corporativo', title: 'Teléfono', render: renderTexto },
        { data: 'rol', title: 'Rol', render: renderRol },
        { data: null, title: '', orderable: false, searchable: false, render: renderAvatar },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
      ],
      layout: { topStart: null, topEnd: null, bottomStart: 'info', bottomEnd: 'paging' },
      language: {
        emptyTable: 'No hay perfiles registrados',
        zeroRecords: 'No encontramos resultados con los filtros actuales',
        info: 'Mostrando _START_-_END_ de _TOTAL_',
        infoEmpty: 'Sin registros',
        infoFiltered: '(filtrado de _MAX_ totales)',
        paginate: { previous: '‹', next: '›' },
        processing: 'Cargando...',
      },
      ajax: {
        url: API_LIST,
        headers: headers,
        dataSrc: 'results',
        error: function (xhr) {
          console.error('[perfil.list] Error cargando ' + API_LIST, xhr && xhr.status);
        },
      },
    });
  }

  // El buscador propio de este modulo (#search-perfil, ya en list.html) --
  // reemplaza el hx-get/hx-trigger anterior, ahora busca client-side.
  function bindSearchInput() {
    var input = d.getElementById('search-perfil');
    if (!input) return;
    var timer = null;
    input.addEventListener('keyup', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (dt) dt.search(input.value || '').draw();
      }, 300);
    });
  }

  // w.refreshPerfilTable (definido en perfil.page.js) dispara este evento
  // tras crear/editar/eliminar (via perfil.modals.js) -- antes lo escuchaba
  // el hx-trigger de #perfiles-panel, ahora lo escucha este modulo.
  d.body.addEventListener('perfil-updated', function () {
    if (dt) dt.ajax.reload(null, false);
  });

  if (w.DOMUtils && w.DOMUtils.onVisibleOnce) {
    w.DOMUtils.onVisibleOnce('#tab-perfil', function () {
      initTable().then(bindSearchInput);
    });
  } else {
    function initFallback() {
      if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initFallback);
        return;
      }
      initTable().then(bindSearchInput);
    }
    initFallback();
  }

})(window, document);
