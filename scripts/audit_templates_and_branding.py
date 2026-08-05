#!/usr/bin/env python
"""
Script de auditoría de templates y hardcodes de marca en TENANT_APPS.

Verifica:
- Templates con namespacing correcto y herencia de base
- Partials reutilizables
- Ausencia de hardcodes de marca (SINTEL, ACME, etc.)
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
TENANT_APPS_DIR = BASE_DIR / "apps" / "tenant"
BRANDING_HARDCODES = ["SINTEL", "ACME", "Mi Empresa", "sintel.net.co"]
ALLOWED_EXTENSIONS = [".html", ".py", ".js", ".css"]
EXCLUDE_PATTERNS = [
    "**/tests/**",
    "**/test_*.py",
    "**/fixtures/**",
    "**/migrations/**",
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/venv/**",
]

errors = []
warnings = []


def should_exclude_file(file_path: Path) -> bool:
    """Verifica si un archivo debe ser excluido de la auditoría."""
    path_str = str(file_path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern.replace("**/", "") in path_str or pattern.replace("**", "") in path_str:
            return True
    return False


def check_template_structure(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Verifica estructura de template:
    - Debe extender una base ({% extends %}) o ser un partial/base
    - Debe usar partials dentro de bloques ({% include %} dentro de {% block %})
    """
    issues = []
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    
    # Excluir archivos de test
    if "test" in file_path.name.lower() or "tests" in str(file_path):
        return True, []  # Archivos de test no se auditan
    
    # Verificar que extiende una base
    if "{% extends" not in content and "{% load" in content:
        # Si tiene {% load %} pero no {% extends %}, puede ser un partial o base
        if "_" in file_path.name or "partials" in str(file_path) or "base.html" in file_path.name:
            pass  # Es un partial o base, está bien
        else:
            issues.append("Template no extiende una base (falta {% extends %})")
    
    # Verificar uso de partials
    if "{% include" in content:
        # Verificar que los includes estén dentro de bloques (opcional pero recomendado)
        lines = content.split('\n')
        in_block = False
        for i, line in enumerate(lines, 1):
            if "{% block" in line:
                in_block = True
            elif "{% endblock" in line:
                in_block = False
            elif "{% include" in line and not in_block:
                # Warning: include fuera de bloque (no crítico)
                warnings.append(f"{file_path}:{i} - include fuera de block (recomendado dentro)")
    
    return len(issues) == 0, issues


def check_branding_hardcodes(file_path: Path) -> List[str]:
    """Busca hardcodes de marca en el archivo."""
    issues = []
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    lines = content.split('\n')
    
    for line_idx, line in enumerate(lines, 1):
        line_lower = line.lower()
        line_stripped = line.strip()
        
        # Excluir líneas que son claramente ejemplos o comentarios
        if any(exclude in line_lower for exclude in [
            '# ejemplo', '# example', 'ejemplo de', 'example of',
            'ejemplo:', 'example:', 'ejemplo respuesta', 'example response',
            'comentario', 'comment', 'todo:', 'fixme:', 'note:'
        ]):
            continue
        
        # Excluir comentarios HTML
        if line_stripped.startswith('<!--') or (line_stripped.startswith('*') and 'ejemplo' in line_lower):
            continue
        
        # Excluir docstrings que son ejemplos
        if '"""' in line and ('ejemplo' in line_lower or 'example' in line_lower):
            continue
        
        # Buscar hardcodes
        for hardcode in BRANDING_HARDCODES:
            pattern = re.compile(re.escape(hardcode), re.IGNORECASE)
            if pattern.search(line):
                # Verificar que no esté en un string de ejemplo o comentario
                if '"' in line and ('ejemplo' in line_lower[:50] or 'example' in line_lower[:50]):
                    continue
                
                issues.append(f"{file_path}:{line_idx} - Hardcode de marca encontrado: '{hardcode}' en: {line_stripped[:80]}")
    
    return issues


