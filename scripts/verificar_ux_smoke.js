#!/usr/bin/env node
/**
 * Script de verificación para UX Smoke Runner
 * Verifica que los archivos estén correctos y listos para ejecutar
 */

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const WORKSPACE_HTML = path.join(ROOT, 'apps/tenant/core/templates/tenant/core/workspace.html');
const UX_SMOKE_JS = path.join(ROOT, 'apps/tenant/core/static/core/js/tests/workspace_ux_smoke.js');

console.log('🧪 Verificando UX Smoke Runner...\n');

let errors = [];
let warnings = [];

// 1. Verificar que workspace.html existe y tiene el panel
if (fs.existsSync(WORKSPACE_HTML)) {
  const content = fs.readFileSync(WORKSPACE_HTML, 'utf8');
  
  if (!content.includes('ux-smoke-panel')) {
    errors.push('❌ workspace.html no contiene ux-smoke-panel');
  } else {
    console.log('✅ Panel de test encontrado en workspace.html');
  }
  
  if (!content.includes('ux-btn-run-all')) {
    errors.push('❌ workspace.html no contiene botón ux-btn-run-all');
  } else {
    console.log('✅ Botón "Ejecutar Todo" encontrado');
  }
  
  if (!content.includes('ux-log')) {
    errors.push('❌ workspace.html no contiene área de log (ux-log)');
  } else {
    console.log('✅ Área de log encontrada');
  }
  
  if (!content.includes('workspace_ux_smoke.js')) {
    errors.push('❌ workspace.html no carga workspace_ux_smoke.js');
  } else {
    console.log('✅ Script workspace_ux_smoke.js referenciado');
  }
} else {
  errors.push(`❌ workspace.html no encontrado: ${WORKSPACE_HTML}`);
}

// 2. Verificar que workspace_ux_smoke.js existe
if (fs.existsSync(UX_SMOKE_JS)) {
  const content = fs.readFileSync(UX_SMOKE_JS, 'utf8');
  
  // Verificar funciones principales
  const requiredFunctions = ['click', 'type', 'select', 'waitFor', 'navigateToTab'];
  for (const fn of requiredFunctions) {
    if (!content.includes(`function ${fn}`)) {
      warnings.push(`⚠️  Función ${fn} no encontrada`);
    }
  }
  
  // Verificar suites
  const suites = [
    'clientes', 'proveedores', 'gastos', 'empleados',
    'facturas', 'contabilidad_cuentas', 'contabilidad_asientos',
    'inventario_catalogo', 'inventario_activos', 'empresa', 'perfil'
  ];
  
  for (const suite of suites) {
    if (!content.includes(`async ${suite}()`)) {
      warnings.push(`⚠️  Suite ${suite} no encontrada`);
    }
  }
  
  console.log('✅ workspace_ux_smoke.js encontrado y verificado');
  console.log(`   - ${suites.length} suites definidas`);
} else {
  errors.push(`❌ workspace_ux_smoke.js no encontrado: ${UX_SMOKE_JS}`);
}

// 3. Resumen
console.log('\n' + '='.repeat(50));
if (errors.length === 0 && warnings.length === 0) {
  console.log('✅ Verificación completada sin errores\n');
  console.log('📋 Para ejecutar los tests:');
  console.log('   1. Inicia el servidor Django');
  console.log('   2. Visita: http://localhost:8000/workspace/?uxsmoke=1');
  console.log('   3. El panel aparecerá en la parte superior');
  console.log('   4. Haz click en "Ejecutar Todo" o en una suite individual\n');
  process.exit(0);
} else {
  if (errors.length > 0) {
    console.log('\n❌ Errores encontrados:');
    errors.forEach(e => console.log(`   ${e}`));
  }
  if (warnings.length > 0) {
    console.log('\n⚠️  Advertencias:');
    warnings.forEach(w => console.log(`   ${w}`));
  }
  console.log('');
  process.exit(errors.length > 0 ? 1 : 0);
}
