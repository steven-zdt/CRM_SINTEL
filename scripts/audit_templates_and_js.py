#!/usr/bin/env python
"""
Auditoría de templates y JavaScript para cumplimiento API-First.

[WARNING] POLÍTICA:
- Verifica que templates sigan estructura estándar Django (namespacing, herencia, partials)
- Detecta URLs absolutas y llamadas directas a endpoints no Core en JS
- Valida que el dashboard shell use módulos ES y consuma solo Core API
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent

# Apps tenant a auditar
TENANT_APPS = ['empresa', 'facturas', 'contabilidad', 'perfil', 'dashboard', 'core']

# Patrones prohibidos
ABSOLUTE_URL_PATTERN = re.compile(r'https?://')
DIRECT_APP_ENDPOINT_PATTERN = re.compile(
    r"fetch\(['\"]/api/v1/(empresa|facturas|contabilidad|perfil)/"
)
SINGULAR_EMPRESA_PATTERN = re.compile(r"/api/v1/empresa/")
INLINE_SCRIPT_PATTERN = re.compile(r'<script[^>]*>(?!.*type=["\']module["\']).*?</script>', re.DOTALL)

# Endpoints Core permitidos
CORE_ENDPOINTS = [
    '/api/v1/core/dashboard/sections/',
    '/api/v1/core/links/',
    '/api/v1/core/dashboard/',
    '/api/v1/core/mi-empresa/',
    '/api/v1/core/mi-perfil/',
    '/api/v1/core/facturas/resumen/',
    '/api/v1/core/contabilidad/resumen/',
]

# Errores encontrados
errors: List[Tuple[str, str, int]] = []
warnings: List[Tuple[str, str, int]] = []


def check_template_structure(file_path: Path) -> None:
    """Verifica estructura de template Django."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Verificar namespacing (debe estar en templates/<app>/...)
    rel_path = file_path.relative_to(PROJECT_ROOT)
    parts = rel_path.parts
    
    # Buscar 'templates' en la ruta
    if 'templates' not in parts:
        return  # No es un template
    
    templates_idx = parts.index('templates')
    if templates_idx + 1 >= len(parts):
        warnings.append((str(file_path), "Template sin namespacing por app", 0))
        return
    
    app_name = parts[templates_idx + 1]
    
    # Partials no necesitan {% extends %} (son fragmentos)
    if 'partials' in parts or file_path.name.startswith('_'):
        return  # Es un partial, no necesita extends
    
    # base.html es la plantilla base, no necesita extends
    if file_path.name == 'base.html':
        return  # Es la base, no necesita extends
    
    # Verificar que extienda una base (solo templates principales)
    if '{% extends' not in content:
        warnings.append((str(file_path), "Template sin {% extends %}", 0))
    
    # Verificar uso de partials dentro de bloques
    if '{% include' in content:
        # Verificar que los includes estén dentro de bloques
        include_pattern = re.compile(r'{%\s*include\s+["\']([^"\']+)["\']')
        extends_pattern = re.compile(r'{%\s*extends\s+["\']([^"\']+)["\']')
        
        has_extends = bool(extends_pattern.search(content))
        includes = include_pattern.findall(content)
        
        if includes and not has_extends:
            # Permitir si es un partial
            if 'partials' not in parts and not file_path.name.startswith('_'):
                warnings.append((str(file_path), "Template con {% include %} pero sin {% extends %}", 0))


