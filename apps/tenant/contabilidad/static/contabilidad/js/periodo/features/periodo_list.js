/**
 * periodo_list.js - Feature List para PeriodoContable
 *
 * DataTables 3.x (mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos/Empleados/Proyectos/Inventario/
 * Contabilidad -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md):
 * la tabla (#tabla-periodos-contables) se puebla via ajax contra
 * POST /api/v1/contabilidad/periodos-contables/dt/
 * (PeriodoContableViewSet.dt()). django-tables2/PeriodoContableTable
 * retirados.
 *
 * Este archivo maneja: init de la tabla, acciones de fila (ver/editar/
 * cerrar/eliminar), apertura de offcanvas, y el refresco tras una mutacion.
 */
(function (w, d) {
  'use strict';

  var TABLA_SELECTOR = '#tabla-periodos-contables';
  var DT_URL = '/api/v1/contabilidad/periodos-contables/dt/';
  var API_URL = '/api/v1/contabilidad/periodos-contables/';
  var inicializada = false;

  var BADGE_ESTADO = { ABIERTO: 'success', CERRADO: 'danger' };

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderEstado(data, type, row) {
    var cls = BADGE_ESTADO[row.estado] || 'light text-dark';
    return '<span class="badge bg-' + cls + '">' + escapeHtml(row.estado_display || row.estado) + '</span>';
  }

  function renderFechaCierre(value) {
    if (!value) return '<span class="text-muted">—</span>';
    return escapeHtml(value);
  }

  function renderAcciones(data, type, row) {
    var cerrarBtn = row.estado === 'ABIERTO'
      ? '<button type="button" class="btn btn-outline-warning btn-cerrar-periodo" data-uuid="' + escapeHtml(row.uuid) +
        '" title="Cerrar periodo"><i class="bi bi-lock"></i></button>'
      : '';
    return '<div class="btn-group btn-group-sm">' +
      '<button type="button" class="btn btn-outline-secondary btn-ver-periodo" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Ver detalle"><i class="bi bi-eye"></i></button>' +
      '<button type="button" class="btn btn-outline-primary btn-editar-periodo" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Editar"><i class="bi bi-pencil"></i></button>' +
      cerrarBtn +
      '<button type="button" class="btn btn-outline-danger btn-eliminar-periodo" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  var COLUMNS = [
    { data: 'periodo', title: 'Periodo' },
    { data: 'fecha_inicio', title: 'Fecha Inicio' },
    { data: 'fecha_fin', title: 'Fecha Fin' },
    { data: null, title: 'Estado', render: renderEstado },
    { data: 'fecha_cierre', title: 'Fecha Cierre', render: function (v) { return renderFechaCierre(v); } },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  function initTabla() {
    if (inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 20,
      order: [[0, 'desc']],
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
    htmx.ajax('GET', url, { target: '#offcanvas-container-periodo', swap: 'innerHTML' })
      .then(() => showOffcanvas(offcanvasId));
  }

  function attachTableListeners() {
    d.body.addEventListener('click', async (ev) => {
      if (!ev.target.closest(TABLA_SELECTOR)) return;

      const btnVer = ev.target.closest('.btn-ver-periodo');
      const btnEditar = ev.target.closest('.btn-editar-periodo');
      const btnCerrar = ev.target.closest('.btn-cerrar-periodo');
      const btnEliminar = ev.target.closest('.btn-eliminar-periodo');

      if (btnVer) {
        ev.preventDefault();
        const uuid = btnVer.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/detalle/`, 'offcanvas-periodo-detalle');
        return;
      }

      if (btnEditar) {
        ev.preventDefault();
        const uuid = btnEditar.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/editar/`, 'offcanvas-periodo-editar');
        return;
      }

      if (btnCerrar) {
        ev.preventDefault();
        const uuid = btnCerrar.dataset.uuid;
        if (uuid && w.PeriodoEditor && typeof w.PeriodoEditor.cerrar === 'function') {
          w.PeriodoEditor.cerrar(uuid);
        }
        return;
      }

      if (btnEliminar) {
        ev.preventDefault();
        const uuid = btnEliminar.dataset.uuid;
        if (uuid && (await w.UIManager?.confirm('¿Está seguro de que desea eliminar este periodo contable?'))) {
          if (w.PeriodoEditor && typeof w.PeriodoEditor.delete === 'function') {
            w.PeriodoEditor.delete(uuid);
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
    var selectEstado = d.getElementById('filter-estado-periodo');
    if (selectEstado) {
      selectEstado.addEventListener('change', function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 3, selectEstado.value);
        }
      });
    }

    var btnRefrescar = d.getElementById('btn-refrescar-periodos');
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

  // Exportar API pública -- PeriodoEditor llama a reload() tras crear/editar/cerrar/eliminar
  w.PeriodoList = Object.freeze({
    init,
    reload,
  });
})(window, document);
