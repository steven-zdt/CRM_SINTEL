// @ts-nocheck
/**
 * Liquidacion List Module — Master-Detail: Empleados con Historial de Liquidaciones
 * Namespace: window.Sintel.Empleados.LiquidacionList
 * Architecture: Master panel (empleados) + Detail panel (historial por empleado)
 * Sintel v4.6.0 — FSD, Zero-Trust, Tabulator, HTMX
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[LiquidacionList]';
    const API_BASE       = '/api/v1/empleados/liquidaciones-prestaciones/';
    const API_EMPLEADOS  = `${API_BASE}empleados-con-liquidaciones/`;

    // ── State ──────────────────────────────────────────────────────────────────
    let tablaMaster  = null;    // Tabulator: lista de empleados
    let tablaDetail  = null;    // Tabulator: historial liquidaciones del empleado
    let empleadoActivo = null;  // { uuid, nombre_completo }
    let filtroTipo   = '';

    // ── Formatters utilitarios ─────────────────────────────────────────────────
    const COP = (val) => {
        const n = parseFloat(val) || 0;
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP', minimumFractionDigits: 0,
        }).format(n);
    };

    const TIPO_BADGES = {
        PRIMA_SERVICIOS:        ['bg-info text-dark',    'bi-award',              'Prima'],
        CESANTIAS:              ['bg-warning text-dark', 'bi-piggy-bank',         'Cesantias'],
        VACACIONES:             ['bg-success',           'bi-sun',                'Vacaciones'],
        LIQUIDACION_DEFINITIVA: ['bg-danger',            'bi-file-earmark-break', 'Liquidacion'],
    };

    function _badgeTipo(raw) {
        const [cls, ico, lbl] = TIPO_BADGES[raw] || ['bg-secondary', 'bi-calculator', raw || '-'];
        return `<span class="badge ${cls}" style="font-size:.68rem;"><i class="bi ${ico} me-1"></i>${lbl}</span>`;
    }

    function _badgeEstado(val) {
        return val === 'PAGADO'
            ? '<span class="badge bg-success" style="font-size:.68rem;"><i class="bi bi-check2-all me-1"></i>Pagado</span>'
            : '<span class="badge bg-warning text-dark" style="font-size:.68rem;"><i class="bi bi-hourglass-split me-1"></i>Proyectado</span>';
    }

    // ── Columnas Master (Empleados) ────────────────────────────────────────────
    function _columnasMaster() {
        return [
            {
                title: 'Empleado',
                field: 'nombre_completo',
                widthGrow: 3,
                formatter(cell) {
                    const row  = cell.getRow().getData();
                    const n    = row.nombre_completo || '-';
                    const doc  = row.numero_documento ? `<div class="text-muted" style="font-size:.68rem;">${row.numero_documento}</div>` : '';
                    const isAct = empleadoActivo && empleadoActivo.uuid === row.uuid;
                    const cls  = isAct ? 'fw-bold text-primary' : 'fw-semibold';
                    return `<div class="${cls} text-truncate" title="${n}"><i class="bi bi-person-fill text-info me-1"></i>${n}</div>${doc}`;
                },
            },
            {
                title: 'Liq.',
                field: 'total_liquidaciones',
                width: 58,
                hozAlign: 'center',
                formatter(cell) {
                    const v = parseInt(cell.getValue(), 10) || 0;
                    const cls = v > 0 ? 'bg-primary' : 'bg-secondary';
                    return `<span class="badge ${cls}" style="font-size:.7rem;">${v}</span>`;
                },
            },
        ];
    }

    // ── Columnas Detail (Historial liquidaciones del empleado) ─────────────────
    function _columnasDetail() {
        return [
            {
                title: 'Tipo',
                field: 'tipo_liquidacion',
                width: 120,
                hozAlign: 'center',
                formatter: (cell) => _badgeTipo(cell.getValue()),
            },
            {
                title: 'Corte',
                field: 'fecha_corte',
                width: 95,
                hozAlign: 'center',
                formatter(cell) {
                    const v = cell.getValue();
                    if (!v) return '-';
                    return `<span class="font-monospace small">${new Date(v + 'T00:00').toLocaleDateString('es-CO', {day:'2-digit', month:'short', year:'2-digit'})}</span>`;
                },
            },
            {
                title: 'Base Salarial',
                field: 'base_salarial',
                width: 120,
                hozAlign: 'right',
                formatter: (cell) => `<span class="font-monospace small text-muted">${COP(cell.getValue())}</span>`,
            },
            {
                title: 'Total',
                field: 'valor_total',
                width: 130,
                hozAlign: 'right',
                formatter: (cell) => `<span class="font-monospace fw-bold text-success">${COP(cell.getValue())}</span>`,
            },
            {
                title: 'Estado',
                field: 'estado',
                width: 100,
                hozAlign: 'center',
                formatter: (cell) => _badgeEstado(cell.getValue()),
            },
            {
                title: '',
                width: 115,
                hozAlign: 'center',
                headerSort: false,
                formatter(cell) {
                    const uuid = cell.getRow().getData().uuid;
                    return `<div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary py-0 px-2" data-action="ver-liq" data-uuid="${uuid}" title="Ver liquidacion">
                            <i class="bi bi-eye"></i>
                        </button>
                        <a class="btn btn-outline-danger py-0 px-2" href="${API_BASE}${uuid}/pdf/" target="_blank" title="PDF">
                            <i class="bi bi-file-earmark-pdf"></i>
                        </a>
                        <button class="btn btn-outline-secondary py-0 px-2" data-action="del-liq" data-uuid="${uuid}" title="Eliminar">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>`;
                },
                cellClick(e, cell) {
                    const btn = e.target.closest('[data-action]');
                    if (!btn) return;
                    const action = btn.dataset.action;
                    const uuid   = btn.dataset.uuid;
                    if (action === 'ver-liq') {
                        _abrirDetalleLiquidacion(uuid);
                    } else if (action === 'del-liq') {
                        if (!confirm('Eliminar esta liquidacion? Esta accion no se puede deshacer.')) return;
                        _eliminarLiquidacion(uuid);
                    }
                },
            },
        ];
    }

    // ── Abrir offcanvas de detalle (solo lectura) ──────────────────────────────
    function _abrirDetalleLiquidacion(uuid) {
        const url = `${API_BASE}${uuid}/render-offcanvas/detalle/`;
        const container = d.getElementById('offcanvas-container-liquidaciones');
        if (!container) {
            console.error(`${MOD} No se encontro #offcanvas-container-liquidaciones`);
            return;
        }
        htmx.ajax('GET', url, { target: container, swap: 'innerHTML' }).then(() => {
            const el = container.querySelector('.offcanvas');
            if (el) {
                const inst = bootstrap.Offcanvas.getOrCreateInstance(el);
                inst.show();
            }
        });
    }

    // ── Eliminar liquidacion ───────────────────────────────────────────────────
    async function _eliminarLiquidacion(uuid) {
        try {
            const res = await w.http('DELETE', `${API_BASE}${uuid}/`);
            if (res.ok) {
                w.UIManager?.notifySuccess('Liquidacion eliminada');
                _recargarDetail();
                _recargarMaster();
            } else {
                w.UIManager?.notifyError(res.data?.detail || 'Error al eliminar');
            }
        } catch (err) {
            console.error(`${MOD} Error al eliminar:`, err);
            w.UIManager?.notifyError('Error de conexion');
        }
    }

    // ── Inicializar panel Master ───────────────────────────────────────────────
    function _initMaster() {
        const el = d.getElementById('liq-master-grid');
        if (!el || tablaMaster) return;

        if (!w.Tabulator) {
            setTimeout(_initMaster, 200);
            return;
        }

        tablaMaster = new w.Tabulator('#liq-master-grid', {
            ajaxURL: API_EMPLEADOS,
            ajaxConfig: {
                method: 'GET',
                headers: _getHeaders(),
            },
            ajaxResponse: function (url, params, response) {
                // Desenvuelve paginacion DRF {count, results} o retorna array directo
                return Array.isArray(response) ? response : (response.results || []);
            },
            layout: 'fitColumns',
            height: '100%',
            placeholder: 'No hay empleados registrados',
            columns: _columnasMaster(),
            rowHeight: 48,
            initialSort: [{ column: 'total_liquidaciones', dir: 'desc' }],
        });

        tablaMaster.on('rowClick', function (e, row) {
            const data = row.getData();
            _seleccionarEmpleado(data);
        });

        // Busqueda local en master
        const searchEl = d.getElementById('search-liq-empleado');
        if (searchEl) {
            searchEl.addEventListener('input', function () {
                const q = this.value.trim().toLowerCase();
                if (!tablaMaster) return;
                if (q) {
                    tablaMaster.setFilter([
                        [
                            { field: 'nombre_completo', type: 'like', value: q },
                            { field: 'numero_documento', type: 'like', value: q },
                        ]
                    ]);
                } else {
                    tablaMaster.clearFilter();
                }
            });
        }
    }

    // ── Seleccionar empleado y cargar su historial ─────────────────────────────
    function _seleccionarEmpleado(data) {
        empleadoActivo = { uuid: data.uuid, nombre: data.nombre_completo };

        // Actualizar cabecera del panel detail
        const titleEl = d.getElementById('liq-detail-title');
        if (titleEl) titleEl.textContent = data.nombre_completo || 'Empleado';

        const subtitleEl = d.getElementById('liq-detail-subtitle');
        if (subtitleEl) {
            subtitleEl.textContent = data.numero_documento
                ? `Doc: ${data.numero_documento} — ${data.total_liquidaciones} liquidacion(es)`
                : `${data.total_liquidaciones} liquidacion(es)`;
        }

        // Mostrar panel detail
        const detailPanel = d.getElementById('liq-detail-panel');
        const placeholder = d.getElementById('liq-detail-placeholder');
        if (detailPanel) detailPanel.style.display = 'flex';
        if (placeholder) placeholder.style.display = 'none';

        // Resaltar fila en master
        if (tablaMaster) tablaMaster.redraw(true);

        // Actualizar btn "Nueva Liquidacion" con el empleado seleccionado
        const btnNueva = d.getElementById('btn-nueva-liquidacion');
        if (btnNueva) {
            btnNueva.dataset.empleadoUuid = data.uuid;
            btnNueva.disabled = false;
        }

        // Inicializar o recargar detail grid
        if (!tablaDetail) {
            _initDetail();
        } else {
            _recargarDetail();
        }
    }

    // ── Inicializar panel Detail ───────────────────────────────────────────────
    function _initDetail() {
        const el = d.getElementById('liq-detail-grid');
        if (!el || !empleadoActivo) return;

        if (!w.Tabulator) {
            setTimeout(_initDetail, 200);
            return;
        }

        const url = _buildDetailUrl();

        tablaDetail = new w.Tabulator('#liq-detail-grid', {
            ajaxURL: url,
            ajaxConfig: {
                method: 'GET',
                headers: _getHeaders(),
            },
            ajaxResponse: function (url, params, response) {
                // Desenvuelve paginacion DRF {count, results} o retorna array directo
                return Array.isArray(response) ? response : (response.results || []);
            },
            layout: 'fitColumns',
            height: '100%',
            placeholder: 'Sin liquidaciones para este empleado',
            columns: _columnasDetail(),
            rowHeight: 48,
            initialSort: [{ column: 'fecha_corte', dir: 'desc' }],
        });

        // Filtros tipo
        _bindFiltrosTipo();
    }

    // ── Reload helpers ─────────────────────────────────────────────────────────
    function _recargarMaster() {
        if (tablaMaster) tablaMaster.replaceData(API_EMPLEADOS, {}, { headers: _getHeaders() });
    }

    function _recargarDetail() {
        if (!tablaDetail || !empleadoActivo) return;
        tablaDetail.replaceData(_buildDetailUrl(), {}, { headers: _getHeaders() });
    }

    function _buildDetailUrl() {
        const base = `${API_BASE}?empleado_uuid=${empleadoActivo.uuid}`;
        return filtroTipo ? `${base}&tipo_liquidacion=${filtroTipo}` : base;
    }

    // ── Headers JWT ────────────────────────────────────────────────────────────
    function _getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const token = w.jwtAuth?.getAccessToken?.();
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    }

    // ── Filtros rapidos por tipo ───────────────────────────────────────────────
    function _bindFiltrosTipo() {
        const container = d.getElementById('filtros-tipo-liquidacion');
        if (!container || container.dataset.bound) return;
        container.dataset.bound = '1';

        container.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-filtro-liq-tipo]');
            if (!btn) return;
            container.querySelectorAll('[data-filtro-liq-tipo]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filtroTipo = btn.dataset.filtroLiqTipo;
            _recargarDetail();
        });
    }

    // ── Punto de entrada principal ─────────────────────────────────────────────
    function init() {
        if (!w.Tabulator) {
            console.warn(`${MOD} Tabulator no disponible, reintentando...`);
            setTimeout(init, 200);
            return;
        }
        _initMaster();
        console.log(`${MOD} Master-Detail inicializado`);
    }

    function reload() {
        _recargarMaster();
        _recargarDetail();
    }

    function redraw() {
        if (tablaMaster?.redraw) tablaMaster.redraw(true);
        if (tablaDetail?.redraw) tablaDetail.redraw(true);
    }

    w.Sintel.Empleados.LiquidacionList = { init, reload, redraw };

})(window, document);
