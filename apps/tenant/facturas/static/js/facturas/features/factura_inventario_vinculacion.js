/**
 * Feature: Vinculación Items Factura ↔ Inventario (v3.9.2+)
 * Permite buscar y vincular items de factura con productos/servicios de inventario
 * Endpoints: GET /api/v1/facturas/inventario-catalogo/?q=
 */
(function(w, d) {
    'use strict';

    const MOD = '[factura.inventario_vinculacion]';
    const API_CATALOGO = '/api/v1/facturas/inventario-catalogo/';

    class FacturaInventarioVinculacion {
        constructor() {
            this.container = d.getElementById('container-vinculaciones');
            this.tablaItems = d.getElementById('tbody-items-factura');
            this.itemsData = this.leerItemsDelDOM();
            this.render();
        }

        leerItemsDelDOM() {
            if (!this.tablaItems) return [];
            const rows = this.tablaItems.querySelectorAll('tr[data-item-id]');
            const items = [];
            rows.forEach((row, idx) => {
                const itemId = row.getAttribute('data-item-id');
                const codigo = row.querySelector('td:nth-child(2)')?.textContent?.trim() || '';
                const descripcion = row.querySelector('td:nth-child(3)')?.textContent?.trim() || '';
                items.push({ id: itemId, codigo, descripcion, idx: idx + 1 });
            });
            return items;
        }

        render() {
            if (!this.container || this.itemsData.length === 0) return;
            this.container.innerHTML = '';
            this.itemsData.forEach(item => {
                const col = d.createElement('div');
                col.className = 'col-12';
                col.innerHTML = this.renderItemRow(item);
                this.container.appendChild(col);
            });
            this.attachListeners();
        }

        renderItemRow(item) {
            return `
                <div class="card bg-light border-0 p-3" data-item-row="${item.id}">
                    <div class="row g-3 align-items-end">
                        <div class="col-md-4">
                            <label class="form-label small text-muted">Ítem #${item.idx}</label>
                            <div class="fw-bold text-truncate" title="${item.descripcion}">
                                ${item.descripcion}
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label small text-muted">Buscar en Inventario</label>
                            <div class="input-group">
                                <input
                                    type="text"
                                    class="form-control form-control-sm autocomplete-inventario"
                                    placeholder="Código o nombre..."
                                    data-item-id="${item.id}"
                                    autocomplete="off"
                                >
                                <button class="btn btn-outline-secondary btn-sm" type="button" data-action="limpiar-vinculacion" data-item-id="${item.id}" title="Limpiar vinculación">
                                    <i class="bi bi-x-circle"></i>
                                </button>
                            </div>
                            <div class="autocomplete-dropdown list-group position-absolute mt-1" style="display:none; width:100%; z-index:1000;" data-item-id="${item.id}"></div>
                        </div>
                        <div class="col-md-2">
                            <small class="d-block text-success fw-bold" data-status-vinculacion="${item.id}"></small>
                        </div>
                    </div>
                </div>
            `;
        }

        attachListeners() {
            // Listeners para búsqueda/autocomplete
            d.querySelectorAll('.autocomplete-inventario').forEach(input => {
                input.addEventListener('input', (e) => this.handleBusqueda(e));
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') {
                        const dropdown = d.querySelector(`.autocomplete-dropdown[data-item-id="${input.dataset.itemId}"]`);
                        if (dropdown) dropdown.style.display = 'none';
                    }
                });
            });

            // Listeners para limpiar vinculación
            d.querySelectorAll('[data-action="limpiar-vinculacion"]').forEach(btn => {
                btn.addEventListener('click', (e) => this.limpiarVinculacion(e));
            });
        }

        handleBusqueda(e) {
            const input = e.target;
            const query = input.value.trim();
            const itemId = input.dataset.itemId;
            const dropdown = d.querySelector(`.autocomplete-dropdown[data-item-id="${itemId}"]`);

            if (!dropdown) return;

            if (query.length < 1) {
                dropdown.style.display = 'none';
                return;
            }

            this.buscarEnInventario(query, itemId, dropdown);
        }

        buscarEnInventario(query, itemId, dropdown) {
            const params = new URLSearchParams({ q: query });
            w.http('GET', `${API_CATALOGO}?${params.toString()}`)
                .then(data => {
                    this.renderResultados(data, itemId, dropdown);
                })
                .catch(err => {
                    console.error(`${MOD} Error en búsqueda:`, err);
                    dropdown.innerHTML = '<div class="list-group-item text-danger small">Error en búsqueda</div>';
                    dropdown.style.display = 'block';
                });
        }

        renderResultados(resultados, itemId, dropdown) {
            dropdown.innerHTML = '';

            if (!resultados || resultados.length === 0) {
                dropdown.innerHTML = '<div class="list-group-item text-muted small">No encontrado</div>';
                dropdown.style.display = 'block';
                return;
            }

            resultados.forEach(item => {
                const btn = d.createElement('button');
                btn.type = 'button';
                btn.className = 'list-group-item list-group-item-action text-start small';
                btn.innerHTML = `
                    <div class="fw-bold">${item.nombre}</div>
                    <div class="text-muted">
                        <i class="bi bi-barcode me-1"></i>${item.codigo}
                        <span class="badge bg-secondary ms-2">${item.tipo}</span>
                    </div>
                `;
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.selectarItem(itemId, item);
                });
                dropdown.appendChild(btn);
            });

            dropdown.style.display = 'block';
        }

        selectarItem(itemId, inventarioItem) {
            const row = d.querySelector(`tr[data-item-id="${itemId}"]`);
            if (!row) return;

            // Guardar datos en hidden inputs dentro de la fila (se enviarán al backend)
            let hiddenContainer = row.querySelector('[data-inventario-fields]');
            if (!hiddenContainer) {
                hiddenContainer = d.createElement('div');
                hiddenContainer.className = 'd-none';
                hiddenContainer.dataset.inventarioFields = 'true';
                row.appendChild(hiddenContainer);
            }

            hiddenContainer.innerHTML = `
                <input type="hidden" name="item_inventario_uuid_${itemId}" value="${inventarioItem.uuid}">
                <input type="hidden" name="item_inventario_tipo_${itemId}" value="${inventarioItem.tipo}">
                <input type="hidden" name="item_inventario_codigo_${itemId}" value="${inventarioItem.codigo}">
            `;

            // Actualizar input y dropdown
            const input = d.querySelector(`.autocomplete-inventario[data-item-id="${itemId}"]`);
            if (input) {
                input.value = `✓ ${inventarioItem.nombre} (${inventarioItem.codigo})`;
            }

            const dropdown = d.querySelector(`.autocomplete-dropdown[data-item-id="${itemId}"]`);
            if (dropdown) {
                dropdown.style.display = 'none';
            }

            const status = d.querySelector(`[data-status-vinculacion="${itemId}"]`);
            if (status) {
                status.innerHTML = `<i class="bi bi-check-circle me-1"></i>Vinculado`;
            }
        }

        limpiarVinculacion(e) {
            const itemId = e.currentTarget.dataset.itemId;
            const row = d.querySelector(`tr[data-item-id="${itemId}"]`);
            if (!row) return;

            const hiddenContainer = row.querySelector('[data-inventario-fields]');
            if (hiddenContainer) hiddenContainer.innerHTML = '';

            const input = d.querySelector(`.autocomplete-inventario[data-item-id="${itemId}"]`);
            if (input) input.value = '';

            const status = d.querySelector(`[data-status-vinculacion="${itemId}"]`);
            if (status) status.innerHTML = '';

            const dropdown = d.querySelector(`.autocomplete-dropdown[data-item-id="${itemId}"]`);
            if (dropdown) dropdown.style.display = 'none';
        }
    }

    // Inicializar cuando el offcanvas se abre
    d.addEventListener('show.bs.offcanvas', (e) => {
        if (e.target?.id === 'offcanvas-factura') {
            setTimeout(() => {
                if (d.getElementById('container-vinculaciones')) {
                    new FacturaInventarioVinculacion();
                }
            }, 100);
        }
    });

    // Exportar para reutilización
    w.FacturaInventarioVinculacion = FacturaInventarioVinculacion;

})(window, document);
