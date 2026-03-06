#!/usr/bin/env python3
"""
Script de auditoría automática para refactor frontend SINTEL (Ola 5)

Busca infracciones contra los estándares:
- URLs hardcodeadas '/api/v1/'
- getCookie('csrftoken')
- setTimeout para visibilidad
- DataTables sin initServerSide

Salida: auditoria_final.json + AUDITORIA_FINAL.md
Exit code != 0 si hay infracciones
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Directorio base del proyecto
BASE_DIR = Path(__file__).parent.parent
JS_DIR = BASE_DIR / 'apps' / 'tenant' / 'core' / 'static' / 'core' / 'js'

# Patrones prohibidos
PATTERNS = {
    'hardcoded_urls': [
        r"/api/v1/",
        r"['\"]/api/v1/",
        r"`/api/v1/",
    ],
    'getcookie_csrf': [
        r"getCookie\(['\"]csrftoken['\"]\)",
        r"getCookie\(['\"]csrftoken['\"]",
    ],
    'settimeout_visibility': [
        r"setTimeout\([^)]*visible",
        r"setTimeout\([^)]*\.is\(['\"]:visible",
        r"setTimeout\([^)]*\.is\(['\"]:hidden",
        r"setTimeout\([^)]*offsetHeight",
        r"setTimeout\([^)]*getBoundingClientRect",
    ],
    'datatables_no_initserver': [
        r"\.DataTable\([^)]*serverSide:\s*true",
        r"\.DataTable\([^)]*ajax:\s*\{",
    ],
}

# Excepciones (archivos que pueden tener estos patrones legítimamente)
EXCEPTIONS = {
    'hardcoded_urls': [
        'helpers/routes.js',  # Puede tener fallbacks
        'lib/api-helpers.js',  # Puede tener constantes
        'lib/http.js',  # Puede tener constantes
    ],
    'getcookie_csrf': [
        'lib/http.js',  # Implementación de getCookie
        'lib/api-helpers.js',  # Implementación de getCSRF
    ],
    'settimeout_visibility': [
        # setTimeout para cerrar modales es válido
    ],
    'datatables_no_initserver': [
        # DataTables client-side son válidos en Ola 4
    ],
}

def find_js_files() -> List[Path]:
    """Encuentra todos los archivos .js en el directorio JS"""
    js_files = []
    for root, dirs, files in os.walk(JS_DIR):
        # Ignorar node_modules y otros directorios
        if 'node_modules' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith('.js'):
                js_files.append(Path(root) / file)
    return js_files

def check_file(file_path: Path) -> Dict[str, List[Dict]]:
    """Revisa un archivo en busca de infracciones"""
    relative_path = file_path.relative_to(BASE_DIR)
    violations = {
        'hardcoded_urls': [],
        'getcookie_csrf': [],
        'settimeout_visibility': [],
        'datatables_no_initserver': [],
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return violations
    
    # Verificar si el archivo está en excepciones
    rel_str = str(relative_path).replace('\\', '/')
    
    # Patrón 1: URLs hardcodeadas
    if 'hardcoded_urls' not in [e.replace('\\', '/') for e in EXCEPTIONS.get('hardcoded_urls', [])]:
        for pattern in PATTERNS['hardcoded_urls']:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    # Excluir comentarios y strings que sean parte de fallbacks documentados
                    if '// TODO' in line or '// Fallback' in line or 'fallback' in line.lower():
                        continue
                    violations['hardcoded_urls'].append({
                        'line': i,
                        'content': line.strip(),
                        'pattern': pattern
                    })
    
    # Patrón 2: getCookie('csrftoken')
    if 'getcookie_csrf' not in [e.replace('\\', '/') for e in EXCEPTIONS.get('getcookie_csrf', [])]:
        for pattern in PATTERNS['getcookie_csrf']:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    # Excluir comentarios y definiciones de función
                    if 'function getCookie' in line or 'const getCookie' in line or '//' in line:
                        continue
                    violations['getcookie_csrf'].append({
                        'line': i,
                        'content': line.strip(),
                        'pattern': pattern
                    })
    
    # Patrón 3: setTimeout para visibilidad
    for pattern in PATTERNS['settimeout_visibility']:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                # Excluir setTimeout para cerrar modales (que es válido)
                if 'modal' in line.lower() or 'hide' in line.lower() or 'close' in line.lower():
                    continue
                violations['settimeout_visibility'].append({
                    'line': i,
                    'content': line.strip(),
                    'pattern': pattern
                })
    
    # Patrón 4: DataTables sin initServerSide
    # Solo verificar si hay serverSide: true pero no usa initServerSide
    has_server_side = any('serverSide' in line and 'true' in line for line in lines)
    has_init_server_side = any('initServerSide' in line for line in lines)
    
    if has_server_side and not has_init_server_side:
        # Buscar la línea donde se inicializa DataTable
        for i, line in enumerate(lines, 1):
            if '.DataTable(' in line and 'serverSide' in ''.join(lines[max(0, i-5):i+5]):
                violations['datatables_no_initserver'].append({
                    'line': i,
                    'content': line.strip(),
                    'pattern': 'DataTable con serverSide pero sin initServerSide'
                })
                break
    
    # Filtrar violaciones vacías
    return {k: v for k, v in violations.items() if v}

def audit_all() -> Tuple[Dict, int]:
    """Audita todos los archivos JS"""
    js_files = find_js_files()
    all_violations = {}
    total_violations = 0
    
    for js_file in js_files:
        violations = check_file(js_file)
        if violations:
            rel_path = str(js_file.relative_to(BASE_DIR)).replace('\\', '/')
            all_violations[rel_path] = violations
            total_violations += sum(len(v) for v in violations.values())
    
    return all_violations, total_violations

def generate_markdown_report(violations: Dict, total: int) -> str:
    """Genera reporte en Markdown"""
    lines = [
        '# AUDITORÍA FINAL - Refactor Frontend SINTEL (Ola 5)',
        '',
        f'**Fecha:** {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'**Total de infracciones:** {total}',
        '',
        '## Resumen por Tipo',
        '',
    ]
    
    # Contar por tipo
    type_counts = {
        'hardcoded_urls': 0,
        'getcookie_csrf': 0,
        'settimeout_visibility': 0,
        'datatables_no_initserver': 0,
    }
    
    for file_violations in violations.values():
        for vtype, vlist in file_violations.items():
            type_counts[vtype] += len(vlist)
    
    lines.extend([
        f'- **URLs hardcodeadas:** {type_counts["hardcoded_urls"]}',
        f'- **getCookie("csrftoken"):** {type_counts["getcookie_csrf"]}',
        f'- **setTimeout para visibilidad:** {type_counts["settimeout_visibility"]}',
        f'- **DataTables sin initServerSide:** {type_counts["datatables_no_initserver"]}',
        '',
        '## Detalle por Archivo',
        '',
    ])
    
    if not violations:
        lines.append('✅ **No se encontraron infracciones.**')
    else:
        for file_path, file_violations in sorted(violations.items()):
            lines.append(f'### {file_path}')
            lines.append('')
            
            for vtype, vlist in file_violations.items():
                if vlist:
                    type_names = {
                        'hardcoded_urls': 'URLs hardcodeadas',
                        'getcookie_csrf': 'getCookie("csrftoken")',
                        'settimeout_visibility': 'setTimeout para visibilidad',
                        'datatables_no_initserver': 'DataTables sin initServerSide',
                    }
                    lines.append(f'#### {type_names.get(vtype, vtype)} ({len(vlist)} encontradas)')
                    lines.append('')
                    for v in vlist[:10]:  # Limitar a 10 por tipo
                        lines.append(f'- Línea {v["line"]}: `{v["content"][:80]}...`')
                    if len(vlist) > 10:
                        lines.append(f'- ... y {len(vlist) - 10} más')
                    lines.append('')
    
    return '\n'.join(lines)

def main():
    """Función principal"""
    print('🔍 Ejecutando auditoría frontend...')
    
    violations, total = audit_all()
    
    # Generar JSON
    json_path = BASE_DIR / 'auditoria_final.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_violations': total,
            'files_affected': len(violations),
            'violations': violations,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    # Generar Markdown
    md_path = BASE_DIR / 'AUDITORIA_FINAL.md'
    md_content = generate_markdown_report(violations, total)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f'✅ Auditoría completada: {total} infracciones encontradas en {len(violations)} archivos')
    print(f'📄 Reportes generados:')
    print(f'   - {json_path}')
    print(f'   - {md_path}')
    
    # Exit code != 0 si hay infracciones
    if total > 0:
        print(f'\n❌ CI fallará: {total} infracciones detectadas')
        exit(1)
    else:
        print('\n✅ CI pasará: 0 infracciones')
        exit(0)

if __name__ == '__main__':
    main()
