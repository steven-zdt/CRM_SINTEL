/**
 * Tenants Manager - Controlador JavaScript para gestión de tenants (API-First)
 * 
 * Consume exclusivamente /api/public/v1/tenants/ como única fuente de verdad.
 * 
 * Funcionalidades:
 * - Listar tenants con DataTables (server-side)
 * - Crear tenant mediante endpoint /onboard/
 * - Actualizar tenant (PATCH)
 * - Eliminar tenant (DELETE)
 * - Manejo de errores de validación
 * 
 * ⚠️ SEGURIDAD: Este módulo solo debe cargarse en el dominio público (localhost).
 */

(function() {
    'use strict';
    
    // Verificación de hostname: la consola solo debe cargarse en el dominio público
    const hostname = window.location.hostname;
    const isPublicHost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'sintel.com';
    
    if (!isPublicHost) {
        // Hard stop: abortar si se carga en un dominio de tenant
        console.error('❌ ERROR DE SEGURIDAD: Tenants Manager no debe cargarse en dominios de tenant.');
        console.error(`Hostname detectado: ${hostname}`);
        throw new Error('Tenants Manager: Hard stop - cargado en dominio de tenant');
    }

    // Obtener CSRF token de las cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function getCSRFToken() {
        return getCookie('csrftoken');
    }

    // Obtener token JWT (si está disponible)
    function getJWTToken() {
        // Intentar obtener desde localStorage o sessionStorage
        const token = localStorage.getItem('jwt_access_token') || sessionStorage.getItem('jwt_access_token');
        return token ? `Bearer ${token}` : null;
    }

    // Headers estándar para peticiones API
    function getHeaders(includeCSRF = true) {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        };

        if (includeCSRF) {
            const csrfToken = getCSRFToken();
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }
        }

        const jwtToken = getJWTToken();
        if (jwtToken) {
            headers['Authorization'] = jwtToken;
        }

        return headers;
    }

    // Manejo de errores de API
    function handleAPIError(error, defaultMessage = 'Error al procesar la solicitud') {
        console.error('API Error:', error);
        
        if (error.response) {
            // Error de respuesta HTTP (400, 404, 500, etc.)
            const status = error.response.status;
            const data = error.response.data || {};
            
            if (status === 400) {
                // Errores de validación
                return {
                    type: 'validation',
                    message: data.error || data.detail || 'Error de validación',
                    errors: data.errors || data
                };
            } else if (status === 401) {
                return {
                    type: 'auth',
                    message: 'No autorizado. Por favor, inicia sesión nuevamente.'
                };
            } else if (status === 403) {
                return {
                    type: 'permission',
                    message: 'No tienes permisos para realizar esta acción.'
                };
            } else if (status === 404) {
                return {
                    type: 'not_found',
                    message: 'Recurso no encontrado.'
                };
            } else {
                return {
                    type: 'server',
                    message: data.error || data.detail || `Error del servidor (${status})`
                };
            }
        } else if (error.request) {
            // Error de red
            return {
                type: 'network',
                message: 'Error de conexión. Verifica tu conexión a internet.'
            };
        } else {
            // Error desconocido
            return {
                type: 'unknown',
                message: error.message || defaultMessage
            };
        }
    }

    // Mostrar mensaje de error en el formulario
    function showFormError(fieldId, message) {
        const field = document.getElementById(fieldId);
        const errorDiv = document.getElementById(`${fieldId}_error`);
        
        if (field) {
            field.classList.add('border-red-500');
        }
        
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
        }
    }

    // Limpiar errores del formulario
    function clearFormErrors() {
        document.querySelectorAll('[id$="_error"]').forEach(el => {
            el.classList.add('hidden');
            el.textContent = '';
        });
        document.querySelectorAll('.border-red-500').forEach(el => {
            el.classList.remove('border-red-500');
        });
    }

    // Mostrar notificación (unificado con users_manager.js)
    function showNotification(message, type = 'info') {
        const container = document.getElementById('messages-container');
        if (!container) {
            // Fallback: crear notificación flotante si no existe el contenedor
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
                type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
                type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
                'bg-blue-50 text-blue-800 border border-blue-200'
            }`;
            notification.textContent = message;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 5000);
            return;
        }

        const alertClassMap = {
            'success': 'bg-green-50 text-green-800 border-green-400',
            'error': 'bg-red-50 text-red-800 border-red-400',
            'warning': 'bg-yellow-50 text-yellow-800 border-yellow-400',
            'info': 'bg-blue-50 text-blue-800 border-blue-400',
        };
        const alertClass = alertClassMap[type] || alertClassMap['info'];

        const iconMap = {
            'success': '<svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
            'error': '<svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
            'warning': '<svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>',
            'info': '<svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>',
        };
        const icon = iconMap[type] || iconMap['info'];

        const alert = document.createElement('div');
        alert.className = `rounded-lg p-4 shadow-sm border-l-4 ${alertClass} animate-fade-in`;
        alert.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">${icon}</div>
                <div class="ml-3 flex-1">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-3 text-gray-400 hover:text-gray-600">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;
        container.appendChild(alert);

        // Auto-remove después de 5 segundos
        setTimeout(() => {
            if (alert.parentElement) {
                alert.remove();
            }
        }, 5000);
    }

    // ============================================
    // GESTIÓN DE LISTADO (DataTables)
    // ============================================

    function initTenantsTable(apiUrl) {
        if (typeof jQuery === 'undefined' || typeof jQuery.fn.dataTable === 'undefined') {
            console.error('DataTables no está disponible');
            return;
        }

        const table = jQuery('#dt-tenants').DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: apiUrl,
                type: 'POST',  // API-First: POST obligatorio con CSRF
                headers: getHeaders(true),  // Incluir CSRF token
                contentType: 'application/json',
                data: function(d) {
                    // DataTables envía parámetros en formato estándar
                    // El backend espera: draw, start, length, search[value], order[i][column], order[i][dir]
                    return JSON.stringify({
                        draw: d.draw,
                        start: d.start,
                        length: d.length,
                        search: {
                            value: d.search.value || ''
                        },
                        order: d.order.map(function(o) {
                            return {
                                column: o.column,
                                dir: o.dir
                            };
                        }),
                        columns: d.columns.map(function(c) {
                            return {
                                data: c.data,
                                name: c.name || '',
                                searchable: c.searchable !== false,
                                orderable: c.orderable !== false,
                                search: {
                                    value: c.search.value || '',
                                    regex: c.search.regex || false
                                }
                            };
                        })
                    });
                },
                dataSrc: function(json) {
                    // El backend responde con contrato DataTables estándar:
                    // { draw, recordsTotal, recordsFiltered, data }
                    // data contiene objetos serializados, los convertimos a arrays para las columnas
                    if (json.data && Array.isArray(json.data)) {
                        return json.data.map(function(tenant) {
                            // Formato: [id, schema_name, nombre, dominio, admin, created_on, on_trial, estado, vence, acciones]
                            // Badge de estado con diseño moderno
                            const estadoBadge = tenant.is_active 
                                ? '<span class="badge-active inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"><svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>Activo</span>'
                                : '<span class="badge-inactive inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"><svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>Inactivo</span>';
                            
                            // Badge de Trial con diseño moderno
                            const trialBadge = tenant.on_trial 
                                ? '<span class="badge-trial badge-trial-yes inline-flex items-center"><svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path></svg>Trial</span>'
                                : '<span class="badge-trial badge-trial-no inline-flex items-center"><svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>Activo</span>';
                            
                            // Botón de toggle activar/desactivar con iconos
                            const toggleBtn = tenant.is_active
                                ? `<button class="btn-toggle-active inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-semibold rounded-lg text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 shadow-sm transition-all duration-200" data-id="${tenant.id}" data-current-state="${tenant.is_active}" title="Suspender tenant">
                                    <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>
                                    </svg>
                                    Desactivar
                                   </button>`
                                : `<button class="btn-toggle-active inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-semibold rounded-lg text-white bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 shadow-sm transition-all duration-200" data-id="${tenant.id}" data-current-state="${tenant.is_active}" title="Activar tenant">
                                    <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                    </svg>
                                    Activar
                                   </button>`;
                            
                            // Botón de eliminar: solo visible si is_active=False Y no es el tenant público
                            let deleteBtn = '';
                            const isPublicTenant = tenant.schema_name === 'public';
                            
                            if (isPublicTenant) {
                                // PROHIBIDO: Ocultar botón de eliminar para tenant público
                                deleteBtn = `<button class="btn-delete-disabled inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-semibold rounded-lg text-gray-400 bg-gray-50 cursor-not-allowed" disabled title="Prohibido: el esquema público no puede eliminarse">
                                    <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                    </svg>
                                    Eliminar
                                   </button>`;
                            } else if (!tenant.is_active) {
                                deleteBtn = `<button class="btn-delete inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-semibold rounded-lg text-white bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 shadow-sm transition-all duration-200" data-id="${tenant.id}" data-schema="${tenant.schema_name || ''}" title="Eliminar permanentemente (irreversible)">
                                    <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                    </svg>
                                    Eliminar
                                   </button>`;
                            } else {
                                deleteBtn = `<button class="btn-delete-disabled inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-semibold rounded-lg text-gray-400 bg-gray-50 cursor-not-allowed" disabled title="Debes suspender el tenant (is_active=False) antes de eliminarlo">
                                    <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                    </svg>
                                    Eliminar
                                   </button>`;
                            }
                            
                            // Botón de editar con icono
                            const editBtn = `<button class="btn-edit inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-semibold rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 shadow-sm transition-all duration-200" data-id="${tenant.id}" title="Editar tenant">
                                <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                                Editar
                               </button>`;
                            
                            // Formatear fecha de creación
                            const createdDate = tenant.created_on 
                                ? new Date(tenant.created_on).toLocaleDateString('es-ES', { 
                                    year: 'numeric', 
                                    month: 'short', 
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })
                                : '-';
                            
                            // Formatear fecha de vencimiento
                            const paidUntil = tenant.paid_until 
                                ? new Date(tenant.paid_until).toLocaleDateString('es-ES', { 
                                    year: 'numeric', 
                                    month: 'short', 
                                    day: 'numeric'
                                  })
                                : '<span class="text-gray-400">-</span>';
                            
                            // Schema name con estilo de código
                            const schemaDisplay = tenant.schema_name 
                                ? `<code class="text-xs font-mono bg-gray-100 px-2 py-1 rounded text-indigo-700">${tenant.schema_name}</code>`
                                : '-';
                            
                            // Función para construir URL del tenant
                            function buildTenantUrl(domain) {
                                if (!domain) return null;
                                // En dev: http://; en prod podrías detectar window.location.protocol === 'https:' y usar https://
                                const protocol = window.location.protocol === 'https:' ? 'https://' : 'http://';
                                return `${protocol}${domain}/`;
                            }
                            
                            // Renderizar dominio como enlace clicable
                            let domainDisplay = '<span class="text-gray-400 italic">sin dominio</span>';
                            if (tenant.primary_domain) {
                                const tenantUrl = buildTenantUrl(tenant.primary_domain);
                                domainDisplay = `<a href="${tenantUrl}" target="_blank" rel="noopener noreferrer" class="text-indigo-600 hover:text-indigo-800 hover:underline font-medium inline-flex items-center transition-colors duration-200">
                                    <span>${tenant.primary_domain}</span>
                                    <svg class="w-4 h-4 ml-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                    </svg>
                                </a>`;
                            }
                            
                            return [
                                `<span class="font-semibold text-gray-900">#${tenant.id || '-'}</span>`,
                                schemaDisplay,
                                `<span class="font-medium text-gray-900">${tenant.nombre || '-'}</span>`,
                                domainDisplay,  // Dominio con enlace clicable
                                '<span class="text-gray-500">-</span>',  // Admin (se puede agregar si está en serializer)
                                `<span class="text-gray-600">${createdDate}</span>`,
                                trialBadge,
                                estadoBadge,
                                paidUntil,
                                // Botones de acción en contenedor flex
                                `<div class="flex items-center gap-2">${toggleBtn}${editBtn}${deleteBtn}</div>`
                            ];
                        });
                    }
                    return [];
                },
                error: function(xhr, error, thrown) {
                    console.error('DataTables error:', error, thrown);
                    if (xhr.status === 401) {
                        showNotification('Sesión expirada. Por favor, inicia sesión nuevamente.', 'error');
                        setTimeout(() => {
                            window.location.href = '/admin/login/';
                        }, 2000);
                    } else if (xhr.status === 403) {
                        showNotification('No tienes permisos para acceder a esta información.', 'error');
                    }
                }
            },
            columns: [
                { data: 0, title: 'ID', orderable: true, searchable: false, className: 'text-center' },
                { data: 1, title: 'Schema', orderable: true, searchable: true },
                { data: 2, title: 'Empresa', orderable: true, searchable: true },
                { data: 3, title: 'Dominio', orderable: false, searchable: false },
                { data: 4, title: 'Admin', orderable: false, searchable: false },
                { data: 5, title: 'Creado', orderable: true, searchable: false },
                { data: 6, title: 'Trial', orderable: true, searchable: false, className: 'text-center' },
                { data: 7, title: 'Estado', orderable: true, searchable: false, className: 'text-center' },
                { data: 8, title: 'Vence', orderable: true, searchable: false },
                { 
                    data: 9, 
                    title: 'Acciones',
                    orderable: false,
                    searchable: false,
                    className: 'text-center'
                }
            ],
            order: [[5, 'desc']], // Ordenar por fecha de creación descendente
            pageLength: 25,
            lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "Todos"]],
            language: {
                url: 'https://cdn.datatables.net/plug-ins/1.13.8/i18n/es-ES.json',
                processing: '<div class="flex items-center justify-center"><svg class="animate-spin h-5 w-5 text-indigo-600 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Cargando...</div>'
            },
            dom: '<"flex flex-col sm:flex-row justify-between items-center mb-4"<"mb-4 sm:mb-0"l><"mb-4 sm:mb-0"f>>rt<"flex flex-col sm:flex-row justify-between items-center mt-4"<"mb-2 sm:mb-0"i><"mb-2 sm:mb-0"p>>',
            responsive: true,
            stateSave: true
        });

        // Delegación de eventos para botones de acción
        jQuery('#dt-tenants').on('click', '.btn-edit', async function() {
            const tenantId = jQuery(this).data('id');
            if (!tenantId) return;
            
            try {
                // Usar window.http (forma objeto) para obtener datos del tenant
                const tenant = await window.http.get(`/api/public/v1/tenants/${tenantId}/`);
                openEditTenantModal(tenant);
            } catch (err) {
                showNotification(err.message || 'No se pudo cargar el tenant', 'error');
            }
        });

        function openEditTenantModal(tenant) {
            const form = document.getElementById('tenant-form');
            if (!form) {
                showNotification('Formulario de tenant no encontrado en la página', 'error');
                return;
            }

            // Precargar campos editables
            const setVal = (id, value) => {
                const el = document.getElementById(id);
                if (el) el.value = value ?? '';
            };
            
            setVal('nombre', tenant.nombre);
            setVal('paid_until', tenant.paid_until ? tenant.paid_until.split('T')[0] : '');
            
            const onTrial = document.getElementById('on_trial');
            if (onTrial) onTrial.checked = !!tenant.on_trial;
            
            const isActive = document.getElementById('is_active');
            if (isActive) isActive.checked = !!tenant.is_active;

            // Bloquear inmutables
            ['schema_name', 'dominio_fqdn', 'owner_email'].forEach((id) => {
                const el = document.getElementById(id);
                if (el) {
                    el.value = id === 'schema_name' ? tenant.schema_name : (tenant[id] || '');
                    el.readOnly = true;
                    el.disabled = true;
                }
            });

            form.dataset.mode = 'edit';
            form.dataset.tenantId = tenant.id;

            // Cambiar título y botón submit
            const title = document.querySelector('#tenant-modal-title, #tenant-form-title') || document.querySelector('.modal-title');
            if (title) title.textContent = `Editar tenant: ${tenant.nombre}`;
            
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.textContent = 'Guardar cambios';

            // Mostrar el modal/offcanvas (tenants_manager usa Tailwind, el modal suele ser un elemento con IDs específicos)
            // Intentar disparar el trigger si existe, o buscar el contenedor del modal
            const modalEl = document.getElementById('tenant-modal') || document.querySelector('[role="dialog"]');
            // Nota: En la consola actual de Tailwind, el modal suele manejarse vía Alpine.js o clases hidden
            // Intentaremos emitir un evento si es necesario, o simplemente remover 'hidden'
            if (modalEl) {
                modalEl.classList.remove('hidden');
            } else {
                // Si usa Bootstrap (algunas partes de la consola lo mezclan)
                if (typeof bootstrap !== 'undefined') {
                    const inst = bootstrap.Modal.getOrCreateInstance(modalEl) || bootstrap.Offcanvas.getOrCreateInstance(modalEl);
                    if (inst) inst.show();
                }
            }
        }

        // Usar la URL base de la API de tenants para eliminación
        const tenantsApiUrlForDelete = '/api/public/v1/tenants/';
        jQuery('#dt-tenants').on('click', '.btn-delete', function() {
            const tenantId = jQuery(this).data('id');
            const schemaName = jQuery(this).data('schema') || 'N/A';
            
            // Confirmación doble: primero genérica, luego pedir schema_name
            const firstConfirm = confirm(
                '⚠️ ADVERTENCIA: Esta acción es IRREVERSIBLE.\n\n' +
                'Se eliminará permanentemente:\n' +
                '- El esquema PostgreSQL del tenant\n' +
                '- Todos los datos del tenant\n' +
                '- El registro del tenant en la base de datos\n\n' +
                '¿Deseas continuar?'
            );
            
            if (!firstConfirm) {
                return;
            }
            
            // Confirmación doble: pedir schema_name
            const schemaConfirm = prompt(
                `Para confirmar la eliminación, escribe el schema_name del tenant:\n\n` +
                `Schema: ${schemaName}\n\n` +
                `Escribe "${schemaName}" para confirmar:`
            );
            
            if (schemaConfirm !== schemaName) {
                if (schemaConfirm !== null) {  // No fue cancelado
                    showNotification('El schema_name no coincide. Eliminación cancelada.', 'error');
                }
                return;
            }
            
            // Ejecutar eliminación
            deleteTenant(tenantId, tenantsApiUrlForDelete);
        });

        // Toggle activar/desactivar tenant
        // Usar la URL base de la API de tenants, no la URL de DataTables
        const tenantsApiUrl = '/api/public/v1/tenants/';
        jQuery('#dt-tenants').on('click', '.btn-toggle-active', function() {
            const tenantId = jQuery(this).data('id');
            const currentState = jQuery(this).data('current-state');
            const action = currentState ? 'desactivar' : 'activar';
            
            if (confirm(`¿Estás seguro de que deseas ${action} este tenant?`)) {
                toggleTenantActive(tenantId, tenantsApiUrl);
            }
        });

    }

    // ============================================
    // CREACIÓN DE TENANT (Onboarding)
    // ============================================

    function initTenantForm(apiOnboardUrl) {
        const form = document.getElementById('tenant-form');
        if (!form) return;

        // Auto-generar preview de dominio_fqdn desde schema_name (solo para mostrar, no para enviar)
        // ⚠️ v2.25: El backend autogenerará el dominio si no se proporciona
        const schemaNameInput = document.getElementById('schema_name');
        const dominioFqdnInput = document.getElementById('dominio_fqdn');
        if (schemaNameInput && dominioFqdnInput) {
            schemaNameInput.addEventListener('input', function() {
                const schemaValue = this.value.trim().toLowerCase();
                if (schemaValue && !dominioFqdnInput.value.trim()) {
                    // Solo mostrar preview, el usuario puede editarlo o dejarlo vacío para autogeneración
                    const domainBase = window.location.hostname.includes('localhost') ? 'localhost' : 'sintel.com';
                    dominioFqdnInput.placeholder = `${schemaValue}.${domainBase}`;
                }
            });
        }

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            clearFormErrors();

            const nombre = document.getElementById('nombre').value.trim();
            const schemaNameInput = document.getElementById('schema_name').value.trim().toLowerCase();
            const dominioFqdnInput = document.getElementById('dominio_fqdn').value.trim();
            const ownerEmail = document.getElementById('owner_email').value.trim().toLowerCase();
            // ⚠️ v2.29: owner_password ELIMINADO - NO se acepta password en onboarding
            const paidUntil = document.getElementById('paid_until')?.value || null;
            const onTrial = document.getElementById('on_trial')?.checked !== false;

            // Validación básica
            if (!nombre) {
                showFormError('nombre', 'El nombre es requerido');
                return;
            }

            if (!ownerEmail) {
                showFormError('owner_email', 'El email del propietario es requerido');
                return;
            }

            // ⚠️ v2.29: Validación de password ELIMINADA - El owner activará su cuenta vía email

            // Validar schema_name si se proporciona
            let schemaName = null;
            if (schemaNameInput) {
                if (!/^[a-z0-9_]+$/.test(schemaNameInput)) {
                    showFormError('schema_name', 'Solo se permiten letras minúsculas, números y guiones bajos');
                    return;
                }
                if (schemaNameInput === 'public') {
                    showFormError('schema_name', "'public' es un esquema reservado");
                    return;
                }
                schemaName = schemaNameInput;
            }

            // Generar schema_name desde nombre si no se proporciona
            if (!schemaName) {
                schemaName = nombre.toLowerCase()
                    .replace(/[^a-z0-9]/g, '_')
                    .replace(/_+/g, '_')
                    .replace(/^_|_$/g, '')
                    .substring(0, 63);
            }

            // Construir dominio FQDN: usar el proporcionado o dejar vacío para autogeneración (v2.25)
            // ⚠️ v2.25: Si no se proporciona, el backend autogenerará como {schema_name}.{TENANT_DOMAIN_BASE}
            // El serializer espera string vacío o null, no undefined
            let dominioFqdn = dominioFqdnInput || "";

            // Construir payload según el contrato del servicio (v2.29: sin owner_password)
            const formData = {
                nombre: nombre,
                schema_name: schemaName,
                owner_email: ownerEmail,
                // ⚠️ v2.29: owner_password ELIMINADO - NO se acepta password en onboarding
                on_trial: onTrial
            };

            // Agregar campos opcionales solo si tienen valor
            if (dominioFqdn) {
                formData.dominio_fqdn = dominioFqdn;
            }
            if (paidUntil) {
                formData.paid_until = paidUntil;
            }

            const mode = form.dataset.mode || 'create';
            const tenantId = form.dataset.tenantId;
            
            // Recolectar payload
            const formData = {
                nombre: nombre,
                on_trial: onTrial
            };

            if (mode === 'create') {
                formData.schema_name = schemaName;
                formData.owner_email = ownerEmail;
                if (dominioFqdn) formData.dominio_fqdn = dominioFqdn;
            }

            if (paidUntil) {
                formData.paid_until = paidUntil;
            }

            // Deshabilitar botón de envío
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = mode === 'edit' ? 'Guardando...' : 'Creando...';

            try {
                let response;
                if (mode === 'edit' && tenantId) {
                    response = await fetch(`${apiOnboardUrl.replace('onboard/', '')}${tenantId}/`, {
                        method: 'PATCH',
                        headers: getHeaders(),
                        body: JSON.stringify(formData),
                        credentials: 'include'
                    });
                } else {
                    response = await fetch(apiOnboardUrl, {
                        method: 'POST',
                        headers: getHeaders(),
                        body: JSON.stringify(formData),
                        credentials: 'include'
                    });
                }

                const data = await response.json();

                if (!response.ok) {
                    console.error('Tenant action error response:', data);
                    
                    // Manejar errores de validación del serializer (estructura DRF)
                    if (data && typeof data === 'object') {
                        // Si hay errores por campo (estructura DRF estándar)
                        let hasFieldErrors = false;
                        Object.keys(data).forEach(field => {
                            if (field !== 'detail' && field !== 'non_field_errors') {
                                hasFieldErrors = true;
                                const message = Array.isArray(data[field]) 
                                    ? data[field][0] 
                                    : (typeof data[field] === 'string' ? data[field] : JSON.stringify(data[field]));
                                showFormError(field, message);
                            }
                        });
                        
                        // Si hay errores de campo, no mostrar mensaje general
                        if (hasFieldErrors) {
                            // Mostrar también non_field_errors si existen
                            if (data.non_field_errors) {
                                const nonFieldMsg = Array.isArray(data.non_field_errors) 
                                    ? data.non_field_errors[0] 
                                    : data.non_field_errors;
                                showNotification(nonFieldMsg, 'error');
                            }
                        } else {
                            // Mostrar error general (detail o mensaje por defecto)
                            const errorMsg = data.detail || data.message || `Error al ${mode === 'edit' ? 'actualizar' : 'crear'} el tenant`;
                            showNotification(errorMsg, 'error');
                        }
                    } else {
                        // Error en formato no esperado
                        const error = handleAPIError({ response, data });
                        showNotification(error.message || error.detail || `Error al ${mode === 'edit' ? 'actualizar' : 'crear'} el tenant`, 'error');
                    }
                } else {
                    const message = mode === 'edit' 
                        ? `Tenant "${data.nombre}" actualizado correctamente`
                        : (data.login_url 
                            ? `Tenant creado exitosamente. Login URL: ${data.login_url}`
                            : 'Tenant creado exitosamente');
                            
                    showNotification(message, 'success');
                    
                    // Si es edición, solo cerrar y recargar tabla, no redirigir
                    if (mode === 'edit') {
                        const modalEl = document.getElementById('tenant-modal') || document.querySelector('[role="dialog"]');
                        if (modalEl) modalEl.classList.add('hidden');
                        
                        // Recargar tabla DataTables
                        if (typeof jQuery !== 'undefined' && jQuery.fn.dataTable) {
                            jQuery('#dt-tenants').DataTable().ajax.reload(null, false);
                        }
                        
                        // Reset form
                        form.reset();
                        delete form.dataset.mode;
                        delete form.dataset.tenantId;
                        
                        // Restaurar campos bloqueados
                        ['schema_name', 'dominio_fqdn', 'owner_email'].forEach((id) => {
                            const el = document.getElementById(id);
                            if (el) { el.readOnly = false; el.disabled = false; }
                        });
                        if (submitBtn) submitBtn.textContent = 'Crear Empresa';
                    } else {
                        // Redirigir después de un breve delay si es creación
                        setTimeout(() => {
                            window.location.href = '/console/tenants/';
                        }, 2000);
                    }
                }
            } catch (error) {
                const errorInfo = handleAPIError(error);
                showNotification(errorInfo.message, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }

    // ============================================
    // ACTIVAR/DESACTIVAR TENANT
    // ============================================

    async function toggleTenantActive(tenantId, apiUrl) {
        try {
            const response = await fetch(`${apiUrl}${tenantId}/toggle-active/`, {
                method: 'POST',
                headers: getHeaders(),
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                const action = data.is_active ? 'activado' : 'desactivado';
                showNotification(`Tenant ${action} exitosamente`, 'success');
                // Recargar tabla
                if (typeof jQuery !== 'undefined' && jQuery.fn.dataTable) {
                    jQuery('#dt-tenants').DataTable().ajax.reload();
                }
            } else {
                const data = await response.json();
                const error = handleAPIError({ response, data });
                showNotification(error.message, 'error');
            }
        } catch (error) {
            const errorInfo = handleAPIError(error);
            showNotification(errorInfo.message, 'error');
        }
    }

    // ============================================
    // ELIMINACIÓN DE TENANT
    // ============================================

    async function deleteTenant(tenantId, apiUrl) {
        try {
            const response = await fetch(`${apiUrl}${tenantId}/`, {
                method: 'DELETE',
                headers: getHeaders(),
                credentials: 'include'
            });

            if (response.ok || response.status === 204) {
                showNotification('Tenant eliminado permanentemente (esquema y datos)', 'success');
                // Recargar tabla
                if (typeof jQuery !== 'undefined' && jQuery.fn.dataTable) {
                    jQuery('#dt-tenants').DataTable().ajax.reload();
                }
            } else {
                const data = await response.json().catch(() => ({}));
                const error = handleAPIError({ response, data });
                
                // Mensaje específico para tenant activo
                if (response.status === 400 && (data.error || '').includes('is_active')) {
                    showNotification(
                        '⚠️ El tenant debe estar suspendido antes de eliminarlo. ' +
                        'Primero desactiva el tenant usando el botón "Desactivar".',
                        'error'
                    );
                } else {
                    showNotification(error.message || 'Error al eliminar el tenant', 'error');
                }
            }
        } catch (error) {
            const errorInfo = handleAPIError(error);
            showNotification(errorInfo.message, 'error');
        }
    }


    // ============================================
    // INICIALIZACIÓN
    // ============================================

    // Exportar funciones globales
    window.TenantsManager = {
        initTable: initTenantsTable,
        initForm: initTenantForm,
        deleteTenant: deleteTenant,
        toggleActive: toggleTenantActive
    };

    // Auto-inicializar si hay elementos en la página
    document.addEventListener('DOMContentLoaded', function() {
        // Inicializar tabla si existe
        const table = document.getElementById('dt-tenants');
        if (table) {
            const apiUrl = table.dataset.apiUrl || '/api/public/v1/tenants/';
            initTenantsTable(apiUrl);
        }

        // Inicializar formulario si existe
        const form = document.getElementById('tenant-form');
        if (form) {
            const apiOnboardUrl = form.dataset.apiOnboardUrl || '/api/public/v1/tenants/onboard/';
            initTenantForm(apiOnboardUrl);
        }
    });

})();
