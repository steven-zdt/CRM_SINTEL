/**
 * Gestión de Usuarios (API-First)
 * 
 * Maneja el CRUD completo de usuarios globales desde la UI,
 * consumiendo endpoints REST de /api/admin/v1/accounts/users/
 * 
 * Patrón: API-First, Service Layer, Cero Signals
 * 
 * ⚠️ SEGURIDAD: Este módulo solo debe cargarse en el dominio público (localhost).
 */

(function() {
    'use strict';
    
    // Verificación de hostname: la consola solo debe cargarse en el dominio público
    const hostname = window.location.hostname;
    const isPublicHost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'sintel.net.co';
    
    if (!isPublicHost) {
        // Hard stop: abortar si se carga en un dominio de tenant
        console.error('❌ ERROR DE SEGURIDAD: Users Manager no debe cargarse en dominios de tenant.');
        console.error(`Hostname detectado: ${hostname}`);
        throw new Error('Users Manager: Hard stop - cargado en dominio de tenant');
    }

    // ============================================
    // CONFIGURACIÓN Y HELPERS
    // ============================================

    const API_DT_URL = '/api/admin/v1/console/dt/users/';

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

    function getHeaders(includeJson = true) {
        const headers = {
            'X-CSRFToken': getCookie('csrftoken'),
        };
        if (includeJson) {
            headers['Content-Type'] = 'application/json';
        }
        return headers;
    }

    function showNotification(message, type = 'info') {
        const container = document.getElementById('messages-container');
        if (!container) return;

        const alertClass = {
            'success': 'bg-green-50 text-green-800 border-green-400',
            'error': 'bg-red-50 text-red-800 border-red-400',
            'info': 'bg-blue-50 text-blue-800 border-blue-400',
        }[type] || alertClass.info;

        const icon = {
            'success': '<svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
            'error': '<svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
            'info': '<svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>',
        }[type] || icon.info;

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

    function clearFormErrors() {
        document.querySelectorAll('[id^="error-"]').forEach(el => {
            el.classList.add('hidden');
            el.textContent = '';
        });
        const formErrors = document.getElementById('form-errors');
        if (formErrors) {
            formErrors.classList.add('hidden');
            formErrors.textContent = '';
        }
    }

    function showFormError(fieldId, message) {
        const errorEl = document.getElementById(`error-${fieldId}`);
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }
    }

    function handleAPIError({ response, data }) {
        if (!response) {
            return { message: 'Error de conexión', type: 'error' };
        }

        if (response.status === 401) {
            return { message: 'Sesión expirada. Por favor, inicia sesión nuevamente.', type: 'error' };
        }

        if (response.status === 403) {
            return { message: 'No tienes permisos para realizar esta acción.', type: 'error' };
        }

        if (response.status === 400 && data) {
            if (data.error) {
                return { message: data.error, type: 'error' };
            }
            if (data.detail) {
                return { message: data.detail, type: 'error' };
            }
            // Errores de validación por campo
            if (typeof data === 'object') {
                const errors = Object.entries(data)
                    .map(([field, messages]) => {
                        const msg = Array.isArray(messages) ? messages[0] : messages;
                        return `${field}: ${msg}`;
                    })
                    .join(', ');
                return { message: errors || 'Error de validación', type: 'validation', errors: data };
            }
        }

        return { message: data?.error || data?.detail || 'Error desconocido', type: 'error' };
    }

    // ============================================
    // DATATABLES: LISTADO DE USUARIOS
    // ============================================

    function initUsersTable() {
        if (typeof jQuery === 'undefined' || typeof jQuery.fn.dataTable === 'undefined') {
            console.error('DataTables no está disponible');
            return;
        }

        const apiUrl = document.getElementById('dt-users')?.dataset.apiUrl || API_DT_URL;

        jQuery('#dt-users').DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: apiUrl,
                type: 'POST',
                headers: getHeaders(),
                contentType: 'application/json',
                xhrFields: {
                    withCredentials: true  // Enviar cookies de sesión
                },
                data: function(d) {
                    return JSON.stringify({
                        draw: d.draw,
                        start: d.start,
                        length: d.length,
                        search: { value: d.search.value || '' },
                        order: d.order.map(function(o) {
                            return { column: o.column, dir: o.dir };
                        }),
                        columns: d.columns.map(function(c) {
                            return {
                                data: c.data,
                                name: c.name || '',
                                searchable: c.searchable !== false,
                                orderable: c.orderable !== false,
                                search: { value: c.search.value || '', regex: c.search.regex || false }
                            };
                        })
                    });
                },
                dataSrc: function(json) {
                    if (json.data && Array.isArray(json.data)) {
                        return json.data.map(function(user) {
                            // Badges
                            const activeBadge = user.is_active
                                ? '<span class="badge-active inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold">Activo</span>'
                                : '<span class="badge-inactive inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold">Inactivo</span>';

                            const tipoBadge = user.tipo_usuario === 'SYSTEM_ADMIN'
                                ? '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-800 border border-red-200">&#9679; Sistema</span>'
                                : user.tipo_usuario === 'TENANT_OWNER'
                                    ? '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">&#9679; Owner</span>'
                                    : '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">?</span>';

                            const staffBadge = tipoBadge;

                            // Columna Tenants asignados — muestra URL del dominio
                            const tenants = Array.isArray(user.tenants) ? user.tenants : [];
                            let tenantsHtml;
                            if (tenants.length === 0) {
                                tenantsHtml = '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200">Sin tenant</span>';
                            } else {
                                tenantsHtml = tenants.map(function(t) {
                                    const rolColor = t.is_primary_admin
                                        ? 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100'
                                        : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100';
                                    const star = t.is_primary_admin ? '<svg class="w-3 h-3 ml-1 text-indigo-400" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>' : '';
                                    const url = t.domain_url || '';
                                    const label = url || t.schema_name;
                                    return `<a href="${url}" target="_blank" rel="noopener"
                                        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium ${rolColor} border mr-1 mb-0.5 transition-colors"
                                        title="${t.nombre} (${t.rol})">${label}${star}</a>`;
                                }).join('');
                            }

                            // Botones
                            const editBtn = `<button class="btn-edit inline-flex items-center px-2.5 py-1 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 shadow-sm transition-all" data-id="${user.id}" title="Editar">
                                <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                                Editar</button>`;

                            const assignBtn = `<button class="btn-assign inline-flex items-center px-2.5 py-1 border border-indigo-300 text-xs font-medium rounded-md text-indigo-700 bg-indigo-50 hover:bg-indigo-100 shadow-sm transition-all" data-id="${user.id}" data-email="${user.email}" title="Asignar a tenant">
                                <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>
                                Asignar</button>`;

                            const deleteBtn = `<button class="btn-delete inline-flex items-center px-2.5 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-red-600 hover:bg-red-700 shadow-sm transition-all" data-id="${user.id}" title="Eliminar">
                                <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                Eliminar</button>`;

                            return [
                                `<span class="font-semibold text-gray-900">#${user.id || '-'}</span>`,
                                `<span class="font-medium text-gray-900">${user.email || '-'}</span>`,
                                `<span class="text-gray-600">${(user.first_name || '') + ' ' + (user.last_name || '')}</span>`,
                                activeBadge,
                                staffBadge,
                                `<div class="flex flex-wrap gap-0.5">${tenantsHtml}</div>`,
                                `<div class="flex items-center gap-1">${editBtn}${assignBtn}${deleteBtn}</div>`
                            ];
                        });
                    }
                    return [];
                },
                error: function(xhr, error, thrown) {
                    console.error('DataTables error:', error, thrown);
                    const errorInfo = handleAPIError({ response: xhr, data: xhr.responseJSON });
                    showNotification(errorInfo.message, 'error');
                }
            },
            columns: [
                { data: 0, title: 'ID', orderable: true, searchable: false, width: '50px' },
                { data: 1, title: 'Email', orderable: true, searchable: true },
                { data: 2, title: 'Nombre', orderable: true, searchable: true },
                { data: 3, title: 'Activo', orderable: false, searchable: false, width: '80px', className: 'text-center' },
                { data: 4, title: 'Staff', orderable: false, searchable: false, width: '70px', className: 'text-center' },
                { data: 5, title: 'Tenants asignados', orderable: false, searchable: false },
                { data: 6, title: 'Acciones', orderable: false, searchable: false, width: '200px' }
            ],
            order: [[0, 'desc']],
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
        jQuery('#dt-users').on('click', '.btn-edit', function() {
            const userId = jQuery(this).data('id');
            openEditModal(userId);
        });

        jQuery('#dt-users').on('click', '.btn-delete', function() {
            const userId = jQuery(this).data('id');
            if (confirm('¿Estás seguro de que deseas eliminar este usuario? Esta acción no se puede deshacer.')) {
                deleteUser(userId);
            }
        });

        jQuery('#dt-users').on('click', '.btn-assign', function() {
            const userId = jQuery(this).data('id');
            const userEmail = jQuery(this).data('email');
            openAssignTenantModal(userId, userEmail);
        });
    }

    // ============================================
    // MODAL: ASIGNAR TENANT HUERFANO
    // ============================================

    let _assignUserId = null;
    let _allOrphanTenants = [];

    async function openAssignTenantModal(userId, userEmail) {
        _assignUserId = userId;
        const modal = document.getElementById('assign-tenant-modal');
        const label = document.getElementById('assign-user-label');
        const feedback = document.getElementById('assign-feedback');
        const searchInput = document.getElementById('assign-search');
        const listEl = document.getElementById('assign-tenant-list');

        if (label) label.textContent = `Usuario: ${userEmail}`;
        if (feedback) { feedback.classList.add('hidden'); feedback.textContent = ''; }
        if (searchInput) searchInput.value = '';

        modal.classList.remove('hidden');

        // Cargar tenants huerfanos
        const table = document.getElementById('dt-users');
        const orphanUrl = table ? table.dataset.orphanApi : '/api/admin/v1/console/orphan-tenants/';

        listEl.innerHTML = '<div class="text-center text-gray-400 text-sm py-6">Cargando tenants sin administrador...</div>';

        try {
            const resp = await fetch(orphanUrl, { headers: getHeaders(false), credentials: 'include' });
            const data = await resp.json();
            _allOrphanTenants = data.results || [];
            renderOrphanTenantList(_allOrphanTenants);
        } catch (e) {
            listEl.innerHTML = '<div class="text-center text-red-400 text-sm py-6">Error al cargar tenants.</div>';
        }
    }

    function renderOrphanTenantList(tenants) {
        const listEl = document.getElementById('assign-tenant-list');
        if (!tenants.length) {
            listEl.innerHTML = '<div class="text-center text-gray-400 text-sm py-6">Todos los tenants ya tienen administrador asignado.</div>';
            return;
        }
        listEl.innerHTML = tenants.map(function(t) {
            return `<button class="btn-orphan-select w-full text-left px-4 py-3 hover:bg-indigo-50 transition-colors flex items-center justify-between"
                            data-tenant-id="${t.id}" data-tenant-nombre="${t.nombre}">
                <div>
                    <div class="text-sm font-semibold text-gray-900">${t.nombre}</div>
                    <div class="text-xs text-gray-500">${t.schema_name}${t.primary_domain ? ' &bull; ' + t.primary_domain : ''}</div>
                </div>
                <svg class="w-4 h-4 text-indigo-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                </svg>
            </button>`;
        }).join('');

        listEl.querySelectorAll('.btn-orphan-select').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const tenantId = this.dataset.tenantId;
                const tenantNombre = this.dataset.tenantNombre;
                assignTenantToUser(tenantId, tenantNombre);
            });
        });
    }

    async function assignTenantToUser(tenantId, tenantNombre) {
        const feedback = document.getElementById('assign-feedback');
        const isPrimary = document.getElementById('assign-primary')?.checked !== false;
        const table = document.getElementById('dt-users');
        const assignUrl = `${table.dataset.assignApi || '/api/admin/v1/console/dt/users/'}${_assignUserId}/assign-tenant/`;

        feedback.classList.add('hidden');

        try {
            const resp = await fetch(assignUrl, {
                method: 'POST',
                headers: getHeaders(),
                credentials: 'include',
                body: JSON.stringify({ tenant_id: tenantId, rol: 'ADMIN', is_primary_admin: isPrimary })
            });
            const data = await resp.json();

            if (resp.ok) {
                feedback.className = 'mt-3 text-sm rounded-lg px-3 py-2 bg-green-50 text-green-800 border border-green-200';
                feedback.textContent = `Usuario asignado a "${tenantNombre}" como Administrador.`;
                feedback.classList.remove('hidden');
                // Actualizar tabla y cerrar modal tras 1.5s
                setTimeout(function() {
                    document.getElementById('assign-tenant-modal').classList.add('hidden');
                    if (typeof jQuery !== 'undefined' && jQuery.fn.dataTable) {
                        jQuery('#dt-users').DataTable().ajax.reload();
                    }
                }, 1500);
            } else {
                feedback.className = 'mt-3 text-sm rounded-lg px-3 py-2 bg-red-50 text-red-800 border border-red-200';
                feedback.textContent = data.error || 'Error al asignar el tenant.';
                feedback.classList.remove('hidden');
            }
        } catch (e) {
            feedback.className = 'mt-3 text-sm rounded-lg px-3 py-2 bg-red-50 text-red-800 border border-red-200';
            feedback.textContent = 'Error de red. Intenta nuevamente.';
            feedback.classList.remove('hidden');
        }
    }

    // ============================================
    // MODAL: CREAR/EDITAR USUARIO
    // ============================================

    function openNewModal() {
        document.getElementById('user-id').value = '';
        document.getElementById('modal-title').textContent = 'Nuevo Usuario';
        document.getElementById('password-required').classList.remove('hidden');
        // Asegurar que password y password2 sean requeridos en creación
        document.getElementById('password').required = true;
        document.getElementById('password2').required = true;
        // Asegurar que password2 esté visible
        const password2Div = document.getElementById('password2').parentElement;
        if (password2Div) {
            password2Div.classList.remove('hidden');
        }
        document.getElementById('user-form').reset();
        document.getElementById('is_active').checked = true;
        document.getElementById('email').disabled = false; // Habilitar email en creación
        clearFormErrors();
        document.getElementById('user-modal').classList.remove('hidden');
    }

    async function openEditModal(userId) {
        try {
            const response = await fetch(`${API_DT_URL}${userId}/`, {
                method: 'GET',
                headers: getHeaders(false),
                credentials: 'include'
            });

            if (!response.ok) {
                const errorInfo = handleAPIError({ response, data: await response.json().catch(() => ({})) });
                showNotification(errorInfo.message, 'error');
                return;
            }

            const user = await response.json();
            
            // Llenar formulario
            document.getElementById('user-id').value = user.id;
            document.getElementById('email').value = user.email || '';
            document.getElementById('email').disabled = true; // No permitir cambiar email
            document.getElementById('password').value = '';
            document.getElementById('password2').value = '';
            document.getElementById('password').required = false;
            document.getElementById('password2').required = false;
            document.getElementById('password-required').classList.add('hidden');
            document.getElementById('password2').parentElement.classList.remove('hidden'); // Mostrar campo de confirmación
            document.getElementById('first_name').value = user.first_name || '';
            document.getElementById('last_name').value = user.last_name || '';
            document.getElementById('telefono').value = user.telefono || '';
            document.getElementById('is_staff').checked = user.is_staff || false;
            document.getElementById('is_active').checked = user.is_active !== false;

            document.getElementById('modal-title').textContent = 'Editar Usuario';
            clearFormErrors();
            document.getElementById('user-modal').classList.remove('hidden');
        } catch (error) {
            const errorInfo = handleAPIError(error);
            showNotification(errorInfo.message, 'error');
        }
    }

    function closeModal() {
        document.getElementById('user-modal').classList.add('hidden');
        document.getElementById('email').disabled = false;
        document.getElementById('user-form').reset();
        // Restaurar requeridos para password y password2
        document.getElementById('password').required = true;
        document.getElementById('password2').required = true;
        clearFormErrors();
    }

    // ============================================
    // CRUD: CREAR/ACTUALIZAR USUARIO
    // ============================================

    async function saveUser(formData) {
        const userId = formData.get('id');
        const isEdit = !!userId;

        const payload = {
            email: formData.get('email'),
            first_name: formData.get('first_name') || '',
            last_name: formData.get('last_name') || '',
            telefono: formData.get('telefono') || null,
            is_staff: formData.get('is_staff') === 'on',
            is_active: formData.get('is_active') === 'on',
        };

        // Password solo para crear o si se proporciona en edición
        const password = formData.get('password');
        const password2 = formData.get('password2');
        
        if (!isEdit) {
            // Crear: password y password2 son obligatorios
            if (!password || password.length < 8) {
                showFormError('password', 'La contraseña debe tener al menos 8 caracteres');
                return;
            }
            if (!password2) {
                showFormError('password2', 'Debes confirmar la contraseña');
                return;
            }
            if (password !== password2) {
                showFormError('password2', 'Las contraseñas no coinciden');
                return;
            }
            payload.password = password;
            payload.password2 = password2;
        } else if (password) {
            // Editar: si se proporciona password, también debe proporcionarse password2
            if (!password2) {
                showFormError('password2', 'Debes confirmar la contraseña');
                return;
            }
            if (password !== password2) {
                showFormError('password2', 'Las contraseñas no coinciden');
                return;
            }
            if (password.length < 8) {
                showFormError('password', 'La contraseña debe tener al menos 8 caracteres');
                return;
            }
            payload.password = password;
            payload.password2 = password2;
        }

        const url = isEdit ? `${API_DT_URL}${userId}/` : API_DT_URL;
        const method = isEdit ? 'PATCH' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: getHeaders(),
                body: JSON.stringify(payload),
                credentials: 'include'  // Enviar cookies de sesión
            });

            const data = await response.json();

            if (!response.ok) {
                const errorInfo = handleAPIError({ response, data });
                
                if (errorInfo.type === 'validation' && errorInfo.errors) {
                    Object.keys(errorInfo.errors).forEach(field => {
                        const message = Array.isArray(errorInfo.errors[field]) 
                            ? errorInfo.errors[field][0] 
                            : errorInfo.errors[field];
                        showFormError(field, message);
                    });
                } else {
                    showNotification(errorInfo.message, 'error');
                }
                return;
            }

            showNotification(
                isEdit ? 'Usuario actualizado exitosamente' : 'Usuario creado exitosamente',
                'success'
            );
            closeModal();
            
            // Recargar tabla
            if (typeof jQuery !== 'undefined' && jQuery.fn.dataTable) {
                jQuery('#dt-users').DataTable().ajax.reload();
            }
        } catch (error) {
            const errorInfo = handleAPIError(error);
            showNotification(errorInfo.message, 'error');
        }
    }

    async function deleteUser(userId) {
        try {
            const response = await fetch(`${API_DT_URL}${userId}/`, {
                method: 'DELETE',
                headers: getHeaders(false),
                credentials: 'include'
            });

            if (response.ok || response.status === 204) {
                showNotification('Usuario eliminado exitosamente', 'success');
                if (typeof jQuery !== 'undefined' && jQuery.fn.dataTable) {
                    jQuery('#dt-users').DataTable().ajax.reload();
                }
            } else {
                const data = await response.json().catch(() => ({}));
                const errorInfo = handleAPIError({ response, data });
                showNotification(errorInfo.message, 'error');
            }
        } catch (error) {
            const errorInfo = handleAPIError(error);
            showNotification(errorInfo.message, 'error');
        }
    }

    // ============================================
    // INICIALIZACIÓN
    // ============================================

    document.addEventListener('DOMContentLoaded', function() {
        // Inicializar tabla
        initUsersTable();

        // Botón nuevo usuario
        const btnNew = document.getElementById('btn-new-user');
        if (btnNew) {
            btnNew.addEventListener('click', openNewModal);
        }

        // Modal: cerrar
        const modal = document.getElementById('user-modal');
        const btnClose = document.getElementById('modal-close');
        const btnCancel = document.getElementById('btn-cancel');
        
        if (btnClose) {
            btnClose.addEventListener('click', closeModal);
        }
        if (btnCancel) {
            btnCancel.addEventListener('click', closeModal);
        }
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    closeModal();
                }
            });
        }

        // Modal asignacion de tenant: cerrar
        const assignModal = document.getElementById('assign-tenant-modal');
        const assignClose = document.getElementById('assign-modal-close');
        const assignBackdrop = document.getElementById('assign-backdrop');

        if (assignClose) assignClose.addEventListener('click', function() {
            if (assignModal) assignModal.classList.add('hidden');
        });
        if (assignBackdrop) assignBackdrop.addEventListener('click', function() {
            if (assignModal) assignModal.classList.add('hidden');
        });

        // Filtrar lista de tenants en el modal
        const assignSearch = document.getElementById('assign-search');
        if (assignSearch) {
            assignSearch.addEventListener('input', function() {
                const q = this.value.trim().toLowerCase();
                const filtered = q
                    ? _allOrphanTenants.filter(function(t) {
                        return t.nombre.toLowerCase().includes(q) || t.schema_name.toLowerCase().includes(q);
                      })
                    : _allOrphanTenants;
                renderOrphanTenantList(filtered);
            });
        }

        // Formulario: submit
        const form = document.getElementById('user-form');
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                clearFormErrors();
                
                const formData = new FormData(form);
                const userId = formData.get('id');
                const isEdit = !!userId;

                // Validación básica
                if (!formData.get('email')) {
                    showFormError('email', 'El email es requerido');
                    return;
                }

                if (!isEdit) {
                    // Crear: validar password y password2
                    if (!formData.get('password')) {
                        showFormError('password', 'La contraseña es requerida');
                        return;
                    }
                    if (!formData.get('password2')) {
                        showFormError('password2', 'Debes confirmar la contraseña');
                        return;
                    }
                    if (formData.get('password') !== formData.get('password2')) {
                        showFormError('password2', 'Las contraseñas no coinciden');
                        return;
                    }
                }

                // Deshabilitar botón durante el envío
                const submitBtn = document.getElementById('btn-submit');
                const originalText = submitBtn.textContent;
                submitBtn.disabled = true;
                submitBtn.textContent = 'Guardando...';

                saveUser(formData).finally(() => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                });
            });
        }
    });

})();
