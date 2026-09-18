/**
 * Feature: Ver Detalle Factura - Solo Lectura v2.61.3
 * ⚠️ v2.61.2: Refactorizado para eliminar capacidad de edición - Solo GET y asignación de datos
 * ⚠️ v2.61.2: Cierra offcanvas y muestra warning si la factura retorna 404 (eliminada)
 * ⚠️ v2.61.3: Alineado con backend persisted:True - verifica data.id para detectar persistencia
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume Core API facade (FACTURAS_API_BASE)
 * 
 * Localización: apps/tenant/core/static/core/js/facturas/features/ver_detalle_factura.js
 */
(function(w, d) {
    'use strict';

    const MOD = '[facturas.ver-detalle]';
    const FACTURAS_API_BASE = '/api/v1/facturas';

    /**
     * Formatear moneda usando Intl.NumberFormat
     * @param {number|string} value - Valor a formatear
     * @param {string} currency - Código de moneda (default: 'COP')
     * @returns {string} Valor formateado
     */
    function formatearMoneda(value, currency = 'COP') {
        if (value === null || value === undefined || value === '') return '$ 0,00';
        const num = parseFloat(value);
        if (isNaN(num)) return '$ 0,00';
        // T-1/T-2: delega a la SSoT de formateo de moneda (dom-utils.js) solo
        // para COP -- DOMUtils.formatCurrency no acepta moneda dinamica, y
        // aqui `currency` viene de `data.moneda`, en teoria no siempre COP.
        if (currency === 'COP' && w.DOMUtils && typeof w.DOMUtils.formatCurrency === 'function') {
            return w.DOMUtils.formatCurrency(num, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
        }
        return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }).format(num);
    }

    /**
     * Formatear fecha
     * @param {string} value - Fecha en formato ISO
     * @returns {string} Fecha formateada
     */
    function formatearFecha(value) {
        if (!value) return '-';
        try {
            const date = new Date(value);
            return date.toLocaleDateString('es-CO', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return value;
        }
    }

    /**
     * Formatear solo fecha (sin hora) -- usado para fecha_vencimiento,
     * payment_due_date, autorizacion_vigencia_* (DateField, no DateTimeField).
     * @param {string} value - Fecha en formato ISO (YYYY-MM-DD)
     * @returns {string} Fecha formateada
     */
    function formatearSoloFecha(value) {
        if (!value) return '-';
        try {
            const date = new Date(value.length === 10 ? value + 'T00:00:00' : value);
            return date.toLocaleDateString('es-CO', { year: 'numeric', month: '2-digit', day: '2-digit' });
        } catch (error) {
            return value;
        }
    }

    /**
     * Obtener badge de estado
     * @param {string} estado - Estado de la factura
     * @returns {string} HTML del badge
     */
    function getBadgeEstado(estado) {
        const estados = {
            'BORRADOR': { clase: 'bg-secondary', texto: 'Borrador' },
            'ENVIADA': { clase: 'bg-primary', texto: 'Enviada' },
            'ACEPTADA': { clase: 'bg-success', texto: 'Aceptada' },
            'RECHAZADA': { clase: 'bg-danger', texto: 'Rechazada' },
            'ANULADA': { clase: 'bg-dark', texto: 'Anulada' }
        };
        const estadoInfo = estados[estado] || { clase: 'bg-secondary', texto: estado || 'N/A' };
        return `<span class="badge ${estadoInfo.clase}">${estadoInfo.texto}</span>`;
    }

    /**
     * Reestructuracion arquitectonica (Facturas = document store): la
     * cotizacion vinculada se muestra como referencia documental de solo
     * lectura -- ya no ofrece vincular/desvincular desde Facturas (accion
     * de negocio ajena, mision §13). cotizacion_uuid/cotizacion_numero
     * siguen siendo campos validos en el DTO, solo se retiro la UI/endpoint
     * de escritura.
     */
    function renderCotizacionVinculada(data) {
        const container = d.getElementById('view_cotizacion_vinculada_container');
        const emptyState = d.getElementById('view_cotizacion_vinculada_empty');
        const card = d.getElementById('view_cotizacion_vinculada_card');
        const label = d.getElementById('view_cotizacion_vinculada_label');

        if (!container || !emptyState || !card || !label) return;

        container.dataset.facturaUuid = data.uuid || '';
        const info = data.cotizacion_vinculada_info || null;

        if (info) {
            emptyState.classList.add('d-none');
            card.classList.remove('d-none');
            card.classList.add('d-flex');
            label.textContent = info.label || info.codigo_unico || info.numero_cotizacion || info.uuid;
            return;
        }

        card.classList.add('d-none');
        card.classList.remove('d-flex');
        emptyState.classList.remove('d-none');
        emptyState.classList.add('d-flex');
    }

    /**
     * Ver detalle de factura - Solo lectura
     * ⚠️ v2.61.2: Solo hace GET y asigna datos, sin funciones de submit/update
     * @param {string} facturaId - ID de la factura
     */
    async function verDetalleFactura(facturaId) {
        if (!facturaId) {
            console.warn(`${MOD} ID de factura no proporcionado`);
            return;
        }

        try {
            // ⚠️ API-First: Usar Core API facade
            const url = `${FACTURAS_API_BASE}/${facturaId}/`;
            let response;

            // T-9: delega a la SSoT de endpoints (facturas.api.js) primero.
            if (w.facturasAPI && typeof w.facturasAPI.getFactura === 'function') {
                response = await w.facturasAPI.getFactura(facturaId);
            } else if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http) {
                response = await w.Sintel.Core.Http.request('GET', url);
            } else {
                // Fallback a fetch nativo
                const fetchRes = await fetch(url, {
                    headers: {
                        'Accept': 'application/json',
                        'X-CSRFToken': d.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    }
                });
                const data = await fetchRes.json();
                response = { ok: fetchRes.ok, status: fetchRes.status, data };
            }

            if (!response.ok) {
                console.error(`${MOD} Error al obtener los datos de la factura:`, response);
                
                // ⚠️ v2.61.2: Si es 404, la factura fue eliminada - cerrar offcanvas
                if (response.status === 404) {
                    const offcanvasEl = d.getElementById('offcanvas-ver-factura');
                    if (offcanvasEl && typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
                        const instance = bootstrap.Offcanvas.getInstance(offcanvasEl);
                        if (instance) {
                            instance.hide();
                        }
                    }
                    
                    if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
                        w.SintelFeedback.warning('La factura ya no existe (puede haber sido eliminada)');
                    } else {
                        alert('La factura ya no existe (puede haber sido eliminada)');
                    }
                    return;
                }
                
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(response, MOD);
                } else {
                    alert('Error al obtener los datos de la factura');
                }
                return;
            }

            const data = response.data || response;

            // ⚠️ Asignar datos a los elementos del DOM
            const setElement = (id, value, formatter = null) => {
                const el = d.getElementById(id);
                if (el) {
                    el.textContent = formatter ? formatter(value) : (value || '-');
                }
            };

            // Información General
            setElement('view_numero_factura', data.numero);
            setElement('view_estado', data.estado, (estado) => getBadgeEstado(estado));
            setElement('view_fecha_emision', data.fecha_emision, formatearFecha);
            setElement('view_fecha_vencimiento', data.fecha_vencimiento, formatearSoloFecha);
            setElement('view_moneda', data.moneda || 'COP');
            setElement('view_forma_pago', data.forma_pago);
            setElement('view_medio_pago', data.medio_pago_codigo);

            // Emisor
            setElement('view_emisor_razon_social', data.emisor_razon_social);
            setElement('view_emisor_nit', data.emisor_nit);

            // Receptor
            setElement('view_receptor_razon_social', data.receptor_razon_social);
            setElement('view_receptor_nit', data.receptor_nit);

            // Totales
            setElement('view_subtotal', data.subtotal, (val) => formatearMoneda(val, data.moneda || 'COP'));
            setElement('view_impuestos', data.impuestos, (val) => formatearMoneda(val, data.moneda || 'COP'));
            setElement('view_total', data.total, (val) => formatearMoneda(val, data.moneda || 'COP'));

            // Valor en Letras (FST-375 secc. 7/27) -- SIEMPRE generado por
            // backend (FacturaDetailSerializer.get_valor_en_letras), el
            // frontend solo lo muestra, nunca lo calcula.
            if (data.valor_en_letras) {
                const letrasContainer = d.getElementById('view_valor_en_letras_container');
                if (letrasContainer) letrasContainer.style.display = 'block';
                setElement('view_valor_en_letras', data.valor_en_letras);
            }

            // CUFE
            if (data.cufe) {
                const cufeContainer = d.getElementById('view_cufe_container');
                if (cufeContainer) {
                    cufeContainer.style.display = 'block';
                }
                setElement('view_cufe', data.cufe);
            }

            // Autorizacion DIAN (FST-375 secc. 11/31) -- solo lectura, oculto
            // si la factura no tiene ningun dato de autorizacion.
            const tieneAutorizacion = data.autorizacion_numero || data.autorizacion_prefijo
                || data.autorizacion_rango_desde || data.autorizacion_vigencia_inicio;
            if (tieneAutorizacion) {
                const autContainer = d.getElementById('view_autorizacion_container');
                if (autContainer) autContainer.style.display = 'block';

                if (data.autorizacion_numero) {
                    const wrap = d.getElementById('view_autorizacion_numero_wrap');
                    if (wrap) wrap.style.display = 'block';
                    setElement('view_autorizacion_numero', data.autorizacion_numero);
                }
                if (data.autorizacion_prefijo || data.autorizacion_rango_desde || data.autorizacion_rango_hasta) {
                    const wrap = d.getElementById('view_autorizacion_rango_wrap');
                    if (wrap) wrap.style.display = 'block';
                    const prefijo = data.autorizacion_prefijo || '-';
                    const desde = data.autorizacion_rango_desde ?? '-';
                    const hasta = data.autorizacion_rango_hasta ?? '-';
                    setElement('view_autorizacion_rango', null, () => `${prefijo} (desde ${desde} hasta ${hasta})`);
                }
                if (data.autorizacion_vigencia_inicio || data.autorizacion_vigencia_fin) {
                    const wrap = d.getElementById('view_autorizacion_vigencia_wrap');
                    if (wrap) wrap.style.display = 'block';
                    const inicio = formatearSoloFecha(data.autorizacion_vigencia_inicio);
                    const fin = formatearSoloFecha(data.autorizacion_vigencia_fin);
                    setElement('view_autorizacion_vigencia', null, () => `${inicio} - ${fin}`);
                }
            }

            // QR (FST-375 secc. 13): solo se muestra el texto crudo ya
            // persistido en la factura -- nunca se genera un QR ficticio.
            if (data.qr_code) {
                const qrContainer = d.getElementById('view_qr_container');
                if (qrContainer) qrContainer.style.display = 'block';
                setElement('view_qr_code', data.qr_code);
            }

            renderCotizacionVinculada(Object.freeze(data));

            // Desglose de impuestos (Fase 4)
            const taxBody = d.getElementById('view_impuestos_desglosados_body');
            if (taxBody) {
                taxBody.innerHTML = '';
                const impuestos = data.impuestos_desglosados;
                if (impuestos && Array.isArray(impuestos) && impuestos.length > 0) {
                    impuestos.forEach(tax => {
                        const row = d.createElement('tr');
                        row.innerHTML = `
                            <td><span class="fw-semibold">${tax.tipo_impuesto || 'OTRO'}</span></td>
                            <td class="text-end">${parseFloat(tax.porcentaje || 0).toFixed(2)}%</td>
                            <td class="text-end">${formatearMoneda(tax.base_imponible, data.moneda || 'COP')}</td>
                            <td class="text-end fw-semibold text-dark">${formatearMoneda(tax.valor_impuesto, data.moneda || 'COP')}</td>
                        `;
                        taxBody.appendChild(row);
                    });
                } else {
                    const row = d.createElement('tr');
                    row.innerHTML = '<td colspan="4" class="text-center text-muted">No se reportaron impuestos desglosados</td>';
                    taxBody.appendChild(row);
                }
            }

            // Items de la factura
            // ⚠️ v2.61.2: Cargar items desde endpoint separado si no vienen en la respuesta
            const tableBody = d.getElementById('view_detalle_items_body');
            if (tableBody) {
                tableBody.innerHTML = ''; // Limpiar previo

                let items = data.items;
                
                // Si no hay items en la respuesta, cargarlos desde el endpoint de items
                if (!items || !Array.isArray(items) || items.length === 0) {
                    try {
                        // BUG preexistente corregido: .replace('/facturas', '/items-factura')
                        // producia '/api/v1/items-factura' (ruta inexistente,
                        // 404 silencioso capturado abajo) -- la ruta real,
                        // segun apps/tenant/facturas/api/urls.py, esta ANIDADA
                        // bajo /facturas/ (router.register(r'items-factura', ...)
                        // dentro del mismo router de FacturaViewSet).
                        const itemsUrl = `${FACTURAS_API_BASE}/items-factura/?factura=${facturaId}`;
                        let itemsResponse;
                        
                        if (w.Sintel && w.Sintel.Core && w.Sintel.Core.Http) {
                            itemsResponse = await w.Sintel.Core.Http.request('GET', itemsUrl);
                        } else {
                            const fetchRes = await fetch(itemsUrl, {
                                headers: {
                                    'Accept': 'application/json',
                                    'X-CSRFToken': d.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                                }
                            });
                            const itemsData = await fetchRes.json();
                            itemsResponse = { ok: fetchRes.ok, status: fetchRes.status, data: itemsData };
                        }
                        
                        if (itemsResponse.ok && itemsResponse.data) {
                            // Si la respuesta es un objeto con 'results', usar results
                            items = itemsResponse.data.results || itemsResponse.data;
                            if (!Array.isArray(items)) {
                                items = [];
                            }
                        }
                    } catch (error) {
                        console.warn(`${MOD} Error al cargar items:`, error);
                        items = [];
                    }
                }

                if (items && Array.isArray(items) && items.length > 0) {
                    items.forEach(item => {
                        const row = d.createElement('tr');
                        // ⚠️ v2.61.2: Usar valor_unitario en lugar de precio_unitario
                        const valorUnitario = item.valor_unitario || item.precio_unitario || 0;
                        const cantidad = item.cantidad || 0;
                        const total = item.total || (cantidad * valorUnitario);
                        
                        row.innerHTML = `
                            <td class="text-start">${item.descripcion || '-'}</td>
                            <td class="text-end">${cantidad}</td>
                            <td class="text-end">${formatearMoneda(valorUnitario, data.moneda || 'COP')}</td>
                            <td class="text-end">${formatearMoneda(total, data.moneda || 'COP')}</td>
                        `;
                        tableBody.appendChild(row);
                    });
                } else {
                    // Si no hay items, mostrar mensaje
                    const row = d.createElement('tr');
                    row.innerHTML = '<td colspan="4" class="text-center text-muted">No hay items disponibles</td>';
                    tableBody.appendChild(row);
                }
            }

            console.log(`${MOD} Detalle de factura cargado correctamente: ${data.numero || facturaId}`);

        } catch (error) {
            console.error(`${MOD} Error de conexión:`, error);
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error de conexión' } }, MOD);
            } else {
                alert('Error de conexión al obtener los datos de la factura');
            }
        }
    }

    // ⚠️ API Pública: Exponer función para uso externo
    w.VerDetalleFactura = {
        ver: verDetalleFactura
    };

    // ⚠️ Compatibilidad: Alias global
    if (typeof window.verDetalleFactura === 'undefined') {
        window.verDetalleFactura = verDetalleFactura;
    }

})(window, document);
