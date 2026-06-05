// @ts-nocheck
/**
 * Clientes List Module v3.10
 * KPIs + filter chips + improved columns.
 * Namespace: window.AppCliente / window.ClientesListModule
 */

(function(w, d) {
    'use strict';

    w.AppCliente = w.AppCliente || {};

    // ── DOM SSoT ────────────────────────────────────────────────────────────
    const DOM = {
        containerClientes:  '#offcanvas-container-clientes',
        containerContactos: '#offcanvas-container-contactos',
        gridClientes:       '#grid-clientes',
        gridContactos:      '#grid-contactos',
        searchCliente:      '#search-cliente',
        searchContacto:     '#search-contacto',
        offcanvasCliente:   'offcanvas-cliente',
        offcanvasContacto:  'offcanvas-contacto-cliente',
        dataSpinner: (t) => `[data-spinner="${t}"]`,
        dataGrid:    (t) => `[data-grid="${t}"]`,
        dataEmpty:   (t) => `[data-empty-state="${t}"]`,
    };

    // ── State ────────────────────────────────────────────────────────────────
    const state = {
        clientesLoaded: false,  clientesLoading: false,
        contactosLoaded: false, contactosLoading: false,
        clientesTable: null,    contactosTable: null,
        clientesCount: 0,       contactosCount: 0,
        filtroActivo: '',
    };

    const log = {
        info:  (m, d2) => console.log(`[Clientes.List] ${m}`, d2 || ''),
        warn:  (m, d2) => console.warn(`[Clientes.List] ${m}`, d2 || ''),
        error: (m, d2) => console.error(`[Clientes.List] ${m}`, d2 || ''),
    };

    // ── KPIs (server-side, single aggregate query) ───────────────────────────

    async function cargarKPIs() {
        try {
            const res = await w.http('GET', '/api/v1/clientes/kpis/');
            if (!res.ok) return;
            const k = res.data;
            const set = (id, v) => { const el = d.getElementById(id); if (el) el.textContent = v ?? '—'; };
            set('kpi-cl-total',       k.total);
            set('kpi-cl-activos',     k.activos);
            set('kpi-cl-inactivos',   k.inactivos);
            set('kpi-cl-juridicas',   k.juridicas);
            set('kpi-cl-naturales',   k.naturales);
            set('kpi-cl-retenedores', k.retenedores);
        } catch (_) {}
    }

    // ── Column Formatters ────────────────────────────────────────────────────

    function fmtRazonSocial(cell) {
        const row = cell.getRow().getData();
        const nombre = row.razon_social || row.nombre_comercial || '—';
        const doc = row.numero_documento
            ? `<div><small class="text-muted">${row.tipo_documento_display || ''} ${row.numero_documento}</small></div>`
            : '';
        return `<div class="lh-sm">${nombre}${doc}</div>`;
    }

    function fmtTipoPersona(cell) {
        const v = cell.getValue();
        const label = cell.getRow().getData().tipo_persona_display || v || '—';
        const cls = v === 'JURIDICA' ? 'bg-info' : v === 'NATURAL' ? 'bg-secondary' : 'bg-light text-dark';
        return `<span class="badge ${cls}">${label}</span>`;
    }

    function fmtRegimen(cell) {
        const row = cell.getRow().getData();
        const label = row.regimen_tributario_display || row.regimen_tributario || '—';
        const ret = row.es_retenedor ? '<span class="badge bg-warning ms-1" title="Retenedor"><i class="bi bi-shield-check"></i></span>' : '';
        return `<span class="small">${label}</span>${ret}`;
    }

    function fmtContacto(cell) {
        const row = cell.getRow().getData();
        const parts = [];
        if (row.email) parts.push(`<div class="text-truncate small"><i class="bi bi-envelope me-1 text-muted"></i>${row.email}</div>`);
        if (row.telefono) parts.push(`<div class="small"><i class="bi bi-telephone me-1 text-muted"></i>${row.telefono}</div>`);
        if (row.ciudad) parts.push(`<div class="small text-muted"><i class="bi bi-geo-alt me-1"></i>${row.ciudad}</div>`);
        return parts.length ? `<div class="lh-sm">${parts.join('')}</div>` : '<span class="text-muted">—</span>';
    }

    function fmtEstado(cell) {
        const v = cell.getValue();
        return v
            ? '<span class="badge bg-success">Activo</span>'
            : '<span class="badge bg-danger">Inactivo</span>';
    }

    function fmtAccionesCliente(cell) {
        return `<div class="btn-group btn-group-sm" role="group">
            <button class="btn btn-outline-primary" data-action="edit" title="Editar"><i class="bi bi-pencil"></i></button>
            <button class="btn btn-outline-info" data-action="view" title="Ver"><i class="bi bi-eye"></i></button>
            <button class="btn btn-outline-danger" data-action="delete" title="Eliminar"><i class="bi bi-trash"></i></button>
        </div>`;
    }

    function fmtCartera(cell) {
        const c = cell.getRow().getData().cartera_resumen;
        if (!c || c.total_count === 0) {
            return '<span class="text-muted small">Sin facturas</span>';
        }
        const fmt = (v) => parseFloat(v || 0).toLocaleString('es-CO', {
            style: 'currency', currency: 'COP', maximumFractionDigits: 0,
        });
        const parts = [];
        if (c.pendiente_count > 0) {
            parts.push(
                `<span class="badge bg-danger" title="Facturas pendientes de cobro">` +
                `<i class="bi bi-exclamation-circle me-1"></i>${c.pendiente_count} x cobrar</span> ` +
                `<span class="small text-danger fw-semibold">${fmt(c.pendiente_monto)}</span>`
            );
        }
        if (c.cobrada_count > 0 && c.pendiente_count === 0) {
            parts.push(
                `<span class="badge bg-success" title="Todas las facturas cobradas">` +
                `<i class="bi bi-check-circle me-1"></i>${c.cobrada_count} cobradas</span>`
            );
        } else if (c.cobrada_count > 0) {
            parts.push(
                `<span class="badge bg-light text-success border border-success" title="${c.cobrada_count} facturas cobradas">` +
                `${c.cobrada_count} cobr.</span>`
            );
        }
        return parts.join(' ') || '<span class="text-muted small">—</span>';
    }

    // ── Table Columns ────────────────────────────────────────────────────────

    const TABLE_COLUMNS = {
        clientes: [
            {
                title: 'Cliente', field: 'razon_social', widthGrow: 3, minWidth: 200,
                formatter: fmtRazonSocial,
            },
            {
                title: 'Tipo', field: 'tipo_persona', width: 110,
                hozAlign: 'center', formatter: fmtTipoPersona,
            },
            {
                title: 'Régimen / Ret.', field: 'regimen_tributario', widthGrow: 1.5, minWidth: 150,
                formatter: fmtRegimen,
            },
            {
                title: 'Cartera', field: 'cartera_resumen', minWidth: 210,
                headerSort: false, formatter: fmtCartera,
            },
            {
                title: 'Contacto', field: 'email', widthGrow: 2, minWidth: 180,
                headerSort: false, formatter: fmtContacto,
            },
            {
                title: 'Estado', field: 'activo', width: 90,
                hozAlign: 'center', formatter: fmtEstado,
            },
            {
                title: '', width: 120, hozAlign: 'center', headerSort: false,
                formatter: fmtAccionesCliente,
                cellClick: (e, cell) => handleCellAction(e, cell, 'clientes'),
            },
        ],
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

    // ── Filter Chips ─────────────────────────────────────────────────────────

    const BASE_API_CLIENTES = '/api/v1/clientes/';

    function _buildApiUrl(filtro) {
        if (!filtro) return BASE_API_CLIENTES;
        const params = new URLSearchParams();
        if (filtro === 'JURIDICA')  params.set('tipo_persona', 'JURIDICA');
        if (filtro === 'NATURAL')   params.set('tipo_persona', 'NATURAL');
        if (filtro === 'RETENEDOR') params.set('es_retenedor', 'true');
        if (filtro === 'ACTIVO')    params.set('activo', 'true');
        if (filtro === 'INACTIVO')  params.set('activo', 'false');
        return `${BASE_API_CLIENTES}?${params.toString()}`;
    }

    function initFiltrosClientes() {
        const container = d.getElementById('filtros-tipo-clientes');
        if (!container || container.dataset.filtrosBound) return;
        container.dataset.filtrosBound = 'true';

        container.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-filtro-cl]');
            if (!btn || !state.clientesTable) return;

            container.querySelectorAll('[data-filtro-cl]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            state.filtroActivo = btn.dataset.filtroCl;
            state.clientesTable.replaceData(_buildApiUrl(state.filtroActivo));
        });
    }

    // ── Table Initialization ─────────────────────────────────────────────────

    async function loadClientesTable() {
        const gridEl = d.querySelector(DOM.gridClientes);

        if (state.clientesLoaded && gridEl && gridEl.children.length > 0) return;

        if (!gridEl || gridEl.children.length === 0) {
            if (state.clientesTable) {
                try { state.clientesTable.destroy(); } catch (_) {}
                state.clientesTable = null;
            }
            state.clientesLoaded = false;
        }

        state.clientesLoading = true;
        updateUIState('clientes');

        try {
            await waitForTabulatorFactory();

            state.clientesTable = w.TabulatorFactory.create(
                DOM.gridClientes,
                '/api/v1/clientes/',
                TABLE_COLUMNS.clientes,
                { searchInputSelector: DOM.searchCliente }
            );

            if (!state.clientesTable) throw new Error('TabulatorFactory.create returned null');

            state.clientesLoaded = true;

            state.clientesTable.on('dataLoaded', (data) => {
                state.clientesCount = data.length;
                updateUIState('clientes');
            });

            initFiltrosClientes();
            setupRefreshBtn();
            cargarKPIs();

        } catch (err) {
            log.error('Error loading clientes table', err);
            state.clientesLoaded = true;
            showError('Error al cargar la tabla de clientes');
        } finally {
            state.clientesLoading = false;
            updateUIState('clientes');
        }
    }

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
        if (type === 'clientes' && state.clientesTable) state.clientesTable.replaceData();
        else if (type === 'contactos' && state.contactosTable) state.contactosTable.replaceData();
    }

    // ── Refresh Buttons ──────────────────────────────────────────────────────

    function setupRefreshBtn() {
        const btn = d.getElementById('btn-refresh-clientes');
        if (!btn || btn.dataset.bound) return;
        btn.dataset.bound = 'true';
        btn.addEventListener('click', () => reloadTable('clientes'));
    }

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

    // ── Cell Actions ─────────────────────────────────────────────────────────

    function handleCellAction(e, cell, type) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        const row = cell.getRow().getData();
        if (type === 'clientes') {
            if (action === 'edit')   editCliente(row.uuid);
            if (action === 'view')   viewCliente(row.uuid);
            if (action === 'delete') deleteCliente(row);
        } else {
            if (action === 'view')   viewContacto(row.uuid);
            if (action === 'edit')   editContacto(row.uuid);
            if (action === 'delete') deleteContacto(row.uuid);
        }
    }

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

    async function deleteCliente(rowData) {
        const uuid = rowData.uuid;
        if (rowData.activo === true) {
            showError(`El cliente "${rowData.razon_social || 'este cliente'}" está activo. Inactívelo antes de eliminarlo.`);
            return;
        }
        if (!confirm('¿Eliminar este cliente de forma permanente?')) return;
        const res = await w.http('DELETE', `/api/v1/clientes/${uuid}/`);
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
        if (!confirm('¿Eliminar este contacto?')) return;
        const res = await w.http('DELETE', `/api/v1/clientes/contactos/${uuid}/`);
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

    const COP = (v) => new Intl.NumberFormat('es-CO', {
        style: 'currency', currency: 'COP', minimumFractionDigits: 0
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
        const loading = type === 'clientes' ? state.clientesLoading : state.contactosLoading;
        const loaded  = type === 'clientes' ? state.clientesLoaded  : state.contactosLoaded;
        const count   = type === 'clientes' ? state.clientesCount   : state.contactosCount;

        const spinner = d.querySelector(DOM.dataSpinner(type));
        if (spinner) spinner.style.display = (!loaded && loading) ? 'block' : 'none';

        const grid = d.querySelector(DOM.dataGrid(type));
        if (grid) grid.style.display = loaded ? 'block' : 'none';

        const empty = d.querySelector(DOM.dataEmpty(type));
        if (empty) empty.style.display = (!loading && loaded && count === 0) ? 'block' : 'none';
    }

    // ── Event Listeners ──────────────────────────────────────────────────────

    // Search debounce — clientes preserves active filter param
    d.addEventListener('keyup', (e) => {
        if (e.target.matches(DOM.searchCliente)) {
            clearTimeout(e.target._t);
            e.target._t = setTimeout(() => {
                if (!state.clientesTable) return;
                const q = e.target.value.trim();
                const base = _buildApiUrl(state.filtroActivo);
                const url = new URL(base, location.origin);
                if (q) url.searchParams.set('search', q);
                else url.searchParams.delete('search');
                state.clientesTable.replaceData(url.pathname + url.search);
            }, 300);
        } else if (e.target.matches(DOM.searchContacto)) {
            clearTimeout(e.target._t);
            e.target._t = setTimeout(() => reloadTable('contactos'), 300);
        }
    });

    // Sub-tab shown: load contactos lazily
    d.addEventListener('shown.bs.tab', (e) => {
        if (e.target?.dataset?.bsTarget === '#tab-pane-contactos') loadContactosTable();
    });

    // Workspace tab activation
    d.addEventListener('tab-activated', (e) => {
        const tabName = e.detail?.tabName;
        if (tabName === 'clientes') loadClientesTable();
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

    // CRUD completion → reload + refresh KPIs
    d.addEventListener('clienteGuardado',  () => { reloadTable('clientes'); cargarKPIs(); });
    d.addEventListener('clienteEliminado', () => { reloadTable('clientes'); cargarKPIs(); });
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

    log.info('Module v3.10 loaded');

    w.ClientesListModule = { state, loadClientesTable, loadContactosTable, reloadTable };
    w.AppCliente.main = w.ClientesListModule;

})(window, document);
