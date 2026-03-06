#!/usr/bin/env python
"""
Auditoría de hardcodes de marca en código.

⚠️ POLÍTICA:
- Prohíbe literales de marca (SINTEL, ACME, etc.) fuera de fixtures/tests
- Branding debe venir de BD/tenant, no literales
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent

# Hardcodes prohibidos
PROHIBITED_BRANDS = ['SINTEL', 'ACME', 'Mi Empresa', 'Mi Empresa S.A.']

# Directorios permitidos (fixtures, tests, documentación)
ALLOWED_DIRS = ['fixtures', 'tests', 'documentacion', 'scripts']

# Errores encontrados
errors: List[Tuple[str, str, int]] = []


def is_allowed_path(file_path: Path) -> bool:
    """Verifica si el archivo está en un directorio permitido."""
    rel_path = file_path.relative_to(PROJECT_ROOT)
    parts = rel_path.parts
    
    for allowed in ALLOWED_DIRS:
        if allowed in parts:
            return True
    return False


def check_file(file_path: Path) -> None:
    """Verifica un archivo por hardcodes de marca."""
    if is_allowed_path(file_path):
        return  # Permitir en fixtures/tests/documentación
    
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for brand in PROHIBITED_BRANDS:
                # Buscar el brand como palabra completa (no parte de otra palabra)
                pattern = re.compile(rf'\b{re.escape(brand)}\b', re.IGNORECASE)
                if pattern.search(line):
                    # Ignorar comentarios que explican la política
                    if 'POLÍTICA' in line or 'hardcode' in line.lower() or 'prohibido' in line.lower():
                        continue
                    errors.append((str(file_path), f"Hardcode de marca '{brand}' encontrado", i))
    except UnicodeDecodeError:
        # Ignorar archivos binarios
        pass


def main():
    """Ejecuta la auditoría."""
    print("🔍 Auditoría de hardcodes de marca...")
    print("=" * 70)
    
    # Buscar en apps/tenant
    tenant_dir = PROJECT_ROOT / 'apps' / 'tenant'
    if tenant_dir.exists():
        for file_path in tenant_dir.rglob('*.{py,html,js,css}'):
            check_file(file_path)
    
    # Buscar en static
    static_dir = PROJECT_ROOT / 'apps' / 'tenant'
    if static_dir.exists():
        for file_path in static_dir.rglob('*.{html,js,css}'):
            check_file(file_path)
    
    # Reportar resultados
    print(f"\n✅ Verificaciones completadas")
    
    if errors:
        print(f"\n❌ ERRORES ({len(errors)}):")
        for file_path, message, line in errors:
            print(f"   {file_path}:{line} - {message}")
        print("\n❌ Auditoría FALLIDA")
        print("   ⚠️  Branding debe venir de BD/tenant, no literales")
        sys.exit(1)
    else:
        print("\n✅ Auditoría EXITOSA - Sin hardcodes de marca")
        sys.exit(0)


if __name__ == '__main__':
    main()
