/**
 * facturas_ui.js - Módulo Centralizado de UI para Facturas v2.60
 * ⚠️ Feature-Sliced Architecture: Capa de Presentación - Lógica de interacción con Offcanvas
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ API-First: Consume DRF REST API vía facturasAPI
 * ⚠️ HTMX Integration: Maneja carga dinámica de Offcanvas
 * ⚠️ Zero Trust: Validaciones de seguridad en cliente
 * 
 * Responsabilidades:
 * - Inicialización y gestión del Offcanvas de facturas
 * - Subida de archivos XML/PDF
 * - Visualización de facturas (detalle)
 * - Eliminación de facturas
 * - Integración con módulos list y editor
 * 
 * Dependencias globales requeridas:
 * - window.facturasAPI (definido en facturas.api.js) - Capa de Datos
 * - window.http (definido en lib/http.js) - Helper HTTP
 * - window.SintelFeedback (definido en sintel-feedback.js) - Feedback visual
 * - window.UIManager (definido en ui-manager.js) - Error Boundary
 * - htmx (global) - HTMX library
 * - bootstrap (global) - Bootstrap 5
 */
(function(w, d) {
    'use strict';

    const MOD = '[facturas.ui]';
    const OFFCANVAS_ID = 'offcanvas-factura'; // ⚠️ Sincronizado con templates: offcanvas_factura.html y offcanvas_form.html
    const OFFCANVAS_CONTAINER_ID = 'offcanvas-container-facturas';
    const GESTOR_OFFCANVAS_URL = '/api/v1/facturas/gestor-offcanvas/';

    // ⚠️ Singleton: Instancia del Offcanvas
    let offcanvasInstance = null;

    // ⚠️ CRÍTICO v2.60: Exponer AppFacturas INMEDIATAMENTE (antes de definir funciones)
    // Esto permite que los eventos onclick en el HTML funcionen incluso si el módulo aún no está completamente inicializado
    // Las funciones se asignarán más adelante, pero el objeto debe existir desde el principio
    // Usaremos funciones que se auto-actualizan cuando las funciones reales estén disponibles
    if (!w.AppFacturas) {
        w.AppFacturas = {};
        console.log(`${MOD} AppFacturas expuesto inmediatamente (se actualizará con funciones reales)`);
    }

    /**
     * Inicializar el Offcanvas de Bootstrap
     * @param {HTMLElement} element - Elemento del Offcanvas
     * @returns {bootstrap.Offcanvas|null} Instancia del Offcanvas o null
     */
    function initOffcanvas(element) {
        if (!element) {
            console.warn(`${MOD} Elemento Offcanvas no encontrado`);
            return null;
        }

        if (typeof bootstrap === 'undefined' || !bootstrap.Offcanvas) {
            console.error(`${MOD} Bootstrap Offcanvas no está disponible`);
            return null;
        }

        try {
            // Dispose instancia previa antes de crear (AGENTS.md §26 — evita backdrops acumulados)
            const prev = bootstrap.Offcanvas.getInstance(element);
            if (prev) prev.dispose();
            d.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
            d.body.style.overflow = '';
            offcanvasInstance = new bootstrap.Offcanvas(element);
            console.log(`${MOD} Offcanvas inicializado`);
            return offcanvasInstance;
        } catch (error) {
            console.error(`${MOD} Error al inicializar Offcanvas:`, error);
            return null;
        }
    }

    /**
     * Mostrar el Offcanvas
     * @param {HTMLElement} element - Elemento del Offcanvas
     */
    function showOffcanvas(element) {
        const instance = initOffcanvas(element);
        if (instance) {
            instance.show();
        }
    }

    /**
     * Ocultar el Offcanvas
     */
    function hideOffcanvas() {
        if (offcanvasInstance) {
            try {
                offcanvasInstance.hide();
            } catch (error) {
                console.warn(`${MOD} Error al ocultar Offcanvas:`, error);
            }
        }
    }

    /**
     * Cargar el Offcanvas desde el servidor vía HTMX
     * @param {number|null} facturaId - ID de la factura (null para nueva)
     * @param {boolean} simple - Si true, usa template simple (default: true)
     * @returns {Promise<void>}
     */
    async function cargarOffcanvas(facturaId = null, simple = true) {
        const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
        if (!container) {
            console.error(`${MOD} Contenedor #${OFFCANVAS_CONTAINER_ID} no encontrado`);
            if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                w.SintelFeedback.error('Error: Contenedor de Offcanvas no encontrado');
            }
            return;
        }

        // Construir URL con parámetros
        const url = facturaId 
            ? `${GESTOR_OFFCANVAS_URL}?id=${facturaId}&simple=${simple ? 'true' : 'false'}`
            : `${GESTOR_OFFCANVAS_URL}?simple=${simple ? 'true' : 'false'}`;

        try {
            // ⚠️ HTMX: Cargar HTML desde el servidor
            await htmx.ajax('GET', url, {
                target: `#${OFFCANVAS_CONTAINER_ID}`,
                swap: 'innerHTML'
            });

            // ⚠️ Safeguard: Esperar un momento para que el DOM se actualice
            await new Promise(resolve => setTimeout(resolve, 50));

            // Inicializar y mostrar el Offcanvas
            const offcanvasEl = d.getElementById(OFFCANVAS_ID);
            if (offcanvasEl) {
                showOffcanvas(offcanvasEl);
            } else {
                console.warn(`${MOD} Offcanvas cargado pero elemento #${OFFCANVAS_ID} no encontrado`);
            }
        } catch (error) {
            console.error(`${MOD} Error al cargar Offcanvas:`, error);
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario' } }, MOD);
            } else {
                alert('Error al cargar el formulario de factura');
            }
        }
    }

    /**
     * Ver detalle de una factura
     * @param {number} facturaId - ID de la factura
     * @param {boolean} simple - Si true, usa template simple (default: true)
     */
    async function ver(facturaId, simple = true) {
        if (!facturaId) {
            console.warn(`${MOD} ID de factura no proporcionado`);
            return;
        }

        await cargarOffcanvas(facturaId, simple);
    }

    /**
     * Abrir formulario para subir nueva factura
     * ⚠️ v2.61.2: Protección contra llamadas simultáneas
     */
    let _subirNuevaEnProceso = false;
    async function subirNueva() {
        // ⚠️ v2.61.2: Prevenir múltiples llamadas simultáneas
        if (_subirNuevaEnProceso) {
            console.warn(`${MOD} subirNueva() ya está en proceso, ignorando llamada duplicada`);
            return;
        }
        
        _subirNuevaEnProceso = true;
        try {
            await cargarOffcanvas(null, true);
        } finally {
            // ⚠️ Resetear flag después de un breve delay para permitir que el offcanvas se abra
            setTimeout(() => {
                _subirNuevaEnProceso = false;
            }, 1000);
        }
    }

    /**
     * Eliminar una factura
     * @param {number} facturaId - ID de la factura
     * @returns {Promise<boolean>} true si se eliminó correctamente
     */
    async function eliminar(facturaId) {
        if (!facturaId) {
            console.warn(`${MOD} ID de factura no proporcionado`);
            return false;
        }

        // Confirmación
        if (!confirm('¿Está seguro de eliminar esta factura? Esta acción no se puede deshacer.')) {
            return false;
        }

        // ⚠️ Aislamiento Gradual: Usar facturasAPI (Capa de Datos)
        let res;
        if (w.facturasAPI && typeof w.facturasAPI.deleteFactura === 'function') {
            res = await w.facturasAPI.deleteFactura(facturaId);
        } else if (w.http && typeof w.http === 'function') {
            res = await w.http('DELETE', `/api/v1/facturas/${facturaId}/`);
        } else {
            console.error(`${MOD} No hay API disponible para eliminar factura`);
            if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                w.SintelFeedback.error('Error: API no disponible');
            }
            return false;
        }

        // ⚠️ Error Boundary: Manejar errores
        if (!res.ok) {
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError(res, MOD);
            } else {
                alert(res.data?.detail || 'Error al eliminar la factura');
            }
            return false;
        }

        // ⚠️ Éxito: Cerrar Offcanvas si está abierto y recargar tabla
        hideOffcanvas();

        // Feedback visual
        if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
            w.SintelFeedback.success('Factura eliminada correctamente');
        }

        // Recargar tabla de facturas
        recargar();

        return true;
    }

    // ⚠️ CRÍTICO v2.60: Exponer función INMEDIATAMENTE después de definirla
    if (w.AppFacturas) {
        w.AppFacturas.eliminar = eliminar;
    }

    /**
     * Recargar la tabla de facturas
     * Integración con módulos list y editor
     */
    function recargar() {
        // Intentar recargar vía FacturasListModule
        if (w.FacturasListModule && typeof w.FacturasListModule.refresh === 'function') {
            w.FacturasListModule.refresh(); // ⚠️ Ya incluye loadSummary() internamente
            console.log(`${MOD} Tabla recargada vía FacturasListModule`);
            return;
        }

        // Fallback: Disparar evento personalizado
        d.dispatchEvent(new CustomEvent('facturaEliminada', { detail: { timestamp: Date.now() } }));
        console.log(`${MOD} Evento facturaEliminada disparado`);
        
        // ⚠️ Cargar summary manualmente si FacturasListModule no está disponible
        if (w.FacturasListModule && typeof w.FacturasListModule.loadSummary === 'function') {
            w.FacturasListModule.loadSummary();
        }
    }

    // ⚠️ CRÍTICO v2.60: Exponer función INMEDIATAMENTE después de definirla
    if (w.AppFacturas) {
        w.AppFacturas.recargar = recargar;
    }

    /**
     * Refrescar el grid de facturas (alias para recargar)
     * @alias recargar
     */
    function refreshGrid() {
        recargar();
    }

    // ⚠️ CRÍTICO v2.60: Exponer función INMEDIATAMENTE después de definirla
    if (w.AppFacturas) {
        w.AppFacturas.refreshGrid = refreshGrid;
    }

    /**
     * Sincronizar facturas desde el buzón de correo
     * ⚠️ v2.60: Flujo de dos etapas - Pre-visualización y Materialización
     * 
     * Flujo:
     * 1. Obtener configuraciones activas de buzones
     * 2. Llamar al endpoint de pre-visualización (solo metadatos, sin persistir)
     * 3. Mostrar lista de facturas pendientes en modal/offcanvas
     * 4. Usuario selecciona cuáles procesar
     * 5. Enviar facturas seleccionadas al endpoint create-from-dto/
     */
    async function sincronizarCorreo() {
        const btnSync = d.getElementById('btn-sync-mail');
        const spinner = d.getElementById('sync-spinner');
        
        if (!btnSync) {
            console.warn(`${MOD} Botón de sincronización no encontrado`);
            return;
        }

        // ⚠️ PREVENIR PETICIONES DUPLICADAS: Si ya está procesando, no hacer nada
        if (btnSync.disabled) {
            console.log(`${MOD} Sincronización ya en curso, ignorando petición duplicada`);
            return;
        }

        // ⚠️ Loading state
        const originalHTML = btnSync.innerHTML;
        btnSync.disabled = true;
        if (spinner) {
            spinner.classList.remove('d-none');
        }

        try {
            // 1. Obtener configuraciones activas de buzones desde el endpoint correcto
            // ⚠️ v2.60: Usar endpoint directo de MailInboxConfig (más confiable que depender de mailinboxAPI)
            let configsRes;
            if (w.http && typeof w.http === 'function') {
                // ⚠️ Endpoint correcto: /api/v1/empresas/mail-inbox-config/
                configsRes = await w.http('GET', '/api/v1/empresas/mail-inbox-config/?is_active=true&page_size=100');
            } else if (w.mailinboxAPI && typeof w.mailinboxAPI.list === 'function') {
                // ⚠️ Fallback: Usar mailinboxAPI si está disponible
                configsRes = await w.mailinboxAPI.list({ is_active: true, page_size: 100 });
            } else {
                console.error(`${MOD} No hay API disponible para listar configuraciones`);
                if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                    w.SintelFeedback.error('Error: API no disponible. Asegúrese de que http() esté cargado.');
                }
                return;
            }

            if (!configsRes.ok) {
                console.error(`${MOD} Error al obtener configuraciones:`, configsRes);
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(configsRes, MOD);
                } else {
                    alert('Error al obtener configuraciones de buzón. Verifique que haya configurado al menos un buzón en "Configuraciones de Correo".');
                }
                return;
            }

            // ⚠️ v2.60: Manejar respuesta paginada o directa
            const configs = configsRes.data?.results || configsRes.data || [];
            
            if (configs.length === 0) {
                if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
                    w.SintelFeedback.warning('No hay configuraciones de buzón activas. Configure un buzón primero en "Configuraciones de Correo".');
                } else {
                    alert('No hay configuraciones de buzón activas. Configure un buzón primero en "Configuraciones de Correo".');
                }
                return;
            }

            // 2. Si hay múltiples configuraciones, permitir selección (por ahora usa la primera activa)
            // ⚠️ TODO FUTURO: Mostrar selector si hay múltiples configuraciones
            const config = configs[0];
            const configId = config.id;
            const limitMessages = 50; // Default según auditoría

            console.log(`${MOD} Pre-visualizando buzón: config_id=${configId}, nombre=${config.nombre || 'N/A'}, email=${config.email_address || 'N/A'}`);
            
            // ⚠️ Si hay múltiples configuraciones, mostrar advertencia
            if (configs.length > 1) {
                console.log(`${MOD} Se encontraron ${configs.length} configuraciones activas. Usando la primera: ${config.nombre || configId}`);
                if (w.SintelFeedback && typeof w.SintelFeedback.info === 'function') {
                    w.SintelFeedback.info(`Usando configuración: ${config.nombre || 'Sin nombre'}. Hay ${configs.length} configuraciones activas disponibles.`);
                }
            }

            // 3. Llamar al endpoint de PRE-VISUALIZACIÓN (solo metadatos, sin persistir)
            let previewRes;
            if (w.facturasAPI && typeof w.facturasAPI.previewMailbox === 'function') {
                previewRes = await w.facturasAPI.previewMailbox(configId, limitMessages);
            } else if (w.http && typeof w.http === 'function') {
                previewRes = await w.http('POST', '/api/v1/facturas/ingesta-correo/preview/', {
                    config_id: configId,
                    limit_messages: limitMessages,
                });
            } else {
                console.error(`${MOD} No hay API disponible para pre-visualizar buzón`);
                if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                    w.SintelFeedback.error('Error: API no disponible');
                }
                return;
            }

            // 4. Manejar respuesta
            if (!previewRes.ok) {
                if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                    w.UIManager.handleError(previewRes, MOD);
                } else {
                    alert(previewRes.data?.message || previewRes.data?.error || 'Error al pre-visualizar buzón');
                }
                return;
            }

            // 5. Mostrar lista de facturas pendientes para que el usuario seleccione
            const pendingInvoices = previewRes.data?.pending_invoices || [];
            const xmlDetected = previewRes.data?.xml_detected || 0;
            const lastUidProcessed = previewRes.data?.last_uid_processed || null;  // ⚠️ Último UID procesado
            const mailboxConfigId = previewRes.data?.config_id || configId;  // ⚠️ ID de configuración (renombrado para evitar conflicto)

            if (pendingInvoices.length === 0) {
                if (w.SintelFeedback && typeof w.SintelFeedback.info === 'function') {
                    w.SintelFeedback.info('No se encontraron facturas nuevas en el buzón.');
                } else {
                    alert('No se encontraron facturas nuevas en el buzón.');
                }
                return;
            }

            // ⚠️ Mostrar modal/offcanvas con lista de pendientes
            // ⚠️ ZERO WASTE: Pasar last_uid_processed y config_id para actualizar estado después de procesar
            mostrarListaPendientes(pendingInvoices, xmlDetected, lastUidProcessed, mailboxConfigId);

            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                w.SintelFeedback.success(`Se encontraron ${xmlDetected} factura(s) pendiente(s). Seleccione cuáles procesar.`);
            }

        } catch (error) {
            console.error(`${MOD} Error al sincronizar correo:`, error);
            if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                w.UIManager.handleError({ ok: false, status: 500, data: { detail: String(error) } }, MOD);
            } else if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                w.SintelFeedback.error('Error al sincronizar correo');
            } else {
                alert('Error al sincronizar correo');
            }
        } finally {
            // Restaurar estado del botón
            btnSync.disabled = false;
            if (spinner) {
                spinner.classList.add('d-none');
            }
        }
    }

    /**
     * Mostrar lista de facturas pendientes en offcanvas para selección
     * ⚠️ v2.60: Migrado a Offcanvas con HTMX para mejor UX
     * ⚠️ ZERO WASTE: Actualiza last_seen_uid después de procesar para evitar reprocesar correos
     * 
     * @param {Array} pendingInvoices - Lista de facturas pendientes con metadatos y XML
     * @param {number} xmlDetected - Número total de XMLs detectados
     * @param {number|null} lastUidProcessed - Último UID procesado (para actualizar estado)
     * @param {number} configId - ID de configuración del buzón
     */
    function mostrarListaPendientes(pendingInvoices, xmlDetected, lastUidProcessed = null, configId = null) {
        // ⚠️ ZERO WASTE: Guardar lastUidProcessed y configId para actualizar estado después de procesar
        // Estos valores se usarán para actualizar MailInboxState.last_seen_uid
        const offcanvasData = {
            lastUidProcessed: lastUidProcessed,
            configId: configId,
            totalProcessed: 0,  // Contador de facturas procesadas exitosamente
            pendingInvoices: pendingInvoices,  // ⚠️ Guardar facturas para procesamiento posterior
        };
        
        // ⚠️ v2.60: Guardar datos en el objeto global para acceso desde event listeners
        if (!w.AppFacturas._pendingData) {
            w.AppFacturas._pendingData = {};
        }
        w.AppFacturas._pendingData = offcanvasData;
        
        // ⚠️ v2.60: Cargar offcanvas usando HTMX
        const containerId = 'offcanvas-container-facturas';
        const offcanvasId = 'offcanvas-facturas-pendientes';
        const url = `/api/v1/facturas/ingesta-correo/render-offcanvas-pendientes/${configId ? `?config_id=${configId}` : ''}`;
        
        if (w.htmx) {
            // Cargar offcanvas HTML
            w.htmx.ajax('GET', url, {
                target: `#${containerId}`,
                swap: 'innerHTML',
                onSuccess: () => {
                    // ⚠️ v2.60: Esperar a que HTMX termine de renderizar (afterSettle)
                    setTimeout(() => {
                        const containerEl = d.getElementById(containerId);
                        const offcanvasEl = containerEl ? containerEl.querySelector(`#${offcanvasId}`) : d.getElementById(offcanvasId);
                        
                        if (offcanvasEl) {
                            // Inyectar datos de facturas en el tbody
                            poblarTablaFacturasPendientes(offcanvasEl, pendingInvoices, xmlDetected);
                            
                            // Configurar event listeners
                            configurarEventosOffcanvasPendientes(offcanvasEl, offcanvasData);
                            
                            // Mostrar offcanvas
                            if (w.bootstrap && w.bootstrap.Offcanvas) {
                                const bsOffcanvas = new w.bootstrap.Offcanvas(offcanvasEl);
                                bsOffcanvas.show();
                                console.log(`${MOD} Offcanvas de facturas pendientes abierto`);
                            } else {
                                console.error(`${MOD} Bootstrap.Offcanvas no está disponible`);
                            }
                        } else {
                            console.error(`${MOD} Offcanvas no encontrado después de cargar HTML`);
                        }
                    }, 200);
                }
            });
        } else {
            console.error(`${MOD} HTMX no está disponible`);
        }

        // Formatear fecha
        function formatearFecha(fechaStr) {
            if (!fechaStr) return 'N/A';
            try {
                const fecha = new Date(fechaStr);
                return fecha.toLocaleDateString('es-CO', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit'
                });
            } catch (e) {
                return fechaStr;
            }
        }

        // Formatear moneda
        function formatearMoneda(valor, moneda = 'COP') {
            if (!valor || valor === '0.00') return '$ 0,00';
            const num = parseFloat(valor);
            if (isNaN(num)) return '$ 0,00';
            return new Intl.NumberFormat('es-CO', {
                style: 'currency',
                currency: moneda,
                minimumFractionDigits: 0,
                maximumFractionDigits: 2
            }).format(num);
        }

        // Construir HTML de la lista
        let tableRows = '';
        pendingInvoices.forEach((invoice, index) => {
            // ⚠️ FILTRO CONTABLE: No marcar por defecto documentos que no pertenecen a la empresa
            const belongsToTenant = invoice.belongs_to_tenant !== false; // true o null = válido, false = no válido
            const checked = (index === 0 && belongsToTenant) ? 'checked' : ''; // Solo marcar primera si pertenece
            const disabled = !belongsToTenant ? 'disabled' : ''; // Deshabilitar checkbox si no pertenece
            tableRows += `
                <tr data-invoice-index="${index}" ${!belongsToTenant ? 'class="table-warning"' : ''}>
                    <td>
                        <input type="checkbox" 
                               class="form-check-input invoice-checkbox" 
                               data-index="${index}"
                               ${checked}
                               ${disabled}
                               id="invoice-${index}">
                    </td>
                    <td>${invoice.numero || 'N/A'}</td>
                    <td>${formatearFecha(invoice.fecha_emision)}</td>
                    <td>${invoice.emisor_razon_social || 'N/A'}</td>
                    <td>${invoice.receptor_razon_social || 'N/A'}</td>
                    <td class="text-end">${formatearMoneda(invoice.total, invoice.moneda)}</td>
                    <td>
                        ${invoice.belongs_to_tenant === false 
                            ? `<span class="badge bg-warning text-dark" title="${invoice.validation_message || 'No pertenece a la empresa'}">
                                   <i class="bi bi-exclamation-triangle me-1"></i>No pertenece
                               </span>`
                            : invoice.belongs_to_tenant === true
                            ? `<span class="badge bg-success" title="${invoice.validation_message || 'Pertenece a la empresa'}">
                                   <i class="bi bi-check-circle me-1"></i>Válida
                               </span>`
                            : `<span class="badge bg-secondary" title="${invoice.validation_message || 'Validación pendiente'}">
                                   <i class="bi bi-question-circle me-1"></i>Sin validar
                               </span>`
                        }
                    </td>
                    <td class="text-center">
                        <button type="button" 
                                class="btn btn-sm btn-outline-primary btn-extraer-factura" 
                                data-index="${index}"
                                ${invoice.belongs_to_tenant === false ? 'disabled title="No se puede procesar: No pertenece a la empresa"' : 'title="Extraer esta factura individualmente"'}
                                >
                            <i class="bi bi-download me-1"></i>Extraer
                        </button>
                    </td>
                </tr>
            `;
        });

        modalEl.innerHTML = `
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}-label">
                            <i class="bi bi-envelope-arrow-down me-2"></i>
                            Facturas Pendientes (${xmlDetected})
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
                    </div>
                    <div class="modal-body">
                        <p class="text-muted mb-3">
                            Se encontraron <strong>${xmlDetected}</strong> factura(s) en el buzón. 
                            Seleccione las que desea procesar y haga clic en "Procesar Seleccionadas".
                        </p>
                        <div class="table-responsive" style="max-height: 400px;">
                            <table class="table table-hover table-sm">
                                <thead class="table-light sticky-top">
                                    <tr>
                                        <th width="50">
                                            <input type="checkbox" 
                                                   class="form-check-input" 
                                                   id="select-all-invoices"
                                                   title="Seleccionar todas">
                                        </th>
                                        <th>Número</th>
                                        <th>Fecha</th>
                                        <th>Emisor</th>
                                        <th>Receptor</th>
                                        <th class="text-end">Total</th>
                                        <th width="120">Validación</th>
                                        <th class="text-center">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${tableRows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" 
                                class="btn btn-primary" 
                                id="btn-procesar-seleccionadas">
                            <i class="bi bi-check-circle me-2"></i>Procesar Seleccionadas
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Configurar event listeners
        const selectAllCheckbox = modalEl.querySelector('#select-all-invoices');
        const checkboxes = modalEl.querySelectorAll('.invoice-checkbox');
        const btnProcesar = modalEl.querySelector('#btn-procesar-seleccionadas');
        const btnExtraerList = modalEl.querySelectorAll('.btn-extraer-factura');

        // Seleccionar/deseleccionar todas
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                });
            });
        }

        // ⚠️ Botones "Extraer" individuales: Enviar XML al pipeline universal
        btnExtraerList.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const index = parseInt(btn.getAttribute('data-index'));
                const invoice = pendingInvoices[index];
                
                if (!invoice) {
                    console.error(`${MOD} Factura no encontrada en índice ${index}`);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error: Factura no encontrada');
                    }
                    return;
                }

                // ⚠️ FILTRO CONTABLE: Validar que el documento pertenezca a la empresa antes de procesar
                if (invoice.belongs_to_tenant === false) {
                    const errorMsg = `No se puede procesar: ${invoice.validation_message || 'No pertenece a la empresa'}`;
                    if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
                        w.SintelFeedback.warning(errorMsg);
                    } else {
                        alert(errorMsg);
                    }
                    return; // No procesar documentos que no pertenecen
                }

                // Deshabilitar botón durante procesamiento
                const originalHTML = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

                try {
                    // ⚠️ Enviar XML al pipeline universal de documentos (create-from-dto/)
                    let persistRes;
                    if (w.facturasAPI && typeof w.facturasAPI.createFacturaFromDTO === 'function') {
                        persistRes = await w.facturasAPI.createFacturaFromDTO(
                            invoice.dto,
                            true,  // persist_anexos
                            invoice.file_bytes_b64,
                            'xml'
                        );
                    } else if (w.http && typeof w.http === 'function') {
                        persistRes = await w.http('POST', '/api/v1/facturas/create-from-dto/', {
                            dto: invoice.dto,
                            persist_anexos: true,
                            file_content_bytes: invoice.file_bytes_b64,
                            file_type: 'xml',
                        });
                    } else {
                        console.error(`${MOD} No hay API disponible para extraer factura`);
                        if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                            w.SintelFeedback.error('Error: API no disponible');
                        }
                        return;
                    }

                    // Manejar respuesta
                    if (persistRes.ok) {
                        if (persistRes.status === 201) {
                            // Factura creada exitosamente
                            if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                                w.SintelFeedback.success(`Factura ${invoice.numero || 'N/A'} extraída exitosamente`);
                            }
                            
                            // Marcar fila como procesada (opcional: cambiar estilo)
                            const row = btn.closest('tr');
                            if (row) {
                                row.classList.add('table-success');
                                row.style.opacity = '0.6';
                            }
                            
                            // Deshabilitar checkbox y botón
                            const checkbox = row.querySelector('.invoice-checkbox');
                            if (checkbox) {
                                checkbox.disabled = true;
                                checkbox.checked = false;
                            }
                            btn.disabled = true;
                            btn.innerHTML = '<i class="bi bi-check-circle text-success"></i> Extraída';
                            
                            // ⚠️ ZERO WASTE: Incrementar contador de procesadas para actualizar estado
                            modalData.totalProcessed++;
                            
                            // ⚠️ ZERO WASTE: Actualizar estado del buzón después de extraer individualmente
                            // Solo si hay lastUidProcessed y configId disponibles
                            if (modalData.lastUidProcessed !== null && modalData.configId !== null) {
                                try {
                                    if (w.http && typeof w.http === 'function') {
                                        await w.http('POST', '/api/v1/facturas/update-inbox-state/', {
                                            config_id: modalData.configId,
                                            last_uid: modalData.lastUidProcessed,
                                            messages_processed: modalData.totalProcessed,
                                        });
                                        console.log(`${MOD} Estado del buzón actualizado después de extraer: last_uid=${modalData.lastUidProcessed}`);
                                    }
                                } catch (updateError) {
                                    console.error(`${MOD} Error al actualizar estado del buzón:`, updateError);
                                    // No bloquear el flujo si falla la actualización del estado
                                }
                            }
                            
                            // Recargar tabla principal
                            recargar();
                        } else if (persistRes.status === 200) {
                            // Factura ya existía (duplicado)
                            if (w.SintelFeedback && typeof w.SintelFeedback.info === 'function') {
                                w.SintelFeedback.info(`Factura ${invoice.numero || 'N/A'} ya existía (duplicado)`);
                            }
                            
                            // Marcar fila como duplicada
                            const row = btn.closest('tr');
                            if (row) {
                                row.classList.add('table-info');
                                row.style.opacity = '0.6';
                            }
                            
                            btn.disabled = true;
                            btn.innerHTML = '<i class="bi bi-info-circle text-info"></i> Duplicada';
                        }
                    } else {
                        // Error al procesar
                        if (persistRes.data?.error === 'document_not_for_tenant') {
                            // ⚠️ CASCADING SECURITY: Factura de terceros rechazada
                            if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
                                w.SintelFeedback.warning(
                                    `Factura ${invoice.numero || 'N/A'} rechazada: ${persistRes.data.message || 'No pertenece a este tenant'}`
                                );
                            }
                            
                            // Marcar fila como rechazada
                            const row = btn.closest('tr');
                            if (row) {
                                row.classList.add('table-warning');
                            }
                            
                            btn.disabled = true;
                            btn.innerHTML = '<i class="bi bi-exclamation-triangle text-warning"></i> Rechazada';
                        } else {
                            // Otro error
                            if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                                w.SintelFeedback.error(
                                    `Error al extraer factura ${invoice.numero || 'N/A'}: ${persistRes.data?.message || 'Error desconocido'}`
                                );
                            }
                            
                            // Restaurar botón para reintentar
                            btn.disabled = false;
                            btn.innerHTML = originalHTML;
                        }
                    }
                } catch (error) {
                    console.error(`${MOD} Error al extraer factura ${invoice.numero || 'N/A'}:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error(`Error al extraer factura: ${String(error)}`);
                    }
                    
                    // Restaurar botón para reintentar
                    btn.disabled = false;
                    btn.innerHTML = originalHTML;
                }
            });
        });

        // Procesar facturas seleccionadas
        if (btnProcesar) {
            btnProcesar.addEventListener('click', async () => {
                const selectedIndices = Array.from(checkboxes)
                    .filter(cb => cb.checked)
                    .map(cb => parseInt(cb.getAttribute('data-index')));

                if (selectedIndices.length === 0) {
                    if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
                        w.SintelFeedback.warning('Por favor, seleccione al menos una factura para procesar.');
                    } else {
                        alert('Por favor, seleccione al menos una factura para procesar.');
                    }
                    return;
                }

                // Deshabilitar botón durante procesamiento
                btnProcesar.disabled = true;
                btnProcesar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';

                try {
                    // Procesar cada factura seleccionada
                    let processed = 0;
                    let errors = 0;
                    let rejected = 0;

                    for (const index of selectedIndices) {
                        const invoice = pendingInvoices[index];
                        
                        // ⚠️ FILTRO CONTABLE: Validar que el documento pertenezca a la empresa antes de procesar
                        if (invoice.belongs_to_tenant === false) {
                            rejected++;
                            logger.warn(`${MOD} Factura ${invoice.numero || 'N/A'} rechazada: No pertenece a la empresa (${invoice.validation_message || 'N/A'})`);
                            continue; // Saltar documentos que no pertenecen
                        }
                        
                        try {
                            // Enviar al endpoint create-from-dto/
                            let persistRes;
                            if (w.facturasAPI && typeof w.facturasAPI.createFacturaFromDTO === 'function') {
                                persistRes = await w.facturasAPI.createFacturaFromDTO(
                                    invoice.dto,
                                    true,  // persist_anexos
                                    invoice.file_bytes_b64,
                                    'xml'
                                );
                            } else if (w.http && typeof w.http === 'function') {
                                persistRes = await w.http('POST', '/api/v1/facturas/create-from-dto/', {
                                    dto: invoice.dto,
                                    persist_anexos: true,
                                    file_content_bytes: invoice.file_bytes_b64,
                                    file_type: 'xml',
                                });
                            } else {
                                console.error(`${MOD} No hay API disponible para persistir factura`);
                                errors++;
                                continue;
                            }

                            if (!persistRes.ok) {
                                if (persistRes.data?.error === 'document_not_for_tenant') {
                                    rejected++;
                                    // ⚠️ CASCADING SECURITY: Factura de terceros rechazada silenciosamente
                                    // El mensaje del servidor ya es claro: "Este correo contiene una factura dirigida a un tercero, no se incluirá en contabilidad"
                                    logger.warn(
                                        `${MOD} Factura ${invoice.numero} rechazada por validación de NIT (Cascading Security): ` +
                                        `Receptor NIT (${persistRes.data?.receptor_nit || 'N/A'}) != Tenant NIT (${persistRes.data?.tenant_nit || 'N/A'})`
                                    );
                                } else {
                                    errors++;
                                    logger.error(`${MOD} Error al procesar factura ${invoice.numero}:`, persistRes.data);
                                }
                            } else {
                                processed++;
                            }
                        } catch (error) {
                            errors++;
                            logger.error(`${MOD} Error al procesar factura ${invoice.numero}:`, error);
                        }
                    }

                    // Cerrar modal
                    const modalInstance = bootstrap.Modal.getInstance(modalEl);
                    if (modalInstance) {
                        modalInstance.hide();
                    }

                    // Feedback al usuario
                    // ⚠️ CASCADING SECURITY: Mostrar mensaje claro sobre facturas rechazadas
                    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                        let message = `Procesadas: ${processed}`;
                        if (rejected > 0) {
                            message += `, Rechazadas: ${rejected} (facturas de terceros no incluidas en contabilidad)`;
                            // Mostrar como warning si hay rechazos
                            w.SintelFeedback.warning(message);
                        } else if (errors > 0) {
                            message += `, Errores: ${errors}`;
                            w.SintelFeedback.warning(message);
                        } else {
                            w.SintelFeedback.success(message);
                        }
                    } else {
                        let message = `Procesadas: ${processed}`;
                        if (rejected > 0) message += `, Rechazadas: ${rejected} (facturas de terceros)`;
                        if (errors > 0) message += `, Errores: ${errors}`;
                        alert(message);
                    }

                    // ⚠️ ZERO WASTE: Actualizar estado del buzón después de procesar
                    // Solo si se procesaron facturas exitosamente (processed > 0)
                    if (processed > 0 && modalData.lastUidProcessed !== null && modalData.configId !== null) {
                        try {
                            // Llamar al endpoint para actualizar last_seen_uid
                            if (w.http && typeof w.http === 'function') {
                                await w.http('POST', '/api/v1/facturas/update-inbox-state/', {
                                    config_id: modalData.configId,
                                    last_uid: modalData.lastUidProcessed,
                                    messages_processed: processed,
                                });
                                console.log(`${MOD} Estado del buzón actualizado: last_uid=${modalData.lastUidProcessed}, processed=${processed}`);
                            } else {
                                console.warn(`${MOD} No hay API disponible para actualizar estado del buzón`);
                            }
                        } catch (updateError) {
                            console.error(`${MOD} Error al actualizar estado del buzón:`, updateError);
                            // No bloquear el flujo si falla la actualización del estado
                        }
                    }

                    // Recargar tabla
                    recargar();

                } catch (error) {
                    console.error(`${MOD} Error al procesar facturas seleccionadas:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error al procesar facturas seleccionadas');
                    } else {
                        alert('Error al procesar facturas seleccionadas');
                    }
                } finally {
                    btnProcesar.disabled = false;
                    btnProcesar.innerHTML = '<i class="bi bi-check-circle me-2"></i>Procesar Seleccionadas';
                }
            });
        }

        // Mostrar modal
        const modalInstance = new bootstrap.Modal(modalEl);
        modalInstance.show();
    }

    // ⚠️ CRÍTICO v2.60: Exponer función INMEDIATAMENTE después de definirla
    if (w.AppFacturas) {
        w.AppFacturas.sincronizarCorreo = sincronizarCorreo;
    }

    /**
     * Validar calidad de extracción de datos del DTO
     * ⚠️ Zero Waste: Detecta datos sospechosos que indican extracción incorrecta
     * 
     * @param {Object} dto - DTO extraído
     * @param {Object} metadata - Metadata del archivo
     * @returns {Object} {calidad: 'alta'|'media'|'baja', advertencias: Array, sugerirXML: boolean}
     */
    function validarCalidadExtraccion(dto, metadata) {
        const advertencias = [];
        let calidad = 'alta';
        let sugerirXML = false;

        // Detectar si es PDF
        const esPDF = metadata?.file_type === 'pdf' || metadata?.mime_type?.includes('pdf');

        // Validar número de factura
        const numero = dto.numero || dto.identificadores?.numero || '';
        if (numero) {
            // Detectar números sospechosos (muy cortos, fragmentos de texto)
            if (numero.length < 3) {
                advertencias.push('El número de factura parece incompleto o incorrecto');
                calidad = 'baja';
                sugerirXML = true;
            } else if (/^[a-z]{1,5}$/i.test(numero) && !/^[A-Z]{2,4}\d+/.test(numero)) {
                // Detectar fragmentos de texto (ej: "imiento" en lugar de "FST-000001")
                advertencias.push('El número de factura parece ser un fragmento de texto extraído incorrectamente');
                calidad = 'baja';
                sugerirXML = true;
            }
        }

        // Validar totales
        const totales = dto.totales || {};
        const total = parseFloat(totales.total || dto.total || 0);
        const subtotal = parseFloat(totales.subtotal || dto.subtotal || 0);
        const impuestos = parseFloat(totales.impuestos || dto.impuestos || 0);

        if (total === 0 && esPDF) {
            advertencias.push('El total de la factura es $0.00 - La extracción del PDF puede ser incorrecta');
            calidad = calidad === 'alta' ? 'media' : 'baja';
            sugerirXML = true;
        }

        if (subtotal === 0 && total > 0 && esPDF) {
            advertencias.push('El subtotal es $0.00 pero el total no - Posible error en la extracción');
            calidad = calidad === 'alta' ? 'media' : 'baja';
        }

        // Validar razón social del emisor (debe tener al menos 3 caracteres)
        const emisorRazonSocial = dto.emisor?.razon_social || '';
        if (emisorRazonSocial && emisorRazonSocial.length < 3) {
            advertencias.push('La razón social del emisor parece incompleta');
            calidad = calidad === 'alta' ? 'media' : 'baja';
        }

        // Validar confidence_score si está disponible
        const confidenceScore = dto.mapping_metadata?.average_confidence || metadata?.confidence_score;
        if (confidenceScore !== undefined && confidenceScore < 0.7) {
            advertencias.push(`La confianza de extracción es baja (${(confidenceScore * 100).toFixed(0)}%)`);
            calidad = calidad === 'alta' ? 'media' : 'baja';
            if (confidenceScore < 0.5) {
                sugerirXML = true;
            }
        }

        // Determinar calidad final
        if (advertencias.length >= 2 || sugerirXML) {
            calidad = 'baja';
        } else if (advertencias.length === 1) {
            calidad = 'media';
        }

        return {
            calidad,
            advertencias,
            sugerirXML,
            esPDF
        };
    }

    /**
     * Mapear campos faltantes a etiquetas legibles y rutas en el DTO
     * @param {string} field - Campo faltante (ej: "emisor.razon_social")
     * @returns {Object} {label: string, path: Array}
     */
    function mapearCampoFaltante(field) {
        const map = {
            'emisor.razon_social': { label: 'Razón Social del Emisor', path: ['emisor', 'razon_social'] },
            'emisor.nit': { label: 'NIT del Emisor', path: ['emisor', 'nit'] },
            'emisor.direccion': { label: 'Dirección del Emisor', path: ['emisor', 'direccion'] },
            'emisor.telefono': { label: 'Teléfono del Emisor', path: ['emisor', 'telefono'] },
            'emisor.email': { label: 'Email del Emisor', path: ['emisor', 'email'] },
            'receptor.razon_social': { label: 'Razón Social del Receptor', path: ['receptor', 'razon_social'] },
            'receptor.nit': { label: 'NIT del Receptor', path: ['receptor', 'nit'] },
            'receptor.direccion': { label: 'Dirección del Receptor', path: ['receptor', 'direccion'] },
            'numero': { label: 'Número de Factura', path: ['numero'] },
            'fecha_emision': { label: 'Fecha de Emisión', path: ['fecha_emision'] },
            'naturaleza': { label: 'Naturaleza (Venta/Compra)', path: ['naturaleza'], type: 'select' },
        };
        
        return map[field] || { label: field.replace(/\./g, ' ').replace(/_/g, ' '), path: field.split('.') };
    }

    /**
     * Obtener valor del DTO desde una ruta anidada
     * @param {Object} dto - DTO
     * @param {Array} path - Ruta al campo (ej: ['emisor', 'razon_social'])
     * @returns {any} Valor del campo o null
     */
    function obtenerValorDTO(dto, path) {
        let current = dto;
        for (const key of path) {
            if (current && typeof current === 'object' && key in current) {
                current = current[key];
            } else {
                return null;
            }
        }
        return current || null;
    }

    /**
     * Establecer valor en el DTO en una ruta anidada
     * @param {Object} dto - DTO
     * @param {Array} path - Ruta al campo (ej: ['emisor', 'razon_social'])
     * @param {any} value - Valor a establecer
     */
    function establecerValorDTO(dto, path, value) {
        let current = dto;
        for (let i = 0; i < path.length - 1; i++) {
            const key = path[i];
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        current[path[path.length - 1]] = value;
    }

    /**
     * Mostrar formulario dinámico para completar campos faltantes
     * ⚠️ v2.60: Extiende error_injector.js para casos específicos de facturas
     * Permite al usuario completar manualmente campos faltantes antes de persistir
     * 
     * @param {Object} dto - DTO original
     * @param {Array} missingFields - Array de campos faltantes (ej: ['emisor.razon_social'])
     * @param {Object} metadata - Metadata del archivo (para incluir file_content_bytes)
     * @param {Object} calidadExtraccion - Resultado de validarCalidadExtraccion (opcional)
     */
    function mostrarFormularioCamposFaltantes(dto, missingFields, metadata, calidadExtraccion = null) {
        const resultDiv = d.getElementById('upload-result');
        if (!resultDiv) {
            console.error(`${MOD} Contenedor #upload-result no encontrado`);
            return;
        }

        // Si no se proporciona calidadExtraccion, calcularla
        if (!calidadExtraccion) {
            calidadExtraccion = validarCalidadExtraccion(dto, metadata || {});
        }

        // Crear formulario dinámico con advertencias de calidad
        let formHTML = `
            <div class="alert alert-warning mb-3">
                <h6 class="alert-heading">
                    <i class="bi bi-exclamation-triangle me-2"></i>Campos Faltantes Detectados
                </h6>
                <p class="mb-0">El archivo PDF no contiene toda la información necesaria. Por favor, complete los siguientes campos:</p>
            </div>
        `;

        // ⚠️ Advertencia de calidad de extracción si es baja
        if (calidadExtraccion.calidad === 'baja' || calidadExtraccion.advertencias.length > 0) {
            formHTML += `
                <div class="alert alert-danger mb-3">
                    <h6 class="alert-heading">
                        <i class="bi bi-exclamation-circle me-2"></i>Advertencia: Calidad de Extracción Baja
                    </h6>
                    <ul class="mb-2">
                        ${calidadExtraccion.advertencias.map(adv => `<li>${adv}</li>`).join('')}
                    </ul>
                    ${calidadExtraccion.sugerirXML ? `
                        <p class="mb-0">
                            <strong>Recomendación:</strong> Para garantizar el 100% de precisión, 
                            use el botón <strong>"Importar XML"</strong> con el archivo XML UBL 2.1 de la DIAN. 
                            El XML contiene toda la información estructurada sin errores de lectura.
                        </p>
                    ` : ''}
                </div>
            `;
        } else if (calidadExtraccion.calidad === 'media') {
            formHTML += `
                <div class="alert alert-info mb-3">
                    <h6 class="alert-heading">
                        <i class="bi bi-info-circle me-2"></i>Calidad de Extracción Media
                    </h6>
                    <p class="mb-0">${calidadExtraccion.advertencias[0] || 'Algunos datos pueden requerir verificación manual.'}</p>
                </div>
            `;
        }

        formHTML += `<form id="form-campos-faltantes" class="needs-validation" novalidate>`;

        // Generar campos para cada campo faltante
        missingFields.forEach((field) => {
            const campoInfo = mapearCampoFaltante(field);
            const valorActual = obtenerValorDTO(dto, campoInfo.path) || '';
            const fieldId = `field-${field.replace(/\./g, '-')}`;
            
            // ⚠️ v2.61.2: Manejo especial para naturaleza (select) y campos normales (input)
            if (campoInfo.type === 'select' && field === 'naturaleza') {
                // Campo select para naturaleza
                formHTML += `
                    <div class="mb-3">
                        <label for="${fieldId}" class="form-label">
                            ${campoInfo.label} <span class="text-danger">*</span>
                        </label>
                        <select class="form-select" 
                                id="${fieldId}" 
                                name="${field}" 
                                data-path='${JSON.stringify(campoInfo.path)}'
                                required>
                            <option value="">Seleccione...</option>
                            <option value="VENTA" ${valorActual === 'VENTA' ? 'selected' : ''}>Venta (emitida por el tenant)</option>
                            <option value="COMPRA" ${valorActual === 'COMPRA' ? 'selected' : ''}>Compra (recibida por el tenant)</option>
                        </select>
                        <div class="invalid-feedback">
                            Por favor, seleccione la naturaleza de la factura.
                        </div>
                    </div>
                `;
            } else {
                // Campo input normal
                formHTML += `
                    <div class="mb-3">
                        <label for="${fieldId}" class="form-label">
                            ${campoInfo.label} <span class="text-danger">*</span>
                        </label>
                        <input type="text" 
                               class="form-control" 
                               id="${fieldId}" 
                               name="${field}" 
                               value="${valorActual}"
                               data-path='${JSON.stringify(campoInfo.path)}'
                               required>
                        <div class="invalid-feedback">
                            Por favor, complete el campo ${campoInfo.label}.
                        </div>
                    </div>
                `;
            }
        });

        formHTML += `
                <div class="d-flex gap-2">
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-save me-2"></i>Guardar Factura
                    </button>
                    <button type="button" class="btn btn-outline-secondary" id="btn-cancelar-campos-faltantes">
                        <i class="bi bi-x me-2"></i>Cancelar
                    </button>
                </div>
            </form>
        `;

        resultDiv.innerHTML = formHTML;

        // Configurar event listener para el botón cancelar
        const btnCancelar = d.getElementById('btn-cancelar-campos-faltantes');
        if (btnCancelar) {
            btnCancelar.addEventListener('click', () => {
                resultDiv.innerHTML = '';
            });
        }

        // Configurar event listener para el formulario
        const form = d.getElementById('form-campos-faltantes');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                e.stopPropagation();

                // Validar formulario
                if (!form.checkValidity()) {
                    form.classList.add('was-validated');
                    return;
                }

                // Crear copia del DTO para no modificar el original
                const dtoCompleto = JSON.parse(JSON.stringify(dto));

                /**
                 * ⚠️ v2.61.2: Limpiar NIT - Eliminar caracteres especiales y dígito de verificación si es necesario
                 * @param {string} nit - NIT con posibles caracteres especiales
                 * @returns {string} NIT limpio
                 */
                function limpiarNIT(nit) {
                    if (!nit) return '';
                    // Eliminar espacios, guiones, puntos y otros caracteres especiales
                    let nitLimpio = nit.replace(/[\s\-\.]/g, '');
                    // Si el backend solo espera el número base (sin dígito de verificación),
                    // eliminar el último dígito si es numérico y el NIT tiene más de 9 caracteres
                    // Nota: Esta lógica puede ajustarse según los requisitos del backend
                    if (nitLimpio.length > 9 && /^\d+$/.test(nitLimpio)) {
                        // Opcional: eliminar último dígito (dígito de verificación)
                        // nitLimpio = nitLimpio.slice(0, -1);
                    }
                    return nitLimpio;
                }

                // ⚠️ v2.61.2: Recopilar valores del formulario y actualizar DTO
                // Asegurar que los objetos anidados (como emisor) se reconstruyan correctamente
                missingFields.forEach((field) => {
                    const fieldId = `field-${field.replace(/\./g, '-')}`;
                    const input = d.getElementById(fieldId);
                    if (input && input.value.trim()) {
                        const campoInfo = mapearCampoFaltante(field);
                        let valor = input.value.trim();
                        
                        // ⚠️ v2.61.2: Limpiar NIT si es un campo de NIT
                        if (field.includes('nit') || field.includes('NIT')) {
                            valor = limpiarNIT(valor);
                        }
                        
                        // ⚠️ v2.61.2: Asegurar que los objetos anidados existan antes de establecer valores
                        // Por ejemplo, si el path es ['emisor', 'nit'], asegurar que dtoCompleto.emisor existe
                        if (campoInfo.path.length > 1) {
                            let current = dtoCompleto;
                            for (let i = 0; i < campoInfo.path.length - 1; i++) {
                                const key = campoInfo.path[i];
                                if (!current[key] || typeof current[key] !== 'object') {
                                    current[key] = {};
                                }
                                current = current[key];
                            }
                        }
                        
                        establecerValorDTO(dtoCompleto, campoInfo.path, valor);
                    }
                });
                
                // ⚠️ v2.61.2: VALIDACIÓN FINAL - Asegurar que emisor y naturaleza estén definidos
                // ⚠️ Sincronización de Naturaleza: Detectar si es AttachedDocument y asignar naturaleza automáticamente
                const esAttachedDocument = metadata?.file_type === 'xml' && (
                    metadata?.document_type === 'AttachedDocument' ||
                    dtoCompleto.metadata?.document_type === 'AttachedDocument' ||
                    dtoCompleto.tipo_documento === 'AttachedDocument'
                );
                
                if (!dtoCompleto.naturaleza || (dtoCompleto.naturaleza !== 'VENTA' && dtoCompleto.naturaleza !== 'COMPRA')) {
                    // ⚠️ v2.61.2: Si es AttachedDocument de la DIAN, generalmente es COMPRA (recibida)
                    if (esAttachedDocument) {
                        dtoCompleto.naturaleza = 'COMPRA';
                        console.log(`${MOD} AttachedDocument detectado, asignando naturaleza: COMPRA`);
                    } else {
                        // Intentar inferir desde el contexto o asignar por defecto
                        // Si el DTO tiene información del receptor y coincide con empresa del tenant, es COMPRA
                        // Por defecto, si no se puede inferir, usar VENTA (más común)
                        dtoCompleto.naturaleza = dtoCompleto.naturaleza || 'VENTA';
                        console.log(`${MOD} Naturaleza no definida, asignando por defecto: ${dtoCompleto.naturaleza}`);
                    }
                }
                
                // ⚠️ v2.61.2: ALINEACIÓN - Validar que emisor.nit y emisor.razon_social sean obligatorios
                if (!dtoCompleto.emisor) {
                    dtoCompleto.emisor = {};
                }
                
                // ⚠️ v2.61.2: Obtener referencia al botón antes de las validaciones
                const submitBtn = form.querySelector('button[type="submit"]');
                const originalBtnText = submitBtn ? submitBtn.innerHTML : '';
                
                // Validar que emisor tenga al menos nit o razon_social (ambos son recomendados)
                if (!dtoCompleto.emisor.nit && !dtoCompleto.emisor.razon_social) {
                    console.error(`${MOD} DTO incompleto: emisor no tiene nit ni razon_social`);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error: El emisor debe tener al menos NIT o Razón Social');
                    }
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                    }
                    return;
                }
                
                // ⚠️ v2.61.2: ALINEACIÓN - Asegurar que ambos campos estén presentes antes de persistir
                // Si falta alguno, mostrar formulario de campos faltantes
                if (!dtoCompleto.emisor.nit || !dtoCompleto.emisor.razon_social) {
                    console.warn(`${MOD} Emisor incompleto: nit=${!!dtoCompleto.emisor.nit}, razon_social=${!!dtoCompleto.emisor.razon_social}`);
                    const camposFaltantes = [];
                    if (!dtoCompleto.emisor.nit) camposFaltantes.push('emisor.nit');
                    if (!dtoCompleto.emisor.razon_social) camposFaltantes.push('emisor.razon_social');
                    
                    if (w.SintelFeedback && typeof w.SintelFeedback.warning === 'function') {
                        w.SintelFeedback.warning('El emisor debe tener tanto NIT como Razón Social');
                    }
                    
                    // Mostrar formulario con campos faltantes
                    // ⚠️ v2.61.2: Obtener calidadExtraccion si no está disponible
                    let calidadExtraccionLocal = calidadExtraccion;
                    if (!calidadExtraccionLocal) {
                        calidadExtraccionLocal = validarCalidadExtraccion(dtoCompleto, metadata || {});
                    }
                    mostrarFormularioCamposFaltantes(dtoCompleto, camposFaltantes, metadata || {}, calidadExtraccionLocal);
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                    }
                    return;
                }

                // Mostrar loading
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
                }

                try {
                    // Enviar DTO completo al endpoint create-from-dto/
                    let persistRes;
                    if (w.facturasAPI && typeof w.facturasAPI.createFacturaFromDTO === 'function') {
                        const fileContentBytesB64 = metadata?.file_content_bytes || null;
                        const fileType = metadata?.file_type || 'pdf';
                        persistRes = await w.facturasAPI.createFacturaFromDTO(dtoCompleto, true, fileContentBytesB64, fileType);
                    } else if (w.http && typeof w.http === 'function') {
                        persistRes = await w.http('POST', '/api/v1/facturas/create-from-dto/', {
                            dto: dtoCompleto,
                            persist_anexos: true,
                            file_content_bytes: metadata?.file_content_bytes || null,
                            file_type: metadata?.file_type || 'pdf',
                        });
                    } else {
                        console.error(`${MOD} No hay API disponible para persistir factura`);
                        if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                            w.SintelFeedback.error('Error: API no disponible para persistir');
                        }
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                        return;
                    }

                    if (!persistRes.ok) {
                        // Mostrar errores en el formulario
                        if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                            w.UIManager.handleError(persistRes, MOD, {
                                errorContainerSelector: '#upload-result'
                            });
                        } else {
                            alert(persistRes.data?.message || persistRes.data?.error || 'Error al guardar la factura');
                        }
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnText;
                        return;
                    }

                    // ⚠️ Éxito: Cerrar Offcanvas y recargar tabla
                    hideOffcanvas();

                    // Feedback visual
                    if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                        const facturaNum = persistRes.data?.numero || persistRes.data?.id || 'N/A';
                        w.SintelFeedback.success(`Factura ${facturaNum} guardada con éxito`);
                    }

                    // Recargar tabla
                    recargar();
                } catch (error) {
                    console.error(`${MOD} Error al guardar factura con campos completados:`, error);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error inesperado al guardar la factura');
                    }
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            });
        }
    }

    /**
     * Manejar respuesta de subida de archivo vía HTMX
     * ⚠️ v2.60: Flujo completo - Parsear y persistir automáticamente
     * 
     * Flujo:
     * 1. Endpoint universal parsea el archivo (solo DTO, no persiste)
     * 2. Si hay campos faltantes, mostrar formulario dinámico
     * 3. Si no es preview y no hay campos faltantes, persistir automáticamente vía create-from-dto
     * 4. Cerrar Offcanvas y recargar tabla
     * 
     * @param {Event} event - Evento HTMX
     */
    async function manejarSubidaArchivo(event) {
        const target = event.detail.target;
        if (!target || target.id !== 'upload-result') {
            return;
        }

        const response = event.detail.xhr;
        if (!response) {
            return;
        }

        try {
            const data = typeof response.response === 'string' 
                ? JSON.parse(response.response) 
                : response.response;

            // ⚠️ v2.60: Manejar errores 422 con missing_fields - Mostrar formulario dinámico
            if (data.error && data.missing_fields && Array.isArray(data.missing_fields) && data.missing_fields.length > 0) {
                // Es un error de validación con campos faltantes - Mostrar formulario dinámico
                const dto = data.dto || {};
                const missingFields = data.missing_fields;
                
                console.log(`${MOD} Campos faltantes detectados en respuesta 422: ${missingFields.join(', ')}`);
                
                // Validar calidad de extracción antes de mostrar formulario
                const calidadExtraccion = validarCalidadExtraccion(dto, data.metadata || {});
                
                // Mostrar formulario de campos faltantes con advertencias de calidad
                // ⚠️ Pasar calidadExtraccion para que el formulario muestre las advertencias correctamente
                mostrarFormularioCamposFaltantes(dto, missingFields, data.metadata || {}, calidadExtraccion);
                
                // Mostrar advertencia en feedback si la calidad es muy baja
                if (calidadExtraccion.calidad === 'baja' && calidadExtraccion.sugerirXML) {
                    const errorDiv = d.getElementById('factura-feedback');
                    if (errorDiv) {
                        errorDiv.innerHTML = `
                            <strong>Advertencia:</strong> La extracción del PDF tiene problemas de calidad. 
                            Se recomienda usar el archivo XML UBL 2.1 para garantizar precisión del 100%.
                        `;
                        errorDiv.classList.remove('d-none');
                        errorDiv.classList.add('alert-warning');
                    }
                }
                
                return; // No procesar más, el formulario ya se mostró
            }

            if (data.error) {
                // Mostrar error genérico
                const errorDiv = d.getElementById('factura-feedback');
                if (errorDiv) {
                    errorDiv.textContent = data.message || data.error || 'Error al procesar el archivo';
                    errorDiv.classList.remove('d-none');
                }

                if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                    w.SintelFeedback.error(data.message || data.error || 'Error al procesar el archivo');
                }
                return;
            }

            // ⚠️ v2.61.3: El endpoint upload-ubl puede retornar {id, persisted:true} (persistencia directa)
            // o {dto, missing_fields} (parseo sin persistir). Se usa data.id como indicador fiable.
            // Si el usuario no marcó "preview" y no hay id devuelto, persistir automáticamente vía create-from-dto
            const previewMode = d.getElementById('previewMode')?.checked || false;
            const dto = data.dto || data;
            const missingFields = data.missing_fields || [];

            // ⚠️ Zero Waste: Validar calidad de extracción antes de procesar
            const calidadExtraccion = validarCalidadExtraccion(dto, data.metadata || {});
            
            // ⚠️ PRIORIDAD: Si hay campos faltantes, mostrar formulario dinámico para completarlos
            // El formulario ya incluye las advertencias de calidad, así que se muestra todo junto
            // ⚠️ v2.61.2 FIX: Usar !data.id en vez de !data.persisted para detectar si ya fue persistido
            if (!previewMode && dto && !data.id && missingFields.length > 0) {
                console.log(`${MOD} Campos faltantes detectados: ${missingFields.join(', ')}`);
                // Pasar calidadExtraccion para que el formulario muestre las advertencias correctamente
                mostrarFormularioCamposFaltantes(dto, missingFields, data.metadata || {}, calidadExtraccion);
                return; // No persistir automáticamente, esperar que el usuario complete el formulario
            }
            
            // Si la calidad es muy baja y sugiere XML, mostrar advertencia (solo si NO hay campos faltantes)
            // ⚠️ NOTA: Si hay campos faltantes, ya se mostró el formulario arriba con las advertencias
            if (calidadExtraccion.calidad === 'baja' && calidadExtraccion.sugerirXML && !previewMode && missingFields.length === 0) {
                const resultDiv = d.getElementById('upload-result');
                if (resultDiv) {
                    let advertenciaHTML = `
                        <div class="alert alert-danger mb-3">
                            <h6 class="alert-heading">
                                <i class="bi bi-exclamation-circle me-2"></i>Advertencia: Calidad de Extracción Muy Baja
                            </h6>
                            <ul class="mb-2">
                                ${calidadExtraccion.advertencias.map(adv => `<li>${adv}</li>`).join('')}
                            </ul>
                            <p class="mb-2">
                                <strong>Recomendación:</strong> El parser de PDF no pudo extraer correctamente los datos. 
                                Para garantizar el 100% de precisión, use el botón <strong>"Importar XML"</strong> 
                                con el archivo XML UBL 2.1 de la DIAN.
                            </p>
                            <div class="d-flex gap-2">
                                <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('upload-result').innerHTML = ''; AppFacturas.subirNueva();">
                                    <i class="bi bi-file-code me-2"></i>Importar XML UBL 2.1
                                </button>
                                <button type="button" class="btn btn-outline-secondary" onclick="document.getElementById('upload-result').innerHTML = '';">
                                    <i class="bi bi-x me-2"></i>Cerrar
                                </button>
                            </div>
                        </div>
                    `;
                    resultDiv.innerHTML = advertenciaHTML;
                    return; // No persistir automáticamente si la calidad es muy baja
                }
            }

            if (!previewMode && dto && !data.id) {
                // ⚠️ v2.61.2 FIX: Usar !data.id (no !data.persisted) para detectar si aún no fue persistido
                // ⚠️ v2.61.2: VALIDACIÓN PREVENTIVA - Asegurar estructura mínima antes de persistir
                // La API requiere que emisor y naturaleza estén definidos para procesar la persistencia
                
                // ⚠️ v2.61.2: Validación de Etiquetas - Buscar NIT en rutas alternativas para AttachedDocument
                // Si es AttachedDocument y no se encuentra emisor.nit, intentar buscar en SenderParty
                const esAttachedDocument = data.metadata?.file_type === 'xml' && (
                    data.metadata?.document_type === 'AttachedDocument' ||
                    dto.metadata?.document_type === 'AttachedDocument' ||
                    dto.tipo_documento === 'AttachedDocument'
                );
                
                // Si es AttachedDocument y falta emisor.nit, intentar extraer desde metadata o rutas alternativas
                if (esAttachedDocument && (!dto.emisor || !dto.emisor.nit)) {
                    // Buscar NIT en metadata o rutas alternativas (SenderParty: cac:SenderParty//cbc:CompanyID)
                    const nitAlternativo = data.metadata?.sender_party_nit || 
                                         data.metadata?.emisor_nit ||
                                         data.metadata?.sender_company_id ||
                                         dto.metadata?.sender_party_nit ||
                                         dto.metadata?.emisor_nit ||
                                         dto.metadata?.sender_company_id;
                    
                    if (nitAlternativo) {
                        if (!dto.emisor) {
                            dto.emisor = {};
                        }
                        if (!dto.emisor.nit) {
                            dto.emisor.nit = nitAlternativo;
                            console.log(`${MOD} NIT encontrado en ruta alternativa (SenderParty/CompanyID): ${nitAlternativo}`);
                        }
                    }
                }
                
                const tieneEmisor = dto.emisor && (
                    dto.emisor.nit || 
                    dto.emisor.razon_social || 
                    (typeof dto.emisor === 'object' && Object.keys(dto.emisor).length > 0)
                );
                
                // ⚠️ v2.61.2: Sincronización de Naturaleza - Asignar automáticamente si es AttachedDocument
                let tieneNaturaleza = dto.naturaleza && (dto.naturaleza === 'VENTA' || dto.naturaleza === 'COMPRA');
                
                if (!tieneNaturaleza && esAttachedDocument) {
                    // AttachedDocument de la DIAN generalmente es COMPRA (recibida)
                    dto.naturaleza = 'COMPRA';
                    tieneNaturaleza = true;
                    console.log(`${MOD} AttachedDocument detectado, naturaleza asignada automáticamente: COMPRA`);
                }
                
                if (!tieneEmisor || !tieneNaturaleza) {
                    console.warn(`${MOD} DTO no tiene estructura mínima requerida. Emisor: ${tieneEmisor}, Naturaleza: ${tieneNaturaleza}`);
                    
                    // Si falta emisor o naturaleza, mostrar formulario de campos faltantes
                    const camposFaltantes = [];
                    if (!tieneEmisor) {
                        // ⚠️ v2.61.2: ALINEACIÓN - Ambos campos son obligatorios
                        camposFaltantes.push('emisor.nit', 'emisor.razon_social');
                    }
                    if (!tieneNaturaleza) {
                        camposFaltantes.push('naturaleza');
                    }
                    
                    // Agregar campos faltantes adicionales si existen
                    if (missingFields && Array.isArray(missingFields)) {
                        camposFaltantes.push(...missingFields.filter(f => !camposFaltantes.includes(f)));
                    }
                    
                    mostrarFormularioCamposFaltantes(dto, camposFaltantes, data.metadata || {}, calidadExtraccion);
                    return; // No persistir automáticamente, esperar que el usuario complete el formulario
                }
                
                // ⚠️ v2.61.2: ALINEACIÓN - Validación final antes de persistir
                // Asegurar que emisor.nit y emisor.razon_social estén presentes
                if (!dto.emisor.nit || !dto.emisor.razon_social) {
                    console.warn(`${MOD} Emisor incompleto antes de persistir: nit=${!!dto.emisor.nit}, razon_social=${!!dto.emisor.razon_social}`);
                    const camposFaltantes = [];
                    if (!dto.emisor.nit) camposFaltantes.push('emisor.nit');
                    if (!dto.emisor.razon_social) camposFaltantes.push('emisor.razon_social');
                    
                    mostrarFormularioCamposFaltantes(dto, camposFaltantes, data.metadata || {}, calidadExtraccion);
                    return;
                }
                
                // Persistir automáticamente vía create-from-dto (sin campos faltantes)
                console.log(`${MOD} Persistiendo factura desde DTO...`);
                
                let persistRes;
                if (w.facturasAPI && typeof w.facturasAPI.createFacturaFromDTO === 'function') {
                    const fileContentBytesB64 = data.metadata?.file_content_bytes || null;
                    const fileType = data.metadata?.file_type || 'xml';
                    persistRes = await w.facturasAPI.createFacturaFromDTO(dto, true, fileContentBytesB64, fileType);
                } else if (w.http && typeof w.http === 'function') {
                    persistRes = await w.http('POST', '/api/v1/facturas/create-from-dto/', {
                        dto: dto,
                        persist_anexos: true,
                        file_content_bytes: data.metadata?.file_content_bytes || null,
                        file_type: data.metadata?.file_type || 'xml',
                    });
                } else {
                    console.error(`${MOD} No hay API disponible para persistir factura`);
                    if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                        w.SintelFeedback.error('Error: API no disponible para persistir');
                    }
                    return;
                }

                if (!persistRes.ok) {
                    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                        w.UIManager.handleError(persistRes, MOD);
                    } else {
                        alert(persistRes.data?.message || persistRes.data?.error || 'Error al guardar la factura');
                    }
                    return;
                }

                // ⚠️ Éxito: Cerrar Offcanvas y recargar tabla
                hideOffcanvas();

                // Feedback visual
                if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                    const facturaNum = persistRes.data?.numero || persistRes.data?.id || 'N/A';
                    w.SintelFeedback.success(`Factura ${facturaNum} procesada y guardada con éxito`);
                }

                // Recargar tabla
                recargar();
            } else if (previewMode) {
                // Solo preview: mostrar DTO sin persistir con validación de calidad
                const resultDiv = d.getElementById('upload-result');
                if (resultDiv && dto) {
                    const numero = dto.numero || dto.identificadores?.numero || 'N/A';
                    const total = dto.total || dto.totales?.total || '0.00';
                    const calidadExtraccion = validarCalidadExtraccion(dto, data.metadata || {});
                    
                    let previewHTML = `
                        <div class="alert alert-info">
                            <h6>Vista Previa del Documento</h6>
                            <p><strong>Número:</strong> ${numero}</p>
                            <p><strong>Total:</strong> $${total}</p>
                    `;

                    // Mostrar advertencias de calidad si existen
                    if (calidadExtraccion.calidad === 'baja' || calidadExtraccion.advertencias.length > 0) {
                        previewHTML += `
                            <hr class="my-2">
                            <div class="alert alert-warning mb-0">
                                <h6 class="alert-heading small">
                                    <i class="bi bi-exclamation-triangle me-2"></i>Advertencias de Calidad
                                </h6>
                                <ul class="mb-0 small">
                                    ${calidadExtraccion.advertencias.map(adv => `<li>${adv}</li>`).join('')}
                                </ul>
                                ${calidadExtraccion.sugerirXML ? `
                                    <p class="mb-0 mt-2 small">
                                        <strong>Recomendación:</strong> Use el archivo XML UBL 2.1 para garantizar precisión del 100%.
                                    </p>
                                ` : ''}
                            </div>
                        `;
                    }

                    previewHTML += `
                            <hr class="my-2">
                            <p class="mb-0"><small>Este documento no ha sido guardado. Desmarca "Modo preview" para guardarlo.</small></p>
                        </div>
                    `;

                    resultDiv.innerHTML = previewHTML;
                }
                
                if (w.SintelFeedback && typeof w.SintelFeedback.info === 'function') {
                    w.SintelFeedback.info('Documento parseado correctamente (modo preview - no persistido)');
                }
            } else if (data.id || data.numero || data.persisted) {
                // Ya persistido (endpoint alternativo)
                hideOffcanvas();

                if (w.SintelFeedback && typeof w.SintelFeedback.success === 'function') {
                    w.SintelFeedback.success('Factura procesada con éxito');
                }

                recargar();
            }
        } catch (error) {
            console.error(`${MOD} Error procesando respuesta de subida:`, error);
            if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                w.SintelFeedback.error('Error al procesar la respuesta del servidor');
            }
        }
    }

    /**
     * Manejar errores de HTMX en subida de archivo
     * ⚠️ v2.60: Extiende error_injector.js para casos específicos de facturas
     * ⚠️ CASO ESPECIAL: Si hay missing_fields, mostrar formulario dinámico en lugar de solo error
     * @param {Event} event - Evento HTMX (htmx:responseError)
     */
    function manejarErrorSubida(event) {
        const target = event.detail.target;
        if (!target || target.id !== 'upload-result') {
            return; // Solo manejar errores en el contenedor de resultados de subida
        }

        const xhr = event.detail.xhr;
        if (!xhr) {
            return;
        }

        // Intentar extraer datos del error
        let errorData = null;
        try {
            const responseText = xhr?.responseText || '';
            if (responseText) {
                errorData = JSON.parse(responseText);
            }
        } catch (e) {
            // Si no es JSON, dejar que error_injector.js maneje el error genérico
            return;
        }

        // ⚠️ CASO ESPECIAL: Si hay missing_fields, mostrar formulario dinámico
        // Esto extiende la funcionalidad de error_injector.js para casos específicos de facturas
        if (errorData && errorData.missing_fields && Array.isArray(errorData.missing_fields) && errorData.missing_fields.length > 0) {
            const dto = errorData.dto || {};
            const missingFields = errorData.missing_fields;
            
            console.log(`${MOD} Error 422 con campos faltantes: ${missingFields.join(', ')}`);
            
            // Ocultar el error básico de error_injector.js (ya que mostraremos el formulario)
            if (w.ErrorHandler && typeof w.ErrorHandler.reset === 'function') {
                w.ErrorHandler.reset();
            }
            
            // Validar calidad de extracción
            const calidadExtraccion = validarCalidadExtraccion(dto, errorData.metadata || {});
            
            // Mostrar formulario de campos faltantes con advertencias de calidad
            mostrarFormularioCamposFaltantes(dto, missingFields, errorData.metadata || {}, calidadExtraccion);
            
            // No procesar más, el formulario ya se mostró
            return;
        }
        
        // Para otros errores, dejar que error_injector.js los maneje
        // (no hacer nada aquí, error_injector.js ya los procesó)
    }

    /**
     * Configurar event listeners para HTMX
     */
    function initHTMXListeners() {
        // afterSettle: DOM estable tras swap — no usar afterSwap (skill htmx.md §12, AGENTS.md §26)
        d.body.addEventListener('htmx:afterSettle', manejarSubidaArchivo);

        // Errores de subida
        d.body.addEventListener('htmx:responseError', manejarErrorSubida);

        // Reinicializar Offcanvas cuando se carga via HTMX — afterSettle garantiza DOM listo
        d.body.addEventListener('htmx:afterSettle', (event) => {
            const target = event.detail.target;
            if (target && target.id === OFFCANVAS_CONTAINER_ID) {
                const offcanvasEl = d.getElementById(OFFCANVAS_ID);
                if (offcanvasEl) {
                    initOffcanvas(offcanvasEl);
                }
            }
        });

        console.log(`${MOD} Event listeners de HTMX configurados`);
    }

    /**
     * Configurar event delegation para botones en el Offcanvas
     */
    function initOffcanvasEvents() {
        // ⚠️ Event Delegation: Escuchar clics en el contenedor del Offcanvas
        const container = d.getElementById(OFFCANVAS_CONTAINER_ID);
        if (!container) {
            return;
        }

        container.addEventListener('click', (e) => {
            // Botón eliminar factura
            const btnEliminar = e.target.closest('[data-action="eliminar-factura"]');
            if (btnEliminar) {
                e.preventDefault();
                e.stopPropagation();

                const facturaId = btnEliminar.getAttribute('data-factura-id');
                if (facturaId) {
                    eliminar(parseInt(facturaId));
                }
                return;
            }

            // Botón ver PDF
            const btnVerPDF = e.target.closest('[data-action="ver-pdf"]');
            if (btnVerPDF) {
                // El enlace ya tiene target="_blank", no necesitamos hacer nada
                // Solo loguear para debugging
                console.log(`${MOD} Abriendo PDF de factura`);
                return;
            }

            // Botón ver XML
            const btnVerXML = e.target.closest('[data-action="ver-xml"]');
            if (btnVerXML) {
                // El enlace ya tiene target="_blank", no necesitamos hacer nada
                console.log(`${MOD} Abriendo XML de factura`);
                return;
            }
        });

        console.log(`${MOD} Event delegation del Offcanvas configurado`);
    }

    /**
     * Configurar event delegation para botones en la toolbar de facturas
     * ⚠️ v2.60: Maneja botones de la lista (subir, actualizar, sincronizar)
     */
    function initToolbarEvents() {
        // ⚠️ Event Delegation: Escuchar clics en el contenedor de la toolbar
        // ⚠️ v2.60: Soporta tanto data-action como onclick (compatibilidad)
        const toolbar = d.getElementById('toolbar-facturas');
        if (!toolbar) {
            console.warn(`${MOD} Toolbar #toolbar-facturas no encontrada`);
            return;
        }

        // Remover listener anterior si existe (evitar duplicados)
        if (toolbar._toolbarClickHandler) {
            toolbar.removeEventListener('click', toolbar._toolbarClickHandler);
        }

        // Crear nuevo handler
        toolbar._toolbarClickHandler = async (e) => {
            // Botón subir factura (data-action o ID)
            const btnSubir = e.target.closest('[data-action="subir-factura"], #btn-subir-factura');
            if (btnSubir) {
                e.preventDefault();
                e.stopPropagation();
                
                // ⚠️ v2.61.2: Protección contra doble click - deshabilitar botón mientras se procesa
                if (btnSubir.disabled || btnSubir.classList.contains('processing')) {
                    console.log(`${MOD} Botón "Subir Factura" ya está procesando, ignorando click`);
                    return;
                }
                
                // Marcar como procesando
                btnSubir.disabled = true;
                btnSubir.classList.add('processing');
                const originalHTML = btnSubir.innerHTML;
                btnSubir.innerHTML = '<i class="bi bi-hourglass-split"></i> Cargando...';
                
                try {
                    console.log(`${MOD} Botón "Subir Factura" clickeado`);
                    await subirNueva();
                } catch (error) {
                    console.error(`${MOD} Error al subir factura:`, error);
                    if (w.UIManager && typeof w.UIManager.handleError === 'function') {
                        w.UIManager.handleError({ ok: false, status: 500, data: { detail: 'Error al cargar el formulario' } }, MOD);
                    }
                } finally {
                    // Restaurar estado del botón
                    btnSubir.disabled = false;
                    btnSubir.classList.remove('processing');
                    btnSubir.innerHTML = originalHTML;
                }
                return;
            }

            // Botón actualizar/refresh (data-action o ID)
            const btnRefresh = e.target.closest('[data-action="refresh-facturas"], #btn-refresh-facturas');
            if (btnRefresh) {
                e.preventDefault();
                e.stopPropagation();
                
                // ⚠️ v2.61.2: Protección contra doble click
                if (btnRefresh.disabled || btnRefresh.classList.contains('processing')) {
                    return;
                }
                
                btnRefresh.disabled = true;
                btnRefresh.classList.add('processing');
                const originalHTML = btnRefresh.innerHTML;
                btnRefresh.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                
                try {
                    console.log(`${MOD} Botón "Actualizar" clickeado`);
                    refreshGrid();
                } finally {
                    // Restaurar después de un breve delay
                    setTimeout(() => {
                        btnRefresh.disabled = false;
                        btnRefresh.classList.remove('processing');
                        btnRefresh.innerHTML = originalHTML;
                    }, 500);
                }
                return;
            }

            // Botón sincronizar correo (data-action o ID)
            const btnSync = e.target.closest('[data-action="sync-mail"], #btn-sync-mail');
            if (btnSync) {
                e.preventDefault();
                e.stopPropagation();
                
                // ⚠️ v2.61.2: Protección contra doble click
                if (btnSync.disabled || btnSync.classList.contains('processing')) {
                    return;
                }
                
                btnSync.disabled = true;
                btnSync.classList.add('processing');
                const spinner = d.getElementById('sync-spinner');
                if (spinner) {
                    spinner.classList.remove('d-none');
                }
                
                try {
                    console.log(`${MOD} Botón "Sincronizar Buzón" clickeado`);
                    await sincronizarCorreo();
                } finally {
                    // Restaurar estado
                    btnSync.disabled = false;
                    btnSync.classList.remove('processing');
                    if (spinner) {
                        spinner.classList.add('d-none');
                    }
                }
                return;
            }
        };

        toolbar.addEventListener('click', toolbar._toolbarClickHandler);
        console.log(`${MOD} Event listeners de toolbar configurados`);
    }

    /**
     * Inicialización principal
     */
    function init() {
        console.log(`${MOD} Inicializando módulo de UI...`);

        // Configurar event listeners
        initHTMXListeners();
        initOffcanvasEvents();
        initToolbarEvents(); // ⚠️ v2.60: Inicializar eventos de toolbar

        // Si el Offcanvas ya existe en el DOM, inicializarlo
        const offcanvasEl = d.getElementById(OFFCANVAS_ID);
        if (offcanvasEl) {
            initOffcanvas(offcanvasEl);
        }

        console.log(`${MOD} Módulo de UI inicializado`);
    }

    // ⚠️ API Pública: Construir objeto con todas las funciones
    // ⚠️ CRÍTICO v2.60: Este objeto se asigna a window.AppFacturas al final del módulo
    // para que los eventos onclick en el HTML puedan acceder a las funciones
    const AppFacturasPublic = {
        // Inicialización
        init,
        
        // Gestión de Offcanvas
        ver,
        subirNueva,
        cargarOffcanvas,
        showOffcanvas,
        hideOffcanvas,
        
        // Acciones
        eliminar,
        recargar,
        refreshGrid,  // Alias para recargar
        sincronizarCorreo,  // Sincronización desde buzón (POST /api/v1/core/maildigester/run/)
        
        // Utilidades
        getOffcanvasInstance: () => offcanvasInstance
    };

    // ⚠️ CRÍTICO v2.60: Exposición Global Final
    // Actualizar el objeto global (ya existe desde el inicio del módulo)
    // Reemplazar las funciones placeholder con las funciones reales
    Object.assign(w.AppFacturas, AppFacturasPublic);
    
    // ⚠️ EXPOSICIÓN EXPLÍCITA: Asegurar que window.AppFacturas esté completamente disponible
    // Esto es crítico para que los eventos onclick en workspace.html funcionen correctamente
    w.AppFacturas = w.AppFacturas || AppFacturasPublic;

    // ⚠️ Compatibilidad: Alias para uso legacy
    if (!w.FacturasModule) {
        w.FacturasModule = {};
    }
    w.FacturasModule.ver = ver;
    w.FacturasModule.subirNueva = subirNueva;
    w.FacturasModule.eliminar = eliminar;
    w.FacturasModule.recargar = recargar;

    console.log(`${MOD} ✅ API pública expuesta en window.AppFacturas (disponible para eventos inline)`);
    console.log(`${MOD} Funciones disponibles:`, Object.keys(AppFacturasPublic));
    
    // ⚠️ DOCUMENTACIÓN: Flujo de Datos para los Botones en workspace/#facturas
    // ============================================================================
    // Botón "Importar XML/PDF" → subirNueva() → POST /api/v1/core/documentos/upload/
    //   - Acepta archivos XML UBL 2.1 o PDF
    //   - Retorna DTO parseado (persisted: false)
    //   - Si hay missing_fields (422), error_injector.js muestra formulario dinámico
    //   - Si no hay errores, se persiste automáticamente vía create-from-dto/
    //
    // Botón "Actualizar" → refreshGrid() → GET /api/v1/facturas/ (con qs_list y only())
    //   - Usa FacturasListModule.refresh() que llama a tabulator.replaceData()
    //   - Zero Waste: Solo carga campos necesarios para la tabla
    //
    // Botón "Sincronizar Correo" → sincronizarCorreo() → POST /api/v1/core/maildigester/run/
    //   - Primero obtiene configuraciones: GET /api/v1/core/maildigester/configs/
    //   - Luego ejecuta sincronización: POST /api/v1/core/maildigester/run/
    //   - La sincronización es asíncrona (202 Accepted)
    //   - Recarga tabla después de 2 segundos
    // ============================================================================

    // ⚠️ Inicialización estándar: Cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM ya está listo, inicializar inmediatamente
        init();
    }

    // ⚠️ FIX PARA HTMX: Si cambias de vistas/tabs dinámicamente, DOMContentLoaded 
    // ya pasó. Necesitas inicializar cuando HTMX inyecte la tabla de facturas
    // Este listener detecta cuando HTMX inyecta contenido y reinicializa los event listeners
    if (typeof htmx !== 'undefined') {
        d.body.addEventListener('htmx:afterSettle', function(evt) {
            // Verificar si la sección de facturas acaba de ser inyectada en el DOM
            // Buscamos múltiples elementos para detectar la inyección de contenido
            const tabFacturas = d.getElementById('tab-facturas');
            const gridFacturas = d.getElementById('grid-facturas');
            const toolbarFacturas = d.getElementById('toolbar-facturas');
            const tabFacturasContent = d.getElementById('tab-facturas-content');
            
            // Si alguno de estos elementos existe y está visible, reinicializar
            const facturasInjected = (
                (tabFacturas && tabFacturas.offsetParent !== null) || 
                (gridFacturas && gridFacturas.offsetParent !== null) || 
                (toolbarFacturas && toolbarFacturas.offsetParent !== null) ||
                (tabFacturasContent && tabFacturasContent.offsetParent !== null)
            );
            
            if (facturasInjected) {
                console.log(`${MOD} HTMX inyectó contenido de facturas, reinicializando event listeners...`);
                
                // Reinicializar solo los event listeners (no destruir instancias existentes)
                // Los listeners de HTMX se configuran una vez, pero verificamos que estén activos
                initHTMXListeners();
                initOffcanvasEvents();
                initToolbarEvents(); // ⚠️ v2.60: Reinicializar eventos de toolbar cuando se carga dinámicamente
                
                // Si el offcanvas existe, inicializarlo
                const offcanvasEl = d.getElementById(OFFCANVAS_ID);
                if (offcanvasEl) {
                    initOffcanvas(offcanvasEl);
                }
                
                // Si el contenedor del offcanvas existe, asegurar que esté listo
                const offcanvasContainer = d.getElementById(OFFCANVAS_CONTAINER_ID);
                if (offcanvasContainer) {
                    console.log(`${MOD} Contenedor de offcanvas verificado`);
                }
            }
        });
        
        console.log(`${MOD} Listener de HTMX configurado para inicialización dinámica`);
    }

})(window, document);
