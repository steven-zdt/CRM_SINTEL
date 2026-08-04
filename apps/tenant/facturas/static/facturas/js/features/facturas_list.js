/**
 * Feature: Listado y Tabulator - Facturas v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (FACTURAS_API_BASE)
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Anti-Zombies: Previene instancias fantasma de Tabulator por recargas HTMX
 * 
 * ⚠️ v2.61.2: Facturas son solo lectura - botón "Ver" carga offcanvas_ver_factura.html
 * ⚠️ v2.61.2: Eliminación corrige URL hash a #facturas y cierra todos los offcanvas
 * ⚠️ v2.61.2: _eliminandoFactura flag para evitar rowClick tras eliminar+refresh
 * ⚠️ v2.61.3: Alineado con backend persisted:True - usa gestor-offcanvas con readonly=true
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.VerDetalleFactura (definido en ver_detalle_factura.js) - Solo lectura
 */
(function(w, d) {
    'use strict';

    const MOD = '[facturas.list]';
    let table = null;
    // ⚠️ v2.61.2: Flag de módulo - previene rowClick durante eliminación (scope compartido)
    let _eliminandoFactura = false;

    // ⚠️ Anti-Zombies v2.60: Singleton global para instancias de Tabulator
    if (window.SintelFacturasTables) {
        Object.values(window.SintelFacturasTables).forEach(tb => {
            if (tb && typeof tb.destroy === 'function') {
                try {
                    tb.destroy();
                } catch (error) {
                    console.warn(`${MOD} Error al destruir instancia zombie:`, error);
                }
            }
        });
    }
    window.SintelFacturasTables = {};

    // Formateador de moneda
    function formatearMoneda(value) {
        if (value === null || value === undefined || value === '') return '$ 0';
        const num = parseFloat(value);
        if (isNaN(num)) return '$ 0';
        return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: 'COP',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(num);
    }

    // ── Helpers de formato ────────────────────────────────────────────────────
    const BADGE_DIAN = {
        'ACEPTADA':  ['bg-success',  'bi-check-circle-fill', 'Aceptada'],
        'ENVIADA':   ['bg-info',     'bi-send-fill',         'Enviada'],
        'BORRADOR':  ['bg-secondary','bi-pencil',            'Borrador'],
        'RECHAZADA': ['bg-danger',   'bi-x-circle-fill',     'Rechazada'],
        'ANULADA':   ['bg-dark',     'bi-slash-circle',      'Anulada'],
    };
    function badgeEstadoDIAN(estado) {
        const [cls, ico, txt] = BADGE_DIAN[estado] || ['bg-secondary', 'bi-question-circle', estado || '---'];
        return `<span class="badge ${cls} badge-sm"><i class="bi ${ico} me-1"></i>${txt}</span>`;
    }
    function badgeEstadoPago(v) {
        if (v === 'PAGADA')       return '<span class="badge bg-success badge-sm"><i class="bi bi-check2-all me-1"></i>Pagada</span>';
        if (v === 'PAGO_PARCIAL') return '<span class="badge bg-warning text-dark badge-sm"><i class="bi bi-clock-history me-1"></i>Parcial</span>';
        return '<span class="badge bg-danger badge-sm"><i class="bi bi-exclamation-circle me-1"></i>Pendiente</span>';
    }
    function _fechaCorta(val) {
        if (!val) return '—';
        try { return new Date(val).toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'2-digit' }); }
        catch (_) { return val; }
    }

    // ── Columnas compactas por naturaleza ────────────────────────────────────
    // Diseño: 7 columnas por tab — sin columnas redundantes de emisor/receptor
    function getColumnsNaturaleza(naturaleza) {
        const isVenta = naturaleza === 'VENTA';
        const S = 'font-size:0.76rem;'; // sub-línea

        return [
            // 1. Número de factura + indicador NC
            {
                title: "Factura",
                field: "numero",
                minWidth: 140,
                widthGrow: 1,
                formatter(cell) {
                    const row = cell.getRow().getData();
                    const num = cell.getValue() || '---';
                    const nc  = row.has_nc ? `<span class="badge bg-warning text-dark ms-1" style="font-size:0.65rem;">NC</span>` : '';
                    const emi = row.fecha_emision ? `<div class="text-muted" style="${S}"><i class="bi bi-calendar2 me-1"></i>${_fechaCorta(row.fecha_emision)}</div>` : '';
                    return `<div class="fw-semibold text-truncate" title="${num}">${num}${nc}</div>${emi}`;
                }
            },
            // 2. Contraparte (Cliente para Venta, Proveedor para Compra)
            {
                title: isVenta ? 'Cliente' : 'Proveedor',
                field: isVenta ? 'receptor_razon_social' : 'emisor_razon_social',
                minWidth: 180,
                widthGrow: 2,
                formatter(cell) {
                    const row   = cell.getRow().getData();
                    const nombre = isVenta ? (row.receptor_razon_social || '---') : (row.emisor_razon_social || '---');
                    const nit    = isVenta ? (row.receptor_nit || '') : (row.emisor_nit || '');
                    const linked = isVenta ? row.cliente_vinculado_info : row.proveedor_vinculado_info;
                    const pin = linked ? '<i class="bi bi-link-45deg text-success me-1"></i>' : '';
                    return `<div class="text-truncate" title="${nombre}">${pin}${nombre}</div>`
                         + (nit ? `<div class="text-muted" style="${S}">NIT: ${nit}</div>` : '');
                }
            },
            // 3. Vencimiento con alerta de mora
            {
                title: "Vencimiento",
                field: "payment_due_date",
                width: 105,
                hozAlign: "center",
                formatter(cell) {
                    const val = cell.getValue() || cell.getRow().getData().fecha_vencimiento;
                    if (!val) return '<span class="text-muted">—</span>';
                    const row  = cell.getRow().getData();
                    const paid = row.estado_pago === 'PAGADA';
                    const hoy  = new Date(); hoy.setHours(0,0,0,0);
                    const vto  = new Date(val); vto.setHours(0,0,0,0);
                    const over = !paid && vto < hoy;
                    const txt  = _fechaCorta(val);
                    return over
                        ? `<span class="text-danger fw-semibold text-nowrap" style="${S}"><i class="bi bi-exclamation-triangle-fill me-1"></i>${txt}</span>`
                        : `<span class="text-nowrap" style="${S}">${txt}</span>`;
                }
            },
            // 4. Total (moneda compacta)
            {
                title: "Total",
                field: "total",
                width: 120,
                hozAlign: "right",
                formatter(cell) {
                    return `<span class="fw-semibold text-nowrap">${formatearMoneda(cell.getValue())}</span>`;
                }
            },
            // 5. Estado DIAN
            {
                title: "DIAN",
                field: "estado",
                width: 105,
                hozAlign: "center",
                formatter(cell) { return badgeEstadoDIAN(cell.getValue()); },
                headerFilter: "select",
                headerFilterParams: { values: { "": "Todos", "ACEPTADA":"Aceptada", "ENVIADA":"Enviada", "BORRADOR":"Borrador", "RECHAZADA":"Rechazada", "ANULADA":"Anulada" } }
            },
            // 6. Estado de pago
            {
                title: "Pago",
                field: "estado_pago",
                width: 100,
                hozAlign: "center",
                formatter(cell) { return badgeEstadoPago(cell.getValue()); },
                headerFilter: "select",
                headerFilterParams: { values: { "": "Todos", "NO_PAGADA":"Pendiente", "PAGO_PARCIAL":"Parcial", "PAGADA":"Pagada" } }
            },
            // 7. Cotización (solo Ventas)
            ...(isVenta ? [{
                title: "Cot.",
                field: "cotizacion_numero",
                width: 90,
                headerSort: false,
                hozAlign: "center",
                formatter(cell) {
                    const num = cell.getValue();
                    if (!num) return '<span class="text-muted">—</span>';
                    return `<span class="badge text-bg-light border" title="${num}" style="font-size:0.7rem;max-width:80px;" class="text-truncate"><i class="bi bi-receipt me-1"></i>${num}</span>`;
                }
            }] : []),
            // 8. Acciones
            {
                title: "",
                headerSort: false,
                hozAlign: "center",
                width: 100,
                formatter(cell) {
                    const id = cell.getRow().getData().uuid;
                    return `<div class="btn-group btn-group-sm"><button class="btn btn-outline-secondary btn-edit-factura" data-id="${id}" title="Editar"><i class="bi bi-pencil"></i></button><button class="btn btn-outline-primary btn-view-factura" data-id="${id}" title="Ver"><i class="bi bi-eye"></i></button><button class="btn btn-outline-danger btn-delete-factura" data-id="${id}" title="Eliminar"><i class="bi bi-trash"></i></button></div>`;
                }
            }
        ];
    }

    // ── Helpers UI por tab ────────────────────────────────────────────────────
    function setTabUI(naturaleza, loading, hasData) {
        const key = naturaleza === 'VENTA' ? 'ventas' : 'compras';
        const spinnerEl  = d.querySelector(`[data-spinner="${key}"]`);
        const gridEl     = d.getElementById(`grid-${key}`);
        const emptyEl    = d.querySelector(`[data-empty-state="${key}"]`);
        if (spinnerEl)  spinnerEl.style.display  = loading ? 'block' : 'none';
        if (gridEl)     gridEl.style.display     = (!loading && hasData !== false) ? 'block' : 'none';
        if (emptyEl)    emptyEl.style.display    = (!loading && hasData === false) ? 'block' : 'none';
    }

    // ── Inicializar Tabulator VENTAS ──────────────────────────────────────────
    // skill: tabulator.md §1 — TabulatorFactory.create()
    function initTabulatorVentas() {
        if (!w.TabulatorFactory) { console.error(`${MOD} TabulatorFactory no disponible`); return; }
        if (!d.getElementById('grid-ventas')) { console.warn(`${MOD} #grid-ventas no encontrado`); return; }

        if (window.SintelFacturasTables.ventas) {
            try { window.SintelFacturasTables.ventas.destroy(); } catch (_) {}
        }

        setTabUI('VENTA', true, null);

        table = w.TabulatorFactory.create(
            '#grid-ventas',
            getVentasUrl(),
            getColumnsNaturaleza('VENTA'),
            { searchInputSelector: '#search-factura', layout: 'fitColumns', rowHeight: 50 }
        );

        if (table) {
            window.SintelFacturasTables.ventas = table;
            // Alias para compatibilidad con código que referencia .main
            window.SintelFacturasTables.main   = table;

            table.on('dataLoaded', (data) => {
                setTabUI('VENTA', false, data.length > 0);
                const badge = d.getElementById('badge-count-ventas');
                if (badge) { badge.textContent = data.length; badge.style.display = data.length ? '' : 'none'; }
            });

            // rowClick — abre detalle (misma lógica existente)
            _bindRowClick(table);

            console.log(`${MOD} Tabulator VENTAS inicializado`);
        } else {
            setTabUI('VENTA', false, false);
        }
    }

    // ── Inicializar Tabulator COMPRAS ─────────────────────────────────────────
    // skill: tabulator.md §6 — lazy init (NO auto-init en tab oculto)
    let _comprasInitialized = false;
    function initTabulatorCompras() {
        if (_comprasInitialized) {
            // Ya inicializado — solo redraw (container antes oculto)
            if (window.SintelFacturasTables.compras?.redraw) {
                window.SintelFacturasTables.compras.redraw(true);
            }
            return;
        }
        if (!w.TabulatorFactory) { console.error(`${MOD} TabulatorFactory no disponible`); return; }
        if (!d.getElementById('grid-compras')) { console.warn(`${MOD} #grid-compras no encontrado`); return; }

        if (window.SintelFacturasTables.compras) {
            try { window.SintelFacturasTables.compras.destroy(); } catch (_) {}
        }

        setTabUI('COMPRA', true, null);

        const tableCompras = w.TabulatorFactory.create(
            '#grid-compras',
            getComprasUrl(),
            getColumnsNaturaleza('COMPRA'),
            { searchInputSelector: '#search-factura', layout: 'fitColumns', rowHeight: 50 }
        );

        if (tableCompras) {
            window.SintelFacturasTables.compras = tableCompras;
            _comprasInitialized = true;

            tableCompras.on('dataLoaded', (data) => {
                setTabUI('COMPRA', false, data.length > 0);
                const badge = d.getElementById('badge-count-compras');
                if (badge) { badge.textContent = data.length; badge.style.display = data.length ? '' : 'none'; }
            });

            _bindRowClick(tableCompras);

            console.log(`${MOD} Tabulator COMPRAS inicializado`);
        } else {
            setTabUI('COMPRA', false, false);
        }
    }

    // ── rowClick reutilizable ─────────────────────────────────────────────────
    function _bindRowClick(tbl) {
        if (typeof tbl.on !== 'function') return;
        tbl.on('rowClick', async (e, row) => {
            if (_eliminandoFactura) return;
            const rowData = row.getData();
            const id = rowData.uuid;
            if (!id) return;
            const path = e.composedPath ? e.composedPath() : (e.path || []);
            const enBotones = path.some(el => el.tagName === 'BUTTON' || (el.classList && el.classList.contains('btn-group')));
            if (enBotones) return;
            try {
                await htmx.ajax('GET', `/api/v1/facturas/gestor-offcanvas/?uuid=${id}&simple=true&readonly=true`, {
                    target: '#offcanvas-container-facturas', swap: 'innerHTML'
                });
                await new Promise(r => setTimeout(r, 100));
                let offcanvasEl = d.getElementById('offcanvas-ver-factura') || d.getElementById('offcanvas-factura');
                if (offcanvasEl && window.bootstrap && window.bootstrap.Offcanvas) {
                    if (w.UIManager?.handleOffcanvas) { w.UIManager.handleOffcanvas(offcanvasEl, 'show'); }
                    else { const prev = bootstrap.Offcanvas.getInstance(offcanvasEl); if (prev) prev.dispose(); new bootstrap.Offcanvas(offcanvasEl).show(); }
                }
            } catch (err) { console.error(`${MOD} Error al abrir detalle:`, err); }
        });
    }

    // ── Helpers de construccion de URLs dinamicas ──
    function getVentasUrl() {
        let url = '/api/v1/facturas/?naturaleza=VENTA';
        const activeBtn = d.querySelector('#filtros-pago-ventas [data-filtro-venta-pago].active');
        if (activeBtn && activeBtn.dataset.filtroVentaPago) {
            url += `&estado_pago=${activeBtn.dataset.filtroVentaPago}`;
        }
        const taxFilter = d.getElementById('filter-tipo-impuesto')?.value;
        if (taxFilter) {
            url += `&tipo_impuesto=${taxFilter}`;
        }
        return url;
    }

    function getComprasUrl() {
        let url = '/api/v1/facturas/?naturaleza=COMPRA';
        const activeBtn = d.querySelector('#filtros-pago-compras [data-filtro-compra-pago].active');
        if (activeBtn && activeBtn.dataset.filtroCompraPago) {
            url += `&estado_pago=${activeBtn.dataset.filtroCompraPago}`;
        }
        const taxFilter = d.getElementById('filter-tipo-impuesto')?.value;
        if (taxFilter) {
            url += `&tipo_impuesto=${taxFilter}`;
        }
        return url;
    }

    // ── Filtros rápidos por estado de pago ────────────────────────────────────
    function initFiltrosPago() {
        // Ventas
        const ctrVentas = d.getElementById('filtros-pago-ventas');
        if (ctrVentas && !ctrVentas.dataset.bound) {
            ctrVentas.dataset.bound = 'true';
            ctrVentas.addEventListener('click', (e) => {
                const btn = e.target.closest('[data-filtro-venta-pago]');
                if (!btn || !window.SintelFacturasTables.ventas) return;
                ctrVentas.querySelectorAll('[data-filtro-venta-pago]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                window.SintelFacturasTables.ventas.replaceData(getVentasUrl());
            });
        }
        // Compras
        const ctrCompras = d.getElementById('filtros-pago-compras');
        if (ctrCompras && !ctrCompras.dataset.bound) {
            ctrCompras.dataset.bound = 'true';
            ctrCompras.addEventListener('click', (e) => {
                const btn = e.target.closest('[data-filtro-compra-pago]');
                if (!btn || !window.SintelFacturasTables.compras) return;
                ctrCompras.querySelectorAll('[data-filtro-compra-pago]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                window.SintelFacturasTables.compras.replaceData(getComprasUrl());
            });
        }
    }

    // ── Filtro por tipo de impuesto ──
    function initFiltroImpuesto() {
        const filterSelect = d.getElementById('filter-tipo-impuesto');
        if (filterSelect && !filterSelect.dataset.bound) {
            filterSelect.dataset.bound = 'true';
            filterSelect.addEventListener('change', () => {
                const tv = window.SintelFacturasTables.ventas;
                if (tv && typeof tv.replaceData === 'function') {
                    tv.replaceData(getVentasUrl());
                }
                const tc = window.SintelFacturasTables.compras;
                if (tc && typeof tc.replaceData === 'function') {
                    tc.replaceData(getComprasUrl());
                }
            });
        }
    }

    // ── shown.bs.tab: lazy init Compras + redraw (skill: tabulator.md §6) ────
    d.addEventListener('shown.bs.tab', (e) => {
        if (e.target?.id === 'tab-compras-btn') {
            initTabulatorCompras();
        }
        if (e.target?.id === 'tab-ventas-btn') {
            if (window.SintelFacturasTables.ventas?.redraw) {
                window.SintelFacturasTables.ventas.redraw(true);
            }
        }
    });

    // ── Backward compat: initTabulator() → ahora inicia ventas ───────────────
    function initTabulator() {
        initTabulatorVentas();
    }

    // ── Crear tabla con rowClick binding (conservado para uso interno) ────────
    function _createTableWithRowClick(gridId, url, columns, opts) {
        const tbl = w.TabulatorFactory.create(gridId, url, columns, opts);
        if (tbl) _bindRowClick(tbl);
        return tbl;
    }

    // Event Delegation para acciones del Grid (cubre #grid-ventas y #grid-compras)
    function initListEvents() {
        const gridElement = d.getElementById('tab-facturas-content');
        if (!gridElement) {
            console.warn(`${MOD} #tab-facturas-content no encontrado para eventos`);
            return;
        }

        gridElement.addEventListener('click', async (e) => {
            // Botón Editar — delega al offcanvas completo (offcanvas_editar_factura.html, simple=false)
            const btnEdit = e.target.closest('.btn-edit-factura');
            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();

                const id = btnEdit.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón editar sin data-id`);
                    return;
                }

                if (w.AppFacturas && typeof w.AppFacturas.cargarOffcanvas === 'function') {
                    w.AppFacturas.cargarOffcanvas(id, false);
                } else {
                    console.error(`${MOD} AppFacturas.cargarOffcanvas no disponible`);
                }
                return;
            }

            // Botón Ver (abre Offcanvas de solo lectura)
            const btnView = e.target.closest('.btn-view-factura');
            if (btnView) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnView.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón sin data-id`);
                    return;
                }

                // ⚠️ Loading state
                const originalHTML = btnView.innerHTML;
                btnView.disabled = true;
                btnView.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // ⚠️ v2.61.2: Cargar template de solo lectura directamente
                    // Primero cargar el template HTML estático
                    const offcanvasContainer = d.getElementById('offcanvas-container-facturas');
                    if (!offcanvasContainer) {
                        console.warn(`${MOD} Contenedor #offcanvas-container-facturas no encontrado`);
                        return;
                    }

                    // ⚠️ HTMX: Cargar template de solo lectura desde el servidor
                    // Usar el endpoint gestor-offcanvas pero con modo solo lectura
                    await htmx.ajax('GET', `/api/v1/facturas/gestor-offcanvas/?uuid=${id}&simple=true&readonly=true`, {
                        target: '#offcanvas-container-facturas',
                        swap: 'innerHTML'
                    });

                    // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
                    await new Promise(resolve => setTimeout(resolve, 100));

                    // ⚠️ v2.61.2: Buscar el offcanvas correcto (puede ser offcanvas-factura o offcanvas-ver-factura)
                    let offcanvasEl = d.getElementById('offcanvas-ver-factura');
                    if (!offcanvasEl) {
                        // Fallback: buscar offcanvas-factura y cambiar su ID
                        offcanvasEl = d.getElementById('offcanvas-factura');
                        if (offcanvasEl) {
                            offcanvasEl.id = 'offcanvas-ver-factura';
                            offcanvasEl.setAttribute('aria-labelledby', 'offcanvas-ver-factura-label');
                        }
                    }

                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        // Cargar datos ANTES de mostrar el offcanvas
                        if (w.VerDetalleFactura && typeof w.VerDetalleFactura.ver === 'function') {
                            await w.VerDetalleFactura.ver(id);
                        } else if (typeof window.VerDetalleFactura !== 'undefined' && typeof window.VerDetalleFactura.ver === 'function') {
                            await window.VerDetalleFactura.ver(id);
                        } else if (typeof window.verDetalleFactura === 'function') {
                            await window.verDetalleFactura(id);
                        } else {
                            console.warn(`${MOD} Función verDetalleFactura no disponible.`);
                            try {
                                const response = await w.http('GET', `/api/v1/facturas/${id}/`);
                                if (response.ok && response.data) {
                                    console.log(`${MOD} Datos cargados directamente desde API (fallback)`);
                                }
                            } catch (error) {
                                console.error(`${MOD} Error en fallback de carga de datos:`, error);
                            }
                        }

                        // UIManager gestiona dispose + backdrops + show (AGENTS.md §26)
                        if (w.UIManager?.handleOffcanvas) {
                            w.UIManager.handleOffcanvas(offcanvasEl, 'show');
                        } else {
                            const prev = bootstrap.Offcanvas.getInstance(offcanvasEl);
                            if (prev) prev.dispose();
                            d.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
                            d.body.style.overflow = '';
                            new bootstrap.Offcanvas(offcanvasEl).show();
                        }
                    } else {
                        console.warn(`${MOD} No se pudo abrir el Offcanvas: elemento no encontrado o Bootstrap no disponible`);
                    }
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al cargar el detalle de la factura');
                    }
                } finally {
                    // Restaurar estado del botón
                    btnView.disabled = false;
                    btnView.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-factura');
            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnDelete.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón eliminar sin data-id`);
                    return;
                }

                // Confirmación
                if (!confirm('¿Está seguro de eliminar esta factura? Esta acción no se puede deshacer.')) {
                    return;
                }

                // ⚠️ v2.61.2: Activar flag para prevenir rowClick durante eliminación
                _eliminandoFactura = true;

                // ⚠️ Loading state
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // [WARNING] v2.61.2: Usar Core API facade
                    const res = await w.http('DELETE', `/api/v1/facturas/${id}/`);
                    
                    if (res.ok) {
                        // ⚠️ v2.61.2: Cerrar cualquier offcanvas abierto que muestre esta factura
                        const offcanvasVerFactura = d.getElementById('offcanvas-ver-factura');
                        const offcanvasFactura = d.getElementById('offcanvas-factura');
                        
                        if (offcanvasVerFactura && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                            const instance = bootstrap.Offcanvas.getInstance(offcanvasVerFactura);
                            if (instance) {
                                instance.hide();
                            }
                        }
                        if (offcanvasFactura && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                            const instance = bootstrap.Offcanvas.getInstance(offcanvasFactura);
                            if (instance) {
                                instance.hide();
                            }
                        }
                        
                        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                            w.SintelFeedback.success('Factura eliminada correctamente');
                        }
                        
                        // ⚠️ v2.61.2: Recargar grid y asegurar que estamos en la pestaña correcta
                        const _activeTable = window.SintelFacturasTables.ventas || window.SintelFacturasTables.compras;
                        if (_activeTable && typeof _activeTable.replaceData === 'function') {
                            _activeTable.replaceData().then(() => {
                                setTimeout(() => { _eliminandoFactura = false; }, 500);
                            });
                        } else {
                            setTimeout(() => { _eliminandoFactura = false; }, 500);
                        }
                        
                        // ⚠️ v2.61.2: Asegurar que estamos en workspace/#facturas
                        if (w.location && w.location.hash !== '#facturas') {
                            w.location.hash = '#facturas';
                        }
                    } else {
                        // Si falla la eliminación, desactivar flag
                        _eliminandoFactura = false;
                        
                        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                            w.UIManager.handleError(res, MOD);
                        } else {
                            alert('Error al eliminar la factura');
                        }
                    }
                } catch (error) {
                    // Si hay error, desactivar flag
                    _eliminandoFactura = false;
                    
                    console.error(`${MOD} Error al eliminar factura:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al eliminar la factura');
                    }
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
                return;
            }
        });

        console.log(`${MOD} Event delegation configurado`);
    }

    // Recarga Reactiva: refrescar ambas tablas tras guardar factura
    function initEventListeners() {
        d.addEventListener('facturaGuardada', () => {
            const tv = window.SintelFacturasTables.ventas;
            const tc = window.SintelFacturasTables.compras;
            if (tv?.replaceData) tv.replaceData();
            if (tc?.replaceData) tc.replaceData();
            loadSummary();
            console.log(`${MOD} Grids refrescados tras guardar factura`);
        });

        console.log(`${MOD} Event listeners configurados`);
    }

    // Inicialización principal
    function init() {
        console.log(`${MOD} Inicializando módulo de listado...`);

        // ⚠️ Lazy Loading: Solo inicializar cuando el tab esté visible
        const tabElement = d.querySelector('#tab-facturas');
        if (tabElement) {
            // Usar DOMUtils.onVisibleOnce si está disponible
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce(tabElement.id ? '#' + tabElement.id : tabElement, () => {
                    initTabulatorVentas();
                    initListEvents();
                    initEventListeners();
                    initFiltrosPago();
                    initFiltroImpuesto();
                    loadSummary();
                });
            } else {
                initTabulatorVentas();
                initListEvents();
                initEventListeners();
                initFiltrosPago();
                initFiltroImpuesto();
                loadSummary();
            }
        } else {
            initTabulatorVentas();
            initListEvents();
            initEventListeners();
            initFiltrosPago();
            initFiltroImpuesto();
            loadSummary();
        }
    }

    // ⚠️ HTMX: Limpiar instancias zombie en recargas
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:beforeSwap', (event) => {
            // Si se está recargando el contenedor principal, destruir instancias
            if (event.detail.target.id === 'tab-facturas-content' ||
                event.detail.target.closest?.('#tab-facturas-content')) {
                ['ventas', 'compras'].forEach(key => {
                    try {
                        window.SintelFacturasTables[key]?.destroy();
                        delete window.SintelFacturasTables[key];
                    } catch (_) {}
                });
                window.SintelFacturasTables._comprasInitialized = false;
            }
        });
    }

    // Debounce: evita que llamadas simultáneas generen requests duplicados
    let _summaryDebounce = null;
    function loadSummary() {
        clearTimeout(_summaryDebounce);
        _summaryDebounce = setTimeout(_doLoadSummary, 150);
    }

    /**
     * Cargar y actualizar el resumen de facturación (Ventas Netas y Compras Netas)
     * Sincroniza con GET /api/v1/facturas/summary/
     */
    async function _doLoadSummary() {
        try {
            let summaryRes;
            
            // Intentar usar facturasAPI si está disponible
            if (w.facturasAPI && typeof w.facturasAPI.getSummary === 'function') {
                summaryRes = await w.facturasAPI.getSummary();
            } else if (w.http && typeof w.http === 'function') {
                summaryRes = await w.http('GET', '/api/v1/facturas/summary/');
            } else {
                console.warn(`${MOD} No hay API disponible para cargar summary`);
                return;
            }

            if (!summaryRes.ok) {
                console.error(`${MOD} Error al cargar summary:`, summaryRes);
                return;
            }

            const summary = summaryRes.data || {};
            const ventas = summary.ventas || {};
            const compras = summary.compras || {};

            // Formatear valores
            function formatMoney(value) {
                if (!value || value === '0.00' || value === '0') return '$ 0,00';
                const num = parseFloat(value);
                if (isNaN(num)) return '$ 0,00';
                return new Intl.NumberFormat('es-CO', {
                    style: 'currency',
                    currency: 'COP',
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 2
                }).format(num);
            }

            // Actualizar Ventas Netas
            const ventasTotalEl = d.getElementById('ventas-total-neto');
            const ventasSubtotalEl = d.getElementById('ventas-subtotal-neto');
            const ventasImpuestosEl = d.getElementById('ventas-impuestos-neto');
            
            if (ventasTotalEl) {
                ventasTotalEl.textContent = formatMoney(ventas.total_neto || '0.00');
            }
            if (ventasSubtotalEl) {
                ventasSubtotalEl.textContent = formatMoney(ventas.subtotal_neto || '0.00');
            }
            if (ventasImpuestosEl) {
                ventasImpuestosEl.textContent = formatMoney(ventas.impuestos_neto || '0.00');
            }

            // Actualizar Compras Netas
            const comprasTotalEl = d.getElementById('compras-total-neto');
            const comprasSubtotalEl = d.getElementById('compras-subtotal-neto');
            const comprasImpuestosEl = d.getElementById('compras-impuestos-neto');
            
            if (comprasTotalEl) {
                comprasTotalEl.textContent = formatMoney(compras.total_neto || '0.00');
            }
            if (comprasSubtotalEl) {
                comprasSubtotalEl.textContent = formatMoney(compras.subtotal_neto || '0.00');
            }
            if (comprasImpuestosEl) {
                comprasImpuestosEl.textContent = formatMoney(compras.impuestos_neto || '0.00');
            }

            console.log(`${MOD} Summary actualizado: Ventas=${ventas.total_neto || '0.00'}, Compras=${compras.total_neto || '0.00'}`);
        } catch (error) {
            console.error(`${MOD} Error al cargar summary:`, error);
        }
    }

    // Auto-inicializar cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ⚠️ API Pública: Exponer funciones para uso externo
    w.FacturasListModule = {
        init,
        refresh: () => {
            const tv = window.SintelFacturasTables.ventas;
            const tc = window.SintelFacturasTables.compras;
            if (tv?.replaceData) tv.replaceData();
            if (tc?.replaceData) tc.replaceData();
            loadSummary();
        },
        getTable: () => table,
        loadSummary
    };

    if (!w.FacturasModule) {
        w.FacturasModule = {
            refresh: () => {
                const tv = window.SintelFacturasTables.ventas;
                const tc = window.SintelFacturasTables.compras;
                if (tv?.replaceData) tv.replaceData();
                if (tc?.replaceData) tc.replaceData();
            }
        };
    }

})(window, document);
