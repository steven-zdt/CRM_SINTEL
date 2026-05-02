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
    const isPublicHost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'sintel.com';
    
    if (!isPublicHost) {
        // Hard stop: abortar si se carga en un dominio de tenant
        console.error('❌ ERROR DE SEGURIDAD: Users Manager no debe cargarse en dominios de tenant.');
        console.error(`Hostname detectado: ${hostname}`);
        throw new Error('Users Manager: Hard stop - cargado en dominio de tenant');
    }

    // ============================================
    // CONFIGURACIÓN Y HELPERS
    // ============================================

    const API_BASE_URL = '/api/admin/v1/accounts/users/';
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
                            // Badges de estado
                            const activeBadge = user.is_active 
                                ? '<span class="badge-active inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"><svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>Activo</span>'
                                : '<span class="badge-inactive inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"><svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>Inactivo</span>';

                            const staffBadge = user.is_staff
                                ? '<span class="badge-staff inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"><svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>Staff</span>'
                                : '<span class="text-gray-400">-</span>';

                            // Fecha formateada
                            const createdDate = user.date_joined 
                                ? new Date(user.date_joined).toLocaleDateString('es-ES', { 
                                    year: 'numeric', 
                                    month: 'short', 
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })
                                : '-';

                            // Botones de acción
                            const editBtn = `<button class="btn-edit inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-semibold rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 shadow-sm transition-all duration-200" data-id="${user.id}" title="Editar usuario">
                                <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                                Editar
                               </button>`;

                            const deleteBtn = `<button class="btn-delete inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-semibold rounded-lg text-white bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 shadow-sm transition-all duration-200" data-id="${user.id}" title="Eliminar usuario">
                                <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                                Eliminar
                               </button>`;

                            return [
                                `<span class="font-semibold text-gray-900">#${user.id || '-'}</span>`,
                                `<span class="font-medium text-gray-900">${user.email || '-'}</span>`,
                                `<span class="text-gray-600">${user.first_name || '-'}</span>`,
                                `<span class="text-gray-600">${user.last_name || '-'}</span>`,
                                activeBadge,
                                staffBadge,
                                `<span class="text-gray-600">${createdDate}</span>`,
                                `<div class="flex items-center gap-2">${editBtn}${deleteBtn}</div>`
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
                { data: 0, title: 'ID', orderable: true, searchable: false, className: 'text-center' },
                { data: 1, title: 'Email', orderable: true, searchable: true },
                { data: 2, title: 'Nombre', orderable: true, searchable: true },
                { data: 3, title: 'Apellido', orderable: true, searchable: true },
                { data: 4, title: 'Activo', orderable: true, searchable: false, className: 'text-center' },
                { data: 5, title: 'Staff', orderable: true, searchable: false, className: 'text-center' },
                { data: 6, title: 'Creado', orderable: true, searchable: false },
                { 
                    data: 7, 
                    title: 'Acciones',
                    orderable: false,
                    searchable: false,
                    className: 'text-center'
                }
            ],
            order: [[6, 'desc']],
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
            const response = await fetch(`${API_BASE_URL}${userId}/`, {
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

        const url = isEdit ? `${API_BASE_URL}${userId}/` : API_BASE_URL;
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
            const response = await fetch(`${API_BASE_URL}${userId}/`, {
                method: 'DELETE',
                headers: getHeaders(false),
                credentials: 'include'  // Enviar cookies de sesión
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
