"""
Script de auditoría para detectar violaciones del patrón Core-Only UI.

Escanea todas las apps privadas de tenant (TENANT_APPS excepto core) y detecta:
1. TemplateView / HTML endpoints
2. Templates no-partial (páginas completas)
3. JS/CSS UI en static/tenant/<app>/
4. Rutas en TENANT_URLCONF que expongan UI directamente
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Apps privadas a auditar (excluyendo core)
TENANT_APPS = ["empresa", "facturas", "contabilidad", "perfil", "dashboard", "landing"]

def find_template_views(app_name):
    """Busca TemplateView o vistas que rendericen HTML."""
    violations = []
    views_files = [
        BASE_DIR / f"apps/tenant/{app_name}/views.py",
        BASE_DIR / f"apps/tenant/{app_name}/views_ui.py",
    ]
    
    for views_file in views_files:
        if views_file.exists():
            with open(views_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'TemplateView' in content or 'render(' in content:
                    violations.append(str(views_file))
    
    return violations

def find_non_partial_templates(app_name):
    """Busca templates que NO sean partials."""
    violations = []
    templates_dir = BASE_DIR / f"apps/tenant/{app_name}/templates"
    
    if templates_dir.exists():
        for html_file in templates_dir.rglob("*.html"):
            # Partials están en subdirectorio "partials/"
            if "partials" not in str(html_file):
                violations.append(str(html_file))
    
    return violations

def find_ui_static_files(app_name):
    """Busca JS/CSS UI en static/tenant/<app>/."""
    violations = []
    static_dirs = [
        BASE_DIR / f"apps/tenant/{app_name}/static/tenant/{app_name}",
        BASE_DIR / f"apps/tenant/{app_name}/static/{app_name}",
    ]
    
    for static_dir in static_dirs:
        if static_dir.exists():
            for js_file in static_dir.rglob("*.js"):
                violations.append(str(js_file))
            for css_file in static_dir.rglob("*.css"):
                violations.append(str(css_file))
    
    return violations

def find_ui_routes_in_urls_tenant(app_name):
    """Busca rutas en config/urls_tenant.py que expongan UI directamente."""
    violations = []
    urls_tenant = BASE_DIR / "config/urls_tenant.py"
    
    if urls_tenant.exists():
        with open(urls_tenant, 'r', encoding='utf-8') as f:
            content = f.read()
            # Buscar rutas que NO sean redirects ni /ui/<app>/partials/
            patterns = [
                f"path('{app_name}/'",  # Ruta directa sin redirect
                f"path('{app_name}s/'",  # Plural sin redirect
            ]
            for pattern in patterns:
                if pattern in content:
                    # Verificar que no sea RedirectView
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if pattern in line:
                            # Verificar las siguientes líneas
                            next_lines = '\n'.join(lines[i:i+3])
                            if 'RedirectView' not in next_lines:
                                violations.append(f"Line {i+1}: {line.strip()}")
    
    return violations

def audit_app(app_name):
    """Audita una app completa."""
    print(f"\n{'='*80}")
    print(f"AUDITORÍA: apps/tenant/{app_name}")
    print(f"{'='*80}")
    
    violations = {
        'template_views': find_template_views(app_name),
        'non_partial_templates': find_non_partial_templates(app_name),
        'ui_static_files': find_ui_static_files(app_name),
        'ui_routes': find_ui_routes_in_urls_tenant(app_name),
    }
    
    total = sum(len(v) for v in violations.values())
    
    if total == 0:
        print(f"[OK] {app_name}: Sin violaciones detectadas")
    else:
        print(f"[WARNING]  {app_name}: {total} violación(es) detectada(s)")
        
        if violations['template_views']:
            print(f"\n  📄 TemplateView/HTML endpoints:")
            for v in violations['template_views']:
                print(f"    - {v}")
        
        if violations['non_partial_templates']:
            print(f"\n  📋 Templates no-partial:")
            for v in violations['non_partial_templates']:
                print(f"    - {v}")
        
        if violations['ui_static_files']:
            print(f"\n  [PAINT] JS/CSS UI en static:")
            for v in violations['ui_static_files']:
                print(f"    - {v}")
        
        if violations['ui_routes']:
            print(f"\n  🔗 Rutas UI directas en urls_tenant.py:")
            for v in violations['ui_routes']:
                print(f"    - {v}")
    
    return violations

def main():
    """Ejecuta auditoría completa."""
    print("="*80)
    print("AUDITORÍA DE VIOLACIONES: Patrón Core-Only UI")
    print("="*80)
    print("\nReglas:")
    print("1. Apps privadas NO deben exponer TemplateView/HTML endpoints")
    print("2. Solo partials HTML permitidos (en templates/tenant/<app>/partials/)")
    print("3. JS/CSS UI debe estar centralizado en apps/tenant/core/static/")
    print("4. Rutas UI deben redirigir a /workspace/#<app> o ser removidas")
    print("="*80)
    
    all_violations = {}
    for app_name in TENANT_APPS:
        all_violations[app_name] = audit_app(app_name)
    
    # Resumen
    print(f"\n{'='*80}")
    print("RESUMEN")
    print(f"{'='*80}")
    total_violations = sum(sum(len(v) for v in violations.values()) for violations in all_violations.values())
    print(f"Total de violaciones detectadas: {total_violations}")
    
    apps_with_violations = [app for app, violations in all_violations.items() 
                           if sum(len(v) for v in violations.values()) > 0]
    
    if apps_with_violations:
        print(f"\nApps con violaciones: {', '.join(apps_with_violations)}")
    else:
        print("\n[OK] Todas las apps cumplen con el patrón Core-Only UI")

if __name__ == "__main__":
    main()
