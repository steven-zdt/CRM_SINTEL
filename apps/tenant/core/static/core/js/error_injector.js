/**
 * error_injector.js - Módulo Inyectable de Manejo de Errores HTMX v2.60
 * ⚠️ Zero Waste: Procesa respuestas de error del servidor sin consultas adicionales
 * ⚠️ Modular: Se puede inyectar en cualquier template que use HTMX
 * ⚠️ Desacoplado: No depende de la lógica de negocio del backend
 * 
 * Responsabilidades:
 * - Interceptar errores de HTMX (htmx:responseError)
 * - Mostrar mensajes de error del servidor
 * - Mostrar lista de campos faltantes (missing_fields) en caso de 422
 * - Resetear el contenedor de errores antes de nuevas peticiones
 * 
 * ⚠️ CAPA DE UI: Módulo Inyectable y Workspace
 * Este módulo se encarga de que, si falla la detección automática del NIT o falta un dato en el PDF,
 * el usuario lo vea sin recargar la página.
 * 
 * Flujo de Inyección:
 * 1. HTMX realiza petición (ej: POST /api/v1/facturas/create-from-dto/)
 * 2. Servidor retorna error 422 con missing_fields
 * 3. HTMX dispara evento htmx:responseError
 * 4. Este módulo intercepta el evento y parsea la respuesta
 * 5. Muestra mensaje y lista de campos faltantes en #error-container
 * 6. El usuario ve el error sin recargar la página
 * 
 * Uso:
 * 1. Incluir error_handler.html en el template (ej: offcanvas_factura.html)
 * 2. Cargar este script en assets_core.html (ya incluido globalmente)
 * 3. El módulo se auto-inicializa y maneja errores automáticamente
 * 
 * Integración en Workspace:
 * - Cargado globalmente en workspace.html → assets_core.html → error_injector.js
 * - Disponible en todos los Offcanvas que incluyan error_handler.html
 */
