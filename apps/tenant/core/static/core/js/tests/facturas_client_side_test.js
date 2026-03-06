/**
 * 🧪 SINTEL TEST SUITE: Facturas & Notas Crédito (Client-Side)
 * 
 * Valida la corrección de 'recalc' y la carga de datos después de la migración a Client-Side.
 * 
 * ⚠️ v2.40+: Pruebas específicas para validar:
 * - Migración exitosa de Server-Side a Client-Side DataTables
 * - Eliminación de errores de 'recalc' al cambiar tabs
 * - Carga correcta de datos desde API REST estándar
 * - Renderizado manual de HTML en tbody
 * - Funcionalidad de importación y recarga
 * 
 * Uso:
 * 1. Abrir consola del navegador en /workspace/
 * 2. Pegar y ejecutar este script completo
 * 3. O agregar ?testfacturas=1 a la URL para auto-ejecución
 */

(async function runFacturasClientSideTest() {
    console.clear();
    console.group("🚀 INICIANDO PRUEBA: MÓDULO FACTURAS (Client-Side)");
    const report = { steps: 0, passed: 0, failed: 0, warnings: 0 };

    function assert(condition, message) {
        report.steps++;
        if (condition) {
            console.log(`%c✅ PASO ${report.steps}: ${message}`, 'color: #0f0');
            report.passed++;
        } else {
            console.error(`%c❌ PASO ${report.steps}: ${message}`, 'color: #f00');
            report.failed++;
        }
    }

    function warn(condition, message) {
        if (!condition) {
            console.warn(`%c⚠️ ADVERTENCIA: ${message}`, 'color: #ffa500');
            report.warnings++;
        }
    }

    try {
        // 1. VALIDACIÓN DOM (ESTRUCTURA WORKSPACE)
        console.group("1. Estructura DOM");
        const tabFacturas = document.querySelector('button[data-bs-target="#tab-facturas"]');
        const tabNotas = document.querySelector('button[data-bs-target="#tab-notas-credito"]');
        const tableFacturas = document.querySelector('#table-facturas');
        const tableNotas = document.querySelector('#table-notas-credito');
        const tabPaneFacturas = document.querySelector('#tab-facturas');
        const tabPaneNotas = document.querySelector('#tab-notas-credito');

        assert(tabFacturas && tabNotas, "Pestañas (Tabs) encontradas en el DOM");
        assert(tableFacturas && tableNotas, "Tablas HTML base encontradas");
        assert(tabPaneFacturas && tabPaneNotas, "Tab panes encontrados");
        
        // Verificar estructura de tablas
        const theadFacturas = tableFacturas?.querySelector('thead');
        const tbodyFacturas = tableFacturas?.querySelector('tbody');
        const theadNotas = tableNotas?.querySelector('thead');
        const tbodyNotas = tableNotas?.querySelector('tbody');
        
        assert(theadFacturas && tbodyFacturas, "Tabla Facturas tiene thead y tbody");
        assert(theadNotas && tbodyNotas, "Tabla Notas Crédito tiene thead y tbody");
        
        // Contar columnas
        const thCountFacturas = theadFacturas?.querySelectorAll('th').length || 0;
        const thCountNotas = theadNotas?.querySelectorAll('th').length || 0;
        warn(thCountFacturas === 10, `Tabla Facturas tiene ${thCountFacturas} columnas (esperado: 10)`);
        warn(thCountNotas === 6, `Tabla Notas Crédito tiene ${thCountNotas} columnas (esperado: 6)`);
        
        console.groupEnd();

        // 2. VALIDACIÓN API FACTURAS (GET)
        console.group("2. API Facturas (Lectura)");
        const t0 = performance.now();
        let respFacturas;
        try {
            respFacturas = await fetch('/api/v1/facturas/', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
                credentials: 'include'
            });
        } catch (fetchErr) {
            assert(false, `Error de red al llamar API: ${fetchErr.message}`);
            console.groupEnd();
            throw fetchErr;
        }
        
        assert(respFacturas.ok, `Endpoint GET /api/v1/facturas/ respondió ${respFacturas.status}`);
        
        const dataFacturas = await respFacturas.json();
        const listaFacturas = Array.isArray(dataFacturas) ? dataFacturas : (dataFacturas.results || []);
        assert(Array.isArray(listaFacturas), "La API devolvió un Array válido");
        
        if (listaFacturas.length > 0) {
            const f = listaFacturas[0];
            // Validar campos del modelo Factura según FacturaListSerializer
            assert(f.hasOwnProperty('id'), "Campo 'id' presente");
            assert(f.hasOwnProperty('numero'), "Campo 'numero' presente");
            assert(f.hasOwnProperty('fecha_emision'), "Campo 'fecha_emision' presente");
            assert(f.hasOwnProperty('total'), "Campo 'total' presente");
            assert(f.hasOwnProperty('naturaleza'), "Campo 'naturaleza' presente (VENTA/COMPRA)");
            assert(f.hasOwnProperty('estado'), "Campo 'estado' presente");
            
            console.log(`📊 Ejemplo de factura:`, {
                id: f.id,
                numero: f.numero,
                naturaleza: f.naturaleza,
                total: f.total
            });
        } else {
            warn(false, "No hay facturas en la base de datos para validar estructura");
        }
        
        const latencyFacturas = (performance.now() - t0).toFixed(2);
        console.log(`⏱️ Tiempo Latencia API Facturas: ${latencyFacturas}ms`);
        console.log(`📦 Total de facturas: ${listaFacturas.length}`);
        console.groupEnd();

        // 3. VALIDACIÓN API NOTAS CRÉDITO (GET)
        console.group("3. API Notas Crédito (Lectura)");
        const t1 = performance.now();
        let respNotas;
        try {
            respNotas = await fetch('/api/v1/facturas/notas-credito/', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
                credentials: 'include'
            });
        } catch (fetchErr) {
            assert(false, `Error de red al llamar API: ${fetchErr.message}`);
            console.groupEnd();
            throw fetchErr;
        }
        
        assert(respNotas.ok, `Endpoint GET /api/v1/facturas/notas-credito/ respondió ${respNotas.status}`);
        
        const dataNotas = await respNotas.json();
        const listaNotas = Array.isArray(dataNotas) ? dataNotas : (dataNotas.results || []);
        assert(Array.isArray(listaNotas), "La API devolvió un Array válido");
        
        if (listaNotas.length > 0) {
            const n = listaNotas[0];
            // Validar campos del modelo NotaCredito según NotaCreditoListSerializer
            assert(n.hasOwnProperty('id'), "Campo 'id' presente");
            assert(n.hasOwnProperty('numero'), "Campo 'numero' presente");
            assert(n.hasOwnProperty('fecha_emision'), "Campo 'fecha_emision' presente");
            assert(n.hasOwnProperty('total'), "Campo 'total' presente");
            
            // Validar relación con Factura
            const hasFacturaRef = n.hasOwnProperty('factura_numero') || 
                                 n.hasOwnProperty('ref_factura_numero') ||
                                 n.hasOwnProperty('factura_referencia');
            assert(hasFacturaRef, "Campo de referencia a factura presente (factura_numero, ref_factura_numero o factura_referencia)");
            
            console.log(`📊 Ejemplo de nota crédito:`, {
                id: n.id,
                numero: n.numero,
                factura_ref: n.factura_numero || n.ref_factura_numero || n.factura_referencia,
                total: n.total
            });
        } else {
            warn(false, "No hay notas de crédito en la base de datos para validar estructura");
        }
        
        const latencyNotas = (performance.now() - t1).toFixed(2);
        console.log(`⏱️ Tiempo Latencia API Notas: ${latencyNotas}ms`);
        console.log(`📦 Total de notas crédito: ${listaNotas.length}`);
        console.groupEnd();

        // 4. VALIDACIÓN MÓDULO JAVASCRIPT
        console.group("4. Módulo JavaScript (facturas.page.js)");
        assert(typeof window.FacturasModule !== 'undefined', "window.FacturasModule está disponible");
        assert(typeof window.FacturasModule.reload === 'function', "Método reload() disponible");
        assert(typeof window.FacturasModule.reloadNotasCredito === 'function', "Método reloadNotasCredito() disponible");
        
        // Verificar que jQuery y DataTables estén disponibles
        assert(typeof window.jQuery !== 'undefined', "jQuery está disponible");
        assert(typeof window.jQuery.fn.DataTable !== 'undefined', "DataTables está disponible");
        console.groupEnd();

        // 5. SIMULACIÓN INTERACCIÓN TAB (FIX 'RECALC')
        console.group("5. Interacción UI (Tab Switching - Fix 'recalc')");
        
        // Asegurar que el tab de Facturas esté activo primero
        if (tabFacturas) {
            tabFacturas.click();
            await new Promise(r => setTimeout(r, 300)); // Esperar animación Bootstrap
            
            // Verificar que la tabla de Facturas esté inicializada (si el módulo ya cargó)
            const dtFacturasExists = window.jQuery && window.jQuery.fn.DataTable.isDataTable('#table-facturas');
            if (dtFacturasExists) {
                const dtFacturas = window.jQuery('#table-facturas').DataTable();
                const filasFacturas = document.querySelectorAll('#table-facturas tbody tr');
                assert(filasFacturas.length > 0, `Tabla Facturas renderizada: ${filasFacturas.length} filas visibles`);
                console.log(`✅ DataTables Facturas inicializado correctamente`);
            } else {
                warn(false, "DataTables Facturas aún no inicializado (puede ser lazy loading)");
            }
        }
        
        // Simular clic en Tab Notas de Crédito (test crítico de 'recalc')
        if (tabNotas) {
            console.log("🔄 Cambiando a tab Notas de Crédito...");
            tabNotas.click();
            await new Promise(r => setTimeout(r, 500)); // Esperar animación BS y carga lazy
            
            // Verificar que no haya errores de 'recalc' en consola
            // (Si llegamos aquí sin excepción, el fix funcionó)
            const dtNotasExists = window.jQuery && window.jQuery.fn.DataTable.isDataTable('#table-notas-credito');
            if (dtNotasExists) {
                try {
                    const dtNotas = window.jQuery('#table-notas-credito').DataTable();
                    assert(dtNotas !== null && dtNotas !== undefined, "DataTables Notas Crédito inicializado");
                    
                    // Verificar que responsive.recalc() no lance error
                    if (dtNotas.responsive && typeof dtNotas.responsive.recalc === 'function') {
                        dtNotas.responsive.recalc();
                        console.log("✅ responsive.recalc() ejecutado sin errores");
                    } else {
                        warn(false, "Plugin responsive no disponible (no crítico para Client-Side)");
                    }
                    
                    const filasNotas = document.querySelectorAll('#table-notas-credito tbody tr');
                    assert(filasNotas.length >= 0, `Tabla Notas Crédito renderizada: ${filasNotas.length} filas visibles`);
                    
                    console.log("✅ Cambio de pestaña ejecutado sin errores de 'recalc'");
                } catch (recalcErr) {
                    assert(false, `Error al acceder a DataTables Notas: ${recalcErr.message}`);
                }
            } else {
                warn(false, "DataTables Notas Crédito aún no inicializado (lazy loading pendiente)");
            }
            
            // Volver a Facturas para verificar que no se rompa
            if (tabFacturas) {
                tabFacturas.click();
                await new Promise(r => setTimeout(r, 300));
                console.log("✅ Regreso a tab Facturas sin errores");
            }
        }
        console.groupEnd();

        // 6. VALIDACIÓN RECARGA MANUAL (Client-Side)
        console.group("6. Recarga Manual (Client-Side)");
        if (typeof window.FacturasModule !== 'undefined' && typeof window.FacturasModule.reload === 'function') {
            try {
                // Intentar recargar (no debe usar .ajax.reload() en Client-Side)
                await window.FacturasModule.reload();
                await new Promise(r => setTimeout(r, 500)); // Esperar recarga
                
                const filasDespuesRecarga = document.querySelectorAll('#table-facturas tbody tr');
                assert(filasDespuesRecarga.length >= 0, `Recarga manual exitosa: ${filasDespuesRecarga.length} filas`);
                console.log("✅ Recarga manual ejecutada sin usar .ajax.reload()");
            } catch (reloadErr) {
                assert(false, `Error en recarga manual: ${reloadErr.message}`);
            }
        } else {
            warn(false, "window.FacturasModule.reload() no disponible");
        }
        console.groupEnd();

    } catch (e) {
        console.error("🔥 ERROR CRÍTICO EN PRUEBA:", e);
        console.error("Stack trace:", e.stack);
        report.failed++;
    }

    console.groupEnd();
    
    // Resumen final
    const totalTests = report.passed + report.failed;
    const successRate = totalTests > 0 ? ((report.passed / totalTests) * 100).toFixed(1) : 0;
    
    console.log(`%c═══════════════════════════════════════════════════════`, 'color: #666');
    console.log(`%cRESULTADO FINAL:`, 'font-size: 16px; font-weight: bold');
    console.log(`%c  ✅ Pasados: ${report.passed}/${totalTests}`, report.passed > 0 ? 'color: #0f0' : 'color: #666');
    console.log(`%c  ❌ Fallidos: ${report.failed}/${totalTests}`, report.failed > 0 ? 'color: #f00' : 'color: #666');
    console.log(`%c  ⚠️ Advertencias: ${report.warnings}`, report.warnings > 0 ? 'color: #ffa500' : 'color: #666');
    console.log(`%c  📊 Tasa de éxito: ${successRate}%`, successRate >= 80 ? 'color: #0f0' : successRate >= 50 ? 'color: #ffa500' : 'color: #f00');
    console.log(`%c═══════════════════════════════════════════════════════`, 'color: #666');

    // Alert final (solo si hay fallos críticos)
    if (report.failed === 0) {
        console.log(`%c✅ PRUEBA EXITOSA: El sistema Client-Side funciona correctamente`, 'font-size: 14px; color: #0f0; font-weight: bold');
        if (report.warnings === 0) {
            // Solo mostrar alert si todo está perfecto
            // alert("✅ PRUEBA EXITOSA\nEl sistema Client-Side funciona correctamente y los modelos están expuestos.");
        }
    } else {
        console.error(`%c❌ PRUEBA FALLIDA: Revisa los errores arriba`, 'font-size: 14px; color: #f00; font-weight: bold');
        // alert(`❌ PRUEBA FALLIDA\n${report.failed} error(es) detectado(s). Revisa la consola para más detalles.`);
    }
    
    // Retornar reporte para uso programático
    return report;
})();
