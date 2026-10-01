/**
 * Feature: DataTable client-side de "Datos de Empresa" (2026-09-24)
 * Reemplaza el panel server-rendered django-tables2+HTMX (#empresa-panel,
 * apps/tenant/empresa/tables.py::EmpresaTable) por un DataTable 3.x sobre
 * el mismo endpoint JSON ya existente (GET /api/v1/empresas/). Completa la
 * migracion de las 3 grillas de "Mi empresa" (Sede/Area ya migradas, ver
 * sede_datatable.js/area_datatable.js) -- Empresa es singleton (0-1
 * registros por tenant, ver EmpresaViewSet), asi que el valor real de
 * DataTables aqui es consistencia visual + busqueda, no paginacion.
 * SOLO UI: no se toco backend/serializer.
 *
 * La logica de click en editar sigue viviendo en empresa_list.js
 * (delegacion sobre #empresa-panel .btn-edit-empresa) -- este archivo
 * genera el mismo markup que generaba EmpresaTable.render_acciones().
 * Namespace: window.EmpresaDataTableModule
 */
(function (w, d) {
  'use strict';

  var TABLE_SELECTOR = '#tabla-empresa';
  var API_LIST = '/api/v1/empresas/?page_size=200';
  var dt = null;

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function renderNit(row) {
    if (!row.nit) return '<span class="text-muted">—</span>';
    var full = row.dv ? row.nit + '-' + row.dv : row.nit;
    return '<code class="text-muted">' + escapeHtml(full) + '</code>';
  }

  function renderRazonSocial(v) {
    if (!v) return '<span class="text-muted">—</span>';
    return '<span class="fw-semibold text-dark">' + escapeHtml(v) + '</span>';
  }

  function renderIconText(icon, colorClass, v) {
    if (!v) return '<span class="text-muted">—</span>';
    return '<i class="bi ' + icon + ' ' + colorClass + ' me-1"></i><span class="small">' + escapeHtml(v) + '</span>';
  }

  function renderAcciones(row) {
    return '<div class="btn-group btn-group-sm" role="group">' +
      '<button type="button" class="btn btn-outline-primary btn-edit-empresa" data-id="' + row.id + '" title="Editar Empresa">' +
      '<i class="bi bi-pencil"></i></button>' +
      '</div>';
  }

  function initTable() {
    if (typeof DataTable === 'undefined') {
      console.error('[empresa.datatable] DataTables no esta cargado -- revisar assets_empresa_datatables.html');
      return;
    }
    dt = new DataTable(TABLE_SELECTOR, {
      serverSide: false,
      processing: true,
      pageLength: 20,
      order: [],
      columns: [
        { data: null, title: 'NIT', render: renderNit },
        { data: 'razon_social', title: 'Razón Social', render: renderRazonSocial },
        { data: 'direccion', title: 'Dirección', render: function (v) { return renderIconText('bi-geo-alt', 'text-primary', v); } },
        { data: 'telefono', title: 'Teléfono', render: function (v) { return renderIconText('bi-telephone', 'text-success', v); } },
        { data: 'email', title: 'Email', render: function (v) { return renderIconText('bi-envelope', 'text-info', v); } },
        { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
      ],
      layout: { topStart: null, topEnd: null, bottomStart: 'info', bottomEnd: 'paging' },
      language: {
        emptyTable: 'No hay empresa registrada',
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
          console.error('[empresa.datatable] Error cargando ' + API_LIST, xhr && xhr.status);
        },
      },
    });
  }

  function bindSearchInput() {
    var input = d.getElementById('search-empresa');
    if (!input) return;
    var timer = null;
    input.addEventListener('keyup', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (dt) dt.search(input.value || '').draw();
      }, 300);
    });
  }

  d.body.addEventListener('empresa-updated', function () {
    if (dt) dt.ajax.reload(null, false);
  });

  function init() {
    if (dt) { dt.columns.adjust(); return; }
    initTable();
    bindSearchInput();
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  w.EmpresaDataTableModule = { init: init, getTable: function () { return dt; } };

})(window, document);
