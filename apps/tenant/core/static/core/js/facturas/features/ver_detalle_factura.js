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
    const FACTURAS_API_BASE = '/api/v1/core/v1/facturas/facturas';

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
            
            if (w.http && typeof w.http === 'function') {
                response = await w.http('GET', url);
            } else if (w.facturasAPI && typeof w.facturasAPI.getFactura === 'function') {
                response = await w.facturasAPI.getFactura(facturaId);
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
            setElement('view_moneda', data.moneda || 'COP');

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

            // CUFE
            if (data.cufe) {
                const cufeContainer = d.getElementById('view_cufe_container');
                if (cufeContainer) {
                    cufeContainer.style.display = 'block';
                }
                setElement('view_cufe', data.cufe);
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
                        const itemsUrl = `${FACTURAS_API_BASE.replace('/facturas', '/items-factura')}/?factura=${facturaId}`;
                        let itemsResponse;
                        
                        if (w.http && typeof w.http === 'function') {
                            itemsResponse = await w.http('GET', itemsUrl);
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