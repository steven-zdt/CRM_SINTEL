/**
 * TabulatorFactory v2.40 - Factory Global para Tabulator (The Engine)
 * 
 * ⚠️ Arquitectura Escalable: Configuración base reutilizable para DRF
 * ⚠️ Vanilla JS: Sin dependencias de jQuery
 * ⚠️ SaaS-Ready: Diseñado para +1000 clientes
 * 
 * Uso:
 *   const table = TabulatorFactory.create('#grid-id', '/api/v1/endpoint/', columns);
 */
(function(w, d) {
    'use strict';

    // Helper: Obtener CSRF token
    function getCookie(name) {
        const value = `; ${d.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    /**
     * Factory principal para crear tablas Tabulator con configuración DRF
     * 
     * @param {string} selector - Selector CSS del contenedor (ej: '#grid-clientes')
     * @param {string} apiUrl - URL base de la API (ej: '/api/v1/clientes/')
     * @param {Array} columns - Array de definiciones de columnas
     * @param {Object} options - Opciones adicionales (opcional)
     * @returns {Tabulator} Instancia de Tabulator
     */
    function createTable(selector, apiUrl, columns, options = {}) {
        const container = d.querySelector(selector);
        if (!container) {
            console.error(`[TabulatorFactory] Contenedor ${selector} no encontrado`);
            return null;
        }

        // ⚠️ v2.61: Asegurar que el contenedor tenga límites de ancho para evitar expansión infinita
        if (!container.style.maxWidth && !container.style.width) {
            container.style.maxWidth = "100%";
            container.style.overflowX = "auto";
        }

        // ⚠️ v2.60: Verificar Tabulator con retry si no está disponible inmediatamente
        if (!w.Tabulator) {
            // Intentar esperar un poco si el script del CDN aún se está cargando
            console.warn('[TabulatorFactory] Tabulator no está disponible. Verificando si se está cargando...');
            // Retornar null - el módulo que llama debe manejar el retry
            return null;
        }

        // ⚠️ CRÍTICO: Guardar pageSize en closure para acceso desde ajaxResponse
        const pageSize = options.paginationSize || 10;
        
        // Configuración base obligatoria
        const defaultConfig = {
            // ⚠️ v2.61: Cambiar de "fitColumns" a "fitDataFill" para evitar expansión horizontal infinita
            // "fitDataFill" ajusta columnas al ancho disponible sin causar loops de redimensionamiento
            layout: options.layout || "fitDataFill",
            // ⚠️ v2.61: Deshabilitar responsiveLayout para evitar loops de expansión
            responsiveLayout: false,
            // ⚠️ v2.61: Deshabilitar redimensionamiento automático de columnas
            resizeColumns: false,
            placeholder: "Sin registros encontrados",
            pagination: true,
            paginationMode: "remote", // Server-Side siempre
            paginationSize: pageSize, // Default: 10
            paginationSizeSelector: options.paginationSizeSelector || [10, 25, 50, 100],
            
            // ⚠️ CRÍTICO: ajaxURL es necesario para que Tabulator sepa de dónde obtener datos
            ajaxURL: apiUrl,
            
            // Generador de URL con parámetros
            ajaxURLGenerator: function(url, config, params) {
                console.log('[TabulatorFactory.ajaxURLGenerator] Llamado con:', { url, params, apiUrl });
                
                // ⚠️ v2.60: Extraer URL base y parámetros existentes de apiUrl
                let baseUrl = apiUrl;
                let existingParams = new URLSearchParams();
                
                // Detectar si apiUrl ya tiene parámetros de consulta
                const urlParts = apiUrl.split('?');
                if (urlParts.length > 1) {
                    baseUrl = urlParts[0];
                    existingParams = new URLSearchParams(urlParts[1]);
                }
                
                // Agregar parámetros de paginación
                if (params.page) existingParams.set('page', params.page);
                if (params.size) existingParams.set('page_size', params.size);
                
                // Búsqueda desde input externo (si existe)
                if (options.searchInputSelector) {
                    const searchInput = d.querySelector(options.searchInputSelector);
                    if (searchInput && searchInput.value.trim()) {
                        existingParams.set('search', searchInput.value.trim());
                    }
                }
                
                // Parámetros adicionales personalizados
                if (options.ajaxParams && typeof options.ajaxParams === 'function') {
                    const customParams = options.ajaxParams(params);
                    Object.entries(customParams || {}).forEach(([key, value]) => {
                        if (value !== null && value !== undefined) {
                            existingParams.set(key, value);
                        }
                    });
                }
                
                // Construir URL final con todos los parámetros
                const queryString = existingParams.toString();
                const finalUrl = queryString ? `${baseUrl}?${queryString}` : baseUrl;
                
                console.log('[TabulatorFactory.ajaxURLGenerator] URL generada:', finalUrl);
                
                return finalUrl;
            },
            
            // Petición AJAX con fetch y manejo de errores
            ajaxRequest: async function(url, config, params) {
                console.log('[TabulatorFactory.ajaxRequest] Iniciando petición:', { url, params });

                // Construir headers iniciales (CSRF + Content-Type)
                const headers = {
                    "X-CSRFToken": getCookie('csrftoken') || '',
                    "Content-Type": "application/json"
                };

                // Intentar inyectar Authorization si el helper jwtAuth está disponible
                try {
                    if (typeof window.jwtAuth === 'object' && typeof window.jwtAuth.getValidAccessToken === 'function') {
                        const access = await window.jwtAuth.getValidAccessToken();
                        if (access) {
                            headers['Authorization'] = `Bearer ${access}`;
                        }
                    }
                } catch (err) {
                    console.debug('[TabulatorFactory] No se pudo obtener JWT desde jwtAuth:', err && err.message ? err.message : err);
                }

                return fetch(url, {
                    method: "GET",
                    credentials: 'same-origin',
                    headers: headers
                }).then(response => {
                    console.log('[TabulatorFactory.ajaxRequest] Respuesta recibida:', {
                        status: response.status,
                        statusText: response.statusText,
                        ok: response.ok,
                        contentType: response.headers.get('content-type')
                    });
                    // Manejo de errores críticos
                    if (response.status === 401) {
                        console.error('[TabulatorFactory] Error 401: Token inválido o expirado');
                        if (w.notyf) {
                            // ⚠️ v2.40: Error 401 - SintelFeedback NO debe mostrar alerta (interceptor global maneja)
                            console.warn('[TabulatorFactory] Error 401, interceptor global manejará redirección');
                        }
                        // Opcional: redirigir a login
                        // window.location.href = '/login/';
                        throw new Error('Unauthorized: Token inválido');
                    }
                    
                    if (response.status === 403) {
                        console.error('[TabulatorFactory] Error 403: Permisos insuficientes');
                        // ⚠️ v2.60: Error Boundary Pattern - Delegar a UIManager
                        if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                            w.UIManager.notifyError(
                                { status: 403, data: { detail: 'No tienes permisos para acceder a este recurso.' } },
                                '[TabulatorFactory]'
                            );
                        } else if (w.SintelFeedback && typeof w.SintelFeedback.handleAPIError === 'function') {
                            // Fallback: usar SintelFeedback directamente si UIManager no está disponible
                            w.SintelFeedback.handleAPIError({ status: 403, data: { detail: 'No tienes permisos para acceder a este recurso.' } }, '[TabulatorFactory]');
                        }
                        throw new Error('Forbidden: Permisos insuficientes');
                    }
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    return response.json().then(json => {
                        console.log('[TabulatorFactory.ajaxRequest] JSON parseado:', {
                            type: typeof json,
                            keys: json && typeof json === 'object' ? Object.keys(json) : 'N/A',
                            hasCount: json && typeof json === 'object' && 'count' in json,
                            hasResults: json && typeof json === 'object' && 'results' in json,
                            resultsLength: json && typeof json === 'object' && Array.isArray(json.results) ? json.results.length : 0
                        });
                        return json;
                    });
                }).catch(error => {
                    console.error('[TabulatorFactory.ajaxRequest] ⚠️ Error en petición AJAX:', error);
                    // ⚠️ v2.40: RESILIENCIA - Retornar estructura vacía válida para evitar crash de Tabulator
                    // Esto asegura que ajaxResponse siempre reciba un objeto válido, no undefined
                    return {
                        count: 0,
                        results: [], // ⚠️ CRÍTICO: Array vacío, no undefined
                        next: null,
                        previous: null
                    };
                });
            },
            
            // Adaptador DRF -> Tabulator (CRÍTICO)
            // ⚠️ v2.40: RESILIENCIA - Siempre retorna un array válido, incluso si la API falla
            ajaxResponse: function(url, params, response) {
                // ⚠️ CRÍTICO: Validación defensiva inicial - response puede ser undefined/null
                if (response === null || response === undefined) {
                    console.warn('[TabulatorFactory.ajaxResponse] ⚠️ Response es null/undefined, retornando array vacío');
                    return {
                        last_page: 1,
                        data: []
                    };
                }
                
                // ⚠️ DEBUG: Log temporal para auditoría forense
                console.log('[TabulatorFactory.ajaxResponse] URL:', url);
                console.log('[TabulatorFactory.ajaxResponse] Params:', params);
                console.log('[TabulatorFactory.ajaxResponse] Response type:', typeof response);
                console.log('[TabulatorFactory.ajaxResponse] Response keys:', response && typeof response === 'object' ? Object.keys(response) : 'N/A');
                if (response && typeof response === 'object' && response.results) {
                    console.log('[TabulatorFactory.ajaxResponse] Response.count:', response.count);
                    console.log('[TabulatorFactory.ajaxResponse] Response.results length:', Array.isArray(response.results) ? response.results.length : 'NO ES ARRAY');
                    console.log('[TabulatorFactory.ajaxResponse] Response.results[0]:', Array.isArray(response.results) ? response.results[0] : 'N/A');
                }
                
                // ⚠️ CRÍTICO: Manejar diferentes formatos de respuesta
                
                // Caso 1: Respuesta directa como array (sin paginación)
                if (Array.isArray(response)) {
                    console.log('[TabulatorFactory.ajaxResponse] Caso 1: Array directo, items:', response.length);
                    return {
                        data: response,
                        last_page: 1
                    };
                }
                
                // Caso 2: Respuesta paginada de DRF Standard Pagination
                // DRF retorna: {count: 100, next: "...", previous: null, results: [...]}
                // Tabulator espera: {last_page: 10, data: [...]}
                if (response && typeof response === 'object' && response.results !== undefined) {
                    // ⚠️ CRÍTICO: Validación defensiva - asegurar que results es un array
                    let results = [];
                    if (Array.isArray(response.results)) {
                        results = response.results;
                    } else {
                        console.warn('[TabulatorFactory.ajaxResponse] ⚠️ response.results no es un array:', typeof response.results);
                        results = [];
                    }
                    
                    // ⚠️ CRÍTICO: Obtener pageSize del closure o de params
                    // params.size puede venir de ajaxURLGenerator, pero en ajaxResponse puede no estar disponible
                    // Usamos el pageSize guardado en el closure como fallback
                    let currentPageSize = pageSize; // Del closure
                    if (params && params.size) {
                        currentPageSize = parseInt(params.size) || pageSize;
                    }
                    
                    const count = parseInt(response.count) || 0;
                    const lastPage = count > 0 && currentPageSize > 0 ? Math.ceil(count / currentPageSize) : 1;
                    
                    console.log('[TabulatorFactory.ajaxResponse] Caso 2: DRF paginado', {
                        count: count,
                        pageSize: currentPageSize,
                        lastPage: lastPage,
                        resultsCount: results.length,
                        firstResult: results[0] || null
                    });
                    
                    const transformedResponse = {
                        last_page: lastPage,
                        data: results // ⚠️ v2.40: Siempre un array válido
                    };
                    
                    console.log('[TabulatorFactory.ajaxResponse] ✅ Transformación exitosa:', {
                        last_page: transformedResponse.last_page,
                        dataCount: transformedResponse.data.length,
                        firstDataItem: transformedResponse.data[0] || null
                    });
                    
                    return transformedResponse;
                }
                
                // Caso 3: Respuesta ya en formato Tabulator (fallback)
                if (response && typeof response === 'object' && response.data !== undefined) {
                    // ⚠️ CRÍTICO: Validación defensiva - asegurar que data es un array
                    let dataArray = [];
                    if (Array.isArray(response.data)) {
                        dataArray = response.data;
                    } else {
                        console.warn('[TabulatorFactory.ajaxResponse] ⚠️ response.data no es un array:', typeof response.data);
                        dataArray = [];
                    }
                    
                    console.log('[TabulatorFactory.ajaxResponse] Caso 3: Formato Tabulator, items:', dataArray.length);
                    return {
                        last_page: response.last_page || 1,
                        data: dataArray
                    };
                }
                
                // Caso 4: Objeto directo (singleton o respuesta única) - convertir a array
                // Esto puede pasar cuando hay un solo registro y la paginación no está activa
                if (response && typeof response === 'object' && !Array.isArray(response) && !response.results && !response.data) {
                    // Verificar si tiene campos típicos de un modelo (id, etc.)
                    if (response.id !== undefined || Object.keys(response).length > 0) {
                        console.log('[TabulatorFactory.ajaxResponse] Caso 4: Objeto directo detectado, convirtiendo a array');
                        return {
                            last_page: 1,
                            data: [response] // Envolver en array
                        };
                    }
                }
                
                // Caso 5: Fallback - respuesta vacía o formato desconocido
                // ⚠️ v2.40: RESILIENCIA - Siempre retornar estructura válida
                console.warn('[TabulatorFactory.ajaxResponse] ⚠️ Caso 5: Formato no reconocido, retornando array vacío. Response:', response);
                return {
                    last_page: 1,
                    data: [] // ⚠️ CRÍTICO: Siempre retornar array vacío en lugar de undefined
                };
            },
            
            // Manejo de errores en AJAX
            ajaxError: function(error) {
                console.error('[TabulatorFactory] Error AJAX:', error);
                // ⚠️ v2.60: Error Boundary Pattern - Delegar a UIManager
                if (w.UIManager && typeof w.UIManager.notifyError === 'function') {
                    w.UIManager.notifyError(
                        { status: 500, data: { detail: 'Error al cargar los datos. Por favor, intenta nuevamente.' } },
                        '[TabulatorFactory]'
                    );
                } else if (w.SintelFeedback && typeof w.SintelFeedback.handleAPIError === 'function') {
                    // Fallback: usar SintelFeedback directamente si UIManager no está disponible
                    w.SintelFeedback.handleAPIError({ status: 500, data: { detail: 'Error al cargar los datos. Por favor, intenta nuevamente.' } }, '[TabulatorFactory]', false);
                }
            },
            
            columns: columns
        };

        // ⚠️ CRÍTICO: Merge seguro - no permitir que options sobrescriba configuración crítica
        // Las funciones ajaxResponse, ajaxRequest, ajaxURLGenerator son inmutables
        const finalConfig = Object.assign({}, defaultConfig);
        
        // ⚠️ v2.61: Detectar si pagination está deshabilitada para ajustar ajaxResponse
        const isPaginationDisabled = options.pagination === false;
        
        // Solo permitir sobrescribir opciones no críticas
        Object.keys(options).forEach(key => {
            // ⚠️ PROHIBIDO sobrescribir funciones críticas de AJAX y ajaxURL
            // ⚠️ v2.61: EXCEPCIÓN: Permitir sobrescribir ajaxResponse si pagination: false
            if (!['ajaxResponse', 'ajaxRequest', 'ajaxURLGenerator', 'ajaxURL', 'ajaxError', 'columns'].includes(key)) {
                finalConfig[key] = options[key];
            } else if (key === 'ajaxResponse' && isPaginationDisabled) {
                // ⚠️ v2.61: Permitir sobrescribir ajaxResponse cuando pagination: false
                // Esto permite que el módulo retorne arrays directos en lugar de {data, last_page}
                finalConfig[key] = options[key];
                console.log('[TabulatorFactory] ⚠️ ajaxResponse personalizado aplicado (pagination: false)');
            }
        });
        
        // ⚠️ v2.61: Si pagination está deshabilitada y no hay ajaxResponse personalizado,
        // modificar el ajaxResponse por defecto para retornar arrays directos
        if (isPaginationDisabled && !options.ajaxResponse) {
            const originalAjaxResponse = finalConfig.ajaxResponse;
            finalConfig.ajaxResponse = function(url, params, response) {
                const result = originalAjaxResponse.call(this, url, params, response);
                // Si el resultado es {data, last_page}, retornar solo el array
                if (result && typeof result === 'object' && result.data && Array.isArray(result.data)) {
                    console.log('[TabulatorFactory] ⚠️ Convertiendo {data, last_page} a array directo (pagination: false)');
                    return result.data;
                }
                // Si ya es un array, retornarlo directamente
                if (Array.isArray(result)) {
                    return result;
                }
                // Fallback: retornar array vacío
                return [];
            };
        }
        
        console.log('[TabulatorFactory] Configuración final:', {
            paginationMode: finalConfig.paginationMode,
            paginationSize: finalConfig.paginationSize,
            ajaxURL: finalConfig.ajaxURL,
            hasAjaxURLGenerator: typeof finalConfig.ajaxURLGenerator === 'function',
            hasAjaxResponse: typeof finalConfig.ajaxResponse === 'function',
            hasAjaxRequest: typeof finalConfig.ajaxRequest === 'function',
            columnsCount: finalConfig.columns ? finalConfig.columns.length : 0
        });
        
        // Crear y retornar instancia
        const tableInstance = new Tabulator(container, finalConfig);

        // ⚠️ DEBUG: Verificar que la tabla se creó correctamente
        console.log('[TabulatorFactory] ✅ Tabla Tabulator creada:', {
            selector: selector,
            apiUrl: apiUrl,
            instance: tableInstance ? 'OK' : 'NULL'
        });

        // ⚠️ v3.5: Debounce en input de búsqueda (300ms) para reducir requests
        if (options.searchInputSelector) {
            const searchInput = d.querySelector(options.searchInputSelector);
            if (searchInput) {
                let debounceTimer = null;

                searchInput.addEventListener('input', function() {
                    // Cancelar timeout anterior si existe
                    if (debounceTimer) {
                        clearTimeout(debounceTimer);
                    }

                    // Configurar nuevo timeout (300ms)
                    debounceTimer = setTimeout(() => {
                        console.log('[TabulatorFactory] 🔍 Búsqueda con debounce:', searchInput.value);
                        // Ir a la página 1 cuando el usuario termina de escribir
                        tableInstance.setPage(1);
                    }, 300);
                });

                console.log('[TabulatorFactory] ✅ Debounce configurado para', options.searchInputSelector);
            }
        }

        return tableInstance;
    }

    /**
     * Alias simplificado: create() es más corto que createTable()
     */
    function create(selector, apiUrl, columns, options) {
        return createTable(selector, apiUrl, columns, options);
    }

    /**
     * Formateadores comunes reutilizables (DRY)
     */
    const formatters = {
        /**
         * Formateador de estado booleano (Activo/Inactivo)
         * @param {CellComponent} cell - Celda de Tabulator
         * @returns {string} HTML con badge
         */
        statusBadge: function(cell) {
            const value = cell.getValue();
            return value 
                ? '<span class="badge bg-success">Activo</span>' 
                : '<span class="badge bg-secondary">Inactivo</span>';
        },
        
        /**
         * Alias para compatibilidad: badgeStatus -> statusBadge
         */
        badgeStatus: function(cell) {
            return formatters.statusBadge(cell);
        },
        
        /**
         * Generador de columna de acciones (Editar/Eliminar)
         * @param {Object} config - Configuración {onEdit: Function, onDelete: Function}
         * @returns {Function} Formatter function
         */
        actions: function(config = {}) {
            return function(cell) {
                const rowData = cell.getRow().getData();
                const id = rowData.id;
                
                let buttons = '';
                
                if (config.onEdit) {
                    buttons += `
                        <button class="btn btn-sm btn-link text-primary p-0 me-2" onclick="(${config.onEdit.toString()})(${id})" title="Editar">
                            <i class="fas fa-edit"></i>
                        </button>
                    `;
                }
                
                if (config.onDelete) {
                    buttons += `
                        <button class="btn btn-sm btn-link text-danger p-0" onclick="(${config.onDelete.toString()})(${id})" title="Eliminar">
                            <i class="fas fa-trash"></i>
                        </button>
                    `;
                }
                
                return buttons || '-';
            };
        },
        
        /**
         * Botón de editar estándar (legacy, usar actions() en su lugar)
         */
        editButton: function(cell, onClick) {
            const id = cell.getRow().getData().id;
            const onclick = onClick 
                ? `onclick="(${onClick.toString()})(${id})"` 
                : '';
            return `
                <button class="btn btn-sm btn-link text-primary p-0" ${onclick} title="Editar">
                    <i class="fas fa-edit"></i>
                </button>
            `;
        },
        
        /**
         * Botón de eliminar estándar (legacy, usar actions() en su lugar)
         */
        deleteButton: function(cell, onClick) {
            const id = cell.getRow().getData().id;
            const onclick = onClick 
                ? `onclick="(${onClick.toString()})(${id})"` 
                : '';
            return `
                <button class="btn btn-sm btn-link text-danger p-0" ${onclick} title="Eliminar">
                    <i class="fas fa-trash"></i>
                </button>
            `;
        },
        
        /**
         * Formateador de badge genérico
         * @param {CellComponent} cell - Celda de Tabulator
         * @param {string} colorClass - Clase de color Bootstrap (bg-primary, bg-success, etc.)
         * @returns {string} HTML con badge
         */
        badge: function(cell, colorClass = 'bg-secondary') {
            const value = cell.getValue();
            return value ? `<span class="badge ${colorClass}">${value}</span>` : '-';
        },
        
        /**
         * Formateador de valor con fallback
         * @param {CellComponent} cell - Celda de Tabulator
         * @param {string} fallback - Valor por defecto si está vacío
         * @returns {string} Valor o fallback
         */
        valueOrFallback: function(cell, fallback = '-') {
            const value = cell.getValue();
            return value || fallback;
        }
    };

    // Exponer API global
    w.TabulatorFactory = {
        create: create,
        createTable: createTable, // Alias para compatibilidad
        formatters: formatters
    };

})(window, document);
