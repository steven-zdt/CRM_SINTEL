/**
 * Feature: DataTable client-side de Áreas (2026-09-24)
 * Reemplaza el panel server-rendered django-tables2+HTMX (#areas-panel,
 * apps/tenant/empresa/tables.py::AreaTable) por un DataTable 3.x sobre el
 * mismo endpoint JSON ya existente (GET /api/v1/empresas/areas/).
 * SOLO UI: no se toco backend/serializer. Ver sede_datatable.js (mismo
 * patron: dataset pequeño, serverSide:false, page_size=200).
 *
 * Columna "Responsable" deliberadamente omitida -- AreaTable ya documenta
 * que ese campo no existe en el modelo ni lo calcula ningun serializer
 * (columna huerfana del Tabulator original, "Sin asignar" siempre).
 *
 * La logica de click en editar/eliminar sigue viviendo en area_list.js
 * (delegacion sobre #areas-panel .btn-edit-area/.btn-delete-area) -- este
 * archivo genera el mismo markup que generaba AreaTable.render_acciones().
 * Namespace: window.AreaDataTableModule
 */
(function (w, d) {
  'use strict';

  var TABLE_SELECTOR = '#tabla-areas';
  var API_LIST = '/api/v1/empresas/areas/?page_size=200';
  var dt = null;

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function renderNombre(v) {
    if (!v) return '<span class="text-muted">—</span>';
    return '<i class="bi bi-diagram-3 text-success me-2"></i><span class="fw-semibold">' + escapeHtml(v) + '</span>';
  }

  function renderCodigo(v) {
    if (!v) return '<span class="text-muted">—</span>';
    return '<code class="bg-light px-2 py-1 rounded small">' + escapeHtml(v) + '</code>';
  }

  function renderSede(row) {
    if (!row.sede_nombre) return '<span class="text-muted">—</span>';
    return '<i class="bi bi-geo-alt text-primary me-1"></i><span class="small">' + escapeHtml(row.sede_nombre) + '</span>';
  }

  function renderAcciones(row) {
    var uuid = row.uuid;
    return '<div class="btn-group btn-group-sm" role="group">' +
      '<button type="button" class="btn btn-outline-primary btn-edit-area" data-uuid="' + uuid + '" title="Editar Área">' +
      '<i class="bi bi-pencil"></i></button>' +
      '<button type="button" class="btn btn-outline-danger btn-delete-area" data-uuid="' + uuid + '" title="Eliminar Área">' +
      '<i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  function initTable() {
    if (typeof DataTable === 'undefined') {
      console.error('[area.datatable] DataTables no esta cargado -- revisar assets_empresa_datatables.html');
      return;
    }
    dt = new DataTable(TABLE_SELECTOR, {
      serverSide: false,
      processing: true,
      pageLength: 20,
      order: [[0, 'asc']],
      columns: [
        { data: 'nombre', title: 'Área / Departamento', render: renderNombre },
        { data: 'codigo_funcionamiento', title: 'Código', render: renderCodigo },
        { data: null, title: 'Sede', render: renderSede },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
      ],
      layout: { topStart: null, topEnd: null, bottomStart: 'info', bottomEnd: 'paging' },
      language: {
        emptyTable: 'No hay áreas registradas',
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
          console.error('[area.datatable] Error cargando ' + API_LIST, xhr && xhr.status);
        },
      },
    });
  }

  function bindSearchInput() {
    var input = d.getElementById('search-area');
    if (!input) return;
    var timer = null;
    input.addEventListener('keyup', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (dt) dt.search(input.value || '').draw();
      }, 300);
    });
  }

  d.body.addEventListener('area-updated', function () {
    if (dt) dt.ajax.reload(null, false);
  });

  function getTable() { return dt; }

  // Init perezoso -- ver el comentario equivalente en sede_datatable.js
  // (misma razon: la pestaña "Áreas" empieza oculta).
  function init() {
    if (dt) { getTable().columns.adjust(); return; }
    initTable();
    bindSearchInput();
  }

  w.AreaDataTableModule = { init: init, getTable: getTable };

})(window, document);
