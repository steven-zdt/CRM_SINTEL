/**
 * libro_diario_list.js — Libro Diario Contable
 *
 * Normatividad Colombia: Codigo de Comercio Art. 48 (orden cronologico obligatorio)
 *
 * DataTables 3.x (mismo patron ya validado en Ventas/Bancos/Facturas/
 * Clientes/Proveedores/Compras/Gastos/Empleados/Proyectos/Inventario/
 * Contabilidad -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md):
 * la tabla (#tabla-libro-diario) se puebla via ajax contra
 * POST /api/v1/contabilidad/libro-diario/dt/ (LibroDiarioViewSet.dt() --
 * consulta AsientoContable directo, no los extractores cross-app de
 * list()/LibroDiarioAPI, que se dejan intactos para otros consumidores).
 * Reemplaza el Tabulator client-side anterior.
 *
 * periodo_uuid/fecha_inicio/fecha_fin/estado son parametros de "reporte"
 * (el usuario elige un periodo y pulsa Consultar) -- viajan como query
 * string en la URL del ajax, se aplican con dt.ajax.url(...).load() (mismo
 * patron ya usado en cuentas_pagar_list.js para los chips de estado_pago).
 * `resumen` viaja como campo extra en la misma respuesta JSON (DataTables
 * ignora claves fuera de draw/recordsTotal/recordsFiltered/data) -- se lee
 * en onDraw() via dt.ajax.json().resumen.
 *
 * Dependencias: Sintel.Core.DataTablesFactory, Sintel.Core.Http, DOMUtils,
 * window.bootstrap, htmx
 */
