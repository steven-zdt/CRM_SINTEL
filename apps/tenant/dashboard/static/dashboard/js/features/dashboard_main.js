// @ts-nocheck
/**
 * Dashboard Main Module v3.9.5
 * Renderiza 5 widgets de métricas consolidadas (Pull Model).
 * Inicializa al activar tab-activated:dashboard desde workspace.js
 *
 * Namespace: window.Sintel.Dashboard.Main
 */
(function(w, d) {
    'use strict';

    const MOD = '[DashboardMain]';
    const CACHE_TTL = 15 * 60 * 1000;

    let _metricas = null;
    let _ultimaActualizacion = 0;
    let _inicializado = false;

    // ── Formatters ──────────────────────────────────────────────────────────

    const COP = (val) => new Intl.NumberFormat('es-CO', {
        style: 'currency', currency: 'COP', minimumFractionDigits: 0
    }).format(parseFloat(val) || 0);

    const num = (val) => new Intl.NumberFormat('es-CO').format(parseInt(val) || 0);

    // ── Carga de datos ──────────────────────────────────────────────────────

    async function cargarMetricas(forzar = false) {
        const ahora = Date.now();
        if (!forzar && _metricas && (ahora - _ultimaActualizacion) < CACHE_TTL) {
            return _metricas;
        }
        const data = await w.Sintel.Dashboard.obtenerMetricas();
        _ultimaActualizacion = ahora;
        return data;
    }

    // ── Inicializar ─────────────────────────────────────────────────────────

    async function inicializar(forzar = false) {
        if (_inicializado && !forzar) return;
        console.log(`${MOD} Inicializando...`);
        try {
            _metricas = await cargarMetricas(forzar);
            renderizarWidgetFacturas();
            renderizarWidgetInventario();
            renderizarWidgetEmpleados();
            renderizarWidgetGastos();
            renderizarWidgetProyectos();
            renderizarWidgetClientes();
            actualizarHeader();
            _inicializado = true;
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            mostrarError('No se pudieron cargar las métricas del dashboard.');
        }
    }

    // ── Helpers de renderizado ──────────────────────────────────────────────

    function metricBox(label, value, colorClass) {
        return `<div class="dashboard-metric-box">
                    <div class="metric-val ${colorClass || ''}">${value}</div>
                    <div class="metric-lbl">${label}</div>
                </div>`;
    }

    function widgetCard(iconClass, bgClass, textClass, title, subtitle, metricsHtml) {
        return `<div class="card dashboard-widget-card h-100">
                    <div class="card-body p-3">
                        <div class="d-flex align-items-center mb-3">
                            <div class="dashboard-kpi-icon ${bgClass} ${textClass} me-3">
                                <i class="bi ${iconClass}"></i>
                            </div>
                            <div class="flex-grow-1 min-w-0">
                                <h6 class="card-title mb-0 fw-semibold">${title}</h6>
                                <small class="text-muted">${subtitle}</small>
                            </div>
                        </div>
                        <div class="row g-2">${metricsHtml}</div>
                    </div>
                </div>`;
    }

    function metricCol(label, value, colorClass, cols) {
        const w = cols || '6';
        return `<div class="col-${w}">${metricBox(label, value, colorClass)}</div>`;
    }

    // ── Widgets ─────────────────────────────────────────────────────────────

    function renderizarWidgetFacturas() {
        const el = d.getElementById('widget-facturas');
        if (!el || !_metricas?.facturas) return;
        const f = _metricas.facturas;
        el.innerHTML = widgetCard(
            'bi-file-invoice-dollar',
            'bg-primary bg-opacity-10',
            'text-primary',
            'Facturación',
            'Mes actual',
            metricCol('Total', num(f.total_facturas), '') +
            metricCol('Ingresos Mes', COP(f.ingresos_mes), 'text-success') +
            metricCol('Pendientes', num(f.facturas_pendientes), 'text-warning') +
            metricCol('Vencidas', num(f.facturas_vencidas), 'text-danger')
        );
    }

    function renderizarWidgetInventario() {
        const el = d.getElementById('widget-inventario');
        if (!el || !_metricas?.inventario) return;
        const inv = _metricas.inventario;
        el.innerHTML = widgetCard(
            'bi-box-seam',
            'bg-success bg-opacity-10',
            'text-success',
            'Inventario',
            'Kardex activo',
            metricCol('Ítems', num(inv.total_productos), '') +
            metricCol('Valor', COP(inv.valor_inventario), 'text-success') +
            metricCol('Bajo Stock', num(inv.productos_bajo_stock), 'text-danger') +
            metricCol('Movs. Mes', num(inv.movimientos_mes), 'text-info')
        );
    }

    function renderizarWidgetEmpleados() {
        const el = d.getElementById('widget-empleados');
        if (!el || !_metricas?.empleados) return;
        const emp = _metricas.empleados;
        const nominaMes = emp.total_nomina_mes ?? emp['total_nómina_mes'] ?? 0;
        el.innerHTML = widgetCard(
            'bi-people-fill',
            'bg-info bg-opacity-10',
            'text-info',
            'Empleados',
            'Planta activa',
            metricCol('Total', num(emp.total_empleados), '') +
            metricCol('Activos', num(emp.empleados_activos), 'text-success') +
            metricCol('Nómina Mes', COP(nominaMes), 'text-primary') +
            metricCol('Pend. Nómina', num(emp.nominas_pendientes), 'text-warning')
        );
    }

    function renderizarWidgetGastos() {
        const el = d.getElementById('widget-gastos');
        if (!el) return;
        const g = _metricas?.gastos;
        if (!g) { el.innerHTML = widgetCard('bi-cash-stack','bg-warning bg-opacity-10','text-warning','Gastos','Mes actual','<div class="col-12"><p class="text-muted small mb-0">Sin datos de gastos</p></div>'); return; }
        el.innerHTML = widgetCard(
            'bi-cash-stack',
            'bg-warning bg-opacity-10',
            'text-warning',
            'Gastos',
            'Mes actual',
            metricCol('Total Mes', COP(g.total_gastos_mes), 'text-warning') +
            metricCol('Promedio', COP(g.gasto_promedio), '') +
            metricCol('Pendientes', num(g.gastos_pendientes), 'text-warning') +
            metricCol('Vencidos', num(g.gastos_vencidos), 'text-danger')
        );
    }

    function renderizarWidgetProyectos() {
        const el = d.getElementById('widget-proyectos');
        if (!el) return;
        const p = _metricas?.proyectos;
        if (!p) { el.innerHTML = widgetCard('bi-kanban','bg-secondary bg-opacity-10','text-secondary','Proyectos','Activos','<div class="col-12"><p class="text-muted small mb-0">Sin datos de proyectos</p></div>'); return; }
        el.innerHTML = widgetCard(
            'bi-kanban',
            'bg-purple bg-opacity-10',
            'text-purple',
            'Proyectos',
            'En curso',
            metricCol('Total', num(p.total_proyectos), '') +
            metricCol('Activos', num(p.proyectos_activos), 'text-success') +
            metricCol('Tareas Pend.', num(p.tareas_pendientes), 'text-warning') +
            metricCol('Vencidas', num(p.tareas_vencidas), 'text-danger')
        );
    }

    function renderizarWidgetClientes() {
        const el = d.getElementById('widget-clientes');
        if (!el) return;
        const c = _metricas?.clientes;
        if (!c) {
            el.innerHTML = widgetCard('bi-person-badge','bg-teal bg-opacity-10','text-teal','Clientes','Cartera activa','<div class="col-12"><p class="text-muted small mb-0">Sin datos de clientes</p></div>');
            return;
        }
        el.innerHTML = widgetCard(
            'bi-person-badge',
            'bg-teal bg-opacity-10',
            'text-teal',
            'Clientes',
            'Cartera activa',
            metricCol('Total', num(c.total_clientes), '') +
            metricCol('Activos', num(c.clientes_activos), 'text-success') +
            metricCol('Nuevos Mes', num(c.nuevos_mes), 'text-primary') +
            metricCol('Retenedores', num(c.retenedores), 'text-warning')
        );
    }

    // ── Header / timestamp ──────────────────────────────────────────────────

    function actualizarHeader() {
        const empresaEl = d.getElementById('dashboard-empresa-info');
        if (empresaEl && _metricas?.empresa_nombre) {
            const nit = _metricas.empresa_nit ? ` — NIT: ${_metricas.empresa_nit}` : '';
            empresaEl.innerHTML = `<i class="bi bi-building me-1"></i>${_metricas.empresa_nombre}${nit}`;
        }
        const tsEl = d.getElementById('dashboard-timestamp');
        if (tsEl && _metricas?.fecha_actualizacion) {
            const fecha = new Date(_metricas.fecha_actualizacion);
            tsEl.innerHTML = `<i class="bi bi-clock-history me-1"></i>Actualizado: ${fecha.toLocaleString('es-CO')}`;
        }
    }

    function mostrarError(msg) {
        const el = d.getElementById('dashboard-error');
        if (el) el.innerHTML = `<div class="alert alert-warning d-flex align-items-center gap-2 mb-3">
            <i class="bi bi-exclamation-triangle-fill"></i>${msg}
            <button class="btn btn-sm btn-outline-warning ms-auto" onclick="window.Sintel.Dashboard.Main.inicializar(true)">
                <i class="bi bi-arrow-clockwise me-1"></i>Reintentar
            </button></div>`;
        // Mostrar placeholders de error en widgets vacíos
        ['widget-facturas','widget-inventario','widget-empleados','widget-gastos','widget-proyectos'].forEach(id => {
            const el = d.getElementById(id);
            if (el && el.classList.contains('dashboard-widget-placeholder')) {
                el.innerHTML = '<div class="d-flex align-items-center justify-content-center h-100 text-muted small py-4"><i class="bi bi-dash-circle me-2"></i>Sin datos</div>';
                el.style.minHeight = '80px';
            }
        });
    }

    // ── Refresh button ──────────────────────────────────────────────────────

    function setupRefreshBtn() {
        const btn = d.getElementById('btn-refresh-dashboard');
        if (!btn || btn.dataset.dashboardBound) return;
        btn.dataset.dashboardBound = 'true';
        btn.addEventListener('click', async () => {
            btn.classList.add('spinning');
            btn.disabled = true;
            _inicializado = false;
            await inicializar(true);
            btn.classList.remove('spinning');
            btn.disabled = false;
        });
    }

    // ── Tab listener (Workspace v3.0) ───────────────────────────────────────

    d.addEventListener('tab-activated', (e) => {
        if (e.detail?.tabName !== 'dashboard') return;
        setupRefreshBtn();
        inicializar();
    });

    // ── Export ───────────────────────────────────────────────────────────────

    w.Sintel = w.Sintel || {};
    w.Sintel.Dashboard = w.Sintel.Dashboard || {};
    w.Sintel.Dashboard.Main = { inicializar, cargarMetricas };

})(window, document);
