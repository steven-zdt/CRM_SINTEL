/**
 * Dashboard Main Module v3.9.4
 * Renderiza métricas consolidadas con Pull Model + Offcanvas seguro
 *
 * Namespace: window.Sintel.Dashboard.Main
 */
(function(w, d) {
    'use strict';

    const MOD = '[DashboardMain]';
    const CACHE_TTL = 15 * 60 * 1000;

    let metricas = null;
    let ultimaActualizacion = 0;

    async function inicializar() {
        console.log(`${MOD} Inicializando...`);
        try {
            metricas = await cargarMetricas();
            renderizarWidgetFacturas();
            renderizarWidgetInventario();
            renderizarWidgetEmpleados();
            actualizarTiempoActualizacion();
            setupOffcanvasListeners();
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            mostrarErrorGlobal();
        }
    }

    async function cargarMetricas() {
        const ahora = Date.now();
        if (metricas && (ahora - ultimaActualizacion) < CACHE_TTL) {
            return metricas;
        }
        try {
            const data = await w.Sintel.Dashboard.obtenerMetricas();
            ultimaActualizacion = ahora;
            return data;
        } catch (error) {
            throw error;
        }
    }

    function renderizarWidgetFacturas() {
        const container = d.getElementById('widget-facturas');
        if (!container || !metricas?.facturas) return;
        const f = metricas.facturas;
        container.innerHTML = `
            <div class="card h-100 shadow-sm">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0"><i class="bi bi-file-invoice me-2"></i>Facturación</h6>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-6"><p class="text-muted small mb-1">Total</p><h4 class="mb-0">${f.total_facturas}</h4></div>
                        <div class="col-6"><p class="text-muted small mb-1">Pendientes</p><h4 class="mb-0 text-warning">${f.facturas_pendientes}</h4></div>
                        <div class="col-6"><p class="text-muted small mb-1">Vencidas</p><h4 class="mb-0 text-danger">${f.facturas_vencidas}</h4></div>
                        <div class="col-6"><p class="text-muted small mb-1">Ingresos</p><h4 class="mb-0 text-success">$${parseFloat(f.ingresos_mes).toLocaleString('es-CO')}</h4></div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderizarWidgetInventario() {
        const container = d.getElementById('widget-inventario');
        if (!container || !metricas?.inventario) return;
        const inv = metricas.inventario;
        container.innerHTML = `
            <div class="card h-100 shadow-sm">
                <div class="card-header bg-success text-white">
                    <h6 class="mb-0"><i class="bi bi-box me-2"></i>Inventario</h6>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-6"><p class="text-muted small mb-1">Productos</p><h4 class="mb-0">${inv.total_productos}</h4></div>
                        <div class="col-6"><p class="text-muted small mb-1">Bajo Stock</p><h4 class="mb-0 text-danger">${inv.productos_bajo_stock}</h4></div>
                        <div class="col-12"><p class="text-muted small mb-1">Valor</p><h4 class="mb-0">$${parseFloat(inv.valor_inventario).toLocaleString('es-CO')}</h4></div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderizarWidgetEmpleados() {
        const container = d.getElementById('widget-empleados');
        if (!container || !metricas?.empleados) return;
        const emp = metricas.empleados;
        container.innerHTML = `
            <div class="card h-100 shadow-sm">
                <div class="card-header bg-info text-white">
                    <h6 class="mb-0"><i class="bi bi-people me-2"></i>Empleados</h6>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-6"><p class="text-muted small mb-1">Total</p><h4 class="mb-0">${emp.total_empleados}</h4></div>
                        <div class="col-6"><p class="text-muted small mb-1">Activos</p><h4 class="mb-0 text-success">${emp.empleados_activos}</h4></div>
                        <div class="col-6"><p class="text-muted small mb-1">Nóminas Pendientes</p><h4 class="mb-0 text-warning">${emp.nominas_pendientes}</h4></div>
                        <div class="col-6"><p class="text-muted small mb-1">Nómina (mes)</p><h4 class="mb-0">$${parseFloat(emp.total_nómina_mes).toLocaleString('es-CO')}</h4></div>
                    </div>
                </div>
            </div>
        `;
    }

    function actualizarTiempoActualizacion() {
        const timestamp = d.getElementById('dashboard-timestamp');
        if (!timestamp || !metricas?.fecha_actualizacion) return;
        const fecha = new Date(metricas.fecha_actualizacion);
        timestamp.textContent = fecha.toLocaleString('es-CO');
    }

    function setupOffcanvasListeners() {
        d.querySelectorAll('[id^="offcanvas-dashboard-"]').forEach(el => {
            el.addEventListener('hidden.bs.offcanvas', () => {
                console.log(`${MOD} Offcanvas cerrado`);
            });
        });
    }

    function mostrarErrorGlobal() {
        const container = d.getElementById('dashboard-error');
        if (!container) return;
        container.innerHTML = '<div class="alert alert-danger">Error al cargar el dashboard.</div>';
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', inicializar);
    } else {
        inicializar();
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Dashboard = w.Sintel.Dashboard || {};
    w.Sintel.Dashboard.Main = {
        inicializar,
        cargarMetricas
    };
                            <div class="flex-grow-1 ms-3">
                                <h6 class="text-muted mb-1">${w.title}</h6>
                                <h4 class="mb-0">${w.value}</h4>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    function loadActivity() {
        const container = document.querySelector('#actividad-reciente');
        if (!container) return;

        fetch(window.Sintel.Dashboard.API.dashboard.activity, {
            headers: window.Sintel.Dashboard.getHeaders()
        })
        .then(r => r.json())
        .then(data => {
            if (!data.length) {
                container.innerHTML = '<p class="text-muted">No hay actividad reciente</p>';
                return;
            }
            container.innerHTML = data.map(item => `
                <div class="d-flex mb-3">
                    <div class="flex-shrink-0">
                        <span class="badge bg-${item.tipo === 'factura' ? 'primary' : 'secondary'}">
                            ${item.tipo}
                        </span>
                    </div>
                    <div class="flex-grow-1 ms-3">
                        <p class="mb-0">${item.descripcion}</p>
                        <small class="text-muted">${item.fecha}</small>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => console.error('[Dashboard] Error cargando actividad:', err));
    }

    window.Sintel.Dashboard.init = init;
    window.Sintel.Dashboard.loadWidgets = loadWidgets;
    window.Sintel.Dashboard.loadActivity = loadActivity;
})();
