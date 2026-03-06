/**
 * Módulo de renderizado para sección de perfil.
 * 
 * ⚠️ POLÍTICA API-First:
 * - Solo renderiza DOM desde datos JSON
 * - No hace fetch directo (los datos vienen de Core API)
 * - Sin hardcodes de marca
 * 
 * @module perfil
 */

/**
 * Renderiza la sección de perfil en el dashboard.
 * 
 * ⚠️ ORDEN: Cuarta sección (empresas → facturas → contabilidad → perfil)
 * 
 * @param {Object} data - Datos de perfil desde Core API
 * @param {Object} data.me - Datos del perfil del usuario actual
 */
export function renderPerfil(data) {
    const container = document.getElementById('perfil-content');
    const section = document.getElementById('section-perfil');
    
    if (!container || !data || !data.me) {
        return;
    }

    const perfil = data.me;
    
    const fotoHtml = perfil.foto_url 
        ? `<img src="${perfil.foto_url}" alt="Foto" class="h-16 w-16 rounded-full">`
        : '<div class="h-16 w-16 rounded-full bg-gray-200 flex items-center justify-center"><i class="fas fa-user text-2xl text-gray-400"></i></div>';
    
    container.innerHTML = `
        <div class="space-y-4">
            <div class="flex items-center space-x-4">
                ${fotoHtml}
                <div>
                    <h4 class="font-semibold text-gray-800">${perfil.cargo || 'Sin cargo'}</h4>
                    ${perfil.departamento ? `<p class="text-sm text-gray-600">${perfil.departamento}</p>` : ''}
                    ${perfil.telefono ? `<p class="text-sm text-gray-600">${perfil.telefono}</p>` : ''}
                </div>
            </div>
        </div>
    `;
    
    if (section) {
        section.style.display = 'block';
    }
}
