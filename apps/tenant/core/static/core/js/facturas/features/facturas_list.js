/**
 * Feature: Listado y Tabulator - Facturas v2.61.3
 * ⚠️ Feature-Sliced Architecture: Lógica de inicialización y gestión de Tabulator
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (FACTURAS_API_BASE)
 * ⚠️ Modular: Usa TabulatorFactory (The Engine)
 * ⚠️ Anti-Zombies: Previene instancias fantasma de Tabulator por recargas HTMX
 * 
 * ⚠️ v2.61.2: Facturas son solo lectura - botón "Ver" carga offcanvas_ver_factura.html
 * ⚠️ v2.61.2: Eliminación corrige URL hash a #facturas y cierra todos los offcanvas
 * ⚠️ v2.61.2: _eliminandoFactura flag para evitar rowClick tras eliminar+refresh
 * ⚠️ v2.61.3: Alineado con backend persisted:True - usa gestor-offcanvas con readonly=true
 * 
 * Dependencias globales requeridas:
 * - TabulatorFactory (definido en tabulator.factory.js)
 * - w.UIManager (definido en ui-manager.js) - Capa de Presentación (Error Boundary)
 * - w.VerDetalleFactura (definido en ver_detalle_factura.js) - Solo lectura
 */
(function(w, d) {
    'use strict';

    const MOD = '[facturas.list]';
    let table = null;
    // ⚠️ v2.61.2: Flag de módulo - previene rowClick durante eliminación (scope compartido)
    let _eliminandoFactura = false;

    // ⚠️ Anti-Zombies v2.60: Singleton global para instancias de Tabulator
    if (window.SintelFacturasTables) {
        Object.values(window.SintelFacturasTables).forEach(tb => {
            if (tb && typeof tb.destroy === 'function') {
                try {
                    tb.destroy();
                } catch (error) {
                    console.warn(`${MOD} Error al destruir instancia zombie:`, error);
                }
            }
        });
    }
    window.SintelFacturasTables = {};

    // Formateador de moneda
    function formatearMoneda(value) {
        if (value === null || value === undefined || value === '') return '$ 0,00';
        const num = parseFloat(value);
        if (isNaN(num)) return '$ 0,00';
        return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: 'COP',
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }).format(num);
    }

    // Formateador de fecha
    function formatearFecha(value) {
        if (!value) return '---';
        try {
            const date = new Date(value);
            return date.toLocaleDateString('es-CO', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        } catch (error) {
            return value;
        }
    }

    // Determinar estado de pago (Pagada, Pendiente, Vencida)
    function determinarEstadoPago(rowData) {
        const estado = rowData.estado || '';
        const fechaVencimiento = rowData.fecha_vencimiento;
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);

        // Si está aceptada, se considera pagada
        if (estado === 'ACEPTADA') {
            return { texto: 'Pagada', clase: 'bg-success' };
        }

        // Si está rechazada o anulada
        if (estado === 'RECHAZADA' || estado === 'ANULADA') {
            return { texto: estado === 'RECHAZADA' ? 'Rechazada' : 'Anulada', clase: 'bg-danger' };
        }

        // Si está enviada pero no aceptada
        if (estado === 'ENVIADA') {
            // Verificar si está vencida
            if (fechaVencimiento) {
                const fechaVen = new Date(fechaVencimiento);
                fechaVen.setHours(0, 0, 0, 0);
                if (fechaVen < hoy) {
                    return { texto: 'Vencida', clase: 'bg-warning' };
                }
            }
            return { texto: 'Pendiente', clase: 'bg-warning' };
        }

        // Borrador
        if (estado === 'BORRADOR') {
            return { texto: 'Borrador', clase: 'bg-secondary' };
        }

        // Default: Pendiente
        return { texto: 'Pendiente', clase: 'bg-warning' };
    }

    // Definir columnas específicas del módulo
    function getColumns() {
        return [
            {
                title: "Nro. Factura",
                field: "numero",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
                    return cell.getValue() || '---';
                },
                minWidth: 150
            },
            {
                title: "Naturaleza",
                field: "naturaleza",
                width: 120,
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="badge bg-secondary">---</span>';
                    // ⚠️ CAPA DE UI: JavaScript (Tabulator) - Formatter con badges de colores
                    // VENTA → badge success (verde), COMPRA → badge info (azul)
                    const color = val === 'VENTA' ? 'success' : 'info';
                    return `<span class="badge bg-${color}">${val}</span>`;
                },
                headerFilter: "select",
                headerFilterParams: {
                    values: {
                        "": "Todas",
                        "VENTA": "VENTA",
                        "COMPRA": "COMPRA"
                    }
                }
            },
            {
                title: "Cliente",
                field: "cliente_nombre",
                formatter: w.TabulatorFactory?.formatters?.valueOrFallback || function(cell) {
                    return cell.getValue() || '---';
                },
                minWidth: 250
            },
            {
                title: "Fecha Emisión",
                field: "fecha_emision",
                formatter: function(cell) {
                    return formatearFecha(cell.getValue());
                },
                width: 130
            },
            {
                title: "Vencimiento",
                field: "fecha_vencimiento",
                formatter: function(cell) {
                    const value = cell.getValue();
                    if (!value) return '---';
                    return formatearFecha(value);
                },
                width: 130
            },
            {
                title: "Estado",
                field: "estado",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    const estadoPago = determinarEstadoPago(rowData);
                    return `<span class="badge ${estadoPago.clase}">${estadoPago.texto}</span>`;
                },
                width: 120
            },
            {
                title: "Total",
                field: "total",
                formatter: function(cell) {
                    return formatearMoneda(cell.getValue());
                },
                hozAlign: "right",
                width: 150
            },
            {
                title: "Acciones",
                formatter: function(cell) {
                    const rowData = cell.getRow().getData();
                    const id = rowData.id;
                    
                    return `
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-primary btn-view-factura" data-id="${id}" title="Ver Factura">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-delete-factura" data-id="${id}" title="Eliminar Factura">
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

    // Inicializar Tabulator usando Factory (The Engine)
    function initTabulator() {
        if (!w.TabulatorFactory) {
            console.error(`${MOD} TabulatorFactory no está disponible`);
            return;
        }

        const gridElement = d.querySelector('#grid-facturas');
        if (!gridElement) {
            console.warn(`${MOD} Elemento #grid-facturas no encontrado`);
            return;
        }

        // ⚠️ Anti-Zombies v2.60: Destruir instancia previa si existe
        if (window.SintelFacturasTables.main) {
            try {
                window.SintelFacturasTables.main.destroy();
                console.log(`${MOD} Instancia zombie de Tabulator destruida`);
            } catch (error) {
                console.warn(`${MOD} Error al destruir instancia previa:`, error);
            }
        }

        // ⚠️ DRY: Solo definimos lo específico, el resto viene del Factory
        table = w.TabulatorFactory.create(
            '#grid-facturas',
            '/api/v1/facturas/',
            getColumns(),
            {
                searchInputSelector: '#search-factura'
            }
        );

        // ⚠️ Anti-Zombies v2.60: Guardar instancia en singleton global
        if (table) {
            window.SintelFacturasTables.main = table;
            console.log(`${MOD} Tabulator inicializado y guardado en SintelFacturasTables`);
            
            // ⚠️ Sincronizar summary cuando se carguen los datos
            if (typeof table.on === 'function') {
                // Sincronizar summary después de cargar datos
                table.on('dataLoaded', () => {
                    loadSummary();
                });
                
                // Sincronizar summary después de procesar datos
                table.on('dataProcessed', () => {
                    loadSummary();
                });
            }
            
            // ⚠️ v2.61.2: Configurar evento rowClick para modo solo lectura
            // ⚠️ _eliminandoFactura está en scope de módulo (compartido con initListEvents)
            if (typeof table.on === 'function') {
                table.on('rowClick', async (e, row) => {
                    // ⚠️ v2.61.2: Prevenir rowClick si se está eliminando una factura
                    if (_eliminandoFactura) {
                        console.log(`${MOD} rowClick ignorado: eliminación en proceso`);
                        return;
                    }
                    
                    const rowData = row.getData();
                    const id = rowData.id;
                    
                    if (!id) return;

                    // Evitar abrir si se hizo click en un botón
                    const target = e.target || e.originalEvent?.target;
                    if (target && target.closest && target.closest('button')) {
                        return;
                    }

                    // ⚠️ v2.61.2: Simular click en botón "Ver" para usar el flujo de solo lectura
                    const btnView = d.querySelector(`.btn-view-factura[data-id="${id}"]`);
                    if (btnView) {
                        btnView.click();
                    } else {
                        // Fallback: usar el mismo flujo que el botón Ver
                        try {
                            const offcanvasContainer = d.getElementById('offcanvas-container-facturas');
                            if (!offcanvasContainer) {
                                console.warn(`${MOD} Contenedor #offcanvas-container-facturas no encontrado`);
                                return;
                            }

                            // ⚠️ HTMX: Cargar template de solo lectura
                            await htmx.ajax('GET', `/api/v1/core/v1/facturas/facturas/gestor-offcanvas/?id=${id}&simple=true&readonly=true`, {
                                target: '#offcanvas-container-facturas',
                                swap: 'innerHTML'
                            });

                            // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
                            await new Promise(resolve => setTimeout(resolve, 100));

                            // ⚠️ v2.61.2: Buscar el offcanvas correcto
                            let offcanvasEl = d.getElementById('offcanvas-ver-factura');
                            if (!offcanvasEl) {
                                offcanvasEl = d.getElementById('offcanvas-factura');
                                if (offcanvasEl) {
                                    offcanvasEl.id = 'offcanvas-ver-factura';
                                    offcanvasEl.setAttribute('aria-labelledby', 'offcanvas-ver-factura-label');
                                }
                            }

                            if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                                const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                                
                                // ⚠️ v2.61.2: Cargar datos de la factura usando verDetalleFactura
                                // Intentar múltiples formas de acceso al módulo
                                if (w.VerDetalleFactura && typeof w.VerDetalleFactura.ver === 'function') {
                                    await w.VerDetalleFactura.ver(id);
                                } else if (typeof window.VerDetalleFactura !== 'undefined' && typeof window.VerDetalleFactura.ver === 'function') {
                                    await window.VerDetalleFactura.ver(id);
                                } else if (typeof window.verDetalleFactura === 'function') {
                                    await window.verDetalleFactura(id);
                                } else {
                                    console.warn(`${MOD} Función verDetalleFactura no disponible. Módulos disponibles:`, {
                                        VerDetalleFactura: typeof w.VerDetalleFactura,
                                        windowVerDetalleFactura: typeof window.VerDetalleFactura,
                                        verDetalleFactura: typeof window.verDetalleFactura
                                    });
                                    // ⚠️ Fallback: Intentar cargar datos directamente
                                    try {
                                        const response = await w.http('GET', `/api/v1/core/v1/facturas/facturas/${id}/`);
                                        if (response.ok && response.data) {
                                            console.log(`${MOD} Datos cargados directamente desde API (fallback)`);
                                        }
                                    } catch (error) {
                                        console.error(`${MOD} Error en fallback de carga de datos:`, error);
                                    }
                                }
                                
                                // Mostrar offcanvas después de cargar datos
                                offcanvasInstance.show();
                            }
                        } catch (error) {
                            console.error(`${MOD} Error al cargar Offcanvas desde fila:`, error);
                        }
                    }
                });
            }
        }

        return table;
    }

    // Event Delegation para acciones del Grid
    function initListEvents() {
        const gridElement = d.querySelector('#grid-facturas');
        if (!gridElement) {
            console.warn(`${MOD} Elemento #grid-facturas no encontrado para eventos`);
            return;
        }

        // ⚠️ Event Delegation: Escuchar clics en el contenedor del grid
        gridElement.addEventListener('click', async (e) => {
            // Botón Ver (abre Offcanvas de solo lectura)
            const btnView = e.target.closest('.btn-view-factura');
            if (btnView) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnView.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón sin data-id`);
                    return;
                }

                // ⚠️ Loading state
                const originalHTML = btnView.innerHTML;
                btnView.disabled = true;
                btnView.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // ⚠️ v2.61.2: Cargar template de solo lectura directamente
                    // Primero cargar el template HTML estático
                    const offcanvasContainer = d.getElementById('offcanvas-container-facturas');
                    if (!offcanvasContainer) {
                        console.warn(`${MOD} Contenedor #offcanvas-container-facturas no encontrado`);
                        return;
                    }

                    // ⚠️ HTMX: Cargar template de solo lectura desde el servidor
                    // Usar el endpoint gestor-offcanvas pero con modo solo lectura
                    await htmx.ajax('GET', `/api/v1/core/v1/facturas/facturas/gestor-offcanvas/?id=${id}&simple=true&readonly=true`, {
                        target: '#offcanvas-container-facturas',
                        swap: 'innerHTML'
                    });

                    // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
                    await new Promise(resolve => setTimeout(resolve, 100));

                    // ⚠️ v2.61.2: Buscar el offcanvas correcto (puede ser offcanvas-factura o offcanvas-ver-factura)
                    let offcanvasEl = d.getElementById('offcanvas-ver-factura');
                    if (!offcanvasEl) {
                        // Fallback: buscar offcanvas-factura y cambiar su ID
                        offcanvasEl = d.getElementById('offcanvas-factura');
                        if (offcanvasEl) {
                            offcanvasEl.id = 'offcanvas-ver-factura';
                            offcanvasEl.setAttribute('aria-labelledby', 'offcanvas-ver-factura-label');
                        }
                    }

                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const offcanvasInstance = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                        
                        // ⚠️ v2.61.2: Cargar datos de la factura usando verDetalleFactura
                        // Intentar múltiples formas de acceso al módulo
                        if (w.VerDetalleFactura && typeof w.VerDetalleFactura.ver === 'function') {
                            await w.VerDetalleFactura.ver(id);
                        } else if (typeof window.VerDetalleFactura !== 'undefined' && typeof window.VerDetalleFactura.ver === 'function') {
                            await window.VerDetalleFactura.ver(id);
                        } else if (typeof window.verDetalleFactura === 'function') {
                            await window.verDetalleFactura(id);
                        } else {
                            console.warn(`${MOD} Función verDetalleFactura no disponible. Módulos disponibles:`, {
                                VerDetalleFactura: typeof w.VerDetalleFactura,
                                windowVerDetalleFactura: typeof window.VerDetalleFactura,
                                verDetalleFactura: typeof window.verDetalleFactura
                            });
                            // ⚠️ Fallback: Intentar cargar datos directamente
                            try {
                                const response = await w.http('GET', `/api/v1/core/v1/facturas/facturas/${id}/`);
                                if (response.ok && response.data) {
                                    console.log(`${MOD} Datos cargados directamente desde API (fallback)`);
                                }
                            } catch (error) {
                                console.error(`${MOD} Error en fallback de carga de datos:`, error);
                            }
                        }
                        
                        // Mostrar offcanvas después de cargar datos
                        offcanvasInstance.show();
                    } else {
                        console.warn(`${MOD} No se pudo abrir el Offcanvas: elemento no encontrado o Bootstrap no disponible`);
                    }
                } catch (error) {
                    console.error(`${MOD} Error al cargar Offcanvas:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al cargar el detalle de la factura');
                    }
                } finally {
                    // Restaurar estado del botón
                    btnView.disabled = false;
                    btnView.innerHTML = originalHTML;
                }
                return;
            }

            // Botón Eliminar
            const btnDelete = e.target.closest('.btn-delete-factura');
            if (btnDelete) {
                e.preventDefault();
                e.stopPropagation();
                
                const id = btnDelete.getAttribute('data-id');
                if (!id) {
                    console.warn(`${MOD} Botón eliminar sin data-id`);
                    return;
                }

                // Confirmación
                if (!confirm('¿Está seguro de eliminar esta factura? Esta acción no se puede deshacer.')) {
                    return;
                }

                // ⚠️ v2.61.2: Activar flag para prevenir rowClick durante eliminación
                _eliminandoFactura = true;

                // ⚠️ Loading state
                const originalHTML = btnDelete.innerHTML;
                btnDelete.disabled = true;
                btnDelete.innerHTML = '<i class="bi bi-hourglass-split"></i>';

                try {
                    // ⚠️ v2.61.2: Usar Core API facade
                    const res = await w.http('DELETE', `/api/v1/core/v1/facturas/facturas/${id}/`);
                    
                    if (res.ok) {
                        // ⚠️ v2.61.2: Cerrar cualquier offcanvas abierto que muestre esta factura
                        const offcanvasVerFactura = d.getElementById('offcanvas-ver-factura');
                        const offcanvasFactura = d.getElementById('offcanvas-factura');
                        
                        if (offcanvasVerFactura && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                            const instance = bootstrap.Offcanvas.getInstance(offcanvasVerFactura);
                            if (instance) {
                                instance.hide();
                            }
                        }
                        if (offcanvasFactura && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                            const instance = bootstrap.Offcanvas.getInstance(offcanvasFactura);
                            if (instance) {
                                instance.hide();
                            }
                        }
                        
                        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                            w.SintelFeedback.success('Factura eliminada correctamente');
                        }
                        
                        // ⚠️ v2.61.2: Recargar grid y asegurar que estamos en la pestaña correcta
                        if (table && typeof table.replaceData === 'function') {
                            // Recargar datos sin disparar eventos de click
                            table.replaceData().then(() => {
                                // ⚠️ v2.61.2: Desactivar flag después de recargar (con delay para evitar eventos residuales)
                                setTimeout(() => {
                                    _eliminandoFactura = false;
                                }, 500);
                            });
                        } else {
                            // Si no hay tabla, desactivar flag inmediatamente
                            setTimeout(() => {
                                _eliminandoFactura = false;
                            }, 500);
                        }
                        
                        // ⚠️ v2.61.2: Asegurar que estamos en workspace/#facturas
                        if (w.location && w.location.hash !== '#facturas') {
                            w.location.hash = '#facturas';
                        }
                    } else {
                        // Si falla la eliminación, desactivar flag
                        _eliminandoFactura = false;
                        
                        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                            w.UIManager.handleError(res, MOD);
                        } else {
                            alert('Error al eliminar la factura');
                        }
                    }
                } catch (error) {
                    // Si hay error, desactivar flag
                    _eliminandoFactura = false;
                    
                    console.error(`${MOD} Error al eliminar factura:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al eliminar la factura');
                    }
                } finally {
                    btnDelete.disabled = false;
                    btnDelete.innerHTML = originalHTML;
                }
                return;
            }
        });

        console.log(`${MOD} Event delegation configurado`);
    }

    // ⚠️ Recarga Reactiva: Escuchar evento personalizado
    function initEventListeners() {
        // Escuchar evento de factura guardada para refrescar el grid
        d.addEventListener('facturaGuardada', () => {
            if (table && typeof table.replaceData === 'function') {
                table.replaceData();
                console.log(`${MOD} Grid refrescado tras guardar factura`);
            } else {
                console.warn(`${MOD} No se pudo refrescar: tabla no inicializada`);
            }
        });

        console.log(`${MOD} Event listeners configurados`);
    }

    // Inicialización principal
    function init() {
        console.log(`${MOD} Inicializando módulo de listado...`);

        // ⚠️ Lazy Loading: Solo inicializar cuando el tab esté visible
        const tabElement = d.querySelector('#tab-facturas');
        if (tabElement) {
            // Usar DOMUtils.onVisibleOnce si está disponible
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce(tabElement, () => {
                    initTabulator();
                    initListEvents();
                    initEventListeners();
                });
            } else {
                // Fallback: Inicializar directamente
                initTabulator();
                initListEvents();
                initEventListeners();
            }
        } else {
            // Si no hay tab, inicializar directamente
            initTabulator();
            initListEvents();
            initEventListeners();
            // ⚠️ Cargar summary al inicializar
            loadSummary();
        }
    }

    // ⚠️ HTMX: Limpiar instancias zombie en recargas
    if (typeof htmx !== 'undefined') {
        d.addEventListener('htmx:beforeSwap', (event) => {
            // Si se está recargando el contenedor principal, destruir instancias
            if (event.detail.target.id === 'tab-facturas-content' || 
                event.detail.target.closest('#tab-facturas-content')) {
                if (window.SintelFacturasTables.main) {
                    try {
                        window.SintelFacturasTables.main.destroy();
                        delete window.SintelFacturasTables.main;
                        console.log(`${MOD} Instancia destruida por HTMX swap`);
                    } catch (error) {
                        console.warn(`${MOD} Error al destruir instancia en HTMX swap:`, error);
                    }
                }
            }
        });
    }

    /**
     * Cargar y actualizar el resumen de facturación (Ventas Netas y Compras Netas)
     * ⚠️ Sincroniza con el endpoint GET /api/v1/facturas/summary/
     */
    async function loadSummary() {
        try {
            let summaryRes;
            
            // Intentar usar facturasAPI si está disponible
            if (w.facturasAPI && typeof w.facturasAPI.getSummary === 'function') {
                summaryRes = await w.facturasAPI.getSummary();
            } else if (w.http && typeof w.http === 'function') {
                summaryRes = await w.http('GET', '/api/v1/facturas/summary/');
            } else {
                console.warn(`${MOD} No hay API disponible para cargar summary`);
                return;
            }

            if (!summaryRes.ok) {
                console.error(`${MOD} Error al cargar summary:`, summaryRes);
                return;
            }

            const summary = summaryRes.data || {};
            const ventas = summary.ventas || {};
            const compras = summary.compras || {};

            // Formatear valores
            function formatMoney(value) {
                if (!value || value === '0.00' || value === '0') return '$ 0,00';
                const num = parseFloat(value);
                if (isNaN(num)) return '$ 0,00';
                return new Intl.NumberFormat('es-CO', {
                    style: 'currency',
                    currency: 'COP',
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 2
                }).format(num);
            }

            // Actualizar Ventas Netas
            const ventasTotalEl = d.getElementById('ventas-total-neto');
            const ventasSubtotalEl = d.getElementById('ventas-subtotal-neto');
            const ventasImpuestosEl = d.getElementById('ventas-impuestos-neto');
            
            if (ventasTotalEl) {
                ventasTotalEl.textContent = formatMoney(ventas.total_neto || '0.00');
            }
            if (ventasSubtotalEl) {
                ventasSubtotalEl.textContent = formatMoney(ventas.subtotal_neto || '0.00');
            }
            if (ventasImpuestosEl) {
                ventasImpuestosEl.textContent = formatMoney(ventas.impuestos_neto || '0.00');
            }

            // Actualizar Compras Netas
            const comprasTotalEl = d.getElementById('compras-total-neto');
            const comprasSubtotalEl = d.getElementById('compras-subtotal-neto');
            const comprasImpuestosEl = d.getElementById('compras-impuestos-neto');
            
            if (comprasTotalEl) {
                comprasTotalEl.textContent = formatMoney(compras.total_neto || '0.00');
            }
            if (comprasSubtotalEl) {
                comprasSubtotalEl.textContent = formatMoney(compras.subtotal_neto || '0.00');
            }
            if (comprasImpuestosEl) {
                comprasImpuestosEl.textContent = formatMoney(compras.impuestos_neto || '0.00');
            }

            console.log(`${MOD} Summary actualizado: Ventas=${ventas.total_neto || '0.00'}, Compras=${compras.total_neto || '0.00'}`);
        } catch (error) {
            console.error(`${MOD} Error al cargar summary:`, error);
        }
    }

    // Auto-inicializar cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ⚠️ API Pública: Exponer funciones para uso externo
    w.FacturasListModule = {
        init,
        refresh: () => {
            if (table && typeof table.replaceData === 'function') {
                table.replaceData();
            }
            // ⚠️ Sincronizar summary después de refrescar tabla
            loadSummary();
        },
        getTable: () => table,
        loadSummary  // ⚠️ Exponer función para uso externo
    };

    // ⚠️ Compatibilidad: Alias para uso legacy
    if (!w.FacturasModule) {
        w.FacturasModule = {
            refresh: () => {
                if (table && typeof table.replaceData === 'function') {
                    table.replaceData();
                }
            }
        };
    }

})(window, document);
