/**
 * reporte.ui.js - Orquestador de la UI de reportes financieros v1.0
 * ⚠️ v3.5: Manejo de Tabulator y componentes visuales.
 */
(function() {
    window.Sintel = window.Sintel || {};
    window.Sintel.Contabilidad = window.Sintel.Contabilidad || {};

    // UIManager fallback con métodos seguros
    const _defaultUI = {
        showLoading: () => {
            const existing = document.getElementById('_loading_overlay');
            if (!existing) {
                const overlay = document.createElement('div');
                overlay.id = '_loading_overlay';
                overlay.className = 'position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-50 d-flex align-items-center justify-content-center';
                overlay.style.zIndex = '9999';
                overlay.innerHTML = '<div class="spinner-border text-light" role="status"><span class="visually-hidden">Cargando...</span></div>';
                document.body.appendChild(overlay);
            }
        },
        hideLoading: () => {
            const overlay = document.getElementById('_loading_overlay');
            if (overlay) overlay.remove();
        },
        notifySuccess: (message) => {
            const toastId = '_toast_' + Date.now();
            const toast = document.createElement('div');
            toast.id = toastId;
            toast.className = 'position-fixed bottom-0 end-0 m-3 alert alert-success alert-dismissible fade show';
            toast.style.zIndex = '9998';
            toast.innerHTML = message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
            document.body.appendChild(toast);
            setTimeout(() => { const el = document.getElementById(toastId); if (el) el.remove(); }, 4000);
        },
        notifyError: (message) => {
            const toastId = '_toast_' + Date.now();
            const toast = document.createElement('div');
            toast.id = toastId;
            toast.className = 'position-fixed bottom-0 end-0 m-3 alert alert-danger alert-dismissible fade show';
            toast.style.zIndex = '9998';
            toast.innerHTML = message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
            document.body.appendChild(toast);
            setTimeout(() => { const el = document.getElementById(toastId); if (el) el.remove(); }, 4000);
        }
    };

    // Crear UIManager con métodos seguros
    if (!window.UIManager) {
        window.UIManager = _defaultUI;
    } else {
        // Si ya existe, sobrescribir métodos que falten o estén rotos
        Object.keys(_defaultUI).forEach(method => {
            try {
                if (typeof window.UIManager[method] !== 'function') {
                    window.UIManager[method] = _defaultUI[method];
                }
            } catch (e) {
                window.UIManager[method] = _defaultUI[method];
            }
        });
    }
    
    window.Sintel.Contabilidad.ReporteUI = {
        gridBalance: null,

        init: function() {
            const container = document.getElementById('ui-contabilidad-reporte');
            if (!container) return;

            this.initDefaultDates();
            this.setupEvents();

            // Esperar a que el grid esté listo antes de inicializar Tabulator
            requestAnimationFrame(() => {
                setTimeout(() => {
                    this.initGridBalance();
                    this.cargarReportes();
                }, 100);
            });
        },

        initDefaultDates: function() {
            const now = new Date();
            const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
            const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);

            document.getElementById('reporte-fecha-inicio').value = firstDay.toISOString().split('T')[0];
            document.getElementById('reporte-fecha-fin').value = lastDay.toISOString().split('T')[0];
        },

        setupEvents: function() {
            const btn = document.getElementById('btn-generar-reportes');
            if (btn) {
                btn.addEventListener('click', () => {
                    this.cargarReportes();
                });
            }
        },

        initGridBalance: function() {
            const container = document.getElementById('grid-balance-prueba');
            if (!container) return;

            this.gridBalance = new Tabulator("#grid-balance-prueba", {
                data: [],
                layout: "fitColumns",
                placeholder: "No hay datos para el periodo seleccionado",
                columns: [
                    {title: "Cuenta", field: "cuenta_codigo", width: 120, headerFilter: "input"},
                    {title: "Nombre de Cuenta", field: "cuenta_nombre", widthGrow: 3, headerFilter: "input"},
                    {title: "Saldo Anterior", field: "saldo_anterior", hozAlign: "right", formatter: "money", 
                     formatterParams: {symbol: "$", precision: 0, thousand: ".", decimal: ","}},
                    {title: "Débitos", field: "debitos", hozAlign: "right", formatter: "money", 
                     formatterParams: {symbol: "$", precision: 0, thousand: ".", decimal: ","}},
                    {title: "Créditos", field: "creditos", hozAlign: "right", formatter: "money", 
                     formatterParams: {symbol: "$", precision: 0, thousand: ".", decimal: ","}},
                    {title: "Nuevo Saldo", field: "nuevo_saldo", hozAlign: "right", formatter: "money", 
                     formatterParams: {symbol: "$", precision: 0, thousand: ".", decimal: ","},
                     bottomCalc: "sum", bottomCalcFormatter: "money", bottomCalcFormatterParams: {symbol: "$", precision: 0}},
                ],
            });
        },

        cargarReportes: async function() {
            // DISABLED: Modulo de reportes no activo en esta vista. Reactivar cuando se habilite el tab Reportes.
            return;

            /* eslint-disable no-unreachable */
            const start = document.getElementById('reporte-fecha-inicio').value;
            const end = document.getElementById('reporte-fecha-fin').value;

            if (!start || !end) {
                if (window.UIManager) window.UIManager.notifyError("Seleccione ambas fechas");
                return;
            }

            try {
                if (window.UIManager) window.UIManager.showLoading();
                
                // Cargar Balance y P&G en paralelo
                const [dataBalance, dataPG] = await Promise.all([
                    window.Sintel.Contabilidad.ReporteAPI.getBalancePrueba(start, end),
                    window.Sintel.Contabilidad.ReporteAPI.getEstadoResultados(start, end)
                ]);

                if (this.gridBalance) {
                    this.gridBalance.setData(dataBalance);
                }
                
                this.renderEstadoResultados(dataPG);

                if (window.UIManager) window.UIManager.notifySuccess("Reportes generados correctamente");
            } catch (error) {
                console.error("Error en ReporteUI:", error);
                if (window.UIManager) window.UIManager.notifyError("Error al procesar los reportes financieros");
            } finally {
                if (window.UIManager) window.UIManager.hideLoading();
            }
            /* eslint-enable no-unreachable */
        },

        renderEstadoResultados: function(data) {
            const container = document.getElementById('container-estado-resultados');
            if (!container || !data || !data.detalle) return;
            
            const margen = ((data.utilidad_neta / (data.total_ingresos || 1)) * 100).toFixed(1);
            const utilidadClass = data.utilidad_neta >= 0 ? 'text-success' : 'text-danger';
            
            let html = `
                <div class="row g-3 mb-4">
                    <div class="col-md-4">
                        <div class="card border-0 shadow-sm overflow-hidden">
                            <div class="card-body p-4 bg-success bg-opacity-10 border-start border-4 border-success">
                                <p class="text-success text-uppercase small fw-bold mb-1">Ingresos Operacionales</p>
                                <h2 class="fw-bold mb-0">${this.formatMoney(data.total_ingresos)}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card border-0 shadow-sm overflow-hidden">
                            <div class="card-body p-4 bg-danger bg-opacity-10 border-start border-4 border-danger">
                                <p class="text-danger text-uppercase small fw-bold mb-1">Costos y Gastos</p>
                                <h2 class="fw-bold mb-0">${this.formatMoney(data.total_costos + data.total_gastos)}</h2>
                                <div class="mt-2 text-muted x-small">
                                    <span>Cos: ${this.formatMoney(data.total_costos)}</span> • 
                                    <span>Gas: ${this.formatMoney(data.total_gastos)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card border-0 shadow-sm overflow-hidden">
                            <div class="card-body p-4 bg-primary bg-opacity-10 border-start border-4 border-primary">
                                <p class="text-primary text-uppercase small fw-bold mb-1">Resultado del Ejercicio</p>
                                <h2 class="fw-bold mb-0 ${utilidadClass}">${this.formatMoney(data.utilidad_neta)}</h2>
                                <p class="mb-0 mt-2 small text-muted">Margen Neto: <strong>${margen}%</strong></p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white py-3 border-0">
                        <h6 class="mb-0 fw-bold"><i class="bi bi-list-check me-2"></i>Estructura de Resultados NIIF</h6>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover table-borderless mb-0 align-middle">
                                <thead class="bg-light">
                                    <tr>
                                        <th class="ps-4" style="width: 100px;">Cuenta</th>
                                        <th>Descripción</th>
                                        <th class="text-end pe-4" style="width: 200px;">Monto Total</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.detalle.map(d => `
                                        <tr class="${d.codigo.length === 1 ? 'table-light fw-bold border-top' : ''}">
                                            <td class="ps-4">${d.codigo}</td>
                                            <td>${d.nombre}</td>
                                            <td class="text-end pe-4">${this.formatMoney(d.total)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
            
            container.innerHTML = html;
        },

        formatMoney: function(amount) {
            // BUG (2026-09-12, hallazgo T-5): sin este guard, una clave
            // ausente en la respuesta del API (no solo en 0, sino no
            // presente) llegaba aqui como undefined y renderizaba el string
            // literal "NaN" en las tarjetas de Ingresos/Costos/Utilidad del
            // Estado de Resultados.
            const value = (amount === null || amount === undefined || amount === '' || isNaN(amount))
                ? 0 : amount;
            // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js).
            if (window.DOMUtils && typeof window.DOMUtils.formatCurrency === 'function') {
                return window.DOMUtils.formatCurrency(value, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
            }
            return new Intl.NumberFormat('es-CO', {
                style: 'currency',
                currency: 'COP',
                maximumFractionDigits: 0
            }).format(value);
        }
    };

    // Auto-init
    document.addEventListener('DOMContentLoaded', () => {
        window.Sintel.Contabilidad.ReporteUI.init();
    });
})();
