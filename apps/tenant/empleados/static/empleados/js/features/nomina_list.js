// @ts-nocheck
/**
 * Nomina List Module — Tabulator centralizado de Nómina v3.9
 *
 * Columnas: Estándar Colombia (Devengos / Deducciones / Neto / Contable / Acciones)
 * Namespace: window.Sintel.Empleados.NominaList
 */
(function (w, d) {
    'use strict';

    w.Sintel = w.Sintel || {};
    w.Sintel.Empleados = w.Sintel.Empleados || {};

    const MOD = '[NominaList]';
    let table = null;
    const API = () => w.Sintel.Empleados.API;

    // ── Formatters ────────────────────────────────────────────────────────────

    const COP = (val) => {
        const n = parseFloat(val) || 0;
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP', minimumFractionDigits: 0
        }).format(n);
    };

    const monedaCelda = (cell) => {
        const v = parseFloat(cell.getValue()) || 0;
        const color = v < 0 ? 'text-danger' : '';
        return `<span class="${color}">${COP(v)}</span>`;
    };

    // ── Acciones ──────────────────────────────────────────────────────────────

    function handleCellAction(e, cell) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        switch (action) {
            case 'historial':
                abrirHistorial(btn.dataset.empleadoUuid);
                break;
            case 'anular':
                anularDevengo(btn.dataset.uuid);
                break;
            case 'asignar-cuenta':
                abrirOffcanvasCuenta(btn.dataset);
                break;
        }
    }

    async function abrirHistorial(empleadoUuid) {
        if (!empleadoUuid) return;
        const api = API();
        if (!api) return;
        try {
            await htmx.ajax('GET', api.empleados.historial(empleadoUuid), {
                target: '#offcanvas-container-nominas',
                swap: 'innerHTML'
            });
        } catch (err) {
            console.error(`${MOD} Error cargando historial:`, err);
            w.SintelFeedback?.error('Error al cargar el historial');
        }
    }

    async function anularDevengo(devengoUuid) {
        if (!devengoUuid) return;
        if (!confirm('¿Confirma que desea anular esta nómina? Esta acción no se puede deshacer.')) return;
        const api = API();
        try {
            const resp = await w.Sintel.Empleados.request(api.devengos.anular(devengoUuid), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': d.querySelector('[name=csrfmiddlewaretoken]')?.value
                }
            });
            if (resp?.ok) {
                w.SintelFeedback?.success('Nómina anulada correctamente');
                if (table) table.replaceData();
            } else {
                w.SintelFeedback?.error(resp?.data?.error || 'Error al anular la nómina');
            }
        } catch (err) {
            console.error(`${MOD} Error anulando:`, err);
            w.SintelFeedback?.error('Error de conexión');
        }
    }

    // ── Columnas ──────────────────────────────────────────────────────────────

    function getColumnas() {
        return [
            // ── Empleado ───────────────────────────────────────────────────
            {
                title: 'Empleado',
                field: 'empleado_nombre',
                minWidth: 170,
                headerFilter: 'input',
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const nom  = cell.getValue() || '—';
                    const doc  = data.empleado_documento || '';
                    return `<div class="fw-semibold lh-sm">${nom}</div>
                            <div class="small text-muted">${doc}</div>`;
                },
            },
            {
                title: 'Cargo',
                field: 'contrato_cargo',
                minWidth: 130,
                formatter: (cell) => `<span class="small">${cell.getValue() || '—'}</span>`,
                headerFilter: 'input',
            },

            // ── Período completo ───────────────────────────────────────────
            {
                title: 'Período',
                field: 'fecha_inicio',
                width: 200,
                hozAlign: 'center',
                headerHozAlign: 'center',
                headerFilter: 'input',
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    const fi   = data.fecha_inicio;
                    const ff   = data.fecha_fin;
                    const pm   = data.periodo_mes || '';
                    if (fi && ff) {
                        return `<div class="small lh-sm fw-semibold">${fi}</div>
                                <div class="small text-muted lh-sm">al ${ff}</div>`;
                    }
                    return `<span class="small">${pm || '—'}</span>`;
                },
            },
            {
                title: 'Días',
                field: 'dias_laborados',
                width: 65,
                hozAlign: 'center',
                headerHozAlign: 'center',
                formatter: (cell) => {
                    const v = parseFloat(cell.getValue()) || 0;
                    return `<span class="badge bg-primary-subtle text-primary border border-primary-subtle">${v}</span>`;
                },
            },

            // ── Devengos ───────────────────────────────────────────────────
            {
                title: 'Salario Base',
                field: 'salario_base',
                width: 130,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: monedaCelda,
            },
            {
                title: 'H.E. y Recargos',
                field: 'valor_horas_extras',
                width: 120,
                hozAlign: 'right',
                headerHozAlign: 'right',
                formatter: (cell) => {
                    const v = parseFloat(cell.getValue()) || 0;
                    return v > 0
                        ? `<span class="text-warning fw-semibold">${COP(v)}</span>`
                        : '<span class="text-muted">—</span>';
                },
            },

            // ── Neto ───────────────────────────────────────────────────────
            {
                title: 'Neto a Pagar',
                field: 'neto_pagar',
                width: 140,
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

            // ── Acciones ───────────────────────────────────────────────────
            {
                title: 'Acciones',
                width: 130,
                hozAlign: 'center',
                headerHozAlign: 'center',
                headerSort: false,
                frozen: true,
                formatter: (cell) => {
                    const data         = cell.getRow().getData();
                    const uuid         = data.uuid;
                    const empleadoUuid = data.empleado_uuid || '';
                    const anulado      = data.anulado;
                    const cuentaUuid   = data.cuenta_contable_uuid || '';

                    let html = '<div class="btn-group btn-group-sm">';

                    // Historial del empleado
                    html += `<button data-action="historial" data-empleado-uuid="${empleadoUuid}"
                                     class="btn btn-outline-secondary" title="Historial de nóminas del empleado">
                                 <i class="bi bi-clock-history"></i>
                             </button>`;

                    // Asignar / cambiar cuenta contable
                    const cuentaClass = cuentaUuid ? 'btn-outline-success' : 'btn-outline-warning';
                    const cuentaTitle = cuentaUuid ? 'Cambiar cuenta contable' : 'Asignar cuenta contable';
                    html += `<button data-action="asignar-cuenta"
                                     data-devengo-uuid="${uuid}"
                                     data-devengo-neto="${data.neto_pagar}"
                                     data-devengo-empleado="${data.empleado_nombre}"
                                     data-devengo-periodo="${data.periodo_mes}"
                                     data-cuenta-uuid="${cuentaUuid}"
                                     class="btn ${cuentaClass}" title="${cuentaTitle}">
                                 <i class="bi bi-journal-check"></i>
                             </button>`;

                    // Anular (solo si activa)
                    if (!anulado) {
                        html += `<button data-action="anular" data-uuid="${uuid}"
                                         class="btn btn-outline-danger" title="Anular nómina">
                                     <i class="bi bi-slash-circle"></i>
                                 </button>`;
                    }

                    html += '</div>';
                    return html;
                },
                cellClick: (e, cell) => handleCellAction(e, cell),
            },
        ];
    }

    // ── Inicializar tabla ─────────────────────────────────────────────────────

    async function init(gridSelector) {
        const el = d.querySelector(gridSelector);
        if (!el) {
            console.warn(`${MOD} Container ${gridSelector} no encontrado`);
            return;
        }

        if (table) {
            console.log(`${MOD} Tabla ya inicializada, omitiendo...`);
            return table;
        }

        const api = API();
        if (!api) { console.error(`${MOD} API no disponible`); return; }

        table = new Tabulator(el, {
            ajaxURL: api.devengos.list,
            ajaxParams: {},
            ajaxResponse: (url, params, response) => response.results ?? response,
            layout: 'fitData',
            responsiveLayout: false,
            pagination: 'remote',
            paginationSize: 20,
            paginationSizeSelector: [10, 20, 50],
            sortMode: 'remote',
            filterMode: 'remote',
            columns: getColumnas(),
            locale: 'es-co',
            langs: {
                'es-co': {
                    pagination: { first: '«', prev: '‹', next: '›', last: '»' }
                }
            },
            placeholder: '<div class="text-center text-muted py-4"><i class="bi bi-cash-coin fs-3"></i><p class="mt-2">Sin nóminas registradas</p></div>',
        });

        // Búsqueda delegada
        const searchEl = d.querySelector('#search-nomina');
        if (searchEl) {
            let debounce;
            searchEl.addEventListener('input', () => {
                clearTimeout(debounce);
                debounce = setTimeout(() => {
                    const q = searchEl.value.trim();
                    if (!q) {
                        if (table) table.clearFilter();
                        return;
                    }
                    if (table) table.setFilter([
                        [
                            { field: 'empleado_nombre', type: 'like', value: q },
                            { field: 'periodo_mes',     type: 'like', value: q },
                        ]
                    ]);
                }, 350);
            });
        }

        return table;
    }

    function _mostrarOffcanvasSeguro(el) {
        if (!el || !w.bootstrap?.Offcanvas) return;
        d.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
        d.body.classList.remove('overflow-hidden', 'modal-open');
        d.body.style.overflow = '';
        d.body.style.paddingRight = '';
        const oc = bootstrap.Offcanvas.getOrCreateInstance(el);
        oc.show();
    }

    // ── Offcanvas Cuenta Contable (desde lista) ────────────────────────────────

    function abrirOffcanvasCuenta(dataset) {
        const oc = d.getElementById('offcanvas-asignar-cuenta-devengo');
        if (!oc) { console.error(`${MOD} Offcanvas #offcanvas-asignar-cuenta-devengo no encontrado`); return; }

        const setTxt = (id, val) => { const el = d.getElementById(id); if (el) el.textContent = val || '—'; };
        setTxt('oc-cuenta-empleado', dataset.devengoEmpleado);
        setTxt('oc-cuenta-periodo',  dataset.devengoPeriodo);
        setTxt('oc-cuenta-neto',     new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(parseFloat(dataset.devengoNeto) || 0));

        const devengoInput = d.getElementById('oc-cuenta-devengo-uuid');
        if (devengoInput) devengoInput.value = dataset.devengoUuid || '';

        const busquedaEl = d.getElementById('oc-cuenta-busqueda');
        const uuidEl     = d.getElementById('oc-cuenta-uuid-selected');
        const resultados = d.getElementById('oc-cuenta-resultados');
        if (busquedaEl) busquedaEl.value = '';
        if (uuidEl)     uuidEl.value     = dataset.cuentaUuid || '';
        if (resultados) resultados.innerHTML = '';

        _mostrarOffcanvasSeguro(oc);
    }

    // ── Guardar cuenta contable (offcanvas lateral) ────────────────────────────

    async function guardarCuentaContable() {
        const devengoUuid = d.getElementById('oc-cuenta-devengo-uuid')?.value;
        const cuentaUuid  = d.getElementById('oc-cuenta-uuid-selected')?.value;

        if (!devengoUuid) { w.SintelFeedback?.error('Devengo no identificado'); return; }
        if (!cuentaUuid)  { w.SintelFeedback?.error('Selecciona una cuenta contable'); return; }

        const api = API();
        const url = api.devengos.asignarCuenta(devengoUuid);

        const btn = d.getElementById('btn-guardar-cuenta-devengo');
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Guardando...'; }

        try {
            const resp = await w.Sintel.Empleados.request(url, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': d.querySelector('[name=csrfmiddlewaretoken]')?.value
                },
                body: JSON.stringify({ cuenta_contable_uuid: cuentaUuid })
            });

            if (resp?.ok) {
                w.SintelFeedback?.success('Cuenta contable asignada correctamente');
                bootstrap.Offcanvas.getInstance(d.getElementById('offcanvas-asignar-cuenta-devengo'))?.hide();
                if (table) table.replaceData();
            } else {
                w.SintelFeedback?.error('Error al guardar la cuenta contable');
            }
        } catch (err) {
            console.error(`${MOD} Error guardando cuenta:`, err);
            w.SintelFeedback?.error('Error de conexión');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Guardar'; }
        }
    }

    // ── Búsqueda de cuentas (offcanvas lateral) ────────────────────────────────

    function initBuscadorCuentas() {
        const busquedaEl = d.getElementById('oc-cuenta-busqueda');
        const listaEl    = d.getElementById('oc-cuenta-resultados');
        const uuidEl     = d.getElementById('oc-cuenta-uuid-selected');
        const labelEl    = d.getElementById('oc-cuenta-label-selected');
        if (!busquedaEl || !listaEl || !uuidEl) return;

        let debounce;
        busquedaEl.addEventListener('input', () => {
            clearTimeout(debounce);
            const q = busquedaEl.value.trim();
            if (q.length < 2) { listaEl.innerHTML = ''; return; }
            debounce = setTimeout(() => buscarCuentas(q), 300);
        });

        async function buscarCuentas(q) {
            const api = API();
            if (!api) return;
            try {
                const resp = await w.Sintel.Empleados.request(api.contabilidad.search(q));
                if (!resp?.ok) return;
                const results = resp.data?.results ?? resp.data ?? [];
                renderResultados(results);
            } catch (err) {
                console.error(`${MOD} Error buscando cuentas:`, err);
            }
        }

        function renderResultados(cuentas) {
            listaEl.innerHTML = '';
            if (!cuentas.length) {
                listaEl.innerHTML = '<div class="list-group-item text-muted small">Sin resultados</div>';
                return;
            }
            cuentas.slice(0, 10).forEach(c => {
                const item = d.createElement('button');
                item.type = 'button';
                item.className = 'list-group-item list-group-item-action py-2 small';
                item.innerHTML = `<span class="fw-bold text-primary me-2">${c.codigo || ''}</span>${c.nombre || ''}`;
                item.addEventListener('click', () => {
                    uuidEl.value = c.uuid;
                    if (labelEl) labelEl.textContent = `${c.codigo} — ${c.nombre}`;
                    busquedaEl.value = `${c.codigo} — ${c.nombre}`;
                    listaEl.innerHTML = '';
                });
                listaEl.appendChild(item);
            });
        }

        const btnGuardar = d.getElementById('btn-guardar-cuenta-devengo');
        if (btnGuardar) btnGuardar.addEventListener('click', guardarCuentaContable);
    }

    d.addEventListener('show.bs.offcanvas', (e) => {
        if (e.target?.id === 'offcanvas-asignar-cuenta-devengo') {
            initBuscadorCuentas();
        }
    });

    // ── Export ────────────────────────────────────────────────────────────────

    function reload() {
        if (table) table.replaceData();
    }

    w.Sintel.Empleados.NominaList = { init, guardarCuentaContable, reload };

})(window, document);
