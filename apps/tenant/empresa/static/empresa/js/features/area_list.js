/**
 * Feature: Listado y Tabulator - Area v2.61
 * FSD: Logica de inicializacion y gestion de Tabulator para Area
 * Namespace: window.AreaListModule
 */
(function(w, d) {
    'use strict';

    const MOD = '[area.list]';
    let table = null;

    if (!w.SintelEmpresaTables) {
        w.SintelEmpresaTables = {};
    }

    // Helper anti-backdrop-acumulado (patron inventario v3.9.0)
    function mostrarOffcanvasSeguro(el) {
        if (!el || !w.bootstrap || !w.bootstrap.Offcanvas) return;
        d.querySelectorAll('.offcanvas-backdrop').forEach(function(b) { b.remove(); });
        d.body.classList.remove('overflow-hidden', 'modal-open');
        var prev = bootstrap.Offcanvas.getInstance(el);
        if (prev) prev.dispose();
        new bootstrap.Offcanvas(el).show();
    }

    function getColumns() {
        return [
            {
                title: "Área / Departamento",
                field: "nombre",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-diagram-3 text-success me-2"></i><span class="fw-semibold">${val}</span>`;
                },
                minWidth: 200
            },
            {
                title: "Código",
                field: "codigo_funcionamiento",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<code class="bg-light px-2 py-1 rounded small">${val}</code>`;
                },
                width: 140,
                hozAlign: "center"
            },
            {
                title: "Sede",
                field: "sede_nombre",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-geo-alt text-primary me-1"></i><span class="small">${val}</span>`;
                },
                minWidth: 180
            },
            {
                title: "Responsable",
                field: "responsable_nombre",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">Sin asignar</span>';
                    return `<i class="bi bi-person-fill text-info me-1"></i><span>${val}</span>`;
                },
                minWidth: 160
            },
            {
                title: "Acciones",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    const id   = rowData.id;
                    const uuid = rowData.uuid;
                    return `
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-primary btn-edit-area" data-uuid="${uuid}" title="Editar Área">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete-area" data-uuid="${uuid}" title="Eliminar Área">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    `;
                },
                headerSort: false,
                hozAlign: "center",
                width: 120
            }
        ];
    }

    function initTabulator() {
        if (!w.TabulatorFactory) {
            console.error(`${MOD} TabulatorFactory no disponible`);
            return;
        }
        const gridElement = d.querySelector('#grid-area');
        if (!gridElement) {
            console.warn(`${MOD} #grid-area no encontrado`);
            return;
        }
        if (w.SintelEmpresaTables['area']) {
            try { w.SintelEmpresaTables['area'].destroy(); } catch (_) {}
        }
        table = w.TabulatorFactory.create('#grid-area', '/api/v1/empresas/areas/', getColumns(), {
            searchInputSelector: '#search-area'
        });
        if (table) w.SintelEmpresaTables['area'] = table;
        return table;
    }

    function initListEvents() {
        const gridElement = d.querySelector('#grid-area');
        if (!gridElement) return;

        gridElement.addEventListener('click', async (e) => {
            const btnEdit   = e.target.closest('.btn-edit-area');
            const btnDelete = e.target.closest('.btn-delete-area');

            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnEdit.getAttribute('data-uuid');
                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `/api/v1/empresas/areas/render-offcanvas/?uuid=${uuid}`, {
                        target: '#offcanvas-container-area',
                        swap: 'innerHTML'
                    });
                    mostrarOffcanvasSeguro(d.getElementById('offcanvas-area'));
                } catch (error) {
                    console.error(`${MOD} Error al cargar offcanvas:`, error);
                    w.SintelFeedback?.error?.('Error al cargar el formulario de area');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
            }

            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnDelete.getAttribute('data-uuid');
                if (!uuid || !confirm('Eliminar esta area?')) return;
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const res = await w.http('DELETE', `/api/v1/empresas/areas/${uuid}/`);
                    if (res.ok) {
                        w.SintelFeedback?.success?.('Area eliminada correctamente');
                        d.dispatchEvent(new Event('areaGuardada'));
                    } else {
                        w.SintelFeedback?.error?.(res.data?.error || 'Error al eliminar el area');
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar area:`, error);
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
            }
        });
    }

    function initEventListeners() {
        d.addEventListener('areaGuardada', () => {
            table?.replaceData?.();
        });
    }

    function init() {
        initTabulator();
        initListEvents();
        initEventListeners();
    }

    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:beforeSwap', (event) => {
            if (event.detail.target.id === 'ui-empresa-list' ||
                event.detail.target.closest?.('#ui-empresa-list')) {
                if (w.SintelEmpresaTables['area']) {
                    try {
                        w.SintelEmpresaTables['area'].destroy();
                        delete w.SintelEmpresaTables['area'];
                    } catch (_) {}
                }
            }
        });
    }

    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    w.AreaListModule = {
        init,
        refresh: () => table?.replaceData?.(),
        getTable: () => table,
        mostrarOffcanvasSeguro
    };

})(window, document);
