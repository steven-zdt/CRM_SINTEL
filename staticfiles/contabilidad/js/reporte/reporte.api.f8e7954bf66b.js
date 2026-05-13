/**
 * reporte.api.js - Consumo de endpoints de reportes financieros v1.0
 * ⚠️ v3.5: Única fuente de verdad para URLs de reportes.
 */
(function() {
    window.Sintel = window.Sintel || {};
    window.Sintel.Contabilidad = window.Sintel.Contabilidad || {};
    
    window.Sintel.Contabilidad.ReporteAPI = {
        /**
         * Obtiene el Balance de Prueba
         * @param {string} fechaInicio - Formato YYYY-MM-DD
         * @param {string} fechaFin - Formato YYYY-MM-DD
         */
        getBalancePrueba: async function(fechaInicio, fechaFin) {
            const url = `/api/v1/contabilidad/asientos-contables/reporte-balance-prueba/?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`;
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${window.jwtAuth?.getAccessToken?.()}`
                }
            });
            if (!response.ok) throw new Error('Error al obtener Balance de Prueba');
            return response.json();
        },

        /**
         * Obtiene el Estado de Resultados (P&G)
         * @param {string} fechaInicio - Formato YYYY-MM-DD
         * @param {string} fechaFin - Formato YYYY-MM-DD
         */
        getEstadoResultados: async function(fechaInicio, fechaFin) {
            const url = `/api/v1/contabilidad/asientos-contables/reporte-estado-resultados/?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`;
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    'Authorization': `Bearer ${window.jwtAuth?.getAccessToken?.()}`
                }
            });
            if (!response.ok) throw new Error('Error al obtener Estado de Resultados');
            return response.json();
        }
    };
})();
