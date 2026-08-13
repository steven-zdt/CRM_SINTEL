/**
 * Feature: Autocomplete Facturas para Registrar Movimiento (v3.9.2)
 * Permite buscar facturas en el campo de búsqueda y vincularlas al movimiento
 * al registrar un movimiento de inventario
 */
(function(w, d) {
    'use strict';

    const MOD = '[inventario.movimiento_facturas]';
    const API_ENDPOINT = '/api/v1/facturas/buscar-para-movimiento/';

    class MovimientoFacturasAutocomplete {
        constructor() {
            this.inputElement = d.getElementById('movimiento-busqueda-factura');
            this.dropdownElement = d.getElementById('movimiento-facturas-dropdown');
            this.tipoMovimientoSelect = d.getElementById('tipo_movimiento');
            this.facturaVinculadaDiv = d.getElementById('movimiento-factura-vinculada');
            this.facturaVinculadaText = d.getElementById('movimiento-factura-vinculada-text');
            this.btnLimpiar = d.getElementById('movimiento-btn-limpiar-factura');
            this.uuidInput = d.getElementById('movimiento-factura-uuid');
            this.numeroInput = d.getElementById('movimiento-factura-numero');

            console.log(`${MOD} Constructor ejecutado. Elementos encontrados:`, {
                inputElement: !!this.inputElement,
                dropdownElement: !!this.dropdownElement,
                tipoMovimientoSelect: !!this.tipoMovimientoSelect
            });

            if (this.inputElement && this.dropdownElement) {
                this.attachListeners();
            }
        }

        attachListeners() {
            // Input listener para búsqueda
            this.inputElement.addEventListener('input', (e) => this.handleBusqueda(e));

            // Cierre con Escape
            this.inputElement.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.dropdownElement.classList.add('d-none');
                }
            });

            // Click fuera del dropdown para cerrar
            d.addEventListener('click', (e) => {
                if (!this.inputElement.contains(e.target) && !this.dropdownElement.contains(e.target)) {
                    this.dropdownElement.classList.add('d-none');
                }
            });

            // Botón limpiar
            if (this.btnLimpiar) {
                this.btnLimpiar.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.limpiarFactura();
                });
            }

            // Actualizar placeholder y limpiar al cambiar tipo de movimiento
            if (this.tipoMovimientoSelect) {
                this.tipoMovimientoSelect.addEventListener('change', () => this.actualizarPorTipo());
            }
        }

        actualizarPorTipo() {
            const tipo = this.tipoMovimientoSelect?.value || '';
            let placeholder = 'Buscar factura por # o cliente...';
            if (tipo === 'ENTRADA_COMPRA') {
                placeholder = 'Buscar factura de compra (proveedor)...';
            } else if (tipo === 'SALIDA_VENTA' || tipo === 'ENTRADA_DEVOLUCION') {
                placeholder = 'Buscar factura de venta (cliente)...';
            }
            if (this.inputElement) {
                this.inputElement.placeholder = placeholder;
            }
            this.limpiarFactura();
        }

        handleBusqueda(e) {
            const query = e.target.value.trim();
            clearTimeout(this._debounce);
            if (query.length < 2) {
                this.dropdownElement.classList.add('d-none');
                return;
            }
            this._debounce = setTimeout(() => this.buscarFacturas(query), 300);
        }

        async buscarFacturas(query) {
            console.log(`${MOD} buscarFacturas llamado con query:`, query);

            // Inferir naturaleza desde el tipo de movimiento seleccionado
            const tipoMovimiento = this.tipoMovimientoSelect?.value || '';
            let naturaleza = '';

            if (tipoMovimiento === 'ENTRADA_COMPRA') {
                naturaleza = 'COMPRA';
            } else if (tipoMovimiento === 'SALIDA_VENTA' || tipoMovimiento === 'ENTRADA_DEVOLUCION') {
                naturaleza = 'VENTA';
            }
            // ENTRADA_AJUSTE, SALIDA_BAJA, SALIDA_CONSUMO, ACTIVO types: sin filtro naturaleza

            const params = new URLSearchParams({ q: query });
            if (naturaleza) {
                params.append('naturaleza', naturaleza);
            }

            const urlCompleta = `${API_ENDPOINT}?${params.toString()}`;
            console.log(`${MOD} Llamando a API:`, urlCompleta);

            try {
                if (!w.Sintel || !w.Sintel.Core || !w.Sintel.Core.Http) {
                    console.error(`${MOD} HTTP client no disponible. Sintel.Core.Http=`, typeof (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http));
                    this.dropdownElement.innerHTML = '<div class="list-group-item text-danger small">HTTP client no disponible</div>';
                    this.dropdownElement.classList.remove('d-none');
                    return;
                }

                const res = await w.Sintel.Core.Http.request('GET', urlCompleta);
                console.log(`${MOD} Respuesta recibida:`, {ok: res.ok, status: res.status, dataType: typeof res.data, dataIsArray: Array.isArray(res.data), dataLength: Array.isArray(res.data) ? res.data.length : 'N/A'});

                if (!res.ok) {
                    console.error(`${MOD} API error:`, res.status, res.data);
                    this.dropdownElement.innerHTML = '<div class="list-group-item text-danger small">Error en búsqueda: ' + res.status + '</div>';
                    this.dropdownElement.classList.remove('d-none');
                    return;
                }

                // Extraer datos del response - puede ser un array directo o dentro de res.data
                const resultados = Array.isArray(res.data) ? res.data : (res.data?.results || []);
                console.log(`${MOD} Resultados extraídos:`, resultados.length, resultados);

                this.renderResultados(resultados);
            } catch (err) {
                console.error(`${MOD} Error en búsqueda (exception):`, err);
                this.dropdownElement.innerHTML = '<div class="list-group-item text-danger small">Error: ' + (err.message || 'desconocido') + '</div>';
                this.dropdownElement.classList.remove('d-none');
            }
        }

        renderResultados(resultados) {
            console.log(`${MOD} renderResultados() llamado con:`, resultados);
            this.dropdownElement.innerHTML = '';

            if (!resultados || resultados.length === 0) {
                console.warn(`${MOD} Sin resultados, mostrando mensaje vacío`);
                this.dropdownElement.innerHTML = '<div class="list-group-item text-muted small">No se encontraron facturas</div>';
                this.dropdownElement.classList.remove('d-none');
                console.log(`${MOD} d-none removido, visible ahora?:`, !this.dropdownElement.classList.contains('d-none'));
                return;
            }
            console.log(`${MOD} Renderizando ${resultados.length} resultados`);

            resultados.forEach((factura) => {
                const btn = d.createElement('button');
                btn.type = 'button';
                btn.className = 'list-group-item list-group-item-action text-start small';
                btn.innerHTML = `
                    <div class="d-flex justify-content-between">
                        <strong>${factura.numero}</strong>
                        <span class="badge bg-primary">${factura.naturaleza}</span>
                    </div>
                    <div class="text-muted small mt-1">
                        <i class="bi bi-person me-1"></i>${factura.cliente}
                        <span class="ms-2"><i class="bi bi-calendar me-1"></i>${factura.fecha}</span>
                    </div>
                    <div class="text-success fw-bold mt-1">
                        <i class="bi bi-currency-dollar"></i>${factura.total}
                    </div>
                `;

                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.selectarFactura(factura);
                });

                this.dropdownElement.appendChild(btn);
            });

            this.dropdownElement.classList.remove('d-none');
            console.log(`${MOD} Dropdown mostrado, visibilidad:`, {
                classList: this.dropdownElement.className,
                hasDNone: this.dropdownElement.classList.contains('d-none'),
                innerHTML: this.dropdownElement.innerHTML.substring(0, 100),
                offsetHeight: this.dropdownElement.offsetHeight,
                offsetWidth: this.dropdownElement.offsetWidth
            });
        }

        selectarFactura(factura) {
            // Llenar el input con el número de la factura
            this.inputElement.value = `${factura.numero} - ${factura.cliente}`;

            // Asignar valores a los hidden inputs
            if (this.uuidInput) this.uuidInput.value = factura.uuid;
            if (this.numeroInput) this.numeroInput.value = factura.numero;

            // Guardar en atributo data para referencia
            this.inputElement.dataset.facturaUuid = factura.uuid;
            this.inputElement.dataset.facturaNaturaleza = factura.naturaleza;

            // Mostrar tarjeta de factura vinculada
            this.mostrarFacturaVinculada(factura);

            // Cerrar dropdown
            this.dropdownElement.classList.add('d-none');

            console.log(`${MOD} Factura seleccionada y vinculada:`, factura);
        }

        mostrarFacturaVinculada(factura) {
            if (!this.facturaVinculadaDiv || !this.facturaVinculadaText) return;

            this.facturaVinculadaText.innerHTML = `
                <strong>${factura.numero}</strong> | ${factura.cliente} | $${factura.total} | ${factura.fecha}
            `;
            this.facturaVinculadaDiv.classList.remove('d-none');

            if (this.btnLimpiar) {
                this.btnLimpiar.style.display = 'block';
            }
        }

        limpiarFactura() {
            // Limpiar input
            this.inputElement.value = '';
            this.inputElement.dataset.facturaUuid = '';
            this.inputElement.dataset.facturaNaturaleza = '';

            // Limpiar hidden inputs
            if (this.uuidInput) this.uuidInput.value = '';
            if (this.numeroInput) this.numeroInput.value = '';

            // Ocultar tarjeta y botón
            if (this.facturaVinculadaDiv) {
                this.facturaVinculadaDiv.classList.add('d-none');
            }
            if (this.btnLimpiar) {
                this.btnLimpiar.style.display = 'none';
            }

            console.log(`${MOD} Factura vinculada limpiada`);
        }
    }

    // Inicializar cuando el offcanvas de movimientos se abre
    d.addEventListener('show.bs.offcanvas', (e) => {
        console.log(`${MOD} Evento show.bs.offcanvas. target.id=`, e.target?.id);
        if (e.target?.id === 'offcanvas-movimientos') {
            console.log(`${MOD} Inicializando MovimientoFacturasAutocomplete desde evento offcanvas`);
            setTimeout(() => {
                new MovimientoFacturasAutocomplete();
            }, 100);
        }
    });

    // Exportar para acceso global
    w.MovimientoFacturasAutocomplete = MovimientoFacturasAutocomplete;
    console.log(`${MOD} Script cargado. MovimientoFacturasAutocomplete exportada a window.`);

})(window, document);
