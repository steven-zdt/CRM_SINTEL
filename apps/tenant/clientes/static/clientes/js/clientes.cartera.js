/**
 * Feature: Gestion de Cartera (Cuentas por Cobrar) v3.10
 * ⚠️ Feature-Sliced Architecture: Modulo para listar y abonar cartera
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API
 */
(function(w, d) {
    'use strict';

    w.AppCliente = w.AppCliente || {};

    const DOM = {
        grid: '#grid-cartera',
        search: '#search-cartera',
        btnRefresh: '#btn-refresh-cartera',
        container: '#offcanvas-container-cartera',
        offcanvas: 'offcanvas-abono-cartera',
        form: '#form-abono-cartera',
        feedback: '#abono-cartera-feedback',
        btnGuardar: '#btn-guardar-abono',
        kpiSummary: '#cartera-kpi-summary',
        kpiPendienteMonto: '#cartera-pendiente-monto',
        kpiPendienteCount: '#cartera-pendiente-count',
        kpiPagadoMonto: '#cartera-pagado-monto',
        filtrosEstado: '#filtros-estado-cartera'
    };

    const state = {
        loaded: false,
        loading: false,
        table: null,
        count: 0,
        filtroEstado: ''
    };

    const log = {
        info: (m, d2) => console.log(`[Clientes.Cartera] ${m}`, d2 || ''),
        error: (m, d2) => console.error(`[Clientes.Cartera] ${m}`, d2 || '')
    };

    const COP = (v) => new Intl.NumberFormat('es-CO', {
        style: 'currency', currency: 'COP', minimumFractionDigits: 0
    }).format(parseFloat(v) || 0);

    // ── KPIs ─────────────────────────────────────────────────────────────────
    async function cargarCarteraKPIs() {
        try {
            const res = await w.AppCliente.carteraApi.kpis();
            if (!res.ok) return;
            const k = res.data;
            const setVal = (id, val) => {
                const el = d.querySelector(id);
                if (el) el.textContent = val;
            };
            setVal(DOM.kpiPendienteMonto, COP(k.pendiente_monto));
            setVal(DOM.kpiPendienteCount, k.pendiente_count);
            setVal(DOM.kpiPagadoMonto, COP(k.pagado_monto));
        } catch (err) {
            log.error('Error cargando KPIs de cartera', err);
        }
    }

    // ── Column Formatters ────────────────────────────────────────────────────
    function fmtFactura(cell) {
        const row = cell.getRow().getData();
        return `<div class="fw-semibold text-dark">${row.numero_factura || '—'}</div>`;
    }

    function fmtEstado(cell) {
        const v = cell.getValue();
        // Acepta tanto nombres Cartera (SIN_PAGO/PARCIAL) como Factura (NO_PAGADA/PAGO_PARCIAL)
        const badges = {
            'SIN_PAGO':   'bg-danger text-white',
            'NO_PAGADA':  'bg-danger text-white',
            'PARCIAL':    'bg-warning text-dark',
            'PAGO_PARCIAL': 'bg-warning text-dark',
            'PAGADA':     'bg-success text-white',
        };
        const labels = {
            'SIN_PAGO':   'Sin Pago',
            'NO_PAGADA':  'Sin Pago',
            'PARCIAL':    'Pago Parcial',
            'PAGO_PARCIAL': 'Pago Parcial',
            'PAGADA':     'Pagada',
        };
        const cls = badges[v] || 'bg-light text-muted';
        const lbl = labels[v] || v || '—';
        return `<span class="badge ${cls}">${lbl}</span>`;
    }

    function fmtAcciones(cell) {
        const row = cell.getRow().getData();
        const pagada = row.estado_pago === 'PAGADA';
        if (pagada) {
            return `<span class="text-muted small"><i class="bi bi-check2-all text-success me-1"></i>Liquidada</span>`;
        }
        return `<button class="btn btn-xs btn-outline-success" data-action="abonar" title="Registrar Abono">
            <i class="bi bi-cash-coin me-1"></i>Abonar
        </button>`;
    }

    const COLUMNS = [
        { title: 'Factura', field: 'numero_factura', widthGrow: 1.5, formatter: fmtFactura },
        { title: 'Cliente', field: 'cliente_nombre', widthGrow: 2.5 },
        {
            title: 'Fecha Vence', field: 'fecha_vencimiento', width: 110,
            formatter: (cell) => cell.getValue() ? `<span class="small">${cell.getValue()}</span>` : '—'
        },
        {
            title: 'Total', field: 'valor_total', width: 120, hozAlign: 'right',
            formatter: (cell) => `<span class="fw-semibold">${COP(cell.getValue())}</span>`
        },
        {
            title: 'Pagado', field: 'valor_pagado', width: 120, hozAlign: 'right',
            formatter: (cell) => `<span class="text-success small">${COP(cell.getValue())}</span>`
        },
        {
            title: 'Saldo', field: 'saldo', width: 120, hozAlign: 'right',
            formatter: (cell) => `<span class="text-danger fw-semibold">${COP(cell.getValue())}</span>`
        },
        { title: 'Estado', field: 'estado_pago', width: 100, hozAlign: 'center', formatter: fmtEstado }, // BUG FIX: estado_pago
        {
            title: '', width: 100, hozAlign: 'center', headerSort: false,
            formatter: fmtAcciones,
            cellClick: (e, cell) => {
                const btn = e.target.closest('[data-action="abonar"]');
                if (!btn) return;
                const row = cell.getRow().getData();
                abrirAbonoOffcanvas(row.uuid);
            }
        }
    ];

    // ── Table Load ───────────────────────────────────────────────────────────
    async function loadCarteraTable() {
        const gridEl = d.querySelector(DOM.grid);
        if (state.loaded && gridEl && gridEl.children.length > 0) return;

        if (!gridEl || gridEl.children.length === 0) {
            if (state.table) {
                try { state.table.destroy(); } catch (_) {}
                state.table = null;
            }
            state.loaded = false;
        }

        state.loading = true;
        updateUIState();

        try {
            await waitForTabulatorFactory();

            state.table = w.TabulatorFactory.create(
                DOM.grid,
                '/api/v1/clientes/cartera/',
                COLUMNS,
                { searchInputSelector: DOM.search }
            );

            if (!state.table) throw new Error('TabulatorFactory.create returned null');

            state.loaded = true;

            state.table.on('dataLoaded', (data) => {
                state.count = data.length;
                updateUIState();
            });

            initFiltros();
            setupRefreshBtn();
            cargarCarteraKPIs();

        } catch (err) {
            log.error('Error cargando tabla cartera', err);
            state.loaded = true;
            showError('Error al cargar la tabla de cartera');
        } finally {
            state.loading = false;
            updateUIState();
        }
    }

    function updateUIState() {
        const spinner = d.querySelector(`[data-spinner="cartera"]`);
        if (spinner) spinner.style.display = (!state.loaded && state.loading) ? 'block' : 'none';

        const grid = d.querySelector(`[data-grid="cartera"]`);
        if (grid) grid.style.display = state.loaded ? 'block' : 'none';

        const empty = d.querySelector(`[data-empty-state="cartera"]`);
        if (empty) empty.style.display = (!state.loading && state.loaded && state.count === 0) ? 'block' : 'none';
    }

    function setupRefreshBtn() {
        const btn = d.querySelector(DOM.btnRefresh);
        if (!btn || btn.dataset.bound) return;
        btn.dataset.bound = 'true';
        btn.addEventListener('click', () => {
            if (state.table) state.table.replaceData();
            cargarCarteraKPIs();
        });
    }

    function initFiltros() {
        const container = d.querySelector(DOM.filtrosEstado);
        if (!container || container.dataset.bound) return;
        container.dataset.bound = 'true';

        container.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-filtro-cartera]');
            if (!btn || !state.table) return;

            container.querySelectorAll('[data-filtro-cartera]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            state.filtroEstado = btn.dataset.filtroCartera;
            
            const base = '/api/v1/clientes/cartera/';
            const url = new URL(base, location.origin);
            if (state.filtroEstado) {
                url.searchParams.set('estado_pago', state.filtroEstado); // BUG FIX: param correcto
            }
            const q = d.querySelector(DOM.search)?.value?.trim();
            if (q) {
                url.searchParams.set('search', q);
            }
            state.table.replaceData(url.pathname + url.search);
        });
    }

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

    // ── Abono Form & Actions ─────────────────────────────────────────────────
    // uuid aqui es el UUID de la Factura (fuente de verdad Pull Model)
    function abrirAbonoOffcanvas(facturaUuid) {
        htmx.ajax('GET', `/api/v1/clientes/cartera/render-offcanvas/abono-factura/?factura_uuid=${facturaUuid}`, {
            target: DOM.container,
            swap: 'innerHTML'
        });
    }

    function abrirCrearOffcanvas(clienteUuid) {
        const qs = clienteUuid ? `?cliente_uuid=${clienteUuid}` : '';
        htmx.ajax('GET', `/api/v1/clientes/cartera/render-offcanvas/crear/${qs}`, {
            target: DOM.container,
            swap: 'innerHTML'
        });
    }

    async function initCrearForm(el) {
        const form = el.querySelector('#form-crear-cartera');
        if (!form || form.dataset.bound) return;
        form.dataset.bound = 'true';

        // Si no hay cliente preseleccionado, cargar select
        const selectCliente = form.querySelector('#cartera-cliente-id[multiple!=""]');
        if (selectCliente && selectCliente.tagName === 'SELECT') {
            try {
                const res = await w.Sintel.Core.Http.request('GET', '/api/v1/clientes/?page_size=200');
                if (res.ok && res.data?.results) {
                    res.data.results.forEach(c => {
                        const opt = d.createElement('option');
                        opt.value = c.id;
                        opt.textContent = `${c.razon_social} — ${c.nit || c.numero_documento || ''}`;
                        selectCliente.appendChild(opt);
                    });
                }
            } catch (_) {}
        }

        // Preset fecha de hoy
        const hoy = new Date().toISOString().split('T')[0];
        const fechaEmision = form.querySelector('#cartera-fecha-emision');
        if (fechaEmision && !fechaEmision.value) fechaEmision.value = hoy;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('#btn-guardar-cartera');
            if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...'; }

            const fd = new FormData(form);
            const payload = Object.fromEntries(
                [...fd.entries()].filter(([k]) => k !== 'csrfmiddlewaretoken' && fd.get(k) !== '')
            );
            const fb = el.querySelector('#cartera-crear-feedback');

            try {
                const res = await w.Sintel.Core.Http.request('POST', '/api/v1/clientes/cartera/', payload);
                if (res.ok) {
                    showSuccess(res.status === 201 ? 'Obligación registrada exitosamente.' : 'Obligación ya existente actualizada.');
                    if (w.UIManager?.handleOffcanvas) w.UIManager.handleOffcanvas(el, 'hide');
                    if (state.table) state.table.replaceData();
                    cargarCarteraKPIs();
                } else {
                    const msg = res.data?.detail || res.data?.numero_factura?.[0] || JSON.stringify(res.data);
                    if (fb) { fb.textContent = msg; fb.classList.remove('d-none'); }
                }
            } catch (err) {
                if (fb) { fb.textContent = 'Error de conexión.'; fb.classList.remove('d-none'); }
            } finally {
                if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Registrar Obligación'; }
            }
        });
    }

    function initAbonoForm(el) {
        const form = el.querySelector(DOM.form);
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const uuid = form.dataset.carteraUuid;
            const montoInput = form.querySelector('#abono-monto');
            const monto = parseFloat(montoInput?.value || 0);

            if (isNaN(monto) || monto <= 0) {
                showError('Ingrese un monto de abono valido');
                return;
            }

            const btnGuardar = form.querySelector(DOM.btnGuardar);
            if (btnGuardar) {
                btnGuardar.disabled = true;
                btnGuardar.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Aplicando...';
            }

            try {
                const res = await w.AppCliente.carteraApi.registrarAbono(uuid, { monto: monto }); // BUG FIX: campo es 'monto'
                if (res.ok) {
                    showSuccess('Abono registrado correctamente');
                    if (w.UIManager?.handleOffcanvas) {
                        w.UIManager.handleOffcanvas('#' + DOM.offcanvas, 'hide');
                    }
                    if (state.table) state.table.replaceData();
                    cargarCarteraKPIs();
                    
                    // Notificar cambios para recargar el listado de clientes y sus kpis
                    if (w.ClientesListModule && typeof w.ClientesListModule.reloadTable === 'function') {
                        w.ClientesListModule.reloadTable('clientes');
                    }
                    d.dispatchEvent(new CustomEvent('clienteGuardado'));
                } else {
                    const fb = el.querySelector(DOM.feedback);
                    if (fb) {
                        fb.textContent = res.data?.detail || res.data?.abono || 'Ocurrio un error al registrar el abono.';
                        fb.classList.remove('d-none');
                    }
                }
            } catch (err) {
                log.error('Error guardando abono', err);
                showError('Error de conexion al procesar el abono.');
            } finally {
                if (btnGuardar) {
                    btnGuardar.disabled = false;
                    btnGuardar.innerHTML = '<i class="bi bi-check-circle me-1"></i>Aplicar Pago';
                }
            }
        });
    }

    // ── Notifications ────────────────────────────────────────────────────────
    function showSuccess(msg) {
        if (w.UIManager?.success) w.UIManager.success(msg);
    }

    function showError(msg) {
        if (w.UIManager?.handleError) {
            w.UIManager.handleError({ status: 400, data: { detail: msg } }, 'Clientes');
        } else {
            log.error(msg);
        }
    }

    // ── Events ───────────────────────────────────────────────────────────────
    d.addEventListener('shown.bs.tab', (e) => {
        if (e.target?.dataset?.bsTarget === '#tab-pane-cartera') {
            loadCarteraTable();
        }
    });

    d.body.addEventListener('htmx:afterSettle', (e) => {
        const tid = e.detail?.target?.id;
        if (tid !== DOM.container.substring(1)) return;

        requestAnimationFrame(() => {
            // Offcanvas de abono
            const elAbono = d.getElementById(DOM.offcanvas);
            if (elAbono && w.UIManager?.handleOffcanvas) {
                w.UIManager.handleOffcanvas(elAbono, 'show');
                initAbonoForm(elAbono);
            }
            // Offcanvas de crear nueva obligación
            const elCrear = d.getElementById('offcanvas-crear-cartera');
            if (elCrear && w.UIManager?.handleOffcanvas) {
                w.UIManager.handleOffcanvas(elCrear, 'show');
                initCrearForm(elCrear);
            }
        });
    });

    // Botón "Nueva Obligación" en la toolbar del tab Cartera
    d.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action="nueva-cartera"]');
        if (!btn) return;
        abrirCrearOffcanvas(btn.dataset.clienteUuid || '');
    });

    // Search input
    d.addEventListener('keyup', (e) => {
        if (e.target.matches(DOM.search)) {
            clearTimeout(e.target._t);
            e.target._t = setTimeout(() => {
                if (!state.table) return;
                const q = e.target.value.trim();
                const base = '/api/v1/clientes/cartera/';
                const url = new URL(base, location.origin);
                if (state.filtroEstado) {
                    url.searchParams.set('estado_pago', state.filtroEstado); // BUG FIX: param correcto
                }
                if (q) {
                    url.searchParams.set('search', q);
                }
                state.table.replaceData(url.pathname + url.search);
            }, 300);
        }
    });

    // Expose submodule API (skill: vanilla-js.md §1)
    w.CarteraModule = {
        state,
        loadCarteraTable,
        cargarCarteraKPIs,
        abrirCrearOffcanvas,
        abrirAbonoOffcanvas,
    };
    w.AppCliente.cartera = w.CarteraModule;

    log.info('Module loaded');

})(window, document);
