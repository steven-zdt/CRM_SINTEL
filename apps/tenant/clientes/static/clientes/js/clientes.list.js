// @ts-nocheck
/**
 * Clientes List Module
 *
 * La grilla "clientes" es DataTables 3.x (#tabla-clientes, mismo patron ya
 * validado en Ventas/Bancos/Facturas -- ver
 * docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md), poblada via ajax
 * contra POST /api/v1/clientes/dt/. ClienteTable/ClienteTableView
 * (django-tables2) retirados; los KPIs siguen server-rendered via HTMX
 * (kpis_clientes.html).
 *
 * La grilla "contactos" y el historial de facturas (dentro del offcanvas de
 * detalle) siguen con Tabulator por ahora -- unidades separadas, fuera de
 * alcance de esta migracion.
 *
 * Namespace: window.AppCliente / window.ClientesListModule
 */

(function(w, d) {
    'use strict';

    w.AppCliente = w.AppCliente || {};

    // ── DOM SSoT ────────────────────────────────────────────────────────────
    const DOM = {
        containerClientes:  '#offcanvas-container-clientes',
        containerContactos: '#offcanvas-container-contactos',
        gridContactos:      '#grid-contactos',
        searchContacto:     '#search-contacto',
        offcanvasCliente:   'offcanvas-cliente',
        offcanvasContacto:  'offcanvas-contacto-cliente',
        dataSpinner: (t) => `[data-spinner="${t}"]`,
        dataGrid:    (t) => `[data-grid="${t}"]`,
        dataEmpty:   (t) => `[data-empty-state="${t}"]`,
    };

    // ── State ────────────────────────────────────────────────────────────────
    const state = {
        contactosLoaded: false,
        contactosLoading: false,
        contactosTable: null,
        contactosCount: 0,
    };

    const log = {
        info:  (m, d2) => console.log(`[Clientes.List] ${m}`, d2 || ''),
        warn:  (m, d2) => console.warn(`[Clientes.List] ${m}`, d2 || ''),
        error: (m, d2) => console.error(`[Clientes.List] ${m}`, d2 || ''),
    };

    // Funcion global de refresco: recarga la tabla DataTables + dispara el
    // evento que el panel HTMX de KPIs escucha via
    // hx-trigger="load, cliente-updated from:body".
    w.refreshClientesTable = function () {
        if (w.Sintel && w.Sintel.Core && w.Sintel.Core.DataTablesFactory) {
            w.Sintel.Core.DataTablesFactory.reload('#tabla-clientes');
        }
        d.body.dispatchEvent(new CustomEvent('cliente-updated'));
    };

    // ── DataTables (tabla "Clientes") ───────────────────────────────────────

    var CLIENTES_SELECTOR = '#tabla-clientes';
    var CLIENTES_DT_URL = '/api/v1/clientes/dt/';
    var _clientesTablaInicializada = false;

    var TIPO_PERSONA_MAP = { JURIDICA: ['bg-info', 'Jurídica'], NATURAL: ['bg-secondary', 'Natural'] };

    function fmtCop(value) {
        var n = parseFloat(value || 0);
        if (isNaN(n)) return '$ 0';
        return '$ ' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
    }

    function escapeHtmlCliente(str) {
        var div = d.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function renderClienteNombre(data, type, row) {
        var nombre = row.razon_social || row.nombre_comercial || '—';
        var doc = row.numero_documento
            ? '<div><small class="text-muted">' + escapeHtmlCliente(row.tipo_documento_display || '') + ' ' + escapeHtmlCliente(row.numero_documento) + '</small></div>'
            : '';
        return '<div class="lh-sm">' + escapeHtmlCliente(nombre) + doc + '</div>';
    }

    function renderTipoPersona(value) {
        var cfg = TIPO_PERSONA_MAP[value] || ['bg-light text-dark', value || '—'];
        return '<span class="badge ' + cfg[0] + '">' + escapeHtmlCliente(cfg[1]) + '</span>';
    }

    function renderRegimen(data, type, row) {
        var label = row.regimen_tributario_display || '—';
        var ret = row.es_retenedor
            ? '<span class="badge bg-warning ms-1" title="Retenedor"><i class="bi bi-shield-check"></i></span>' : '';
        return '<span class="small">' + escapeHtmlCliente(label) + '</span>' + ret;
    }

    function renderCartera(data, type, row) {
        var c = row.cartera_resumen || { pendiente_count: 0, cobrada_count: 0, total_count: 0 };
        if (!c.total_count) return '<span class="text-muted small">Sin facturas</span>';
        var parts = [];
        if (c.pendiente_count > 0) {
            parts.push('<span class="badge bg-danger" title="Facturas pendientes de cobro">' +
                '<i class="bi bi-exclamation-circle me-1"></i>' + c.pendiente_count + ' x cobrar</span> ' +
                '<span class="small text-danger fw-semibold">' + fmtCop(c.pendiente_monto) + '</span>');
        } else if (c.cobrada_count > 0) {
            parts.push('<span class="badge bg-success" title="Todas las facturas cobradas">' +
                '<i class="bi bi-check-circle me-1"></i>' + c.cobrada_count + ' cobradas</span>');
        }
        return parts.length ? parts.join(' ') : '<span class="text-muted">—</span>';
    }

    function renderContacto(data, type, row) {
        var parts = [];
        if (row.email) parts.push('<div class="text-truncate small"><i class="bi bi-envelope me-1 text-muted"></i>' + escapeHtmlCliente(row.email) + '</div>');
        if (row.telefono) parts.push('<div class="small"><i class="bi bi-telephone me-1 text-muted"></i>' + escapeHtmlCliente(row.telefono) + '</div>');
        if (row.ciudad) parts.push('<div class="small text-muted"><i class="bi bi-geo-alt me-1"></i>' + escapeHtmlCliente(row.ciudad) + '</div>');
        return parts.length ? '<div class="lh-sm">' + parts.join('') + '</div>' : '<span class="text-muted">—</span>';
    }

    function renderClienteEstado(value) {
        return value ? '<span class="badge bg-success">Activo</span>' : '<span class="badge bg-danger">Inactivo</span>';
    }

    function renderClienteAcciones(data, type, row) {
        return '<div class="btn-group btn-group-sm" role="group">' +
            '<button class="btn btn-outline-primary" data-action="edit" data-uuid="' + escapeHtmlCliente(row.uuid) + '" title="Editar"><i class="bi bi-pencil"></i></button>' +
            '<button class="btn btn-outline-info" data-action="view" data-uuid="' + escapeHtmlCliente(row.uuid) + '" title="Ver"><i class="bi bi-eye"></i></button>' +
            '<button class="btn btn-outline-danger" data-action="delete" data-uuid="' + escapeHtmlCliente(row.uuid) + '" data-activo="' + (row.activo ? 'true' : 'false') + '" data-nombre="' + escapeHtmlCliente(row.razon_social || '') + '" title="Eliminar"><i class="bi bi-trash"></i></button>' +
            '</div>';
    }

    var CLIENTES_COLUMNS = [
        { data: 'razon_social', title: 'Cliente', render: renderClienteNombre },
        { data: 'tipo_persona', title: 'Tipo', render: renderTipoPersona },
        { data: null, title: 'Régimen / Ret.', orderable: false, render: renderRegimen },
        { data: 'cartera_resumen', title: 'Cartera', orderable: false, searchable: false, render: renderCartera },
        { data: null, title: 'Contacto', orderable: false, searchable: false, render: renderContacto },
        { data: 'activo', title: 'Estado', render: renderClienteEstado },
        { data: null, title: '', orderable: false, searchable: false, render: renderClienteAcciones },
    ];

    function bindFiltrosTipoCliente() {
        var contenedor = d.getElementById('filtros-tipo-clientes');
        if (!contenedor) return;
        contenedor.addEventListener('click', function (ev) {
            var btn = ev.target.closest('[data-filtro-cl]');
            if (!btn) return;
            contenedor.querySelectorAll('[data-filtro-cl]').forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            var Factory = w.Sintel.Core.DataTablesFactory;
            var filtro = btn.getAttribute('data-filtro-cl');
            // Columna 1 = tipo_persona, columna 2 = es_retenedor, columna 5 = activo
            // (ver ClienteViewSet.dt() -- column_filters). "Todos" limpia las 3.
            Factory.columnSearch(CLIENTES_SELECTOR, 1, filtro === 'JURIDICA' ? 'JURIDICA' : filtro === 'NATURAL' ? 'NATURAL' : '');
            Factory.columnSearch(CLIENTES_SELECTOR, 2, filtro === 'RETENEDOR' ? 'true' : '');
            Factory.columnSearch(CLIENTES_SELECTOR, 5, filtro === 'ACTIVO' ? 'true' : filtro === 'INACTIVO' ? 'false' : '');
        });
    }

    function initClientesTabla() {
        if (_clientesTablaInicializada) return;
        if (typeof DataTable === 'undefined' || !w.Sintel.Core || !w.Sintel.Core.DataTablesFactory) return;
        w.Sintel.Core.DataTablesFactory.create(CLIENTES_SELECTOR, CLIENTES_DT_URL, CLIENTES_COLUMNS, {
            pageLength: 20,
            order: [[0, 'asc']],
        });
        bindFiltrosTipoCliente();
        _clientesTablaInicializada = true;
    }

    function fmtEstado(cell) {
        const v = cell.getValue();
        return v
            ? '<span class="badge bg-success">Activo</span>'
            : '<span class="badge bg-danger">Inactivo</span>';
    }

    // ── Table Columns (solo contactos -- clientes es server-rendered) ────────

    const TABLE_COLUMNS = {
        contactos: [
            { title: 'Nombre', field: 'nombre_completo', widthGrow: 2 },
            { title: 'Cliente', field: 'cliente_nombre', widthGrow: 1.5 },
            { title: 'Email', field: 'email', widthGrow: 1.5 },
            { title: 'Teléfono', field: 'telefono', minWidth: 120 },
            {
                title: 'Cargo', field: 'cargo',
                formatter: (cell) => cell.getValue() || '<span class="text-muted">—</span>',
            },
            {
                title: 'Estado', field: 'activo', width: 90, hozAlign: 'center',
                formatter: fmtEstado,
            },
            {
                title: '', width: 120, hozAlign: 'center', headerSort: false,
                formatter: () => `<div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-info" data-action="view" title="Ver"><i class="bi bi-eye"></i></button>
                    <button class="btn btn-outline-primary" data-action="edit" title="Editar"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger" data-action="delete" title="Eliminar"><i class="bi bi-trash"></i></button>
                </div>`,
                cellClick: (e, cell) => handleCellAction(e, cell, 'contactos'),
            },
        ],
    };

    // ── Table Initialization ─────────────────────────────────────────────────

    async function loadContactosTable() {
        const gridEl = d.querySelector(DOM.gridContactos);

        if (state.contactosLoaded && gridEl && gridEl.children.length > 0) return;

        if (!gridEl || gridEl.children.length === 0) {
            if (state.contactosTable) {
                try { state.contactosTable.destroy(); } catch (_) {}
                state.contactosTable = null;
            }
            state.contactosLoaded = false;
        }

        state.contactosLoading = true;
        updateUIState('contactos');

        try {
            await waitForTabulatorFactory();

            state.contactosTable = w.TabulatorFactory.create(
                DOM.gridContactos,
                '/api/v1/clientes/contactos/',
                TABLE_COLUMNS.contactos,
                { searchInputSelector: DOM.searchContacto }
            );

            if (!state.contactosTable) throw new Error('TabulatorFactory.create returned null');

            state.contactosLoaded = true;

            state.contactosTable.on('dataLoaded', (data) => {
                state.contactosCount = data.length;
                updateUIState('contactos');
            });

            setupRefreshBtnContactos();

        } catch (err) {
            log.error('Error loading contactos table', err);
            state.contactosLoaded = true;
            showError('Error al cargar la tabla de contactos');
        } finally {
            state.contactosLoading = false;
            updateUIState('contactos');
        }
    }

    function reloadTable(type) {
        if (type === 'clientes') w.refreshClientesTable();
        else if (type === 'contactos' && state.contactosTable) state.contactosTable.replaceData();
    }

    // ── Refresh Buttons ──────────────────────────────────────────────────────

    function setupRefreshBtn() {
        const btn = d.getElementById('btn-refresh-clientes');
        if (!btn || btn.dataset.bound) return;
        btn.dataset.bound = 'true';
        btn.addEventListener('click', () => reloadTable('clientes'));
    }
    setupRefreshBtn();

    function setupRefreshBtnContactos() {
        const btn = d.getElementById('btn-refresh-contactos');
        if (!btn || btn.dataset.bound) return;
        btn.dataset.bound = 'true';
        btn.addEventListener('click', () => reloadTable('contactos'));
    }

    // ── TabulatorFactory helper ──────────────────────────────────────────────

    async function waitForTabulatorFactory() {
        if (w.TabulatorFactory) return;
        return new Promise((resolve, reject) => {
            let tries = 0;
            const iv = setInterval(() => {
                tries++;
                if (w.TabulatorFactory) { clearInterval(iv); resolve(); }
                else if (tries > 50)   { clearInterval(iv); reject(new Error('TabulatorFactory timeout')); }
            }, 100);
        });
    }

    // ── Cell Actions (contactos, sigue con Tabulator cellClick) ──────────────

    function handleCellAction(e, cell, type) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const row = cell.getRow().getData();
        if (action === 'view')   viewContacto(row.uuid);
        if (action === 'edit')   editContacto(row.uuid);
        if (action === 'delete') deleteContacto(row.uuid);
    }

    // ── Clientes Actions (DataTables: delegacion sobre document.body) ────────
    // Los botones de #tabla-clientes llevan data-action/data-uuid (ver
    // renderClienteAcciones en clientes.list.js), no dependen de un objeto
    // de fila de Tabulator.

    d.body.addEventListener('click', (e) => {
        const btn = e.target.closest('#tabla-clientes button[data-action]');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        const action = btn.dataset.action;
        const uuid = btn.dataset.uuid;
        if (!uuid) return;
        if (action === 'edit')   editCliente(uuid);
        if (action === 'view')   viewCliente(uuid);
        if (action === 'delete') deleteCliente(uuid, btn.dataset.activo === 'true', btn.dataset.nombre);
    });

    function editCliente(uuid) {
        htmx.ajax('GET', `/api/v1/clientes/${uuid}/render-offcanvas/editar/`, {
            target: DOM.containerClientes, swap: 'innerHTML'
        });
    }

    function viewCliente(uuid) {
        htmx.ajax('GET', `/api/v1/clientes/${uuid}/render-offcanvas/detalle/`, {
            target: DOM.containerClientes, swap: 'innerHTML'
        });
    }

    async function deleteCliente(uuid, activo, nombre) {
        if (activo === true) {
            showError(`El cliente "${nombre || 'este cliente'}" está activo. Inactívelo antes de eliminarlo.`);
            return;
        }
        if (!(await w.UIManager?.confirm('¿Eliminar este cliente de forma permanente?'))) return;
        // T-9: delega a la SSoT de endpoints (clientes.api.js).
        const res = await w.clientesAPI.delete(uuid);
        if (res.ok || res.status === 204) {
            showSuccess('Cliente eliminado');
            d.dispatchEvent(new CustomEvent('clienteEliminado'));
        } else {
            showError(res.data?.detail || 'No se pudo eliminar el cliente');
        }
    }

    function viewContacto(uuid) {
        htmx.ajax('GET', `/api/v1/clientes/contactos/${uuid}/render-offcanvas/detalle/`, {
            target: DOM.containerContactos, swap: 'innerHTML'
        });
    }

    function editContacto(uuid) {
        htmx.ajax('GET', `/api/v1/clientes/contactos/${uuid}/render-offcanvas/editar/`, {
            target: DOM.containerContactos, swap: 'innerHTML'
        });
    }

    async function deleteContacto(uuid) {
        if (!(await w.UIManager?.confirm('¿Eliminar este contacto?'))) return;
        // T-9: delega a la SSoT de endpoints (clientes.api.js).
        const res = await w.contactosAPI.delete(uuid);
        if (res.ok || res.status === 204) {
            showSuccess('Contacto eliminado');
            d.dispatchEvent(new CustomEvent('contactoEliminado'));
        } else {
            showError('No se pudo eliminar el contacto');
        }
    }

    // ── Historial Facturas (en offcanvas detalle) ────────────────────────────

    let _historialTable = null;
    let _historialUUID = null;

    // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
    const COP = (v) => (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function')
        ? w.DOMUtils.formatCurrency(parseFloat(v) || 0, { minimumFractionDigits: 0 })
        : new Intl.NumberFormat('en-US', {
            style: 'currency', currency: 'USD', minimumFractionDigits: 0
        }).format(parseFloat(v) || 0);

    const HISTORIAL_COLUMNS = [
        {
            title: 'Número', field: 'numero', widthGrow: 1,
            formatter: (cell) => {
                const v = cell.getValue() || '—';
                return `<span class="fw-semibold small">${v}</span>`;
            }
        },
        {
            title: 'Fecha', field: 'fecha_emision', width: 95,
            formatter: (cell) => {
                const v = cell.getValue();
                return v ? `<span class="small">${v.substring(0,10)}</span>` : '—';
            }
        },
        {
            title: 'Estado', field: 'estado', width: 95, hozAlign: 'center',
            formatter: (cell) => {
                const v = cell.getValue();
                const cls = {
                    'ACEPTADA': 'bg-success', 'PENDIENTE': 'bg-warning text-dark',
                    'ANULADA': 'bg-danger',   'RECHAZADA': 'bg-danger',
                    'BORRADOR': 'bg-secondary',
                }[v] || 'bg-light text-muted';
                return `<span class="badge ${cls}">${v || '—'}</span>`;
            }
        },
        {
            title: 'Total', field: 'total', widthGrow: 1, hozAlign: 'right',
            formatter: (cell) => `<span class="small fw-semibold">${COP(cell.getValue())}</span>`
        },
    ];

    function initHistorialFacturas(offcanvasEl) {
        const uuid = offcanvasEl?.dataset?.clienteUuid;
        if (!uuid) return;
        _historialUUID = uuid;

        // Wire tab shown event (one time per offcanvas instance)
        const tabBtn = d.getElementById('tab-facturas-btn');
        if (tabBtn && !tabBtn.dataset.historialBound) {
            tabBtn.dataset.historialBound = 'true';
            tabBtn.addEventListener('shown.bs.tab', () => _cargarHistorial(uuid));
        }

        // Wire estado filter chips
        const filtros = d.getElementById('historial-filtros-estado');
        if (filtros && !filtros.dataset.bound) {
            filtros.dataset.bound = 'true';
            filtros.addEventListener('click', (e) => {
                const btn = e.target.closest('[data-historial-estado]');
                if (!btn || !_historialTable) return;
                filtros.querySelectorAll('[data-historial-estado]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const estado = btn.dataset.historialEstado;
                _historialTable.clearFilter();
                if (estado) _historialTable.setFilter('estado', '=', estado);
            });
        }
    }

    async function _cargarHistorial(uuid) {
        if (!uuid) return;

        // Destroy previous instance if UUID changed
        if (_historialTable) {
            try { _historialTable.destroy(); } catch (_) {}
            _historialTable = null;
        }

        const spinner = d.getElementById('historial-facturas-spinner');
        const empty   = d.getElementById('historial-facturas-empty');
        const grid    = d.getElementById('historial-facturas-grid');
        if (!grid) return;

        if (spinner) spinner.style.display = 'block';
        if (empty)   empty.style.display   = 'none';

        try {
            await waitForTabulatorFactory();

            _historialTable = w.TabulatorFactory.create(
                '#historial-facturas-grid',
                `/api/v1/facturas/?cliente_uuid=${uuid}&naturaleza=VENTA`,
                HISTORIAL_COLUMNS,
                { ajaxSorting: true }
            );

            if (!_historialTable) throw new Error('Tabulator null');

            _historialTable.on('dataLoaded', (data) => {
                if (spinner) spinner.style.display = 'none';
                if (empty)   empty.style.display   = data.length === 0 ? 'block' : 'none';
                _actualizarKPIsHistorial(data);
            });

        } catch (err) {
            log.error('Error cargando historial facturas', err);
            if (spinner) spinner.style.display = 'none';
        }
    }

    function _actualizarKPIsHistorial(rows) {
        const set = (id, v) => { const el = d.getElementById(id); if (el) el.textContent = v; };
        const total    = rows.length;
        const monto    = rows.reduce((s, r) => s + (parseFloat(r.total) || 0), 0);
        const pendiente = rows
            .filter(r => r.estado === 'PENDIENTE' || r.estado === 'ENVIADA')
            .reduce((s, r) => s + (parseFloat(r.total) || 0), 0);
        set('hkpi-total',    total);
        set('hkpi-monto',    COP(monto));
        set('hkpi-pendiente', COP(pendiente));
    }

    // ── UI State ─────────────────────────────────────────────────────────────

    function updateUIState(type) {
        const loading = state.contactosLoading;
        const loaded  = state.contactosLoaded;
        const count   = state.contactosCount;

        const spinner = d.querySelector(DOM.dataSpinner(type));
        if (spinner) spinner.style.display = (!loaded && loading) ? 'block' : 'none';

        const grid = d.querySelector(DOM.dataGrid(type));
        if (grid) grid.style.display = loaded ? 'block' : 'none';

        const empty = d.querySelector(DOM.dataEmpty(type));
        if (empty) empty.style.display = (!loading && loaded && count === 0) ? 'block' : 'none';
    }

    // ── Event Listeners ──────────────────────────────────────────────────────

    // Search debounce — contactos (busqueda de clientes va via hx-trigger
    // directo en el input, ver clientes_list.html)
    d.addEventListener('keyup', (e) => {
        if (e.target.matches(DOM.searchContacto)) {
            clearTimeout(e.target._t);
            e.target._t = setTimeout(() => reloadTable('contactos'), 300);
        }
    });

    // Sub-tab shown: load contactos lazily
    d.addEventListener('shown.bs.tab', (e) => {
        if (e.target?.dataset?.bsTarget === '#tab-pane-contactos') loadContactosTable();
    });

    // HTMX afterSettle → show offcanvas + init historial
    d.body.addEventListener('htmx:afterSettle', (e) => {
        const tid = e.detail?.target?.id;
        if (tid === 'offcanvas-container-clientes') {
            requestAnimationFrame(() => {
                const el = d.getElementById(DOM.offcanvasCliente);
                if (el && w.UIManager?.handleOffcanvas) {
                    w.UIManager.handleOffcanvas(el, 'show');
                    initHistorialFacturas(el);
                }
            });
        } else if (tid === 'offcanvas-container-contactos') {
            requestAnimationFrame(() => {
                const el = d.getElementById(DOM.offcanvasContacto);
                if (el && w.UIManager?.handleOffcanvas) w.UIManager.handleOffcanvas(el, 'show');
            });
        }
    });

    // CRUD completion → reload (KPIs se recalculan server-side con la tabla)
    d.addEventListener('clienteGuardado',  () => w.refreshClientesTable());
    d.addEventListener('clienteEliminado', () => w.refreshClientesTable());
    d.addEventListener('contactoGuardado',  () => reloadTable('contactos'));
    d.addEventListener('contactoEliminado', () => reloadTable('contactos'));

    // ── Notifications ────────────────────────────────────────────────────────

    function showSuccess(msg) {
        if (w.UIManager) w.UIManager.success(msg);
    }

    function showError(msg) {
        if (w.UIManager?.handleError) w.UIManager.handleError({ status: 400, data: { detail: msg } }, 'Clientes');
        else log.error(msg);
    }

    // ── Export ───────────────────────────────────────────────────────────────

    log.info('Module loaded');

    w.ClientesListModule = { state, loadContactosTable, reloadTable };
    w.AppCliente.main = w.ClientesListModule;

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', initClientesTabla);
    } else {
        initClientesTabla();
    }

})(window, document);
