/**
 * Módulo de renderizado para sección de contabilidad.
 * 
 * ⚠️ POLÍTICA API-First:
 * - Solo renderiza DOM desde datos JSON
 * - No hace fetch directo (los datos vienen de Core API)
 * - Sin hardcodes de marca
 * 
 * @module contabilidad
 */

/**
 * Renderiza la sección de contabilidad en el dashboard.
 * 
 * ⚠️ ORDEN: Tercera sección (empresas → facturas → contabilidad → perfil)
 * 
 * @param {Object} data - Datos de contabilidad desde Core API
 * @param {number} data.total_cuentas - Total de cuentas contables
 * @param {number} data.total_asientos - Total de asientos contables
 * @param {Array} data.asientos_recientes - Últimos asientos contables
 */
export function renderContabilidad(data) {
    const container = document.getElementById('contabilidad-content');
    const section = document.getElementById('section-contabilidad');
    
    if (!container || !data) {
        return;
    }

    container.innerHTML = `
        <div class="grid md:grid-cols-3 gap-4 mb-4">
            <div class="bg-green-50 p-4 rounded-lg">
                <p class="text-sm text-gray-600">Cuentas</p>
                <p class="text-2xl font-bold text-green-600">${data.total_cuentas || 0}</p>
            </div>
            <div class="bg-indigo-50 p-4 rounded-lg">
                <p class="text-sm text-gray-600">Asientos</p>
                <p class="text-2xl font-bold text-indigo-600">${data.total_asientos || 0}</p>
            </div>
            <div class="bg-purple-50 p-4 rounded-lg">
                <p class="text-sm text-gray-600">Movimientos (mes)</p>
                <p class="text-2xl font-bold text-purple-600">${data.mes_actual?.total_movimientos || 0}</p>
            </div>
        </div>
        ${data.asientos_recientes && data.asientos_recientes.length > 0 ? `
            <div>
                <h4 class="font-semibold text-gray-800 mb-2">Últimos asientos</h4>
                <div class="space-y-2">
                    ${data.asientos_recientes.slice(0, 5).map(a => {
                        const numero = a.numero || 'N/A';
                        const descripcion = a.descripcion || 'Sin descripción';
                        const fecha = a.fecha || 'N/A';
                        return `
                            <div class="flex items-center justify-between p-2 bg-gray-50 rounded">
                                <span class="text-sm">${numero} - ${descripcion}</span>
                                <span class="text-sm text-gray-600">${fecha}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        ` : ''}
    `;
    
    if (section) {
        section.style.display = 'block';
    }
}
