/**
 * Dashboard Main Module
 * 
 * Namespace: window.Sintel.Dashboard
 * Versión: v3.5
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Dashboard = window.Sintel.Dashboard || {};

    function init(selector) {
        const container = document.querySelector(selector);
        if (!container) {
            console.error('[Dashboard] Container no encontrado:', selector);
            return;
        }

        loadWidgets(container);
        loadActivity();
    }

    function loadWidgets(container) {
        fetch(window.Sintel.Dashboard.API.dashboard.widgets, {
            headers: window.Sintel.Dashboard.getHeaders()
        })
        .then(r => r.json())
        .then(data => {
            container.innerHTML = renderWidgets(data);
        })
        .catch(err => console.error('[Dashboard] Error cargando widgets:', err));
    }

    function renderWidgets(data) {
        const widgets = [
            { title: 'Facturas del Mes', value: data.facturas_mes || 0, icon: 'receipt', color: 'primary' },
            { title: 'Total Facturado', value: `$${(data.total_facturado || 0).toLocaleString()}`, icon: 'currency-dollar', color: 'success' },
            { title: 'Clientes Activos', value: data.clientes_activos || 0, icon: 'people', color: 'info' },
            { title: 'Cotizaciones Pendientes', value: data.cotizaciones_pendientes || 0, icon: 'file-text', color: 'warning' }
        ];

        return widgets.map(w => `
            <div class="col-md-3">
                <div class="card border-${w.color}">
                    <div class="card-body">
                        <div class="d-flex align-items-center">
                            <div class="flex-shrink-0">
                                <i class="bi bi-${w.icon} fs-1 text-${w.color}"></i>
                            </div>
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
