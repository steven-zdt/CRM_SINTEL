#!/usr/bin/env python
"""
Script de auditoría para verificar cumplimiento de reglas de UI en Tenant Apps.

Verifica que todas las apps en TENANT_APPS sigan el estándar:
- Templates que extienden tenant/base.html
- Vistas TemplateView + LoginRequiredMixin
- Rutas registradas en urls_tenant.py
- Tests de humo existentes
- JavaScript consume APIs (no hay datos server-side)

Uso:
    python scripts/audit_tenant_ui_compliance.py
"""
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings


class TenantUIComplianceAuditor:
    """Auditor de cumplimiento de reglas de UI para Tenant Apps."""
    
    def __init__(self):
        self.base_dir = BASE_DIR
        self.tenant_apps = [app for app in settings.TENANT_APPS if app.startswith('apps.tenant.')]
        # Apps que NO requieren páginas de UI (solo APIs o funcionalidad interna)
        self.excluded_apps = ['core', 'landing']  # core: solo errores, landing: solo APIs
        self.issues = []
        self.warnings = []
        self.success = []
    
    def audit_all(self) -> Dict[str, List[str]]:
        """Ejecuta todas las auditorías."""
        print("Auditoria de Cumplimiento de Reglas de UI para Tenant Apps\n")
        print("=" * 80)
        
        for app_path in self.tenant_apps:
            app_name = app_path.split('.')[-1]
            
            # Saltar apps excluidas
            if app_name in self.excluded_apps:
                print(f"\n[*] Skipping: {app_name} (excluded from UI compliance)")
                continue
            
            print(f"\n[*] Auditing: {app_name}")
            print("-" * 80)
            
            self.audit_app(app_name)
        
        return {
            'issues': self.issues,
            'warnings': self.warnings,
            'success': self.success,
        }
    
    def audit_app(self, app_name: str):
        """Audita una app específica."""
        app_dir = self.base_dir / 'apps' / 'tenant' / app_name
        
        if not app_dir.exists():
            self.warnings.append(f"{app_name}: Directorio no existe")
            print(f"  [WARNING]  Directorio no existe: {app_dir}")
            return
        
        # 1. Verificar template
        template_path = app_dir / 'templates' / 'tenant' / app_name / 'page.html'
        has_template = template_path.exists()
        
        if has_template:
            self.success.append(f"{app_name}: Template existe")
            print(f"  [OK] Template existe: {template_path.relative_to(self.base_dir)}")
            
            # Verificar que extiende tenant/base.html
            template_content = template_path.read_text(encoding='utf-8')
            if '{% extends \'tenant/base.html\' %}' in template_content or '{% extends "tenant/base.html" %}' in template_content:
                self.success.append(f"{app_name}: Template extiende tenant/base.html")
                print(f"  [OK] Template extiende tenant/base.html")
            else:
                self.issues.append(f"{app_name}: Template NO extiende tenant/base.html")
                print(f"  [ERROR] Template NO extiende tenant/base.html")
            
            # Verificar que no hay datos server-side (excepto branding)
            if re.search(r'\{\{.*\.(razon_social|nit|email|telefono|direccion)', template_content):
                self.warnings.append(f"{app_name}: Template puede tener datos server-side")
                print(f"  [WARN] Template puede tener datos server-side (revisar manualmente)")
        else:
            self.warnings.append(f"{app_name}: Template NO existe")
            print(f"  [WARN] Template NO existe: {template_path.relative_to(self.base_dir)}")
        
        # 2. Verificar vista
        views_path = app_dir / 'views.py'
        has_views = views_path.exists()
        
        if has_views:
            views_content = views_path.read_text(encoding='utf-8')
            
            # Buscar TemplateView
            if 'TemplateView' in views_content:
                self.success.append(f"{app_name}: Vista existe")
                print(f"  [OK] Vista existe: {views_path.relative_to(self.base_dir)}")
                
                # Verificar LoginRequiredMixin
                if 'LoginRequiredMixin' in views_content:
                    self.success.append(f"{app_name}: Vista usa LoginRequiredMixin")
                    print(f"  [OK] Vista usa LoginRequiredMixin")
                else:
                    self.issues.append(f"{app_name}: Vista NO usa LoginRequiredMixin")
                    print(f"  [ERROR] Vista NO usa LoginRequiredMixin")
                
                # Buscar nombre de clase de vista
                view_match = re.search(r'class\s+(\w+PageView)\s*\([^)]*\)', views_content)
                if view_match:
                    view_class = view_match.group(1)
                    self.success.append(f"{app_name}: Vista encontrada: {view_class}")
                    print(f"  [OK] Vista encontrada: {view_class}")
                else:
                    self.warnings.append(f"{app_name}: No se encontró clase *PageView")
                    print(f"  [WARN] No se encontró clase *PageView")
            else:
                self.warnings.append(f"{app_name}: Vista NO usa TemplateView")
                print(f"  [WARN] Vista NO usa TemplateView")
        else:
            self.warnings.append(f"{app_name}: Vista NO existe")
            print(f"  [WARN] Vista NO existe: {views_path.relative_to(self.base_dir)}")
        
        # 3. Verificar ruta en urls_tenant.py
        urls_tenant_path = self.base_dir / 'config' / 'urls_tenant.py'
        if urls_tenant_path.exists():
            urls_content = urls_tenant_path.read_text(encoding='utf-8')
            
            # Buscar import de la app
            import_pattern = rf'from\s+apps\.tenant\.{app_name}\s+import\s+views\s+as\s+{app_name}_views'
            if re.search(import_pattern, urls_content):
                self.success.append(f"{app_name}: Import encontrado en urls_tenant.py")
                print(f"  [OK] Import encontrado en urls_tenant.py")
            else:
                self.warnings.append(f"{app_name}: Import NO encontrado en urls_tenant.py")
                print(f"  [WARN] Import NO encontrado en urls_tenant.py")
            
            # Buscar ruta
            route_pattern = rf"path\('{app_name}/',\s+{app_name}_views\.\w+PageView\.as_view\(\),\s+name='tenant-{app_name}-page'\)"
            if re.search(route_pattern, urls_content):
                self.success.append(f"{app_name}: Ruta registrada en urls_tenant.py")
                print(f"  [OK] Ruta registrada en urls_tenant.py")
            else:
                self.issues.append(f"{app_name}: Ruta NO registrada en urls_tenant.py")
                print(f"  [ERROR] Ruta NO registrada en urls_tenant.py")
        
        # 4. Verificar tests (buscar en ambas ubicaciones posibles)
        tests_dir_app = app_dir / 'tests'
        tests_dir_root = self.base_dir / 'tests' / 'tenant' / app_name
        test_file_app = tests_dir_app / f'test_{app_name}_page_smoke.py'
        test_file_root = tests_dir_root / f'test_{app_name}_page_smoke.py'
        
        if test_file_app.exists():
            self.success.append(f"{app_name}: Tests de humo existen")
            print(f"  [OK] Tests de humo existen: {test_file_app.relative_to(self.base_dir)}")
        elif test_file_root.exists():
            self.success.append(f"{app_name}: Tests de humo existen")
            print(f"  [OK] Tests de humo existen: {test_file_root.relative_to(self.base_dir)}")
        else:
            self.warnings.append(f"{app_name}: Tests de humo NO existen")
            print(f"  [WARN] Tests de humo NO existen (buscado en {test_file_app.relative_to(self.base_dir)} y {test_file_root.relative_to(self.base_dir)})")
    
    def print_summary(self):
        """Imprime resumen de la auditoría."""
        print("\n" + "=" * 80)
        print("RESUMEN DE AUDITORIA")
        print("=" * 80)
        
        print(f"\n[OK] Exitos: {len(self.success)}")
        for item in self.success:
            print(f"  [OK] {item}")
        
        print(f"\n[WARN] Advertencias: {len(self.warnings)}")
        for item in self.warnings:
            print(f"  [WARN] {item}")
        
        print(f"\n[ERROR] Problemas: {len(self.issues)}")
        for item in self.issues:
            print(f"  [ERROR] {item}")
        
        print("\n" + "=" * 80)
        
        if self.issues:
            print("[ERROR] HAY PROBLEMAS QUE DEBEN CORREGIRSE")
            return 1
        elif self.warnings:
            print("[WARN] HAY ADVERTENCIAS (revisar manualmente)")
            return 0
        else:
            print("[OK] TODO CORRECTO")
            return 0


def main():
    """Función principal."""
    auditor = TenantUIComplianceAuditor()
    auditor.audit_all()
    exit_code = auditor.print_summary()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
