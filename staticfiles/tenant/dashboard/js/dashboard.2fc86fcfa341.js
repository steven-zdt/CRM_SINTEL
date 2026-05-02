/**
 * Módulo principal del dashboard.
 * 
 * ⚠️ POLÍTICA API-First:
 * - Consume EXCLUSIVAMENTE Core API
 * - Renderiza KPIs y acciones rápidas
 * - Coordina renderizado de secciones mediante módulos ES
 * 
 * @module dashboard
 */

import { getJSON, sendJSON } from '/static/core/js/http.js';
import { renderEmpresas } from '/static/empresa/js/empresas.js';
import { renderFacturas } from '/static/facturas/js/facturas.js';
import { renderContabilidad } from '/static/contabilidad/js/contabilidad.js';
import { renderPerfil } from '/static/perfil/js/perfil.js';

/**
 * Renderiza los KPIs del dashboard.
 * 
 * @param {Object} kpis - KPIs desde Core API
 */
export function renderKPIs(kpis) {
    const statsGrid = document.getElementById('stats-grid');
    
    if (!statsGrid) {
        return;
    }
    
    const stats = [
        {
            label: 'Total Facturas',
            value: kpis.total_facturas || 0,
            icon: 'fa-file-invoice',
            color: 'blue',
        },
        {
            label: 'Pendientes',
            value: kpis.facturas_pendientes || 0,
            icon: 'fa-clock',
            color: 'yellow',
        },
        {
            label: 'Clientes',
            value: kpis.total_clientes || 0,
            icon: 'fa-users',
            color: 'green',
        },
        {
            label: 'Ingresos del Mes',
            value: new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(kpis.ingresos_mes || 0),
            icon: 'fa-dollar-sign',
            color: 'purple',
        },
    ];

    statsGrid.innerHTML = stats.map(stat => `
        <div class="bg-white rounded-lg shadow-md p-6">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-gray-600 text-sm mb-1">${stat.label}</p>
                    <p class="text-3xl font-bold text-gray-800">${stat.value}</p>
                </div>
                <div class="bg-${stat.color}-100 rounded-full p-3">
                    <i class="fas ${stat.icon} text-2xl text-${stat.color}-600"></i>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Actualiza el branding del dashboard (header, footer, título).
 * 
 * @param {Object} data - Datos desde Core API (user, tenant, branding)
 */
export function updateBranding(data) {
    const branding = data.branding || {};
    const tenantName = branding.nombre || data.tenant?.nombre || 'Tenant';
    
    // Actualizar UI con datos de usuario y tenant (valores por defecto, serán sobrescritos por sección empresas si hay empresa)
    const tenantNameEl = document.getElementById('tenant-name');
    if (tenantNameEl) {
        tenantNameEl.textContent = tenantName;
    }
    
    const userEmailEl = document.getElementById('user-email');
    if (userEmailEl) {
        userEmailEl.textContent = data.user?.email || '';
    }
    
    const welcomeTextEl = document.getElementById('welcome-text');
    if (welcomeTextEl) {
        welcomeTextEl.textContent = `Bienvenido al dashboard de ${tenantName}`;
    }
    
    // Actualizar título de la página con branding (será sobrescrito por sección empresas si hay empresa)
    const pageTitleEl = document.getElementById('page-title');
    if (pageTitleEl) {
        pageTitleEl.textContent = `Dashboard - ${tenantName}`;
    }
    
    // Actualizar footer con branding (será sobrescrito por sección empresas si hay empresa)
    const footerTextEl = document.getElementById('footer-text');
    if (footerTextEl) {
        footerTextEl.textContent = `© ${new Date().getFullYear()} ${tenantName}. Sistema de gestión contable y facturación electrónica.`;
    }

    // Mostrar badge de rol
    if (data.user?.role) {
        const roleTextEl = document.getElementById('user-role-text');
        const roleBadgeEl = document.getElementById('user-role-badge');
        if (roleTextEl) {
            roleTextEl.textContent = data.user.role;
        }
        if (roleBadgeEl) {
            roleBadgeEl.style.display = 'inline-block';
        }
    }
}

/**
 * Carga y renderiza el dashboard completo desde Core API.
 * 
 * ⚠️ POLÍTICA API-First: Consume EXCLUSIVAMENTE Core API
 * ⚠️ ORDEN REQUERIDO: empresas → facturas → contabilidad → perfil
 */
export async function loadDashboard() {
    try {
        // ⚠️ POLÍTICA API-First: Consumir EXCLUSIVAMENTE Core API
        // Core API incluye: user, tenant, branding, KPIs y todas las secciones
        const data = await getJSON('/api/v1/core/dashboard/sections/');

        // Actualizar branding (header, footer, título)
        updateBranding(data);

        // Renderizar KPIs
        renderKPIs(data.kpis || {});

        // ⚠️ ORDEN REQUERIDO: empresas → facturas → contabilidad → perfil
        // Renderizar secciones del dashboard desde Core API
        renderEmpresas(data.empresas);
        renderFacturas(data.facturas);
        renderContabilidad(data.contabilidad);
        renderPerfil(data.perfil);

        // Cargar acciones rápidas (usa Link Registry)
        await loadQuickActions();

        // Ocultar loading y mostrar dashboard
        const loadingEl = document.getElementById('loading');
        const dashboardEl = document.getElementById('dashboard');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
        if (dashboardEl) {
            dashboardEl.style.display = 'block';
        }

    } catch (error) {
        console.error('Error cargando dashboard:', error);
        const loadingEl = document.getElementById('loading');
        const errorEl = document.getElementById('error');
        const errorTextEl = document.getElementById('error-text');
        
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
        if (errorEl) {
            errorEl.style.display = 'block';
        }
        if (errorTextEl) {
            errorTextEl.textContent = error.message || 'Error desconocido';
        }
    }
}

/**
 * Carga acciones rápidas desde Link Registry.
 * 
 * ⚠️ POLÍTICA: Usa Link Registry para evitar "link rot"
 * ⚠️ NOTA: quick-actions todavía usa /api/v1/dashboard/quick-actions/ (pendiente migración a Core)
 */
async function loadQuickActions() {
    try {
        // Obtener Link Registry desde Core API
        const links = await getJSON('/api/v1/core/links/');
        
        // Obtener acciones rápidas (temporalmente desde dashboard API, pendiente migración a Core)
        const actions = await getJSON('/api/v1/dashboard/quick-actions/');
        const actionsContainer = document.getElementById('quick-actions');
        
        if (!actionsContainer) {
            return;
        }

        // Construir acciones usando Link Registry
        actionsContainer.innerHTML = actions.map(action => {
            // Usar Link Registry para corregir URLs si es necesario
            let finalUrl = action.url;
            if (action.url.includes('/api/v1/empresa/') || action.url.includes('/api/v1/empresas/')) {
                // Usar URL plural canónica del registry
                finalUrl = links.empresa?.api || '/api/v1/empresas/';
            } else if (action.url.includes('/api/v1/facturas/')) {
                finalUrl = links.facturas?.api || action.url;
            } else if (action.url.includes('/api/v1/contabilidad/')) {
                finalUrl = links.contabilidad?.api || action.url;
            }

            const color = action.color || 'blue';
            return `
                <a href="${finalUrl}" 
                   class="flex items-center p-4 bg-${color}-50 rounded-lg hover:bg-${color}-100 transition-colors">
                    <i class="fas ${action.icon || 'fa-link'} text-2xl text-${color}-600 mr-3"></i>
                    <span class="font-semibold text-gray-800">${action.label}</span>
                </a>
            `;
        }).join('');

    } catch (error) {
        console.error('Error cargando acciones rápidas:', error);
    }
}

/**
 * Maneja el logout del usuario.
 * 
 * ⚠️ POLÍTICA API-First: Consume endpoint de logout
 */
export async function handleLogout() {
    try {
        // Llamar al endpoint de logout (API-First)
        // ⚠️ POLÍTICA: Consumir Core API centralizado
        const data = await sendJSON('/api/v1/core/auth/logout/', {}, { method: 'POST' });

        // Usar redirect_url de la respuesta JSON (API-First)
        const redirectUrl = data.redirect_url || '/';
        window.location.replace(redirectUrl);
    } catch (error) {
        console.error('Error en logout:', error);
        // Fallback: redirigir a la página principal
        window.location.replace('/');
    }
}

// Inicializar dashboard al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    
    // Configurar botón de logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
});
