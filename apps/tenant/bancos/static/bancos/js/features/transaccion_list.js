// @ts-nocheck
/**
 * transaccion_list.js — Tabla de Transacciones Bancarias con Conciliación
 * Namespace: window.Sintel.Bancos.TransaccionList
 * Patrón Master-Detail: extracto → transacciones con filtros y conciliación inline
 */
(function (w, d) {
  'use strict';

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};

  const MOD = '[transaccion_list]';
  const GRID_ID = '#grid-transacciones';
  const SEARCH_ID = '#search-transaccion';
  const FILTRO_MOVIMIENTO_ID = '#filtro-tipo-movimiento';
  const FILTRO_CONCILIADO_ID = '#filtro-conciliado';
  const API_URL = '/api/v1/bancos/transacciones/';
  let table = null;
  let extractoUuidActual = null;

  // Formatters utilitarios
  const COP = (val) => {
    const n = parseFloat(val) || 0;
    return new Intl.NumberFormat('es-CO', {
      style: 'currency', currency: 'COP', minimumFractionDigits: 0,
    }).format(n);
  };

  function fmtValor(cell) {
    const val = parseFloat(cell.getValue()) || 0;
    const prefix = val >= 0 ? '+' : '';
    const cls = val >= 0 ? 'text-success' : 'text-danger';
    return `<span class="${cls} fw-semibold font-monospace">${prefix}${COP(val)}</span>`;
  }

  function fmtTipoMovimiento(cell) {
    const tipo = cell.getValue();
    if (tipo === 'DEBITO') {
      return '<span class="badge bg-danger" style="font-size:.65rem;"><i class="bi bi-arrow-down me-1"></i>Egreso</span>';
    }
    return '<span class="badge bg-success" style="font-size:.65rem;"><i class="bi bi-arrow-up me-1"></i>Ingreso</span>';
  }

  function fmtConciliacion(cell) {
    const row = cell.getRow().getData();
    const display = row.conciliacion_display || 'No conciliado';
    const conciliado = row.conciliado;
    const cls = conciliado ? 'bg-info' : 'bg-warning text-dark';
    return `<span class="badge ${cls}" style="font-size:.65rem;"><i class="bi ${conciliado ? 'bi-check2-all' : 'bi-exclamation-lg'} me-1"></i>${display}</span>`;
  }

  function getColumnas() {
    return [
      {
        title: 'Fecha',
        field: 'fecha',
        width: 95,
        formatter: (cell) => `<span class="font-monospace small">${cell.getValue()}</span>`,
        headerSort: true,
      },
      {
        title: 'Descripción',
        field: 'descripcion',
        widthGrow: 3,
        minWidth: 200,
        formatter: (cell) => {
          const v = cell.getValue() || '—';
          const row = cell.getRow().getData();
          const dcto = row.dcto ? `<div class="small text-muted">Doc: ${row.dcto}</div>` : '';
          return `<div class="text-truncate fw-semibold">${v}</div>${dcto}`;
        },
        headerSort: true,
      },
      {
        title: 'Tipo',
        field: 'tipo_movimiento',
        width: 110,
        hozAlign: 'center',
        formatter: fmtTipoMovimiento,
        headerSort: true,
      },
      {
        title: 'Valor',
        field: 'valor',
        width: 140,
        hozAlign: 'right',
        formatter: fmtValor,
        headerSort: true,
      },
      {
        title: 'Saldo',
        field: 'saldo',
        width: 140,
        hozAlign: 'right',
        formatter: (cell) => `<span class="font-monospace small">${COP(cell.getValue())}</span>`,
        headerSort: true,
      },
      {
        title: 'Conciliación',
        field: 'conciliacion_display',
        width: 160,
        hozAlign: 'center',
        formatter: fmtConciliacion,
        headerSort: true,
      },
      {
        title: '',
        width: 80,
        hozAlign: 'center',
        headerSort: false,
        formatter(cell) {
          const uuid = cell.getRow().getData().uuid;
          return `<button class="btn btn-outline-primary btn-sm py-0 px-2"
                    data-action="conciliar" data-uuid="${uuid}" title="Conciliar">
            <i class="bi bi-link-45deg"></i>
          </button>`;
        },
        cellClick(e, cell) {
          const btn = e.target.closest('[data-action="conciliar"]');
          if (!btn) return;
          const uuid = btn.dataset.uuid;
          _abrirConciliacion(uuid);
        },
      },
    ];
  }

  function _abrirConciliacion(uuid) {
    // Abrir modal/offcanvas de conciliación
    const modalId = `modal-conciliar-${uuid}`;
    let modal = d.getElementById(modalId);
    if (!modal) {
      modal = d.createElement('div');
      modal.id = modalId;
      modal.className = 'modal fade';
      modal.innerHTML = _renderModalConciliacion(uuid);
      d.body.appendChild(modal);
    }
    const instance = new bootstrap.Modal(modal);
    instance.show();
  }

  function _renderModalConciliacion(uuid) {
    return `
<div class="modal-dialog modal-lg">
  <div class="modal-content">
    <div class="modal-header bg-primary text-white">
      <h5 class="modal-title">Conciliar Transacción</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
    </div>
    <div class="modal-body">
      <div class="mb-3">
        <label class="form-label">Vincular a Factura (opcional)</label>
        <input type="text" class="form-control" id="search-factura-${uuid}"
               placeholder="Buscar factura por número o cliente..." autocomplete="off">
        <input type="hidden" id="factura-uuid-${uuid}" value="">
        <div id="suggestions-factura-${uuid}" class="list-group mt-2 d-none position-absolute" style="width:100%;z-index:1050;"></div>
      </div>
      <div class="mb-3">
        <label class="form-label">Vincular a Proveedor (opcional)</label>
        <input type="text" class="form-control" id="search-proveedor-${uuid}"
               placeholder="Buscar proveedor por NIT o nombre..." autocomplete="off">
        <input type="hidden" id="proveedor-uuid-${uuid}" value="">
        <div id="suggestions-proveedor-${uuid}" class="list-group mt-2 d-none position-absolute" style="width:100%;z-index:1050;"></div>
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
      <button type="button" class="btn btn-primary" id="btn-guardar-conciliar-${uuid}">Guardar</button>
    </div>
  </div>
</div>`;
  }

  function init(extractoUuid) {
    if (table) table.destroy();
    extractoUuidActual = extractoUuid;

    if (!w.TabulatorFactory) {
      setTimeout(() => init(extractoUuid), 200);
      return;
    }

    // URL con extracto_uuid
    const url = `${API_URL}?extracto_uuid=${extractoUuid}`;

    table = w.TabulatorFactory.create(
      GRID_ID,
      url,
      getColumnas(),
      {
        searchInputSelector: SEARCH_ID,
        ajaxResponse: function(url, params, response) {
          return response.results || response;
        },
      }
    );

    // Listeners para filtros
    const btnTipoMovimiento = d.getElementById('btn-filtro-ingresos');
    const btnEgresos = d.getElementById('btn-filtro-egresos');
    const btnTodos = d.getElementById('btn-filtro-todos-movimientos');

    if (btnTipoMovimiento || btnEgresos || btnTodos) {
      [btnTipoMovimiento, btnEgresos, btnTodos].forEach((btn) => {
        if (!btn) return;
        btn.addEventListener('click', (e) => {
          d.querySelectorAll('[data-filtro-movimiento]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const filtro = btn.dataset.filtroMovimiento;
          if (filtro === 'TODOS') {
            table.setFilter([]);
          } else {
            table.setFilter('tipo_movimiento', '==', filtro);
          }
        });
      });
    }

    const btnConciliados = d.getElementById('btn-filtro-conciliados');
    const btnNoConc = d.getElementById('btn-filtro-no-conciliados');
    const btnTodosCo = d.getElementById('btn-filtro-todos-conciliacion');

    if (btnConciliados || btnNoConc || btnTodosCo) {
      [btnConciliados, btnNoConc, btnTodosCo].forEach((btn) => {
        if (!btn) return;
        btn.addEventListener('click', (e) => {
          d.querySelectorAll('[data-filtro-conciliacion]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const filtro = btn.dataset.filtroConciliacion;
          if (filtro === 'TODOS') {
            table.setFilter([]);
          } else {
            table.setFilter('conciliado', '==', filtro === 'true');
          }
        });
      });
    }
  }

  function reload() {
    if (table && extractoUuidActual) {
      const url = `${API_URL}?extracto_uuid=${extractoUuidActual}`;
      table.replaceData(url);
    }
  }

  w.Sintel.Bancos.TransaccionList = { init, reload };

})(window, document);
