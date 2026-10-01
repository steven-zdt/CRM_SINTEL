// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * cuenta_list.js - Controlador de Lista de Cuentas Bancarias
 * Namespace: window.Sintel.Bancos.CuentaList
 *
 * DataTables 3.x (mismo patron ya validado en Ventas -- gate visual
 * cerrado, ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md): la
 * tabla (#tabla-cuentas-bancarias) se puebla via ajax contra
 * POST /api/v1/bancos/cuentas/dt/ usando Sintel.Core.DataTablesFactory.
 * django-tables2/CuentaBancariaTable retirados.
 *
 * Las acciones de fila (editar/activar/desactivar/eliminar) las maneja
 * bancos.main.js via delegacion global sobre document.body -- no se
 * tocan aqui.
 *
 * init()/redraw() ahora hacen trabajo real (a diferencia de la version
 * HTMX anterior, no-op): bancos.main.js los invoca en varios momentos
 * (activacion de sub-tab, activacion del tab del workspace) porque
 * #tab-pane-cuentas puede estar oculto (display:none) cuando el DataTable
 * se crea -- init() es idempotente (guardia `inicializada`), redraw()
 * solo recalcula anchos de columna (dt.columns().adjust()), nunca
 * reconsulta ni reconstruye la tabla.
 */
(function (w, d) {
  'use strict';

  var TABLA_SELECTOR = '#tabla-cuentas-bancarias';
  var DT_URL = '/api/v1/bancos/cuentas/dt/';
  var inicializada = false;

  var BANCOS_MAP = {
    BANCOLOMBIA: 'Bancolombia',
    BANCO_BOGOTA: 'Banco de Bogotá',
    DAVIVIENDA: 'Davivienda',
    BBVA: 'BBVA',
    OCCIDENTE: 'Banco de Occidente',
    POPULAR: 'Banco Popular',
    AV_VILLAS: 'Banco AV Villas',
  };

  var TIPOS_CUENTA_MAP = {
    AHORROS: 'Ahorros',
    CORRIENTE: 'Corriente',
  };

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderBanco(value) {
    return escapeHtml(BANCOS_MAP[value] || value || '—');
  }

  function renderTipo(value) {
    return escapeHtml(TIPOS_CUENTA_MAP[value] || value || '—');
  }

  function renderEstado(value) {
    return value
      ? '<span class="badge bg-success">Activa</span>'
      : '<span class="badge bg-secondary">Inactiva</span>';
  }

  function renderAcciones(data, type, row) {
    var editBtn = '<button type="button" class="btn btn-outline-primary btn-edit-cuenta" ' +
        'data-id="' + escapeHtml(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>';
    var toggleBtn = row.activo
        ? '<button type="button" class="btn btn-outline-secondary btn-desactivar-cuenta" ' +
          'data-id="' + escapeHtml(row.uuid) + '" title="Desactivar"><i class="bi bi-eye-slash"></i></button>'
        : '<button type="button" class="btn btn-outline-success btn-activar-cuenta" ' +
          'data-id="' + escapeHtml(row.uuid) + '" title="Activar"><i class="bi bi-eye"></i></button>';
    // B-4: eliminar fisico solo tiene sentido si ya esta inactiva
    // (crud_service.eliminar_cuenta lo rechaza si activo=True).
    var deleteBtn = row.activo ? '' : '<button type="button" class="btn btn-outline-danger btn-delete-cuenta" ' +
        'data-id="' + escapeHtml(row.uuid) + '" title="Eliminar"><i class="bi bi-trash"></i></button>';
    return '<div class="btn-group btn-group-sm" role="group">' + editBtn + toggleBtn + deleteBtn + '</div>';
  }

  var COLUMNS = [
    { data: 'nombre', title: 'Nombre de la Cuenta' },
    { data: 'banco', title: 'Banco', render: renderBanco },
    { data: 'tipo', title: 'Tipo', orderable: false, render: renderTipo },
    { data: 'numero', title: 'Número', orderable: false },
    { data: 'activo', title: 'Estado', orderable: false, render: renderEstado },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  // ── Filtros por columna (misma limitacion que Ventas: no pueden vivir en
  // el <thead> estatico, DataTables lo reescribe al iniciar) ─────────────

  function filaFiltrosHtml() {
    var bancoOptions = '<option value="">Todos</option>';
    Object.keys(BANCOS_MAP).forEach(function (key) {
      bancoOptions += '<option value="' + key + '">' + escapeHtml(BANCOS_MAP[key]) + '</option>';
    });
    var tipoOptions = '<option value="">Todos</option>';
    Object.keys(TIPOS_CUENTA_MAP).forEach(function (key) {
      tipoOptions += '<option value="' + key + '">' + escapeHtml(TIPOS_CUENTA_MAP[key]) + '</option>';
    });
    return '<tr id="fila-filtros-cuentas" class="table-light">' +
        '<th><input type="text" class="form-control form-control-sm" id="filtro-cuenta-nombre" placeholder="Filtrar nombre..."></th>' +
        '<th><select class="form-select form-select-sm" id="filtro-cuenta-banco">' + bancoOptions + '</select></th>' +
        '<th><select class="form-select form-select-sm" id="filtro-cuenta-tipo">' + tipoOptions + '</select></th>' +
        '<th><input type="text" class="form-control form-control-sm" id="filtro-cuenta-numero" placeholder="Filtrar número..."></th>' +
        '<th><select class="form-select form-select-sm" id="filtro-cuenta-estado">' +
        '<option value="">Todas</option><option value="true">Activa</option><option value="false">Inactiva</option>' +
        '</select></th>' +
        '<th></th>' +
        '</tr>';
  }

  function insertarFilaFiltros() {
    var thead = d.querySelector(TABLA_SELECTOR + ' thead');
    if (!thead || d.getElementById('filtro-cuenta-nombre')) return;
    thead.insertAdjacentHTML('beforeend', filaFiltrosHtml());
  }

  function debounce(fn, delay) {
    var timer = null;
    return function () {
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(null, args); }, delay);
    };
  }

  function bindFiltrosColumna() {
    var Factory = w.Sintel.Core.DataTablesFactory;

    var inputNombre = d.getElementById('filtro-cuenta-nombre');
    if (inputNombre) {
      inputNombre.addEventListener('keyup', debounce(function () {
        Factory.columnSearch(TABLA_SELECTOR, 0, inputNombre.value);
      }, 400));
    }

    var selectBanco = d.getElementById('filtro-cuenta-banco');
    if (selectBanco) {
      selectBanco.addEventListener('change', function () {
        Factory.columnSearch(TABLA_SELECTOR, 1, selectBanco.value);
      });
    }

    var selectTipo = d.getElementById('filtro-cuenta-tipo');
    if (selectTipo) {
      selectTipo.addEventListener('change', function () {
        Factory.columnSearch(TABLA_SELECTOR, 2, selectTipo.value);
      });
    }

    var inputNumero = d.getElementById('filtro-cuenta-numero');
    if (inputNumero) {
      inputNumero.addEventListener('keyup', debounce(function () {
        Factory.columnSearch(TABLA_SELECTOR, 3, inputNumero.value);
      }, 400));
    }

    var selectEstado = d.getElementById('filtro-cuenta-estado');
    if (selectEstado) {
      selectEstado.addEventListener('change', function () {
        Factory.columnSearch(TABLA_SELECTOR, 4, selectEstado.value);
      });
    }
  }

  // ── Init / refresh / redraw ─────────────────────────────────────────

  function init() {
    if (inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 20,
      order: [[0, 'asc']],
    });
    insertarFilaFiltros();
    bindFiltrosColumna();
    inicializada = true;
  }

  function refresh() {
    w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
  }

  function redraw() {
    var dt = w.Sintel.Core.DataTablesFactory.get(TABLA_SELECTOR);
    if (dt) dt.columns.adjust();
  }

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.CuentaList = {
    init: init,
    refresh: refresh,
    redraw: redraw,
  };

})(window, document);
