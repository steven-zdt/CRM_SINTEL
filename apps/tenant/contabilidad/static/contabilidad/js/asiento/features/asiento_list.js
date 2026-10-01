/**
 * asiento_list.js - Feature List para AsientoContable
 *
 * DataTables 3.x (mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos/Empleados/Proyectos/Inventario/
 * Contabilidad -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md):
 * la tabla (#tabla-asientos-contables) se puebla via ajax contra
 * POST /api/v1/contabilidad/asientos-contables/dt/
 * (AsientoContableViewSet.dt()). django-tables2/AsientoContableTable
 * retirados. El filtro de cuadratura (?cuadratura=cuadrado|no_cuadrado) se
 * omitio en la migracion -- no es un filtro de columna simple (compara 2
 * campos entre si), ver docstring de AsientoContableViewSet.dt().
 *
 * Este archivo maneja: init de la tabla, acciones de fila (ver/editar/
 * aprobar/eliminar), apertura de offcanvas, y el refresco tras una mutacion.
 */
(function (w, d) {
  'use strict';

  var TABLA_SELECTOR = '#tabla-asientos-contables';
  var DT_URL = '/api/v1/contabilidad/asientos-contables/dt/';
  var API_URL = '/api/v1/contabilidad/asientos-contables/';
  var inicializada = false;

  var BADGE_ESTADO = { BORRADOR: 'secondary', APROBADO: 'success', CERRADO: 'info' };

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderDescripcion(value) {
    if (!value) return '<span class="text-muted">—</span>';
    var texto = value.length > 50 ? value.substring(0, 50) + '...' : value;
    return escapeHtml(texto);
  }

  function renderEstado(data, type, row) {
    var cls = BADGE_ESTADO[row.estado] || 'light text-dark';
    return '<span class="badge bg-' + cls + '">' + escapeHtml(row.estado || '—') + '</span>';
  }

  function renderMovimientos(value) {
    var n = parseInt(value) || 0;
    if (!n) return '<span class="text-muted">0</span>';
    return '<span class="badge bg-primary">' + n + '</span>';
  }

  function renderMoneda(value) {
    var n = parseFloat(value) || 0;
    return '<span>$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '</span>';
  }

  function renderCuadratura(data, type, row) {
    var debe = parseFloat(row.total_debe) || 0;
    var haber = parseFloat(row.total_haber) || 0;
    var diferencia = Math.abs(debe - haber);
    if (diferencia < 0.01) {
      return '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Cuadrado</span>';
    }
    return '<span class="badge bg-danger"><i class="bi bi-x-circle"></i> $' +
      diferencia.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '</span>';
  }

  function renderAcciones(data, type, row) {
    var debe = parseFloat(row.total_debe) || 0;
    var haber = parseFloat(row.total_haber) || 0;
    var cuadrado = Math.abs(debe - haber) < 0.01;
    var aprobarBtn = (row.estado === 'BORRADOR' && cuadrado)
      ? '<button type="button" class="btn btn-outline-success btn-aprobar-asiento" data-uuid="' + escapeHtml(row.uuid) +
        '" title="Aprobar"><i class="bi bi-check-circle"></i></button>'
      : '';
    return '<div class="btn-group btn-group-sm">' +
      '<button type="button" class="btn btn-outline-secondary btn-ver-asiento" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Ver detalle"><i class="bi bi-eye"></i></button>' +
      '<button type="button" class="btn btn-outline-primary btn-editar-asiento" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Editar"><i class="bi bi-pencil"></i></button>' +
      aprobarBtn +
      '<button type="button" class="btn btn-outline-danger btn-eliminar-asiento" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  var COLUMNS = [
    { data: 'numero', title: 'Número' },
    { data: 'fecha', title: 'Fecha' },
    { data: 'descripcion', title: 'Descripción', render: function (v) { return renderDescripcion(v); } },
    { data: null, title: 'Estado', render: renderEstado },
    { data: 'movimientos_count', title: 'Movimientos', orderable: false, render: function (v) { return renderMovimientos(v); } },
    { data: 'total_debe', title: 'Débito', render: function (v) { return renderMoneda(v); } },
    { data: 'total_haber', title: 'Crédito', render: function (v) { return renderMoneda(v); } },
    { data: null, title: 'Cuadratura', orderable: false, render: renderCuadratura },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  function initTabla() {
    if (inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 20,
      order: [[1, 'desc']],
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
    htmx.ajax('GET', url, { target: '#offcanvas-container-asiento', swap: 'innerHTML' })
      .then(() => showOffcanvas(offcanvasId));
  }

  function attachTableListeners() {
    d.body.addEventListener('click', async (ev) => {
      if (!ev.target.closest(TABLA_SELECTOR)) return;

      const btnVer = ev.target.closest('.btn-ver-asiento');
      const btnEditar = ev.target.closest('.btn-editar-asiento');
      const btnAprobar = ev.target.closest('.btn-aprobar-asiento');
      const btnEliminar = ev.target.closest('.btn-eliminar-asiento');

      if (btnVer) {
        ev.preventDefault();
        const uuid = btnVer.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/detalle/`, 'offcanvas-asiento-detalle');
        return;
      }

      if (btnEditar) {
        ev.preventDefault();
        const uuid = btnEditar.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/editar/`, 'offcanvas-asiento-editar');
        return;
      }

      if (btnAprobar) {
        ev.preventDefault();
        const uuid = btnAprobar.dataset.uuid;
        if (uuid && w.AsientoEditor && typeof w.AsientoEditor.aprobar === 'function') {
          w.AsientoEditor.aprobar(uuid);
        }
        return;
      }

      if (btnEliminar) {
        ev.preventDefault();
        const uuid = btnEliminar.dataset.uuid;
        if (uuid && (await w.UIManager?.confirm('¿Está seguro de que desea eliminar este asiento contable?'))) {
          if (w.AsientoEditor && typeof w.AsientoEditor.delete === 'function') {
            w.AsientoEditor.delete(uuid);
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
    var selectEstado = d.getElementById('filter-estado-asiento');
    if (selectEstado) {
      selectEstado.addEventListener('change', function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 3, selectEstado.value);
        }
      });
    }

    var btnRefrescar = d.getElementById('btn-refrescar-asiento');
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

  // Exportar API pública -- AsientoEditor llama a reload() tras crear/editar/aprobar/eliminar
  w.AsientoList = Object.freeze({
    init,
    reload,
  });
})(window, document);