def check_js_file(file_path: Path) -> None:
    """Verifica JavaScript para cumplimiento API-First."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Verificar URLs absolutas
    for i, line in enumerate(lines, 1):
        if ABSOLUTE_URL_PATTERN.search(line):
            # Permitir CDN (tailwindcss, font-awesome) en HTML
            if file_path.suffix == '.html' and ('cdn' in line.lower() or 'cdnjs' in line.lower()):
                continue
            # Permitir validaciones de URLs absolutas en código (startsWith, includes, etc.)
            if 'startsWith' in line or 'includes' in line or 'match' in line or 'test' in line:
                continue
            # Permitir w3.org (SVG, etc.)
            if 'w3.org' in line:
                continue
            errors.append((str(file_path), f"URL absoluta encontrada: {line.strip()[:80]}", i))
        
        # Verificar llamadas directas a endpoints no Core
        if DIRECT_APP_ENDPOINT_PATTERN.search(line):
            # Permitir si es para CRUD específico de la app (no agregación)
            if '/api/v1/core/' not in line:
                errors.append((str(file_path), f"Llamada directa a endpoint no Core: {line.strip()[:80]}", i))
        
        # Verificar URL singular de empresa (permitir si es para detectar/corregir)
        if SINGULAR_EMPRESA_PATTERN.search(line):
            # Permitir si es código de detección/corrección
            if 'includes' in line or 'replace' in line or 'corregir' in line.lower() or 'detect' in line.lower():
                continue
            warnings.append((str(file_path), f"URL singular /api/v1/empresa/ encontrada (debe ser /api/v1/empresas/)", i))


def check_dashboard_shell(file_path: Path) -> None:
    """Verifica que el dashboard shell use módulos ES."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Verificar que use type="module"
    has_module_script = bool(re.search(r'<script[^>]*type=["\']module["\']', content))
    
    if not has_module_script:
        errors.append((str(file_path), "Dashboard shell debe usar <script type='module'>", 0))
    
    # Verificar que no tenga scripts inline grandes
    inline_scripts = INLINE_SCRIPT_PATTERN.findall(content)
    for script in inline_scripts:
        if len(script) > 200:  # Scripts grandes deben ser módulos
            warnings.append((str(file_path), f"Script inline grande encontrado (debe ser módulo ES)", 0))
    
    # Verificar que consuma Core API (puede estar en el módulo JS importado)
    # Verificar que importe el módulo dashboard.js
    if '/static/tenant/dashboard/js/dashboard.js' not in content:
        errors.append((str(file_path), "Dashboard shell debe importar /static/tenant/dashboard/js/dashboard.js", 0))
    
    # Verificar que el módulo JS exista y consuma Core API
    dashboard_js_path = PROJECT_ROOT / 'apps' / 'tenant' / 'dashboard' / 'static' / 'tenant' / 'dashboard' / 'js' / 'dashboard.js'
    if dashboard_js_path.exists():
        js_content = dashboard_js_path.read_text(encoding='utf-8')
        if '/api/v1/core/dashboard/sections/' not in js_content:
            errors.append((str(dashboard_js_path), "Dashboard JS debe consumir /api/v1/core/dashboard/sections/", 0))


def main():
    """Ejecuta la auditoría."""
    print("🔍 Auditoría de templates y JavaScript (API-First)...")
    print("=" * 70)
    
    # Buscar templates
    templates_dir = PROJECT_ROOT / 'apps' / 'tenant'
    for app_name in TENANT_APPS:
        app_templates = templates_dir / app_name / 'templates'
        if app_templates.exists():
            for template_file in app_templates.rglob('*.html'):
                check_template_structure(template_file)
    
    # Buscar archivos JS
    static_dir = PROJECT_ROOT / 'apps' / 'tenant'
    for app_name in TENANT_APPS:
        app_static = static_dir / app_name / 'static'
        if app_static.exists():
            for js_file in app_static.rglob('*.js'):
                check_js_file(js_file)
            
            # Verificar dashboard shell específicamente
            dashboard_html = app_static / 'tenant' / 'dashboard' / 'index.html'
            if dashboard_html.exists():
                check_dashboard_shell(dashboard_html)
    
    # Reportar resultados
    print(f"\n[OK] Verificaciones completadas")
    print(f"   - Templates revisados")
    print(f"   - Archivos JS revisados")
    print(f"   - Dashboard shell verificado")
    
    if warnings:
        print(f"\n[WARNING]  ADVERTENCIAS ({len(warnings)}):")
        for file_path, message, line in warnings:
            print(f"   {file_path}:{line} - {message}")
    
    if errors:
        print(f"\n[ERROR] ERRORES ({len(errors)}):")
        for file_path, message, line in errors:
            print(f"   {file_path}:{line} - {message}")
        print("\n[ERROR] Auditoría FALLIDA")
        sys.exit(1)
    else:
        print("\n[OK] Auditoría EXITOSA")
        sys.exit(0)


if __name__ == '__main__':
    main()
