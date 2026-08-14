/**
 * reporte.api.js - Consumo de endpoints de reportes financieros v1.0
 * ⚠️ v3.5: Única fuente de verdad para URLs de reportes.
 *
 * F32.9: migrado a Sintel.Core.Http (hallazgo de la revalidacion de
 * gobernanza F32.9.5 -- este archivo nunca fue tocado por F32.6/F32.7,
 * que solo auditaron window.http/w.http, no fetch() directo con JWT
 * manual sin refresh, el mismo patron de bug que F32.1 documento en los
 * 6 archivos originales). Contrato publico preservado: cada metodo
 * resuelve con los datos ya parseados o lanza un Error generico -- unico
 * consumidor real, reporte.ui.js, usa un try/catch simple.
 */
(function() {
    window.Sintel = window.Sintel || {};
    window.Sintel.Contabilidad = window.Sintel.Contabilidad || {};

    async function _get(url, errorMsg) {
        const res = await window.Sintel.Core.Http.get(url);
        if (!res.ok) throw new Error(errorMsg);
        return res.data;
    }

    window.Sintel.Contabilidad.ReporteAPI = {
        /**
         * Obtiene el Balance de Prueba
         * @param {string} fechaInicio - Formato YYYY-MM-DD
         * @param {string} fechaFin - Formato YYYY-MM-DD
         */
        getBalancePrueba: function(fechaInicio, fechaFin) {
            const url = `/api/v1/contabilidad/asientos-contables/reporte-balance-prueba/?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`;
            return _get(url, 'Error al obtener Balance de Prueba');
        },

        /**
         * Obtiene el Estado de Resultados (P&G)
         * @param {string} fechaInicio - Formato YYYY-MM-DD
         * @param {string} fechaFin - Formato YYYY-MM-DD
         */
        getEstadoResultados: function(fechaInicio, fechaFin) {
            const url = `/api/v1/contabilidad/asientos-contables/reporte-estado-resultados/?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`;
            return _get(url, 'Error al obtener Estado de Resultados');
        }
    };
})();
