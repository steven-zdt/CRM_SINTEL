/**
 * Gasto List Module - Tabla de Gastos con Tabulator
 * 
 * Namespace: window.Sintel.Gastos.GastoList
 * Versión: v2.61.4
 */
(function() {
    'use strict';

    window.Sintel = window.Sintel || {};
    window.Sintel.Gastos = window.Sintel.Gastos || {};

    // ID del gasto a eliminar
    let gastoIdEliminar = null;

    const defaultConfig = {
        layout: "fitColumns",
        pagination: true,
        paginationMode: "remote",
        ajaxURL: window.Sintel.Gastos.API.gastos.list,
        ajaxConfig: {
            method: "GET",
            headers: window.Sintel.Gastos.getHeaders()
        },
        columns: [
            { 
                title: "Consecutivo", 
                field: "documento_soporte.consecutivo",
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    return (data.documento_soporte?.prefijo || '') + (data.documento_soporte?.consecutivo || '');
                }
            },
            { title: "Fecha", field: "documento_soporte.fecha" },
            { title: "Proveedor", field: "documento_soporte.vendedor_nombre" },
            { title: "Periodo", field: "periodo" },
            { title: "Categoria", field: "categoria_contable" },
            { 
                title: "Total", 
                field: "documento_soporte.total",
                formatter: "money",
                formatterParams: { symbol: "$", precision: 2 }
            },
            {
                title: "Estado",
                field: "documento_soporte.anulado",
                formatter: function(cell) {
                    return cell.getValue() ? 
                        '<span class="badge bg-danger">Anulado</span>' : 
                        '<span class="badge bg-success">Activo</span>';
                }
            },
            {
                title: "Acciones",
                width: 150,
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    return '<div class="btn-group btn-group-sm" role="group">' +
                        '<button class="btn btn-primary" onclick="Sintel.Gastos.GastoList.editar(\'' + data.id + '\')" title="Editar"><i class="bi bi-pencil"></i></button>' +
                        '<button class="btn btn-info" onclick="Sintel.Gastos.GastoList.verDetalle(\'' + data.id + '\')" title="Ver"><i class="bi bi-eye"></i></button>' +
                        '<button class="btn btn-warning" onclick="Sintel.Gastos.GastoList.anular(\'' + data.id + '\')" title="Anular"><i class="bi bi-x-circle"></i></button>' +
                        '</div>';
                }
            }
        ]
    };

    function init(selector, config = {}) {
        const element = document.querySelector(selector);
        if (!element) {
            console.error('[GastoList] Selector no encontrado:', selector);
            return null;
        }

        const mergedConfig = { ...defaultConfig, ...config };
        const table = new Tabulator(element, mergedConfig);
        window.Sintel.Gastos.table = table;

        return table;
    }

    function reload() {
        if (window.Sintel.Gastos.table) {
            window.Sintel.Gastos.table.setData();
        }
    }

    function editar(id) {
        const url = window.Sintel.Gastos.API.gastos.detail(id);
        htmx.ajax('GET', url, {
            target: '#offcanvas-container',
            swap: 'innerHTML'
        });
    }

    function verDetalle(id) {
        const url = window.Sintel.Gastos.API.gastos.detail(id);
        fetch(url, {
            headers: window.Sintel.Gastos.getHeaders()
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            console.log('[GastoList] Detalle:', data);
        })
        .catch(function(err) { console.error('[GastoList] Error:', err); });
    }

    function anular(id) {
        if (!confirm('Esta seguro de anular este gasto?')) return;

        const url = window.Sintel.Gastos.API.gastos.anular(id);
        fetch(url, {
            method: 'POST',
            headers: window.Sintel.Gastos.getHeaders()
        })
        .then(function(r) {
            if (r.ok) {
                if (window.UIManager) {
                    window.UIManager.notifySuccess('Gasto anulado correctamente');
                }
                reload();
                loadSummary('#gastos-summary');
            } else {
                return r.json().then(function(err) { throw err; });
            }
        })
        .catch(function(err) {
            console.error('[GastoList] Error anulando:', err);
            if (window.UIManager) {
                window.UIManager.notifyError(err.error || 'Error al anular gasto');
            }
        });
    }

    function loadSummary(selector) {
        const element = document.querySelector(selector);
        if (!element) return;

        fetch(window.Sintel.Gastos.API.gastos.summary, {
            headers: window.Sintel.Gastos.getHeaders()
        })
        .then(r => r.json())
        .then(data => {
            element.innerHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">Total Mes</h6>
                                <h4 class="text-primary">$${parseFloat(data.total_gastos_mes).toFixed(2)}</h4>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">Documentos</h6>
                                <h4 class="text-info">${data.documentos_emitidos}</h4>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">Periodo</h6>
                                <h4 class="text-secondary">${data.periodo_actual}</h4>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        })
        .catch(err => console.error('[GastoList] Error cargando summary:', err));
    }

    window.Sintel.Gastos.GastoList = {
        init,
        reload,
        verDetalle,
        editar,
        anular,
        loadSummary
    };

})();
