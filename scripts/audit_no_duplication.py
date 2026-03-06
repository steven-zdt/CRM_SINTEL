#!/usr/bin/env python
"""
Script de auditoría: Detecta lógica de parsing XML fuera de apps/services/xml_*

⚠️ OBJETIVO: Garantizar SSoT - Toda la lógica de parsing XML debe estar en:
- apps/services/xml_parser/
- apps/services/xml_ingest/

Este script busca:
- Imports de lxml.etree fuera de apps/services/xml_*
- Funciones que parsean XML (busca patrones como 'parse', 'xml', 'ubl')
- Clases que heredan de parsers fuera del directorio canónico

Uso:
    python scripts/audit_no_duplication.py
"""
import os
import re
import sys
from pathlib import Path

# Directorios permitidos para parsing XML
ALLOWED_DIRS = [
    'apps/services/xml_parser',
    'apps/services/xml_ingest',
]

# Directorios a excluir de la búsqueda
EXCLUDE_DIRS = [
    '__pycache__',
    '.git',
    'node_modules',
    'venv',
    'env',
    '.venv',
    'migrations',
    'static',
    'media',
]

# Patrones sospechosos de parsing XML
SUSPICIOUS_PATTERNS = [
    (r'from lxml', 'Import de lxml fuera de apps/services/xml_*'),
    (r'import lxml', 'Import de lxml fuera de apps/services/xml_*'),
    (r'etree\.', 'Uso de etree fuera de apps/services/xml_*'),
    (r'parse.*xml|xml.*parse', 'Función parse XML fuera de apps/services/xml_*'),
    (r'class.*Parser', 'Clase Parser fuera de apps/services/xml_*'),
]

# Extensiones de archivos a revisar
PYTHON_EXTENSIONS = ['.py']


def is_allowed_path(file_path: Path) -> bool:
    """Verifica si el archivo está en un directorio permitido."""
    file_str = str(file_path)
    return any(allowed in file_str for allowed in ALLOWED_DIRS)


def should_exclude_path(file_path: Path) -> bool:
    """Verifica si el archivo debe ser excluido de la búsqueda."""
    parts = file_path.parts
    return any(excluded in parts for excluded in EXCLUDE_DIRS)


def find_suspicious_files(root_dir: Path) -> list:
    """Encuentra archivos con patrones sospechosos de parsing XML."""
    violations = []
    
    for py_file in root_dir.rglob('*.py'):
        # Excluir archivos en directorios no permitidos
        if should_exclude_path(py_file):
            continue
        
        # Si está en directorio permitido, no es violación
        if is_allowed_path(py_file):
            continue
        
        # Leer contenido del archivo
        try:
            content = py_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"WARNING: No se pudo leer {py_file}: {e}", file=sys.stderr)
            continue
        
        # Buscar patrones sospechosos
        for pattern, description in SUSPICIOUS_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                violations.append({
                    'file': str(py_file.relative_to(root_dir)),
                    'line': line_num,
                    'pattern': pattern,
                    'description': description,
                    'match': match.group(0)
                })
    
    return violations


def main():
    """Función principal del script de auditoría."""
    # Obtener directorio raíz del proyecto
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    
    print("Auditoria: Deteccion de logica XML fuera de apps/services/xml_*")
    print("=" * 70)
    
    violations = find_suspicious_files(root_dir)
    
    if not violations:
        print("OK: No se encontraron violaciones. Todo el parsing XML esta en apps/services/xml_*")
        return 0
    
    print(f"ERROR: Se encontraron {len(violations)} violacion(es):\n")
    
    # Agrupar por archivo
    by_file = {}
    for v in violations:
        file_path = v['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(v)
    
    # Mostrar violaciones
    for file_path, file_violations in sorted(by_file.items()):
        print(f"\nArchivo: {file_path}")
        for v in file_violations:
            print(f"   Linea {v['line']}: {v['description']}")
            print(f"   -> {v['match']}")
    
    print("\n" + "=" * 70)
    print("RECOMENDACION: Mover la logica de parsing XML a apps/services/xml_*")
    print("   - Parsers: apps/services/xml_parser/")
    print("   - Ingesta: apps/services/xml_ingest/")
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
