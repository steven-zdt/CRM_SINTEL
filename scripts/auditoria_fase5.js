#!/usr/bin/env node
/**
 * Auditoría Fase 5 (Pruebas y CI)
 * 
 * Detecta:
 * - Contaminación Core (partials): tenant/<app> ≠ core dentro de tenant/core/partials
 * - Re-init DataTables (patrones peligrosos)
 * - setTimeout usado para "visibilidad" (recomendado awaitVisibleAny/onVisibleOnce)
 * 
 * ⚠️ FASE 5: Script que falla CI si detecta infracciones
 */

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const CORE_PARTIALS = path.join(ROOT, 'apps/tenant/core/templates/tenant/core/partials');
const APP_STATIC = path.join(ROOT, 'apps/tenant');
const APP_TEMPLATES = path.join(ROOT, 'apps/tenant');

const results = {
  timestamp: new Date().toISOString(),
  contamination: [],
  reinit: [],
  timeouts: [],
  summary: {
    contamination: 0,
    reinit: 0,
    timeouts: 0
  }
};

/**
 * Recorre directorio recursivamente buscando archivos con extensiones específicas
 */
function walk(dir, exts = ['.html', '.js', '.mjs', '.cjs', '.ts']) {
  const out = [];
  
  function _walk(d) {
    if (!fs.existsSync(d)) return;
    
    try {
      const entries = fs.readdirSync(d, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(d, entry.name);
        
        // Ignorar node_modules, .git, etc.
        if (entry.isDirectory()) {
          if (!entry.name.startsWith('.') && entry.name !== 'node_modules') {
            _walk(fullPath);
          }
        } else if (entry.isFile()) {
          const ext = path.extname(entry.name);
          if (exts.includes(ext)) {
            out.push(fullPath);
          }
        }
      }
    } catch (err) {
      // Ignorar errores de permisos
      console.warn(`[auditoria_fase5] No se pudo leer directorio: ${d}`, err.message);
    }
  }
  
  _walk(dir);
  return out;
}

/**
 * Obtiene ruta relativa desde ROOT
 */
const rel = (p) => path.relative(ROOT, p);

/**
 * 1) Contaminación Core: tenant/(?!core/) dentro de tenant/core/partials
 */
function checkContamination() {
  if (!fs.existsSync(CORE_PARTIALS)) {
    console.warn(`[auditoria_fase5] Directorio no encontrado: ${CORE_PARTIALS}`);
    return;
  }

  // Patrón: tenant/<app> donde <app> no es 'core'
  const reContam = /tenant\/(?!core\/)[A-Za-z0-9_\-]+/g;
  
  for (const f of walk(CORE_PARTIALS, ['.html'])) {
    try {
      const content = fs.readFileSync(f, 'utf8');
      const matches = content.match(reContam);
      
      if (matches) {
        results.contamination.push({
          file: rel(f),
          matches: [...new Set(matches)]
        });
      }
    } catch (err) {
      console.warn(`[auditoria_fase5] Error leyendo ${f}:`, err.message);
    }
  }
}

/**
 * 2) Re-init DataTables: patrones comunes peligrosos
 */