(function (w, d) {
  'use strict';

  const MOD = '[libro.diario.list]';
  const TABLA_SELECTOR = '#tabla-libro-diario';
  const DT_URL_BASE = '/api/v1/contabilidad/libro-diario/dt/';
  const TAB_ID = '#subtab-libro-diario';
  const PERIODOS_API_URL = '/api/v1/contabilidad/periodos-contables/';
  const ASIENTOS_API_URL = '/api/v1/contabilidad/asientos-contables/';

  let inicializada = false;
  let consultado = false;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function escapeHtml(str) {
    var div = d.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function fmtMoney(val) {
    const n = parseFloat(val) || 0;
    // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
    if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
      return w.DOMUtils.formatCurrency(n, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency: 'USD',
      minimumFractionDigits: 0, maximumFractionDigits: 0,
    }).format(n);
  }

  function fmtFecha(val) {
    if (!val) return '---';
    try { return new Date(val + 'T00:00:00').toLocaleDateString('es-CO'); }
    catch (_) { return val; }
  }

  // ---------------------------------------------------------------------------
  // Columns (AsientoContableListSerializer)
  // ---------------------------------------------------------------------------

  function renderNumero(value) {
    return '<strong>' + escapeHtml(value || '---') + '</strong>';
  }

  function renderDescripcion(value) {
    var v = value || '---';
    var texto = v.length > 60 ? v.substring(0, 60) + '...' : v;
    return escapeHtml(texto);
  }

  function renderEstado(value) {
    var map = {
      BORRADOR: '<span class="badge bg-secondary">Borrador</span>',
      APROBADO: '<span class="badge bg-success">Aprobado</span>',
      CERRADO: '<span class="badge bg-info">Cerrado</span>',
    };
    return map[value] || '<span class="badge bg-light text-dark">' + escapeHtml(value || '---') + '</span>';
  }

  function renderMovimientos(value) {
    var n = parseInt(value) || 0;
    return n > 0 ? '<span class="badge bg-primary">' + n + '</span>' : '<span class="text-muted">0</span>';
  }

  function renderCuadratura(data, type, row) {
    var debe = parseFloat(row.total_debe) || 0;
    var haber = parseFloat(row.total_haber) || 0;
    return Math.abs(debe - haber) < 0.01
      ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>OK</span>'
      : '<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Error</span>';
  }

  function renderAcciones(data, type, row) {
    if (!row.uuid) return '';
    return '<button class="btn btn-sm btn-outline-secondary btn-ver-asiento-libro" data-uuid="' + escapeHtml(row.uuid) +
      '" title="Ver detalle del asiento"><i class="bi bi-eye"></i></button>';
  }

  var COLUMNS = [
    { data: 'numero', title: 'Numero', render: function (v) { return renderNumero(v); } },
    { data: 'fecha', title: 'Fecha', render: function (v) { return fmtFecha(v); } },
    { data: 'descripcion', title: 'Descripcion', orderable: false, render: function (v) { return renderDescripcion(v); } },
    { data: 'estado', title: 'Estado', render: function (v) { return renderEstado(v); } },
    { data: 'movimientos_count', title: 'Movs.', orderable: false, render: function (v) { return renderMovimientos(v); } },
    { data: 'total_debe', title: 'Debito', className: 'text-end', render: function (v) { return '<span class="text-primary">' + fmtMoney(v) + '</span>'; } },
    { data: 'total_haber', title: 'Credito', className: 'text-end', render: function (v) { return '<span class="text-danger">' + fmtMoney(v) + '</span>'; } },
    { data: null, title: 'Cuadratura', orderable: false, render: renderCuadratura },
    { data: null, title: '', orderable: false, searchable: false, render: renderAcciones },
  ];

  // ---------------------------------------------------------------------------
  // Resumen panel (poblado desde el campo extra `resumen` de la respuesta)
  // ---------------------------------------------------------------------------

  function updateResumen(dt) {
    const el = d.getElementById('resumen-libro-diario');
    if (!el) return;
    const json = dt.ajax.json() || {};
    const r = json.resumen || {};
    const total = r.total_asientos || 0;
    const cuadrados = r.cuadrados || 0;
    const descuadre = r.descuadrados || 0;
    const totalDebe = parseFloat(r.total_debe) || 0;
    const totalHaber = parseFloat(r.total_haber) || 0;
    const cuadra = Math.abs(totalDebe - totalHaber) < 0.01;

    const cuadraBadge = total > 0
      ? `<span class="badge ${cuadra ? 'bg-success' : 'bg-danger'}">
           ${cuadra ? '<i class="bi bi-check-circle me-1"></i>Cuadratura OK' : 'Descuadre ' + fmtMoney(Math.abs(totalDebe - totalHaber))}
         </span>`
      : '';

    el.innerHTML = `
      <span class="badge bg-secondary">${total} asientos</span>
      <span class="badge bg-success">${cuadrados} cuadrados</span>
      ${descuadre > 0 ? `<span class="badge bg-danger">${descuadre} descuadrados</span>` : ''}
      <span class="badge bg-outline-secondary border text-dark">D: ${fmtMoney(totalDebe)}</span>
      <span class="badge bg-outline-secondary border text-dark">H: ${fmtMoney(totalHaber)}</span>
      ${cuadraBadge}
    `;
  }

  // ---------------------------------------------------------------------------
  // Table init
  // ---------------------------------------------------------------------------

  function _ajaxUrl() {
    const periodoSelect = d.getElementById('filter-periodo-libro');
    const periodoUuid = periodoSelect ? periodoSelect.value : '';
    const fechaInicio = d.getElementById('filter-fecha-inicio-libro')?.value || '';
    const fechaFin = d.getElementById('filter-fecha-fin-libro')?.value || '';
    const estado = d.getElementById('filter-estado-libro')?.value || '';

    const params = new URLSearchParams();
    if (periodoUuid) {
      params.set('periodo_uuid', periodoUuid);
    } else if (fechaInicio && fechaFin) {
      params.set('fecha_inicio', fechaInicio);
      params.set('fecha_fin', fechaFin);
    }
    if (estado) params.set('estado', estado);
    const qs = params.toString();
    return qs ? DT_URL_BASE + '?' + qs : DT_URL_BASE;
  }

  function initTabla() {
    if (inicializada) return;
    if (typeof DataTable === 'undefined' || !w.Sintel || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
    w.Sintel.Core.DataTablesFactory.create(TABLA_SELECTOR, _ajaxUrl(), COLUMNS, {
      pageLength: 25,
      order: [[1, 'asc'], [0, 'asc']],
      onDraw: updateResumen,
    });
    inicializada = true;
  }

  // ---------------------------------------------------------------------------
  // Load available periods into dropdown
  // ---------------------------------------------------------------------------

  async function loadPeriodos() {
    const select = d.getElementById('filter-periodo-libro');
    if (!select) return;

    try {
      const url = `${PERIODOS_API_URL}?ordering=-periodo&page_size=50`;
      const response = await w.Sintel.Core.Http.request('GET', url);
      if (!response.ok) return;

      const data = response.data;
      const periodos = Array.isArray(data) ? data : (data.results || []);

      while (select.options.length > 1) select.remove(1);

      periodos.forEach(function (p) {
        const opt = d.createElement('option');
        opt.value = p.uuid;
        const estadoLabel = p.estado === 'CERRADO' ? ' [Cerrado]' : '';
        opt.textContent = `${p.periodo}${estadoLabel}`;
        opt.dataset.fechaInicio = p.fecha_inicio;
        opt.dataset.fechaFin = p.fecha_fin;
        select.appendChild(opt);
      });
    } catch (err) {
      console.warn(MOD, 'No se pudieron cargar los periodos:', err);
    }
  }

  // ---------------------------------------------------------------------------
  // Consultar / Refrescar (recarga la tabla con los parametros actuales)
  // ---------------------------------------------------------------------------

  function consultar() {
    const periodoUuid = d.getElementById('filter-periodo-libro')?.value || '';
    const fechaInicio = d.getElementById('filter-fecha-inicio-libro')?.value || '';
    const fechaFin = d.getElementById('filter-fecha-fin-libro')?.value || '';

    if (!periodoUuid && (!fechaInicio || !fechaFin)) {
      showFeedback('Seleccione un periodo o ingrese un rango de fechas.', 'warning');
      return;
    }
    if (!periodoUuid && fechaInicio > fechaFin) {
      showFeedback('La fecha inicio debe ser anterior o igual a la fecha fin.', 'danger');
      return;
    }

    hideFeedback();
    consultado = true;
    initTabla();
    setConsultarLoading(true);
    const dt = w.Sintel.Core.DataTablesFactory.get(TABLA_SELECTOR);
    if (dt) {
      dt.ajax.url(_ajaxUrl()).load(function () {
        setConsultarLoading(false);
        const total = (dt.ajax.json() || {}).recordsTotal || 0;
        if (total === 0) {
          showFeedback('No se encontraron asientos para el periodo seleccionado.', 'info');
        }
      });
    } else {
      setConsultarLoading(false);
    }
  }

  function reload() {
    if (!consultado) return;
    const dt = w.Sintel.Core.DataTablesFactory.get(TABLA_SELECTOR);
    if (dt) dt.ajax.url(_ajaxUrl()).load();
  }

  // ---------------------------------------------------------------------------
  // UI helpers
  // ---------------------------------------------------------------------------

  function setConsultarLoading(loading) {
    const btn = d.getElementById('btn-consultar-libro-diario');
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading
      ? '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Cargando...'
      : '<i class="bi bi-search me-1"></i>Consultar';
  }

  function showFeedback(msg, type) {
    const el = d.getElementById('feedback-libro-diario');
    if (!el) return;
    el.className = `alert alert-${type} mb-2`;
    el.textContent = msg;
    el.classList.remove('d-none');
  }

  function hideFeedback() {
    const el = d.getElementById('feedback-libro-diario');
    if (el) el.classList.add('d-none');
  }

  // ---------------------------------------------------------------------------
  // Event listeners
  // ---------------------------------------------------------------------------

  function attachListeners() {
    const btnConsultar = d.getElementById('btn-consultar-libro-diario');
    if (btnConsultar) btnConsultar.addEventListener('click', consultar);

    const btnRefresh = d.getElementById('btn-refrescar-libro-diario');
    if (btnRefresh) btnRefresh.addEventListener('click', consultar);

    // Periodo seleccionado → auto-rellena fechas (informativo -- el dt() ya
    // resuelve periodo_uuid server-side, esto solo sincroniza los inputs).
    const periodoSelect = d.getElementById('filter-periodo-libro');
    if (periodoSelect) {
      periodoSelect.addEventListener('change', function () {
        const opt = this.options[this.selectedIndex];
        const fechaInicio = opt.dataset.fechaInicio || '';
        const fechaFin = opt.dataset.fechaFin || '';
        const elInicio = d.getElementById('filter-fecha-inicio-libro');
        const elFin = d.getElementById('filter-fecha-fin-libro');
        if (elInicio) elInicio.value = fechaInicio;
        if (elFin) elFin.value = fechaFin;
      });
    }

    // Busqueda: nativa de DataTables (columna Numero/Descripcion via
    // search_fields del backend), pero el input viejo (#search-libro-diario)
    // sigue en el HTML -- lo redirigimos a Factory.search().
    const searchInput = d.getElementById('search-libro-diario');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        if (!consultado || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.search(TABLA_SELECTOR, this.value);
      });
    }

    // Estado: recarga del servidor con filtro
    const filterEstado = d.getElementById('filter-estado-libro');
    if (filterEstado) {
      filterEstado.addEventListener('change', function () {
        if (consultado) reload();
      });
    }

    // Ver detalle del asiento — event delegation, sobre document.body (la
    // tabla se recrea via ajax.load(), nunca via innerHTML swap)
    d.body.addEventListener('click', function (ev) {
      if (!ev.target.closest(TABLA_SELECTOR)) return;
      const btn = ev.target.closest('.btn-ver-asiento-libro');
      if (!btn) return;
      ev.preventDefault();
      const uuid = btn.dataset.uuid;
      if (!uuid || typeof htmx === 'undefined') return;
      htmx.ajax('GET', `${ASIENTOS_API_URL}${uuid}/render-offcanvas/detalle/`, {
        target: '#offcanvas-container-libro-diario',
        swap: 'innerHTML',
      }).then(function () {
        const offcanvasEl = d.getElementById('offcanvas-asiento-detalle');
        if (offcanvasEl) {
          w.Sintel?.Core?.mostrarOffcanvasSeguro(offcanvasEl);
        }
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------

  function init() {
    if (!w.DOMUtils || typeof w.DOMUtils.onVisibleOnce !== 'function') {
      console.error(MOD, 'DOMUtils.onVisibleOnce no disponible');
      return;
    }

    w.DOMUtils.onVisibleOnce(TAB_ID, function () {
      attachListeners();
      loadPeriodos();
    });
  }

  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  w.LibroDiarioList = Object.freeze({
    init,
    reload: consultar,
  });
})(window, document);
