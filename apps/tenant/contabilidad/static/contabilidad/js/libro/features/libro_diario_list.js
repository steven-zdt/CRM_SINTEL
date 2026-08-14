/**
 * libro_diario_list.js — Libro Diario Contable v3.7.7
 *
 * Normatividad Colombia: Codigo de Comercio Art. 48 (orden cronologico obligatorio)
 * v3.7.7: Fuente de datos: AsientoContable filtrado por PeriodoContable o rango de fechas.
 *
 * Dependencias: LibroDiarioAPI, TabulatorFactory, DOMUtils.onVisibleOnce, window.bootstrap
 */
(function (w, d) {
  'use strict';

  const MOD = '[libro.diario.list]';
  const TABLE_SELECTOR = '#grid-libro-diario';
  const TAB_ID = '#subtab-libro-diario';
  const PERIODOS_API_URL = '/api/v1/contabilidad/periodos-contables/';
  const ASIENTOS_API_URL = '/api/v1/contabilidad/asientos-contables/';

  let table = null;
  let currentData = [];

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function fmtMoney(val) {
    const n = parseFloat(val) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency', currency: 'COP',
      minimumFractionDigits: 0, maximumFractionDigits: 0,
    }).format(n);
  }

  function fmtFecha(val) {
    if (!val) return '---';
    try { return new Date(val + 'T00:00:00').toLocaleDateString('es-CO'); }
    catch (_) { return val; }
  }

  // ---------------------------------------------------------------------------
  // Columns (aligned with AsientoContableListSerializer)
  // ---------------------------------------------------------------------------

  function getColumns() {
    return [
      {
        title: 'Numero',
        field: 'numero',
        minWidth: 140,
        formatter: function (cell) {
          return `<strong>${cell.getValue() || '---'}</strong>`;
        },
      },
      {
        title: 'Fecha',
        field: 'fecha',
        width: 110,
        sorter: 'date',
        formatter: function (cell) { return fmtFecha(cell.getValue()); },
      },
      {
        title: 'Descripcion',
        field: 'descripcion',
        minWidth: 200,
        formatter: function (cell) {
          const v = cell.getValue() || '---';
          return v.length > 60 ? v.substring(0, 60) + '...' : v;
        },
      },
      {
        title: 'Estado',
        field: 'estado',
        width: 110,
        hozAlign: 'center',
        formatter: function (cell) {
          const v = cell.getValue();
          const map = {
            'BORRADOR': '<span class="badge bg-secondary">Borrador</span>',
            'APROBADO': '<span class="badge bg-success">Aprobado</span>',
            'CERRADO':  '<span class="badge bg-info">Cerrado</span>',
          };
          return map[v] || `<span class="badge bg-light text-dark">${v || '---'}</span>`;
        },
      },
      {
        title: 'Movs.',
        field: 'movimientos_count',
        width: 75,
        hozAlign: 'center',
        formatter: function (cell) {
          const n = parseInt(cell.getValue()) || 0;
          return n > 0
            ? `<span class="badge bg-primary">${n}</span>`
            : '<span class="text-muted">0</span>';
        },
      },
      {
        title: 'Debito',
        field: 'total_debe',
        hozAlign: 'right',
        width: 145,
        sorter: 'number',
        formatter: function (cell) {
          return `<span class="text-primary">${fmtMoney(cell.getValue())}</span>`;
        },
      },
      {
        title: 'Credito',
        field: 'total_haber',
        hozAlign: 'right',
        width: 145,
        sorter: 'number',
        formatter: function (cell) {
          return `<span class="text-danger">${fmtMoney(cell.getValue())}</span>`;
        },
      },
      {
        title: 'Cuadratura',
        field: 'cuadratura',
        width: 110,
        hozAlign: 'center',
        formatter: function (cell) {
          return cell.getValue()
            ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>OK</span>'
            : '<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Error</span>';
        },
      },
      {
        title: '',
        width: 55,
        hozAlign: 'center',
        headerSort: false,
        formatter: function (cell) {
          const row = cell.getRow().getData();
          const uuid = row.uuid || '';
          if (!uuid) return '';
          return `<button class="btn btn-sm btn-outline-secondary btn-ver-asiento-libro"
                    data-uuid="${uuid}" title="Ver detalle del asiento">
                    <i class="bi bi-eye"></i>
                  </button>`;
        },
      },
    ];
  }

  // ---------------------------------------------------------------------------
  // Table init
  // ---------------------------------------------------------------------------

  function initTable() {
    if (!w.TabulatorFactory) { console.error(MOD, 'TabulatorFactory no disponible'); return null; }
    const el = d.querySelector(TABLE_SELECTOR);
    if (!el) { console.error(MOD, 'Elemento no encontrado:', TABLE_SELECTOR); return null; }

    // Tabla con datos locales (setData). La request AJAX inicial devuelve [] (sin params).
    return w.TabulatorFactory.create(TABLE_SELECTOR, '/api/v1/contabilidad/libro-diario/', getColumns(), {
      paginationSize: 25,
      paginationSizeSelector: [10, 25, 50, 100],
      placeholder: 'Seleccione un periodo y haga clic en Consultar.',
    });
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

      // Clear existing options (keep placeholder)
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
  // Data loading
  // ---------------------------------------------------------------------------

  async function loadData() {
    const periodoSelect = d.getElementById('filter-periodo-libro');
    const periodoUuid   = periodoSelect ? periodoSelect.value : '';
    const fechaInicio   = d.getElementById('filter-fecha-inicio-libro')?.value || '';
    const fechaFin      = d.getElementById('filter-fecha-fin-libro')?.value || '';
    const estado        = d.getElementById('filter-estado-libro')?.value || '';

    if (!periodoUuid && (!fechaInicio || !fechaFin)) {
      showFeedback('Seleccione un periodo o ingrese un rango de fechas.', 'warning');
      return;
    }
    if (!periodoUuid && fechaInicio > fechaFin) {
      showFeedback('La fecha inicio debe ser anterior o igual a la fecha fin.', 'danger');
      return;
    }
    if (!w.LibroDiarioAPI) {
      showFeedback('Modulo API no disponible. Recargue la pagina.', 'danger');
      return;
    }

    setConsultarLoading(true);
    try {
      const params = {};
      if (periodoUuid) {
        params.periodo_uuid = periodoUuid;
      } else {
        params.fecha_inicio = fechaInicio;
        params.fecha_fin = fechaFin;
      }
      if (estado) params.estado = estado;

      const data = await w.LibroDiarioAPI.list(params);
      currentData = Array.isArray(data) ? data : [];
      if (table) table.setData(currentData);
      applySearchFilter();
      updateResumen(currentData);
      hideFeedback();

      if (currentData.length === 0) {
        showFeedback('No se encontraron asientos para el periodo seleccionado.', 'info');
      }
    } catch (err) {
      console.error(MOD, err);
      showFeedback('Error al cargar el Libro Diario: ' + (err.message || 'Error desconocido'), 'danger');
    } finally {
      setConsultarLoading(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Client-side search filter (applies on currentData already loaded)
  // ---------------------------------------------------------------------------

  function applySearchFilter() {
    if (!table) return;
    const search = (d.getElementById('search-libro-diario')?.value || '').trim().toLowerCase();
    if (!search) {
      table.clearFilter(false);
      return;
    }
    table.setFilter(function (rowData) {
      return (rowData.numero || '').toLowerCase().includes(search) ||
             (rowData.descripcion || '').toLowerCase().includes(search);
    });
  }

  // ---------------------------------------------------------------------------
  // Summary panel
  // ---------------------------------------------------------------------------

  function updateResumen(data) {
    const el = d.getElementById('resumen-libro-diario');
    if (!el) return;

    const total      = data.length;
    const cuadrados  = data.filter(function (r) { return r.cuadratura === true; }).length;
    const descuadre  = data.filter(function (r) { return r.cuadratura === false; }).length;

    let totalDebe  = 0;
    let totalHaber = 0;
    data.forEach(function (r) {
      totalDebe  += parseFloat(r.total_debe)  || 0;
      totalHaber += parseFloat(r.total_haber) || 0;
    });
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
    // Consultar
    const btnConsultar = d.getElementById('btn-consultar-libro-diario');
    if (btnConsultar) btnConsultar.addEventListener('click', loadData);

    // Refrescar
    const btnRefresh = d.getElementById('btn-refrescar-libro-diario');
    if (btnRefresh) btnRefresh.addEventListener('click', loadData);

    // Periodo seleccionado → auto-rellena fechas
    const periodoSelect = d.getElementById('filter-periodo-libro');
    if (periodoSelect) {
      periodoSelect.addEventListener('change', function () {
        const opt = this.options[this.selectedIndex];
        const fechaInicio = opt.dataset.fechaInicio || '';
        const fechaFin    = opt.dataset.fechaFin    || '';
        const elInicio = d.getElementById('filter-fecha-inicio-libro');
        const elFin    = d.getElementById('filter-fecha-fin-libro');
        if (elInicio) elInicio.value = fechaInicio;
        if (elFin)    elFin.value    = fechaFin;
      });
    }

    // Busqueda client-side (sobre datos ya cargados)
    const searchInput = d.getElementById('search-libro-diario');
    if (searchInput) {
      searchInput.addEventListener('input', applySearchFilter);
    }

    // Estado: recarga del servidor con filtro
    const filterEstado = d.getElementById('filter-estado-libro');
    if (filterEstado) {
      filterEstado.addEventListener('change', function () {
        if (currentData.length > 0) {
          // Si ya hay datos cargados, recarga con el filtro nuevo
          loadData();
        }
      });
    }

    // Ver detalle del asiento — event delegation
    d.addEventListener('click', function (ev) {
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
      table = initTable();
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
    reload: function () { if (table) loadData(); else init(); },
    getTable: function () { return table; },
  });
})(window, document);
