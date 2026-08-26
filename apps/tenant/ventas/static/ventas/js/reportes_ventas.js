/**
 * reportes_ventas.js -- boton "volver" al catalogo + enlaces de export
 * reales (Sintel.Reporting.API.exportUrl()) para el reporte ventas.resumen.
 *
 * Se ejecuta una vez por carga del contenedor (ver
 * reportes_ventas_container.html) -- el <script> no se vuelve a swapear
 * cuando solo cambia #reportes-ventas-panel (el formulario de filtros
 * queda fijo en el DOM), asi que no hay riesgo de listeners duplicados.
 */
(function (w, d) {
    'use strict';

    var form = d.getElementById('filtros-reportes-ventas');
    var exportContainer = d.getElementById('reportes-ventas-export');
    var volverBtn = d.querySelector('[data-reportes-volver]');

    function currentFilters() {
        if (!form) return {};
        var data = new FormData(form);
        var filters = {};
        ['fecha_inicio', 'fecha_fin', 'estado'].forEach(function (key) {
            var value = data.get(key);
            if (value) filters[key] = value;
        });
        return {
            filters: filters,
            group_by: [data.get('group_by') || 'fecha'],
            measures: ['cantidad_ventas', 'subtotal', 'impuestos', 'total'],
        };
    }

    function renderExportLinks() {
        if (!exportContainer || !w.Sintel || !w.Sintel.Reporting || !w.Sintel.Reporting.API) return;
        var base = currentFilters();
        base.dataset_id = 'ventas.resumen';

        var csvUrl = w.Sintel.Reporting.API.exportUrl(Object.assign({}, base, { export_format: 'csv' }));
        var xlsxUrl = w.Sintel.Reporting.API.exportUrl(Object.assign({}, base, { export_format: 'xlsx' }));

        exportContainer.innerHTML =
            '<a href="' + csvUrl + '" class="btn btn-sm btn-outline-secondary" title="Exportar CSV">' +
            '<i class="bi bi-filetype-csv"></i></a> ' +
            '<a href="' + xlsxUrl + '" class="btn btn-sm btn-outline-secondary" title="Exportar XLSX">' +
            '<i class="bi bi-file-earmark-excel"></i></a>';
    }

    if (form) {
        form.addEventListener('change', renderExportLinks);
        form.addEventListener('submit', renderExportLinks);
    }
    if (volverBtn) {
        volverBtn.addEventListener('click', function () {
            if (w.Sintel && w.Sintel.Core && w.Sintel.Core.ReportesLanding) {
                w.Sintel.Core.ReportesLanding.showCatalog();
            }
        });
    }

    renderExportLinks();
})(window, document);
