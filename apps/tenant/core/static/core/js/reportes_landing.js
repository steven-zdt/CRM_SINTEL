/**
 * reportes_landing.js -- catalogo del Reporting Hub (window.Sintel.Core.ReportesLanding).
 *
 * Usa Sintel.Reporting.API.catalog() (Report API Client) para listar los
 * datasets REALES registrados en el backend -- Regla Absoluta #4 de la
 * mision Reporting Hub Frontend: nunca inventar datasets en el frontend.
 *
 * El mapeo dataset_id -> URL de pantalla es deliberadamente frontend-only
 * (el contrato ReportDataset del backend no conoce rutas de UI, ver
 * apps/services/reporting/contracts.py) -- un dataset sin pantalla propia
 * todavia se muestra como "Proximamente" en vez de ocultarse, para que el
 * catalogo real quede visible aunque la UI vaya un paso atras (FASE 39,
 * loop de expansion).
 */
(function (w, d) {
    'use strict';

    // dataset_id -> URL del contenedor HTMX de su pantalla de reporte.
    var KNOWN_VIEWS = {
        'ventas.resumen': '/ui/ventas/reportes/',
    };

    var GROUP_ICONS = {
        ventas: 'bag-check',
        contabilidad: 'journal-text',
        inventario: 'box-seam',
        facturas: 'receipt',
        gastos: 'cash-stack',
        clientes: 'person-badge',
        proveedores: 'truck',
        empleados: 'people',
    };

    function showError(message) {
        var content = d.getElementById('reportes-content');
        if (!content) return;
        content.innerHTML =
            '<div class="alert alert-danger d-flex align-items-center gap-2 mb-0">' +
            '<i class="bi bi-exclamation-triangle fs-5"></i><div>' + message + '</div></div>';
    }

    function datasetCard(dataset) {
        var icon = GROUP_ICONS[dataset.owner_app] || 'file-earmark-bar-graph';
        var viewUrl = KNOWN_VIEWS[dataset.dataset_id];
        var actionHtml = viewUrl
            ? '<button type="button" class="btn btn-sm btn-primary" ' +
              'hx-get="' + viewUrl + '" hx-target="#reportes-content" hx-swap="innerHTML">' +
              'Ver reporte <i class="bi bi-arrow-right ms-1"></i></button>'
            : '<span class="badge text-bg-light border">Proximamente</span>';

        return (
            '<div class="col-12 col-md-6 col-xl-4">' +
            '<div class="card border-0 shadow-sm h-100">' +
            '<div class="card-body d-flex flex-column">' +
            '<div class="d-flex align-items-center gap-2 mb-2">' +
            '<i class="bi bi-' + icon + ' text-primary fs-5"></i>' +
            '<span class="badge text-bg-light border text-uppercase" style="font-size:.65rem;">' + dataset.owner_app + '</span>' +
            '</div>' +
            '<h6 class="fw-bold mb-1">' + dataset.name + '</h6>' +
            '<p class="text-muted small mb-3 flex-grow-1">' + dataset.description + '</p>' +
            actionHtml +
            '</div></div></div>'
        );
    }

    function showCatalog() {
        var content = d.getElementById('reportes-content');
        if (!content) return;
        content.innerHTML =
            '<div class="text-center py-5"><div class="spinner-border text-primary opacity-50" role="status"></div>' +
            '<p class="text-muted mt-2">Cargando catalogo de reportes...</p></div>';

        if (!w.Sintel || !w.Sintel.Reporting || !w.Sintel.Reporting.API) {
            showError('No fue posible cargar el catalogo de reportes.');
            return;
        }

        w.Sintel.Reporting.API.catalog()
            .then(function (datasets) {
                if (!datasets || datasets.length === 0) {
                    content.innerHTML = '<p class="text-muted">No hay reportes disponibles todavia.</p>';
                    return;
                }
                content.innerHTML = '<div class="row g-3">' + datasets.map(datasetCard).join('') + '</div>';
                if (w.htmx) w.htmx.process(content);
            })
            .catch(function (err) {
                if (err && err.status === 403) {
                    showError('Sin permisos para consultar el catalogo de reportes.');
                } else {
                    showError('No fue posible generar el reporte.');
                }
            });
    }

    w.Sintel = w.Sintel || {};
    w.Sintel.Core = w.Sintel.Core || {};
    w.Sintel.Core.ReportesLanding = { showCatalog: showCatalog };

    // WARNING: BUGFIX: este <script> vive dentro de #tab-reportes, que el
    // DOM recorre ANTES que assets_core.html (incluido al final de
    // workspace.html -- ver comentario en workspace.html:279 "HTMX debe
    // cargarse ANTES de assets_core.html"). Llamar showCatalog() de forma
    // sincrona aqui corria antes de que Sintel.Core.Http/Reporting.API
    // existieran -- confirmado en vivo: "No fue posible cargar el catalogo
    // de reportes." en cada carga real. DOMContentLoaded solo se dispara
    // despues de que TODOS los <script> del documento (incluidos los de
    // assets_core.html, mas abajo en el DOM) ya se ejecutaron.
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', showCatalog);
    } else {
        showCatalog();
    }
})(window, document);