(function(w, d) {
    'use strict';

    const MOD = '[error.injector]';
    const ERROR_CONTAINER_ID = 'error-container';
    const ERROR_MESSAGE_ID = 'error-message';
    const MISSING_FIELDS_LIST_ID = 'missing-fields-list';
    const FIELDS_UL_ID = 'fields-ul';

    /**
     * Mapear nombres de campos técnicos a etiquetas legibles
     * @param {string} field - Campo técnico (ej: "emisor.razon_social")
     * @returns {string} Etiqueta legible
     */
    function mapearCampoALegible(field) {
        const map = {
            // Campos de Facturas
            'emisor.razon_social': 'Razón Social del Emisor',
            'emisor.nit': 'NIT del Emisor (⚠️ CRÍTICO: Sin este campo no se puede determinar la naturaleza de la factura)',
            'emisor.direccion': 'Dirección del Emisor',
            'emisor.telefono': 'Teléfono del Emisor',
            'emisor.email': 'Email del Emisor',
            'receptor.razon_social': 'Razón Social del Receptor',
            'receptor.nit': 'NIT del Receptor (⚠️ CRÍTICO: Debe coincidir con el NIT de la empresa del tenant para facturas de COMPRA)',
            'receptor.direccion': 'Dirección del Receptor',
            'numero': 'Número de Factura',
            'fecha_emision': 'Fecha de Emisión',
            'total': 'Total de la Factura',
            // Campos de Gastos
            'subtotal': 'Subtotal (Base gravable para el cálculo de retenciones)',
            'retefuente_porcentaje': 'Porcentaje de Retefuente',
            'reteica_porcentaje': 'Porcentaje de ReteICA',
            'fecha': 'Fecha de la Operación',
            'vendedor_nit': 'NIT del Vendedor',
            'vendedor_nombre': 'Nombre o Razón Social del Vendedor',
            'categoria_contable': 'Categoría Contable',
            'periodo': 'Periodo Fiscal (YYYY-MM)',
            'resolucion_dian': 'Resolución DIAN (⚠️ CRÍTICO: Debe haber una resolución activa configurada)',
            'empresa': 'Empresa del Tenant',
            // Campos de configuración de correo
            'config_id': 'ID de Configuración de Buzón',
            'password': 'Contraseña de Aplicación (⚠️ GMAIL: Debe ser App Password de 16 dígitos)',
            'imap_port': 'Puerto IMAP (⚠️ Debe ser 993 para SSL)',
            'imap_host': 'Servidor IMAP (Gmail: imap.gmail.com, Outlook: outlook.office365.com)',
            // Campos de Asientos Contables
            'movimientos': 'Movimientos Contables (⚠️ CRÍTICO: El asiento debe tener movimientos y estar cuadrado: Débito = Crédito)',
            'numero': 'Número de Asiento',
            'fecha': 'Fecha del Asiento',
            'descripcion': 'Descripción del Asiento',
            'estado': 'Estado del Asiento (BORRADOR, APROBADO, CERRADO)',
            'total_debe': 'Total Débito',
            'total_haber': 'Total Crédito',
            'cuenta': 'Cuenta Contable',
            'debe': 'Valor Débito',
            'haber': 'Valor Crédito',
            // Campos de Inventario - Productos
            'codigo': 'Código del Producto (SKU)',
            'nombre': 'Nombre del Producto',
            'categoria': 'Categoría del Producto',
            'precio_venta': 'Precio de Venta',
            'stock_actual': 'Stock Actual',
            'stock_minimo': 'Stock Mínimo',
            'unidad': 'Unidad de Medida',
            'descripcion': 'Descripción del Producto',
            'activo': 'Estado del Producto (Activo/Inactivo)',
            'producto': 'Producto',
            'producto_id': 'ID del Producto',
            'tipo_movimiento': 'Tipo de Movimiento',
            'cantidad': 'Cantidad',
            'costo_unitario': 'Costo Unitario',
            'origen_referencia': 'Referencia Externa',
            'observaciones': 'Observaciones',
            // Campos de Inventario - Categorías
            'aplicacion': 'Aplicación de la Categoría (PRODUCTO, SERVICIO, ACTIVO, TODO)',
            // Campos de Inventario - Servicios
            'precio': 'Precio del Servicio',
            // Campos de Inventario - Activos Fijos
            'estado': 'Estado del Activo (ACTIVO, MANTENIMIENTO, BAJA)',
            'costo_adquisicion': 'Costo de Adquisición',
            'fecha_adquisicion': 'Fecha de Adquisición',
            'ubicacion': 'Ubicación del Activo',
            'responsable': 'Responsable del Activo',
        };
        
        return map[field] || field.replace(/\./g, ' ').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    /**
     * Mostrar error en el contenedor
     * @param {XMLHttpRequest} xhr - Objeto XHR de la respuesta
     */
    function showError(xhr) {
        // ⚠️ v2.60: Buscar contenedor de errores en múltiples ubicaciones
        // 1. Buscar en el DOM principal
        let container = d.getElementById(ERROR_CONTAINER_ID);
        let msgDiv = d.getElementById(ERROR_MESSAGE_ID);
        let fieldsUl = d.getElementById(FIELDS_UL_ID);
        let fieldsContainer = d.getElementById(MISSING_FIELDS_LIST_ID);
        
        // 2. Si no se encuentra, buscar en contenedores HTMX comunes
        if (!container || !msgDiv) {
            // Buscar en contenedor de mailinbox
            const mailinboxContainer = d.getElementById('offcanvas-container-mailinbox');
            if (mailinboxContainer) {
                container = mailinboxContainer.querySelector(`#${ERROR_CONTAINER_ID}`);
                if (container) {
                    msgDiv = container.querySelector(`#${ERROR_MESSAGE_ID}`);
                    fieldsUl = container.querySelector(`#${FIELDS_UL_ID}`);
                    fieldsContainer = container.querySelector(`#${MISSING_FIELDS_LIST_ID}`);
                }
            }
        }
        
        // 2b. Buscar en contenedor de asientos contables
        if (!container || !msgDiv) {
            const asientosContainer = d.getElementById('offcanvas-container-asientos');
            if (asientosContainer) {
                container = asientosContainer.querySelector(`#${ERROR_CONTAINER_ID}`);
                if (container) {
                    msgDiv = container.querySelector(`#${ERROR_MESSAGE_ID}`);
                    fieldsUl = container.querySelector(`#${FIELDS_UL_ID}`);
                    fieldsContainer = container.querySelector(`#${MISSING_FIELDS_LIST_ID}`);
                }
            }
        }
        
        // 3. Si aún no se encuentra, buscar en el offcanvas de mailinbox si está cargado
        if (!container || !msgDiv) {
            const offcanvasEl = d.getElementById('offcanvas-mailinbox');
            if (offcanvasEl) {
                container = offcanvasEl.querySelector(`#${ERROR_CONTAINER_ID}`);
                if (container) {
                    msgDiv = container.querySelector(`#${ERROR_MESSAGE_ID}`);
                    fieldsUl = container.querySelector(`#${FIELDS_UL_ID}`);
                    fieldsContainer = container.querySelector(`#${MISSING_FIELDS_LIST_ID}`);
                }
            }
        }
        
        // 3b. Buscar en el offcanvas de asientos si está cargado
        if (!container || !msgDiv) {
            const offcanvasAsiento = d.getElementById('offcanvas-asiento-crear') || d.getElementById('offcanvas-asiento-editar');
            if (offcanvasAsiento) {
                container = offcanvasAsiento.querySelector(`#${ERROR_CONTAINER_ID}`) || offcanvasAsiento.querySelector(`#error-container-asiento`);
                if (container) {
                    msgDiv = container.querySelector(`#${ERROR_MESSAGE_ID}`) || container.querySelector(`#error-message-asiento`);
                    fieldsUl = container.querySelector(`#${FIELDS_UL_ID}`);
                    fieldsContainer = container.querySelector(`#${MISSING_FIELDS_LIST_ID}`) || container.querySelector(`#missing-fields-list-asiento`);
                }
            }
        }
        
        // 3c. Buscar en el offcanvas de cuentas si está cargado
        if (!container || !msgDiv) {
            const offcanvasCuenta = d.getElementById('offcanvas-cuenta-crear') || d.getElementById('offcanvas-cuenta-editar');
            if (offcanvasCuenta) {
                container = offcanvasCuenta.querySelector(`#${ERROR_CONTAINER_ID}`) || offcanvasCuenta.querySelector(`#error-container-cuenta`);
                if (container) {
                    msgDiv = container.querySelector(`#${ERROR_MESSAGE_ID}`) || container.querySelector(`#error-message-cuenta`);
                    fieldsUl = container.querySelector(`#${FIELDS_UL_ID}`);
                    fieldsContainer = container.querySelector(`#${MISSING_FIELDS_LIST_ID}`) || container.querySelector(`#missing-fields-list-cuenta`);
                }
            }
        }

        // 3d. Buscar en el offcanvas de inventario/productos si está cargado
        if (!container || !msgDiv) {
            const offcanvasInventario = d.getElementById('offcanvas-inventario');
            if (offcanvasInventario) {
                container = offcanvasInventario.querySelector(`#${ERROR_CONTAINER_ID}`);
                if (container) {
                    msgDiv = container.querySelector(`#${ERROR_MESSAGE_ID}`);
                    fieldsUl = container.querySelector(`#${FIELDS_UL_ID}`);
                    fieldsContainer = container.querySelector(`#${MISSING_FIELDS_LIST_ID}`);
                } else {
                    // Buscar en contenedor HTMX de productos
                    const inventarioContainer = d.getElementById('offcanvas-container-inventario');
                    if (inventarioContainer) {
                        container = inventarioContainer.querySelector(`#${ERROR_CONTAINER_ID}`);
                        if (container) {
                            msgDiv = container.querySelector(`#${ERROR_MESSAGE_ID}`);
                            fieldsUl = container.querySelector(`#${FIELDS_UL_ID}`);
                            fieldsContainer = container.querySelector(`#${MISSING_FIELDS_LIST_ID}`);
                        }
                    }
                }
            }
        }
        
        // 4. Si aún no se encuentra, buscar en contenedores HTMX comunes
        if (!container || !msgDiv) {
            // 4a. Buscar en contenedor de inventario/productos
            const inventarioContainer = d.getElementById('offcanvas-container-inventario');
            if (inventarioContainer) {
                // Buscar dentro del offcanvas cargado
                const offcanvasInventario = inventarioContainer.querySelector('#offcanvas-inventario');
                if (offcanvasInventario) {
                    container = offcanvasInventario.querySelector(`#${ERROR_CONTAINER_ID}`);
                    if (container) {
                        msgDiv = container.querySelector(`#${ERROR_MESSAGE_ID}`);
                        fieldsUl = container.querySelector(`#${FIELDS_UL_ID}`);
                        fieldsContainer = container.querySelector(`#${MISSING_FIELDS_LIST_ID}`);
                    }
                }
            }
        }

        // 5. Si aún no se encuentra, crear un contenedor temporal en el contenedor HTMX
        if (!container || !msgDiv) {
            // Intentar en contenedor de inventario primero
            const inventarioContainer = d.getElementById('offcanvas-container-inventario');
            if (inventarioContainer && xhr.status >= 400) {
                // Crear contenedor temporal de error
                const tempErrorHtml = `
                    <div id="${ERROR_CONTAINER_ID}" class="mt-3">
                        <div class="alert alert-danger d-flex align-items-start" role="alert">
                            <i class="bi bi-exclamation-triangle-fill me-2 mt-1"></i>
                            <div class="flex-grow-1">
                                <div id="${ERROR_MESSAGE_ID}" class="mb-0"></div>
                                <div id="${MISSING_FIELDS_LIST_ID}" class="mt-2 d-none">
                                    <small class="text-muted text-uppercase fw-bold d-block mb-1">Campos Requeridos Faltantes:</small>
                                    <ul class="list-group list-group-flush small mb-0" id="${FIELDS_UL_ID}"></ul>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                inventarioContainer.insertAdjacentHTML('afterbegin', tempErrorHtml);
                container = d.getElementById(ERROR_CONTAINER_ID);
                msgDiv = d.getElementById(ERROR_MESSAGE_ID);
                fieldsUl = d.getElementById(FIELDS_UL_ID);
                fieldsContainer = d.getElementById(MISSING_FIELDS_LIST_ID);
            } else {
                // Intentar en contenedor de asientos
                const asientosContainer = d.getElementById('offcanvas-container-asiento') || d.getElementById('offcanvas-container-asientos');
                if (asientosContainer && xhr.status >= 400) {
                    // Crear contenedor temporal de error
                    const tempErrorHtml = `
                        <div id="${ERROR_CONTAINER_ID}" class="mt-3">
                            <div class="alert alert-danger d-flex align-items-start" role="alert">
                                <i class="bi bi-exclamation-triangle-fill me-2 mt-1"></i>
                                <div class="flex-grow-1">
                                    <div id="${ERROR_MESSAGE_ID}" class="mb-0"></div>
                                    <div id="${MISSING_FIELDS_LIST_ID}" class="mt-2 d-none">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">Campos Requeridos Faltantes:</small>
                                        <ul class="list-group list-group-flush small mb-0" id="${FIELDS_UL_ID}"></ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    asientosContainer.insertAdjacentHTML('afterbegin', tempErrorHtml);
                    container = d.getElementById(ERROR_CONTAINER_ID);
                    msgDiv = d.getElementById(ERROR_MESSAGE_ID);
                    fieldsUl = d.getElementById(FIELDS_UL_ID);
                    fieldsContainer = d.getElementById(MISSING_FIELDS_LIST_ID);
                } else {
                    // Fallback: intentar en mailinbox
                    const mailinboxContainer = d.getElementById('offcanvas-container-mailinbox');
                    if (mailinboxContainer && xhr.status >= 400) {
                        // Crear contenedor temporal de error
                        const tempErrorHtml = `
                            <div id="${ERROR_CONTAINER_ID}" class="mt-3">
                                <div class="alert alert-danger d-flex align-items-start" role="alert">
                                    <i class="bi bi-exclamation-triangle-fill me-2 mt-1"></i>
                                    <div class="flex-grow-1">
                                        <div id="${ERROR_MESSAGE_ID}" class="mb-0"></div>
                                        <div id="${MISSING_FIELDS_LIST_ID}" class="mt-2 d-none">
                                            <small class="text-muted text-uppercase fw-bold d-block mb-1">Campos Requeridos Faltantes:</small>
                                            <ul class="list-group list-group-flush small mb-0" id="${FIELDS_UL_ID}"></ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                        mailinboxContainer.insertAdjacentHTML('afterbegin', tempErrorHtml);
                        container = d.getElementById(ERROR_CONTAINER_ID);
                        msgDiv = d.getElementById(ERROR_MESSAGE_ID);
                        fieldsUl = d.getElementById(FIELDS_UL_ID);
                        fieldsContainer = d.getElementById(MISSING_FIELDS_LIST_ID);
                    } else {
                        // Fallback: intentar en inventario/productos
                        const inventarioContainer = d.getElementById('offcanvas-container-inventario');
                        if (inventarioContainer && xhr.status >= 400) {
                            // Crear contenedor temporal de error
                            const tempErrorHtml = `
                                <div id="${ERROR_CONTAINER_ID}" class="mt-3">
                                    <div class="alert alert-danger d-flex align-items-start" role="alert">
                                        <i class="bi bi-exclamation-triangle-fill me-2 mt-1"></i>
                                        <div class="flex-grow-1">
                                            <div id="${ERROR_MESSAGE_ID}" class="mb-0"></div>
                                            <div id="${MISSING_FIELDS_LIST_ID}" class="mt-2 d-none">
                                                <small class="text-muted text-uppercase fw-bold d-block mb-1">Campos Requeridos Faltantes:</small>
                                                <ul class="list-group list-group-flush small mb-0" id="${FIELDS_UL_ID}"></ul>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                            inventarioContainer.insertAdjacentHTML('afterbegin', tempErrorHtml);
                            container = d.getElementById(ERROR_CONTAINER_ID);
                            msgDiv = d.getElementById(ERROR_MESSAGE_ID);
                            fieldsUl = d.getElementById(FIELDS_UL_ID);
                            fieldsContainer = d.getElementById(MISSING_FIELDS_LIST_ID);
                        }
                    }
                }
            }
        }

        if (!container || !msgDiv) {
            console.warn(`${MOD} Contenedor de errores no encontrado. Asegúrate de incluir error_handler.html en el template.`);
            // ⚠️ Último recurso: mostrar error en consola y alerta
            try {
                const response = typeof xhr.response === 'string' 
                    ? JSON.parse(xhr.response) 
                    : xhr.response;
                const errorMsg = response?.message || response?.detail || `Error ${xhr.status}: ${xhr.statusText}`;
                console.error(`${MOD} Error no mostrado en UI:`, errorMsg);
                if (w.SintelFeedback && typeof w.SintelFeedback.error === 'function') {
                    w.SintelFeedback.error(errorMsg);
                } else {
                    alert(`Error ${xhr.status}: ${errorMsg}`);
                }
            } catch (e) {
                console.error(`${MOD} Error al procesar respuesta:`, e);
            }
            return;
        }

        let response;
        try {
            response = typeof xhr.response === 'string' 
                ? JSON.parse(xhr.response) 
                : xhr.response;
        } catch (e) {
            // ⚠️ Fallback v2.60: Si no es JSON (ej: 403 Forbidden de Django), usar texto plano
            console.warn(`${MOD} Respuesta no es JSON válida, usando fallback de texto`, e);
            response = { 
                detail: xhr.responseText || xhr.response || `Error ${xhr.status}: ${xhr.statusText}` 
            };
        }

        if (response) {
            // Mostrar contenedor
            container.classList.remove('d-none');

            // Mensaje principal
            // ⚠️ v2.60: Priorizar mensajes específicos de validación
            let errorMessage = response.message || response.error || response.detail || 'Error al procesar el documento.';
            
            // ⚠️ v2.61: Manejo de errores de validación de campos específicos (formato DRF: {campo: [mensaje]})
            // Si la respuesta tiene campos con errores (formato DRF), construir mensaje detallado
            const camposConErrores = [];
            if (response && typeof response === 'object') {
                // Buscar campos que sean arrays (formato DRF: {campo: [mensaje1, mensaje2]})
                Object.keys(response).forEach(campo => {
                    if (Array.isArray(response[campo]) && response[campo].length > 0) {
                        // Es un error de campo específico
                        const mensajesCampo = response[campo].join(', ');
                        const campoLegible = mapearCampoALegible(campo);
                        camposConErrores.push({
                            campo: campo,
                            campoLegible: campoLegible,
                            mensajes: response[campo],
                            mensajeUnificado: mensajesCampo
                        });
                    }
                });
            }
            
            // Si hay campos con errores, construir mensaje detallado
            if (camposConErrores.length > 0) {
                const mensajesCampos = camposConErrores.map(ce => 
                    `<strong>${ce.campoLegible}:</strong> ${ce.mensajeUnificado}`
                ).join('<br>');
                errorMessage = `⚠️ Errores de validación:<br>${mensajesCampos}`;
                
                // Agregar campos a missing_fields para mostrarlos en la lista
                if (!response.missing_fields || !Array.isArray(response.missing_fields)) {
                    response.missing_fields = camposConErrores.map(ce => ce.campo);
                }
            }
            
            // ⚠️ Manejo específico para errores conocidos
            if (response.error === "document_not_for_tenant") {
                // El mensaje del servidor ya contiene toda la información necesaria
                // ⚠️ MENSAJE ESPECÍFICO: "Este correo contiene una factura dirigida a un tercero, no se incluirá en contabilidad"
                errorMessage = response.message || errorMessage;
                
                // Si es contexto de ingesta por correo, agregar información adicional
                if (response.context === "mail_ingestion") {
                    errorMessage = `<strong>⚠️ Factura de Terceros Detectada</strong><br>${errorMessage}`;
                }
            } else if (response.error === "resolucion_no_configurada" || response.error === "resolucion_no_valida") {
                // ⚠️ v2.60: Manejo específico para errores de resolución DIAN (Gastos)
                errorMessage = response.message || errorMessage;
                errorMessage = `<strong>⚠️ Error de Configuración</strong><br>${errorMessage}`;
            } else if (response.error === "rango_agotado") {
                // ⚠️ v2.60: Manejo específico para rango de consecutivos agotado (409 Conflict)
                errorMessage = response.message || errorMessage;
                errorMessage = `<strong>⚠️ Rango de Consecutivos Agotado</strong><br>${errorMessage}`;
            } else if (response.error === "empresa_not_found" || response.code === "empresa_not_found") {
                // ⚠️ v2.60: Error de empresa no configurada (Proveedores, Clientes, etc.)
                errorMessage = response.detail || response.message || errorMessage;
                errorMessage = `<strong>⚠️ Configuración Requerida</strong><br>${errorMessage}<br><small class="text-muted">Por favor, configure la empresa del tenant antes de continuar.</small>`;
            } else if (response.error === "asiento_no_cuadrado" || response.error === "asiento_sin_movimientos") {
                // ⚠️ v2.60 Fase 3: Error Injector Contable - Análisis detallado de cuadratura
                errorMessage = response.message || errorMessage;
                
                // Construir mensaje detallado con análisis de movimientos
                let detallesHtml = '';
                if (response.detalles) {
                    const detalles = response.detalles;
                    detallesHtml = '<div class="mt-3"><strong>📊 Análisis Detallado:</strong><ul class="mb-0 mt-2">';
                    
                    // Información básica
                    detallesHtml += `<li><strong>Total Débito:</strong> $${parseFloat(detalles.total_debe || 0).toFixed(2)}</li>`;
                    detallesHtml += `<li><strong>Total Crédito:</strong> $${parseFloat(detalles.total_haber || 0).toFixed(2)}</li>`;
                    detallesHtml += `<li><strong>Diferencia:</strong> <span class="text-danger fw-bold">$${parseFloat(detalles.diferencia_absoluta || 0).toFixed(2)}</span></li>`;
                    
                    // Tipo de desbalance
                    if (detalles.tipo_desbalance === 'falta_credito') {
                        detallesHtml += `<li class="text-danger"><strong>⚠️ Falta Crédito:</strong> Agregue un movimiento de crédito por $${parseFloat(detalles.valor_faltante || 0).toFixed(2)}</li>`;
                    } else if (detalles.tipo_desbalance === 'falta_debito') {
                        detallesHtml += `<li class="text-danger"><strong>⚠️ Falta Débito:</strong> Agregue un movimiento de débito por $${parseFloat(detalles.valor_faltante || 0).toFixed(2)}</li>`;
                    }
                    
                    // Cuentas problemáticas
                    if (detalles.cuentas_problematicas && detalles.cuentas_problematicas.length > 0) {
                        detallesHtml += '<li class="mt-2"><strong>🔴 Cuentas con Problemas:</strong><ul class="mb-0">';
                        detalles.cuentas_problematicas.forEach(cuenta => {
                            detallesHtml += `<li><strong>${cuenta.cuenta_codigo} - ${cuenta.cuenta_nombre}:</strong> ${cuenta.problema} (Débito: $${parseFloat(cuenta.debe || 0).toFixed(2)}, Crédito: $${parseFloat(cuenta.haber || 0).toFixed(2)})</li>`;
                        });
                        detallesHtml += '</ul></li>';
                    }
                    
                    // Sugerencia
                    if (detalles.sugerencia) {
                        detallesHtml += `<li class="mt-2 text-info"><strong>💡 Sugerencia:</strong> ${detalles.sugerencia}</li>`;
                    }
                    
                    detallesHtml += '</ul></div>';
                }
                
                errorMessage = `<strong>⚠️ Error de Cuadratura</strong><br>${errorMessage}${detallesHtml}`;
            } else if (response.error === "validacion_error") {
                // ⚠️ v2.60: Manejo específico para errores de validación (400/422)
                errorMessage = response.message || errorMessage;
                // Si hay detalles, agregarlos al mensaje
                if (response.details && typeof response.details === 'object') {
                    const detalles = Object.entries(response.details)
                        .map(([field, msg]) => `${mapearCampoALegible(field)}: ${msg}`)
                        .join('<br>');
                    errorMessage = `<strong>⚠️ Error de Validación</strong><br>${errorMessage}<br><small class="text-muted">${detalles}</small>`;
                } else {
                    errorMessage = `<strong>⚠️ Error de Validación</strong><br>${errorMessage}`;
                }
            } else if (response.error === "authentication_error" || response.error === "auth_failed") {
                // ⚠️ v2.60: Manejo específico para errores de autenticación de correo
                // ⚠️ COMPATIBILIDAD: Maneja tanto "authentication_error" como "auth_failed"
                errorMessage = response.message || errorMessage;
                if (response.troubleshooting) {
                    errorMessage = `<strong>🔐 Error de Autenticación de Correo</strong><br>${errorMessage}<br><br><div class="alert alert-info mt-2 mb-0"><small>${response.troubleshooting}</small></div>`;
                } else {
                    errorMessage = `<strong>🔐 Error de Autenticación de Correo</strong><br>${errorMessage}`;
                }
            } else if (response.error === "connection_error") {
                // ⚠️ v2.60: Manejo específico para errores de conexión de correo
                errorMessage = response.message || errorMessage;
                if (response.troubleshooting) {
                    errorMessage = `<strong>🌐 Error de Conexión de Correo</strong><br>${errorMessage}<br><br><div class="alert alert-info mt-2 mb-0"><small>${response.troubleshooting}</small></div>`;
                } else {
                    errorMessage = `<strong>🌐 Error de Conexión de Correo</strong><br>${errorMessage}`;
                }
            } else if (response.error === "mailbox_error") {
                // ⚠️ v2.60: Manejo específico para errores generales de buzón
                errorMessage = response.message || errorMessage;
                if (response.troubleshooting) {
                    errorMessage = `<strong>📧 Error de Buzón de Correo</strong><br>${errorMessage}<br><br><div class="alert alert-info mt-2 mb-0"><small>${response.troubleshooting}</small></div>`;
                } else {
                    errorMessage = `<strong>📧 Error de Buzón de Correo</strong><br>${errorMessage}`;
                }
            } else if (response.error === "config_not_found" || response.error === "config_error") {
                // ⚠️ v2.60: Manejo específico para errores de configuración de buzón
                errorMessage = response.message || errorMessage;
                errorMessage = `<strong>⚙️ Error de Configuración de Buzón</strong><br>${errorMessage}<br><br><div class="alert alert-warning mt-2 mb-0"><small>Verifique que la configuración de buzón exista y esté activa para este tenant.</small></div>`;
            } else if (response.missing_fields && Array.isArray(response.missing_fields) && response.missing_fields.length > 0) {
                // Si hay campos faltantes (caso normal), agregar información adicional
                const camposLegibles = response.missing_fields.map(f => mapearCampoALegible(f));
                errorMessage = `Validación fallida: ${camposLegibles.join(', ')}`;
            }
            
            // Usar innerHTML para permitir formato HTML si es necesario
            msgDiv.innerHTML = `<strong>${errorMessage}</strong>`;

            // Manejo específico de campos faltantes (caso 422 del PDF)
            if (response.missing_fields && Array.isArray(response.missing_fields) && response.missing_fields.length > 0) {
                fieldsContainer.classList.remove('d-none');
                fieldsUl.innerHTML = response.missing_fields
                    .map(field => {
                        const label = mapearCampoALegible(field);
                        return `<li class="list-group-item bg-transparent text-danger border-0 py-1">
                            <i class="bi bi-dash-circle me-1"></i>${label}
                        </li>`;
                    })
                    .join('');
            } else {
                fieldsContainer.classList.add('d-none');
                fieldsUl.innerHTML = '';
            }

            // Log para debugging
            console.log(`${MOD} Error mostrado:`, {
                status: xhr.status,
                message: errorMessage,
                missing_fields: response.missing_fields || []
            });

        } catch (e) {
            console.error(`${MOD} Error parseando respuesta de error:`, e);
            // Fallback: mostrar mensaje genérico
            if (msgDiv) {
                msgDiv.textContent = `Error ${xhr.status || 500}: No se pudo procesar la respuesta del servidor.`;
            }
            container.classList.remove('d-none');
        }
    }

    /**
     * Resetear el contenedor de errores
     * ⚠️ v2.61.3: Busca en múltiples contenedores (facturas, asientos, inventario, etc.)
     */
    function resetError() {
        // Buscar en todos los contenedores posibles
        const containers = [
            d.getElementById(ERROR_CONTAINER_ID),
            d.querySelector('#offcanvas-inventario')?.querySelector(`#${ERROR_CONTAINER_ID}`),
            d.querySelector('#offcanvas-container-inventario')?.querySelector(`#${ERROR_CONTAINER_ID}`),
            d.querySelector('#offcanvas-container-asientos')?.querySelector(`#${ERROR_CONTAINER_ID}`),
            d.querySelector('#offcanvas-container-mailinbox')?.querySelector(`#${ERROR_CONTAINER_ID}`),
        ].filter(Boolean);

        containers.forEach(container => {
            if (container) {
                container.classList.add('d-none');
            }
            const fieldsContainer = container?.querySelector(`#${MISSING_FIELDS_LIST_ID}`);
            const fieldsUl = container?.querySelector(`#${FIELDS_UL_ID}`);
            
            if (fieldsContainer) {
                fieldsContainer.classList.add('d-none');
            }
            if (fieldsUl) {
                fieldsUl.innerHTML = '';
            }
        });
    }

    /**
     * Inicializar listeners de HTMX
     */
    function init() {
        // Resetear errores antes de cada petición
        d.body.addEventListener('htmx:beforeRequest', () => {
            resetError();
        });

        // Manejar errores de respuesta
        d.body.addEventListener('htmx:responseError', (evt) => {
            const xhr = evt.detail.xhr;
            if (xhr) {
                // ⚠️ v2.60: Manejo específico de errores según código de estado
                if (xhr.status === 401) {
                    console.log(`${MOD} Error 401 detectado - Error de autenticación`);
                } else if (xhr.status === 422) {
                    console.log(`${MOD} Error 422 detectado - Validación fallida`);
                } else if (xhr.status === 503) {
                    console.log(`${MOD} Error 503 detectado - Error de conexión`);
                }
                showError(xhr);
            }
        });

        console.log(`${MOD} Módulo de manejo de errores inicializado`);
    }

    // Auto-inicializar cuando el DOM esté listo
    if (d.readyState === 'loading') {
        d.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exponer API pública (opcional, para uso manual)
    w.ErrorHandler = {
        show: showError,
        reset: resetError
    };

})(window, document);
