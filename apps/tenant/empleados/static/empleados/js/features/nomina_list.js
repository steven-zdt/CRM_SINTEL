// @ts-nocheck
/**
 * Nomina List Module — Master-Detail v4.8.0
 *
 * Panel Izquierdo (Master): Empleados con nominas, ordenados por cantidad DESC.
 * Panel Derecho (Detail):  Historico de nominas del empleado seleccionado.
 *
 * Namespace: window.Sintel.Empleados.NominaList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[NominaList]';

    // ── Estado interno ─────────────────────────────────────────────────────────
    let masterTable  = null;
    let detailTable  = null;
    let empleadoActivo = null;   // { uuid, nombre }

    // ── Helpers ────────────────────────────────────────────────────────────────

    const COP = (val) => {
        const n = parseFloat(val) || 0;
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP', minimumFractionDigits: 0
        }).format(n);
    };

    function _getAuthHeaders() {
        const headers = { 'Accept': 'application/json' };
        const token = w.jwtAuth?.getAccessToken?.();
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    }

    // ── Columnas Master ────────────────────────────────────────────────────────

    function getColumnasMaster() {
        return [
            {
                title: 'Empleado',
                field: 'empleado_nombre',
                headerSort: false,
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const nom  = cell.getValue() || '—';
                    const doc  = data.empleado_documento || '';
                    const cnt  = parseInt(data.total_nominas) || 0;
                    return `<div class="d-flex align-items-start justify-content-between gap-1 py-1">
                                <div class="lh-sm">
                                    <div class="fw-semibold small">${nom}</div>
                                    <div class="text-muted" style="font-size:.72rem;"><code>${doc}</code></div>
                                </div>
                                <span class="badge bg-primary-subtle text-primary border border-primary-subtle flex-shrink-0 mt-1">
                                    ${cnt}
                                </span>
                            </div>`;
                },
            },
        ];
    }

    // ── Columnas Detail ────────────────────────────────────────────────────────

    function getColumnasDetail() {
        return [
            {
                title: 'Período',
                field: 'fecha_inicio',
                width: 190,
                hozAlign: 'center',
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const fi = data.fecha_inicio;
                    const ff = data.fecha_fin;
                    if (fi && ff) {
                        return `<div class="small lh-sm fw-semibold">${fi}</div>
                                <div class="small text-muted lh-sm">al ${ff}</div>`;
                    }
                    return `<span class="small">${data.periodo_mes || '—'}</span>`;
                },
            },
            {
                title: 'Días',
                field: 'dias_laborados',
                width: 65,
                hozAlign: 'center',
                formatter: (cell) => {
                    const v = parseFloat(cell.getValue()) || 0;
                    return `<span class="badge bg-primary-subtle text-primary border border-primary-subtle">${v}</span>`;
                },
            },
            {
                title: 'Fecha Pago',
                field: 'fecha_pago',
                width: 130,
                hozAlign: 'center',
                formatter: (cell) => {
                    const val = cell.getValue();
                    return val ? new Date(val + 'T00:00:00').toLocaleDateString('es-CO') : '—';
                },
            },
            {
                title: 'Salario Base',
                field: 'salario_base',
                width: 150,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: (cell) => COP(cell.getValue()),
            },
            {
                title: 'H.E. y Recargos',
                field: 'valor_horas_extras',
                width: 130,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: (cell) => {
                    const v = parseFloat(cell.getValue()) || 0;
                    return v > 0
                        ? `<span class="text-warning fw-semibold">${COP(v)}</span>`
                        : '<span class="text-muted">—</span>';
                },
            },
            {
                title: 'Neto a Pagar',
                field: 'neto_pagar',
                width: 150,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: (cell) => {
                    const data    = cell.getRow().getData();
                    const anulado = data.anulado;
                    if (anulado) {
                        return `<span class="text-decoration-line-through text-muted small">${COP(cell.getValue())}</span>
                                <span class="badge bg-danger ms-1">Anulada</span>`;
                    }
                    return `<strong class="text-success">${COP(cell.getValue())}</strong>`;
                },
            },
            {
                title: 'Estado',
                field: 'anulado',
                width: 90,
                hozAlign: 'center',
                formatter: (cell) => cell.getValue()
                    ? '<span class="badge bg-danger">Anulado</span>'
                    : '<span class="badge bg-success">Activo</span>',
            },
            {
                title: 'Acción',
                width: 80,
                hozAlign: 'center',
                headerSort: false,
                frozen: true,
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    if (data.anulado) return '<span class="text-muted">—</span>';
                    return `<button class="btn btn-sm btn-outline-danger"
                                    onclick="window.Sintel.Empleados.NominaList.anularDevengo('${data.uuid}')"
                                    title="Anular nómina">
                                <i class="bi bi-slash-circle"></i>
                            </button>`;
                },
            },
        ];
    }

    // ── Seleccionar empleado (rowClick) ────────────────────────────────────────

    function _seleccionarEmpleado(e, row) {
        const data = row.getData();
        const uuid = data.empleado_uuid;
        const nombre = data.empleado_nombre || 'Empleado';

        if (empleadoActivo?.uuid === uuid) return;  // no recargar si ya estaba

        empleadoActivo = { uuid, nombre };

        // Destacar fila activa visualmente
        masterTable?.getRows().forEach(r => r.getElement().classList.remove('table-active', 'fw-bold'));
        row.getElement().classList.add('table-active', 'fw-bold');

        // Actualizar header del panel derecho
        const header = d.getElementById('nomina-detail-header');
        if (header) {
            header.innerHTML = `<i class="bi bi-person-check-fill me-1 text-primary"></i>
                                <strong>${nombre}</strong>
                                <span class="text-muted ms-2 fw-normal">(${data.total_nominas} nómina${data.total_nominas !== 1 ? 's' : ''})</span>`;
        }

        // Mostrar grid, ocultar placeholder
        const placeholder = d.getElementById('nomina-detail-placeholder');
        const detailGrid  = d.getElementById('nomina-detail-grid');
        if (placeholder) placeholder.style.display = 'none';
        if (detailGrid)  detailGrid.style.display  = '';

        // Habilitar botón "Nueva Nómina"
        const btn = d.getElementById('btn-nueva-nomina');
        if (btn) {
            btn.classList.remove('disabled');
            btn.removeAttribute('disabled');
            btn.title = `Registrar nómina para ${nombre}`;
            btn.setAttribute('data-empleado-uuid', uuid);
        }

        // Cargar / actualizar tabla Detail
        _cargarDetalle(uuid);
    }

    // ── Inicializar / recargar tabla Detail ────────────────────────────────────

    function _cargarDetalle(uuid) {
        const url = `/api/v1/empleados/devengos/?empleado_uuid=${encodeURIComponent(uuid)}`;

        if (detailTable) {
            detailTable.replaceData(url);
            return;
        }

        const el = d.getElementById('nomina-detail-grid');
        if (!el) return;

        detailTable = new Tabulator(el, {
            ajaxURL: url,
            ajaxConfig: { headers: _getAuthHeaders() },
            ajaxResponse: function (reqUrl, params, response) {
                // Unwrap paginación DRF {count, results} — fix DEUDA-23
                return response.results || response;
            },
            layout: 'fitDataFill',
            pagination: 'local',
            paginationSize: 15,
            paginationSizeSelector: [10, 15, 25, 50],
            columns: getColumnasDetail(),
            locale: 'es-co',
            langs: {
                'es-co': {
                    pagination: { first: '«', prev: '‹', next: '›', last: '»' }
                }
            },
            placeholder: '<div class="text-center text-muted py-4"><i class="bi bi-inbox fs-3"></i><p class="mt-2 small">Sin nóminas para este empleado</p></div>',
        });
    }

    // ── Inicializar tabla Master ───────────────────────────────────────────────

    function _inicializarMaster() {
        const el = d.getElementById('nomina-master-grid');
        if (!el) {
            console.warn(`${MOD} #nomina-master-grid no encontrado`);
            return;
        }
        if (masterTable) return;

        masterTable = new Tabulator(el, {
            ajaxURL: '/api/v1/empleados/devengos/empleados-con-nominas/',
            ajaxConfig: { headers: _getAuthHeaders() },
            ajaxResponse: function (url, params, response) {
                // Unwrap DRF pagination
                return response.results || response;
            },
            layout: 'fitColumns',
            columns: getColumnasMaster(),
            locale: 'es-co',
            langs: {
                'es-co': {
                    pagination: { first: '«', prev: '‹', next: '›', last: '»' }
                }
            },
            placeholder: '<div class="text-center text-muted py-4 small"><i class="bi bi-people fs-3"></i><p class="mt-2">Sin empleados con nóminas</p></div>',
            rowFormatter: (row) => {
                row.getElement().style.cursor = 'pointer';
            },
        });

        // Tabulator 6: el evento rowClick se registra con .on(), no como propiedad de config
        masterTable.on('rowClick', _seleccionarEmpleado);

        // Búsqueda con debounce en el Master
        const searchEl = d.getElementById('search-nomina-master');
        if (searchEl) {
            let debounce;
            searchEl.addEventListener('input', () => {
                clearTimeout(debounce);
                debounce = setTimeout(() => {
                    const q = searchEl.value.trim();
                    const url = `/api/v1/empleados/devengos/empleados-con-nominas/${q ? '?search=' + encodeURIComponent(q) : ''}`;
                    masterTable?.replaceData(url);
                }, 350);
            });
        }
    }

    // ── Anular nómina (acción Detail) ─────────────────────────────────────────

    async function anularDevengo(uuid) {
        if (!uuid) return;
        if (!confirm('¿Confirma anular esta nómina? La operación no puede revertirse.')) return;
        try {
            const resp = await w.http('POST', `/api/v1/empleados/devengos/${uuid}/anular/`);
            if (resp.ok) {
                w.UIManager?.notifySuccess('Nómina anulada correctamente');
                detailTable?.replaceData();
                masterTable?.replaceData();
            } else {
                w.UIManager?.handleError(resp);
            }
        } catch (err) {
            console.error(`${MOD} Error anulando:`, err);
            w.UIManager?.notifyError('Error al anular la nómina');
        }
    }

    // ── Inicialización ────────────────────────────────────────────────────────

    function init() {
        _inicializarMaster();
    }

    function reload() {
        masterTable?.replaceData();
        if (empleadoActivo) detailTable?.replaceData();
    }

    function redraw() {
        masterTable?.redraw(true);
        detailTable?.redraw(true);
    }

    // ── Export ────────────────────────────────────────────────────────────────

    w.Sintel.Empleados.NominaList = { init, reload, redraw, anularDevengo };

})(window, document);
