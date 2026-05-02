// Tabulator Factory para Empresa
// API: GET /api/v1/empresas/
// Contrato: nit, direccion, telefono, email_contacto, regimen_tributario, moneda

(function(window) {
    const EmpresaPage = {
        table: null,
        init: function() {
            DOMUtils.onVisibleOnce('#empresa-table', () => {
                this.initTable();
            });
        },
        initTable: function() {
            this.table = new Tabulator('#empresa-table', {
                ajaxURL: '/api/v1/empresas/',
                ajaxConfig: 'GET',
                layout: 'fitColumns',
                pagination: 'remote',
                paginationSize: 10,
                columns: [
                    { title: 'NIT', field: 'nit', headerFilter: true },
                    { title: 'Dirección', field: 'direccion' },
                    { title: 'Teléfono', field: 'telefono' },
                    { title: 'Email', field: 'email_contacto' },
                    { title: 'Régimen', field: 'regimen_tributario' },
                    { title: 'Moneda', field: 'moneda' }
                ],
                ajaxResponse: function(url, params, response) {
                    // DRF paginated response
                    return response.results;
                }
            });
        }
    };
    window.Sintel = window.Sintel || {};
    window.Sintel.Empresa = EmpresaPage;
    document.addEventListener('DOMContentLoaded', function() {
        EmpresaPage.init();
    });
})(window);
