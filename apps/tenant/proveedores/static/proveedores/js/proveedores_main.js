// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * proveedores_main.js - Orquestador del Módulo Proveedores
 *
 * La grilla "Directorio de Proveedores" es DataTables 3.x (#tabla-proveedores,
 * mismo patron ya validado en Ventas/Bancos/Facturas/Clientes -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via ajax
 * contra POST /api/v1/proveedores/dt/. ProveedorTable/ProveedorTableView
 * (django-tables2) retirados. Cuentas por Pagar (grilla unificada, fuente
 * Python list no QuerySet) sigue en django-tables2/HTMX -- no migrada en
 * esta pasada.
 *
 * Este archivo maneja: init de la tabla, delegacion de eventos
 * (editar/eliminar/ver/representantes, click-en-fila abre detalle via
 * data-uuid en <tr> -- ver createdRow abajo) y los chips de filtro rapido.
 */
(function (w, d) {
  'use strict';

  const MOD = '[proveedores:main]';
  let listEventsBound = false;

  var TABLA_PROV_SELECTOR = '#tabla-proveedores';
  var TABLA_PROV_URL = '/api/v1/proveedores/dt/';
  var _proveedoresTablaInicializada = false;

  var TIPO_PERSONA_MAP_PROV = { JURIDICA: ['bg-info', 'Jurídica'], NATURAL: ['bg-secondary', 'Natural'] };

  function fmtCopProv(value) {
    var n = parseFloat(value || 0);
    if (isNaN(n)) return '$ 0';
    return '$ ' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }

  function escapeHtmlProv(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderProveedorNombre(value) {
    return '<span class="fw-semibold">' + escapeHtmlProv(value || '—') + '</span>';
  }

  function renderProveedorTipo(value) {
    var cfg = TIPO_PERSONA_MAP_PROV[value] || ['bg-light text-dark', value || '—'];
    return '<span class="badge ' + cfg[0] + '">' + escapeHtmlProv(cfg[1]) + '</span>';
  }

  function renderProveedorDocumento(data, type, row) {
    if (!row.numero_documento) return '<span class="text-muted small">—</span>';
    return '<span class="small">' + escapeHtmlProv(row.nit || row.numero_documento) + '</span>';
  }

  function renderProveedorRegimen(data, type, row) {
    var label = row.regimen_tributario_display || '—';
    var ret = row.es_retenedor
      ? '<span class="badge bg-warning ms-1" title="Agente Retenedor"><i class="bi bi-shield-check"></i></span>' : '';
    return '<span class="small">' + escapeHtmlProv(label) + '</span>' + ret;
  }

  function renderProveedorContacto(data, type, row) {
    var parts = [];
    if (row.email_contacto) parts.push('<div class="text-truncate small"><i class="bi bi-envelope me-1 text-muted"></i>' + escapeHtmlProv(row.email_contacto) + '</div>');
    if (row.telefono_contacto) parts.push('<div class="small"><i class="bi bi-telephone me-1 text-muted"></i>' + escapeHtmlProv(row.telefono_contacto) + '</div>');
    if (row.ciudad) parts.push('<div class="small text-muted"><i class="bi bi-geo-alt me-1"></i>' + escapeHtmlProv(row.ciudad) + '</div>');
    return parts.length ? '<div class="lh-sm">' + parts.join('') + '</div>' : '<span class="text-muted small">—</span>';
  }

  function renderProveedorEstado(value) {
    return value ? '<span class="badge bg-success">Activo</span>' : '<span class="badge bg-secondary">Inactivo</span>';
  }

  function renderProveedorCartera(data, type, row) {
    var c = row.cuentas_pagar_resumen || { pendiente_count: 0, pagada_count: 0, total_count: 0 };
    if (!c.total_count) return '<span class="text-muted small">Sin facturas</span>';
    if (c.pendiente_count > 0) {
      return '<span class="badge bg-warning text-dark" title="Facturas pendientes de pago">' +
        '<i class="bi bi-clock me-1"></i>' + c.pendiente_count + ' pend.</span> ' +
        '<span class="small text-warning fw-semibold">' + fmtCopProv(c.pendiente_monto) + '</span>';
    }
    if (c.pagada_count > 0) {
      return '<span class="badge bg-success" title="Todas las facturas pagadas">' +
        '<i class="bi bi-check-circle me-1"></i>' + c.pagada_count + ' pagadas</span>';
    }
    return '<span class="text-muted small">—</span>';
  }

  function renderProveedorAcciones(data, type, row) {
    var isActive = row.activo === true;
    var deleteDisabled = isActive ? 'disabled' : '';
    var deleteClass = isActive ? 'opacity-50' : '';
    return '<div class="btn-group btn-group-sm">' +
      '<button type="button" class="btn btn-outline-info btn-view-proveedor" data-id="' + escapeHtmlProv(row.uuid) + '" title="Ver"><i class="bi bi-eye"></i></button>' +
      '<button type="button" class="btn btn-outline-primary btn-edit-proveedor" data-id="' + escapeHtmlProv(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
      '<button type="button" class="btn btn-outline-secondary btn-representantes-proveedor" data-id="' + escapeHtmlProv(row.uuid) + '" title="Representantes"><i class="bi bi-person-check"></i></button>' +
      '<button type="button" class="btn btn-outline-danger btn-delete-proveedor ' + deleteClass + '" data-id="' + escapeHtmlProv(row.uuid) + '" ' + deleteDisabled + ' title="Eliminar"><i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  var PROVEEDORES_COLUMNS = [
    { data: 'razon_social', title: 'Proveedor', render: renderProveedorNombre },
    { data: 'tipo_persona', title: 'Tipo', render: renderProveedorTipo },
    { data: null, title: 'Documento', orderable: false, render: renderProveedorDocumento },
    { data: null, title: 'Régimen', render: renderProveedorRegimen },
    { data: null, title: 'Contacto', orderable: false, searchable: false, render: renderProveedorContacto },
    { data: 'activo', title: 'Estado', render: renderProveedorEstado },
    { data: 'cuentas_pagar_resumen', title: 'Cartera', orderable: false, searchable: false, render: renderProveedorCartera },
    { data: null, title: '', orderable: false, searchable: false, render: renderProveedorAcciones },
  ];

  function bindFiltrosTipoProveedor() {
    var contenedor = d.getElementById('filtros-tipo-proveedores');
    if (!contenedor) return;
    contenedor.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-filtro-prov]');
      if (!btn) return;
      var Factory = w.Sintel.Core.DataTablesFactory;
      var filtro = btn.getAttribute('data-filtro-prov');
      // Columna 1 = tipo_persona, columna 3 = es_retenedor, columna 5 = activo
      // (ver ProveedorViewSet.dt() -- column_filters). "Todos" limpia las 3.
      Factory.columnSearch(TABLA_PROV_SELECTOR, 1, filtro === 'JURIDICA' ? 'JURIDICA' : filtro === 'NATURAL' ? 'NATURAL' : '');
      Factory.columnSearch(TABLA_PROV_SELECTOR, 3, filtro === 'RETENEDOR' ? 'true' : '');
      Factory.columnSearch(TABLA_PROV_SELECTOR, 5, filtro === 'ACTIVO' ? 'true' : filtro === 'INACTIVO' ? 'false' : '');
    });
  }

  function initProveedoresTabla() {
    if (_proveedoresTablaInicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_PROV_SELECTOR, TABLA_PROV_URL, PROVEEDORES_COLUMNS, {
      pageLength: 20,
      order: [[0, 'asc']],
      // data-uuid en <tr> replica el rowClick de Tabulator (ver delegacion
      // de "click en fila" mas abajo).
      createdRow: function (tr, rowData) {
        if (rowData && rowData.uuid) tr.setAttribute('data-uuid', rowData.uuid);
      },
    });
    bindFiltrosTipoProveedor();
    _proveedoresTablaInicializada = true;
  }

  // Funcion global de refresco: recarga la tabla DataTables.
  w.refreshProveedoresTable = function () {
    if (w.Sintel && w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
      w.Sintel.Core.DataTablesFactory.reload(TABLA_PROV_SELECTOR);
    }
  };

  /**
   * Delegación de eventos resiliente (v2.61.7)
   */
  function initListEvents() {
    if (listEventsBound) return;

    console.log(`${MOD} Inicializando delegación de eventos global...`);

    d.addEventListener('click', function(e) {
      // Acciones de Tabla (Ver/Editar/Representantes/Eliminar)
      // NOTA: Boton "Nuevo" es HTMX declarativo (hx-get en [data-create-button]) — no requiere JS.
      const btnAction = e.target.closest(
        '.btn-view-proveedor, .btn-edit-proveedor, .btn-representantes-proveedor, .btn-delete-proveedor'
      );
      if (btnAction) {
        e.stopPropagation();
        if (btnAction.disabled || btnAction.classList.contains('disabled')) return;

        const id = btnAction.getAttribute('data-id');
        if (!id) return;

        if (btnAction.classList.contains('btn-view-proveedor')) {
          w.Sintel.Proveedores.Form?.openDetalle(id);
        } else if (btnAction.classList.contains('btn-edit-proveedor')) {
          w.Sintel.Proveedores.Form?.openOffcanvas(id);
        } else if (btnAction.classList.contains('btn-representantes-proveedor')) {
          w.Sintel.Proveedores.Form?.openDetalle(id, 'representantes');
        } else if (btnAction.classList.contains('btn-delete-proveedor')) {
          w.Sintel.Proveedores.Form?.eliminar(id);
        }
        return;
      }

      // Click en fila (fuera de un boton) abre detalle -- replica el
      // rowClick de Tabulator. data-uuid viene de row_attrs en tables.py.
      const row = e.target.closest('#tabla-proveedores tbody tr[data-uuid]');
      if (row) {
        if (e.target.closest('button')) return;
        const identifier = row.getAttribute('data-uuid');
        if (identifier) w.Sintel.Proveedores.Form?.openDetalle(identifier);
      }

      // Chips de filtro (Directorio / Cuentas por Pagar): marcar visualmente
      // el chip clickeado como activo dentro de su propio grupo -- hx-get/
      // hx-include ya disparan la recarga de la tabla via HTMX, esto solo
      // sincroniza el estado visual del boton.
      const chip = e.target.closest('[data-filtro-prov], [data-filtro-cxp]');
      if (chip) {
        const grupo = chip.closest('#filtros-tipo-proveedores, #filtros-estado-cuentas-pagar');
        grupo?.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
        chip.classList.add('active');
      }
    });

    listEventsBound = true;
  }

  /**
   * Vincula eventos de cambio de subtab (v3.17.0: agregado soporte para Representantes)
   */
  function initSubtabRedraws() {
    const tabCuentasPagar = d.querySelector('#subtab-cuentas-pagar-btn');
    const tabRepresentantes = d.querySelector('#subtab-representantes-btn');

    if (tabCuentasPagar) {
      tabCuentasPagar.addEventListener('shown.bs.tab', function() {
        console.log(`${MOD} Subtab Cuentas por Pagar activado.`);
      });
    }

    if (tabRepresentantes) {
      // Representantes: inicializado por representantes_directory.html (lazy-load)
      tabRepresentantes.addEventListener('shown.bs.tab', function() {
        console.log(`${MOD} Subtab Representantes activado (v3.17.0).`);
      });
    }
  }

  // Registro en Namespace Global
  w.Sintel = w.Sintel || {};
  w.Sintel.Proveedores = w.Sintel.Proveedores || {};
  w.Sintel.Proveedores.Main = {
    init: initListEvents,
    redraw: () => {
      var dt = w.Sintel.Core && w.Sintel.Core.DataTablesFactory && w.Sintel.Core.DataTablesFactory.get(TABLA_PROV_SELECTOR);
      if (dt) dt.columns.adjust();
    },
    refresh: () => w.refreshProveedoresTable()
  };

  initListEvents();
  initSubtabRedraws();

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', initProveedoresTabla);
  } else {
    initProveedoresTabla();
  }

  d.addEventListener('tab-activated', function (event) {
    if (event.detail && event.detail.tabName === 'proveedores') {
      setTimeout(function () {
        initProveedoresTabla();
        requestAnimationFrame(function () { w.Sintel.Proveedores.Main.redraw(); });
      }, 100);
    }
  });

})(window, document);
