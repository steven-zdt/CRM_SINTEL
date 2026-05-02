/**
 * empleados.module.js - Orquestador del módulo Empleados v2.60
 * 
 * Responsabilidad:
 * - Inicialización Lazy del módulo de empleados
 * - Integración con el ciclo de vida del Workspace
 * - Puente entre workspace.js y las features de empleados
 */
(function(w, d) {
    'use strict';
    
    const MOD = '[empleados.module]';
    const TAB_ID = '#tab-empleados';

    /**
     * Inicializa el módulo llamando a la feature principal (lista)
     */
    function init() {
        console.log(`${MOD} Inicializando módulo...`);
        
        // Verificar si la feature de lista está cargada
        if (w.empleadosDT && typeof w.empleadosDT.init === 'function') {
            w.empleadosDT.init();
        } else {
            // Si carga muy rápido, puede que el script de feature no esté listo
            // Reintentar brevemente
            setTimeout(() => {
                if (w.empleadosDT && typeof w.empleadosDT.init === 'function') {
                    w.empleadosDT.init();
                } else {
                    console.warn(`${MOD} Feature empleados_list.js no disponible o no expuso empleadosDT`);
                }
            }, 100);
        }
    }

    // Exponer API pública del módulo
    w.EmpleadosModule = {
        init: init
    };

    // Configurar Lazy Loading automático
    // Esto complementa la orquestación central de workspace.js
    if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
        w.DOMUtils.onVisibleOnce(TAB_ID, init);
    } else {
        // Fallback si DOMUtils no está listo (aunque assets_core debería garantizarlo)
        d.addEventListener('DOMContentLoaded', () => {
            if (w.DOMUtils && typeof w.DOMUtils.onVisibleOnce === 'function') {
                w.DOMUtils.onVisibleOnce(TAB_ID, init);
            }
        });
    }

})(window, document);
