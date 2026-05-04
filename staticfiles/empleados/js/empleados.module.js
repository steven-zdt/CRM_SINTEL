/**
 * empleados.module.js - Orquestador del Módulo Empleados v2.95
 * 
 * Responsable de la inicialización y coordinación de submódulos.
 */
(function(w, d) {
    'use strict';

    const MOD = '[empleados:module]';
    let initialized = false;

    /**
     * Inicialización del módulo
     */
    async function init() {
        console.log(`${MOD} Ejecutando orquestación inicial...`);

        // Inicializar pestaña activa por defecto (Empleados)
        initSubTab('empleados');

        initialized = true;
    }

    /**
     * Inicializa una sub-pestaña específica
     */
    async function initSubTab(tabName) {
        console.log(`${MOD} Inicializando sub-pestaña: ${tabName}`);
        
        const gridId = `#grid-${tabName}`;
        const spinnerSelector = `[data-spinner="${tabName}"]`;
        const grid = d.querySelector(gridId);
        const spinner = d.querySelector(spinnerSelector);

        if (spinner) spinner.style.display = 'block';
        if (grid) grid.style.display = 'none';

        try {
            if (tabName === 'empleados' && w.Sintel.Empleados.EmpleadoList) {
                await w.Sintel.Empleados.EmpleadoList.init(gridId);
                await w.Sintel.Empleados.EmpleadoList.loadSummary('#empleados-summary');
            } else if (tabName === 'contratos' && w.Sintel.Empleados.ContratoList) {
                // Asumiendo que existe ContratoList
                // await w.Sintel.Empleados.ContratoList.init(gridId);
            }
            // ... otros sub-tabs
            
            if (grid) grid.style.display = 'block';
        } catch (err) {
            console.error(`${MOD} Error inicializando ${tabName}:`, err);
        } finally {
            if (spinner) spinner.style.display = 'none';
        }
    }

    // Escuchar activación de tab en el workspace
    d.addEventListener('tab-activated', function(e) {
        if (e.detail.tabName === 'empleados') {
            init();
        }
    });

    // Escuchar cambios en las sub-pestañas de empleados
    d.addEventListener('shown.bs.tab', function(e) {
        if (e.target.closest('#empleados-tabs')) {
            const targetId = e.target.getAttribute('data-bs-target');
            const subTab = targetId.replace('#tab-pane-', '');
            initSubTab(subTab);
        }
    });

    // Fallback: si el hash ya es #empleados al cargar
    if (w.location.hash === '#empleados') {
        d.addEventListener('DOMContentLoaded', init);
    }

})(window, document);
