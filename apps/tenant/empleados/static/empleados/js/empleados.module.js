// @ts-nocheck
/**
 * empleados.module.js - Orquestador del Modulo Empleados v3.8.0
 *
 * Responsabilidad: inicializar y coordinar los 3 sub-modulos independientes:
 *   - EmpleadoList  (tab-pane-empleados)
 *   - ContratoList  (tab-pane-contratos)  <- v3.8.0: activado
 *   - NominaList    (tab-pane-nominas)
 */
(function(w, d) {
    window.Sintel = window.Sintel || {};
    window.Sintel.Empleados = window.Sintel.Empleados || {};
    
    // Si ya existe el módulo, evitar re-ejecución
    if (window.Sintel.Empleados.Module) {
        return;
    }

    const MOD = '[empleados:module]';
    
    window.Sintel.Empleados.Module = {
        initialized: false,
        subTabsInitialized: {
            empleados: false,
            contratos: false,
            nominas: false,
            resoluciones: false,
            liquidaciones: false
        },
        subTabsPending: {
            empleados: false,
            contratos: false,
            nominas: false,
            resoluciones: false,
            liquidaciones: false
        }
    };

    const state = window.Sintel.Empleados.Module;

    // ── Botones de creacion independiente ──────────────────────────────────────

    function conectarBotonesCreacion() {
        // Boton Nuevo Contrato (Tab Contratos)
        // Usa el endpoint dedicado del ContratoViewSet: render-offcanvas/crear/
        // Sin empleado preseleccionado -> el template muestra selector
        const btnContrato = d.getElementById('btn-nuevo-contrato');
        if (btnContrato && !btnContrato.dataset.bound) {
            btnContrato.dataset.bound = '1';
            btnContrato.addEventListener('click', () => {
                const api = w.Sintel?.Empleados?.API;
                if (!api) return;
                htmx.ajax('GET', api.contratos.crearOffcanvas, {
                    target: '#offcanvas-container-contratos',
                    swap: 'innerHTML'
                });
            });
        }

        // Boton Nueva Nomina (Tab Nominas)
        // Usa el endpoint dedicado del DevengoViewSet: render-offcanvas/crear/
        const btnNomina = d.getElementById('btn-nueva-nomina');
        if (btnNomina && !btnNomina.dataset.bound) {
            btnNomina.dataset.bound = '1';
            btnNomina.addEventListener('click', () => {
                const api = w.Sintel?.Empleados?.API;
                if (!api) return;
                htmx.ajax('GET', api.devengos.crearOffcanvas, {
                    target: '#offcanvas-container-nominas',
                    swap: 'innerHTML'
                });
            });
        }

        // Boton Nueva Resolucion (Tab Resoluciones)
        const btnResolucion = d.getElementById('btn-nueva-resolucion');
        if (btnResolucion && !btnResolucion.dataset.bound) {
            btnResolucion.dataset.bound = '1';
            btnResolucion.addEventListener('click', () => {
                if (w.Sintel?.Empleados?.ResolucionEditor) {
                    w.Sintel.Empleados.ResolucionEditor.open();
                } else {
                    console.error('[empleados:module] ResolucionEditor no cargado');
                }
            });
        }

        // Boton Nueva Liquidacion (Tab Liquidaciones) — pasa empleado_uuid del Master
        const btnLiquidacion = d.getElementById('btn-nueva-liquidacion');
        if (btnLiquidacion && !btnLiquidacion.dataset.bound) {
            btnLiquidacion.dataset.bound = '1';
            btnLiquidacion.addEventListener('click', () => {
                if (w.Sintel?.Empleados?.LiquidacionEditor) {
                    const empUuid = btnLiquidacion.dataset.empleadoUuid || '';
                    w.Sintel.Empleados.LiquidacionEditor.open(empUuid);
                } else {
                    console.error('[empleados:module] LiquidacionEditor no cargado');
                }
            });
        }
    }

    // ── Sub-tabs ───────────────────────────────────────────────────────────────

    async function initSubTab(tabName) {
        if (state.subTabsInitialized[tabName]) {
            // Ya inicializado, recargar datos en lugar de recrear
            if (tabName === 'empleados' && w.Sintel.Empleados.EmpleadoList) {
                w.Sintel.Empleados.EmpleadoList.reload();
                w.Sintel.Empleados.EmpleadoList.loadSummary('#panel-resumen-empleados');
            } else if (tabName === 'contratos' && w.Sintel.Empleados.ContratoList) {
                w.Sintel.Empleados.ContratoList.reload();
            } else if (tabName === 'nominas' && w.Sintel.Empleados.NominaList) {
                w.Sintel.Empleados.NominaList.reload();
            } else if (tabName === 'resoluciones' && w.Sintel.Empleados.ResolucionList) {
                w.Sintel.Empleados.ResolucionList.reload();
            } else if (tabName === 'liquidaciones' && w.Sintel.Empleados.LiquidacionList) {
                w.Sintel.Empleados.LiquidacionList.reload();
            }
            return;
        }

        if (state.subTabsPending[tabName]) {
            return; // Ya se está inicializando
        }

        state.subTabsPending[tabName] = true;
        console.log(`${MOD} Inicializando sub-tab: ${tabName}`);

        const gridId         = `#grid-${tabName}`;
        const spinnerSel     = `[data-spinner="${tabName}"]`;
        const grid           = d.querySelector(gridId);
        const spinner        = d.querySelector(spinnerSel);

        // Mostrar grid antes de inicializar Tabulator para que pueda medir dimensiones correctamente
        if (grid)    grid.style.display    = 'block';
        if (spinner) spinner.style.display = 'block';

        try {
            if (tabName === 'empleados' && w.Sintel.Empleados.EmpleadoList) {
                await w.Sintel.Empleados.EmpleadoList.init(gridId);
                await w.Sintel.Empleados.EmpleadoList.loadSummary('#panel-resumen-empleados');
                state.subTabsInitialized.empleados = true;

            } else if (tabName === 'contratos' && w.Sintel.Empleados.ContratoList) {
                await w.Sintel.Empleados.ContratoList.init(gridId);
                state.subTabsInitialized.contratos = true;
                setTimeout(() => w.Sintel.Empleados.ContratoList.redraw?.(), 50);

            } else if (tabName === 'nominas' && w.Sintel.Empleados.NominaList) {
                await w.Sintel.Empleados.NominaList.init(gridId);
                state.subTabsInitialized.nominas = true;
                setTimeout(() => w.Sintel.Empleados.NominaList.redraw?.(), 50);

            } else if (tabName === 'resoluciones' && w.Sintel.Empleados.ResolucionList) {
                await w.Sintel.Empleados.ResolucionList.init(gridId);
                state.subTabsInitialized.resoluciones = true;
                setTimeout(() => w.Sintel.Empleados.ResolucionList.redraw?.(), 50);

            } else if (tabName === 'liquidaciones' && w.Sintel.Empleados.LiquidacionList) {
                // Master-Detail: no usa #grid-liquidaciones, gestiona sus propios grids
                await w.Sintel.Empleados.LiquidacionList.init();
                state.subTabsInitialized.liquidaciones = true;
                setTimeout(() => w.Sintel.Empleados.LiquidacionList.redraw?.(), 50);
            }
        } catch (err) {
            console.error(`${MOD} Error inicializando tab "${tabName}":`, err);
        } finally {
            if (spinner) spinner.style.display = 'none';
            state.subTabsPending[tabName] = false;
        }
    }

    // ── Init principal ─────────────────────────────────────────────────────────

    async function init() {
        if (state.initialized) return;
        state.initialized = true; // Prevenir múltiples llamadas asíncronas concurrentes
        console.log(`${MOD} Orquestando modulo empleados v3.8.0...`);

        conectarBotonesCreacion();
        await initSubTab('empleados');
    }

    // ── Listeners ──────────────────────────────────────────────────────────────

    // Activacion del tab principal del workspace (#empleados)
    d.addEventListener('tab-activated', function(e) {
        if (e.detail.tabName === 'empleados') {
            if (state.initialized) {
                // Si ya está inicializado, recargar la pestaña activa actual
                const activeTab = d.querySelector('#empleados-tabs .nav-link.active');
                if (activeTab) {
                    const targetId = activeTab.getAttribute('data-bs-target');
                    const subTab = targetId ? targetId.replace('#tab-pane-', '') : '';
                    if (subTab) initSubTab(subTab);
                }
            } else {
                init();
            }
        }
    });

    // Cambios entre sub-tabs (Bootstrap tab events)
    d.addEventListener('shown.bs.tab', function(e) {
        if (e.target.closest('#empleados-tabs')) {
            const targetId = e.target.getAttribute('data-bs-target');
            const subTab   = targetId ? targetId.replace('#tab-pane-', '') : '';
            if (subTab) initSubTab(subTab);
        }
    });

    // Fallback: si el hash ya apunta a #empleados al cargar
    if (w.location.hash === '#empleados') {
        d.addEventListener('DOMContentLoaded', init);
    }

})(window, document);
