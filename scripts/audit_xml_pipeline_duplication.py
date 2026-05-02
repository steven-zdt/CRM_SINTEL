#!/usr/bin/env python
"""
Script de auditoría para detectar duplicación de lógica de procesamiento XML.

[WARNING] POLÍTICA SSoT XML: apps/services/xml_ingest + apps/services/xml_parser son la ÚNICA vía.
Este script detecta cualquier uso de parseo/ingesta XML fuera de estos servicios.
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
SERVICES_XML_DIR = BASE_DIR / 'apps' / 'services' / 'xml_ingest'
SERVICES_PARSER_DIR = BASE_DIR / 'apps' / 'services' / 'xml_parser'
TENANT_APPS_DIR = BASE_DIR / 'apps' / 'tenant'
PUBLIC_APPS_DIR = BASE_DIR / 'apps' / 'public'

# Patrones que indican procesamiento XML (fuera de servicios canónicos)
XML_PROCESSING_PATTERNS = [
    # Funciones de parseo
    r'def\s+parse.*xml',
    r'def\s+parse.*ubl',
    r'def\s+ingest.*xml',
    r'def\s+ingest.*ubl',
    r'def\s+import.*xml',
    r'def\s+import.*ubl',
    # Imports de parsers XML
    r'from\s+lxml\s+import',
    r'from\s+xml\.etree\s+import',
    r'from\s+xml\.dom\s+import',
    r'import\s+lxml',
    r'import\s+xml\.etree',
    # Llamadas a funciones de parseo
    r'parse.*xml\s*\(',
    r'parse.*ubl\s*\(',
    r'ingest.*xml\s*\(',
    r'ingest.*ubl\s*\(',
    # Uso directo de etree
    r'etree\.parse\s*\(',
    r'etree\.fromstring\s*\(',
    r'etree\.ElementTree\s*\(',
]

# Whitelist: archivos permitidos (servicios canónicos)
CANONICAL_WHITELIST = [
    'apps/services/xml_ingest/',
    'apps/services/xml_parser/',
    'apps/tenant/facturas/ubl_parser.py',  # Mapeo UBL→DTO (dominio específico)
    'apps/tenant/facturas/services.py',    # Orquestación (consume xml_ingest)
]

# Errores encontrados
errors: List[Tuple[str, str, int, str]] = []
warnings: List[Tuple[str, str, int, str]] = []


def is_canonical_path(file_path: Path) -> bool:
    """Verifica si el archivo está en la whitelist de servicios canónicos."""
    path_str = str(file_path)
    for whitelist_path in CANONICAL_WHITELIST:
        if whitelist_path in path_str:
            return True
    return False


def check_file_for_xml_processing(file_path: Path) -> None:
    """Verifica un archivo en busca de procesamiento XML no canónico."""
    if is_canonical_path(file_path):
        return  # Skip archivos canónicos
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Ignorar comentarios y docstrings
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            # Buscar patrones de procesamiento XML
            for pattern in XML_PROCESSING_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Verificar si es import de servicios canónicos (permitido)
                    if 'from apps.services.xml_ingest' in line or 'from apps.services.xml_parser' in line:
                        continue
                    if 'import.*xml_ingest' in line or 'import.*xml_parser' in line:
                        continue
                    
                    # Error: procesamiento XML fuera de servicios canónicos
                    rel_path = file_path.relative_to(BASE_DIR)
                    errors.append((
                        str(rel_path),
                        line.strip(),
                        line_num,
                        f"Procesamiento XML detectado fuera de apps/services/xml_*"
                    ))
                    break  # Solo reportar una vez por línea
    except Exception as e:
        warnings.append((str(file_path.relative_to(BASE_DIR)), str(e), 0, "Error leyendo archivo"))


def audit_xml_pipeline():
    """Ejecuta la auditoría de duplicación de pipeline XML."""
    print("[AUDIT] Auditoría de duplicación de pipeline XML...")
    print(f"[DIR] Servicios canónicos: {SERVICES_XML_DIR}, {SERVICES_PARSER_DIR}")
    print()
    
    # Verificar que los servicios canónicos existen
    if not SERVICES_XML_DIR.exists():
        print(f"[WARN] [WARNING]  Servicio canónico no encontrado: {SERVICES_XML_DIR}")
        print("[WARN] Asegúrate de que apps/services/xml_ingest existe")
    
    if not SERVICES_PARSER_DIR.exists():
        print(f"[WARN] [WARNING]  Servicio canónico no encontrado: {SERVICES_PARSER_DIR}")
        print("[WARN] Asegúrate de que apps/services/xml_parser existe")
    
    # Buscar en tenant apps
    if TENANT_APPS_DIR.exists():
        print(f"[SCAN] Escaneando {TENANT_APPS_DIR}...")
        for py_file in TENANT_APPS_DIR.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            check_file_for_xml_processing(py_file)
    
    # Buscar en public apps (si aplica)
    if PUBLIC_APPS_DIR.exists():
        print(f"[SCAN] Escaneando {PUBLIC_APPS_DIR}...")
        for py_file in PUBLIC_APPS_DIR.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            check_file_for_xml_processing(py_file)
    
    # Reportar resultados
    print()
    if errors:
        print(f"[ERROR] Violaciones encontradas: {len(errors)}")
        print()
        for file_path, line, line_num, reason in errors:
            print(f"  [VIOLATION] {file_path}:{line_num}")
            print(f"     [LINE] {line[:80]}...")
            print(f"     [REASON] {reason}")
            print(f"     [TIP] Usa apps/services/xml_ingest o apps/services/xml_parser")
            print()
    else:
        print("[OK] No se encontraron violaciones")
        print("[OK] Todo el procesamiento XML pasa por servicios canónicos")
    
    if warnings:
        print(f"[WARN] Warnings: {len(warnings)}")
        for file_path, error, line_num, reason in warnings[:5]:
            print(f"  [WARN] {file_path}:{line_num} - {reason}")
    
    return len(errors) == 0


def main():
    """Función principal."""
    print("=" * 80)
    print("AUDITORÍA DE DUPLICACIÓN DE PIPELINE XML")
    print("=" * 80)
    print()
    print("[WARNING]  POLÍTICA SSoT XML:")
    print("   - ÚNICA vía: apps/services/xml_ingest + apps/services/xml_parser")
    print("   - apps/tenant/facturas solo orquesta (consume servicios)")
    print("   - Prohibido parseo/ingesta XML fuera de servicios canónicos")
    print()
    
    success = audit_xml_pipeline()
    
    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print()
    
    if errors:
        print(f"[FAIL] AUDITORÍA FALLÓ - {len(errors)} violaciones encontradas")
        print("[FAIL] Corrige las violaciones antes de continuar")
        sys.exit(1)
    else:
        print("[OK] AUDITORÍA PASÓ - Sin violaciones encontradas")
        if warnings:
            print(f"[WARN] {len(warnings)} warnings (revisar manualmente)")
        sys.exit(0)


if __name__ == "__main__":
    main()
