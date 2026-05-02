/**
 * UI Module para Landing (API-First).
 * 
 * ⚠️ CENTRALIZADO: Este JS vive en apps/public/core/static/core/js/landing.ui.js
 * y es referenciado desde el shell estático en apps/public/core/static/public/core/landing/index.html
 * 
 * ⚠️ IMPORTANTE: Este módulo consume APIs de apps/tenant/landing/api (JSON only).
 */
(function () {
  'use strict';
  
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }
  
  async function jget(url) {
    const csrftoken = getCookie('csrftoken') || '';
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrftoken,
      },
    });
    if (!response.ok) throw new Error(response.status + ' ' + url);
    return response.json();
  }
  
  async function jpost(url, data) {
    const csrftoken = getCookie('csrftoken') || '';
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(errorData.detail || `HTTP ${response.status}`);
      error.status = response.status;
      error.data = errorData;
      throw error;
    }
    return response.json();
  }
  
  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }
  
  async function boot() {
    const root = document.getElementById('landing_content');
    if (!root) return;
    
    try {
      // ⚠️ POLÍTICA: Consumir Core API (orquestador) en lugar de landing directo
      // Core API: /api/v1/core/landing/resumen/ (consume apps/tenant/core/services/landing.py)
      const data = await jget('/api/v1/core/landing/resumen/');
      
      // Actualizar título de la página
      const pageTitle = document.querySelector('title');
      if (pageTitle && data.nombre) {
        pageTitle.textContent = `${data.nombre} - Sistema de Gestión`;
      }
      
      root.innerHTML = `
        <div class="min-h-screen flex items-center justify-center px-4 py-8">
          <div class="max-w-4xl w-full">
            <!-- Header con información del tenant -->
            <div class="bg-white rounded-lg shadow-xl p-8 mb-6">
              <div class="text-center mb-6">
                <div class="inline-block bg-indigo-600 text-white rounded-full p-4 mb-4">
                  <i class="fas fa-building text-4xl"></i>
                </div>
                <h1 class="text-3xl font-bold text-gray-800 mb-2">${escapeHtml(data.nombre || 'Sistema de Gestión')}</h1>
                <p class="text-gray-600">Sistema de Gestión Empresarial</p>
              </div>

              <!-- Información del servicio -->
              <div class="grid md:grid-cols-3 gap-4 mb-6">
                <div class="bg-blue-50 rounded-lg p-4 text-center">
                  <i class="fas fa-chart-line text-blue-600 text-2xl mb-2"></i>
                  <h3 class="font-semibold text-gray-800">Análisis</h3>
                  <p class="text-sm text-gray-600">Datos en tiempo real</p>
                </div>
                <div class="bg-green-50 rounded-lg p-4 text-center">
                  <i class="fas fa-shield-alt text-green-600 text-2xl mb-2"></i>
                  <h3 class="font-semibold text-gray-800">Seguro</h3>
                  <p class="text-sm text-gray-600">Protección de datos</p>
                </div>
                <div class="bg-purple-50 rounded-lg p-4 text-center">
                  <i class="fas fa-cloud text-purple-600 text-2xl mb-2"></i>
                  <h3 class="font-semibold text-gray-800">Cloud</h3>
                  <p class="text-sm text-gray-600">Acceso desde cualquier lugar</p>
                </div>
              </div>

              <!-- Botón de login -->
              <div class="text-center">
                <a href="/static/tenant/landing/index.html" 
                   class="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-8 rounded-lg transition-colors duration-200 shadow-lg">
                  <i class="fas fa-sign-in-alt mr-2"></i>
                  Iniciar Sesión
                </a>
              </div>
            </div>

            <!-- Footer -->
            <div class="text-center text-gray-600 text-sm">
              <p>© ${new Date().getFullYear()} ${escapeHtml(data.nombre || 'Sistema de Gestión')}. Todos los derechos reservados.</p>
            </div>
          </div>
        </div>
      `;
    } catch (e) {
      root.innerHTML = `
        <div class="min-h-screen flex items-center justify-center px-4 py-8">
          <div class="max-w-4xl w-full">
            <div class="bg-white rounded-lg shadow-xl p-8 mb-6">
              <div class="text-center mb-6">
                <div class="inline-block bg-indigo-600 text-white rounded-full p-4 mb-4">
                  <i class="fas fa-building text-4xl"></i>
                </div>
                <h1 class="text-3xl font-bold text-gray-800 mb-2">Sistema de Gestión</h1>
                <p class="text-gray-600">Sistema de Gestión Empresarial</p>
              </div>
              <div class="text-center">
                <a href="/static/tenant/landing/index.html" 
                   class="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-8 rounded-lg transition-colors duration-200 shadow-lg">
                  <i class="fas fa-sign-in-alt mr-2"></i>
                  Iniciar Sesión
                </a>
              </div>
            </div>
          </div>
        </div>
      `;
    }
  }
  
  document.addEventListener('DOMContentLoaded', boot);
})();
