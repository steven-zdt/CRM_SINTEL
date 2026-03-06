#!/usr/bin/env node
/**
 * verifica_core_contaminacion.js
 * 
 * Escaneo de:
 *  1) Contaminación de Core: tenant/<app>/ dentro de apps/tenant/core/templates/tenant/core/partials
 *  2) Duplicados legacy en Core (getCookie, setTimeout visibilidad, inicialización DataTables inline, mini-http/mini-csrf fuera de lib oficial)
 * 
 * Salida:
 *  - auditoria_core_contaminacion.json
 *  - AUDITORIA_CORE_CONTAMINACION.md
 * Exit code != 0 si hay infracciones.
 */

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();

// Rutas a inspeccionar
const CORE_PARTIALS_DIR = path.join(ROOT, 'apps/tenant/core/templates/tenant/core/partials');
const CORE_STATIC_DIR   = path.join(ROOT, 'apps/tenant/core/static/tenant/core/js');

const results = {
  timestamp: new Date().toISOString(),
  contamination: [],
  legacy: [],
  summary: {
    contamination_count: 0,
    legacy_count: 0
  }
};

// Helpers
function walk(dir, exts = ['.html', '.js', '.ts', '.mjs', '.cjs']) {
  const files = [];
  function _walk(d) {
    if (!fs.existsSync(d)) return;
    const entries = fs.readdirSync(d, { withFileTypes: true });
    for (const e of entries) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) _walk(full);
      else if (exts.includes(path.extname(e.name))) files.push(full);
    }
  }
  _walk(dir);
  return files;
}

function rel(p) { return path.relative(ROOT, p).replace(/\\/g, '/'); }

function testContaminationInCorePartials(filePath) {
  // Busca cualquier 'tenant/<algo>' que NO sea core/
  const text = fs.readFileSync(filePath, 'utf8');
  const regex = /tenant\/(?!core\/)[A-Za-z0-9_\-]+\/?/g;
  const matches = text.match(regex);
  if (matches) {
    results.contamination.push({
      file: rel(filePath),
      matches: [...new Set(matches)]
    });
  }
}

function testLegacyInCore(filePath) {
  const text = fs.readFileSync(filePath, 'utf8');
  const localFindings = [];
  
  // getCookie('csrftoken')
  if (/getCookie\(['"]csrftoken['"]\)/.test(text)) {
    localFindings.push("getCookie('csrftoken')");
  }
  
  // setTimeout( como heurística de visibilidad inline en Core partials
  if (/setTimeout\s*\(/.test(text) && filePath.includes('/templates/')) {
    localFindings.push('setTimeout( (posible visibilidad inline)');
  }
  
  // Inicialización directa de DataTables
  if (/\.(DataTable|dataTable)\s*\(|new\s+DataTable\s*\(|\$\s*\.fn\s*\.DataTable/.test(text)) {
    localFindings.push('Inicialización directa DataTables (inline)');
  }
  
  // Mini-http o réplica de http.js fuera de lib oficial (heurística)
  if (/fetch\s*\(/.test(text) && !/API_HELPERS\s*\.\s*safeFetchJson/.test(text)) {
    // Sólo marcar si está en Core estáticos, excluyendo helpers oficiales
    if (filePath.includes('/static/tenant/core/js/') && !filePath.includes('/static/tenant/core/js/lib/')) {
      localFindings.push('fetch directo fuera de http.js oficial (sospechoso)');
    }
  }
  
  if (localFindings.length > 0) {
    results.legacy.push({
      file: rel(filePath),
      findings: localFindings
    });
  }
}

// 1) Contaminación en partials Core
const corePartials = walk(CORE_PARTIALS_DIR, ['.html']);
corePartials.forEach(testContaminationInCorePartials);

// 2) Duplicados legacy
const coreHtmlAndJs = [
  ...walk(CORE_PARTIALS_DIR, ['.html']),
  ...walk(CORE_STATIC_DIR, ['.js', '.mjs', '.cjs', '.ts'])
];
coreHtmlAndJs.forEach(testLegacyInCore);

// Resumen
results.summary.contamination_count = results.contamination.length;
results.summary.legacy_count = results.legacy.length;

// Emitir JSON
const jsonOut = path.join(ROOT, 'auditoria_core_contaminacion.json');
fs.writeFileSync(jsonOut, JSON.stringify(results, null, 2), 'utf8');

// Emitir Markdown
const mdOut = path.join(ROOT, 'AUDITORIA_CORE_CONTAMINACION.md');
const md = [];
md.push('# Auditoría de Contaminación Core y Legacy');
md.push(`**Fecha:** ${results.timestamp}`);
md.push('');
md.push('## Resumen');
md.push(`- Contaminación Core (partials con tenant/<app>/): **${results.summary.contamination_count}**`);
md.push(`- Legacy duplicado (Core): **${results.summary.legacy_count}**`);
md.push('');
md.push('---');
md.push('## Detalle de Contaminación (Core partials)');
if (results.contamination.length === 0) {
  md.push('- [OK] Sin hallazgos');
} else {
  for (const c of results.contamination) {
    md.push(`- **${c.file}**`);
    md.push(`  - matches: ${c.matches.join(', ')}`);
  }
}
md.push('');
md.push('---');
md.push('## Detalle Legacy en Core (partials/static)');
if (results.legacy.length === 0) {
  md.push('- [OK] Sin hallazgos');
} else {
  for (const l of results.legacy) {
    md.push(`- **${l.file}**`);
    md.push(`  - findings: ${l.findings.join(' | ')}`);
  }
}
fs.writeFileSync(mdOut, md.join('\n'), 'utf8');

// Exit code != 0 si hay infracciones
const violations = results.summary.contamination_count + results.summary.legacy_count;
if (violations > 0) {
  console.error(`\n[ERROR] Infracciones detectadas: ${violations}. Revisa AUDITORIA_CORE_CONTAMINACION.md\n`);
  process.exit(2);
}

console.log('\n[OK] Sin infracciones en Core. Auditoria OK.\n');
process.exit(0);
