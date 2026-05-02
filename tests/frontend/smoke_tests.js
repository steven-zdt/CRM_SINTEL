/**
 * Smoke Tests para Refactor Frontend SINTEL (Ola 5)
 * 
 * Tests mínimos para validar:
 * - Core Routes endpoint funciona
 * - Módulos cargan sin errores JS
 * - Discovery vía Routes funciona
 * 
 * Ejecutar en navegador o con test runner (Jest, Mocha, etc.)
 */

(function () {
  'use strict';

  const MODULES = [
    'facturas',
    'contabilidad',
    'inventario',
    'clientes',
    'proveedores',
    'gastos',
    'empleados',
    'empresa',
    'perfil'
  ];

  const TESTS = {
    coreRoutes: {
      name: 'Core Routes Endpoint',
      async run() {
        try {
          const response = await fetch('/api/v1/core/routes/', {
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
          });
          
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
          
          const data = await response.json();
          
          // Verificar que devuelve las claves esperadas
          const requiredKeys = ['facturas', 'contabilidad', 'inventario', 'clientes', 'proveedores', 'gastos', 'empleados', 'empresa', 'perfil'];
          const missing = requiredKeys.filter(key => !(key in data));
          
          if (missing.length > 0) {
            throw new Error(`Faltan claves en routes: ${missing.join(', ')}`);
          }
          
          // Verificar estructura de facturas
          if (!data.facturas || !data.facturas.datatable) {
            throw new Error('facturas.datatable no encontrado');
          }
          
          // Verificar estructura de contabilidad (subclaves)
          if (!data.contabilidad || !data.contabilidad.cuentas || !data.contabilidad.cuentas.datatable) {
            throw new Error('contabilidad.cuentas.datatable no encontrado');
          }
          
          // Verificar estructura de inventario (subclaves)
          if (!data.inventario || !data.inventario.catalogo || !data.inventario.catalogo.datatable) {
            throw new Error('inventario.catalogo.datatable no encontrado');
          }
          
          // Verificar singleton de empresa
          if (!data.empresa || !data.empresa.singleton) {
            throw new Error('empresa.singleton no encontrado');
          }
          
          // Verificar singleton de perfil
          if (!data.perfil || !data.perfil.singleton) {
            throw new Error('perfil.singleton no encontrado');
          }
          
          return { ok: true, data };
        } catch (err) {
          return { ok: false, error: err.message };
        }
      }
    },
    
    routesHelper: {
      name: 'Routes Helper Disponible',
      async run() {
        try {
          if (typeof window.Routes === 'undefined') {
            throw new Error('window.Routes no está disponible');
          }
          
          if (typeof window.Routes.get !== 'function') {
            throw new Error('Routes.get no es una función');
          }
          
          if (typeof window.Routes.collectionUrl !== 'function') {
            throw new Error('Routes.collectionUrl no es una función');
          }
          
          if (typeof window.Routes.detailUrl !== 'function') {
            throw new Error('Routes.detailUrl no es una función');
          }
          
          if (typeof window.Routes.singletonUrl !== 'function') {
            throw new Error('Routes.singletonUrl no es una función');
          }
          
          // Probar obtener rutas
          const routes = await window.Routes.get('facturas');
          if (!routes || !routes.datatable) {
            throw new Error('Routes.get("facturas") no devuelve datatable');
          }
          
          return { ok: true };
        } catch (err) {
          return { ok: false, error: err.message };
        }
      }
    },
    
    crudHelper: {
      name: 'CRUD Helper Disponible',
      async run() {
        try {
          if (typeof window.CRUD === 'undefined') {
            throw new Error('window.CRUD no está disponible');
          }
          
          if (typeof window.CRUD.create !== 'function') {
            throw new Error('CRUD.create no es una función');
          }
          
          if (typeof window.CRUD.read !== 'function') {
            throw new Error('CRUD.read no es una función');
          }
          
          if (typeof window.CRUD.update !== 'function') {
            throw new Error('CRUD.update no es una función');
          }
          
          if (typeof window.CRUD.delete !== 'function') {
            throw new Error('CRUD.delete no es una función');
          }
          
          return { ok: true };
        } catch (err) {
          return { ok: false, error: err.message };
        }
      }
    },
    
    domUtilsHelper: {
      name: 'DOMUtils Helper Disponible',
      async run() {
        try {
          if (typeof window.DOMUtils === 'undefined') {
            throw new Error('window.DOMUtils no está disponible');
          }
          
          if (typeof window.DOMUtils.waitForVisible !== 'function') {
            throw new Error('DOMUtils.waitForVisible no es una función');
          }
          
          if (typeof window.DOMUtils.getEl !== 'function') {
            throw new Error('DOMUtils.getEl no es una función');
          }
          
          return { ok: true };
        } catch (err) {
          return { ok: false, error: err.message };
        }
      }
    },
    
    datatablesUtilsHelper: {
      name: 'DataTablesUtils Helper Disponible',
      async run() {
        try {
          if (typeof window.DataTablesUtils === 'undefined') {
            throw new Error('window.DataTablesUtils no está disponible');
          }
          
          if (typeof window.DataTablesUtils.initServerSide !== 'function') {
            throw new Error('DataTablesUtils.initServerSide no es una función');
          }
          
          if (typeof window.DataTablesUtils.canUseDataTables !== 'function') {
            throw new Error('DataTablesUtils.canUseDataTables no es una función');
          }
          
          return { ok: true };
        } catch (err) {
          return { ok: false, error: err.message };
        }
      }
    }
  };

  // Exportar para uso en test runner
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TESTS, MODULES };
  }
  
  // Exportar para uso en navegador
  if (typeof window !== 'undefined') {
    window.SINTEL_SMOKE_TESTS = { TESTS, MODULES };
    
    // Función helper para ejecutar todos los tests
    window.runSmokeTests = async function () {
      console.log('🧪 Ejecutando smoke tests...');
      const results = {};
      
      for (const [key, test] of Object.entries(TESTS)) {
        console.log(`  Testing: ${test.name}...`);
        const result = await test.run();
        results[key] = result;
        
        if (result.ok) {
          console.log(`  ✅ ${test.name}: OK`);
        } else {
          console.error(`  ❌ ${test.name}: ${result.error}`);
        }
      }
      
      const passed = Object.values(results).filter(r => r.ok).length;
      const total = Object.keys(results).length;
      
      console.log(`\n📊 Resultados: ${passed}/${total} tests pasaron`);
      
      return {
        passed,
        total,
        results,
        allPassed: passed === total
      };
    };
  }
})();