def check_namespacing(file_path: Path) -> Tuple[bool, str]:
    """
    Verifica que el template esté en la estructura correcta:
    templates/<app>/... o templates/<app>/<namespace>/...
    """
    # Excluir archivos de test
    if "test" in file_path.name.lower() or "tests" in str(file_path):
        return True, ""  # Archivos de test no se auditan
    
    parts = file_path.parts
    try:
        # Buscar el índice de "templates"
        templates_idx = parts.index("templates")
        if templates_idx + 1 < len(parts):
            app_name = parts[templates_idx + 1]
            
            # Caso 1: templates/<app>/archivo.html (archivo directamente en templates/<app>/)
            if templates_idx + 2 >= len(parts):
                # Es un archivo directamente en templates/<app>/
                # Esto es válido para base.html en templates/tenant/
                if file_path.name == "base.html" and app_name == "tenant":
                    return True, ""
                return True, ""  # Otros archivos en templates/<app>/ también son válidos
            
            # Caso 2: templates/<app>/<namespace>/archivo.html
            namespace = parts[templates_idx + 2]
            
            # Si es base.html en templates/tenant/, está bien
            if file_path.name == "base.html" and app_name == "tenant" and namespace == "tenant":
                return True, ""
            
            # Namespaces válidos: nombre de app, "tenant", "partials", "errors"
            if namespace not in [app_name, "tenant", "partials", "errors", "base"]:
                # Verificar si es un subdirectorio válido (errors/, partials/, etc.)
                if namespace.endswith('.html'):
                    # Es el nombre del archivo, no un namespace
                    return True, ""
                return False, f"Namespace incorrecto: esperado '{app_name}' o 'tenant', encontrado '{namespace}'"
    except ValueError:
        # Si no tiene "templates" en la ruta, no es un template (puede ser un archivo de test)
        if "test" in file_path.name.lower():
            return True, ""  # Archivos de test no se auditan
        return False, "No se encontró directorio 'templates' en la ruta"
    
    return True, ""


def audit_templates():
    """Audita todos los templates en TENANT_APPS."""
    print("[AUDIT] Auditoria de templates y hardcodes de marca...")
    print(f"[DIR] Directorio: {TENANT_APPS_DIR}")
    print()
    
    template_files = []
    other_files = []
    
    # Buscar todos los archivos relevantes
    for root, dirs, files in os.walk(TENANT_APPS_DIR):
        root_path = Path(root)
        
        # Excluir directorios
        dirs[:] = [d for d in dirs if not should_exclude_file(root_path / d)]
        
        for file in files:
            file_path = root_path / file
            
            if should_exclude_file(file_path):
                continue
            
            if file_path.suffix in ALLOWED_EXTENSIONS:
                if "templates" in str(file_path):
                    template_files.append(file_path)
                else:
                    other_files.append(file_path)
    
    print(f"[INFO] Templates encontrados: {len(template_files)}")
    print(f"[INFO] Otros archivos: {len(other_files)}")
    print()
    
    # Auditar templates
    print("[AUDIT] Verificando estructura de templates...")
    for template_file in template_files:
        # Verificar namespacing
        is_valid, msg = check_namespacing(template_file)
        if not is_valid:
            errors.append(f"[ERROR] {template_file}: {msg}")
        
        # Verificar estructura
        is_valid, issues = check_template_structure(template_file)
        if not is_valid:
            for issue in issues:
                errors.append(f"[ERROR] {template_file}: {issue}")
    
    # Auditar hardcodes
    print("[AUDIT] Buscando hardcodes de marca...")
    all_files = template_files + other_files
    for file_path in all_files:
        issues = check_branding_hardcodes(file_path)
        for issue in issues:
            errors.append(f"[ERROR] {file_path}: {issue}")
    
    return len(errors) == 0


def main():
    """Función principal."""
    print("=" * 80)
    print("AUDITORÍA DE TEMPLATES Y BRANDING - TENANT_APPS")
    print("=" * 80)
    print()
    
    success = audit_templates()
    
    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print()
    
    if warnings:
        print(f"[WARN] Warnings: {len(warnings)}")
        for warning in warnings[:10]:  # Mostrar solo los primeros 10
            print(f"  {warning}")
        if len(warnings) > 10:
            print(f"  ... y {len(warnings) - 10} mas")
        print()
    
    if errors:
        print(f"[ERROR] Errores encontrados: {len(errors)}")
        for error in errors[:20]:  # Mostrar solo los primeros 20
            print(f"  {error}")
        if len(errors) > 20:
            print(f"  ... y {len(errors) - 20} mas")
        print()
        print("[FAIL] AUDITORIA FALLO")
        sys.exit(1)
    else:
        print("[OK] AUDITORIA PASO - Sin errores encontrados")
        if warnings:
            print(f"[WARN] {len(warnings)} warnings (revisar manualmente)")
        sys.exit(0)


if __name__ == "__main__":
    main()
