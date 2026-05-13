/**
 * Nomina Historial Module - Feature: Historial de Nóminas
 * ⚠️ Feature-Sliced Architecture v2.61.8
 * 
 * Namespace: window.Sintel.Empleados.NominaHistorial
 */
(function(w, d) {
    'use strict';

    const MOD = '[NominaHistorial]';
    const API_BASE = '/api/v1/empleados/';
    const CONTAINER_ID = 'offcanvas-container-nominas';

    /**
     * Abrir historial de nóminas
     */
    async function open(empleadoId) {
        if (!empleadoId) {
            console.error(`${MOD} ID de empleado no proporcionado`);
            return;
        }
        
        const url = `${API_BASE}${empleadoId}/historial-nominas/`;
        
        console.log(`${MOD} Cargando historial: ${url}`);
        
        try {
            await htmx.ajax('GET', url, {
                target: `#${CONTAINER_ID}`,
                swap: 'innerHTML'
            });
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al cargar historial de nóminas');
        }
    }

    /**
     * Listener para activar offcanvas tras inyección HTMX
     */
    function setupOffcanvasLoadListener() {
        document.body.addEventListener('htmx:afterSettle', function(evt) {
            const target = evt.detail.target;
            if (!target || target.id !== CONTAINER_ID) return;

            const offcanvasEl = target.querySelector('#offcanvas-historial-nominas');
            if (offcanvasEl && window.bootstrap) {
                console.log(`${MOD} Activando offcanvas: ${offcanvasEl.id}`);
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                bsOffcanvas.show();
                
                // Inicializar tabla después de que el offcanvas esté visible
                const empleadoId = offcanvasEl.dataset.empleadoId; // Asumimos que viene en el data-attribute
                setTimeout(() => initTable(empleadoId), 300);
            }
        });
    }

    /**
     * Inicializar tabla Tabulator
     */
    function initTable(empleadoId) {
        const gridEl = d.querySelector('#grid-historial-nominas');
        if (!gridEl || !w.TabulatorFactory) return;

        const url = `${API_BASE}devengos/?empleado=${empleadoId}`;
        
        const columns = [
            { title: "Periodo", field: "periodo_mes", width: 120 },
            { 
                title: "Fecha Pago", 
                field: "fecha_pago", 
                width: 140,
                formatter: (cell) => {
                    const val = cell.getValue();
                    return val ? new Date(val).toLocaleDateString('es-CO') : '-';
                }
            },
            { title: "Días", field: "dias_laborados", width: 80 },
            { 
                title: "Salario Base", 
                field: "salario_base", 
                formatter: "money", 
                formatterParams: { symbol: "$", decimal: ".", thousand: "," } 
            },
            { 
                title: "Neto Pagar", 
                field: "neto_pagar", 
                cssClass: "fw-bold text-primary",
                formatter: "money", 
                formatterParams: { symbol: "$", decimal: ".", thousand: "," } 
            },
            { 
                title: "Estado", 
                field: "anulado", 
                formatter: (cell) => cell.getValue() ? '<span class="badge bg-danger">Anulado</span>' : '<span class="badge bg-success">Activo</span>'
            },
            {
                title: "Acciones",
                hozAlign: "center",
                headerSort: false,
                formatter: (cell) => {
                    const data = cell.getRow().getData();
                    if (data.anulado) return '-';
                    return `
                        <button class="btn btn-sm btn-outline-danger" onclick="window.Sintel.Empleados.NominaHistorial.anular(${data.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    `;
                }
            }
        ];

        const table = w.TabulatorFactory.create('#grid-historial-nominas', url, columns, {
            pagination: false,
            ajaxParams: { page_size: 200 }
        });

        // Guardar referencia
        w.Sintel.Empleados.NominaHistorial._table = table;
    }

    /**
     * Anular nómina
     */
    async function anular(id) {
        if (!confirm('¿Está seguro de que desea anular esta nómina?')) return;

        try {
            const resp = await w.http('POST', `${API_BASE}devengos/${id}/anular/`);
            if (resp.ok) {
                window.UIManager?.notifySuccess('Nómina anulada correctamente');
                w.Sintel.Empleados.NominaHistorial._table?.replaceData();
                window.Sintel.Empleados.EmpleadoList?.reload();
            } else {
                window.UIManager?.handleError(resp);
            }
        } catch (error) {
            console.error(`${MOD} Error:`, error);
            window.UIManager?.notifyError('Error al anular nómina');
        }
    }

    // Inicializar listeners
    setupOffcanvasLoadListener();

    // Exportar
    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};
    window.Sintel.Empleados.NominaHistorial = {
        open,
        openHistorial: open,
        anular
    };

    // Alias legacy
    window.HistorialNominas = window.Sintel.Empleados.NominaHistorial;

})(window, document);
