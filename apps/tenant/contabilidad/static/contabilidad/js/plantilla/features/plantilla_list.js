/**
 * plantilla_list.js - Tabla Tabulator para PlantillaContable v3.16.2
 * Feature-Sliced Design: renderizado de grid + event delegation.
 * Dependencias: TabulatorFactory, DOMUtils, PlantillaAPI
 */
(function (w, d) {
  'use strict';

  const MOD = '[plantilla.list]';
  const TABLE_SEL = '#grid-plantillas';
  const SEARCH_SEL = '#search-plantilla';
  const FILTER_TIPO_SEL = '#filter-tipo-plantilla';
  const FILTER_ACTIVO_SEL = '#filter-activo-plantilla';
  const API_URL = '/api/v1/contabilidad/plantillas-contables/';
  const TAB_ID = '#subtab-plantillas';
  let table = null;

  // ------------------------------------------------------------------ helpers
  function badgeTipo(val) {
    const map = {
      VENTA:  ['success',  'Venta'],
      COMPRA: ['primary',  'Compra'],
      GASTO:  ['warning',  'Gasto'],
      NOMINA: ['info',     'Nomina'],
    };
    const [cls, label] = map[val] || ['secondary', val || 'Resolver'];
    return '<span class="badge bg-' + cls + '">' + label + '</span>';
  }

  function badgeModo(val) {
    return val === 'MOTOR'
      ? '<span class="badge bg-dark">Motor</span>'
      : '<span class="badge bg-light text-dark border">Resolver</span>';
  }

  function badgeActivo(val) {
    return val
      ? '<span class="badge bg-success">Activa</span>'
      : '<span class="badge bg-danger">Inactiva</span>';
  }

  // ---------------------------------------------------------------- columns
  function getColumns() {
    return [
      {
        title: 'Nombre',
        field: 'nombre',
        widthGrow: 2,
        formatter: function (cell) {
          return cell.getValue() || '<span class="text-muted fst-italic">Sin nombre</span>';
        },
      },
      {
        title: 'Tipo',
        field: 'tipo_transaccion',
        width: 120,
        formatter: function (cell) { return badgeTipo(cell.getValue()); },
      },
      {
        title: 'Modo',
        field: 'modo',
        width: 100,
        formatter: function (cell) { return badgeModo(cell.getValue()); },
      },
      {
        title: 'Lineas',
        field: 'lineas_count',
        hozAlign: 'center',
        width: 80,
        formatter: function (cell) {
          const n = cell.getValue() || 0;
          return '<span class="badge bg-secondary">' + n + '</span>';
        },
      },
      {
        title: 'Estado',
        field: 'activo',
        width: 100,
        formatter: function (cell) { return badgeActivo(cell.getValue()); },
      },
      {
        title: 'Creada',
        field: 'created_at',
        width: 130,
        formatter: function (cell) {
          const v = cell.getValue();
          if (!v) return '-';
          try { return new Date(v).toLocaleDateString('es-CO'); } catch { return v; }
        },
      },
      {
        title: 'Acciones',
        headerSort: false,
        hozAlign: 'right',
        width: 160,
        formatter: function (cell) {
          const row = cell.getRow().getData();
          const uuid = row.uuid || '';
          if (!uuid) return '-';
          return [
            '<div class="btn-group btn-group-sm">',
            '  <button class="btn btn-outline-secondary btn-ver-plantilla" data-uuid="' + uuid + '" title="Ver detalle"><i class="bi bi-eye"></i></button>',
            '  <button class="btn btn-outline-primary btn-editar-plantilla" data-uuid="' + uuid + '" title="Editar"><i class="bi bi-pencil"></i></button>',
            '  <button class="btn btn-outline-danger btn-eliminar-plantilla" data-uuid="' + uuid + '" title="Eliminar"><i class="bi bi-trash"></i></button>',
            '</div>',
          ].join('');
        },
      },
    ];
  }

  // -------------------------------------------------------------- init table
  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(MOD, 'TabulatorFactory no disponible');
      return null;
    }
    const el = d.querySelector(TABLE_SEL);
    if (!el) { console.error(MOD, TABLE_SEL + ' no encontrado'); return null; }

    table = w.TabulatorFactory.create(TABLE_SEL, API_URL, getColumns(), {
      searchInputSelector: SEARCH_SEL,
      paginationSize: 15,
      ajaxParams: function () {
        const tipo   = d.querySelector(FILTER_TIPO_SEL)?.value   || '';
        const activo = d.querySelector(FILTER_ACTIVO_SEL)?.value || '';
        const p = {};
        if (tipo)   p.tipo_transaccion = tipo;
        if (activo !== '') p.activo = activo;
        return p;
      },
    });
    return table;
  }

  // --------------------------------------------------------- event delegation
  function showOffcanvas(id) {
    const el = d.getElementById(id);
    if (!el) return;
    if (w.UIManager?.handleOffcanvas) {
      w.UIManager.handleOffcanvas(el, 'show');
    } else {
      const p = w.bootstrap?.Offcanvas?.getInstance(el);
      if (p) p.dispose();
      d.querySelectorAll('.offcanvas-backdrop').forEach(function (b) { b.remove(); });
      new w.bootstrap.Offcanvas(el).show();
    }
  }

  function htmxLoad(url, target, offcanvasId) {
    if (typeof htmx === 'undefined') return;
    htmx.ajax('GET', url, { target: target, swap: 'innerHTML' }).then(function () {
      showOffcanvas(offcanvasId);
    });
  }

  function attachListeners() {
    // Ver detalle
    d.addEventListener('click', function (ev) {
      const btn = ev.target.closest('.btn-ver-plantilla');
      if (!btn) return;
      ev.preventDefault();
      htmxLoad(
        API_URL + btn.dataset.uuid + '/render-offcanvas/detalle/',
        '#offcanvas-container-plantilla',
        'offcanvas-plantilla-detalle'
      );
    });

    // Editar
    d.addEventListener('click', function (ev) {
      const btn = ev.target.closest('.btn-editar-plantilla');
      if (!btn) return;
      ev.preventDefault();
      htmxLoad(
        API_URL + btn.dataset.uuid + '/render-offcanvas/editar/',
        '#offcanvas-container-plantilla',
        'offcanvas-plantilla-editar'
      );
    });

    // Eliminar
    d.addEventListener('click', function (ev) {
      const btn = ev.target.closest('.btn-eliminar-plantilla');
      if (!btn) return;
      ev.preventDefault();
      if (!confirm('Eliminar esta plantilla contable? Se eliminaran todas sus lineas.')) return;
      if (w.PlantillaEditor?.delete) {
        w.PlantillaEditor.delete(btn.dataset.uuid);
      }
    });

    // Filtros
    [FILTER_TIPO_SEL, FILTER_ACTIVO_SEL].forEach(function (sel) {
      const el = d.querySelector(sel);
      if (el) el.addEventListener('change', function () { table && table.replaceData(); });
    });

    // Refrescar
    const btnRef = d.querySelector('#btn-refrescar-plantilla');
    if (btnRef) btnRef.addEventListener('click', function () { table && table.replaceData(); });
  }

  // -------------------------------------------------------------------- init
  function init() {
    if (!w.TabulatorFactory || !w.DOMUtils?.onVisibleOnce) {
      console.error(MOD, 'Dependencias no disponibles');
      return;
    }
    w.DOMUtils.onVisibleOnce(TAB_ID, function () {
      table = initTable();
      attachListeners();
    });
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  w.PlantillaList = Object.freeze({
    init: init,
    reload: function () { table ? table.replaceData() : init(); },
    getTable: function () { return table; },
  });
})(window, document);
