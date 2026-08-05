/**
 * Console API Client
 * 
 * Cliente JavaScript para consumir las APIs REST de la consola.
 * Sigue el principio API-First: toda la lógica de datos viene del backend.
 * 
 * ⚠️ SEGURIDAD: Esta consola solo debe cargarse en el dominio público (localhost).
 * Si se detecta que se está cargando en un dominio de tenant, se aborta la ejecución.
 */

// Verificación de hostname: la consola solo debe cargarse en el dominio público
(function() {
    'use strict';
    const hostname = window.location.hostname;
    const isPublicHost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'sintel.net.co' || hostname === '192.168.2.15';
    
    if (!isPublicHost) {
        // Hard stop: abortar si se carga en un dominio de tenant
        console.error('❌ ERROR DE SEGURIDAD: La consola pública no debe cargarse en dominios de tenant.');
        console.error(`Hostname detectado: ${hostname}`);
        console.error('La consola solo está disponible en el dominio público (localhost).');
        
        // Mostrar mensaje de error en la página
        document.addEventListener('DOMContentLoaded', function() {
            const body = document.body;
            if (body) {
                body.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #f3f4f6; font-family: system-ui, -apple-system, sans-serif;">
                        <div style="text-align: center; padding: 2rem; background: white; border-radius: 0.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 600px;">
                            <h1 style="color: #dc2626; font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;">⚠️ Error de Seguridad</h1>
                            <p style="color: #374151; margin-bottom: 0.5rem;">La consola de administración solo está disponible en el dominio público.</p>
                            <p style="color: #6b7280; font-size: 0.875rem; margin-bottom: 1.5rem;">Hostname detectado: <code style="background: #f3f4f6; padding: 0.25rem 0.5rem; border-radius: 0.25rem;">${hostname}</code></p>
                            <p style="color: #6b7280; font-size: 0.875rem;">Por favor, accede a la consola desde <code style="background: #f3f4f6; padding: 0.25rem 0.5rem; border-radius: 0.25rem;">localhost</code> o el dominio público configurado.</p>
                        </div>
                    </div>
                `;
            }
        });
        
        // Abortar ejecución del resto del código
        throw new Error('Console API: Hard stop - consola cargada en dominio de tenant');
    }
})();

const consoleAPI = {
    /**
     * Obtiene el token CSRF desde el meta tag.
     */
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    },

    /**
     * Realiza una petición fetch con autenticación JWT y CSRF.
     */
    async fetchAPI(url, options = {}) {
        const defaultOptions = {
            credentials: 'include', // Incluir cookies (sesión)
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
            },
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...(options.headers || {}),
            },
        };

        // Inyectar header de Authorization JWT
        try {
            mergedOptions.headers = await jwtAuth.injectAuthHeader(mergedOptions.headers);
        } catch (error) {
            // Si no hay token disponible, intentar obtenerlo desde la sesión
            console.warn('No hay JWT token disponible, intentando obtener desde sesión...');
            try {
                const response = await fetch('/console/jwt/from-session/', {
                    method: 'GET',
                    credentials: 'include',
                });
                
                if (response.ok) {
                    const { access, refresh } = await response.json();
                    jwtAuth.setTokens(access, refresh);
                    mergedOptions.headers = await jwtAuth.injectAuthHeader(mergedOptions.headers);
                } else {
                    throw new Error('No se pudo obtener JWT desde sesión');
                }
            } catch (sessionError) {
                console.error('Error obteniendo JWT desde sesión:', sessionError);
                throw new Error('Las credenciales de autenticación no se proveyeron. Por favor, inicia sesión.');
            }
        }

        try {
            const response = await fetch(url, mergedOptions);
            
            if (!response.ok) {
                // Si es 401, intentar refrescar el token y reintentar
                if (response.status === 401) {
                    try {
                        const newAccess = await jwtAuth.refresh();
                        mergedOptions.headers['Authorization'] = `Bearer ${newAccess}`;
                        const retryResponse = await fetch(url, mergedOptions);
                        
                        if (!retryResponse.ok) {
                            const error = await retryResponse.json().catch(() => ({ detail: 'Error desconocido' }));
                            throw new Error(error.detail || error.message || `HTTP ${retryResponse.status}`);
                        }
                        
                        return await retryResponse.json();
                    } catch (refreshError) {
                        console.error('Error refrescando token:', refreshError);
                        throw new Error('Las credenciales de autenticación expiraron. Por favor, recarga la página.');
                    }
                } else {
                    const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
                    throw new Error(error.detail || error.message || `HTTP ${response.status}`);
                }
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error en fetchAPI:', error);
            throw error;
        }
    },

    /**
     * Carga métricas del dashboard.
     */
    async loadDashboardMetrics() {
        try {
            // Cargar datos de tenants
            const tenantsData = await this.fetchAPI('/api/public/v1/tenants/');
            document.getElementById('metric-total-tenants').textContent = tenantsData.count || 0;
            
            // Contar activos (no en trial)
            const activeCount = tenantsData.results?.filter(t => !t.on_trial).length || 0;
            document.getElementById('metric-active-tenants').textContent = activeCount;
            
            // Contar en prueba
            const trialCount = tenantsData.results?.filter(t => t.on_trial).length || 0;
            document.getElementById('metric-trial-tenants').textContent = trialCount;
            
            // Cargar datos de usuarios
            const usersData = await this.fetchAPI('/api/public/v1/users/');
            document.getElementById('metric-total-users').textContent = usersData.count || 0;
        } catch (error) {
            console.error('Error cargando métricas:', error);
        }
    },

    /**
     * Carga la lista de tenants (empresas).
     */
    async loadTenants(search = '', trial = '', page = 1) {
        try {
            const params = new URLSearchParams({ page });
            if (search) params.append('search', search);
            if (trial) params.append('on_trial', trial);
            
            const data = await this.fetchAPI(`/api/public/v1/tenants/?${params}`);
            this.renderTenantsTable(data);
            this.renderPagination('tenants-pagination', data, (p) => this.loadTenants(search, trial, p));
        } catch (error) {
            document.getElementById('tenants-table-body').innerHTML = 
                `<tr><td colspan="6" class="px-6 py-4 text-center text-red-500">Error: ${error.message}</td></tr>`;
        }
    },

    /**
     * Renderiza la tabla de tenants.
     */
    renderTenantsTable(data) {
        const tbody = document.getElementById('tenants-table-body');
        
        if (!data.results || data.results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-gray-500">No hay empresas</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.results.map(tenant => `
            <tr>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${tenant.nombre}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${tenant.schema_name}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${tenant.domains?.[0]?.domain || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${tenant.on_trial ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}">
                        ${tenant.on_trial ? 'En Prueba' : 'Pagado'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${new Date(tenant.created_on).toLocaleDateString('es-CO')}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <a href="/admin/tenants/client/${tenant.id}/change/" class="text-indigo-600 hover:text-indigo-900">Editar</a>
                </td>
            </tr>
        `).join('');
    },

    /**
     * Crea un nuevo tenant usando el servicio de onboarding.
     * 
     * ⚠️ v2.17: Estandarización de subdominios
     * - Ya no se requiere el parámetro 'dominio' - se construye automáticamente como {schema_name}.{TENANT_DOMAIN_BASE}
     * - El dominio se crea automáticamente por la señal post_save
     * 
     * Usa el endpoint POST /api/public/v1/tenants/create/ que internamente
     * llama a apps.services.onboarding.empresa_service.crear_empresa()
     * siguiendo el principio de Service Layer Pattern.
     */
    async createTenant(nombre, email, schemaName = null) {
        const body = {
            nombre,
            email_admin: email,
        };
        
        // Agregar schema_name solo si se proporciona (opcional)
        if (schemaName) {
            body.schema_name = schemaName;
        }
        
        const response = await this.fetchAPI('/api/public/v1/tenants/create/', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        
        return response;
    },

    /**
     * Carga la lista de usuarios.
     */
    async loadUsers(search = '', active = '', page = 1) {
        try {
            const params = new URLSearchParams({ page });
            if (search) params.append('search', search);
            if (active) params.append('is_active', active);
            
            const data = await this.fetchAPI(`/api/public/v1/users/?${params}`);
            this.renderUsersTable(data);
            this.renderPagination('users-pagination', data, (p) => this.loadUsers(search, active, p));
        } catch (error) {
            document.getElementById('users-table-body').innerHTML = 
                `<tr><td colspan="5" class="px-6 py-4 text-center text-red-500">Error: ${error.message}</td></tr>`;
        }
    },

    /**
     * Renderiza la tabla de usuarios.
     */
    renderUsersTable(data) {
        const tbody = document.getElementById('users-table-body');
        
        if (!data.results || data.results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-4 text-center text-gray-500">No hay usuarios</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.results.map(user => `
            <tr>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${user.email}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.username}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${user.is_staff ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}">
                        ${user.is_staff ? 'Sí' : 'No'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                        ${user.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${new Date(user.date_joined).toLocaleDateString('es-CO')}</td>
            </tr>
        `).join('');
    },

    /**
     * Carga el catálogo de impuestos DIAN.
     * 
     * ⚠️ IMPORTANTE: Los endpoints de impuestos están en /api/public/v1/impuestos/...
     * porque están registrados en config/public_api_urls.py para estar disponibles solo en esquema public.
     * 
     * ⚠️ POLÍTICA SSoT: apps/public/impuestos es la única fuente de verdad para normativa DIAN.
     */
    async loadCatalog(type, search = '', page = 1) {
        try {
            const endpointMap = {
                // Catálogos existentes
                'tipos': 'impuestos/tipos',
                'tarifas-iva': 'impuestos/tarifas-iva',
                'conceptos-retencion': 'impuestos/conceptos-retencion',
                'codigos-tributarios': 'impuestos/codigos-tributarios',
                'actividades-economicas': 'impuestos/actividades-economicas',
                // Nuevos catálogos de normativa DIAN (v2.30+)
                'contribuyentes-tipos': 'impuestos/contribuyentes-tipos',
                'regimenes-renta': 'impuestos/regimenes-renta',
                'responsabilidades-rut': 'impuestos/responsabilidades-rut',
                'perfiles-tributarios': 'impuestos/perfiles-tributarios',
            };
            
            const endpoint = endpointMap[type];
            if (!endpoint) {
                throw new Error('Tipo de catálogo inválido');
            }
            
            const params = new URLSearchParams({ page });
            if (search) params.append('search', search);
            
            // Los endpoints de impuestos están en /api/public/v1/impuestos/...
            const data = await this.fetchAPI(`/api/public/v1/${endpoint}/?${params}`);
            this.renderCatalogTable(data, type);
            this.renderPagination('catalog-pagination', data, (p) => this.loadCatalog(type, search, p));
        } catch (error) {
            document.getElementById('catalog-table-body').innerHTML = 
                `<tr><td colspan="10" class="px-6 py-4 text-center text-red-500">Error: ${error.message}</td></tr>`;
        }
    },

    /**
     * Renderiza la tabla del catálogo.
     */
    renderCatalogTable(data, type) {
        const thead = document.getElementById('catalog-table-head');
        const tbody = document.getElementById('catalog-table-body');
        
        if (!data.results || data.results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="px-6 py-4 text-center text-gray-500">No hay datos</td></tr>';
            return;
        }
        
        // Headers dinámicos basados en el primer resultado
        const firstItem = data.results[0];
        const headers = Object.keys(firstItem).filter(key => 
            !['id'].includes(key)
        );
        
        thead.innerHTML = `
            <tr>
                ${headers.map(h => `<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">${h}</th>`).join('')}
            </tr>
        `;
        
        tbody.innerHTML = data.results.map(item => `
            <tr>
                ${headers.map(h => `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${item[h] || '-'}</td>`).join('')}
            </tr>
        `).join('');
    },

    /**
     * Renderiza la paginación.
     * 
     * DRF devuelve: { count, next, previous, results }
     * Extraemos el número de página de las URLs next/previous.
     */
    renderPagination(containerId, data, onPageChange) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        if (!data.next && !data.previous) {
            container.innerHTML = '';
            return;
        }
        
        // Extraer página actual de la URL next o previous
        let currentPage = 1;
        if (data.next) {
            const match = data.next.match(/[?&]page=(\d+)/);
            if (match) currentPage = parseInt(match[1]) - 1;
        } else if (data.previous) {
            const match = data.previous.match(/[?&]page=(\d+)/);
            if (match) currentPage = parseInt(match[1]) + 1;
        }
        
        const pageSize = 20; // StandardResultsSetPagination default
        const totalPages = Math.ceil((data.count || 0) / pageSize);
        
        let html = '<div class="flex items-center justify-between">';
        html += `<div class="text-sm text-gray-700">Página ${currentPage} de ${totalPages} (${data.count || 0} resultados)</div>`;
        html += '<div class="flex space-x-2">';
        
        if (data.previous) {
            const prevPage = currentPage - 1;
            html += `<button onclick="(${onPageChange.toString()})(${prevPage})" class="px-3 py-1 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50">Anterior</button>`;
        }
        
        if (data.next) {
            const nextPage = currentPage + 1;
            html += `<button onclick="(${onPageChange.toString()})(${nextPage})" class="px-3 py-1 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50">Siguiente</button>`;
        }
        
        html += '</div></div>';
        container.innerHTML = html;
    },
};
