/**
 * Feature: Ledger Universal — Movimientos Recientes (Timeline Unificado) v3.9.0
 * Consolida Productos (Kardex), Activos Fijos (Eventos) y Servicios (Historial).
 * Endpoint: GET /api/v1/inventario/movimientos/timeline/
 * Dependencias: TabulatorFactory, Sintel.Core.Http (F32.7), w.SintelFeedback, htmx, bootstrap
 */
(function(w, d) {
    'use strict';

    const MOD = '[movimientos.list.v390]';

    // Abre un offcanvas de forma segura, limpiando backdrops huerfanos primero.
    function mostrarOffcanvasSeguro(el) {
        // FE-A5: delega al helper SSoT (core/js/common/offcanvas.helper.js).
        return w.Sintel?.Core?.mostrarOffcanvasSeguro(el);
    }
    const GRID_ID = '#grid-movimientos';
    const SEARCH_ID = '#search-movimiento';
    const API_URL = '/api/v1/inventario/movimientos/timeline/';
    const API_MOV = '/api/v1/inventario/movimientos';
    const API_HIST = '/api/v1/inventario/historial-servicios';
    let table = null;

    w.SintelInventarioTables = w.SintelInventarioTables || {};
    if (w.SintelInventarioTables.movimientos?.destroy) {
        try { w.SintelInventarioTables.movimientos.destroy(); } catch (_) {}
    }

    // -----------------------------------------------------------------------
    // Helpers de formato
    // -----------------------------------------------------------------------

    function fmtFecha(val) {
        if (!val) return '-';
        try {
            // Acepta tanto 'YYYY-MM-DD' como ISO datetime
            const d = new Date(val.length === 10 ? val + 'T00:00:00' : val);
            return d.toLocaleString('es-CO');
        } catch (_) { return val; }
    }

    function fmtMoneda(val) {
        const n = parseFloat(val) || 0;
        // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
        if (w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
            return w.DOMUtils.formatCurrency(n, { minimumFractionDigits: 0 });
        }
        return new Intl.NumberFormat('es-CO', {
            style: 'currency', currency: 'COP', minimumFractionDigits: 0
        }).format(n);
    }

    function badgeModulo(modulo) {
        if (modulo === 'PRODUCTO')    return '<span class="badge bg-success">Producto</span>';
        if (modulo === 'ACTIVO_FIJO') return '<span class="badge bg-warning text-dark">Activo</span>';
        if (modulo === 'SERVICIO')    return '<span class="badge bg-info text-dark">Servicio</span>';
        return '<span class="badge bg-secondary">' + (modulo || '-') + '</span>';
    }

    function badgeTipoAccion(tipo, tipoDisplay) {
        const label = tipoDisplay || tipo || '-';
        let cls = 'bg-secondary';
        if (tipo && tipo.includes('ENTRADA')) cls = 'bg-success';
        else if (tipo && tipo.includes('SALIDA')) cls = 'bg-danger';
        else if (tipo && (tipo.includes('TRASLADO') || tipo.includes('ASIGNACION'))) cls = 'bg-warning text-dark';
        else if (tipo && tipo.includes('BAJA')) cls = 'bg-dark';
        else if (tipo === 'VENTA_SERVICIO') cls = 'bg-info text-dark';
        return '<span class="badge ' + cls + '">' + label + '</span>';
    }

    // -----------------------------------------------------------------------
    // Columnas del Ledger Universal
    // -----------------------------------------------------------------------

    function getColumns() {
        return [
            {
                title: 'Fecha',
                field: 'fecha',
                formatter: function(cell) { return fmtFecha(cell.getValue()); },
                width: 145
            },
            {
                title: 'Modulo',
                field: 'modulo_origen',
                formatter: function(cell) { return badgeModulo(cell.getValue()); },
                width: 100,
                headerFilter: 'list',
                headerFilterParams: {
                    values: { '': 'Todos', 'PRODUCTO': 'Producto', 'ACTIVO_FIJO': 'Activo', 'SERVICIO': 'Servicio' }
                }
            },
            {
                title: 'Item',
                field: 'item_nombre',
                formatter: function(cell) {
                    const d = cell.getRow().getData();
                    const codigo = d.item_codigo
                        ? '<span class="text-muted me-1">[' + d.item_codigo + ']</span>'
                        : '';
                    const nombre = d.item_nombre || '<span class="text-muted">-</span>';
                    return codigo + '<strong>' + nombre + '</strong>';
                },
                minWidth: 200,
                headerFilter: 'input'
            },
            {
                title: 'Transaccion',
                field: 'tipo_accion',
                formatter: function(cell) {
                    const d = cell.getRow().getData();
                    return badgeTipoAccion(d.tipo_accion, d.tipo_accion_display);
                },
                width: 155
            },
            {
                title: 'Impacto',
                field: 'cantidad',
                formatter: function(cell) {
                    const d = cell.getRow().getData();
                    if (d.modulo_origen === 'SERVICIO') {
                        const val = parseFloat(d.valor_costo) || 0;
                        return '<span class="text-info">' + fmtMoneda(val) + '</span>';
                    }
                    if (d.modulo_origen === 'ACTIVO_FIJO') {
                        return '<span class="text-muted">Evento</span>';
                    }
                    const cant = parseFloat(d.cantidad) || 0;
                    return cant.toFixed(3);
                },
                width: 110,
                hozAlign: 'right'
            },
            {
                title: 'Referencia',
                field: 'referencia',
                formatter: function(cell) {
                    const v = cell.getValue();
                    return v ? String(v) : '<span class="text-muted">-</span>';
                },
                width: 145
            },
            {
                title: 'Acciones',
                field: 'uuid',
                formatter: function(cell) {
                    const row = cell.getRow().getData();
                    const uuid = row.uuid;
                    const modulo = row.modulo_origen;
                    const verBtn = '<button class="btn btn-outline-info btn-km-ver" data-uuid="' + uuid + '" data-modulo="' + modulo + '" title="Ver detalle"><i class="bi bi-eye"></i></button>';
                    const delBtn = '<button class="btn btn-outline-danger btn-km-eliminar" data-uuid="' + uuid + '" data-modulo="' + modulo + '" title="Eliminar"><i class="bi bi-trash"></i></button>';
                    if (modulo === 'SERVICIO') {
                        // Servicio: ver + proyBtn/Badge + eliminar (sin editar — no hay form de edicion)
                        let proyPart = '';
                        if (row.proyecto_uuid) {
                            proyPart = '<button class="btn btn-outline-success btn-km-proyecto-link" data-uuid="' + row.proyecto_uuid + '" title="Proyecto: ' + (row.proyecto_nombre || 'Ver Proyecto') + '"><i class="bi bi-folder-check"></i></button>';
                        } else {
                            proyPart = '<button class="btn btn-outline-success btn-km-crear-proyecto" data-uuid="' + uuid + '" title="Crear Proyecto"><i class="bi bi-plus-circle"></i></button>';
                        }
                        return '<div class="btn-group btn-group-sm">' + verBtn + proyPart + delBtn + '</div>';
                    }
                    const editBtn = '<button class="btn btn-outline-primary btn-km-editar" data-uuid="' + uuid + '" title="Editar"><i class="bi bi-pencil"></i></button>';
                    return '<div class="btn-group btn-group-sm">' + verBtn + editBtn + delBtn + '</div>';
                },
                width: 160,
                headerSort: false,
                resizable: false,
                hozAlign: 'center',
                responsive: 0,
                frozen: true
            }
        ];
    }

    // -----------------------------------------------------------------------
    // Inicializar tabla
    // -----------------------------------------------------------------------

    function initTable() {
        const el = d.querySelector(GRID_ID);
        if (!el || !w.TabulatorFactory?.create) return null;

        table = w.TabulatorFactory.create(GRID_ID, API_URL, getColumns(), {
            searchInputSelector: SEARCH_ID,
            pagination: true,
            paginationMode: 'remote',
            paginationSize: 15,
            paginationSizeSelector: [10, 15, 25, 50],
            layout: 'fitDataFill',
            responsiveLayout: false,
            resizeColumns: false,
            placeholder: 'No hay movimientos registrados',
            locale: 'es'
        });

        w.SintelInventarioTables.movimientos = table;
        initListEvents();
        return table;
    }

    // -----------------------------------------------------------------------
    // Acciones: Ver, Editar, Eliminar
    // -----------------------------------------------------------------------

    async function abrirDetalle(uuid, modulo) {
        if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) return;
        try {
            const apiBase = modulo === 'SERVICIO' ? API_HIST : API_MOV;
            const res = await w.Sintel.Core.Http.request('GET', apiBase + '/' + uuid + '/');
            if (!res.ok) { mostrarError('No se pudo cargar el detalle.'); return; }
            const m = res.data;

            const itemNombre = m.item_nombre || m.producto_nombre || m.activo_fijo_nombre
                || (m.servicio ? (m.servicio.nombre || m.servicio_nombre) : '') || '-';
            const itemCodigo = m.item_codigo || m.producto_codigo || m.activo_fijo_codigo
                || (m.servicio ? (m.servicio.codigo || '') : '') || '';

            const badgeMod = badgeModulo(modulo);
            const tipoDisplay = m.tipo_accion_display || m.tipo_display || m.tipo || '-';

            const html = '<dl class="row mb-0 small">'
                + '<dt class="col-5">Modulo</dt><dd class="col-7">' + badgeMod + '</dd>'
                + '<dt class="col-5">Item</dt><dd class="col-7">' + (itemCodigo ? '[' + itemCodigo + '] ' : '') + itemNombre + '</dd>'
                + '<dt class="col-5">Transaccion</dt><dd class="col-7">' + tipoDisplay + '</dd>'
                + '<dt class="col-5">Cantidad</dt><dd class="col-7">' + (m.cantidad || '-') + '</dd>'
                + '<dt class="col-5">Valor / Costo</dt><dd class="col-7">' + fmtMoneda(m.costo_unitario || m.valor_cobrado || 0) + '</dd>'
                + '<dt class="col-5">Referencia</dt><dd class="col-7">' + (m.origen_referencia || m.referencia || '-') + '</dd>'
                + '<dt class="col-5">Destino</dt><dd class="col-7">' + (m.cliente_referencia || '-') + '</dd>'
                + '<dt class="col-5">Observaciones</dt><dd class="col-7">' + (m.observaciones || '-') + '</dd>'
                + '<dt class="col-5">Fecha</dt><dd class="col-7">' + fmtFecha(m.created_at || m.fecha_registro || '') + '</dd>'
                + '</dl>';

            const container = d.getElementById('offcanvas-container-movimientos');
            if (container) {
                container.innerHTML = '<div class="offcanvas offcanvas-end show" tabindex="-1" id="offcanvas-movimiento-detalle" style="width:480px;">'
                    + '<div class="offcanvas-header bg-info text-white">'
                    + '<h5 class="offcanvas-title"><i class="bi bi-eye me-2"></i>Detalle</h5>'
                    + '<button type="button" class="btn-close btn-close-white" data-bs-dismiss="offcanvas"></button>'
                    + '</div><div class="offcanvas-body">' + html + '</div></div>';
                const el = d.getElementById('offcanvas-movimiento-detalle');
                mostrarOffcanvasSeguro(el);
            }
        } catch (err) {
            console.error(MOD, err);
            mostrarError('Error al cargar el detalle.');
        }
    }

    async function abrirEditar(uuid) {
        try {
            await htmx.ajax('GET', API_MOV + '/gestor-offcanvas/?id=' + uuid, {
                target: '#offcanvas-container-movimientos',
                swap: 'innerHTML'
            });
            await new Promise(r => setTimeout(r, 80));
            const el = d.getElementById('offcanvas-movimientos');
            mostrarOffcanvasSeguro(el);
        } catch (err) {
            console.error(MOD, err);
            mostrarError('Error al cargar el formulario de edicion.');
        }
    }

    async function eliminar(uuid, modulo, btn) {
        const esServicio = modulo === 'SERVICIO';
        const msgConfirm = esServicio
            ? 'Eliminar este registro de Historial de Servicio? Esta accion es irreversible.'
            : 'Eliminar este movimiento? El stock del producto sera recalculado automaticamente.';

        if (!(await w.UIManager?.confirm(msgConfirm))) return;

        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

        try {
            const apiBase = esServicio ? API_HIST : API_MOV;
            const res = await w.Sintel.Core.Http.request('DELETE', apiBase + '/' + uuid + '/');
            if (!res.ok) {
                mostrarError(res.data?.detail || 'Error al eliminar.');
                return;
            }
            const msg = esServicio ? 'Historial eliminado.' : 'Movimiento eliminado. Stock recalculado.';
            w.SintelFeedback?.success?.(msg);
            table?.replaceData();
        } catch (err) {
            console.error(MOD, err);
            mostrarError('Error inesperado al eliminar.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = original;
        }
    }

    // -----------------------------------------------------------------------
    // Event delegation
    // -----------------------------------------------------------------------

    function initListEvents() {
        const grid = d.querySelector(GRID_ID);
        if (!grid) return;

        grid.addEventListener('click', async function(e) {
            const btnVer = e.target.closest('.btn-km-ver');
            if (btnVer) {
                e.preventDefault(); e.stopPropagation();
                await abrirDetalle(btnVer.dataset.uuid, btnVer.dataset.modulo);
                return;
            }

            const btnEdit = e.target.closest('.btn-km-editar');
            if (btnEdit) {
                e.preventDefault(); e.stopPropagation();
                const original = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try { await abrirEditar(btnEdit.dataset.uuid); }
                finally { btnEdit.disabled = false; btnEdit.innerHTML = original; }
                return;
            }

            const btnDel = e.target.closest('.btn-km-eliminar');
            if (btnDel) {
                e.preventDefault(); e.stopPropagation();
                await eliminar(btnDel.dataset.uuid, btnDel.dataset.modulo, btnDel);
                return;
            }

            // Crear proyecto desde venta de servicio (v3.9.7)
            const btnCrearProy = e.target.closest('.btn-km-crear-proyecto');
            if (btnCrearProy) {
                e.preventDefault(); e.stopPropagation();
                const uuid = btnCrearProy.dataset.uuid;
                const original = btnCrearProy.innerHTML;
                btnCrearProy.disabled = true;
                btnCrearProy.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', '/api/v1/proyectos/gestor-offcanvas/?historial_uuid=' + uuid, {
                        target: '#offcanvas-container-inventario-proyecto',
                        swap: 'innerHTML'
                    });
                } catch (err) {
                    console.error(MOD, err);
                    mostrarError('Error al iniciar la creación de proyecto.');
                } finally {
                    btnCrearProy.disabled = false;
                    btnCrearProy.innerHTML = original;
                }
                return;
            }

            // Ver proyecto vinculado (v3.9.7)
            const btnLinkProy = e.target.closest('.btn-km-proyecto-link');
            if (btnLinkProy) {
                e.preventDefault(); e.stopPropagation();
                const uuid = btnLinkProy.dataset.uuid;
                const original = btnLinkProy.innerHTML;
                btnLinkProy.disabled = true;
                btnLinkProy.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', '/api/v1/proyectos/gestor-offcanvas/?uuid=' + uuid, {
                        target: '#offcanvas-container-inventario-proyecto',
                        swap: 'innerHTML'
                    });
                } catch (err) {
                    console.error(MOD, err);
                    mostrarError('Error al cargar el proyecto.');
                } finally {
                    btnLinkProy.disabled = false;
                    btnLinkProy.innerHTML = original;
                }
                return;
            }
        });
    }

    // -----------------------------------------------------------------------
    // Helpers UI
    // -----------------------------------------------------------------------

    function mostrarError(msg) {
        const el = d.getElementById('feedback-movimientos-list');
        if (el) {
            el.className = 'alert alert-danger mb-2';
            el.textContent = msg;
            el.classList.remove('d-none');
            setTimeout(() => el.classList.add('d-none'), 5000);
        }
    }

    function recargar() {
        if (table) table.replaceData();
    }

    // -----------------------------------------------------------------------
    // Init
    // -----------------------------------------------------------------------

    function init() {
        const el = d.querySelector(GRID_ID);
        if (!el) return;
        initTable();

        // Escuchar cuando un proyecto es guardado o creado para recargar el grid
        d.addEventListener('proyectoGuardado', recargar);
    }

    w.MovimientosList = { init, recargar, getTable: () => table };

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else if (w.DOMUtils?.onVisibleOnce) {
        w.DOMUtils.onVisibleOnce('#pane-movimientos', init);
    } else {
        const tab = d.querySelector('#tab-movimientos');
        if (tab?.classList.contains('active')) {
            init();
        } else if (tab) {
            tab.addEventListener('shown.bs.tab', function() { if (!table) init(); });
        }
    }

})(window, document);
