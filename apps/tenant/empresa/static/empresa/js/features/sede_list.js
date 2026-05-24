/**
 * Feature: Listado y Tabulator - Sede v2.61
 * FSD: Logica de inicializacion y gestion de Tabulator para Sede
 * Namespace: window.SedeListModule
 */
(function(w, d) {
    'use strict';

    const MOD = '[sede.list]';
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
                title: "Sede",
                field: "nombre",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-geo-alt-fill text-primary me-2"></i><span class="fw-semibold">${val}</span>`;
                },
                minWidth: 200
            },
            {
                title: "Dirección",
                field: "direccion",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-house text-secondary me-1"></i><span class="small">${val}</span>`;
                },
                minWidth: 220
            },
            {
                title: "Teléfono",
                field: "telefono",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">—</span>';
                    return `<i class="bi bi-telephone text-success me-1"></i><span class="text-monospace">${val}</span>`;
                },
                width: 140,
                hozAlign: "center"
            },
            {
                title: "Encargado",
                field: "encargado_nombre",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="text-muted">Sin asignar</span>';
                    return `<i class="bi bi-person text-info me-1"></i><span>${val}</span>`;
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
                            <button type="button" class="btn btn-outline-primary btn-edit-sede" data-uuid="${uuid}" title="Editar Sede">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete-sede" data-uuid="${uuid}" title="Eliminar Sede">
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
        const gridElement = d.querySelector('#grid-sede');
        if (!gridElement) {
            console.warn(`${MOD} #grid-sede no encontrado`);
            return;
        }
        if (w.SintelEmpresaTables['sede']) {
            try { w.SintelEmpresaTables['sede'].destroy(); } catch (_) {}
        }
        table = w.TabulatorFactory.create('#grid-sede', '/api/v1/empresas/sedes/', getColumns(), {
            searchInputSelector: '#search-sede'
        });
        if (table) w.SintelEmpresaTables['sede'] = table;
        return table;
    }

    function initListEvents() {
        const gridElement = d.querySelector('#grid-sede');
        if (!gridElement) return;

        gridElement.addEventListener('click', async (e) => {
            const btnEdit   = e.target.closest('.btn-edit-sede');
            const btnDelete = e.target.closest('.btn-delete-sede');

            if (btnEdit) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnEdit.getAttribute('data-uuid');
                const originalHTML = btnEdit.innerHTML;
                btnEdit.disabled = true;
                btnEdit.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    await htmx.ajax('GET', `/api/v1/empresas/sedes/render-offcanvas/?uuid=${uuid}`, {
                        target: '#offcanvas-container-sede',
                        swap: 'innerHTML'
                    });
                    mostrarOffcanvasSeguro(d.getElementById('offcanvas-sede'));
                } catch (error) {
                    console.error(`${MOD} Error al cargar offcanvas:`, error);
                    w.SintelFeedback?.error?.('Error al cargar el formulario de sede');
                } finally {
                    btnEdit.disabled = false;
                    btnEdit.innerHTML = originalHTML;
                }
            }

            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                const uuid = btnDelete.getAttribute('data-uuid');
                if (!uuid || !confirm('Eliminar esta sede?')) return;
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                try {
                    const res = await w.http('DELETE', `/api/v1/empresas/sedes/${uuid}/`);
                    if (res.ok) {
                        w.SintelFeedback?.success?.('Sede eliminada correctamente');
                        d.dispatchEvent(new Event('sedeGuardada'));
                    } else {
                        w.SintelFeedback?.error?.(res.data?.error || 'Error al eliminar la sede');
                    }
                } catch (error) {
                    console.error(`${MOD} Error al eliminar sede:`, error);
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
            }
        });
    }

    function initEventListeners() {
        d.addEventListener('sedeGuardada', () => {
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
                if (w.SintelEmpresaTables['sede']) {
                    try {
                        w.SintelEmpresaTables['sede'].destroy();
                        delete w.SintelEmpresaTables['sede'];
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

    w.SedeListModule = {
        init,
        refresh: () => table?.replaceData?.(),
        getTable: () => table,
        mostrarOffcanvasSeguro
    };

})(window, document);
