/**
 * cuenta_list.js - Feature List para CuentaContable (Plan de Cuentas)
 *
 * La tabla es DataTables 3.x (#tabla-cuentas, mismo patron ya validado en
 * Ventas/Bancos/Facturas/Clientes/Proveedores/Compras/Gastos/Empleados/
 * Proyectos/Inventario -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md),
 * poblada via ajax contra POST /api/v1/contabilidad/cuentas-contables/dt/.
 * CuentaContableTable/CuentaContableTableView (django-tables2) retirados.
 * Periodos/Asientos/Retenciones/Plantillas siguen en django-tables2/HTMX --
 * no migrados en esta pasada.
 *
 * Este archivo maneja: init de la tabla, acciones de fila (ver/editar/
 * eliminar), apertura de offcanvas, y el refresco tras una mutacion.
 */
(function (w, d) {
  'use strict';

  const TABLA_SELECTOR = '#tabla-cuentas';
  const DT_URL = '/api/v1/contabilidad/cuentas-contables/dt/';
  const API_URL = '/api/v1/contabilidad/cuentas-contables/';
  let _tablaInicializada = false;

  const BADGE_TIPO = { ACTIVO: 'primary', PASIVO: 'danger', PATRIMONIO: 'success', INGRESO: 'info', GASTO: 'warning' };

  function escapeHtml(str) {
    const div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function renderTipo(value) {
    const badge = BADGE_TIPO[value] || 'secondary';
    return '<span class="badge bg-' + badge + '">' + escapeHtml(value || '—') + '</span>';
  }

  function renderEstado(value) {
    return value ? '<span class="badge bg-success">Activa</span>' : '<span class="badge bg-secondary">Inactiva</span>';
  }

  function renderCreado(value) {
    if (!value) return '—';
    const parsed = new Date(value);
    if (isNaN(parsed.getTime())) return escapeHtml(value);
    return parsed.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) +
      ' ' + parsed.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
  }

  function renderAcciones(data, type, row) {
    return '<div class="btn-group btn-group-sm">' +
      '<button type="button" class="btn btn-outline-secondary btn-ver-cuenta" data-uuid="' + escapeHtml(row.uuid) + '" title="Ver detalle"><i class="bi bi-eye"></i></button>' +
      '<button type="button" class="btn btn-outline-primary btn-editar-cuenta" data-uuid="' + escapeHtml(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
      '<button type="button" class="btn btn-outline-danger btn-eliminar-cuenta" data-uuid="' + escapeHtml(row.uuid) + '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
      '</div>';
  }

  const COLUMNS = [
    { data: 'codigo', title: 'Código' },
    { data: 'nombre', title: 'Nombre' },
    { data: 'tipo', title: 'Tipo', render: renderTipo },
    { data: 'activa', title: 'Estado', render: renderEstado },
    { data: 'created_at', title: 'Creado', render: renderCreado },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  function initTabla() {
    if (_tablaInicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 20,
      order: [[0, 'asc']],
    });
    _tablaInicializada = true;
  }

  function showOffcanvas(id) {
    const el = d.getElementById(id);
    if (!el) return;
    w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
  }

  function htmxLoad(url, offcanvasId) {
    if (typeof htmx === 'undefined') return;
    htmx.ajax('GET', url, { target: '#offcanvas-container-cuentas', swap: 'innerHTML' })
      .then(() => showOffcanvas(offcanvasId));
  }

  function attachTableListeners() {
    d.body.addEventListener('click', async (ev) => {
      if (!ev.target.closest(TABLA_SELECTOR)) return;

      const btnVer = ev.target.closest('.btn-ver-cuenta');
      const btnEditar = ev.target.closest('.btn-editar-cuenta');
      const btnEliminar = ev.target.closest('.btn-eliminar-cuenta');

      if (btnVer) {
        ev.preventDefault();
        const uuid = btnVer.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/detalle/`, 'offcanvas-cuenta-detalle');
        return;
      }

      if (btnEditar) {
        ev.preventDefault();
        const uuid = btnEditar.dataset.uuid;
        if (uuid) htmxLoad(`${API_URL}${uuid}/render-offcanvas/editar/`, 'offcanvas-cuenta-editar');
        return;
      }

      if (btnEliminar) {
        ev.preventDefault();
        const uuid = btnEliminar.dataset.uuid;
        if (uuid && (await w.UIManager?.confirm('¿Está seguro de que desea eliminar esta cuenta contable?'))) {
          if (w.CuentaEditor && typeof w.CuentaEditor.delete === 'function') {
            w.CuentaEditor.delete(uuid);
          }
        }
      }
    });
  }

  function reload() {
    if (w.Sintel && w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
      w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
    }
  }

  function init() {
    initTabla();
    attachTableListeners();
    // cuenta_offcanvas_form.html dispara 'cuenta-updated' tras crear/editar
    // (antes lo escuchaba el panel HTMX #contabilidad-cuentas-panel, ver
    // list_cuentas.html/F31.9) -- ahora recarga la tabla DataTables directo.
    d.body.addEventListener('cuenta-updated', reload);
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Exportar API pública -- CuentaEditor llama a reload() tras crear/editar/eliminar
  w.CuentaList = Object.freeze({ init, reload });
})(window, document);
