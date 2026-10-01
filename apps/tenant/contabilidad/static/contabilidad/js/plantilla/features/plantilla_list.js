/**
 * plantilla_list.js - Feature List para PlantillaContable
 *
 * DataTables 3.x (mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos/Empleados/Proyectos/Inventario/
 * Contabilidad -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md):
 * la tabla (#tabla-plantillas-contables) se puebla via ajax contra
 * POST /api/v1/contabilidad/plantillas-contables/dt/
 * (PlantillaContableViewSet.dt()). django-tables2/PlantillaContableTable
 * retirados.
 *
 * Este archivo maneja: init de la tabla, acciones de fila (ver/editar/
 * eliminar), apertura de offcanvas, y el refresco tras una mutacion.
 */
(function (w, d) {
  'use strict';

  var TABLA_SELECTOR = '#tabla-plantillas-contables';
  var DT_URL = '/api/v1/contabilidad/plantillas-contables/dt/';
  var API_URL = '/api/v1/contabilidad/plantillas-contables/';
  var inicializada = false;

  var BADGE_TIPO = {
    VENTA: ['bg-success', 'Venta'],
    COMPRA: ['bg-primary', 'Compra'],
    GASTO: ['bg-warning', 'Gasto'],
    NOMINA: ['bg-info', 'Nomina'],
  };

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderNombre(value) {
    if (!value) return '<span class="text-muted fst-italic">Sin nombre</span>';
    return escapeHtml(value);
  }

  function renderTipo(data, type, row) {
    var cfg = BADGE_TIPO[row.tipo_transaccion] || ['bg-secondary', row.tipo_transaccion || 'Resolver'];
    return '<span class="badge ' + cfg[0] + '">' + escapeHtml(cfg[1]) + '</span>';
  }

  function renderModo(data, type, row) {
    if (row.modo === 'MOTOR' || row.tipo_transaccion) return '<span class="badge bg-dark">Motor</span>';
    return '<span class="badge bg-light text-dark border">Resolver</span>';
  }

  function renderLineasCount(value) {
    return '<span class="badge bg-secondary">' + (value || 0) + '</span>';
  }

  function renderActivo(value) {
    if (value) return '<span class="badge bg-success">Activa</span>';
    return '<span class="badge bg-danger">Inactiva</span>';
  }

  function renderAcciones(data, type, row) {
    return '<div class="btn-group btn-group-sm">' +
      '<button type="button" class="btn btn-outline-secondary btn-ver-plantilla" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Ver detalle"><i class="bi bi-eye"></i></button>' +
      '<button type="button" class="btn btn-outline-primary btn-editar-plantilla" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Editar"><i class="bi bi-pencil"></i></button>' +
      '<button type="button" class="btn btn-outline-danger btn-eliminar-plantilla" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  var COLUMNS = [
    { data: 'nombre', title: 'Nombre', render: function (v) { return renderNombre(v); } },
    { data: null, title: 'Tipo', render: renderTipo },
    { data: null, title: 'Modo', orderable: false, render: renderModo },
    { data: 'lineas_count', title: 'Líneas', orderable: false, render: function (v) { return renderLineasCount(v); } },
    { data: 'activo', title: 'Estado', render: function (v) { return renderActivo(v); } },
    { data: 'created_at', title: 'Creada' },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  function initTabla() {
    if (inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 20,
      order: [[4, 'desc']],
    });
    inicializada = true;
  }

  function showOffcanvas(id) {
    const el = d.getElementById(id);
    if (!el) return;
    w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
  }

  function htmxLoad(url, offcanvasId) {
    if (typeof htmx === 'undefined') return;
    htmx.ajax('GET', url, { target: '#offcanvas-container-plantilla', swap: 'innerHTML' })
      .then(() => showOffcanvas(offcanvasId));
  }

  function attachTableListeners() {
    d.body.addEventListener('click', async (ev) => {
      if (!ev.target.closest(TABLA_SELECTOR)) return;

      const btnVer = ev.target.closest('.btn-ver-plantilla');
      const btnEditar = ev.target.closest('.btn-editar-plantilla');
      const btnEliminar = ev.target.closest('.btn-eliminar-plantilla');

      if (btnVer) {
        ev.preventDefault();
        const uuid = btnVer.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/detalle/`, 'offcanvas-plantilla-detalle');
        return;
      }

      if (btnEditar) {
        ev.preventDefault();
        const uuid = btnEditar.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/editar/`, 'offcanvas-plantilla-editar');
        return;
      }

      if (btnEliminar) {
        ev.preventDefault();
        const uuid = btnEliminar.dataset.uuid;
        if (uuid && (await w.UIManager?.confirm('Eliminar esta plantilla contable? Se eliminaran todas sus lineas.'))) {
          if (w.PlantillaEditor && typeof w.PlantillaEditor.delete === 'function') {
            w.PlantillaEditor.delete(uuid);
          }
        }
      }
    });
  }

  function reload() {
    if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
      w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
    }
  }

  function attachToolbarListeners() {
    var selectTipo = d.getElementById('filter-tipo-plantilla');
    if (selectTipo) {
      selectTipo.addEventListener('change', function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 1, selectTipo.value);
        }
      });
    }

    var selectActivo = d.getElementById('filter-activo-plantilla');
    if (selectActivo) {
      selectActivo.addEventListener('change', function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 4, selectActivo.value);
        }
      });
    }

    var btnRefrescar = d.getElementById('btn-refrescar-plantilla');
    if (btnRefrescar) {
      btnRefrescar.addEventListener('click', reload);
    }
  }

  function init() {
    initTabla();
    attachTableListeners();
    attachToolbarListeners();
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Exportar API pública -- PlantillaEditor llama a reload() tras crear/editar/eliminar
  w.PlantillaList = Object.freeze({
    init,
    reload,
  });
})(window, document);
