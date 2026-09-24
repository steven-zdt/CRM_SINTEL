/**
 * Feature: DataTable client-side de Sedes (2026-09-24)
 * Reemplaza el panel server-rendered django-tables2+HTMX (#sedes-panel,
 * apps/tenant/empresa/tables.py::SedeTable) por un DataTable 3.x sobre el
 * mismo endpoint JSON ya existente (GET /api/v1/empresas/sedes/).
 * SOLO UI: no se toco backend/serializer. Dataset pequeño (sedes por
 * tenant) -- pagina grande (page_size=200) + serverSide:false, DataTables
 * pagina/busca/ordena client-side.
 *
 * La logica de click en editar/eliminar sigue viviendo en sede_list.js
 * (delegacion sobre #sedes-panel .btn-edit-sede/.btn-delete-sede) -- este
 * archivo NO la duplica, solo genera el mismo markup que generaba
 * SedeTable.render_acciones() para que esa delegacion siga funcionando sin
 * cambios. w.refreshSedeTable() (definido en sede_list.js) sigue siendo la
 * funcion de refresco global -- aqui solo se escucha el evento
 * "sede-updated" que ya dispara.
 * Namespace: window.SedeDataTableModule
 */
(function (w, d) {
  'use strict';

  var TABLE_SELECTOR = '#tabla-sedes';
  var API_LIST = '/api/v1/empresas/sedes/?page_size=200';
  var dt = null;

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function renderIconText(icon, colorClass, value, fallback) {
    if (!value) return '<span class="text-muted">' + fallback + '</span>';
    return '<i class="bi ' + icon + ' ' + colorClass + ' me-1"></i><span>' + escapeHtml(value) + '</span>';
  }

  function renderAcciones(row) {
    var uuid = row.uuid;
    return '<div class="btn-group btn-group-sm" role="group">' +
      '<button type="button" class="btn btn-outline-primary btn-edit-sede" data-uuid="' + uuid + '" title="Editar Sede">' +
      '<i class="bi bi-pencil"></i></button>' +
      '<button type="button" class="btn btn-outline-danger btn-delete-sede" data-uuid="' + uuid + '" title="Eliminar Sede">' +
      '<i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  function initTable() {
    if (typeof DataTable === 'undefined') {
      console.error('[sede.datatable] DataTables no esta cargado -- revisar assets_empresa_datatables.html');
      return;
    }
    dt = new DataTable(TABLE_SELECTOR, {
      serverSide: false,
      processing: true,
      pageLength: 20,
      order: [[0, 'asc']],
      columns: [
        { data: 'nombre', title: 'Sede', render: function (v) { return renderIconText('bi-geo-alt-fill', 'text-primary', v, '—'); } },
        { data: 'direccion', title: 'Dirección', render: function (v) { return renderIconText('bi-house', 'text-secondary', v, '—'); } },
        { data: 'telefono', title: 'Teléfono', render: function (v) { return renderIconText('bi-telephone', 'text-success', v, '—'); } },
        { data: 'encargado_nombre', title: 'Encargado', render: function (v) { return renderIconText('bi-person', 'text-info', v, 'Sin asignar'); } },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
      ],
      layout: { topStart: null, topEnd: null, bottomStart: 'info', bottomEnd: 'paging' },
      language: {
        emptyTable: 'No hay sedes registradas',
        zeroRecords: 'No encontramos resultados con los filtros actuales',
        info: 'Mostrando _START_-_END_ de _TOTAL_',
        infoEmpty: 'Sin registros',
        infoFiltered: '(filtrado de _MAX_ totales)',
        paginate: { previous: '‹', next: '›' },
        processing: 'Cargando...',
      },
      ajax: {
        url: API_LIST,
        dataSrc: 'results',
        error: function (xhr) {
          console.error('[sede.datatable] Error cargando ' + API_LIST, xhr && xhr.status);
        },
      },
    });
  }

  function bindSearchInput() {
    var input = d.getElementById('search-sede');
    if (!input) return;
    var timer = null;
    input.addEventListener('keyup', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (dt) dt.search(input.value || '').draw();
      }, 300);
    });
  }

  d.body.addEventListener('sede-updated', function () {
    if (dt) dt.ajax.reload(null, false);
  });

  function getTable() { return dt; }

  // Init perezoso -- NO se auto-arranca al cargar el script: la pestaña
  // "Sedes" empieza oculta (Bootstrap tab-pane sin "show active"), y
  // DataTables calcula anchos de columna mal si se inicializa con el
  // contenedor en display:none (hallazgo real ya documentado en el
  // comentario "Redraw Tabulator" que este archivo reemplaza, ver
  // empresa_list.html). empresa_list.html llama a init() en el primer
  // shown.bs.tab de "Sedes"; llamadas posteriores solo reajustan anchos.
  function init() {
    if (dt) { getTable().columns.adjust(); return; }
    initTable();
    bindSearchInput();
  }

  w.SedeDataTableModule = { init: init, getTable: getTable };

})(window, document);