function checkReinit() {
  // Patrones de inicialización directa
  const reReinit = [
    /\.DataTable\s*\(\s*\{/g,  // inicialización directa repetida
    /new\s+DataTable\s*\(/g     // nueva API
  ];
  
  for (const f of walk(APP_STATIC, ['.js', '.mjs', '.cjs', '.ts'])) {
    try {
      const content = fs.readFileSync(f, 'utf8');
      
      // Contar ocurrencias de cada patrón
      let totalHits = 0;
      for (const pattern of reReinit) {
        const matches = content.match(pattern);
        if (matches) {
          totalHits += matches.length;
        }
      }
      
      // Si hay más de una inicialización, puede ser re-init peligroso
      // (admitimos un init por tabla en *.page.js; la auditoría busca duplicados obvios)
      if (totalHits > 1) {
        results.reinit.push({
          file: rel(f),
          count: totalHits
        });
      }
    } catch (err) {
      console.warn(`[auditoria_fase5] Error leyendo ${f}:`, err.message);
    }
  }
}

/**
 * 3) setTimeout sospechoso (sin awaitVisibleAny/onVisibleOnce)
 */
function checkTimeouts() {
  const reTimeout = /setTimeout\s*\(/g;
  
  for (const f of walk(APP_STATIC, ['.js', '.mjs', '.cjs', '.ts'])) {
    try {
      const content = fs.readFileSync(f, 'utf8');
      const hits = content.match(reTimeout);
      
      if (hits) {
        // Heurística: si el archivo contiene awaitVisibleAny/onVisibleOnce,
        // lo toleramos; si no, lo marcamos como sospechoso
        // (posible gestión de visibilidad incorrecta)
        const hasVisibilityHelpers = /awaitVisibleAny|onVisibleOnce/.test(content);
        
        if (!hasVisibilityHelpers) {
          results.timeouts.push({
            file: rel(f),
            count: hits.length
          });
        }
      }
    } catch (err) {
      console.warn(`[auditoria_fase5] Error leyendo ${f}:`, err.message);
    }
  }
}

/**
 * Genera reporte Markdown
 */
function generateMarkdownReport() {
  const lines = [
    '# Auditoría Fase 5 (Pruebas y CI)',
    `**Fecha:** ${results.timestamp}`,
    '',
    '## Resumen',
    `- Contaminación Core: **${results.summary.contamination}**`,
    `- Re-init sospechoso: **${results.summary.reinit}**`,
    `- setTimeout sospechoso: **${results.summary.timeouts}**`,
    '',
    '---',
    '',
    '## Contaminación Core',
    results.contamination.length
      ? results.contamination.map(c => `- \`${c.file}\` → ${c.matches.join(', ')}`).join('\n')
      : '- ✅ Sin hallazgos',
    '',
    '## Re-init sospechoso',
    results.reinit.length
      ? results.reinit.map(r => `- \`${r.file}\` (${r.count} ocurrencias)`).join('\n')
      : '- ✅ Sin hallazgos',
    '',
    '## setTimeout sospechoso (sin awaitVisibleAny/onVisibleOnce)',
    results.timeouts.length
      ? results.timeouts.map(t => `- \`${t.file}\` (${t.count} ocurrencias)`).join('\n')
      : '- ✅ Sin hallazgos',
    ''
  ];
  
  return lines.join('\n');
}

/**
 * Ejecutar auditoría
 */
function main() {
  console.log('[auditoria_fase5] Iniciando auditoría...\n');
  
  checkContamination();
  checkReinit();
  checkTimeouts();
  
  // Actualizar resumen
  results.summary = {
    contamination: results.contamination.length,
    reinit: results.reinit.length,
    timeouts: results.timeouts.length
  };
  
  // Generar reportes
  const markdown = generateMarkdownReport();
  const jsonPath = path.join(ROOT, 'auditoria_fase5.json');
  const mdPath = path.join(ROOT, 'AUDITORIA_FASE5.md');
  
  try {
    fs.writeFileSync(jsonPath, JSON.stringify(results, null, 2), 'utf8');
    fs.writeFileSync(mdPath, markdown, 'utf8');
    
    console.log(`[auditoria_fase5] Reportes generados:`);
    console.log(`  - ${rel(jsonPath)}`);
    console.log(`  - ${rel(mdPath)}\n`);
  } catch (err) {
    console.error(`[auditoria_fase5] Error escribiendo reportes:`, err);
    process.exit(1);
  }
  
  // Verificar infracciones
  const violations = results.summary.contamination + results.summary.reinit + results.summary.timeouts;
  
  if (violations > 0) {
    console.error(`\n❌ Auditoría Fase 5: ${violations} infracción(es) detectada(s).`);
    console.error(`   Revisa AUDITORIA_FASE5.md para más detalles.\n`);
    process.exit(2);
  }
  
  console.log('\n✅ Auditoría Fase 5: sin infracciones\n');
  process.exit(0);
}

// Ejecutar
main();
