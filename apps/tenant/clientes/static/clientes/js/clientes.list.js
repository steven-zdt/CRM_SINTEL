// @ts-nocheck
/**
 * Clientes List Module
 * Fase 5-BIS: la grilla "clientes" es server-rendered via django-tables2 +
 * HTMX (#clientes-panel, cargada por atributos hx-get/hx-trigger declarados
 * en clientes_list.html). Columnas, KPIs y filtros por tipo viven en
 * tables.py/views.py/selectors.py (server-side).
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

    // Funcion global de refresco: dispara el evento que el panel HTMX de
    // clientes escucha via hx-trigger="load, cliente-updated from:body".
    w.refreshClientesTable = function () {
        d.body.dispatchEvent(new CustomEvent('cliente-updated'));
    };

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

    // ── Clientes Actions (server-rendered: delegacion sobre document.body) ───
    // Fase 5-BIS: los botones de #clientes-panel llevan data-action/data-uuid
    // (ver render_acciones en apps/tenant/clientes/tables.py), no dependen de
    // un objeto de fila de Tabulator.

    d.body.addEventListener('click', (e) => {
        const btn = e.target.closest('#clientes-panel button[data-action]');
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
        : new Intl.NumberFormat('es-CO', {
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

})(window, document);
