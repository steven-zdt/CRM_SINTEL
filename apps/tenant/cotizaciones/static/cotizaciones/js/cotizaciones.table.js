// @ts-nocheck
/**
 * cotizaciones.table.js — Tabla "Cotizaciones" es DataTables 3.x
 * (#tabla-cotizaciones-principal, mismo patron ya validado en Ventas/
 * Bancos/Facturas/Clientes/Proveedores/Compras/Gastos/Empleados/
 * Proyectos/Inventario/Contabilidad -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via ajax
 * contra POST /api/v1/cotizaciones/dt/ (CotizacionViewSet.dt()). Tabulator
 * retirado. Los KPIs (Total/Borrador/Enviada/Aceptada/Vencidas/Monto)
 * siguen server-rendered via HTMX (kpis_cotizaciones.html,
 * CotizacionKpisView) -- antes se computaban client-side sobre TODAS las
 * filas ya cargadas por Tabulator, incompatible con paginacion server-side.
 *
 * Namespace: window.Sintel.Cotizaciones.table
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Cotizaciones = w.Sintel.Cotizaciones || {};

  var MOD = '[cotizaciones.table]';
  var TABLA_SELECTOR = '#tabla-cotizaciones-principal';
  var DT_URL = '/api/v1/cotizaciones/dt/';
  var _inicializada = false;

  // ── Formatters ──────────────────────────────────────────────────────────────

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function fmtMoneda(v) {
    var n = parseFloat(v);
    if (isNaN(n)) return '—';
    // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
    if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
      return w.DOMUtils.formatCurrency(n, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency: 'USD',
      minimumFractionDigits: 0, maximumFractionDigits: 0
    }).format(n);
  }

  function fmtFecha(v) {
    if (!v) return '<span class="text-muted">—</span>';
    try {
      var fecha = new Date(v + 'T00:00:00');
      return fecha.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch (_) { return escapeHtml(v); }
  }

  // Hallazgo real (2026-09-25): estas claves seguian los nombres de
  // estado ANTERIORES al rename de COTIZACIONES-02 (ACEPTADA->APROBADA,
  // CANCELADA->RECHAZADA, ver Cotizacion.Estado en models.py) -- ninguna
  // cotizacion real tiene ya esos valores, asi que APROBADA/RECHAZADA/
  // ARCHIVADA siempre caian al badge generico bg-light. Corregido a los
  // valores reales.
  var BADGE_ESTADO = {
    BORRADOR: ['bg-secondary', 'Borrador'],
    ENVIADA: ['bg-primary', 'Enviada'],
    APROBADA: ['bg-success', 'Aprobada'],
    RECHAZADA: ['bg-danger', 'Rechazada'],
    ARCHIVADA: ['bg-dark', 'Archivada'],
  };

  function renderEstado(data, type, row) {
    var pair = BADGE_ESTADO[row.estado] || ['bg-light text-dark', row.estado || '—'];
    var display = row.estado_display || pair[1];
    return '<span class="badge ' + pair[0] + ' px-2 py-1">' + escapeHtml(display) + '</span>';
  }

  var TIPO_MAP = { PRODUCTOS: 'Productos', SERVICIOS: 'Servicios', MIXTO: 'Mixto' };

  function renderNumero(data, type, row) {
    var num = row.numero_cotizacion || '—';
    var cod = row.codigo_unico || '';
    var tipoLabel = TIPO_MAP[row.tipo_cotizacion] || row.tipo_cotizacion;
    var tipoHtml = tipoLabel
      ? '<span class="badge bg-light text-secondary border fw-normal" style="font-size:0.65rem;">' + escapeHtml(tipoLabel) + '</span> '
      : '';
    return '<div style="line-height:1.35;">' +
      '<div class="fw-semibold">' + escapeHtml(num) + '</div>' +
      '<div class="mt-1">' + tipoHtml + (cod ? '<code class="text-muted" style="font-size:0.7rem;">' + escapeHtml(cod) + '</code>' : '') + '</div>' +
      '</div>';
  }

  function renderCliente(data, type, row) {
    var nombre = row.cliente_razon_social || row.cliente_nombre || '—';
    return '<span class="text-truncate d-block small" style="max-width:160px;" title="' + escapeHtml(nombre) + '">' + escapeHtml(nombre) + '</span>';
  }

  function renderVencimiento(data, type, row) {
    var v = row.fecha_vencimiento;
    if (!v) return '<span class="text-muted">—</span>';
    var hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    var fecha = new Date(v + 'T00:00:00');
    var abierto = row.estado === 'BORRADOR' || row.estado === 'ENVIADA';
    var vencida = abierto && fecha < hoy;
    var label = fmtFecha(v);
    if (vencida) {
      return '<span class="text-danger fw-semibold" title="Vencida"><i class="bi bi-exclamation-triangle-fill me-1"></i>' + label + '</span>';
    }
    return '<span>' + label + '</span>';
  }

  function renderTotal(value) {
    return '<span class="fw-semibold">' + fmtMoneda(value) + '</span>';
  }

  // Maquina de estados real (Cotizacion.Estado.TRANSICIONES_VALIDAS,
  // business_service.py): BORRADOR->ENVIADA (gated por PDF, endpoint
  // generar-pdf/), ENVIADA->APROBADA|RECHAZADA (endpoints aprobar/
  // rechazar/). Solo se exponen aqui las transiciones que el usuario
  // pidio -- volver-a-borrador/archivar quedan disponibles por API pero
  // no se agregan a la grilla para no saturar la UI (alcance minimo,
  // 2026-09-25).
  function renderAcciones(data, type, row) {
    var uuid = row.uuid || '';
    if (!uuid) return '<span class="text-muted small">—</span>';
    var estado = row.estado;
    var html = '<div class="btn-group btn-group-sm" role="group">';

    // Editar: solo BORRADOR admite edicion de cabecera/items
    // (CotizacionService.actualizar_cotizacion() rechaza cualquier otro
    // estado con 400) -- ocultarlo evita un click que siempre falla.
    if (estado === 'BORRADOR') {
      html += '<button class="btn btn-outline-primary btn-edit-cotizacion" data-uuid="' + escapeHtml(uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>';
    }
    html += '<button class="btn btn-outline-info btn-detail-cotizacion" data-uuid="' + escapeHtml(uuid) + '" title="Detalle"><i class="bi bi-eye"></i></button>';
    html += '<button class="btn btn-outline-secondary btn-pdf-cotizacion" data-uuid="' + escapeHtml(uuid) + '" title="Descargar PDF"><i class="bi bi-file-pdf"></i></button>';

    if (estado === 'BORRADOR') {
      html += '<button class="btn btn-outline-primary btn-send-cotizacion" data-uuid="' + escapeHtml(uuid) + '" title="Enviar (genera PDF)"><i class="bi bi-send"></i></button>';
    } else if (estado === 'ENVIADA') {
      html += '<button class="btn btn-outline-success btn-approve-cotizacion" data-uuid="' + escapeHtml(uuid) + '" title="Aprobar"><i class="bi bi-check-circle"></i></button>';
      html += '<button class="btn btn-outline-danger btn-reject-cotizacion" data-uuid="' + escapeHtml(uuid) + '" title="Rechazar"><i class="bi bi-x-circle"></i></button>';
    }

    // Eliminar: solo BORRADOR/ENVIADA (CotizacionService.eliminar_cotizacion()
    // -- APROBADA/RECHAZADA/ARCHIVADA nunca admiten hard delete, la
    // trazabilidad comercial se conserva via esos estados, no borrando).
    if (estado === 'BORRADOR' || estado === 'ENVIADA') {
      html += '<button class="btn btn-outline-danger btn-delete-cotizacion" data-uuid="' + escapeHtml(uuid) + '" title="Eliminar"><i class="bi bi-trash"></i></button>';
    }

    html += '</div>';
    return html;
  }

  var COLUMNS = [
    { data: null, title: 'Cotizacion', render: renderNumero },
    { data: null, title: 'Cliente', render: renderCliente },
    { data: 'fecha_emision', title: 'Emision', render: function (v) { return fmtFecha(v); } },
    { data: null, title: 'Vencimiento', render: renderVencimiento },
    { data: null, title: 'Estado', render: renderEstado },
    { data: 'total_con_impuestos', title: 'Total', className: 'text-end', render: function (v) { return renderTotal(v); } },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  // ── Busqueda global (input ya existente en el toolbar, redirigido a
  // Factory.search() -- antes lo manejaba Tabulator via searchInputSelector) ──

  function initSearchInput() {
    var input = d.getElementById('search-cotizacion');
    if (!input || input.dataset.bound === 'true') return;
    input.dataset.bound = 'true';
    var timer = null;
    input.addEventListener('keyup', function () {
      clearTimeout(timer);
      var value = this.value;
      timer = setTimeout(function () {
        if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
          w.Sintel.Core.DataTablesFactory.search(TABLA_SELECTOR, value);
        }
      }, 400);
    });
  }

  // ── Filtros por Estado (chips) ────────────────────────────────────────────

  function initFiltrosEstado() {
    var contenedor = d.getElementById('filtros-estado-cotizaciones');
    if (!contenedor || contenedor.dataset.bound === 'true') return;
    contenedor.dataset.bound = 'true';
    contenedor.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-estado]');
      if (!btn) return;
      contenedor.querySelectorAll('[data-estado]').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var estado = btn.getAttribute('data-estado');
      if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
        w.Sintel.Core.DataTablesFactory.columnSearch(TABLA_SELECTOR, 4, estado);
      }
    });
  }

  // ── Inicializar Tabla ─────────────────────────────────────────────────────

  function initTable() {
    if (_inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, DT_URL, COLUMNS, {
      pageLength: 20,
      order: [[2, 'desc']],
    });
    initGridEvents();
    initFiltrosEstado();
    initSearchInput();
    _inicializada = true;
    console.log(MOD + ' Tabla inicializada');
  }

  // ── Event Delegation ──────────────────────────────────────────────────────
  // Delegado sobre document.body (persistente -- la tabla se recrea via
  // ajax.reload(), nunca via innerHTML swap de un contenedor).

  function initGridEvents() {
    d.body.addEventListener('click', function (e) {
      if (!e.target.closest(TABLA_SELECTOR)) return;
      var btn = e.target.closest('button[data-uuid]');
      if (!btn) return;
      e.stopPropagation();
      var uuid = btn.getAttribute('data-uuid');
      if (!uuid) return;

      var api = w.Sintel.Cotizaciones.api;
      if (!api) return;

      var htmxUrl = null;
      if (btn.classList.contains('btn-edit-cotizacion')) {
        htmxUrl = api.offcanvasEditarUrl(uuid);
      } else if (btn.classList.contains('btn-detail-cotizacion')) {
        htmxUrl = api.offcanvasDetalleUrl(uuid);
      } else if (btn.classList.contains('btn-pdf-cotizacion')) {
        window.open(api.exportarPdfUrl(uuid), '_blank');
        return;
      } else if (btn.classList.contains('btn-delete-cotizacion')) {
        w.Sintel.Cotizaciones.ui.confirmarEliminar(uuid);
        return;
      } else if (btn.classList.contains('btn-send-cotizacion')) {
        w.Sintel.Cotizaciones.ui.confirmarEnviar(uuid);
        return;
      } else if (btn.classList.contains('btn-approve-cotizacion')) {
        w.Sintel.Cotizaciones.ui.confirmarAprobar(uuid);
        return;
      } else if (btn.classList.contains('btn-reject-cotizacion')) {
        w.Sintel.Cotizaciones.ui.confirmarRechazar(uuid);
        return;
      }

      if (htmxUrl) {
        var trigger = d.createElement('button');
        trigger.setAttribute('hx-get', htmxUrl);
        trigger.setAttribute('hx-target', '#offcanvas-container');
        d.body.appendChild(trigger);
        if (w.htmx) w.htmx.process(trigger);
        trigger.click();
        trigger.remove();
      }
    });
  }

  // ── Export ────────────────────────────────────────────────────────────────

  w.Sintel.Cotizaciones.table = {
    init: initTable,
    refresh: function () {
      if (w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
        w.Sintel.Core.DataTablesFactory.reload(TABLA_SELECTOR);
      }
      // Los KPIs siguen server-rendered via HTMX (kpis_cotizaciones.html).
      d.body.dispatchEvent(new CustomEvent('cotizacion-updated'));
    },
    redraw: function () {
      var dt = w.Sintel.Core && w.Sintel.Core.DataTablesFactory && w.Sintel.Core.DataTablesFactory.get(TABLA_SELECTOR);
      if (dt) dt.columns.adjust();
    },
    getInstance: function () {
      return w.Sintel.Core && w.Sintel.Core.DataTablesFactory && w.Sintel.Core.DataTablesFactory.get(TABLA_SELECTOR);
    }
  };

})(window, document);
