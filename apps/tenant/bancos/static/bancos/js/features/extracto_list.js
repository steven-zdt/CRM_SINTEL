// @ts-nocheck — Vanilla JS con namespace global window.Sintel (no TypeScript)
/**
 * extracto_list.js - Controlador de Lista de Extractos Bancarios
 * Namespace: window.Sintel.Bancos.ExtractoList
 * ⚠️ FSD / Vanilla JS
 */
(function (w, d) {
  'use strict';

  const MOD = '[bancos:extracto_list]';
  const GRID_ID = '#grid-extractos';
  const SEARCH_ID = '#search-extracto';
  const API_URL = '/api/v1/bancos/extractos/';
  let table = null;
  let initialized = false;

  const MESES_MAP = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
  };

  function fmtMes(cell) {
    const val = cell.getValue();
    return MESES_MAP[val] || val || '—';
  }

  function getFilename(url) {
    if (!url) return '—';
    try {
      const parts = url.split('/');
      return parts[parts.length - 1];
    } catch (e) {
      return url;
    }
  }

  function getColumns() {
    return [
      {
        title: "Cuenta Bancaria",
        field: "cuenta_nombre",
        formatter: function(cell) {
          const row = cell.getRow().getData();
          const nombre = row.cuenta_nombre || '—';
          const numero = row.cuenta_numero ? `<span class="text-muted small d-block">${row.cuenta_numero}</span>` : '';
          return `<div class="py-1"><span class="fw-semibold">${nombre}</span>${numero}</div>`;
        },
        widthGrow: 2,           // columna flexible principal
        minWidth: 160,
        headerSort: true
      },
      {
        title: "Periodo",
        field: "mes",
        formatter: function(cell) {
          const row = cell.getRow().getData();
          const mesStr = MESES_MAP[row.mes] || '—';
          return `${mesStr} / ${row.anio || '—'}`;
        },
        width: 150,
        headerSort: true
      },
      {
        title: "Archivo",
        field: "archivo_s3",
        formatter: function(cell) {
          const val = cell.getValue();
          if (!val) return '—';
          const name = getFilename(val);
          return `<a href="${val}" target="_blank" class="text-decoration-none small text-truncate d-inline-block" style="max-width: 150px;" title="${name}"><i class="bi bi-file-earmark-excel text-success me-1"></i>${name}</a>`;
        },
        width: 180,
        headerSort: false
      },
      {
        title: "Estado",
        field: "procesado",
        formatter: function(cell) {
          const val = cell.getValue();
          if (val) {
            return `<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Procesado</span>`;
          } else {
            return `<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle me-1"></i>Pendiente</span>`;
          }
        },
        width: 110,
        hozAlign: "center",
        headerSort: true
      },
      {
        title: "Conciliación",
        field: "tx_conciliadas",
        width: 145,
        hozAlign: "center",
        headerSort: false,
        formatter: function(cell) {
          const row   = cell.getRow().getData();
          const total = row.total_transacciones || 0;
          const conc  = row.tx_conciliadas      || 0;
          const pend  = row.tx_pendientes       || 0;

          if (!row.procesado || total === 0) {
            return `<span class="text-muted small">Sin transacciones</span>`;
          }

          const pct   = total > 0 ? Math.round((conc / total) * 100) : 0;
          const color = pct === 100 ? 'bg-success' : pct > 0 ? 'bg-warning' : 'bg-danger';
          const txtColor = pct >= 50 ? 'text-success' : 'text-danger';

          return `
            <div style="font-size:.72rem;line-height:1.2;">
              <div class="d-flex justify-content-between mb-1">
                <span class="fw-semibold ${txtColor}">${conc}/${total}</span>
                ${pend > 0
                  ? `<span class="badge bg-danger" style="font-size:.6rem;">${pend} pendiente${pend > 1 ? 's' : ''}</span>`
                  : `<span class="badge bg-success" style="font-size:.6rem;"><i class="bi bi-check2-all"></i></span>`
                }
              </div>
              <div class="progress" style="height:4px;border-radius:2px;">
                <div class="progress-bar ${color}" style="width:${pct}%;transition:width .3s;"></div>
              </div>
            </div>`;
        }
      },
      {
        title: "Acciones",
        field: "acciones",
        formatter: function(cell) {
          const rowData  = cell.getRow().getData();
          const id       = rowData.uuid || rowData.id;
          const procesado = rowData.procesado;

          let btns = `<div class="btn-group btn-group-sm">`;

          // Ver Detalle
          btns += `<button type="button" class="btn btn-outline-info btn-view-extracto"
                     data-id="${id}" title="Ver Detalle / Conciliar">
                     <i class="bi bi-eye"></i>
                   </button>`;

          // Conciliar (solo si está procesado y tiene pendientes)
          if (procesado && (rowData.tx_pendientes || 0) > 0) {
            btns += `<button type="button" class="btn btn-outline-primary btn-conciliar-extracto"
                       data-id="${id}" title="Conciliar Transacciones (${rowData.tx_pendientes} pendientes)">
                       <i class="bi bi-link-45deg"></i>
                     </button>`;
          }

          // Procesar
          if (!procesado) {
            btns += `<button type="button" class="btn btn-outline-warning btn-procesar-extracto"
                       data-id="${id}" title="Procesar Transacciones">
                       <i class="bi bi-cpu"></i>
                     </button>`;
          }

          // Eliminar
          btns += `<button type="button" class="btn btn-outline-danger btn-delete-extracto"
                     data-id="${id}" title="Eliminar">
                     <i class="bi bi-trash"></i>
                   </button>`;

          btns += `</div>`;
          return btns;
        },
        width: 155,
        headerSort: false,
        hozAlign: "center"
      }
    ];
  }

  function initTable() {
    if (!w.TabulatorFactory) {
      console.error(`${MOD} TabulatorFactory no disponible`);
      return;
    }

    const spinner = d.querySelector('[data-spinner="extractos"]');
    const emptyState = d.querySelector('[data-empty-state="extractos"]');
    const gridEl = d.querySelector(GRID_ID);

    if (spinner) spinner.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (gridEl) gridEl.style.display = 'none';

    table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), {
      searchInputSelector: SEARCH_ID,
      layout: "fitDataFill",    // columnas ajustan al dato, sin desbordar el container
    });

    if (table) {
      table.on("dataLoaded", function (data) {
        if (spinner) spinner.style.display = 'none';
        if (data.length === 0) {
          if (emptyState) emptyState.style.display = 'block';
          if (gridEl) gridEl.style.display = 'none';
        } else {
          if (emptyState) emptyState.style.display = 'none';
          if (gridEl) gridEl.style.display = 'block';
        }
      });
    }
  }

  function init() {
    const gridEl = d.querySelector(GRID_ID);
    if (!gridEl) return;

    if (initialized) {
      refresh();
      return;
    }

    console.log(`${MOD} Inicializando tabla de extractos...`);
    initTable();
    initialized = true;
  }

  function refresh() {
    if (table && typeof table.replaceData === 'function') {
      table.replaceData().catch(err => console.warn(`${MOD} Error al refrescar tabla:`, err));
    }
  }

  // Recalcula dimensiones al mostrar el tab (container oculto al inicializar)
  function redraw() {
    if (table && typeof table.redraw === 'function') {
      table.redraw(true);
    }
  }

  async function procesarExtracto(uuid) {
    if (!uuid) return;
    
    // Show spinner/loader using bootstrap or UIManager
    if (w.UIManager?.showLoading) {
      w.UIManager.showLoading('Procesando extracto bancario...');
    }

    const api = w.Sintel.Bancos.API;
    if (!api || !api.extractos) return;

    const res = await api.extractos.procesar(uuid);

    if (w.UIManager?.hideLoading) {
      w.UIManager.hideLoading();
    }

    if (!res.ok) {
      return w.UIManager?.handleError(res, MOD);
    }

    if (w.UIManager?.showSuccess) {
      w.UIManager.showSuccess('Extracto procesado exitosamente.');
    }

    refresh();
  }

  w.Sintel = w.Sintel || {};
  w.Sintel.Bancos = w.Sintel.Bancos || {};
  w.Sintel.Bancos.ExtractoList = {
    init: init,
    refresh: refresh,
    redraw: redraw,
    procesarExtracto: procesarExtracto
  };

})(window, document);
